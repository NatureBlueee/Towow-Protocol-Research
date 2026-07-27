#!/usr/bin/env python3
"""Query the A2A design capability audit ledgers."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEDGERS = ROOT / "research/projects/a2a-reconstruction/04_audit/ledgers"
SOURCES = ROOT / "research/projects/a2a-reconstruction/04_audit/source_registry.csv"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def contains_id(value: str, target: str) -> bool:
    return target in {item.strip() for item in value.split("|") if item.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--capability")
    group.add_argument("--source")
    group.add_argument("--component")
    group.add_argument("--claim")
    group.add_argument("--text")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    datasets = {
        "capabilities": rows(LEDGERS / "capability_preservation_matrix.csv"),
        "claims": rows(LEDGERS / "claim_ledger.csv"),
        "evidence": rows(LEDGERS / "evidence_ledger.csv"),
        "decisions": rows(LEDGERS / "decision_timeline.csv"),
        "components": rows(LEDGERS / "component_capability_index.csv"),
        "facts": rows(LEDGERS / "formal_fact_ownership.csv"),
        "sources": rows(SOURCES),
    }
    result: dict[str, list[dict[str, str]]] = {}

    if args.capability:
        target = args.capability
        for name, data in datasets.items():
            selected = [
                row for row in data
                if row.get("capability_id") == target
                or contains_id(row.get("capability_ids", ""), target)
                or contains_id(row.get("affected_capabilities", ""), target)
            ]
            if selected:
                result[name] = selected
    elif args.source:
        target = args.source
        for name, data in datasets.items():
            selected = [
                row for row in data
                if row.get("source_id") == target
                or contains_id(row.get("source_ids", ""), target)
                or contains_id(row.get("primary_sources", ""), target)
            ]
            if selected:
                result[name] = selected
    elif args.component:
        result["components"] = [
            row for row in datasets["components"]
            if row["component_id"] == args.component
            or args.component.lower() in row["component_name"].lower()
        ]
    elif args.claim:
        target = args.claim
        result["claims"] = [row for row in datasets["claims"] if row["claim_id"] == target]
        result["evidence"] = [
            row for row in datasets["evidence"] if contains_id(row["claim_ids"], target)
        ]
    else:
        term = args.text.lower()
        for name, data in datasets.items():
            selected = [
                row for row in data
                if term in " ".join(row.values()).lower()
            ]
            if selected:
                result[name] = selected

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    for name, data in result.items():
        print(f"## {name} ({len(data)})")
        for row in data:
            primary = (
                row.get("capability_id")
                or row.get("claim_id")
                or row.get("evidence_id")
                or row.get("decision_id")
                or row.get("component_id")
                or row.get("fact_key")
                or row.get("source_id")
            )
            print(f"- {primary}: " + " | ".join(f"{k}={v}" for k, v in row.items() if v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

