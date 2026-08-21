#!/usr/bin/env python3
"""Independent evaluator for the Wave 019 local-synthetic E2 suite.

No runtime module or runtime summary is imported.  Acceptance is rebuilt from
raw launch/transcript artifacts, owner Ed25519 records, standalone owner
SQLite files and the mature Target ledger's HMAC-bound rows.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


EVALUATOR_VERSION = "WAVE019_ROOT_EVALUATOR_V1"
TARGET_ID = "VenueV:CircuitC7"
ARM_ID = "MATURE-WORKFLOW-HITL-FORMATION"
CASES = ("baseline", "remove", "refuse")
ROLES = ("O_Q", "O_V", "O_R", "O_S", "O_P")
RESPONSE_ROLES = ("O_Q", "O_V", "O_R", "O_S")
ROLE_FACTS = {
    "O_Q": ("PURPOSE_TOKEN",),
    "O_V": ("C7_SHORT_DELEGATION",),
    "O_R": ("RESOURCE_COMMITMENT", "RESOURCE_RESERVATION"),
    "O_S": ("SAFETY_APPROVAL",),
    "O_P": ("PAYMENT_FINALITY",),
}
ROLE_PRINCIPALS = {
    "O_Q": "PRINCIPAL_REQUESTER_Q",
    "O_V": "PRINCIPAL_VENUE_V",
    "O_R": "PRINCIPAL_RESOURCE_R",
    "O_S": "PRINCIPAL_SAFETY_S",
    "O_P": "PRINCIPAL_SETTLEMENT_P",
}
FROZEN_DB_ROOT = "ROOT-FROZEN-SQLITE"
ROOT_OUTPUTS = {"ROOT-FREEZE.json", "ROOT-INDEPENDENT-ACCEPTANCE.json"}


class AcceptanceError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AcceptanceError(message)


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
        raise AcceptanceError("non-canonical value") from exc


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


def load_json(path: Path) -> Any:
    require(path.is_file(), "missing artifact: %s" % path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AcceptanceError("invalid JSON artifact: %s" % path) from exc


def verify_owner_record(
    record: Mapping[str, Any],
    expected_public_key_hex: str,
) -> None:
    require(
        record.get("owner_public_key_hex") == expected_public_key_hex,
        "wrong owner/controller-forged record",
    )
    try:
        key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(expected_public_key_hex)
        )
        key.verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(_without(record, "signature_hex")),
        )
    except Exception as exc:
        raise AcceptanceError("owner signature invalid") from exc


def scope_from_view(view: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "public_run_id": view["public_run_id"],
        "world_id": view["episode_instance_id"],
        "q_version": view["q_version"],
        "object_id": view["object_id"],
        "target_id": view["target_id"],
        "operation_id": view["operation_id"],
        "purpose": "TEMPORARY_C7_3KW_45MIN",
        "required_power_kw": view["required_power_kw"],
        "required_duration_minutes": view["required_duration_minutes"],
        "deadline_minute": view["deadline_minute"],
    }


def owner_head(
    owner_id: str,
    role: str,
    principal_id: str,
    facts: Sequence[Mapping[str, Any]],
) -> str:
    return sha256_value(
        {
            "owner_id": owner_id,
            "owner_role": role,
            "principal_id": principal_id,
            "facts": sorted(facts, key=lambda item: item["fact_kind"]),
        }
    )


def validate_owner_response(
    response: Mapping[str, Any],
    ready: Mapping[str, Any],
    proposal: Mapping[str, Any],
    expected_owner_head: str,
) -> None:
    verify_owner_record(response, ready["public_key_hex"])
    role = ready["owner_role"]
    require(
        response.get("schema") == "E2_OWNER_PROPOSAL_RESPONSE_V1",
        "wrong owner response schema",
    )
    for field in ("owner_id", "owner_role", "principal_id", "process_id"):
        expected_field = "public_key_hex" if field == "owner_public_key_hex" else field
        require(
            response.get(field) == ready.get(expected_field),
            "wrong-owner response binding: %s" % field,
        )
    proposal_bytes = canonical_bytes(proposal)
    require(
        response.get("proposal_sha256")
        == hashlib.sha256(proposal_bytes).hexdigest(),
        "owner response proposal hash mismatch",
    )
    require(
        response.get("owner_head") == expected_owner_head,
        "stale owner response head",
    )
    frozen_policy = ready["s0_absence"]["frozen_policy"]
    require(
        response.get("policy_head") == sha256_value(frozen_policy),
        "owner response policy head mismatch",
    )
    require(
        response.get("scope_sha256") == proposal["scope_sha256"],
        "wrong-scope owner response",
    )
    require(
        response.get("expiry_minute") == proposal["requested_expiry_minute"],
        "owner response expiry mismatch",
    )
    require(
        response.get("request_nonce")
        == proposal["owner_request_nonces"][role],
        "owner response nonce mismatch",
    )
    require(
        response.get("decision") in {"APPROVE", "COUNTER", "REFUSE", "DEFER"},
        "invalid owner decision",
    )
    require(
        response.get("decision") in frozen_policy["decision_family"],
        "owner response outside pre-run frozen decision family",
    )


def validate_case_sequence(case: str, transcript: Sequence[Mapping[str, Any]]) -> None:
    schemas = [event.get("message", {}).get("schema") for event in transcript]
    expected = {
        "baseline": [
            "E2_BROKER_PROPOSAL_REQUEST_V1",
            "E2_BROKER_PROPOSAL_RESULT_V1",
            "E2_BROKER_MATERIALIZE_REQUEST_V1",
            "E2_BROKER_MATERIALIZE_RESULT_V1",
            "E2_BROKER_TARGET_EXECUTE_REQUEST_V1",
            "E2_BROKER_TARGET_EXECUTE_RESULT_V1",
            "E2_BROKER_ACCEPTANCE_REQUEST_V1",
            "E2_BROKER_ACCEPTANCE_RESULT_V1",
        ],
        "remove": [],
        "refuse": [
            "E2_BROKER_PROPOSAL_REQUEST_V1",
            "E2_BROKER_PROPOSAL_RESULT_V1",
        ],
    }[case]
    require(
        schemas == expected,
        "%s sequence invalid; formation-before-execute or forbidden descendants"
        % case,
    )
    for index, event in enumerate(transcript):
        require(
            event.get("direction")
            == ("ARM_TO_BROKER" if index % 2 == 0 else "BROKER_TO_ARM"),
            "transcript direction invalid",
        )


def _db_rows(connection: sqlite3.Connection, table: str, order: str) -> list:
    return [
        dict(row)
        for row in connection.execute(
            "SELECT * FROM %s ORDER BY %s" % (table, order)
        )
    ]


def owner_db_snapshot(path: Path) -> Dict[str, Any]:
    assert_standalone(path)
    connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            "metadata": _db_rows(connection, "metadata", "singleton"),
            "facts": _db_rows(connection, "facts", "fact_kind"),
            "events": _db_rows(connection, "events", "event_index"),
        }
        return {"tables": tables, "snapshot_sha256": sha256_value(tables)}
    finally:
        connection.close()


def target_db_snapshot(path: Path) -> Dict[str, Any]:
    assert_standalone(path)
    connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        tables = {
            "metadata": _db_rows(connection, "metadata", "singleton"),
            "targets": _db_rows(connection, "targets", "target_id"),
            "capabilities": _db_rows(connection, "capabilities", "capability_id"),
            "requests": _db_rows(connection, "requests", "request_id"),
            "receipts": _db_rows(connection, "receipts", "receipt_id"),
            "commit_events": _db_rows(connection, "commit_events", "commit_id"),
            "readbacks": _db_rows(connection, "readbacks", "readback_id"),
        }
        return {"tables": tables, "snapshot_sha256": sha256_value(tables)}
    finally:
        connection.close()


def assert_standalone(path: Path) -> None:
    require(path.is_file(), "frozen SQLite missing")
    require(
        not Path(str(path) + "-wal").exists()
        and not Path(str(path) + "-shm").exists(),
        "frozen SQLite has WAL/SHM dependency",
    )
    connection = sqlite3.connect("file:%s?mode=ro" % path, uri=True)
    try:
        require(
            connection.execute("PRAGMA journal_mode").fetchone()[0].lower()
            == "delete",
            "frozen SQLite is not DELETE journal",
        )
        require(
            connection.execute("PRAGMA quick_check").fetchone()[0] == "ok",
            "frozen SQLite quick_check failed",
        )
    finally:
        connection.close()


def freeze_databases(suite_dir: Path) -> None:
    sources = sorted(
        list(suite_dir.glob("*/target-ledger.sqlite3"))
        + list(suite_dir.glob("*/owners/*.sqlite3"))
    )
    require(len(sources) == 18, "expected 18 runtime databases")
    frozen_root = suite_dir / FROZEN_DB_ROOT
    for source in sources:
        relative = source.relative_to(suite_dir)
        destination = frozen_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(str(destination) + ".tmp")
        for candidate in (
            temporary,
            Path(str(temporary) + "-wal"),
            Path(str(temporary) + "-shm"),
        ):
            if candidate.exists():
                candidate.unlink()
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
        for companion in (
            Path(str(temporary) + "-wal"),
            Path(str(temporary) + "-shm"),
        ):
            if companion.exists():
                companion.unlink()
        os.replace(temporary, destination)
        assert_standalone(destination)


def frozen_db(suite_dir: Path, relative: str) -> Path:
    return suite_dir / FROZEN_DB_ROOT / relative


def validate_owner_db(
    suite_dir: Path,
    case: str,
    role: str,
    ready: Mapping[str, Any],
    audit: Mapping[str, Any],
) -> Dict[str, Any]:
    snapshot = owner_db_snapshot(
        frozen_db(suite_dir, "%s/owners/%s.sqlite3" % (case, role.lower()))
    )
    tables = snapshot["tables"]
    require(len(tables["metadata"]) == 1, "owner metadata not singular")
    metadata = tables["metadata"][0]
    require(metadata["owner_id"] == ready["owner_id"], "owner DB identity mismatch")
    require(metadata["owner_role"] == role, "owner DB role mismatch")
    require(
        metadata["principal_id"] == ROLE_PRINCIPALS[role],
        "owner DB principal mismatch",
    )
    require(
        metadata["public_key_hex"] == ready["public_key_hex"],
        "owner DB key mismatch",
    )
    facts = [
        {
            "fact_kind": row["fact_kind"],
            "scope_sha256": row["scope_sha256"],
            "proposal_sha256": row["proposal_sha256"],
            "expiry_minute": row["expiry_minute"],
            "value": json.loads(row["value_json"]),
        }
        for row in tables["facts"]
    ]
    require(facts == audit["facts"], "owner audit differs from frozen DB")
    require(
        len(tables["events"]) == audit["event_count"],
        "owner event count differs from frozen DB",
    )
    require(
        owner_head(
            ready["owner_id"],
            role,
            ready["principal_id"],
            facts,
        )
        == audit["final_head"],
        "owner final head mismatch",
    )
    return {
        "facts": facts,
        "events": tables["events"],
        "snapshot_sha256": snapshot["snapshot_sha256"],
    }


def _verify_ledger_record(
    record: Mapping[str, Any],
    *,
    hash_field: str,
    auth_field: str,
    key: bytes,
) -> None:
    require(
        record[hash_field] == sha256_value(_without(record, hash_field, auth_field)),
        "Target ledger record hash invalid",
    )
    expected = hmac.new(
        key,
        canonical_bytes(_without(record, auth_field)),
        hashlib.sha256,
    ).hexdigest()
    require(hmac.compare_digest(record[auth_field], expected), "Target HMAC invalid")


def validate_occurrence_coordinates(
    occurrence: Mapping[str, Any],
    *,
    expected: Mapping[str, Any] | None = None,
) -> None:
    require(
        occurrence.get("object_id") == TARGET_ID
        and occurrence.get("target_id") == TARGET_ID,
        "Target occurrence wrong object",
    )
    require(
        occurrence.get("duration_minutes") == 45,
        "Target occurrence duration gap",
    )
    start = occurrence.get("effect_start_minute")
    deadline = occurrence.get("deadline_minute")
    require(
        isinstance(start, int)
        and isinstance(deadline, int)
        and occurrence.get("effect_end_minute") == start + 45
        and start + 45 <= deadline,
        "Target occurrence duration/deadline invalid",
    )
    require(
        occurrence.get("other_circuits_energized") == [],
        "other circuit energized",
    )
    required_power = occurrence.get("required_power_kw")
    tolerance_percent = occurrence.get("power_tolerance_percent")
    require(
        required_power == 3.0 and tolerance_percent == 5,
        "Target occurrence tolerance coordinates invalid",
    )
    calculated_min = required_power * (1 - tolerance_percent / 100)
    calculated_max = required_power * (1 + tolerance_percent / 100)
    require(
        abs(occurrence.get("power_min_kw") - calculated_min) < 1e-12
        and abs(occurrence.get("power_max_kw") - calculated_max) < 1e-12,
        "Target occurrence power bounds do not implement tolerance",
    )
    samples = occurrence.get("samples")
    require(isinstance(samples, list) and len(samples) == 46, "synthetic sample count not 46")
    require(
        [item.get("offset_minute") for item in samples] == list(range(46)),
        "synthetic sample offsets not continuous",
    )
    require(
        all(item.get("target_id") == TARGET_ID for item in samples),
        "synthetic sample wrong target",
    )
    require(
        all(item.get("other_circuits_energized") == [] for item in samples),
        "synthetic sample other circuit energized",
    )
    require(
        all(
            item.get("observed_at_minute") == start + item["offset_minute"]
            and calculated_min <= item.get("power_kw") <= calculated_max
            and item.get("safety_ok") is True
            and item.get("noise_ok") is True
            and item.get("source") == "LOCAL_SYNTHETIC"
            for item in samples
        ),
        "unsafe/noisy/out-of-tolerance synthetic sample",
    )
    if expected is not None:
        for field in (
            "public_run_id",
            "world_id",
            "q_version",
            "object_id",
            "target_id",
            "operation_id",
            "proposal_sha256",
        ):
            require(
                occurrence.get(field) == expected.get(field),
                "Target occurrence exact coordinate mismatch: %s" % field,
            )
        require(
            deadline == expected.get("deadline_minute"),
            "Target occurrence deadline differs from Q",
        )


def validate_target_db(
    suite_dir: Path,
    case: str,
    *,
    expect_mutation: bool,
) -> Dict[str, Any]:
    snapshot = target_db_snapshot(
        frozen_db(suite_dir, "%s/target-ledger.sqlite3" % case)
    )
    tables = snapshot["tables"]
    require(len(tables["targets"]) == 1, "Target state not singular")
    target = tables["targets"][0]
    expected_count = 1 if expect_mutation else 0
    require(
        len(tables["commit_events"]) == expected_count,
        "duplicate or missing Target mutation",
    )
    require(
        len(tables["receipts"]) == expected_count
        and len(tables["requests"]) == expected_count
        and len(tables["readbacks"]) == expected_count,
        "Target descendants count mismatch",
    )
    if not expect_mutation:
        require(
            target["version"] == 0
            and json.loads(target["state_json"]) == {"occurrences": []},
            "negative run Target changed",
        )
        return {
            "mutation_count": 0,
            "snapshot_sha256": snapshot["snapshot_sha256"],
        }
    key = bytes.fromhex(tables["metadata"][0]["authentication_key_hex"])
    receipt = json.loads(tables["receipts"][0]["receipt_json"])
    readback = json.loads(tables["readbacks"][0]["readback_json"])
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
    require(receipt["decision"] == "COMMITTED", "Target receipt not committed")
    require(receipt["mutation_applied"] is True, "Target receipt non-mutating")
    require(receipt["target_id"] == TARGET_ID, "Target receipt wrong object")
    require(receipt["actor_id"] == ARM_ID, "Target receipt wrong actor")
    state = json.loads(target["state_json"])
    require(target["version"] == 1, "Target version not one")
    require(len(state["occurrences"]) == 1, "Target occurrence count not one")
    occurrence = state["occurrences"][0]
    validate_occurrence_coordinates(occurrence)
    require(
        readback["attached_to_receipt_commit"] is True
        and readback["observed_state"] == state,
        "Target readback detached",
    )
    return {
        "mutation_count": 1,
        "receipt": receipt,
        "readback": readback,
        "occurrence": occurrence,
        "snapshot_sha256": snapshot["snapshot_sha256"],
    }


def validate_s0_and_independence(
    view: Mapping[str, Any],
    ready: Mapping[str, Any],
) -> Dict[str, str]:
    require(set(ready) == set(ROLES), "owner ready set incomplete")
    require(len({item["process_id"] for item in ready.values()}) == 5, "owner PIDs not independent")
    require(len({item["public_key_hex"] for item in ready.values()}) == 5, "owner keys not independent")
    require(len({item["principal_id"] for item in ready.values()}) == 5, "owner principals not independent")
    heads = {}
    scope = scope_from_view(view)
    for role in ROLES:
        item = ready[role]
        require(item["owner_role"] == role, "owner role mismatch")
        require(item["principal_id"] == ROLE_PRINCIPALS[role], "principal mismatch")
        s0 = item["s0_absence"]
        verify_owner_record(s0, item["public_key_hex"])
        require(s0["status"] == "ABSENT", "S0 fact not absent")
        require(s0["scope"] == scope, "S0 wrong scope")
        require(s0["scope_sha256"] == sha256_value(scope), "S0 scope hash mismatch")
        policy = s0.get("frozen_policy")
        require(isinstance(policy, Mapping), "S0 frozen owner policy missing")
        require(
            s0.get("policy_head") == sha256_value(policy),
            "S0 owner policy head mismatch",
        )
        require(
            policy.get("budget")
            == {"max_power_kw": 3.0, "max_duration_minutes": 45}
            and policy.get("horizon_minute") == 90
            and policy.get("exogenous_schedule")
            == {
                "response_available": True,
                "materialize_after_response_only": True,
                "resource_window_start_minute": 5,
            },
            "S0 owner policy budget/horizon/schedule not frozen",
        )
        require(
            s0["absent_fact_kinds"] == list(ROLE_FACTS[role]),
            "S0 missing exact absence",
        )
        expected_head = owner_head(
            item["owner_id"],
            role,
            item["principal_id"],
            [],
        )
        require(s0["owner_head"] == expected_head, "S0 head not empty-state head")
        heads[role] = expected_head
    return heads


def validate_case(suite_dir: Path, case: str) -> Dict[str, Any]:
    case_dir = suite_dir / case
    view = load_json(case_dir / "view.json")
    ready = load_json(case_dir / "owner-ready.json")
    launch = load_json(case_dir / "arm-launch.json")
    arm = load_json(case_dir / "arm-result.json")
    broker = load_json(case_dir / "broker-result.json")
    audits = load_json(case_dir / "owner-audits.json")
    require(launch["process_start_method"] == "spawn", "arm not real spawn")
    require(launch["exit_code"] == 0, "arm failed")
    require(launch["visible_surface"]["view"] == view, "arm startup view mismatch")
    require(
        launch["visible_surface"]["view_bytes"]
        == canonical_bytes(view).decode("utf-8"),
        "arm startup bytes mismatch",
    )
    require(launch["worker_result"] == arm, "launch/arm result mismatch")
    startup_raw = canonical_bytes(launch["visible_surface"])
    for forbidden in (
        "APPROVE",
        "COUNTER",
        "REFUSE",
        "DEFER",
        "BASELINE_COUNTER_SUCCESS",
        "OWNER_REFUSE",
    ):
        require(
            forbidden.encode("utf-8") not in startup_raw,
            "future owner decision leaked into startup",
        )
    require(
        broker["controller_signed_owner_fact_count"] == 0,
        "controller signed owner facts",
    )
    require(arm["transcript"] == broker["transcript"], "arm/broker transcript mismatch")
    require(
        sha256_value(arm["transcript"]) == arm["transcript_sha256"]
        and sha256_value(broker["transcript"]) == broker["transcript_sha256"],
        "transcript hash invalid",
    )
    validate_case_sequence(case, arm["transcript"])
    s0_heads = validate_s0_and_independence(view, ready)
    owner_dbs = {
        role: validate_owner_db(suite_dir, case, role, ready[role], audits[role])
        for role in ROLES
    }

    if case == "remove":
        require(
            "FORMATION_PROPOSE" not in view["broker_surface"]["capabilities"],
            "remove run still exposes formation operator",
        )
        require(arm["proposal_sent"] is False, "remove run sent proposal")
        require(arm["target_submit_sent"] is False, "remove run submitted Target")
        require(
            arm["disposition"] == "BOUNDED_UNAVAILABLE_NO_FORMATION_OPERATOR",
            "remove run wrong disposition",
        )
        require(
            all(not owner_dbs[role]["facts"] for role in ROLES),
            "remove run formed owner descendants",
        )
        target = validate_target_db(suite_dir, case, expect_mutation=False)
        return {
            "disposition": arm["disposition"],
            "target_mutation_count": 0,
            "proposal_descendant_count": 0,
            "owner_independent_count": 5,
            "owner_db_snapshot_sha256": {
                role: owner_dbs[role]["snapshot_sha256"] for role in ROLES
            },
            "target_db_snapshot_sha256": target["snapshot_sha256"],
        }

    proposal_request = arm["transcript"][0]["message"]
    proposal_result = arm["transcript"][1]["message"]
    proposal_bytes = proposal_request["proposal_bytes"]
    proposal = json.loads(proposal_bytes)
    require(
        canonical_bytes(proposal).decode("utf-8") == proposal_bytes,
        "proposal bytes not exact canonical bytes",
    )
    proposal_hash = hashlib.sha256(proposal_bytes.encode("utf-8")).hexdigest()
    require(
        proposal_request["proposal_sha256"] == proposal_hash
        and arm["proposal_bytes"] == proposal_bytes
        and arm["proposal"] == proposal,
        "proposal artifact/hash mismatch",
    )
    responses = proposal_result["owner_responses"]
    require({item["owner_role"] for item in responses} == set(RESPONSE_ROLES), "response roles incomplete")
    for response in responses:
        role = response["owner_role"]
        validate_owner_response(response, ready[role], proposal, s0_heads[role])

    if case == "refuse":
        decisions = {item["owner_role"]: item["decision"] for item in responses}
        require(decisions["O_R"] == "REFUSE", "refuse run lacks owner REFUSE")
        require(
            arm["disposition"] == "BOUNDED_REFUSAL_OWNER_SIGNED",
            "signed refusal misclassified as success/Unknown",
        )
        require(arm["target_submit_sent"] is False, "refuse run Target submit")
        require(
            all(not owner_dbs[role]["facts"] for role in ROLES),
            "refuse run formed owner facts",
        )
        target = validate_target_db(suite_dir, case, expect_mutation=False)
        return {
            "disposition": arm["disposition"],
            "target_mutation_count": 0,
            "signed_refusal_role": "O_R",
            "owner_independent_count": 5,
            "owner_db_snapshot_sha256": {
                role: owner_dbs[role]["snapshot_sha256"] for role in ROLES
            },
            "target_db_snapshot_sha256": target["snapshot_sha256"],
        }

    decisions = {item["owner_role"]: item["decision"] for item in responses}
    require(
        decisions
        == {"O_Q": "APPROVE", "O_V": "APPROVE", "O_R": "COUNTER", "O_S": "APPROVE"},
        "baseline response family lacks exact COUNTER distinction",
    )
    counter = next(item for item in responses if item["owner_role"] == "O_R")
    require(
        counter["counter"]
        == {
            "effective_expiry_minute": 85,
            "resource_window_start_minute": 5,
            "resource_window_end_minute": 50,
        },
        "O_R counter terms invalid",
    )
    materialize_request = arm["transcript"][2]["message"]
    materialize_result = arm["transcript"][3]["message"]
    require(
        materialize_request["accepted_counter_roles"] == ["O_R"],
        "COUNTER was not explicitly accepted",
    )
    acts = materialize_result["owner_acts"]
    require({item["owner_role"] for item in acts} == set(RESPONSE_ROLES), "owner act set incomplete")
    act_by_role = {item["owner_role"]: item for item in acts}
    for role, act in act_by_role.items():
        verify_owner_record(act, ready[role]["public_key_hex"])
        response = next(item for item in responses if item["owner_role"] == role)
        require(act["proposal_sha256"] == proposal_hash, "act proposal mismatch")
        require(act["response_sha256"] == sha256_value(response), "act response mismatch")
        require(act["scope_sha256"] == proposal["scope_sha256"], "act scope mismatch")
        require(act["pre_head"] == s0_heads[role], "act did not first-form from S0")
        require(
            act["created_fact_kinds"] == list(ROLE_FACTS[role]),
            "act created wrong facts",
        )
        expected_expiry = 85 if role == "O_R" else 90
        require(act["expiry_minute"] == expected_expiry, "act expiry mismatch")
        formation_facts = [
            item
            for item in owner_dbs[role]["facts"]
            if item["fact_kind"] in ROLE_FACTS[role]
        ]
        require(
            owner_head(
                ready[role]["owner_id"],
                role,
                ready[role]["principal_id"],
                formation_facts,
            )
            == act["post_head"],
            "act post-head does not match formed facts",
        )

    execute_request = arm["transcript"][4]["message"]
    execute_result = arm["transcript"][5]["message"]
    require(
        execute_request["owner_act_sha256"]
        == {role: sha256_value(act_by_role[role]) for role in RESPONSE_ROLES},
        "Target execute did not bind exact owner acts",
    )
    revalidations = execute_result["commit_revalidations"]
    require({item["owner_role"] for item in revalidations} == set(RESPONSE_ROLES), "revalidation set incomplete")
    for item in revalidations:
        role = item["owner_role"]
        verify_owner_record(item, ready[role]["public_key_hex"])
        require(item["status"] == "CURRENT", "stale owner fact consumed")
        require(item["owner_head"] == act_by_role[role]["post_head"], "revalidation head mismatch")
        require(item["proposal_sha256"] == proposal_hash, "revalidation proposal mismatch")
        require(item["scope_sha256"] == proposal["scope_sha256"], "revalidation scope mismatch")
    target = validate_target_db(suite_dir, case, expect_mutation=True)
    require(execute_result["receipt"] == target["receipt"], "runtime/DB receipt mismatch")
    require(execute_result["readback"] == target["readback"], "runtime/DB readback mismatch")
    require(
        target["occurrence"]["proposal_sha256"] == proposal_hash,
        "Target occurrence detached from formation",
    )
    validate_occurrence_coordinates(
        target["occurrence"],
        expected={
            "public_run_id": view["public_run_id"],
            "world_id": view["episode_instance_id"],
            "q_version": view["q_version"],
            "object_id": view["object_id"],
            "target_id": view["target_id"],
            "operation_id": view["operation_id"],
            "proposal_sha256": proposal_hash,
            "deadline_minute": view["deadline_minute"],
        },
    )
    accept_result = arm["transcript"][7]["message"]
    acceptances = accept_result["acceptances"]
    require({item["owner_role"] for item in acceptances} == {"O_Q", "O_V"}, "dual Acceptance missing")
    for item in acceptances:
        role = item["owner_role"]
        verify_owner_record(item, ready[role]["public_key_hex"])
        require(
            item["status"] == "ACCEPTED"
            and item["receipt_sha256"] == target["receipt"]["receipt_sha256"]
            and item["readback_sha256"] == target["readback"]["readback_sha256"],
            "Acceptance detached from exact Target readback",
        )
    finality = accept_result["finality"]
    verify_owner_record(finality, ready["O_P"]["public_key_hex"])
    require(
        finality["status"] == "FINAL"
        and finality["acceptance_sha256"] == sha256_value(acceptances)
        and finality["receipt_sha256"] == target["receipt"]["receipt_sha256"],
        "O_P finality detached",
    )
    require(arm["disposition"] == "SUCCEEDED_AFTER_FORMATION", "baseline disposition wrong")
    return {
        "disposition": arm["disposition"],
        "target_mutation_count": 1,
        "counter_role": "O_R",
        "owner_independent_count": 5,
        "owner_db_snapshot_sha256": {
            role: owner_dbs[role]["snapshot_sha256"] for role in ROLES
        },
        "target_db_snapshot_sha256": target["snapshot_sha256"],
    }


def build_freeze(suite_dir: Path) -> Dict[str, Any]:
    raw_hashes = {}
    for path in sorted(suite_dir.rglob("*.json")):
        if path.name in ROOT_OUTPUTS:
            continue
        raw_hashes[str(path.relative_to(suite_dir))] = sha256_file(path)
    frozen = {}
    paths = sorted((suite_dir / FROZEN_DB_ROOT).rglob("*.sqlite3"))
    require(len(paths) == 18, "frozen DB set incomplete")
    for path in paths:
        assert_standalone(path)
        relative = str(path.relative_to(suite_dir))
        if "/owners/" in relative:
            logical = owner_db_snapshot(path)["snapshot_sha256"]
        else:
            logical = target_db_snapshot(path)["snapshot_sha256"]
        frozen[relative] = {
            "physical_file_sha256": sha256_file(path),
            "logical_snapshot_sha256": logical,
            "journal_mode": "delete",
            "wal_shm_absent": True,
        }
    body = {
        "schema": "WAVE019_ROOT_FREEZE_V1",
        "evaluator_version": EVALUATOR_VERSION,
        "suite_id": suite_dir.name,
        "raw_json_sha256": raw_hashes,
        "frozen_standalone_sqlite": frozen,
        "runtime_summary_not_used": ["suite-result.json"],
    }
    return {**body, "artifact_freeze_sha256": sha256_value(body)}


def evaluate_suite(
    suite_dir: Path,
    *,
    write_outputs: bool = False,
) -> Dict[str, Any]:
    suite_dir = Path(suite_dir).resolve()
    require(suite_dir.is_dir(), "suite directory missing")
    if write_outputs:
        freeze_databases(suite_dir)
    require((suite_dir / FROZEN_DB_ROOT).is_dir(), "standalone DB freeze missing")
    views = load_json(suite_dir / "shared-views.json")
    require(
        views["BASELINE_COUNTER_SUCCESS"] == views["OWNER_REFUSE"],
        "baseline/refuse startup views reveal future owner decision",
    )
    baseline_view = views["BASELINE_COUNTER_SUCCESS"]
    remove_view = views["REMOVE_FORMATION_OPERATOR"]
    baseline_projection = dict(baseline_view)
    remove_projection = dict(remove_view)
    baseline_projection["broker_surface"] = dict(baseline_view["broker_surface"])
    remove_projection["broker_surface"] = dict(remove_view["broker_surface"])
    baseline_projection["broker_surface"]["capabilities"] = sorted(
        set(baseline_projection["broker_surface"]["capabilities"])
        - {"FORMATION_PROPOSE", "FORMATION_MATERIALIZE"}
    )
    require(
        baseline_projection == remove_projection,
        "remove intervention changed more than formation operator",
    )
    results = {case: validate_case(suite_dir, case) for case in CASES}
    freeze = build_freeze(suite_dir)
    acceptance = {
        "schema": "WAVE019_ROOT_INDEPENDENT_ACCEPTANCE_V1",
        "status": "ACCEPTED_LOCAL_SYNTHETIC_E2_MATURE_WORKFLOW_HITL_SCOPED",
        "evaluator_version": EVALUATOR_VERSION,
        "suite_id": suite_dir.name,
        "artifact_freeze_sha256": freeze["artifact_freeze_sha256"],
        "decision_source": (
            "RAW_SPAWN_TRANSCRIPTS_OWNER_ED25519_STANDALONE_OWNER_STATE_"
            "AND_TARGET_LEDGER; RUNTIME_SUMMARY_NOT_TRUSTED"
        ),
        "cases": results,
        "checks": {
            "plural_independent_owner_process_key_state_principal": True,
            "signed_exact_s0_absence": True,
            "startup_future_decisions_absent": True,
            "exact_proposal_bytes_actually_sent": True,
            "owner_responses_bound_to_hash_head_scope_expiry_nonce": True,
            "owner_native_first_formation": True,
            "counter_distinguished_and_accepted": True,
            "commit_time_current_head_revalidation": True,
            "single_exact_target_digital_occurrence_readback": True,
            "dual_acceptance_and_finality": True,
            "remove_has_no_proposal_descendants_or_target_submit": True,
            "signed_refusal_not_unknown_or_success": True,
            "controller_signed_owner_fact_count_zero": True,
            "all_18_sqlite_truth_files_standalone_delete_journal": True,
        },
        "accepted_claim": (
            "In the frozen local-synthetic E2 world, a mature workflow plus "
            "independent HITL owner acts and purpose-scoped grants can first-form "
            "the missing conditions and then safely produce one exact digital "
            "Target occurrence; removing the operator or receiving signed refusal "
            "prevents all formation/Target descendants."
        ),
        "not_proved": [
            "legal Authority or real owner/principal status",
            "physical electrical Effect or physical telemetry",
            "external identity/PKI binding",
            "hostile same-user tamper resistance",
            "production reliability, generality, or net economic value",
            "protocol-wide relation formation or formal mechanism promotion",
        ],
    }
    if write_outputs:
        (suite_dir / "ROOT-FREEZE.json").write_text(
            json.dumps(freeze, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        (suite_dir / "ROOT-INDEPENDENT-ACCEPTANCE.json").write_text(
            json.dumps(acceptance, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )
    return acceptance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite_dir", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = evaluate_suite(args.suite_dir, write_outputs=args.write)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AcceptanceError",
    "canonical_bytes",
    "evaluate_suite",
    "validate_case_sequence",
    "validate_occurrence_coordinates",
    "validate_owner_response",
    "verify_owner_record",
]
