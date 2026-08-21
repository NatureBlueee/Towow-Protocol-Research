"""Run the Wave 011 discriminator over the frozen pilot worlds."""

from __future__ import annotations

from dataclasses import asdict
import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any

from .evaluator import evaluate_candidate, summarize
from .model import PRIVATE_ORACLE, VISIBLE_FIXTURE, load_oracle, load_worlds
from .workers import WORKERS, full_trace


def run_arm(arm: str) -> dict[str, Any]:
    worlds = load_worlds()
    oracle = load_oracle()
    evaluations = []
    for world_id, world in worlds.items():
        if arm == "FULL_TRACE":
            candidate = full_trace(world)
            intervention = "FULL_ACTUAL_TRACE"
        elif arm == "REMOVE_OPERATOR":
            candidate = full_trace(world, mutation="REMOVE_OPERATOR")
            intervention = "REMOVE_OPERATOR"
        elif arm == "REVERSE_OPERATOR":
            candidate = full_trace(world, mutation="REVERSE_OPERATOR")
            intervention = "REVERSE_OPERATOR"
        else:
            candidate = WORKERS[arm](world)
            intervention = {
                "PUBLIC_BASELINE": "PUBLIC_BASELINE",
                "FINAL_PROPOSAL_ONLY": "FINAL_PROPOSAL_ONLY",
            }.get(arm, "T0_LEGAL_EVIDENCE_PATH")
        evaluations.append(
            evaluate_candidate(
                candidate,
                world,
                oracle[world_id],
                trusted_arm=arm,
                intervention=intervention,
            )
        )
    return {
        "arm": arm,
        "summary": summarize(evaluations),
        "worlds": [asdict(item) for item in evaluations],
    }


def build_report() -> dict[str, Any]:
    arms = [
        "PUBLIC_BASELINE",
        "C_EQUAL_ACCESS",
        "H_EQUAL_ENVELOPE",
        "C_RAW_UPPER",
        "FINAL_PROPOSAL_ONLY",
        "FULL_TRACE",
        "REMOVE_OPERATOR",
        "REVERSE_OPERATOR",
    ]
    return {
        "schema_version": "wave011-g1-provenance-discriminator-v1",
        "evidence_level": "LOCAL_SYNTHETIC_INSTRUMENT_ONLY",
        "intent_boundary": "IntentAtCoordinationInterface",
        "isolation_boundary": (
            "MODULE_AND_INPUT_DISCIPLINE_ONLY_NOT_HOSTILE_SAME_PROCESS"
        ),
        "cannot_support": (
            "LEAK_FREE_EVALUATION_AGAINST_REFLECTIVE_OR_MALICIOUS_WORKER"
        ),
        "population_receipt": {
            "method_visible_sha256": hashlib.sha256(
                VISIBLE_FIXTURE.read_bytes()
            ).hexdigest(),
            "private_oracle_sha256": hashlib.sha256(
                PRIVATE_ORACLE.read_bytes()
            ).hexdigest(),
        },
        "worker_implementation_sha256": {
            arm: hashlib.sha256(
                inspect.getsource(worker).encode("utf-8")
            ).hexdigest()
            for arm, worker in WORKERS.items()
        },
        "arms": {arm: run_arm(arm) for arm in arms},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
