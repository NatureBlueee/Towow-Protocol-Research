#!/usr/bin/env python3
"""Audit the three different interaction quantifiers used by the fixture."""

from __future__ import annotations

import copy
import itertools
import json
from pathlib import Path
from typing import Any

from primitive_services import PrimitiveService
from runner import FIXTURE, ORACLE, expanded_public


HERE = Path(__file__).resolve().parent


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def service_for(
    fixture: dict[str, Any], oracle: dict[str, Any], world_ref: str
) -> PrimitiveService:
    world = next(item for item in fixture["worlds"] if item["world_ref"] == world_ref)
    packet = expanded_public(fixture, world)
    return PrimitiveService(
        world_ref,
        packet,
        oracle["base_state"],
        oracle["worlds"][world_ref],
        world["allowed_actions"],
    )


def args_for(service: PrimitiveService) -> dict[str, Any]:
    op = service.operation
    return {
        "operation_id": op["operation_id"],
        "operation_hash": op["arguments_hash"],
        "target_id": op["target_id"],
        "token_id": op["token_id"],
        "resource_id": op["resource_id"],
        "requested_delegate": "delegated-center",
        "requested_scope": "exact-operation",
    }


def transcript(
    fixture: dict[str, Any],
    oracle: dict[str, Any],
    world_ref: str,
    plan: tuple[str, ...],
) -> list[Any]:
    service = service_for(fixture, oracle, world_ref)
    args = args_for(service)
    output: list[Any] = []
    for action in plan:
        raw = service.call(action, args)
        output.append(raw)
        if action == "request_authority" and isinstance(raw, dict):
            args["authority_revision"] = raw.get("revision")
        elif action == "request_delegation" and isinstance(raw, dict):
            args["delegation_revision"] = raw.get("revision")
            args["delegate"] = raw.get("delegate")
        elif action == "request_reservation" and isinstance(raw, dict):
            args["reservation_sequence"] = raw.get("fence_sequence")
    return output


def audit() -> dict[str, Any]:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    oracle = json.loads(ORACLE.read_text(encoding="utf-8"))
    worlds = {item["world_ref"]: item for item in fixture["worlds"]}
    results: dict[str, Any] = {}
    active_probe = {
        "A-STALE-HEAD-TWO-SEMANTICS": ("read_policy",),
        "A-RESPONSE-LOST": (
            "request_authority",
            "request_reservation",
            "submit_operation",
            "read_operation_status",
        ),
        "A-REVOCATION-AFTER-CHECK": ("request_authority",),
        "A-RESERVATION-NOT-CONSENT": (
            "request_reservation",
            "request_authority",
        ),
    }
    for pair in fixture["pairs"]:
        left, right = pair["worlds"]
        left_packet = expanded_public(fixture, worlds[left])
        right_packet = expanded_public(fixture, worlds[right])
        initial_equal = canonical(left_packet) == canonical(right_packet)
        pair_class = pair["pair_class"]
        if pair_class == "PASSIVE":
            results[pair["pair_ref"]] = {
                "pair_class": pair_class,
                "initial_packets_identical": initial_equal,
                "quantifier": "initial observation only",
                "passes": initial_equal,
            }
        elif pair_class == "ACTIVE":
            plan = active_probe[pair["pair_ref"]]
            left_trace = transcript(fixture, oracle, left, plan)
            right_trace = transcript(fixture, oracle, right, plan)
            results[pair["pair_ref"]] = {
                "pair_class": pair_class,
                "initial_packets_identical": initial_equal,
                "witness_plan": list(plan),
                "lawful_trace_differs": canonical(left_trace) != canonical(right_trace),
                "quantifier": "there exists a lawful distinguishing or truth-changing action trace",
                "passes": initial_equal and canonical(left_trace) != canonical(right_trace),
            }
        else:
            common_actions = sorted(
                set(worlds[left]["allowed_actions"])
                & set(worlds[right]["allowed_actions"])
            )
            plans = [tuple()]
            plans += [(action,) for action in common_actions]
            plans += list(itertools.product(common_actions, repeat=2))
            unequal: list[list[str]] = []
            for plan in plans:
                if canonical(transcript(fixture, oracle, left, plan)) != canonical(
                    transcript(fixture, oracle, right, plan)
                ):
                    unequal.append(list(plan))
            left_initial_truth = oracle["worlds"][left]["p0"]
            right_initial_truth = oracle["worlds"][right]["p0"]
            results[pair["pair_ref"]] = {
                "pair_class": pair_class,
                "initial_packets_identical": initial_equal,
                "action_alphabet": common_actions,
                "enumerated_plans": len(plans),
                "max_sequence_length": 2,
                "unequal_transcript_plans": unequal,
                "opposite_initial_success_truth": (
                    left_initial_truth["Y_success"]
                    != right_initial_truth["Y_success"]
                ),
                "quantifier": "for every lawful sequence in the finite alphabet through depth two, raw transcripts are equal",
                "passes": (
                    initial_equal
                    and not unequal
                    and left_initial_truth["Y_success"]
                    != right_initial_truth["Y_success"]
                ),
            }
    return {
        "fixture_id": fixture["fixture_id"],
        "results": results,
        "all_pairs_pass": all(item["passes"] for item in results.values()),
        "scope": "finite deterministic service model; hard-pair universal quantifier is bounded to the declared action alphabet and sequence depth two",
    }


if __name__ == "__main__":
    print(json.dumps(audit(), ensure_ascii=False, indent=2, sort_keys=True))
