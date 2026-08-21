#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import search  # noqa: E402


def main() -> None:
    job = json.load(sys.stdin)
    inventory = job["inventory"]
    oracle = job["private_oracle"]
    completeness_keys = [
        "action_inventory",
        "response_family",
        "observation_kernel",
        "transition_semantics",
    ]
    if any(inventory[key] != "COMPLETE" for key in completeness_keys):
        output = {
            "worker": "measurable-oracle-v1",
            "result": "UNKNOWN",
            "trace": [],
            "reason": "INCOMPLETE_INVENTORY",
        }
    else:
        actions = [
            action
            for action in oracle["old_actions"] + oracle.get("extension_actions", [])
            if action.get("measurable", False)
        ]
        branches = [
            {
                "response": response,
                **search(
                    oracle,
                    actions,
                    horizon=inventory["horizon"],
                    response=response,
                ),
            }
            for response in oracle["response_branches"]
        ]
        output = {
            "worker": "measurable-oracle-v1",
            "result": "SAT" if any(branch["result"] == "SAT" for branch in branches) else "UNSAT",
            "branches": branches,
            "trace": next(
                (branch["trace"] for branch in branches if branch["result"] == "SAT"),
                [],
            ),
            "quantifier": "EXISTS_OBSERVATION_MEASURABLE_POLICY_AND_LAWFUL_RESPONSE_BRANCH",
            "reason": "FROZEN_OBSERVATION_POLICY_SEARCH",
        }
    json.dump(output, sys.stdout, sort_keys=True)


if __name__ == "__main__":
    main()
