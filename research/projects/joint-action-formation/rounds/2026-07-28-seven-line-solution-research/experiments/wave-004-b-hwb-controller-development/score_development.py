#!/usr/bin/env python3
"""Run the public HW-B scorer after the controller-derived candidate exists."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import adapter


HERE = Path(__file__).resolve().parent
CANDIDATE = adapter.HWB_ROOT / "candidate-submission-v2.json"
SCORE = adapter.HWB_ROOT / "candidate-score-v2-development.json"
RECORD = HERE / "development-score-record.json"


def run() -> dict:
    if not CANDIDATE.exists():
        raise RuntimeError("CANDIDATE_V2_MISSING")
    completed = subprocess.run(
        [
            "python3",
            "scorer.py",
            "--submission",
            CANDIDATE.name,
        ],
        cwd=adapter.HWB_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError(
            f"SCORER_PROCESS_FAILED:{completed.returncode}:{completed.stderr}"
        )
    score = json.loads(completed.stdout)
    adapter.write_json(SCORE, score)
    record = {
        "schema": "towow.hwb-development-score-record.v1",
        "development_label": "DEVELOPMENT_POST_FEEDBACK_NOT_BLIND",
        "candidate_path": str(CANDIDATE.relative_to(adapter.ROUND_ROOT)),
        "candidate_file_sha256": adapter.hashlib.sha256(
            CANDIDATE.read_bytes()
        ).hexdigest(),
        "scorer_output_path": str(SCORE.relative_to(adapter.ROUND_ROOT)),
        "scorer_output_file_sha256": adapter.hashlib.sha256(
            SCORE.read_bytes()
        ).hexdigest(),
        "status": score["status"],
        "requirements_passed": score["coverage"]["requirements_passed"],
        "requirements_total": score["coverage"]["requirements_total"],
        "coverage_ratio": score["coverage"]["ratio"],
        "not_claimed": [
            "new blind result",
            "real-world effect",
            "recipient-independent acknowledgement",
        ],
    }
    adapter.write_json(RECORD, record)
    return record


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True, indent=2))
