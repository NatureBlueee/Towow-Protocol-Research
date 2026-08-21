"""Candidate-side relation reconstruction using only the EvidenceGateway."""

from __future__ import annotations

from typing import Any

from public_api import (
    JsonRpcEvidenceGateway,
    OPERATION,
    PURPOSE,
    RETENTION,
    REUSE_OPERATION,
    SHARED_TASK_ID,
    SHARED_TASK_SHA256,
    STEP,
    WORLD_ID,
)


REQUIRED_RELATION_EVIDENCE = [
    "delivery",
    "ack_seek",
    "ack_offer",
    "explain_seek",
    "explain_offer",
    "proposal",
    "auth_seek",
    "auth_offer",
]


def _base_bound(body: dict[str, Any]) -> bool:
    return all(
        [
            body.get("shared_task_id") == SHARED_TASK_ID,
            body.get("shared_task_sha256") == SHARED_TASK_SHA256,
            body.get("world_id") == WORLD_ID,
            body.get("evaluation_step") == STEP,
            body.get("operation") == OPERATION,
            body.get("purpose") == PURPOSE,
            body.get("retention") == RETENTION,
        ]
    )


def _bounded_relation_evidence(
    verified: dict[str, dict[str, Any]],
) -> tuple[bool, list[str], list[dict[str, Any]], str | None]:
    if not all(name in verified for name in REQUIRED_RELATION_EVIDENCE):
        return False, [], [], None
    delivery = verified["delivery"]
    envelopes = verified["_envelopes"]
    expected_envelopes = {
        "delivery": ("TASK_DELIVERY", "CONTROLLER-W7B"),
        "ack_seek": ("TASK_DELIVERY_ACK", "LAB-SEEK"),
        "ack_offer": ("TASK_DELIVERY_ACK", "LAB-OFFER"),
        "explain_seek": ("RELATION_EXPLAIN_BACK", "LAB-SEEK"),
        "explain_offer": ("RELATION_EXPLAIN_BACK", "LAB-OFFER"),
        "proposal": (
            "BOUNDED_RELATION_PROPOSAL",
            "CONTROLLER-W7B",
        ),
        "auth_seek": (
            "BOUNDED_REUSE_AUTHORIZATION",
            "LAB-SEEK",
        ),
        "auth_offer": (
            "BOUNDED_REUSE_AUTHORIZATION",
            "LAB-OFFER",
        ),
    }
    if any(
        envelopes[name].get("kind") != expected_kind
        or envelopes[name].get("issuer") != expected_issuer
        for name, (expected_kind, expected_issuer) in (
            expected_envelopes.items()
        )
    ):
        return False, [], [], None
    if any(
        not _base_bound(verified[name])
        for name in REQUIRED_RELATION_EVIDENCE
    ):
        return False, [], [], None
    if (
        delivery.get("operation") != OPERATION
        or delivery.get("purpose") != PURPOSE
        or delivery.get("retention") != RETENTION
    ):
        return False, [], [], None

    delivery_ref = verified["_refs"]["delivery"]
    ack_bodies = [verified["ack_seek"], verified["ack_offer"]]
    if {item.get("party") for item in ack_bodies} != {
        "LAB-SEEK",
        "LAB-OFFER",
    }:
        return False, [], [], None
    if any(
        item.get("delivery_sha256") != delivery_ref
        or item.get("ack_scope") != "THIS_OPERATION_ONLY"
        for item in ack_bodies
    ):
        return False, [], [], None

    explains = [verified["explain_seek"], verified["explain_offer"]]
    if {item.get("party") for item in explains} != {
        "LAB-SEEK",
        "LAB-OFFER",
    }:
        return False, [], [], None
    if any(
        item.get("understanding")
        != "EXPLICIT_BOUNDED_REUSE_AUTHORIZED"
        or item.get("reuse_operation") != REUSE_OPERATION
        or item.get("bounded_reuse_count") != 1
        for item in explains
    ):
        return False, [], [], None
    relation_ids = {item.get("relation_id") for item in explains}
    if len(relation_ids) != 1 or None in relation_ids:
        return False, [], [], None
    relation_id = next(iter(relation_ids))

    proposal = verified["proposal"]
    proposal_ref = verified["_refs"]["proposal"]
    if (
        proposal.get("relation_id") != relation_id
        or proposal.get("status") != "PROPOSED_NOT_CONSTITUTED"
        or proposal.get("reuse_operation") != REUSE_OPERATION
        or proposal.get("bounded_reuse_count") != 1
    ):
        return False, [], [], None

    auth_names = ["auth_seek", "auth_offer"]
    auth_bodies = [verified[name] for name in auth_names]
    if {item.get("party") for item in auth_bodies} != {
        "LAB-SEEK",
        "LAB-OFFER",
    }:
        return False, [], [], None
    if any(
        item.get("relation_id") != relation_id
        or item.get("proposal_sha256") != proposal_ref
        or item.get("reuse_operation") != REUSE_OPERATION
        or item.get("bounded_reuse_count") != 1
        or item.get("authorized") is not True
        for item in auth_bodies
    ):
        return False, [], [], None
    evidence_refs = [
        verified["_refs"][name]
        for name in REQUIRED_RELATION_EVIDENCE
    ]
    auth_envelopes = [
        verified["_envelopes"][name] for name in auth_names
    ]
    return True, evidence_refs, auth_envelopes, relation_id


def run_candidate(
    gateway: JsonRpcEvidenceGateway,
    *,
    visible_evidence: list[str],
    candidate_label: str,
    self_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verified: dict[str, Any] = {
        "_refs": {},
        "_envelopes": {},
        "_observations": {},
    }
    for name in visible_evidence:
        if name == "withdrawal":
            continue
        returned = gateway.read_evidence(name)
        verified["_observations"][name] = returned["observation"]
        evidence = returned.get("evidence")
        if evidence is None:
            continue
        verification = gateway.verify_evidence(evidence)
        if not verification["valid"]:
            continue
        if returned["observation"] != "PRESENT":
            continue
        verified[name] = verification["body"]
        verified["_refs"][name] = returned["evidence_ref"]
        verified["_envelopes"][name] = evidence

    active, evidence_refs, authorizations, relation_id = (
        _bounded_relation_evidence(verified)
    )
    if active:
        gateway.record_relation_decision(
            "ACTIVE_BOUNDED", evidence_refs
        )
        reuse = gateway.request_reuse(authorizations)
        reuse_verification = gateway.verify_evidence(reuse["evidence"])
        reuse_status = (
            reuse_verification["body"].get("status")
            if reuse_verification["valid"]
            else "INVALID_RESPONSE"
        )
    else:
        observations = set(verified["_observations"].values())
        state = (
            "INACTIVE_REFUSED"
            if "REFUSE" in observations
            else (
                "UNKNOWN_INSUFFICIENT"
                if "UNKNOWN" in observations
                else "INACTIVE_TASK_BOUND"
            )
        )
        gateway.record_relation_decision(state, [])
        reuse_status = "NOT_REQUESTED"

    withdrawal_status = "NOT_OBSERVED"
    if "withdrawal" in visible_evidence:
        withdrawal = gateway.poll_withdrawal()
        evidence = withdrawal.get("evidence")
        if evidence is not None:
            verification = gateway.verify_evidence(evidence)
            if (
                verification["valid"]
                and withdrawal["observation"] == "PRESENT"
                and evidence["kind"] == "RELATION_WITHDRAWAL"
                and evidence["issuer"] in {"LAB-SEEK", "LAB-OFFER"}
                and relation_id is not None
                and _base_bound(verification["body"])
                and verification["body"].get("relation_id")
                == relation_id
                and verification["body"].get("relation_version") == 1
                and verification["body"].get(
                    "effective_after_reuse_count"
                )
                == 1
                and verification["body"].get("status") == "WITHDRAWN"
            ):
                withdrawal_status = "WITHDRAWN"
                gateway.record_relation_decision(
                    "INACTIVE_WITHDRAWN",
                    [withdrawal["evidence_ref"]],
                )
                active = False
            else:
                withdrawal_status = withdrawal["observation"]

    return {
        "schema": "towow.wave007b-candidate-output.v1",
        "opaque_handle": gateway.opaque_handle,
        "candidate_label": candidate_label,
        "relation_active_at_end": active,
        "reuse_status": reuse_status,
        "withdrawal_status": withdrawal_status,
        "self_report": self_report or {},
    }
