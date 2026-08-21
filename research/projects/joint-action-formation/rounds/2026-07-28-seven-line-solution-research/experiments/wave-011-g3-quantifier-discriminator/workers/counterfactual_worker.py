#!/usr/bin/env python3
"""Replay a pre-frozen trace under predeclared reset/block semantics."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import replay  # noqa: E402


def outcome(result: dict) -> str:
    return "SAT" if result["goal_reached"] else "UNSAT"


def main() -> None:
    job = json.load(sys.stdin)
    oracle = copy.deepcopy(job["private_oracle"])
    action_ids = list(job["frozen_action_ids"])
    operator_ids = set(job["operator_ids"])
    derived_effects = {
        operator_id: oracle.get("derived_effects", {}).get(operator_id, [])
        for operator_id in sorted(operator_ids)
    }
    response = oracle["actual_response"]
    extra_actions = job.get("extra_actions", [])
    actions = {
        action["id"]: action
        for action in oracle["old_actions"]
        + oracle.get("extension_actions", [])
        + list(extra_actions)
    }
    expected_derived_effects: dict[str, list[str]] = {}
    initial_facts = set(oracle["initial_facts"])
    for operator_id in sorted(operator_ids):
        if operator_id not in action_ids or operator_id not in actions:
            expected_derived_effects[operator_id] = []
            continue
        start = action_ids.index(operator_id)
        suffix_adds: set[str] = set()
        for action_id in action_ids[start:]:
            action = actions.get(action_id)
            if action is not None:
                suffix_adds.update(action.get("adds", []))
        expected_derived_effects[operator_id] = sorted(suffix_adds - initial_facts)
    derived_effect_graph_valid = all(
        sorted(derived_effects[operator_id])
        == expected_derived_effects[operator_id]
        for operator_id in sorted(operator_ids)
    )

    remove = replay(
        oracle,
        action_ids,
        response=response,
        extra_actions=extra_actions,
        blocked=operator_ids,
    )
    reverse_trace = [action for action in action_ids if action not in operator_ids]
    reverse = replay(
        oracle,
        reverse_trace,
        response=response,
        extra_actions=extra_actions,
    )
    block = replay(
        oracle,
        action_ids,
        response=response,
        extra_actions=extra_actions,
        blocked=operator_ids,
    )
    json.dump(
        {
            "worker": "frozen-trace-counterfactual-v1",
            "reset_semantics": "RESET_TO_PRIVATE_S0_AND_DISCARD_DERIVED_EFFECTS",
            "derived_effects_consumed": derived_effects,
            "expected_derived_effects_from_frozen_trace": expected_derived_effects,
            "derived_effect_graph_valid": derived_effect_graph_valid,
            "derived_effect_reset_verified": all(
                not (set(effects) & set(remove["final_facts"]))
                for effects in derived_effects.values()
            )
            and derived_effect_graph_valid,
            "operator_ids": sorted(operator_ids),
            "remove": {"result": outcome(remove), "replay": remove},
            "reverse": {"result": outcome(reverse), "replay": reverse},
            "block": {"result": outcome(block), "replay": block},
        },
        sys.stdout,
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
