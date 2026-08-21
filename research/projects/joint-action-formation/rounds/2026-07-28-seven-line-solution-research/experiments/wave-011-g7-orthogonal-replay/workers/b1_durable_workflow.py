#!/usr/bin/env python3
"""B1: durable workflow/history/version migration plus human amendment."""

import json
import sys


def workflow_scope(packet):
    graph = packet.get("public_graph") or packet.get("graph") or {}
    nodes = []
    for item in graph.get("nodes", []):
        node = item if isinstance(item, str) else item.get("id", item.get("name"))
        if node is not None:
            nodes.append(str(node))
    return sorted(set(nodes))


def scan(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()


def decide(request):
    packet = request.get("public_packet", {})
    observations = scan(request.get("observations", {}))
    runtime = request.get("runtime_snapshot", {})
    uncertain = bool(runtime.get("uncertain_effects"))
    migration = request.get("migration", {})
    import_failed = migration and not migration.get("imported", True)
    normative_bad = any(
        x in observations
        for x in (
            "revoked",
            "refused_action",
            "superseded",
            '"active": false',
            '"decision": "deny"',
            "rescinded",
            "retired",
            "owner_declined",
            "purpose_not_authorized",
        )
    )
    epistemic_bad = any(x in observations for x in ("stale", "fork", "equivocat", "conflict", '"age"')) or (
        '"active": true' in observations and '"active": false' in observations
    )
    channel_bad = any(x in observations for x in ("timeout", "lost", "unreachable"))

    if import_failed or normative_bad or epistemic_bad:
        action, reason = "HUMAN_AMEND", "workflow version cannot repair normative or capsule uncertainty"
    elif uncertain or channel_bad:
        action, reason = "RECOVER", "durable history requires authoritative Effect reconciliation"
    elif any(x in observations for x in ('"active": true', '"allow"', '"decision": "permit"', "current")):
        action, reason = "CONTINUE", "durable replay continues current exact version"
    else:
        action, reason = "BLOCK", "workflow history has no fresh Authority basis"

    closure = workflow_scope(packet) if action == "HUMAN_AMEND" else []
    return {
        "method_id": "B1_DURABLE_WORKFLOW",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "EFFECT_READBACK" if action == "RECOVER" else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 2, "human_minutes": 25 if action == "HUMAN_AMEND" else 0, "runtime": 7},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
