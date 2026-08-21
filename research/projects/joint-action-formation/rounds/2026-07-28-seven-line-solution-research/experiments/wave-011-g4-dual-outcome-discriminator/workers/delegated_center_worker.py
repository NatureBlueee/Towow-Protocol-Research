#!/usr/bin/env python3
"""Center policy that lawfully asks an owner for exact-scope delegation.

The arm does not start with extra authority. It uses the same public primitive
as every arm, pays its cost, and relies on delegation only when the raw owner
record binds the exact operation, scope, delegate, and validity window.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker_runtime import BrokerClient, abstain_all  # noqa: E402


def ask(client: BrokerClient, name: str) -> dict[str, Any] | None:
    if name not in client.available:
        return None
    op = client.packet["operation"]
    return client.call(
        name,
        operation_id=op["operation_id"],
        operation_hash=op["arguments_hash"],
        target_id=op["target_id"],
        token_id=op["token_id"],
        resource_id=op["resource_id"],
        requested_delegate="delegated-center",
        requested_scope="exact-operation",
    )


def main() -> None:
    client = BrokerClient()
    client.predict("P0", abstain_all())
    op = client.packet["operation"]
    owners = client.packet["source_contract"]
    delegation = ask(client, "request_delegation")
    policy = ask(client, "read_policy")
    revision = ask(client, "read_revision")
    token = ask(client, "get_token_state")
    reservation = ask(client, "request_reservation")
    dependency = ask(client, "read_dependency")
    status = ask(client, "discover_status_api")

    failures: list[str] = []
    unknown: list[str] = []
    if delegation is None:
        unknown.append("delegation_channel_absent")
    elif delegation.get("delegation_decision") == "REFUSE":
        failures.append("delegation_refused")
    elif not (
        delegation.get("delegation_decision") == "APPROVE"
        and delegation.get("issuer") == owners["authority_owner"]
        and delegation.get("delegate") == "delegated-center"
        and delegation.get("scope") == "exact-operation"
        and delegation.get("revocation_terms") == "BINDING_THROUGH_VALID_UNTIL"
    ):
        unknown.append("delegation_not_binding_for_window")

    if not policy or not revision:
        unknown.append("policy_missing")
    else:
        exact = op["artifact_revision"]
        failures += ["artifact_revoked"] if exact in policy.get("revoked_revisions", []) else []
        if policy.get("mode") == "CURRENT_SECURITY_HEAD_REQUIRED" and exact != revision.get("revision"):
            failures.append("head_required")
        elif exact not in policy.get("allowed_revisions", []):
            failures.append("artifact_not_allowed")
    if not token or token.get("status") != "ISSUED":
        failures.append("token_not_issued")
    if not reservation or reservation.get("reservation_decision") != "RESERVED":
        unknown.append("reservation_not_bound")
    if dependency and dependency.get("provider_response") == "REFUSE_DISCLOSURE":
        unknown.append("dependency_unqueryable")

    success = "NO" if failures else ("ABSTAIN" if unknown else "YES")
    resolution = (
        "YES"
        if status
        and status.get("issuer") == owners["effect_owner"]
        and status.get("endpoint") == "status-by-operation-id"
        else "ABSTAIN"
    )
    client.predict(
        "P1",
        {
            "Y_success": success,
            "Y_resolution": resolution,
            "Y_effect": "ABSTAIN",
            "Y_acceptance": "ABSTAIN",
        },
    )
    if success == "YES" and "submit_operation" in client.available:
        client.call(
            "submit_operation",
            operation_id=op["operation_id"],
            operation_hash=op["arguments_hash"],
            target_id=op["target_id"],
            delegation_revision=delegation.get("revision") if delegation else None,
            delegate="delegated-center",
            reservation_sequence=reservation.get("fence_sequence")
            if reservation
            else None,
        )
        if "read_operation_status" in client.available:
            ask(client, "read_operation_status")
    client.finish(failures + unknown)


if __name__ == "__main__":
    main()
