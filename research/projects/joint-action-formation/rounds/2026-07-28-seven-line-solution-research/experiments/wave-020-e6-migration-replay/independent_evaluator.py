"""Independent SQLite evaluator for Wave 020 E6.

This evaluator does not import the runtime implementation or trust its
in-memory summaries.  It reconstructs the claim from frozen files, signatures,
history rows, owner stores, TargetOperationLedger rows, and the durable fence.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import re
import sqlite3
import sys
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


PLATFORM_ID = "PluralClosure:ExecutionRuntime"
TARGET_ID = "VenueV:CircuitC7"
OPERATION_ID = "CE001:VenueV:CircuitC7:3kW:45m"
Q_VERSION = "Q@v1"
GENESIS_HASH = "0" * 64
SANITIZED_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "PYTHONHASHSEED": "0",
    "__CF_USER_TEXT_ENCODING": f"0x{os.getuid():X}:0x19:0x34",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def without(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


def verify_record(
    record: Mapping[str, Any],
    *,
    public_key: str,
    digest_field: str,
) -> bool:
    try:
        unsigned = without(record, "signature_hex")
        if unsigned.get(digest_field) != sha256_value(
            without(unsigned, digest_field)
        ):
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(unsigned),
        )
        return True
    except Exception:
        return False


def open_immutable(path: pathlib.Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def sqlite_logical_snapshot(path: pathlib.Path) -> dict[str, Any]:
    def encode(value: Any) -> Any:
        if isinstance(value, bytes):
            return {"sqlite_blob_hex": value.hex()}
        return value

    with open_immutable(path) as connection:
        tables = [
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        snapshot: dict[str, Any] = {"tables": {}}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [
                row[1] for row in connection.execute(f"PRAGMA table_info({quoted})")
            ]
            rows = [
                [encode(value) for value in row]
                for row in connection.execute(
                    f"SELECT * FROM {quoted} ORDER BY rowid"
                )
            ]
            snapshot["tables"][table] = {
                "columns": columns,
                "rows": rows,
            }
        return snapshot


def sqlite_companions(path: pathlib.Path) -> list[pathlib.Path]:
    return [
        pathlib.Path(f"{path}-wal"),
        pathlib.Path(f"{path}-shm"),
        pathlib.Path(f"{path}-journal"),
    ]


def sqlite_header_versions(path: pathlib.Path) -> dict[str, int]:
    with path.open("rb") as handle:
        header = handle.read(20)
    if len(header) != 20 or header[:16] != b"SQLite format 3\x00":
        raise ValueError("invalid SQLite header")
    return {
        "write_version": header[18],
        "read_version": header[19],
    }


def verify_formal_database(
    path: pathlib.Path,
    metadata: Mapping[str, Any],
) -> bool:
    try:
        if (
            not path.is_file()
            or any(item.exists() for item in sqlite_companions(path))
        ):
            return False
        with open_immutable(path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        logical_sha256 = sha256_value(sqlite_logical_snapshot(path))
        header_versions = sqlite_header_versions(path)
        return (
            metadata.get("standalone") is True
            and metadata.get("companions_absent") is True
            and metadata.get("logical_match") is True
            and metadata.get("integrity") == "ok"
            and metadata.get("journal_mode") == "delete"
            and integrity == "ok"
            and str(mode).lower() == "delete"
            and file_sha256(path)
            == metadata.get("formal_physical_sha256")
            and logical_sha256 == metadata.get("formal_logical_sha256")
            and metadata.get("source_runtime_logical_sha256")
            == metadata.get("formal_logical_sha256")
            and header_versions
            == {"write_version": 1, "read_version": 1}
            and metadata.get("header_versions") == header_versions
        )
    except Exception:
        return False


def exact_task() -> dict[str, Any]:
    return {
        "schema": "CE001_EXACT_TASK_V1",
        "q_version": Q_VERSION,
        "object_id": TARGET_ID,
        "target_id": TARGET_ID,
        "operation_id": OPERATION_ID,
        "effect_start_minute": 0,
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
        "safety_required": True,
        "noise_required": True,
        "other_circuits_energized": [],
    }


def target_state_is_exact(state: Mapping[str, Any]) -> bool:
    samples = state.get("power_samples")
    return (
        state.get("target_id") == TARGET_ID
        and state.get("energized") is True
        and state.get("power_kw") == 3.0
        and state.get("duration_minutes") == 45
        and state.get("effect_start_minute") == 0
        and state.get("deadline_minute") == 90
        and state.get("safety_ok") is True
        and state.get("noise_ok") is True
        and state.get("other_circuits_energized") == []
        and isinstance(samples, list)
        and len(samples) == 46
        and [item.get("offset_minute") for item in samples] == list(range(46))
        and [item.get("observed_at_minute") for item in samples]
        == list(range(46))
        and all(
            2.85 <= float(item.get("power_kw", 0)) <= 3.15
            and item.get("target_id") == TARGET_ID
            and item.get("safety_ok") is True
            and item.get("noise_ok") is True
            and item.get("other_circuits_energized") == []
            for item in samples
        )
        and int(state["effect_start_minute"]) + 45
        <= int(state["deadline_minute"])
    )


def read_durable(path: pathlib.Path) -> dict[str, Any]:
    with open_immutable(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        config = json.loads(
            connection.execute(
                "SELECT config_json FROM experiment_config"
            ).fetchone()[0]
        )
        runtimes = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM runtimes ORDER BY epoch"
            )
        ]
        startups = [
            {
                **dict(row),
                "visibility": json.loads(row["visibility_json"]),
            }
            for row in connection.execute(
                "SELECT * FROM runtime_startups ORDER BY process_id"
            )
        ]
        history = [
            json.loads(row["event_json"])
            for row in connection.execute(
                "SELECT event_json FROM history ORDER BY sequence"
            )
        ]
        capsule_row = connection.execute("SELECT * FROM capsules").fetchone()
        marker_row = connection.execute(
            "SELECT marker_json FROM durable_markers "
            "WHERE marker='CAPSULE_DURABLE'"
        ).fetchone()
        fence_state = connection.execute(
            "SELECT current_epoch FROM fence_state"
        ).fetchone()[0]
        fence_actions = [
            {
                **dict(row),
                "authentication": json.loads(row["authentication_json"]),
            }
            for row in connection.execute(
                "SELECT * FROM fence_actions ORDER BY rowid"
            )
        ]
        controller_events = [
            {
                **dict(row),
                "payload": json.loads(row["payload_json"]),
            }
            for row in connection.execute(
                "SELECT * FROM controller_events ORDER BY sequence"
            )
        ]
        outcome_row = connection.execute(
            "SELECT * FROM migration_outcomes"
        ).fetchone()
        postconditions = [
            {
                **dict(row),
                "record": json.loads(row["record_json"]),
            }
            for row in connection.execute(
                "SELECT * FROM postconditions ORDER BY kind"
            )
        ]
        runtime_probes = [
            {
                **dict(row),
                "probe": json.loads(row["probe_json"]),
            }
            for row in connection.execute(
                "SELECT * FROM runtime_probes ORDER BY rowid"
            )
        ]
    return {
        "integrity": integrity,
        "journal_mode": mode,
        "config": config,
        "runtimes": runtimes,
        "startups": startups,
        "history": history,
        "capsule_row": dict(capsule_row) if capsule_row else None,
        "marker": json.loads(marker_row[0]) if marker_row else None,
        "fence_state": fence_state,
        "fence_actions": fence_actions,
        "controller_events": controller_events,
        "outcome": (
            {
                **dict(outcome_row),
                "value": json.loads(outcome_row["outcome_json"]),
            }
            if outcome_row
            else None
        ),
        "postconditions": postconditions,
        "runtime_probes": runtime_probes,
    }


def verify_history(
    events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    previous = GENESIS_HASH
    valid = True
    for expected_sequence, event in enumerate(events, 1):
        valid = valid and (
            event.get("sequence") == expected_sequence
            and event.get("prev_hash") == previous
            and verify_record(
                event,
                public_key=str(event.get("signer_public_key_hex")),
                digest_field="event_hash",
            )
        )
        previous = str(event.get("event_hash"))
    return {
        "valid": valid,
        "head_hash": previous,
        "event_types": [str(event.get("event_type")) for event in events],
    }


def verify_startups(
    startups: list[Mapping[str, Any]],
    *,
    frozen: Mapping[str, Any],
) -> dict[str, Any]:
    forbidden = (
        "e6",
        "migration-replay",
        "wave-020",
        "crash_cut",
        "target_epoch",
        "restart_schedule",
        "expected_outcome",
        "recovered_after_migration",
        "remove_target",
    )
    allowed_inputs = {
        frozenset(
            {
                "capsule_store",
                "opaque_runtime_handle",
                "runtime_state_store",
                "target_store",
            }
        ),
        frozenset({"capsule_store", "opaque_runtime_handle"}),
        frozenset(
            {
                "capsule_store",
                "credential_store",
                "opaque_runtime_handle",
                "runtime_state_store",
            }
        ),
        frozenset(
            {
                "capsule_store",
                "migration_view_store",
                "opaque_runtime_handle",
                "owner_sources",
                "runtime_state_store",
                "target_store",
            }
        ),
    }
    values: list[bool] = []
    for startup in startups:
        visibility = startup["visibility"]
        semantic_surface = canonical_bytes(
            {
                "argv": visibility.get("argv"),
                "process_name": visibility.get("process_name"),
                "environment": visibility.get("environment"),
                "input_fields": visibility.get("input_fields"),
            }
        ).decode("utf-8").casefold()
        values.append(
            visibility.get("schema") == "OPAQUE_RUNTIME_STARTUP_V1"
            and visibility.get("process_name") == "opaque-runtime-worker"
            and visibility.get("argv") == ["opaque-runtime-worker"]
            and visibility.get("start_method") == "spawn"
            and visibility.get("cwd_entries") == []
            and re.fullmatch(
                r"opaque-worker-[0-9a-f]{20}",
                pathlib.Path(str(visibility.get("cwd"))).name,
            )
            is not None
            and re.fullmatch(
                r"runtime-[0-9a-f]{32}",
                str(visibility.get("runtime_handle")),
            )
            is not None
            and visibility.get("environment") == SANITIZED_ENVIRONMENT
            and frozenset(visibility.get("input_fields", [])) in allowed_inputs
            and not any(token in semantic_surface for token in forbidden)
            and startup["runtime_handle"]
            in {
                frozen["source_runtime_handle"],
                frozen["migrated_runtime_handle"],
            }
        )
    source_startups = [
        item
        for item in startups
        if item["runtime_handle"] == frozen["source_runtime_handle"]
    ]
    migrated_startups = [
        item
        for item in startups
        if item["runtime_handle"] == frozen["migrated_runtime_handle"]
    ]
    pids = [int(item["process_id"]) for item in startups]
    return {
        "valid": (
            len(startups) == 3
            and len(source_startups) == 2
            and len(migrated_startups) == 1
            and len(set(pids)) == 3
            and all(values)
        ),
        "source_pids": [int(item["process_id"]) for item in source_startups],
        "migrated_pid": (
            int(migrated_startups[0]["process_id"])
            if len(migrated_startups) == 1
            else None
        ),
    }


def verify_target_db(
    path: pathlib.Path,
    *,
    capsule: Mapping[str, Any],
    frozen: Mapping[str, Any],
) -> dict[str, Any]:
    with open_immutable(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        metadata = connection.execute("SELECT * FROM metadata").fetchone()
        target = connection.execute(
            "SELECT * FROM targets WHERE target_id=?", (TARGET_ID,)
        ).fetchone()
        receipts = [
            json.loads(row["receipt_json"])
            for row in connection.execute("SELECT * FROM receipts")
        ]
        readbacks = [
            json.loads(row["readback_json"])
            for row in connection.execute("SELECT * FROM readbacks")
        ]
        commits = [
            dict(row) for row in connection.execute("SELECT * FROM commit_events")
        ]
        capabilities = [
            dict(row) for row in connection.execute("SELECT * FROM capabilities")
        ]
    if metadata is None or target is None:
        return {"valid": False}
    key = bytes.fromhex(metadata["authentication_key_hex"])

    def receipt_valid(receipt: Mapping[str, Any]) -> bool:
        expected_hash = sha256_value(
            without(receipt, "receipt_sha256", "receipt_auth_hex")
        )
        expected_auth = hmac.new(
            key,
            canonical_bytes(without(receipt, "receipt_auth_hex")),
            hashlib.sha256,
        ).hexdigest()
        return (
            receipt.get("receipt_sha256") == expected_hash
            and hmac.compare_digest(
                str(receipt.get("receipt_auth_hex")), expected_auth
            )
        )

    def readback_valid(readback: Mapping[str, Any]) -> bool:
        expected_hash = sha256_value(
            without(readback, "readback_sha256", "readback_auth_hex")
        )
        expected_auth = hmac.new(
            key,
            canonical_bytes(without(readback, "readback_auth_hex")),
            hashlib.sha256,
        ).hexdigest()
        return (
            readback.get("readback_sha256") == expected_hash
            and hmac.compare_digest(
                str(readback.get("readback_auth_hex")), expected_auth
            )
        )

    state = json.loads(target["state_json"])
    evidence = capsule.get("target_evidence") or {}
    receipt = receipts[0] if len(receipts) == 1 else {}
    readback = readbacks[0] if len(readbacks) == 1 else {}
    return {
        "valid": (
            integrity == "ok"
            and str(mode).lower() == "delete"
            and metadata["ledger_id"] == frozen["target_ledger_id"]
            and hashlib.sha256(
                bytes.fromhex(metadata["authentication_key_hex"])
            ).hexdigest()
            == frozen["target_authentication_key_sha256"]
            and len(receipts) == 1
            and len(readbacks) == 1
            and len(commits) == 1
            and len(capabilities) == 1
            and receipt_valid(receipt)
            and readback_valid(readback)
            and evidence.get("receipt") == receipt
            and evidence.get("readback") == readback
            and receipt.get("decision") == "COMMITTED"
            and receipt.get("mutation_applied") is True
            and receipt.get("actor_id") == PLATFORM_ID
            and commits[0].get("actor_id") == PLATFORM_ID
            and readback.get("attached_to_receipt_commit") is True
            and readback.get("observed_commit_id") == receipt.get("commit_id")
            and int(target["version"]) == 1
            and target_state_is_exact(state)
            and readback.get("observed_state") == state
        ),
        "occurrence_count": len(commits),
        "state": state,
        "receipt": receipt,
        "readback": readback,
    }


def verify_owner_stores(
    run_dir: pathlib.Path,
    *,
    owner_paths: Mapping[str, str],
    cut_snapshot: Mapping[str, Any],
    capsule: Mapping[str, Any],
    postconditions: list[Mapping[str, Any]],
    successful: bool,
) -> dict[str, Any]:
    post_by_kind = {item["kind"]: item for item in postconditions}
    heads_valid = True
    acceptances_valid = True
    append_only_valid = True
    process_ids: list[int] = []
    for owner_id in ("O_Q", "O_V", "O_P"):
        path = run_dir / owner_paths[owner_id]
        with open_immutable(path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            state = connection.execute("SELECT * FROM owner_state").fetchone()
            acceptance_rows = list(
                connection.execute("SELECT * FROM acceptances")
            )
            owner_events = [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM owner_events ORDER BY sequence"
                )
            ]
        if state is None:
            heads_valid = False
            continue
        heads_valid = heads_valid and (
            integrity == "ok"
            and str(mode).lower() == "delete"
            and state["head_hash"] == capsule["owner_heads"][owner_id]["head_hash"]
            and json.loads(state["head_json"])
            == capsule["owner_heads"][owner_id]["head"]
            and state["public_key_hex"]
            == capsule["owner_heads"][owner_id]["public_key_hex"]
        )
        cut = cut_snapshot.get(owner_id, {})
        genesis = {
            "sequence": 1,
            "prev_hash": GENESIS_HASH,
            "event_type": "OWNER_HEAD_ANCHORED",
            "record_hash": state["head_hash"],
        }
        append_only_valid = append_only_valid and (
            cut.get("owner_head_hash") == state["head_hash"]
            and cut.get("owner_public_key_hex") == state["public_key_hex"]
            and cut.get("acceptance_count") == 0
            and cut.get("owner_event_count") == 1
            and len(owner_events) == (2 if successful else 1)
            and owner_events[0]["sequence"] == 1
            and owner_events[0]["prev_hash"] == GENESIS_HASH
            and owner_events[0]["event_hash"] == sha256_value(genesis)
            and owner_events[0]["record_hash"] == state["head_hash"]
            and cut.get("owner_event_head_hash")
            == owner_events[0]["event_hash"]
        )
        if owner_id in ("O_Q", "O_V"):
            if successful:
                kind = f"{owner_id}_ACCEPTANCE"
                if len(acceptance_rows) != 1 or kind not in post_by_kind:
                    acceptances_valid = False
                else:
                    acceptance = json.loads(
                        acceptance_rows[0]["acceptance_json"]
                    )
                    acceptances_valid = acceptances_valid and (
                        acceptance == post_by_kind[kind]["record"]
                        and int(post_by_kind[kind]["process_id"])
                        == int(acceptance["process_id"])
                        and verify_record(
                            acceptance,
                            public_key=state["public_key_hex"],
                            digest_field="acceptance_hash",
                        )
                        and acceptance["decision"]
                        == "ACCEPTED_POST_MIGRATION"
                        and acceptance["owner_head_hash"] == state["head_hash"]
                        and acceptance["capsule_hash"] == capsule["capsule_hash"]
                    )
                    process_ids.append(int(acceptance["process_id"]))
                    append_only_valid = append_only_valid and (
                        owner_events[1]["sequence"] == 2
                        and owner_events[1]["prev_hash"]
                        == owner_events[0]["event_hash"]
                        and owner_events[1]["event_type"]
                        == "POST_MIGRATION_ACCEPTANCE"
                        and owner_events[1]["record_hash"]
                        == acceptance["acceptance_hash"]
                        and owner_events[1]["event_hash"]
                        == sha256_value(
                            {
                                "sequence": 2,
                                "prev_hash": owner_events[0]["event_hash"],
                                "event_type": "POST_MIGRATION_ACCEPTANCE",
                                "record_hash": acceptance["acceptance_hash"],
                            }
                        )
                    )
            else:
                acceptances_valid = acceptances_valid and not acceptance_rows
        else:
            acceptances_valid = acceptances_valid and not acceptance_rows
    finality_valid = True
    if successful:
        if "O_P_FINALITY" not in post_by_kind:
            finality_valid = False
        else:
            finality = post_by_kind["O_P_FINALITY"]["record"]
            o_p_public = capsule["owner_heads"]["O_P"]["public_key_hex"]
            expected_acceptance_hashes = [
                post_by_kind[kind]["record_hash"]
                for kind in ("O_Q_ACCEPTANCE", "O_V_ACCEPTANCE")
            ]
            finality_valid = (
                verify_record(
                    finality,
                    public_key=o_p_public,
                    digest_field="finality_hash",
                )
                and finality["decision"] == "RECOVERED_AFTER_MIGRATION"
                and finality["acceptance_hashes"] == expected_acceptance_hashes
                and finality["capsule_hash"] == capsule["capsule_hash"]
                and int(post_by_kind["O_P_FINALITY"]["process_id"])
                == int(finality["process_id"])
            )
            process_ids.append(int(finality["process_id"]))
            o_p_events_path = run_dir / owner_paths["O_P"]
            with open_immutable(o_p_events_path) as connection:
                o_p_events = [
                    dict(row)
                    for row in connection.execute(
                        "SELECT * FROM owner_events ORDER BY sequence"
                    )
                ]
            append_only_valid = append_only_valid and (
                len(o_p_events) == 2
                and o_p_events[1]["prev_hash"] == o_p_events[0]["event_hash"]
                and o_p_events[1]["event_type"] == "POST_MIGRATION_FINALITY"
                and o_p_events[1]["record_hash"] == finality["finality_hash"]
                and o_p_events[1]["event_hash"]
                == sha256_value(
                    {
                        "sequence": 2,
                        "prev_hash": o_p_events[0]["event_hash"],
                        "event_type": "POST_MIGRATION_FINALITY",
                        "record_hash": finality["finality_hash"],
                    }
                )
            )
    else:
        finality_valid = not postconditions
    return {
        "valid": (
            heads_valid
            and acceptances_valid
            and finality_valid
            and append_only_valid
            and (
                len(process_ids) == 3 and len(set(process_ids)) == 3
                if successful
                else not process_ids
            )
        ),
        "heads_valid": heads_valid,
        "acceptances_valid": acceptances_valid,
        "finality_valid": finality_valid,
        "append_only_from_cut_valid": append_only_valid,
        "owner_process_ids": process_ids,
    }


def verify_state_databases(
    run_dir: pathlib.Path,
    state_paths: Mapping[str, str],
    frozen: Mapping[str, Any],
) -> dict[str, Any]:
    values = []
    for key, runtime_id, epoch in (
        ("source_state", frozen["source_runtime_id"], 1),
        ("migrated_state", frozen["migrated_runtime_id"], 2),
    ):
        with open_immutable(run_dir / state_paths[key]) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            row = connection.execute("SELECT * FROM state").fetchone()
        values.append(
            row is not None
            and integrity == "ok"
            and str(mode).lower() == "delete"
            and row["runtime_id"] == runtime_id
            and int(row["epoch"]) == epoch
        )
    return {
        "valid": all(values)
        and frozen["source_runtime_id"] != frozen["migrated_runtime_id"]
        and frozen["source_public_key_hex"]
        != frozen["migrated_public_key_hex"],
    }


def audit_run(artifact_path: pathlib.Path) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    run_dir = artifact_path.parent
    frozen = artifact["frozen_input"]
    formal_paths = artifact["formal_database_paths"]
    successful = artifact["evidence_projection"] == "DURABLE_FULL"
    expected_formal_paths = {
        "formal/durable.sqlite3",
        "formal/source-cut.sqlite3",
        "formal/source-state.sqlite3",
        "formal/migrated-state.sqlite3",
        "formal/owners/o_q.sqlite3",
        "formal/owners/o_v.sqlite3",
        "formal/owners/o_p.sqlite3",
    }
    if successful:
        expected_formal_paths.add("formal/target-ledger.sqlite3")
    declared_formal_paths = {
        formal_paths["durable"],
        formal_paths["source_cut"],
        formal_paths["source_state"],
        formal_paths["migrated_state"],
        *formal_paths["owners"].values(),
    }
    if formal_paths["target"] is not None:
        declared_formal_paths.add(formal_paths["target"])
    formal_layout_valid = (
        declared_formal_paths == expected_formal_paths
        and set(artifact["database_artifacts"]) == expected_formal_paths
        and all(
            not pathlib.Path(relative).is_absolute()
            and pathlib.Path(relative).parts[0] == "formal"
            and ".." not in pathlib.Path(relative).parts
            for relative in declared_formal_paths
        )
        and (formal_paths["target"] is not None) == successful
    )
    frozen_valid = (
        frozen.get("frozen_input_sha256")
        == sha256_value(without(frozen, "frozen_input_sha256"))
        and frozen["task"] == exact_task()
        and frozen["task_sha256"] == sha256_value(exact_task())
    )
    artifact_hash_valid = artifact.get("artifact_sha256") == sha256_value(
        without(artifact, "artifact_sha256")
    )
    database_hashes_valid = True
    for relative, metadata in artifact["database_artifacts"].items():
        path = run_dir / relative
        database_hashes_valid = (
            database_hashes_valid
            and verify_formal_database(path, metadata)
        )
    durable = read_durable(run_dir / formal_paths["durable"])
    source_cut = read_durable(run_dir / formal_paths["source_cut"])
    capsule_row = source_cut["capsule_row"]
    capsule_file = run_dir / artifact["capsule_file"]
    capsule = (
        json.loads(capsule_row["capsule_json"]) if capsule_row else {}
    )
    capsule_valid = bool(capsule_row) and (
        capsule == json.loads(capsule_file.read_text(encoding="utf-8"))
        and file_sha256(capsule_file) == capsule_row["capsule_file_sha256"]
        and file_sha256(capsule_file) == artifact["capsule_file_sha256"]
        and capsule["capsule_hash"] == capsule_row["capsule_hash"]
        and capsule["source_history_head_hash"]
        == capsule_row["source_head_hash"]
        and capsule_row["durability_status"] == "FSYNCED_BEFORE_CRASH"
        and verify_record(
            capsule,
            public_key=frozen["source_public_key_hex"],
            digest_field="capsule_hash",
        )
        and capsule["store_id"] == artifact["store_id"]
        and capsule["operation_id"] == OPERATION_ID
        and capsule["task_sha256"] == frozen["task_sha256"]
        and capsule["restart_schedule_sha256"]
        == frozen["restart_schedule_sha256"]
        and capsule["target_evidence_status"] == "DURABLE_FULL"
        and isinstance(capsule["target_evidence"], dict)
        and capsule["pending_obligations"]
        == ["O_Q_ACCEPTANCE", "O_V_ACCEPTANCE", "O_P_FINALITY"]
    )
    migration_view_file = run_dir / artifact["migration_view_file"]
    migration_view = json.loads(
        migration_view_file.read_text(encoding="utf-8")
    )
    visible_capsule = migration_view.get("visible_capsule", {})
    if successful:
        expected_visible_capsule = capsule
    else:
        expected_visible_capsule = json.loads(canonical_bytes(capsule))
        expected_visible_capsule["target_evidence_status"] = "WITHHELD_AFTER_CUT"
        expected_visible_capsule["target_evidence"] = None
    migration_view_valid = (
        file_sha256(migration_view_file)
        == artifact["migration_view_file_sha256"]
        and verify_record(
            migration_view,
            public_key=frozen["controller_projection_public_key_hex"],
            digest_field="view_hash",
        )
        and migration_view.get("view_hash") == artifact["migration_view_hash"]
        and "projection" not in migration_view
        and "evidence_projection" not in migration_view
        and migration_view.get("source_capsule_hash")
        == capsule.get("capsule_hash")
        and migration_view.get("source_capsule_file_sha256")
        == file_sha256(capsule_file)
        and visible_capsule == expected_visible_capsule
    )
    restart_schedule_file = run_dir / artifact["restart_schedule_file"]
    restart_schedule = json.loads(
        restart_schedule_file.read_text(encoding="utf-8")
    )
    restart_schedule_valid = (
        file_sha256(restart_schedule_file)
        == artifact["restart_schedule_file_sha256"]
        and restart_schedule.get("schedule_sha256")
        == sha256_value(without(restart_schedule, "schedule_sha256"))
        and restart_schedule.get("schedule_sha256")
        == frozen["restart_schedule_sha256"]
        and restart_schedule.get("trigger") == "AFTER_CONTROLLER_REOPEN"
        and restart_schedule.get("runtime_handle")
        == frozen["source_runtime_handle"]
        and restart_schedule.get("runtime_id") == frozen["source_runtime_id"]
        and restart_schedule.get("state_identity") == "source-state.sqlite3"
        and isinstance(restart_schedule.get("challenge_hex"), str)
        and len(restart_schedule["challenge_hex"]) == 64
    )
    history_audit = verify_history(durable["history"])
    source_length = int(capsule.get("source_history_length", -1))
    source_prefix = durable["history"][:source_length]
    source_types = [item.get("event_type") for item in source_prefix]
    prefix_valid = (
        source_length == 3
        and source_types
        == [
            "RUNTIME_STARTED",
            "TARGET_OCCURRENCE_COMMITTED",
            "TARGET_READBACK_OBSERVED",
        ]
        and source_prefix[-1]["event_hash"]
        == capsule.get("source_history_head_hash")
        and all(
            item["signer_public_key_hex"] == frozen["source_public_key_hex"]
            for item in source_prefix
        )
        and not any(
            "ACCEPTANCE" in str(item["event_type"])
            or "FINALITY" in str(item["event_type"])
            for item in source_prefix
        )
        and source_cut["history"] == source_prefix
    )
    source_evidence_isolation_valid = (
        durable["capsule_row"] is None
        and source_cut["capsule_row"] is not None
        and not source_cut["postconditions"]
        and source_cut["outcome"] is None
        and [
            item["event_type"] for item in source_cut["controller_events"]
        ]
        == [
            "CUT_OWNER_NATIVE_SNAPSHOT_BOUND",
            "SOURCE_TERMINATED_AT_HIDDEN_CUT",
        ]
    )
    runtime_probe_valid = (
        len(durable["runtime_probes"]) == 1
        and durable["runtime_probes"][0]["runtime_handle"]
        == frozen["migrated_runtime_handle"]
        and durable["runtime_probes"][0]["process_id"]
        == artifact["migrated_process"]["pid"]
        and durable["runtime_probes"][0]["probe"]
        == {
            "schema": "MIGRATED_EVIDENCE_INTERFACE_PROBE_V1",
            "full_source_capsule_rows_visible": 0,
            "source_capsule_file_input_present": False,
            "controller_private_path_input_present": False,
        }
    )
    startup_audit = verify_startups(durable["startups"], frozen=frozen)
    source_startup_projection = [
        without(item["visibility"], "process_id", "cwd")
        for item in durable["startups"]
        if item["runtime_handle"] == frozen["source_runtime_handle"]
    ]
    source_prefix_projection = [
        {
            "schema": item.get("schema"),
            "sequence": item.get("sequence"),
            "event_type": item.get("event_type"),
            "operation_id": item.get("operation_id"),
            "actor_id": item.get("actor_id"),
            "epoch": item.get("epoch"),
            "payload_shape": (
                {"runtime_handle": item["payload"].get("runtime_handle")}
                if item.get("event_type") == "RUNTIME_STARTED"
                else (
                    {
                        "occurrence_committed": True,
                        "payload_fields": sorted(item["payload"]),
                    }
                    if item.get("event_type") == "TARGET_OCCURRENCE_COMMITTED"
                    else {
                        "target_readback_observed": True,
                        "observed_version": item["payload"].get(
                            "observed_version"
                        ),
                        "payload_fields": sorted(item["payload"]),
                    }
                )
            ),
        }
        for item in source_prefix
    ]
    source_evidence = capsule.get("target_evidence") or {}
    source_receipt = source_evidence.get("receipt") or {}
    source_readback = source_evidence.get("readback") or {}
    source_capsule_projection = {
        "schema": capsule.get("schema"),
        "operation_id": capsule.get("operation_id"),
        "q_version": capsule.get("q_version"),
        "task_sha256": capsule.get("task_sha256"),
        "source_runtime_id": capsule.get("source_runtime_id"),
        "source_runtime_handle": capsule.get("source_runtime_handle"),
        "source_epoch": capsule.get("source_epoch"),
        "source_public_key_hex": capsule.get("source_public_key_hex"),
        "restart_schedule_sha256": capsule.get("restart_schedule_sha256"),
        "source_history_length": capsule.get("source_history_length"),
        "pending_obligations": capsule.get("pending_obligations"),
        "owner_heads": capsule.get("owner_heads"),
        "target_evidence_status": capsule.get("target_evidence_status"),
        "ledger_id": source_evidence.get("ledger_id"),
        "receipt_semantics": {
            "decision": source_receipt.get("decision"),
            "mutation_applied": source_receipt.get("mutation_applied"),
            "actor_id": source_receipt.get("actor_id"),
        },
        "readback_semantics": {
            "attached_to_receipt_commit": source_readback.get(
                "attached_to_receipt_commit"
            ),
            "observed_version": source_readback.get("observed_version"),
            "state": source_readback.get("observed_state"),
        },
    }
    source_equivalence_projection = {
        "prefix": source_prefix_projection,
        "startups": source_startup_projection,
        "capsule": source_capsule_projection,
    }
    source_equivalence_sha256 = sha256_value(source_equivalence_projection)
    marker = source_cut["marker"] or {}
    controller_types = [
        item["event_type"] for item in durable["controller_events"]
    ]
    source_crash_events = [
        item
        for item in durable["controller_events"]
        if item["event_type"] == "SOURCE_TERMINATED_AT_HIDDEN_CUT"
    ]
    cut_snapshot_events = [
        item
        for item in durable["controller_events"]
        if item["event_type"] == "CUT_OWNER_NATIVE_SNAPSHOT_BOUND"
    ]
    migration_projection_events = [
        item
        for item in durable["controller_events"]
        if item["event_type"] == "MIGRATION_INPUT_PROJECTED"
    ]
    cut_snapshot = (
        cut_snapshot_events[0]["payload"]
        if len(cut_snapshot_events) == 1
        else {}
    )
    cut_snapshot_valid = (
        len(cut_snapshot_events) == 1
        and cut_snapshot.get("capsule_hash") == capsule.get("capsule_hash")
        and cut_snapshot.get("source_history_head_hash")
        == capsule.get("source_history_head_hash")
        and cut_snapshot.get("history_count") == 3
        and cut_snapshot.get("postcondition_count") == 0
        and set(cut_snapshot.get("owners", {})) == {"O_Q", "O_V", "O_P"}
        and all(
            item.get("acceptance_count") == 0
            and item.get("owner_event_count") == 1
            for item in cut_snapshot.get("owners", {}).values()
        )
    )
    migration_projection_valid = (
        len(migration_projection_events) == 1
        and migration_projection_events[0]["payload"]["view_hash"]
        == migration_view.get("view_hash")
        and migration_projection_events[0]["payload"]["view_file_sha256"]
        == file_sha256(migration_view_file)
        and migration_projection_events[0]["payload"]["source_capsule_hash"]
        == capsule.get("capsule_hash")
        and set(migration_projection_events[0]["payload"])
        == {"view_hash", "view_file_sha256", "source_capsule_hash"}
    )
    source_crash_valid = (
        marker.get("capsule_hash") == capsule.get("capsule_hash")
        and marker.get("capsule_file_sha256")
        == file_sha256(capsule_file)
        and marker.get("capsule_file_sha256")
        == capsule_row.get("capsule_file_sha256")
        and marker.get("source_history_head_hash")
        == capsule.get("source_history_head_hash")
        and marker.get("source_process_id")
        == artifact["source_process"]["pid"]
        and marker.get("source_epoch") == 1
        and len(source_crash_events) == 1
        and source_crash_events[0]["payload"]["durable_marker_observed"]
        == marker
        and source_crash_events[0]["payload"]["source_process_id"]
        == marker.get("source_process_id")
        and source_crash_events[0]["payload"]["source_result_queue_present"]
        is False
        and int(source_crash_events[0]["payload"]["source_exitcode"]) < 0
    )

    actions = durable["fence_actions"]
    source_actions = [
        item
        for item in actions
        if item["runtime_handle"] == frozen["source_runtime_handle"]
    ]
    migrated_actions = [
        item
        for item in actions
        if item["runtime_handle"] == frozen["migrated_runtime_handle"]
    ]
    accepted_source_execute = [
        item
        for item in source_actions
        if item["action"] == "EXECUTE" and item["decision"] == "ACCEPTED"
    ]
    rejected_old_execute = [
        item
        for item in source_actions
        if item["action"] == "EXECUTE"
        and item["decision"] == "REJECTED"
        and item["reason"] == "STALE_EPOCH"
    ]
    old_authentication = (
        rejected_old_execute[0]["authentication"]
        if len(rejected_old_execute) == 1
        else {}
    )
    old_reopen_authentication_valid = (
        verify_record(
            old_authentication,
            public_key=frozen["source_public_key_hex"],
            digest_field="authentication_hash",
        )
        and old_authentication.get("runtime_id")
        == frozen["source_runtime_id"]
        and old_authentication.get("runtime_handle")
        == frozen["source_runtime_handle"]
        and old_authentication.get("state_identity") == "source-state.sqlite3"
        and old_authentication.get("state_runtime_id")
        == frozen["source_runtime_id"]
        and old_authentication.get("state_epoch") == 1
        and old_authentication.get("state_reopened") is True
        and old_authentication.get("schedule_sha256")
        == restart_schedule.get("schedule_sha256")
        and old_authentication.get("challenge_hex")
        == restart_schedule.get("challenge_hex")
        and old_authentication.get("process_id")
        == rejected_old_execute[0].get("process_id")
    )
    fence_valid = (
        durable["fence_state"] == 2
        and len(source_actions) == 2
        and len(accepted_source_execute) == 1
        and accepted_source_execute[0]["claimed_epoch"] == 1
        and len(rejected_old_execute) == 1
        and rejected_old_execute[0]["claimed_epoch"] == 1
        and old_reopen_authentication_valid
        and len(
            [
                item
                for item in actions
                if item["action"] == "EXECUTE"
                and item["decision"] == "ACCEPTED"
            ]
        )
        == 1
        and len(
            [item for item in actions if item["action"] == "EXECUTE"]
        )
        == 2
        and not any(
            item["action"] == "EXECUTE" for item in migrated_actions
        )
        and [item["action"] for item in migrated_actions]
        == (
            ["IMPORT_CAPSULE", "VERIFY_TARGET", "POSTCONDITIONS_ONLY"]
            if successful
            else ["IMPORT_CAPSULE"]
        )
        and all(
            item["decision"] == "ACCEPTED"
            and item["claimed_epoch"] == 2
            for item in migrated_actions
        )
        and controller_types
        == [
            "CUT_OWNER_NATIVE_SNAPSHOT_BOUND",
            "SOURCE_TERMINATED_AT_HIDDEN_CUT",
            "MIGRATION_INPUT_PROJECTED",
            "EPOCH_ADVANCED_BEFORE_CONTROLLER_CRASH",
            "CONTROLLER_GENERATION_ONE_EXIT_OBSERVED",
            "CONTROLLER_REOPENED_FROM_DURABLE_SQLITE",
            "OLD_RUNTIME_RESTART_OBSERVED",
        ]
        and durable["controller_events"][4]["payload"]["exitcode"] == 73
        and durable["controller_events"][4]["payload"][
            "controller_process_id"
        ]
        == durable["controller_events"][3]["process_id"]
        and len(
            {
                item["process_id"]
                for item in durable["controller_events"]
                if item["event_type"]
                in {
                    "EPOCH_ADVANCED_BEFORE_CONTROLLER_CRASH",
                    "CONTROLLER_REOPENED_FROM_DURABLE_SQLITE",
                }
            }
        )
        == 2
    )
    runtime_rows = {row["epoch"]: row for row in durable["runtimes"]}
    runtime_boundaries_valid = (
        set(runtime_rows) == {1, 2}
        and runtime_rows[1]["public_key_hex"]
        == frozen["source_public_key_hex"]
        and runtime_rows[2]["public_key_hex"]
        == frozen["migrated_public_key_hex"]
        and runtime_rows[1]["runtime_id"] != runtime_rows[2]["runtime_id"]
        and runtime_rows[1]["state_identity"]
        != runtime_rows[2]["state_identity"]
        and startup_audit["migrated_pid"]
        not in startup_audit["source_pids"]
    )
    state_db_audit = verify_state_databases(run_dir, formal_paths, frozen)
    target_audit: dict[str, Any]
    if successful:
        target_path = run_dir / formal_paths["target"]
        target_audit = verify_target_db(
            target_path,
            capsule=capsule,
            frozen=frozen,
        )
        target_condition = (
            artifact["target_ledger_file"] == formal_paths["target"]
            and target_audit["valid"]
            and target_audit["occurrence_count"] == 1
            and capsule["target_evidence_status"] == "DURABLE_FULL"
        )
    else:
        target_audit = {"valid": False, "occurrence_count": "UNRECONCILED"}
        target_condition = (
            artifact["target_ledger_file"] is None
            and formal_paths["target"] is None
            and not (run_dir / "formal/target-ledger.sqlite3").exists()
            and not (run_dir / "target-ledger.sqlite3").exists()
            and capsule.get("target_evidence_status") == "DURABLE_FULL"
            and isinstance(capsule.get("target_evidence"), dict)
            and visible_capsule.get("target_evidence_status")
            == "WITHHELD_AFTER_CUT"
            and visible_capsule.get("target_evidence") is None
        )
    owner_audit = verify_owner_stores(
        run_dir,
        owner_paths=formal_paths["owners"],
        cut_snapshot=cut_snapshot.get("owners", {}),
        capsule=capsule,
        postconditions=durable["postconditions"],
        successful=successful,
    )
    outcome = durable["outcome"]["value"] if durable["outcome"] else {}
    full_types = history_audit["event_types"]
    expected_history_authorities = {
        "RUNTIME_STARTED": (
            frozen["source_runtime_id"],
            1,
            frozen["source_public_key_hex"],
        ),
        "TARGET_OCCURRENCE_COMMITTED": (
            frozen["source_runtime_id"],
            1,
            frozen["source_public_key_hex"],
        ),
        "TARGET_READBACK_OBSERVED": (
            frozen["source_runtime_id"],
            1,
            frozen["source_public_key_hex"],
        ),
        "MIGRATION_IMPORTED": (
            frozen["migrated_runtime_id"],
            2,
            frozen["migrated_public_key_hex"],
        ),
        "TARGET_READBACK_REVERIFIED": (
            frozen["migrated_runtime_id"],
            2,
            frozen["migrated_public_key_hex"],
        ),
        "POSTCONDITIONS_READY": (
            frozen["migrated_runtime_id"],
            2,
            frozen["migrated_public_key_hex"],
        ),
        "MIGRATION_BOUNDED_UNKNOWN": (
            frozen["migrated_runtime_id"],
            2,
            frozen["migrated_public_key_hex"],
        ),
        "O_Q_POST_MIGRATION_ACCEPTANCE": (
            "O_Q",
            2,
            frozen["owner_heads"]["O_Q"]["public_key_hex"],
        ),
        "O_V_POST_MIGRATION_ACCEPTANCE": (
            "O_V",
            2,
            frozen["owner_heads"]["O_V"]["public_key_hex"],
        ),
        "O_P_POST_MIGRATION_FINALITY": (
            "O_P",
            2,
            frozen["owner_heads"]["O_P"]["public_key_hex"],
        ),
    }
    history_authorities_valid = all(
        (
            event.get("actor_id"),
            event.get("epoch"),
            event.get("signer_public_key_hex"),
        )
        == expected_history_authorities.get(event.get("event_type"))
        for event in durable["history"]
    )
    if successful:
        terminal_valid = (
            outcome.get("disposition") == "POSTCONDITIONS_READY"
            and outcome.get("execute_count") == 0
            and outcome.get("postconditions_ready") is True
            and outcome.get("history_head_hash")
            == durable["history"][5]["event_hash"]
            and durable["history"][5]["payload"]["execute_count"] == 0
            and full_types
            == [
                "RUNTIME_STARTED",
                "TARGET_OCCURRENCE_COMMITTED",
                "TARGET_READBACK_OBSERVED",
                "MIGRATION_IMPORTED",
                "TARGET_READBACK_REVERIFIED",
                "POSTCONDITIONS_READY",
                "O_Q_POST_MIGRATION_ACCEPTANCE",
                "O_V_POST_MIGRATION_ACCEPTANCE",
                "O_P_POST_MIGRATION_FINALITY",
            ]
            and len(durable["postconditions"]) == 3
            and owner_audit["valid"]
        )
        disposition = "RECOVERED_AFTER_MIGRATION"
    else:
        terminal_valid = (
            outcome.get("disposition")
            == "BOUNDED_UNKNOWN/UNRECONCILED_EFFECT"
            and outcome.get("execute_count") == 0
            and outcome.get("postconditions_ready") is False
            and outcome.get("history_head_hash")
            == durable["history"][3]["event_hash"]
            and durable["history"][3]["payload"]["target_evidence_valid"]
            is False
            and full_types
            == [
                "RUNTIME_STARTED",
                "TARGET_OCCURRENCE_COMMITTED",
                "TARGET_READBACK_OBSERVED",
                "MIGRATION_BOUNDED_UNKNOWN",
            ]
            and not durable["postconditions"]
            and owner_audit["valid"]
        )
        disposition = "BOUNDED_UNKNOWN/UNRECONCILED_EFFECT"
    common_checks = {
        "artifact_hash_valid": artifact_hash_valid,
        "frozen_input_valid": frozen_valid,
        "formal_database_layout_valid": formal_layout_valid,
        "database_hashes_valid": database_hashes_valid,
        "source_config_arm_blind": (
            "target_evidence_projection" not in durable["config"]
            and "evidence_projection" not in durable["config"]
        ),
        "full_source_evidence_isolated_from_migrated_store": (
            source_evidence_isolation_valid and runtime_probe_valid
        ),
        "durable_store_integrity": (
            durable["integrity"] == "ok"
            and str(durable["journal_mode"]).lower() == "delete"
        ),
        "capsule_valid": capsule_valid,
        "post_cut_migration_view_valid": migration_view_valid,
        "restart_schedule_frozen_and_bound": restart_schedule_valid,
        "source_history_prefix_valid": prefix_valid,
        "history_append_only_valid": history_audit["valid"],
        "history_authorities_valid": history_authorities_valid,
        "source_crash_after_durable_marker": source_crash_valid,
        "cut_owner_native_snapshot_valid": cut_snapshot_valid,
        "post_cut_projection_event_valid": migration_projection_valid,
        "runtime_startups_blind_and_actual": startup_audit["valid"],
        "runtime_boundaries_distinct": runtime_boundaries_valid,
        "runtime_state_databases_distinct": state_db_audit["valid"],
        "persistent_fence_and_old_restart_valid": fence_valid,
        "target_condition_correct": target_condition,
        "terminal_order_and_owner_sources_valid": terminal_valid,
    }
    accepted = all(common_checks.values())
    return {
        "schema": "E6_INDEPENDENT_RUN_AUDIT_V1",
        "accepted": accepted,
        "disposition": disposition if accepted else "INVALID_EVIDENCE",
        "common_checks": common_checks,
        "target_audit": target_audit,
        "owner_audit": owner_audit,
        "history_event_types": full_types,
        "source_history_head_hash": capsule.get("source_history_head_hash"),
        "source_equivalence_projection": source_equivalence_projection,
        "source_equivalence_sha256": source_equivalence_sha256,
        "final_history_head_hash": history_audit["head_hash"],
        "fence_actions": actions,
        "postcondition_count": len(durable["postconditions"]),
        "not_proven": [
            "UNANNOUNCED_PHYSICAL_HARD_CRASH",
            "PHYSICAL_EFFECT",
            "LEGAL_AUTHORITY",
            "OS_LEVEL_NONINTERFERENCE",
            "MALICIOUS_SAME_DIRECTORY_WRITER_RESISTANCE",
        ],
    }


def audit_pair(summary_path: pathlib.Path) -> dict[str, Any]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_valid = summary.get("summary_sha256") == sha256_value(
        without(summary, "summary_sha256")
    )
    baseline_path = summary_path.parent / summary["baseline"]["artifact"]
    removal_path = summary_path.parent / summary["removal"]["artifact"]
    baseline_artifact = json.loads(baseline_path.read_text(encoding="utf-8"))
    removal_artifact = json.loads(removal_path.read_text(encoding="utf-8"))
    baseline = audit_run(baseline_path)
    removal = audit_run(removal_path)
    frozen_equal = (
        baseline_artifact["frozen_input"]
        == removal_artifact["frozen_input"]
    )
    source_equivalent = (
        baseline["source_equivalence_sha256"]
        == removal["source_equivalence_sha256"]
        and baseline["source_equivalence_projection"]
        == removal["source_equivalence_projection"]
    )
    bindings = (
        summary["baseline"]["artifact_sha256"]
        == baseline_artifact["artifact_sha256"]
        and summary["removal"]["artifact_sha256"]
        == removal_artifact["artifact_sha256"]
        and summary["frozen_input_sha256"]
        == baseline_artifact["frozen_input"]["frozen_input_sha256"]
    )
    accepted = (
        summary_valid
        and bindings
        and frozen_equal
        and source_equivalent
        and baseline["accepted"]
        and removal["accepted"]
        and baseline["disposition"] == "RECOVERED_AFTER_MIGRATION"
        and removal["disposition"]
        == "BOUNDED_UNKNOWN/UNRECONCILED_EFFECT"
    )
    return {
        "schema": "E6_INDEPENDENT_PAIR_AUDIT_V1",
        "accepted": accepted,
        "summary_hash_valid": summary_valid,
        "summary_bindings_valid": bindings,
        "same_frozen_input": frozen_equal,
        "source_prefix_startups_capsule_equivalent": source_equivalent,
        "baseline": baseline,
        "removal": removal,
        "accepted_claim": (
            "LOCAL_SYNTHETIC_E6_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE_SCOPED_SOLUTION"
            if accepted
            else "NOT_ACCEPTED"
        ),
        "not_proven": baseline["not_proven"],
    }


def build_root(
    summary_path: pathlib.Path,
    root_path: pathlib.Path,
) -> dict[str, Any]:
    audit = audit_pair(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_root = pathlib.Path(__file__).resolve().parent
    bound: dict[str, pathlib.Path] = {
        "summary": summary_path,
        "baseline_artifact": (
            summary_path.parent / summary["baseline"]["artifact"]
        ),
        "removal_artifact": (
            summary_path.parent / summary["removal"]["artifact"]
        ),
        "runtime_implementation": source_root / "migration_runtime.py",
        "independent_evaluator": source_root / "independent_evaluator.py",
        "suite_runner": source_root / "run.py",
        "contract": source_root / "CONTRACT.md",
        "red_team_matrix": source_root / "INDEPENDENT-RED-TEAM.md",
        "attack_tests": source_root / "tests/test_e6_attacks.py",
        "pytest_configuration": source_root / "pytest.ini",
    }
    for label in ("baseline", "removal"):
        artifact_path = summary_path.parent / summary[label]["artifact"]
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        for relative in artifact["database_artifacts"]:
            bound[f"{label}:{relative}"] = artifact_path.parent / relative
        bound[f"{label}:capsule"] = (
            artifact_path.parent / artifact["capsule_file"]
        )
        bound[f"{label}:migration_view"] = (
            artifact_path.parent / artifact["migration_view_file"]
        )
        bound[f"{label}:restart_schedule"] = (
            artifact_path.parent / artifact["restart_schedule_file"]
        )
    root = {
        "schema": "E6_ROOT_ACCEPTANCE_V1",
        "decision": "ACCEPTED_SCOPED" if audit["accepted"] else "REJECTED",
        "accepted_claim": audit["accepted_claim"],
        "bound_files": {
            name: {
                "path": (
                    str(path.relative_to(source_root))
                    if path.is_relative_to(source_root)
                    else str(path)
                ),
                "sha256": file_sha256(path),
            }
            for name, path in bound.items()
        },
        "independent_pair_audit": audit,
        "not_proven": audit["not_proven"],
    }
    root["root_sha256"] = sha256_value(root)
    root_path.write_text(
        json.dumps(root, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return root


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: independent_evaluator.py SUMMARY.json", file=sys.stderr)
        return 2
    result = audit_pair(pathlib.Path(argv[1]).resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
