from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .fixtures import ORACLE_BY_ID, PUBLIC_BY_ID
from .model import Proposal, Trace, serialize
from .oracle import evaluate
from .session import ActionSession
from .workers import WORKER_BY_NAME, WORKERS


INTERVENTIONS = (
    "PUBLIC_BASELINE",
    "T0_LEGAL_EVIDENCE_PATH",
    "FINAL_PROPOSAL_ONLY",
    "FULL_ACTUAL_TRACE",
)


def make_session(
    world_id: str,
    arm: str,
    intervention: str,
    *,
    oracle_override: dict[str, Any] | None = None,
    removed_operator: str | None = None,
    reversed_operator: str | None = None,
) -> tuple[ActionSession, dict[str, Any]]:
    public = PUBLIC_BY_ID[world_id]
    oracle = deepcopy(oracle_override or ORACLE_BY_ID[world_id])
    trace = Trace(world_id=world_id, arm=arm, intervention=intervention)
    allow_queries = intervention in {"T0_LEGAL_EVIDENCE_PATH", "FULL_ACTUAL_TRACE"}
    allow_operators = intervention == "FULL_ACTUAL_TRACE"
    allow_raw = arm == "C_RAW_UPPER"
    session = ActionSession(
        public,
        oracle,
        trace,
        allow_t0_queries=allow_queries,
        allow_operators=allow_operators,
        allow_raw=allow_raw,
        removed_operator=removed_operator,
        reversed_operator=reversed_operator,
    )
    return session, oracle


def run_arm(
    world_id: str,
    arm: str,
    intervention: str = "FULL_ACTUAL_TRACE",
    *,
    oracle_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session, oracle = make_session(
        world_id, arm, intervention, oracle_override=oracle_override
    )
    WORKER_BY_NAME[arm].run(session)
    return {"trace": serialize(session.trace), "vector": evaluate(oracle, session.trace)}


def _submit_canonical(session: ActionSession, oracle: dict[str, Any]) -> None:
    canonical = oracle["canonical_proposal"]
    session.submit_proposal(
        Proposal(
            path_id=canonical["path_id"],
            target=canonical["target"],
            quality_floor=canonical["quality_floor"],
            necessary_principals=tuple(canonical["necessary_principals"]),
        ),
        "FROZEN_FINAL_PROPOSAL",
    )


def run_intervention(
    world_id: str,
    intervention: str,
    *,
    removed_operator: str | None = None,
    reversed_operator: str | None = None,
) -> dict[str, Any]:
    session, oracle = make_session(
        world_id,
        "CANONICAL_INTERVENTION",
        intervention,
        removed_operator=removed_operator,
        reversed_operator=reversed_operator,
    )
    public = session.observe_public()
    if intervention == "PUBLIC_BASELINE" and public["public_index"]:
        item = public["public_index"][0]
        session.submit_proposal(
            Proposal(
                path_id=item["path_id"],
                target=item["target"],
                quality_floor=item["quality_floor"],
                necessary_principals=tuple(item["necessary_principals"]),
            ),
            "PUBLIC_INDEX",
        )
    elif intervention != "PUBLIC_BASELINE":
        _submit_canonical(session, oracle)
    if intervention in {"T0_LEGAL_EVIDENCE_PATH", "FULL_ACTUAL_TRACE"}:
        claim = f"complement_for:{public['intent']['objective']}"
        for owner in public["owners"]:
            session.ask(owner, claim)
    if intervention == "FULL_ACTUAL_TRACE":
        for operator_id in session.available_operator_ids:
            session.apply_operator(operator_id)
    return {"trace": serialize(session.trace), "vector": evaluate(oracle, session.trace)}


def run_operator_variants(world_id: str) -> list[dict[str, Any]]:
    oracle = ORACLE_BY_ID[world_id]
    results: list[dict[str, Any]] = []
    for operator in oracle["operators"]:
        operator_id = operator["id"]
        session, private = make_session(
            world_id,
            "CANONICAL_INTERVENTION",
            "FULL_ACTUAL_TRACE",
            removed_operator=operator_id,
        )
        public = session.observe_public()
        _submit_canonical(session, private)
        claim = f"complement_for:{public['intent']['objective']}"
        for owner in public["owners"]:
            session.ask(owner, claim)
        for current in session.available_operator_ids:
            session.apply_operator(current)
        results.append(
            {
                "variant": f"REMOVE_OPERATOR:{operator_id}",
                "trace": serialize(session.trace),
                "vector": evaluate(private, session.trace),
            }
        )
        session, private = make_session(
            world_id,
            "CANONICAL_INTERVENTION",
            "FULL_ACTUAL_TRACE",
            reversed_operator=operator_id,
        )
        public = session.observe_public()
        _submit_canonical(session, private)
        claim = f"complement_for:{public['intent']['objective']}"
        for owner in public["owners"]:
            session.ask(owner, claim)
        for current in session.available_operator_ids:
            session.apply_operator(current)
        results.append(
            {
                "variant": f"REVERSE_OPERATOR:{operator_id}",
                "trace": serialize(session.trace),
                "vector": evaluate(private, session.trace),
            }
        )
    return results


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for item in results:
        by_arm.setdefault(item["vector"]["arm"], []).append(item["vector"])
    summary: dict[str, Any] = {}
    for arm, vectors in by_arm.items():
        l_paths = sum(len(item["l_benchmark"]) for item in vectors)
        d_paths = sum(len(item["d_actual"]) for item in vectors)
        l_hits = sum(
            bool(item["l_benchmark"]) and item["eligible_positive"] for item in vectors
        )
        d_hits = sum(
            bool(item["d_actual"]) and item["eligible_positive"] for item in vectors
        )
        summary[arm] = {
            "structural_recall": l_hits / l_paths if l_paths else None,
            "actual_policy_recall": d_hits / d_paths if d_paths else None,
            "l_benchmark_denominator": l_paths,
            "d_actual_denominator": d_paths,
            "invalid": sum(item["boundary"] == "INVALID" for item in vectors),
            "hard_gate_pass": not any(
                item["boundary"] == "INVALID" for item in vectors
            ),
            "refused_or_indistinguishable_not_actual_miss": sum(
                not item["d_actual"]
                and item["boundary"] in {"UNWILLING_TO_DISCLOSE", "UNKNOWN", "DEFER"}
                for item in vectors
            ),
            "cost": {
                key: sum(item["cost"][key] for item in vectors)
                for key in (
                    "actions",
                    "disclosure_exposure",
                    "model_calls",
                    "human_minutes",
                    "raw_exposure",
                )
            },
        }
    return summary


def run_all() -> dict[str, Any]:
    baseline_results = [
        run_arm(world_id, worker.name)
        for world_id in PUBLIC_BY_ID
        for worker in WORKERS
    ]
    interventions = [
        run_intervention(world_id, intervention)
        for world_id in PUBLIC_BY_ID
        for intervention in INTERVENTIONS
    ]
    operator_variants = [
        result
        for world_id in PUBLIC_BY_ID
        for result in run_operator_variants(world_id)
    ]
    return {
        "scope": {
            "intent_ingress": "IntentAtCoordinationInterface",
            "vague_goal_to_intent": "EXCLUDED",
            "world_count": len(PUBLIC_BY_ID),
            "evidence_level": "LOCAL_SYNTHETIC_DISCRIMINATOR_ONLY",
            "worker_oracle_isolation": (
                "INTERFACE_DISCIPLINE_ONLY_NOT_HOSTILE_SAME_PROCESS"
            ),
            "cannot_support": (
                "LEAK_FREE_EVALUATION_AGAINST_REFLECTIVE_OR_MALICIOUS_WORKER"
            ),
        },
        "baseline_results": baseline_results,
        "baseline_summary": aggregate(baseline_results),
        "interventions": interventions,
        "operator_variants": operator_variants,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = run_all()
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


if __name__ == "__main__":
    main()
