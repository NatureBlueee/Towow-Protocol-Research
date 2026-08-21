"""Generate the actual E0 platform-direct and Authority-removal artifacts."""

from __future__ import annotations

import json
import pathlib
import uuid

from independent_evaluator import build_root_acceptance
from platform_direct import (
    make_frozen_pair_configuration,
    run_platform_direct,
    sha256_value,
)


ROOT = pathlib.Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    batch = f"batch-{uuid.uuid4().int % 10**16:016d}"
    batch_dir = ARTIFACTS / batch
    frozen_configuration = make_frozen_pair_configuration()
    positive = run_platform_direct(
        direct_authority_present=True,
        run_dir=batch_dir / "run-0001",
        frozen_configuration=frozen_configuration,
    )
    removal = run_platform_direct(
        direct_authority_present=False,
        run_dir=batch_dir / "run-0002",
        frozen_configuration=frozen_configuration,
    )
    summary = {
        "schema": "E0_PLATFORM_DIRECT_ACTUAL_PAIR_V2",
        "batch_id": batch,
        "positive_run": {
            "artifact": f"{batch}/run-0001/artifact.json",
            "run_id": positive["run_id"],
            "artifact_sha256": positive["artifact_sha256"],
            "evaluation": positive["evaluation"],
            "cost": positive["cost"],
        },
        "authority_removal_run": {
            "artifact": f"{batch}/run-0002/artifact.json",
            "run_id": removal["run_id"],
            "artifact_sha256": removal["artifact_sha256"],
            "evaluation": removal["evaluation"],
            "cost": removal["cost"],
        },
        "counterfactual_binding": {
            "frozen_input_sha256": positive["frozen_input"][
                "frozen_input_sha256"
            ],
            "same_frozen_input": (
                positive["frozen_input"] == removal["frozen_input"]
            ),
            "positive_signed_authority_status": positive["evaluation"][
                "SignedAuthorityStatus"
            ],
            "removal_signed_authority_status": removal["evaluation"][
                "SignedAuthorityStatus"
            ],
            "positive_target_version": positive["target_final_state"]["version"],
            "removal_target_version": removal["target_final_state"]["version"],
        },
        "claim_boundary": (
            "LOCAL_SYNTHETIC_E0_LAWFULLY_UNIFIED_PLATFORM_DIRECT; "
            "NOT_REAL_POWER_OR_GENERAL_CE001"
        ),
    }
    summary["summary_sha256"] = sha256_value(summary)
    summary_path = ARTIFACTS / "actual-e0-platform-direct.json"
    temporary_path = ARTIFACTS / "actual-e0-platform-direct.json.tmp"
    temporary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(summary_path)
    latest_path = ARTIFACTS / "latest-batch.txt"
    latest_temp = ARTIFACTS / "latest-batch.txt.tmp"
    latest_temp.write_text(f"{batch}\n", encoding="utf-8")
    latest_temp.replace(latest_path)
    root = build_root_acceptance(
        summary_path,
        ARTIFACTS / "ROOT-ACCEPTANCE.json",
    )

    # No cleanup is done implicitly: prior evidence remains available and can
    # be removed only by a separate, intentional maintenance action.
    print(
        json.dumps(
            {
                "summary": summary,
                "root_acceptance": {
                    "decision": root["decision"],
                    "root_sha256": root["root_sha256"],
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
