"""Method workers.

Workers never import or load the private oracle.  They are deliberately
different policies over a shared action envelope, not renamed copies.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .model import Candidate, candidate_from_dict


def _stop(world: dict[str, Any], arm: str) -> Candidate:
    return Candidate(
        world_id=world["world_id"],
        proposal_id="NONE",
        principals=(),
        source_arm=arm,
        response_state=world.get("visible_response", "UNKNOWN"),
    )


def _with_arm_cost(candidate: Candidate, world: dict[str, Any], arm: str) -> Candidate:
    cost = dict(world["arm_costs"].get(arm, {}))
    return replace(candidate, source_arm=arm, cost=cost)


def public_baseline(world: dict[str, Any]) -> Candidate:
    """Index/card baseline: it can only consume records marked public at t0."""

    proposal = world.get("public_proposal")
    if proposal is None:
        return _with_arm_cost(_stop(world, "PUBLIC_BASELINE"), world, "PUBLIC_BASELINE")
    candidate = candidate_from_dict(proposal, source_arm="PUBLIC_BASELINE")
    public_ids = set(world.get("public_evidence_ids", ()))
    candidate = replace(
        candidate,
        evidence_ids=tuple(
            evidence_id
            for evidence_id in candidate.evidence_ids
            if evidence_id in public_ids
        ),
    )
    return _with_arm_cost(candidate, world, "PUBLIC_BASELINE")


def equal_access_center(world: dict[str, Any]) -> Candidate:
    """Central planner over only the t0 legal action/evidence envelope."""

    paths = [
        path
        for path in world.get("t0_paths", ())
        if path["allowed"]
        and path["action"] in world["equal_action_envelope"]
        and path["cost"] <= world["budget"]
    ]
    if not paths:
        return _with_arm_cost(
            _stop(world, "C_EQUAL_ACCESS"),
            world,
            "C_EQUAL_ACCESS",
        )
    path = min(paths, key=lambda item: (item["cost"], item["path_id"]))
    proposal = dict(world["final_proposal"])
    proposal["evidence_ids"] = list(path["evidence_ids"])
    candidate = candidate_from_dict(proposal, source_arm="C_EQUAL_ACCESS")
    return _with_arm_cost(candidate, world, "C_EQUAL_ACCESS")


def human_equal_envelope(world: dict[str, Any]) -> Candidate:
    """Human broker heuristic with the same actions, budget and deadline.

    It prioritizes a purpose-bound owner query over public search, and records
    attention/wait cost.  It cannot use a hidden action or an oracle shortcut.
    """

    action_priority = {
        "ASK_OWNER": 0,
        "READ_PUBLIC": 1,
        "RUN_SHARED_PREDICATE": 2,
    }
    paths = [
        path
        for path in world.get("t0_paths", ())
        if path["allowed"]
        and path["action"] in world["equal_action_envelope"]
        and path["action"] in world["human_action_envelope"]
        and path["cost"] <= world["budget"]
    ]
    if not paths:
        return _with_arm_cost(
            _stop(world, "H_EQUAL_ENVELOPE"),
            world,
            "H_EQUAL_ENVELOPE",
        )
    path = min(
        paths,
        key=lambda item: (
            action_priority.get(item["action"], 99),
            item["cost"],
            item["path_id"],
        ),
    )
    proposal = dict(world["final_proposal"])
    proposal["evidence_ids"] = list(path["evidence_ids"])
    candidate = candidate_from_dict(proposal, source_arm="H_EQUAL_ENVELOPE")
    return _with_arm_cost(candidate, world, "H_EQUAL_ENVELOPE")


def raw_upper(world: dict[str, Any]) -> Candidate:
    """Legal raw-information upper bound, separately costed and never fair arm."""

    raw = world.get("raw_upper")
    if raw is None or not raw.get("legally_available", False):
        return _with_arm_cost(_stop(world, "C_RAW_UPPER"), world, "C_RAW_UPPER")
    candidate = candidate_from_dict(raw["proposal"], source_arm="C_RAW_UPPER")
    return _with_arm_cost(candidate, world, "C_RAW_UPPER")


def final_proposal_only(world: dict[str, Any]) -> Candidate:
    """Replay the final proposal without injecting future receipts."""

    proposal = dict(world["final_proposal"])
    t0_ids = {
        evidence_id
        for path in world.get("t0_paths", ())
        if path["allowed"]
        for evidence_id in path["evidence_ids"]
    }
    proposal["evidence_ids"] = [
        evidence_id
        for evidence_id in proposal.get("evidence_ids", ())
        if evidence_id in t0_ids
    ]
    candidate = candidate_from_dict(proposal, source_arm="FINAL_PROPOSAL_ONLY")
    return _with_arm_cost(candidate, world, "FINAL_PROPOSAL_ONLY")


def full_trace(world: dict[str, Any], *, mutation: str = "NONE") -> Candidate:
    """Use actual trace evidence, with explicit operator ablation/reversal."""

    proposal = dict(world["final_proposal"])
    events = list(world.get("full_trace", ()))
    operators = [
        event
        for event in events
        if event["event_type"].startswith("OPERATOR_")
        and event["event_type"] != "OPERATOR_REVERSED"
    ]
    if mutation == "REMOVE_OPERATOR":
        operators = []
    elif mutation == "REVERSE_OPERATOR":
        operators = [
            event
            for event in events
            if event["event_type"] == "OPERATOR_REVERSED"
        ]

    evidence_ids: list[str] = []
    for event in events:
        if event["event_type"] == "EVIDENCE_ISSUED":
            required_operator = event.get("requires_operator")
            active_ids = {operator["operator_id"] for operator in operators}
            if required_operator is None or required_operator in active_ids:
                evidence_ids.append(event["evidence_id"])
        if mutation == "REVERSE_OPERATOR" and event["event_type"] == "OPERATOR_REVERSED":
            evidence_ids.extend(event.get("evidence_ids", ()))

    proposal["evidence_ids"] = evidence_ids
    proposal["operator_ids"] = [
        event["operator_id"] for event in operators
    ]
    if not evidence_ids:
        return _with_arm_cost(_stop(world, f"FULL_TRACE_{mutation}"), world, "FULL_TRACE")
    candidate = candidate_from_dict(proposal, source_arm=f"FULL_TRACE_{mutation}")
    return _with_arm_cost(candidate, world, "FULL_TRACE")


WORKERS = {
    "PUBLIC_BASELINE": public_baseline,
    "C_EQUAL_ACCESS": equal_access_center,
    "H_EQUAL_ENVELOPE": human_equal_envelope,
    "C_RAW_UPPER": raw_upper,
    "FINAL_PROPOSAL_ONLY": final_proposal_only,
}
