from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pair_runtime import (  # noqa: E402
    DESIRED_STATE,
    RECOVERED_EXISTING_EFFECT_NO_REPLAY,
    RECOVERED_NO_EFFECT_SAFE_RETRY,
    run_pair,
    verify_target_signature,
)


@pytest.fixture(scope="module")
def completed_pair(tmp_path_factory):
    output = tmp_path_factory.mktemp("wave016-e3-pair")
    return run_pair(output)


def test_actual_spawn_pair_has_byte_identical_start_and_prefix(completed_pair):
    evaluation = completed_pair["pair_evaluation"]
    assert evaluation["status"] == "PAIR_PASSED"
    assert evaluation["startup_view_raw_equal"] is True
    assert evaluation["pre_readback_raw_equal"] is True
    assert evaluation["pre_readback_event_count"] == 3
    assert evaluation["first_public_difference_index"] == 3
    assert (
        evaluation["first_public_difference_kind"]
        == "EXACT_TARGET_STATUS_RESPONSE"
    )

    world_a = completed_pair["world_a"]
    world_b = completed_pair["world_b"]
    assert world_a["launch_receipt"]["process_start_method"] == "spawn"
    assert world_b["launch_receipt"]["process_start_method"] == "spawn"
    assert (
        world_a["launch_receipt"]["visible_surface"]["view_bytes"]
        == world_b["launch_receipt"]["visible_surface"]["view_bytes"]
    )
    assert (
        world_a["arm_result"]["transcript"][:3]
        == world_b["arm_result"]["transcript"][:3]
    )


def test_existing_effect_world_reconciles_without_replay(completed_pair):
    world = completed_pair["world_a"]
    arm = world["arm_result"]
    broker = world["broker_private_result"]
    assert arm["disposition"] == RECOVERED_EXISTING_EFFECT_NO_REPLAY
    assert arm["retry_performed"] is False
    assert arm["submit_message_count"] == 1
    assert broker["commit_before_unconfirmed"] is True
    assert broker["retry_seen"] is False
    assert broker["ledger_apply_calls"] == 1
    assert world["ledger_audit"]["mutation_count"] == 1
    assert world["ledger_audit"]["version"] == 1
    assert world["ledger_audit"]["state"] == DESIRED_STATE


def test_no_effect_world_uses_signed_negative_then_safe_retry(completed_pair):
    world = completed_pair["world_b"]
    arm = world["arm_result"]
    broker = world["broker_private_result"]
    negative = arm["status_envelope"]
    assert arm["disposition"] == RECOVERED_NO_EFFECT_SAFE_RETRY
    assert arm["retry_performed"] is True
    assert arm["submit_message_count"] == 2
    assert negative["status"] == "NOT_COMMITTED"
    assert negative["matching_occurrence_hashes"] == []
    assert negative["observed_version"] == 0
    assert negative["covered_ledger_range"]["through_version"] == 0
    assert verify_target_signature(negative)
    assert broker["commit_before_unconfirmed"] is False
    assert broker["freshness_seen"] is True
    assert broker["retry_seen"] is True
    assert broker["ledger_apply_calls"] == 1
    assert world["ledger_audit"]["mutation_count"] == 1
    assert world["ledger_audit"]["version"] == 1
    assert world["ledger_audit"]["state"] == DESIRED_STATE
    freshness = arm["freshness_response"]["capability_freshness"]
    assert freshness["schema"] == "TARGET_CAPABILITY_FRESHNESS_V1"
    assert freshness["status"] == "CURRENT"
    assert freshness["capability_consumed_by_request_id"] is None
    assert freshness["observed_negative_head"] == negative["current_head"]


def test_wrong_object_decoy_is_signed_but_cannot_satisfy_exact_query(
    completed_pair,
):
    arm = completed_pair["world_b"]["arm_result"]
    exclusions = arm["decoy_exclusions"]
    assert len(exclusions) == 1
    assert exclusions[0]["excluded"] is True
    assert "OBJECT_ID_MISMATCH" in exclusions[0]["reasons"]
    assert "TARGET_ID_MISMATCH" in exclusions[0]["reasons"]
    assert "OPERATION_ID_MISMATCH" in exclusions[0]["reasons"]
    assert completed_pair["pair_evaluation"]["wrong_object_decoy_excluded"] is True
    assert (
        completed_pair["pair_evaluation"]["wrong_object_decoy_actual_commit"]
        is True
    )
    decoy_audit = completed_pair["world_b"]["decoy_ledger_audit"]
    assert decoy_audit["target_id"] == "VenueV:CircuitC8"
    assert decoy_audit["mutation_count"] == 1
    assert decoy_audit["version"] == 1
    assert decoy_audit["state"] == DESIRED_STATE


def test_target_status_signature_and_exact_query_binding_fail_closed(
    completed_pair,
):
    negative = completed_pair["world_b"]["arm_result"]["status_envelope"]
    tampered = copy.deepcopy(negative)
    tampered["object_id"] = "VenueV:CircuitC8"
    assert verify_target_signature(tampered) is False

    query_bytes = negative["query_request_bytes"]
    query = json.loads(query_bytes)
    assert query["object_id"] == "VenueV:CircuitC7"
    assert query["operation_id"] == completed_pair["world_b"][
        "launch_receipt"
    ]["visible_surface"]["view"]["operation_id"]
    assert negative["query_request_sha256"]
    expected_key = completed_pair["world_b"]["broker_private_result"][
        "target_public_key_hex"
    ]
    assert negative["target_public_key_hex"] == expected_key
    assert verify_target_signature(negative, expected_key)
    assert completed_pair["pair_evaluation"]["target_endpoint_key_bound"] is True


def test_raw_artifacts_and_claim_boundaries_are_preserved(completed_pair):
    run_dir = Path(completed_pair["run_dir"])
    expected = {
        "shared-startup-view.json",
        "shared-pre-readback-prefix.json",
        "pair-evaluation.json",
        "BOUNDARIES.json",
        "result.json",
    }
    assert expected.issubset({path.name for path in run_dir.iterdir()})
    for world_name in ("world-a", "world-b"):
        world_dir = run_dir / world_name
        assert (world_dir / "blind-launch-receipt.json").is_file()
        assert (world_dir / "arm-result.json").is_file()
        assert (world_dir / "broker-private-result.json").is_file()
        assert (world_dir / "target-ledger-audit.json").is_file()
        assert (world_dir / "historical-decoy-ledger-audit.json").is_file()

    boundaries = completed_pair["boundaries"]
    assert completed_pair["pair_evaluation"]["no_physical_effect_claim"] is True
    assert completed_pair["pair_evaluation"]["no_legal_authority_claim"] is True
    assert any(
        "No physical electrical Effect" in item
        for item in boundaries["non_claims"]
    )
