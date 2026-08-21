from __future__ import annotations

from collections import deque
from typing import Any


def goal_reached(facts: set[str], goals: list[str]) -> bool:
    return set(goals).issubset(facts)


def search(
    oracle: dict[str, Any],
    actions: list[dict[str, Any]],
    *,
    horizon: int,
    response: str,
) -> dict[str, Any]:
    initial = frozenset(oracle["initial_facts"])
    queue: deque[tuple[frozenset[str], list[str]]] = deque([(initial, [])])
    seen = {initial}
    while queue:
        frozen, trace = queue.popleft()
        facts = set(frozen)
        if goal_reached(facts, oracle["qualified_goal_facts"]):
            return {"result": "SAT", "trace": trace, "visited_states": len(seen)}
        if len(trace) >= horizon:
            continue
        for action in actions:
            allowed = action.get("allowed_responses")
            if allowed is not None and response not in allowed:
                continue
            if not set(action["requires"]).issubset(facts):
                continue
            next_facts = (facts - set(action.get("removes", []))) | set(action["adds"])
            next_frozen = frozenset(next_facts)
            if next_frozen not in seen:
                seen.add(next_frozen)
                queue.append((next_frozen, trace + [action["id"]]))
    return {"result": "UNSAT", "trace": [], "visited_states": len(seen)}


def replay(
    oracle: dict[str, Any],
    action_ids: list[str],
    *,
    response: str,
    extra_actions: list[dict[str, Any]] | None = None,
    blocked: set[str] | None = None,
) -> dict[str, Any]:
    actions = {
        action["id"]: action
        for action in oracle["old_actions"]
        + oracle.get("extension_actions", [])
        + list(extra_actions or [])
    }
    facts = set(oracle["initial_facts"])
    steps: list[dict[str, Any]] = []
    blocked = blocked or set()
    valid = True
    for index, action_id in enumerate(action_ids):
        before = sorted(facts)
        action = actions.get(action_id)
        reason = None
        if action_id in blocked:
            reason = "BLOCKED_BY_COUNTERFACTUAL"
        elif action is None:
            reason = "ACTION_NOT_IN_FROZEN_SEMANTICS"
        elif action.get("allowed_responses") is not None and response not in action["allowed_responses"]:
            reason = "RESPONSE_DISALLOWS_ACTION"
        elif not set(action["requires"]).issubset(facts):
            reason = "PRECONDITION_FALSE"
        if reason:
            valid = False
            steps.append(
                {
                    "index": index,
                    "action_id": action_id,
                    "before": before,
                    "after": before,
                    "applied": False,
                    "reason": reason,
                }
            )
            break
        facts = (facts - set(action.get("removes", []))) | set(action["adds"])
        steps.append(
            {
                "index": index,
                "action_id": action_id,
                "before": before,
                "after": sorted(facts),
                "applied": True,
                "reason": "APPLIED",
            }
        )
    return {
        "valid": valid,
        "goal_reached": valid and goal_reached(facts, oracle["qualified_goal_facts"]),
        "terminal_safe": (
            "terminal_safe" in facts
            or "owner_authorized_change" in facts
            or (valid and goal_reached(facts, oracle["qualified_goal_facts"]))
        ),
        "final_facts": sorted(facts),
        "steps": steps,
    }
