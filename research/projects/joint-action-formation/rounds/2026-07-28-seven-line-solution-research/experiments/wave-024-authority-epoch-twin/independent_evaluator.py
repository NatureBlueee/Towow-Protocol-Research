"""Independent evaluator for the Wave 024 Authority-epoch twin.

The evaluator deliberately does not import ``twin_runtime.py`` and does not
accept ``TWIN-ARTIFACT.json`` or ``WORLD-ARTIFACT.json`` summaries as facts.
It reopens every native SQLite store read-only, verifies the Ed25519 chains,
recomputes file and self hashes, and derives the S/R/U outcomes from owner
rows.  Self hashes bind the currently supplied package; they are not claimed
to be an external append-only anchor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


GENESIS = "0" * 64
TARGET_ID = "VenueV:CircuitC7"
OBJECT_ID = "PowerOccurrence:VenueV:CircuitC7"
OPERATION = "ENERGIZE_EXACTLY_ONCE_45_MINUTES"
ACTOR_ID = "CANDIDATE-A4-MATURE-COMPOSITION"

SCOPED_CLAIMS = (
    "CL-024-TARGET-CONSUMED-AUTHORITY-FENCE",
    "CL-024-EXACTLY-ONCE-RECOVERY",
    "CL-024-NATIVE-POSTCONDITIONS",
    "CL-024-ISOMORPHIC-BLINDNESS",
)


class EvaluationError(RuntimeError):
    """The supplied evidence package cannot support its scoped claims."""


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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationError(message)


def load_json(path: pathlib.Path) -> Any:
    require(path.is_file(), f"missing JSON artifact: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"invalid JSON artifact: {path}") from exc


def verify_self_hash(record: Mapping[str, Any], field: str, label: str) -> None:
    require(
        record.get(field) == sha256_value(without(record, field)),
        f"{label} self-hash mismatch",
    )


def verify_record(
    record: Mapping[str, Any],
    *,
    public_key_hex: str,
    digest_field: str,
    label: str,
) -> None:
    try:
        unsigned = without(record, "signature_hex")
        require(
            unsigned.get(digest_field)
            == sha256_value(without(unsigned, digest_field)),
            f"{label} digest mismatch",
        )
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(str(record["signature_hex"])), canonical_bytes(unsigned)
        )
    except EvaluationError:
        raise
    except Exception as exc:
        raise EvaluationError(f"{label} Ed25519 signature invalid") from exc


def open_immutable(path: pathlib.Path) -> sqlite3.Connection:
    require(path.is_file(), f"missing SQLite store: {path}")
    companions = [
        pathlib.Path(f"{path}-wal"),
        pathlib.Path(f"{path}-shm"),
        pathlib.Path(f"{path}-journal"),
    ]
    require(
        not any(item.exists() for item in companions),
        f"SQLite store has an unbound companion: {path}",
    )
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    require(
        connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
        f"SQLite integrity failure: {path}",
    )
    require(
        str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        == "delete",
        f"SQLite store is not DELETE-journal standalone: {path}",
    )
    return connection


def _rows(connection: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    return [dict(row) for row in connection.execute(query)]


def _assert_schema(
    connection: sqlite3.Connection,
    expected: Mapping[str, tuple[str, ...]],
    label: str,
) -> None:
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    require(tables == set(expected), f"{label} table set mismatch")
    for table, columns in expected.items():
        actual = tuple(row[1] for row in connection.execute(f'PRAGMA table_info("{table}")'))
        require(actual == columns, f"{label}.{table} column set/order mismatch")


def _target_state_is_exact(state: Mapping[str, Any]) -> bool:
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
        and [item.get("observed_at_minute") for item in samples] == list(range(46))
        and all(
            item.get("target_id") == TARGET_ID
            and item.get("power_kw") == 3.0
            and item.get("safety_ok") is True
            and item.get("noise_ok") is True
            and item.get("other_circuits_energized") == []
            for item in samples
        )
    )


def _initial_target_state() -> dict[str, Any]:
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


def _read_target(path: pathlib.Path) -> dict[str, Any]:
    with open_immutable(path) as connection:
        _assert_schema(
            connection,
            {
                "metadata": ("singleton", "target_id", "target_certificate_json"),
                "target_state": (
                    "singleton",
                    "state_json",
                    "state_sha256",
                    "version",
                    "effect_count",
                    "last_effect_id",
                ),
                "authority_heads": (
                    "sequence",
                    "epoch",
                    "status",
                    "head_sha256",
                    "record_json",
                ),
                "native_events": (
                    "sequence",
                    "event_type",
                    "event_sha256",
                    "event_json",
                ),
                "requests": (
                    "request_id",
                    "request_sha256",
                    "decision",
                    "receipt_json",
                ),
                "effects": (
                    "effect_id",
                    "request_id",
                    "state_sha256",
                    "authority_head_sha256",
                ),
                "readbacks": ("readback_id", "request_id", "readback_json"),
            },
            "target-native",
        )
        metadata = dict(connection.execute("SELECT * FROM metadata").fetchone())
        state = dict(connection.execute("SELECT * FROM target_state").fetchone())
        heads = _rows(connection, "SELECT * FROM authority_heads ORDER BY sequence")
        events = _rows(connection, "SELECT * FROM native_events ORDER BY sequence")
        requests = _rows(connection, "SELECT * FROM requests ORDER BY request_id")
        effects = _rows(connection, "SELECT * FROM effects ORDER BY effect_id")
        readbacks = _rows(connection, "SELECT * FROM readbacks ORDER BY readback_id")
    for head in heads:
        head["record"] = json.loads(head.pop("record_json"))
    for event in events:
        event["event"] = json.loads(event.pop("event_json"))
    for request in requests:
        request["receipt"] = json.loads(request.pop("receipt_json"))
    for readback in readbacks:
        readback["readback"] = json.loads(readback.pop("readback_json"))
    return {
        "metadata": {
            **metadata,
            "target_certificate": json.loads(metadata["target_certificate_json"]),
        },
        "state": {**state, "state": json.loads(state["state_json"])},
        "heads": heads,
        "events": events,
        "requests": requests,
        "effects": effects,
        "readbacks": readbacks,
    }


def _runtime_target_audit(target: Mapping[str, Any]) -> dict[str, Any]:
    state = target["state"]
    return {
        "schema": "TARGET_NATIVE_AUDIT_V1",
        "state": state["state"],
        "state_sha256": state["state_sha256"],
        "version": state["version"],
        "effect_count": state["effect_count"],
        "last_effect_id": state["last_effect_id"],
        "request_count": len(target["requests"]),
        "refusal_count": sum(
            item["decision"] == "REJECTED_STALE_EPOCH"
            for item in target["requests"]
        ),
        "readback_count": len(target["readbacks"]),
        "authority_heads": [
            {
                "sequence": item["sequence"],
                "epoch": item["epoch"],
                "status": item["status"],
                "head_sha256": item["head_sha256"],
                "record": item["record"],
            }
            for item in target["heads"]
        ],
        "native_events": [
            {
                "sequence": item["sequence"],
                "event_type": item["event_type"],
                "event_sha256": item["event_sha256"],
                "event": item["event"],
            }
            for item in target["events"]
        ],
    }


def _read_source(path: pathlib.Path) -> dict[str, Any]:
    with open_immutable(path) as connection:
        _assert_schema(
            connection,
            {
                "operation": (
                    "singleton",
                    "payload_sha256",
                    "request_json",
                    "request_sha256",
                    "source_process_id",
                    "phase",
                    "ack_received_count",
                    "retry_execute_count",
                ),
                "runtime_startups": (
                    "phase",
                    "process_id",
                    "visible_surface_json",
                ),
            },
            "candidate-source-state",
        )
        operations = _rows(connection, "SELECT * FROM operation")
        startups = _rows(connection, "SELECT * FROM runtime_startups ORDER BY phase")
    require(len(operations) == 1, "source store must contain one operation")
    row = operations[0]
    return {
        **row,
        "request": json.loads(row["request_json"]),
        "runtime_startups": [
            {
                "phase": item["phase"],
                "process_id": item["process_id"],
                "visible_surface": json.loads(item["visible_surface_json"]),
            }
            for item in startups
        ],
    }


def _read_proxy(path: pathlib.Path) -> dict[str, Any]:
    with open_immutable(path) as connection:
        _assert_schema(
            connection,
            {
                "proxy_identity": ("singleton", "public_key_hex", "process_id"),
                "ack_events": (
                    "event_id",
                    "target_receipt_sha256",
                    "event_json",
                ),
            },
            "ack-drop-proxy",
        )
        identities = _rows(connection, "SELECT * FROM proxy_identity")
        events = _rows(connection, "SELECT * FROM ack_events ORDER BY rowid")
    require(len(identities) == 1, "proxy store must contain one identity")
    return {
        "identity": identities[0],
        "events": [json.loads(item["event_json"]) for item in events],
        "event_count": len(events),
    }


def _read_owner(path: pathlib.Path) -> dict[str, Any]:
    with open_immutable(path) as connection:
        _assert_schema(
            connection,
            {
                "owner_identity": (
                    "singleton",
                    "owner_id",
                    "principal_id",
                    "public_key_hex",
                    "pinned_q_sha256",
                    "pinned_lab_root_public_key_hex",
                    "pinned_acceptance_keys_json",
                ),
                "owner_events": (
                    "sequence",
                    "prev_event_sha256",
                    "event_sha256",
                    "event_type",
                    "record_json",
                ),
            },
            "owner-native",
        )
        identities = _rows(connection, "SELECT * FROM owner_identity")
        rows = _rows(connection, "SELECT * FROM owner_events ORDER BY sequence")
    require(len(identities) == 1, "owner store must contain one identity")
    return {
        "identity": identities[0],
        "events": [
            {
                "sequence": item["sequence"],
                "prev_event_sha256": item["prev_event_sha256"],
                "event_sha256": item["event_sha256"],
                "event_type": item["event_type"],
                "record": json.loads(item["record_json"]),
            }
            for item in rows
        ],
        "event_count": len(rows),
    }


def _verify_file_hash(path: pathlib.Path, expected: str, label: str) -> None:
    require(file_sha256(path) == expected, f"{label} physical file hash mismatch")


def _verify_authority_root(
    run_dir: pathlib.Path, twin: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    authority_key = str(twin["authority_public_key_hex"])
    authority_path = run_dir / str(twin["authority_store"]["path"])
    registry_path = run_dir / str(twin["lab_registry_store"]["path"])
    _verify_file_hash(authority_path, twin["authority_store"]["sha256"], "Authority DB")
    _verify_file_hash(registry_path, twin["lab_registry_store"]["sha256"], "registry DB")

    with open_immutable(authority_path) as connection:
        _assert_schema(
            connection,
            {
                "authority_identity": (
                    "singleton",
                    "principal_id",
                    "public_key_hex",
                    "process_id",
                ),
                "authority_records": (
                    "sequence",
                    "head_sha256",
                    "prev_head_sha256",
                    "record_json",
                ),
            },
            "authority-native",
        )
        identities = _rows(connection, "SELECT * FROM authority_identity")
        records = _rows(connection, "SELECT * FROM authority_records ORDER BY sequence")
    require(len(identities) == 1, "Authority identity cardinality mismatch")
    require(identities[0]["principal_id"] == "Principal:VenueV", "Authority principal mismatch")
    require(identities[0]["public_key_hex"] == authority_key, "Authority key mismatch")
    require(
        identities[0]["process_id"] == twin["authority_process"]["process_id"],
        "Authority process identity mismatch",
    )
    require(len(records) == 2, "Authority log must contain delegation and revoke")
    parsed = [json.loads(item["record_json"]) for item in records]
    delegation, revocation = parsed
    for index, (row, record) in enumerate(zip(records, parsed), 1):
        verify_record(
            record,
            public_key_hex=authority_key,
            digest_field="authority_head_sha256",
            label=f"Authority record {index}",
        )
        require(row["sequence"] == index, "Authority sequence is not contiguous")
        require(row["head_sha256"] == record["authority_head_sha256"], "Authority row head mismatch")
        require(row["prev_head_sha256"] == record["prev_authority_head_sha256"], "Authority row predecessor mismatch")
    require(delegation["schema"] == "AUTHORITY_DELEGATION_V1", "delegation schema mismatch")
    require(delegation["status"] == "CURRENT" and delegation["epoch"] == 1, "delegation head mismatch")
    require(delegation["prev_authority_head_sha256"] == GENESIS, "delegation genesis mismatch")
    require(revocation["schema"] == "AUTHORITY_HEAD_V1", "revocation schema mismatch")
    require(revocation["status"] == "REVOKED" and revocation["epoch"] == 2, "revocation head mismatch")
    require(
        revocation["prev_authority_head_sha256"] == delegation["authority_head_sha256"],
        "revocation predecessor mismatch",
    )
    for field in (
        "delegation_id",
        "principal_id",
        "actor_id",
        "q_sha256",
        "object_id",
        "target_id",
        "operation",
    ):
        require(revocation[field] == delegation[field], f"revocation scope mismatch: {field}")
    require(load_json(run_dir / "AUTHORITY-DELEGATION.json") == delegation, "delegation file/DB mismatch")
    require(load_json(run_dir / "AUTHORITY-REVOCATION.json") == revocation, "revocation file/DB mismatch")
    require(twin["initial_authority"] == delegation, "TWIN delegation/DB mismatch")
    require(twin["revocation"] == revocation, "TWIN revocation/DB mismatch")
    return delegation, revocation


def _verify_registry(
    run_dir: pathlib.Path,
    twin: Mapping[str, Any],
    certificates: list[Mapping[str, Any]],
) -> None:
    root_key = str(twin["lab_root_public_key_hex"])
    path = run_dir / str(twin["lab_registry_store"]["path"])
    with open_immutable(path) as connection:
        _assert_schema(
            connection,
            {
                "registry_identity": ("singleton", "public_key_hex", "process_id"),
                "certificates": ("certificate_sha256", "certificate_json"),
            },
            "lab-key-registry",
        )
        identities = _rows(connection, "SELECT * FROM registry_identity")
        rows = _rows(connection, "SELECT * FROM certificates ORDER BY certificate_sha256")
    require(len(identities) == 1, "registry identity cardinality mismatch")
    require(identities[0]["public_key_hex"] == root_key, "registry root key mismatch")
    require(
        identities[0]["process_id"] == twin["lab_registry_process"]["process_id"],
        "registry process identity mismatch",
    )
    parsed = [json.loads(item["certificate_json"]) for item in rows]
    require(len(parsed) == 3, "registry must contain exactly three Target certificates")
    require(
        {canonical_bytes(item) for item in parsed}
        == {canonical_bytes(item) for item in certificates},
        "registry certificates do not match world Target certificates",
    )
    for row, certificate in zip(rows, parsed):
        verify_record(
            certificate,
            public_key_hex=root_key,
            digest_field="certificate_sha256",
            label="Target certificate",
        )
        require(row["certificate_sha256"] == certificate["certificate_sha256"], "registry certificate row hash mismatch")


def _verify_native_event_chain(events: list[Mapping[str, Any]], label: str) -> None:
    require(
        [item["sequence"] for item in events] == list(range(1, len(events) + 1)),
        f"{label} native event sequence is not contiguous",
    )
    for item in events:
        require(item["event_type"] == item["event"]["event_type"], f"{label} event type mismatch")
        require(item["event_sha256"] == sha256_value(item["event"]), f"{label} event hash mismatch")


def _verify_owner_chain(owner: Mapping[str, Any], owner_id: str) -> None:
    identity = owner["identity"]
    require(identity["owner_id"] == owner_id, f"{owner_id} identity mismatch")
    require(identity["principal_id"] == f"Principal:{owner_id}", f"{owner_id} principal mismatch")
    predecessor = GENESIS
    for index, event in enumerate(owner["events"], 1):
        record = event["record"]
        require(event["sequence"] == index, f"{owner_id} sequence mismatch")
        require(event["prev_event_sha256"] == predecessor, f"{owner_id} predecessor mismatch")
        body = {
            "sequence": index,
            "prev_event_sha256": predecessor,
            "event_type": event["event_type"],
            "record_sha256": record["owner_receipt_sha256"],
        }
        require(event["event_sha256"] == sha256_value(body), f"{owner_id} event hash mismatch")
        verify_record(
            record,
            public_key_hex=identity["public_key_hex"],
            digest_field="owner_receipt_sha256",
            label=f"{owner_id} owner receipt",
        )
        predecessor = event["event_sha256"]


def _verify_world(
    run_dir: pathlib.Path,
    role: str,
    relative_path: str,
    twin: Mapping[str, Any],
    frozen_payload: Mapping[str, Any],
    delegation: Mapping[str, Any],
    revocation: Mapping[str, Any],
) -> dict[str, Any]:
    world_path = run_dir / relative_path
    world_dir = world_path.parent
    world = load_json(world_path)
    verify_self_hash(world, "world_artifact_sha256", f"world {role}")
    require(world.get("schema") == "AUTHORITY_EPOCH_WORLD_ARTIFACT_V1", f"world {role} schema mismatch")
    require(world.get("role") == role, f"world {role} role mismatch")
    require(world["candidate_payload"] == frozen_payload, f"world {role} candidate payload differs")
    require(world["candidate_payload_sha256"] == sha256_value(frozen_payload), f"world {role} payload digest mismatch")
    request = frozen_payload["request"]
    request_sha = sha256_value(request)
    require(world["request_sha256"] == request_sha, f"world {role} request digest mismatch")
    require(world["key_registry"]["authority_public_key_hex"] == twin["authority_public_key_hex"], f"world {role} Authority key mismatch")
    require(world["key_registry"]["lab_root_public_key_hex"] == twin["lab_root_public_key_hex"], f"world {role} lab root mismatch")

    candidate_file = load_json(world_dir / "candidate-initial-payload.json")
    require(candidate_file == frozen_payload, f"world {role} candidate input file differs")

    file_meta = world["files"]
    target_path = world_dir / file_meta["target_db"]
    proxy_path = world_dir / file_meta["proxy_db"]
    source_path = world_dir / file_meta["source_state_db"]
    _verify_file_hash(target_path, file_meta["target_db_sha256"], f"world {role} Target DB")
    _verify_file_hash(proxy_path, file_meta["proxy_db_sha256"], f"world {role} proxy DB")
    _verify_file_hash(source_path, file_meta["source_state_db_sha256"], f"world {role} source DB")
    for owner_id in ("O_Q", "O_V", "O_P"):
        _verify_file_hash(
            world_dir / file_meta["owner_dbs"][owner_id],
            file_meta["owner_db_sha256"][owner_id],
            f"world {role} {owner_id} DB",
        )

    target = _read_target(target_path)
    source = _read_source(source_path)
    proxy = _read_proxy(proxy_path)
    owners = {
        owner_id: _read_owner(world_dir / file_meta["owner_dbs"][owner_id])
        for owner_id in ("O_Q", "O_V", "O_P")
    }
    require(world["target_audit"] == _runtime_target_audit(target), f"world {role} Target summary/DB mismatch")
    require(world["source_state_audit"] == source, f"world {role} source summary/DB mismatch")
    require(world["proxy_store_audit"] == proxy, f"world {role} proxy summary/DB mismatch")
    require(world["owner_store_audits"] == owners, f"world {role} owner summaries/DB mismatch")

    certificate = target["metadata"]["target_certificate"]
    require(target["metadata"]["target_id"] == TARGET_ID, f"world {role} Target metadata mismatch")
    require(certificate == world["target_certificate"], f"world {role} certificate DB/JSON mismatch")
    verify_record(
        certificate,
        public_key_hex=twin["lab_root_public_key_hex"],
        digest_field="certificate_sha256",
        label=f"world {role} Target certificate",
    )
    require(certificate["target_id"] == TARGET_ID, f"world {role} certificate Target mismatch")
    require(certificate["q_sha256"] == frozen_payload["q_sha256"], f"world {role} certificate Q mismatch")
    require(certificate["target_public_key_hex"] == world["key_registry"]["target_public_key_hex"], f"world {role} Target key mismatch")
    target_key = certificate["target_public_key_hex"]

    _verify_native_event_chain(target["events"], f"world {role}")
    expected_event_types = {
        "S": ["AUTHORITY_FENCE_BOOTSTRAPPED", "REQUEST_INGRESS", "EFFECT_COMMITTED"],
        "R": ["AUTHORITY_FENCE_BOOTSTRAPPED", "FENCE_ADVANCED", "REQUEST_INGRESS", "AUTHORITY_REJECTED"],
        "U": ["AUTHORITY_FENCE_BOOTSTRAPPED", "REQUEST_INGRESS", "EFFECT_COMMITTED"],
    }[role]
    require([item["event_type"] for item in target["events"]] == expected_event_types, f"world {role} native event shape mismatch")
    expected_heads = [delegation] if role in {"S", "U"} else [delegation, revocation]
    require([item["record"] for item in target["heads"]] == expected_heads, f"world {role} Target Authority heads mismatch")
    for index, head in enumerate(target["heads"], 1):
        require(head["sequence"] == index, f"world {role} Target head sequence mismatch")
        require(head["epoch"] == head["record"]["epoch"], f"world {role} Target head epoch mismatch")
        require(head["status"] == head["record"]["status"], f"world {role} Target head status mismatch")
        require(head["head_sha256"] == head["record"]["authority_head_sha256"], f"world {role} Target head hash mismatch")
        verify_record(
            head["record"],
            public_key_hex=twin["authority_public_key_hex"],
            digest_field="authority_head_sha256",
            label=f"world {role} Target-consumed Authority head {index}",
        )

    require(len(target["requests"]) == 1, f"world {role} must have one exact request")
    native_request = target["requests"][0]
    receipt = native_request["receipt"]
    require(receipt == world["target_execute_receipt"], f"world {role} execute receipt DB/JSON mismatch")
    require(receipt.get("target_certificate") == certificate, f"world {role} execute receipt certificate mismatch")
    verify_record(
        receipt,
        public_key_hex=target_key,
        digest_field="target_receipt_sha256",
        label=f"world {role} Target execute receipt",
    )
    require(native_request["request_id"] == request["request_id"] == receipt["request_id"], f"world {role} request id mismatch")
    require(native_request["request_sha256"] == request_sha == receipt["request_sha256"], f"world {role} request hash mismatch")
    require(receipt["q_sha256"] == frozen_payload["q_sha256"], f"world {role} receipt Q mismatch")
    for field, expected in (("object_id", OBJECT_ID), ("target_id", TARGET_ID), ("operation", OPERATION), ("actor_id", ACTOR_ID)):
        require(request[field] == expected and receipt[field] == expected, f"world {role} exact scope mismatch: {field}")
    require(receipt["presented_delegation_sha256"] == delegation["authority_head_sha256"], f"world {role} presented delegation mismatch")
    require(receipt["ingress_event_sequence"] == target["events"][-2]["sequence"], f"world {role} ingress sequence mismatch")
    require(receipt["decision_event_sequence"] == target["events"][-1]["sequence"], f"world {role} decision sequence mismatch")

    require(len(target["readbacks"]) == 1, f"world {role} must have one exact readback")
    readback = target["readbacks"][0]["readback"]
    require(readback.get("target_certificate") == certificate, f"world {role} readback certificate mismatch")
    verify_record(
        readback,
        public_key_hex=target_key,
        digest_field="target_receipt_sha256",
        label=f"world {role} Target readback",
    )
    recovery = world["candidate_recovery_result"]
    require(recovery["target_status"]["receipt"] == receipt, f"world {role} recovery receipt differs")
    require(recovery["target_status"]["readback"] == readback, f"world {role} recovery readback differs")
    require(readback["receipt_sha256"] == receipt["target_receipt_sha256"], f"world {role} readback detached from receipt")
    require(readback["request_id"] == request["request_id"] and readback["request_sha256"] == request_sha, f"world {role} readback request mismatch")
    require(readback["state_sha256"] == sha256_value(readback["state"]), f"world {role} readback state hash mismatch")
    require(readback["state"] == target["state"]["state"], f"world {role} readback/native state mismatch")
    require(readback["effect_count"] == target["state"]["effect_count"], f"world {role} readback effect count mismatch")
    require(readback["last_effect_id"] == target["state"]["last_effect_id"], f"world {role} readback Effect id mismatch")

    _verify_owner_and_proxy(
        role=role,
        world=world,
        target=target,
        source=source,
        proxy=proxy,
        owners=owners,
        receipt=receipt,
        readback=readback,
        frozen_payload=frozen_payload,
    )

    expected = {
        "S": ("COMMITTED", 1, "RECOVERED_COMMITTED_NO_REPLAY"),
        "R": ("REJECTED_STALE_EPOCH", 0, "RECOVERED_REVOKED_NO_RETRY"),
        "U": ("COMMITTED", 1, "RECOVERED_COMMITTED_NO_REPLAY"),
    }[role]
    require(native_request["decision"] == receipt["decision"] == expected[0], f"world {role} decision mismatch")
    require(target["state"]["effect_count"] == expected[1], f"world {role} Effect count mismatch")
    require(recovery["disposition"] == expected[2], f"world {role} recovery disposition mismatch")
    require(target["state"]["state_sha256"] == sha256_value(target["state"]["state"]), f"world {role} native state hash mismatch")
    require(target["state"]["state"] == (request["desired_state"] if role in {"S", "U"} else _initial_target_state()), f"world {role} native state value mismatch")
    require(_target_state_is_exact(target["state"]["state"]) if role in {"S", "U"} else True, f"world {role} exact target state invalid")
    require(len(target["effects"]) == expected[1], f"world {role} effects table count mismatch")
    if role in {"S", "U"}:
        effect = target["effects"][0]
        require(effect["request_id"] == request["request_id"], f"world {role} Effect request mismatch")
        require(effect["effect_id"] == receipt["effect_id"] == readback["last_effect_id"], f"world {role} Effect id mismatch")
        require(effect["state_sha256"] == sha256_value(request["desired_state"]), f"world {role} Effect state mismatch")
        require(effect["authority_head_sha256"] == delegation["authority_head_sha256"], f"world {role} Effect Authority head mismatch")
    else:
        require(receipt["reason"] == "REVOKED/STALE_AUTHORITY", "world R refusal reason mismatch")
        require(receipt["current_at_commit"] is False and receipt["mutation_applied"] is False, "world R stale gate did not fail closed")
        require(receipt["durable_fence_head_sha256"] == revocation["authority_head_sha256"], "world R refusal did not consume revoke head")
        fence = world["fence_advanced_receipt"]
        require(isinstance(fence, dict), "world R lacks Target durable fence ACK")
        verify_record(
            fence,
            public_key_hex=target_key,
            digest_field="target_receipt_sha256",
            label="world R fence ACK",
        )
        require(fence["decision"] == "FENCE_ADVANCED", "world R fence ACK decision mismatch")
        require(fence["authority_head_sha256"] == revocation["authority_head_sha256"], "world R fence ACK head mismatch")
        require(fence["event_sequence"] == target["events"][1]["sequence"] < receipt["ingress_event_sequence"], "world R fence ACK does not precede ingress")
    if role in {"S", "U"}:
        require(world["fence_advanced_receipt"] is None, f"world {role} unexpectedly has fence ACK")

    return {
        "role": role,
        "world_artifact_sha256": world["world_artifact_sha256"],
        "decision": receipt["decision"],
        "effect_count": target["state"]["effect_count"],
        "refusal_count": sum(item["decision"] == "REJECTED_STALE_EPOCH" for item in target["requests"]),
        "acceptance_count": owners["O_Q"]["event_count"] + owners["O_V"]["event_count"],
        "finality_count": owners["O_P"]["event_count"],
        "ack_received_count": source["ack_received_count"],
        "retry_execute_count": source["retry_execute_count"],
        "source_phase": source["phase"],
        "startup_surfaces": [item["visible_surface"] for item in source["runtime_startups"]],
        "target_certificate": certificate,
        "target_db_sha256": file_sha256(target_path),
    }


def _verify_owner_and_proxy(
    *,
    role: str,
    world: Mapping[str, Any],
    target: Mapping[str, Any],
    source: Mapping[str, Any],
    proxy: Mapping[str, Any],
    owners: Mapping[str, Mapping[str, Any]],
    receipt: Mapping[str, Any],
    readback: Mapping[str, Any],
    frozen_payload: Mapping[str, Any],
) -> None:
    processes = world["processes"]
    require(processes["candidate_source_exitcode"] == -15, f"world {role} source was not SIGTERM-terminated")
    require(processes["candidate_recovery_exitcode"] == 0, f"world {role} recovery process failed")
    require(source["source_process_id"] == processes["candidate_source"], f"world {role} source PID mismatch")
    require(source["ack_received_count"] == 0, f"world {role} source received an ACK")
    require(source["retry_execute_count"] == 0, f"world {role} source replayed execute")
    require([item["phase"] for item in source["runtime_startups"]] == ["RECOVERY", "SOURCE"], f"world {role} startup phases mismatch")
    startup_by_phase = {item["phase"]: item for item in source["runtime_startups"]}
    require(startup_by_phase["SOURCE"]["process_id"] == processes["candidate_source"], f"world {role} source startup PID mismatch")
    require(startup_by_phase["RECOVERY"]["process_id"] == processes["candidate_recovery"], f"world {role} recovery startup PID mismatch")
    require(source["payload_sha256"] == sha256_value(frozen_payload), f"world {role} source payload mismatch")
    require(source["request"] == frozen_payload["request"], f"world {role} durable source request differs")
    require(source["request_sha256"] == sha256_value(source["request"]), f"world {role} durable source request hash mismatch")
    for item in source["runtime_startups"]:
        surface = item["visible_surface"]
        require(surface["candidate_artifact_sha256"] == frozen_payload["candidate_artifact_sha256"], f"world {role} startup artifact mismatch")
        require(surface["payload_sha256"] == sha256_value(frozen_payload), f"world {role} startup payload mismatch")

    proxy_receipt = world["ack_drop_proxy_receipt"]
    require(proxy["event_count"] == 1 and proxy["events"] == [proxy_receipt], f"world {role} proxy DB/receipt mismatch")
    require(proxy["identity"]["public_key_hex"] == world["key_registry"]["proxy_public_key_hex"], f"world {role} proxy key mismatch")
    require(proxy["identity"]["process_id"] == processes["ack_drop_proxy"], f"world {role} proxy process mismatch")
    verify_record(
        proxy_receipt,
        public_key_hex=proxy["identity"]["public_key_hex"],
        digest_field="proxy_receipt_sha256",
        label=f"world {role} ACK-drop receipt",
    )
    require(proxy_receipt["target_receipt_sha256"] == receipt["target_receipt_sha256"], f"world {role} proxy receipt detached")
    require(proxy_receipt["candidate_ack_channel_configured"] is True, f"world {role} ACK channel absent")
    require(proxy_receipt["candidate_ack_delivered"] is False, f"world {role} proxy delivered ACK")

    controller_key = world["key_registry"]["controller_public_key_hex"]
    verify_record(
        world["controller_schedule"],
        public_key_hex=controller_key,
        digest_field="controller_receipt_sha256",
        label=f"world {role} controller schedule",
    )
    require(world["controller_schedule"]["role"] == role, f"world {role} schedule role mismatch")
    require(world["controller_schedule"]["candidate_payload_sha256"] == sha256_value(frozen_payload), f"world {role} schedule payload mismatch")
    termination = world["controller_termination_receipt"]
    verify_record(
        termination,
        public_key_hex=controller_key,
        digest_field="controller_receipt_sha256",
        label=f"world {role} termination receipt",
    )
    require(termination["signal"] == "SIGTERM" and termination["source_exitcode"] == -15, f"world {role} termination semantics mismatch")
    require(termination["source_process_id"] == processes["candidate_source"], f"world {role} termination PID mismatch")
    require(termination["target_receipt_sha256"] == receipt["target_receipt_sha256"], f"world {role} termination Target binding mismatch")
    require(termination["ack_drop_proxy_receipt_sha256"] == proxy_receipt["proxy_receipt_sha256"], f"world {role} termination proxy binding mismatch")

    keys = [
        world["key_registry"]["authority_public_key_hex"],
        world["key_registry"]["lab_root_public_key_hex"],
        world["key_registry"]["target_public_key_hex"],
        controller_key,
        world["key_registry"]["proxy_public_key_hex"],
        *world["key_registry"]["owner_public_keys"].values(),
    ]
    require(len(keys) == len(set(keys)), f"world {role} process keys are not independent")
    pids = [
        processes["target"],
        processes["candidate_source"],
        processes["candidate_recovery"],
        processes["ack_drop_proxy"],
        *processes["owners"].values(),
    ]
    require(len(pids) == len(set(pids)), f"world {role} process boundaries collapsed")

    for owner_id, owner in owners.items():
        _verify_owner_chain(owner, owner_id)
        require(owner["identity"]["public_key_hex"] == world["key_registry"]["owner_public_keys"][owner_id], f"world {role} {owner_id} key mismatch")
        require(owner["identity"]["pinned_q_sha256"] == frozen_payload["q_sha256"], f"world {role} {owner_id} pinned Q mismatch")
        pinned_peers = json.loads(owner["identity"]["pinned_acceptance_keys_json"])
        if owner_id in {"O_Q", "O_V"}:
            require(owner["identity"]["pinned_lab_root_public_key_hex"] == frozen_payload["lab_root_public_key_hex"], f"world {role} {owner_id} pinned lab root mismatch")
            require(pinned_peers == {}, f"world {role} {owner_id} has unexpected peer keys")
        else:
            require(owner["identity"]["pinned_lab_root_public_key_hex"] is None, f"world {role} O_P must not receive a mutable lab root")
            require(
                pinned_peers
                == {
                    owner: owners[owner]["identity"]["public_key_hex"]
                    for owner in ("O_Q", "O_V")
                },
                f"world {role} O_P pinned Acceptance keys mismatch",
            )
    # U is deliberately unscored, not forced to zero.  Because its Target has
    # not consumed the revoke, its raw local decision can be COMMITTED and its
    # native owners may consistently append the same postconditions as S.
    expected_counts = (
        {"O_Q": 0, "O_V": 0, "O_P": 0}
        if role == "R"
        else {"O_Q": 1, "O_V": 1, "O_P": 1}
    )
    require({key: value["event_count"] for key, value in owners.items()} == expected_counts, f"world {role} owner-native event counts mismatch")
    if role == "R":
        require(world["acceptances"] == [] and world["finality"] is None, f"world {role} synthesized postconditions")
        return

    acceptances = [owners[owner]["events"][0]["record"] for owner in ("O_Q", "O_V")]
    require(sorted(acceptances, key=lambda item: item["owner_id"]) == world["acceptances"], f"world {role} Acceptance summary/owner DB mismatch")
    for acceptance in acceptances:
        require(acceptance["schema"] == "OWNER_NATIVE_ACCEPTANCE_V1", f"world {role} Acceptance schema mismatch")
        require(acceptance["decision"] == "ACCEPTED_EXACT_EFFECT", f"world {role} Acceptance decision mismatch")
        require(acceptance["q_sha256"] == frozen_payload["q_sha256"], f"world {role} Acceptance Q mismatch")
        require(acceptance["target_receipt_sha256"] == receipt["target_receipt_sha256"], f"world {role} Acceptance receipt mismatch")
        require(acceptance["readback_sha256"] == readback["target_receipt_sha256"], f"world {role} Acceptance readback mismatch")
        require(acceptance["effect_id"] == receipt["effect_id"], f"world {role} Acceptance Effect mismatch")
        require(acceptance["owner_process_id"] == processes["owners"][acceptance["owner_id"]], f"world {role} Acceptance process mismatch")
    finality = owners["O_P"]["events"][0]["record"]
    require(finality == world["finality"], f"world {role} finality summary/owner DB mismatch")
    require(finality["schema"] == "OWNER_NATIVE_FINALITY_V1", f"world {role} finality schema mismatch")
    require(finality["decision"] == "FINALIZED_EXACTLY_ONCE", f"world {role} finality decision mismatch")
    require(finality["effect_id"] == receipt["effect_id"], f"world {role} finality Effect mismatch")
    require(finality["q_sha256"] == frozen_payload["q_sha256"], f"world {role} finality Q mismatch")
    require(finality["acceptance_hashes"] == sorted(item["owner_receipt_sha256"] for item in acceptances), f"world {role} finality Acceptance binding mismatch")
    require(finality["owner_process_id"] == processes["owners"]["O_P"], f"world {role} finality process mismatch")


def _evaluate_strict(run_dir: pathlib.Path) -> dict[str, Any]:
    run_dir = pathlib.Path(run_dir).resolve()
    twin = load_json(run_dir / "TWIN-ARTIFACT.json")
    verify_self_hash(twin, "twin_artifact_sha256", "TWIN root")
    require(twin.get("schema") == "WAVE024_AUTHORITY_EPOCH_TWIN_ARTIFACT_V1", "TWIN schema mismatch")
    require(twin.get("status") == "RUN_COMPLETED_PENDING_INDEPENDENT_EVALUATION", "TWIN runtime status mismatch")
    require(set(twin.get("worlds", {})) == {"S", "R", "U"}, "TWIN world set mismatch")
    require(
        twin.get("artifact_hash_semantics")
        == "CANONICAL_JSON_SHA256_AFTER_REMOVING_TWIN_ARTIFACT_SHA256_FIELD",
        "TWIN artifact hash semantics missing or changed",
    )

    frozen_payload = load_json(run_dir / "FROZEN-CANDIDATE-PAYLOAD.json")
    require(frozen_payload.get("schema") == "WAVE024_CANDIDATE_PUBLIC_INPUT_V1", "frozen candidate schema mismatch")
    require(twin["candidate_payload_sha256"] == sha256_value(frozen_payload), "TWIN/frozen candidate hash mismatch")
    require(twin["request_sha256"] == sha256_value(frozen_payload["request"]), "TWIN request hash mismatch")
    require(frozen_payload["q_sha256"] == sha256_value(frozen_payload["task"]), "Q/task hash mismatch")
    require(frozen_payload["request"]["q_sha256"] == frozen_payload["q_sha256"], "request detached from Q")
    require(frozen_payload["request"]["delegation"]["q_sha256"] == frozen_payload["q_sha256"], "delegation detached from Q")
    require(frozen_payload["candidate_artifact"] == "twin_runtime.py", "candidate artifact name mismatch")
    candidate_path = pathlib.Path(__file__).resolve().parent / frozen_payload["candidate_artifact"]
    _verify_file_hash(candidate_path, frozen_payload["candidate_artifact_sha256"], "candidate artifact")
    require(twin["candidate_artifact_sha256"] == frozen_payload["candidate_artifact_sha256"], "TWIN candidate artifact hash mismatch")

    delegation, revocation = _verify_authority_root(run_dir, twin)
    require(frozen_payload["request"]["delegation"] == delegation, "frozen request delegation mismatch")
    require(frozen_payload["authority_root_public_key_hex"] == twin["authority_public_key_hex"], "frozen Authority root mismatch")
    require(frozen_payload["lab_root_public_key_hex"] == twin["lab_root_public_key_hex"], "frozen lab root mismatch")

    worlds = {
        role: _verify_world(
            run_dir,
            role,
            twin["worlds"][role],
            twin,
            frozen_payload,
            delegation,
            revocation,
        )
        for role in ("S", "R", "U")
    }
    require(
        twin.get("world_artifact_sha256")
        == {
            role: worlds[role]["world_artifact_sha256"]
            for role in ("S", "R", "U")
        },
        "TWIN root does not bind exact child world semantic hashes",
    )
    s_receipt = load_json(run_dir / twin["worlds"]["S"])[
        "target_execute_receipt"
    ]
    s_receipt_hash = s_receipt["target_receipt_sha256"]
    require(
        revocation.get("experiment_predecessor_s_target_receipt_sha256")
        == s_receipt_hash,
        "Authority-signed revocation does not bind the verified S Target receipt",
    )
    require(
        revocation.get("experiment_predecessor_s_target_certificate_sha256")
        == s_receipt["target_certificate"]["certificate_sha256"],
        "Authority-signed predecessor Target certificate mismatch",
    )
    require(
        revocation.get("experiment_predecessor_s_request_sha256")
        == s_receipt["request_sha256"],
        "Authority-signed predecessor request mismatch",
    )
    require(
        revocation.get("experiment_predecessor_s_effect_id")
        == s_receipt["effect_id"],
        "Authority-signed predecessor Effect mismatch",
    )
    require(
        revocation.get("experiment_predecessor_validation")
        == "AUTHORITY_VERIFIED_PINNED_LAB_ROOT_TARGET_SIGNATURE_AND_EXACT_SCOPE",
        "Authority predecessor validation mode missing or changed",
    )
    authority_timing = twin.get("authority_timing", {})
    require(
        authority_timing
        == {
            "S": "COMPLETED_BEFORE_AUTHORITY_REVOCATION_RECORD",
            "R": "TARGET_ACKED_MATCHING_REVOCATION_BEFORE_INGRESS",
            "U": "AUTHORITY_REVOCATION_EXISTS_TARGET_NOT_ACKED_NOT_SCORED",
            "s_target_receipt_sha256": s_receipt_hash,
            "revocation_head_sha256": revocation["authority_head_sha256"],
        },
        "TWIN Authority timing summary/native causal evidence mismatch",
    )
    _verify_registry(run_dir, twin, [worlds[role]["target_certificate"] for role in ("S", "R", "U")])

    surfaces = [worlds[role]["startup_surfaces"] for role in ("S", "R", "U")]
    require(canonical_bytes(surfaces[0]) == canonical_bytes(surfaces[1]) == canonical_bytes(surfaces[2]), "recorded candidate startup surfaces differ across S/R/U")
    require(worlds["S"]["decision"] == "COMMITTED" and worlds["S"]["effect_count"] == 1, "S discriminator failed")
    require(worlds["R"]["decision"] == "REJECTED_STALE_EPOCH" and worlds["R"]["effect_count"] == 0, "R discriminator failed")
    require(worlds["R"]["refusal_count"] == 1, "R lacks exactly one native refusal")
    require(worlds["U"]["decision"] == "COMMITTED", "U Target-local raw decision changed unexpectedly")

    expected_results = {
        "S": {
            "decision": "COMMITTED",
            "effect_count": 1,
            "acceptance_count": 2,
            "finality_count": 1,
            "retry_effect_count": 0,
        },
        "R": {
            "decision": "REJECTED_STALE_EPOCH",
            "effect_count": 0,
            "acceptance_count": 0,
            "finality_count": 0,
            "retry_effect_count": 0,
            "authority_rejection_count": 1,
        },
    }
    require(twin["results"]["S"] == expected_results["S"], "TWIN S summary/native evidence mismatch")
    require(twin["results"]["R"] == expected_results["R"], "TWIN R summary/native evidence mismatch")
    u_result = twin["results"]["U"]
    require(u_result["scoring_status"] == "CONCURRENT_OR_UNORDERED/NOT_SCORED", "U was incorrectly scored")
    require(u_result["authority_revoke_record_exists"] is True, "U lacks Authority revoke negative control")
    require(u_result["target_matching_fence_ack_exists"] is False and u_result["target_consumed_matching_fence_before_ingress"] is False, "U incorrectly claims Target fence consumption")

    return {
        "schema": "WAVE024_INDEPENDENT_EVALUATION_V1",
        "status": "EVALUATED_MIXED_SCOPED_LOCAL_SYNTHETIC_DISCRIMINATOR",
        "run_dir": str(run_dir),
        "root_evidence": {
            "twin_self_hash_verified": True,
            "twin_artifact_sha256": twin["twin_artifact_sha256"],
            "world_self_hashes_verified": True,
            "authority_and_registry_physical_hashes_verified": True,
            "all_world_native_file_hashes_verified": True,
            "external_append_only_anchor": "NOT_TESTED",
        },
        "worlds": {
            role: without(value, "startup_surfaces", "target_certificate")
            for role, value in worlds.items()
        },
        "claims": {
            "CL-024-TARGET-CONSUMED-AUTHORITY-FENCE": {
                "status": "SUPPORT_SCOPED",
                "evidence": "R Target-native FENCE_ADVANCED precedes ingress and produces one signed stale refusal with zero Effect; S retains current fence and commits one exact Effect.",
            },
            "CL-024-EXACTLY-ONCE-RECOVERY": {
                "status": "SUPPORT_SCOPED",
                "evidence": "All source processes end by SIGTERM after proxy-owned ACK drop; new recovery processes verify signed status/readback with zero ACK and zero execute retry.",
            },
            "CL-024-NATIVE-POSTCONDITIONS": {
                "status": "SUPPORT_SCOPED",
                "evidence": "S and unscored U have independently signed O_Q/O_V Acceptance rows and O_P finality for their Target-local commit; R has no owner postconditions for its native refusal.",
            },
            "CL-024-ISOMORPHIC-BLINDNESS": {
                "status": "FAIL",
                "evidence": "Recorded payload/startup surfaces are equal, but fixed S→R→U execution order and shared same-UID filesystem/process visibility leave path/order/timing side channels. The full frozen claim is not established.",
            },
            "CL-024-GLOBAL-AUTHORITY-CURRENTNESS": {
                "status": "NOT_TESTED",
                "evidence": "U contains an Authority revoke without a Target-consumed matching fence and is explicitly not scored.",
            },
        },
        "limitations": [
            "LOCAL_SYNTHETIC_AUTHORITY_ONLY",
            "TARGET_PROCESS_RESTART_PERSISTENCE_NOT_TESTED",
            "HOSTILE_SAME_UID_BLINDNESS_AND_WRITE_RESISTANCE_NOT_ESTABLISHED",
            "EXTERNAL_APPEND_ONLY_ROOT_ANCHOR_NOT_TESTED",
            "NO_LEGAL_AUTHORITY_OR_PHYSICAL_EFFECT_OR_PRODUCTION_CLAIM",
            "NO_A1_A5_COMPARISON_OR_WINNER",
        ],
    }


def evaluate_run(run_dir: pathlib.Path) -> dict[str, Any]:
    """Evaluate a run fail-closed while always returning per-claim states."""

    try:
        return _evaluate_strict(pathlib.Path(run_dir))
    except (EvaluationError, KeyError, TypeError, ValueError, sqlite3.Error) as exc:
        return {
            "schema": "WAVE024_INDEPENDENT_EVALUATION_V1",
            "status": "REJECTED_EVIDENCE_PACKAGE",
            "run_dir": str(pathlib.Path(run_dir).resolve()),
            "errors": [str(exc)],
            "claims": {
                claim: {
                    "status": "FAIL",
                    "evidence": "The evidence package failed independent validation.",
                }
                for claim in SCOPED_CLAIMS
            }
            | {
                "CL-024-GLOBAL-AUTHORITY-CURRENTNESS": {
                    "status": "NOT_TESTED",
                    "evidence": "This stronger claim is outside Wave 024 even when package validation fails.",
                }
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    result = evaluate_run(args.run_dir)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 1 if result["status"] == "REJECTED_EVIDENCE_PACKAGE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
