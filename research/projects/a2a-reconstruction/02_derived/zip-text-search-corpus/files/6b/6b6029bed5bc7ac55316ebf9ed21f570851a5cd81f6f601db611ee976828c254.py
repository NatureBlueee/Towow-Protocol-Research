#!/usr/bin/env python3
"""Compare shallow success signals with effect and acceptance contracts."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SUCCESS_TEXT = re.compile(r"\b(success|succeeded|switched|complete|completed|ok)\b", re.I)


def target_exists(case_dir: Path) -> bool:
    return (case_dir / "target").is_file()


def targets_a_and_b_exist(case_dir: Path) -> bool:
    return (case_dir / "target_a").is_file() and (case_dir / "target_b").is_file()


def no_target(case_dir: Path) -> bool:
    return not any(case_dir.iterdir())


CASES: list[dict[str, Any]] = [
    {
        "case_id": "truthful_success",
        "command": 'print -r -- "operation complete"\n: > "$R5_CASE_DIR/target"',
        "postcondition": target_exists,
        "ground_truth_acceptance": True,
    },
    {
        "case_id": "success_text_failure",
        "command": 'print -r -- "Switched to a new branch"\nfalse',
        "postcondition": no_target,
        "invert_postcondition_for_effect": True,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "masked_first_failure",
        "command": 'print -u2 -- "permission denied"\nfalse\nprint -r -- "follow-up read succeeded"',
        "postcondition": no_target,
        "invert_postcondition_for_effect": True,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "exit_zero_no_effect",
        "command": 'print -r -- "OK"',
        "postcondition": no_target,
        "invert_postcondition_for_effect": True,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "effect_then_failure",
        "command": ': > "$R5_CASE_DIR/target"\nprint -u2 -- "later validation failed"\nfalse',
        "postcondition": target_exists,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "effect_then_rollback",
        "command": ': > "$R5_CASE_DIR/target"\n/bin/rm "$R5_CASE_DIR/target"\nprint -r -- "operation complete"',
        "postcondition": no_target,
        "invert_postcondition_for_effect": True,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "partial_bundle_masked",
        "command": ': > "$R5_CASE_DIR/target_a"\nfalse\ntrue',
        "postcondition": targets_a_and_b_exist,
        "ground_truth_acceptance": False,
    },
    {
        "case_id": "explicit_refusal",
        "command": 'print -r -- "REFUSED: no authorized operator"\nexit 3',
        "postcondition": no_target,
        "invert_postcondition_for_effect": True,
        "ground_truth_acceptance": False,
        "ground_truth_outcome": "refused",
    },
]


def bool_metrics(rows: list[dict[str, Any]], predictor: str, truth: str) -> dict[str, Any]:
    tp = sum(bool(row[predictor]) and bool(row[truth]) for row in rows)
    tn = sum(not bool(row[predictor]) and not bool(row[truth]) for row in rows)
    fp = sum(bool(row[predictor]) and not bool(row[truth]) for row in rows)
    fn = sum(not bool(row[predictor]) and bool(row[truth]) for row in rows)
    total = len(rows)
    return {
        "accuracy": (tp + tn) / total if total else 0.0,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "n": total,
    }


def project_records(row: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    minimal = {
        "attempt_id": row["case_id"],
        "actor": row["actor"],
        "atomic_action": row["command"],
        "executor_exit_code": row["outer_exit_code"],
        "postcondition": row["postcondition_passed"],
        "effect_observed": row["ground_truth_effect"],
        "acceptance": row["minimal_contract_acceptance"],
        "outcome": row["ground_truth_outcome"],
    }
    full = {
        "CoordinationCase": {
            "id": f"case:{row['case_id']}",
            "status": row["ground_truth_outcome"],
        },
        "ObjectiveVersion": {
            "id": f"objective:{row['case_id']}:v1",
            "content_hash": row["command_hash"],
            "parent": None,
        },
        "Claim": {
            "id": f"claim:{row['case_id']}:effect",
            "scope": "local temporary case directory",
            "status": "observed" if row["ground_truth_effect"] else "refuted",
        },
        "Evidence": {
            "stdout": row["stdout"],
            "stderr": row["stderr"],
            "executor_exit_code": row["outer_exit_code"],
        },
        "RecognitionAction": {
            "status": "not_required_for_local_test",
            "content_hash": row["command_hash"],
        },
        "AuthorityGrant": {
            "scope": "local temporary case directory",
            "granted": True,
        },
        "Commitment": {
            "status": "local_test_only",
            "resource_reservation": "temporary_directory",
        },
        "Effect": {
            "attempted": True,
            "observed": row["ground_truth_effect"],
            "partial_effect_paths": row["partial_effect_paths"],
        },
        "Verification": {
            "postcondition_passed": row["postcondition_passed"],
        },
        "Acceptance": {
            "accepted": row["minimal_contract_acceptance"],
        },
        "Settlement": {
            "status": "not_applicable",
        },
    }
    return minimal, full


def add_predictions(row: dict[str, Any]) -> None:
    visible_text = f"{row['stdout']}\n{row['stderr']}"
    row["stdout_language_acceptance"] = bool(SUCCESS_TEXT.search(visible_text))
    row["outer_exit_acceptance"] = row["outer_exit_code"] == 0
    row["postcondition_only_acceptance"] = bool(row["postcondition_passed"])
    row["minimal_contract_acceptance"] = (
        row["outer_exit_code"] == 0 and bool(row["postcondition_passed"])
    )
    row["eager_full_projection_acceptance"] = row["minimal_contract_acceptance"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--actual-events", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    logs = output / "logs"
    outputs = output / "outputs"
    logs.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="towow-r5-effect-") as temp_root:
        root = Path(temp_root)
        for spec in CASES:
            case_dir = root / spec["case_id"]
            case_dir.mkdir()
            before = sorted(path.name for path in case_dir.iterdir())
            case_started = time.monotonic()
            completed = subprocess.run(
                ["/bin/zsh", "-f", "-c", spec["command"]],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "R5_CASE_DIR": str(case_dir)},
            )
            duration_ms = round((time.monotonic() - case_started) * 1000, 3)
            after = sorted(path.name for path in case_dir.iterdir())
            raw_postcondition = bool(spec["postcondition"](case_dir))
            effect_observed = (
                not raw_postcondition
                if spec.get("invert_postcondition_for_effect")
                else raw_postcondition
            )
            import hashlib

            row = {
                "case_id": spec["case_id"],
                "source": "executed_holdout",
                "actor": "local-zsh-executor",
                "command": spec["command"],
                "command_hash": hashlib.sha256(spec["command"].encode()).hexdigest(),
                "outer_exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "state_before": before,
                "state_after": after,
                "postcondition_passed": effect_observed,
                "ground_truth_effect": effect_observed,
                "ground_truth_acceptance": spec["ground_truth_acceptance"],
                "ground_truth_outcome": spec.get(
                    "ground_truth_outcome",
                    "accepted" if spec["ground_truth_acceptance"] else "failed",
                ),
                "partial_effect_paths": after,
                "duration_ms": duration_ms,
            }
            add_predictions(row)
            rows.append(row)
            (logs / f"{spec['case_id']}.stdout.log").write_text(
                completed.stdout, encoding="utf-8"
            )
            (logs / f"{spec['case_id']}.stderr.log").write_text(
                completed.stderr, encoding="utf-8"
            )

    actual_payload = json.loads(args.actual_events.read_text(encoding="utf-8"))
    for actual in actual_payload["events"]:
        row = dict(actual)
        add_predictions(row)
        rows.append(row)
        (logs / f"{row['case_id']}.stdout.log").write_text(
            row["stdout"], encoding="utf-8"
        )
        (logs / f"{row['case_id']}.stderr.log").write_text(
            row["stderr"], encoding="utf-8"
        )

    minimal_records: list[dict[str, Any]] = []
    full_records: list[dict[str, Any]] = []
    for row in rows:
        minimal, full = project_records(row)
        minimal_records.append(minimal)
        full_records.append(full)

    acceptance_predictors = [
        "stdout_language_acceptance",
        "outer_exit_acceptance",
        "postcondition_only_acceptance",
        "minimal_contract_acceptance",
        "eager_full_projection_acceptance",
    ]
    metrics = {
        predictor: bool_metrics(rows, predictor, "ground_truth_acceptance")
        for predictor in acceptance_predictors
    }
    effect_metrics = {
        "outer_exit_as_effect": bool_metrics(
            rows, "outer_exit_acceptance", "ground_truth_effect"
        ),
        "postcondition_as_effect": bool_metrics(
            rows, "postcondition_passed", "ground_truth_effect"
        ),
    }
    minimal_bytes = len(
        json.dumps(minimal_records, ensure_ascii=False, separators=(",", ":")).encode()
    )
    full_bytes = len(
        json.dumps(full_records, ensure_ascii=False, separators=(",", ":")).encode()
    )
    summary = {
        "schema_version": "towow-r5-effect-trace-lab-v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "case_count": len(rows),
        "executed_holdout_count": len(CASES),
        "actual_workspace_trace_count": len(actual_payload["events"]),
        "acceptance_metrics": metrics,
        "effect_metrics": effect_metrics,
        "minimal_projection_bytes": minimal_bytes,
        "eager_full_projection_bytes": full_bytes,
        "eager_to_minimal_byte_ratio": full_bytes / minimal_bytes if minimal_bytes else None,
        "wall_clock_ms": round((time.monotonic() - started) * 1000, 3),
        "scope_limit": (
            "Synthetic holdouts test executor semantics; the Git trace is an actual "
            "workspace event. Record size is not a complete implementation-cost metric."
        ),
    }
    (outputs / "events.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (outputs / "minimal_projection.json").write_text(
        json.dumps(minimal_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (outputs / "eager_full_projection.json").write_text(
        json.dumps(full_records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (outputs / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
