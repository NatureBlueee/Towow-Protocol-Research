from __future__ import annotations

import os
import sys

from .models import RunRecord
from .protocol import read_message, write_message
from .scorer import FormationScorer


def _record(value: dict) -> RunRecord:
    return RunRecord(**value)


def main() -> int:
    message = read_message(sys.stdin)
    if message.get("type") != "GRADE_FROZEN_TRANSCRIPT":
        raise ValueError("grader requires frozen transcript input")
    run = _record(message["run"])
    counterfactuals = [_record(item) for item in message["counterfactuals"]]
    receipt = FormationScorer(
        message["case_truth"], message["semantic_case_id"]
    ).score(message["public_case"], run, counterfactuals)
    write_message(
        sys.stdout,
        {
            "type": "GRADER_RESULT",
            "grader_pid": os.getpid(),
            "transcript_frozen_sha256": message[
                "transcript_frozen_sha256"
            ],
            "receipt": receipt,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
