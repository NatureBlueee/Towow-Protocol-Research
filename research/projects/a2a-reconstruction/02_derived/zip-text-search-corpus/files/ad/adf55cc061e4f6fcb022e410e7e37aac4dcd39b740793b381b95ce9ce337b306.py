from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
from typing import Any, Iterable


SCHEMA_COMPONENTS = (
    "roles",
    "object_types",
    "actions",
    "transitions",
    "authority_rules",
    "witness_rules",
    "acceptance_rules",
    "data_rules",
    "standing_rules",
    "jurisdiction_rules",
    "challenge_rules",
    "settlement_rules",
)


@dataclass(frozen=True)
class ChangeFinding:
    path: str
    component: str
    kind: str
    material: bool
    reason: str


@dataclass(frozen=True)
class ChangeReport:
    classification: str
    material: bool
    findings: tuple[ChangeFinding, ...]
    reachable_actions: tuple[str, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "material": self.material,
            "findings": [asdict(item) for item in self.findings],
            "reachable_actions": list(self.reachable_actions),
            "notes": list(self.notes),
        }


def _dict_diff(old: Any, new: Any, prefix: str = "") -> list[tuple[str, Any, Any]]:
    """Return leaf-level differences between JSON-compatible values."""
    if isinstance(old, dict) and isinstance(new, dict):
        diffs: list[tuple[str, Any, Any]] = []
        keys = sorted(set(old) | set(new))
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in old:
                diffs.append((path, None, new[key]))
            elif key not in new:
                diffs.append((path, old[key], None))
            else:
                diffs.extend(_dict_diff(old[key], new[key], path))
        return diffs
    if isinstance(old, list) and isinstance(new, list):
        # Relation-schema lists encode sets or unordered rule collections in
        # this minimal fieldkit. Compare canonical JSON members so a pure
        # reordering does not create a false schema change. If a future schema
        # needs order-sensitive semantics, it must model the order explicitly.
        import json

        old_members = sorted(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in old)
        new_members = sorted(json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":")) for item in new)
        if old_members == new_members:
            return []
        return [(prefix, old, new)]
    return [] if old == new else [(prefix, old, new)]


def _transition_index(schema: dict[str, Any]) -> dict[str, list[tuple[str, str]]]:
    index: dict[str, list[tuple[str, str]]] = {}
    for transition in schema.get("transitions", []):
        if not isinstance(transition, dict):
            continue
        source = str(transition.get("from", ""))
        action = str(transition.get("action", ""))
        target = str(transition.get("to", ""))
        if source and action and target:
            index.setdefault(source, []).append((action, target))
    return index


def reachable_actions(schema: dict[str, Any], current_state: str, max_depth: int = 12) -> set[str]:
    """Compute actions reachable from the current state in a bounded finite schema."""
    index = _transition_index(schema)
    seen_states = {current_state}
    queue: deque[tuple[str, int]] = deque([(current_state, 0)])
    actions: set[str] = set()
    while queue:
        state, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for action, target in index.get(state, []):
            actions.add(action)
            if target not in seen_states:
                seen_states.add(target)
                queue.append((target, depth + 1))
    return actions


def _top_component(path: str) -> str:
    return path.split(".", 1)[0] if path else ""


def _second_token(path: str) -> str | None:
    parts = path.split(".")
    return parts[1] if len(parts) > 1 else None


def classify_change(
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    *,
    current_state: str,
    active_resources: Iterable[str] = (),
    active_roles: Iterable[str] = (),
    max_depth: int = 12,
) -> ChangeReport:
    """Classify a schema change as parameter, non-material schema, or material schema.

    Parameters are deliberately not stored in the relation schema. If the two
    schemas are identical, this function returns PARAMETER_OR_NO_SCHEMA_CHANGE.
    Materiality is task-relative: a structural change is material only when it
    can alter a reachable trace, authority, evidence, outcome, or data right in
    the current task envelope.
    """
    diffs = _dict_diff(old_schema, new_schema)
    old_reachable = reachable_actions(old_schema, current_state, max_depth)
    new_reachable = reachable_actions(new_schema, current_state, max_depth)
    reachable = old_reachable | new_reachable
    resources = set(active_resources)
    roles = set(active_roles)

    if not diffs:
        return ChangeReport(
            classification="PARAMETER_OR_NO_SCHEMA_CHANGE",
            material=False,
            findings=(),
            reachable_actions=tuple(sorted(reachable)),
            notes=("No relation-schema difference was detected; instance values may still have changed.",),
        )

    findings: list[ChangeFinding] = []
    for path, before, after in diffs:
        component = _top_component(path)
        token = _second_token(path)
        material = False
        reason = "The change is outside the operational relation schema."
        kind = "metadata_or_extension"

        if component == "metadata" or component.startswith("x-"):
            reason = "Metadata and presentation-only extensions do not change valid relation traces."
        elif component == "roles":
            kind = "role_change"
            referenced = bool(token and (token in roles or token in _roles_referenced_by_actions(old_schema, reachable) or token in _roles_referenced_by_actions(new_schema, reachable)))
            material = referenced
            reason = (
                "The role participates in a reachable action or is active in the current instance."
                if material
                else "The role is not used by any currently reachable action or active assignment."
            )
        elif component == "object_types":
            kind = "object_type_change"
            material = bool(token and token in resources)
            reason = (
                "The object type is active in the current relation instance."
                if material
                else "The object type is not active in the current relation instance."
            )
        elif component == "actions":
            kind = "action_alphabet_change"
            material = bool(token and token in reachable)
            reason = (
                "The action is reachable from the current relation state."
                if material
                else "The action is not reachable in the current task envelope."
            )
        elif component == "transitions":
            kind = "transition_change"
            old_sig = _reachable_transition_signatures(old_schema, current_state, max_depth)
            new_sig = _reachable_transition_signatures(new_schema, current_state, max_depth)
            material = old_sig != new_sig
            reason = (
                "The change alters a transition whose source is reachable from the current state."
                if material
                else "The changed transition remains outside the current reachable subgraph."
            )
        elif component in {"authority_rules", "witness_rules", "acceptance_rules"}:
            kind = component.rstrip("s") + "_change"
            material = bool(token and token in reachable)
            reason = (
                f"The {component} change applies to a reachable action or disposition."
                if material
                else f"The {component} change applies only outside the reachable subgraph."
            )
        elif component == "data_rules":
            kind = "data_right_change"
            material = bool(token and token in resources)
            reason = (
                "The changed data rule governs a resource used by the current relation."
                if material
                else "The changed data rule does not govern an active resource."
            )
        elif component in {"standing_rules", "jurisdiction_rules", "challenge_rules", "settlement_rules"}:
            kind = component.rstrip("s") + "_change"
            # Public institutional cases show that a bilateral relation may be
            # reopened, prohibited, or re-qualified by an authority or affected
            # stakeholder not represented in the immediate action graph. In the
            # minimal fieldkit these rules are therefore material by default. A
            # future domain-specific checker may prove a scoped change irrelevant.
            material = True
            reason = (
                f"The {component} change can alter who may challenge, which legal or "
                "institutional scope applies, or when the disposition may be treated "
                "as settled; it is material unless a domain-specific proof shows irrelevance."
            )
        elif component in SCHEMA_COMPONENTS:
            kind = "schema_change"
            material = True
            reason = "The changed component is operational and could not be proven irrelevant."

        findings.append(ChangeFinding(path, component, kind, material, reason))

    any_material = any(item.material for item in findings)
    classification = "MATERIAL_SCHEMA_CHANGE" if any_material else "NON_MATERIAL_SCHEMA_CHANGE"
    notes: list[str] = []
    if old_reachable != new_reachable:
        notes.append("The set of actions reachable from the current state changed.")
    if any_material:
        notes.append("Re-form only the affected dependency subgraph; do not reopen unrelated settled nodes.")
    else:
        notes.append("A compatibility update is sufficient; a new formation episode is not required.")
    return ChangeReport(classification, any_material, tuple(findings), tuple(sorted(reachable)), tuple(notes))


def _roles_referenced_by_actions(schema: dict[str, Any], action_names: set[str]) -> set[str]:
    result: set[str] = set()
    actions = schema.get("actions", {})
    if not isinstance(actions, dict):
        return result
    for name in action_names:
        action = actions.get(name, {})
        if not isinstance(action, dict):
            continue
        for field in ("actor_roles", "target_roles", "required_roles"):
            value = action.get(field, [])
            if isinstance(value, str):
                result.add(value)
            elif isinstance(value, list):
                result.update(str(item) for item in value)
    return result


def _actions_in_transition_diff(before: Any, after: Any) -> set[str]:
    actions: set[str] = set()
    for value in (before, after):
        if isinstance(value, dict) and value.get("action"):
            actions.add(str(value["action"]))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and item.get("action"):
                    actions.add(str(item["action"]))
    return actions


def compile_readiness(
    schema: dict[str, Any],
    relation_state: dict[str, Any],
    *,
    current_state: str | None = None,
) -> dict[str, Any]:
    """Assess whether the currently reachable subgraph can be deterministically compiled."""
    state = current_state or str(relation_state.get("state", "FORMING"))
    reachable = reachable_actions(schema, state)
    actions = schema.get("actions", {}) if isinstance(schema.get("actions", {}), dict) else {}
    authority = schema.get("authority_rules", {}) if isinstance(schema.get("authority_rules", {}), dict) else {}
    witnesses = schema.get("witness_rules", {}) if isinstance(schema.get("witness_rules", {}), dict) else {}

    failures: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    for action_name in sorted(reachable):
        action = actions.get(action_name, {}) if isinstance(actions.get(action_name, {}), dict) else {}
        if action.get("material", True) and action_name not in authority:
            failures.append({"code": "MISSING_AUTHORITY_RULE", "subject": action_name})
        if action.get("produces_effect", False) and action_name not in witnesses:
            failures.append({"code": "MISSING_EFFECT_WITNESS", "subject": action_name})

    unresolved = relation_state.get("unresolved_material_counterexamples", [])
    if unresolved:
        failures.append({"code": "UNRESOLVED_MATERIAL_COUNTEREXAMPLE", "subject": str(len(unresolved))})

    required_stances = set(str(x) for x in relation_state.get("required_stances", []))
    obtained_stances = set(str(x) for x in relation_state.get("obtained_stances", []))
    missing_stances = sorted(required_stances - obtained_stances)
    if missing_stances:
        failures.append({"code": "MISSING_REQUIRED_STANCE", "subject": ",".join(missing_stances)})

    required_mandates = set(str(x) for x in relation_state.get("required_mandates", []))
    valid_mandates = set(str(x) for x in relation_state.get("valid_mandates", []))
    missing_mandates = sorted(required_mandates - valid_mandates)
    if missing_mandates:
        failures.append({"code": "MISSING_OR_STALE_MANDATE", "subject": ",".join(missing_mandates)})

    if not relation_state.get("reopen_rules_defined", False):
        failures.append({"code": "MISSING_REOPEN_RULES", "subject": state})
    if not relation_state.get("rollback_or_compensation_defined", False):
        warnings.append({"code": "NO_ROLLBACK_OR_COMPENSATION", "subject": state})
    if not schema.get("acceptance_rules"):
        warnings.append({"code": "NO_ACCEPTANCE_RULES", "subject": state})

    required_jurisdictions = set(str(x) for x in relation_state.get("required_jurisdictions", []))
    covered_jurisdictions = set(str(x) for x in relation_state.get("covered_jurisdictions", []))
    missing_jurisdictions = sorted(required_jurisdictions - covered_jurisdictions)
    if missing_jurisdictions:
        failures.append({
            "code": "MISSING_REQUIRED_JURISDICTION_REVIEW",
            "subject": ",".join(missing_jurisdictions),
        })

    required_standing = set(str(x) for x in relation_state.get("required_external_standing", []))
    reviewed_standing = set(str(x) for x in relation_state.get("reviewed_external_standing", []))
    missing_standing = sorted(required_standing - reviewed_standing)
    if missing_standing:
        failures.append({
            "code": "UNREVIEWED_EXTERNAL_STANDING",
            "subject": ",".join(missing_standing),
        })

    open_challenges = [str(x) for x in relation_state.get("open_material_challenges", [])]
    has_contingency = bool(relation_state.get("challenge_contingency_defined", False))
    if open_challenges and not has_contingency:
        failures.append({
            "code": "OPEN_MATERIAL_CHALLENGE_WITHOUT_CONTINGENCY",
            "subject": ",".join(open_challenges),
        })
    elif open_challenges:
        warnings.append({
            "code": "OPEN_MATERIAL_CHALLENGE_COMPILED_WITH_CONTINGENCY",
            "subject": ",".join(open_challenges),
        })

    if (schema.get("settlement_rules") or required_jurisdictions or required_standing) and not relation_state.get("challenge_horizon"):
        warnings.append({
            "code": "UNSPECIFIED_CHALLENGE_HORIZON",
            "subject": state,
        })

    ready = not failures
    readiness = "NOT_READY"
    if ready and open_challenges:
        readiness = "READY_WITH_CONTINGENCY"
    elif ready:
        readiness = "READY"

    return {
        "ready": ready,
        "readiness": readiness,
        "state": state,
        "reachable_actions": sorted(reachable),
        "failures": failures,
        "warnings": warnings,
        "settlement_scope": {
            "required_jurisdictions": sorted(required_jurisdictions),
            "covered_jurisdictions": sorted(covered_jurisdictions),
            "required_external_standing": sorted(required_standing),
            "reviewed_external_standing": sorted(reviewed_standing),
            "open_material_challenges": open_challenges,
            "challenge_horizon": relation_state.get("challenge_horizon"),
        },
        "compiler_rule": "Compilation may only preserve existing authority and semantics; it must not create a new mandate, stance, commitment, effect, jurisdictional clearance, or settlement claim.",
    }


def _reachable_transition_signatures(schema: dict[str, Any], current_state: str, max_depth: int = 12) -> set[tuple[str, str, str]]:
    index = _transition_index(schema)
    seen_states = {current_state}
    queue: deque[tuple[str, int]] = deque([(current_state, 0)])
    signatures: set[tuple[str, str, str]] = set()
    while queue:
        state, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for action, target in index.get(state, []):
            signatures.add((state, action, target))
            if target not in seen_states:
                seen_states.add(target)
                queue.append((target, depth + 1))
    return signatures
