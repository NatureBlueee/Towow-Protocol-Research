#!/usr/bin/env python3
"""Run semantic conformance and/or local synthetic E2E execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluator import evaluate, load_frozen_grader
from method import G6Method
from model import (
    Attempt,
    AuthorityObservation,
    AuthorityStatus,
    Episode,
    Finality,
    Obligation,
    RawOccurrence,
    SchemePhase,
    Truth,
    _jsonable,
    assess_effect,
    assess_settlement,
)
from owner_api import start_owner_session
from scenarios import CASE_IDS, build_world
from wire import canonical_bytes, canonical_hash


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"


def semantic_conformance() -> dict:
    episode = Episode("CE-001:semantic", "Q@v1", "Circuit-C7")
    attempt = Attempt(
        "attempt-sem", "op-sem", "provider", "Circuit-C7",
        episode.episode_id, episode.q_version, 100
    )
    authorized = AuthorityObservation(
        "O_S", "op-sem", "provider", "Circuit-C7", "Q@v1",
        AuthorityStatus.AUTHORIZED, 100, "scope:op-sem:Circuit-C7"
    )
    occurrences = {
        "exact": RawOccurrence(
            "occ-exact", "O_E", "TARGET_NATIVE", "POWER_STATE_TRANSITION",
            "Circuit-C7", 101, "op-sem", "UNPOWERED", "POWERED", 3.0
        ),
        "preexisting": RawOccurrence(
            "occ-pre", "O_E", "TARGET_NATIVE", "POWER_STATE_TRANSITION",
            "Circuit-C7", 90, None, "UNPOWERED", "POWERED", 3.0
        ),
        "wrong_target_damage": RawOccurrence(
            "occ-wrong", "O_E", "TARGET_NATIVE", "POWER_STATE_TRANSITION",
            "Circuit-C8", 101, "op-sem", "UNPOWERED", "POWERED", 3.0, True
        ),
    }
    assessments = {
        name: assess_effect(episode, attempt, occurrence, authorized)
        for name, occurrence in occurrences.items()
    }
    unauthorized = assess_effect(
        episode,
        attempt,
        occurrences["exact"],
        AuthorityObservation(
            "O_S", "op-sem", "provider", "Circuit-C7", "Q@v1",
            AuthorityStatus.UNAUTHORIZED, 100, "scope:none"
        ),
    )
    obligation = Obligation(
        "obl-sem", "O_P", "occ-exact", "CE_PAY_V1", "requester",
        "provider", ("CAPTURE", "PAYOUT"), ("DISPUTE", "REVERSAL"), 105
    )
    reversal_phases = [
        SchemePhase(
            "obl-sem", "CE_PAY_V1", "CAPTURE", Truth.TRUE, 102,
            "phase-capture"
        ),
        SchemePhase(
            "obl-sem", "CE_PAY_V1", "PAYOUT", Truth.TRUE, 103,
            "phase-payout"
        ),
        SchemePhase(
            "obl-sem", "CE_PAY_V1", "DISPUTE", Truth.FALSE, 104,
            "phase-dispute"
        ),
        SchemePhase(
            "obl-sem", "CE_PAY_V1", "REVERSAL", Truth.TRUE, 106,
            "phase-reversal", "phase-payout"
        ),
    ]
    settlement = assess_settlement(obligation, reversal_phases, 110)
    checks = {
        "exact_attempt_counts": assessments["exact"].counts_toward_q,
        "preexisting_does_not_count": (
            not assessments["preexisting"].counts_toward_q
            and assessments["preexisting"].causality.value == "PRE_EXISTING"
            and assessments["preexisting"].current_state_matches_q
            and not assessments["preexisting"].exact_attempt_causality
            and assessments["preexisting"].episode_contribution == Truth.FALSE
        ),
        "wrong_target_damage_preserved": (
            assessments["wrong_target_damage"].qualifies_as_effect
            and not assessments["wrong_target_damage"].counts_toward_q
            and not assessments[
                "wrong_target_damage"
            ].authority_covers_actual_object
            and assessments[
                "wrong_target_damage"
            ].episode_contribution == Truth.FALSE
            and assessments["wrong_target_damage"].recovery.value == "REQUIRED"
        ),
        "unauthorized_effect_preserved": (
            unauthorized.qualifies_as_effect
            and not unauthorized.counts_toward_q
            and unauthorized.recovery.value == "REQUIRED"
        ),
        "settlement_reversal_not_final": (
            settlement.finality == Finality.REVERSED
            and not settlement.discharged
        ),
        "settlement_is_obligation_graph": (
            settlement.graph["nodes"][0]["type"] == "O_P_OBLIGATION"
            and any(
                edge["kind"] == "REVERSES"
                for edge in settlement.graph["edges"]
            )
        ),
    }
    return {
        "evidence_class": "LOCAL_SYNTHETIC_COMPONENT",
        "semantic_checks": checks,
        "passed": sum(checks.values()),
        "total": len(checks),
        "end_to_end_execution": "NOT_PART_OF_THIS_DENOMINATOR",
        "real_product_execution": "NOT_RUN",
    }


def end_to_end() -> tuple[dict, list[dict]]:
    records = []
    trace = []
    method = G6Method()
    grader = load_frozen_grader()
    for case_id in CASE_IDS:
        world = build_world(case_id)
        with start_owner_session(world) as session:
            client = session.client
            result = method.run(world.plan, client)
            case_trace = list(client.trace)
            plan_sha256 = canonical_hash(canonical_bytes(world.plan))
            trace_closure = session.freeze_closure(
                plan_sha256,
                canonical_hash(canonical_bytes(result.as_dict())),
            )
        records.append({
            "evaluation": evaluate(
                result,
                case_id,
                grader,
                trace_closure=trace_closure,
                expected_plan_sha256=plan_sha256,
            ),
            "method_result": result.as_dict(),
            "trace_closure": _jsonable(trace_closure),
        })
        trace.extend(
            {"case_id": case_id, **receipt.as_dict()}
            for receipt in case_trace
        )
    evaluations = [record["evaluation"] for record in records]
    summary = {
        "evidence_class": "LOCAL_SYNTHETIC_E2E",
        "case_count": len(records),
        "correct_resolution": sum(
            item["correct_resolution"] for item in evaluations
        ),
        "g6_line_local_closure": sum(
            item["g6_line_local_closure"] for item in evaluations
        ),
        "contract_exact_task_success": "NOT_COMPUTED_BY_G6",
        "deadline": "UNKNOWN",
        "continuous_duration": "UNKNOWN",
        "full_safety_constraints": "UNKNOWN",
        "raw_occurrences": sum(
            item["raw_occurrence_count"] for item in evaluations
        ),
        "wrong_target_real_effects": sum(
            item["wrong_target_real_effect_count"] for item in evaluations
        ),
        "recoveries": sum(item["recovery_count"] for item in evaluations),
        "duplicate_effects": sum(item["duplicate_effect"] for item in evaluations),
        "owner_api_calls": len(trace),
        "semantic_conformance": "SEPARATE_RUN",
        "real_product_execution": "NOT_RUN",
        "production_effect": "NOT_RUN",
        "human_acceptance": "NOT_RUN",
        "payment_finality": "NOT_RUN",
        "records": records,
    }
    return summary, trace


def failure_injections() -> tuple[dict, list[dict]]:
    method = G6Method()
    records = []
    trace = []

    preexisting = build_world("E0-PLATFORM-DIRECT")
    preexisting.effect.operations["op-platform"].create_effect = False
    preexisting.occurrences.append(
        RawOccurrence(
            "occ-preexisting", "O_E", "TARGET_NATIVE",
            "POWER_STATE_TRANSITION", "Circuit-C7", 90, None,
            "UNPOWERED", "POWERED", 3.0
        )
    )
    injections = [("PREEXISTING_STATE", preexisting)]

    owner_down = build_world("E0-PLATFORM-DIRECT")
    owner_down.fail_endpoint("O_E", "effects")
    injections.append(("OWNER_READBACK_UNAVAILABLE", owner_down))

    acceptance_refusal = build_world("E0-PLATFORM-DIRECT")
    acceptance_refusal.venue.acceptance_state = Truth.FALSE
    injections.append(("VENUE_ACCEPTANCE_REFUSAL", acceptance_refusal))

    settlement_reversal = build_world("E0-PLATFORM-DIRECT")
    settlement_reversal.payment.reversal = True
    injections.append(("SETTLEMENT_REVERSAL", settlement_reversal))

    for injection_id, world in injections:
        with start_owner_session(world) as session:
            client = session.client
            result = method.run(world.plan, client)
            injection_trace = list(client.trace)
        record = {
            "injection_id": injection_id,
            "resolution": result.resolution,
            "counting_effects": sum(
                effect.counts_toward_q for effect in result.effects
            ),
            "preexisting_effects": sum(
                effect.causality.value == "PRE_EXISTING"
                for effect in result.effects
            ),
            "settled_obligations": sum(
                settlement.discharged for settlement in result.settlements
            ),
            "reversed_obligations": sum(
                settlement.finality.value == "REVERSED"
                for settlement in result.settlements
            ),
            "settlement_attempted": bool(result.settlements),
        }
        records.append(record)
        trace.extend(
            {"injection_id": injection_id, **receipt.as_dict()}
            for receipt in injection_trace
        )
    checks = {
        "preexisting_not_counted": (
            records[0]["preexisting_effects"] == 1
            and records[0]["counting_effects"] == 0
        ),
        "owner_unavailable_stays_unknown": (
            records[1]["resolution"] == "BOUNDED_UNKNOWN_OWNER_UNAVAILABLE"
            and not records[1]["settlement_attempted"]
        ),
        "acceptance_refusal_blocks_settlement": (
            records[2]["resolution"] == "EFFECT_WITHOUT_ACCEPTANCE"
            and not records[2]["settlement_attempted"]
        ),
        "reversal_reopens_obligation": (
            records[3]["resolution"] == "ACCEPTED_SETTLEMENT_OPEN"
            and records[3]["reversed_obligations"] == 1
            and records[3]["settled_obligations"] == 0
        ),
    }
    return {
        "evidence_class": "LOCAL_SYNTHETIC_FAILURE_INJECTION",
        "injection_count": len(records),
        "passed": sum(checks.values()),
        "total": len(checks),
        "checks": checks,
        "records": records,
        "real_product_execution": "NOT_RUN",
    }, trace


def write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("semantic", "end-to-end", "failure-injection", "all"),
        default="all",
    )
    args = parser.parse_args()
    ARTIFACTS.mkdir(exist_ok=True)
    output: dict[str, object] = {}
    if args.mode in {"semantic", "all"}:
        semantic = semantic_conformance()
        write_json(ARTIFACTS / "semantic-results.json", semantic)
        output["semantic"] = semantic
    if args.mode in {"end-to-end", "all"}:
        e2e, trace = end_to_end()
        write_json(ARTIFACTS / "e2e-results.json", e2e)
        (ARTIFACTS / "raw-trace.jsonl").write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                for item in trace
            ),
            encoding="utf-8",
        )
        output["end_to_end"] = {
            key: value for key, value in e2e.items() if key != "records"
        }
    if args.mode in {"failure-injection", "all"}:
        failures, failure_trace = failure_injections()
        write_json(ARTIFACTS / "failure-injection-results.json", failures)
        (ARTIFACTS / "failure-trace.jsonl").write_text(
            "".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
                for item in failure_trace
            ),
            encoding="utf-8",
        )
        output["failure_injection"] = {
            key: value for key, value in failures.items() if key != "records"
        }
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
