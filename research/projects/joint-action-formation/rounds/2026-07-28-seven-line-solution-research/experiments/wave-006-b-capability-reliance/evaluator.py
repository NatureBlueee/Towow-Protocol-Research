#!/usr/bin/env python3
"""Evaluate reliance calibration, recovery, evidence cost, and net task value."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from simulator import DEFAULT_FIXTURE, STRATEGIES, load_json, run_simulation


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = BASE_DIR / "results" / "baseline.json"


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _costs_for(strategy_id: str, row: dict[str, Any]) -> dict[str, float]:
    visible = row["visible_sha256_input"]
    if row["decisions"][strategy_id]["decision_state"] in {
        "UNKNOWN",
        "REFUSE",
        "ABSENT",
    }:
        return {"disclosure_units": 0.1, "coordination_operations": 1.0}
    if strategy_id == "DECLARATION":
        return {"disclosure_units": 0.2, "coordination_operations": 1.0}
    if strategy_id == "LATEST_PROBE":
        return {"disclosure_units": 0.5, "coordination_operations": 2.0}
    if strategy_id == "RECEIPT_HISTORY":
        return {
            "disclosure_units": 0.8,
            "coordination_operations": 1.0 + len(visible["receipt_history"]),
        }
    return {
        "disclosure_units": 1.0,
        "coordination_operations": (
            4.0 + (1.0 if visible["sla"]["health"] == "RECOVERED" else 0.0)
        ),
    }


def evaluate(fixture: dict[str, Any]) -> dict[str, Any]:
    simulation = run_simulation(fixture)
    economics = fixture["economics"]
    per_strategy: dict[str, dict[str, Any]] = {}
    per_scenario: dict[str, dict[str, Any]] = {}

    for strategy_id in STRATEGIES:
        totals = {
            "decision_count": 0,
            "relied_count": 0,
            "false_reliance": 0,
            "missed_opportunity": 0,
            "operation_success": 0,
            "verified_reliance_success": 0,
            "business_effect_accepted": 0,
            "operation_success_without_business_effect": 0,
            "disclosure_units": 0.0,
            "coordination_operations": 0.0,
            "recovery_time_steps": 0,
        }
        for row in simulation["rows"]:
            decision = row["decisions"][strategy_id]
            truth = row["truth"]
            costs = _costs_for(strategy_id, row)
            totals["decision_count"] += 1
            totals["disclosure_units"] += costs["disclosure_units"]
            totals["coordination_operations"] += costs["coordination_operations"]
            if decision["rely"]:
                totals["relied_count"] += 1
                if truth["operation_success"]:
                    totals["operation_success"] += 1
                if truth["safe_to_rely"]:
                    totals["verified_reliance_success"] += 1
                else:
                    totals["false_reliance"] += 1
                if truth["business_effect_accepted"]:
                    totals["business_effect_accepted"] += 1
                if (
                    truth["operation_success"]
                    and not truth["business_effect_accepted"]
                ):
                    totals["operation_success_without_business_effect"] += 1
            elif truth["safe_to_rely"]:
                totals["missed_opportunity"] += 1

        for scenario in fixture["scenarios"]:
            if "recovery_at_step" not in scenario:
                continue
            rows = [
                row for row in simulation["rows"]
                if row["scenario_id"] == scenario["scenario_id"]
                and row["step"] >= scenario["recovery_at_step"]
            ]
            first = next(
                (
                    row["step"]
                    for row in rows
                    if row["truth"]["safe_to_rely"]
                    and row["decisions"][strategy_id]["rely"]
                ),
                scenario["horizon_step"] + 1,
            )
            totals["recovery_time_steps"] += first - scenario["recovery_at_step"]

        accepted_value = (
            totals["business_effect_accepted"]
            * economics["accepted_task_value"]
        )
        disclosure_cost = (
            totals["disclosure_units"] * economics["disclosure_unit_cost"]
        )
        coordination_cost = (
            totals["coordination_operations"]
            * economics["coordination_operation_cost"]
        )
        recovery_cost = (
            totals["recovery_time_steps"] * economics["recovery_step_cost"]
        )
        false_action_loss = (
            totals["false_reliance"] * economics["false_action_loss"]
        )
        evidence_cost = disclosure_cost + coordination_cost
        totals.update({
            "accepted_task_value": accepted_value,
            "evidence_cost": round(evidence_cost, 4),
            "recovery_cost": recovery_cost,
            "false_action_loss": false_action_loss,
            "net_task_value": round(
                accepted_value
                - disclosure_cost
                - coordination_cost
                - recovery_cost
                - false_action_loss,
                4,
            ),
        })
        per_strategy[strategy_id] = totals

    for scenario in fixture["scenarios"]:
        scenario_rows = [
            row for row in simulation["rows"]
            if row["scenario_id"] == scenario["scenario_id"]
        ]
        strategy_scores: dict[str, float] = {}
        strategy_metrics: dict[str, dict[str, Any]] = {}
        for strategy_id in STRATEGIES:
            accepted = 0
            false_reliance = 0
            missed = 0
            disclosure = 0.0
            coordination = 0.0
            for row in scenario_rows:
                decision = row["decisions"][strategy_id]
                truth = row["truth"]
                costs = _costs_for(strategy_id, row)
                disclosure += costs["disclosure_units"]
                coordination += costs["coordination_operations"]
                accepted += int(
                    decision["rely"] and truth["business_effect_accepted"]
                )
                false_reliance += int(
                    decision["rely"] and not truth["safe_to_rely"]
                )
                missed += int(
                    not decision["rely"] and truth["safe_to_rely"]
                )
            score = (
                accepted * economics["accepted_task_value"]
                - false_reliance * economics["false_action_loss"]
                - disclosure * economics["disclosure_unit_cost"]
                - coordination * economics["coordination_operation_cost"]
            )
            strategy_scores[strategy_id] = round(score, 4)
            strategy_metrics[strategy_id] = {
                "false_reliance": false_reliance,
                "missed_opportunity": missed,
                "score_before_recovery_cost": round(score, 4),
            }
        best_score = max(strategy_scores.values())
        winners = sorted(
            strategy_id
            for strategy_id, score in strategy_scores.items()
            if score == best_score
        )
        per_scenario[scenario["scenario_id"]] = {
            "risk": scenario["risk"],
            "strategy_metrics": strategy_metrics,
            "winners": winners,
        }

    ranked = sorted(
        per_strategy,
        key=lambda strategy_id: (
            -per_strategy[strategy_id]["net_task_value"],
            strategy_id,
        ),
    )
    epistemic_preservation: dict[str, list[str]] = {}
    for strategy_id in STRATEGIES:
        epistemic_preservation[strategy_id] = sorted({
            row["decisions"][strategy_id]["decision_state"]
            for row in simulation["rows"]
            if row["decisions"][strategy_id]["decision_state"]
            in {"UNKNOWN", "REFUSE", "ABSENT"}
        })

    return {
        "schema_version": "1.0",
        "shared_task": simulation["shared_task"],
        "operation": simulation["operation"],
        "fixture_sha256": canonical_sha256(fixture),
        "scope_distinctions": {
            "operation_success": "Frozen simulator reaches domain postcondition within the operation deadline.",
            "capability": "Evidence supports ability for the exact operation under bound key and environment, not all future operations.",
            "reliance": "Principal has a calibrated basis to assign this exact operation at this decision point.",
            "business_effect": "Beneficiary separately accepts the exact frozen output."
        },
        "per_strategy": per_strategy,
        "per_scenario": per_scenario,
        "ranking_by_net_task_value": ranked,
        "epistemic_states_preserved": epistemic_preservation,
        "claims": {
            "all_strategies_received_same_visible_snapshot_per_row": True,
            "strategies_received_truth": False,
            "steady_low_risk_allows_simplest_strategy_to_win": (
                per_scenario["steady-low-risk"]["winners"] == ["DECLARATION"]
            ),
            "synthetic_result_is_real_world_frequency": False,
            "business_effect_inferred_from_operation_success": False
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = evaluate(load_json(args.fixture))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
