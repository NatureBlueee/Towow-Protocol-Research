#!/usr/bin/env python3
"""Independent root mutations against Wave 007-A."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path


ROUND = Path(__file__).resolve().parents[2]
EXPERIMENT = ROUND / "experiments" / "wave-007-a-opaque-authority-harness"
sys.path.insert(0, str(EXPERIMENT))

from runner import load_fixtures, run_inputs  # noqa: E402


def main() -> int:
    public, hidden = load_fixtures()

    world = copy.deepcopy(hidden["worlds"]["X7-C73"])
    world["preload"] = "BASELINE"
    world["idempotency_conflict"] = True
    world["expected_terminal"] = "REFUSE"
    changed = copy.deepcopy(public["requests"]["X7-C73"])
    changed["command"] = {
        "capacity_units": 9,
        "window": "E0-E8",
    }
    result = run_inputs(changed, world)
    operation_log = result["operation_log"]
    partial_then_changed = {
        "actual_terminal": result["evaluation"]["actual_terminal"],
        "terminal_match": result["evaluation"]["terminal_match"],
        "controller_refused_at_attempt": any(
            row["operation"] == "REQUEST_EFFECT_ATTEMPT"
            and row["outcome"] == "REFUSE"
            for row in operation_log
        ),
        "new_domain_postcondition_called": any(
            row["operation"] == "REQUEST_DOMAIN_POSTCONDITION"
            for row in operation_log
        ),
        "operations": [row["operation"] for row in operation_log],
    }

    hidden_path = EXPERIMENT / "fixtures" / "hidden-worlds.json"
    peer_code = (
        "from pathlib import Path; "
        f"p=Path({str(hidden_path)!r}); "
        "s=p.read_text(); "
        "print({'readable': True, "
        "'contains_expected_terminal': 'expected_terminal' in s, "
        "'bytes': len(s)})"
    )
    peer_output = subprocess.check_output(
        [sys.executable, "-c", peer_code],
        text=True,
    ).strip()

    print(json.dumps(
        {
            "partial_then_changed_same_idempotency": partial_then_changed,
            "candidate_os_peer_hidden_fixture": peer_output,
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

