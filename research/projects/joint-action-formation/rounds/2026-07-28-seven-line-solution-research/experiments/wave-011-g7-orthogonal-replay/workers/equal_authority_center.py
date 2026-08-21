#!/usr/bin/env python3
"""Equal-authority center with its own centralized graph implementation."""

import json
import sys


def central_cone(packet, seeds):
    graph = packet.get("public_graph") or {}
    edges = []
    for edge in graph.get("edges", []):
        if isinstance(edge, dict):
            a = edge.get("source", edge.get("from"))
            b = edge.get("target", edge.get("to"))
        else:
            a, b = edge[:2]
        if a is not None and b is not None:
            edges.append((str(a), str(b)))
    cone = {str(x) for x in seeds}
    changed = True
    while changed:
        changed = False
        for parent, child in edges:
            if parent in cone and child not in cone:
                cone.add(child)
                changed = True
    return sorted(cone)


def decide(request):
    packet = request.get("public_packet", {})
    encoded = json.dumps(request.get("observations", {}), ensure_ascii=False, sort_keys=True).lower()
    runtime = request.get("runtime_snapshot", {})
    migration = request.get("migration", {})
    seeds = packet.get("changed_public_nodes", [])
    if isinstance(seeds, str):
        seeds = [seeds]
    conflict = any(x in encoded for x in ("fork", "equivocat", "conflict")) or (
        '"active": true' in encoded and '"active": false' in encoded
    )
    stale_or_lost = any(x in encoded for x in ("stale", "timeout", "lost", "unreachable", '"age"'))
    revoked = any(
        x in encoded
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
    refused = "refused" in encoded
    current = any(x in encoded for x in ('"active": true', '"allow"', '"decision": "permit"', "current"))
    uncertain_effect = bool(runtime.get("uncertain_effects"))

    if migration and not migration.get("imported", True):
        action, closure, reason = "BLOCK", [], "central importer rejects an incomplete capsule"
    elif uncertain_effect:
        action, closure, reason = "RECOVER", [], "central coordinator orders Effect reconciliation"
    elif conflict or stale_or_lost:
        action, closure, reason = "GLOBAL_REOPEN", central_cone(packet, seeds), "equal authority cannot resolve missing or conflicting owner truth"
    elif refused:
        action, closure, reason = "HUMAN_AMEND", central_cone(packet, seeds), "center cannot override an independent refusal"
    elif revoked:
        cone = central_cone(packet, seeds)
        action = "LOCAL_REOPEN" if cone and not packet.get("high_coupling") else "GLOBAL_REOPEN"
        closure, reason = cone, "central graph engine recomputed the visible dependency cone"
    elif current:
        action, closure, reason = "CONTINUE", [], "all visible owner checks are current"
    else:
        action, closure, reason = "BLOCK", [], "central observation set is incomplete"
    return {
        "method_id": "EQUAL_AUTHORITY_CENTER",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "CENTRAL_EFFECT_RECONCILIATION" if action == "RECOVER" else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 3, "human_minutes": 18 if action == "HUMAN_AMEND" else 0, "central_ops": 8},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
