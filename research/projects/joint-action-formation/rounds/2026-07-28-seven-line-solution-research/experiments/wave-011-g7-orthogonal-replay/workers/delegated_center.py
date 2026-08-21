#!/usr/bin/env python3
"""Legitimately delegated center; authority stratum differs from equal center."""

import json
import sys


def delegated_impact(packet, seeds):
    graph = packet.get("public_graph", {})
    reverse_index = {}
    for raw in graph.get("edges", []):
        if isinstance(raw, dict):
            parent = raw.get("prerequisite", raw.get("from", raw.get("source")))
            child = raw.get("dependent", raw.get("to", raw.get("target")))
        else:
            parent, child = raw[0], raw[1]
        if parent is not None and child is not None:
            reverse_index.setdefault(str(parent), []).append(str(child))
    queue = [str(x) for x in seeds]
    output = []
    while queue:
        node = queue.pop(0)
        if node in output:
            continue
        output.append(node)
        queue.extend(reverse_index.get(node, []))
    return sorted(output)


def decide(request):
    packet = request.get("public_packet", {})
    raw = json.dumps(request.get("observations", {}), ensure_ascii=False, sort_keys=True).lower()
    runtime = request.get("runtime_snapshot", {})
    migration = request.get("migration", {})
    seeds = packet.get("changed_public_nodes", [])
    if isinstance(seeds, str):
        seeds = [seeds]
    delegated = bool(packet.get("delegated_authority", False))
    uncertain = bool(runtime.get("uncertain_effects"))
    hard_refusal = "refused_action" in raw
    forked = any(x in raw for x in ("fork", "equivocat", "conflict")) or (
        '"active": true' in raw and '"active": false' in raw
    )
    revoked = any(
        x in raw
        for x in (
            "revoked",
            "expired",
            "superseded",
            '"active": false',
            '"decision": "deny"',
            "rescinded",
            "retired",
            "owner_declined",
        )
    )
    temporarily_unavailable = any(x in raw for x in ("timeout", "unreachable", "stale", '"age"'))
    current = any(x in raw for x in ('"active": true', '"allow"', '"decision": "permit"', "current"))

    if migration and not migration.get("imported", True):
        action, closure, reason = "BLOCK", [], "delegation does not authorize filling dropped capsule fields"
    elif not delegated:
        action, closure, reason = "BLOCK", [], "delegation receipt absent"
    elif uncertain:
        action, closure, reason = "RECOVER", [], "delegated transaction manager reconciles in-flight Effect"
    elif hard_refusal or forked:
        action, closure, reason = "HUMAN_AMEND", delegated_impact(packet, seeds), "delegation does not erase a reserved refusal/conflict"
    elif revoked:
        closure = delegated_impact(packet, seeds)
        action, reason = ("LOCAL_REOPEN" if closure else "GLOBAL_REOPEN"), "delegated center atomically invalidates its controlled cone"
    elif temporarily_unavailable and packet.get("delegated_condition_write", True):
        action, closure, reason = "RECOVER", [], "delegated source of record can refresh under its own transaction boundary"
    elif current:
        action, closure, reason = "CONTINUE", [], "delegated center owns a current conditional-write boundary"
    else:
        action, closure, reason = "BLOCK", [], "delegated center lacks a current record"
    return {
        "method_id": "DELEGATED_CENTER",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "DELEGATED_TRANSACTION_READBACK" if action == "RECOVER" else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 1, "human_minutes": 12 if action == "HUMAN_AMEND" else 0, "central_ops": 5},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
