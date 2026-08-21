#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _engine import replay  # noqa: E402


def main() -> None:
    job = json.load(sys.stdin)
    oracle = job["private_oracle"]
    action_ids = job["frozen_action_ids"]
    branch_results = []
    for response in oracle["response_branches"]:
        result = replay(
            oracle,
            action_ids,
            response=response,
            extra_actions=job.get("extra_actions", []),
        )
        branch_results.append({"response": response, **result})
    effect_robust = bool(branch_results) and all(item["goal_reached"] for item in branch_results)
    safe_robust = bool(branch_results) and all(item["terminal_safe"] for item in branch_results)
    terminal_robust = bool(branch_results) and all(
        item["goal_reached"] or item["terminal_safe"]
        for item in branch_results
    )
    json.dump(
        {
            "worker": "robust-tree-checker-v1",
            "branches": branch_results,
            "effect_robust": effect_robust,
            "safe_robust": safe_robust,
            "terminal_robust": terminal_robust,
        },
        sys.stdout,
        sort_keys=True,
    )


if __name__ == "__main__":
    main()
