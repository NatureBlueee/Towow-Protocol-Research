#!/usr/bin/env python3
"""Recompute the return packet's core claim metrics from portable CSV evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", nargs="?", default=".")
    args = parser.parse_args()
    root = Path(args.packet).resolve()

    matrix_path = (
        root
        / "experiments"
        / "r5-2-run-001-effect-reality"
        / "outputs"
        / "scenario_matrix.csv"
    )
    scorecard_path = (
        root
        / "experiments"
        / "r5-2-run-002-capability-holdout"
        / "outputs"
        / "scorecard.csv"
    )
    matrix = read_csv(matrix_path)
    scorecard = read_csv(scorecard_path)

    b0_wrong = sum(row["classification"] != "B0_correct" for row in matrix)
    b1_t1_mismatch = sum(row["B1_harness"] != row["T1_explicit"] for row in matrix)
    families = sorted({row["family"] for row in matrix})

    executable = [
        row for row in scorecard if row["strict_score"] in {"correct", "incorrect"}
    ]
    six_axis_correct = sum(row["strict_score"] == "correct" for row in executable)
    static_correct = sum(
        row["static_installed_score"] == "correct" for row in executable
    )
    withdrawn = [row for row in scorecard if row["strict_score"] == "excluded"]
    non_executable = [
        row for row in scorecard if row["strict_score"] == "correct_non_executable"
    ]

    run_paths = [
        root / "experiments" / "r5-2-run-001-effect-reality" / "run.json",
        root / "experiments" / "r5-2-run-002-capability-holdout" / "run.json",
    ]
    evidence_errors: list[str] = []
    for run_path in run_paths:
        run = json.loads(run_path.read_text(encoding="utf-8"))
        if run.get("status") != "completed":
            evidence_errors.append(f"{run_path}: status is not completed")
        for relative in run.get("evidence_paths", []):
            candidate = run_path.parent / relative
            if not candidate.exists():
                evidence_errors.append(f"{run_path}: missing evidence {relative}")

    checks = {
        "scenario_count_is_17": len(matrix) == 17,
        "family_count_is_5": len(families) == 5,
        "B0_wrong_count_is_10": b0_wrong == 10,
        "B1_matches_T1_in_all_scenarios": b1_t1_mismatch == 0,
        "capability_executable_count_is_6": len(executable) == 6,
        "six_axis_first_attempt_is_4_of_6": (
            six_axis_correct == 4 and len(executable) == 6
        ),
        "static_first_attempt_is_3_of_6": (
            static_correct == 3 and len(executable) == 6
        ),
        "one_case_withdrawn_from_scoring": len(withdrawn) == 1,
        "one_authorization_negative_non_executable": len(non_executable) == 1,
        "all_run_evidence_paths_exist": not evidence_errors,
        "excluded_trace_not_packaged": not (
            root
            / "experiments"
            / "r5-2-run-002-capability-holdout"
            / "traces"
            / "cap-tool-07-reference-monitor-availability.json"
        ).exists(),
    }
    passed = all(checks.values())
    result = {
        "status": "passed" if passed else "failed",
        "scenario_matrix": {
            "rows": len(matrix),
            "families": families,
            "B0_wrong": b0_wrong,
            "B1_T1_mismatch": b1_t1_mismatch,
        },
        "capability_scorecard": {
            "executable": len(executable),
            "six_axis_correct": six_axis_correct,
            "static_installed_correct": static_correct,
            "withdrawn": len(withdrawn),
            "correct_non_executable": len(non_executable),
        },
        "checks": checks,
        "evidence_errors": evidence_errors,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
