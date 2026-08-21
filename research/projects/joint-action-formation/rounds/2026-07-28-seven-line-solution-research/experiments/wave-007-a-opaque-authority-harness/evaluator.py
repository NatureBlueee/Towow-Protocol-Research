#!/usr/bin/env python3
"""Evaluator that rebuilds outcomes from truth, signatures and raw API logs."""

from __future__ import annotations

from typing import Any

from authorities import (
    WITNESS_ALLOWLIST,
    WITNESS_THRESHOLD,
    verify_witness_quorum,
)
from protocol import (
    EvidenceError,
    envelope_sha256,
    normalize_request,
    sha256_value,
    verify_envelope,
)


TERMINAL_STATES = {"UNKNOWN", "REFUSE", "ABSENT"}
OBSERVATION_AUTHORITIES = {
    "HOLDER_AUTHORIZATION": {"LAB-SEEK", "LAB-OFFER", "REGISTRY-W7"},
    "EFFECT_ATTEMPT": {"CONTROLLER-W7"},
    "ANCHOR_COMMIT": {"ANCHOR-W7"},
    "RECIPIENT_ACK": {"SIM-RECIPIENT"},
    "BENEFICIARY_DECISION": {"BENEFICIARY-REVIEWER"},
}


def operational_expected_terminal(world: dict[str, Any]) -> str:
    """Derive a consistency check without using display/case names."""

    if world.get("idempotency_conflict"):
        return "REFUSE"
    if "ABSENT" in (world["holder_seek"], world["holder_offer"]):
        return "ABSENT"
    if (
        world["holder_seek"] != "ACTIVE"
        or world["holder_offer"] != "ACTIVE"
    ):
        return "REFUSE"
    if world["anchor"] != "HEALTHY":
        return "UNKNOWN"
    if world["recipient"] != "ACTIVE":
        return "REFUSE"
    if world["beneficiary"] != "ACCEPT":
        return "REFUSE"
    return "ACCEPTED"


def recompute_cost(operation_log: list[dict[str, Any]]) -> dict[str, Any]:
    """Bill what the API log says happened, never a candidate cost field."""

    authority_requests = sum(
        entry.get("operation", "").startswith("REQUEST_")
        for entry in operation_log
    )
    verification_operations = sum(
        entry.get("operation") == "VERIFY_EVIDENCE"
        for entry in operation_log
    )
    response_bytes = sum(
        max(0, int(entry.get("response_bytes", 0)))
        for entry in operation_log
    )
    return {
        "public_input_reads": sum(
            entry.get("operation") == "READ_PUBLIC_REQUEST"
            for entry in operation_log
        ),
        "authority_requests": authority_requests,
        "witness_requests": sum(
            entry.get("operation") == "REQUEST_ANCHOR_WITNESS"
            for entry in operation_log
        ),
        "verification_operations": verification_operations,
        "cache_hits": sum(
            bool(entry.get("cache_hit")) for entry in operation_log
        ),
        "response_bytes": response_bytes,
        "disclosure_units_256b": (response_bytes + 255) // 256,
        "coordination_operations": len(operation_log),
        "non_success_observations": sum(
            entry.get("outcome") in TERMINAL_STATES
            for entry in operation_log
        ),
    }


def _verify_bound(
    evidence: dict[str, Any],
    key: str,
    registry: dict[str, str],
    *,
    issuer: str,
    kind: str,
    request_sha: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    envelope = evidence[key]
    body = verify_envelope(
        envelope,
        registry,
        expected_issuer=issuer,
        expected_kind=kind,
    )
    if body.get("request_sha256") != request_sha:
        raise EvidenceError(f"{key.upper()}_REQUEST_BINDING_MISMATCH")
    return envelope, body


def _validate_full_chain(
    evidence: dict[str, Any],
    registry: dict[str, str],
    request: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    request_sha = sha256_value(request)
    try:
        h1, h1_body = _verify_bound(
            evidence,
            "holder_authorization_1",
            registry,
            issuer="LAB-SEEK",
            kind="HOLDER_AUTHORIZATION",
            request_sha=request_sha,
        )
        h2, h2_body = _verify_bound(
            evidence,
            "holder_authorization_2",
            registry,
            issuer="LAB-OFFER",
            kind="HOLDER_AUTHORIZATION",
            request_sha=request_sha,
        )
        for body in (h1_body, h2_body):
            expected = {
                "operation": request["operation"],
                "purpose": request["purpose"],
                "retention": request["retention"],
                "environment_version": request["environment_version"],
                "status": "AUTHORIZED",
            }
            for key, value in expected.items():
                if body.get(key) != value:
                    raise EvidenceError(f"HOLDER_{key.upper()}_MISMATCH")

        attempt, attempt_body = _verify_bound(
            evidence,
            "attempt",
            registry,
            issuer="CONTROLLER-W7",
            kind="EFFECT_ATTEMPT",
            request_sha=request_sha,
        )
        if attempt_body.get("holder_authorization_sha256") != [
            envelope_sha256(h1),
            envelope_sha256(h2),
        ]:
            raise EvidenceError("ATTEMPT_AUTHORIZATION_LINK_MISMATCH")
        if attempt_body.get("status") != "ATTEMPTED":
            raise EvidenceError("ATTEMPT_STATUS_INVALID")

        delivery, delivery_body = _verify_bound(
            evidence,
            "delivery",
            registry,
            issuer="CONTROLLER-W7",
            kind="DELIVERY_RECEIPT",
            request_sha=request_sha,
        )
        if delivery_body.get("attempt_sha256") != envelope_sha256(attempt):
            raise EvidenceError("DELIVERY_ATTEMPT_LINK_MISMATCH")
        expected_deliveries = {
            ("LAB-SEEK", "route-constraints", "SIM-RECIPIENT"),
            ("LAB-OFFER", "window-capacity", "SIM-RECIPIENT"),
        }
        actual_deliveries = {
            (item.get("origin"), item.get("facet"), item.get("recipient"))
            for item in delivery_body.get("deliveries", [])
            if isinstance(item, dict)
        }
        if actual_deliveries != expected_deliveries:
            raise EvidenceError("DELIVERY_SET_MISMATCH")

        anchor, anchor_body = _verify_bound(
            evidence,
            "anchor",
            registry,
            issuer="ANCHOR-W7",
            kind="ANCHOR_COMMIT",
            request_sha=request_sha,
        )
        delivery_sha = envelope_sha256(delivery)
        if (
            anchor_body.get("delivery_sha256") != delivery_sha
            or anchor_body.get("checkpoint_sha256") != delivery_sha
        ):
            raise EvidenceError("ANCHOR_DELIVERY_LINK_MISMATCH")
        quorum = verify_witness_quorum(
            anchor_body.get("witness_attestations", []),
            registry,
            allowlist=WITNESS_ALLOWLIST,
            threshold=WITNESS_THRESHOLD,
            checkpoint_sha256=anchor_body.get("checkpoint_sha256", ""),
            slot=anchor_body.get("slot", ""),
            branch_sha256=anchor_body.get("branch_sha256", ""),
        )
        if not quorum["quorum"]:
            raise EvidenceError("ANCHOR_UNIQUE_QUORUM_INVALID")

        ack, ack_body = _verify_bound(
            evidence,
            "recipient_ack",
            registry,
            issuer="SIM-RECIPIENT",
            kind="RECIPIENT_ACK",
            request_sha=request_sha,
        )
        if (
            ack_body.get("delivery_sha256") != delivery_sha
            or ack_body.get("anchor_sha256") != envelope_sha256(anchor)
        ):
            raise EvidenceError("RECIPIENT_ACK_LINK_MISMATCH")

        postcondition, post_body = _verify_bound(
            evidence,
            "postcondition",
            registry,
            issuer="SIMULATOR-W7",
            kind="DOMAIN_POSTCONDITION",
            request_sha=request_sha,
        )
        if post_body.get("recipient_ack_sha256") != envelope_sha256(ack):
            raise EvidenceError("POSTCONDITION_ACK_LINK_MISMATCH")
        expected_output = {
            "route_status": "STERILE_ROUTE_FEASIBLE",
            "command": request["command"],
            "environment_version": request["environment_version"],
        }
        if (
            post_body.get("output") != expected_output
            or post_body.get("output_sha256")
            != sha256_value(expected_output)
        ):
            raise EvidenceError("POSTCONDITION_OUTPUT_MISMATCH")

        _, acceptance_body = _verify_bound(
            evidence,
            "beneficiary_acceptance",
            registry,
            issuer="BENEFICIARY-REVIEWER",
            kind="BENEFICIARY_ACCEPTANCE",
            request_sha=request_sha,
        )
        if (
            acceptance_body.get("postcondition_sha256")
            != envelope_sha256(postcondition)
            or acceptance_body.get("accepted_output_sha256")
            != post_body.get("output_sha256")
            or acceptance_body.get("status") != "ACCEPTED"
        ):
            raise EvidenceError("BENEFICIARY_ACCEPTANCE_LINK_MISMATCH")
    except KeyError as error:
        errors.append(f"MISSING_EVIDENCE:{error.args[0]}")
    except EvidenceError as error:
        errors.append(error.code)
    return errors


def _validate_observation(
    evidence: dict[str, Any],
    registry: dict[str, str],
    request_sha: str,
) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    envelope = evidence.get("terminal_observation")
    if envelope is None:
        return None, errors
    try:
        body = verify_envelope(
            envelope,
            registry,
            expected_kind="AUTHORITY_OBSERVATION",
        )
        stage = body.get("stage")
        state = body.get("state")
        if body.get("request_sha256") != request_sha:
            raise EvidenceError("OBSERVATION_REQUEST_BINDING_MISMATCH")
        if state not in TERMINAL_STATES:
            raise EvidenceError("OBSERVATION_STATE_INVALID")
        if envelope.get("issuer") not in OBSERVATION_AUTHORITIES.get(
            stage, set()
        ):
            raise EvidenceError("OBSERVATION_AUTHORITY_INVALID")
        if "beneficiary_acceptance" in evidence:
            raise EvidenceError("OBSERVATION_ACCEPTANCE_CONFLICT")
        return state, errors
    except EvidenceError as error:
        errors.append(error.code)
        return None, errors


def evaluate(
    *,
    public_request: dict[str, Any],
    world_truth: dict[str, Any],
    public_registry: dict[str, str],
    candidate_output: dict[str, Any],
    operation_log: list[dict[str, Any]],
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruct one world; candidate self-reports are intentionally ignored."""

    errors: list[str] = []
    request = normalize_request(public_request)
    request_sha = sha256_value(request)
    evidence = candidate_output.get("evidence", {})
    if not isinstance(evidence, dict):
        evidence = {}
        errors.append("EVIDENCE_NOT_OBJECT")
    if candidate_output.get("request") != request:
        errors.append("CANDIDATE_REQUEST_MISMATCH")
    if candidate_output.get("request_sha256") != request_sha:
        errors.append("CANDIDATE_REQUEST_HASH_MISMATCH")
    if evidence.get("request") != request:
        errors.append("EVIDENCE_REQUEST_MISMATCH")
    if evidence.get("request_sha256") != request_sha:
        errors.append("EVIDENCE_REQUEST_HASH_MISMATCH")

    observation_state, observation_errors = _validate_observation(
        evidence, public_registry, request_sha
    )
    errors.extend(observation_errors)
    accepted = False
    if observation_state is None:
        chain_errors = _validate_full_chain(
            evidence, public_registry, request
        )
        errors.extend(chain_errors)
        accepted = not errors
    actual_terminal = (
        "ACCEPTED"
        if accepted
        else observation_state
        if observation_state is not None and not errors
        else "UNKNOWN"
    )

    expected_terminal = world_truth["expected_terminal"]
    derived_terminal = operational_expected_terminal(world_truth)
    truth_consistent = expected_terminal == derived_terminal
    false_positive = accepted and expected_terminal != "ACCEPTED"
    false_negative = expected_terminal == "ACCEPTED" and not accepted

    before_count = int(before_snapshot["accepted_effect_count"])
    after_count = int(after_snapshot["accepted_effect_count"])
    actual_effect_delta = after_count - before_count
    already_present = request_sha in set(
        before_snapshot["accepted_effect_sha256"]
    )
    expected_effect_delta = (
        0
        if expected_terminal != "ACCEPTED" or already_present
        else 1
    )
    effect_delta_match = actual_effect_delta == expected_effect_delta
    cost = recompute_cost(operation_log)
    net_value = (
        (100 if accepted else 0)
        - cost["coordination_operations"]
        - cost["disclosure_units_256b"]
        - (100 if false_positive else 0)
        - (50 if false_negative else 0)
    )
    ignored_self_report_fields = sorted(
        key
        for key in candidate_output
        if key
        in {
            "accepted",
            "false_positive",
            "false_negative",
            "promotion",
            "net_value",
            "cost",
        }
    )
    return {
        "expected_terminal": expected_terminal,
        "operational_expected_terminal": derived_terminal,
        "truth_consistent": truth_consistent,
        "actual_terminal": actual_terminal,
        "accepted": accepted,
        "evidence_valid": not errors,
        "errors": errors,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "terminal_match": actual_terminal == expected_terminal,
        "actual_effect_delta": actual_effect_delta,
        "expected_effect_delta": expected_effect_delta,
        "effect_delta_match": effect_delta_match,
        "duplicate_effect": already_present and actual_effect_delta > 0,
        "cost": cost,
        "net_task_value": net_value,
        "ignored_self_report_fields": ignored_self_report_fields,
    }
