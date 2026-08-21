#!/usr/bin/env python3
"""Independent artifact evaluator for the Wave 016 E3 pair.

The evaluator intentionally does not import ``pair_runtime`` and does not use
``pair-evaluation.json`` or ``result.json`` as acceptance inputs.  It rebuilds
the decision from raw arm/broker artifacts, Ed25519 records, ledger HMACs and
SQLite rows.

Its strongest accepted claim is a scoped local-digital result.  It does not
accept legal Authority, a physical electrical Effect, external PKI binding,
hostile-process isolation, production reliability, or general protocol
formation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


EVALUATOR_VERSION = "WAVE016_ROOT_EVALUATOR_V1"
TARGET_ID = "VenueV:CircuitC7"
DECOY_TARGET_ID = "VenueV:CircuitC8"
ARM_ID = "A4-MATURE-ACK-RECONCILIATION"
INITIAL_STATE = {"energized": False, "power_kw": 0.0}
DESIRED_STATE = {"energized": True, "power_kw": 3.0}

WORLD_A_DISPOSITION = "RECOVERED_EXISTING_EFFECT_NO_REPLAY"
WORLD_B_DISPOSITION = "RECOVERED_NO_EFFECT_SAFE_RETRY"

UNTRUSTED_SUMMARY_FILES = frozenset({"pair-evaluation.json", "result.json"})
ROOT_OUTPUT_FILES = frozenset(
    {"ROOT-FREEZE.json", "ROOT-INDEPENDENT-ACCEPTANCE.json"}
)
FROZEN_SQLITE_DIR = "ROOT-FROZEN-SQLITE"


class AcceptanceError(ValueError):
    """The raw artifact set does not support the scoped acceptance claim."""


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AcceptanceError("value is not canonical JSON: %s" % exc) from exc


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _without(value: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    excluded = set(keys)
    return {key: item for key, item in value.items() if key not in excluded}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), "missing artifact: %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AcceptanceError("invalid JSON artifact: %s" % path) from exc


def verify_target_signature(
    record: Mapping[str, Any],
    expected_public_key_hex: str,
) -> None:
    require(
        record.get("target_public_key_hex") == expected_public_key_hex,
        "Target endpoint key replacement detected",
    )
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(expected_public_key_hex)
        )
        public_key.verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(_without(record, "signature_hex")),
        )
    except Exception as exc:
        raise AcceptanceError("invalid Target Ed25519 signature") from exc


def exact_binding(view: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
    }


def validate_exact_binding(
    value: Mapping[str, Any],
    view: Mapping[str, Any],
) -> None:
    for field, expected in exact_binding(view).items():
        require(
            value.get(field) == expected,
            "exact binding mismatch: %s" % field,
        )


def validate_status_envelope(
    envelope: Mapping[str, Any],
    query: Mapping[str, Any],
    view: Mapping[str, Any],
    expected_public_key_hex: str,
) -> None:
    require(
        envelope.get("schema") == "TARGET_OPERATION_STATUS_V1",
        "wrong Target status schema",
    )
    verify_target_signature(envelope, expected_public_key_hex)
    validate_exact_binding(envelope, view)
    query_bytes = canonical_bytes(query).decode("utf-8")
    require(
        envelope.get("query_request_bytes") == query_bytes,
        "Target status does not preserve exact query bytes",
    )
    require(
        envelope.get("query_request_sha256")
        == hashlib.sha256(query_bytes.encode("utf-8")).hexdigest(),
        "Target status query hash mismatch",
    )
    coverage = envelope.get("covered_ledger_range")
    require(isinstance(coverage, Mapping), "Target status lacks ledger coverage")
    require(
        coverage.get("from_version") == 0,
        "Target status coverage does not start at ledger genesis",
    )
    require(
        coverage.get("through_version") == envelope.get("observed_version"),
        "Target status coverage is not complete through observed head",
    )
    require(
        coverage.get("current_head") == envelope.get("current_head"),
        "Target status coverage head differs from signed current head",
    )
    status = envelope.get("status")
    require(
        status in {"COMMITTED", "NOT_COMMITTED", "NOT_FOUND"},
        "unsupported Target status",
    )
    occurrences = envelope.get("matching_occurrence_hashes")
    require(isinstance(occurrences, list), "occurrence hashes are not a list")
    if status in {"NOT_COMMITTED", "NOT_FOUND"}:
        require(occurrences == [], "negative status has matching occurrence")
    else:
        require(
            len(occurrences) == 1,
            "committed status does not bind exactly one occurrence",
        )


def validate_capability_freshness(
    freshness: Mapping[str, Any],
    view: Mapping[str, Any],
    expected_public_key_hex: str,
    negative_head: str,
    desired_state_sha256: str,
) -> None:
    require(
        freshness.get("schema") == "TARGET_CAPABILITY_FRESHNESS_V1",
        "wrong capability freshness schema",
    )
    verify_target_signature(freshness, expected_public_key_hex)
    validate_exact_binding(freshness, view)
    require(freshness.get("status") == "CURRENT", "capability is not CURRENT")
    require(
        freshness.get("capability_target_id") == view["target_id"],
        "freshness capability target mismatch",
    )
    require(
        freshness.get("capability_actor_id") == ARM_ID,
        "freshness capability actor mismatch",
    )
    require(
        freshness.get("capability_operation") == "SET_STATE",
        "freshness capability operation mismatch",
    )
    require(
        freshness.get("capability_allowed_state_sha256")
        == desired_state_sha256,
        "freshness capability allowed-state mismatch",
    )
    require(
        freshness.get("capability_consumed_by_request_id") is None,
        "consumed capability falsely claims CURRENT",
    )
    require(
        freshness.get("observed_negative_head") == negative_head,
        "freshness is detached from signed negative head",
    )
    require(
        freshness.get("current_head") == negative_head,
        "Target head moved before safe retry",
    )
    require(
        freshness.get("observed_version") == 0,
        "freshness was not evaluated at the negative version",
    )


def validate_sequence(world_slot: str, transcript: Sequence[Mapping[str, Any]]) -> None:
    schemas = [event.get("message", {}).get("schema") for event in transcript]
    if world_slot == "world-a":
        expected = [
            "BROKER_SUBMIT_REQUEST_V1",
            "BROKER_SUBMIT_RESULT_V1",
            "BROKER_EXACT_STATUS_QUERY_V1",
            "BROKER_EXACT_STATUS_RESULT_V1",
        ]
    elif world_slot == "world-b":
        expected = [
            "BROKER_SUBMIT_REQUEST_V1",
            "BROKER_SUBMIT_RESULT_V1",
            "BROKER_EXACT_STATUS_QUERY_V1",
            "BROKER_EXACT_STATUS_RESULT_V1",
            "BROKER_CAPABILITY_FRESHNESS_QUERY_V1",
            "BROKER_CAPABILITY_FRESHNESS_RESULT_V1",
            "BROKER_SAFE_RETRY_REQUEST_V1",
            "BROKER_SAFE_RETRY_RESULT_V1",
        ]
    else:
        raise AcceptanceError("unknown world slot")
    require(
        schemas == expected,
        "%s transcript order invalid; retry may precede freshness" % world_slot,
    )
    for index, event in enumerate(transcript):
        expected_direction = "ARM_TO_BROKER" if index % 2 == 0 else "BROKER_TO_ARM"
        require(
            event.get("direction") == expected_direction,
            "%s transcript direction invalid" % world_slot,
        )


def _rows(connection: sqlite3.Connection, table: str, order_by: str) -> list:
    return [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM %s ORDER BY %s" % (table, order_by)
        )
    ]


def sqlite_snapshot(db_path: Path) -> Dict[str, Any]:
    require(db_path.is_file(), "missing SQLite artifact: %s" % db_path)
    connection = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        require(quick_check == "ok", "SQLite quick_check failed")
        tables = {
            "metadata": _rows(connection, "metadata", "singleton"),
            "targets": _rows(connection, "targets", "target_id"),
            "capabilities": _rows(connection, "capabilities", "capability_id"),
            "requests": _rows(connection, "requests", "request_id"),
            "receipts": _rows(connection, "receipts", "receipt_id"),
            "commit_events": _rows(connection, "commit_events", "commit_id"),
            "readbacks": _rows(connection, "readbacks", "readback_id"),
        }
        return {
            "schema": "WAVE016_SQLITE_LOGICAL_SNAPSHOT_V1",
            "tables": tables,
            "snapshot_sha256": sha256_value(tables),
        }
    finally:
        connection.close()


def frozen_sqlite_path(
    run_dir: Path,
    world_slot: str,
    filename: str,
) -> Path:
    return run_dir / FROZEN_SQLITE_DIR / world_slot / filename


def _assert_standalone_delete_journal(db_path: Path) -> None:
    require(db_path.is_file(), "frozen standalone SQLite missing: %s" % db_path)
    require(
        not Path(str(db_path) + "-wal").exists()
        and not Path(str(db_path) + "-shm").exists(),
        "frozen SQLite has unbound WAL/SHM companions",
    )
    connection = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    try:
        journal_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0])
        require(
            journal_mode.lower() == "delete",
            "frozen SQLite is not DELETE-journal standalone",
        )
        require(
            connection.execute("PRAGMA quick_check").fetchone()[0] == "ok",
            "frozen standalone SQLite quick_check failed",
        )
    finally:
        connection.close()


def freeze_standalone_databases(run_dir: Path) -> Dict[str, Any]:
    """Materialize every runtime DB, including WAL state, as standalone SQLite.

    ``sqlite3.Connection.backup`` reads the source's coherent logical view,
    including committed WAL pages.  The destination is a new DELETE-journal
    database.  Acceptance subsequently reads only these destinations.
    """

    frozen_root = run_dir / FROZEN_SQLITE_DIR
    source_paths = sorted(
        path
        for path in run_dir.glob("world-*/*.sqlite3")
        if FROZEN_SQLITE_DIR not in path.parts
    )
    require(len(source_paths) == 4, "expected exactly four runtime SQLite databases")
    frozen = {}
    for source in source_paths:
        relative = source.relative_to(run_dir)
        destination = frozen_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".sqlite3.tmp")
        if temporary.exists():
            temporary.unlink()
        source_connection = sqlite3.connect(
            "file:%s?mode=ro" % source,
            uri=True,
        )
        destination_connection = sqlite3.connect(str(temporary))
        try:
            source_connection.backup(destination_connection)
            destination_connection.execute("PRAGMA journal_mode=DELETE")
            destination_connection.commit()
        finally:
            destination_connection.close()
            source_connection.close()
        for suffix in ("-wal", "-shm"):
            temporary_companion = Path(str(temporary) + suffix)
            if temporary_companion.exists():
                temporary_companion.unlink()
        os.replace(temporary, destination)
        for suffix in ("-wal", "-shm"):
            companion = Path(str(destination) + suffix)
            require(
                not companion.exists(),
                "standalone freeze unexpectedly created %s" % companion.name,
            )
        _assert_standalone_delete_journal(destination)
        frozen[str(relative)] = {
            "source_relative_path": str(relative),
            "frozen_relative_path": str(destination.relative_to(run_dir)),
            "physical_file_sha256": sha256_file(destination),
            "logical_snapshot_sha256": sqlite_snapshot(destination)[
                "snapshot_sha256"
            ],
            "journal_mode": "delete",
            "wal_shm_absent": True,
        }
    return frozen


def _verify_ledger_record(
    record: Mapping[str, Any],
    *,
    hash_field: str,
    auth_field: str,
    key: bytes,
) -> None:
    require(
        record.get(hash_field)
        == sha256_value(_without(record, hash_field, auth_field)),
        "ledger record content hash invalid",
    )
    expected_auth = hmac.new(
        key,
        canonical_bytes(_without(record, auth_field)),
        hashlib.sha256,
    ).hexdigest()
    require(
        hmac.compare_digest(str(record.get(auth_field, "")), expected_auth),
        "ledger record HMAC invalid",
    )


def validate_ledger(
    snapshot: Mapping[str, Any],
    target_id: str,
    *,
    expected_actor: str,
) -> Dict[str, Any]:
    tables = snapshot["tables"]
    require(len(tables["metadata"]) == 1, "ledger metadata is not singular")
    metadata = tables["metadata"][0]
    key = bytes.fromhex(metadata["authentication_key_hex"])
    targets = [row for row in tables["targets"] if row["target_id"] == target_id]
    events = [
        row for row in tables["commit_events"] if row["target_id"] == target_id
    ]
    receipts_rows = [
        row for row in tables["receipts"] if row["target_id"] == target_id
    ]
    require(len(targets) == 1, "exact target is not singular")
    require(len(events) == 1, "exact target mutation count is not exactly one")
    require(
        len(tables["commit_events"]) == 1,
        "ledger contains mutation outside the exact target",
    )
    require(len(receipts_rows) == 1, "exact target receipt count is not one")
    require(len(tables["requests"]) == 1, "ledger request count is not one")
    require(len(tables["readbacks"]) == 1, "ledger readback count is not one")
    require(len(tables["capabilities"]) == 1, "ledger capability count is not one")

    target = targets[0]
    event = events[0]
    receipt = json.loads(receipts_rows[0]["receipt_json"])
    readback = json.loads(tables["readbacks"][0]["readback_json"])
    capability = tables["capabilities"][0]
    request = tables["requests"][0]

    _verify_ledger_record(
        receipt,
        hash_field="receipt_sha256",
        auth_field="receipt_auth_hex",
        key=key,
    )
    _verify_ledger_record(
        readback,
        hash_field="readback_sha256",
        auth_field="readback_auth_hex",
        key=key,
    )
    require(receipt["decision"] == "COMMITTED", "ledger receipt is not COMMITTED")
    require(receipt["mutation_applied"] is True, "ledger receipt is non-mutating")
    require(receipt["target_id"] == target_id, "receipt target mismatch")
    require(receipt["actor_id"] == expected_actor, "receipt actor mismatch")
    require(receipt["pre_state"] == INITIAL_STATE, "receipt pre-state mismatch")
    require(receipt["post_state"] == DESIRED_STATE, "receipt post-state mismatch")
    require(receipt["pre_version"] == 0, "receipt pre-version mismatch")
    require(receipt["post_version"] == 1, "receipt post-version mismatch")
    require(
        target["version"] == 1
        and json.loads(target["state_json"]) == DESIRED_STATE,
        "Target final state/version mismatch",
    )
    require(event["pre_version"] == 0 and event["post_version"] == 1, "commit CAS mismatch")
    require(event["commit_id"] == receipt["commit_id"], "commit/receipt id mismatch")
    require(
        event["request_sha256"] == receipt["request_sha256"],
        "commit/receipt request mismatch",
    )
    require(
        event["post_state_sha256"] == receipt["post_state_sha256"],
        "commit/receipt state mismatch",
    )
    require(
        readback["attached_to_receipt_commit"] is True,
        "readback is not attached to committed receipt",
    )
    require(
        readback["receipt_sha256"] == receipt["receipt_sha256"],
        "readback/receipt hash mismatch",
    )
    require(
        readback["observed_commit_id"] == receipt["commit_id"]
        and readback["observed_version"] == 1
        and readback["observed_state"] == DESIRED_STATE,
        "readback does not observe the exact commit",
    )
    require(
        request["receipt_id"] == receipt["receipt_id"]
        and request["request_sha256"] == receipt["request_sha256"],
        "request index is detached from receipt",
    )
    require(
        capability["consumed_by_request_id"] == receipt["request_id"]
        and capability["consumed_by_receipt_id"] == receipt["receipt_id"],
        "one-shot capability was not consumed by exact commit",
    )
    return {
        "ledger_id": metadata["ledger_id"],
        "target": target,
        "event": event,
        "receipt": receipt,
        "readback": readback,
        "capability": capability,
        "mutation_count": len(events),
        "logical_snapshot_sha256": snapshot["snapshot_sha256"],
    }


def current_head_from_ledger(ledger: Mapping[str, Any]) -> str:
    target = ledger["target"]
    body = {
        "ledger_id": ledger["ledger_id"],
        "target_id": target["target_id"],
        "version": target["version"],
        "state_sha256": target["state_sha256"],
        "last_commit_id": target["last_commit_id"],
        "last_request_sha256": target["last_request_sha256"],
    }
    return sha256_value(body)


def _all_target_records(transcript: Sequence[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
    for event in transcript:
        message = event.get("message", {})
        if not isinstance(message, Mapping):
            continue
        envelope = message.get("status_envelope")
        if isinstance(envelope, Mapping):
            yield envelope
        freshness = message.get("capability_freshness")
        if isinstance(freshness, Mapping):
            yield freshness
        decoys = message.get("nearby_decoys", [])
        if isinstance(decoys, list):
            for decoy in decoys:
                if isinstance(decoy, Mapping):
                    yield decoy


def validate_world(
    run_dir: Path,
    world_slot: str,
    shared_view: Mapping[str, Any],
) -> Dict[str, Any]:
    world_dir = run_dir / world_slot
    launch = load_json(world_dir / "blind-launch-receipt.json")
    arm = load_json(world_dir / "arm-result.json")
    broker = load_json(world_dir / "broker-private-result.json")
    transcript = arm["transcript"]
    broker_transcript = broker["transcript"]

    require(launch["process_start_method"] == "spawn", "arm was not spawn-launched")
    require(launch["exit_code"] == 0, "blind arm exit was nonzero")
    require(launch["private_material_absent"] is True, "private launch scan failed")
    require(
        launch["visible_surface"]["view"] == shared_view,
        "blind arm startup view differs from frozen shared view",
    )
    require(
        launch["visible_surface"]["view_bytes"]
        == canonical_bytes(shared_view).decode("utf-8"),
        "blind arm startup view bytes mismatch",
    )
    require(launch["worker_result"] == arm, "launch receipt/arm result mismatch")
    validate_sequence(world_slot, transcript)
    require(
        broker_transcript[: len(transcript)] == transcript,
        "arm and broker transcript disagree",
    )
    require(
        broker_transcript[-1]["message"]["schema"] == "BROKER_STOP_V1",
        "broker transcript lacks terminal stop",
    )
    require(
        sha256_value(transcript) == arm["transcript_sha256"],
        "arm transcript hash mismatch",
    )
    require(
        sha256_value(broker_transcript) == broker["transcript_sha256"],
        "broker transcript hash mismatch",
    )
    raw_public = canonical_bytes({"launch": launch, "arm": arm})
    for private_label in (
        "E3A-ACK-LOST-EFFECT",
        "E3B-ACK-LOST-NO-EFFECT",
        "commit_before_unconfirmed",
        "target_private_key_hex",
    ):
        require(
            private_label.encode("utf-8") not in raw_public,
            "private scenario material reached arm artifact",
        )

    submit = transcript[0]["message"]
    ack = transcript[1]["message"]
    status_query = transcript[2]["message"]
    status_result = transcript[3]["message"]
    require(submit["schema"] == "BROKER_SUBMIT_REQUEST_V1", "missing initial submit")
    require(
        ack
        == {
            "schema": "BROKER_SUBMIT_RESULT_V1",
            "status": "OUTCOME_UNCONFIRMED",
            "operation_handle": status_query["operation_handle"],
        },
        "ACK-lost public result is not the fixed unconfirmed response",
    )
    validate_exact_binding(submit, shared_view)
    validate_exact_binding(status_query, shared_view)
    require(
        submit["request_id"] == status_query["request_id"],
        "status query changed request identity",
    )
    expected_target_key = broker["target_public_key_hex"]
    require(
        isinstance(expected_target_key, str) and len(expected_target_key) == 64,
        "broker endpoint trust key missing",
    )
    for record in _all_target_records(transcript):
        verify_target_signature(record, expected_target_key)

    target_db = frozen_sqlite_path(
        run_dir,
        world_slot,
        "target-ledger.sqlite3",
    )
    _assert_standalone_delete_journal(target_db)
    ledger_snapshot = sqlite_snapshot(target_db)
    ledger = validate_ledger(
        ledger_snapshot,
        TARGET_ID,
        expected_actor=ARM_ID,
    )
    require(
        ledger["receipt"] == arm["final_receipt"],
        "arm final receipt differs from durable SQLite receipt",
    )
    require(
        ledger["readback"] == arm["final_readback"],
        "arm final readback differs from durable SQLite readback",
    )

    envelope = status_result["status_envelope"]
    validate_status_envelope(
        envelope,
        status_query,
        shared_view,
        expected_target_key,
    )
    desired_hash = sha256_value(DESIRED_STATE)

    if world_slot == "world-a":
        require(
            envelope["status"] == "COMMITTED",
            "world-a did not reconcile an existing commit",
        )
        require(
            arm["disposition"] == WORLD_A_DISPOSITION,
            "world-a disposition mismatch",
        )
        require(arm["retry_performed"] is False, "world-a replayed the operation")
        require(arm["submit_message_count"] == 1, "world-a emitted a replay submit")
        require(
            status_result["ledger_receipt"] == ledger["receipt"]
            and status_result["ledger_readback"] == ledger["readback"],
            "world-a status evidence differs from durable ledger",
        )
        require(
            envelope["current_head"] == current_head_from_ledger(ledger),
            "world-a signed status is not at durable current head",
        )
        require(
            envelope["matching_occurrence_hashes"]
            == [ledger["receipt"]["receipt_sha256"]],
            "world-a status occurrence does not bind exact receipt",
        )
        require(
            broker["freshness_seen"] is False and broker["retry_seen"] is False,
            "world-a broker executed recovery replay path",
        )
        decoy_ledger = None
    else:
        require(
            envelope["status"] in {"NOT_COMMITTED", "NOT_FOUND"},
            "world-b lacks signed exact negative status",
        )
        require(
            envelope["observed_version"] == 0
            and envelope["observed_state_sha256"]
            == ledger["event"]["pre_state_sha256"],
            "world-b negative status is not bound to pre-commit ledger state",
        )
        require(
            arm["disposition"] == WORLD_B_DISPOSITION,
            "world-b disposition mismatch",
        )
        require(arm["retry_performed"] is True, "world-b did not safe-retry")
        require(arm["submit_message_count"] == 2, "world-b submit count mismatch")
        freshness_query = transcript[4]["message"]
        freshness = transcript[5]["message"]["capability_freshness"]
        require(
            freshness_query["observed_negative_head"] == envelope["current_head"],
            "freshness query is detached from negative head",
        )
        validate_capability_freshness(
            freshness,
            shared_view,
            expected_target_key,
            envelope["current_head"],
            desired_hash,
        )
        retry = transcript[6]["message"]
        retry_result = transcript[7]["message"]
        require(
            retry["request_id"] == submit["request_id"]
            and retry["operation_id"] == submit["operation_id"]
            and retry["observed_negative_head"] == envelope["current_head"],
            "safe retry changed identity or negative-head precondition",
        )
        retry_envelope = retry_result["status_envelope"]
        validate_status_envelope(
            retry_envelope,
            retry,
            shared_view,
            expected_target_key,
        )
        require(retry_envelope["status"] == "COMMITTED", "safe retry did not commit")
        require(
            retry_envelope["current_head"] == current_head_from_ledger(ledger),
            "safe-retry status is not at durable current head",
        )
        require(
            retry_result["ledger_receipt"] == ledger["receipt"]
            and retry_result["ledger_readback"] == ledger["readback"],
            "safe-retry evidence differs from durable ledger",
        )
        require(
            broker["freshness_seen"] is True and broker["retry_seen"] is True,
            "world-b broker trace lacks freshness/retry",
        )

        decoys = status_result.get("nearby_decoys")
        require(isinstance(decoys, list) and len(decoys) == 1, "decoy missing")
        decoy = decoys[0]
        verify_target_signature(decoy, expected_target_key)
        mismatch_fields = {
            field
            for field, expected in exact_binding(shared_view).items()
            if decoy.get(field) != expected
        }
        require(
            {"public_run_id", "world_id", "object_id", "target_id", "operation_id"}
            .issubset(mismatch_fields),
            "historical decoy is not safely excluded by exact binding",
        )
        decoy_db = frozen_sqlite_path(
            run_dir,
            world_slot,
            "historical-decoy-ledger.sqlite3",
        )
        _assert_standalone_delete_journal(decoy_db)
        decoy_snapshot = sqlite_snapshot(decoy_db)
        decoy_ledger = validate_ledger(
            decoy_snapshot,
            DECOY_TARGET_ID,
            expected_actor="HISTORICAL_PLATFORM",
        )
        require(
            decoy["source_ledger_id"] == decoy_ledger["ledger_id"]
            and decoy["source_receipt_id"] == decoy_ledger["receipt"]["receipt_id"]
            and decoy["source_receipt_sha256"]
            == decoy_ledger["receipt"]["receipt_sha256"]
            and decoy["source_commit_id"] == decoy_ledger["receipt"]["commit_id"]
            and decoy["source_readback_sha256"]
            == decoy_ledger["readback"]["readback_sha256"],
            "decoy wrapper is not backed by its historical ledger commit",
        )

    require(broker["ledger_apply_calls"] == 1, "broker apply count is not one")
    return {
        "world_slot": world_slot,
        "disposition": arm["disposition"],
        "retry_performed": arm["retry_performed"],
        "target_public_key_hex": expected_target_key,
        "target_mutation_count": ledger["mutation_count"],
        "target_ledger_snapshot_sha256": ledger["logical_snapshot_sha256"],
        "target_final_head": current_head_from_ledger(ledger),
        "historical_decoy_snapshot_sha256": (
            None
            if decoy_ledger is None
            else decoy_ledger["logical_snapshot_sha256"]
        ),
    }


def _first_difference(left: Sequence[Any], right: Sequence[Any]) -> int:
    for index in range(min(len(left), len(right))):
        if canonical_bytes(left[index]) != canonical_bytes(right[index]):
            return index
    return -1 if len(left) == len(right) else min(len(left), len(right))


def build_freeze(run_dir: Path, world_results: Mapping[str, Any]) -> Dict[str, Any]:
    raw_json_hashes = {}
    for path in sorted(run_dir.rglob("*.json")):
        if path.name in ROOT_OUTPUT_FILES:
            continue
        raw_json_hashes[str(path.relative_to(run_dir))] = sha256_file(path)
    frozen_sqlite = {}
    frozen_root = run_dir / FROZEN_SQLITE_DIR
    frozen_paths = sorted(frozen_root.glob("world-*/*.sqlite3"))
    require(len(frozen_paths) == 4, "formal freeze does not contain all four DBs")
    for path in frozen_paths:
        _assert_standalone_delete_journal(path)
        frozen_sqlite[str(path.relative_to(run_dir))] = {
            "physical_file_sha256": sha256_file(path),
            "logical_snapshot_sha256": sqlite_snapshot(path)[
                "snapshot_sha256"
            ],
            "journal_mode": "delete",
            "wal_shm_absent": True,
        }
    body = {
        "schema": "WAVE016_ROOT_ARTIFACT_FREEZE_V1",
        "evaluator_version": EVALUATOR_VERSION,
        "run_id": run_dir.name,
        "raw_json_sha256": raw_json_hashes,
        # Acceptance reads only these coherent standalone copies.  Runtime
        # DB/WAL/SHM files remain provenance, not accepted truth sources.
        "frozen_standalone_sqlite": frozen_sqlite,
        "untrusted_summary_files_not_used_for_acceptance": sorted(
            UNTRUSTED_SUMMARY_FILES
        ),
    }
    return {
        **body,
        "artifact_freeze_sha256": sha256_value(body),
    }


def evaluate_run(run_dir: Path, *, write_outputs: bool = False) -> Dict[str, Any]:
    run_dir = Path(run_dir).resolve()
    require(run_dir.is_dir(), "run directory missing")
    if write_outputs:
        freeze_standalone_databases(run_dir)
    require(
        (run_dir / FROZEN_SQLITE_DIR).is_dir(),
        "formal standalone SQLite freeze is missing",
    )
    shared_view = load_json(run_dir / "shared-startup-view.json")
    launch_a = load_json(run_dir / "world-a" / "blind-launch-receipt.json")
    launch_b = load_json(run_dir / "world-b" / "blind-launch-receipt.json")
    require(
        launch_a["visible_surface"]["view_bytes"]
        == launch_b["visible_surface"]["view_bytes"]
        == canonical_bytes(shared_view).decode("utf-8"),
        "startup view bytes differ across actual blind arms",
    )

    arm_a = load_json(run_dir / "world-a" / "arm-result.json")
    arm_b = load_json(run_dir / "world-b" / "arm-result.json")
    prefix_a = {
        "startup_view": shared_view,
        "transcript": arm_a["transcript"][:3],
    }
    prefix_b = {
        "startup_view": shared_view,
        "transcript": arm_b["transcript"][:3],
    }
    require(
        canonical_bytes(prefix_a) == canonical_bytes(prefix_b),
        "pre-readback paired prefix differs",
    )
    frozen_prefix = load_json(run_dir / "shared-pre-readback-prefix.json")
    require(
        frozen_prefix == prefix_a,
        "frozen shared prefix differs from recomputed raw prefix",
    )
    require(
        _first_difference(arm_a["transcript"], arm_b["transcript"]) == 3,
        "first public difference is not exact Target status response",
    )

    world_results = {
        "world-a": validate_world(run_dir, "world-a", shared_view),
        "world-b": validate_world(run_dir, "world-b", shared_view),
    }
    require(
        world_results["world-a"]["target_public_key_hex"]
        != world_results["world-b"]["target_public_key_hex"],
        "paired worlds unexpectedly share one Target endpoint key",
    )
    freeze = build_freeze(run_dir, world_results)
    acceptance = {
        "schema": "WAVE016_ROOT_INDEPENDENT_ACCEPTANCE_V1",
        "status": "ACCEPTED_SCOPED_LOCAL_DIGITAL_E3_PAIR",
        "evaluator_version": EVALUATOR_VERSION,
        "run_id": run_dir.name,
        "artifact_freeze_sha256": freeze["artifact_freeze_sha256"],
        "decision_source": (
            "RAW_ARM_AND_BROKER_ARTIFACTS_PLUS_ED25519_PLUS_SQLITE; "
            "PAIR_RUNTIME_EVALUATION_NOT_TRUSTED"
        ),
        "checks": {
            "actual_spawn_startup_view_bytes_equal": True,
            "pre_readback_prefix_raw_equal": True,
            "first_difference_exact_target_status": True,
            "target_endpoint_keys_bound_and_signatures_valid": True,
            "world_a_existing_commit_no_replay": True,
            "world_b_signed_negative_then_freshness_then_retry": True,
            "world_b_decoy_backed_by_real_historical_commit": True,
            "world_a_exact_target_mutation_count": 1,
            "world_b_exact_target_mutation_count": 1,
            "ledger_receipt_readback_hmac_and_sqlite_binding_valid": True,
            "standalone_delete_journal_sqlite_truth_bound": True,
        },
        "worlds": world_results,
        "accepted_claim": (
            "Under the frozen local digital world, the mature composition "
            "distinguishes ACK-lost committed from ACK-lost not-committed and "
            "selects no-replay versus freshness-gated safe retry."
        ),
        "not_proved": [
            "physical electrical Effect or 46 physical samples",
            "legal Authority or independent Principal identity",
            "external PKI binding of the evaluator-private endpoint key",
            "resistance to a malicious same-user artifact rewriter",
            "production reliability or cross-domain generality",
            "relation formation, protocol-wide validity, or formal promotion",
        ],
    }
    if write_outputs:
        (run_dir / "ROOT-FREEZE.json").write_text(
            json.dumps(freeze, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "ROOT-INDEPENDENT-ACCEPTANCE.json").write_text(
            json.dumps(acceptance, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )
    return acceptance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate_run(args.run_dir, write_outputs=args.write)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AcceptanceError",
    "canonical_bytes",
    "evaluate_run",
    "validate_capability_freshness",
    "validate_sequence",
    "validate_status_envelope",
    "verify_target_signature",
]
