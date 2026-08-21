"""Executable E6 migration/replay recovery workflow.

The source runtime performs one TargetOperationLedger occurrence, persists a
signed recovery capsule to an external SQLite store, and is then terminated by
the controller without a result queue.  A distinct higher-epoch runtime
imports the capsule and performs postconditions only.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import multiprocessing as mp
import os
import pathlib
import queue
import secrets
import sqlite3
import sys
import tempfile
import time
import uuid
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


WAVE_015 = pathlib.Path(__file__).resolve().parents[1] / "wave-015-runner-foundation"
if str(WAVE_015) not in sys.path:
    sys.path.insert(0, str(WAVE_015))

from target_ledger import COMMITTED, TargetOperationLedger  # noqa: E402


PLATFORM_ID = "PluralClosure:ExecutionRuntime"
TARGET_ID = "VenueV:CircuitC7"
OPERATION_ID = "CE001:VenueV:CircuitC7:3kW:45m"
Q_VERSION = "Q@v1"
SANITIZED_ENVIRONMENT = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
    "PYTHONHASHSEED": "0",
    "__CF_USER_TEXT_ENCODING": f"0x{os.getuid():X}:0x19:0x34",
}
GENESIS_HASH = "0" * 64


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


def private_key_hex(key: Ed25519PrivateKey) -> str:
    return key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()


def public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def key_from_hex(value: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))


def sign_record(
    body: Mapping[str, Any],
    *,
    key: Ed25519PrivateKey,
    digest_field: str,
) -> dict[str, Any]:
    record = dict(body)
    record[digest_field] = sha256_value(record)
    record["signature_hex"] = key.sign(canonical_bytes(record)).hex()
    return record


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


def initial_target_state() -> dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "energized": False,
        "power_kw": 0.0,
        "duration_minutes": 0,
        "safety_ok": True,
        "noise_ok": True,
        "other_circuits_energized": [],
        "power_samples": [],
    }


def exact_target_state() -> dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "energized": True,
        "power_kw": 3.0,
        "duration_minutes": 45,
        "effect_start_minute": 0,
        "deadline_minute": 90,
        "safety_ok": True,
        "noise_ok": True,
        "other_circuits_energized": [],
        "power_samples": [
            {
                "offset_minute": offset,
                "observed_at_minute": offset,
                "target_id": TARGET_ID,
                "power_kw": 3.0,
                "safety_ok": True,
                "noise_ok": True,
                "other_circuits_energized": [],
            }
            for offset in range(46)
        ],
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
        and 0 + 45 <= 90
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
    )


def sqlite_connect(path: str | pathlib.Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=15, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 15000")
    connection.execute("PRAGMA synchronous = FULL")
    return connection


def initialize_durable_store(
    path: pathlib.Path,
    *,
    config: Mapping[str, Any],
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE experiment_config(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                config_json TEXT NOT NULL
            );
            CREATE TABLE runtimes(
                runtime_handle TEXT PRIMARY KEY,
                runtime_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                public_key_hex TEXT NOT NULL,
                state_identity TEXT NOT NULL
            );
            CREATE TABLE runtime_startups(
                startup_id TEXT PRIMARY KEY,
                runtime_handle TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                visibility_json TEXT NOT NULL
            );
            CREATE TABLE history(
                sequence INTEGER PRIMARY KEY,
                event_hash TEXT NOT NULL UNIQUE,
                prev_hash TEXT NOT NULL,
                event_json TEXT NOT NULL,
                signer_id TEXT NOT NULL,
                signer_public_key_hex TEXT NOT NULL
            );
            CREATE TABLE capsules(
                capsule_id TEXT PRIMARY KEY,
                capsule_hash TEXT NOT NULL,
                source_head_hash TEXT NOT NULL,
                capsule_json TEXT NOT NULL,
                capsule_file_sha256 TEXT NOT NULL,
                durability_status TEXT NOT NULL
            );
            CREATE TABLE durable_markers(
                marker TEXT PRIMARY KEY,
                marker_json TEXT NOT NULL
            );
            CREATE TABLE fence_state(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                current_epoch INTEGER NOT NULL
            );
            CREATE TABLE fence_actions(
                action_id TEXT PRIMARY KEY,
                runtime_handle TEXT NOT NULL,
                claimed_epoch INTEGER NOT NULL,
                action TEXT NOT NULL,
                decision TEXT NOT NULL,
                reason TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                authentication_json TEXT NOT NULL
            );
            CREATE TABLE controller_events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE migration_outcomes(
                runtime_handle TEXT PRIMARY KEY,
                disposition TEXT NOT NULL,
                outcome_json TEXT NOT NULL
            );
            CREATE TABLE runtime_probes(
                probe_id TEXT PRIMARY KEY,
                runtime_handle TEXT NOT NULL,
                process_id INTEGER NOT NULL,
                probe_json TEXT NOT NULL
            );
            CREATE TABLE postconditions(
                kind TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                record_json TEXT NOT NULL,
                process_id INTEGER NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO experiment_config VALUES(1, ?)",
            (canonical_bytes(config).decode("utf-8"),),
        )
        for runtime in config["runtimes"]:
            connection.execute(
                "INSERT INTO runtimes VALUES(?, ?, ?, ?, ?)",
                (
                    runtime["runtime_handle"],
                    runtime["runtime_id"],
                    runtime["epoch"],
                    runtime["public_key_hex"],
                    runtime["state_identity"],
                ),
            )
        connection.execute("INSERT INTO fence_state VALUES(1, 1)")
        connection.commit()
    finally:
        connection.close()


def initialize_owner_store(
    path: pathlib.Path,
    *,
    owner: Mapping[str, Any],
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(
            """
            CREATE TABLE owner_state(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                owner_id TEXT NOT NULL,
                principal_id TEXT NOT NULL,
                public_key_hex TEXT NOT NULL,
                head_json TEXT NOT NULL,
                head_hash TEXT NOT NULL
            );
            CREATE TABLE acceptances(
                acceptance_hash TEXT PRIMARY KEY,
                acceptance_json TEXT NOT NULL
            );
            CREATE TABLE owner_events(
                sequence INTEGER PRIMARY KEY,
                prev_hash TEXT NOT NULL,
                event_hash TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                record_hash TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO owner_state VALUES(1, ?, ?, ?, ?, ?)",
            (
                owner["owner_id"],
                owner["principal_id"],
                owner["public_key_hex"],
                canonical_bytes(owner["head"]).decode("utf-8"),
                owner["head_hash"],
            ),
        )
        genesis_event = {
            "sequence": 1,
            "prev_hash": GENESIS_HASH,
            "event_type": "OWNER_HEAD_ANCHORED",
            "record_hash": owner["head_hash"],
        }
        connection.execute(
            "INSERT INTO owner_events VALUES(1, ?, ?, ?, ?)",
            (
                GENESIS_HASH,
                sha256_value(genesis_event),
                "OWNER_HEAD_ANCHORED",
                owner["head_hash"],
            ),
        )
        connection.commit()
    finally:
        connection.close()


def append_owner_event(
    connection: sqlite3.Connection,
    *,
    event_type: str,
    record_hash: str,
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT sequence, event_hash FROM owner_events "
        "ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    sequence = int(row["sequence"]) + 1
    event = {
        "sequence": sequence,
        "prev_hash": row["event_hash"],
        "event_type": event_type,
        "record_hash": record_hash,
    }
    event_hash = sha256_value(event)
    connection.execute(
        "INSERT INTO owner_events VALUES(?, ?, ?, ?, ?)",
        (
            sequence,
            row["event_hash"],
            event_hash,
            event_type,
            record_hash,
        ),
    )
    return {**event, "event_hash": event_hash}


def capture_owner_cut_snapshot(
    owner_paths: Mapping[str, pathlib.Path],
) -> dict[str, Any]:
    snapshots: dict[str, Any] = {}
    for owner_id, path in owner_paths.items():
        connection = sqlite_connect(path)
        try:
            state = connection.execute("SELECT * FROM owner_state").fetchone()
            events = list(
                connection.execute(
                    "SELECT * FROM owner_events ORDER BY sequence"
                )
            )
            acceptance_count = connection.execute(
                "SELECT COUNT(*) FROM acceptances"
            ).fetchone()[0]
        finally:
            connection.close()
        snapshots[owner_id] = {
            "owner_head_hash": state["head_hash"],
            "owner_public_key_hex": state["public_key_hex"],
            "acceptance_count": int(acceptance_count),
            "owner_event_count": len(events),
            "owner_event_head_hash": events[-1]["event_hash"],
        }
    return snapshots


def configure_target(
    target: TargetOperationLedger,
    *,
    authentication_key_hex: str,
    genesis_commit_id: str,
) -> None:
    connection = sqlite_connect(target.db_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE metadata SET authentication_key_hex=? WHERE singleton=1",
            (authentication_key_hex,),
        )
        connection.execute(
            "UPDATE targets SET last_commit_id=? WHERE target_id=? AND version=0",
            (genesis_commit_id, TARGET_ID),
        )
        connection.commit()
    finally:
        connection.close()


def append_history(
    durable_path: pathlib.Path,
    *,
    event_type: str,
    actor_id: str,
    epoch: int,
    payload: Mapping[str, Any],
    key: Ed25519PrivateKey,
) -> dict[str, Any]:
    connection = sqlite_connect(durable_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT sequence, event_hash FROM history ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = 1 if row is None else int(row["sequence"]) + 1
        prev_hash = GENESIS_HASH if row is None else str(row["event_hash"])
        event = sign_record(
            {
                "schema": "MIGRATION_HISTORY_EVENT_V1",
                "sequence": sequence,
                "prev_hash": prev_hash,
                "event_type": event_type,
                "operation_id": OPERATION_ID,
                "actor_id": actor_id,
                "epoch": epoch,
                "process_id": os.getpid(),
                "payload": dict(payload),
                "signer_public_key_hex": public_key_hex(key),
            },
            key=key,
            digest_field="event_hash",
        )
        connection.execute(
            "INSERT INTO history VALUES(?, ?, ?, ?, ?, ?)",
            (
                sequence,
                event["event_hash"],
                prev_hash,
                canonical_bytes(event).decode("utf-8"),
                actor_id,
                public_key_hex(key),
            ),
        )
        connection.commit()
        return event
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def record_startup(
    durable_path: pathlib.Path,
    *,
    runtime_handle: str,
    input_fields: list[str],
) -> dict[str, Any]:
    visibility = {
        "schema": "OPAQUE_RUNTIME_STARTUP_V1",
        "runtime_handle": runtime_handle,
        "process_id": os.getpid(),
        "process_name": mp.current_process().name,
        "start_method": mp.get_start_method(),
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "cwd_entries": sorted(os.listdir(".")),
        "environment": dict(os.environ),
        "input_fields": sorted(input_fields),
    }
    connection = sqlite_connect(durable_path)
    try:
        connection.execute(
            "INSERT INTO runtime_startups VALUES(?, ?, ?, ?)",
            (
                f"startup-{uuid.uuid4().hex}",
                runtime_handle,
                os.getpid(),
                canonical_bytes(visibility).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return visibility


def append_controller_event(
    durable_path: pathlib.Path,
    *,
    event_type: str,
    payload: Mapping[str, Any],
) -> None:
    connection = sqlite_connect(durable_path)
    try:
        connection.execute(
            "INSERT INTO controller_events(event_type, process_id, payload_json) "
            "VALUES(?, ?, ?)",
            (
                event_type,
                os.getpid(),
                canonical_bytes(payload).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def load_config(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        row = connection.execute(
            "SELECT config_json FROM experiment_config WHERE singleton=1"
        ).fetchone()
        if row is None:
            raise RuntimeError("experiment config missing")
        return json.loads(row["config_json"])
    finally:
        connection.close()


def load_runtime(path: pathlib.Path, runtime_handle: str) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        row = connection.execute(
            "SELECT * FROM runtimes WHERE runtime_handle=?",
            (runtime_handle,),
        ).fetchone()
        if row is None:
            raise RuntimeError("runtime credential missing")
        return dict(row)
    finally:
        connection.close()


def attempt_fenced_action(
    durable_path: pathlib.Path,
    *,
    runtime_handle: str,
    action: str,
    authentication: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    connection = sqlite_connect(durable_path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        runtime = connection.execute(
            "SELECT * FROM runtimes WHERE runtime_handle=?",
            (runtime_handle,),
        ).fetchone()
        fence = connection.execute(
            "SELECT current_epoch FROM fence_state WHERE singleton=1"
        ).fetchone()
        if runtime is None or fence is None:
            raise RuntimeError("fence state incomplete")
        claimed = int(runtime["epoch"])
        current = int(fence["current_epoch"])
        accepted = claimed == current
        result = {
            "schema": "DURABLE_FENCE_ACTION_V1",
            "action_id": f"fence-action-{uuid.uuid4().hex}",
            "runtime_handle": runtime_handle,
            "claimed_epoch": claimed,
            "current_epoch": current,
            "action": action,
            "decision": "ACCEPTED" if accepted else "REJECTED",
            "reason": "CURRENT_EPOCH" if accepted else "STALE_EPOCH",
            "process_id": os.getpid(),
            "authentication": (
                dict(authentication)
                if authentication is not None
                else {
                    "schema": "RUNTIME_TABLE_BINDING_V1",
                    "runtime_id": runtime["runtime_id"],
                    "public_key_hex": runtime["public_key_hex"],
                    "state_identity": runtime["state_identity"],
                    "state_reopened": False,
                }
            ),
        }
        connection.execute(
            "INSERT INTO fence_actions VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result["action_id"],
                runtime_handle,
                claimed,
                action,
                result["decision"],
                result["reason"],
                os.getpid(),
                canonical_bytes(result["authentication"]).decode("utf-8"),
            ),
        )
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def write_fsync_json(path: pathlib.Path, value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return hashlib.sha256(payload).hexdigest()


def backup_sqlite_live(source: pathlib.Path, destination: pathlib.Path) -> None:
    source_connection = sqlite_connect(source)
    destination_connection = sqlite_connect(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()


def initialize_runtime_state(
    path: pathlib.Path,
    *,
    runtime_id: str,
    epoch: int,
    phase: str,
) -> None:
    connection = sqlite_connect(path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE state(
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                runtime_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                phase TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO state VALUES(1, ?, ?, ?)",
            (runtime_id, epoch, phase),
        )
        connection.commit()
    finally:
        connection.close()


def setup_child(opaque_workdir: str, process_name: str) -> None:
    os.environ.clear()
    os.environ.update(SANITIZED_ENVIRONMENT)
    os.chdir(opaque_workdir)
    sys.argv[:] = [process_name]
    mp.current_process().name = process_name


def source_runtime_worker(
    *,
    durable_path: str,
    target_path: str,
    state_path: str,
    capsule_file: str,
    runtime_handle: str,
    source_private_key_hex: str,
    opaque_workdir: str,
) -> None:
    setup_child(opaque_workdir, "opaque-runtime-worker")
    durable = pathlib.Path(durable_path)
    config = load_config(durable)
    runtime = load_runtime(durable, runtime_handle)
    source_key = key_from_hex(source_private_key_hex)
    if public_key_hex(source_key) != runtime["public_key_hex"]:
        raise RuntimeError("source key mismatch")
    record_startup(
        durable,
        runtime_handle=runtime_handle,
        input_fields=[
            "capsule_store",
            "opaque_runtime_handle",
            "runtime_state_store",
            "target_store",
        ],
    )
    initialize_runtime_state(
        pathlib.Path(state_path),
        runtime_id=runtime["runtime_id"],
        epoch=int(runtime["epoch"]),
        phase="SOURCE_ACTIVE",
    )
    append_history(
        durable,
        event_type="RUNTIME_STARTED",
        actor_id=runtime["runtime_id"],
        epoch=int(runtime["epoch"]),
        payload={"runtime_handle": runtime_handle},
        key=source_key,
    )
    fence = attempt_fenced_action(
        durable,
        runtime_handle=runtime_handle,
        action="EXECUTE",
    )
    if fence["decision"] != "ACCEPTED":
        raise RuntimeError("source execution fenced")

    target = TargetOperationLedger(
        target_path,
        ledger_id=config["target_ledger_id"],
    )
    target.initialize_target(TARGET_ID, initial_target_state())
    configure_target(
        target,
        authentication_key_hex=config["target_authentication_key_hex"],
        genesis_commit_id=config["target_genesis_commit_id"],
    )
    capability_id = config["target_capability_id"]
    target.issue_capability(
        capability_id=capability_id,
        target_id=TARGET_ID,
        actor_id=PLATFORM_ID,
        allowed_state=exact_target_state(),
    )
    receipt = target.apply(
        target_id=TARGET_ID,
        actor_id=PLATFORM_ID,
        request_id=config["target_request_id"],
        capability_id=capability_id,
        expected_version=0,
        desired_state=exact_target_state(),
    )
    if receipt["decision"] != COMMITTED or not receipt["mutation_applied"]:
        raise RuntimeError("source target did not commit")
    readback = target.readback(receipt)
    if (
        not target.verify_receipt(receipt)
        or not target.verify_readback(readback, receipt)
        or not target_state_is_exact(readback["observed_state"])
    ):
        raise RuntimeError("source target evidence invalid")
    append_history(
        durable,
        event_type="TARGET_OCCURRENCE_COMMITTED",
        actor_id=runtime["runtime_id"],
        epoch=int(runtime["epoch"]),
        payload={
            "receipt_sha256": receipt["receipt_sha256"],
            "commit_id": receipt["commit_id"],
        },
        key=source_key,
    )
    readback_event = append_history(
        durable,
        event_type="TARGET_READBACK_OBSERVED",
        actor_id=runtime["runtime_id"],
        epoch=int(runtime["epoch"]),
        payload={
            "readback_sha256": readback["readback_sha256"],
            "observed_version": readback["observed_version"],
            "observed_commit_id": readback["observed_commit_id"],
        },
        key=source_key,
    )

    target_evidence = {
        "ledger_id": readback["ledger_id"],
        "receipt": receipt,
        "readback": readback,
    }
    capsule = sign_record(
        {
            "schema": "PORTABLE_RECOVERY_CAPSULE_V1",
            "capsule_id": config["capsule_id"],
            "store_id": config["store_id"],
            "operation_id": OPERATION_ID,
            "q_version": Q_VERSION,
            "task_sha256": sha256_value(exact_task()),
            "source_runtime_id": runtime["runtime_id"],
            "source_runtime_handle": runtime_handle,
            "source_epoch": int(runtime["epoch"]),
            "source_public_key_hex": runtime["public_key_hex"],
            "restart_schedule_sha256": config["restart_schedule_sha256"],
            "source_history_head_hash": readback_event["event_hash"],
            "source_history_length": readback_event["sequence"],
            "pending_obligations": [
                "O_Q_ACCEPTANCE",
                "O_V_ACCEPTANCE",
                "O_P_FINALITY",
            ],
            "owner_heads": config["owner_heads"],
            "target_evidence_status": "DURABLE_FULL",
            "target_evidence": target_evidence,
        },
        key=source_key,
        digest_field="capsule_hash",
    )
    capsule_file_hash = write_fsync_json(pathlib.Path(capsule_file), capsule)
    connection = sqlite_connect(durable)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO capsules VALUES(?, ?, ?, ?, ?, ?)",
            (
                capsule["capsule_id"],
                capsule["capsule_hash"],
                capsule["source_history_head_hash"],
                canonical_bytes(capsule).decode("utf-8"),
                capsule_file_hash,
                "FSYNCED_BEFORE_CRASH",
            ),
        )
        marker = {
            "schema": "SOURCE_DURABILITY_MARKER_V1",
            "capsule_hash": capsule["capsule_hash"],
            "capsule_file_sha256": capsule_file_hash,
            "source_history_head_hash": capsule["source_history_head_hash"],
            "source_process_id": os.getpid(),
            "source_epoch": int(runtime["epoch"]),
            "precrash_acceptance_count": 0,
            "precrash_finality_count": 0,
        }
        connection.execute(
            "INSERT INTO durable_markers VALUES('CAPSULE_DURABLE', ?)",
            (canonical_bytes(marker).decode("utf-8"),),
        )
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    while True:
        time.sleep(0.1)


def controller_generation_one_worker(
    *,
    durable_path: str,
    opaque_workdir: str,
) -> None:
    setup_child(opaque_workdir, "opaque-controller-worker")
    durable = pathlib.Path(durable_path)
    connection = sqlite_connect(durable)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "UPDATE fence_state SET current_epoch=2 WHERE singleton=1 "
            "AND current_epoch=1"
        )
        if connection.total_changes != 1:
            raise RuntimeError("epoch advance failed")
        connection.execute(
            "INSERT INTO controller_events(event_type, process_id, payload_json) "
            "VALUES('EPOCH_ADVANCED_BEFORE_CONTROLLER_CRASH', ?, ?)",
            (
                os.getpid(),
                canonical_bytes({"new_epoch": 2}).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    os._exit(73)


def old_runtime_restart_worker(
    *,
    durable_path: str,
    source_state_path: str,
    source_private_key_hex: str,
    restart_schedule: Mapping[str, Any],
    runtime_handle: str,
    opaque_workdir: str,
) -> None:
    setup_child(opaque_workdir, "opaque-runtime-worker")
    durable = pathlib.Path(durable_path)
    record_startup(
        durable,
        runtime_handle=runtime_handle,
        input_fields=[
            "capsule_store",
            "credential_store",
            "opaque_runtime_handle",
            "runtime_state_store",
        ],
    )
    runtime = load_runtime(durable, runtime_handle)
    source_key = key_from_hex(source_private_key_hex)
    state_connection = sqlite_connect(source_state_path)
    try:
        state = state_connection.execute("SELECT * FROM state").fetchone()
        if state is None:
            raise RuntimeError("source runtime state missing")
        state = dict(state)
    finally:
        state_connection.close()
    if (
        restart_schedule.get("schedule_sha256")
        != sha256_value(without(restart_schedule, "schedule_sha256"))
        or restart_schedule.get("trigger") != "AFTER_CONTROLLER_REOPEN"
        or restart_schedule.get("runtime_handle") != runtime_handle
        or restart_schedule.get("runtime_id") != runtime["runtime_id"]
        or restart_schedule.get("state_identity") != runtime["state_identity"]
        or state["runtime_id"] != runtime["runtime_id"]
        or int(state["epoch"]) != int(runtime["epoch"])
        or public_key_hex(source_key) != runtime["public_key_hex"]
    ):
        raise RuntimeError("old runtime durable identity reopen failed")
    authentication = sign_record(
        {
            "schema": "OLD_RUNTIME_REOPEN_AUTHENTICATION_V1",
            "runtime_id": runtime["runtime_id"],
            "runtime_handle": runtime_handle,
            "state_identity": runtime["state_identity"],
            "state_runtime_id": state["runtime_id"],
            "state_epoch": int(state["epoch"]),
            "state_reopened": True,
            "schedule_sha256": restart_schedule["schedule_sha256"],
            "challenge_hex": restart_schedule["challenge_hex"],
            "process_id": os.getpid(),
        },
        key=source_key,
        digest_field="authentication_hash",
    )
    attempt_fenced_action(
        durable,
        runtime_handle=runtime_handle,
        action="EXECUTE",
        authentication=authentication,
    )


def controller_generation_two_worker(
    *,
    durable_path: str,
    source_state_path: str,
    source_private_key_hex: str,
    restart_schedule_file: str,
    restart_schedule_sha256: str,
    source_runtime_handle: str,
    controller_workdir: str,
    restart_workdir: str,
) -> None:
    setup_child(controller_workdir, "opaque-controller-worker")
    durable = pathlib.Path(durable_path)
    append_controller_event(
        durable,
        event_type="CONTROLLER_REOPENED_FROM_DURABLE_SQLITE",
        payload={"fence_source": "SQLITE"},
    )
    restart_schedule = json.loads(
        pathlib.Path(restart_schedule_file).read_text(encoding="utf-8")
    )
    if (
        restart_schedule.get("schedule_sha256") != restart_schedule_sha256
        or sha256_value(without(restart_schedule, "schedule_sha256"))
        != restart_schedule_sha256
    ):
        raise RuntimeError("private restart schedule mismatch")
    context = mp.get_context("spawn")
    restart = context.Process(
        target=old_runtime_restart_worker,
        kwargs={
            "durable_path": durable_path,
            "source_state_path": source_state_path,
            "source_private_key_hex": source_private_key_hex,
            "restart_schedule": restart_schedule,
            "runtime_handle": source_runtime_handle,
            "opaque_workdir": restart_workdir,
        },
    )
    restart.start()
    restart.join(timeout=15)
    if restart.exitcode != 0:
        raise RuntimeError(f"old runtime restart exited {restart.exitcode}")
    append_controller_event(
        durable,
        event_type="OLD_RUNTIME_RESTART_OBSERVED",
        payload={"restart_process_id": restart.pid, "exitcode": restart.exitcode},
    )


def read_owner_head(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        row = connection.execute("SELECT * FROM owner_state").fetchone()
        if row is None:
            raise RuntimeError("owner head missing")
        value = dict(row)
        value["head"] = json.loads(value.pop("head_json"))
        return value
    finally:
        connection.close()


def load_capsule(durable: pathlib.Path, capsule_file: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(durable)
    try:
        row = connection.execute("SELECT * FROM capsules").fetchone()
        if row is None:
            raise RuntimeError("capsule missing")
        db_capsule = json.loads(row["capsule_json"])
        file_capsule = json.loads(capsule_file.read_text(encoding="utf-8"))
        if db_capsule != file_capsule:
            raise RuntimeError("capsule file/db mismatch")
        if file_sha256(capsule_file) != row["capsule_file_sha256"]:
            raise RuntimeError("capsule file digest mismatch")
        return db_capsule
    finally:
        connection.close()


def create_migration_input_view(
    *,
    source_capsule_file: pathlib.Path,
    migration_view_file: pathlib.Path,
    evidence_projection: str,
    projection_private_key_hex: str,
) -> dict[str, Any]:
    source_capsule = json.loads(
        source_capsule_file.read_text(encoding="utf-8")
    )
    visible_capsule = json.loads(canonical_bytes(source_capsule))
    if evidence_projection == "DURABLE_FULL":
        pass
    elif evidence_projection == "REMOVE_TARGET_LEDGER_READBACK":
        visible_capsule["target_evidence_status"] = "WITHHELD_AFTER_CUT"
        visible_capsule["target_evidence"] = None
    else:
        raise RuntimeError(f"unknown evidence projection: {evidence_projection}")
    view = sign_record(
        {
            "schema": "POST_CUT_MIGRATION_INPUT_VIEW_V1",
            "source_capsule_hash": source_capsule["capsule_hash"],
            "source_capsule_file_sha256": file_sha256(source_capsule_file),
            "visible_capsule": visible_capsule,
        },
        key=key_from_hex(projection_private_key_hex),
        digest_field="view_hash",
    )
    view_file_sha256 = write_fsync_json(migration_view_file, view)
    return {
        "view": view,
        "view_file_sha256": view_file_sha256,
    }


def load_migration_input_view(
    *,
    durable: pathlib.Path,
    migration_view_file: pathlib.Path,
    projection_public_key_hex: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    view = json.loads(migration_view_file.read_text(encoding="utf-8"))
    connection = sqlite_connect(durable)
    try:
        rows = [
            json.loads(row["payload_json"])
            for row in connection.execute(
                "SELECT payload_json FROM controller_events "
                "WHERE event_type='MIGRATION_INPUT_PROJECTED'"
            )
        ]
    finally:
        connection.close()
    if len(rows) != 1:
        raise RuntimeError("migration input projection event missing")
    event = rows[0]
    if (
        not verify_record(
            view,
            public_key=projection_public_key_hex,
            digest_field="view_hash",
        )
        or event.get("view_hash") != view.get("view_hash")
        or event.get("view_file_sha256") != file_sha256(migration_view_file)
        or event.get("source_capsule_hash") != view.get("source_capsule_hash")
    ):
        raise RuntimeError("migration input projection binding invalid")
    visible = view.get("visible_capsule")
    if not isinstance(visible, dict):
        raise RuntimeError("visible capsule missing")
    if (
        visible.get("target_evidence_status") == "DURABLE_FULL"
        and isinstance(visible.get("target_evidence"), Mapping)
    ):
        valid_projection = (
            visible.get("capsule_hash") == view.get("source_capsule_hash")
            and verify_record(
                visible,
                public_key=visible.get("source_public_key_hex", ""),
                digest_field="capsule_hash",
            )
        )
    elif (
        visible.get("target_evidence_status") == "WITHHELD_AFTER_CUT"
        and visible.get("target_evidence") is None
    ):
        valid_projection = (
            visible.get("capsule_hash") == view.get("source_capsule_hash")
            and visible.get("target_evidence_status") == "WITHHELD_AFTER_CUT"
            and visible.get("target_evidence") is None
        )
    else:
        valid_projection = False
    if not valid_projection:
        raise RuntimeError("migration input projection invalid")
    return view, visible


def verify_history_chain(durable: pathlib.Path) -> list[dict[str, Any]]:
    connection = sqlite_connect(durable)
    try:
        rows = list(connection.execute("SELECT * FROM history ORDER BY sequence"))
    finally:
        connection.close()
    events: list[dict[str, Any]] = []
    previous = GENESIS_HASH
    for expected_sequence, row in enumerate(rows, 1):
        event = json.loads(row["event_json"])
        if (
            int(row["sequence"]) != expected_sequence
            or event["sequence"] != expected_sequence
            or event["prev_hash"] != previous
            or row["prev_hash"] != previous
            or row["event_hash"] != event["event_hash"]
            or row["signer_public_key_hex"]
            != event["signer_public_key_hex"]
            or not verify_record(
                event,
                public_key=event["signer_public_key_hex"],
                digest_field="event_hash",
            )
        ):
            raise RuntimeError("history chain invalid")
        previous = event["event_hash"]
        events.append(event)
    return events


def migrated_runtime_worker(
    *,
    durable_path: str,
    target_path: str,
    state_path: str,
    migration_view_file: str,
    owner_paths: Mapping[str, str],
    runtime_handle: str,
    migrated_private_key_hex: str,
    opaque_workdir: str,
    result_queue: Any,
) -> None:
    setup_child(opaque_workdir, "opaque-runtime-worker")
    durable = pathlib.Path(durable_path)
    config = load_config(durable)
    runtime = load_runtime(durable, runtime_handle)
    migrated_key = key_from_hex(migrated_private_key_hex)
    if public_key_hex(migrated_key) != runtime["public_key_hex"]:
        raise RuntimeError("migrated key mismatch")
    record_startup(
        durable,
        runtime_handle=runtime_handle,
        input_fields=[
            "capsule_store",
            "migration_view_store",
            "opaque_runtime_handle",
            "owner_sources",
            "runtime_state_store",
            "target_store",
        ],
    )
    initialize_runtime_state(
        pathlib.Path(state_path),
        runtime_id=runtime["runtime_id"],
        epoch=int(runtime["epoch"]),
        phase="MIGRATION_IMPORT",
    )
    probe_connection = sqlite_connect(durable)
    try:
        full_capsule_rows = probe_connection.execute(
            "SELECT COUNT(*) FROM capsules"
        ).fetchone()[0]
        probe = {
            "schema": "MIGRATED_EVIDENCE_INTERFACE_PROBE_V1",
            "full_source_capsule_rows_visible": int(full_capsule_rows),
            "source_capsule_file_input_present": False,
            "controller_private_path_input_present": False,
        }
        probe_connection.execute(
            "INSERT INTO runtime_probes VALUES(?, ?, ?, ?)",
            (
                f"probe-{uuid.uuid4().hex}",
                runtime_handle,
                os.getpid(),
                canonical_bytes(probe).decode("utf-8"),
            ),
        )
        probe_connection.commit()
    finally:
        probe_connection.close()
    if full_capsule_rows != 0:
        raise RuntimeError("full source capsule leaked into migrated interface")
    migration_view, capsule = load_migration_input_view(
        durable=durable,
        migration_view_file=pathlib.Path(migration_view_file),
        projection_public_key_hex=config[
            "controller_projection_public_key_hex"
        ],
    )
    history = verify_history_chain(durable)
    source_public = config["source_public_key_hex"]
    capsule_valid = (
        verify_record(
            migration_view,
            public_key=config["controller_projection_public_key_hex"],
            digest_field="view_hash",
        )
        and capsule["source_public_key_hex"] == source_public
        and migration_view["source_capsule_hash"] == capsule["capsule_hash"]
        and capsule["store_id"] == config["store_id"]
        and capsule["operation_id"] == OPERATION_ID
        and capsule["task_sha256"] == sha256_value(exact_task())
        and len(history) == capsule["source_history_length"]
        and history[-1]["event_hash"] == capsule["source_history_head_hash"]
    )
    owner_heads_valid = all(
        read_owner_head(pathlib.Path(owner_paths[owner_id]))["head_hash"]
        == capsule["owner_heads"][owner_id]["head_hash"]
        for owner_id in ("O_Q", "O_V", "O_P")
    )
    target_valid = False
    if capsule.get("target_evidence_status") == "DURABLE_FULL":
        evidence = capsule.get("target_evidence")
        if isinstance(evidence, Mapping) and pathlib.Path(target_path).is_file():
            target = TargetOperationLedger(target_path)
            receipt = evidence["receipt"]
            readback = evidence["readback"]
            target_valid = (
                target.verify_receipt(receipt)
                and target.verify_readback(readback, receipt)
                and receipt["decision"] == COMMITTED
                and receipt["mutation_applied"] is True
                and readback["observed_version"] == 1
                and target_state_is_exact(readback["observed_state"])
                and len(history) >= 3
            )
    attempt_fenced_action(
        durable,
        runtime_handle=runtime_handle,
        action="IMPORT_CAPSULE",
    )
    if not (capsule_valid and owner_heads_valid and target_valid):
        event = append_history(
            durable,
            event_type="MIGRATION_BOUNDED_UNKNOWN",
            actor_id=runtime["runtime_id"],
            epoch=int(runtime["epoch"]),
            payload={
                "capsule_valid": capsule_valid,
                "owner_heads_valid": owner_heads_valid,
                "target_evidence_valid": target_valid,
                "disposition": "BOUNDED_UNKNOWN/UNRECONCILED_EFFECT",
            },
            key=migrated_key,
        )
        outcome = {
            "schema": "MIGRATION_OUTCOME_V1",
            "disposition": "BOUNDED_UNKNOWN/UNRECONCILED_EFFECT",
            "history_head_hash": event["event_hash"],
            "execute_count": 0,
            "postconditions_ready": False,
        }
    else:
        attempt_fenced_action(
            durable,
            runtime_handle=runtime_handle,
            action="VERIFY_TARGET",
        )
        imported = append_history(
            durable,
            event_type="MIGRATION_IMPORTED",
            actor_id=runtime["runtime_id"],
            epoch=int(runtime["epoch"]),
            payload={
                "capsule_hash": capsule["capsule_hash"],
                "source_head_hash": capsule["source_history_head_hash"],
            },
            key=migrated_key,
        )
        verified = append_history(
            durable,
            event_type="TARGET_READBACK_REVERIFIED",
            actor_id=runtime["runtime_id"],
            epoch=int(runtime["epoch"]),
            payload={
                "readback_sha256": capsule["target_evidence"]["readback"][
                    "readback_sha256"
                ],
                "no_execute": True,
            },
            key=migrated_key,
        )
        attempt_fenced_action(
            durable,
            runtime_handle=runtime_handle,
            action="POSTCONDITIONS_ONLY",
        )
        ready = append_history(
            durable,
            event_type="POSTCONDITIONS_READY",
            actor_id=runtime["runtime_id"],
            epoch=int(runtime["epoch"]),
            payload={
                "import_event_hash": imported["event_hash"],
                "target_verify_event_hash": verified["event_hash"],
                "execute_count": 0,
            },
            key=migrated_key,
        )
        outcome = {
            "schema": "MIGRATION_OUTCOME_V1",
            "disposition": "POSTCONDITIONS_READY",
            "history_head_hash": ready["event_hash"],
            "execute_count": 0,
            "postconditions_ready": True,
        }
    connection = sqlite_connect(durable)
    try:
        connection.execute(
            "INSERT INTO migration_outcomes VALUES(?, ?, ?)",
            (
                runtime_handle,
                outcome["disposition"],
                canonical_bytes(outcome).decode("utf-8"),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    result_queue.put(
        {
            "runtime_handle": runtime_handle,
            "disposition": outcome["disposition"],
        }
    )


def owner_acceptance_worker(
    *,
    durable_path: str,
    owner_path: str,
    owner_id: str,
    owner_private_key_hex: str,
    migration_view_file: str,
    opaque_workdir: str,
) -> None:
    setup_child(opaque_workdir, "opaque-owner-worker")
    durable = pathlib.Path(durable_path)
    owner_key = key_from_hex(owner_private_key_hex)
    owner_head = read_owner_head(pathlib.Path(owner_path))
    if public_key_hex(owner_key) != owner_head["public_key_hex"]:
        raise RuntimeError("owner key mismatch")
    outcome_connection = sqlite_connect(durable)
    try:
        outcome_row = outcome_connection.execute(
            "SELECT outcome_json FROM migration_outcomes"
        ).fetchone()
    finally:
        outcome_connection.close()
    if outcome_row is None:
        raise RuntimeError("migration outcome missing")
    outcome = json.loads(outcome_row["outcome_json"])
    if not outcome["postconditions_ready"]:
        raise RuntimeError("postconditions not ready")
    config = load_config(durable)
    view, capsule = load_migration_input_view(
        durable=durable,
        migration_view_file=pathlib.Path(migration_view_file),
        projection_public_key_hex=config[
            "controller_projection_public_key_hex"
        ],
    )
    if (
        not verify_record(
            capsule,
            public_key=config["source_public_key_hex"],
            digest_field="capsule_hash",
        )
    ):
        raise RuntimeError("owner source capsule unavailable")
    acceptance = sign_record(
        {
            "schema": "POST_MIGRATION_OWNER_ACCEPTANCE_V1",
            "owner_id": owner_id,
            "principal_id": owner_head["principal_id"],
            "operation_id": OPERATION_ID,
            "capsule_hash": capsule["capsule_hash"],
            "owner_head_hash": owner_head["head_hash"],
            "target_readback_sha256": capsule["target_evidence"]["readback"][
                "readback_sha256"
            ],
            "decision": "ACCEPTED_POST_MIGRATION",
            "process_id": os.getpid(),
        },
        key=owner_key,
        digest_field="acceptance_hash",
    )
    owner_connection = sqlite_connect(pathlib.Path(owner_path))
    try:
        owner_connection.execute(
            "INSERT INTO acceptances VALUES(?, ?)",
            (
                acceptance["acceptance_hash"],
                canonical_bytes(acceptance).decode("utf-8"),
            ),
        )
        append_owner_event(
            owner_connection,
            event_type="POST_MIGRATION_ACCEPTANCE",
            record_hash=acceptance["acceptance_hash"],
        )
        owner_connection.commit()
    finally:
        owner_connection.close()
    durable_connection = sqlite_connect(durable)
    try:
        durable_connection.execute(
            "INSERT INTO postconditions VALUES(?, ?, ?, ?, ?)",
            (
                f"{owner_id}_ACCEPTANCE",
                owner_id,
                acceptance["acceptance_hash"],
                canonical_bytes(acceptance).decode("utf-8"),
                os.getpid(),
            ),
        )
        durable_connection.commit()
    finally:
        durable_connection.close()
    append_history(
        durable,
        event_type=f"{owner_id}_POST_MIGRATION_ACCEPTANCE",
        actor_id=owner_id,
        epoch=2,
        payload={"acceptance_hash": acceptance["acceptance_hash"]},
        key=owner_key,
    )


def finality_worker(
    *,
    durable_path: str,
    owner_path: str,
    owner_private_key_hex: str,
    migration_view_file: str,
    opaque_workdir: str,
) -> None:
    setup_child(opaque_workdir, "opaque-owner-worker")
    durable = pathlib.Path(durable_path)
    owner_key = key_from_hex(owner_private_key_hex)
    owner_head = read_owner_head(pathlib.Path(owner_path))
    if public_key_hex(owner_key) != owner_head["public_key_hex"]:
        raise RuntimeError("finality owner key mismatch")
    connection = sqlite_connect(durable)
    try:
        rows = list(
            connection.execute(
                "SELECT * FROM postconditions WHERE kind IN "
                "('O_Q_ACCEPTANCE','O_V_ACCEPTANCE') ORDER BY kind"
            )
        )
    finally:
        connection.close()
    if len(rows) != 2:
        raise RuntimeError("both owner acceptances required")
    config = load_config(durable)
    view, capsule = load_migration_input_view(
        durable=durable,
        migration_view_file=pathlib.Path(migration_view_file),
        projection_public_key_hex=config[
            "controller_projection_public_key_hex"
        ],
    )
    if not isinstance(capsule.get("target_evidence"), Mapping):
        raise RuntimeError("finality source capsule unavailable")
    finality = sign_record(
        {
            "schema": "POST_MIGRATION_FINALITY_V1",
            "owner_id": "O_P",
            "principal_id": owner_head["principal_id"],
            "operation_id": OPERATION_ID,
            "capsule_hash": capsule["capsule_hash"],
            "acceptance_hashes": [row["record_hash"] for row in rows],
            "decision": "RECOVERED_AFTER_MIGRATION",
            "process_id": os.getpid(),
        },
        key=owner_key,
        digest_field="finality_hash",
    )
    owner_connection = sqlite_connect(pathlib.Path(owner_path))
    try:
        append_owner_event(
            owner_connection,
            event_type="POST_MIGRATION_FINALITY",
            record_hash=finality["finality_hash"],
        )
        owner_connection.commit()
    finally:
        owner_connection.close()
    connection = sqlite_connect(durable)
    try:
        connection.execute(
            "INSERT INTO postconditions VALUES('O_P_FINALITY','O_P',?,?,?)",
            (
                finality["finality_hash"],
                canonical_bytes(finality).decode("utf-8"),
                os.getpid(),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    append_history(
        durable,
        event_type="O_P_POST_MIGRATION_FINALITY",
        actor_id="O_P",
        epoch=2,
        payload={"finality_hash": finality["finality_hash"]},
        key=owner_key,
    )


def sqlite_logical_snapshot(path: pathlib.Path) -> dict[str, Any]:
    def encode(value: Any) -> Any:
        if isinstance(value, bytes):
            return {"sqlite_blob_hex": value.hex()}
        return value

    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
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
    finally:
        connection.close()


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
        raise RuntimeError(f"invalid SQLite header: {path}")
    return {
        "write_version": header[18],
        "read_version": header[19],
    }


def freeze_sqlite(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite_connect(path)
    try:
        busy, log_frames, checkpointed = connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        if busy:
            raise RuntimeError(f"SQLite busy during freeze: {path}")
        mode = connection.execute("PRAGMA journal_mode = DELETE").fetchone()[0]
        if str(mode).lower() != "delete":
            raise RuntimeError(f"SQLite did not freeze: {path}")
    finally:
        connection.close()
    shm = pathlib.Path(f"{path}-shm")
    if shm.exists():
        shm.unlink()
    remaining = [str(item) for item in sqlite_companions(path) if item.exists()]
    if remaining:
        raise RuntimeError(f"SQLite companion remains: {remaining}")
    logical = sqlite_logical_snapshot(path)
    header_versions = sqlite_header_versions(path)
    if header_versions != {"write_version": 1, "read_version": 1}:
        raise RuntimeError(f"SQLite header is not DELETE mode: {path}")
    return {
        "journal_mode": "delete",
        "checkpoint": "TRUNCATE",
        "log_frames": log_frames,
        "checkpointed_frames": checkpointed,
        "standalone": True,
        "companions_absent": True,
        "physical_sha256": file_sha256(path),
        "logical_sha256": sha256_value(logical),
        "header_versions": header_versions,
    }


def create_formal_sqlite_snapshot(
    source: pathlib.Path,
    destination: pathlib.Path,
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise RuntimeError(f"formal snapshot already exists: {destination}")
    source_logical = sqlite_logical_snapshot(source)
    source_connection = sqlite3.connect(
        f"file:{source}?mode=ro&immutable=1",
        uri=True,
    )
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.execute("PRAGMA journal_mode = DELETE")
        destination_connection.commit()
    finally:
        destination_connection.close()
        source_connection.close()
    remaining = [
        str(item) for item in sqlite_companions(destination) if item.exists()
    ]
    if remaining:
        raise RuntimeError(f"formal SQLite companion remains: {remaining}")
    formal_logical = sqlite_logical_snapshot(destination)
    header_versions = sqlite_header_versions(destination)
    integrity_connection = sqlite3.connect(
        f"file:{destination}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        integrity = integrity_connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        mode = integrity_connection.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        integrity_connection.close()
    source_logical_sha256 = sha256_value(source_logical)
    formal_logical_sha256 = sha256_value(formal_logical)
    if (
        integrity != "ok"
        or str(mode).lower() != "delete"
        or header_versions != {"write_version": 1, "read_version": 1}
    ):
        raise RuntimeError(f"formal SQLite invalid: {destination}")
    if source_logical_sha256 != formal_logical_sha256:
        raise RuntimeError(f"formal SQLite logical mismatch: {destination}")
    return {
        "source_runtime_physical_sha256": file_sha256(source),
        "source_runtime_logical_sha256": source_logical_sha256,
        "formal_physical_sha256": file_sha256(destination),
        "formal_logical_sha256": formal_logical_sha256,
        "logical_match": True,
        "integrity": "ok",
        "journal_mode": "delete",
        "standalone": True,
        "companions_absent": True,
        "header_versions": header_versions,
    }


def start_with_sanitized_environment(process: mp.Process) -> None:
    original = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(SANITIZED_ENVIRONMENT)
        process.start()
    finally:
        os.environ.clear()
        os.environ.update(original)


def opaque_workdir(store_id: str, slot: str) -> pathlib.Path:
    token = hashlib.sha256(f"{store_id}:{slot}".encode("utf-8")).hexdigest()[:20]
    path = pathlib.Path(tempfile.gettempdir()) / f"opaque-worker-{token}"
    path.mkdir(parents=False, exist_ok=False)
    return path


def wait_for_marker(path: pathlib.Path, timeout_seconds: float = 15) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        connection = sqlite_connect(path)
        try:
            row = connection.execute(
                "SELECT marker_json FROM durable_markers "
                "WHERE marker='CAPSULE_DURABLE'"
            ).fetchone()
        finally:
            connection.close()
        if row is not None:
            return json.loads(row["marker_json"])
        time.sleep(0.02)
    raise TimeoutError("source durable marker not observed")


def cleanup_workdir(path: pathlib.Path) -> None:
    path.rmdir()


def make_frozen_configuration() -> dict[str, Any]:
    source_key = Ed25519PrivateKey.generate()
    migrated_key = Ed25519PrivateKey.generate()
    projection_key = Ed25519PrivateKey.generate()
    restart_schedule = {
        "schema": "CONTROLLER_PRIVATE_RESTART_SCHEDULE_V1",
        "trigger": "AFTER_CONTROLLER_REOPEN",
        "runtime_handle": None,
        "runtime_id": None,
        "state_identity": "source-state.sqlite3",
        "challenge_hex": secrets.token_hex(32),
    }
    owner_keys = {
        owner_id: Ed25519PrivateKey.generate()
        for owner_id in ("O_Q", "O_V", "O_P")
    }
    owner_heads: dict[str, Any] = {}
    owner_private_keys: dict[str, str] = {}
    for owner_id, key in owner_keys.items():
        head = {
            "schema": "OWNER_HEAD_V1",
            "owner_id": owner_id,
            "principal_id": f"Principal:{owner_id}",
            "operation_id": OPERATION_ID,
            "authority_state": "CURRENT",
            "revision": 1,
        }
        owner_heads[owner_id] = {
            "head": head,
            "head_hash": sha256_value(head),
            "public_key_hex": public_key_hex(key),
            "principal_id": head["principal_id"],
        }
        owner_private_keys[owner_id] = private_key_hex(key)
    public = {
        "schema": "E6_MIGRATION_FROZEN_INPUT_V1",
        "task": exact_task(),
        "task_sha256": sha256_value(exact_task()),
        "operation_id": OPERATION_ID,
        "source_runtime_handle": f"runtime-{uuid.uuid4().hex}",
        "migrated_runtime_handle": f"runtime-{uuid.uuid4().hex}",
        "source_runtime_id": f"source-{uuid.uuid4().hex}",
        "migrated_runtime_id": f"migrated-{uuid.uuid4().hex}",
        "source_public_key_hex": public_key_hex(source_key),
        "migrated_public_key_hex": public_key_hex(migrated_key),
        "controller_projection_public_key_hex": public_key_hex(projection_key),
        "source_epoch": 1,
        "migrated_epoch": 2,
        "target_ledger_id": f"target-ledger-{uuid.uuid4().hex}",
        "target_authentication_key_sha256": hashlib.sha256(
            bytes.fromhex(target_key := secrets.token_hex(32))
        ).hexdigest(),
        "target_genesis_commit_id": f"genesis-{uuid.uuid4().hex}",
        "target_capability_id": f"target-cap-{uuid.uuid4().hex}",
        "target_request_id": f"target-request-{uuid.uuid4().hex}",
        "owner_heads": owner_heads,
    }
    restart_schedule["runtime_handle"] = public["source_runtime_handle"]
    restart_schedule["runtime_id"] = public["source_runtime_id"]
    restart_schedule["schedule_sha256"] = sha256_value(restart_schedule)
    public["restart_schedule_sha256"] = restart_schedule["schedule_sha256"]
    public["frozen_input_sha256"] = sha256_value(public)
    return {
        "public": public,
        "source_private_key_hex": private_key_hex(source_key),
        "migrated_private_key_hex": private_key_hex(migrated_key),
        "controller_projection_private_key_hex": private_key_hex(projection_key),
        "owner_private_keys": owner_private_keys,
        "target_authentication_key_hex": target_key,
        "restart_schedule": restart_schedule,
    }


def build_case_config(
    frozen: Mapping[str, Any],
    *,
    store_id: str,
) -> dict[str, Any]:
    public = frozen["public"]
    return {
        "schema": "MIGRATION_CASE_CONFIG_V1",
        "store_id": store_id,
        "capsule_id": f"capsule-{uuid.uuid4().hex}",
        "task": public["task"],
        "source_public_key_hex": public["source_public_key_hex"],
        "migrated_public_key_hex": public["migrated_public_key_hex"],
        "controller_projection_public_key_hex": public[
            "controller_projection_public_key_hex"
        ],
        "target_ledger_id": public["target_ledger_id"],
        "target_authentication_key_hex": frozen[
            "target_authentication_key_hex"
        ],
        "target_genesis_commit_id": public["target_genesis_commit_id"],
        "target_capability_id": public["target_capability_id"],
        "target_request_id": public["target_request_id"],
        "restart_schedule_sha256": public["restart_schedule_sha256"],
        "owner_heads": public["owner_heads"],
        "runtimes": [
            {
                "runtime_handle": public["source_runtime_handle"],
                "runtime_id": public["source_runtime_id"],
                "epoch": 1,
                "public_key_hex": public["source_public_key_hex"],
                "state_identity": "source-state.sqlite3",
            },
            {
                "runtime_handle": public["migrated_runtime_handle"],
                "runtime_id": public["migrated_runtime_id"],
                "epoch": 2,
                "public_key_hex": public["migrated_public_key_hex"],
                "state_identity": "migrated-state.sqlite3",
            },
        ],
    }


def run_case(
    *,
    run_dir: pathlib.Path,
    frozen: Mapping[str, Any],
    evidence_projection: str,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=False)
    store_id = f"store-{uuid.uuid4().hex}"
    config = build_case_config(
        frozen,
        store_id=store_id,
    )
    durable = run_dir / "durable.sqlite3"
    controller_private_dir = pathlib.Path(
        tempfile.mkdtemp(
            prefix=(
                "opaque-controller-private-"
                + hashlib.sha256(store_id.encode("utf-8")).hexdigest()[:12]
                + "-"
            )
        )
    )
    capsule_file = controller_private_dir / "source-recovery-capsule.json"
    source_cut_store = controller_private_dir / "source-cut.sqlite3"
    migration_view_file = run_dir / "migration-input-view.json"
    restart_schedule_file = (
        controller_private_dir / "controller-private-restart-schedule.json"
    )
    restart_schedule_file_sha256 = write_fsync_json(
        restart_schedule_file,
        frozen["restart_schedule"],
    )
    source_state = run_dir / "source-state.sqlite3"
    migrated_state = run_dir / "migrated-state.sqlite3"
    persistent_target = evidence_projection == "DURABLE_FULL"
    source_target_path = pathlib.Path(tempfile.gettempdir()) / (
        "opaque-target-"
        + hashlib.sha256(store_id.encode("utf-8")).hexdigest()[:20]
        + ".sqlite3"
    )
    retained_target_path = run_dir / "target-ledger.sqlite3"
    owner_dir = run_dir / "owners"
    owner_dir.mkdir()
    owner_paths: dict[str, pathlib.Path] = {}
    for owner_id in ("O_Q", "O_V", "O_P"):
        path = owner_dir / f"{owner_id.lower()}.sqlite3"
        owner_paths[owner_id] = path
        owner = dict(frozen["public"]["owner_heads"][owner_id])
        owner["owner_id"] = owner_id
        initialize_owner_store(path, owner=owner)
    initialize_durable_store(durable, config=config)

    context = mp.get_context("spawn")
    source_workdir = opaque_workdir(store_id, "runtime")
    source = context.Process(
        target=source_runtime_worker,
        kwargs={
            "durable_path": str(durable),
            "target_path": str(source_target_path),
            "state_path": str(source_state),
            "capsule_file": str(capsule_file),
            "runtime_handle": frozen["public"]["source_runtime_handle"],
            "source_private_key_hex": frozen["source_private_key_hex"],
            "opaque_workdir": str(source_workdir),
        },
    )
    start_with_sanitized_environment(source)
    marker = wait_for_marker(durable)
    owner_cut_snapshot = capture_owner_cut_snapshot(owner_paths)
    cut_connection = sqlite_connect(durable)
    try:
        cut_history_count = cut_connection.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]
        cut_postcondition_count = cut_connection.execute(
            "SELECT COUNT(*) FROM postconditions"
        ).fetchone()[0]
    finally:
        cut_connection.close()
    append_controller_event(
        durable,
        event_type="CUT_OWNER_NATIVE_SNAPSHOT_BOUND",
        payload={
            "capsule_hash": marker["capsule_hash"],
            "source_history_head_hash": marker["source_history_head_hash"],
            "history_count": int(cut_history_count),
            "postcondition_count": int(cut_postcondition_count),
            "owners": owner_cut_snapshot,
        },
    )
    source.terminate()
    source.join(timeout=15)
    if source.exitcode is None:
        raise RuntimeError("source did not terminate")
    cleanup_workdir(source_workdir)
    append_controller_event(
        durable,
        event_type="SOURCE_TERMINATED_AT_HIDDEN_CUT",
        payload={
            "source_process_id": source.pid,
            "source_exitcode": source.exitcode,
            "durable_marker_observed": marker,
            "source_result_queue_present": False,
        },
    )
    backup_sqlite_live(durable, source_cut_store)
    if persistent_target:
        backup_sqlite_live(source_target_path, retained_target_path)
        migration_target_path = retained_target_path
    else:
        migration_target_path = source_target_path
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = pathlib.Path(f"{source_target_path}{suffix}")
        if candidate.exists():
            candidate.unlink()
    migration_view_record = create_migration_input_view(
        source_capsule_file=capsule_file,
        migration_view_file=migration_view_file,
        evidence_projection=evidence_projection,
        projection_private_key_hex=frozen[
            "controller_projection_private_key_hex"
        ],
    )
    capsule_connection = sqlite_connect(durable)
    try:
        capsule_connection.execute("DELETE FROM capsules")
        capsule_connection.commit()
    finally:
        capsule_connection.close()
    append_controller_event(
        durable,
        event_type="MIGRATION_INPUT_PROJECTED",
        payload={
            "view_hash": migration_view_record["view"]["view_hash"],
            "view_file_sha256": migration_view_record["view_file_sha256"],
            "source_capsule_hash": marker["capsule_hash"],
        },
    )

    generation_one_workdir = opaque_workdir(store_id, "controller-1")
    generation_one = context.Process(
        target=controller_generation_one_worker,
        kwargs={
            "durable_path": str(durable),
            "opaque_workdir": str(generation_one_workdir),
        },
    )
    start_with_sanitized_environment(generation_one)
    generation_one.join(timeout=15)
    cleanup_workdir(generation_one_workdir)
    if generation_one.exitcode != 73:
        raise RuntimeError(
            f"generation-one controller did not crash as planned: "
            f"{generation_one.exitcode}"
        )
    append_controller_event(
        durable,
        event_type="CONTROLLER_GENERATION_ONE_EXIT_OBSERVED",
        payload={
            "controller_process_id": generation_one.pid,
            "exitcode": generation_one.exitcode,
        },
    )

    generation_two_workdir = opaque_workdir(store_id, "controller-2")
    restart_workdir = opaque_workdir(store_id, "old-runtime")
    generation_two = context.Process(
        target=controller_generation_two_worker,
        kwargs={
            "durable_path": str(durable),
            "source_state_path": str(source_state),
            "source_private_key_hex": frozen["source_private_key_hex"],
            "restart_schedule_file": str(restart_schedule_file),
            "restart_schedule_sha256": frozen["public"][
                "restart_schedule_sha256"
            ],
            "source_runtime_handle": frozen["public"][
                "source_runtime_handle"
            ],
            "controller_workdir": str(generation_two_workdir),
            "restart_workdir": str(restart_workdir),
        },
    )
    start_with_sanitized_environment(generation_two)
    generation_two.join(timeout=20)
    cleanup_workdir(generation_two_workdir)
    cleanup_workdir(restart_workdir)
    if generation_two.exitcode != 0:
        raise RuntimeError(f"reopened controller failed: {generation_two.exitcode}")

    migrated_workdir = opaque_workdir(store_id, "runtime")
    migrated_results = context.Queue()
    migrated = context.Process(
        target=migrated_runtime_worker,
        kwargs={
            "durable_path": str(durable),
            "target_path": str(migration_target_path),
            "state_path": str(migrated_state),
            "migration_view_file": str(migration_view_file),
            "owner_paths": {
                key: str(value) for key, value in owner_paths.items()
            },
            "runtime_handle": frozen["public"]["migrated_runtime_handle"],
            "migrated_private_key_hex": frozen["migrated_private_key_hex"],
            "opaque_workdir": str(migrated_workdir),
            "result_queue": migrated_results,
        },
    )
    start_with_sanitized_environment(migrated)
    migrated_result: dict[str, Any] | None = None
    result_deadline = time.monotonic() + 20
    while time.monotonic() < result_deadline:
        try:
            migrated_result = migrated_results.get(timeout=0.05)
            break
        except queue.Empty:
            if not migrated.is_alive():
                migrated.join(timeout=1)
                raise RuntimeError(
                    "migrated runtime exited before returning result: "
                    f"{migrated.exitcode}"
                )
    if migrated_result is None:
        migrated.terminate()
        migrated.join(timeout=5)
        raise RuntimeError("migrated runtime result timeout")
    migrated.join(timeout=15)
    cleanup_workdir(migrated_workdir)
    if migrated.exitcode != 0:
        raise RuntimeError(f"migrated runtime failed: {migrated.exitcode}")

    owner_process_ids: dict[str, int] = {}
    if migrated_result["disposition"] == "POSTCONDITIONS_READY":
        for owner_id in ("O_Q", "O_V"):
            workdir = opaque_workdir(store_id, owner_id)
            process = context.Process(
                target=owner_acceptance_worker,
                kwargs={
                    "durable_path": str(durable),
                    "owner_path": str(owner_paths[owner_id]),
                    "owner_id": owner_id,
                    "owner_private_key_hex": frozen["owner_private_keys"][
                        owner_id
                    ],
                    "migration_view_file": str(migration_view_file),
                    "opaque_workdir": str(workdir),
                },
            )
            start_with_sanitized_environment(process)
            process.join(timeout=15)
            cleanup_workdir(workdir)
            if process.exitcode != 0:
                raise RuntimeError(f"{owner_id} acceptance failed")
            owner_process_ids[owner_id] = int(process.pid)
        workdir = opaque_workdir(store_id, "O_P")
        finality = context.Process(
            target=finality_worker,
            kwargs={
                "durable_path": str(durable),
                "owner_path": str(owner_paths["O_P"]),
                "owner_private_key_hex": frozen["owner_private_keys"]["O_P"],
                "migration_view_file": str(migration_view_file),
                "opaque_workdir": str(workdir),
            },
        )
        start_with_sanitized_environment(finality)
        finality.join(timeout=15)
        cleanup_workdir(workdir)
        if finality.exitcode != 0:
            raise RuntimeError("O_P finality failed")
        owner_process_ids["O_P"] = int(finality.pid)

    artifact_private_dir = run_dir / "controller-private"
    artifact_private_dir.mkdir()
    relocated_private_files: dict[str, pathlib.Path] = {}
    for private_path in (
        capsule_file,
        source_cut_store,
        restart_schedule_file,
    ):
        destination = artifact_private_dir / private_path.name
        private_path.replace(destination)
        relocated_private_files[private_path.name] = destination
    controller_private_dir.rmdir()
    capsule_file = relocated_private_files[capsule_file.name]
    source_cut_store = relocated_private_files[source_cut_store.name]
    restart_schedule_file = relocated_private_files[restart_schedule_file.name]

    connection = sqlite_connect(durable)
    try:
        outcome_row = connection.execute(
            "SELECT outcome_json FROM migration_outcomes"
        ).fetchone()
        history_count = connection.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0]
        postcondition_count = connection.execute(
            "SELECT COUNT(*) FROM postconditions"
        ).fetchone()[0]
    finally:
        connection.close()
    outcome = json.loads(outcome_row["outcome_json"])

    runtime_databases: dict[str, pathlib.Path] = {
        "durable.sqlite3": durable,
        "controller-private/source-cut.sqlite3": source_cut_store,
        "source-state.sqlite3": source_state,
        "migrated-state.sqlite3": migrated_state,
    }
    for path in owner_paths.values():
        runtime_databases[f"owners/{path.name}"] = path
    if persistent_target:
        runtime_databases["target-ledger.sqlite3"] = retained_target_path
    runtime_freeze_receipts = {
        relative: freeze_sqlite(path)
        for relative, path in runtime_databases.items()
    }

    formal_database_paths: dict[str, Any] = {
        "durable": "formal/durable.sqlite3",
        "source_cut": "formal/source-cut.sqlite3",
        "source_state": "formal/source-state.sqlite3",
        "migrated_state": "formal/migrated-state.sqlite3",
        "owners": {
            owner_id: f"formal/owners/{path.name}"
            for owner_id, path in owner_paths.items()
        },
        "target": (
            "formal/target-ledger.sqlite3" if persistent_target else None
        ),
    }
    formal_sources: dict[str, pathlib.Path] = {
        formal_database_paths["durable"]: durable,
        formal_database_paths["source_cut"]: source_cut_store,
        formal_database_paths["source_state"]: source_state,
        formal_database_paths["migrated_state"]: migrated_state,
    }
    for owner_id, path in owner_paths.items():
        formal_sources[formal_database_paths["owners"][owner_id]] = path
    if persistent_target:
        formal_sources[formal_database_paths["target"]] = retained_target_path
    formal_databases = {
        relative: create_formal_sqlite_snapshot(
            source,
            run_dir / relative,
        )
        for relative, source in formal_sources.items()
    }

    artifact = {
        "schema": "E6_MIGRATION_RUN_ARTIFACT_V1",
        "store_id": store_id,
        "frozen_input": frozen["public"],
        "evidence_projection": evidence_projection,
        "source_process": {
            "pid": source.pid,
            "exitcode": source.exitcode,
            "result_queue_present": False,
        },
        "controller_processes": {
            "generation_one_pid": generation_one.pid,
            "generation_one_exitcode": generation_one.exitcode,
            "generation_two_pid": generation_two.pid,
            "generation_two_exitcode": generation_two.exitcode,
        },
        "migrated_process": {
            "pid": migrated.pid,
            "exitcode": migrated.exitcode,
        },
        "owner_process_ids": owner_process_ids,
        "migration_outcome": outcome,
        "history_count": history_count,
        "postcondition_count": postcondition_count,
        "capsule_file": str(capsule_file.relative_to(run_dir)),
        "capsule_file_sha256": file_sha256(capsule_file),
        "migration_view_file": migration_view_file.name,
        "migration_view_file_sha256": file_sha256(migration_view_file),
        "migration_view_hash": migration_view_record["view"]["view_hash"],
        "restart_schedule_file": str(
            restart_schedule_file.relative_to(run_dir)
        ),
        "restart_schedule_file_sha256": restart_schedule_file_sha256,
        "runtime_freeze_receipts": runtime_freeze_receipts,
        "database_artifacts": formal_databases,
        "formal_database_paths": formal_database_paths,
        "target_ledger_file": formal_database_paths["target"],
        "claim_boundary": (
            "LOCAL_SYNTHETIC_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE"
        ),
    }
    artifact["artifact_sha256"] = sha256_value(artifact)
    (run_dir / "artifact.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact
