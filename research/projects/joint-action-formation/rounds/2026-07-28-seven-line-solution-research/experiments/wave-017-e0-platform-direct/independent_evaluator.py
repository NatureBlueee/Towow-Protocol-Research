"""Independent, database-backed evaluator for Wave 017 E0.

This module intentionally does not import ``platform_direct`` or Wave 015.
It reconstructs the accepted claim from frozen JSON, signed records, and the
two standalone SQLite databases.
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
from collections import Counter
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


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
INTERNAL_EVENT_TYPES = {
    "PLATFORM_NATIVE_REQUEST",
    "POLICY_ALLOW",
    "POLICY_DENY",
    "POLICY_DENIED_NO_EFFECT",
    "RESOURCE_LOCKED",
    "TARGET_COMMIT_RECORDED",
    "TARGET_READBACK_RECORDED",
    "ROLE_ACCEPTANCE",
    "NO_EXTERNAL_TRANSFER_FINALITY",
    "PLATFORM_FAILED_NO_EFFECT",
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


def verify_ed25519_record(
    record: Mapping[str, Any],
    *,
    public_key_hex: str,
    digest_field: str,
) -> bool:
    try:
        unsigned = without(record, "signature_hex")
        content = without(unsigned, digest_field)
        if unsigned.get(digest_field) != sha256_value(content):
            return False
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(str(record["signature_hex"])),
            canonical_bytes(unsigned),
        )
        return True
    except Exception:
        return False


def authority_status(
    grant: Mapping[str, Any],
    *,
    venue_public_key_hex: str,
    operation_id: str,
) -> str:
    if not verify_ed25519_record(
        grant,
        public_key_hex=venue_public_key_hex,
        digest_field="grant_sha256",
    ):
        return "INVALID"
    shared = {
        "schema": "VENUE_DIRECT_AUTHORITY_GRANT_V1",
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
    if any(grant.get(key) != value for key, value in shared.items()):
        return "INVALID"
    actions = [
        "SCHEDULE",
        "LOCK_INTERNAL_RESOURCE",
        "EXECUTE_TARGET",
        "ACCEPT_AS_REQUESTER_ROLE",
        "ACCEPT_AS_VENUE_ROLE",
        "FINALIZE_NO_EXTERNAL_TRANSFER",
    ]
    if (
        grant.get("decision") == "ALLOW"
        and grant.get("authority_mode") == "LAWFULLY_UNIFIED_DIRECT"
        and grant.get("granted_actions") == actions
    ):
        return "PRESENT"
    if (
        grant.get("decision") == "DENY"
        and grant.get("authority_mode") == "DIRECT_AUTHORITY_REMOVED"
        and grant.get("granted_actions") == []
    ):
        return "REMOVED"
    return "INVALID"


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


def state_is_exact(state: Mapping[str, Any]) -> bool:
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
        and [sample.get("minute") for sample in samples] == list(range(46))
        and all(
            sample.get("power_kw") == 3.0
            and sample.get("safety_ok") is True
            and sample.get("noise_ok") is True
            for sample in samples
        )
    )


def open_immutable(path: pathlib.Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def verify_target_datastore(
    path: pathlib.Path,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    with open_immutable(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        metadata = connection.execute(
            "SELECT ledger_id, authentication_key_hex FROM metadata"
        ).fetchone()
        target = connection.execute(
            "SELECT * FROM targets WHERE target_id = ?", (TARGET_ID,)
        ).fetchone()
        receipt_rows = list(
            connection.execute("SELECT receipt_json FROM receipts")
        )
        readback_rows = list(
            connection.execute("SELECT readback_json FROM readbacks")
        )
        commits = [
            dict(row)
            for row in connection.execute(
                "SELECT * FROM commit_events ORDER BY commit_id"
            )
        ]
    if metadata is None or target is None:
        return {"accepted": False, "reason": "TARGET_DB_CORE_ROW_MISSING"}

    key = bytes.fromhex(metadata["authentication_key_hex"])
    receipts = [json.loads(row["receipt_json"]) for row in receipt_rows]
    readbacks = [json.loads(row["readback_json"]) for row in readback_rows]

    def receipt_valid(receipt: Mapping[str, Any]) -> bool:
        expected_sha = sha256_value(
            without(receipt, "receipt_sha256", "receipt_auth_hex")
        )
        expected_auth = hmac.new(
            key,
            canonical_bytes(without(receipt, "receipt_auth_hex")),
            hashlib.sha256,
        ).hexdigest()
        return (
            receipt.get("receipt_sha256") == expected_sha
            and hmac.compare_digest(
                str(receipt.get("receipt_auth_hex", "")), expected_auth
            )
        )

    def readback_valid(readback: Mapping[str, Any]) -> bool:
        expected_sha = sha256_value(
            without(readback, "readback_sha256", "readback_auth_hex")
        )
        expected_auth = hmac.new(
            key,
            canonical_bytes(without(readback, "readback_auth_hex")),
            hashlib.sha256,
        ).hexdigest()
        return (
            readback.get("readback_sha256") == expected_sha
            and hmac.compare_digest(
                str(readback.get("readback_auth_hex", "")), expected_auth
            )
        )

    reconstructed_target = {
        "target_id": target["target_id"],
        "state": json.loads(target["state_json"]),
        "state_sha256": target["state_sha256"],
        "version": target["version"],
        "last_commit_id": target["last_commit_id"],
        "last_commit_actor_id": target["last_commit_actor_id"],
        "last_request_sha256": target["last_request_sha256"],
    }
    stored_receipts = artifact["platform_native_service_log"]["target_receipts"]
    stored_readbacks = artifact["platform_native_service_log"]["target_readbacks"]
    checks = {
        "integrity_ok": integrity == "ok",
        "journal_mode_delete": str(journal_mode).lower() == "delete",
        "ledger_id_frozen": (
            metadata["ledger_id"]
            == artifact["frozen_input"]["target_ledger_id"]
        ),
        "authentication_key_frozen": (
            hashlib.sha256(
                bytes.fromhex(metadata["authentication_key_hex"])
            ).hexdigest()
            == artifact["frozen_input"]["target_authentication_key_sha256"]
        ),
        "genesis_frozen_when_unmodified": (
            target["version"] != 0
            or target["last_commit_id"]
            == artifact["frozen_input"]["target_genesis_commit_id"]
        ),
        "target_matches_artifact": (
            reconstructed_target == artifact["target_final_state"]
        ),
        "receipts_match_artifact": receipts == stored_receipts,
        "readbacks_match_artifact": readbacks == stored_readbacks,
        "receipt_authentic": all(receipt_valid(item) for item in receipts),
        "readback_authentic": all(readback_valid(item) for item in readbacks),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "target": reconstructed_target,
        "receipts": receipts,
        "readbacks": readbacks,
        "commits": commits,
    }


def verify_platform_datastore(
    path: pathlib.Path,
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    with open_immutable(path) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        resource_row = connection.execute(
            "SELECT * FROM resources WHERE resource_id = ?", (RESOURCE_ID,)
        ).fetchone()
        event_rows = [
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
    if resource_row is None:
        return {"accepted": False, "reason": "RESOURCE_ROW_MISSING"}

    resource = dict(resource_row)
    external = {counter: 0 for counter in EXTERNAL_EVENT_TYPES.values()}
    event_types_valid = True
    for event in event_rows:
        event_type = event["event_type"]
        if event_type not in INTERNAL_EVENT_TYPES | set(EXTERNAL_EVENT_TYPES):
            event_types_valid = False
        counter = EXTERNAL_EVENT_TYPES.get(event_type)
        if counter is not None:
            external[counter] += 1

    ledger = artifact["platform_native_service_log"]["event_ledger"]
    service = artifact["platform_native_service_log"]
    payload_events: list[tuple[str, str]] = []
    for request in service["requests"]:
        payload_events.append(("PLATFORM_NATIVE_REQUEST", sha256_value(request)))
    for policy in service["policy_checks"]:
        payload_events.append(
            (
                "POLICY_ALLOW"
                if policy["decision"] == "ALLOW"
                else "POLICY_DENY",
                sha256_value(policy),
            )
        )
    for lock in service["resource_locks"]:
        lock_payload = {
            "resource_id": lock["resource_id"],
            "operation_id": lock["operation_id"],
            "decision": lock["decision"],
        }
        payload_events.append(("RESOURCE_LOCKED", sha256_value(lock_payload)))
    for receipt in service["target_receipts"]:
        payload_events.append(
            ("TARGET_COMMIT_RECORDED", sha256_value(receipt))
        )
    for readback in service["target_readbacks"]:
        payload_events.append(
            ("TARGET_READBACK_RECORDED", sha256_value(readback))
        )
    for acceptance in service["acceptances"]:
        payload_events.append(("ROLE_ACCEPTANCE", sha256_value(acceptance)))
    for finality in service["finality"]:
        payload_events.append(
            ("NO_EXTERNAL_TRANSFER_FINALITY", sha256_value(finality))
        )
    response = artifact["arm_transcript"]["native_response"]
    if response["decision"] == "POLICY_DENIED":
        payload_events.append(("POLICY_DENIED_NO_EFFECT", sha256_value(response)))
    elif response["decision"] == "PLATFORM_FAILED":
        payload_events.append(("PLATFORM_FAILED_NO_EFFECT", sha256_value(response)))

    db_payload_events = Counter(
        (event["event_type"], event["payload_sha256"]) for event in event_rows
    )
    checks = {
        "integrity_ok": integrity == "ok",
        "journal_mode_delete": str(journal_mode).lower() == "delete",
        "resource_matches_artifact": resource == artifact["resource_final_state"],
        "event_rows_match_artifact": event_rows == ledger["events"],
        "event_count_matches": len(event_rows) == ledger["event_count"],
        "external_counts_recomputed": (
            external == ledger["external_activity"]
            and external == service["external_activity"]
        ),
        "event_types_registered": event_types_valid,
        "payload_events_complete": (
            db_payload_events == Counter(payload_events)
        ),
    }
    return {
        "accepted": all(checks.values()),
        "checks": checks,
        "resource": resource,
        "events": event_rows,
        "external_activity": external,
    }


def verify_blind_execution(artifact: Mapping[str, Any]) -> dict[str, Any]:
    frozen = artifact["frozen_input"]
    arm = artifact["arm_transcript"]
    visibility = arm["visibility"]
    service_start = artifact["platform_native_service_start"]
    service_log = artifact["platform_native_service_log"]
    blindness = artifact["blindness_receipt"]
    request = arm["native_request"]
    start_payload = {
        "schema": "OPAQUE_NATIVE_ARM_INPUT_V1",
        "run_id": artifact["run_id"],
        "operation_id": artifact["operation_id"],
        "request_id": frozen["request_id"],
        "task": frozen["task"],
        "authority_grant": request["authority_grant"],
        "available_native_interface": frozen["available_native_interface"],
    }
    allowed_fields = sorted(start_payload)
    forbidden_labels = (
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
    inspected_surfaces = {
        "payload": start_payload,
        "arm_transcript": arm,
    }
    serialized_surfaces = canonical_bytes(inspected_surfaces).decode("utf-8")
    private_canary_pattern_absent = (
        re.search(r"private-canary-[0-9a-f]{32}", serialized_surfaces) is None
    )
    event_types = [
        item["event_type"] for item in service_log["event_ledger"]["events"]
    ]
    expected_request = {
        "schema": "PLATFORM_NATIVE_REQUEST_V1",
        "request_id": frozen["request_id"],
        "operation_id": frozen["operation_id"],
        "task": frozen["task"],
        "authority_grant": request["authority_grant"],
    }
    checks = {
        "spawn_start_method": (
            visibility.get("start_method") == "spawn"
            and service_start.get("start_method") == "spawn"
            and blindness.get("spawn_start_method") == "spawn"
        ),
        "distinct_processes": (
            arm.get("process_id") == blindness.get("arm_pid")
            and service_log.get("process_id") == blindness.get("service_pid")
            and service_start.get("process_id") == blindness.get("service_pid")
            and blindness.get("arm_pid") != blindness.get("service_pid")
            and blindness.get("arm_pid") != blindness.get("controller_pid")
            and blindness.get("service_pid") != blindness.get("controller_pid")
        ),
        "visible_schema_exact": (
            visibility.get("visible_fields") == allowed_fields
            and visibility.get("start_payload_sha256")
            == sha256_value(start_payload)
            and set(visibility)
            == {
                "schema",
                "process_id",
                "start_method",
                "process_name",
                "argv",
                "cwd",
                "cwd_entries",
                "environment",
                "visible_fields",
                "start_payload_sha256",
            }
            and set(service_start)
            == {
                "process_id",
                "start_method",
                "argv",
                "cwd",
                "environment",
                "public_key_hex",
            }
        ),
        "native_request_exact": request == expected_request,
        "same_opaque_pair_run_id": artifact["run_id"] == frozen["pair_id"],
        "opaque_process_surface": (
            visibility.get("process_name") == "opaque-native-worker"
            and visibility.get("argv") == ["opaque-native-worker"]
            and visibility.get("cwd_entries") == []
            and pathlib.Path(str(visibility.get("cwd"))).name.startswith(
                "opaque-worker-"
            )
        ),
        "child_environments_sanitized": (
            visibility.get("environment") == SANITIZED_CHILD_ENVIRONMENT
            and service_start.get("environment")
            == SANITIZED_CHILD_ENVIRONMENT
            and blindness.get("sanitized_child_environment")
            == SANITIZED_CHILD_ENVIRONMENT
            and blindness.get("child_environments_exact") is True
        ),
        "private_canary_absent": (
            blindness.get("private_canary_absent") is True
            and private_canary_pattern_absent
        ),
        "private_fields_absent": (
            blindness.get("private_fields_absent_from_payload") is True
            and not {
                "private_world_reveal",
                "expected_outcome",
                "counterfactual_arm",
                "private_canary",
            }
            & set(visibility.get("visible_fields", []))
        ),
        "semantic_case_label_absent": (
            blindness.get("semantic_case_label_present") is False
            and not any(
                label.casefold() in serialized_surfaces.casefold()
                for label in forbidden_labels
            )
        ),
        "one_actual_native_call": (
            arm.get("platform_native_call_count") == 1
            and len(service_log.get("requests", [])) == 1
            and event_types.count("PLATFORM_NATIVE_REQUEST") == 1
        ),
    }
    return {"accepted": all(checks.values()), "checks": checks}


def audit_run(artifact_path: pathlib.Path) -> dict[str, Any]:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    frozen = artifact["frozen_input"]
    frozen_valid = frozen.get("frozen_input_sha256") == sha256_value(
        without(frozen, "frozen_input_sha256")
    )
    artifact_hash_valid = artifact.get("artifact_sha256") == sha256_value(
        without(artifact, "artifact_sha256")
    )
    task_valid = (
        artifact["task"] == exact_task()
        and artifact["task"] == frozen["task"]
        and artifact["task_sha256"] == sha256_value(artifact["task"])
    )
    db_meta = artifact["database_artifacts"]
    target_path = artifact_path.parent / db_meta["target_ledger_file"]
    platform_path = artifact_path.parent / db_meta["platform_native_file"]
    db_hashes_valid = (
        target_path.is_file()
        and platform_path.is_file()
        and file_sha256(target_path) == db_meta["target_ledger_sha256"]
        and file_sha256(platform_path) == db_meta["platform_native_sha256"]
    )
    target_audit = verify_target_datastore(target_path, artifact)
    platform_audit = verify_platform_datastore(platform_path, artifact)
    blind_execution = verify_blind_execution(artifact)

    arm = artifact["arm_transcript"]
    request = arm["native_request"]
    response = arm["native_response"]
    grant = request["authority_grant"]
    signed_authority_status = authority_status(
        grant,
        venue_public_key_hex=frozen["venue_authority_public_key_hex"],
        operation_id=frozen["operation_id"],
    )
    common_request_frozen = (
        request["operation_id"] == frozen["operation_id"]
        and request["request_id"] == frozen["request_id"]
        and request["task"] == frozen["task"]
    )
    service_public_key = artifact["platform_native_service_start"][
        "public_key_hex"
    ]
    service_key_frozen = (
        service_public_key == frozen["platform_service_public_key_hex"]
    )
    target_receipts = target_audit.get("receipts", [])
    target_readbacks = target_audit.get("readbacks", [])
    commit_events = target_audit.get("commits", [])
    resource = platform_audit.get("resource", {})
    external = platform_audit.get("external_activity", {})
    external_zero = external == {
        "discovery_calls": 0,
        "relation_events": 0,
        "delegation_events": 0,
        "external_transfer_count": 0,
    }

    acceptances = artifact["platform_native_service_log"]["acceptances"]
    receipt = target_receipts[0] if len(target_receipts) == 1 else {}
    readback = target_readbacks[0] if len(target_readbacks) == 1 else {}
    acceptance_valid = (
        len(acceptances) == 2
        and {item.get("role") for item in acceptances}
        == {"REQUESTER_ROLE", "VENUE_ROLE"}
        and all(
            verify_ed25519_record(
                item,
                public_key_hex=service_public_key,
                digest_field="acceptance_sha256",
            )
            and item.get("target_commit_id") == receipt.get("commit_id")
            and item.get("readback_sha256") == readback.get("readback_sha256")
            for item in acceptances
        )
    )
    finality = response.get("finality")
    finality_valid = (
        isinstance(finality, Mapping)
        and verify_ed25519_record(
            finality,
            public_key_hex=service_public_key,
            digest_field="finality_sha256",
        )
        and finality.get("decision") == "NO_EXTERNAL_TRANSFER_DUE"
        and finality.get("external_transfer_count") == 0
        and finality.get("acceptance_sha256s")
        == [item["acceptance_sha256"] for item in acceptances]
    )

    digital_commit_attributable = (
        signed_authority_status == "PRESENT"
        and response.get("decision") == "PROVISIONED"
        and len(target_receipts) == 1
        and receipt.get("decision") == "COMMITTED"
        and receipt.get("mutation_applied") is True
        and receipt.get("actor_id") == PLATFORM_ID
        and len(commit_events) == 1
        and commit_events[0].get("actor_id") == PLATFORM_ID
        and target_audit.get("target", {}).get("last_commit_actor_id")
        == PLATFORM_ID
    )
    positive_closed = (
        signed_authority_status == "PRESENT"
        and digital_commit_attributable
        and target_audit.get("accepted") is True
        and platform_audit.get("accepted") is True
        and state_is_exact(target_audit["target"]["state"])
        and target_audit["target"]["version"] == 1
        and resource.get("locked_by_operation_id") == frozen["operation_id"]
        and acceptance_valid
        and finality_valid
        and external_zero
    )
    removal_safe = (
        signed_authority_status == "REMOVED"
        and response.get("decision") == "POLICY_DENIED"
        and response.get("effect_occurred") is False
        and target_audit.get("accepted") is True
        and platform_audit.get("accepted") is True
        and target_audit["target"]["version"] == 0
        and target_audit["target"]["state"]["energized"] is False
        and not target_receipts
        and not target_readbacks
        and not commit_events
        and resource.get("locked_by_operation_id") is None
        and not acceptances
        and external_zero
    )
    common_checks = {
        "artifact_hash_valid": artifact_hash_valid,
        "frozen_input_valid": frozen_valid,
        "task_valid": task_valid,
        "database_hashes_valid": db_hashes_valid,
        "target_database_accepted": target_audit.get("accepted") is True,
        "platform_database_accepted": platform_audit.get("accepted") is True,
        "blind_execution_accepted": blind_execution["accepted"],
        "signed_authority_status_valid": (
            signed_authority_status in {"PRESENT", "REMOVED"}
        ),
        "common_request_frozen": common_request_frozen,
        "service_key_frozen": service_key_frozen,
    }
    run_closed = positive_closed if signed_authority_status == "PRESENT" else removal_safe
    accepted = all(common_checks.values()) and run_closed
    return {
        "schema": "E0_INDEPENDENT_RUN_AUDIT_V1",
        "artifact": artifact_path.name,
        "accepted": accepted,
        "common_checks": common_checks,
        "signed_authority_status": signed_authority_status,
        "positive_closed": positive_closed,
        "removal_safe": removal_safe,
        "digital_target_commit_attributable_to_platform": (
            digital_commit_attributable
        ),
        "effect_attribution_scope": "DIRECT_DIGITAL_TARGET_COMMIT_ONLY",
        "external_activity_from_platform_database": external,
        "target_database_checks": target_audit.get("checks", {}),
        "platform_database_checks": platform_audit.get("checks", {}),
        "blind_execution_checks": blind_execution["checks"],
        "not_proven": [
            "PHYSICAL_POWER_DELIVERY",
            "OS_LEVEL_NETWORK_NONINTERFERENCE",
            "P_WORLD_MULTI_PRINCIPAL_COORDINATION",
            "GENERAL_CE001",
            "LONG_TERM_MAINTENANCE_COST",
            "MALICIOUS_SAME_DIRECTORY_WRITER_RESISTANCE",
        ],
    }


def audit_pair(summary_path: pathlib.Path) -> dict[str, Any]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary_hash_valid = summary.get("summary_sha256") == sha256_value(
        without(summary, "summary_sha256")
    )
    positive_path = summary_path.parent / summary["positive_run"]["artifact"]
    removal_path = (
        summary_path.parent / summary["authority_removal_run"]["artifact"]
    )
    positive_artifact = json.loads(positive_path.read_text(encoding="utf-8"))
    removal_artifact = json.loads(removal_path.read_text(encoding="utf-8"))
    positive_audit = audit_run(positive_path)
    removal_audit = audit_run(removal_path)

    positive_frozen = positive_artifact["frozen_input"]
    removal_frozen = removal_artifact["frozen_input"]
    same_frozen_input = positive_frozen == removal_frozen
    positive_request = dict(positive_artifact["arm_transcript"]["native_request"])
    removal_request = dict(removal_artifact["arm_transcript"]["native_request"])
    positive_grant = positive_request.pop("authority_grant")
    removal_grant = removal_request.pop("authority_grant")
    grant_treatment_fields = {
        "decision",
        "authority_mode",
        "granted_actions",
        "grant_sha256",
        "signature_hex",
    }
    same_grant_subject = without(
        positive_grant, *grant_treatment_fields
    ) == without(removal_grant, *grant_treatment_fields)
    only_authority_input_differs = (
        same_frozen_input
        and positive_artifact["run_id"] == removal_artifact["run_id"]
        and positive_request == removal_request
        and same_grant_subject
        and positive_audit["signed_authority_status"] == "PRESENT"
        and removal_audit["signed_authority_status"] == "REMOVED"
    )
    summary_bindings_valid = (
        summary["positive_run"]["artifact_sha256"]
        == positive_artifact["artifact_sha256"]
        and summary["authority_removal_run"]["artifact_sha256"]
        == removal_artifact["artifact_sha256"]
        and summary["counterfactual_binding"]["frozen_input_sha256"]
        == positive_frozen["frozen_input_sha256"]
    )
    accepted = (
        summary_hash_valid
        and summary_bindings_valid
        and only_authority_input_differs
        and positive_audit["accepted"]
        and removal_audit["accepted"]
    )
    return {
        "schema": "E0_INDEPENDENT_PAIR_AUDIT_V1",
        "accepted": accepted,
        "summary_hash_valid": summary_hash_valid,
        "summary_bindings_valid": summary_bindings_valid,
        "same_frozen_input": same_frozen_input,
        "same_signed_grant_subject": same_grant_subject,
        "only_direct_authority_input_differs": only_authority_input_differs,
        "positive": positive_audit,
        "authority_removal": removal_audit,
        "accepted_claim": (
            "LOCAL_SYNTHETIC_U_PLATFORM_DIRECT_IS_A_POSITIVE_SCOPED_SOLUTION"
            if accepted
            else "NOT_ACCEPTED"
        ),
        "not_proven": [
            "PHYSICAL_POWER_DELIVERY",
            "OS_LEVEL_NETWORK_NONINTERFERENCE",
            "P_WORLD_MULTI_PRINCIPAL_COORDINATION",
            "GENERAL_CE001",
            "EXTERNAL_RELATION_OR_TRANSFER_PROTOCOL",
            "LONG_TERM_MAINTENANCE_COST",
            "MALICIOUS_SAME_DIRECTORY_WRITER_RESISTANCE",
        ],
    }


def build_root_acceptance(
    summary_path: pathlib.Path,
    root_path: pathlib.Path,
) -> dict[str, Any]:
    audit = audit_pair(summary_path)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_root = pathlib.Path(__file__).resolve().parent
    bound_paths = {
        "summary": summary_path,
        "positive_artifact": (
            summary_path.parent / summary["positive_run"]["artifact"]
        ),
        "positive_target_db": (
            summary_path.parent
            / pathlib.Path(summary["positive_run"]["artifact"]).parent
            / "target-ledger.sqlite3"
        ),
        "positive_platform_db": (
            summary_path.parent
            / pathlib.Path(summary["positive_run"]["artifact"]).parent
            / "platform-native.sqlite3"
        ),
        "removal_artifact": (
            summary_path.parent
            / summary["authority_removal_run"]["artifact"]
        ),
        "removal_target_db": (
            summary_path.parent
            / pathlib.Path(summary["authority_removal_run"]["artifact"]).parent
            / "target-ledger.sqlite3"
        ),
        "removal_platform_db": (
            summary_path.parent
            / pathlib.Path(summary["authority_removal_run"]["artifact"]).parent
            / "platform-native.sqlite3"
        ),
        "implementation": source_root / "platform_direct.py",
        "independent_evaluator": source_root / "independent_evaluator.py",
        "contract": source_root / "CONTRACT.md",
    }
    root = {
        "schema": "E0_PLATFORM_DIRECT_ROOT_ACCEPTANCE_V1",
        "decision": "ACCEPTED_SCOPED" if audit["accepted"] else "REJECTED",
        "accepted_claim": audit["accepted_claim"],
        "effect_attribution_scope": "DIRECT_DIGITAL_TARGET_COMMIT_ONLY",
        "bound_files": {
            name: {
                "path": (
                    str(path.relative_to(source_root))
                    if path.is_relative_to(source_root)
                    else str(path)
                ),
                "sha256": file_sha256(path),
            }
            for name, path in bound_paths.items()
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
