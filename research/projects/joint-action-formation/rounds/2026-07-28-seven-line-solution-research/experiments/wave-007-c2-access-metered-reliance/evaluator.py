#!/usr/bin/env python3
"""C2 evaluator with parent-owned identity, broker ledger, and hidden truth."""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from broker import DEFAULT_EVIDENCE, load_json, reconstruct_cost
from runner import (
    BASELINE_COST_MODEL,
    DEFAULT_REGISTRY,
    run_candidates,
    run_worker,
)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TRUTH = BASE_DIR / "private" / "truth.json"
DEFAULT_OUTPUT = BASE_DIR / "results" / "evaluation.json"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _group(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["implementation_id"], []).append(row)
    return grouped


def _cell(rely: bool, expected: bool | None) -> str:
    if expected is None:
        return "UNKNOWN_TRUTH"
    if rely and expected:
        return "TP"
    if rely and not expected:
        return "FP"
    if not rely and expected:
        return "FN"
    return "TN"


def metrics(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = {row["world_token"]: row for row in truth_rows}
    result: dict[str, Any] = {}
    for implementation_id, rows in sorted(_group(candidate_rows).items()):
        confusion = {
            key: 0 for key in ("TP", "FP", "TN", "FN", "UNKNOWN_TRUTH")
        }
        split_confusion = {
            split: {
                key: 0
                for key in ("TP", "FP", "TN", "FN", "UNKNOWN_TRUTH")
            }
            for split in ("IN_DISTRIBUTION", "SHIFTED")
        }
        cost = {
            key: 0
            for key in (
                "api_operations",
                "bytes",
                "latency_ms",
                "disclosure_units",
                "retries",
                "total_evidence_cost",
            )
        }
        operation_success = 0
        business_accepted = 0
        epistemic = {"UNKNOWN": 0, "REFUSE": 0, "ABSENT": 0}
        for row in rows:
            world = truth[row["world_token"]]
            cell = _cell(
                bool(row["decision"]["rely"]),
                world["safe_to_rely"],
            )
            confusion[cell] += 1
            split_confusion[world["split"]][cell] += 1
            for key in cost:
                cost[key] += row["cost"][key]
            if (
                row["decision"]["rely"]
                and world.get("operation_success")
            ):
                operation_success += 1
            if (
                row["decision"]["rely"]
                and world.get("business_accepted")
            ):
                business_accepted += 1
            state = row["decision"]["decision_state"]
            if state in epistemic:
                epistemic[state] += 1
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
                step for step, row in sequence
                if truth[row["world_token"]].get("recovery_at_step")
                == step
            ),
            None,
        )
        recovery_steps = 0
        if recovery_at is not None:
            recovery_step = next(
                (
                    step for step, row in sequence
                    if step >= recovery_at
                    and row["decision"]["rely"]
                    and truth[row["world_token"]]["safe_to_rely"] is True
                ),
                max(step for step, _ in sequence) + 1,
            )
            recovery_steps = recovery_step - recovery_at
        result[implementation_id] = {
            "confusion": confusion,
            "cost": {
                key: round(value, 6)
                if isinstance(value, float) else value
                for key, value in cost.items()
            },
            "operation_success_when_relied": operation_success,
            "business_effect_when_relied": business_accepted,
            "recovery_time_steps": recovery_steps,
            "epistemic_output_counts": epistemic,
            "distribution_shift": {
                "per_split_confusion": split_confusion,
                "error_delta_shift_minus_in_distribution": (
                    split_confusion["SHIFTED"]["FP"]
                    + split_confusion["SHIFTED"]["FN"]
                    - split_confusion["IN_DISTRIBUTION"]["FP"]
                    - split_confusion["IN_DISTRIBUTION"]["FN"]
                ),
            },
        }
    return result


def per_scenario(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = {row["world_token"]: row for row in truth_rows}
    result: dict[str, Any] = {}
    for row in candidate_rows:
        world = truth[row["world_token"]]
        scenario = f"{world['pair']}::{world['variant']}"
        result.setdefault(scenario, {
            "split": world["split"],
            "safe_to_rely": world["safe_to_rely"],
            "operation_success": world["operation_success"],
            "business_accepted": world["business_accepted"],
            "strategies": {},
        })
        relied = bool(row["decision"]["rely"])
        result[scenario]["strategies"][row["implementation_id"]] = {
            "decision_state": row["decision"]["decision_state"],
            "rely": relied,
            "confusion_cell": _cell(relied, world["safe_to_rely"]),
            "cost": row["cost"],
            "recovery": (
                {
                    "delay_steps": 0 if relied else None,
                    "censored_without_reliance": not relied,
                }
                if world["pair"] == "recovery" else None
            ),
        }
    return result


def pareto(per_strategy: dict[str, Any]) -> dict[str, Any]:
    vectors = {
        implementation_id: (
            -row["confusion"]["TP"],
            row["confusion"]["FP"],
            row["confusion"]["FN"],
            row["cost"]["total_evidence_cost"],
            row["recovery_time_steps"],
        )
        for implementation_id, row in per_strategy.items()
    }
    dominated_by = {key: [] for key in vectors}
    for candidate, candidate_vector in vectors.items():
        for other, other_vector in vectors.items():
            if candidate == other:
                continue
            if (
                all(left <= right for left, right in zip(
                    other_vector, candidate_vector
                ))
                and any(left < right for left, right in zip(
                    other_vector, candidate_vector
                ))
            ):
                dominated_by[candidate].append(other)
    return {
        "objectives": [
            "maximize_TP",
            "minimize_FP",
            "minimize_FN",
            "minimize_actual_evidence_cost",
            "minimize_recovery_time",
        ],
        "frontier": sorted(
            key for key, value in dominated_by.items() if not value
        ),
        "dominated_by": {
            key: sorted(value)
            for key, value in dominated_by.items() if value
        },
    }


def sensitivity(per_strategy: dict[str, Any]) -> dict[str, Any]:
    failure_losses = [0.0, 5.0, 20.0, 50.0]
    missed_values = [0.0, 5.0, 20.0]
    evidence_multipliers = [0.5, 1.0, 2.0, 4.0]
    winner_counts = {key: 0 for key in per_strategy}
    unique_counts = {key: 0 for key in per_strategy}
    no_conclusion = 0
    examples: dict[str, Any] = {}
    for failure, missed, evidence in itertools.product(
        failure_losses, missed_values, evidence_multipliers
    ):
        scores = {
            key: (
                row["business_effect_when_relied"] * 20.0
                - row["confusion"]["FP"] * failure
                - row["confusion"]["FN"] * missed
                - row["cost"]["total_evidence_cost"] * evidence
                - row["recovery_time_steps"] * 2.0
            )
            for key, row in per_strategy.items()
        }
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
                "scores": {
                    key: round(value, 6)
                    for key, value in scores.items()
                },
            })
        if len(winners) == 1:
            unique_counts[winners[0]] += 1
        ordered = sorted(scores.values(), reverse=True)
        if len(winners) > 1 or ordered[0] - ordered[1] <= 1.0:
            no_conclusion += 1
    return {
        "ranges": {
            "failure_loss": failure_losses,
            "missed_opportunity_value": missed_values,
            "evidence_multiplier": evidence_multipliers,
        },
        "point_count": 48,
        "winner_counts_including_ties": winner_counts,
        "unique_winner_counts": unique_counts,
        "no_conclusion_or_margin_le_1_count": no_conclusion,
        "representative_winner_regions": examples,
    }


def frequency_regions(
    candidate_rows: list[dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    truth = {row["world_token"]: row for row in truth_rows}
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
    }
    output: dict[str, Any] = {}
    for profile, weight_function in profiles.items():
        vectors: dict[str, dict[str, float]] = {}
        for implementation_id, rows in _group(candidate_rows).items():
            vector = {"TP": 0.0, "FP": 0.0, "FN": 0.0, "cost": 0.0}
            for row in rows:
                world = truth[row["world_token"]]
                weight = weight_function(world)
                cell = _cell(
                    bool(row["decision"]["rely"]),
                    world["safe_to_rely"],
                )
                if cell in {"TP", "FP", "FN"}:
                    vector[cell] += weight
                vector["cost"] += (
                    weight * row["cost"]["total_evidence_cost"]
                )
            vectors[implementation_id] = vector
        counts = {key: 0 for key in vectors}
        no_conclusion = 0
        for failure, missed, evidence in itertools.product(
            [0.0, 10.0, 50.0],
            [0.0, 10.0, 50.0],
            [0.5, 1.0, 4.0],
        ):
            scores = {
                key: (
                    row["TP"] * 20.0
                    - row["FP"] * failure
                    - row["FN"] * missed
                    - row["cost"] * evidence
                )
                for key, row in vectors.items()
            }
            best = max(scores.values())
            winners = [
                key for key, value in scores.items()
                if abs(value - best) <= 1e-9
            ]
            for winner in winners:
                counts[winner] += 1
            ordered = sorted(scores.values(), reverse=True)
            if len(winners) > 1 or ordered[0] - ordered[1] <= 1.0:
                no_conclusion += 1
        output[profile] = {
            "weighted_vectors": {
                key: {
                    field: round(value, 6)
                    for field, value in row.items()
                }
                for key, row in vectors.items()
            },
            "winner_counts_including_ties": counts,
            "no_conclusion_or_margin_le_1_count": no_conclusion,
        }
    return {
        "points_per_profile": 27,
        "profiles": output,
        "interpretation": (
            "Counterfactual frequency and cost regions, not real-world "
            "frequencies or a universal recommendation."
        ),
    }


def direct_mutations(
    database: dict[str, Any],
    truth: dict[str, Any],
    baseline_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    active_token = "w7c-50de71"
    revoked_token = "w7c-a76e20"
    replayed = copy.deepcopy(database)
    replayed["worlds"][revoked_token]["evidence"][
        "authority_status"
    ] = copy.deepcopy(
        replayed["worlds"][active_token]["evidence"]["authority_status"]
    )
    replay_rows = run_candidates(
        replayed, world_tokens=[revoked_token]
    )
    forged_context_row = run_worker(
        replayed,
        revoked_token,
        "IMPL_DECLARATION",
        "FORGE_AUTHORITY_CONTEXT",
        "DECLARATION",
    )

    valid_token = "w7c-8f13a0"
    malicious = run_worker(
        database,
        valid_token,
        "IMPL_DECLARATION",
        "MALICIOUS_CLEAR_LOG",
        "DECLARATION",
    )
    spoofed = run_worker(
        database,
        valid_token,
        "IMPL_DECLARATION",
        "SPOOF_IMPLEMENTATION_ID",
        "DECLARATION",
    )

    swapped_labels = {
        owner: {
            **registration,
            "display_label": f"RENAMED-{index}",
        }
        for index, (owner, registration)
        in enumerate(DEFAULT_REGISTRY.items(), 1)
    }
    renamed_rows = run_candidates(database, swapped_labels)
    baseline_signature = sorted(
        (
            row["world_token"],
            row["implementation_id"],
            row["decision"],
            row["cost"],
        )
        for row in baseline_rows
    )
    renamed_signature = sorted(
        (
            row["world_token"],
            row["implementation_id"],
            row["decision"],
            row["cost"],
        )
        for row in renamed_rows
    )

    deletion_results: dict[str, Any] = {}
    primary = {
        "IMPL_DECLARATION": "declaration",
        "IMPL_LATEST_PROBE": "probe",
        "IMPL_RECEIPT_WINDOW": "receipt_history",
        "IMPL_SLA_RECOVERY": "sla",
    }
    for owner, evidence_type in primary.items():
        mutated = copy.deepcopy(database)
        for world in mutated["worlds"].values():
            world["evidence"].pop(evidence_type, None)
        rows = run_candidates(
            mutated, {owner: DEFAULT_REGISTRY[owner]}
        )
        deletion_results[owner] = {
            "deleted_evidence_type": evidence_type,
            "relied_count": sum(
                bool(row["decision"]["rely"]) for row in rows
            ),
            "unknown_count": sum(
                row["decision"]["decision_state"] == "UNKNOWN"
                for row in rows
            ),
        }

    duplicate = copy.deepcopy(database)
    record = duplicate["worlds"][valid_token]["evidence"][
        "receipt_history"
    ]["records"][0]
    duplicate["worlds"][valid_token]["evidence"][
        "receipt_history"
    ]["records"] = [copy.deepcopy(record) for _ in range(3)]
    duplicate_row = run_worker(
        duplicate,
        valid_token,
        "IMPL_RECEIPT_WINDOW",
        "RECEIPT_WINDOW",
        "RECEIPT_WINDOW",
    )

    repeated = run_worker(
        database,
        valid_token,
        "IMPL_REPEATED_ACCESS_TEST",
        "REPEATED_ACCESS",
        "REPEATED_ACCESS",
    )
    repeated_counts = {
        operation: sum(
            row["operation"] == operation
            for row in repeated["operation_log"]
        )
        for operation in (
            "READ_EVIDENCE",
            "VERIFY_SIGNATURE",
            "VALIDATE_FRESHNESS",
        )
    }

    sample_log = copy.deepcopy(baseline_rows[0]["operation_log"])
    log_recompute = {
        "baseline": reconstruct_cost(sample_log, BASELINE_COST_MODEL),
        "reordered": reconstruct_cost(
            list(reversed(sample_log)), BASELINE_COST_MODEL
        ),
        "one_deleted": reconstruct_cost(
            sample_log[:-1], BASELINE_COST_MODEL
        ),
        "one_added": reconstruct_cost(
            sample_log + [copy.deepcopy(sample_log[-1])],
            BASELINE_COST_MODEL,
        ),
        "candidate_cost_field_used": False,
    }

    flipped_truth = copy.deepcopy(truth)
    for world in flipped_truth["worlds"]:
        if isinstance(world["safe_to_rely"], bool):
            world["safe_to_rely"] = not world["safe_to_rely"]
    rerun = run_candidates(database)

    opaque = copy.deepcopy(database)
    rename_map = {
        old: f"r72-{index:06x}"
        for index, old in enumerate(sorted(database["worlds"]), 1)
    }
    opaque["worlds"] = {
        rename_map[old]: world
        for old, world in opaque["worlds"].items()
    }
    for renamed_token, world in opaque["worlds"].items():
        world["request"]["world_token"] = renamed_token
    opaque_rows = run_candidates(opaque)
    reverse_rename = {value: key for key, value in rename_map.items()}
    opaque_signature = sorted(
        (
            reverse_rename[row["world_token"]],
            row["implementation_id"],
            row["decision"],
            row["cost"],
        )
        for row in opaque_rows
    )

    injected = copy.deepcopy(baseline_rows)
    for row in injected:
        row["decision"].update({
            "accepted": True,
            "false_positive": 0,
            "net_value": 9999,
        })

    authority_missing = copy.deepcopy(database)
    authority_missing["worlds"][valid_token]["evidence"].pop(
        "authority_status", None
    )
    authority_missing_rows = run_candidates(
        authority_missing, world_tokens=[valid_token]
    )

    unauthorized_signature: dict[str, Any] = {}
    for owner, evidence_type in primary.items():
        mutated = copy.deepcopy(database)
        response = mutated["worlds"][valid_token]["evidence"][
            evidence_type
        ]
        records = []
        if isinstance(response.get("record"), dict):
            records.append(response["record"])
        records.extend(response.get("records", []))
        for record in records:
            record["signature_hex"] = "00" * 64
        row = run_worker(
            mutated,
            valid_token,
            owner,
            DEFAULT_REGISTRY[owner]["worker_strategy"],
            DEFAULT_REGISTRY[owner]["display_label"],
        )
        unauthorized_signature[owner] = {
            "rely": row["decision"]["rely"],
            "signature_failure_count": sum(
                log["operation"] == "VERIFY_SIGNATURE"
                and not log["success"]
                for log in row["operation_log"]
            ),
        }

    bytes_binding: dict[str, Any] = {}
    replacements = {
        "command_hash": "CMD-W7C-X1",
        "purpose": "sterile-route-counterfactual",
        "key_id": "RECIPIENT-KEY-v9",
        "environment": "SIM-ENV-X",
    }
    for field, replacement in replacements.items():
        mutated = copy.deepcopy(database)
        mutated["worlds"][valid_token]["request"][field] = replacement
        rows = run_candidates(mutated, world_tokens=[valid_token])
        bytes_binding[field] = {
            row["implementation_id"]: {
                "rely": row["decision"]["rely"],
                "decision_state": row["decision"]["decision_state"],
            }
            for row in rows
        }

    freshness_missing = copy.deepcopy(database)
    freshness_missing["worlds"][valid_token]["evidence"]["probe"][
        "record"
    ]["payload"].pop("issued_step", None)
    freshness_row = run_worker(
        freshness_missing,
        valid_token,
        "IMPL_LATEST_PROBE",
        "LATEST_PROBE",
        "LATEST_PROBE",
    )

    recovery_missing = copy.deepcopy(database)
    recovery_missing["worlds"]["w7c-926db1"]["evidence"].pop(
        "recovery_receipt", None
    )
    recovery_row = run_worker(
        recovery_missing,
        "w7c-926db1",
        "IMPL_SLA_RECOVERY",
        "SLA_RECOVERY",
        "SLA_RECOVERY",
    )

    private_read = run_worker(
        database,
        valid_token,
        "IMPL_DECLARATION",
        "PRIVATE_STATE_READ_ATTEMPT",
        "DECLARATION",
    )
    epistemic_tokens = {
        row["epistemic_truth"]: row["world_token"]
        for row in truth["worlds"]
        if row.get("epistemic_truth") in {
            "UNKNOWN", "REFUSE", "ABSENT"
        }
        and row["pair"] != "beneficiary"
    }
    epistemic_preservation = {
        state: sorted({
            row["decision"]["decision_state"]
            for row in baseline_rows
            if row["world_token"] == token
        })
        for state, token in epistemic_tokens.items()
    }

    return {
        "audit_failure_1_authority_active_replay": {
            "source_world": active_token,
            "target_revoked_world": revoked_token,
            "target_trusted_authority_head": database["worlds"][
                revoked_token
            ]["request"]["authority_head"],
            "replayed_authority_head": database["worlds"][
                active_token
            ]["request"]["authority_head"],
            "strategies": {
                row["implementation_id"]: {
                    "rely": row["decision"]["rely"],
                    "decision_state": row["decision"]["decision_state"],
                    "authority_head_validation_failed": any(
                        log["operation"] == "VALIDATE_AUTHORITY_HEAD"
                        and not log["success"]
                        for log in row["operation_log"]
                    ),
                }
                for row in replay_rows
            },
            "old_active_replay_rejected_by_all": all(
                not row["decision"]["rely"] for row in replay_rows
            ),
            "candidate_forged_context_rely": (
                forged_context_row["decision"]["rely"]
            ),
            "parent_trusted_context_cannot_be_overridden": (
                not forged_context_row["decision"]["rely"]
            ),
        },
        "audit_failure_2_candidate_log_clear": {
            "decision_rely_unchanged": malicious["decision"]["rely"],
            "candidate_attempt": malicious["decision"][
                "mutation_attempt"
            ],
            "parent_log_operation_count": malicious["cost"][
                "api_operations"
            ],
            "parent_cost": malicious["cost"],
            "denied_control_rpc_count": sum(
                row["operation"] == "DENIED_RPC"
                for row in malicious["operation_log"]
            ),
            "candidate_cleared_parent_log": False,
        },
        "audit_failure_3_identity_spoof": {
            "registry_owner_identity": spoofed["implementation_id"],
            "candidate_claimed_identity": (
                spoofed["candidate_claimed_implementation_id"]
            ),
            "evaluator_group_identity": next(iter(
                metrics([spoofed], truth["worlds"])
            )),
            "candidate_identity_used_for_grouping": False,
        },
        "candidate_private_state_read": {
            "runtime_guard": (
                "Python audit hook denies candidate-time file reads, "
                "imports, process expansion, and network operations."
            ),
            "read_blocked": private_read["decision"][
                "private_state_read_blocked"
            ],
            "private_state_sent_over_rpc": False,
        },
        "opaque_rename": {
            "same_length_tokens": all(
                len(old) == len(new) for old, new in rename_map.items()
            ),
            "decisions_and_cost_invariant": (
                opaque_signature == baseline_signature
            ),
        },
        "self_report_injection": {
            "independent_metrics_invariant": (
                metrics(injected, truth["worlds"])
                == metrics(baseline_rows, truth["worlds"])
            ),
            "ignored_fields": [
                "accepted", "false_positive", "net_value"
            ],
        },
        "label_only_rename": {
            "decisions_and_cost_invariant": (
                baseline_signature == renamed_signature
            )
        },
        "primary_evidence_deletion": deletion_results,
        "authority_status_deletion": {
            row["implementation_id"]: {
                "rely": row["decision"]["rely"],
                "decision_state": row["decision"]["decision_state"],
            }
            for row in authority_missing_rows
        },
        "probe_freshness_deletion": {
            "rely": freshness_row["decision"]["rely"],
            "decision_state": freshness_row["decision"][
                "decision_state"
            ],
        },
        "recovery_receipt_deletion": {
            "rely": recovery_row["decision"]["rely"],
            "decision_state": recovery_row["decision"][
                "decision_state"
            ],
        },
        "unauthorized_signature": unauthorized_signature,
        "bytes_binding": bytes_binding,
        "duplicate_receipt": {
            "rely": duplicate_row["decision"]["rely"],
            "decision_state": duplicate_row["decision"]["decision_state"],
        },
        "repeated_access_billing": {
            "semantics": (
                "No implicit cache. Each repeated read, verification, and "
                "freshness check reaches the parent broker and is billed."
            ),
            "operation_counts": repeated_counts,
            "cost": repeated["cost"],
        },
        "operation_log_recompute": log_recompute,
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
        "truth_label_flip": {
            "candidate_decisions_and_logs_invariant": canonical_sha256([
                (
                    row["world_token"],
                    row["implementation_id"],
                    row["decision"],
                    row["operation_log"],
                )
                for row in baseline_rows
            ]) == canonical_sha256([
                (
                    row["world_token"],
                    row["implementation_id"],
                    row["decision"],
                    row["operation_log"],
                )
                for row in rerun
            ]),
            "original_metrics": metrics(
                baseline_rows, truth["worlds"]
            ),
            "flipped_metrics": metrics(
                rerun, flipped_truth["worlds"]
            ),
        },
    }


def evaluate(
    database: dict[str, Any],
    truth: dict[str, Any],
) -> dict[str, Any]:
    if set(database["worlds"]) != {
        row["world_token"] for row in truth["worlds"]
    }:
        raise ValueError("public fixture and hidden truth are not closed")
    baseline_rows = run_candidates(database)
    per_strategy = metrics(baseline_rows, truth["worlds"])
    return {
        "schema_version": "2.0",
        "shared_task_sha256": truth["shared_task_sha256"],
        "public_fixture_sha256": canonical_sha256(database),
        "hidden_truth_sha256": canonical_sha256(truth),
        "cost_model": BASELINE_COST_MODEL,
        "per_strategy": per_strategy,
        "per_scenario": per_scenario(
            baseline_rows, truth["worlds"]
        ),
        "distribution_shift": {
            key: value["distribution_shift"]
            for key, value in per_strategy.items()
        },
        "pareto": pareto(per_strategy),
        "sensitivity": sensitivity(per_strategy),
        "frequency_and_cost_regions": frequency_regions(
            baseline_rows, truth["worlds"]
        ),
        "direct_mutations": direct_mutations(
            database, truth, baseline_rows
        ),
        "claims": {
            "authority_status_bound_to_trusted_head_epoch_contract": True,
            "candidate_process_can_access_parent_raw_log": False,
            "cost_reconstructed_from_parent_broker_log": True,
            "candidate_claimed_identity_is_authoritative": False,
            "implementation_self_check_is_independent_evidence": False,
            "universal_winner_claimed": False,
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
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
