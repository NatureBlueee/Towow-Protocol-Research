#!/usr/bin/env python3
"""CLI for the research-b race/fence simulator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from typing import Any

from authority_sim import (
    FENCE_MODES,
    OWNER_NAMES,
    STRATEGIES,
    RacePlan,
    SimulationConfig,
    SimulationHarness,
    run_fence_probe,
)


def write_report(report: Any, output: Path | None) -> None:
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def race_boundaries() -> list[str]:
    boundaries = []
    for kind in ("read", "reread", "sign"):
        boundaries.extend(f"{kind}:{owner}" for owner in OWNER_NAMES)
    boundaries.extend(("reserve:resource_owner", "execute:target"))
    return boundaries


def run_matrix(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(prefix="g5-race-matrix-") as temp:
        root = Path(temp)
        for strategy in STRATEGIES:
            topology = "unified" if strategy == "unified_center" else "independent"
            for index, boundary in enumerate(race_boundaries()):
                runtime = root / f"{strategy}-{index}"
                report = SimulationHarness(
                    SimulationConfig(
                        strategy=strategy,
                        race=RacePlan(
                            boundary=boundary,
                            owner=args.race_owner,
                            action=args.race_action,
                        ),
                        fence_mode=args.fence_mode,
                        authority_topology=topology,
                    ),
                    runtime_dir=runtime,
                ).run()
                rows.append(
                    {
                        "strategy": strategy,
                        "boundary": boundary,
                        "method_status": report["method_status"],
                        "atomicity_claim": report["atomicity_claim"],
                        "metrics": report["metrics"],
                    }
                )
    return {
        "schema_version": "research-b-race-matrix-v1",
        "evidence_level": "LOCAL_SYNTHETIC",
        "race_action": args.race_action,
        "race_owner": args.race_owner,
        "fence_mode": args.fence_mode,
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", choices=STRATEGIES)
    parser.add_argument("--race-boundary")
    parser.add_argument("--race-owner", choices=OWNER_NAMES, default="budget_owner")
    parser.add_argument(
        "--race-action",
        choices=("revoke", "reject", "outage", "fork"),
        default="revoke",
    )
    parser.add_argument("--fence-mode", choices=FENCE_MODES, default="enforce")
    parser.add_argument(
        "--authority-topology",
        choices=("independent", "unified"),
        default="independent",
    )
    parser.add_argument("--crash-after-prepare", action="store_true")
    parser.add_argument("--no-compensation", action="store_true")
    parser.add_argument("--fence-probe", choices=FENCE_MODES)
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.fence_probe:
        write_report(run_fence_probe(args.fence_probe), args.output)
        return 0
    if args.matrix:
        write_report(run_matrix(args), args.output)
        return 0
    if not args.strategy:
        raise SystemExit("--strategy is required unless --matrix/--fence-probe is used")
    race = None
    if args.race_boundary:
        race = RacePlan(args.race_boundary, args.race_owner, args.race_action)
    report = SimulationHarness(
        SimulationConfig(
            strategy=args.strategy,
            race=race,
            fence_mode=args.fence_mode,
            authority_topology=args.authority_topology,
            crash_after_prepare=args.crash_after_prepare,
            compensation_supported=not args.no_compensation,
        )
    ).run()
    write_report(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
