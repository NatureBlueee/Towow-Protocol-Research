#!/usr/bin/env python3
"""Static validator for the Wave 021 CE-001 A1-A5 fairness preregistration.

This validator establishes comparison admission only.  It does not execute an
arm, score a result, or select a winner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence


CONTRACT_SCHEMA = "CE001_FAIR_BASELINE_CONTRACT_V1"
PLAN_SCHEMA = "CE001_FAIR_BATCH_PLAN_V1"
FAILURE_TRIGGER_SCHEMA = "CE001_FAILURE_TRIGGER_SPEC_V1"
REQUIRED_ARMS = {
    "A1-LAWFUL-CENTER",
    "A2-EQUAL-INFORMATION-CENTER",
    "A3-GENERAL-MODEL-MATURE-STACK",
    "A4-DETERMINISTIC-MATURE-COMPOSITION",
    "A5-BOUNDED-HUMAN-INSTITUTION",
}
REQUIRED_METRIC_GROUPS = {
    "task_completion",
    "unique_effect",
    "exact_effect_evidence",
    "acceptance",
    "wrong_actions",
    "disclosure_cost",
    "coordination_cost",
    "recovery_cost",
}


class FairnessError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FairnessError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "%s must contain one JSON object" % path)
    return value


def _profile_ids(contract: Mapping[str, Any]) -> Dict[str, str]:
    profiles = contract["common_profiles"]
    return {
        "initial_view_profile_id": profiles["initial_view"]["profile_id"],
        "interaction_budget_profile_id": profiles["interaction_budget"]["profile_id"],
        "disclosure_policy_id": profiles["disclosure_policy"]["profile_id"],
        "effect_evidence_profile_id": profiles["effect_evidence"]["profile_id"],
        "failure_plan_id": profiles["failure_injection"]["profile_id"],
    }


def _arm_map(contract: Mapping[str, Any]) -> Dict[str, Mapping[str, Any]]:
    arms = contract.get("arm_definitions")
    require(isinstance(arms, list), "arm_definitions must be a list")
    require(
        all(isinstance(arm, Mapping) and isinstance(arm.get("arm_id"), str) for arm in arms),
        "arm_definitions contains an invalid arm",
    )
    result = {arm["arm_id"]: arm for arm in arms}
    require(len(result) == len(arms), "duplicate arm definition")
    return result


def validate_contract(
    contract: Mapping[str, Any],
    *,
    source_root: Path | None = None,
) -> Dict[str, Any]:
    require(contract.get("schema") == CONTRACT_SCHEMA, "wrong contract schema")
    require(
        contract.get("status") == "PREREGISTERED_NO_COMPARATIVE_RUNS_NO_WINNER",
        "contract status improperly claims a run or winner",
    )
    claimed_hash = contract.get("contract_sha256")
    require(
        isinstance(claimed_hash, str) and len(claimed_hash) == 64,
        "contract_sha256 missing",
    )
    body = dict(contract)
    body.pop("contract_sha256", None)
    actual_hash = sha256_value(body)
    require(claimed_hash == actual_hash, "contract_sha256 mismatch")

    task = contract.get("task_contract", {})
    require(task.get("q_version") == "Q@v1", "task Q changed")
    require(task.get("target_id") == "VenueV:CircuitC7", "task Target changed")
    require(task.get("deadline_minute") == 90, "task deadline changed")
    require(task.get("required_duration_minutes") == 45, "task duration changed")
    require(task.get("required_power_kw") == 3.0, "task power changed")
    require(task.get("power_tolerance_percent") == 5, "task tolerance changed")
    require(task.get("other_circuits_energized") == [], "other circuits allowed")
    require(task.get("task_substitution_forbidden") is True, "task substitution not blocked")

    arms = _arm_map(contract)
    require(set(arms) == REQUIRED_ARMS, "A1-A5 arm set is incomplete or expanded")
    profile_ids = _profile_ids(contract)
    for arm_id, arm in arms.items():
        for field, value in profile_ids.items():
            require(
                arm.get(field) == value,
                "%s does not share %s" % (arm_id, field),
            )
    require(
        set(arms["A1-LAWFUL-CENTER"]["applicability_strata"]) == {"U", "D"},
        "A1 applicability must be exactly U/D",
    )
    for arm_id in REQUIRED_ARMS - {"A1-LAWFUL-CENTER"}:
        require(
            set(arms[arm_id]["applicability_strata"]) == {"U", "D", "P"},
            "%s must preserve U/D/P applicability" % arm_id,
        )

    profiles = contract["common_profiles"]
    view = profiles["initial_view"]
    allowlist = view.get("allowlist")
    forbidden = set(view.get("forbidden_fields_or_channels", []))
    require(isinstance(allowlist, list) and len(allowlist) == len(set(allowlist)), "bad allowlist")
    require(not (set(allowlist) & forbidden), "initial allowlist exposes forbidden fields")
    require(
        view.get("projection_mode") == "EXPLICIT_ALLOWLIST_FAIL_CLOSED",
        "public view is not fail-closed",
    )
    budget = profiles["interaction_budget"]
    for zero_field in (
        "evaluated_episode_reruns_max",
        "grader_feedback_reads_max",
        "private_truth_reads_max",
        "prior_arm_transcript_reads_max",
    ):
        require(budget.get(zero_field) == 0, "%s must remain zero" % zero_field)
    require(budget.get("budget_overrides_allowed") is False, "budget overrides allowed")
    require(
        budget.get("sufficiency_status")
        == "NOT_ESTABLISHED_UNTIL_ALL_ARM_PREFLIGHTS",
        "budget adequacy is overstated",
    )
    failure = profiles["failure_injection"]
    require(failure.get("controller_private") is True, "failure plan is not private")
    require(failure.get("arm_visible_flags") == [], "failure flags exposed")
    require(
        failure.get("same_semantic_schedule_across_arm_clones") is True,
        "failure schedule differs across arms",
    )
    require(
        failure.get("e3_pair_first_public_difference")
        == "EXACT_TARGET_STATUS_OR_READBACK",
        "E3 pair may diverge before exact Target readback",
    )
    trigger = failure.get("trigger_equivalence", {})
    require(
        trigger.get("basis") == "SEMANTIC_NATIVE_BOUNDARY",
        "failure equality is not defined at semantic native boundary",
    )
    require(
        set(trigger.get("required_bindings", []))
        >= {
            "equivalent_event_class",
            "current_owner_head_set",
            "Target_prefix_semantic_digest",
        },
        "failure trigger lacks semantic/head/Target-prefix binding",
    )
    for forbidden_mode in (
        "raw_event_ordinal_only_forbidden",
        "raw_trace_length_only_forbidden",
        "wall_time_only_forbidden",
        "raw_event_hash_only_forbidden",
    ):
        require(trigger.get(forbidden_mode) is True, "%s not forbidden" % forbidden_mode)
    require(
        trigger.get("clone_specific_trigger_visible_to_arm") is False,
        "clone-specific failure trigger is visible to an arm",
    )
    disclosure = profiles["disclosure_policy"]
    require(
        disclosure.get("same_initial_semantic_task_bytes_after_alpha_normalization")
        is True,
        "initial task semantics need not match",
    )
    alpha_fields = set(disclosure.get("alpha_renaming_allowlist", []))
    require(
        alpha_fields
        <= {
            "arm_binding_token",
            "opaque_episode_handle",
            "opaque_run_binding",
            "operation_id",
        },
        "alpha normalization can erase task semantics",
    )
    require(
        not alpha_fields
        & {
            "q_version",
            "object_id",
            "target_id",
            "deadline_minute",
            "required_duration_minutes",
            "required_power_kw",
            "power_tolerance_percent",
        },
        "alpha normalization erases task coordinates",
    )
    effect = profiles["effect_evidence"]
    require(effect.get("profile_id") == "CE001-EXACT-EFFECT-EVIDENCE@v1", "wrong Effect gate")
    require(effect.get("sample_count") == 46, "Effect gate does not require 46 samples")
    require(
        effect.get("sample_offsets") == "0..45_CONTIGUOUS_UNIQUE",
        "Effect gate does not require continuous unique offsets",
    )
    require(effect.get("sample_target_id") == "VenueV:CircuitC7", "sample Target gate missing")
    require(effect.get("sample_other_circuits_energized") == [], "sample circuit gate missing")
    require(
        effect.get("sample_power_min_kw") == 2.85
        and effect.get("sample_power_max_kw") == 3.15,
        "sample tolerance gate missing",
    )
    require(
        effect.get("sample_safety_ok") is True
        and effect.get("sample_noise_ok") is True,
        "sample safety/noise gate missing",
    )
    require(effect.get("duration_minutes") == 45, "Effect duration gate missing")
    require(
        effect.get("deadline_rule") == "effect_start_minute+45<=deadline_minute",
        "Effect deadline gate missing",
    )
    require(
        effect.get("top_level_other_circuits_energized") == [],
        "occurrence circuit gate missing",
    )
    require(effect.get("count_only_scoring_forbidden") is True, "count-only Effect scoring allowed")

    metrics = contract.get("preregistered_metrics", {})
    require(
        REQUIRED_METRIC_GROUPS <= set(metrics),
        "pre-registered metric groups incomplete",
    )
    reporting = metrics.get("reporting", {})
    require(reporting.get("single_composite_score") is False, "single score enabled")
    require(reporting.get("raw_vector_required") is True, "raw result vector not required")
    require(reporting.get("safety_gate_before_cost_ranking") is True, "cost may outrank safety")

    boundary = contract.get("claim_boundary", {})
    require(boundary.get("final_winner_claim_allowed") is False, "winner claim enabled")
    require(
        contract.get("evidence_boundary", {}).get("comparative_evidence") == "NONE",
        "component results mislabeled as comparative evidence",
    )
    require(
        contract.get("existing_technology_arms", {}).get("a6_allowed") is False,
        "A6 opened before A1-A5 comparison",
    )

    if source_root is not None:
        root = Path(source_root).resolve()
        sources = contract.get("source_bindings")
        require(isinstance(sources, list) and sources, "source bindings missing")
        for source in sources:
            path = (root / source["path"]).resolve()
            require(path.is_relative_to(root), "source escapes frozen root")
            require(path.is_file(), "source missing: %s" % source["path"])
            require(
                sha256_file(path) == source["sha256"],
                "source hash drift: %s" % source["path"],
            )

    return {
        "status": "FAIRNESS_CONTRACT_ACCEPTED_NO_RUN_NO_WINNER",
        "contract_id": contract["contract_id"],
        "contract_sha256": claimed_hash,
        "arm_count": len(arms),
        "source_count": len(contract.get("source_bindings", [])),
    }


def _reject_forbidden_fields(
    fields: Iterable[Any],
    *,
    allowed: Sequence[str],
    arm_id: str,
) -> None:
    actual = list(fields)
    require(all(isinstance(field, str) for field in actual), "%s has non-string field" % arm_id)
    require(
        set(actual) == set(allowed) and len(actual) == len(allowed),
        "%s initial public fields differ from common allowlist" % arm_id,
    )


def validate_batch_plan(
    plan: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    validate_contract(contract)
    require(plan.get("schema") == PLAN_SCHEMA, "wrong batch plan schema")
    require(plan.get("contract_id") == contract["contract_id"], "plan contract mismatch")
    require(
        plan.get("semantic_case_id_location") == "EVALUATOR_PRIVATE_ONLY",
        "semantic case label is not evaluator-private",
    )
    public_hash = plan.get("shared_task_projection_sha256")
    require(
        isinstance(public_hash, str) and len(public_hash) == 64,
        "shared task projection hash missing",
    )
    failure_plan_id = contract["common_profiles"]["failure_injection"]["profile_id"]
    require(plan.get("failure_plan_id") == failure_plan_id, "batch failure plan mismatch")

    arm_runs = plan.get("arm_runs")
    require(isinstance(arm_runs, list), "arm_runs must be a list")
    run_map = {
        run.get("arm_id"): run
        for run in arm_runs
        if isinstance(run, Mapping) and isinstance(run.get("arm_id"), str)
    }
    require(len(run_map) == len(arm_runs), "duplicate or invalid arm run")
    require(set(run_map) == REQUIRED_ARMS, "batch must contain exactly A1-A5")

    profile_ids = _profile_ids(contract)
    allowlist = contract["common_profiles"]["initial_view"]["allowlist"]
    stratum = plan.get("evaluator_private_authority_stratum")
    require(stratum in {"U", "D", "P"}, "invalid evaluator-private Authority stratum")

    for arm_id, run in run_map.items():
        require(
            run.get("shared_task_projection_sha256") == public_hash,
            "%s received different initial task semantics" % arm_id,
        )
        _reject_forbidden_fields(
            run.get("initial_public_field_names", []),
            allowed=allowlist,
            arm_id=arm_id,
        )
        for field, value in profile_ids.items():
            require(run.get(field) == value, "%s differs on %s" % (arm_id, field))
        require(
            run.get("visible_failure_plan_fields") == [],
            "%s can see hidden failure injection" % arm_id,
        )
        require(run.get("private_truth_access") is False, "%s has private truth oracle" % arm_id)
        require(run.get("grader_feedback_access") is False, "%s has grader oracle" % arm_id)
        require(
            run.get("prior_arm_transcript_access") is False,
            "%s has cross-arm answer transfer" % arm_id,
        )
        require(
            run.get("evaluated_episode_reruns") == 0,
            "%s has post-evaluation reruns" % arm_id,
        )
        require(run.get("budget_overrides") == {}, "%s has an extra budget" % arm_id)

    a1 = run_map["A1-LAWFUL-CENTER"]
    if stratum == "P":
        require(
            a1.get("planned_status") == "NOT_APPLICABLE",
            "A1 must be NOT_APPLICABLE in P",
        )
    else:
        require(a1.get("planned_status") == "PLANNED", "A1 missing in lawful U/D clone")

    return {
        "status": "FAIR_BATCH_PLAN_ACCEPTED_NOT_EXECUTED",
        "batch_id": plan.get("batch_id"),
        "arm_count": len(run_map),
        "authority_stratum": stratum,
    }


def collect_batch_errors(
    plan: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Sequence[str]:
    """Return all independently detectable per-arm fairness defects."""
    errors = []
    try:
        validate_batch_plan(plan, contract)
        return errors
    except FairnessError as exc:
        errors.append(str(exc))

    profile_ids = _profile_ids(contract)
    allowlist = set(contract["common_profiles"]["initial_view"]["allowlist"])
    public_hash = plan.get("shared_task_projection_sha256")
    for run in plan.get("arm_runs", []):
        if not isinstance(run, Mapping):
            errors.append("invalid arm run")
            continue
        arm_id = str(run.get("arm_id"))
        extras = set(run.get("initial_public_field_names", [])) - allowlist
        if extras:
            errors.append("%s extra initial fields: %s" % (arm_id, sorted(extras)))
        if run.get("shared_task_projection_sha256") != public_hash:
            errors.append("%s different initial task semantics" % arm_id)
        for field, value in profile_ids.items():
            if run.get(field) != value:
                errors.append("%s differs on %s" % (arm_id, field))
        if run.get("visible_failure_plan_fields"):
            errors.append("%s visible failure oracle" % arm_id)
        if run.get("private_truth_access") is not False:
            errors.append("%s private truth oracle" % arm_id)
        if run.get("grader_feedback_access") is not False:
            errors.append("%s grader oracle" % arm_id)
        if run.get("prior_arm_transcript_access") is not False:
            errors.append("%s cross-arm answer transfer" % arm_id)
        if run.get("evaluated_episode_reruns") != 0:
            errors.append("%s post-evaluation rerun" % arm_id)
        if run.get("budget_overrides") != {}:
            errors.append("%s budget override" % arm_id)
    return errors


def validate_failure_trigger_spec(
    spec: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    validate_contract(contract)
    require(spec.get("schema") == FAILURE_TRIGGER_SCHEMA, "wrong failure trigger schema")
    require(spec.get("contract_id") == contract["contract_id"], "trigger contract mismatch")
    expected = contract["common_profiles"]["failure_injection"]
    require(spec.get("failure_plan_id") == expected["profile_id"], "trigger plan mismatch")
    require(
        spec.get("basis") == "SEMANTIC_NATIVE_BOUNDARY",
        "failure trigger uses raw ordinal/timing/hash instead of semantic native boundary",
    )
    for field in (
        "equivalent_event_class_bound",
        "current_owner_head_set_bound",
        "Target_prefix_semantic_digest_bound",
    ):
        require(spec.get(field) is True, "failure trigger missing %s" % field)
    require(
        spec.get("clone_specific_trigger_visible_to_arm") is False,
        "clone-specific failure trigger exposed",
    )
    for field in (
        "uses_raw_event_ordinal_only",
        "uses_raw_trace_length_only",
        "uses_wall_time_only",
        "uses_raw_event_hash_only",
    ):
        require(spec.get(field) is False, "failure trigger improperly uses %s" % field)
    return {
        "status": "SEMANTIC_FAILURE_TRIGGER_ACCEPTED_NOT_EXECUTED",
        "failure_plan_id": spec["failure_plan_id"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--failure-trigger", type=Path)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()

    try:
        contract = load_json(args.contract)
        result = validate_contract(contract, source_root=args.source_root)
        if args.plan is not None:
            result["batch_plan"] = validate_batch_plan(load_json(args.plan), contract)
        if args.failure_trigger is not None:
            result["failure_trigger"] = validate_failure_trigger_spec(
                load_json(args.failure_trigger),
                contract,
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (FairnessError, OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"status": "FAIRNESS_ADMISSION_REJECTED", "error": str(exc)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
