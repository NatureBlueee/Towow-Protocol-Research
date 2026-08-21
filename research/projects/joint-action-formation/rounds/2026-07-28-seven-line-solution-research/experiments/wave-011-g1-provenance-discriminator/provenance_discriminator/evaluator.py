"""Independent oracle and provenance evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import Candidate


T0_ONLY_INTERVENTIONS = {
    "PUBLIC_BASELINE",
    "T0_LEGAL_EVIDENCE_PATH",
    "FINAL_PROPOSAL_ONLY",
}


@dataclass(frozen=True)
class Evaluation:
    world_id: str
    arm: str
    validity: str
    invalidity_reasons: tuple[str, ...]
    discovered: bool
    response_state: str | None
    event_vector: dict[str, Any]
    counts_as_actual_policy_miss: bool
    l_benchmark: bool
    d_actual: bool
    cost_account: dict[str, float]


def _invalidity_gate(
    candidate: Candidate,
    world: dict[str, Any],
    truth: dict[str, Any],
    *,
    intervention: str,
) -> list[str]:
    """Run before every positive conclusion."""

    reasons: list[str] = []
    if candidate.proposal_id == "NONE":
        return reasons
    if candidate.world_id != world["world_id"]:
        reasons.append("TRUTH_TRANSPLANT")
    if candidate.target != truth["target"]:
        reasons.append("TARGET_DRIFT")
    if candidate.q_version != truth["q_version"]:
        reasons.append("Q_DRIFT")
    if set(candidate.principals) != set(truth["necessary_principals"]):
        reasons.append("NECESSARY_PRINCIPAL_REMOVED")
    if candidate.status != "CANDIDATE_NOT_COMMITMENT":
        reasons.append("G1_STATUS_OVERPROMOTION")

    evidence_truth = truth["evidence_truth"]
    canonical_sources: list[str] = []
    for evidence_id in candidate.evidence_ids:
        evidence = evidence_truth.get(evidence_id)
        if evidence is None:
            reasons.append("UNKNOWN_OR_CROSS_WORLD_EVIDENCE")
            continue
        if evidence["world_binding"] != world["world_id"]:
            reasons.append("TRUTH_TRANSPLANT")
        if evidence["issuer"] != evidence["expected_issuer"]:
            reasons.append("WRONG_AUTHORITY")
        if not evidence["disclosure_allowed"]:
            reasons.append("FORBIDDEN_DISCLOSURE")
        if intervention in T0_ONLY_INTERVENTIONS and evidence["issued_at"] > 0:
            reasons.append("POST_TREATMENT_EVIDENCE")
        if evidence.get("revoked", False):
            reasons.append("REVOKED_EVIDENCE")
        if not evidence.get("supports_qualification", False):
            reasons.append("NON_QUALIFYING_EVIDENCE")
        canonical_sources.append(evidence["canonical_source"])

    if len(set(canonical_sources)) < truth["min_unique_sources"]:
        if candidate.evidence_ids:
            reasons.append("SAME_SOURCE_ALIAS")
        else:
            reasons.append("MISSING_QUALIFICATION_EVIDENCE")
    if not candidate.evidence_ids:
        reasons.append("MISSING_QUALIFICATION_EVIDENCE")
    return sorted(set(reasons))


def _event_vector(
    candidate: Candidate,
    truth: dict[str, Any],
    validity: str,
    *,
    trusted_arm: str,
) -> dict[str, Any]:
    operator_kinds = {
        operator_id: truth.get("operators", {}).get(operator_id)
        for operator_id in candidate.operator_ids
    }
    evidence = [
        truth["evidence_truth"][evidence_id]
        for evidence_id in candidate.evidence_ids
        if evidence_id in truth["evidence_truth"]
    ]
    return {
        "candidate_sources": sorted(
            {
                item["candidate_source"]
                for item in evidence
            }
            or ({trusted_arm} if candidate.proposal_id != "NONE" else set())
        ),
        "fact_existed_at_t0": truth["fact_existed_at_t0"],
        "legal_evidence_path_existed_at_t0": truth["d_actual"],
        "qualification_created": any(
            item["issued_at"] > 0 and item["supports_qualification"]
            for item in evidence
        ),
        "understanding_changed": "UNDERSTANDING" in operator_kinds.values(),
        "terms_changed": "TERMS" in operator_kinds.values(),
        "authority_changed": "AUTHORITY" in operator_kinds.values(),
        "capability_changed": "CAPABILITY" in operator_kinds.values(),
        "claimability_changed": bool(operator_kinds),
        "validity": validity,
    }


def evaluate_candidate(
    candidate: Candidate,
    world: dict[str, Any],
    truth: dict[str, Any],
    *,
    trusted_arm: str,
    intervention: str,
) -> Evaluation:
    reasons = _invalidity_gate(
        candidate,
        world,
        truth,
        intervention=intervention,
    )
    if candidate.proposal_id == "NONE":
        validity = "NON_SUCCESS"
        discovered = False
    elif reasons:
        validity = "INVALID"
        discovered = False
    else:
        validity = "VALID"
        discovered = True
    event_vector = _event_vector(
        candidate,
        truth,
        validity,
        trusted_arm=trusted_arm,
    )
    cost_key = (
        "FULL_TRACE"
        if trusted_arm.startswith("FULL_TRACE")
        or trusted_arm in {"REMOVE_OPERATOR", "REVERSE_OPERATOR"}
        else trusted_arm
    )
    # Cost is reconstructed from the controller fixture, never accepted from
    # the candidate's self-report.
    cost_account = dict(world["arm_costs"].get(cost_key, {}))
    return Evaluation(
        world_id=world["world_id"],
        arm=trusted_arm,
        validity=validity,
        invalidity_reasons=tuple(reasons),
        discovered=discovered,
        response_state=candidate.response_state,
        event_vector=event_vector,
        counts_as_actual_policy_miss=truth["d_actual"] and not discovered,
        l_benchmark=truth["l_benchmark"],
        d_actual=truth["d_actual"],
        cost_account=cost_account,
    )


def summarize(evaluations: list[Evaluation]) -> dict[str, Any]:
    l_denominator = sum(item.l_benchmark for item in evaluations)
    d_denominator = sum(item.d_actual for item in evaluations)
    structural_hits = sum(
        item.l_benchmark and item.discovered for item in evaluations
    )
    actual_hits = sum(item.d_actual and item.discovered for item in evaluations)
    invalid = {
        item.world_id: list(item.invalidity_reasons)
        for item in evaluations
        if item.validity == "INVALID"
    }
    return {
        "L_benchmark": {
            "denominator": l_denominator,
            "discovered": structural_hits,
            "recall": structural_hits / l_denominator if l_denominator else None,
        },
        "D_actual": {
            "denominator": d_denominator,
            "discovered": actual_hits,
            "recall": actual_hits / d_denominator if d_denominator else None,
        },
        "actual_policy_misses": sorted(
            item.world_id
            for item in evaluations
            if item.counts_as_actual_policy_miss
        ),
        "excluded_non_misses": sorted(
            item.world_id
            for item in evaluations
            if item.l_benchmark and not item.d_actual
        ),
        "invalid": invalid,
        "hard_gate_pass": not invalid,
    }
