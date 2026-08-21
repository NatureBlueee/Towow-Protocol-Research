#!/usr/bin/env python3
"""Hidden-truth evaluator for access-metered reliance strategies."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Callable

from evidence_api import (
    DEFAULT_EVIDENCE,
    EvidenceAPI,
    load_json,
    reconstruct_cost,
)
from strategies import STRATEGIES


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TRUTH = BASE_DIR / "private" / "truth.json"
DEFAULT_OUTPUT = BASE_DIR / "results" / "evaluation.json"
BASELINE_COST_MODEL = {
    "operation_cost": 0.1,
    "byte_cost": 0.00005,
    "latency_ms_cost": 0.01,
    "disclosure_unit_cost": 1.0,
    "retry_cost": 0.5,
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def run_candidates(
    database: dict[str, Any],
    strategy_map: dict[str, Callable[[EvidenceAPI], dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for world_token in sorted(database["worlds"]):
        for strategy_label, function in strategy_map.items():
            api = EvidenceAPI(database, world_token, strategy_label)
            decision = function(api)
            log = api.operation_log
            rows.append({
                "world_token": world_token,
                "strategy_label": strategy_label,
                "implementation_id": decision["implementation_id"],
                "decision": decision,
                "operation_log": log,
                "cost": reconstruct_cost(log, BASELINE_COST_MODEL),
            })
    return rows


def _confusion(rows: list[dict[str, Any]], truth_rows: list[dict[str, Any]]) -> dict[str, int]:
    truth = {row["world_token"]: row for row in truth_rows}
    counts = {"TP": 0, "FP": 0, "TN": 0, "FN": 0, "UNKNOWN_TRUTH": 0}
    for row in rows:
        expected = truth[row["world_token"]]["safe_to_rely"]
        rely = row["decision"]["rely"]
        if expected is None:
            counts["UNKNOWN_TRUTH"] += 1
        elif rely and expected:
            counts["TP"] += 1
        elif rely and not expected:
            counts["FP"] += 1
        elif not rely and expected:
            counts["FN"] += 1
        else:
            counts["TN"] += 1
    return counts


def _metrics(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = {row["world_token"]: row for row in truth_rows}
    by_implementation: dict[str, list[dict[str, Any]]] = {}
    for row in candidate_rows:
        by_implementation.setdefault(row["implementation_id"], []).append(row)
    metrics: dict[str, Any] = {}
    for implementation_id, rows in sorted(by_implementation.items()):
        confusion = _confusion(rows, truth_rows)
        cost_fields = {
            field: sum(row["cost"][field] for row in rows)
            for field in (
                "api_operations",
                "bytes",
                "latency_ms",
                "disclosure_units",
                "retries",
                "total_evidence_cost",
            )
        }
        epistemic = {"UNKNOWN": 0, "REFUSE": 0, "ABSENT": 0}
        epistemic_correct = {"UNKNOWN": 0, "REFUSE": 0, "ABSENT": 0}
        operation_success = 0
        business_effect = 0
        for row in rows:
            world_truth = truth[row["world_token"]]
            state = row["decision"]["decision_state"]
            if state in epistemic:
                epistemic[state] += 1
            expected_state = world_truth.get("epistemic_truth")
            if expected_state in epistemic and state == expected_state:
                epistemic_correct[expected_state] += 1
            if row["decision"]["rely"] and world_truth.get("operation_success"):
                operation_success += 1
            if row["decision"]["rely"] and world_truth.get("business_accepted"):
                business_effect += 1

        sequence = sorted(
            (
                truth[row["world_token"]]["sequence_step"],
                row,
            )
            for row in rows
            if truth[row["world_token"]].get("recovery_group")
            == "authority-cycle"
        )
        recovery_at = next(
            (
                step
                for step, row in sequence
                if truth[row["world_token"]].get("recovery_at_step") == step
            ),
            None,
        )
        recovery_steps = 0
        if recovery_at is not None:
            first = next(
                (
                    step
                    for step, row in sequence
                    if step >= recovery_at
                    and row["decision"]["rely"]
                    and truth[row["world_token"]]["safe_to_rely"] is True
                ),
                max(step for step, _ in sequence) + 1,
            )
            recovery_steps = first - recovery_at

        split_metrics: dict[str, Any] = {}
        for split in ("IN_DISTRIBUTION", "SHIFTED"):
            split_truth = [
                row for row in truth_rows if row["split"] == split
            ]
            split_tokens = {row["world_token"] for row in split_truth}
            split_rows = [
                row for row in rows if row["world_token"] in split_tokens
            ]
            split_metrics[split] = _confusion(split_rows, split_truth)
        id_error = (
            split_metrics["IN_DISTRIBUTION"]["FP"]
            + split_metrics["IN_DISTRIBUTION"]["FN"]
        )
        shifted_error = (
            split_metrics["SHIFTED"]["FP"]
            + split_metrics["SHIFTED"]["FN"]
        )
        metrics[implementation_id] = {
            "confusion": confusion,
            "cost": {
                key: round(value, 6) if isinstance(value, float) else value
                for key, value in cost_fields.items()
            },
            "recovery_time_steps": recovery_steps,
            "operation_success_when_relied": operation_success,
            "business_effect_when_relied": business_effect,
            "epistemic_output_counts": epistemic,
            "epistemic_correct_counts": epistemic_correct,
            "distribution_shift": {
                "per_split_confusion": split_metrics,
                "error_delta_shift_minus_in_distribution": shifted_error - id_error,
            },
        }
    return metrics


def _per_scenario(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = {row["world_token"]: row for row in truth_rows}
    result: dict[str, Any] = {}
    for row in candidate_rows:
        world = truth[row["world_token"]]
        scenario = f"{world['pair']}::{world['variant']}"
        expected = world["safe_to_rely"]
        relied = row["decision"]["rely"]
        if expected is None:
            confusion_cell = "UNKNOWN_TRUTH"
        elif relied and expected:
            confusion_cell = "TP"
        elif relied and not expected:
            confusion_cell = "FP"
        elif not relied and expected:
            confusion_cell = "FN"
        else:
            confusion_cell = "TN"
        result.setdefault(scenario, {
            "split": world["split"],
            "safe_to_rely": world["safe_to_rely"],
            "operation_success": world["operation_success"],
            "business_accepted": world["business_accepted"],
            "strategies": {},
        })
        result[scenario]["strategies"][row["implementation_id"]] = {
            "decision_state": row["decision"]["decision_state"],
            "rely": relied,
            "confusion_cell": confusion_cell,
            "cost": row["cost"],
            "recovery": (
                {
                    "delay_steps": 0 if relied else None,
                    "censored_without_reliance": not relied,
                }
                if world["pair"] == "recovery"
                else None
            ),
        }
    return result


def _pareto(metrics: dict[str, Any]) -> dict[str, Any]:
    ids = sorted(metrics)
    dominated_by: dict[str, list[str]] = {strategy_id: [] for strategy_id in ids}

    def vector(strategy_id: str) -> tuple[float, ...]:
        row = metrics[strategy_id]
        return (
            -row["confusion"]["TP"],
            row["confusion"]["FP"],
            row["confusion"]["FN"],
            row["cost"]["total_evidence_cost"],
            row["recovery_time_steps"],
        )

    for candidate in ids:
        candidate_vector = vector(candidate)
        for other in ids:
            if candidate == other:
                continue
            other_vector = vector(other)
            if (
                all(left <= right for left, right in zip(
                    other_vector, candidate_vector
                ))
                and any(left < right for left, right in zip(
                    other_vector, candidate_vector
                ))
            ):
                dominated_by[candidate].append(other)
    frontier = sorted(
        strategy_id for strategy_id in ids if not dominated_by[strategy_id]
    )
    return {
        "objectives": [
            "maximize_TP",
            "minimize_FP",
            "minimize_FN",
            "minimize_actual_evidence_cost",
            "minimize_recovery_time",
        ],
        "frontier": frontier,
        "dominated_by": {
            key: sorted(value)
            for key, value in dominated_by.items()
            if value
        },
    }


def _sensitivity(metrics: dict[str, Any]) -> dict[str, Any]:
    failure_losses = [0.0, 5.0, 20.0, 50.0]
    missed_values = [0.0, 5.0, 20.0]
    evidence_multipliers = [0.5, 1.0, 2.0, 4.0]
    winner_counts = {strategy_id: 0 for strategy_id in metrics}
    unique_counts = {strategy_id: 0 for strategy_id in metrics}
    ties = 0
    unknown_margin = 0
    examples: dict[str, Any] = {}
    for failure, missed, evidence in itertools.product(
        failure_losses, missed_values, evidence_multipliers
    ):
        scores = {}
        for strategy_id, row in metrics.items():
            scores[strategy_id] = (
                row["business_effect_when_relied"] * 20.0
                - row["confusion"]["FP"] * failure
                - row["confusion"]["FN"] * missed
                - row["cost"]["total_evidence_cost"] * evidence
                - row["recovery_time_steps"] * 2.0
            )
        best = max(scores.values())
        winners = sorted(
            key for key, value in scores.items()
            if abs(value - best) <= 1e-9
        )
        for winner in winners:
            winner_counts[winner] += 1
            examples.setdefault(winner, {
                "weights": {
                    "failure_loss": failure,
                    "missed_opportunity_value": missed,
                    "evidence_multiplier": evidence,
                },
                "scores": {key: round(value, 6) for key, value in scores.items()},
                "winners": winners,
            })
        if len(winners) == 1:
            unique_counts[winners[0]] += 1
        else:
            ties += 1
        ordered = sorted(scores.values(), reverse=True)
        if len(winners) > 1 or ordered[0] - ordered[1] <= 1.0:
            unknown_margin += 1
    total = len(failure_losses) * len(missed_values) * len(evidence_multipliers)
    return {
        "ranges": {
            "failure_loss": failure_losses,
            "missed_opportunity_value": missed_values,
            "evidence_multiplier": evidence_multipliers,
        },
        "point_count": total,
        "winner_counts_including_ties": winner_counts,
        "unique_winner_counts": unique_counts,
        "tie_count": ties,
        "unknown_or_margin_le_1_count": unknown_margin,
        "representative_winner_points": examples,
    }


def _frequency_cost_regions(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Reweight scenario frequencies without changing candidate observations."""
    truth = {row["world_token"]: row for row in truth_rows}
    by_implementation = _rows_by_implementation(candidate_rows)
    profiles = {
        "UNIFORM": lambda _: 1.0,
        "CURRENT_FAILURE_HEAVY": lambda row: (
            8.0 if row["pair"] == "recent-operation"
            and row["variant"] == "CURRENT_FAILURE" else 1.0
        ),
        "RECOVERY_HEAVY": lambda row: (
            8.0 if row["pair"] == "recovery" else 1.0
        ),
        "SHIFTED_HEAVY": lambda row: (
            5.0 if row["split"] == "SHIFTED" else 1.0
        ),
        "IN_DISTRIBUTION_HEAVY": lambda row: (
            5.0 if row["split"] == "IN_DISTRIBUTION" else 1.0
        ),
        "CONTRACT_HEAVY": lambda row: (
            8.0 if row["pair"] == "contract" else 1.0
        ),
    }
    failure_losses = [0.0, 10.0, 50.0]
    missed_values = [0.0, 10.0, 50.0]
    evidence_multipliers = [0.5, 1.0, 4.0]
    result: dict[str, Any] = {}
    for profile_name, weight_function in profiles.items():
        vectors: dict[str, dict[str, float]] = {}
        for implementation_id, rows in by_implementation.items():
            vector = {
                "weighted_TP": 0.0,
                "weighted_FP": 0.0,
                "weighted_FN": 0.0,
                "weighted_cost": 0.0,
            }
            for row in rows:
                world = truth[row["world_token"]]
                weight = weight_function(world)
                expected = world["safe_to_rely"]
                relied = row["decision"]["rely"]
                if expected is True and relied:
                    vector["weighted_TP"] += weight
                elif expected is False and relied:
                    vector["weighted_FP"] += weight
                elif expected is True and not relied:
                    vector["weighted_FN"] += weight
                vector["weighted_cost"] += (
                    weight * row["cost"]["total_evidence_cost"]
                )
            vectors[implementation_id] = vector

        dominated_by: dict[str, list[str]] = {
            implementation_id: [] for implementation_id in vectors
        }
        for candidate, candidate_row in vectors.items():
            candidate_vector = (
                -candidate_row["weighted_TP"],
                candidate_row["weighted_FP"],
                candidate_row["weighted_FN"],
                candidate_row["weighted_cost"],
            )
            for other, other_row in vectors.items():
                if candidate == other:
                    continue
                other_vector = (
                    -other_row["weighted_TP"],
                    other_row["weighted_FP"],
                    other_row["weighted_FN"],
                    other_row["weighted_cost"],
                )
                if (
                    all(left <= right for left, right in zip(
                        other_vector, candidate_vector
                    ))
                    and any(left < right for left, right in zip(
                        other_vector, candidate_vector
                    ))
                ):
                    dominated_by[candidate].append(other)
        frontier = sorted(
            implementation_id
            for implementation_id, dominators in dominated_by.items()
            if not dominators
        )

        winner_counts = {
            implementation_id: 0 for implementation_id in vectors
        }
        no_conclusion = 0
        representative: dict[str, Any] = {}
        for failure, missed, evidence in itertools.product(
            failure_losses, missed_values, evidence_multipliers
        ):
            scores = {
                implementation_id: (
                    row["weighted_TP"] * 20.0
                    - row["weighted_FP"] * failure
                    - row["weighted_FN"] * missed
                    - row["weighted_cost"] * evidence
                )
                for implementation_id, row in vectors.items()
            }
            best = max(scores.values())
            winners = sorted(
                implementation_id
                for implementation_id, score in scores.items()
                if abs(score - best) <= 1e-9
            )
            for winner in winners:
                winner_counts[winner] += 1
                representative.setdefault(winner, {
                    "failure_loss": failure,
                    "missed_opportunity_value": missed,
                    "evidence_multiplier": evidence,
                    "scores": {
                        key: round(value, 6)
                        for key, value in scores.items()
                    },
                })
            ordered = sorted(scores.values(), reverse=True)
            if len(winners) > 1 or ordered[0] - ordered[1] <= 1.0:
                no_conclusion += 1
        result[profile_name] = {
            "weighted_vectors": {
                implementation_id: {
                    key: round(value, 6)
                    for key, value in row.items()
                }
                for implementation_id, row in vectors.items()
            },
            "pareto_frontier": frontier,
            "dominated_by": {
                key: sorted(value)
                for key, value in dominated_by.items()
                if value
            },
            "winner_counts_including_ties": winner_counts,
            "no_conclusion_or_margin_le_1_count": no_conclusion,
            "representative_winner_regions": representative,
        }
    return {
        "frequency_profiles": list(profiles),
        "failure_loss_values": failure_losses,
        "missed_opportunity_values": missed_values,
        "evidence_cost_multipliers": evidence_multipliers,
        "points_per_profile": (
            len(failure_losses)
            * len(missed_values)
            * len(evidence_multipliers)
        ),
        "profiles": result,
        "interpretation": (
            "Regions are conditional on simulated scenario frequency and "
            "cost/loss weights; they are not a universal recommendation."
        ),
    }


def _primary_evidence_type(implementation_id: str) -> str:
    return {
        "IMPL_DECLARATION": "declaration",
        "IMPL_LATEST_PROBE": "probe",
        "IMPL_RECEIPT_WINDOW": "receipt_history",
        "IMPL_SLA_RECOVERY": "sla",
    }[implementation_id]


def _rows_by_implementation(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["implementation_id"], []).append(row)
    for implementation_id in grouped:
        grouped[implementation_id] = sorted(
            grouped[implementation_id], key=lambda row: row["world_token"]
        )
    return grouped


def _attack_results(
    database: dict[str, Any],
    truth: dict[str, Any],
    baseline_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_by_impl = _rows_by_implementation(baseline_rows)

    opaque_renamed = copy.deepcopy(database)
    rename_map = {
        old: f"r7c-{index:06x}"
        for index, old in enumerate(sorted(database["worlds"]), 1)
    }
    opaque_renamed["worlds"] = {
        rename_map[old]: world
        for old, world in opaque_renamed["worlds"].items()
    }
    for renamed_token, world in opaque_renamed["worlds"].items():
        world["request"]["world_token"] = renamed_token
    renamed_rows = run_candidates(opaque_renamed, STRATEGIES)
    reverse_rename = {value: key for key, value in rename_map.items()}
    renamed_signature = sorted(
        (
            reverse_rename[row["world_token"]],
            row["implementation_id"],
            row["decision"],
            row["cost"],
        )
        for row in renamed_rows
    )
    baseline_rename_signature = sorted(
        (
            row["world_token"],
            row["implementation_id"],
            row["decision"],
            row["cost"],
        )
        for row in baseline_rows
    )

    swapped_items = list(reversed(list(STRATEGIES.items())))
    swapped_map = {
        original_label: swapped_items[index][1]
        for index, original_label in enumerate(STRATEGIES)
    }
    swapped_rows = run_candidates(database, swapped_map)
    swapped_by_impl = _rows_by_implementation(swapped_rows)
    label_swap_invariant = True
    for implementation_id, rows in baseline_by_impl.items():
        baseline_signature = [
            (
                row["world_token"],
                row["decision"]["rely"],
                row["decision"]["decision_state"],
                row["cost"],
            )
            for row in rows
        ]
        swapped_signature = [
            (
                row["world_token"],
                row["decision"]["rely"],
                row["decision"]["decision_state"],
                row["cost"],
            )
            for row in swapped_by_impl[implementation_id]
        ]
        label_swap_invariant &= baseline_signature == swapped_signature

    deletion: dict[str, Any] = {}
    for label, function in STRATEGIES.items():
        probe_api = EvidenceAPI(
            database, sorted(database["worlds"])[0], label
        )
        implementation_id = function(probe_api)["implementation_id"]
        evidence_type = _primary_evidence_type(implementation_id)
        mutated = copy.deepcopy(database)
        for world in mutated["worlds"].values():
            world["evidence"].pop(evidence_type, None)
        rows = run_candidates(mutated, {label: function})
        deletion[implementation_id] = {
            "deleted_evidence_type": evidence_type,
            "relied_count": sum(row["decision"]["rely"] for row in rows),
            "unknown_count": sum(
                row["decision"]["decision_state"] == "UNKNOWN"
                for row in rows
            ),
            "cost": sum(
                row["cost"]["total_evidence_cost"] for row in rows
            ),
        }

    dependency_deletion: dict[str, Any] = {}
    for evidence_type in ("authority_status", "recovery_receipt"):
        mutated = copy.deepcopy(database)
        for world in mutated["worlds"].values():
            world["evidence"].pop(evidence_type, None)
        rows = run_candidates(mutated, STRATEGIES)
        dependency_deletion[evidence_type] = {
            implementation_id: {
                "relied_count": sum(
                    row["decision"]["rely"]
                    for row in implementation_rows
                ),
                "unknown_count": sum(
                    row["decision"]["decision_state"] == "UNKNOWN"
                    for row in implementation_rows
                ),
            }
            for implementation_id, implementation_rows
            in _rows_by_implementation(rows).items()
        }
    freshness_deleted = copy.deepcopy(database)
    for world in freshness_deleted["worlds"].values():
        probe = world["evidence"].get("probe", {}).get("record")
        if isinstance(probe, dict):
            probe.get("payload", {}).pop("issued_step", None)
    freshness_rows = run_candidates(
        freshness_deleted, {"LATEST_PROBE": STRATEGIES["LATEST_PROBE"]}
    )
    dependency_deletion["probe_freshness"] = {
        "IMPL_LATEST_PROBE": {
            "relied_count": sum(
                row["decision"]["rely"] for row in freshness_rows
            ),
            "unknown_count": sum(
                row["decision"]["decision_state"] == "UNKNOWN"
                for row in freshness_rows
            ),
        }
    }

    unauthorized: dict[str, Any] = {}
    for label, function in STRATEGIES.items():
        probe_api = EvidenceAPI(
            database, sorted(database["worlds"])[0], label
        )
        implementation_id = function(probe_api)["implementation_id"]
        evidence_type = _primary_evidence_type(implementation_id)
        mutated = copy.deepcopy(database)
        for world in mutated["worlds"].values():
            response = world["evidence"].get(evidence_type)
            if not isinstance(response, dict):
                continue
            records = []
            if isinstance(response.get("record"), dict):
                records.append(response["record"])
            records.extend(response.get("records", []))
            for record in records:
                record["signature_hex"] = "00" * 64
        rows = run_candidates(mutated, {label: function})
        unauthorized[implementation_id] = {
            "relied_count": sum(row["decision"]["rely"] for row in rows),
            "signature_failure_count": sum(
                not log["success"]
                for row in rows
                for log in row["operation_log"]
                if log["operation"] == "VERIFY_SIGNATURE"
            ),
        }

    flipped_truth = copy.deepcopy(truth)
    for world in flipped_truth["worlds"]:
        if isinstance(world["safe_to_rely"], bool):
            world["safe_to_rely"] = not world["safe_to_rely"]
    baseline_decisions_hash = canonical_sha256([
        (
            row["world_token"],
            row["implementation_id"],
            row["decision"],
            row["operation_log"],
        )
        for row in baseline_rows
    ])
    rerun = run_candidates(database, STRATEGIES)
    truth_flip_decisions_hash = canonical_sha256([
        (
            row["world_token"],
            row["implementation_id"],
            row["decision"],
            row["operation_log"],
        )
        for row in rerun
    ])

    injected_rows = copy.deepcopy(baseline_rows)
    for row in injected_rows:
        row["decision"].update({
            "accepted": True,
            "false_positive": 0,
            "net_value": 9999,
        })
    injected_metrics = _metrics(injected_rows, truth["worlds"])
    baseline_metrics = _metrics(baseline_rows, truth["worlds"])

    binding_attacks: dict[str, Any] = {}
    binding_world = next(
        row["world_token"]
        for row in truth["worlds"]
        if row["pair"] == "static" and row["variant"] == "VALID"
    )
    replacements = {
        "command_hash": "CMD-W7C-X1",
        "purpose": "sterile-route-counterfactual",
        "key_id": "RECIPIENT-KEY-v9",
        "environment": "SIM-ENV-X",
        "semantic_hash": "SEM-W7C-X1",
    }
    for field, replacement in replacements.items():
        mutated = copy.deepcopy(database)
        mutated["worlds"][binding_world]["request"][field] = replacement
        rows = run_candidates(mutated, STRATEGIES)
        target_rows = [
            row for row in rows if row["world_token"] == binding_world
        ]
        binding_attacks[field] = {
            row["implementation_id"]: {
                "rely": row["decision"]["rely"],
                "decision_state": row["decision"]["decision_state"],
            }
            for row in target_rows
        }

    refusal_world = next(
        row["world_token"]
        for row in truth["worlds"]
        if row["pair"] == "authority-response"
        and row["variant"] == "REFUSE"
    )
    observation_binding_attacks: dict[str, Any] = {}
    for field, replacement in replacements.items():
        mutated = copy.deepcopy(database)
        mutated["worlds"][refusal_world]["request"][field] = replacement
        rows = run_candidates(mutated, STRATEGIES)
        target_rows = [
            row for row in rows if row["world_token"] == refusal_world
        ]
        observation_binding_attacks[field] = {
            row["implementation_id"]: {
                "rely": row["decision"]["rely"],
                "decision_state": row["decision"]["decision_state"],
            }
            for row in target_rows
        }

    duplicate_database = copy.deepcopy(database)
    original_receipt = duplicate_database["worlds"][binding_world][
        "evidence"
    ]["receipt_history"]["records"][0]
    duplicate_database["worlds"][binding_world]["evidence"][
        "receipt_history"
    ]["records"] = [copy.deepcopy(original_receipt) for _ in range(3)]
    duplicate_rows = run_candidates(
        duplicate_database,
        {"RECEIPT_WINDOW": STRATEGIES["RECEIPT_WINDOW"]},
    )
    duplicate_target = next(
        row for row in duplicate_rows if row["world_token"] == binding_world
    )

    api = EvidenceAPI(database, binding_world, "REPEATED-READ-TEST")
    repeated_context = api.get_request_context()
    repeated_first = api.read("declaration")
    repeated_second = api.read("declaration")
    api.verify_signature(repeated_first["record"])
    api.verify_signature(repeated_second["record"])
    api.validate_freshness(
        repeated_first["record"], repeated_context, max_age=10
    )
    api.validate_freshness(
        repeated_second["record"], repeated_context, max_age=10
    )
    repeated_log = api.operation_log

    sample_log = copy.deepcopy(baseline_rows[0]["operation_log"])
    sample_reordered = list(reversed(sample_log))
    sample_deleted = sample_log[:-1]
    sample_added = sample_log + [copy.deepcopy(sample_log[-1])]
    operation_log_attack = {
        "baseline": reconstruct_cost(sample_log, BASELINE_COST_MODEL),
        "reordered": reconstruct_cost(
            sample_reordered, BASELINE_COST_MODEL
        ),
        "one_operation_deleted": reconstruct_cost(
            sample_deleted, BASELINE_COST_MODEL
        ),
        "one_operation_added": reconstruct_cost(
            sample_added, BASELINE_COST_MODEL
        ),
        "candidate_self_reported_cost": -9999,
        "candidate_cost_field_used": False,
    }

    epistemic_worlds = {
        row.get("epistemic_truth"): row["world_token"]
        for row in truth["worlds"]
        if row.get("epistemic_truth") in {"UNKNOWN", "REFUSE", "ABSENT"}
        and row["pair"] != "beneficiary"
    }
    epistemic_rows = run_candidates(database, STRATEGIES)
    epistemic_preservation = {
        state: sorted({
            row["decision"]["decision_state"]
            for row in epistemic_rows
            if row["world_token"] == token
        })
        for state, token in epistemic_worlds.items()
    }

    strategy_source = (BASE_DIR / "strategies.py").read_text(
        encoding="utf-8"
    )
    api_source = (BASE_DIR / "evidence_api.py").read_text(
        encoding="utf-8"
    )
    return {
        "opaque_rename": {
            "behavior_and_cost_invariant": (
                renamed_signature == baseline_rename_signature
            ),
            "same_length_opaque_tokens_used": all(
                len(old) == len(new) for old, new in rename_map.items()
            ),
        },
        "label_function_swap": {
            "implementation_results_and_cost_invariant": label_swap_invariant,
        },
        "evidence_deletion": deletion,
        "dependency_deletion": dependency_deletion,
        "unauthorized_signature": unauthorized,
        "candidate_private_key_surface": {
            "strategies_or_api_reference_private_builder": (
                "build_public_fixture" in strategy_source
                or "build_public_fixture" in api_source
            ),
            "strategies_or_api_reference_private_key_type": (
                "Ed25519PrivateKey" in strategy_source
                or "Ed25519PrivateKey" in api_source
            ),
            "strategies_or_api_reference_hidden_truth": (
                "truth.json" in strategy_source
                or "truth.json" in api_source
                or "DEFAULT_TRUTH" in strategy_source
                or "DEFAULT_TRUTH" in api_source
            ),
        },
        "bytes_binding": binding_attacks,
        "signed_observation_bytes_binding": observation_binding_attacks,
        "duplicate_evidence": {
            "world_token": binding_world,
            "rely": duplicate_target["decision"]["rely"],
            "decision_state": duplicate_target["decision"]["decision_state"],
            "reason": duplicate_target["decision"]["reason"],
        },
        "repeated_access_billing": {
            "cache_semantics": (
                "No implicit cache: every read, signature verification, and "
                "freshness check is a separately logged and billed operation."
            ),
            "operation_counts": {
                operation: sum(
                    row["operation"] == operation for row in repeated_log
                )
                for operation in (
                    "READ_REQUEST_CONTEXT",
                    "READ_EVIDENCE",
                    "VERIFY_SIGNATURE",
                    "VALIDATE_FRESHNESS",
                )
            },
            "cost": reconstruct_cost(
                repeated_log, BASELINE_COST_MODEL
            ),
        },
        "operation_log_recompute": operation_log_attack,
        "missing_conflicting_observations": {
            "candidate_outputs_by_hidden_observation": (
                epistemic_preservation
            ),
            "all_three_remain_distinct": (
                epistemic_preservation.get("UNKNOWN") == ["UNKNOWN"]
                and epistemic_preservation.get("REFUSE") == ["REFUSE"]
                and epistemic_preservation.get("ABSENT") == ["ABSENT"]
            ),
        },
        "self_report_injection": {
            "independent_metrics_invariant": (
                injected_metrics == baseline_metrics
            ),
            "ignored_fields": [
                "accepted",
                "false_positive",
                "net_value",
            ],
        },
        "truth_label_flip": {
            "candidate_decisions_and_logs_invariant": (
                baseline_decisions_hash == truth_flip_decisions_hash
            ),
            "original_confusion": _metrics(
                baseline_rows, truth["worlds"]
            ),
            "flipped_confusion": _metrics(
                rerun, flipped_truth["worlds"]
            ),
        },
    }


def evaluate(
    database: dict[str, Any],
    truth: dict[str, Any],
) -> dict[str, Any]:
    truth_tokens = {row["world_token"] for row in truth["worlds"]}
    if truth_tokens != set(database["worlds"]):
        raise ValueError("public opaque worlds and hidden truth are not closed")
    baseline_rows = run_candidates(database, STRATEGIES)
    metrics = _metrics(baseline_rows, truth["worlds"])
    return {
        "schema_version": "1.0",
        "shared_task_sha256": truth["shared_task_sha256"],
        "public_fixture_sha256": canonical_sha256(database),
        "hidden_truth_sha256": canonical_sha256(truth),
        "cost_model": BASELINE_COST_MODEL,
        "per_strategy": metrics,
        "per_scenario": _per_scenario(baseline_rows, truth["worlds"]),
        "distribution_shift": {
            implementation_id: row["distribution_shift"]
            for implementation_id, row in metrics.items()
        },
        "pareto": _pareto(metrics),
        "sensitivity": _sensitivity(metrics),
        "frequency_and_cost_regions": _frequency_cost_regions(
            baseline_rows, truth["worlds"]
        ),
        "attacks": _attack_results(
            database, truth, baseline_rows
        ),
        "claims": {
            "cost_reconstructed_only_from_api_operation_log": True,
            "strategy_label_used_for_cost": False,
            "truth_visible_to_candidate": False,
            "single_aggregate_winner_is_universal_recommendation": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = evaluate(load_json(args.evidence), load_json(args.truth))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
