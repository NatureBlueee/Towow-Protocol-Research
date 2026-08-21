#!/usr/bin/env python3
"""Non-candidate diagnostic for scorer sensitivity to event/probe identifiers.

This deliberately rewrites only identifiers, not route semantics. The mutated
file is invalid as controller evidence and must never replace the development
candidate.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import adapter


HERE = Path(__file__).resolve().parent
DIAGNOSTICS = HERE / "diagnostics"


def run() -> dict:
    candidate_path = adapter.HWB_ROOT / "candidate-submission-v2.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(candidate)
    aliases = {
        "HELIOS-44": "EV-HWB-HELIOS-TO-COPPER",
        "ION-06:0": "EV-HWB-ION-TO-SILVER",
        "ION-06:1": "EV-HWB-ION-SILVER-TO-COPPER",
        "JUNIPER-28": "EV-HWB-JUNIPER-TO-KITE",
        "KITE-15": "EV-HWB-KITE-TO-JUNIPER",
    }
    old_to_new = {}
    for item in mutated["disclosures"]:
        if item["origin_party"] == "ION-06":
            key = f"ION-06:{item['depth']}"
        else:
            key = item["origin_party"]
        old_to_new[item["event_id"]] = aliases[key]
        item["event_id"] = aliases[key]
    for item in mutated["disclosures"]:
        if "derived_from_event_id" in item:
            item["derived_from_event_id"] = old_to_new[
                item["derived_from_event_id"]
            ]
    mutated["probes"][0]["probe_id"] = "PROBE-HWB-JUNIPER-KITE"

    mutated_path = DIAGNOSTICS / "evaluator-id-alias-mutation.json"
    score_path = DIAGNOSTICS / "evaluator-id-alias-mutation-score.json"
    adapter.write_json(mutated_path, mutated)
    completed = subprocess.run(
        [
            "python3",
            "scorer.py",
            "--submission",
            str(mutated_path),
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
    adapter.write_json(score_path, score)
    record = {
        "schema": "towow.evaluator-id-sensitivity-diagnostic.v1",
        "status": "INVALID_EVALUATOR_DIAGNOSTIC_NOT_CANDIDATE",
        "mutation": "IDENTIFIERS_ONLY",
        "candidate_semantic_fields_changed": False,
        "controller_evidence_binding_preserved": False,
        "original_candidate_score": {
            "requirements_passed": 4,
            "requirements_total": 8,
        },
        "mutated_score": {
            "status": score["status"],
            "requirements_passed": score["coverage"]["requirements_passed"],
            "requirements_total": score["coverage"]["requirements_total"],
        },
        "interpretation_if_score_changes": (
            "The scorer is sensitive to unregistered identifiers rather than "
            "only to the declared route/probe semantics."
        ),
        "forbidden_use": [
            "candidate replacement",
            "controller completion evidence",
            "blind score",
        ],
    }
    adapter.write_json(DIAGNOSTICS / "README.json", record)
    return record


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True, indent=2))
