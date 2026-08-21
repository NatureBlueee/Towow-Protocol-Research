"""Stateful raw-response primitives for the paired-world prototype.

The service deliberately does not compute reliance or validity verdicts.  It
returns owner/provider vocabulary and lets the worker compare revisions,
scopes, expiry and operation records.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from fixtures import WorldSpec


FORBIDDEN_RESPONSE_KEYS = {
    "authoritative",
    "fenced",
    "head_current",
    "is_safe_to_rely",
    "safe_to_rely",
}

PRIMITIVE_META = {
    "read_revision": (2, "INTERNAL"),
    "read_policy": (3, "SENSITIVE"),
    "request_authority": (11, "HUMAN_DECISION"),
    "request_reservation": (7, "RESOURCE_SCOPE"),
    "submit_operation": (13, "OPERATION_PAYLOAD"),
    "read_operation_status": (5, "OPERATION_STATUS"),
    "reconcile_operation": (8, "OPERATION_STATUS"),
}


def _stable_id(namespace: str, kind: str, sequence: int) -> str:
    raw = f"{namespace}:{kind}:{sequence}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def assert_raw_response(value: Any) -> None:
    if isinstance(value, dict):
        overlap = FORBIDDEN_RESPONSE_KEYS.intersection(value)
        if overlap:
            raise AssertionError(f"pre-adjudicated response keys: {sorted(overlap)}")
        for nested in value.values():
            assert_raw_response(nested)
    elif isinstance(value, list):
        for nested in value:
            assert_raw_response(nested)


@dataclass
class PrimitiveService:
    spec: WorldSpec
    operation_ref: str = "refund:merchant-17:12743"
    now_tick: int = 100
    call_sequence: int = 0
    authority_receipt: dict[str, Any] | None = None
    reservation_receipt: dict[str, Any] | None = None
    operation_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    reconciliation_records: dict[str, dict[str, Any]] = field(default_factory=dict)
    broker_log: list[dict[str, Any]] = field(default_factory=list)

    def public_bootstrap(self) -> dict[str, Any]:
        return {
            "operation": {
                "operation_ref": self.operation_ref,
                "executor": "processor-A",
                "artifact": "refund-adapter",
                "expected_revision": self.spec.revision,
                "policy_scope": "refund:merchant-17",
                "amount_minor": 12743,
                "currency": "USD",
                "horizon_tick": 180,
            },
            "allowed_primitives": self.allowed_primitives(),
        }

    def allowed_primitives(self) -> list[str]:
        allowed = ["read_revision", "read_policy"]
        if self.spec.allow_formation:
            allowed.extend(["request_authority", "request_reservation"])
        if self.spec.allow_submit:
            allowed.extend(
                [
                    "submit_operation",
                    "read_operation_status",
                    "reconcile_operation",
                ]
            )
        return allowed

    def call(self, primitive: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if primitive not in self.allowed_primitives():
            raise ValueError(f"primitive not allowed: {primitive}")
        self.call_sequence += 1
        handler = getattr(self, f"_do_{primitive}")
        response = handler(arguments)
        assert_raw_response(response)
        encoded = json.dumps(response, sort_keys=True, separators=(",", ":")).encode()
        latency, sensitivity = PRIMITIVE_META[primitive]
        self.broker_log.append(
            {
                "sequence": self.call_sequence,
                "primitive": primitive,
                "source": response["source"],
                "latency_ms": latency,
                "response_bytes": len(encoded),
                "sensitivity": sensitivity,
                "response": response,
            }
        )
        self.now_tick += 1
        return response

    def _do_read_revision(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "artifact-registry",
            "object_ref": arguments["object_ref"],
            "revision": self.spec.revision,
            "registry_sequence": 44,
            "observed_tick": self.now_tick,
        }

    def _do_read_policy(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {
            "source": "merchant-policy-owner",
            "scope": arguments["scope"],
            "revision": self.spec.policy_revision,
            "state": self.spec.policy_state,
            "subject": "processor-A",
            "action": "refund",
            "valid_from_tick": 20,
            "expires_tick": 220,
            "observed_tick": self.now_tick,
        }

    def _do_request_authority(self, arguments: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "source": "merchant-authority-owner",
            "receipt_id": _stable_id(
                self.spec.public_namespace, "authority", self.call_sequence
            ),
            "response": self.spec.authority_response,
            "subject": arguments["subject"],
            "operation_ref": arguments["operation_ref"],
            "policy_revision": arguments["policy_revision"],
            "expires_tick": 180,
            "observed_tick": self.now_tick,
        }
        self.authority_receipt = receipt
        return receipt

    def _do_request_reservation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        outcome = self.spec.reservation_response
        receipt = {
            "source": "processor-capacity-owner",
            "request_id": _stable_id(
                self.spec.public_namespace, "reservation-request", self.call_sequence
            ),
            "outcome": outcome,
            "resource_ref": arguments["resource_ref"],
            "operation_ref": arguments["operation_ref"],
            "lease_id": (
                _stable_id(self.spec.public_namespace, "lease", self.call_sequence)
                if outcome == "GRANTED"
                else None
            ),
            "epoch": 9 if outcome == "GRANTED" else None,
            "expires_tick": 175 if outcome == "GRANTED" else None,
            "observed_tick": self.now_tick,
        }
        self.reservation_receipt = receipt
        return receipt

    def _do_submit_operation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation_key = arguments["operation_key"]
        if (
            self.authority_receipt is None
            or self.authority_receipt["response"] != "APPROVED"
            or self.reservation_receipt is None
            or self.reservation_receipt["outcome"] != "GRANTED"
        ):
            return {
                "source": "processor-submit-endpoint",
                "delivery": "DELIVERED",
                "provider_code": "PRECONDITION_REJECTED",
                "operation_key": operation_key,
                "observed_tick": self.now_tick,
            }

        if operation_key not in self.operation_records:
            provider_state = self.spec.execution_state
            self.operation_records[operation_key] = {
                "provider_state": provider_state,
                "postcondition_revision": (
                    "ledger-r81" if provider_state == "APPLIED" else "ledger-r80"
                ),
                "effect_count": 1 if provider_state == "APPLIED" else 0,
            }
        if self.spec.submit_delivery == "LOST":
            return {
                "source": "processor-submit-endpoint",
                "delivery": "LOST",
                "provider_code": "UPSTREAM_RESPONSE_TIMEOUT",
                "operation_key": operation_key,
                "observed_tick": self.now_tick,
            }
        return {
            "source": "processor-submit-endpoint",
            "delivery": "DELIVERED",
            "provider_code": self.operation_records[operation_key]["provider_state"],
            "operation_key": operation_key,
            "observed_tick": self.now_tick,
        }

    def _do_read_operation_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation_key = arguments["operation_key"]
        if self.spec.status_visibility != "VISIBLE":
            return {
                "source": "processor-operation-ledger",
                "operation_key": operation_key,
                "lookup": "UNAVAILABLE",
                "observed_tick": self.now_tick,
            }
        record = self.operation_records.get(operation_key)
        if record is None:
            return {
                "source": "processor-operation-ledger",
                "operation_key": operation_key,
                "lookup": "NOT_FOUND",
                "observed_tick": self.now_tick,
            }
        response = {
            "source": "processor-operation-ledger",
            "operation_key": operation_key,
            "lookup": "FOUND",
            "provider_state": record["provider_state"],
            "postcondition_revision": record["postcondition_revision"],
            "effect_count": record["effect_count"],
            "observed_tick": self.now_tick,
        }
        if operation_key in self.reconciliation_records:
            response["reconciliation"] = self.reconciliation_records[operation_key]
        return response

    def _do_reconcile_operation(self, arguments: dict[str, Any]) -> dict[str, Any]:
        operation_key = arguments["operation_key"]
        record = self.operation_records.get(operation_key)
        if record is None:
            disposition = "NO_OPERATION_RECORD"
        elif record["provider_state"] == "APPLIED":
            disposition = "CONFIRMED_APPLIED_NO_RETRY"
        else:
            disposition = "CONFIRMED_NO_EFFECT"
        reconciliation = {
            "record_id": _stable_id(
                self.spec.public_namespace, "reconciliation", self.call_sequence
            ),
            "disposition": disposition,
            "based_on_revision": arguments["postcondition_revision"],
            "recorded_tick": self.now_tick,
        }
        self.reconciliation_records[operation_key] = reconciliation
        return {
            "source": "merchant-reconciliation-owner",
            "operation_key": operation_key,
            "record": reconciliation,
            "observed_tick": self.now_tick,
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "operation_records": self.operation_records,
            "reconciliation_records": self.reconciliation_records,
            "authority_request_made": self.authority_receipt is not None,
            "reservation_request_made": self.reservation_receipt is not None,
        }
