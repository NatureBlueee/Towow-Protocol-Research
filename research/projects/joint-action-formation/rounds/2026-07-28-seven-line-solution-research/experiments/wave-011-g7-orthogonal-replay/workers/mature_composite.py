#!/usr/bin/env python3
"""Mature composite: owner adapters, workflow, effect readback and planner."""

import json
import sys


def downstream(packet, seeds):
    graph = packet.get("public_graph") or packet.get("dependency_graph") or {}
    adjacency = {}
    for edge in graph.get("edges", []):
        if isinstance(edge, (list, tuple)) and len(edge) >= 2:
            left, right = edge[0], edge[1]
        else:
            left = edge.get("from", edge.get("source", edge.get("prerequisite")))
            right = edge.get("to", edge.get("target", edge.get("dependent")))
        if left is not None and right is not None:
            adjacency.setdefault(str(left), set()).add(str(right))
    seen = set(str(seed) for seed in seeds if seed is not None)
    stack = list(seen)
    while stack:
        for child in adjacency.get(stack.pop(), set()):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return sorted(seen)


def bodies(observations):
    return json.dumps(observations, ensure_ascii=False, sort_keys=True).lower()


def every_node(packet):
    graph = packet.get("public_graph") or {}
    values = []
    for item in graph.get("nodes", []):
        value = item if isinstance(item, str) else item.get("id", item.get("node_id"))
        if value is not None:
            values.append(str(value))
    return sorted(set(values))


def find_scalar(value, keys):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in keys and not isinstance(child, (dict, list)):
                return child
            found = find_scalar(child, keys)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_scalar(child, keys)
            if found is not None:
                return found
    return None


def decide(request):
    packet = request.get("public_packet", {})
    observations = request.get("observations", {})
    raw = bodies(observations)
    runtime = request.get("runtime_snapshot", {})
    migration = request.get("migration", {})
    seeds = packet.get("changed_public_nodes") or packet.get("defeater_refs") or []
    if isinstance(seeds, str):
        seeds = [seeds]
    if not seeds:
        endpoints = bodies(packet.get("native_queries", []))
        if "leaf" in endpoints:
            seeds = ["optional-leaf"]
        elif "root" in endpoints:
            seeds = ["shared-root"]
        else:
            seeds = ["authorization"]
    uncertain = bool(runtime.get("uncertain_effects"))
    packet_text = bodies(packet)
    high_coupling = bool(packet.get("high_coupling")) or (
        "shared-root" in packet_text and "owner://root/" in packet_text
    )
    refused = any(
        marker in raw
        for marker in ("refused_action", '"refused"', "purpose_not_authorized", "no_disclosure")
    )
    ambiguous = any(x in raw for x in ("timeout", "lost", "stale", "fork", "equivocat", "conflict", '"age"')) or (
        '"active": true' in raw and '"active": false' in raw
    )
    revoked = any(
        x in raw
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
    current = any(x in raw for x in ('"active": true', '"allow"', '"decision": "permit"', "current"))
    effect_key = find_scalar(observations.get("effect_readback"), {"effectKey", "effect_key"})
    expected_effect_key = (packet.get("operation") or {}).get("semantic_effect_key")
    effect_key_mismatch = bool(
        effect_key and expected_effect_key and effect_key != expected_effect_key
    )
    effect_object = find_scalar(observations.get("effect_readback"), {"object", "object_id"})
    acceptance_object = find_scalar(
        observations.get("acceptance_readback"), {"object", "object_id"}
    )
    acceptance_object_mismatch = bool(
        effect_object and acceptance_object and effect_object != acceptance_object
    )
    acceptance_goal = find_scalar(observations.get("acceptance_readback"), {"goal"})
    packet_goal = packet.get("goal_version")
    goal_mismatch = bool(acceptance_goal and packet_goal and acceptance_goal != packet_goal)
    authority_goal = find_scalar(observations.get("authority"), {"goal"})
    goal_mismatch = goal_mismatch or bool(
        authority_goal and packet_goal and authority_goal != packet_goal
    )
    migration_phase = str(migration.get("phase", "")).upper()
    crash_recovery = migration_phase in {"CRASH_TAKEOVER", "RECONCILING"}
    readback_text = bodies(observations.get("migration_effect_readbacks", []))

    if migration and not migration.get("imported", True):
        action, closure, reason = "BOUNDED_UNKNOWN", every_node(packet), "capsule failed semantic import; future continuation is not proved"
    elif crash_recovery and any(
        marker in readback_text
        for marker in ("object_not_found", '"phase": "completed"', "timeout")
    ):
        if '"phase": "completed"' in readback_text:
            closure = ["acceptance"]
            reason = "response-lost Effect was confirmed; Acceptance remains to reconcile"
        else:
            closure = [
                node
                for node in ("intent", "fulfilment", "acceptance")
                if node in every_node(packet)
            ]
            reason = "crash takeover remains in reconciliation after authoritative readback"
        action = "RECOVER"
    elif effect_key_mismatch:
        action, closure, reason = "GLOBAL_REOPEN", every_node(packet), "target readback causal identity differs from exact operation"
    elif acceptance_object_mismatch:
        action, closure, reason = "LOCAL_REOPEN", ["acceptance"], "Acceptance binds a different Effect object"
    elif goal_mismatch:
        action, closure, reason = "GLOBAL_REOPEN", every_node(packet), "goal/Acceptance version changed materially"
    elif '"active": true' in raw and '"active": false' in raw:
        action, closure, reason = "GLOBAL_REOPEN", every_node(packet), "owner views fork or equivocate"
    elif uncertain:
        action, closure, reason = "RECOVER", [], "reconcile semantic effect key before any retry"
    elif high_coupling and (revoked or ambiguous or refused):
        action, closure, reason = "GLOBAL_REOPEN", every_node(packet), "shared-root uncertainty defeats local proof"
    elif revoked and seeds:
        action, closure, reason = "LOCAL_REOPEN", downstream(packet, seeds), "fresh explicit defeater has a public causal cone"
    elif revoked:
        action, closure, reason = "LOCAL_REOPEN", downstream(packet, seeds), "revocation invalidates the visible authorization cone"
    elif refused:
        action, closure, reason = "HUMAN_AMEND", downstream(packet, seeds), "respect native refusal and seek lawful amendment"
    elif ambiguous:
        action, closure, reason = "BOUNDED_UNKNOWN", downstream(packet, seeds), "orthogonal observation is not sufficient for continuation"
    elif current:
        action, closure, reason = "CONTINUE", [], "fresh native evidence supports fenced attempt"
    else:
        action, closure, reason = "BLOCK", [], "no current owner basis"
    return {
        "method_id": "MATURE_COMPOSITE",
        "action": action,
        "closure": closure,
        "dispatch": action == "CONTINUE",
        "requires_fence": True,
        "reconciliation": "EFFECT_THEN_ACCEPTANCE_READBACK" if action == "RECOVER" else "NONE",
        "query_requests": packet.get("native_queries", []),
        "reason": reason,
        "cost": {"query": 3, "human_minutes": 15 if action == "HUMAN_AMEND" else 0, "assurance": 9},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
