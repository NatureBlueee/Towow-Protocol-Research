#!/usr/bin/env python3
"""Existing-component composition arm.

The policy explicitly validates each raw record against the frozen operation
and source contract. It shares transport but no decision function with either
center worker.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker_runtime import BrokerClient, abstain_all  # noqa: E402


def collect(client: BrokerClient, action: str) -> dict[str, Any] | None:
    if action not in client.available:
        return None
    operation = client.packet["operation"]
    return client.call(
        action,
        operation_id=operation["operation_id"],
        operation_hash=operation["arguments_hash"],
        target_id=operation["target_id"],
        token_id=operation["token_id"],
        resource_id=operation["resource_id"],
    )


def classify(
    packet: dict[str, Any], records: dict[str, dict[str, Any] | None]
) -> tuple[str, str, list[str]]:
    op = packet["operation"]
    owners = packet["source_contract"]
    hard_fail: list[str] = []
    unknown: list[str] = []

    revision = records.get("read_revision")
    policy = records.get("read_policy")
    if revision is None or policy is None:
        unknown.append("revision_or_policy_missing")
    else:
        exact = op["artifact_revision"]
        if policy.get("issuer") != owners["policy_owner"]:
            hard_fail.append("policy_wrong_owner")
        elif exact in policy.get("revoked_revisions", []):
            hard_fail.append("artifact_revoked")
        elif policy.get("mode") == "CURRENT_SECURITY_HEAD_REQUIRED":
            if exact != revision.get("revision"):
                hard_fail.append("security_head_mismatch")
        elif exact not in policy.get("allowed_revisions", []):
            hard_fail.append("artifact_not_allowed")

    token = records.get("get_token_state")
    if token is None:
        unknown.append("token_missing")
    elif (
        token.get("issuer") != owners["token_owner"]
        or token.get("token_id") != op["token_id"]
        or token.get("status") != "ISSUED"
        or "execute:exact-operation" not in token.get("scopes", [])
    ):
        hard_fail.append("token_invalid")

    authority = records.get("request_authority")
    if authority is None:
        unknown.append("authority_missing")
    elif authority.get("owner_decision") == "REFUSE":
        hard_fail.append("owner_refused")
    elif authority.get("owner_decision") != "APPROVE":
        unknown.append("owner_not_disclosed")
    elif (
        authority.get("issuer") != owners["authority_owner"]
        or authority.get("operation_hash") != op["arguments_hash"]
        or authority.get("scope") != "exact-operation"
    ):
        hard_fail.append("authority_binding_mismatch")

    reservation = records.get("request_reservation")
    if reservation is None:
        unknown.append("reservation_missing")
    elif reservation.get("reservation_decision") == "NOT_PROVIDED":
        unknown.append("reservation_not_provided")
    elif (
        reservation.get("issuer") != owners["reservation_owner"]
        or reservation.get("reservation_decision") != "RESERVED"
        or reservation.get("operation_hash") != op["arguments_hash"]
        or reservation.get("resource_id") != op["resource_id"]
        or not isinstance(reservation.get("fence_sequence"), int)
    ):
        hard_fail.append("reservation_binding_mismatch")

    dependency = records.get("read_dependency")
    if dependency is not None:
        if dependency.get("provider_response") == "REFUSE_DISCLOSURE":
            unknown.append("dependency_declared_unqueryable")
        elif dependency.get("state") != "AVAILABLE":
            hard_fail.append("dependency_unavailable")

    status_api = records.get("discover_status_api")
    if (
        status_api is not None
        and status_api.get("issuer") == owners["effect_owner"]
        and status_api.get("endpoint") == "status-by-operation-id"
        and status_api.get("lookup_key") == "operation_id"
    ):
        resolution = "YES"
    elif status_api is None:
        resolution = "ABSTAIN"
    else:
        resolution = "NO"

    if hard_fail:
        success = "NO"
    elif unknown:
        success = "ABSTAIN"
    else:
        success = "YES"
    return success, resolution, hard_fail + unknown


def main() -> None:
    client = BrokerClient()
    client.predict("P0", abstain_all())
    records: dict[str, dict[str, Any] | None] = {}
    for action in (
        "read_revision",
        "read_policy",
        "get_token_state",
        "read_dependency",
        "request_authority",
        "request_reservation",
        "discover_status_api",
    ):
        if action in client.available:
            records[action] = collect(client, action)
    success, resolution, reasons = classify(client.packet, records)
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
        operation = client.packet["operation"]
        client.call(
            "submit_operation",
            operation_id=operation["operation_id"],
            operation_hash=operation["arguments_hash"],
            target_id=operation["target_id"],
            authority_revision=records["request_authority"].get("revision"),
            reservation_sequence=records["request_reservation"].get(
                "fence_sequence"
            ),
        )
        if "read_operation_status" in client.available:
            collect(client, "read_operation_status")
    client.finish(reasons)


if __name__ == "__main__":
    main()
