from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admission_validator import (  # noqa: E402
    AdmissionError,
    canonical_bytes,
    load_json,
    sha256_bytes,
    sha256_text,
    sha256_value,
    validate_batch,
    validate_contract,
)


CONTRACT_PATH = ROOT / "RUN-CONTRACT.json"
BATCH_PATH = ROOT / "fixtures" / "FAIR-SEALED-BATCH.json"


def contract():
    return load_json(CONTRACT_PATH)


def batch():
    return load_json(BATCH_PATH)


def rehash_contract(value):
    body = dict(value)
    body.pop("contract_sha256", None)
    value["contract_sha256"] = sha256_value(body)
    return value


def rehash_batch(value):
    body = dict(value)
    body.pop("batch_manifest_sha256", None)
    value["batch_manifest_sha256"] = sha256_value(body)
    return value


def rehash_value_receipt(receipt):
    receipt["sha256"] = sha256_value(receipt["actual"])


def rehash_text_receipt(receipt):
    receipt["byte_length"] = len(receipt["bytes_utf8"].encode("utf-8"))
    receipt["sha256"] = sha256_text(receipt["bytes_utf8"])


def rehash_trigger(trigger):
    body = dict(trigger)
    body.pop("receipt_sha256", None)
    trigger["receipt_sha256"] = sha256_value(body)


def run_for(value, treatment):
    return next(item for item in value["run_admissions"] if item["treatment_id"] == treatment)


def candidate_for(value, treatment):
    return next(item for item in value["sealed_candidates"] if item["treatment_id"] == treatment)


def test_contract_binds_wave021_internal_hash_and_all_eight_sources():
    result = validate_contract(contract())
    assert result["status"] == "SEALED_ADMISSION_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER"
    assert result["contract_sha256"] == contract()["contract_sha256"]


@pytest.mark.parametrize(
    "old,new",
    [
        ("exactly one", "at least one"),
        ("must be verified again at commit time", "may be cached from preflight"),
        ("owner-native Acceptance", "controller PASS"),
    ],
)
def test_contract_author_cannot_substitute_pinned_q_and_rehash(old, new):
    attacked = contract()
    attacked["full_task_preimage"]["q_bytes_utf8"] = attacked["full_task_preimage"][
        "q_bytes_utf8"
    ].replace(old, new)
    attacked["full_task_preimage"]["q_sha256"] = sha256_text(
        attacked["full_task_preimage"]["q_bytes_utf8"]
    )
    rehash_contract(attacked)
    with pytest.raises(AdmissionError, match="pinned Wave023 preimage"):
        validate_contract(attacked)


def test_development_fixture_is_admitted_only_as_unscored_and_not_executed():
    result = validate_batch(batch(), contract())
    assert result == {
        "status": "DEVELOPMENT_SMOKE_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED",
        "batch_id": "wave023-development-smoke-fixture-no-run",
        "family": "DIRECT_A1_A5",
        "candidate_count": 5,
        "world_count": 1,
        "run_count": 5,
        "comparison_status": "NOT_RUN",
        "winner": "NOT_EVALUATED",
    }


def test_closed_contract_schema_rejects_unknown_key_even_with_valid_self_hash():
    attacked = contract()
    attacked["friendly_extension"] = True
    rehash_contract(attacked)
    with pytest.raises(AdmissionError, match="unknown keys"):
        validate_contract(attacked)


def test_closed_nested_batch_schema_rejects_unknown_key_even_with_valid_manifest_hash():
    attacked = batch()
    attacked["sealed_candidates"][0]["private_oracle"] = "helpful"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="unknown keys"):
        validate_batch(attacked, contract())


def test_obvious_placeholder_hash_is_rejected_not_just_length_checked():
    attacked = batch()
    attacked["sealed_candidates"][0]["bundle_sha256"] = "a" * 64
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="placeholder hash"):
        validate_batch(attacked, contract())


def test_full_q_bytes_cannot_be_replaced_while_preserving_task_coordinates():
    attacked = batch()
    run = attacked["run_admissions"][0]
    packet = json.loads(run["launch_receipt"]["initial_payload"]["bytes_utf8"])
    packet["q_bytes_utf8"] = packet["q_bytes_utf8"].replace("exactly one", "at least one")
    run["launch_receipt"]["initial_payload"]["bytes_utf8"] = canonical_bytes(packet).decode()
    rehash_text_receipt(run["launch_receipt"]["initial_payload"])
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="changed q_bytes_utf8"):
        validate_batch(attacked, contract())


@pytest.mark.parametrize(
    "field,new_actual",
    [
        ("argv", ["/sealed/case-P-runner"]),
        ("env", {"SEMANTIC_CASE_ID": "E3B"}),
        ("cwd", "/sealed/E3B"),
        ("process_name", "a4-special"),
        ("fd_inventory", [{"fd": 9, "role": "private-truth"}]),
        ("network_inventory", [{"direction": "connect", "endpoint_id": "oracle", "family": "INET"}]),
        ("endpoint_inventory", [{"endpoint_id": "grader", "surface": "private"}]),
    ],
)
def test_actual_launch_surface_attacks_are_rejected(field, new_actual):
    attacked = batch()
    receipt = attacked["run_admissions"][3]["launch_receipt"][field]
    receipt["actual"] = new_actual
    rehash_value_receipt(receipt)
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="launch surface leaks|surface differs"):
        validate_batch(attacked, contract())


def test_candidate_executable_model_prompt_and_console_are_content_bound():
    attacked = batch()
    a3 = candidate_for(attacked, "A3-GENERAL-MODEL-MATURE-STACK")
    a3["artifacts"]["model"]["bytes_utf8"] += "post-world repair"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="model hash mismatch"):
        validate_batch(attacked, contract())


def test_authority_topology_signature_tamper_is_rejected():
    attacked = batch()
    witness = attacked["world_preimages"][0]["authority_topology_witness"]
    witness["signature_b64"] = witness["signature_b64"][:-2] + "AA"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="signature verification failed"):
        validate_batch(attacked, contract())


def test_authority_topology_p_cannot_smuggle_a_delegation_even_if_resigned_is_not_claimed():
    attacked = batch()
    witness = attacked["world_preimages"][0]["authority_topology_witness"]
    statement = json.loads(witness["signed_statement_bytes_utf8"])
    statement["delegation_ids"] = ["fake-central-delegation"]
    witness["signed_statement_bytes_utf8"] = canonical_bytes(statement).decode()
    witness["signed_statement_sha256"] = sha256_text(witness["signed_statement_bytes_utf8"])
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="signature verification failed"):
        validate_batch(attacked, contract())


def test_trigger_must_bind_q_target_operation_heads_prefix_and_pre_post():
    attacked = batch()
    trigger = attacked["run_admissions"][1]["trigger_receipt"]
    trigger["current_owner_head_set"] = []
    rehash_trigger(trigger)
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="owner heads missing"):
        validate_batch(attacked, contract())


def test_fired_trigger_requires_exactly_once_and_distinct_pre_post():
    attacked = batch()
    trigger = attacked["run_admissions"][1]["trigger_receipt"]
    trigger["fired_status"] = "FIRED"
    trigger["fired_count"] = 1
    trigger["post_state_sha256"] = trigger["pre_state_sha256"]
    rehash_trigger(trigger)
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="distinct pre/post"):
        validate_batch(attacked, contract())


def test_world_clones_cannot_share_namespace_keyset_or_mutable_state():
    attacked = batch()
    attacked["world_clones"][1]["storage_namespace"] = attacked["world_clones"][0]["storage_namespace"]
    attacked["world_clones"][1]["shared_mutable_state_paths"] = ["/shared/target.sqlite"]
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="shares mutable state"):
        validate_batch(attacked, contract())


def test_budget_overflow_and_component_budget_are_rejected():
    attacked = batch()
    receipt = attacked["run_admissions"][2]["budget_receipt"]
    receipt["observed"]["target_execute_calls_max"] = 3
    receipt["component_budget_grants"] = [{"component": "A4", "extra_calls": 1}]
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="exceeds budget"):
        validate_batch(attacked, contract())


def test_direct_family_rejects_duplicate_candidate_or_combined_candidate_mixing():
    attacked = batch()
    attacked["sealed_candidates"][4] = copy.deepcopy(attacked["sealed_candidates"][0])
    attacked["sealed_candidates"][4]["treatment_id"] = "C1-PUBLIC-AUTHORITY-ROUTER-A1-A4"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="bundle identity|may not mix A/C"):
        validate_batch(attacked, contract())


def test_redteam_candidate_oracle_marker_attack_is_rejected_after_all_hashes_are_recomputed():
    attacked = batch()
    candidate = candidate_for(attacked, "A3-GENERAL-MODEL-MATURE-STACK")
    executable = candidate["artifacts"]["executable"]
    executable["bytes_utf8"] += (
        "semantic_case_id=E0 expected_disposition=SUCCESS "
        "private_truth=true runtime_env=oracle"
    )
    executable["sha256"] = sha256_text(executable["bytes_utf8"])
    bundle_value = json.loads(candidate["bundle_bytes_utf8"])
    bundle_value["artifact_sha256s"]["executable"] = executable["sha256"]
    candidate["bundle_bytes_utf8"] = canonical_bytes(bundle_value).decode()
    candidate["bundle_sha256"] = sha256_text(candidate["bundle_bytes_utf8"])
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="forbidden oracle/case marker"):
        validate_batch(attacked, contract())


def test_redteam_hidden_model_calls_meter_attack_is_rejected_after_receipt_rehash():
    attacked = batch()
    receipt = run_for(attacked, "A3-GENERAL-MODEL-MATURE-STACK")["budget_receipt"]
    receipt["meter_log"]["bytes_utf8"] = canonical_bytes({
        "schema": "CE001_METER_LEDGER_V1",
        "events": [],
        "model_calls": 10000,
        "hidden_retrieval": True,
        "tokens": 999999999,
    }).decode()
    rehash_text_receipt(receipt["meter_log"])
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="unknown keys"):
        validate_batch(attacked, contract())


def test_redteam_post_grader_trigger_attack_is_rejected_after_trigger_rehash():
    attacked = batch()
    trigger = run_for(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION")["trigger_receipt"]
    trigger["equivalent_event_class"] = "AFTER_GRADER_SUCCESS"
    trigger["intervention"] = "POSTHOC_ONLY_IF_SUCCESS"
    rehash_trigger(trigger)
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="event class is not preregistered"):
        validate_batch(attacked, contract())


def test_a1_in_plural_world_is_not_applicable_not_failed_or_planned():
    attacked = batch()
    run_for(attacked, "A1-LAWFUL-CENTER")["planned_status"] = "SEALED_NOT_RUN"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="wrong applicability/status"):
        validate_batch(attacked, contract())


def test_randomized_order_must_be_an_exact_committed_permutation():
    attacked = batch()
    attacked["randomization"]["ordered_run_ids"][0] = attacked["randomization"]["ordered_run_ids"][1]
    attacked["randomization"]["order_commitment_sha256"] = sha256_value(
        attacked["randomization"]["ordered_run_ids"]
    )
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="exact run permutation"):
        validate_batch(attacked, contract())


def test_ci_optional_stopping_and_posthoc_repair_are_rejected():
    attacked = batch()
    attacked["replication_and_ci"]["optional_stopping"] = True
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="optional stopping"):
        validate_batch(attacked, contract())


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda c: c["candidate_seal_policy"].update({"model_required_for": []}), "model/prompt-bearing"),
        (lambda c: c["candidate_seal_policy"].update({"console_required_for": []}), "human/console-bearing"),
        (lambda c: c["launch_receipt_policy"].update({"candidate_visible_case_or_stratum_forbidden": False}), "case/stratum leak"),
        (lambda c: c["failure_trigger_policy"].update({"frozen_before_launch": False}), "chosen after launch"),
        (lambda c: c["common_budget"]["limits"].update({"broker_round_trips_max": 10**9}), "frozen Wave021 envelope"),
    ],
)
def test_contract_author_cannot_weaken_frozen_policy_and_rehash(mutator, match):
    attacked = contract()
    mutator(attacked)
    rehash_contract(attacked)
    with pytest.raises(AdmissionError, match=match):
        validate_contract(attacked)


def test_incomplete_isomorphic_twin_is_rejected():
    attacked = batch()
    world = attacked["world_preimages"][0]
    world["isomorphic_twin_group_id"] = "S-R-twin-001"
    world["twin_role"] = "S"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="exactly S/R"):
        validate_batch(attacked, contract())


def test_pre_run_batch_cannot_claim_commit_target_acceptance_or_finality_receipts():
    attacked = batch()
    attacked["run_admissions"][0]["runtime_native_receipts_status"] = "COMPLETE"
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="improperly claims native runtime receipts"):
        validate_batch(attacked, contract())


def test_actual_comparison_is_fail_closed_until_trusted_runtime_seals_exist():
    attacked = batch()
    attacked["execution_mode"] = "ACTUAL_COMPARISON_SEALED_NOT_RUN"
    attacked["receipt_provenance"] = "LIVE_CONTROLLER_OBSERVED"
    attacked["claim_boundary"]["development_smoke_unscored"] = False
    attacked["replication_and_ci"]["replicates_per_world_treatment"] = 2
    rehash_batch(attacked)
    with pytest.raises(AdmissionError, match="actual comparison admission is blocked"):
        validate_batch(attacked, contract())
