from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from independent_evaluator import (  # noqa: E402
    audit_pair,
    audit_run,
    build_root_acceptance,
    file_sha256,
    sha256_value as independent_sha256_value,
    without as independent_without,
)
from platform_direct import (  # noqa: E402
    PLATFORM_ID,
    SANITIZED_CHILD_ENVIRONMENT,
    authority_status_from_signed_grant,
    evaluate_artifact,
    exact_task,
    make_frozen_pair_configuration,
    public_key_hex,
    run_platform_direct,
    sha256_value,
    signed_authority_grant,
    verify_authority_grant,
    verify_platform_record,
)


@pytest.fixture(scope="module")
def actual_pair(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    root = tmp_path_factory.mktemp("e0-platform-direct")
    configuration = make_frozen_pair_configuration()
    positive = run_platform_direct(
        direct_authority_present=True,
        run_dir=root / "run-0001",
        frozen_configuration=configuration,
    )
    removal = run_platform_direct(
        direct_authority_present=False,
        run_dir=root / "run-0002",
        frozen_configuration=configuration,
    )
    summary = {
        "schema": "E0_PLATFORM_DIRECT_ACTUAL_PAIR_V2",
        "batch_id": "pytest-batch",
        "positive_run": {
            "artifact": "run-0001/artifact.json",
            "artifact_sha256": positive["artifact_sha256"],
        },
        "authority_removal_run": {
            "artifact": "run-0002/artifact.json",
            "artifact_sha256": removal["artifact_sha256"],
        },
        "counterfactual_binding": {
            "frozen_input_sha256": positive["frozen_input"][
                "frozen_input_sha256"
            ],
        },
        "claim_boundary": "LOCAL_SYNTHETIC_TEST",
    }
    summary["summary_sha256"] = sha256_value(summary)
    summary_path = root / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    root_acceptance_path = root / "ROOT-ACCEPTANCE.json"
    root_acceptance = build_root_acceptance(
        summary_path,
        root_acceptance_path,
    )
    return {
        "positive": positive,
        "removal": removal,
        "root_path": root,
        "summary_path": summary_path,
        "root_acceptance_path": root_acceptance_path,
        "root_acceptance": root_acceptance,
    }


def test_lawful_unified_platform_direct_closes_exact_task(
    actual_pair: dict[str, Any],
) -> None:
    artifact = actual_pair["positive"]
    evaluation = artifact["evaluation"]

    assert evaluation["TaskOutcomeSatisfied"] is True
    assert evaluation["CorrectResolution"] is True
    assert evaluation["SafeHandling"] is True
    assert evaluation["UnnecessaryFormation"] is False
    assert evaluation["EffectAttributableToPlatform"] is True
    assert (
        evaluation["EffectAttributionScope"]
        == "DIRECT_DIGITAL_TARGET_COMMIT_ONLY"
    )
    assert evaluation["SignedAuthorityStatus"] == "PRESENT"
    assert evaluation["TargetVersion"] == 1
    assert evaluation["ResourceLocked"] is True
    assert artifact["target_authenticity"] == {
        "receipt_valid": [True],
        "readback_valid": [True],
    }

    response = artifact["arm_transcript"]["native_response"]
    receipt = response["target_receipt"]
    readback = response["target_readback"]
    finality = response["finality"]
    acceptances = artifact["platform_native_service_log"]["acceptances"]
    service_key = artifact["platform_native_service_start"]["public_key_hex"]
    assert response["decision"] == "PROVISIONED"
    assert receipt["decision"] == "COMMITTED"
    assert receipt["mutation_applied"] is True
    assert receipt["actor_id"] == PLATFORM_ID
    assert readback["observed_commit_id"] == receipt["commit_id"]
    assert readback["attached_to_receipt_commit"] is True
    assert {acceptance["role"] for acceptance in acceptances} == {
        "REQUESTER_ROLE",
        "VENUE_ROLE",
    }
    assert all(
        verify_platform_record(
            acceptance,
            public_key=service_key,
            digest_field="acceptance_sha256",
        )
        for acceptance in acceptances
    )
    assert finality["decision"] == "NO_EXTERNAL_TRANSFER_DUE"
    assert finality["external_transfer_count"] == 0
    assert finality["acceptance_sha256s"] == [
        acceptance["acceptance_sha256"] for acceptance in acceptances
    ]
    assert verify_platform_record(
        finality,
        public_key=service_key,
        digest_field="finality_sha256",
    )


def test_exact_power_window_is_target_native_readback(
    actual_pair: dict[str, Any],
) -> None:
    state = actual_pair["positive"]["target_final_state"]["state"]
    samples = state["power_samples"]

    assert state["target_id"] == exact_task()["target_id"]
    assert state["energized"] is True
    assert state["duration_minutes"] == 45
    assert state["power_kw"] == 3.0
    assert state["other_circuits_energized"] == []
    assert [sample["minute"] for sample in samples] == list(range(46))
    assert all(sample["power_kw"] == 3.0 for sample in samples)
    assert all(sample["safety_ok"] is True for sample in samples)
    assert all(sample["noise_ok"] is True for sample in samples)


def test_platform_direct_has_zero_external_formation_and_transfer(
    actual_pair: dict[str, Any],
) -> None:
    artifact = actual_pair["positive"]
    service = artifact["platform_native_service_log"]
    external = service["external_activity"]
    event_ledger = service["event_ledger"]
    evaluation = artifact["evaluation"]

    assert external == {
        "discovery_calls": 0,
        "relation_events": 0,
        "delegation_events": 0,
        "external_transfer_count": 0,
    }
    assert event_ledger["external_activity"] == external
    assert event_ledger["event_count"] == len(event_ledger["events"])
    assert all(
        not event["event_type"].startswith("EXTERNAL_")
        for event in event_ledger["events"]
    )
    assert evaluation["ExternalDiscoveryCalls"] == 0
    assert evaluation["ExternalRelationEvents"] == 0
    assert evaluation["ExternalDelegationEvents"] == 0
    assert evaluation["ExternalTransferCount"] == 0
    assert artifact["arm_transcript"]["platform_native_call_count"] == 1
    assert len(service["requests"]) == 1


def test_removing_direct_authority_prevents_effect_and_resource_lock(
    actual_pair: dict[str, Any],
) -> None:
    artifact = actual_pair["removal"]
    evaluation = artifact["evaluation"]
    response = artifact["arm_transcript"]["native_response"]

    assert response["decision"] == "POLICY_DENIED"
    assert response["effect_occurred"] is False
    assert response["finality"] == "NO_EXTERNAL_TRANSFER_DUE"
    assert evaluation["TaskOutcomeSatisfied"] is False
    assert evaluation["CorrectResolution"] is True
    assert evaluation["SafeHandling"] is True
    assert evaluation["EffectAttributableToPlatform"] is False
    assert evaluation["SignedAuthorityStatus"] == "REMOVED"
    assert evaluation["UnnecessaryFormation"] is False
    assert evaluation["TargetVersion"] == 0
    assert evaluation["ResourceLocked"] is False
    assert artifact["target_final_state"]["state"]["energized"] is False
    assert artifact["resource_final_state"]["locked_by_operation_id"] is None
    assert artifact["platform_native_service_log"]["resource_locks"] == []
    assert artifact["platform_native_service_log"]["target_receipts"] == []
    assert artifact["platform_native_service_log"]["target_readbacks"] == []
    assert artifact["platform_native_service_log"]["acceptances"] == []


def test_removal_is_same_task_counterfactual(
    actual_pair: dict[str, Any],
) -> None:
    positive = actual_pair["positive"]
    removal = actual_pair["removal"]

    assert positive["frozen_input"] == removal["frozen_input"]
    assert positive["run_id"] == removal["run_id"]
    assert positive["task"] == removal["task"]
    assert positive["task_sha256"] == removal["task_sha256"]
    frozen = positive["frozen_input"]
    positive_grant = positive["arm_transcript"]["native_request"][
        "authority_grant"
    ]
    removal_grant = removal["arm_transcript"]["native_request"][
        "authority_grant"
    ]
    assert (
        authority_status_from_signed_grant(
            positive_grant,
            venue_public_key_hex=frozen["venue_authority_public_key_hex"],
            operation_id=frozen["operation_id"],
        )
        == "PRESENT"
    )
    assert (
        authority_status_from_signed_grant(
            removal_grant,
            venue_public_key_hex=frozen["venue_authority_public_key_hex"],
            operation_id=frozen["operation_id"],
        )
        == "REMOVED"
    )
    assert positive["target_final_state"]["version"] == 1
    assert removal["target_final_state"]["version"] == 0


def test_arm_is_real_spawn_and_receives_no_private_case_label(
    actual_pair: dict[str, Any],
) -> None:
    for artifact in (actual_pair["positive"], actual_pair["removal"]):
        blindness = artifact["blindness_receipt"]
        visibility = artifact["arm_transcript"]["visibility"]
        assert blindness["spawn_start_method"] == "spawn"
        assert blindness["distinct_processes"] is True
        assert blindness["private_canary_absent"] is True
        assert blindness["semantic_case_label_present"] is False
        assert blindness["child_environments_exact"] is True
        assert visibility["environment"] == SANITIZED_CHILD_ENVIRONMENT
        assert visibility["start_method"] == "spawn"
        assert "private_world_reveal" not in visibility["visible_fields"]
        assert "expected_outcome" not in visibility["visible_fields"]
        assert artifact["arm_transcript"]["native_response"]["decision"] in {
            "PROVISIONED",
            "POLICY_DENIED",
        }


def test_policy_rejects_signature_tamper_and_wrong_operation() -> None:
    private_key = Ed25519PrivateKey.generate()
    grant = signed_authority_grant(
        private_key=private_key,
        operation_id="operation-123",
        direct_authority_present=True,
    )
    valid, reason = verify_authority_grant(
        grant,
        venue_public_key_hex=public_key_hex(private_key),
        operation_id="operation-123",
    )
    assert valid is True
    assert reason == "DIRECT_AUTHORITY_CURRENT"

    tampered = copy.deepcopy(grant)
    tampered["target_id"] = "VenueV:WrongCircuit"
    valid, reason = verify_authority_grant(
        tampered,
        venue_public_key_hex=public_key_hex(private_key),
        operation_id="operation-123",
    )
    assert valid is False
    assert reason == "GRANT_SIGNATURE_INVALID"

    valid, reason = verify_authority_grant(
        grant,
        venue_public_key_hex=public_key_hex(private_key),
        operation_id="operation-456",
    )
    assert valid is False
    assert reason == "POLICY_MISMATCH:operation_id"


def test_evaluator_detects_injected_unnecessary_formation(
    actual_pair: dict[str, Any],
) -> None:
    artifact = copy.deepcopy(actual_pair["positive"])
    artifact["platform_native_service_log"]["external_activity"][
        "relation_events"
    ] = 1
    artifact["platform_native_service_log"]["event_ledger"][
        "external_activity"
    ]["relation_events"] = 1

    evaluation = evaluate_artifact(artifact)

    assert evaluation["TaskOutcomeSatisfied"] is True
    assert evaluation["CorrectResolution"] is False
    assert evaluation["UnnecessaryFormation"] is True
    assert evaluation["ExternalRelationEvents"] == 1


def test_actual_artifact_and_database_hashes_exist(
    actual_pair: dict[str, Any],
) -> None:
    for artifact in (actual_pair["positive"], actual_pair["removal"]):
        assert artifact["artifact_sha256"]
        assert artifact["database_artifacts"]["target_ledger_sha256"]
        assert artifact["database_artifacts"]["platform_native_sha256"]
        assert artifact["database_artifacts"]["target_ledger_snapshot"][
            "standalone_file"
        ] is True
        assert artifact["database_artifacts"]["platform_native_snapshot"][
            "standalone_file"
        ] is True
        assert artifact["cost"]["platform_native_calls"] == 1
        assert artifact["cost"]["model_calls"] == 0
        assert artifact["cost"]["human_minutes"] == 0
        artifact_path = (
            Path(artifact["database_artifacts"]["target_ledger_file"]).name
        )
        assert artifact_path == "target-ledger.sqlite3"


def copy_run_for_attack(
    actual_pair: dict[str, Any],
    *,
    arm: str,
    destination: Path,
) -> Path:
    source_name = "run-0001" if arm == "positive" else "run-0002"
    source = actual_pair["root_path"] / source_name
    shutil.copytree(source, destination)
    return destination / "artifact.json"


def rewrite_attacked_artifact(
    artifact_path: Path,
    artifact: dict[str, Any],
) -> None:
    artifact["artifact_sha256"] = independent_sha256_value(
        independent_without(artifact, "artifact_sha256")
    )
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_independent_pair_evaluator_and_root_acceptance(
    actual_pair: dict[str, Any],
) -> None:
    pair_audit = audit_pair(actual_pair["summary_path"])
    root = json.loads(
        actual_pair["root_acceptance_path"].read_text(encoding="utf-8")
    )

    assert pair_audit["accepted"] is True
    assert pair_audit["same_frozen_input"] is True
    assert pair_audit["only_direct_authority_input_differs"] is True
    assert pair_audit["positive"][
        "digital_target_commit_attributable_to_platform"
    ] is True
    assert pair_audit["positive"]["effect_attribution_scope"] == (
        "DIRECT_DIGITAL_TARGET_COMMIT_ONLY"
    )
    assert pair_audit["positive"][
        "external_activity_from_platform_database"
    ] == {
        "discovery_calls": 0,
        "relation_events": 0,
        "delegation_events": 0,
        "external_transfer_count": 0,
    }
    assert pair_audit["positive"]["common_checks"][
        "blind_execution_accepted"
    ] is True
    assert all(
        pair_audit["positive"]["blind_execution_checks"].values()
    )
    assert root["decision"] == "ACCEPTED_SCOPED"
    assert root["root_sha256"] == independent_sha256_value(
        independent_without(root, "root_sha256")
    )
    assert "PHYSICAL_POWER_DELIVERY" in root["not_proven"]


def test_attack_forged_frozen_authority_key_is_rejected(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "forged-key",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["frozen_input"]["venue_authority_public_key_hex"] = "00" * 32
    artifact["frozen_input"]["frozen_input_sha256"] = independent_sha256_value(
        independent_without(
            artifact["frozen_input"],
            "frozen_input_sha256",
        )
    )
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False
    assert audit["signed_authority_status"] == "INVALID"


def test_attack_external_event_in_database_defeats_zero_claim(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "external-event",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    platform_path = artifact_path.parent / "platform-native.sqlite3"
    payload = {"query": "candidate external agent"}
    with sqlite3.connect(platform_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO events(
                event_type, operation_id, request_id, payload_sha256
            ) VALUES (?, ?, ?, ?)
            """,
            (
                "EXTERNAL_DISCOVERY_CALL",
                artifact["operation_id"],
                artifact["frozen_input"]["request_id"],
                independent_sha256_value(payload),
            ),
        )
        sequence = cursor.lastrowid
    event = {
        "sequence": sequence,
        "event_type": "EXTERNAL_DISCOVERY_CALL",
        "operation_id": artifact["operation_id"],
        "request_id": artifact["frozen_input"]["request_id"],
        "payload_sha256": independent_sha256_value(payload),
    }
    ledger = artifact["platform_native_service_log"]["event_ledger"]
    ledger["events"].append(event)
    ledger["event_count"] += 1
    ledger["external_activity"]["discovery_calls"] = 1
    artifact["platform_native_service_log"]["external_activity"][
        "discovery_calls"
    ] = 1
    artifact["database_artifacts"]["platform_native_sha256"] = file_sha256(
        platform_path
    )
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False
    assert audit["external_activity_from_platform_database"][
        "discovery_calls"
    ] == 1


def test_attack_role_acceptance_tamper_is_rejected(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "acceptance-tamper",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["platform_native_service_log"]["acceptances"][0][
        "decision"
    ] = "REJECTED"
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False


def test_attack_target_database_swap_is_rejected(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "target-swap",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    removal_db = (
        actual_pair["root_path"] / "run-0002" / "target-ledger.sqlite3"
    )
    target_path = artifact_path.parent / "target-ledger.sqlite3"
    shutil.copy2(removal_db, target_path)
    artifact["database_artifacts"]["target_ledger_sha256"] = file_sha256(
        target_path
    )
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False
    assert audit["common_checks"]["target_database_accepted"] is False


def test_attack_fake_spawn_receipt_is_rejected(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "fake-spawn",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["arm_transcript"]["visibility"]["start_method"] = "fork"
    artifact["blindness_receipt"]["spawn_start_method"] = "fork"
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False
    assert audit["blind_execution_checks"]["spawn_start_method"] is False


def test_attack_extra_visibility_and_second_call_are_rejected(
    actual_pair: dict[str, Any],
    tmp_path: Path,
) -> None:
    artifact_path = copy_run_for_attack(
        actual_pair,
        arm="positive",
        destination=tmp_path / "visibility-leak",
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["arm_transcript"]["visibility"]["visible_fields"].append(
        "expected_outcome"
    )
    artifact["arm_transcript"]["visibility"]["environment"][
        "PRIVATE_CASE_LABEL"
    ] = "EXPECTED_SUCCESS"
    artifact["arm_transcript"]["platform_native_call_count"] = 2
    rewrite_attacked_artifact(artifact_path, artifact)

    audit = audit_run(artifact_path)

    assert audit["accepted"] is False
    assert audit["blind_execution_checks"]["visible_schema_exact"] is False
    assert (
        audit["blind_execution_checks"]["child_environments_sanitized"]
        is False
    )
    assert audit["blind_execution_checks"]["one_actual_native_call"] is False
