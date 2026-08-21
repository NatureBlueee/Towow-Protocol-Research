#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from g3disc.common import canonical_sha256, dump_json, load_json, receipt_ref


ROOT = Path(__file__).resolve().parent
PUBLIC_PATH = ROOT / "fixtures" / "public-worlds.json"
PRIVATE_PATH = ROOT / "private" / "oracles.json"
WORKERS = ROOT / "workers"
OUTPUTS = ROOT / "outputs"

ARMS = [
    "B-CENTER-EQUAL-ENVELOPE",
    "B-CENTER-LEGAL-CONTROL",
    "B-MATURE-PLANNER-WORKFLOW",
    "B-HUMAN-RULE",
    "C-FORMATION",
]

def run_worker(filename: str, job: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(WORKERS / filename)],
        input=json.dumps(job, ensure_ascii=False, sort_keys=True),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{filename} failed ({completed.returncode}): {completed.stderr.strip()}"
        )
    return json.loads(completed.stdout)


def tri(value: bool | None) -> str:
    if value is None:
        return "UNKNOWN"
    return "TRUE" if value else "FALSE"


def task_object(public_world: dict[str, Any]) -> dict[str, Any]:
    episode = public_world["episode"]
    return {
        "q": episode["q"],
        "v0": episode["v0"],
        "principals": episode["principals"],
        "authority": episode["authority"],
    }


def apply_task_changes(
    original: dict[str, Any], changes: list[dict[str, Any]]
) -> dict[str, Any]:
    result = copy.deepcopy(original)
    for change in changes:
        path = change["path"]
        if path == "/q":
            result["q"] = change["after_value"]
        elif path == "/v0/minimum_integrity":
            result["v0"]["minimum_integrity"] = change["after_value"]
        elif path == "/principals":
            result["principals"] = change["after_value"]
        elif path == "/authority":
            result["authority"] = change["after_value"]
        else:
            raise ValueError(f"unsupported material task path: {path}")
    return result


def make_task_diff(
    public_world: dict[str, Any],
    policy: dict[str, Any],
    private_oracle: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    original = task_object(public_world)
    proposal = public_world["task_change_proposal"]
    if proposal is None:
        task_hash = canonical_sha256(original)
        return (
            "INVARIANT",
            {
                "classification": "UNCHANGED",
                "original_task_sha256": task_hash,
                "result_task_sha256": task_hash,
                "material_fields": [],
                "changes": [],
                "owner_authorization_receipts": [],
                "controller_claim_refs": [],
            },
        )
    changes = proposal["changes"]
    result = apply_task_changes(original, changes)
    action_ids = policy["action_ids"]
    owner_authorized = (
        "request_owner_change" in action_ids
        and private_oracle["actual_response"] == "APPROVE"
    )
    if owner_authorized:
        classification = "OWNER_AUTHORIZED_NEW_EPISODE"
        t_value = "OWNER_AUTHORIZED_NEW_EPISODE"
        owner_receipts = [
            receipt_ref(
                f"{public_world['world_id']}:owner-authorized-task-diff",
                "owner",
            )
        ]
        controller_refs: list[dict[str, str]] = []
    elif "controller_rewrite" in action_ids:
        classification = "CONTROLLER_SUBSTITUTION"
        t_value = "CONTROLLER_SUBSTITUTION"
        owner_receipts = []
        controller_refs = [
            receipt_ref(
                f"{public_world['world_id']}:controller-claimed-task-diff",
                "controller",
            )
        ]
    else:
        task_hash = canonical_sha256(original)
        return (
            "INVARIANT",
            {
                "classification": "UNCHANGED",
                "original_task_sha256": task_hash,
                "result_task_sha256": task_hash,
                "material_fields": [],
                "changes": [],
                "owner_authorization_receipts": [],
                "controller_claim_refs": [],
            },
        )
    return (
        t_value,
        {
            "classification": classification,
            "original_task_sha256": canonical_sha256(original),
            "result_task_sha256": canonical_sha256(result),
            "material_fields": [change["path"] for change in changes],
            "changes": changes,
            "owner_authorization_receipts": owner_receipts,
            "controller_claim_refs": controller_refs,
        },
    )


def inventory_receipt(public_world: dict[str, Any]) -> dict[str, Any]:
    inventory = copy.deepcopy(public_world["inventory"])
    inventory["evidence_sha256"] = canonical_sha256(
        {
            "world_id": public_world["world_id"],
            "inventory": public_world["inventory"],
        }
    )
    return inventory


def classify(
    body: dict[str, Any],
    *,
    old_result: str,
    extended_result: str,
) -> tuple[str, str]:
    if body["T"] == "OWNER_AUTHORIZED_NEW_EPISODE":
        return (
            "AUTHORIZED_NEW_EPISODE",
            "G3_OWNER_AUTHORIZED_MATERIAL_GOAL_CHANGE",
        )
    if body["T"] == "CONTROLLER_SUBSTITUTION":
        return (
            "INVALID_SUBSTITUTION",
            "G3_CONTROLLER_INVALID_SUBSTITUTION",
        )
    if any(
        body["inventory_completeness"][key] != "COMPLETE"
        for key in [
            "action_inventory",
            "response_family",
            "observation_kernel",
            "transition_semantics",
        ]
    ):
        return ("UNKNOWN", "G3_OPEN_INVENTORY_UNRESOLVED_MODEL")
    if (
        body["C"] == "SAT"
        and body["R"]["R_measurable_exists"] == "TRUE"
        and body["R"]["R_actual"] == "FALSE"
    ):
        return (
            "ACTUAL_POLICY_MISS",
            "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS",
        )
    if (
        old_result == "UNSAT"
        and extended_result == "SAT"
        and body["R"]["R_actual"] == "TRUE"
        and body["V"] == "VALID"
        and body["counterfactual"]["remove_result"] == "UNSAT"
    ):
        return (
            "QUALIFIED_CONDITION_FORMATION",
            "G3_COMPLETE_OLD_CLOSURE_UNSAT_LEGAL_EXTENSION_SAT",
        )
    if (
        body["C"] == "SAT"
        and body["N"] == "NEW_TOKEN"
        and body["V"] == "VALID"
        and body["counterfactual"]["remove_result"] == "UNSAT"
    ):
        return (
            "PREFIX_SAT_NEW_TOKEN",
            "G3_OLD_POLICY_CREATED_TOKEN_WITHOUT_KERNEL_CHANGE",
        )
    if body["C"] == "SAT" and body["R"]["R_actual"] == "TRUE":
        return (
            "PREEXISTING_QUALIFIED_PATH",
            "G3_DIRECT_OR_EXTANT_QUALIFIED_PATH",
        )
    if (
        body["C"] == "UNSAT"
        and body["R"]["R_physical_exists"] == "FALSE"
        and body["R"]["R_measurable_exists"] == "FALSE"
        and body["inventory_completeness"]["search_bound_frozen"]
    ):
        return ("BOUNDED_UNREACHABLE", "G3_BOUNDED_UNREACHABLE")
    return ("NO_QUALIFIED_EFFECT", "G3_NO_QUALIFIED_EFFECT")


def evaluate_one(
    public_world: dict[str, Any],
    private_oracle: dict[str, Any],
    arm_id: str,
    arm_envelope: dict[str, Any],
) -> dict[str, Any]:
    # The policy subprocess receives no private oracle, scorer output, or expected label.
    policy = run_worker(
        "actual_policy_worker.py",
        {
            "public_world": public_world,
            "arm_id": arm_id,
            "arm_envelope": arm_envelope,
        },
    )
    frozen_policy_hash = canonical_sha256(policy)
    inventory = inventory_receipt(public_world)
    closure = run_worker(
        "closure_oracle_worker.py",
        {
            "private_oracle": private_oracle,
            "horizon": inventory["horizon"],
            "inventory": public_world["inventory"],
        },
    )
    measurable = run_worker(
        "measurable_oracle_worker.py",
        {
            "private_oracle": private_oracle,
            "inventory": public_world["inventory"],
        },
    )
    extra_actions: list[dict[str, Any]] = []
    robust = run_worker(
        "robust_worker.py",
        {
            "private_oracle": private_oracle,
            "frozen_action_ids": policy["action_ids"],
            "extra_actions": extra_actions,
        },
    )
    actual_branch = next(
        branch
        for branch in robust["branches"]
        if branch["response"] == private_oracle["actual_response"]
    )

    extension_ids = {
        action["id"] for action in private_oracle.get("extension_actions", [])
    }
    operator_ids = list(private_oracle["pre_registered_intervention_ids"])
    if operator_ids:
        counterfactual_raw = run_worker(
            "counterfactual_worker.py",
            {
                "private_oracle": private_oracle,
                "frozen_action_ids": policy["action_ids"],
                "operator_ids": operator_ids,
                "extra_actions": extra_actions,
            },
        )
        counterfactual = {
            "status": (
                "APPLICABLE"
                if counterfactual_raw["derived_effect_graph_valid"]
                and counterfactual_raw["derived_effect_reset_verified"]
                else "UNKNOWN"
            ),
            "operator_ids": operator_ids,
            "remove_result": (
                counterfactual_raw["remove"]["result"]
                if counterfactual_raw["derived_effect_graph_valid"]
                else "UNKNOWN"
            ),
            "reverse_result": (
                counterfactual_raw["reverse"]["result"]
                if counterfactual_raw["derived_effect_graph_valid"]
                else "UNKNOWN"
            ),
            "block_result": (
                counterfactual_raw["block"]["result"]
                if counterfactual_raw["derived_effect_graph_valid"]
                else "UNKNOWN"
            ),
            "evidence_sha256": canonical_sha256(counterfactual_raw),
        }
    else:
        counterfactual_raw = {
            "worker": "frozen-trace-counterfactual-v1",
            "status": "NOT_APPLICABLE",
            "frozen_policy_sha256": frozen_policy_hash,
        }
        counterfactual = {
            "status": "NOT_APPLICABLE",
            "operator_ids": [],
            "remove_result": "NOT_APPLICABLE",
            "reverse_result": "NOT_APPLICABLE",
            "block_result": "NOT_APPLICABLE",
            "evidence_sha256": canonical_sha256(counterfactual_raw),
        }

    complete = all(
        inventory[key] == "COMPLETE"
        for key in [
            "action_inventory",
            "response_family",
            "observation_kernel",
            "transition_semantics",
        ]
    )
    old_result = closure["old_closure"]["result"]
    extended_result = closure["extended_closure"]["result"]
    c_value = old_result if complete else "UNKNOWN"
    final_facts = set(actual_branch["final_facts"])
    token_equivalence = private_oracle["operative_token_equivalence"]
    newly_present_equivalent_tokens = (
        set(token_equivalence["new_token_facts"]) & final_facts
    ) - set(token_equivalence["s0_equivalent_tokens"])
    if newly_present_equivalent_tokens:
        n_value = "NEW_TOKEN"
    elif "extant_activated" in final_facts:
        n_value = "EXTANT_ACTIVATED"
    else:
        n_value = "NONE"
    extension_applied = any(
        step["applied"] and step["action_id"] in extension_ids
        for step in actual_branch["steps"]
    )
    e_value = "CHANGED" if extension_applied else "SAME"
    t_value, task_diff = make_task_diff(public_world, policy, private_oracle)
    counterfactual_invalid = (
        bool(operator_ids)
        and counterfactual["status"] != "APPLICABLE"
    )
    if t_value == "CONTROLLER_SUBSTITUTION" or counterfactual_invalid:
        v_value = "INVALID"
    elif not actual_branch["valid"]:
        v_value = "INVALID"
    else:
        v_value = "VALID"

    if complete:
        physical = extended_result == "SAT"
        measurable_exists: bool | None = measurable["result"] == "SAT"
    else:
        physical = None
        measurable_exists = None
    body = {
        "C": c_value,
        "N": n_value,
        "E": e_value,
        "T": t_value,
        "V": v_value,
        "R": {
            "R_physical_exists": tri(physical),
            "R_measurable_exists": tri(measurable_exists),
            "R_actual": tri(
                actual_branch["goal_reached"]
                or actual_branch["terminal_safe"]
            ),
            "R_effect_robust": tri(robust["effect_robust"]),
            "R_safe_robust": tri(robust["safe_robust"]),
            "R_terminal_robust": tri(robust["terminal_robust"]),
        },
        "inventory_completeness": inventory,
        "counterfactual": counterfactual,
        "task_diff": task_diff,
    }
    category, reason_code = classify(
        body,
        old_result=old_result,
        extended_result=extended_result,
    )
    receipt = {
        "receipt_ref": receipt_ref(
            f"{public_world['world_id']}:{arm_id}:g3",
            "wave011-g3-evaluator",
        ),
        "body_sha256": canonical_sha256(body),
        "body": body,
    }
    actual_policy_transcript = {
        "frozen_before_scoring": True,
        "policy_sha256": frozen_policy_hash,
        "method_return": policy,
        "actual_response": private_oracle["actual_response"],
        "execution": actual_branch,
    }
    oracle_receipts = {
        "closure": closure,
        "measurable": measurable,
        "robust": robust,
        "counterfactual": counterfactual_raw,
    }
    evidence_binding = {
        "g3_body_sha256": receipt["body_sha256"],
        "actual_policy_transcript_sha256": canonical_sha256(
            actual_policy_transcript
        ),
        "oracle_receipts_sha256": canonical_sha256(oracle_receipts),
        "exact_task_diff_sha256": canonical_sha256(task_diff),
    }
    evidence_binding["binding_sha256"] = canonical_sha256(evidence_binding)
    return {
        "world_id": public_world["world_id"],
        "arm_id": arm_id,
        "environment_variant": policy["environment_variant"],
        "comparison_scope": policy["comparison_scope"],
        "category": category,
        "reason_code": reason_code,
        "g3_receipt": receipt,
        "actual_policy_transcript": actual_policy_transcript,
        "oracle_receipts": oracle_receipts,
        "exact_task_diff": task_diff,
        "evidence_binding": evidence_binding,
    }


def run(selected_world: str | None = None, selected_arm: str | None = None) -> dict[str, Any]:
    public_bundle = load_json(PUBLIC_PATH)
    private_bundle = load_json(PRIVATE_PATH)
    worlds = public_bundle["worlds"]
    if selected_world is not None:
        worlds = [world for world in worlds if world["world_id"] == selected_world]
        if not worlds:
            raise ValueError(f"unknown world: {selected_world}")
    arms = [selected_arm] if selected_arm is not None else ARMS
    unknown_arms = set(arms) - set(ARMS)
    if unknown_arms:
        raise ValueError(f"unknown arms: {sorted(unknown_arms)}")

    results = []
    for world in worlds:
        private_oracle = private_bundle["worlds"][world["world_id"]]
        for arm_id in arms:
            result = evaluate_one(
                world,
                private_oracle,
                arm_id,
                public_bundle["baseline_envelopes"][arm_id],
            )
            results.append(result)
            dump_json(
                OUTPUTS / "runs" / f"{world['world_id']}__{arm_id}.json",
                result,
            )
    report = {
        "schema_version": "wave011-g3-discriminator-report-v1",
        "status": "LOCAL_SYNTHETIC_QUANTIFIER_DISCRIMINATOR",
        "world_count": len(worlds),
        "arm_count": len(arms),
        "result_count": len(results),
        "public_fixture_sha256": canonical_sha256(public_bundle),
        "private_oracle_sha256": canonical_sha256(private_bundle),
        "separation": {
            "actual_policy_worker_received_private_oracle": False,
            "method_formation_witness_received_private_oracle": False,
            "policy_frozen_before_oracle_scoring": True,
            "closure_measurable_robust_counterfactual_processes_separate": True,
        },
        "results": results,
    }
    dump_json(OUTPUTS / "report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world")
    parser.add_argument("--arm")
    args = parser.parse_args()
    report = run(args.world, args.arm)
    summary = {
        "world_count": report["world_count"],
        "arm_count": report["arm_count"],
        "result_count": report["result_count"],
        "categories": sorted({item["category"] for item in report["results"]}),
        "report": str(OUTPUTS / "report.json"),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
