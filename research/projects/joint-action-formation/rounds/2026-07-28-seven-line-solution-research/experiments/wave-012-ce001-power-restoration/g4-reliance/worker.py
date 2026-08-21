#!/usr/bin/env python3
"""Blind JSON-lines G4 policy for the exact CE-001 operation.

This file is standalone so its process needs no imports from the broker,
service, holdout, or evaluator.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def send(message: dict[str, Any]) -> dict[str, Any]:
    sys.stdout.write(json.dumps(message, sort_keys=True) + "\n")
    sys.stdout.flush()
    reply = sys.stdin.readline()
    if not reply:
        raise RuntimeError("broker closed")
    return json.loads(reply)


def predict(stage: str, values: dict[str, str]) -> None:
    reply = send({"type": "prediction", "stage": stage, "predictions": values})
    if reply.get("type") != "ack":
        raise RuntimeError("prediction was not acknowledged")


def call(action: str, args: dict[str, Any]) -> dict[str, Any] | None:
    reply = send({"type": "action", "action": action, "args": args})
    if reply.get("type") != "response":
        raise RuntimeError("invalid broker response")
    return reply.get("raw")


start = json.loads(sys.stdin.readline())
if start.get("type") != "start":
    raise RuntimeError("missing start packet")
episode = start["episode"]
available = set(start["available_actions"])
bound = {
    "episode_id": episode["episode_id"],
    "Q_version": episode["Q_version"],
    "object_id": episode["object_id"],
    "operation_id": episode["operation_id"],
}

abstain = {
    "first_attempt_target_record": "ABSTAIN",
    "terminal_reconciliation": "ABSTAIN",
    "owner_act_closure": "ABSTAIN",
}
predict("P0", abstain)

interface = call("inspect_interfaces", bound)
resolution = "ABSTAIN"
if (
    isinstance(interface, dict)
    and interface.get("issuer") == episode["owners"]["effect"]
    and interface.get("status_endpoint") == "exact-operation-readback"
    and all(interface.get(key) == value for key, value in bound.items())
):
    resolution = "YES"

# P1 is frozen after a read-only interaction, before reservation and commit
# evidence.  Later success/readback must never be used to rewrite it.
predict(
    "P1",
    {
        "first_attempt_target_record": "ABSTAIN",
        "terminal_reconciliation": resolution,
        "owner_act_closure": "ABSTAIN",
    },
)

reservation = call("reserve", bound)
commit = call("read_commit_evidence", bound)
records = commit.get("owner_records", []) if isinstance(commit, dict) else []
required_owners = {
    episode["owners"]["Q"],
    episode["owners"]["venue"],
    episode["owners"]["resource"],
    episode["owners"]["safety"],
}
records_exact = (
    {item.get("issuer") for item in records} == required_owners
    and all(
        item.get("owner_decision") == "CURRENT"
        and all(item.get(key) == value for key, value in bound.items())
        for item in records
    )
)
reservation_exact = bool(
    isinstance(reservation, dict)
    and reservation.get("issuer") == episode["owners"]["resource"]
    and reservation.get("reservation_status") == "RESERVED"
    and all(reservation.get(key) == value for key, value in bound.items())
)

result = {
    "wrong_object_rejected": False,
    "exact_reconciled": False,
    "terminal_state": "OWNER_BLOCKED",
}
if records_exact and reservation_exact:
    attempt_args = {
        **bound,
        "reservation_id": reservation["reservation_id"],
        "fence_epoch": reservation["fence_epoch"],
        "commit_revisions": {
            item["issuer"]: item["revision"] for item in records
        },
    }
    call("submit_operation", attempt_args)
    broad = call("readback_operation", bound)
    broad_exact = bool(
        isinstance(broad, dict)
        and all(broad.get(key) == value for key, value in bound.items())
    )
    result["wrong_object_rejected"] = not broad_exact
    exact = call("reconcile_operation", bound)
    if isinstance(exact, dict) and exact.get("state") == "NO_RECORD":
        call("retry_idempotent", attempt_args)
        exact = call("reconcile_operation", bound)
    result["exact_reconciled"] = bool(
        isinstance(exact, dict)
        and all(exact.get(key) == value for key, value in bound.items())
        and exact.get("state") in {"SUCCEEDED", "NO_RECORD"}
    )
    result["terminal_state"] = (
        exact.get("state") if isinstance(exact, dict) else "UNKNOWN"
    )
    target_is_exact = bool(
        isinstance(exact, dict)
        and exact.get("state") == "SUCCEEDED"
        and exact.get("circuit_id") == "C7"
        and isinstance(exact.get("power_kw"), (int, float))
        and 2.85 <= float(exact["power_kw"]) <= 3.15
        and isinstance(exact.get("continuous_minutes"), (int, float))
        and float(exact["continuous_minutes"]) >= 45
        and exact.get("no_other_circuit") is True
        and exact.get("other_circuits_energized") == []
        and isinstance(exact.get("effect_occurrence_id"), str)
        and isinstance(exact.get("oe_provenance"), dict)
        and all(exact.get(key) == value for key, value in bound.items())
    )
    if target_is_exact:
        acceptance_args = {
            **bound,
            "effect_occurrence_id": exact["effect_occurrence_id"],
            "effect_revision": exact["effect_revision"],
        }
        q_act = call("request_q_acceptance", acceptance_args)
        venue_act = call("request_venue_acceptance", acceptance_args)
        result["owner_acceptance_statuses"] = [
            q_act.get("status") if isinstance(q_act, dict) else "NO_RESPONSE",
            (
                venue_act.get("status")
                if isinstance(venue_act, dict)
                else "NO_RESPONSE"
            ),
        ]

sys.stdout.write(json.dumps({"type": "result", "result": result}, sort_keys=True) + "\n")
sys.stdout.flush()
