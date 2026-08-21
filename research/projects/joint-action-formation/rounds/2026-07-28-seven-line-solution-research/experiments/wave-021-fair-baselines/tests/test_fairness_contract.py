from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ROUND_ROOT = ROOT.parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fairness_validator import (  # noqa: E402
    FairnessError,
    collect_batch_errors,
    load_json,
    validate_batch_plan,
    validate_contract,
    validate_failure_trigger_spec,
)


CONTRACT_PATH = ROOT / "BASELINE-CONTRACT.json"
PLAN_PATH = ROOT / "fixtures" / "FAIR-BATCH-TEMPLATE.json"
ATTACK_PATH = ROOT / "fixtures" / "UNFAIR-TOWOW-EXTRA-ORACLE.json"
FAIR_TRIGGER_PATH = ROOT / "fixtures" / "FAIR-FAILURE-TRIGGER.json"
RAW_ORDINAL_TRIGGER_PATH = (
    ROOT / "fixtures" / "UNFAIR-RAW-ORDINAL-FAILURE-TRIGGER.json"
)


def contract():
    return load_json(CONTRACT_PATH)


def plan():
    return load_json(PLAN_PATH)


def arm_run(batch, arm_id):
    return next(run for run in batch["arm_runs"] if run["arm_id"] == arm_id)


def test_frozen_contract_and_source_hashes_are_valid():
    result = validate_contract(contract(), source_root=ROUND_ROOT)
    assert result["status"] == "FAIRNESS_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER"
    assert result["arm_count"] == 5
    assert result["source_count"] == 8


def test_fair_batch_template_passes_without_running_or_selecting_winner():
    result = validate_batch_plan(plan(), contract())
    assert result == {
        "status": "FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED",
        "batch_id": "batch-template-no-run",
        "arm_count": 5,
        "authority_stratum": "U",
    }
    view = contract()["common_profiles"]["initial_view"]
    assert "arm_id" not in view["allowlist"]
    assert "arm_id" in view["forbidden_fields_or_channels"]


def test_unfair_towow_oracle_retry_and_budget_attack_is_detected():
    errors = collect_batch_errors(load_json(ATTACK_PATH), contract())
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION extra initial fields" in item for item in errors)
    assert any("arm_id" in item for item in errors)
    assert any(
        "A4-DETERMINISTIC-MATURE-COMPOSITION differs on effect_evidence_profile_id"
        in item
        for item in errors
    )
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION visible failure oracle" in item for item in errors)
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION private truth oracle" in item for item in errors)
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION grader oracle" in item for item in errors)
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION post-evaluation rerun" in item for item in errors)
    assert any("A4-DETERMINISTIC-MATURE-COMPOSITION budget override" in item for item in errors)


def test_different_initial_bytes_are_rejected():
    attacked = plan()
    arm_run(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION")[
        "shared_task_projection_sha256"
    ] = "b" * 64
    with pytest.raises(FairnessError, match="different initial task semantics"):
        validate_batch_plan(attacked, contract())


def test_different_failure_plan_is_rejected():
    attacked = plan()
    arm_run(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION")[
        "failure_plan_id"
    ] = "A4-POSTERIOR-ORACLE-PLAN"
    with pytest.raises(FairnessError, match="differs on failure_plan_id"):
        validate_batch_plan(attacked, contract())


def test_count_only_effect_scorer_is_rejected():
    attacked = plan()
    arm_run(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION")[
        "effect_evidence_profile_id"
    ] = "CE001-OCCURRENCE-COUNT-ONLY@invalid"
    with pytest.raises(FairnessError, match="differs on effect_evidence_profile_id"):
        validate_batch_plan(attacked, contract())


def test_extra_retry_budget_is_rejected():
    attacked = plan()
    arm_run(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION")[
        "budget_overrides"
    ] = {"target_execute_calls_max": 3}
    with pytest.raises(FairnessError, match="extra budget"):
        validate_batch_plan(attacked, contract())


def test_a1_must_be_not_applicable_in_plural_independent_world():
    attacked = plan()
    attacked["evaluator_private_authority_stratum"] = "P"
    with pytest.raises(FairnessError, match="A1 must be NOT_APPLICABLE in P"):
        validate_batch_plan(attacked, contract())
    arm_run(attacked, "A1-LAWFUL-CENTER")["planned_status"] = "NOT_APPLICABLE"
    assert validate_batch_plan(attacked, contract())["authority_stratum"] == "P"


def test_contract_does_not_turn_component_acceptance_into_comparative_result():
    value = contract()
    assert value["evidence_boundary"]["comparative_evidence"] == "NONE"
    assert value["evidence_boundary"]["winner"] == "NOT_EVALUATED"
    assert value["claim_boundary"]["final_winner_claim_allowed"] is False
    assert value["claim_boundary"]["existing_solution_full_success_is_positive"] is True


def test_exact_effect_gate_rejects_the_earlier_count_only_false_green_shape():
    gate = contract()["common_profiles"]["effect_evidence"]
    assert gate["sample_count"] == 46
    assert gate["sample_offsets"] == "0..45_CONTIGUOUS_UNIQUE"
    assert gate["sample_target_id"] == "VenueV:CircuitC7"
    assert gate["sample_other_circuits_energized"] == []
    assert gate["sample_power_min_kw"] == 2.85
    assert gate["sample_power_max_kw"] == 3.15
    assert gate["sample_safety_ok"] is True
    assert gate["sample_noise_ok"] is True
    assert gate["duration_minutes"] == 45
    assert gate["deadline_rule"] == "effect_start_minute+45<=deadline_minute"
    assert gate["count_only_scoring_forbidden"] is True


def test_hidden_failure_equality_is_semantic_not_trace_ordinal():
    trigger = contract()["common_profiles"]["failure_injection"][
        "trigger_equivalence"
    ]
    assert trigger["basis"] == "SEMANTIC_NATIVE_BOUNDARY"
    assert "equivalent_event_class" in trigger["required_bindings"]
    assert "current_owner_head_set" in trigger["required_bindings"]
    assert "Target_prefix_semantic_digest" in trigger["required_bindings"]
    assert trigger["raw_event_ordinal_only_forbidden"] is True
    assert trigger["raw_trace_length_only_forbidden"] is True
    assert trigger["clone_specific_trigger_visible_to_arm"] is False


def test_raw_ordinal_failure_trigger_attack_is_rejected():
    assert (
        validate_failure_trigger_spec(load_json(FAIR_TRIGGER_PATH), contract())["status"]
        == "SEMANTIC_FAILURE_TRIGGER_ACCEPTED_NOT_EXECUTED"
    )
    with pytest.raises(FairnessError, match="raw ordinal/timing/hash"):
        validate_failure_trigger_spec(
            load_json(RAW_ORDINAL_TRIGGER_PATH),
            contract(),
        )


def test_a5_model_simulation_cannot_be_registered_as_real_human_treatment():
    value = contract()
    a5 = next(
        arm
        for arm in value["arm_definitions"]
        if arm["arm_id"] == "A5-BOUNDED-HUMAN-INSTITUTION"
    )
    assert "real_human_coordinator" in a5["native_resources"]
    assert any("model simulation is fixture only" in item for item in a5["constraints"])
