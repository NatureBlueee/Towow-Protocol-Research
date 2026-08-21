#!/usr/bin/env python3
"""Run and freeze the local-synthetic E4 actual-process common world."""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import pathlib
import sqlite3
import sys
import tempfile
import uuid
from typing import Any, Dict, Mapping

from evaluator import evaluate_bundle
from runtime import (
    OWNER_IDS,
    arm_worker,
    broker_worker,
    canonical_bytes,
    make_endpoint,
    owner_worker,
    sha256_value,
    target_worker,
    validate_public_startup,
)


HERE = pathlib.Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
OBJECT_ID = "VenueV:CircuitC7"
PRINCIPALS = {
    "RESOURCE_PRIMARY": "principal-resource-primary",
    "RESOURCE_ALTERNATIVE": "principal-resource-alternative",
    "O_V": "principal-venue",
    "O_S": "principal-safety",
    "O_Q": "principal-task-owner",
    "O_P": "principal-obligation-ledger",
}


def _sqlite_header_journal_mode(database_path: pathlib.Path) -> str:
    header = database_path.read_bytes()[:100]
    if len(header) != 100 or header[:16] != b"SQLite format 3\x00":
        return "invalid"
    write_version, read_version = header[18], header[19]
    if (write_version, read_version) == (1, 1):
        return "delete"
    if (write_version, read_version) == (2, 2):
        return "wal"
    return "mixed-or-unknown"


def _sqlite_logical_payload(database_path: pathlib.Path) -> Dict[str, Any]:
    database_uri = "file:%s?mode=ro&immutable=1" % database_path.as_posix()
    with sqlite3.connect(database_uri, uri=True) as connection:
        tables = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        ).fetchall()
        logical_tables = []
        for table_name, create_sql in tables:
            quoted_name = '"%s"' % table_name.replace('"', '""')
            columns = connection.execute(
                "PRAGMA table_info(%s)" % quoted_name
            ).fetchall()
            column_names = [item[1] for item in columns]
            primary_key_columns = [
                item[1]
                for item in sorted(columns, key=lambda item: item[5])
                if item[5] > 0
            ]
            order_columns = primary_key_columns or column_names
            order_sql = ", ".join(
                '"%s"' % item.replace('"', '""') for item in order_columns
            )
            rows = connection.execute(
                "SELECT * FROM %s ORDER BY %s" % (quoted_name, order_sql)
            ).fetchall()
            logical_tables.append(
                {
                    "name": table_name,
                    "create_sql": create_sql,
                    "columns": column_names,
                    "rows": [list(row) for row in rows],
                }
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "schema": "E4_SQLITE_LOGICAL_SNAPSHOT_V1",
        "journal_mode": _sqlite_header_journal_mode(database_path),
        "integrity_check": integrity,
        "tables": logical_tables,
    }


def _freeze_sqlite_database(
    source_path: pathlib.Path,
    destination_path: pathlib.Path,
) -> Dict[str, str]:
    if destination_path.exists():
        raise FileExistsError(destination_path)
    with sqlite3.connect(source_path) as source:
        source.execute("PRAGMA wal_checkpoint(FULL)")
        with sqlite3.connect(destination_path) as destination:
            source.backup(destination)
            journal_mode = destination.execute(
                "PRAGMA journal_mode=DELETE"
            ).fetchone()[0]
            destination.execute("PRAGMA synchronous=FULL")
            integrity = destination.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
            destination.commit()
    if journal_mode.lower() != "delete" or integrity != "ok":
        raise RuntimeError("standalone SQLite freeze failed")
    logical_payload = _sqlite_logical_payload(destination_path)
    if (
        logical_payload["journal_mode"] != "delete"
        or logical_payload["integrity_check"] != "ok"
    ):
        raise RuntimeError("frozen SQLite logical verification failed")
    companions = [
        destination_path.with_name(destination_path.name + suffix)
        for suffix in ("-wal", "-shm", "-journal")
    ]
    # SQLite may leave an empty WAL shared-memory file while switching the
    # freshly backed-up destination header from WAL to DELETE.  Only after the
    # independent immutable read above proves the destination itself is
    # DELETE-journal do we remove those conversion by-products.
    for path in companions:
        path.unlink(missing_ok=True)
    present = [str(path) for path in companions if path.exists()]
    if present:
        raise RuntimeError("standalone SQLite freeze left companions: %s" % present)
    return {
        "journal_mode": "delete",
        "physical_sha256": hashlib.sha256(
            destination_path.read_bytes()
        ).hexdigest(),
        "logical_sha256": hashlib.sha256(
            canonical_bytes(logical_payload)
        ).hexdigest(),
    }


def _digits(length: int) -> str:
    value = str(uuid.uuid4().int)
    return (value * ((length // len(value)) + 1))[:length]


def alpha_shape(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: alpha_shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [alpha_shape(item) for item in value]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if value is None:
        return "null"
    if isinstance(value, str):
        return "str:%d" % len(value)
    return type(value).__name__


def _start_arm_opaque(
    process: multiprocessing.Process, opaque_cwd: str
) -> None:
    original_argv = list(sys.argv)
    original_cwd = os.getcwd()
    try:
        sys.argv = ["blind-child", "--opaque"]
        os.chdir(opaque_cwd)
        process.start()
    finally:
        os.chdir(original_cwd)
        sys.argv = original_argv


def _public_startup(
    *,
    run_binding: str,
    operation_id: str,
    broker_endpoint_handle: str,
    target_endpoint_handle: str,
    extra: Mapping[str, Any] = None,
) -> Dict[str, Any]:
    startup = {
        "schema": "COMMON_ARM_PUBLIC_STARTUP_V1",
        "run_binding": run_binding,
        "arm_binding_token": _digits(32),
        "q_version": "Q@v1",
        "object_id": OBJECT_ID,
        "operation_id": operation_id,
        "deadline_minute": 90,
        "broker_surface": {
            "endpoint_handle": broker_endpoint_handle,
            "capabilities": ["DISCOVER", "REQUEST", "STATUS"],
            "version": 1,
        },
        "target_surface": {
            "endpoint_handle": target_endpoint_handle,
            "capabilities": ["COMMIT", "READBACK"],
            "version": 1,
        },
    }
    if extra:
        startup.update(dict(extra))
    return validate_public_startup(startup)


def run_case(
    *,
    alternative_enabled: bool,
    strategy: str = "NORMAL",
    database_path: pathlib.Path | None = None,
) -> Dict[str, Any]:
    if database_path is None:
        database_path = (
            pathlib.Path(tempfile.mkdtemp(prefix="e4-ledger-"))
            / "target-ledger.sqlite3"
        )
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if database_path.exists():
        raise FileExistsError(database_path)
    runtime_database_temp = tempfile.TemporaryDirectory(
        prefix="e4-runtime-ledger-"
    )
    runtime_database_path = (
        pathlib.Path(runtime_database_temp.name) / "target-ledger.sqlite3"
    )
    ctx = multiprocessing.get_context("spawn")
    ready_queue = ctx.Queue()
    run_binding = _digits(32)
    operation_id = "operation-%s" % _digits(20)
    ledger_id = "ledger-%s" % _digits(24)
    capability_id = "capability-%s" % _digits(24)
    startup = _public_startup(
        run_binding=run_binding,
        operation_id=operation_id,
        broker_endpoint_handle=uuid.uuid4().hex,
        target_endpoint_handle=uuid.uuid4().hex,
    )
    owner_endpoints = {owner: make_endpoint(ctx) for owner in OWNER_IDS}
    owner_processes: Dict[str, multiprocessing.Process] = {}
    for owner_id in OWNER_IDS:
        config = {
            "owner_id": owner_id,
            "principal_id": PRINCIPALS[owner_id],
            "run_binding": run_binding,
            "object_id": OBJECT_ID,
            "operation_id": operation_id,
        }
        process = ctx.Process(
            target=owner_worker,
            name="p-%s" % _digits(16),
            args=(config, owner_endpoints[owner_id], ready_queue),
        )
        process.start()
        owner_processes[owner_id] = process
    ready: Dict[str, Dict[str, Any]] = {}
    for _ in OWNER_IDS:
        item = ready_queue.get(timeout=20)
        ready[item["service_id"]] = item
    if set(ready) != set(OWNER_IDS):
        raise RuntimeError("owner readiness incomplete")

    broker_endpoint = make_endpoint(ctx)
    broker_process = ctx.Process(
        target=broker_worker,
        name="p-%s" % _digits(16),
        args=(
            {
                "run_binding": run_binding,
                "object_id": OBJECT_ID,
                "operation_id": operation_id,
                "alternative_enabled": alternative_enabled,
            },
            owner_endpoints,
            broker_endpoint,
            ready_queue,
        ),
    )
    broker_process.start()
    broker_ready = ready_queue.get(timeout=20)
    if broker_ready["service_id"] != "BROKER":
        raise RuntimeError("broker readiness missing")
    ready["BROKER"] = broker_ready

    owner_registry = {
        owner: ready[owner]["identity"] for owner in OWNER_IDS
    }
    target_endpoint = make_endpoint(ctx)
    target_process = ctx.Process(
        target=target_worker,
        name="p-%s" % _digits(16),
        args=(
            {
                "run_binding": run_binding,
                "object_id": OBJECT_ID,
                "operation_id": operation_id,
                "alternative_enabled": alternative_enabled,
                "alternative_handle": broker_ready["private_handle_map"][
                    "RESOURCE_ALTERNATIVE"
                ],
                "broker_public_key_hex": broker_ready["identity"][
                    "public_key_hex"
                ],
                "owner_registry": owner_registry,
                "database_path": str(runtime_database_path),
                "ledger_id": ledger_id,
                "capability_id": capability_id,
            },
            owner_endpoints,
            target_endpoint,
            ready_queue,
        ),
    )
    target_process.start()
    target_ready = ready_queue.get(timeout=20)
    if target_ready["service_id"] != "TARGET":
        raise RuntimeError("Target readiness missing")
    ready["TARGET"] = target_ready

    arm_result_queue = ctx.Queue()
    arm_process = ctx.Process(
        target=arm_worker,
        name="p-%s" % _digits(16),
        args=(
            startup,
            broker_endpoint,
            target_endpoint,
            arm_result_queue,
            strategy,
        ),
    )
    with tempfile.TemporaryDirectory(prefix="") as arm_cwd:
        _start_arm_opaque(arm_process, arm_cwd)
        arm_result = arm_result_queue.get(timeout=40)
        arm_process.join(timeout=20)
        if arm_process.is_alive():
            arm_process.terminate()
            arm_process.join(timeout=5)
    if arm_process.exitcode != 0:
        raise RuntimeError("arm process failed")
    ready["ARM"] = {"identity": arm_result["identity"]}

    for endpoint in owner_endpoints.values():
        endpoint["control"].put("FREEZE")
    broker_endpoint["control"].put("FREEZE")
    target_endpoint["control"].put("FREEZE")
    owner_logs = {
        owner: owner_endpoints[owner]["result"].get(timeout=20)
        for owner in OWNER_IDS
    }
    broker_log = broker_endpoint["result"].get(timeout=20)
    target_log = target_endpoint["result"].get(timeout=20)

    for process in owner_processes.values():
        process.join(timeout=20)
    broker_process.join(timeout=20)
    target_process.join(timeout=20)
    processes = {
        **owner_processes,
        "BROKER": broker_process,
        "TARGET": target_process,
        "ARM": arm_process,
    }
    exit_codes = {key: process.exitcode for key, process in processes.items()}
    if set(exit_codes.values()) != {0}:
        raise RuntimeError("service process failure: %s" % exit_codes)

    frozen_database = _freeze_sqlite_database(
        runtime_database_path, database_path
    )
    runtime_database_temp.cleanup()

    service_manifest = {
        key: ready[key]["identity"]
        for key in (*OWNER_IDS, "BROKER", "TARGET", "ARM")
    }
    if len(
        {identity["process_id"] for identity in service_manifest.values()}
    ) != len(service_manifest):
        raise RuntimeError("process identity collision")
    if len(
        {
            identity["public_key_hex"]
            for identity in service_manifest.values()
        }
    ) != len(service_manifest):
        raise RuntimeError("process key collision")

    bundle: Dict[str, Any] = {
        "schema": "E4_LOCAL_SYNTHETIC_BUNDLE_V1",
        "run_id": "e4-%s" % _digits(20),
        "arm_startup": startup,
        "service_manifest": service_manifest,
        "arm_result": arm_result,
        "owner_native_logs": owner_logs,
        "broker_native_log": broker_log,
        "target_native_log": target_log,
        "target_truth": {
            "database_file": database_path.name,
            "database_journal_mode": frozen_database["journal_mode"],
            "database_physical_sha256": frozen_database["physical_sha256"],
            "database_logical_sha256": frozen_database["logical_sha256"],
            "ledger_id": ledger_id,
            "capability_id": capability_id,
            "object_id": OBJECT_ID,
            "operation_id": operation_id,
            "exact_state": target_log["exact_state"],
        },
        "runtime": {
            "start_method": ctx.get_start_method(),
            "process_exit_codes": exit_codes,
        },
        "private_case": {
            "alternative_enabled": alternative_enabled,
            "strategy": strategy,
            "semantic_case": (
                "E4-REVOKE-WITH-ALTERNATIVE"
                if alternative_enabled
                else "E4-REMOVE-ALTERNATIVE"
            ),
        },
        "claim_boundary": (
            "LOCAL_SYNTHETIC_E4_EXISTING_COMPOSITION_ONLY; "
            "NO_LEGAL_AUTHORITY_PROOF; NO_PHYSICAL_EFFECT"
        ),
    }
    bundle["evaluation"] = evaluate_bundle(
        bundle, database_path=database_path
    )
    unsigned = dict(bundle)
    bundle["bundle_sha256"] = sha256_value(unsigned)
    return bundle


def run_pair(artifacts_dir: pathlib.Path = ARTIFACTS) -> pathlib.Path:
    pair_id = "pair-%s" % _digits(20)
    output_dir = artifacts_dir / pair_id
    output_dir.mkdir(parents=True, exist_ok=False)
    main = run_case(
        alternative_enabled=True,
        database_path=output_dir / "e4-target-ledger.sqlite3",
    )
    removed = run_case(
        alternative_enabled=False,
        database_path=output_dir / "remove-alternative-target-ledger.sqlite3",
    )
    pair = {
        "schema": "E4_MAIN_REMOVE_ALTERNATIVE_PAIR_V1",
        "pair_id": pair_id,
        "worlds": {
            "E4": main,
            "REMOVE_ALTERNATIVE": removed,
        },
        "startup_alpha_equivalent": (
            alpha_shape(main["arm_startup"])
            == alpha_shape(removed["arm_startup"])
        ),
        "expected_dispositions": {
            "E4": "RECOVERED_VIA_LEGAL_ALTERNATIVE",
            "REMOVE_ALTERNATIVE": "BOUNDED_REFUSAL_NO_ALTERNATIVE",
        },
        "claim_boundary": (
            "LOCAL_SYNTHETIC_PAIRED_COUNTERFACTUAL; "
            "NOT_LEGAL_OR_PHYSICAL_GENERALIZATION"
        ),
        "standalone_databases": {
            "E4": main["target_truth"]["database_file"],
            "REMOVE_ALTERNATIVE": removed["target_truth"]["database_file"],
        },
    }
    pair["pair_sha256"] = sha256_value(pair)
    path = output_dir / "e4-pair.json"
    path.write_text(
        json.dumps(pair, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=pathlib.Path, default=ARTIFACTS)
    args = parser.parse_args()
    path = run_pair(args.artifacts_dir)
    print(json.dumps({"artifact": str(path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
