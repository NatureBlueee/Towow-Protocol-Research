"""Deterministic authoritative platform state machine for T5."""

from __future__ import annotations

import hashlib
import json
from typing import Any


FAILURES = {
    "NONE",
    "ORDER_REJECTED",
    "PAYMENT_FAILED",
    "PROVISIONING_FAILED",
    "CANCELLED",
}


def receipt(event: dict[str, Any]) -> str:
    payload = json.dumps(
        event, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def execute(
    task: dict[str, Any],
    candidate: dict[str, Any],
    failure: str = "NONE",
) -> dict[str, Any]:
    if failure not in FAILURES:
        raise ValueError(f"unknown failure branch: {failure}")
    platform = task["platform"]["id"]
    approver = task["authority"]["buyer_approver"]
    expected_ops = task["required_operations"]
    operations = candidate["operations"]
    event_log: list[dict[str, Any]] = []
    state = {
        "catalog_read": False,
        "approved": False,
        "order_status": "NOT_CREATED",
        "payment_status": "NOT_STARTED",
        "subscription_status": "NOT_PROVISIONED",
        "seat_count": 0,
        "invoice_status": "NOT_ISSUED",
    }

    if [item["op"] for item in operations] != expected_ops:
        return {
            "status": "INVALID_OPERATION_SEQUENCE",
            "state": state,
            "events": event_log,
        }

    for index, item in enumerate(operations):
        op = item["op"]
        authority = item["authority_source"]
        inputs = item["inputs"]
        if op == "READ_CATALOG":
            valid = authority == platform and inputs == {
                "sku": task["request"]["sku"]
            }
            if valid:
                state["catalog_read"] = True
        elif op == "REQUEST_BUYER_APPROVAL":
            valid = authority == approver and inputs == {
                "sku": task["request"]["sku"],
                "seat_count": task["request"]["seat_count"],
                "total_price_cny": task["platform"]["total_price_cny"],
            }
            if valid:
                state["approved"] = True
        elif op == "CREATE_ORDER":
            valid = (
                authority == platform
                and state["catalog_read"]
                and state["approved"]
                and inputs
                == {
                    "sku": task["request"]["sku"],
                    "seat_count": task["request"]["seat_count"],
                    "billing_period": task["request"]["billing_period"],
                }
            )
            state["order_status"] = (
                "REJECTED" if valid and failure == "ORDER_REJECTED"
                else "CREATED" if valid
                else "INVALID"
            )
        elif op == "AUTHORIZE_PAYMENT":
            valid = (
                authority == platform
                and state["order_status"] == "CREATED"
                and inputs
                == {
                    "amount_cny": task["platform"]["total_price_cny"],
                    "payment_token_reference": "TOKEN-REF-ONLY",
                }
            )
            state["payment_status"] = (
                "FAILED" if valid and failure == "PAYMENT_FAILED"
                else "PAID" if valid
                else "NOT_AUTHORIZED"
            )
        elif op == "READ_PROVISIONING":
            valid = (
                authority == platform
                and state["payment_status"] == "PAID"
                and inputs == {"sku": task["request"]["sku"]}
            )
            if valid and failure == "PROVISIONING_FAILED":
                state["subscription_status"] = "PROVISIONING_FAILED"
            elif valid and failure == "CANCELLED":
                state["subscription_status"] = "CANCELLED"
            elif valid:
                state["subscription_status"] = "ACTIVE"
                state["seat_count"] = task["request"]["seat_count"]
        else:
            valid = (
                authority == platform
                and state["subscription_status"] == "ACTIVE"
                and inputs == {"sku": task["request"]["sku"]}
            )
            if valid:
                state["invoice_status"] = "ISSUED"

        event = {
            "index": index,
            "op": op,
            "authority_source": authority,
            "valid": valid,
            "platform_state": dict(state),
        }
        event["receipt_sha256"] = receipt(event)
        event_log.append(event)
        if not valid:
            break
        if state["order_status"] == "REJECTED":
            break
        if state["payment_status"] == "FAILED":
            break
        if state["subscription_status"] in {
            "PROVISIONING_FAILED",
            "CANCELLED",
        }:
            break

    expected = task["platform"]["success_postcondition"]
    success = all(state[key] == value for key, value in expected.items())
    any_invalid_operation = any(not event["valid"] for event in event_log)
    if success:
        terminal = "SUCCESS"
    elif any_invalid_operation:
        terminal = "INVALID_OPERATION"
    elif state["order_status"] == "REJECTED":
        terminal = "ORDER_REJECTED"
    elif state["payment_status"] == "FAILED":
        terminal = "PAYMENT_FAILED"
    elif state["subscription_status"] == "PROVISIONING_FAILED":
        terminal = "PROVISIONING_FAILED"
    elif state["subscription_status"] == "CANCELLED":
        terminal = "CANCELLED"
    else:
        terminal = "INCOMPLETE"
    return {
        "status": terminal,
        "authoritative_source": platform,
        "state": state,
        "events": event_log,
        "postcondition_verified": success,
    }
