#!/usr/bin/env python3
"""Self-contained replay of the two disputed legacy identity policies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _fold(events: list[dict[str, object]], wildcard: bool) -> dict[tuple[object, object], bool]:
    state: dict[tuple[object, object], bool] = {}
    for event in sorted(events, key=lambda item: int(item["sequence"])):
        key = (event.get("source"), event.get("locator"))
        if event["type"] == "add":
            state[key] = True
            continue
        if event["type"] != "remove":
            raise ValueError(f"unknown event type: {event['type']}")
        if wildcard and event.get("source") is None:
            for existing in list(state):
                if existing[1] == event.get("locator"):
                    state[existing] = False
        else:
            state[key] = False
    return state


def _named(state: dict[tuple[object, object], bool], locator: str) -> dict[str, bool]:
    return {
        "legacy_active": state.get((None, locator), False),
        "consumer_a_active": state.get(("consumer-a@v1", locator), False),
        "consumer_b_active": state.get(("consumer-b@v1", locator), False),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    locator = fixture["locator"]
    events = [
        {**event, "locator": locator}
        for event in fixture["events"]
    ]
    observed = {
        "null_source_class": _named(_fold(events, wildcard=False), locator),
        "legacy_wildcard": _named(_fold(events, wildcard=True), locator),
    }
    expected = fixture["expected"]
    output = {
        "fixture": args.fixture.name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
        "conclusion": (
            "The policies are behaviorally incompatible in a mixed stream."
            if observed == expected
            else "Replay did not reproduce the frozen counterfactual."
        ),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
