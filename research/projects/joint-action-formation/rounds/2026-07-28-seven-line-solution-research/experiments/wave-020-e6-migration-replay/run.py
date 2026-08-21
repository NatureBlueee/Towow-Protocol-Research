"""Generate the actual E6 baseline/removal pair and frozen ROOT."""

from __future__ import annotations

import json
import pathlib
import uuid

from independent_evaluator import build_root
from migration_runtime import (
    make_frozen_configuration,
    run_case,
    sha256_value,
)


ROOT = pathlib.Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    suite_id = f"suite-{uuid.uuid4().hex}"
    suite_dir = ARTIFACTS / suite_id
    frozen = make_frozen_configuration()
    baseline = run_case(
        run_dir=suite_dir / "case-001",
        frozen=frozen,
        evidence_projection="DURABLE_FULL",
    )
    removal = run_case(
        run_dir=suite_dir / "case-002",
        frozen=frozen,
        evidence_projection="REMOVE_TARGET_LEDGER_READBACK",
    )
    summary = {
        "schema": "E6_ACTUAL_PAIR_V1",
        "suite_id": suite_id,
        "frozen_input_sha256": frozen["public"]["frozen_input_sha256"],
        "baseline": {
            "artifact": f"{suite_id}/case-001/artifact.json",
            "artifact_sha256": baseline["artifact_sha256"],
        },
        "removal": {
            "artifact": f"{suite_id}/case-002/artifact.json",
            "artifact_sha256": removal["artifact_sha256"],
        },
        "claim_boundary": (
            "LOCAL_SYNTHETIC_EXISTING_DURABLE_WORKFLOW_LEDGER_FENCE"
        ),
    }
    summary["summary_sha256"] = sha256_value(summary)
    summary_path = ARTIFACTS / "actual-e6-migration-replay.json"
    temporary = ARTIFACTS / "actual-e6-migration-replay.json.tmp"
    temporary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(summary_path)
    root = build_root(
        summary_path,
        ARTIFACTS / "ROOT-ACCEPTANCE.json",
    )
    latest = ARTIFACTS / "latest-suite.txt"
    latest_temp = ARTIFACTS / "latest-suite.txt.tmp"
    latest_temp.write_text(f"{suite_id}\n", encoding="utf-8")
    latest_temp.replace(latest)
    print(
        json.dumps(
            {
                "summary": summary,
                "root": {
                    "decision": root["decision"],
                    "root_sha256": root["root_sha256"],
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0 if root["decision"] == "ACCEPTED_SCOPED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
