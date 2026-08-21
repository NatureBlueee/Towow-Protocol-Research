#!/usr/bin/env python3
"""Fail-closed admission for a sealed CE-001 blind batch.

This module validates evidence needed *before* a comparison may start.  It does
not launch a candidate, score a run, compute a winner, or turn development
fixtures into comparative evidence.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


CONTRACT_SCHEMA = "CE001_SEALED_RUN_ADMISSION_CONTRACT_V1"
BATCH_SCHEMA = "CE001_SEALED_BATCH_ADMISSION_V1"

DIRECT_TREATMENTS = {
    "A1-LAWFUL-CENTER",
    "A2-EQUAL-INFORMATION-CENTER",
    "A3-GENERAL-MODEL-MATURE-STACK",
    "A4-DETERMINISTIC-MATURE-COMPOSITION",
    "A5-BOUNDED-HUMAN-INSTITUTION",
}
COMBINED_TREATMENTS = {
    "C1-PUBLIC-AUTHORITY-ROUTER-A1-A4",
    "C2-MODEL-PLAN-DETERMINISTIC-GATES",
    "C3-DETERMINISTIC-HUMAN-ESCALATION",
}

HASH_RE = re.compile(r"^[0-9a-f]{64}$")
OBVIOUS_PLACEHOLDERS = {
    "0" * 64,
    "1" * 64,
    "a" * 64,
    "b" * 64,
    "f" * 64,
    "0123456789abcdef" * 4,
}
EXPECTED_Q_SHA256 = "8b66d611556654c70346665cfc5052cbd81b315bd4e1ccbfe64d083cfbfb485b"
EXPECTED_PROBLEM_BINDINGS = {
    "problem/v1-candidate.md": "7982aa908ce4e457e655fbe553db228f2ab9a09fdaa1202309df261d1bdc4a56",
    "problem/v1-candidate.json": "9a59de81ac7c5ca0a42ff012bbade98b4be60978742b3c81d26f9024a3e9b408",
    "problem/v2.md": "d305867ca07d02f86daddfe8bb76fc22df5a68ee18edb7ce599e6c03a2ab3cc8",
    "problem/v2.json": "cb6d4bd9c5930181df9176957daa144085a3eaf9f1edfc3c3992cd87f94a2f46",
}


class AdmissionError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AdmissionError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise AdmissionError("duplicate JSON key: %s" % key)
        value[key] = item
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
    )
    require(isinstance(value, dict), "%s must contain one JSON object" % path)
    return value


def exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    require(isinstance(value, Mapping), "%s must be an object" % label)
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    require(not missing, "%s missing keys: %s" % (label, missing))
    require(not unknown, "%s unknown keys: %s" % (label, unknown))


def valid_hash(value: Any, label: str) -> str:
    require(isinstance(value, str) and HASH_RE.fullmatch(value) is not None,
            "%s must be a lowercase sha256" % label)
    require(value not in OBVIOUS_PLACEHOLDERS and len(set(value)) > 4,
            "%s is an obvious placeholder hash" % label)
    return value


def _verify_text_receipt(value: Mapping[str, Any], label: str) -> str:
    exact_keys(value, {"bytes_utf8", "byte_length", "sha256"}, label)
    text = value["bytes_utf8"]
    require(isinstance(text, str), "%s bytes_utf8 must be text" % label)
    raw = text.encode("utf-8")
    require(value["byte_length"] == len(raw), "%s byte_length mismatch" % label)
    valid_hash(value["sha256"], "%s.sha256" % label)
    require(value["sha256"] == sha256_bytes(raw), "%s sha256 mismatch" % label)
    return text


def _verify_value_receipt(value: Mapping[str, Any], label: str) -> Any:
    exact_keys(value, {"actual", "sha256"}, label)
    valid_hash(value["sha256"], "%s.sha256" % label)
    require(value["sha256"] == sha256_value(value["actual"]),
            "%s actual value hash mismatch" % label)
    return value["actual"]


def _verify_self_hash(value: Mapping[str, Any], field: str, label: str) -> None:
    claimed = valid_hash(value.get(field), "%s.%s" % (label, field))
    body = dict(value)
    body.pop(field, None)
    require(claimed == sha256_value(body), "%s %s mismatch" % (label, field))


CONTRACT_KEYS = {
    "schema", "contract_id", "contract_sha256", "status", "baseline_binding",
    "problem_source_bindings", "full_task_preimage", "batch_families", "authority_policy",
    "candidate_seal_policy", "launch_receipt_policy", "failure_trigger_policy",
    "world_clone_policy", "runtime_native_receipt_policy", "common_budget", "randomization_replication_ci",
    "claim_boundary",
}


def validate_contract(
    contract: Mapping[str, Any],
    *,
    experiments_root: Path | None = None,
) -> dict[str, Any]:
    exact_keys(contract, CONTRACT_KEYS, "contract")
    require(contract["schema"] == CONTRACT_SCHEMA, "wrong contract schema")
    require(contract["status"] == "PREREGISTERED_ADMISSION_ONLY_COMPARISON_NOT_RUN",
            "contract improperly claims execution")
    _verify_self_hash(contract, "contract_sha256", "contract")

    binding = contract["baseline_binding"]
    exact_keys(binding, {"contract_id", "path", "sha256"}, "baseline_binding")
    require(binding["contract_id"] == "CE001-A1-A5-FAIR-BASELINES@v1",
            "wrong Wave021 contract binding")
    valid_hash(binding["sha256"], "baseline_binding.sha256")
    if experiments_root is None:
        experiments_root = Path(__file__).resolve().parent.parent
    baseline = (Path(experiments_root) / binding["path"]).resolve()
    root = Path(experiments_root).resolve()
    require(baseline.is_relative_to(root), "baseline path escapes experiments root")
    require(baseline.is_file(), "bound Wave021 contract is missing")
    require(sha256_file(baseline) == binding["sha256"], "bound Wave021 contract drifted")
    baseline_value = load_json(baseline)
    require(baseline_value.get("contract_id") == binding["contract_id"],
            "bound Wave021 contract id mismatch")
    baseline_body = dict(baseline_value)
    baseline_internal_hash = baseline_body.pop("contract_sha256", None)
    require(baseline_internal_hash == sha256_value(baseline_body),
            "bound Wave021 internal contract hash mismatch")
    round_root = root.parent
    sources = baseline_value.get("source_bindings")
    require(isinstance(sources, list) and len(sources) == 8,
            "bound Wave021 source set is not the frozen eight")
    for source in sources:
        exact_keys(source, {"path", "sha256"}, "Wave021.source_binding")
        source_path = (round_root / source["path"]).resolve()
        require(source_path.is_relative_to(round_root) and source_path.is_file(),
                "Wave021 bound source missing or escapes root: %s" % source["path"])
        require(sha256_file(source_path) == source["sha256"],
                "Wave021 source binding drifted: %s" % source["path"])

    problem_sources = contract["problem_source_bindings"]
    require(isinstance(problem_sources, list), "problem_source_bindings must be a list")
    problem_map: dict[str, str] = {}
    project_root = root.parent.parent.parent
    for source in problem_sources:
        exact_keys(source, {"path", "sha256"}, "problem_source_binding")
        require(source["path"] not in problem_map, "duplicate problem source binding")
        problem_map[source["path"]] = source["sha256"]
        source_path = (project_root / source["path"]).resolve()
        require(source_path.is_relative_to(project_root) and source_path.is_file(),
                "problem source missing or escapes project root: %s" % source["path"])
        require(sha256_file(source_path) == source["sha256"],
                "problem source binding drifted: %s" % source["path"])
    require(problem_map == EXPECTED_PROBLEM_BINDINGS,
            "Problem V1/V2 source closure changed")

    task = contract["full_task_preimage"]
    exact_keys(task, {
        "q_version", "q_bytes_utf8", "q_sha256", "object_id", "target_id",
        "operation_scope", "deadline_minute", "required_duration_minutes",
        "required_power_kw", "power_tolerance_percent", "safety_required",
        "noise_required", "acceptance_owners", "finality_owner",
    }, "full_task_preimage")
    require(isinstance(task["q_bytes_utf8"], str) and len(task["q_bytes_utf8"].encode("utf-8")) >= 200,
            "full Q bytes are absent or suspiciously short")
    valid_hash(task["q_sha256"], "full_task_preimage.q_sha256")
    require(task["q_sha256"] == sha256_text(task["q_bytes_utf8"]), "full Q hash mismatch")
    require(task["q_sha256"] == EXPECTED_Q_SHA256,
            "full Q differs from the pinned Wave023 preimage")
    require(task["q_version"] == "Q@v1", "Q version changed")
    require(task["object_id"] == "PowerOccurrence:VenueV:CircuitC7", "task object changed")
    require(task["target_id"] == "VenueV:CircuitC7", "Target changed")
    require(task["deadline_minute"] == 90 and task["required_duration_minutes"] == 45,
            "task timing changed")
    require(task["required_power_kw"] == 3.0 and task["power_tolerance_percent"] == 5,
            "task power changed")
    require(task["safety_required"] is True and task["noise_required"] is True,
            "safety/noise requirement missing")
    require(task["acceptance_owners"] == ["O_Q", "O_V"] and task["finality_owner"] == "O_P",
            "Acceptance/finality changed")

    families = contract["batch_families"]
    exact_keys(families, {"direct", "combined", "mixing_forbidden"}, "batch_families")
    require(set(families["direct"]) == DIRECT_TREATMENTS and len(families["direct"]) == 5,
            "direct batch must be exactly A1-A5")
    require(set(families["combined"]) == COMBINED_TREATMENTS and len(families["combined"]) == 3,
            "combined batch must be exactly C1-C3")
    require(families["mixing_forbidden"] is True, "direct and combined candidates may mix")

    authority = contract["authority_policy"]
    exact_keys(authority, {
        "allowed_strata", "witness_algorithm", "witness_verified_before_launch",
        "a1_applicable_strata", "a1_plural_status", "topology_statement_required_fields",
    }, "authority_policy")
    require(authority["allowed_strata"] == ["U", "D", "P"], "Authority strata changed")
    require(authority["witness_algorithm"] == "ED25519", "Authority witness is not Ed25519")
    require(authority["witness_verified_before_launch"] is True, "Authority witness may be late")
    require(set(authority["a1_applicable_strata"]) == {"U", "D"}
            and authority["a1_plural_status"] == "NOT_APPLICABLE",
            "A1 applicability changed")

    seal = contract["candidate_seal_policy"]
    exact_keys(seal, {
        "one_candidate_per_treatment", "alternates_forbidden", "sealed_before_world_assignment",
        "required_artifact_slots", "model_required_for", "prompt_required_for",
        "console_required_for", "development_fixture_marker_forbidden_in_actual",
    }, "candidate_seal_policy")
    require(seal["one_candidate_per_treatment"] is True and seal["alternates_forbidden"] is True,
            "single-candidate rule missing")
    require(seal["sealed_before_world_assignment"] is True, "candidate may be selected after world")
    require(seal["required_artifact_slots"] == ["executable", "model", "prompt", "console"],
            "candidate artifact slots changed")
    require(set(seal["model_required_for"]) == {
        "A3-GENERAL-MODEL-MATURE-STACK", "C2-MODEL-PLAN-DETERMINISTIC-GATES",
    } and set(seal["prompt_required_for"]) == {
        "A3-GENERAL-MODEL-MATURE-STACK", "C2-MODEL-PLAN-DETERMINISTIC-GATES",
    }, "model/prompt-bearing treatment requirements weakened")
    require(set(seal["console_required_for"]) == {
        "A4-DETERMINISTIC-MATURE-COMPOSITION",
        "A5-BOUNDED-HUMAN-INSTITUTION",
        "C3-DETERMINISTIC-HUMAN-ESCALATION",
    }, "human/console-bearing treatment requirements weakened")
    require(seal["development_fixture_marker_forbidden_in_actual"] is True,
            "development fixture marker may enter an actual batch")

    launch = contract["launch_receipt_policy"]
    exact_keys(launch, {
        "controller_observed_actual_values_required", "required_receipts",
        "same_surface_across_treatments", "candidate_visible_case_or_stratum_forbidden",
    }, "launch_receipt_policy")
    require(launch["controller_observed_actual_values_required"] is True,
            "declared launch profile may substitute for actual observation")
    require(set(launch["required_receipts"]) == {
        "initial_payload", "argv", "env", "cwd", "process_name", "fd_inventory",
        "network_inventory", "endpoint_inventory",
    }, "launch receipt set incomplete")
    require(launch["same_surface_across_treatments"] is True, "launch surfaces may differ")
    require(launch["candidate_visible_case_or_stratum_forbidden"] is True,
            "candidate-visible case/stratum leak allowed")

    trigger = contract["failure_trigger_policy"]
    exact_keys(trigger, {
        "basis", "frozen_before_launch", "required_bindings", "allowed_fired_statuses",
        "raw_only_triggers_forbidden", "pre_post_required_when_fired",
    }, "failure_trigger_policy")
    require(trigger["basis"] == "SEMANTIC_NATIVE_BOUNDARY", "trigger basis is not semantic")
    require(trigger["frozen_before_launch"] is True, "failure trigger may be chosen after launch")
    require(set(trigger["required_bindings"]) == {
        "q_sha256", "target_id", "operation_scope", "equivalent_event_class",
        "current_owner_head_set", "target_prefix_semantic_digest", "intervention",
        "fired_status", "fired_count", "pre_state_sha256", "post_state_sha256",
        "clone_native_event_sha256", "semantic_projection_sha256",
    }, "failure trigger bindings incomplete")
    require(trigger["raw_only_triggers_forbidden"] is True
            and trigger["pre_post_required_when_fired"] is True,
            "trigger exactness weakened")
    require(trigger["allowed_fired_statuses"]
            == ["FROZEN_NOT_FIRED", "FIRED", "TRIGGER_NOT_REACHED"],
            "trigger fired statuses changed")

    clone = contract["world_clone_policy"]
    exact_keys(clone, {
        "world_preimage_bytes_required", "one_independent_clone_per_treatment",
        "unique_storage_namespace", "unique_keyset", "shared_mutable_state_forbidden",
        "cross_clone_channels_forbidden", "semantic_preimage_equal",
    }, "world_clone_policy")
    require(all(clone.values()), "world clone independence policy weakened")

    native = contract["runtime_native_receipt_policy"]
    exact_keys(native, {
        "required_if_execution_occurs", "pre_run_status",
        "commit_time_authority_receipt_fields", "target_native_receipts",
        "owner_native_receipts", "finality_native_receipt",
        "controller_declaration_cannot_substitute",
    }, "runtime_native_receipt_policy")
    require(native["required_if_execution_occurs"] is True
            and native["pre_run_status"] == "NOT_AVAILABLE_COMPARISON_NOT_RUN"
            and native["controller_declaration_cannot_substitute"] is True,
            "native runtime receipt boundary weakened")
    require(set(native["commit_time_authority_receipt_fields"]) >= {
        "signed_authority_epoch", "q_sha256", "target_id", "operation_scope",
        "current_at_commit",
    }, "commit-time current Authority receipt incomplete")
    require(set(native["target_native_receipts"]) == {
        "EFFECT_COMMIT", "TARGET_STATUS", "TARGET_READBACK",
    }, "Target-native receipt set incomplete")
    require(set(native["owner_native_receipts"]) == {
        "O_Q_ACCEPTANCE", "O_V_ACCEPTANCE",
    } and native["finality_native_receipt"] == "O_P_FINALITY",
            "owner Acceptance/finality receipt set incomplete")

    budget = contract["common_budget"]
    exact_keys(budget, {
        "profile_id", "limits", "actual_meter_log_required", "overrides_forbidden",
        "combined_candidate_single_total_budget", "component_budget_grants_forbidden",
    }, "common_budget")
    limits = budget["limits"]
    exact_keys(limits, {
        "logical_deadline_minute", "wall_timeout_seconds", "owner_queries_max",
        "broker_round_trips_max", "target_execute_calls_max",
        "target_status_or_readback_calls_max", "retry_or_recovery_actions_max",
        "dynamic_disclosed_bytes_max", "disclosure_sensitivity_points_max",
        "evaluated_episode_reruns_max", "grader_feedback_reads_max",
        "private_truth_reads_max", "prior_arm_transcript_reads_max",
    }, "common_budget.limits")
    require(limits["evaluated_episode_reruns_max"] == 0
            and limits["grader_feedback_reads_max"] == 0
            and limits["private_truth_reads_max"] == 0
            and limits["prior_arm_transcript_reads_max"] == 0,
            "zero-access budget weakened")
    require(limits == {
        "logical_deadline_minute": 90,
        "wall_timeout_seconds": 300,
        "owner_queries_max": 24,
        "broker_round_trips_max": 48,
        "target_execute_calls_max": 2,
        "target_status_or_readback_calls_max": 6,
        "retry_or_recovery_actions_max": 12,
        "dynamic_disclosed_bytes_max": 65536,
        "disclosure_sensitivity_points_max": 32,
        "evaluated_episode_reruns_max": 0,
        "grader_feedback_reads_max": 0,
        "private_truth_reads_max": 0,
        "prior_arm_transcript_reads_max": 0,
    }, "common budget differs from the frozen Wave021 envelope")
    require(budget["actual_meter_log_required"] is True
            and budget["overrides_forbidden"] is True
            and budget["combined_candidate_single_total_budget"] is True
            and budget["component_budget_grants_forbidden"] is True,
            "budget metering or combined budget rule weakened")

    rrci = contract["randomization_replication_ci"]
    exact_keys(rrci, {
        "seed_commitment_before_launch", "order_commitment_before_launch",
        "order_evaluator_private", "actual_min_replicates_per_world_treatment",
        "ci_method", "ci_level", "ci_only_after_replicates", "fixed_stop_rule",
        "optional_stopping_forbidden", "repair_requires_new_batch_all_treatments",
    }, "randomization_replication_ci")
    require(rrci["seed_commitment_before_launch"] is True
            and rrci["order_commitment_before_launch"] is True
            and rrci["order_evaluator_private"] is True,
            "seed/order seal weakened")
    require(rrci["actual_min_replicates_per_world_treatment"] >= 2,
            "actual comparison lacks replication")
    require(rrci["ci_only_after_replicates"] is True
            and rrci["optional_stopping_forbidden"] is True
            and rrci["repair_requires_new_batch_all_treatments"] is True,
            "CI/stop/repair rule weakened")

    boundary = contract["claim_boundary"]
    exact_keys(boundary, {
        "admission_is_not_execution", "development_smoke_unscored",
        "comparison_status", "winner", "ce001_complete_claim_allowed",
    }, "claim_boundary")
    require(boundary == {
        "admission_is_not_execution": True,
        "development_smoke_unscored": True,
        "comparison_status": "NOT_RUN",
        "winner": "NOT_EVALUATED",
        "ce001_complete_claim_allowed": False,
    }, "claim boundary changed")

    return {
        "status": "SEALED_ADMISSION_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER",
        "contract_id": contract["contract_id"],
        "contract_sha256": contract["contract_sha256"],
    }


ARTIFACT_KEYS = {"present", "bytes_utf8", "sha256"}
CANDIDATE_KEYS = {
    "treatment_id", "candidate_id", "sealed_before_world_assignment",
    "alternate_candidate_ids", "bundle_bytes_utf8", "bundle_sha256", "artifacts",
}


def _validate_candidate(candidate: Mapping[str, Any], contract: Mapping[str, Any], mode: str) -> None:
    label = "candidate[%s]" % candidate.get("treatment_id")
    exact_keys(candidate, CANDIDATE_KEYS, label)
    require(candidate["sealed_before_world_assignment"] is True, "%s sealed too late" % label)
    require(candidate["alternate_candidate_ids"] == [], "%s has alternate candidates" % label)
    require(isinstance(candidate["candidate_id"], str) and candidate["candidate_id"],
            "%s candidate_id missing" % label)
    valid_hash(candidate["bundle_sha256"], "%s.bundle_sha256" % label)
    require(candidate["bundle_sha256"] == sha256_text(candidate["bundle_bytes_utf8"]),
            "%s bundle hash mismatch" % label)
    exact_keys(candidate["artifacts"], {"executable", "model", "prompt", "console"},
               "%s.artifacts" % label)
    for slot, artifact in candidate["artifacts"].items():
        exact_keys(artifact, ARTIFACT_KEYS, "%s.artifacts.%s" % (label, slot))
        require(isinstance(artifact["present"], bool), "%s %s present is not bool" % (label, slot))
        valid_hash(artifact["sha256"], "%s.artifacts.%s.sha256" % (label, slot))
        require(artifact["sha256"] == sha256_text(artifact["bytes_utf8"]),
                "%s %s hash mismatch" % (label, slot))
        require(artifact["present"] == bool(artifact["bytes_utf8"]),
                "%s %s presence/bytes mismatch" % (label, slot))
    try:
        bundle = json.loads(
            candidate["bundle_bytes_utf8"], object_pairs_hook=_reject_duplicate_keys
        )
    except json.JSONDecodeError as exc:
        raise AdmissionError("%s bundle is not a closed JSON manifest" % label) from exc
    exact_keys(bundle, {
        "schema", "treatment_id", "candidate_id", "artifact_sha256s",
        "no_private_oracle", "no_semantic_case_router", "no_post_world_selection",
        "development_fixture",
    }, "%s.bundle" % label)
    require(bundle["schema"] == "CE001_CANDIDATE_BUNDLE_V1",
            "%s wrong bundle schema" % label)
    require(bundle["treatment_id"] == candidate["treatment_id"]
            and bundle["candidate_id"] == candidate["candidate_id"],
            "%s bundle identity mismatch" % label)
    require(bundle["artifact_sha256s"]
            == {slot: artifact["sha256"] for slot, artifact in candidate["artifacts"].items()},
            "%s bundle does not bind all artifact hashes" % label)
    require(bundle["no_private_oracle"] is True
            and bundle["no_semantic_case_router"] is True
            and bundle["no_post_world_selection"] is True,
            "%s bundle admits oracle/case-router/post-world selection" % label)
    require(bundle["development_fixture"] is (mode == "DEVELOPMENT_SMOKE_UNSCORED"),
            "%s bundle development marker mismatches mode" % label)
    forbidden_markers = (
        "semantic_case_id", "expected_disposition", "private_truth", "grader_output",
        "prior_arm_transcript", "runtime_env=oracle", "hidden_retrieval=true",
    )
    sealed_bytes = "\n".join(
        [candidate["bundle_bytes_utf8"]]
        + [artifact["bytes_utf8"] for artifact in candidate["artifacts"].values()]
    ).lower()
    require(not any(marker in sealed_bytes for marker in forbidden_markers),
            "%s sealed bytes contain a forbidden oracle/case marker" % label)
    require(candidate["artifacts"]["executable"]["present"] is True,
            "%s executable is not sealed" % label)
    policy = contract["candidate_seal_policy"]
    for field, slot in (("model_required_for", "model"),
                        ("prompt_required_for", "prompt"),
                        ("console_required_for", "console")):
        if candidate["treatment_id"] in policy[field]:
            require(candidate["artifacts"][slot]["present"] is True,
                    "%s required %s is not sealed" % (label, slot))
    if mode == "ACTUAL_COMPARISON_SEALED_NOT_RUN":
        for artifact in candidate["artifacts"].values():
            require("fixture" not in artifact["bytes_utf8"].lower()
                    and "development" not in artifact["bytes_utf8"].lower(),
                    "%s development artifact cannot enter actual comparison" % label)


LAUNCH_KEYS = {
    "initial_payload", "argv", "env", "cwd", "process_name", "fd_inventory",
    "network_inventory", "endpoint_inventory",
}


def _validate_initial_packet(text: str, contract: Mapping[str, Any], label: str) -> None:
    try:
        packet = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise AdmissionError("%s initial payload is not JSON: %s" % (label, exc)) from exc
    exact_keys(packet, {
        "schema", "opaque_episode_handle", "opaque_run_binding", "arm_binding_token",
        "q_version", "q_bytes_utf8", "q_sha256", "object_id", "target_id",
        "operation_id", "operation_scope", "deadline_minute", "required_duration_minutes",
        "required_power_kw", "power_tolerance_percent", "safety_required", "noise_required",
        "acceptance_owners", "finality_owner", "common_budget_profile_id",
        "disclosure_policy_id", "fixed_broker_capabilities",
    }, "%s.initial_packet" % label)
    task = contract["full_task_preimage"]
    for field in (
        "q_version", "q_bytes_utf8", "q_sha256", "object_id", "target_id",
        "operation_scope", "deadline_minute", "required_duration_minutes",
        "required_power_kw", "power_tolerance_percent", "safety_required",
        "noise_required", "acceptance_owners", "finality_owner",
    ):
        require(packet[field] == task[field], "%s initial packet changed %s" % (label, field))
    require(isinstance(packet["operation_id"], str) and packet["operation_id"],
            "%s operation_id missing" % label)


def _validate_launch(receipt: Mapping[str, Any], contract: Mapping[str, Any], label: str) -> dict[str, Any]:
    exact_keys(receipt, LAUNCH_KEYS, "%s.launch_receipt" % label)
    payload = _verify_text_receipt(receipt["initial_payload"], "%s.initial_payload" % label)
    _validate_initial_packet(payload, contract, label)
    values = {"initial_payload": payload}
    for field in ("argv", "env", "cwd", "process_name", "fd_inventory",
                  "network_inventory", "endpoint_inventory"):
        values[field] = _verify_value_receipt(receipt[field], "%s.%s" % (label, field))
    require(isinstance(values["argv"], list) and values["argv"], "%s argv empty" % label)
    require(isinstance(values["env"], dict), "%s env is not object" % label)
    require(isinstance(values["cwd"], str) and values["cwd"], "%s cwd empty" % label)
    require(isinstance(values["process_name"], str) and values["process_name"],
            "%s process name empty" % label)
    for inventory in ("fd_inventory", "network_inventory", "endpoint_inventory"):
        require(isinstance(values[inventory], list), "%s %s is not a list" % (label, inventory))
    forbidden = canonical_bytes(values).lower()
    require(b"semantic_case_id" not in forbidden and b"authority_stratum" not in forbidden,
            "%s launch surface leaks evaluator-private world labels" % label)
    return values


WITNESS_KEYS = {
    "witness_id", "algorithm", "signer_key_id", "public_key_b64",
    "signed_statement_bytes_utf8", "signed_statement_sha256", "signature_b64",
}


def _validate_authority_witness(
    witness: Mapping[str, Any], world: Mapping[str, Any], contract: Mapping[str, Any]
) -> None:
    label = "authority_witness[%s]" % witness.get("witness_id")
    exact_keys(witness, WITNESS_KEYS, label)
    require(witness["algorithm"] == "ED25519", "%s wrong algorithm" % label)
    statement_text = witness["signed_statement_bytes_utf8"]
    valid_hash(witness["signed_statement_sha256"], "%s.statement_hash" % label)
    require(witness["signed_statement_sha256"] == sha256_text(statement_text),
            "%s statement hash mismatch" % label)
    try:
        public_key = base64.b64decode(witness["public_key_b64"], validate=True)
        signature = base64.b64decode(witness["signature_b64"], validate=True)
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            signature, statement_text.encode("utf-8")
        )
    except (ValueError, InvalidSignature) as exc:
        raise AdmissionError("%s signature verification failed" % label) from exc
    try:
        statement = json.loads(statement_text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise AdmissionError("%s signed statement is not JSON" % label) from exc
    required = set(contract["authority_policy"]["topology_statement_required_fields"])
    exact_keys(statement, required, "%s.statement" % label)
    task = contract["full_task_preimage"]
    require(statement["world_id"] == world["world_id"], "%s world binding mismatch" % label)
    require(statement["world_preimage_sha256"] == world["preimage"]["sha256"],
            "%s preimage binding mismatch" % label)
    require(statement["q_sha256"] == task["q_sha256"], "%s Q binding mismatch" % label)
    require(statement["target_id"] == task["target_id"], "%s Target binding mismatch" % label)
    require(statement["operation_scope"] == task["operation_scope"],
            "%s operation scope mismatch" % label)
    require(statement["authority_stratum"] == world["authority_stratum"],
            "%s stratum mismatch" % label)
    principals = statement["principals"]
    delegations = statement["delegation_ids"]
    require(isinstance(principals, list) and len(principals) == len(set(principals)),
            "%s principals invalid" % label)
    require(isinstance(delegations, list) and len(delegations) == len(set(delegations)),
            "%s delegations invalid" % label)
    if world["authority_stratum"] == "U":
        require(len(principals) == 1 and delegations == [], "%s invalid U topology" % label)
    elif world["authority_stratum"] == "D":
        require(len(principals) >= 2 and delegations, "%s invalid D topology" % label)
    else:
        require(len(principals) >= 2 and delegations == [], "%s invalid P topology" % label)


TRIGGER_KEYS = {
    "trigger_id", "basis", "q_sha256", "target_id", "operation_scope",
    "equivalent_event_class", "current_owner_head_set", "target_prefix_semantic_digest",
    "intervention", "fired_status", "fired_count", "pre_state_sha256",
    "post_state_sha256", "clone_native_event_sha256", "semantic_projection_sha256",
    "receipt_sha256",
}


def _validate_trigger(
    receipt: Mapping[str, Any], clone: Mapping[str, Any], contract: Mapping[str, Any],
    mode: str, label: str,
) -> None:
    exact_keys(receipt, TRIGGER_KEYS, "%s.trigger_receipt" % label)
    _verify_self_hash(receipt, "receipt_sha256", "%s.trigger_receipt" % label)
    task = contract["full_task_preimage"]
    require(receipt["basis"] == "SEMANTIC_NATIVE_BOUNDARY", "%s raw-only trigger" % label)
    require(receipt["equivalent_event_class"] in {
        "FORMATION_OPERATOR_LOOKUP",
        "OWNER_DECISION_READ",
        "OWNER_DECISION_SIGN",
        "OWNER_DECISION_RESERVE",
        "OWNER_DECISION_EXECUTE",
        "BEFORE_TARGET_EFFECT_COMMIT",
        "AFTER_TARGET_EFFECT_COMMIT_BEFORE_ACK",
        "AFTER_PRIMARY_RESERVATION_BEFORE_EXECUTE",
        "AFTER_VERIFIED_TARGET_READBACK_BEFORE_ACCEPTANCE",
        "AFTER_MIGRATION_CUT_BEFORE_REPLAY",
    }, "%s trigger equivalent event class is not preregistered" % label)
    require(receipt["intervention"] in {
        "REMOVE_FORMATION_OPERATOR",
        "REVERSE_OWNER_DECISION@read",
        "REVERSE_OWNER_DECISION@sign",
        "REVERSE_OWNER_DECISION@reserve",
        "REVERSE_OWNER_DECISION@execute",
        "DROP_SUBMIT_ACK@effect",
        "DROP_SUBMIT_ACK@no-effect",
        "WRONG_OBJECT_READBACK",
        "TARGET_IGNORE_FENCE",
        "TARGET_RESTART_LOSES_EPOCH",
        "CRASH_AFTER_EFFECT_BEFORE_ACCEPTANCE",
        "OLD_RUNTIME_RESTART",
        "DROP_MIGRATION_CAPSULE_FIELD",
        "MATERIAL_Q_CHANGE_BY_O_Q",
        "MATERIAL_Q_CHANGE_BY_CONTROLLER",
    }, "%s trigger intervention is not preregistered" % label)
    require(receipt["q_sha256"] == task["q_sha256"], "%s trigger Q mismatch" % label)
    require(receipt["target_id"] == task["target_id"], "%s trigger Target mismatch" % label)
    require(receipt["operation_scope"] == task["operation_scope"],
            "%s trigger operation mismatch" % label)
    require(isinstance(receipt["current_owner_head_set"], list)
            and receipt["current_owner_head_set"], "%s trigger owner heads missing" % label)
    for field in ("target_prefix_semantic_digest", "pre_state_sha256", "post_state_sha256",
                  "clone_native_event_sha256", "semantic_projection_sha256"):
        valid_hash(receipt[field], "%s.trigger.%s" % (label, field))
    require(receipt["target_prefix_semantic_digest"] == clone["initial_state_semantic_sha256"],
            "%s trigger Target prefix not bound to clone" % label)
    status = receipt["fired_status"]
    require(status in contract["failure_trigger_policy"]["allowed_fired_statuses"],
            "%s invalid fired status" % label)
    if status == "FIRED":
        require(receipt["fired_count"] == 1, "%s fired trigger must fire exactly once" % label)
        require(receipt["pre_state_sha256"] != receipt["post_state_sha256"],
                "%s fired trigger lacks distinct pre/post state" % label)
    else:
        require(receipt["fired_count"] == 0, "%s non-fired trigger has fired count" % label)
    if mode == "ACTUAL_COMPARISON_SEALED_NOT_RUN":
        require(status == "FROZEN_NOT_FIRED", "%s pre-run actual trigger cannot claim firing" % label)


BUDGET_KEYS = {
    "profile_id", "limits", "observed", "meter_log", "budget_overrides",
    "component_budget_grants", "single_total_budget", "exhausted",
}


def _validate_budget(
    receipt: Mapping[str, Any], contract: Mapping[str, Any], treatment: str, label: str
) -> None:
    exact_keys(receipt, BUDGET_KEYS, "%s.budget_receipt" % label)
    common = contract["common_budget"]
    require(receipt["profile_id"] == common["profile_id"], "%s budget profile mismatch" % label)
    require(receipt["limits"] == common["limits"], "%s budget limits differ" % label)
    exact_keys(receipt["observed"], set(common["limits"]), "%s.budget.observed" % label)
    for field, limit in common["limits"].items():
        value = receipt["observed"][field]
        require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
                "%s observed %s is invalid" % (label, field))
        require(value <= limit, "%s exceeds budget %s" % (label, field))
    meter_text = _verify_text_receipt(receipt["meter_log"], "%s.meter_log" % label)
    try:
        meter = json.loads(meter_text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise AdmissionError("%s meter log is not closed JSON" % label) from exc
    exact_keys(meter, {"schema", "events"}, "%s.meter_log.body" % label)
    require(meter["schema"] == "CE001_METER_LEDGER_V1"
            and isinstance(meter["events"], list), "%s invalid meter ledger" % label)
    totals = {field: 0 for field in common["limits"]}
    previous = "GENESIS"
    for index, event in enumerate(meter["events"]):
        exact_keys(event, {"seq", "metric", "amount", "previous_event_sha256", "event_sha256"},
                   "%s.meter_event[%d]" % (label, index))
        require(event["seq"] == index and event["metric"] in totals,
                "%s meter event sequence/metric invalid" % label)
        require(isinstance(event["amount"], int) and not isinstance(event["amount"], bool)
                and event["amount"] >= 0, "%s meter amount invalid" % label)
        require(event["previous_event_sha256"] == previous,
                "%s meter hash chain broken" % label)
        valid_hash(event["event_sha256"], "%s.meter_event_hash" % label)
        event_body = dict(event)
        event_body.pop("event_sha256")
        require(event["event_sha256"] == sha256_value(event_body),
                "%s meter event hash mismatch" % label)
        previous = event["event_sha256"]
        totals[event["metric"]] += event["amount"]
    require(totals == receipt["observed"],
            "%s observed budget counters do not equal the meter ledger" % label)
    require(receipt["budget_overrides"] == {}, "%s has a budget override" % label)
    require(receipt["component_budget_grants"] == [],
            "%s has component-level extra budgets" % label)
    require(receipt["single_total_budget"] is True, "%s lacks one total budget" % label)
    require(isinstance(receipt["exhausted"], bool), "%s exhausted is not bool" % label)
    if treatment in COMBINED_TREATMENTS:
        require(receipt["component_budget_grants"] == []
                and receipt["single_total_budget"] is True,
                "%s combined candidate must share one envelope" % label)


def _validate_alias(alias: Mapping[str, Any], treatment: str, label: str) -> None:
    exact_keys(alias, {
        "required", "status", "behavior_trace_sha256", "decision_provenance_sha256",
        "aliases_treatment_id",
    }, "%s.alias_assessment" % label)
    if treatment in COMBINED_TREATMENTS:
        require(alias["required"] is True, "%s combined alias assessment missing" % label)
        require(alias["status"] == "PENDING_UNTIL_EXECUTED",
                "%s pre-run alias status is not pending" % label)
    else:
        require(alias == {
            "required": False,
            "status": "NOT_APPLICABLE_DIRECT_ARM",
            "behavior_trace_sha256": None,
            "decision_provenance_sha256": None,
            "aliases_treatment_id": None,
        }, "%s direct alias object invalid" % label)


BATCH_KEYS = {
    "schema", "contract_id", "contract_sha256", "batch_manifest_sha256", "batch_id",
    "batch_family", "execution_mode", "comparison_status", "winner", "receipt_provenance",
    "task_packet", "sealed_candidates", "world_preimages", "world_clones",
    "run_admissions", "randomization", "replication_and_ci", "claim_boundary",
}


def validate_batch(batch: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    validate_contract(contract)
    exact_keys(batch, BATCH_KEYS, "batch")
    require(batch["schema"] == BATCH_SCHEMA, "wrong batch schema")
    require(batch["contract_id"] == contract["contract_id"]
            and batch["contract_sha256"] == contract["contract_sha256"],
            "batch contract binding mismatch")
    _verify_self_hash(batch, "batch_manifest_sha256", "batch")
    require(batch["comparison_status"] == "NOT_RUN" and batch["winner"] == "NOT_EVALUATED",
            "admission batch claims execution or a winner")
    mode = batch["execution_mode"]
    require(mode == "DEVELOPMENT_SMOKE_UNSCORED",
            "actual comparison admission is blocked: trusted controller/Authority/meter/replicate/root seals are not implemented")
    require(batch["receipt_provenance"] == "DEVELOPMENT_FIXTURE_NOT_EXECUTION_EVIDENCE",
            "development smoke receipt provenance is overstated")

    task_packet_text = _verify_text_receipt(batch["task_packet"], "task_packet")
    _validate_initial_packet(task_packet_text, contract, "batch")

    family = batch["batch_family"]
    require(family in {"DIRECT_A1_A5", "COMBINED_C1_C3"}, "invalid batch family")
    required = DIRECT_TREATMENTS if family == "DIRECT_A1_A5" else COMBINED_TREATMENTS
    candidates = batch["sealed_candidates"]
    require(isinstance(candidates, list), "sealed_candidates must be a list")
    candidate_map: dict[str, Mapping[str, Any]] = {}
    ids: set[str] = set()
    for candidate in candidates:
        require(isinstance(candidate, Mapping), "invalid candidate")
        treatment = candidate.get("treatment_id")
        require(isinstance(treatment, str) and treatment not in candidate_map,
                "duplicate or invalid treatment candidate")
        _validate_candidate(candidate, contract, mode)
        candidate_map[treatment] = candidate
        require(candidate["candidate_id"] not in ids, "duplicate candidate_id")
        ids.add(candidate["candidate_id"])
    require(set(candidate_map) == required and len(candidate_map) == len(required),
            "batch family must contain exactly one candidate for each treatment and may not mix A/C")

    worlds = batch["world_preimages"]
    require(isinstance(worlds, list) and worlds, "world preimages missing")
    world_map: dict[str, Mapping[str, Any]] = {}
    witness_ids: set[str] = set()
    for world in worlds:
        exact_keys(world, {
            "world_id", "authority_stratum", "semantic_case_id_location", "preimage",
            "authority_topology_witness", "isomorphic_twin_group_id", "twin_role",
            "shared_public_prefix_sha256",
        }, "world_preimage")
        world_id = world["world_id"]
        require(isinstance(world_id, str) and world_id not in world_map, "duplicate world_id")
        require(world["authority_stratum"] in {"U", "D", "P"}, "invalid Authority stratum")
        require(world["semantic_case_id_location"] == "EVALUATOR_PRIVATE_ONLY",
                "semantic case id is not evaluator-private")
        require((world["isomorphic_twin_group_id"] is None and world["twin_role"] is None)
                or (isinstance(world["isomorphic_twin_group_id"], str)
                    and world["twin_role"] in {"S", "R"}),
                "isomorphic twin group/role invalid")
        valid_hash(world["shared_public_prefix_sha256"],
                   "world[%s].shared_public_prefix_sha256" % world_id)
        _verify_text_receipt(world["preimage"], "world[%s].preimage" % world_id)
        witness = world["authority_topology_witness"]
        _validate_authority_witness(witness, world, contract)
        require(witness["witness_id"] not in witness_ids, "duplicate Authority witness id")
        witness_ids.add(witness["witness_id"])
        world_map[world_id] = world

    clones = batch["world_clones"]
    require(isinstance(clones, list), "world_clones must be a list")
    clone_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    clone_ids: set[str] = set()
    namespaces: set[str] = set()
    keysets: set[str] = set()
    for clone in clones:
        exact_keys(clone, {
            "world_id", "treatment_id", "clone_id", "world_preimage_sha256",
            "semantic_preimage_sha256", "storage_namespace", "keyset_preimage",
            "keyset_sha256", "initial_state_preimage", "initial_state_semantic_sha256",
            "shared_mutable_state_paths", "cross_clone_channels",
        }, "world_clone")
        key = (clone["world_id"], clone["treatment_id"])
        require(key not in clone_map, "duplicate clone for world/treatment")
        require(clone["world_id"] in world_map and clone["treatment_id"] in required,
                "clone has unknown world or treatment")
        world = world_map[clone["world_id"]]
        require(clone["world_preimage_sha256"] == world["preimage"]["sha256"],
                "clone world preimage mismatch")
        require(clone["semantic_preimage_sha256"] == world["preimage"]["sha256"],
                "clone semantic preimage differs")
        valid_hash(clone["keyset_sha256"], "clone.keyset_sha256")
        require(clone["keyset_sha256"] == sha256_text(clone["keyset_preimage"]),
                "clone keyset receipt mismatch")
        valid_hash(clone["initial_state_semantic_sha256"], "clone.initial_state_semantic_sha256")
        require(clone["initial_state_semantic_sha256"] == sha256_text(clone["initial_state_preimage"]),
                "clone initial state receipt mismatch")
        require(clone["shared_mutable_state_paths"] == [], "clone shares mutable state")
        require(clone["cross_clone_channels"] == [], "clone has cross-clone channel")
        for value, seen, label in (
            (clone["clone_id"], clone_ids, "clone id"),
            (clone["storage_namespace"], namespaces, "storage namespace"),
            (clone["keyset_sha256"], keysets, "keyset"),
        ):
            require(isinstance(value, str) and value and value not in seen,
                    "world clones do not have unique %s" % label)
            seen.add(value)
        clone_map[key] = clone
    expected_clone_keys = {(world_id, treatment) for world_id in world_map for treatment in required}
    require(set(clone_map) == expected_clone_keys,
            "every world needs one independent clone per treatment")

    runs = batch["run_admissions"]
    require(isinstance(runs, list), "run_admissions must be a list")
    run_map: dict[tuple[str, str], Mapping[str, Any]] = {}
    run_ids: set[str] = set()
    common_surfaces: dict[str, Any] | None = None
    for run in runs:
        exact_keys(run, {
            "run_id", "world_id", "treatment_id", "candidate_id", "clone_id",
            "authority_witness_id", "planned_status", "launch_receipt", "trigger_receipt",
            "budget_receipt", "alias_assessment", "runtime_native_receipts_status",
        }, "run_admission")
        treatment = run["treatment_id"]
        key = (run["world_id"], treatment)
        require(key in expected_clone_keys and key not in run_map, "duplicate or unknown run binding")
        require(run["run_id"] not in run_ids, "duplicate run_id")
        run_ids.add(run["run_id"])
        candidate = candidate_map[treatment]
        clone = clone_map[key]
        world = world_map[run["world_id"]]
        require(run["candidate_id"] == candidate["candidate_id"], "run candidate mismatch")
        require(run["clone_id"] == clone["clone_id"], "run clone mismatch")
        require(run["authority_witness_id"] == world["authority_topology_witness"]["witness_id"],
                "run Authority witness mismatch")
        expected_status = "NOT_APPLICABLE" if (
            treatment == "A1-LAWFUL-CENTER" and world["authority_stratum"] == "P"
        ) else "SEALED_NOT_RUN"
        require(run["planned_status"] == expected_status,
                "%s has wrong applicability/status" % treatment)
        require(run["runtime_native_receipts_status"]
                == contract["runtime_native_receipt_policy"]["pre_run_status"],
                "%s improperly claims native runtime receipts before execution" % run["run_id"])
        surfaces = _validate_launch(run["launch_receipt"], contract, run["run_id"])
        if common_surfaces is None:
            common_surfaces = surfaces
        else:
            require(surfaces == common_surfaces,
                    "%s actual payload/argv/env/cwd/process/fd/network/endpoint surface differs" % run["run_id"])
        _validate_trigger(run["trigger_receipt"], clone, contract, mode, run["run_id"])
        _validate_budget(run["budget_receipt"], contract, treatment, run["run_id"])
        _validate_alias(run["alias_assessment"], treatment, run["run_id"])
        run_map[key] = run
    require(set(run_map) == expected_clone_keys, "missing run admission for a world/treatment clone")

    twin_groups: dict[str, list[Mapping[str, Any]]] = {}
    for world in worlds:
        if world["isomorphic_twin_group_id"] is not None:
            twin_groups.setdefault(world["isomorphic_twin_group_id"], []).append(world)
    for group_id, members in twin_groups.items():
        require(len(members) == 2 and {item["twin_role"] for item in members} == {"S", "R"},
                "isomorphic twin %s must contain exactly S/R" % group_id)
        require(len({item["shared_public_prefix_sha256"] for item in members}) == 1,
                "isomorphic twin %s differs before the sealed boundary" % group_id)

    randomization = batch["randomization"]
    exact_keys(randomization, {
        "algorithm", "seed_commitment_sha256", "seed_reveal_status",
        "ordered_run_ids", "order_commitment_sha256", "evaluator_private",
    }, "randomization")
    valid_hash(randomization["seed_commitment_sha256"], "randomization.seed_commitment")
    require(randomization["seed_reveal_status"] == "SEALED_NOT_REVEALED",
            "random seed was revealed before batch close")
    ordered = randomization["ordered_run_ids"]
    require(isinstance(ordered, list) and len(ordered) == len(set(ordered))
            and set(ordered) == run_ids, "randomized order is not an exact run permutation")
    valid_hash(randomization["order_commitment_sha256"], "randomization.order_commitment")
    require(randomization["order_commitment_sha256"] == sha256_value(ordered),
            "randomized order commitment mismatch")
    require(randomization["evaluator_private"] is True, "run order is not evaluator-private")

    reps = batch["replication_and_ci"]
    exact_keys(reps, {
        "replicates_per_world_treatment", "ci_method", "ci_level", "ci_status",
        "fixed_stop_rule", "optional_stopping", "repair_rule",
    }, "replication_and_ci")
    policy = contract["randomization_replication_ci"]
    require(reps["replicates_per_world_treatment"] == 1,
            "development smoke must remain one unscored replicate")
    require(reps["ci_method"] == policy["ci_method"] and reps["ci_level"] == policy["ci_level"],
            "CI method/level changed")
    require(reps["ci_status"] == "NOT_COMPUTED_COMPARISON_NOT_RUN",
            "CI computed before comparison")
    require(reps["fixed_stop_rule"] == policy["fixed_stop_rule"], "stop rule changed")
    require(reps["optional_stopping"] is False, "optional stopping enabled")
    require(reps["repair_rule"] == "NEW_BATCH_AND_ALL_FAMILY_TREATMENTS",
            "post-result repair can preserve favorable arms")

    exact_keys(batch["claim_boundary"], {
        "development_smoke_unscored", "admission_is_not_execution",
        "comparative_evidence", "winner_claim_allowed",
    }, "batch.claim_boundary")
    require(batch["claim_boundary"] == {
        "development_smoke_unscored": mode == "DEVELOPMENT_SMOKE_UNSCORED",
        "admission_is_not_execution": True,
        "comparative_evidence": "NONE",
        "winner_claim_allowed": False,
    }, "batch claim boundary mismatch")

    return {
        "status": "DEVELOPMENT_SMOKE_ADMISSION_ACCEPTED_UNSCORED_NOT_EXECUTED",
        "batch_id": batch["batch_id"],
        "family": family,
        "candidate_count": len(candidate_map),
        "world_count": len(world_map),
        "run_count": len(run_map),
        "comparison_status": "NOT_RUN",
        "winner": "NOT_EVALUATED",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("batch", type=Path)
    args = parser.parse_args()
    try:
        contract = load_json(args.contract)
        result = validate_batch(load_json(args.batch), contract)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (AdmissionError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({
            "status": "SEALED_RUN_ADMISSION_REJECTED",
            "error": str(exc),
            "comparison_status": "NOT_RUN",
            "winner": "NOT_EVALUATED",
        }, ensure_ascii=False, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
