#!/usr/bin/env python3
"""Blind policy worker.

This process receives one public packet and an arm declaration.  It has no path
or import that reaches ``private/`` and emits only a proposed transcript.
"""

from __future__ import annotations

import json
import sys
from typing import Any


ARMS = {
    "B-CENTER-EQUAL-ENVELOPE",
    "B-CENTER-LEGAL-CONTROL",
    "B-MATURE-PLANNER-WORKFLOW",
    "B-HUMAN-RULE",
    "C-FORMATION",
}


def choose(packet: dict[str, Any]) -> list[str]:
    action_ids = {action["id"] for action in packet["available_actions"]}
    if packet["task_change_proposal"] is not None:
        return ["request_owner_change"]
    if "safe_exit" in action_ids:
        return ["safe_exit"]
    if packet["operator_proposal"] is not None:
        execute = next(
            action["id"]
            for action in packet["available_actions"]
            if action["kind"] == "EXECUTE"
        )
        return [packet["operator_proposal"]["id"], execute]
    if "execute_direct" in action_ids:
        return ["execute_direct"]
    if "request_token" in action_ids:
        if "stale_cache_says_ready" in packet["s0_observations"]:
            return ["execute_with_token"]
        return ["request_token", "holder_sign", "execute_with_token"]
    return []


def deterministic_center_rule(packet: dict[str, Any]) -> list[str]:
    return choose(packet)


def bounded_workflow_rule(packet: dict[str, Any]) -> list[str]:
    return choose(packet)


def bounded_human_rule(packet: dict[str, Any]) -> list[str]:
    # Executable, bounded institutional rule; it does not represent a live person.
    return choose(packet)


def candidate_rule(packet: dict[str, Any]) -> list[str]:
    return choose(packet)


IMPLEMENTATIONS = {
    "deterministic_center_rule": deterministic_center_rule,
    "bounded_workflow_rule": bounded_workflow_rule,
    "bounded_human_rule": bounded_human_rule,
    "candidate_rule": candidate_rule,
}


def main() -> None:
    job = json.load(sys.stdin)
    packet = job["public_world"]
    arm_id = job["arm_id"]
    envelope = job["arm_envelope"]
    if arm_id not in ARMS:
        raise SystemExit(f"unknown arm: {arm_id}")
    if envelope.get("may_impersonate_other_principals") is not False:
        raise SystemExit("baseline envelope must forbid principal impersonation")
    implementation = envelope["implementation"]
    action_ids = IMPLEMENTATIONS[implementation](packet)
    action_endpoints = {
        action["id"]: action["authority_endpoint"]
        for action in packet["available_actions"]
    }
    if packet["operator_proposal"] is not None:
        action_endpoints[packet["operator_proposal"]["id"]] = packet[
            "operator_proposal"
        ]["authority_endpoint"]
    unknown_actions = [action_id for action_id in action_ids if action_id not in action_endpoints]
    if unknown_actions:
        raise SystemExit(f"policy selected actions outside public envelope: {unknown_actions}")
    claimed_operator_ids: list[str] = []
    if packet["operator_proposal"] is not None:
        proposal_id = packet["operator_proposal"]["id"]
        if proposal_id in action_ids:
            claimed_operator_ids.append(proposal_id)
    if "holder_sign" in action_ids:
        claimed_operator_ids.append("holder_sign")
    task_change_claim = None
    if packet["task_change_proposal"] is not None:
        task_change_claim = {
            "selected_action": next(
                (
                    action_id
                    for action_id in action_ids
                    if action_id in {"request_owner_change", "controller_rewrite"}
                ),
                None,
            ),
            "changes": packet["task_change_proposal"]["changes"],
        }
    result = {
        "worker": "blind-actual-policy-v1",
        "world_id": packet["world_id"],
        "arm_id": arm_id,
        "environment_variant": envelope["environment_variant"],
        "baseline_implementation": envelope["implementation"],
        "authority_mode": envelope["authority_mode"],
        "comparison_scope": envelope["comparison_scope"],
        "authority_binding": {
            "grants": envelope["grants"],
            "selected_action_endpoints": [
                {"action_id": action_id, "authority_endpoint": action_endpoints[action_id]}
                for action_id in action_ids
            ],
            "principal_impersonation_used": False,
        },
        "lawful_inputs_used": {
            "s0_observations": packet["s0_observations"],
            "available_action_ids": [action["id"] for action in packet["available_actions"]],
            "operator_proposal_id": (
                packet["operator_proposal"]["id"]
                if packet["operator_proposal"] is not None
                else None
            ),
        },
        "action_ids": action_ids,
        "formation_witness_proposal": {
            "source": "PUBLIC_PACKET_AND_SELECTED_ACTIONS_ONLY",
            "claimed_operator_ids": claimed_operator_ids,
            "task_change_claim": task_change_claim,
            "claims_oracle_verdict": False,
        },
    }
    json.dump(result, sys.stdout, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()
