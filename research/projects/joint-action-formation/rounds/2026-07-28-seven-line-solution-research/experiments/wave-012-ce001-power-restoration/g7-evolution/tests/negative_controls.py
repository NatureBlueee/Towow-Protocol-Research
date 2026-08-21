#!/usr/bin/env python3
"""Expected-red mutation: old runtime is allowed to commit after takeover."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g7evo.audit import audit_results  # noqa: E402
from g7evo.runtime import EvolutionModule  # noqa: E402


def main() -> int:
    fixture = json.loads(
        (ROOT / "fixtures" / "ce001-g7.json").read_text(encoding="utf-8")
    )
    results = EvolutionModule(fixture).run_regressions()
    results["cases"]["E6"]["old_runtime_restart"]["outcome"] = "COMMITTED"
    results["cases"]["E6"]["old_runtime_restart"]["committed"] = True
    violations = audit_results(results)
    print(
        json.dumps(
            {
                "negative_control": "OLD_RUNTIME_RESTART_COMMITS",
                "status": "RED_DETECTED" if violations else "FALSE_GREEN",
                "violations": violations,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
