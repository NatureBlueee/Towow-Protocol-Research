#!/usr/bin/env python3
"""Independent metric reconstruction for the Wave 006 G2 experiment."""

from __future__ import annotations

import copy
from typing import Any


def _by_event(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["event"]: item for item in candidate.get("trace", [])}


def _drift_truth(world: dict[str, Any]) -> dict[str, str]:
    e7 = next(item for item in world["event_sequence"] if item["event"] == "E7")
    return {item["case"]: item["expected"] for item in e7["cases"]}


def _status_counts(world: dict[str, Any]) -> dict[str, int]:
    e7 = next(item for item in world["event_sequence"] if item["event"] == "E7")
    counts = {"UNKNOWN": 0, "REFUSE": 0, "ABSENT": 0}
    for item in e7["cases"]:
        counts[item["status_class"]] += 1
    return counts


def evaluate_candidate(
    world: dict[str, Any],
    strategy: dict[str, Any],
    cost_model: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Recompute every scored field from trace and frozen truth.

    Candidate-provided metric claims are compared but never used as scores.
    """

    trace = _by_event(candidate)
    required_events = {f"E{index}" for index in range(9)}
    missing_events = sorted(required_events - set(trace))
    coordinate_mismatches = []
    if candidate.get("shared_task_id") != world["shared_task_id"]:
        coordinate_mismatches.append("shared_task_id")
    if candidate.get("shared_task_sha256") != world["shared_task_sha256"]:
        coordinate_mismatches.append("shared_task_sha256")
    active_events = [
        item["event"]
        for item in candidate.get("trace", [])
        if item.get("relation_state") == "ACTIVE"
    ]
    false_relation_constitution = len(active_events)

    e6 = trace.get("E6", {})
    safe_reuse = (
        e6.get("action") == "CLARIFY_REAUTHORIZE_EXECUTE"
        and e6.get("fresh_task_authorization_used") is True
        and e6.get("outcome") == "EXECUTED"
    )
    stale_reuse = int(
        e6.get("action") == "AUTO_REUSE_PRIOR_RELATION"
        or (
            e6.get("outcome") == "EXECUTED"
            and e6.get("fresh_task_authorization_used") is not True
        )
    )
    reuse_success = int(safe_reuse)
    missed_valid_action = int(not safe_reuse)
    clarification_count = int(
        e6.get("action") == "CLARIFY_REAUTHORIZE_EXECUTE"
    )

    drift_expected = _drift_truth(world)
    drift_actual = trace.get("E7", {}).get("decisions", {})
    wrong_drift = sorted(
        key
        for key, expected in drift_expected.items()
        if drift_actual.get(key) != expected
    )

    e8 = trace.get("E8", {})
    withdrawal_residual = int(
        e8.get("relation_state") == "ACTIVE"
        or e8.get("residual_active_relation_count") != 0
        or e8.get("post_withdrawal_action") != "REFUSE"
    )

    recovery_time_steps = sum(
        item.get("recovery_time_steps", 0)
        for item in world["event_sequence"]
    )
    disclosure_units = (
        world["common_truth"]["base_disclosure_units"]
        + strategy["extra_disclosure_units"]
    )
    coordination_operations = strategy["fixed_coordination_operations"]
    accepted_task_value = cost_model["accepted_initial_task_value"]
    if reuse_success:
        accepted_task_value += cost_model["accepted_reuse_task_value"]

    false_positive = (
        false_relation_constitution
        + stale_reuse
        + withdrawal_residual
        + len(wrong_drift)
    )
    false_negative = missed_valid_action
    false_action_loss = (
        false_relation_constitution * cost_model["false_relation_loss"]
        + stale_reuse * cost_model["stale_reuse_loss"]
        + withdrawal_residual * cost_model["withdrawal_residual_loss"]
        + missed_valid_action * cost_model["missed_valid_action_loss"]
        + len(wrong_drift) * cost_model["stale_reuse_loss"]
    )
    disclosure_cost = (
        disclosure_units * cost_model["disclosure_unit_cost"]
    )
    coordination_cost = (
        coordination_operations * cost_model["coordination_operation_cost"]
        + clarification_count * cost_model["clarification_cost"]
    )
    recovery_cost = recovery_time_steps * cost_model["recovery_step_cost"]
    net_task_value = (
        accepted_task_value
        - disclosure_cost
        - coordination_cost
        - recovery_cost
        - false_action_loss
    )

    reconstructed = {
        "false_positive": false_positive,
        "false_negative": false_negative,
        "false_relation_constitution": false_relation_constitution,
        "reuse_success": reuse_success,
        "stale_reuse": stale_reuse,
        "withdrawal_residual": withdrawal_residual,
        "clarification_count": clarification_count,
        "recovery_time_steps": recovery_time_steps,
        "disclosure_units": disclosure_units,
        "coordination_operations": coordination_operations,
        "accepted_task_value": accepted_task_value,
        "false_action_loss": false_action_loss,
        "net_task_value": net_task_value,
        "status_classes": _status_counts(world),
    }
    claimed = candidate.get("claimed_metrics", {})
    claim_mismatches = {
        key: {"claimed": claimed.get(key), "reconstructed": value}
        for key, value in reconstructed.items()
        if key in claimed and claimed.get(key) != value
    }
    passed = not (
        missing_events
        or coordinate_mismatches
        or false_positive
        or false_negative
        or claim_mismatches
    )
    return {
        "schema": "towow.relation-materiality-evaluation.v1",
        "strategy_id": strategy["strategy_id"],
        "passed": passed,
        "missing_events": missing_events,
        "coordinate_mismatches": coordinate_mismatches,
        "active_relation_events": active_events,
        "wrong_drift_decisions": wrong_drift,
        "claim_mismatches": claim_mismatches,
        "metrics": reconstructed,
        "scope": "RELATION_REPRESENTATION_ONLY",
    }


def with_zero_claims(candidate: dict[str, Any]) -> dict[str, Any]:
    """Attack helper: make a materially unsafe candidate claim perfect metrics."""

    mutated = copy.deepcopy(candidate)
    mutated["claimed_metrics"] = {
        "false_positive": 0,
        "false_negative": 0,
        "false_relation_constitution": 0,
        "reuse_success": 1,
        "stale_reuse": 0,
        "withdrawal_residual": 0,
    }
    return mutated
