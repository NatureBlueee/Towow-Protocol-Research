#!/usr/bin/env python3
"""Four reliance strategies over one frozen Wave-006 operation timeline."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FIXTURE = BASE_DIR / "fixtures" / "timeline.json"


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON top level must be an object")
    return value


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def visible_snapshot(
    fixture: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Expand only frozen evidence visible at this decision point."""
    visible = deep_merge(
        fixture["base_visible"],
        fixture["visible_presets"].get(snapshot.get("visible_preset", "steady"), {}),
    )
    visible = deep_merge(visible, snapshot.get("visible_override", {}))
    visible["decision_step"] = snapshot["step"]
    visible["event_history"] = copy.deepcopy(snapshot["event_history"])
    return visible


def _epistemic_guard(visible: dict[str, Any]) -> dict[str, Any] | None:
    state = visible["current"]["epistemic_state"]
    if state in {"UNKNOWN", "REFUSE", "ABSENT"}:
        return {
            "rely": False,
            "decision_state": state,
            "reason": f"explicit_{state.lower()}",
        }
    return None


def declaration_strategy(visible: dict[str, Any]) -> dict[str, Any]:
    guarded = _epistemic_guard(visible)
    if guarded:
        return guarded
    declaration = visible["declaration"]
    rely = bool(
        declaration["active"]
        and declaration["operation_family"] == visible["current"]["operation_family"]
    )
    return {
        "rely": rely,
        "decision_state": "RELY" if rely else "DO_NOT_RELY",
        "reason": "active_capability_declaration" if rely else "no_active_declaration",
    }


def latest_probe_strategy(visible: dict[str, Any]) -> dict[str, Any]:
    guarded = _epistemic_guard(visible)
    if guarded:
        return guarded
    probe = visible["latest_probe"]
    current = visible["current"]
    rely = bool(
        probe["status"] == "SUCCESS"
        and visible["decision_step"] - probe["step"] <= 2
        and probe["operation_id"] == current["operation_id"]
        and probe["key_id"] == current["key_id"]
        and probe["environment"] == current["environment"]
        and probe["command_hash"] == current["command_hash"]
        and probe["semantic_hash"] == current["semantic_hash"]
        and probe["latency_ms"] <= current["deadline_ms"]
    )
    return {
        "rely": rely,
        "decision_state": "RELY" if rely else "DO_NOT_RELY",
        "reason": "fresh_exact_probe" if rely else "probe_not_current_or_exact",
    }


def receipt_history_strategy(visible: dict[str, Any]) -> dict[str, Any]:
    guarded = _epistemic_guard(visible)
    if guarded:
        return guarded
    current = visible["current"]
    receipts = visible["receipt_history"][-3:]
    exact = len(receipts) == 3 and all(
        receipt["status"] == "SUCCESS"
        and receipt["operation_id"] == current["operation_id"]
        and receipt["key_id"] == current["key_id"]
        and receipt["environment"] == current["environment"]
        and receipt["command_hash"] == current["command_hash"]
        and receipt["semantic_hash"] == current["semantic_hash"]
        and receipt["recipient_ack"]
        and receipt["external_anchor"]
        and visible["decision_step"] - receipt["step"] <= 5
        for receipt in receipts
    )
    latency_ok = (
        exact
        and max(receipt["latency_ms"] for receipt in receipts)
        <= current["deadline_ms"]
    )
    current_boundaries_ok = (
        current["authority_state"] == "ACTIVE"
        and current["partial_state"] == "NONE"
        and current["anchor_state"] == "VALID"
        and current["idempotency_state"] in {"NEW", "EXACT_REPLAY"}
    )
    rely = bool(exact and latency_ok and current_boundaries_ok)
    return {
        "rely": rely,
        "decision_state": "RELY" if rely else "DO_NOT_RELY",
        "reason": "continuous_exact_receipts" if rely else "history_or_current_boundary_failed",
    }


def sla_recovery_strategy(visible: dict[str, Any]) -> dict[str, Any]:
    guarded = _epistemic_guard(visible)
    if guarded:
        return guarded
    current = visible["current"]
    sla = visible["sla"]
    recovery_ok = (
        sla["health"] == "GREEN"
        or (
            sla["health"] == "RECOVERED"
            and sla["recovery_receipt_valid"]
        )
    )
    rely = bool(
        sla["status"] == "IN_FORCE"
        and bool(sla["recovery_owner"])
        and recovery_ok
        and sla["operation_id"] == current["operation_id"]
        and sla["key_id"] == current["key_id"]
        and sla["environment"] == current["environment"]
        and sla["command_hash"] == current["command_hash"]
        and sla["semantic_hash"] == current["semantic_hash"]
        and sla["max_latency_ms"] <= current["deadline_ms"]
        and current["ack_delay_ms"] <= current["deadline_ms"]
        and current["authority_state"] == "ACTIVE"
        and current["partial_state"] == "NONE"
        and current["anchor_state"] == "VALID"
        and current["idempotency_state"] in {"NEW", "EXACT_REPLAY"}
    )
    return {
        "rely": rely,
        "decision_state": "RELY" if rely else "DO_NOT_RELY",
        "reason": "sla_and_recovery_obligation_current" if rely else "sla_or_current_boundary_failed",
    }


STRATEGIES: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "DECLARATION": declaration_strategy,
    "LATEST_PROBE": latest_probe_strategy,
    "RECEIPT_HISTORY": receipt_history_strategy,
    "SLA_RECOVERY": sla_recovery_strategy,
}


def run_simulation(fixture: dict[str, Any]) -> dict[str, Any]:
    if fixture["shared_task"]["task_id"] != "W6-STERILE-ROUTE-SIMULATION-001":
        raise ValueError("fixture is not bound to the frozen Wave-006 task")
    rows: list[dict[str, Any]] = []
    for scenario in fixture["scenarios"]:
        for snapshot in scenario["snapshots"]:
            visible = visible_snapshot(fixture, snapshot)
            visible_before = copy.deepcopy(visible)
            decisions = {
                strategy_id: strategy(copy.deepcopy(visible))
                for strategy_id, strategy in STRATEGIES.items()
            }
            if visible != visible_before:
                raise RuntimeError("strategy evaluation mutated visible evidence")
            rows.append({
                "scenario_id": scenario["scenario_id"],
                "risk": scenario["risk"],
                "step": snapshot["step"],
                "label": snapshot["label"],
                "event_history": copy.deepcopy(snapshot["event_history"]),
                "visible_sha256_input": visible,
                "truth": copy.deepcopy(snapshot["truth"]),
                "decisions": decisions,
            })
    return {
        "schema_version": "1.0",
        "shared_task": copy.deepcopy(fixture["shared_task"]),
        "operation": copy.deepcopy(fixture["operation"]),
        "strategy_ids": list(STRATEGIES),
        "rows": rows,
    }
