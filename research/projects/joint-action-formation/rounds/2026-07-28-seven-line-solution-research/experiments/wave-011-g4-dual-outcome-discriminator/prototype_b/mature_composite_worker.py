#!/usr/bin/env python3
"""Independent mature-composite process using only the primitive broker."""

from __future__ import annotations

import json
import sys
from typing import Any


def send(message: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def receive() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise SystemExit("broker closed")
    return json.loads(line)


def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    send({"type": "call", "primitive": name, "arguments": arguments})
    reply = receive()
    if reply.get("type") != "response" or reply.get("primitive") != name:
        raise SystemExit("broker protocol mismatch")
    return reply["raw"]


def prediction(stage: str, success: str, resolution: str, basis: list[str]) -> None:
    send(
        {
            "type": "prediction",
            "stage": stage,
            "Y_success": success,
            "Y_resolution": resolution,
            "Y_effect": "NOT_PREDICTED_BY_G4",
            "Y_acceptance": "NOT_PREDICTED_BY_G4",
            "basis": basis,
        }
    )


def main() -> None:
    init = receive()
    if init.get("type") != "init":
        raise SystemExit("missing init")
    operation = init["operation"]
    allowed = set(init["allowed_primitives"])

    # P0 is frozen before any query or world-changing request.
    prediction("P0", "ABSTAIN", "ABSTAIN", ["NO_CURRENT_PRIMITIVE_RESPONSE"])

    revision = call(
        "read_revision", {"object_ref": operation["artifact"]}
    )
    policy = call("read_policy", {"scope": operation["policy_scope"]})
    basis = [
        f"artifact-registry:{revision['revision']}",
        f"merchant-policy-owner:{policy['revision']}:{policy['state']}",
    ]

    if (
        revision["revision"] != operation["expected_revision"]
        or policy["state"] != "PUBLISHED"
        or policy["subject"] != operation["executor"]
        or policy["action"] != "refund"
        or not (policy["valid_from_tick"] <= 100 < policy["expires_tick"])
    ):
        prediction("P1", "BLOCK", "BLOCK", basis + ["RAW_SCOPE_OR_REVISION_MISMATCH"])
        send({"type": "final", "execution": "NOT_ATTEMPTED"})
        return

    if "request_authority" not in allowed or "request_reservation" not in allowed:
        prediction("P1", "ABSTAIN", "ABSTAIN", basis + ["FORMATION_NOT_AVAILABLE"])
        send({"type": "final", "execution": "NOT_ATTEMPTED"})
        return

    authority = call(
        "request_authority",
        {
            "subject": operation["executor"],
            "operation_ref": operation["operation_ref"],
            "policy_revision": policy["revision"],
        },
    )
    reservation = call(
        "request_reservation",
        {
            "resource_ref": "processor-A:refund-slot",
            "operation_ref": operation["operation_ref"],
        },
    )
    basis.extend(
        [
            f"merchant-authority-owner:{authority['response']}",
            f"processor-capacity-owner:{reservation['outcome']}",
        ]
    )
    if authority["response"] == "REFUSED" or reservation["outcome"] == "REFUSED":
        prediction("P1", "BLOCK", "BLOCK", basis)
        send({"type": "final", "execution": "NOT_ATTEMPTED"})
        return
    if (
        authority["response"] != "APPROVED"
        or authority["operation_ref"] != operation["operation_ref"]
        or authority["policy_revision"] != policy["revision"]
        or authority["expires_tick"] < operation["horizon_tick"]
        or reservation["outcome"] != "GRANTED"
        or reservation["operation_ref"] != operation["operation_ref"]
        or reservation["expires_tick"] < operation["horizon_tick"] - 5
    ):
        prediction("P1", "ABSTAIN", "ABSTAIN", basis + ["RAW_RECEIPT_INCOMPLETE"])
        send({"type": "final", "execution": "NOT_ATTEMPTED"})
        return

    # A formation action has changed the world; this is a new frozen prediction,
    # not a correction of P0.
    resolution_prediction = (
        "RELY"
        if {"read_operation_status", "reconcile_operation"}.issubset(allowed)
        else "ABSTAIN"
    )
    prediction("P1", "RELY", resolution_prediction, basis)
    if "submit_operation" not in allowed:
        send({"type": "final", "execution": "NOT_ATTEMPTED"})
        return

    operation_key = "refund-op-001"
    submit = call(
        "submit_operation",
        {
            "operation_key": operation_key,
            "operation_ref": operation["operation_ref"],
            "lease_id": reservation["lease_id"],
            "epoch": reservation["epoch"],
        },
    )
    if submit["delivery"] == "LOST":
        status = call("read_operation_status", {"operation_key": operation_key})
        if status["lookup"] == "FOUND":
            call(
                "reconcile_operation",
                {
                    "operation_key": operation_key,
                    "postcondition_revision": status["postcondition_revision"],
                },
            )
            final_status = call(
                "read_operation_status", {"operation_key": operation_key}
            )
            send(
                {
                    "type": "final",
                    "execution": "RECONCILED_AFTER_RESPONSE_LOSS",
                    "provider_state": final_status["provider_state"],
                    "postcondition_revision": final_status[
                        "postcondition_revision"
                    ],
                    "effect_count": final_status["effect_count"],
                    "resolution_disposition": final_status["reconciliation"][
                        "disposition"
                    ],
                }
            )
            return
        send({"type": "final", "execution": "UNRESOLVED_AFTER_RESPONSE_LOSS"})
        return

    status = call("read_operation_status", {"operation_key": operation_key})
    send(
        {
            "type": "final",
            "execution": "READ_BACK_AFTER_DELIVERY",
            "provider_state": status.get("provider_state"),
            "postcondition_revision": status.get("postcondition_revision"),
            "effect_count": status.get("effect_count"),
        }
    )


if __name__ == "__main__":
    main()
