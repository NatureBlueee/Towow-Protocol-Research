#!/usr/bin/env python3
"""Bounded local controller executor for authorized projection routes.

The executor deliberately treats holder receipts as immutable authorizations,
not as proof that a route has already run.  Every first attempt becomes one
hash-chained state event and receives an execution receipt.  Exact retries are
idempotent replays and do not mutate state.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


class ExecutionError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def new_state(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "towow.controller-state.v1",
        "controller_id": contract["controller_id"],
        "contract_sha256": sha256_value(contract),
        "world_id": contract["world_id"],
        "evaluation_step": contract["evaluation_step"],
        "last_event_hash": None,
        "disclosure_units_used": 0,
        "revoked_holder_receipts": [],
        "delivery_store": [],
        "recipient_stores": {},
        "pending_transactions": [],
        "events": [],
    }


def state_hash(state: dict[str, Any]) -> str:
    return sha256_value(state)


def _trusted_by_hash(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["sha256"]: item
        for item in contract.get("trusted_holder_receipts", [])
    }


def _reject(code: str, message: str, **details: Any) -> None:
    raise ExecutionError(code, message, details)


def _validate_state_contract(
    contract: dict[str, Any], state: dict[str, Any]
) -> None:
    if state.get("contract_sha256") != sha256_value(contract):
        _reject(
            "CONTRACT_STATE_MISMATCH",
            "The persistent state is bound to a different contract.",
        )
    if state.get("controller_id") != contract.get("controller_id"):
        _reject("CONTROLLER_STATE_MISMATCH", "Controller identity changed.")
    if state.get("world_id") != contract.get("world_id"):
        _reject("WORLD_STATE_MISMATCH", "State and contract world differ.")
    if state.get("evaluation_step") != contract.get("evaluation_step"):
        _reject(
            "WORLD_STEP_STATE_MISMATCH",
            "State and contract evaluation step differ.",
        )


def _validate_request_coordinates(
    contract: dict[str, Any], request: dict[str, Any]
) -> None:
    if request.get("world_id") != contract.get("world_id"):
        _reject(
            "WORLD_MISMATCH",
            "Request world does not match the frozen controller contract.",
        )
    if request.get("evaluation_step") != contract.get("evaluation_step"):
        _reject(
            "WORLD_STEP_MISMATCH",
            "Request evaluation step does not match the frozen contract.",
        )


def _validate_holder_envelope(
    envelope: dict[str, Any],
    contract: dict[str, Any],
    state: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    payload = envelope.get("payload")
    declared_hash = envelope.get("declared_sha256")
    if not isinstance(payload, dict) or not isinstance(declared_hash, str):
        _reject(
            "HOLDER_RECEIPT_MALFORMED",
            "A holder authorization must contain payload and declared_sha256.",
        )

    actual_hash = sha256_value(payload)
    if declared_hash != actual_hash:
        _reject(
            "HOLDER_RECEIPT_HASH_MISMATCH",
            "Declared holder receipt hash does not match its canonical payload.",
            declared_sha256=declared_hash,
            actual_sha256=actual_hash,
        )

    trusted = _trusted_by_hash(contract).get(actual_hash)
    if trusted is None:
        _reject(
            "UNTRUSTED_HOLDER_RECEIPT",
            "Holder receipt hash is not frozen in this contract.",
            actual_sha256=actual_hash,
        )
    if payload.get("receipt_id") != trusted.get("receipt_id"):
        _reject(
            "TRUSTED_RECEIPT_ID_MISMATCH",
            "Trusted hash is paired with a different receipt id.",
        )
    if payload.get("issuer") != trusted.get("issuer"):
        _reject(
            "TRUSTED_RECEIPT_ISSUER_MISMATCH",
            "Trusted hash is paired with a different issuer.",
        )
    trusted_source_hash = trusted.get("source_file_sha256")
    if trusted_source_hash is not None and payload.get(
        "source_file_sha256"
    ) != trusted_source_hash:
        _reject(
            "SOURCE_RECEIPT_BINDING_MISMATCH",
            "Normalized authorization is not bound to the frozen source receipt.",
        )
    if payload.get("world_id") != contract.get("world_id"):
        _reject("WORLD_MISMATCH", "Holder receipt belongs to another world.")
    if payload.get("evaluation_step") != contract.get("evaluation_step"):
        _reject(
            "WORLD_STEP_MISMATCH",
            "Holder receipt belongs to another evaluation step.",
        )
    step = contract["evaluation_step"]
    if not (
        payload.get("valid_from_step", step) <= step
        <= payload.get("valid_through_step", step)
    ):
        _reject(
            "WORLD_STEP_MISMATCH",
            "Holder receipt is not valid at the frozen world step.",
        )
    if payload.get("revoked") is True or actual_hash in set(
        state.get("revoked_holder_receipts", [])
    ):
        _reject(
            "AUTHORIZATION_REVOKED",
            "Holder authorization has been revoked.",
            receipt_sha256=actual_hash,
        )
    if payload.get("status") != "AUTHORIZED":
        _reject(
            "AUTHORIZATION_NOT_ACTIVE",
            "Holder receipt is not an active authorization.",
        )
    return payload, actual_hash


def _require_exact(
    actual: Any,
    expected: Any,
    code: str,
    field: str,
) -> None:
    if actual != expected:
        _reject(
            code,
            f"Requested {field} is not authorized.",
            requested=actual,
            authorized=expected,
        )


def _validate_projection(
    requested: dict[str, Any], authorized: dict[str, Any]
) -> None:
    _require_exact(
        requested.get("direction"),
        authorized.get("direction"),
        "DIRECTION_MISMATCH",
        "direction",
    )
    _require_exact(
        requested.get("facet"),
        authorized.get("facet"),
        "FACET_MISMATCH",
        "facet",
    )
    _require_exact(
        requested.get("compatibility_key"),
        authorized.get("compatibility_key"),
        "COMPATIBILITY_KEY_MISMATCH",
        "compatibility_key",
    )


def _validate_policy(
    requested: dict[str, Any],
    authorized: dict[str, Any],
    *,
    depth: int,
) -> None:
    _require_exact(
        requested.get("recipient"),
        authorized.get("recipient"),
        "RECIPIENT_POLICY_DENIED",
        "recipient",
    )
    _require_exact(
        requested.get("purpose"),
        authorized.get("purpose"),
        "PURPOSE_POLICY_DENIED",
        "purpose",
    )
    _require_exact(
        requested.get("retention"),
        authorized.get("retention"),
        "RETENTION_POLICY_DENIED",
        "retention",
    )
    if requested.get("depth") != depth or depth > authorized.get("max_depth", -1):
        _reject(
            "DEPTH_POLICY_DENIED",
            "Requested route depth exceeds or misstates authorization.",
            requested=requested.get("depth"),
            required=depth,
            maximum=authorized.get("max_depth"),
        )


def _event_id(
    controller_id: str, request_hash: str, label: str, ordinal: int
) -> str:
    digest = sha256_value(
        {
            "controller_id": controller_id,
            "request_hash": request_hash,
            "label": label,
            "ordinal": ordinal,
        }
    )
    return f"{label}-{digest[:24]}"


def _direct_projection(
    contract: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    request_hash: str,
) -> tuple[dict[str, Any], int]:
    if len(request.get("authorizations", [])) != 1:
        _reject(
            "AUTHORIZATION_COUNT_INVALID",
            "Direct projection requires exactly one holder authorization.",
        )
    holder, holder_hash = _validate_holder_envelope(
        request["authorizations"][0], contract, state
    )
    if holder.get("authorization_type") != "PROJECTION_ROUTE":
        _reject(
            "AUTHORIZATION_TYPE_MISMATCH",
            "Direct projection requires PROJECTION_ROUTE authorization.",
        )

    route = request.get("route", {})
    _validate_projection(route.get("projection", {}), holder.get("projection", {}))
    _validate_policy(route, holder.get("policy", {}), depth=0)
    units = route.get("budget_units")
    _require_exact(
        units,
        holder.get("policy", {}).get("budget_units"),
        "DISCLOSURE_BUDGET_MISMATCH",
        "budget_units",
    )

    disclosure = {
        "event_id": _event_id(
            contract["controller_id"], request_hash, "disclosure", 0
        ),
        "status": "PERFORMED",
        "from": holder["issuer"],
        "to": route["recipient"],
        "purpose": route["purpose"],
        "retention": route["retention"],
        "depth": 0,
        "projection": copy.deepcopy(holder["projection"]),
        "source_holder_receipt_sha256": holder_hash,
    }
    return (
        {
            "status": "EXECUTED",
            "route_type": "DIRECT_PROJECTION",
            "disclosures": [disclosure],
            "derived_authorizations": [],
            "reciprocal_exchange": None,
            "relation_status": "NOT_ESTABLISHED",
            "commitment_status": "NOT_CREATED",
            "authority_status": "NOT_INFERRED",
        },
        units,
    )


def _derived_onward(
    contract: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    request_hash: str,
) -> tuple[dict[str, Any], int]:
    if len(request.get("authorizations", [])) != 1:
        _reject(
            "AUTHORIZATION_COUNT_INVALID",
            "Derived onward route requires one source holder authorization.",
        )
    holder, holder_hash = _validate_holder_envelope(
        request["authorizations"][0], contract, state
    )
    if holder.get("authorization_type") != "PROJECTION_ROUTE":
        _reject(
            "AUTHORIZATION_TYPE_MISMATCH",
            "Derived onward route requires PROJECTION_ROUTE authorization.",
        )

    route = request.get("route", {})
    _validate_projection(route.get("projection", {}), holder.get("projection", {}))
    hops = route.get("hops", [])
    if len(hops) != 2:
        _reject(
            "ONWARD_ROUTE_SHAPE_INVALID",
            "Derived onward route must contain exactly two hops.",
        )
    source_policy = holder.get("policy", {})
    if source_policy.get("onward_allowed") is not True:
        _reject("ONWARD_POLICY_DENIED", "Source policy forbids onward disclosure.")
    _validate_policy(hops[0], source_policy, depth=0)
    onward_policy = source_policy.get("onward_policy", {})
    _validate_policy(hops[1], onward_policy, depth=1)
    if onward_policy.get("source_recipient") != hops[0].get("recipient"):
        _reject(
            "ONWARD_POLICY_DENIED",
            "The first recipient is not authorized to derive the onward route.",
        )

    units = sum(hop.get("budget_units", 0) for hop in hops)
    expected_units = source_policy.get("budget_units", 0) + onward_policy.get(
        "budget_units", 0
    )
    _require_exact(
        units,
        expected_units,
        "DISCLOSURE_BUDGET_MISMATCH",
        "total budget_units",
    )

    first_event = _event_id(
        contract["controller_id"], request_hash, "disclosure", 0
    )
    first = {
        "event_id": first_event,
        "status": "PERFORMED",
        "from": holder["issuer"],
        "to": hops[0]["recipient"],
        "purpose": hops[0]["purpose"],
        "retention": hops[0]["retention"],
        "depth": 0,
        "projection": copy.deepcopy(holder["projection"]),
        "source_holder_receipt_sha256": holder_hash,
    }
    derived_body = {
        "schema": "towow.derived-onward-authorization.v1",
        "issuer": contract["controller_id"],
        "source_holder_receipt_sha256": holder_hash,
        "parent_disclosure_event_id": first_event,
        "from": hops[0]["recipient"],
        "to": hops[1]["recipient"],
        "purpose": hops[1]["purpose"],
        "retention": hops[1]["retention"],
        "depth": 1,
        "projection": copy.deepcopy(holder["projection"]),
    }
    derived = {
        **derived_body,
        "receipt_sha256": sha256_value(derived_body),
    }
    second = {
        "event_id": _event_id(
            contract["controller_id"], request_hash, "disclosure", 1
        ),
        "status": "PERFORMED",
        "from": hops[0]["recipient"],
        "to": hops[1]["recipient"],
        "purpose": hops[1]["purpose"],
        "retention": hops[1]["retention"],
        "depth": 1,
        "projection": copy.deepcopy(holder["projection"]),
        "derived_authorization_sha256": derived["receipt_sha256"],
    }
    return (
        {
            "status": "EXECUTED",
            "route_type": "DERIVED_ONWARD",
            "disclosures": [first, second],
            "derived_authorizations": [derived],
            "reciprocal_exchange": None,
            "relation_status": "NOT_ESTABLISHED",
            "commitment_status": "NOT_CREATED",
            "authority_status": "NOT_INFERRED",
        },
        units,
    )


def _reciprocal_exchange(
    contract: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    request_hash: str,
) -> tuple[dict[str, Any], int]:
    if len(request.get("authorizations", [])) != 2:
        _reject(
            "AUTHORIZATION_COUNT_INVALID",
            "Reciprocal exchange requires two holder authorizations.",
        )
    validated = [
        _validate_holder_envelope(envelope, contract, state)
        for envelope in request["authorizations"]
    ]
    holders = [item[0] for item in validated]
    holder_hashes = [item[1] for item in validated]
    if any(
        holder.get("authorization_type") != "RECIPROCAL_OFFER"
        for holder in holders
    ):
        _reject(
            "AUTHORIZATION_TYPE_MISMATCH",
            "Both sides must provide RECIPROCAL_OFFER authorization.",
        )

    route = request.get("route", {})
    sides = route.get("sides", [])
    if len(sides) != 2:
        _reject(
            "RECIPROCAL_ROUTE_SHAPE_INVALID",
            "Reciprocal exchange must declare two sides.",
        )
    by_id = {holder["receipt_id"]: holder for holder in holders}
    hash_by_id = {
        holder["receipt_id"]: receipt_hash
        for holder, receipt_hash in validated
    }
    if set(side.get("receipt_id") for side in sides) != set(by_id):
        _reject(
            "COUNTERPARTY_MISMATCH",
            "Requested sides do not match the two trusted holder receipts.",
        )

    ordered_holders = [by_id[side["receipt_id"]] for side in sides]
    delivery_mode = route.get("delivery_mode", "CENTRAL_COLLECTION")
    if delivery_mode not in {
        "CENTRAL_COLLECTION",
        "COUNTERPARTY_EXCHANGE",
    }:
        _reject(
            "RECIPROCAL_DELIVERY_MODE_INVALID",
            "Reciprocal route uses an unsupported delivery mode.",
        )
    delivery_routes: list[dict[str, Any]] = []
    for side, holder in zip(sides, ordered_holders):
        _validate_projection(side, holder.get("projection", {}))
        requested_counterparty = side.get("counterparty")
        other = ordered_holders[1] if holder is ordered_holders[0] else ordered_holders[0]
        _require_exact(
            requested_counterparty,
            other.get("issuer"),
            "COUNTERPARTY_MISMATCH",
            "counterparty",
        )
        allowed = holder.get("counterparty_contract", {}).get(
            "allowed_counterparties", []
        )
        if other.get("issuer") not in allowed:
            _reject(
                "COUNTERPARTY_MISMATCH",
                "Other holder is not admitted by the reciprocal contract.",
            )
        delivery_route = (
            side.get("delivery")
            if delivery_mode == "COUNTERPARTY_EXCHANGE"
            else route
        )
        if not isinstance(delivery_route, dict):
            _reject(
                "RECIPROCAL_ROUTE_SHAPE_INVALID",
                "Counterparty exchange requires one delivery route per side.",
            )
        if (
            delivery_mode == "COUNTERPARTY_EXCHANGE"
            and delivery_route.get("recipient") != other.get("issuer")
        ):
            _reject(
                "COUNTERPARTY_MISMATCH",
                "Counterparty exchange must deliver each side to the other holder.",
            )
        _validate_policy(
            delivery_route,
            holder.get("policy", {}),
            depth=0,
        )
        delivery_routes.append(delivery_route)

    directions = {holder["projection"]["direction"] for holder in ordered_holders}
    if directions != {"SEEK", "OFFER"}:
        _reject(
            "DIRECTION_MISMATCH",
            "Reciprocal exchange requires one SEEK and one OFFER.",
        )
    keys = {
        holder["projection"]["compatibility_key"] for holder in ordered_holders
    }
    if len(keys) != 1:
        _reject(
            "COMPATIBILITY_KEY_MISMATCH",
            "Reciprocal sides use different compatibility keys.",
        )
    facet_pair = sorted(
        holder["projection"]["facet"] for holder in ordered_holders
    )
    allowed_pairs = [
        sorted(pair) for pair in contract.get("compatible_facet_pairs", [])
    ]
    if facet_pair not in allowed_pairs:
        _reject(
            "FACET_MISMATCH",
            "Reciprocal facets are not a frozen compatible pair.",
        )

    units_each = route.get("budget_units_each")
    for holder in ordered_holders:
        _require_exact(
            units_each,
            holder.get("policy", {}).get("budget_units"),
            "DISCLOSURE_BUDGET_MISMATCH",
            "budget_units_each",
        )
    units = units_each * 2

    disclosures = []
    for index, holder in enumerate(ordered_holders):
        other = ordered_holders[1 - index]
        delivery_route = delivery_routes[index]
        disclosures.append(
            {
                "event_id": _event_id(
                    contract["controller_id"],
                    request_hash,
                    "reciprocal-disclosure",
                    index,
                ),
                "status": "PERFORMED",
                "from": holder["issuer"],
                "to": delivery_route["recipient"],
                "purpose": delivery_route["purpose"],
                "retention": delivery_route["retention"],
                "depth": 0,
                "counterparty": other["issuer"],
                "projection": copy.deepcopy(holder["projection"]),
                "source_holder_receipt_sha256": hash_by_id[holder["receipt_id"]],
            }
        )
    exchange_body = {
        "schema": "towow.reciprocal-exchange.v1",
        "exchange_id": _event_id(
            contract["controller_id"], request_hash, "reciprocal-exchange", 0
        ),
        "status": "PERFORMED",
        "controller_id": contract["controller_id"],
        "participant_issuers": sorted(holder["issuer"] for holder in holders),
        "holder_receipt_sha256": sorted(holder_hashes),
        "compatibility_key": next(iter(keys)),
        "disclosure_event_ids": [item["event_id"] for item in disclosures],
        "delivery_mode": delivery_mode,
        "scope": (
            "RECIPROCAL_COUNTERPARTY_PROJECTION_EXCHANGE"
            if delivery_mode == "COUNTERPARTY_EXCHANGE"
            else "CENTRAL_RECIPROCAL_PROJECTION_COLLECTION"
        ),
    }
    exchange = {
        **exchange_body,
        "receipt_sha256": sha256_value(exchange_body),
    }
    return (
        {
            "status": "EXECUTED",
            "route_type": "RECIPROCAL_EXCHANGE",
            "disclosures": disclosures,
            "derived_authorizations": [],
            "reciprocal_exchange": exchange,
            "relation_status": "NOT_ESTABLISHED",
            "commitment_status": "NOT_CREATED",
            "authority_status": "NOT_INFERRED",
        },
        units,
    )


def _dispatch(
    contract: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    request_hash: str,
) -> tuple[dict[str, Any], int]:
    _validate_state_contract(contract, state)
    _validate_request_coordinates(contract, request)
    route_type = request.get("route_type")
    if route_type == "DIRECT_PROJECTION":
        return _direct_projection(contract, request, state, request_hash)
    if route_type == "DERIVED_ONWARD":
        return _derived_onward(contract, request, state, request_hash)
    if route_type == "RECIPROCAL_EXCHANGE":
        return _reciprocal_exchange(contract, request, state, request_hash)
    _reject("ROUTE_TYPE_UNSUPPORTED", "Controller does not support this route type.")


def _prior_attempt(
    state: dict[str, Any], idempotency_key: str, request_hash: str
) -> dict[str, Any] | None:
    for event in state.get("events", []):
        if (
            event.get("idempotency_key") == idempotency_key
            and event.get("request_sha256") == request_hash
        ):
            return event
    return None


def _key_seen_with_other_request(
    state: dict[str, Any], idempotency_key: str, request_hash: str
) -> bool:
    return any(
        event.get("idempotency_key") == idempotency_key
        and event.get("request_sha256") != request_hash
        for event in state.get("events", [])
    ) or any(
        pending.get("idempotency_key") == idempotency_key
        and pending.get("request_sha256") != request_hash
        for pending in state.get("pending_transactions", [])
    )


def _authorization_bindings(request: dict[str, Any]) -> tuple[str, str]:
    envelopes = request.get("authorizations", [])
    policies = []
    for envelope in envelopes:
        payload = envelope.get("payload", {}) if isinstance(envelope, dict) else {}
        policies.append(
            {
                "receipt_id": payload.get("receipt_id"),
                "issuer": payload.get("issuer"),
                "policy": payload.get("policy"),
                "counterparty_contract": payload.get("counterparty_contract"),
            }
        )
    return sha256_value(envelopes), sha256_value(policies)


def _issue_and_append_audit_event(
    contract: dict[str, Any],
    state: dict[str, Any],
    *,
    idempotency_key: str,
    request_hash: str,
    prior_state_sha256: str,
    prior_event_hash: str | None,
    outcome: dict[str, Any],
    authorization_bundle_sha256: str,
    policy_snapshot_sha256: str,
    authoritative_event_sha256: str | None,
    authoritative_state_root: str | None,
    readback_sha256: str | None,
) -> dict[str, Any]:
    sequence = len(state.get("events", [])) + 1
    outcome_hash = sha256_value(outcome)
    receipt_body = {
        "schema": "towow.controller-execution-receipt.v1",
        "issuer": contract.get("controller_id"),
        "sequence": sequence,
        "idempotency_key": idempotency_key,
        "decision": outcome["status"],
        "code": outcome.get("code", "EXECUTED"),
        "contract_sha256": sha256_value(contract),
        "input_sha256": request_hash,
        "trusted_holder_envelopes_sha256": authorization_bundle_sha256,
        "policy_snapshot_sha256": policy_snapshot_sha256,
        "prior_state_sha256": prior_state_sha256,
        "prior_event_sha256": prior_event_hash,
        "authoritative_event_sha256": authoritative_event_sha256,
        "authoritative_state_root": authoritative_state_root,
        "readback_sha256": readback_sha256,
        "output_sha256": outcome_hash,
    }
    execution_receipt = {
        **receipt_body,
        "receipt_sha256": sha256_value(receipt_body),
    }
    event_body = {
        "sequence": sequence,
        "idempotency_key": idempotency_key,
        "request_sha256": request_hash,
        "prior_event_sha256": prior_event_hash,
        "outcome": outcome,
        "execution_receipt": execution_receipt,
    }
    event = {**event_body, "event_sha256": sha256_value(event_body)}
    state["events"].append(event)
    state["last_event_hash"] = event["event_sha256"]
    return execution_receipt


def _record_rejection(
    contract: dict[str, Any],
    request: dict[str, Any],
    state: dict[str, Any],
    *,
    idempotency_key: str,
    request_hash: str,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    authorization_hash, policy_hash = _authorization_bindings(request)
    rejection_body = {
        "schema": "towow.controller-rejection.v1",
        "controller_id": contract.get("controller_id"),
        "idempotency_key": idempotency_key,
        "contract_sha256": sha256_value(contract),
        "input_sha256": request_hash,
        "trusted_holder_envelopes_sha256": authorization_hash,
        "policy_snapshot_sha256": policy_hash,
        "unchanged_state_sha256": state_hash(state),
        "outcome_sha256": sha256_value(outcome),
    }
    return {
        "replay": "NOT_APPLICABLE_REJECTED",
        "state_changed": False,
        "outcome": copy.deepcopy(outcome),
        "execution_receipt": None,
        "rejection_evidence": {
            **rejection_body,
            "rejection_sha256": sha256_value(rejection_body),
        },
    }


def _authority_event(
    contract: dict[str, Any],
    request: dict[str, Any],
    request_hash: str,
    outcome: dict[str, Any],
    previous_store_root: str,
) -> dict[str, Any]:
    body = {
        "schema": "towow.recipient-delivery-event.v1",
        "transaction_id": _event_id(
            contract["controller_id"], request_hash, "delivery-transaction", 0
        ),
        "idempotency_key": request["idempotency_key"],
        "request_sha256": request_hash,
        "route_type": request["route_type"],
        "atomic": True,
        "previous_store_root": previous_store_root,
        "deliveries": copy.deepcopy(outcome["disclosures"]),
        "derived_authorizations": copy.deepcopy(
            outcome.get("derived_authorizations", [])
        ),
        "reciprocal_exchange": copy.deepcopy(
            outcome.get("reciprocal_exchange")
        ),
    }
    return {**body, "event_sha256": sha256_value(body)}


def delivery_store_root(state: dict[str, Any]) -> str:
    return sha256_value(
        {
            "event_log": state.get("delivery_store", []),
            "recipient_stores": state.get("recipient_stores", {}),
        }
    )


def _readback_transaction(
    state: dict[str, Any], authoritative_event_sha256: str
) -> dict[str, Any]:
    matches = [
        item
        for item in state.get("delivery_store", [])
        if item.get("event_sha256") == authoritative_event_sha256
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "authoritative readback did not find exactly one delivery transaction"
        )
    event = matches[0]
    body = {key: value for key, value in event.items() if key != "event_sha256"}
    if sha256_value(body) != authoritative_event_sha256:
        raise RuntimeError("authoritative delivery event hash failed readback")
    deliveries = event.get("deliveries", [])
    if not deliveries or any(item.get("status") != "PERFORMED" for item in deliveries):
        raise RuntimeError("authoritative readback postcondition is incomplete")
    if event.get("route_type") in {"DERIVED_ONWARD", "RECIPROCAL_EXCHANGE"}:
        if len(deliveries) != 2 or event.get("atomic") is not True:
            raise RuntimeError("multi-party transaction was not committed atomically")
    observed = []
    for delivery in deliveries:
        recipient_records = state.get("recipient_stores", {}).get(
            delivery["to"], []
        )
        matched = [
            record
            for record in recipient_records
            if record.get("authoritative_event_sha256")
            == authoritative_event_sha256
            and record.get("delivery", {}).get("event_id")
            == delivery.get("event_id")
        ]
        if len(matched) != 1 or matched[0].get("delivery") != delivery:
            raise RuntimeError(
                "recipient-side store readback did not reproduce a delivery"
            )
        observed.append(
            {
                "recipient": delivery["to"],
                "delivery_event_id": delivery["event_id"],
                "delivery_sha256": sha256_value(delivery),
            }
        )
    return {
        "schema": "towow.recipient-delivery-readback.v1",
        "transaction_id": event["transaction_id"],
        "authoritative_event_sha256": authoritative_event_sha256,
        "authoritative_state_root": delivery_store_root(state),
        "delivery_count": len(deliveries),
        "delivery_event_ids": [item["event_id"] for item in deliveries],
        "recipient_store_observations": observed,
        "all_postconditions_observed": True,
    }


def _find_pending(
    state: dict[str, Any], idempotency_key: str, request_hash: str
) -> dict[str, Any] | None:
    for pending in state.get("pending_transactions", []):
        if (
            pending.get("idempotency_key") == idempotency_key
            and pending.get("request_sha256") == request_hash
        ):
            return pending
    return None


def _validate_pending_records(state: dict[str, Any]) -> None:
    for pending in state.get("pending_transactions", []):
        declared = pending.get("pending_sha256")
        body = {
            key: value
            for key, value in pending.items()
            if key != "pending_sha256"
        }
        if not isinstance(declared, str) or sha256_value(body) != declared:
            _reject(
                "PENDING_RECORD_INTEGRITY_INVALID",
                "A recoverable pending transaction failed its integrity check.",
            )


def _historical_delivery_root(
    state: dict[str, Any], target_event_sha256: str
) -> str:
    event_log: list[dict[str, Any]] = []
    recipient_stores: dict[str, list[dict[str, Any]]] = {}
    for event in state.get("delivery_store", []):
        event_log.append(copy.deepcopy(event))
        for delivery in event.get("deliveries", []):
            matches = [
                record
                for record in state.get("recipient_stores", {}).get(
                    delivery.get("to"), []
                )
                if record.get("authoritative_event_sha256")
                == event.get("event_sha256")
                and record.get("delivery", {}).get("event_id")
                == delivery.get("event_id")
            ]
            if len(matches) != 1 or matches[0].get("delivery") != delivery:
                _reject(
                    "RECIPIENT_STORE_INTEGRITY_INVALID",
                    "Recipient store does not reproduce an authoritative delivery.",
                )
            recipient_stores.setdefault(delivery["to"], []).append(
                copy.deepcopy(matches[0])
            )
        if event.get("event_sha256") == target_event_sha256:
            return sha256_value(
                {
                    "event_log": event_log,
                    "recipient_stores": recipient_stores,
                }
            )
    _reject(
        "AUTHORITATIVE_EVENT_MISSING",
        "Execution receipt points to a missing authoritative delivery event.",
    )


def _validate_persistent_integrity(
    contract: dict[str, Any], state: dict[str, Any]
) -> None:
    _validate_state_contract(contract, state)
    _validate_pending_records(state)

    known_authoritative_events: set[str] = set()
    previous_root = sha256_value({"event_log": [], "recipient_stores": {}})
    for authority_event in state.get("delivery_store", []):
        declared = authority_event.get("event_sha256")
        body = {
            key: value
            for key, value in authority_event.items()
            if key != "event_sha256"
        }
        if not isinstance(declared, str) or sha256_value(body) != declared:
            _reject(
                "AUTHORITATIVE_EVENT_INTEGRITY_INVALID",
                "Authoritative delivery event hash is invalid.",
            )
        if authority_event.get("previous_store_root") != previous_root:
            _reject(
                "AUTHORITATIVE_STORE_CHAIN_INVALID",
                "Authoritative delivery-store root chain is invalid.",
            )
        try:
            _readback_transaction(state, declared)
        except RuntimeError as exc:
            _reject(
                "RECIPIENT_STORE_INTEGRITY_INVALID",
                str(exc),
            )
        previous_root = _historical_delivery_root(state, declared)
        known_authoritative_events.add(declared)

    for records in state.get("recipient_stores", {}).values():
        for record in records:
            if record.get("authoritative_event_sha256") not in (
                known_authoritative_events
            ):
                _reject(
                    "RECIPIENT_STORE_INTEGRITY_INVALID",
                    "Recipient store contains an unbound delivery record.",
                )

    prior_event_sha256 = None
    for event in state.get("events", []):
        event_body = {
            key: value for key, value in event.items() if key != "event_sha256"
        }
        if (
            event.get("prior_event_sha256") != prior_event_sha256
            or sha256_value(event_body) != event.get("event_sha256")
        ):
            _reject(
                "AUDIT_CHAIN_INTEGRITY_INVALID",
                "Controller audit event chain is invalid.",
            )
        receipt = event.get("execution_receipt", {})
        receipt_body = {
            key: value
            for key, value in receipt.items()
            if key != "receipt_sha256"
        }
        outcome = event.get("outcome", {})
        if (
            sha256_value(receipt_body) != receipt.get("receipt_sha256")
            or receipt.get("contract_sha256") != sha256_value(contract)
            or receipt.get("input_sha256") != event.get("request_sha256")
            or receipt.get("output_sha256") != sha256_value(outcome)
        ):
            _reject(
                "EXECUTION_RECEIPT_INTEGRITY_INVALID",
                "Controller execution receipt failed its binding checks.",
            )
        evidence = outcome.get("authority_evidence", {})
        stored_readback = evidence.get("readback", {})
        authority_hash = receipt.get("authoritative_event_sha256")
        if (
            authority_hash not in known_authoritative_events
            or evidence.get("recipient_delivery_event_sha256")
            != authority_hash
            or evidence.get("readback_sha256")
            != sha256_value(stored_readback)
            or receipt.get("readback_sha256")
            != evidence.get("readback_sha256")
            or receipt.get("authoritative_state_root")
            != evidence.get("authoritative_state_root")
            or stored_readback.get("authoritative_state_root")
            != _historical_delivery_root(state, authority_hash)
        ):
            _reject(
                "EXECUTION_READBACK_INTEGRITY_INVALID",
                "Stored execution readback no longer matches authoritative state.",
            )
        current_readback = _readback_transaction(state, authority_hash)
        stable_fields = {
            "transaction_id",
            "authoritative_event_sha256",
            "delivery_count",
            "delivery_event_ids",
            "recipient_store_observations",
            "all_postconditions_observed",
        }
        if any(
            current_readback.get(field) != stored_readback.get(field)
            for field in stable_fields
        ):
            _reject(
                "EXECUTION_READBACK_INTEGRITY_INVALID",
                "Recipient readback differs from the issued execution receipt.",
            )
        prior_event_sha256 = event.get("event_sha256")
    if state.get("last_event_hash") != prior_event_sha256:
        _reject(
            "AUDIT_CHAIN_INTEGRITY_INVALID",
            "Controller last-event anchor is invalid.",
        )


def _finalize_pending(
    contract: dict[str, Any],
    state_path: Path,
    *,
    idempotency_key: str,
    request_hash: str,
) -> dict[str, Any]:
    # This load is intentionally separate from the authority-store write.  A
    # success receipt is impossible unless the committed bytes survive readback.
    state = load_json(state_path)
    _validate_persistent_integrity(contract, state)
    pending = _find_pending(state, idempotency_key, request_hash)
    if pending is None:
        raise RuntimeError("pending delivery transaction disappeared before readback")
    readback = _readback_transaction(
        state, pending["authoritative_event_sha256"]
    )
    outcome = copy.deepcopy(pending["outcome"])
    outcome["authority_evidence"] = {
        "recipient_delivery_event_sha256": pending[
            "authoritative_event_sha256"
        ],
        "authoritative_state_root": readback["authoritative_state_root"],
        "readback": readback,
        "readback_sha256": sha256_value(readback),
    }
    receipt = _issue_and_append_audit_event(
        contract,
        state,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        prior_state_sha256=pending["prior_state_sha256"],
        prior_event_hash=pending["prior_event_sha256"],
        outcome=outcome,
        authorization_bundle_sha256=pending[
            "trusted_holder_envelopes_sha256"
        ],
        policy_snapshot_sha256=pending["policy_snapshot_sha256"],
        authoritative_event_sha256=pending["authoritative_event_sha256"],
        authoritative_state_root=readback["authoritative_state_root"],
        readback_sha256=sha256_value(readback),
    )
    state["pending_transactions"] = [
        item
        for item in state.get("pending_transactions", [])
        if not (
            item.get("idempotency_key") == idempotency_key
            and item.get("request_sha256") == request_hash
        )
    ]
    save_state_atomic(state_path, state)
    return {
        "replay": "FIRST_ATTEMPT",
        "state_changed": True,
        "outcome": outcome,
        "execution_receipt": receipt,
    }


def execute_persisted(
    contract: dict[str, Any],
    request: dict[str, Any],
    state_path: Path,
) -> dict[str, Any]:
    """Execute against a file-backed authority store.

    Successful execution is two-phase: first one atomic replacement commits the
    complete recipient delivery transaction, then a fresh disk readback verifies
    the postcondition, and only then a second atomic replacement records the
    execution receipt.  A pending transaction is recoverable after interruption.
    """
    request_hash = sha256_value(request)
    raw_idempotency_key = request.get("idempotency_key")
    idempotency_valid = (
        isinstance(raw_idempotency_key, str) and bool(raw_idempotency_key)
    )
    idempotency_key = raw_idempotency_key
    if not idempotency_valid:
        idempotency_key = f"missing:{request_hash}"

    if not state_path.parent.exists():
        raise RuntimeError("state parent directory must already exist")
    directory_fd = os.open(state_path.parent, os.O_RDONLY)
    try:
        # Lock the existing directory descriptor so a rejected request creates
        # no lock artifact and no state bytes.
        fcntl.flock(directory_fd, fcntl.LOCK_EX)
        state = load_json(state_path) if state_path.exists() else new_state(contract)

        try:
            _validate_persistent_integrity(contract, state)
        except ExecutionError as exc:
            return _record_rejection(
                contract,
                request,
                state,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                outcome={
                    "status": "REJECTED",
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            )

        if not idempotency_valid:
            return _record_rejection(
                contract,
                request,
                state,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                outcome={
                    "status": "REJECTED",
                    "code": "IDEMPOTENCY_KEY_INVALID",
                    "message": (
                        "A non-empty idempotency key is part of the full command."
                    ),
                    "details": {},
                },
            )

        prior = _prior_attempt(state, idempotency_key, request_hash)
        if prior is not None:
            return {
                "replay": "IDEMPOTENT_REPLAY",
                "state_changed": False,
                "outcome": copy.deepcopy(prior["outcome"]),
                "execution_receipt": copy.deepcopy(prior["execution_receipt"]),
            }

        pending = _find_pending(state, idempotency_key, request_hash)
        if pending is not None:
            return _finalize_pending(
                contract,
                state_path,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )

        if _key_seen_with_other_request(state, idempotency_key, request_hash):
            result = _record_rejection(
                contract,
                request,
                state,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                outcome={
                    "status": "REJECTED",
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": (
                        "Idempotency key was already used by a different request."
                    ),
                    "details": {},
                },
            )
            return result

        try:
            outcome, units = _dispatch(contract, request, state, request_hash)
        except ExecutionError as exc:
            result = _record_rejection(
                contract,
                request,
                state,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                outcome={
                    "status": "REJECTED",
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            )
            return result

        projected_total = state.get("disclosure_units_used", 0) + units
        maximum = contract.get("max_disclosure_units", 0)
        if projected_total > maximum:
            result = _record_rejection(
                contract,
                request,
                state,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
                outcome={
                    "status": "REJECTED",
                    "code": "DISCLOSURE_BUDGET_EXHAUSTED",
                    "message": (
                        "Execution would exceed the frozen cumulative budget."
                    ),
                    "details": {
                        "current": state.get("disclosure_units_used", 0),
                        "requested": units,
                        "maximum": maximum,
                    },
                },
            )
            return result

        prior_state_sha256 = state_hash(state)
        prior_event_hash = state.get("last_event_hash")
        previous_store_root = delivery_store_root(state)
        authority_event = _authority_event(
            contract, request, request_hash, outcome, previous_store_root
        )
        authorization_hash, policy_hash = _authorization_bindings(request)
        pending_record = {
            "idempotency_key": idempotency_key,
            "request_sha256": request_hash,
            "prior_state_sha256": prior_state_sha256,
            "prior_event_sha256": prior_event_hash,
            "trusted_holder_envelopes_sha256": authorization_hash,
            "policy_snapshot_sha256": policy_hash,
            "authoritative_event_sha256": authority_event["event_sha256"],
            "outcome": copy.deepcopy(outcome),
        }
        pending_record["pending_sha256"] = sha256_value(pending_record)

        # One all-or-nothing mutation contains every delivery in this route.
        state["delivery_store"].append(authority_event)
        for delivery in authority_event["deliveries"]:
            state["recipient_stores"].setdefault(delivery["to"], []).append(
                {
                    "transaction_id": authority_event["transaction_id"],
                    "authoritative_event_sha256": authority_event[
                        "event_sha256"
                    ],
                    "delivery": copy.deepcopy(delivery),
                }
            )
        state["pending_transactions"].append(pending_record)
        state["disclosure_units_used"] = projected_total
        save_state_atomic(state_path, state)

        return _finalize_pending(
            contract,
            state_path,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
    finally:
        fcntl.flock(directory_fd, fcntl.LOCK_UN)
        os.close(directory_fd)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_state_atomic(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    args = parser.parse_args()

    contract = load_json(args.contract)
    request = load_json(args.input)
    result = execute_persisted(contract, request, args.state)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["outcome"]["status"] == "EXECUTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
