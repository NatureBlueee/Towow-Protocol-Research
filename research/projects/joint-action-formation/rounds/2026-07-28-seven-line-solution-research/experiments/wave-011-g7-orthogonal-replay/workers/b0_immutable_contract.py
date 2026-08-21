#!/usr/bin/env python3
"""B0: immutable contract plus monitoring and full human amendment."""

import json
import sys


def all_nodes(packet):
    graph = packet.get("public_graph") or packet.get("dependency_graph") or {}
    result = []
    for node in graph.get("nodes", []):
        value = node if isinstance(node, str) else node.get("id", node.get("node_id"))
        if value is not None:
            result.append(str(value))
    return sorted(set(result))


def text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).lower()


def decide(request):
    packet = request.get("public_packet", {})
    evidence = text(request.get("observations", {}))
    runtime = request.get("runtime_snapshot", {})
    migration = request.get("migration", {})
    uncertain = bool(runtime.get("uncertain_effects"))
    explicit_negative = any(
        token in evidence
        for token in (
            '"active": false',
            '"decision": "deny"',
            "rescinded",
            "retired",
            "superseded",
            "purpose_not_authorized",
            "owner_declined",
            "conflicting_heads",
        )
    )
    clean_current = (
        any(
            token in evidence
            for token in ('"active": true', '"decision": "permit"', "current", '"allow"')
        )
        and not explicit_negative
        and not any(
            token in evidence
            for token in ("revoked", "stale", "timeout", "refused", "fork", "equivocat", "conflict", '"age"')
        )
    )
    if migration and not migration.get("imported", True):
        action = "HUMAN_AMEND"
        reason = "immutable runbook rejects an incomplete migration capsule"
    elif uncertain:
        action = "HUMAN_AMEND"
        reason = "immutable runbook requires human reconciliation of uncertain Effect"
    elif clean_current:
        action = "CONTINUE"
        reason = "immutable exact version remains supported by a clean native response"
    else:
        action = "HUMAN_AMEND"
        reason = "immutable contract cannot infer a safe local amendment"
    closure = [] if action == "CONTINUE" else all_nodes(packet)
    return {
        "method_id": "B0_IMMUTABLE_CONTRACT",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "HUMAN_READBACK" if uncertain else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 1, "human_minutes": 35 if action != "CONTINUE" else 0, "governance": 4},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
