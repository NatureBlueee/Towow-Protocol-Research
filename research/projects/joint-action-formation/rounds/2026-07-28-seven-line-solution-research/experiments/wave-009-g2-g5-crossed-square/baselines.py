"""Method-neutral mature baseline implementations over one public packet."""

from __future__ import annotations

from typing import Any, Callable

from common import canonical_bytes, sha256_hex, verify_envelope


def _verified(
    section: dict[str, Any],
    *,
    domain: str,
) -> list[dict[str, Any]]:
    contract = section["contract"]
    return [
        event
        for event in section["events"]
        if verify_envelope(event, contract, expected_domain=domain)
    ]


def _bound_events(
    packet: dict[str, Any],
    section: dict[str, Any],
    *,
    domain: str,
    broker_issuer: str,
) -> tuple[list[dict[str, Any]], str | None]:
    contract = section.get("contract", {})
    context_envelope = section.get("section_context")
    if not isinstance(context_envelope, dict) or not verify_envelope(
        context_envelope,
        contract,
        expected_domain=domain,
    ):
        return [], "SECTION_CONTEXT_INVALID"
    if (
        context_envelope.get("issuer") != broker_issuer
        or context_envelope.get("kind") != "SECTION_CONTEXT"
    ):
        return [], "SECTION_CONTEXT_INVALID"
    recomputed_semantic_input = sha256_hex(
        canonical_bytes(
            {
                "world_id": packet.get("world_id"),
                "task": packet.get("task"),
                "presentation": packet.get("presentation"),
            }
        )
    )
    context = context_envelope.get("body")
    if (
        context != packet.get("issuance_context")
        or packet.get("semantic_input_sha256")
        != recomputed_semantic_input
        or context.get("semantic_input_sha256")
        != recomputed_semantic_input
        or context.get("world_id") != packet.get("world_id")
        or context.get("task_fingerprint")
        != packet.get("task", {}).get("task_fingerprint")
    ):
        return [], "SECTION_CONTEXT_INVALID"
    if domain == "TOWOW-WAVE009-RELATION":
        if (
            context.get("current_relation_version")
            != section.get("current_version")
        ):
            return [], "SECTION_CONTEXT_INVALID"
    else:
        relation = packet.get("relation", {})
        if (
            context.get("current_relation_version")
            != section.get("current_relation_version")
            or context.get("current_relation_version")
            != relation.get("current_version")
            or context.get("current_authority_head")
            != section.get("current_revoke_head")
            or context.get("current_authority_head")
            != contract.get("current_revoke_head")
        ):
            return [], "SECTION_CONTEXT_INVALID"
    events = _verified(section, domain=domain)
    if len(events) != len(section.get("events", [])):
        return [], "EVENT_CONTEXT_OWNERSHIP_INVALID"
    context_sha256 = context_envelope["payload_sha256"]
    if any(
        event.get("body", {}).get("world_id") != packet.get("world_id")
        or event.get("body", {}).get("task_fingerprint")
        != packet.get("task", {}).get("task_fingerprint")
        or event.get("body", {}).get("issuance_context_sha256")
        != context_sha256
        or event.get("body", {}).get("event_owner_domain") != domain
        for event in events
    ):
        return [], "EVENT_CONTEXT_OWNERSHIP_INVALID"
    return events, None


def _relation_sequence_valid(
    events: list[dict[str, Any]],
    task: dict[str, Any],
) -> bool:
    kinds = [event["kind"] for event in events]
    ranks = {
        "PROPOSAL": 0,
        "ACK": 1,
        "EXPLAIN_BACK": 2,
        "STANCE": 3,
        "COUNTER": 4,
        "RELATION_VERSION": 5,
    }
    if any(kind not in ranks for kind in kinds):
        return False
    principals = len(task["principals"])
    return all(
        [
            kinds == sorted(kinds, key=lambda kind: ranks[kind]),
            kinds[:1] == ["PROPOSAL"],
            kinds[-1:] == ["RELATION_VERSION"],
            kinds.count("PROPOSAL") == 1,
            kinds.count("ACK") == principals,
            kinds.count("EXPLAIN_BACK") == principals,
            kinds.count("STANCE") == principals,
            kinds.count("COUNTER") == 1,
            kinds.count("RELATION_VERSION") == 1,
        ]
    )


def _authority_sequence_valid(
    events: list[dict[str, Any]],
    task: dict[str, Any],
) -> bool:
    principals = task["principals"]
    prefix = events[: 2 * len(principals)]
    if len(prefix) != 2 * len(principals):
        return False
    for index, principal in enumerate(principals):
        mandate = prefix[index * 2]
        commitment = prefix[index * 2 + 1]
        if (
            mandate["kind"] != "MANDATE"
            or mandate["body"].get("principal_id") != principal
            or commitment["kind"] != "COMMITMENT"
            or commitment["body"].get("principal_id") != principal
        ):
            return False
    tail = events[2 * len(principals) :]
    if not tail or tail[-1]["kind"] != "STANDING":
        return False
    middle_kinds = [event["kind"] for event in tail[:-1]]
    if middle_kinds.count("REVOCATION") > 1:
        return False
    if "REVOCATION" in middle_kinds and middle_kinds[0] != "REVOCATION":
        return False
    reservation_kinds = [
        kind
        for kind in middle_kinds
        if kind in {"RESERVATION", "RESERVATION_CONFLICT"}
    ]
    if len(reservation_kinds) not in {1, 2}:
        return False
    if middle_kinds != (
        (["REVOCATION"] if "REVOCATION" in middle_kinds else [])
        + reservation_kinds
    ):
        return False
    return (
        reservation_kinds.count("RESERVATION") == 1
        and reservation_kinds.count("RESERVATION_CONFLICT") in {0, 1}
        and sum(event["kind"] == "STANDING" for event in events) == 1
    )


def center_relation_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B0 direct decision-table path over independently verified evidence."""
    section = packet["relation"]
    task = packet["task"]
    events, context_error = _bound_events(
        packet,
        section,
        domain="TOWOW-WAVE009-RELATION",
        broker_issuer="REL-BROKER",
    )
    if context_error is not None:
        return _relation_unknown(section, context_error)
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_kind.setdefault(event["kind"], []).append(event)
    versions = [
        event
        for event in by_kind.get("RELATION_VERSION", [])
        if event["body"].get("relation_version")
        == section["current_version"]
    ]
    if len(versions) != 1:
        return _relation_unknown(section)
    version = versions[0]["body"]
    principals = set(task["principals"])

    def exact_principals(kind: str) -> bool:
        rows = by_kind.get(kind, [])
        return (
            len(rows) == len(principals)
            and {row["body"].get("principal_id") for row in rows}
            == principals
            and all(
                row["body"].get("relation_version")
                == section["current_version"]
                for row in rows
            )
        )

    ack_valid = exact_principals("ACK") and all(
        row["body"].get("ack_scope") == "RECEIPT_ONLY"
        for row in by_kind.get("ACK", [])
    )
    explain_valid = exact_principals("EXPLAIN_BACK") and all(
        row["body"].get("understanding_hash")
        == version.get("source_semantic_fingerprint")
        for row in by_kind.get("EXPLAIN_BACK", [])
    )
    stance_valid = exact_principals("STANCE") and all(
        row["body"].get("stance") == "ACCEPT_CURRENT_RELATION_VERSION"
        for row in by_kind.get("STANCE", [])
    )
    horizon = version.get("horizon")
    if horizon == "ONE_SHOT":
        horizon_valid = (
            version.get("reuse_limit") == 0
            and version.get("exit_rule") == "END_AFTER_OPERATION"
        )
    elif horizon == "BOUNDED":
        horizon_valid = (
            isinstance(version.get("reuse_limit"), int)
            and version["reuse_limit"] > 0
            and isinstance(version.get("expiry_step"), int)
            and version["expiry_step"] > version.get("current_step", 0)
            and version.get("purpose") == task["purpose"]
            and version.get("exit_rule") == "END_AT_LIMIT_OR_EXPIRY"
        )
    elif horizon == "DURABLE":
        horizon_valid = all(
            [
                version.get("amendment_governance")
                == "ALL_AFFECTED_PRINCIPALS_SIGN_MATERIAL_CHANGE",
                version.get("evidence_governance")
                == "PERIODIC_CURRENT_VERSION_READBACK",
                isinstance(version.get("review_interval_steps"), int),
                version.get("exit_rule")
                == "PRINCIPAL_WITHDRAWAL_OR_SUPERSEDING_VERSION",
            ]
        )
    else:
        horizon_valid = False
    semantic_loss = (
        version.get("compiled_semantic_fingerprint")
        != version.get("source_semantic_fingerprint")
    )
    material_change = version.get("material_change") is True
    sequence_valid = _relation_sequence_valid(events, task)
    formed = all(
        [
            sequence_valid,
            ack_valid,
            explain_valid,
            stance_valid,
            horizon_valid,
            not semantic_loss,
            not material_change,
        ]
    )
    if semantic_loss or material_change:
        stage = "REOPEN_REQUIRED"
    else:
        stage = "FORMED" if formed else "PROPOSED"
    return {
        "stage": stage,
        "formed": formed,
        "horizon": horizon,
        "version_id": section["current_version"],
        "material_change": material_change,
        "semantic_loss": semantic_loss,
        "stale": False,
        "source_provenance": version.get("source_provenance"),
        "opposition_preserved": (
            version.get("opposition_preserved") is True
        ),
        "context_error": (
            None
            if sequence_valid
            else "RELATION_SEQUENCE_OR_CARDINALITY_INVALID"
        ),
    }


def _relation_unknown(
    section: dict[str, Any],
    context_error: str | None = None,
) -> dict[str, Any]:
    return {
        "stage": "UNKNOWN",
        "formed": False,
        "horizon": None,
        "version_id": section.get("current_version"),
        "material_change": False,
        "semantic_loss": False,
        "stale": True,
        "source_provenance": None,
        "opposition_preserved": False,
        "context_error": context_error,
    }


def _relation_component_facts(
    packet: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    section = packet["relation"]
    task = packet["task"]
    events, context_error = _bound_events(
        packet,
        section,
        domain="TOWOW-WAVE009-RELATION",
        broker_issuer="REL-BROKER",
    )
    if context_error is not None:
        return None, context_error
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_kind.setdefault(event["kind"], []).append(event)
    versions = [
        event
        for event in by_kind.get("RELATION_VERSION", [])
        if event["body"].get("relation_version")
        == section["current_version"]
    ]
    if len(versions) != 1:
        return None, "CURRENT_RELATION_VERSION_NOT_UNIQUE"
    version = versions[0]["body"]
    principals = set(task["principals"])

    def exact_principals(kind: str) -> bool:
        rows = by_kind.get(kind, [])
        return (
            len(rows) == len(principals)
            and {row["body"].get("principal_id") for row in rows}
            == principals
            and all(
                row["body"].get("relation_version")
                == section["current_version"]
                for row in rows
            )
        )

    horizon = version.get("horizon")
    horizon_valid = False
    if horizon == "ONE_SHOT":
        horizon_valid = (
            version.get("reuse_limit") == 0
            and version.get("exit_rule") == "END_AFTER_OPERATION"
        )
    elif horizon == "BOUNDED":
        horizon_valid = (
            isinstance(version.get("reuse_limit"), int)
            and version["reuse_limit"] > 0
            and isinstance(version.get("expiry_step"), int)
            and version["expiry_step"] > version.get("current_step", 0)
            and version.get("purpose") == task["purpose"]
            and version.get("exit_rule") == "END_AT_LIMIT_OR_EXPIRY"
        )
    elif horizon == "DURABLE":
        horizon_valid = all(
            [
                version.get("amendment_governance")
                == "ALL_AFFECTED_PRINCIPALS_SIGN_MATERIAL_CHANGE",
                version.get("evidence_governance")
                == "PERIODIC_CURRENT_VERSION_READBACK",
                isinstance(version.get("review_interval_steps"), int),
                version.get("exit_rule")
                == "PRINCIPAL_WITHDRAWAL_OR_SUPERSEDING_VERSION",
            ]
        )
    facts = {
        "section": section,
        "version": version,
        "horizon": horizon,
        "ack_valid": exact_principals("ACK")
        and all(
            row["body"].get("ack_scope") == "RECEIPT_ONLY"
            for row in by_kind.get("ACK", [])
        ),
        "explain_valid": exact_principals("EXPLAIN_BACK")
        and all(
            row["body"].get("understanding_hash")
            == version.get("source_semantic_fingerprint")
            for row in by_kind.get("EXPLAIN_BACK", [])
        ),
        "stance_valid": exact_principals("STANCE")
        and all(
            row["body"].get("stance")
            == "ACCEPT_CURRENT_RELATION_VERSION"
            for row in by_kind.get("STANCE", [])
        ),
        "horizon_valid": horizon_valid,
        "semantic_loss": (
            version.get("compiled_semantic_fingerprint")
            != version.get("source_semantic_fingerprint")
        ),
        "material_change": version.get("material_change") is True,
        "proposal_valid": (
            len(by_kind.get("PROPOSAL", [])) == 1
            and events
            and events[0]["kind"] == "PROPOSAL"
        ),
        "counter_valid": len(by_kind.get("COUNTER", [])) == 1,
        "sequence_valid": _relation_sequence_valid(events, task),
    }
    return facts, None


def _relation_output_from_components(
    facts: dict[str, Any],
    *,
    formed: bool,
) -> dict[str, Any]:
    version = facts["version"]
    if facts["semantic_loss"] or facts["material_change"]:
        stage = "REOPEN_REQUIRED"
    else:
        stage = "FORMED" if formed else "PROPOSED"
    return {
        "stage": stage,
        "formed": formed,
        "horizon": facts["horizon"],
        "version_id": facts["section"]["current_version"],
        "material_change": facts["material_change"],
        "semantic_loss": facts["semantic_loss"],
        "stale": False,
        "source_provenance": version.get("source_provenance"),
        "opposition_preserved": (
            version.get("opposition_preserved") is True
        ),
        "context_error": (
            None
            if facts["sequence_valid"]
            else "RELATION_SEQUENCE_OR_CARDINALITY_INVALID"
        ),
    }


def workflow_relation_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B1 explicit workflow path; each state gate must be entered in order."""
    facts, error = _relation_component_facts(packet)
    if facts is None:
        return _relation_unknown(packet["relation"], error)
    workflow_state = "START"
    for next_state, predicate in [
        ("PROPOSAL_RECEIVED", facts["proposal_valid"]),
        ("SEQUENCE_AND_CARDINALITY_VALID", facts["sequence_valid"]),
        ("ALL_ACKS_RECEIVED", facts["ack_valid"]),
        ("EXPLAIN_BACK_COMPLETE", facts["explain_valid"]),
        ("STANCES_BOUND", facts["stance_valid"]),
        ("HORIZON_GOVERNED", facts["horizon_valid"]),
        ("SEMANTICS_RETAINED", not facts["semantic_loss"]),
        ("NO_MATERIAL_REOPEN", not facts["material_change"]),
        ("COUNTER_RECORDED", facts["counter_valid"]),
    ]:
        if not predicate:
            break
        workflow_state = next_state
    formed = workflow_state == "COUNTER_RECORDED"
    output = _relation_output_from_components(facts, formed=formed)
    output["workflow_state"] = workflow_state
    return output


def composition_relation_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B5 composition of separately inspectable relation sub-capabilities."""
    facts, error = _relation_component_facts(packet)
    if facts is None:
        return _relation_unknown(packet["relation"], error)
    components = {
        "proposal_and_sequence_component": facts["sequence_valid"],
        "receipt_component": facts["ack_valid"],
        "understanding_component": facts["explain_valid"],
        "stance_component": facts["stance_valid"],
        "horizon_component": facts["horizon_valid"],
        "semantic_retention_component": not facts["semantic_loss"],
        "materiality_component": not facts["material_change"],
    }
    output = _relation_output_from_components(
        facts,
        formed=all(components.values()),
    )
    output["component_results"] = components
    return output


def receipt_only_relation(packet: dict[str, Any]) -> dict[str, Any]:
    section = packet["relation"]
    events, context_error = _bound_events(
        packet,
        section,
        domain="TOWOW-WAVE009-RELATION",
        broker_issuer="REL-BROKER",
    )
    if context_error is not None:
        return _relation_unknown(section, context_error)
    ack_count = sum(event["kind"] == "ACK" for event in events)
    result = _relation_unknown(section)
    result["stage"] = "ACKNOWLEDGED" if ack_count else "PROPOSED"
    return result


def center_authority_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B0 direct decision-table path over the whole authority section."""
    section = packet["authority"]
    task = packet["task"]
    events, context_error = _bound_events(
        packet,
        section,
        domain="TOWOW-WAVE009-AUTHORITY",
        broker_issuer="AUTH-BROKER",
    )
    if context_error is not None:
        return {
            "permit_status": "DENY",
            "mandate_valid": False,
            "commitment_valid": False,
            "reservation_valid": False,
            "standing_valid": False,
            "authority_chain_valid": False,
            "error": context_error,
            "current_relation_version": section.get(
                "current_relation_version"
            ),
        }
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_kind.setdefault(event["kind"], []).append(event)
    principals = set(task["principals"])
    sequence_valid = _authority_sequence_valid(events, task)
    mandates = by_kind.get("MANDATE", [])
    controller_error = any(
        event["issuer"] != f"AUTH-{event['body'].get('principal_id')}"
        for event in mandates
    )
    stale_error = any(
        event["body"].get("relation_version")
        != section["current_relation_version"]
        for event in mandates
    )
    revoke_error = bool(by_kind.get("REVOCATION")) or any(
        event["body"].get("revoke_head") != section["current_revoke_head"]
        for event in mandates
    )
    exact_scope = all(
        [
            event["body"].get("task_fingerprint")
            == task["task_fingerprint"]
            and event["body"].get("action") == task["required_action"]
            and event["body"].get("purpose") == task["purpose"]
            and event["body"].get("resource") == task["resource"]
            and event["body"].get("time_window") == task["time_window"]
            and event["body"].get("counterparty")
            == task["counterparty"]
            for event in mandates
        ]
    )
    mandate_valid = (
        sequence_valid
        and len(mandates) == len(principals)
        and {row["body"].get("principal_id") for row in mandates}
        == principals
        and exact_scope
        and not controller_error
        and not stale_error
        and not revoke_error
    )
    commitments = by_kind.get("COMMITMENT", [])
    commitment_valid = (
        len(commitments) == len(principals)
        and {row["body"].get("principal_id") for row in commitments}
        == principals
        and all(
            row["issuer"] == f"AUTH-{row['body'].get('principal_id')}"
            and row["body"].get("action") == task["required_action"]
            and row["body"].get("purpose") == task["purpose"]
            and row["body"].get("status") == "PROMISED_NOT_EXECUTED"
            for row in commitments
        )
    )
    reservations = by_kind.get("RESERVATION", [])
    conflicts = by_kind.get("RESERVATION_CONFLICT", [])
    reservation_valid = (
        len(reservations) == 1
        and not conflicts
        and reservations[0]["body"].get("status") == "RESERVED"
        and reservations[0]["body"].get("resource") == task["resource"]
        and reservations[0]["body"].get("time_window")
        == task["time_window"]
        and reservations[0]["body"].get("purpose") == task["purpose"]
        and reservations[0]["body"].get("relation_version")
        == section["current_relation_version"]
    )
    standings = by_kind.get("STANDING", [])
    standing_valid = (
        len(standings) == 1
        and standings[0]["body"].get("active") is True
        and standings[0]["body"].get("acceptance_authority")
        == task["acceptance_authority"]
    )
    if not sequence_valid:
        error = "AUTHORITY_SEQUENCE_OR_CARDINALITY_INVALID"
    elif controller_error:
        error = "CONTROLLER_NOT_PRINCIPAL"
    elif stale_error:
        error = "STALE_RELATION_VERSION"
    elif revoke_error:
        error = "MANDATE_REVOKED"
    elif conflicts:
        error = "DUPLICATE_RESERVATION_CONFLICT"
    elif not mandate_valid:
        error = "MANDATE_INVALID"
    elif not commitment_valid:
        error = "COMMITMENT_INVALID"
    elif not reservation_valid:
        error = "RESERVATION_INVALID"
    elif not standing_valid:
        error = "STANDING_INVALID"
    else:
        error = None
    return {
        "permit_status": "PERMIT" if mandate_valid else "DENY",
        "mandate_valid": mandate_valid,
        "commitment_valid": commitment_valid,
        "reservation_valid": reservation_valid,
        "standing_valid": standing_valid,
        "authority_chain_valid": all(
            [
                mandate_valid,
                commitment_valid,
                reservation_valid,
                standing_valid,
            ]
        ),
        "error": error,
        "current_relation_version": section["current_relation_version"],
    }


def _authority_component_facts(
    packet: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    section = packet["authority"]
    task = packet["task"]
    events, context_error = _bound_events(
        packet,
        section,
        domain="TOWOW-WAVE009-AUTHORITY",
        broker_issuer="AUTH-BROKER",
    )
    if context_error is not None:
        return None, context_error
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_kind.setdefault(event["kind"], []).append(event)
    principals = set(task["principals"])
    sequence_valid = _authority_sequence_valid(events, task)
    mandates = by_kind.get("MANDATE", [])
    controller_error = any(
        event["issuer"] != f"AUTH-{event['body'].get('principal_id')}"
        for event in mandates
    )
    stale_error = any(
        event["body"].get("relation_version")
        != section["current_relation_version"]
        for event in mandates
    )
    revoke_error = bool(by_kind.get("REVOCATION")) or any(
        event["body"].get("revoke_head")
        != section["current_revoke_head"]
        for event in mandates
    )
    mandate_valid = all(
        [
            sequence_valid,
            len(mandates) == len(principals),
            {row["body"].get("principal_id") for row in mandates}
            == principals,
            not controller_error,
            not stale_error,
            not revoke_error,
            all(
                row["body"].get("action") == task["required_action"]
                and row["body"].get("purpose") == task["purpose"]
                and row["body"].get("resource") == task["resource"]
                and row["body"].get("time_window")
                == task["time_window"]
                and row["body"].get("counterparty")
                == task["counterparty"]
                for row in mandates
            ),
        ]
    )
    commitments = by_kind.get("COMMITMENT", [])
    commitment_valid = (
        len(commitments) == len(principals)
        and {row["body"].get("principal_id") for row in commitments}
        == principals
        and all(
            row["issuer"] == f"AUTH-{row['body'].get('principal_id')}"
            and row["body"].get("action") == task["required_action"]
            and row["body"].get("purpose") == task["purpose"]
            and row["body"].get("status") == "PROMISED_NOT_EXECUTED"
            for row in commitments
        )
    )
    reservations = by_kind.get("RESERVATION", [])
    conflicts = by_kind.get("RESERVATION_CONFLICT", [])
    reservation_exists = (
        len(reservations) == 1
        and reservations[0]["body"].get("status") == "RESERVED"
        and reservations[0]["body"].get("resource") == task["resource"]
        and reservations[0]["body"].get("time_window")
        == task["time_window"]
        and reservations[0]["body"].get("purpose") == task["purpose"]
        and reservations[0]["body"].get("relation_version")
        == section["current_relation_version"]
    )
    reservation_unique = reservation_exists and not conflicts
    standings = by_kind.get("STANDING", [])
    standing_valid = (
        len(standings) == 1
        and standings[0]["body"].get("active") is True
        and standings[0]["body"].get("acceptance_authority")
        == task["acceptance_authority"]
    )
    return {
        "section": section,
        "mandate_valid": mandate_valid,
        "commitment_valid": commitment_valid,
        "reservation_exists": reservation_exists,
        "reservation_unique": reservation_unique,
        "standing_valid": standing_valid,
        "controller_error": controller_error,
        "stale_error": stale_error,
        "revoke_error": revoke_error,
        "duplicate_error": bool(conflicts),
        "sequence_valid": sequence_valid,
    }, None


def _authority_error(
    facts: dict[str, Any],
    *,
    reservation_valid: bool,
) -> str | None:
    if not facts["sequence_valid"]:
        return "AUTHORITY_SEQUENCE_OR_CARDINALITY_INVALID"
    if facts["controller_error"]:
        return "CONTROLLER_NOT_PRINCIPAL"
    if facts["stale_error"]:
        return "STALE_RELATION_VERSION"
    if facts["revoke_error"]:
        return "MANDATE_REVOKED"
    if facts["duplicate_error"] and not reservation_valid:
        return "DUPLICATE_RESERVATION_CONFLICT"
    if not facts["mandate_valid"]:
        return "MANDATE_INVALID"
    if not facts["commitment_valid"]:
        return "COMMITMENT_INVALID"
    if not reservation_valid:
        return "RESERVATION_INVALID"
    if not facts["standing_valid"]:
        return "STANDING_INVALID"
    return None


def _invalid_authority_context(
    section: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    return {
        "permit_status": "DENY",
        "mandate_valid": False,
        "commitment_valid": False,
        "reservation_valid": False,
        "standing_valid": False,
        "authority_chain_valid": False,
        "error": error,
        "current_relation_version": section.get(
            "current_relation_version"
        ),
    }


def workflow_authority_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B1 workflow path, intentionally lacking atomic conflict adjudication."""
    facts, error = _authority_component_facts(packet)
    if facts is None:
        return _invalid_authority_context(packet["authority"], error)
    workflow_states = []
    for state, predicate in [
        ("SEQUENCE_AND_CARDINALITY_VALID", facts["sequence_valid"]),
        ("MANDATE_APPROVED", facts["mandate_valid"]),
        ("COMMITMENT_RECORDED", facts["commitment_valid"]),
        # This mature-workflow-only path observes one reservation receipt but
        # cannot adjudicate a concurrent conflict without B4's ledger.
        ("RESERVATION_RECEIVED", facts["reservation_exists"]),
        ("STANDING_CONFIRMED", facts["standing_valid"]),
    ]:
        if not predicate:
            break
        workflow_states.append(state)
    reservation_valid = facts["reservation_exists"]
    chain = all(
        [
            facts["mandate_valid"],
            facts["commitment_valid"],
            reservation_valid,
            facts["standing_valid"],
        ]
    )
    result = {
        "permit_status": (
            "PERMIT" if facts["mandate_valid"] else "DENY"
        ),
        "mandate_valid": facts["mandate_valid"],
        "commitment_valid": facts["commitment_valid"],
        "reservation_valid": reservation_valid,
        "standing_valid": facts["standing_valid"],
        "authority_chain_valid": chain,
        "error": _authority_error(
            facts,
            reservation_valid=reservation_valid,
        ),
        "current_relation_version": facts["section"][
            "current_relation_version"
        ],
        "workflow_states": workflow_states,
    }
    if facts["duplicate_error"] and reservation_valid:
        result["error"] = None
    return result


def composition_authority_path(packet: dict[str, Any]) -> dict[str, Any]:
    """B5 composition of policy, commitment, ledger and standing outputs."""
    facts, error = _authority_component_facts(packet)
    if facts is None:
        return _invalid_authority_context(packet["authority"], error)
    component_results = {
        "sequence_and_cardinality_component": facts["sequence_valid"],
        "policy_component": facts["mandate_valid"],
        "commitment_component": facts["commitment_valid"],
        "atomic_reservation_component": facts["reservation_unique"],
        "standing_component": facts["standing_valid"],
    }
    reservation_valid = facts["reservation_unique"]
    return {
        "permit_status": (
            "PERMIT" if facts["mandate_valid"] else "DENY"
        ),
        "mandate_valid": facts["mandate_valid"],
        "commitment_valid": facts["commitment_valid"],
        "reservation_valid": reservation_valid,
        "standing_valid": facts["standing_valid"],
        "authority_chain_valid": all(component_results.values()),
        "error": _authority_error(
            facts,
            reservation_valid=reservation_valid,
        ),
        "current_relation_version": facts["section"][
            "current_relation_version"
        ],
        "component_results": component_results,
    }


def clm_authority(packet: dict[str, Any]) -> dict[str, Any]:
    result = composition_authority_path(packet)
    # CLM/approval records promises but does not itself establish a
    # transactional reservation.  It therefore reports the distinction.
    result["reservation_valid"] = False
    result["authority_chain_valid"] = False
    if result["error"] is None:
        result["error"] = "RESERVATION_NOT_ESTABLISHED_BY_CLM"
    return result


def policy_authority(packet: dict[str, Any]) -> dict[str, Any]:
    result = composition_authority_path(packet)
    result["commitment_valid"] = False
    result["reservation_valid"] = False
    result["authority_chain_valid"] = False
    if result["error"] is None:
        result["error"] = "POLICY_PERMIT_NOT_COMMITMENT_OR_RESERVATION"
    return result


def _compose(
    packet: dict[str, Any],
    relation_fn: Callable[[dict[str, Any]], dict[str, Any]],
    authority_fn: Callable[[dict[str, Any]], dict[str, Any]],
    mechanism_trace: list[str],
) -> dict[str, Any]:
    return {
        "relation": relation_fn(packet),
        "authority": authority_fn(packet),
        "mechanism_trace": mechanism_trace,
        "candidate_claimed_identity": packet.get(
            "candidate_claimed_identity"
        ),
    }


def run_baseline(
    baseline_id: str,
    packet: dict[str, Any],
) -> dict[str, Any]:
    implementations: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "B0": lambda value: _compose(
            value,
            center_relation_path,
            center_authority_path,
            ["STRONG_CENTER", "HITL_REVIEW", "TRANSACTIONAL_LEDGER"],
        ),
        "B1": lambda value: _compose(
            value,
            workflow_relation_path,
            workflow_authority_path,
            ["CMMN", "BPMN", "DMN", "HITL"],
        ),
        "B2": lambda value: _compose(
            value,
            workflow_relation_path,
            clm_authority,
            ["CLM", "APPROVAL_WORKFLOW"],
        ),
        "B3A": lambda value: _compose(
            value,
            receipt_only_relation,
            policy_authority,
            ["OPENFGA", "CEDAR"],
        ),
        "B3B": lambda value: _compose(
            value,
            receipt_only_relation,
            policy_authority,
            ["OPENFGA", "OPA"],
        ),
        "B4": lambda value: _compose(
            value,
            receipt_only_relation,
            composition_authority_path,
            ["COMMITMENT_STORE", "TRANSACTIONAL_RESERVATION"],
        ),
        "B5": lambda value: _compose(
            value,
            composition_relation_path,
            composition_authority_path,
            [
                "WORKFLOW",
                "CLM",
                "POLICY_ENGINE",
                "COMMITMENT_STORE",
                "TRANSACTIONAL_RESERVATION",
                "HITL",
            ],
        ),
    }
    try:
        return implementations[baseline_id](packet)
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_BASELINE:{baseline_id}") from exc
