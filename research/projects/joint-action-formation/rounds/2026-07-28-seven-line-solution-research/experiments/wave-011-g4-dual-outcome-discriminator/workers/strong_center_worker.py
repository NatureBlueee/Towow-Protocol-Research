#!/usr/bin/env python3
"""Same-permission center implemented as an independent evidence ledger.

Unlike the mature-composite arm, this policy builds an issuer-indexed ledger
and evaluates invariants over the ledger after a different query schedule.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker_runtime import BrokerClient, abstain_all  # noqa: E402


def main() -> None:
    client = BrokerClient()
    client.predict("P0", abstain_all())
    packet = client.packet
    op = packet["operation"]
    owners = packet["source_contract"]
    ledger: dict[str, list[dict[str, Any]]] = {}
    notes: list[str] = []

    agenda = [
        "discover_status_api",
        "get_token_state",
        "read_policy",
        "read_revision",
        "request_reservation",
        "request_authority",
        "read_dependency",
    ]
    by_action: dict[str, dict[str, Any]] = {}
    for action in agenda:
        if action not in client.available:
            continue
        raw = client.call(
            action,
            operation_id=op["operation_id"],
            operation_hash=op["arguments_hash"],
            target_id=op["target_id"],
            token_id=op["token_id"],
            resource_id=op["resource_id"],
        )
        if isinstance(raw, dict):
            by_action[action] = raw
            ledger.setdefault(str(raw.get("issuer", "UNATTRIBUTED")), []).append(raw)

    explicit_no = False
    unresolved = False
    policy = by_action.get("read_policy")
    head = by_action.get("read_revision")
    if not policy or not head:
        unresolved = True
    else:
        revision = op["artifact_revision"]
        allowed = revision in policy.get("allowed_revisions", [])
        revoked = revision in policy.get("revoked_revisions", [])
        mode = policy.get("mode")
        head_required_violation = (
            mode == "CURRENT_SECURITY_HEAD_REQUIRED"
            and revision != head.get("revision")
        )
        explicit_no |= revoked or not allowed or head_required_violation

    token = by_action.get("get_token_state")
    explicit_no |= bool(token and token.get("status") != "ISSUED")
    unresolved |= token is None

    owner = by_action.get("request_authority")
    if owner:
        explicit_no |= owner.get("owner_decision") == "REFUSE"
        unresolved |= owner.get("owner_decision") not in {"APPROVE", "REFUSE"}
        explicit_no |= owner.get("issuer") != owners["authority_owner"]
        explicit_no |= owner.get("operation_hash") not in {
            None,
            op["arguments_hash"],
        }
    else:
        unresolved = True

    reserve = by_action.get("request_reservation")
    if reserve:
        unresolved |= reserve.get("reservation_decision") == "NOT_PROVIDED"
        explicit_no |= reserve.get("reservation_decision") not in {
            "RESERVED",
            "NOT_PROVIDED",
        }
        explicit_no |= reserve.get("issuer") != owners["reservation_owner"]
        explicit_no |= reserve.get("resource_id") != op["resource_id"]
        explicit_no |= reserve.get("operation_hash") not in {
            None,
            op["arguments_hash"],
        }
    else:
        unresolved = True

    dependency = by_action.get("read_dependency")
    if dependency:
        unresolved |= dependency.get("provider_response") == "REFUSE_DISCLOSURE"
        explicit_no |= (
            "state" in dependency and dependency.get("state") != "AVAILABLE"
        )

    status = by_action.get("discover_status_api")
    resolution = (
        "YES"
        if status
        and status.get("issuer") == owners["effect_owner"]
        and status.get("lookup_key") == "operation_id"
        and status.get("endpoint") == "status-by-operation-id"
        else "ABSTAIN"
    )
    success = "NO" if explicit_no else ("ABSTAIN" if unresolved else "YES")
    if len(ledger.get("cache:edge-7", [])) > 1:
        notes.append("same-source aliases counted once")
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
            authority_revision=owner.get("revision") if owner else None,
            reservation_sequence=reserve.get("fence_sequence") if reserve else None,
        )
        if "read_operation_status" in client.available:
            client.call(
                "read_operation_status",
                operation_id=op["operation_id"],
                target_id=op["target_id"],
            )
    client.finish(notes)


if __name__ == "__main__":
    main()
