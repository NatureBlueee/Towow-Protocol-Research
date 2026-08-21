#!/usr/bin/env python3
"""Run the CE-001 G7 Agent B component and preserve raw traces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from g7evo import EvolutionModule
from g7evo.audit import audit_line_local_results


ROOT = Path(__file__).resolve().parent
DEFAULT_FIXTURE = ROOT / "fixtures" / "ce001-g7.json"
DEFAULT_OUTPUT = ROOT / "raw" / "run-traces.json"
DEFAULT_SUMMARY = ROOT / "results.json"


def run(fixture_path: Path = DEFAULT_FIXTURE) -> dict:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return EvolutionModule(fixture).run_all()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()
    results = run(args.fixture)
    violations = audit_line_local_results(results)
    results["audit"] = {
        "status": "PASS" if not violations else "FAIL",
        "violation_count": len(violations),
        "violations": violations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    evidence = results["evidence"]
    summary = {
        "schema": "g7.evolution.line-local-summary.v2",
        "implementation_identity": results["implementation_identity"],
        "evidence_level": results["evidence_level"],
        "audit": results["audit"],
        "run_root": evidence["run_root"],
        "owner_processes": {
            owner: {
                "process_id": item["process_id"],
                "state_path": item["state_path"],
                "state_bytes_hash": item["state_bytes_hash"],
                "state_source_id": item["state_source_id"],
                "act_source_id": item["act_source_id"],
            }
            for owner, item in evidence["owner_sources"].items()
        },
        "migration": evidence["migration"],
        "owner_binding_attacks": evidence["owner_binding_attacks"],
        "receipt_consumption_attacks": evidence["receipt_consumption_attacks"],
        "byte_provenance": evidence["byte_provenance"],
        "evidence_boundaries": evidence["evidence_boundaries"],
        "integration_envelope": results["integration_envelope"],
    }
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "implementation_identity": results["implementation_identity"],
                "audit_status": results["audit"]["status"],
                "owner_process_count": len(evidence["owner_sources"]),
                "old_epoch_result": evidence["migration"]["old_runtime_restart"][
                    "fence_result"
                ],
                "output": str(args.output),
                "summary_output": str(args.summary_output),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
