#!/usr/bin/env python3
"""Deterministic G2 relation-materiality simulation on the Wave 006 denominator."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from evaluator import evaluate_candidate, with_zero_claims


ROOT = Path(__file__).resolve().parent


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    world = load_json(ROOT / "fixtures" / "shared-world.json")
    strategies = load_json(ROOT / "fixtures" / "strategies.json")
    costs = load_json(ROOT / "fixtures" / "cost-model.json")
    return world, strategies, costs


def safe_trace(strategy: dict[str, Any], world: dict[str, Any]) -> list[dict[str, Any]]:
    drift = next(
        item for item in world["event_sequence"] if item["event"] == "E7"
    )
    proposal = (
        world["relation_proposal"]["status"]
        if strategy["strategy_id"] == "C_ACK_EXPLAINBACK_RELATION_PROPOSAL"
        else "NOT_PRESENT"
    )
    return [
        {"event": "E0", "relation_state": "ABSENT", "action": "OBSERVE"},
        {"event": "E1", "relation_state": "ABSENT", "action": "PROBE_ONLY"},
        {
            "event": "E2",
            "relation_state": "ABSENT",
            "action": "RECORD_DELIVERY_NOT_RELATION",
        },
        {
            "event": "E3",
            "relation_state": "ABSENT",
            "action": "RECORD_TASK_ACK_NOT_RELATION",
        },
        {
            "event": "E4",
            "relation_state": "ABSENT",
            "action": "RECORD_POSTCONDITION_NOT_RELATION",
        },
        {
            "event": "E5",
            "relation_state": "ABSENT",
            "action": "RECORD_ACCEPTANCE_NOT_RELATION",
            "relation_proposal_status": proposal,
        },
        {
            "event": "E6",
            "relation_state": "ABSENT",
            "action": "CLARIFY_REAUTHORIZE_EXECUTE",
            "fresh_task_authorization_used": True,
            "outcome": "EXECUTED",
        },
        {
            "event": "E7",
            "relation_state": "ABSENT",
            "decisions": {
                item["case"]: item["expected"] for item in drift["cases"]
            },
        },
        {
            "event": "E8",
            "relation_state": "ABSENT",
            "action": "RECORD_WITHDRAWAL",
            "post_withdrawal_action": "REFUSE",
            "residual_active_relation_count": 0,
        },
    ]


def candidate_for(strategy: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "towow.relation-materiality-candidate.v1",
        "strategy_id": strategy["strategy_id"],
        "shared_task_id": world["shared_task_id"],
        "shared_task_sha256": world["shared_task_sha256"],
        "trace": safe_trace(strategy, world),
        "claimed_metrics": {},
    }


def strongest_false_relation_attack(
    base_strategy: dict[str, Any], world: dict[str, Any]
) -> dict[str, Any]:
    candidate = candidate_for(base_strategy, world)
    candidate["strategy_id"] = "ATTACK_ONE_SHOT_AS_CONTINUING_RELATION"
    by_event = {item["event"]: item for item in candidate["trace"]}
    for event in ("E2", "E3", "E4", "E5", "E6", "E7", "E8"):
        by_event[event]["relation_state"] = "ACTIVE"
    by_event["E6"].update(
        {
            "action": "AUTO_REUSE_PRIOR_RELATION",
            "fresh_task_authorization_used": False,
            "outcome": "EXECUTED",
        }
    )
    by_event["E8"].update(
        {
            "post_withdrawal_action": "AUTO_REUSE_PRIOR_RELATION",
            "residual_active_relation_count": 1,
        }
    )
    return with_zero_claims(candidate)


def run_experiment() -> dict[str, Any]:
    world, registry, costs = frozen_inputs()
    evaluations = []
    candidates = []
    by_id = {
        item["strategy_id"]: item for item in registry["strategies"]
    }
    for strategy in registry["strategies"]:
        candidate = candidate_for(strategy, world)
        evaluation = evaluate_candidate(world, strategy, costs, candidate)
        candidates.append(candidate)
        evaluations.append(evaluation)

    attack = strongest_false_relation_attack(
        by_id["A_DELIVERY_RECEIPT_ONLY"], world
    )
    attack_evaluation = evaluate_candidate(
        world,
        {
            **by_id["A_DELIVERY_RECEIPT_ONLY"],
            "strategy_id": attack["strategy_id"],
        },
        costs,
        attack,
    )
    eligible = [item for item in evaluations if item["passed"]]
    winner = max(
        eligible,
        key=lambda item: (
            item["metrics"]["net_task_value"],
            -item["metrics"]["disclosure_units"],
            -item["metrics"]["coordination_operations"],
        ),
    )
    b = next(
        item for item in evaluations
        if item["strategy_id"] == "B_DUAL_RECIPIENT_ACK"
    )
    c = next(
        item for item in evaluations
        if item["strategy_id"] == "C_ACK_EXPLAINBACK_RELATION_PROPOSAL"
    )
    material_fields = [
        "reuse_success",
        "stale_reuse",
        "withdrawal_residual",
        "false_positive",
        "false_negative",
    ]
    relation_version_task_increment = any(
        b["metrics"][field] != c["metrics"][field]
        for field in material_fields
    )
    return {
        "schema": "towow.relation-materiality-result.v1",
        "experiment_id": world["experiment_id"],
        "shared_task_id": world["shared_task_id"],
        "shared_task_sha256": world["shared_task_sha256"],
        "invariant": registry["invariant"],
        "candidate_count": len(candidates),
        "evaluations": evaluations,
        "strongest_counterexample": {
            "name": "one-shot retrieval mistaken for continuing relation",
            "evaluation": attack_evaluation,
        },
        "selection": {
            "winner_at_relation_representation_scope": winner["strategy_id"],
            "relation_version_material_increment_over_dual_ack": relation_version_task_increment,
            "relation_version_net_value_delta_over_dual_ack": (
                c["metrics"]["net_task_value"]
                - b["metrics"]["net_task_value"]
            ),
            "decision": (
                "USE_SIMPLER_EXISTING_EVIDENCE; DO_NOT_CONSTITUTE_A_RELATION"
                if not relation_version_task_increment
                else "RELATION_VERSION_HAS_SCOPED_TASK_INCREMENT"
            ),
            "dual_ack_interpretation": (
                "Dual ACK is sufficient to establish task receipt, but neither "
                "ACK nor RelationVersion creates continuing authority."
            ),
        },
        "evidence_boundary": {
            "environment": "LOCAL_DETERMINISTIC_SYNTHETIC_SIMULATION",
            "not_claimed": [
                "real subject understanding",
                "real relation formation",
                "medical or production validity",
                "cross-domain frequency",
                "need for a novel Towow protocol"
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run_experiment(),
            ensure_ascii=False,
            sort_keys=True,
            indent=None if args.compact else 2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
