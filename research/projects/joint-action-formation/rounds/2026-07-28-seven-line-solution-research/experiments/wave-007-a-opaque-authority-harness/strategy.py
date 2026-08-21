#!/usr/bin/env python3
"""Candidate strategies.

The candidate receives only the RPC facade supplied by ``runner.py``.  It never
receives a case identifier, world state, expected label, authority object, key,
evaluator, or operation log.
"""

from __future__ import annotations

from typing import Any

from protocol import normalize_request, sha256_value


TERMINAL_STATES = {"UNKNOWN", "REFUSE", "ABSENT"}


def _terminal_if_observation(
    api: Any,
    envelope: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any] | None:
    if envelope.get("kind") != "AUTHORITY_OBSERVATION":
        return None
    body = api.verify(envelope)
    if body.get("state") not in TERMINAL_STATES:
        raise ValueError("unsupported authority observation")
    evidence["terminal_observation"] = envelope
    return {
        "schema": "towow.wave007.candidate-output.v1",
        "request": evidence["request"],
        "request_sha256": evidence["request_sha256"],
        "evidence": evidence,
    }


def bounded_reopen(api: Any) -> dict[str, Any]:
    """Request the minimum signed chain needed for a bounded effect."""

    request = normalize_request(api.read_request())
    request_sha = sha256_value(request)
    evidence: dict[str, Any] = {
        "request": request,
        "request_sha256": request_sha,
    }

    authorizations: list[dict[str, Any]] = []
    for index, holder in enumerate(("LAB-SEEK", "LAB-OFFER"), start=1):
        envelope = api.request_holder_authorization(holder, request)
        terminal = _terminal_if_observation(api, envelope, evidence)
        if terminal is not None:
            return terminal
        api.verify(envelope)
        evidence[f"holder_authorization_{index}"] = envelope
        authorizations.append(envelope)

    attempt = api.request_attempt(request, authorizations)
    terminal = _terminal_if_observation(api, attempt, evidence)
    if terminal is not None:
        return terminal
    api.verify(attempt)
    evidence["attempt"] = attempt

    delivery = api.request_delivery(request, attempt)
    terminal = _terminal_if_observation(api, delivery, evidence)
    if terminal is not None:
        return terminal
    api.verify(delivery)
    evidence["delivery"] = delivery

    anchor = api.request_anchor(request, delivery)
    terminal = _terminal_if_observation(api, anchor, evidence)
    if terminal is not None:
        return terminal
    api.verify(anchor)
    evidence["anchor"] = anchor

    ack = api.request_recipient_ack(request, delivery, anchor)
    terminal = _terminal_if_observation(api, ack, evidence)
    if terminal is not None:
        return terminal
    api.verify(ack)
    evidence["recipient_ack"] = ack

    postcondition = api.request_domain_postcondition(request, ack)
    terminal = _terminal_if_observation(api, postcondition, evidence)
    if terminal is not None:
        return terminal
    api.verify(postcondition)
    evidence["postcondition"] = postcondition

    acceptance = api.request_beneficiary_decision(request, postcondition)
    terminal = _terminal_if_observation(api, acceptance, evidence)
    if terminal is not None:
        return terminal
    api.verify(acceptance)
    evidence["beneficiary_acceptance"] = acceptance

    return {
        "schema": "towow.wave007.candidate-output.v1",
        "request": request,
        "request_sha256": request_sha,
        "evidence": evidence,
    }


def bounded_reopen_relabelled(api: Any) -> dict[str, Any]:
    """Same operations under another function label for cost-label mutation."""

    return bounded_reopen(api)
