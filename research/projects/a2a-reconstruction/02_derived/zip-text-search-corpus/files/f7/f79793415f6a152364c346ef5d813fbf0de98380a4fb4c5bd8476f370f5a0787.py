#!/usr/bin/env python3
"""Recompute provider-reported cost aggregates from a relocated return packet."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def _condition(path: Path) -> str:
    value = path.as_posix()
    if "/conformance/" in value:
        return "boundary_conformance"
    if "/transcripts/a2a/" in value:
        return "direct_a2a"
    if "/traces/static/" in value:
        return "static"
    if "run-002-central-replication" in value:
        return "least_privilege_central_replication"
    if "/traces/central/" in value:
        return "least_privilege_central_run001"
    return "unclassified"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet_root", type=Path)
    args = parser.parse_args()
    aggregate: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"calls": 0, "errors": 0, "wall_clock_seconds": 0.0, "total_cost_usd": 0.0}
    )
    for request_path in sorted(args.packet_root.glob("experiments/**/request.json")):
        parsed_path = request_path.with_name("parsed.json")
        if not parsed_path.exists():
            continue
        request = json.loads(request_path.read_text(encoding="utf-8"))
        result = json.loads(parsed_path.read_text(encoding="utf-8"))
        bucket = aggregate[_condition(request_path)]
        bucket["calls"] += 1
        bucket["errors"] += int(bool(result.get("is_error")) or request.get("exit_code") != 0)
        bucket["wall_clock_seconds"] += float(request.get("wall_clock_seconds", 0))
        bucket["total_cost_usd"] += float(result.get("total_cost_usd", 0) or 0)
    print(json.dumps(dict(sorted(aggregate.items())), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
