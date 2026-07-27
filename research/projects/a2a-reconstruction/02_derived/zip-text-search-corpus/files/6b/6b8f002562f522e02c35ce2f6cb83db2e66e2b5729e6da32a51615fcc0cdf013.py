#!/usr/bin/env python3
"""Recompute per-condition model-call cost from captured request/result pairs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _condition(path: Path) -> str:
    text = path.as_posix()
    if "/conformance/" in text:
        return "boundary_conformance"
    if "/transcripts/a2a/" in text:
        return "direct_a2a"
    if "/traces/static/" in text:
        return "static"
    if "run-002-central-replication" in text:
        return "least_privilege_central_replication"
    if "/traces/central/" in text:
        return "least_privilege_central_run001"
    return "unclassified"


def _tokens(model_usage: object) -> dict[str, int]:
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "web_search_requests": 0,
    }
    if not isinstance(model_usage, dict):
        return totals
    mapping = {
        "inputTokens": "input_tokens",
        "outputTokens": "output_tokens",
        "cacheReadInputTokens": "cache_read_input_tokens",
        "cacheCreationInputTokens": "cache_creation_input_tokens",
        "webSearchRequests": "web_search_requests",
    }
    for usage in model_usage.values():
        if not isinstance(usage, dict):
            continue
        for source, target in mapping.items():
            value = usage.get(source, 0)
            if isinstance(value, int):
                totals[target] += value
    return totals


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("research_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    calls: list[dict[str, Any]] = []
    for request_path in sorted(args.research_root.glob("runs/**/request.json")):
        result_path = request_path.with_name("parsed.json")
        if not result_path.exists():
            continue
        request = json.loads(request_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        call = {
            "condition": _condition(request_path),
            "request_path": request_path.relative_to(args.research_root).as_posix(),
            "result_path": result_path.relative_to(args.research_root).as_posix(),
            "role": request.get("role"),
            "exit_code": request.get("exit_code"),
            "wall_clock_seconds": request.get("wall_clock_seconds", 0),
            "is_error": result.get("is_error"),
            "total_cost_usd": result.get("total_cost_usd", 0) or 0,
            **_tokens(result.get("modelUsage")),
        }
        calls.append(call)

    aggregate: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {
            "calls": 0,
            "errors": 0,
            "wall_clock_seconds": 0.0,
            "total_cost_usd": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "web_search_requests": 0,
        }
    )
    for call in calls:
        bucket = aggregate[call["condition"]]
        bucket["calls"] += 1
        bucket["errors"] += int(bool(call["is_error"]) or call["exit_code"] != 0)
        for key in (
            "wall_clock_seconds",
            "total_cost_usd",
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "web_search_requests",
        ):
            bucket[key] += call[key]

    document = {
        "schema_version": "towow-r5-model-costs-v1",
        "source": "captured request.json and parsed.json pairs",
        "aggregate_by_condition": dict(sorted(aggregate.items())),
        "calls": calls,
        "notes": [
            "Provider-reported token accounting includes internal Claude CLI model routing.",
            "Wall-clock sums are serial call durations, not critical-path elapsed time.",
            "Boundary conformance includes failed sandbox-network attempts and is reported separately.",
            "No human-attention currency conversion is inferred."
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
