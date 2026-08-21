#!/usr/bin/env python3
"""Human institution baseline with native escalation channels and full cost."""

import json
import sys


def institutional_scope(packet, global_review):
    graph = packet.get("public_graph", {})
    nodes = []
    for raw in graph.get("nodes", []):
        value = raw if isinstance(raw, str) else raw.get("id", raw.get("node_id"))
        if value is not None:
            nodes.append(str(value))
    if global_review:
        return sorted(set(nodes))
    nominated = packet.get("changed_public_nodes", [])
    if isinstance(nominated, str):
        nominated = [nominated]
    return sorted(set(str(value) for value in nominated))


def decide(request):
    packet = request.get("public_packet", {})
    observations = json.dumps(request.get("observations", {}), ensure_ascii=False, sort_keys=True).lower()
    runtime = request.get("runtime_snapshot", {})
    migration = request.get("migration", {})
    high_risk = bool(packet.get("high_coupling") or packet.get("irreversible"))
    acceptance_issue = any(x in observations for x in ("wrong_object", "criterion_changed", "acceptance_refused"))
    refusal = "refused" in observations
    ambiguity = any(x in observations for x in ("timeout", "lost", "stale", "fork", "equivocat", "unknown", "conflict", '"age"')) or (
        '"active": true' in observations and '"active": false' in observations
    )
    revoked = any(
        x in observations
        for x in (
            "revoked",
            "superseded",
            "expired",
            '"active": false',
            '"decision": "deny"',
            "rescinded",
            "retired",
            "owner_declined",
        )
    )
    current = any(x in observations for x in ('"active": true', '"allow"', '"decision": "permit"', "current"))
    uncertain_effect = bool(runtime.get("uncertain_effects"))

    if migration and not migration.get("imported", True):
        action, reason = "BLOCK", "runbook blocks a field-loss migration pending reconstruction"
    elif uncertain_effect:
        action, reason = "HUMAN_AMEND", "incident commander orders owner-to-owner reconciliation"
    elif acceptance_issue or refusal:
        action, reason = "HUMAN_AMEND", "authorized human process preserves refusal and exact Acceptance object"
    elif revoked or ambiguity:
        action = "GLOBAL_REOPEN" if high_risk or ambiguity else "HUMAN_AMEND"
        reason = "runbook escalates normative drift without guessing hidden truth"
    elif current:
        action, reason = "CONTINUE", "runbook records current owner confirmation"
    else:
        action, reason = "BLOCK", "deadline reached without lawful confirmation"
    closure = [] if action in {"CONTINUE", "BLOCK"} else institutional_scope(packet, action == "GLOBAL_REOPEN")
    return {
        "method_id": "HUMAN_RULE_BASELINE",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "OWNER_CONFERENCE" if uncertain_effect else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 2, "human_minutes": 55 if action != "CONTINUE" else 8, "handoffs": 3, "calendar_wait": 40},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
