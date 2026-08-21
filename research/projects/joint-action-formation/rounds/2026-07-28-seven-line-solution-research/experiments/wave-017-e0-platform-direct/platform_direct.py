"""Executable E0 platform-direct baseline for Wave 017.

The platform is a lawful unified synthetic authority over one venue-owned
resource and one target.  It uses a signed venue grant, deterministic
policy/IAM, an internal resource lock, and the mature Wave 015
TargetOperationLedger.  The arm is label-blind: it submits one exact task to
the platform and receives the platform-native result.
"""

from __future__ import annotations

import hashlib
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


PLATFORM_ID = "VenueV:NativeOperationsPlatform"
TARGET_ID = "VenueV:CircuitC7"
RESOURCE_ID = "VenueV:Battery:B7"
Q_VERSION = "Q@v1"
EXTERNAL_EVENT_TYPES = {
    "EXTERNAL_DISCOVERY_CALL": "discovery_calls",
    "EXTERNAL_RELATION_EVENT": "relation_events",
    "EXTERNAL_DELEGATION_EVENT": "delegation_events",
    "EXTERNAL_TRANSFER": "external_transfer_count",
}
SANITIZED_CHILD_ENVIRONMENT = {
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


def freeze_sqlite_snapshot(path: pathlib.Path) -> dict[str, Any]:
    """Checkpoint WAL bytes so the named database is a standalone artifact."""

    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    try:
        busy, log_frames, checkpointed_frames = connection.execute(
            "PRAGMA wal_checkpoint(TRUNCATE)"
        ).fetchone()
        if busy:
            raise RuntimeError(f"cannot freeze busy SQLite artifact: {path}")
        journal_mode = connection.execute(
            "PRAGMA journal_mode = DELETE"
        ).fetchone()[0]
        if str(journal_mode).lower() != "delete":
            raise RuntimeError(
                f"SQLite artifact did not leave WAL mode: {path}"
            )
    finally:
        connection.close()

    wal_path = pathlib.Path(f"{path}-wal")
    shm_path = pathlib.Path(f"{path}-shm")
    if wal_path.exists():
        raise RuntimeError(
            f"SQLite artifact still depends on WAL bytes: {wal_path.name}"
        )
    return {
        "schema": "FROZEN_SQLITE_SNAPSHOT_V1",
        "journal_mode": "delete",
        "checkpoint": "TRUNCATE",
        "wal_log_frames_before_truncate": log_frames,
        "wal_checkpointed_frames_before_truncate": checkpointed_frames,
        "residual_shm_present_but_not_required": shm_path.exists(),
        "standalone_file": True,
    }


def exact_task() -> dict[str, Any]:
    return {
        "schema": "CE001_EXACT_TASK_V1",
        "q_version": Q_VERSION,
        "target_id": TARGET_ID,
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
        "safety_required": True,
        "noise_required": True,
        "other_circuits_energized": [],
        "requester_acceptance_required": True,
        "venue_acceptance_required": True,
    }


def desired_target_state() -> dict[str, Any]:
    return {
        "target_id": TARGET_ID,
        "energized": True,
        "power_kw": 3.0,
        "duration_minutes": 45,
        "safety_ok": True,
        "noise_ok": True,
        "other_circuits_energized": [],
        "power_samples": [
            {
                "minute": minute,
                "power_kw": 3.0,
                "safety_ok": True,
                "noise_ok": True,
            }
            for minute in range(46)
        ],
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


def freeze_target_initial_conditions(
    path: pathlib.Path,
    *,
    authentication_key_hex: str,
    genesis_commit_id: str,
) -> None:
    """Replace TargetOperationLedger setup entropy before either arm runs."""

    if len(bytes.fromhex(authentication_key_hex)) != 32:
        raise ValueError("target authentication key must be 32 bytes")
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE metadata SET authentication_key_hex = ? WHERE singleton = 1",
            (authentication_key_hex,),
        )
        connection.execute(
            """
            UPDATE targets
            SET last_commit_id = ?
            WHERE target_id = ? AND version = 0
            """,
            (genesis_commit_id, TARGET_ID),
        )
        connection.commit()
    finally:
        connection.close()


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def private_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    ).hex()


def private_key_from_hex(value: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(value))


def make_frozen_pair_configuration() -> dict[str, Any]:
    """Create one semantic input shared by both counterfactual arms."""

    venue_key = Ed25519PrivateKey.generate()
    service_key = Ed25519PrivateKey.generate()
    target_authentication_key_hex = secrets.token_hex(32)
    pair_id = f"opaque-pair-{uuid.uuid4().hex}"
    semantic_input = {
        "schema": "E0_PLATFORM_DIRECT_FROZEN_INPUT_V1",
        "pair_id": pair_id,
        "operation_id": f"operation-{uuid.uuid4().hex}",
        "request_id": f"request-{uuid.uuid4().hex}",
        "task": exact_task(),
        "initial_target_state": initial_target_state(),
        "target_ledger_id": f"target-ledger-{uuid.uuid4().hex}",
        "target_genesis_commit_id": f"genesis-{uuid.uuid4().hex}",
        "target_authentication_key_sha256": hashlib.sha256(
            bytes.fromhex(target_authentication_key_hex)
        ).hexdigest(),
        "platform_id": PLATFORM_ID,
        "resource": {
            "resource_id": RESOURCE_ID,
            "owner_id": "VenueV",
            "max_power_kw": 3.0,
        },
        "venue_authority_public_key_hex": public_key_hex(venue_key),
        "platform_service_public_key_hex": public_key_hex(service_key),
        "available_native_interface": "PROVISION_EXACT_TASK",
    }
    semantic_input["frozen_input_sha256"] = sha256_value(semantic_input)
    return {
        "semantic_input": semantic_input,
        "venue_private_key_hex": private_key_hex(venue_key),
        "service_private_key_hex": private_key_hex(service_key),
        "target_authentication_key_hex": target_authentication_key_hex,
        "private_canary": f"private-canary-{uuid.uuid4().hex}",
    }


def sign_platform_record(
    record: Mapping[str, Any],
    *,
    private_key: Ed25519PrivateKey,
    digest_field: str,
) -> dict[str, Any]:
    signed = dict(record)
    signed[digest_field] = sha256_value(signed)
    signed["signature_hex"] = private_key.sign(
        canonical_bytes(signed)
    ).hex()
    return signed


def verify_platform_record(
    record: Mapping[str, Any],
    *,
    public_key: str,
    digest_field: str,
) -> bool:
    try:
        unsigned = {
            key: value for key, value in record.items() if key != "signature_hex"
        }
        content = {
            key: value for key, value in unsigned.items() if key != digest_field
        }
        if unsigned.get(digest_field) != sha256_value(content):
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key)).verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(unsigned),
        )
        return True
    except Exception:
        return False


def signed_authority_grant(
    *,
    private_key: Ed25519PrivateKey,
    operation_id: str,
    direct_authority_present: bool,
) -> dict[str, Any]:
    grant = {
        "schema": "VENUE_DIRECT_AUTHORITY_GRANT_V1",
        "issuer": "O_V",
        "principal_id": "VenueV",
        "grantee_id": PLATFORM_ID,
        "target_id": TARGET_ID,
        "resource_id": RESOURCE_ID,
        "q_version": Q_VERSION,
        "operation_id": operation_id,
        "decision": "ALLOW" if direct_authority_present else "DENY",
        "authority_mode": (
            "LAWFULLY_UNIFIED_DIRECT"
            if direct_authority_present
            else "DIRECT_AUTHORITY_REMOVED"
        ),
        "issued_at_minute": 0,
        "expires_at_minute": 90,
        "granted_actions": (
            [
                "SCHEDULE",
                "LOCK_INTERNAL_RESOURCE",
                "EXECUTE_TARGET",
                "ACCEPT_AS_REQUESTER_ROLE",
                "ACCEPT_AS_VENUE_ROLE",
                "FINALIZE_NO_EXTERNAL_TRANSFER",
            ]
            if direct_authority_present
            else []
        ),
    }
    grant["grant_sha256"] = sha256_value(grant)
    grant["signature_hex"] = private_key.sign(
        canonical_bytes(grant)
    ).hex()
    return grant


def verify_authority_envelope(
    grant: Mapping[str, Any],
    *,
    venue_public_key_hex: str,
) -> bool:
    try:
        unsigned = {
            key: value for key, value in grant.items() if key != "signature_hex"
        }
        content = {
            key: value for key, value in unsigned.items() if key != "grant_sha256"
        }
        if unsigned.get("grant_sha256") != sha256_value(content):
            return False
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(venue_public_key_hex)
        ).verify(
            bytes.fromhex(str(grant["signature_hex"])),
            canonical_bytes(unsigned),
        )
        return True
    except Exception:
        return False


def authority_status_from_signed_grant(
    grant: Mapping[str, Any],
    *,
    venue_public_key_hex: str,
    operation_id: str,
) -> str:
    if not verify_authority_envelope(
        grant,
        venue_public_key_hex=venue_public_key_hex,
    ):
        return "INVALID"
    shared = {
        "issuer": "O_V",
        "principal_id": "VenueV",
        "grantee_id": PLATFORM_ID,
        "target_id": TARGET_ID,
        "resource_id": RESOURCE_ID,
        "q_version": Q_VERSION,
        "operation_id": operation_id,
        "issued_at_minute": 0,
        "expires_at_minute": 90,
    }
    if any(grant.get(field) != expected for field, expected in shared.items()):
        return "INVALID"
    if (
        grant.get("decision") == "ALLOW"
        and grant.get("authority_mode") == "LAWFULLY_UNIFIED_DIRECT"
        and grant.get("granted_actions")
        == [
            "SCHEDULE",
            "LOCK_INTERNAL_RESOURCE",
            "EXECUTE_TARGET",
            "ACCEPT_AS_REQUESTER_ROLE",
            "ACCEPT_AS_VENUE_ROLE",
            "FINALIZE_NO_EXTERNAL_TRANSFER",
        ]
    ):
        return "PRESENT"
    if (
        grant.get("decision") == "DENY"
        and grant.get("authority_mode") == "DIRECT_AUTHORITY_REMOVED"
        and grant.get("granted_actions") == []
    ):
        return "REMOVED"
    return "INVALID"


def verify_authority_grant(
    grant: Mapping[str, Any],
    *,
    venue_public_key_hex: str,
    operation_id: str,
) -> tuple[bool, str]:
    if not verify_authority_envelope(
        grant,
        venue_public_key_hex=venue_public_key_hex,
    ):
        return False, "GRANT_SIGNATURE_INVALID"

    required = {
        "issuer": "O_V",
        "principal_id": "VenueV",
        "grantee_id": PLATFORM_ID,
        "target_id": TARGET_ID,
        "resource_id": RESOURCE_ID,
        "q_version": Q_VERSION,
        "operation_id": operation_id,
        "decision": "ALLOW",
        "authority_mode": "LAWFULLY_UNIFIED_DIRECT",
        "granted_actions": [
            "SCHEDULE",
            "LOCK_INTERNAL_RESOURCE",
            "EXECUTE_TARGET",
            "ACCEPT_AS_REQUESTER_ROLE",
            "ACCEPT_AS_VENUE_ROLE",
            "FINALIZE_NO_EXTERNAL_TRANSFER",
        ],
    }
    for field, expected in required.items():
        if grant.get(field) != expected:
            return False, f"POLICY_MISMATCH:{field}"
    if not (
        int(grant.get("issued_at_minute", -1))
        <= 0
        < int(grant.get("expires_at_minute", -1))
    ):
        return False, "GRANT_NOT_CURRENT"
    return True, "DIRECT_AUTHORITY_CURRENT"


def initialize_platform_store(path: pathlib.Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE resources(
                resource_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                platform_id TEXT NOT NULL,
                max_power_kw REAL NOT NULL,
                locked_by_operation_id TEXT
            )
            """
        )
        connection.execute(
            """
            INSERT INTO resources(
                resource_id, owner_id, platform_id, max_power_kw,
                locked_by_operation_id
            ) VALUES (?, 'VenueV', ?, 3.0, NULL)
            """,
            (RESOURCE_ID, PLATFORM_ID),
        )
        connection.execute(
            """
            CREATE TABLE events(
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                operation_id TEXT NOT NULL,
                request_id TEXT,
                payload_sha256 TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def append_platform_event(
    path: pathlib.Path,
    *,
    event_type: str,
    operation_id: str,
    request_id: str | None,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    event = {
        "event_type": event_type,
        "operation_id": operation_id,
        "request_id": request_id,
        "payload_sha256": sha256_value(payload),
    }
    connection = sqlite3.connect(path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO events(
                event_type, operation_id, request_id, payload_sha256
            ) VALUES (?, ?, ?, ?)
            """,
            (
                event["event_type"],
                event["operation_id"],
                event["request_id"],
                event["payload_sha256"],
            ),
        )
        connection.commit()
        event["sequence"] = cursor.lastrowid
        return event
    finally:
        connection.close()


def platform_event_snapshot(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT sequence, event_type, operation_id, request_id,
                       payload_sha256
                FROM events
                ORDER BY sequence
                """
            )
        ]
    finally:
        connection.close()
    counts = {counter: 0 for counter in EXTERNAL_EVENT_TYPES.values()}
    for row in rows:
        counter = EXTERNAL_EVENT_TYPES.get(row["event_type"])
        if counter is not None:
            counts[counter] += 1
    return {
        "schema": "PLATFORM_EVENT_LEDGER_SNAPSHOT_V1",
        "events": rows,
        "event_count": len(rows),
        "external_activity": counts,
        "external_event_type_registry": dict(EXTERNAL_EVENT_TYPES),
        "evidence_boundary": (
            "COUNTS_RECORDED_PLATFORM_SERVICE_EVENTS; "
            "NOT_OS_LEVEL_NETWORK_NONINTERFERENCE"
        ),
    }


def lock_internal_resource(
    path: pathlib.Path,
    *,
    operation_id: str,
) -> dict[str, Any]:
    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM resources WHERE resource_id = ?",
            (RESOURCE_ID,),
        ).fetchone()
        if row is None:
            raise RuntimeError("platform resource missing")
        if row["owner_id"] != "VenueV" or row["platform_id"] != PLATFORM_ID:
            raise RuntimeError("resource is not platform-native")
        if float(row["max_power_kw"]) < 3.0:
            raise RuntimeError("resource power insufficient")
        current_lock = row["locked_by_operation_id"]
        if current_lock not in {None, operation_id}:
            raise RuntimeError("resource already locked")
        connection.execute(
            "UPDATE resources SET locked_by_operation_id = ? "
            "WHERE resource_id = ?",
            (operation_id, RESOURCE_ID),
        )
        event_payload = {
            "resource_id": RESOURCE_ID,
            "operation_id": operation_id,
            "decision": "LOCKED",
        }
        connection.execute(
            """
            INSERT INTO events(
                event_type, operation_id, request_id, payload_sha256
            ) VALUES ('RESOURCE_LOCKED', ?, NULL, ?)
            """,
            (operation_id, sha256_value(event_payload)),
        )
        connection.commit()
        receipt = {
            "schema": "PLATFORM_INTERNAL_RESOURCE_LOCK_V1",
            "resource_id": RESOURCE_ID,
            "owner_id": "VenueV",
            "platform_id": PLATFORM_ID,
            "operation_id": operation_id,
            "decision": "LOCKED",
            "max_power_kw": 3.0,
        }
        receipt["receipt_sha256"] = sha256_value(receipt)
        return receipt
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def release_internal_resource(
    path: pathlib.Path,
    *,
    operation_id: str,
) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE resources SET locked_by_operation_id = NULL "
            "WHERE resource_id = ? AND locked_by_operation_id = ?",
            (RESOURCE_ID, operation_id),
        )
        connection.commit()
    finally:
        connection.close()


def platform_resource_snapshot(path: pathlib.Path) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute(
            "SELECT * FROM resources WHERE resource_id = ?",
            (RESOURCE_ID,),
        ).fetchone()
        if row is None:
            raise RuntimeError("platform resource missing")
        return dict(row)
    finally:
        connection.close()


def _task_is_exact(task: Mapping[str, Any]) -> bool:
    return task == exact_task()


def _state_satisfies_exact_task(state: Mapping[str, Any]) -> bool:
    samples = state.get("power_samples")
    return (
        state.get("target_id") == TARGET_ID
        and state.get("energized") is True
        and state.get("power_kw") == 3.0
        and state.get("duration_minutes") == 45
        and state.get("safety_ok") is True
        and state.get("noise_ok") is True
        and state.get("other_circuits_energized") == []
        and isinstance(samples, list)
        and len(samples) == 46
        and [item.get("minute") for item in samples] == list(range(46))
        and all(
            item.get("power_kw") == 3.0
            and item.get("safety_ok") is True
            and item.get("noise_ok") is True
            for item in samples
        )
    )


def platform_service_process(
    *,
    request_queue: Any,
    response_queue: Any,
    control_queue: Any,
    result_queue: Any,
    ready_queue: Any,
    platform_db_path: str,
    target_db_path: str,
    venue_public_key_hex: str,
    service_private_key_hex: str,
) -> None:
    service_key = private_key_from_hex(service_private_key_hex)
    ready_queue.put(
        {
            "process_id": os.getpid(),
            "start_method": mp.get_start_method(),
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
            "environment": dict(os.environ),
            "public_key_hex": public_key_hex(service_key),
        }
    )
    service_log: dict[str, Any] = {
        "schema": "PLATFORM_NATIVE_SERVICE_LOG_V1",
        "process_id": os.getpid(),
        "policy_checks": [],
        "requests": [],
        "resource_locks": [],
        "target_receipts": [],
        "target_readbacks": [],
        "acceptances": [],
        "finality": [],
    }
    target = TargetOperationLedger(target_db_path)
    platform_db = pathlib.Path(platform_db_path)
    while True:
        try:
            control = control_queue.get_nowait()
        except queue.Empty:
            control = None
        if control == "STOP":
            event_ledger = platform_event_snapshot(platform_db)
            service_log["event_ledger"] = event_ledger
            service_log["external_activity"] = event_ledger[
                "external_activity"
            ]
            result_queue.put(service_log)
            return
        try:
            request = request_queue.get(timeout=0.05)
        except queue.Empty:
            continue

        service_log["requests"].append(request)
        task = request.get("task")
        operation_id = request.get("operation_id")
        request_id = request.get("request_id")
        append_platform_event(
            platform_db,
            event_type="PLATFORM_NATIVE_REQUEST",
            operation_id=str(operation_id),
            request_id=str(request_id),
            payload=request,
        )
        grant = request.get("authority_grant")
        policy_ok = isinstance(grant, Mapping) and _task_is_exact(task)
        if not isinstance(grant, Mapping):
            policy_reason = "GRANT_MISSING"
        elif not _task_is_exact(task):
            policy_reason = "TASK_NOT_EXACT"
        else:
            policy_ok, policy_reason = verify_authority_grant(
                grant,
                venue_public_key_hex=venue_public_key_hex,
                operation_id=str(operation_id),
            )
        service_log["policy_checks"].append(
            policy_record := {
                "request_id": request.get("request_id"),
                "decision": "ALLOW" if policy_ok else "DENY",
                "reason": policy_reason,
                "grant_sha256": (
                    grant.get("grant_sha256")
                    if isinstance(grant, Mapping)
                    else None
                ),
            }
        )
        append_platform_event(
            platform_db,
            event_type=("POLICY_ALLOW" if policy_ok else "POLICY_DENY"),
            operation_id=str(operation_id),
            request_id=str(request_id),
            payload=policy_record,
        )
        if not policy_ok:
            denial = {
                "schema": "PLATFORM_NATIVE_RESPONSE_V1",
                "request_id": request.get("request_id"),
                "decision": "POLICY_DENIED",
                "reason": policy_reason,
                "effect_occurred": False,
                "finality": "NO_EXTERNAL_TRANSFER_DUE",
            }
            append_platform_event(
                platform_db,
                event_type="POLICY_DENIED_NO_EFFECT",
                operation_id=str(operation_id),
                request_id=str(request_id),
                payload=denial,
            )
            response_queue.put(denial)
            continue

        lock_receipt: dict[str, Any] | None = None
        try:
            lock_receipt = lock_internal_resource(
                platform_db,
                operation_id=str(operation_id),
            )
            service_log["resource_locks"].append(lock_receipt)
            capability_id = f"platform-cap-{uuid.uuid4().hex}"
            target.issue_capability(
                capability_id=capability_id,
                target_id=TARGET_ID,
                actor_id=PLATFORM_ID,
                allowed_state=desired_target_state(),
            )
            target_receipt = target.apply(
                target_id=TARGET_ID,
                actor_id=PLATFORM_ID,
                request_id=str(request["request_id"]),
                capability_id=capability_id,
                expected_version=0,
                desired_state=desired_target_state(),
            )
            service_log["target_receipts"].append(target_receipt)
            append_platform_event(
                platform_db,
                event_type="TARGET_COMMIT_RECORDED",
                operation_id=str(operation_id),
                request_id=str(request_id),
                payload=target_receipt,
            )
            if target_receipt["decision"] != COMMITTED:
                raise RuntimeError(
                    f"target did not commit: {target_receipt['decision']}"
                )
            readback = target.readback(target_receipt)
            service_log["target_readbacks"].append(readback)
            append_platform_event(
                platform_db,
                event_type="TARGET_READBACK_RECORDED",
                operation_id=str(operation_id),
                request_id=str(request_id),
                payload=readback,
            )
            if (
                not target.verify_readback(readback, target_receipt)
                or not _state_satisfies_exact_task(readback["observed_state"])
            ):
                raise RuntimeError("target readback did not close exact task")
            acceptances = []
            for role in ("REQUESTER_ROLE", "VENUE_ROLE"):
                acceptance = sign_platform_record(
                    {
                        "schema": "PLATFORM_NATIVE_ACCEPTANCE_V1",
                        "principal_id": "VenueV",
                        "role": role,
                        "q_version": Q_VERSION,
                        "target_id": TARGET_ID,
                        "operation_id": operation_id,
                        "decision": "ACCEPTED",
                        "target_commit_id": target_receipt["commit_id"],
                        "readback_sha256": readback["readback_sha256"],
                    },
                    private_key=service_key,
                    digest_field="acceptance_sha256",
                )
                acceptances.append(acceptance)
                append_platform_event(
                    platform_db,
                    event_type="ROLE_ACCEPTANCE",
                    operation_id=str(operation_id),
                    request_id=str(request_id),
                    payload=acceptance,
                )
            service_log["acceptances"].extend(acceptances)
            finality = sign_platform_record(
                {
                    "schema": "PLATFORM_NATIVE_FINALITY_V1",
                    "operation_id": operation_id,
                    "decision": "NO_EXTERNAL_TRANSFER_DUE",
                    "reason": "VENUE_OWNS_PLATFORM_RESOURCE_AND_TARGET",
                    "external_transfer_count": 0,
                    "target_commit_id": target_receipt["commit_id"],
                    "readback_sha256": readback["readback_sha256"],
                    "acceptance_sha256s": [
                        acceptance["acceptance_sha256"]
                        for acceptance in acceptances
                    ],
                },
                private_key=service_key,
                digest_field="finality_sha256",
            )
            service_log["finality"].append(finality)
            append_platform_event(
                platform_db,
                event_type="NO_EXTERNAL_TRANSFER_FINALITY",
                operation_id=str(operation_id),
                request_id=str(request_id),
                payload=finality,
            )
            response_queue.put(
                {
                    "schema": "PLATFORM_NATIVE_RESPONSE_V1",
                    "request_id": request["request_id"],
                    "decision": "PROVISIONED",
                    "reason": "PLATFORM_NATIVE_EXACT_TASK_CLOSED",
                    "effect_occurred": True,
                    "resource_lock_receipt_sha256": lock_receipt[
                        "receipt_sha256"
                    ],
                    "target_receipt": target_receipt,
                    "target_readback": readback,
                    "finality": finality,
                }
            )
        except Exception as error:
            if lock_receipt is not None:
                release_internal_resource(
                    platform_db,
                    operation_id=str(operation_id),
                )
            failure = {
                "schema": "PLATFORM_NATIVE_RESPONSE_V1",
                "request_id": request.get("request_id"),
                "decision": "PLATFORM_FAILED",
                "reason": type(error).__name__,
                "effect_occurred": False,
                "finality": "NO_EXTERNAL_TRANSFER_DUE",
            }
            append_platform_event(
                platform_db,
                event_type="PLATFORM_FAILED_NO_EFFECT",
                operation_id=str(operation_id),
                request_id=str(request_id),
                payload=failure,
            )
            response_queue.put(failure)


def blind_arm_process(
    *,
    start_payload: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
    result_queue: Any,
    opaque_workdir: str,
) -> None:
    os.chdir(opaque_workdir)
    sys.argv[:] = ["opaque-native-worker"]
    mp.current_process().name = "opaque-native-worker"
    observation = {
        "schema": "BLIND_ARM_VISIBILITY_V1",
        "process_id": os.getpid(),
        "process_name": mp.current_process().name,
        "start_method": mp.get_start_method(),
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "cwd_entries": sorted(os.listdir(".")),
        "environment": dict(os.environ),
        "visible_fields": sorted(start_payload),
        "start_payload_sha256": sha256_value(start_payload),
    }
    request = {
        "schema": "PLATFORM_NATIVE_REQUEST_V1",
        "request_id": start_payload["request_id"],
        "operation_id": start_payload["operation_id"],
        "task": start_payload["task"],
        "authority_grant": start_payload["authority_grant"],
    }
    request_queue.put(request)
    response = response_queue.get(timeout=15)
    result_queue.put(
        {
            "schema": "BLIND_NATIVE_ARM_TRANSCRIPT_V1",
            "arm_id": "A0-OPAQUE-NATIVE",
            "process_id": os.getpid(),
            "visibility": observation,
            "native_request": request,
            "native_response": response,
            "platform_native_call_count": 1,
        }
    )


def _scan_for_value(value: Any, needle: str) -> bool:
    return needle in canonical_bytes(value).decode("utf-8")


def _scan_for_token(value: Any, needle: str) -> bool:
    return needle.casefold() in canonical_bytes(value).decode("utf-8").casefold()


def evaluate_artifact(artifact: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute outcome coordinates without trusting arm self-report."""

    service = artifact["platform_native_service_log"]
    arm = artifact["arm_transcript"]
    response = arm["native_response"]
    frozen = artifact["frozen_input"]
    target = artifact["target_final_state"]
    resource = artifact["resource_final_state"]
    event_ledger = service["event_ledger"]
    external = event_ledger["external_activity"]

    external_zero = external == {
        "discovery_calls": 0,
        "relation_events": 0,
        "delegation_events": 0,
        "external_transfer_count": 0,
    }
    target_exact = _state_satisfies_exact_task(target["state"])
    grant = arm["native_request"]["authority_grant"]
    authority_status = authority_status_from_signed_grant(
        grant,
        venue_public_key_hex=frozen["venue_authority_public_key_hex"],
        operation_id=frozen["operation_id"],
    )
    direct_authority = authority_status == "PRESENT"
    authority_removed = authority_status == "REMOVED"
    frozen_input_valid = (
        frozen.get("frozen_input_sha256")
        == sha256_value(
            {
                key: value
                for key, value in frozen.items()
                if key != "frozen_input_sha256"
            }
        )
        and frozen.get("task") == exact_task()
        and artifact["operation_id"] == frozen.get("operation_id")
        and artifact["task"] == frozen.get("task")
    )
    provisioned = response.get("decision") == "PROVISIONED"
    policy_denied = response.get("decision") == "POLICY_DENIED"
    receipt = response.get("target_receipt")
    readback = response.get("target_readback")
    committed = (
        isinstance(receipt, Mapping)
        and receipt.get("decision") == COMMITTED
        and receipt.get("mutation_applied") is True
        and receipt.get("actor_id") == PLATFORM_ID
    )
    readback_attached = (
        isinstance(readback, Mapping)
        and isinstance(receipt, Mapping)
        and readback.get("receipt_sha256") == receipt.get("receipt_sha256")
        and readback.get("observed_commit_id") == receipt.get("commit_id")
        and readback.get("attached_to_receipt_commit") is True
    )
    finality = response.get("finality")
    acceptances = service.get("acceptances", [])
    service_public_key = artifact["platform_native_service_start"].get(
        "public_key_hex"
    )
    acceptance_roles = {
        acceptance.get("role")
        for acceptance in acceptances
        if isinstance(acceptance, Mapping)
        and verify_platform_record(
            acceptance,
            public_key=str(service_public_key),
            digest_field="acceptance_sha256",
        )
        and acceptance.get("decision") == "ACCEPTED"
        and acceptance.get("q_version") == Q_VERSION
        and acceptance.get("target_id") == TARGET_ID
        and isinstance(receipt, Mapping)
        and acceptance.get("target_commit_id") == receipt.get("commit_id")
        and isinstance(readback, Mapping)
        and acceptance.get("readback_sha256") == readback.get("readback_sha256")
    }
    acceptance_complete = acceptance_roles == {"REQUESTER_ROLE", "VENUE_ROLE"}
    no_transfer_finality = (
        isinstance(finality, Mapping)
        and verify_platform_record(
            finality,
            public_key=str(service_public_key),
            digest_field="finality_sha256",
        )
        and finality.get("decision") == "NO_EXTERNAL_TRANSFER_DUE"
        and finality.get("external_transfer_count") == 0
        and finality.get("acceptance_sha256s")
        == [
            acceptance["acceptance_sha256"]
            for acceptance in acceptances
        ]
    )
    no_unnecessary_formation = (
        external_zero
        and service.get("external_activity") == external
        and len(service["requests"]) == 1
        and arm["platform_native_call_count"] == 1
    )

    if direct_authority and frozen_input_valid:
        task_outcome = (
            provisioned
            and committed
            and readback_attached
            and target_exact
            and acceptance_complete
            and resource["locked_by_operation_id"]
            == artifact["operation_id"]
            and no_transfer_finality
        )
        correct_resolution = task_outcome and no_unnecessary_formation
        causal_attribution = task_outcome
        safe_handling = correct_resolution
    elif authority_removed and frozen_input_valid:
        task_outcome = False
        correct_resolution = (
            policy_denied
            and target["version"] == 0
            and target["state"]["energized"] is False
            and resource["locked_by_operation_id"] is None
            and not service["target_receipts"]
            and not service["target_readbacks"]
            and external_zero
        )
        causal_attribution = False
        safe_handling = correct_resolution
    else:
        task_outcome = False
        correct_resolution = False
        causal_attribution = False
        safe_handling = False

    return {
        "schema": "E0_PLATFORM_DIRECT_EVALUATION_V2",
        "TaskOutcomeSatisfied": task_outcome,
        "CorrectResolution": correct_resolution,
        "SafeHandling": safe_handling,
        "UnnecessaryFormation": not no_unnecessary_formation,
        "EffectAttributableToPlatform": causal_attribution,
        "EffectAttributionScope": "DIRECT_DIGITAL_TARGET_COMMIT_ONLY",
        "SignedAuthorityStatus": authority_status,
        "FrozenInputValid": frozen_input_valid,
        "ExternalDiscoveryCalls": external["discovery_calls"],
        "ExternalRelationEvents": external["relation_events"],
        "ExternalDelegationEvents": external["delegation_events"],
        "ExternalTransferCount": external["external_transfer_count"],
        "TargetVersion": target["version"],
        "ResourceLocked": resource["locked_by_operation_id"] is not None,
        "evidence_boundary": (
            "LOCAL_SYNTHETIC_LAWFUL_UNIFIED_DIGITAL_TARGET"
            if direct_authority
            else "LOCAL_SYNTHETIC_DIRECT_AUTHORITY_REMOVAL_COUNTEREXAMPLE"
        ),
    }


def run_platform_direct(
    *,
    direct_authority_present: bool,
    run_dir: pathlib.Path,
    frozen_configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=False)
    start_time = time.monotonic()
    configuration = dict(
        frozen_configuration or make_frozen_pair_configuration()
    )
    frozen = json.loads(
        json.dumps(configuration["semantic_input"], ensure_ascii=False)
    )
    if frozen.get("frozen_input_sha256") != sha256_value(
        {
            key: value
            for key, value in frozen.items()
            if key != "frozen_input_sha256"
        }
    ):
        raise ValueError("frozen semantic input digest invalid")
    venue_key = private_key_from_hex(str(configuration["venue_private_key_hex"]))
    service_key = private_key_from_hex(
        str(configuration["service_private_key_hex"])
    )
    if public_key_hex(venue_key) != frozen["venue_authority_public_key_hex"]:
        raise ValueError("venue private key does not match frozen public key")
    if public_key_hex(service_key) != frozen["platform_service_public_key_hex"]:
        raise ValueError("service private key does not match frozen public key")
    target_authentication_key_hex = str(
        configuration["target_authentication_key_hex"]
    )
    if (
        hashlib.sha256(bytes.fromhex(target_authentication_key_hex)).hexdigest()
        != frozen["target_authentication_key_sha256"]
    ):
        raise ValueError("target authentication key digest mismatch")
    arm_name = (
        "DIRECT_AUTHORITY_PRESENT"
        if direct_authority_present
        else "DIRECT_AUTHORITY_REMOVED"
    )
    # The blind arm receives the same opaque run identifier in both arms.
    # Counterfactual identity stays in the private artifact, not in its input.
    run_id = str(frozen["pair_id"])
    operation_id = str(frozen["operation_id"])
    request_id = str(frozen["request_id"])
    target_db = run_dir / "target-ledger.sqlite3"
    platform_db = run_dir / "platform-native.sqlite3"
    target = TargetOperationLedger(
        target_db,
        ledger_id=str(frozen["target_ledger_id"]),
    )
    target.initialize_target(TARGET_ID, frozen["initial_target_state"])
    freeze_target_initial_conditions(
        target_db,
        authentication_key_hex=target_authentication_key_hex,
        genesis_commit_id=str(frozen["target_genesis_commit_id"]),
    )
    initialize_platform_store(platform_db)

    grant = signed_authority_grant(
        private_key=venue_key,
        operation_id=operation_id,
        direct_authority_present=direct_authority_present,
    )
    private_canary = str(configuration["private_canary"])
    opaque_workdir = pathlib.Path(tempfile.gettempdir()) / (
        "opaque-worker-"
        + hashlib.sha256(str(frozen["pair_id"]).encode("utf-8")).hexdigest()[:16]
    )
    opaque_workdir.mkdir(parents=False, exist_ok=False)
    start_payload = {
        "schema": "OPAQUE_NATIVE_ARM_INPUT_V1",
        "run_id": run_id,
        "operation_id": operation_id,
        "request_id": request_id,
        "task": frozen["task"],
        "authority_grant": grant,
        "available_native_interface": frozen["available_native_interface"],
    }
    semantic_case_labels = (
        "e0_platform",
        "e0-platform",
        "e0 platform",
        "platform-direct",
        "platform_direct",
        "wave-017",
        "removal_counterexample",
        "expected_success",
        "expected_failure",
        "counterfactual_arm",
        "private_world_reveal",
        "expected_outcome",
        "result_label",
    )
    context = mp.get_context("spawn")
    request_queue = context.Queue()
    response_queue = context.Queue()
    control_queue = context.Queue()
    service_result_queue = context.Queue()
    service_ready_queue = context.Queue()
    arm_result_queue = context.Queue()
    service = context.Process(
        target=platform_service_process,
        kwargs={
            "request_queue": request_queue,
            "response_queue": response_queue,
            "control_queue": control_queue,
            "result_queue": service_result_queue,
            "ready_queue": service_ready_queue,
            "platform_db_path": str(platform_db),
            "target_db_path": str(target_db),
            "venue_public_key_hex": frozen["venue_authority_public_key_hex"],
            "service_private_key_hex": configuration[
                "service_private_key_hex"
            ],
        },
    )
    arm = context.Process(
        target=blind_arm_process,
        kwargs={
            "start_payload": start_payload,
            "request_queue": request_queue,
            "response_queue": response_queue,
            "result_queue": arm_result_queue,
            "opaque_workdir": str(opaque_workdir),
        },
    )
    controller_environment = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(SANITIZED_CHILD_ENVIRONMENT)
        service.start()
        service_ready = service_ready_queue.get(timeout=15)
        arm.start()
    finally:
        os.environ.clear()
        os.environ.update(controller_environment)
    arm_transcript = arm_result_queue.get(timeout=20)
    arm.join(timeout=10)
    opaque_workdir.rmdir()
    if arm.exitcode != 0:
        raise RuntimeError(f"blind arm exited {arm.exitcode}")
    control_queue.put("STOP")
    service_log = service_result_queue.get(timeout=15)
    service.join(timeout=10)
    if service.exitcode != 0:
        raise RuntimeError(f"platform service exited {service.exitcode}")

    final_target = target.current_state(TARGET_ID)
    final_resource = platform_resource_snapshot(platform_db)
    target_authenticity = {
        "receipt_valid": [],
        "readback_valid": [],
    }
    for receipt in service_log["target_receipts"]:
        target_authenticity["receipt_valid"].append(
            target.verify_receipt(receipt)
        )
    for receipt, readback in zip(
        service_log["target_receipts"],
        service_log["target_readbacks"],
    ):
        target_authenticity["readback_valid"].append(
            target.verify_readback(readback, receipt)
        )
    target_snapshot = freeze_sqlite_snapshot(target_db)
    platform_snapshot = freeze_sqlite_snapshot(platform_db)

    artifact: dict[str, Any] = {
        "schema": "E0_PLATFORM_DIRECT_RUN_ARTIFACT_V1",
        "run_id": run_id,
        "operation_id": operation_id,
        "frozen_input": frozen,
        "task": frozen["task"],
        "task_sha256": sha256_value(frozen["task"]),
        "arm_transcript": arm_transcript,
        "platform_native_service_start": service_ready,
        "platform_native_service_log": service_log,
        "target_final_state": final_target,
        "resource_final_state": final_resource,
        "target_authenticity": target_authenticity,
        "private_world_reveal": {
            "counterfactual_arm": arm_name,
            "private_canary_sha256": hashlib.sha256(
                private_canary.encode("utf-8")
            ).hexdigest(),
        },
        "blindness_receipt": {
            "controller_pid": os.getpid(),
            "spawn_start_method": arm_transcript["visibility"]["start_method"],
            "arm_pid": arm_transcript["process_id"],
            "service_pid": service_log["process_id"],
            "distinct_processes": (
                arm_transcript["process_id"] != service_log["process_id"]
            ),
            "private_canary_absent": (
                not _scan_for_value(start_payload, private_canary)
                and not _scan_for_value(arm_transcript, private_canary)
                and not _scan_for_value(service_ready, private_canary)
            ),
            "sanitized_child_environment": dict(
                SANITIZED_CHILD_ENVIRONMENT
            ),
            "child_environments_exact": (
                arm_transcript["visibility"]["environment"]
                == SANITIZED_CHILD_ENVIRONMENT
                and service_ready["environment"]
                == SANITIZED_CHILD_ENVIRONMENT
            ),
            "semantic_case_label_present": any(
                _scan_for_token(candidate, label)
                for candidate in (
                    start_payload,
                    arm_transcript,
                )
                for label in semantic_case_labels
            ),
            "private_fields_absent_from_payload": not any(
                field in start_payload
                for field in (
                    "private_world_reveal",
                    "expected_outcome",
                    "counterfactual_arm",
                    "private_canary",
                )
            ),
        },
        "cost": {
            "boundary": "LOCAL_SYNTHETIC_PLATFORM_DIRECT",
            "wall_seconds": round(time.monotonic() - start_time, 6),
            "child_process_count": 2,
            "platform_native_calls": 1,
            "policy_checks": len(service_log["policy_checks"]),
            "internal_resource_lock_ops": len(service_log["resource_locks"]),
            "target_mutation_attempts": len(service_log["target_receipts"]),
            "model_calls": 0,
            "human_minutes": 0,
            "external_discovery_calls": service_log["external_activity"][
                "discovery_calls"
            ],
            "external_relation_events": service_log["external_activity"][
                "relation_events"
            ],
            "external_delegation_events": service_log["external_activity"][
                "delegation_events"
            ],
            "external_transfer_count": service_log["external_activity"][
                "external_transfer_count"
            ],
            "cold_integration_cost": (
                "PLATFORM_POLICY_IAM_RESOURCE_LOCK_TARGET_LEDGER_ADAPTER"
            ),
            "repeat_cost": "ONE_PLATFORM_NATIVE_CALL_PLUS_TARGET_COMMIT",
            "maintenance_cost_not_measured": True,
        },
        "database_artifacts": {
            "target_ledger_file": target_db.name,
            "target_ledger_sha256": file_sha256(target_db),
            "target_ledger_snapshot": target_snapshot,
            "platform_native_file": platform_db.name,
            "platform_native_sha256": file_sha256(platform_db),
            "platform_native_snapshot": platform_snapshot,
        },
    }
    artifact["evaluation"] = evaluate_artifact(artifact)
    artifact["artifact_sha256"] = sha256_value(artifact)
    (run_dir / "artifact.json").write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return artifact
