#!/usr/bin/env python3
"""Cost sensitivity and dominance analysis for Wave-006 G2 and G4."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = BASE_DIR / "config.json"
DEFAULT_OUTPUT = BASE_DIR / "results" / "sensitivity.json"


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON top level must be an object")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_and_verify(config: dict[str, Any]) -> dict[str, Any]:
    paths = {
        "shared_task": config["shared_task"],
        **config["bound_results"],
    }
    resolved: dict[str, Any] = {}
    for source_id, binding in paths.items():
        path = (BASE_DIR / binding["path"]).resolve()
        actual = sha256_file(path)
        if actual != binding["sha256"]:
            raise ValueError(
                f"frozen input drift: {source_id}: "
                f"expected {binding['sha256']}, got {actual}"
            )
        resolved[source_id] = {
            "path": str(path),
            "sha256": actual,
            "value": load_json(path) if path.suffix == ".json" else None,
        }
    return resolved


def relation_metrics(result: dict[str, Any]) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for row in result["safe_strategy_results"]:
        metrics[row["strategy_id"]] = {
            "accepted": float(row["reuse_success"]),
            "failure": float(
                row["false_relation_constitution"]
                + row["stale_reuse"]
                + row["withdrawal_residual"]
            ),
            "missed": 0.0,
            "disclosure": float(row["disclosure_units"]),
            "coordination": float(row["coordination_operations"]),
            "recovery": float(row["withdrawal_residual"]),
        }
    return metrics


def reliance_metrics(result: dict[str, Any]) -> dict[str, dict[str, float]]:
    metrics: dict[str, dict[str, float]] = {}
    for strategy_id, row in result["per_strategy"].items():
        metrics[strategy_id] = {
            "accepted": float(row["business_effect_accepted"]),
            "failure": float(row["false_reliance"]),
            "missed": float(row["missed_opportunity"]),
            "disclosure": float(row["disclosure_units"]),
            "coordination": float(row["coordination_operations"]),
            "recovery": float(row["recovery_time_steps"]),
        }
    return metrics


def score(
    metrics: dict[str, float],
    weights: dict[str, float],
    accepted_task_value: float,
) -> float:
    evidence_cost = weights["evidence_multiplier"] * (
        metrics["disclosure"] * weights["disclosure_unit_cost"]
        + metrics["coordination"] * weights["coordination_operation_cost"]
    )
    return (
        metrics["accepted"] * accepted_task_value
        - metrics["failure"] * weights["failure_loss"]
        - metrics["missed"] * weights["missed_opportunity_value"]
        - evidence_cost
        - metrics["recovery"] * weights["recovery_step_cost"]
    )


def weight_grid(config: dict[str, Any]) -> list[dict[str, float]]:
    ranges = config["scan_ranges"]
    names = list(ranges)
    return [
        dict(zip(names, values))
        for values in itertools.product(*(ranges[name] for name in names))
    ]


def scan(
    metrics: dict[str, dict[str, float]],
    config: dict[str, Any],
) -> dict[str, Any]:
    strategies = sorted(metrics)
    grid = weight_grid(config)
    winner_counts = {strategy_id: 0 for strategy_id in strategies}
    unique_winner_counts = {strategy_id: 0 for strategy_id in strategies}
    tie_count = 0
    near_tie_count = 0
    representative_points: dict[str, dict[str, Any]] = {}
    score_rows: list[dict[str, float]] = []

    for weights in grid:
        scores = {
            strategy_id: score(
                metrics[strategy_id],
                weights,
                config["fixed"]["accepted_task_value"],
            )
            for strategy_id in strategies
        }
        score_rows.append(scores)
        best = max(scores.values())
        winners = sorted(
            strategy_id
            for strategy_id, value in scores.items()
            if abs(value - best) <= 1e-9
        )
        for strategy_id in winners:
            winner_counts[strategy_id] += 1
            representative_points.setdefault(strategy_id, {
                "weights": weights,
                "scores": {key: round(value, 6) for key, value in scores.items()},
                "winners": winners,
            })
        if len(winners) == 1:
            unique_winner_counts[winners[0]] += 1
        else:
            tie_count += 1
        ordered = sorted(scores.values(), reverse=True)
        if len(winners) > 1 or ordered[0] - ordered[1] <= config["no_conclusion_margin"]:
            near_tie_count += 1

    weak_dominance: dict[str, list[str]] = {
        strategy_id: [] for strategy_id in strategies
    }
    strict_dominance: dict[str, list[str]] = {
        strategy_id: [] for strategy_id in strategies
    }
    for left in strategies:
        for right in strategies:
            if left == right:
                continue
            comparisons = [
                row[left] - row[right]
                for row in score_rows
            ]
            if min(comparisons) > 1e-9:
                strict_dominance[left].append(right)
            elif min(comparisons) >= -1e-9 and max(comparisons) > 1e-9:
                weak_dominance[left].append(right)

    baseline_scores = {
        strategy_id: score(
            metrics[strategy_id],
            config["baseline_weights"],
            config["fixed"]["accepted_task_value"],
        )
        for strategy_id in strategies
    }
    baseline_best = max(baseline_scores.values())
    baseline_winners = sorted(
        strategy_id
        for strategy_id, value in baseline_scores.items()
        if abs(value - baseline_best) <= 1e-9
    )
    total = len(grid)
    return {
        "grid_point_count": total,
        "winner_counts_including_ties": winner_counts,
        "unique_winner_counts": unique_winner_counts,
        "unique_winner_share": {
            strategy_id: round(count / total, 6)
            for strategy_id, count in unique_winner_counts.items()
        },
        "tie_count": tie_count,
        "near_tie_or_no_conclusion_count": near_tie_count,
        "near_tie_or_no_conclusion_share": round(near_tie_count / total, 6),
        "sampled_weak_dominance": {
            key: sorted(value)
            for key, value in weak_dominance.items()
            if value
        },
        "sampled_strict_dominance": {
            key: sorted(value)
            for key, value in strict_dominance.items()
            if value
        },
        "representative_winner_points": representative_points,
        "baseline": {
            "weights": config["baseline_weights"],
            "scores": {
                key: round(value, 6)
                for key, value in baseline_scores.items()
            },
            "winners": baseline_winners,
        },
    }


def analytic_thresholds() -> dict[str, Any]:
    return {
        "g4_sla_vs_declaration": {
            "difference": (
                "SLA - DECLARATION = "
                "7*failure_loss - evidence_multiplier*"
                "(15.2*disclosure_unit_cost + 60*coordination_operation_cost)"
            ),
            "sla_wins_when": (
                "failure_loss > evidence_multiplier*"
                "(15.2*disclosure_unit_cost + 60*coordination_operation_cost)/7"
            ),
            "baseline_threshold": 6.457143,
            "baseline_failure_loss": 18.0,
        },
        "g4_declaration_vs_latest_probe": {
            "difference": (
                "DECLARATION - LATEST_PROBE = "
                "60 - 6*failure_loss + 4*missed_opportunity_value + "
                "evidence_multiplier*(5.7*disclosure_unit_cost + "
                "19*coordination_operation_cost) + recovery_step_cost"
            ),
            "declaration_wins_when": (
                "failure_loss < (60 + 4*missed_opportunity_value + "
                "evidence_multiplier*(5.7*disclosure_unit_cost + "
                "19*coordination_operation_cost) + recovery_step_cost)/6"
            ),
            "baseline_threshold": 12.866667,
            "baseline_failure_loss": 18.0,
        },
        "g4_sla_vs_latest_probe": {
            "difference": (
                "SLA - LATEST_PROBE = "
                "60 + failure_loss + 4*missed_opportunity_value - "
                "evidence_multiplier*(9.5*disclosure_unit_cost + "
                "41*coordination_operation_cost) + recovery_step_cost"
            ),
            "baseline_difference": 50.0,
        },
        "g2_a_vs_b": {
            "difference": (
                "A - B = evidence_multiplier*"
                "(2*coordination_operation_cost)"
            ),
            "conclusion": (
                "A weakly dominates B for all nonnegative sampled costs; "
                "they tie only when coordination cost is zero."
            ),
        },
        "g2_b_vs_c": {
            "difference": (
                "B - C = evidence_multiplier*"
                "(2*disclosure_unit_cost + 5*coordination_operation_cost)"
            ),
            "conclusion": (
                "B weakly dominates C for all nonnegative sampled costs; "
                "they tie only when both disclosure and coordination costs are zero."
            ),
        },
    }


def main_analysis(config: dict[str, Any]) -> dict[str, Any]:
    sources = resolve_and_verify(config)
    g2_metrics = relation_metrics(sources["wave_006_a"]["value"])
    g4_metrics = reliance_metrics(sources["wave_006_b"]["value"])
    g2 = scan(g2_metrics, config)
    g4 = scan(g4_metrics, config)

    g2_baseline_claim = sources["wave_006_a"]["value"]["selection"][
        "winner_at_relation_representation_scope"
    ]
    g4_baseline_claim = sources["wave_006_b"]["value"][
        "ranking_by_net_task_value"
    ][0]
    return {
        "schema_version": "1.0",
        "shared_task_sha256": sources["shared_task"]["sha256"],
        "bound_input_hashes": {
            source_id: source["sha256"]
            for source_id, source in sources.items()
        },
        "parameter_ranges": config["scan_ranges"],
        "fixed": config["fixed"],
        "score_formula": (
            "accepted*accepted_task_value - failure*failure_loss - "
            "missed*missed_opportunity_value - evidence_multiplier*"
            "(disclosure*disclosure_unit_cost + coordination*"
            "coordination_operation_cost) - recovery*recovery_step_cost"
        ),
        "g2_relation_representation": {
            "source_metrics": g2_metrics,
            "baseline_claim": g2_baseline_claim,
            "sensitivity": g2,
            "claim_stability": (
                "ROBUST_WITH_NONNEGATIVE_COSTS_BUT_TIES_AT_ZERO_COORDINATION"
            ),
        },
        "g4_capability_reliance": {
            "source_metrics": g4_metrics,
            "baseline_claim": g4_baseline_claim,
            "sensitivity": g4,
            "claim_stability": (
                "CONDITION_DEPENDENT_BASELINE_WINNER_NOT_GLOBALLY_STABLE"
                if g4["unique_winner_counts"].get(g4_baseline_claim, 0)
                < g4["grid_point_count"]
                else "ROBUST_ON_SAMPLED_RANGE"
            ),
        },
        "analytic_thresholds": analytic_thresholds(),
        "scope": {
            "wave_006_c_used_as_bound_denominator_not_rescored": True,
            "sampled_regions_are_not_real_world_probabilities": True,
            "baseline_winner_is_not_promoted_to_universal_winner": True,
            "simple_solution_winning_is_positive_result": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = main_analysis(load_json(args.config))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
