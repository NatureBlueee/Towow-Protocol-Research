#!/usr/bin/env python3
"""Reproduce five runtime-admission gaps in the frozen Wave 021 validator.

This does not modify Wave 021 or claim its preregistration is invalid.  It shows
that the static validator cannot admit scored runtime evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
WAVE021 = ROOT.parent / "wave-021-fair-baselines"
sys.path.insert(0, str(WAVE021))

import fairness_validator as v  # noqa: E402


def file_sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def arm(plan: dict[str, Any], arm_id: str) -> dict[str, Any]:
    return next(item for item in plan["arm_runs"] if item["arm_id"] == arm_id)


def reproduce() -> dict[str, Any]:
    contract_path = WAVE021 / "BASELINE-CONTRACT.json"
    plan_path = WAVE021 / "fixtures" / "FAIR-BATCH-TEMPLATE.json"
    trigger_path = WAVE021 / "fixtures" / "FAIR-FAILURE-TRIGGER.json"
    contract = v.load_json(contract_path)
    plan = v.load_json(plan_path)
    trigger = v.load_json(trigger_path)

    results: dict[str, str] = {}

    attacked = copy.deepcopy(plan)
    arm(attacked, "A4-DETERMINISTIC-MATURE-COMPOSITION").update(
        {
            "runtime_env": {"CASE": "E4", "EXPECTED": "SUCCESS"},
            "startup_payload_values": {"private_truth": True},
        }
    )
    results["unknown_payload_oracle"] = v.validate_batch_plan(
        attacked, contract
    )["status"]

    attacked = copy.deepcopy(plan)
    attacked["actual_world_authority_stratum"] = "P"
    results["declared_U_actual_P"] = v.validate_batch_plan(
        attacked, contract
    )["status"]

    attacked = copy.deepcopy(plan)
    arm(attacked, "A3-GENERAL-MODEL-MATURE-STACK").update(
        {
            "model_calls": 10_000,
            "hidden_retrieval": True,
            "input_tokens": 999_999_999,
        }
    )
    results["unmetered_A3"] = v.validate_batch_plan(attacked, contract)[
        "status"
    ]

    attacked_trigger = copy.deepcopy(trigger)
    attacked_trigger.update(
        {
            "per_arm_trigger": {
                "A1": "after_success",
                "A4": "after_grader_green",
            },
            "q_version_bound": False,
            "target_id_bound": False,
            "operation_scope_bound": False,
        }
    )
    results["posthoc_per_arm_trigger"] = v.validate_failure_trigger_spec(
        attacked_trigger, contract
    )["status"]

    attacked = copy.deepcopy(plan)
    for index, run in enumerate(attacked["arm_runs"]):
        run.update(
            {
                "candidate_executable": f"/tmp/arm-{index}.py",
                "world_root": f"/tmp/world-{index}",
            }
        )
    results["unfrozen_executable_world"] = v.validate_batch_plan(
        attacked, contract
    )["status"]

    return {
        "schema": "WAVE021_RUNTIME_ADMISSION_GAP_REPRODUCTION_V1",
        "interpretation": (
            "ALL_ATTACKS_ACCEPTED_BY_STATIC_VALIDATOR; "
            "WAVE021_REMAINS_PREREGISTRATION_ONLY"
        ),
        "source_files": {
            "contract": {
                "path": str(contract_path.relative_to(ROOT.parents[3])),
                "sha256": file_sha256(contract_path),
            },
            "plan": {
                "path": str(plan_path.relative_to(ROOT.parents[3])),
                "sha256": file_sha256(plan_path),
            },
            "trigger": {
                "path": str(trigger_path.relative_to(ROOT.parents[3])),
                "sha256": file_sha256(trigger_path),
            },
        },
        "results": results,
        "all_attacks_accepted": len(results) == 5
        and all("ACCEPTED" in status for status in results.values()),
        "claim_boundary": {
            "wave021_contract_invalidated": False,
            "wave021_scored_runtime_admission_supported": False,
            "wave023_sealed_admission_required": True,
        },
    }


def main(argv: list[str]) -> int:
    result = reproduce()
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(argv) == 2:
        output = pathlib.Path(argv[1]).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0 if result["all_attacks_accepted"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

