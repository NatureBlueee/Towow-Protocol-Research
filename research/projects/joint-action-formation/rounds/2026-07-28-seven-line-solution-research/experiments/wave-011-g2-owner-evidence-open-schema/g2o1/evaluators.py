"""Separated public-evidence evaluators for the five G2-O1 axes."""

from __future__ import annotations

from typing import Any, Optional

from g2o1.actors import digest, verified_events
from g2o1.kernel import analyze_schema_delta, evaluate_coupled_constraints


def _relation(world: dict[str, Any]) -> dict[str, Any]:
    return (
        world.get("candidate_relation")
        or world.get("relation")
        or world.get("base_relation")
        or {}
    )


def _principals(world: dict[str, Any]) -> set[str]:
    return set(world.get("principal_ids") or world.get("principals") or [])


def _schema_fields(schema: Any) -> set[str]:
    if isinstance(schema, dict):
        return set(map(str, schema))
    if isinstance(schema, list):
        return {
            str(item.get("name") if isinstance(item, dict) else item)
            for item in schema
        }
    return set()


def _index(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        result.setdefault(event["action"], []).append(event)
    return result


def _body(
    by_action: dict[str, list[dict[str, Any]]], action: str
) -> dict[str, Any]:
    rows = by_action.get(action, [])
    return rows[-1]["body"] if rows else {}


def _constraint_satisfied(
    constraint: dict[str, Any], relation: dict[str, Any]
) -> bool:
    path = str(constraint.get("path", "")).split(".")
    value: Any = relation
    for part in filter(None, path):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    if "equals" in constraint:
        return value == constraint["equals"]
    if "in" in constraint:
        return value in constraint["in"]
    if "not_equals" in constraint:
        return value != constraint["not_equals"]
    return bool(value)


def _derive_axes(
    world: dict[str, Any],
    events: list[dict[str, Any]],
    candidate: Optional[dict[str, Any]] = None,
) -> dict[str, bool]:
    relation = _relation(world)
    principals = _principals(world)
    by_action = _index(events)
    current_version = str(relation.get("version", "UNSPECIFIED"))
    current_digest = digest(relation)
    current = [
        event
        for event in events
        if event["relation_version"] == current_version
        and event["version_digest"] == current_digest
    ]
    current_by_action = _index(current)

    rules = _body(current_by_action, "CONSTITUTION_RULES")
    required_claimants = set(
        rules.get("required_principals", principals)
    )
    comprehension_required = set(
        rules.get("comprehension_required", required_claimants)
    )
    understanding = {
        row["principal_id"]: bool(row["body"].get("correctness"))
        for row in current_by_action.get("UNDERSTANDING", [])
        if row["principal_id"] in comprehension_required
    }
    understood = (
        bool(comprehension_required)
        and set(understanding) == comprehension_required
        and all(understanding.values())
    )

    stances = {
        row["principal_id"]: row["body"]
        for row in current_by_action.get("STANCE", [])
        if row["principal_id"] in required_claimants
    }
    claim_modes = {"ACCEPT"}
    claimed = (
        bool(required_claimants)
        and set(stances) == required_claimants
        and all(
            str(body.get("stance", "")).upper() in claim_modes
            and bool(body.get("claim_scope"))
            for body in stances.values()
        )
    )

    required_fields = set(
        map(str, rules.get("required_schema_fields", []))
    )
    schema_ok = required_fields <= _schema_fields(
        relation.get("schema", {})
    )
    constraint_ids = {
        str(item.get("id"))
        for item in relation.get("schema", {}).get("constraints", [])
        if isinstance(item, dict)
    }
    constraint_ids.update(
        map(str, (candidate or {}).get("formed_schema_ids", []))
    )
    for observation in current_by_action.get("SCHEMA_OBSERVATION", []):
        constraint_ids.update(
            map(
                str,
                observation["body"].get("schema_delta", {}).get(
                    "add", []
                ),
            )
        )
    constraint_ids_ok = set(
        map(str, rules.get("required_constraint_ids", []))
    ) <= constraint_ids
    constraints_ok, _ = evaluate_coupled_constraints(
        rules.get("held_out_constraints", []),
        rules.get("coupled_assignments", {}),
    )
    global_opposition = any(
        str(row["body"].get("claim_scope", "")).upper()
        in {"RELATION", "GLOBAL"}
        and str(
            row["body"].get("opposition")
            or row["body"].get("stance", "")
        ).upper()
        in {"OPPOSE", "REFUSE", "WITHDRAW"}
        for row in current_by_action.get("OPPOSITION", [])
        + current_by_action.get("STANCE", [])
    )
    constituted = (
        schema_ok
        and constraint_ids_ok
        and constraints_ok
        and claimed
        and not global_opposition
    )
    if rules.get("understanding_constitutive") or rules.get(
        "comprehension_required"
    ):
        constituted = constituted and understood

    authority = _body(current_by_action, "AUTHORITY")
    revocation = _body(current_by_action, "REVOCATION")
    reservation = _body(current_by_action, "RESERVATION")
    authorized = bool(
        authority.get("authorized", authority.get("valid", False))
        and authority.get("current", True)
        and not authority.get("revoked", False)
        and not revocation.get("revoked", bool(revocation))
    )
    duplicate_reservation = bool(
        reservation.get("duplicate", False)
        or reservation.get("duplicate_attempt", False)
        or reservation.get("unique") is False
    )
    if authority.get("reservation_required", False) or duplicate_reservation:
        authorized = authorized and bool(
            reservation.get("unique", not duplicate_reservation)
            and reservation.get("current", True)
            and not duplicate_reservation
        )

    activation = _body(current_by_action, "ACTIVATION")
    activated = bool(
        activation.get("activated", activation.get("target_readback", False))
        and activation.get("accepted", True)
        and activation.get("current", True)
    )
    return {
        "constituted": constituted,
        "understood": understood,
        "claimed": claimed,
        "authorized": authorized,
        "activated": activated,
    }


def constitution_evaluator(
    world: dict[str, Any],
    candidate: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, bool]:
    """Institutional constitution, understanding and claim axes only."""
    events = verified_events(
        candidate.get("owner_events", []),
        owner_packet.get("public_keys", {}),
    )
    axes = _derive_axes(world, events, candidate)
    return {key: axes[key] for key in ("constituted", "understood", "claimed")}


def authority_evaluator(
    world: dict[str, Any],
    candidate: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, bool]:
    """Current action Authority only; it never promotes Relation truth."""
    events = verified_events(
        candidate.get("owner_events", []),
        owner_packet.get("public_keys", {}),
    )
    return {
        "authorized": _derive_axes(world, events, candidate)["authorized"]
    }


def target_acceptance_evaluator(
    world: dict[str, Any],
    candidate: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, bool]:
    """Target-domain readback/Acceptance only."""
    events = verified_events(
        candidate.get("owner_events", []),
        owner_packet.get("public_keys", {}),
    )
    return {
        "activated": _derive_axes(world, events, candidate)["activated"]
    }


def evaluate_run(
    world: dict[str, Any],
    candidate: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    all_events = verified_events(
        owner_packet.get("owner_events", []),
        owner_packet.get("public_keys", {}),
    )
    reference_axes = _derive_axes(world, all_events)
    axes = {
        **constitution_evaluator(world, candidate, owner_packet),
        **authority_evaluator(world, candidate, owner_packet),
        **target_acceptance_evaluator(world, candidate, owner_packet),
    }
    by_action = _index(all_events)
    reference_delta = analyze_schema_delta(
        world.get("base_relation") or {},
        world.get("candidate_relation") or {},
    )
    schema_changed = reference_delta.requires_new_version
    if candidate.get("platform_direct"):
        method_schema_changed = False
    else:
        method_delta = analyze_schema_delta(
            world.get("base_relation") or {},
            {
                **(world.get("candidate_relation") or {}),
                "schema": candidate.get("proposed_schema", {}),
            },
        )
        method_schema_changed = method_delta.requires_new_version
    column = _body(by_action, "PRIVATE_COLUMN")
    column_status = str(column.get("status", "ABSENT")).upper()
    reported_column_state = (
        {
            "PRESENT": "FOUND",
            "WITHHELD": "WITHHELD",
            "ABSENT": "ABSENT",
        }.get(column_status, column_status)
        if world.get("family") == "T4_HELD_OUT"
        else "NOT_APPLICABLE"
    )
    candidate_statuses = {
        str(item.get("status", "")).upper()
        for item in candidate.get("private_columns", [])
    }
    column_recalled = column_status in candidate_statuses
    if column_status == "PRESENT":
        column_recalled = column_recalled and any(
            item.get("column") or item.get("proposal")
            for item in candidate.get("private_columns", [])
        )
    opposition_digests = {
        row["payload_digest"]
        for row in all_events
        if row["action"] in {"OPPOSITION", "STANCE"}
        and (
            row["body"].get("opposition")
            or str(row["body"].get("stance", "")).upper()
            in {"OPPOSE", "PARTIAL", "REFUSE"}
        )
    }
    candidate_refs = {
        row.get("evidence_digest")
        for row in candidate.get("owner_evidence_refs", [])
    }
    authority = _body(by_action, "AUTHORITY")
    revocation = _body(by_action, "REVOCATION")
    reservation = _body(by_action, "RESERVATION")
    topology_events = [
        row["body"]
        for row in all_events
        if row["action"] in {"PARTITION", "EQUIVOCATION", "RECOVERY"}
    ]
    has_pressure = (
        "partition" in str(world.get("public_context", {})).lower()
        or "equivocation" in str(world.get("public_context", {})).lower()
        or bool(topology_events)
    )
    topology = topology_events[-1] if topology_events else {}
    fault = str(topology.get("fault", "")).upper()
    recovery = (
        candidate.get("replicated_state", {}).get("recovery_rule")
        or authority.get("recovery_rule")
    )
    partition_recovered = bool(
        fault in {"PARTITION", "EQUIVOCATION"} and recovery
    )
    diagnostics = {
        "schema_change": {
            "reference": schema_changed,
            "detected": method_schema_changed,
            "correct": schema_changed == method_schema_changed,
        },
        "private_column_recall": {
            "status": reported_column_state,
            "recalled_without_collapsing_withheld_to_absent": column_recalled,
        },
        "provenance_opposition": {
            "required_opposition_events": len(opposition_digests),
            "round_trip": opposition_digests <= candidate_refs,
            "status": (
                "PRESERVED"
                if opposition_digests <= candidate_refs
                else "LOST"
            ),
        },
        "stale_revoke": {
            "stale_present": not authority.get(
                "current", revocation.get("current", True)
            ),
            "revoked_present": bool(
                authority.get("revoked", False)
                or revocation.get("revoked", bool(revocation))
            ),
            "fail_closed": not axes["authorized"]
            if (
                not authority.get("current", True)
                or authority.get("revoked", False)
                or revocation
            )
            else True,
        },
        "duplicate_reservation": {
            "duplicate_present": bool(
                reservation.get("duplicate", False)
                or reservation.get("duplicate_attempt", False)
                or reservation.get("unique") is False
            ),
            "fail_closed": not axes["authorized"]
            if (
                reservation.get("duplicate", False)
                or reservation.get("duplicate_attempt", False)
                or reservation.get("unique") is False
            )
            else True,
        },
        "partition_recovery": {
            "pressure_present": has_pressure,
            "authority_topology": world.get("authority_topology"),
            "state_placement": candidate.get("state_placement"),
            "recovery_rule": recovery,
            "fail_closed_or_recoverable": (
                not has_pressure
                or not axes["authorized"]
                or bool(recovery)
            ),
            "equivocation_detected": fault == "EQUIVOCATION",
            "partition_recovered": partition_recovered,
            "max_divergent_heads_after_recovery": (
                1 if partition_recovered else None
            ),
        },
        "cost": {
            "operations": len(candidate.get("operations", [])),
            "disclosure_units": candidate.get("disclosure_units", 0),
            "owner_events": len(candidate.get("owner_events", [])),
        },
    }
    return {
        "axes": axes,
        "reference_axes": reference_axes,
        "axis_correctness": {
            key: axes[key] == reference_axes[key] for key in axes
        },
        "diagnostics": diagnostics,
    }
