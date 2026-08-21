#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import search  # noqa: E402


def main() -> None:
    job = json.load(sys.stdin)
    oracle = job["private_oracle"]
    inventory = job["inventory"]
    horizon = job["horizon"]
    keys = [
        "action_inventory",
        "response_family",
        "observation_kernel",
        "transition_semantics",
    ]
    if any(inventory[key] != "COMPLETE" for key in keys):
        old = {"result": "UNKNOWN", "branches": [], "reason": "INCOMPLETE_INVENTORY"}
        extended = {"result": "UNKNOWN", "branches": [], "reason": "INCOMPLETE_INVENTORY"}
    else:
        old_branches = [
            {
                "response": response,
                **search(oracle, oracle["old_actions"], horizon=horizon, response=response),
            }
            for response in oracle["response_branches"]
        ]
        extended_branches = [
            {
                "response": response,
                **search(
                    oracle,
                    oracle["old_actions"] + oracle.get("extension_actions", []),
                    horizon=horizon,
                    response=response,
                ),
            }
            for response in oracle["response_branches"]
        ]
        old = {
            "result": "SAT" if any(branch["result"] == "SAT" for branch in old_branches) else "UNSAT",
            "branches": old_branches,
            "quantifier": "EXISTS_LAWFUL_RESPONSE_BRANCH",
        }
        extended = {
            "result": "SAT" if any(branch["result"] == "SAT" for branch in extended_branches) else "UNSAT",
            "branches": extended_branches,
            "quantifier": "EXISTS_LAWFUL_RESPONSE_BRANCH",
        }
    json.dump(
        {
            "worker": "closure-oracle-v1",
            "old_closure": old,
            "extended_closure": extended,
        },
        sys.stdout,
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
