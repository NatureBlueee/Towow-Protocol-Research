from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .model import Trace, serialize


POSITIVE = "QUALIFIED_CANDIDATE"
T0_INTERVENTIONS = {
    "PUBLIC_BASELINE",
    "T0_LEGAL_EVIDENCE_PATH",
    "FINAL_PROPOSAL_ONLY",
}


def _root_and_source_coverage(oracle: dict[str, Any], trace: Trace) -> tuple[set[str], set[str]]:
    matching = [
        event
        for event in trace.evidence
        if trace.proposal is not None and event.path_id == trace.proposal.path_id
    ]
    return (
        {event.authority_root for event in matching},
        {event.canonical_source for event in matching},
    )


def _compute_state(oracle: dict[str, Any], trace: Trace) -> dict[str, bool]:
    state = deepcopy(oracle["initial"])
    for operator_event in trace.operators:
        spec = next(
            item
            for item in oracle["operators"]
            if item["id"] == operator_event.operator_id
        )
        for key, value in spec.get("effects", {}).items():
            state[key] = (not value) if operator_event.mode == "REVERSED" else value
    roots, sources = _root_and_source_coverage(oracle, trace)
    required_roots = set(oracle["required_authority_roots"])
    evidence_sufficient = required_roots.issubset(roots) and (
        len(sources) >= oracle["required_distinct_sources"]
    )
    if required_roots or oracle["required_distinct_sources"] > 1:
        state["qualified"] = bool(state["qualified"] or evidence_sufficient)
    return state


def legal_evidence_path_existed_at_t0(oracle: dict[str, Any]) -> bool:
    if not oracle["fact_existed_at_t0"]:
        return False
    allowed = [item for item in oracle["t0_responses"] if item["allowed"]]
    if not oracle["required_authority_roots"] and oracle["initial"]["qualified"]:
        return True
    roots = {item["authority_root"] for item in allowed}
    sources = {item["canonical_source"] for item in allowed}
    return set(oracle["required_authority_roots"]).issubset(roots) and (
        len(sources) >= oracle["required_distinct_sources"]
    )


def invalidity_gate(oracle: dict[str, Any], trace: Trace) -> dict[str, Any]:
    failures: list[str] = []
    proposal = trace.proposal
    canonical = oracle["canonical_proposal"]
    if proposal is not None:
        if proposal.target != canonical["target"]:
            failures.append("TARGET_DRIFT")
        if proposal.quality_floor != canonical["quality_floor"]:
            failures.append("QUALITY_FLOOR_DRIFT")
        if set(proposal.necessary_principals) != set(canonical["necessary_principals"]):
            failures.append("NECESSARY_PRINCIPAL_REMOVAL_OR_ADDITION")
        if proposal.path_id != canonical["path_id"]:
            failures.append("WRONG_PATH")
    if any(not item.valid_authority for item in trace.operators):
        failures.append("WRONG_AUTHORITY")
    if any(not item.disclosure_legal for item in trace.operators):
        failures.append("FORBIDDEN_DISCLOSURE")
    if trace.intervention in T0_INTERVENTIONS and any(
        event.observed_at != "t0" or not event.existed_at_t0
        for event in trace.evidence
    ):
        failures.append("POST_TREATMENT_EVIDENCE_IN_T0_ARM")
    roots, sources = _root_and_source_coverage(oracle, trace)
    matching_count = len(
        [
            item
            for item in trace.evidence
            if proposal is not None and item.path_id == proposal.path_id
        ]
    )
    if (
        matching_count >= oracle["required_distinct_sources"]
        and len(sources) < oracle["required_distinct_sources"]
    ):
        failures.append("SAME_SOURCE_ALIAS")
    claimed_roots = Counter(item.authority_root for item in trace.evidence)
    if any(count > 1 for count in claimed_roots.values()) and not set(
        oracle["required_authority_roots"]
    ).issubset(roots):
        failures.append("AUTHORITY_ALIAS_DOES_NOT_SATISFY_ROOT")
    return {"valid": not failures, "failures": sorted(set(failures))}


def evaluate(oracle: dict[str, Any], trace: Trace) -> dict[str, Any]:
    """Independent scorer.

    The invalidity gate is evaluated before any positive eligibility decision.
    The result is a multi-field event vector, not a mutually exclusive
    provenance label.
    """

    gate = invalidity_gate(oracle, trace)
    initial = oracle["initial"]
    final = _compute_state(oracle, trace)
    proposal_matches = (
        trace.proposal is not None
        and trace.proposal.path_id == oracle["canonical_proposal"]["path_id"]
    )
    eligible_positive = bool(
        gate["valid"]
        and proposal_matches
        and oracle["fact_existed_at_t0"]
        and final["qualified"]
        and final["understood"]
        and final["terms_compatible"]
        and final["authority_valid"]
        and final["capability_present"]
        and final["claimable"]
    )
    if not gate["valid"]:
        boundary = "INVALID"
    elif eligible_positive:
        boundary = POSITIVE
    elif trace.refusals:
        boundary = "UNWILLING_TO_DISCLOSE"
    elif not trace.proposal:
        boundary = "UNKNOWN"
    else:
        boundary = "DEFER"
    path_id = oracle["canonical_proposal"]["path_id"]
    l_benchmark = [path_id] if oracle["fact_existed_at_t0"] else []
    d_actual = [path_id] if legal_evidence_path_existed_at_t0(oracle) else []
    vector = {
        "world_id": trace.world_id,
        "arm": trace.arm,
        "intervention": trace.intervention,
        "candidate_sources": sorted(set(trace.candidate_sources)),
        "fact_existed_at_t0": oracle["fact_existed_at_t0"],
        "legal_evidence_path_existed_at_t0": bool(d_actual),
        "qualification_created": (not initial["qualified"] and final["qualified"]),
        "understanding_changed": initial["understood"] != final["understood"],
        "terms_changed": initial["terms_compatible"] != final["terms_compatible"],
        "authority_changed": initial["authority_valid"] != final["authority_valid"],
        "capability_changed": initial["capability_present"]
        != final["capability_present"],
        "claimability_changed": initial["claimable"] != final["claimable"],
        "validity": gate,
        "eligible_positive": eligible_positive,
        "boundary": boundary,
        "l_benchmark": l_benchmark,
        "d_actual": d_actual,
        "observed_evidence": [serialize(item) for item in trace.evidence],
        "operators": [serialize(item) for item in trace.operators],
        "refusals": deepcopy(trace.refusals),
        "cost": serialize(trace.cost),
    }
    return vector

