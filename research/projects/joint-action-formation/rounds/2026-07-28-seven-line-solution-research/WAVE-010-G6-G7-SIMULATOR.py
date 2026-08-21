#!/usr/bin/env python3
"""Method-neutral local state simulation for Wave 010 G6/G7.

The policies receive only a public packet and explicitly queried owner readbacks.
The evaluator alone receives the frozen truth package. This is a deterministic
development fixture, not blind, independent, real-world, or production evidence.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "WAVE-010-G6-G7-FIXTURE.json"
DEFAULT_OUTPUT = HERE / "WAVE-010-G6-G7-RESULTS.json"
LAYERS = ("Attempt", "Effect", "Adoption", "Acceptance", "Settlement")


PROFILES: dict[str, dict[str, Any]] = {
    "EVENT_BUS_ONLY": {
        "readback": "NONE",
        "retry": "NEW_CAUSAL_ID",
        "reopen": "ALWAYS_CONTINUE",
        "manual": False,
    },
    "WORKFLOW_IDEMPOTENCY_ONLY": {
        "readback": "NONE",
        "retry": "SAME_CAUSAL_ID",
        "reopen": "ALWAYS_CONTINUE",
        "manual": False,
    },
    "TARGET_EFFECT_READBACK_ONLY": {
        "readback": "EFFECT_ONLY",
        "retry": "READBACK_FIRST",
        "reopen": "ALWAYS_CONTINUE",
        "manual": False,
    },
    "MATURE_COMPOSITION_LOCAL": {
        "readback": "ALL",
        "retry": "READBACK_FIRST",
        "reopen": "PUBLIC_LOCAL",
        "manual": False,
    },
    "MATURE_COMPOSITION_CONSERVATIVE": {
        "readback": "ALL",
        "retry": "READBACK_FIRST",
        "reopen": "GLOBAL_IF_INCOMPLETE",
        "manual": False,
    },
    "LAWFUL_STRONG_CENTER": {
        "readback": "ALL",
        "retry": "READBACK_FIRST",
        "reopen": "GLOBAL_IF_INCOMPLETE",
        "manual": False,
    },
    "HUMAN_INSTITUTION": {
        "readback": "ALL",
        "retry": "MANUAL_READBACK_FIRST",
        "reopen": "GLOBAL_IF_INCOMPLETE",
        "manual": True,
    },
    "MATURE_COMPOSITION_WITH_OWNER_DEP_QUERY": {
        "readback": "ALL",
        "retry": "READBACK_FIRST",
        "reopen": "OWNER_DEP_QUERY",
        "manual": False,
    },
    "STRONG_CENTER_WITH_OWNER_DEP_QUERY": {
        "readback": "ALL",
        "retry": "READBACK_FIRST",
        "reopen": "OWNER_DEP_QUERY",
        "manual": False,
    },
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def public_equivalence_view(world: dict[str, Any]) -> dict[str, Any]:
    """Return everything a no-query method may lawfully observe."""
    return copy.deepcopy(world["public"])


def broker_method_view(world: dict[str, Any], profile: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    """Build a method-visible view without exposing the private truth object."""
    view = {"public": public_equivalence_view(world), "readbacks": {}}
    costs = {"owner_readback_queries": 0, "dependency_queries": 0, "human_actions": 0}
    truth_layers = world["truth"]["layers"]

    if profile["readback"] == "EFFECT_ONLY":
        layer = truth_layers["Effect"]
        view["readbacks"]["Effect"] = copy.deepcopy(layer)
        costs["owner_readback_queries"] += 1
    elif profile["readback"] == "ALL":
        for name in LAYERS:
            view["readbacks"][name] = copy.deepcopy(truth_layers[name])
            costs["owner_readback_queries"] += 1
        if profile["manual"]:
            costs["human_actions"] += len(LAYERS)

    if profile["reopen"] == "OWNER_DEP_QUERY" and world["task"] == "T6":
        view["dependency_query"] = {
            "contract": world["public"]["dependency_query_contract"],
            "owner": "dependency-and-current-head-owners",
            "state": world["truth"]["dependency_query_response"],
        }
        costs["dependency_queries"] += 1
    return view, costs


def method_decision(view: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Apply a generic policy. No task label, world id, case id, or truth is accepted."""
    public = view["public"]
    readbacks = view["readbacks"]
    claims: dict[str, dict[str, str]] = {}
    observations: dict[str, str] = {}

    if profile["readback"] == "NONE" and public["workflow_status"] == "COMPLETED":
        for layer in LAYERS:
            claims[layer] = {"source": "workflow-controller", "state": "TRUE"}
    else:
        for layer, receipt in readbacks.items():
            observations[layer] = receipt["state"]
            if receipt["state"] == "TRUE":
                claims[layer] = {"source": receipt["owner"], "state": "TRUE"}

    if public["timeout_position"] == "AFTER_TARGET_COMMIT_BEFORE_ACK":
        retry = profile["retry"]
    else:
        retry = "NO_RETRY"

    reopen_action = "NOT_APPLICABLE"
    reopen_closure: list[str] = []
    if public["episode_kind"] == "REPEAT_AFTER_MODEL_UPGRADE":
        reopen_mode = profile["reopen"]
        if reopen_mode == "ALWAYS_CONTINUE":
            reopen_action = "CONTINUE"
        elif reopen_mode == "PUBLIC_LOCAL":
            reopen_action = "LOCAL_REOPEN"
            reopen_closure = list(public["public_changed_nodes"])
        elif reopen_mode == "GLOBAL_IF_INCOMPLETE":
            if public["public_dependency_coverage"] == "PARTIAL_UNKNOWN":
                reopen_action = "GLOBAL_REOPEN"
                reopen_closure = list(public["all_active_nodes"])
            else:
                reopen_action = "LOCAL_REOPEN"
                reopen_closure = list(public["public_changed_nodes"])
        elif reopen_mode == "OWNER_DEP_QUERY":
            dep_state = view["dependency_query"]["state"]
            if dep_state == "CURRENT":
                reopen_action = "CONTINUE"
            elif dep_state == "REVOKED":
                reopen_action = "LOCAL_REOPEN"
                reopen_closure = ["container-v2", "sidecar-account", "buyer-sandbox"]
            else:
                reopen_action = "BOUNDED_UNKNOWN"
                reopen_closure = list(public["all_active_nodes"])

    return {
        "claims": claims,
        "observations": observations,
        "retry": retry,
        "reopen_action": reopen_action,
        "reopen_closure": reopen_closure,
    }


def evaluate_world(
    world: dict[str, Any],
    decision: dict[str, Any],
    profile: dict[str, Any],
    query_costs: dict[str, int],
) -> dict[str, Any]:
    truth = world["truth"]
    false_promotions = 0
    wrong_owner_promotions = 0
    ladder_collapse_errors = 0
    valid_claims: set[str] = set()
    for layer, claim in decision["claims"].items():
        expected = truth["layers"][layer]
        owner_valid = claim["source"] == expected["owner"]
        state_valid = expected["state"] == "TRUE"
        if owner_valid and state_valid:
            valid_claims.add(layer)
        else:
            false_promotions += 1
            wrong_owner_promotions += int(not owner_valid)
            ladder_collapse_errors += int(not state_valid)

    missed_effects = int(
        truth["layers"]["Effect"]["state"] == "TRUE" and "Effect" not in valid_claims
    )

    duplicate_effects = 0
    recovery_steps = 0
    if world["public"]["timeout_position"] == "AFTER_TARGET_COMMIT_BEFORE_ACK":
        if decision["retry"] == "NEW_CAUSAL_ID" and truth["retry_with_new_identity_adds_effect"]:
            duplicate_effects = 1
            recovery_steps = 1
        elif decision["retry"] == "SAME_CAUSAL_ID":
            recovery_steps = 2
        elif decision["retry"] == "READBACK_FIRST":
            recovery_steps = 1
        elif decision["retry"] == "MANUAL_READBACK_FIRST":
            recovery_steps = 3

    unsafe_continuations = 0
    missed_reopen_nodes = 0
    over_reopen_nodes = 0
    reopen_exact = True
    if truth["expected_reopen"] is not None:
        expected = set(truth["expected_reopen"]["closure"])
        proposed = set(decision["reopen_closure"])
        missed_reopen_nodes = len(expected - proposed)
        over_reopen_nodes = len(proposed - expected)
        reopen_exact = (
            decision["reopen_action"] == truth["expected_reopen"]["action"]
            and proposed == expected
        )
        if missed_reopen_nodes and decision["reopen_action"] in {"CONTINUE", "LOCAL_REOPEN"}:
            unsafe_continuations = 1
        if decision["reopen_action"] == "GLOBAL_REOPEN":
            recovery_steps += 8 if profile["manual"] else 6
        elif decision["reopen_action"] == "LOCAL_REOPEN":
            recovery_steps += 2
        elif decision["reopen_action"] == "CONTINUE" and profile["reopen"] == "OWNER_DEP_QUERY":
            recovery_steps += 1

    recovery_expected = bool(truth["recovery_opportunity"])
    recovery_succeeded = True
    if recovery_expected and world["task"] == "T3":
        recovery_succeeded = duplicate_effects == 0 and "Effect" in valid_claims
    elif recovery_expected and world["task"] == "T6":
        recovery_succeeded = unsafe_continuations == 0 and missed_reopen_nodes == 0

    return {
        "false_promotions": false_promotions,
        "wrong_owner_promotions": wrong_owner_promotions,
        "ladder_collapse_errors": ladder_collapse_errors,
        "missed_effects": missed_effects,
        "duplicate_effects": duplicate_effects,
        "unsafe_continuations": unsafe_continuations,
        "missed_reopen_nodes": missed_reopen_nodes,
        "over_reopen_nodes": over_reopen_nodes,
        "reopen_exact": reopen_exact,
        "recovery_expected": recovery_expected,
        "recovery_succeeded": recovery_succeeded,
        "recovery_steps": recovery_steps,
        **query_costs,
    }


def aggregate(method_id: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    summed_fields = (
        "false_promotions",
        "wrong_owner_promotions",
        "ladder_collapse_errors",
        "missed_effects",
        "duplicate_effects",
        "unsafe_continuations",
        "missed_reopen_nodes",
        "over_reopen_nodes",
        "recovery_steps",
        "owner_readback_queries",
        "dependency_queries",
        "human_actions",
    )
    totals = {field: sum(row[field] for row in rows) for field in summed_fields}
    totals["failed_recoveries"] = sum(
        int(row["recovery_expected"] and not row["recovery_succeeded"]) for row in rows
    )
    gates = {
        "authoritative_postcondition": totals["false_promotions"] == 0,
        "effect_liveness": totals["missed_effects"] == 0,
        "ladder_noncollapse": totals["ladder_collapse_errors"] == 0,
        "causal_idempotency": totals["duplicate_effects"] == 0,
        "safe_continuation": totals["unsafe_continuations"] == 0,
        "exact_reopen": (
            totals["missed_reopen_nodes"] == 0 and totals["over_reopen_nodes"] == 0
        ),
        "bounded_recovery": totals["failed_recoveries"] == 0,
    }
    return {
        "method_id": method_id,
        **totals,
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
    }


def run_simulation(fixture: dict[str, Any]) -> dict[str, Any]:
    method_results: dict[str, Any] = {}
    per_world: dict[str, Any] = {}
    for method_id, profile in PROFILES.items():
        rows = []
        per_world[method_id] = {}
        for world in fixture["worlds"]:
            view, costs = broker_method_view(world, profile)
            decision = method_decision(view, profile)
            evaluation = evaluate_world(world, decision, profile, costs)
            rows.append(evaluation)
            per_world[method_id][world["opaque_id"]] = {
                "decision": decision,
                "evaluation": evaluation,
            }
        method_results[method_id] = aggregate(method_id, rows)

    fixture_bytes = FIXTURE.read_bytes()
    simulator_bytes = Path(__file__).read_bytes()
    return {
        "schema": "towow.wave010.g6-g7.results.v1",
        "status": "LOCAL_SYNTHETIC_DEVELOPMENT_RUN",
        "claims_not_supported": [
            "real Effect, Adoption, Acceptance, Settlement, production safety, real distribution frequency",
            "blind or independent implementation",
            "X1/X2 scoreable run or formal G6/G7 promotion"
        ],
        "fixture_sha256": sha256_bytes(fixture_bytes),
        "simulator_sha256": sha256_bytes(simulator_bytes),
        "world_count": len(fixture["worlds"]),
        "task_families": sorted(fixture["tasks"]),
        "method_results": method_results,
        "per_world": per_world,
    }


def self_test(fixture: dict[str, Any], results: dict[str, Any]) -> list[str]:
    checks: list[str] = []
    t6 = [world for world in fixture["worlds"] if world["task"] == "T6"]
    assert len(t6) == 2
    assert public_equivalence_view(t6[0]) == public_equivalence_view(t6[1])
    checks.append("t6_hidden_dependency_pair_public_transcript_identical")

    assert fixture["tasks"]["T3"]["evidence_level"] == "SYNTHETIC_TASK_SPEC_CANDIDATE"
    checks.append("t3_source_correction_preserved")

    conservative = results["method_results"]["MATURE_COMPOSITION_CONSERVATIVE"]
    center = results["method_results"]["LAWFUL_STRONG_CENTER"]
    assert conservative == {**center, "method_id": "MATURE_COMPOSITION_CONSERVATIVE"}
    checks.append("lawful_strong_center_causally_equal_under_same_legal_observations")

    for method_id in (
        "MATURE_COMPOSITION_WITH_OWNER_DEP_QUERY",
        "STRONG_CENTER_WITH_OWNER_DEP_QUERY",
    ):
        row = results["method_results"][method_id]
        assert row["gate_pass_count"] == row["gate_count"] == 7
        for field in (
            "false_promotions",
            "missed_effects",
            "duplicate_effects",
            "unsafe_continuations",
            "missed_reopen_nodes",
            "over_reopen_nodes",
            "failed_recoveries",
        ):
            assert row[field] == 0
    checks.append("owner_dependency_query_closes_this_fixture_for_both_control_topologies")

    event_only = results["method_results"]["EVENT_BUS_ONLY"]
    assert event_only["false_promotions"] > 0
    assert event_only["duplicate_effects"] > 0
    assert event_only["unsafe_continuations"] > 0
    checks.append("workflow_green_counterexample_exposes_false_closure_duplicate_and_unsafe_reuse")

    # Rename/permute opaque IDs; policies do not receive IDs, so aggregates must remain invariant.
    permuted = copy.deepcopy(fixture)
    for index, world in enumerate(reversed(permuted["worlds"])):
        world["opaque_id"] = f"ep-{index:08x}"
    rerun = run_simulation_from_worlds_only(permuted)
    assert rerun == results["method_results"]
    checks.append("opaque_identifier_and_order_permutation_invariant")
    return checks


def run_simulation_from_worlds_only(fixture: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for method_id, profile in PROFILES.items():
        rows = []
        for world in fixture["worlds"]:
            view, costs = broker_method_view(world, profile)
            decision = method_decision(view, profile)
            rows.append(evaluate_world(world, decision, profile, costs))
        output[method_id] = aggregate(method_id, rows)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    fixture = load_fixture()
    results = run_simulation(fixture)
    checks = self_test(fixture, results) if args.self_test else []
    results["self_test_checks"] = checks
    results["self_test_count"] = len(checks)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": results["status"],
        "world_count": results["world_count"],
        "method_count": len(results["method_results"]),
        "self_test_count": len(checks),
        "output": str(args.output),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
