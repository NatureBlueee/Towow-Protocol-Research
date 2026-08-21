"""Four equal-envelope G2-O1 method arms.

These methods only consume public worlds and signed owner evidence.  They do
not load the private oracle and deliberately keep Authority topology separate
from state placement.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from g2o1.actors import digest, verified_events


ARM_IDS = (
    "STRUCTURED_HUMAN_INSTITUTION",
    "EQUAL_ENVELOPE_STRONG_CENTER",
    "ACTUAL_MATURE_COMPOSITION",
    "SIGNED_REPLICATED_STATE",
)


def _relation(world: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(
        world.get("candidate_relation")
        or world.get("relation")
        or world.get("base_relation")
        or {}
    )


def _required_principals(world: dict[str, Any]) -> list[str]:
    return list(
        world.get("principal_ids")
        or world.get("principals")
        or []
    )


def _event_index(
    owner_packet: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    events = verified_events(
        owner_packet.get("owner_events", []),
        owner_packet.get("public_keys", {}),
    )
    by_action: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        by_action.setdefault(event["action"], []).append(event)
    return events, by_action


def _common_candidate(
    arm: str,
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    relation = _relation(world)
    relation_version = str(relation.get("version", "UNSPECIFIED"))
    relation_digest = digest(relation)
    principals = _required_principals(world)
    events, by_action = _event_index(owner_packet)

    schema_events = by_action.get("SCHEMA_OBSERVATION", [])
    proposed_schema = copy.deepcopy(
        (world.get("base_relation") or {}).get("schema", {})
    )
    schema_deltas: list[dict[str, Any]] = []
    formed_schema_ids: set[str] = set()
    for event in schema_events:
        delta = event["body"].get("schema_delta")
        if isinstance(delta, dict):
            schema_deltas.append(delta)
            for field in delta.get("add", []):
                field_id = str(field)
                formed_schema_ids.add(field_id)
                inserted = False
                for section, values in relation.get("schema", {}).items():
                    if not isinstance(values, list):
                        continue
                    match = next(
                        (
                            item
                            for item in values
                            if isinstance(item, dict)
                            and str(item.get("id")) == field_id
                        ),
                        None,
                    )
                    if match is not None:
                        target = proposed_schema.setdefault(section, [])
                        if not any(
                            isinstance(item, dict)
                            and str(item.get("id")) == field_id
                            for item in target
                        ):
                            target.append(copy.deepcopy(match))
                        inserted = True
                        break
                if not inserted:
                    proposed_schema.setdefault("open_schema", []).append(
                        {
                            "id": field_id,
                            "formed_by": event["actor_id"],
                        }
                    )
            for field in delta.get("remove", []):
                field_id = str(field)
                for section, values in list(proposed_schema.items()):
                    if isinstance(values, list):
                        proposed_schema[section] = [
                            item
                            for item in values
                            if not (
                                isinstance(item, dict)
                                and str(item.get("id")) == field_id
                            )
                        ]

    current_events = [
        event
        for event in events
        if event.get("relation_version") == relation_version
        and event.get("version_digest") == relation_digest
    ]
    private_columns = [
        event["body"]
        for event in current_events
        if event["action"] == "PRIVATE_COLUMN"
    ]
    opposition = [
        {
            "actor_id": event["actor_id"],
            "principal_id": event["principal_id"],
            "claim_scope": event["body"].get("claim_scope"),
            "opposition": event["body"].get("opposition"),
            "evidence_digest": event["payload_digest"],
        }
        for event in current_events
        if event["action"] in {"STANCE", "OPPOSITION"}
        and (
            event["body"].get("opposition")
            or event["body"].get("stance") in {"OPPOSE", "PARTIAL"}
        )
    ]
    owner_refs = [
        {
            "actor_id": event["actor_id"],
            "principal_id": event["principal_id"],
            "action": event["action"],
            "evidence_digest": event["payload_digest"],
        }
        for event in events
    ]
    return {
        "arm": arm,
        "world_id": world.get("world_id"),
        "authority_topology": world.get(
            "authority_topology", "UNSPECIFIED"
        ),
        "state_placement": (
            "REPLICATED"
            if arm == "SIGNED_REPLICATED_STATE"
            else "CENTRAL"
        ),
        "relation_version": relation_version,
        "relation_digest": relation_digest,
        "proposed_schema": proposed_schema,
        "schema_deltas": schema_deltas,
        "formed_schema_ids": sorted(formed_schema_ids),
        "required_principals": principals,
        "owner_evidence_refs": owner_refs,
        "owner_events": current_events,
        "private_columns": private_columns,
        "opposition": opposition,
        "decision": "EVALUATE_OWNER_EVIDENCE",
        "fail_closed": True,
        "operations": [],
        "disclosure_units": sum(
            int(event["body"].get("disclosure_units", 0) or 0)
            for event in current_events
        ),
    }


def _platform_direct(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    """Bypass Relation machinery for a precompiled platform transaction."""
    candidate.update(
        {
            "platform_direct": True,
            "relation_artifact_created": False,
            "schema_reopen": False,
            "schema_deltas": [],
            "formed_schema_ids": [],
            "proposed_schema": {},
            "operations": [
                "READ_PLATFORM_OFFER",
                "RECORD_PRINCIPAL_PLATFORM_DECISION",
                "CHECK_PLATFORM_SCOPED_AUTHORITY",
                "READ_PLATFORM_TARGET_OUTCOME",
            ],
        }
    )
    return candidate


def _is_platform_control(world: dict[str, Any]) -> bool:
    return str(world.get("family", "")).upper() == "T5_CONTROL"


def structured_human_institution(
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate = _common_candidate(
        "STRUCTURED_HUMAN_INSTITUTION", world, owner_packet
    )
    if _is_platform_control(world):
        return _platform_direct(candidate)
    candidate["operations"] = [
        "OPEN_CASE_FILE",
        "RECORD_SCHEMA_AMENDMENTS",
        "SEPARATE_EXPLAIN_BACK",
        "COLLECT_EXACT_VERSION_STANCES",
        "HUMAN_CONSTITUTION_REVIEW",
        "AUTHORITY_AND_ACCEPTANCE_READBACK",
    ]
    candidate["institutional_artifact"] = {
        "case_file_digest": digest(candidate["owner_evidence_refs"]),
        "reviewed_scopes": [
            event["body"].get("claim_scope")
            for event in candidate["owner_events"]
            if event["action"] in {"STANCE", "OPPOSITION"}
        ],
    }
    return candidate


def equal_envelope_strong_center(
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate = _common_candidate(
        "EQUAL_ENVELOPE_STRONG_CENTER", world, owner_packet
    )
    if _is_platform_control(world):
        return _platform_direct(candidate)
    candidate["operations"] = [
        "VERIFY_OWNER_SIGNATURES",
        "DIFF_OPEN_SCHEMA",
        "QUERY_LOCAL_COLUMN_ENDPOINT",
        "CHECK_EXACT_VERSION",
        "CHECK_AUTHORITY",
        "CHECK_TARGET_ACCEPTANCE",
    ]
    candidate["central_decision_record"] = {
        "input_digest": digest(candidate["owner_evidence_refs"]),
        "no_owner_substitution": True,
    }
    return candidate


def actual_mature_composition(
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate = _common_candidate(
        "ACTUAL_MATURE_COMPOSITION", world, owner_packet
    )
    if _is_platform_control(world):
        return _platform_direct(candidate)
    # The stages are separate artifacts, not aliases for one all-knowing rule.
    cmmn_case = {
        "schema": candidate["proposed_schema"],
        "schema_deltas": candidate["schema_deltas"],
        "owner_evidence_refs": candidate["owner_evidence_refs"],
    }
    clm_version = {
        "relation_version": candidate["relation_version"],
        "relation_digest": candidate["relation_digest"],
        "opposition": candidate["opposition"],
    }
    iam_gate = {
        "authority_evidence": [
            event["payload_digest"]
            for event in candidate["owner_events"]
            if event["action"] in {"AUTHORITY", "REVOCATION"}
        ]
    }
    ledger = {
        "reservations": [
            event["body"]
            for event in candidate["owner_events"]
            if event["action"] == "RESERVATION"
        ]
    }
    candidate["mature_components"] = {
        "CMMN_HITL": cmmn_case,
        "CLM_VERSIONED_WORKSPACE": clm_version,
        "IAM_POLICY": iam_gate,
        "TRANSACTIONAL_RESERVATION_LEDGER": ledger,
        "APPEND_ONLY_PROVENANCE": {
            "event_digests": [
                event["payload_digest"]
                for event in candidate["owner_events"]
            ]
        },
    }
    candidate["operations"] = [
        "CMMN_CASE_AMEND",
        "CLM_EXACT_VERSION_STANCE",
        "IAM_SCOPED_AUTHORITY_CHECK",
        "HITL_EXCEPTION_REVIEW",
        "TRANSACTIONAL_RESERVATION",
        "TARGET_ACCEPTANCE_READBACK",
    ]
    return candidate


def signed_replicated_state(
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    candidate = _common_candidate(
        "SIGNED_REPLICATED_STATE", world, owner_packet
    )
    if _is_platform_control(world):
        return _platform_direct(candidate)
    heads: dict[str, list[str]] = {}
    for event in candidate["owner_events"]:
        heads.setdefault(event["actor_id"], []).append(
            event["payload_digest"]
        )
    candidate["replicated_state"] = {
        "actor_heads": heads,
        "forks": {
            actor: values
            for actor, values in heads.items()
            if len(set(values[-2:])) > 1
            and any(
                event["body"].get("equivocation")
                for event in candidate["owner_events"]
                if event["actor_id"] == actor
            )
        },
        "recovery_rule": "MERGE_ONLY_NON_CONFLICTING_SIGNED_HEADS_ELSE_HALT",
    }
    candidate["operations"] = [
        "VERIFY_SIGNED_LOCAL_HEADS",
        "DETECT_FORK_OR_EQUIVOCATION",
        "MERGE_NON_CONFLICTING_SCHEMA_DELTAS",
        "REQUIRE_CURRENT_OWNER_STANCE",
        "FAIL_CLOSED_DURING_UNRESOLVED_PARTITION",
    ]
    return candidate


_METHODS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "STRUCTURED_HUMAN_INSTITUTION": structured_human_institution,
    "EQUAL_ENVELOPE_STRONG_CENTER": equal_envelope_strong_center,
    "ACTUAL_MATURE_COMPOSITION": actual_mature_composition,
    "SIGNED_REPLICATED_STATE": signed_replicated_state,
}


def run_method(
    arm: str,
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> dict[str, Any]:
    try:
        method = _METHODS[arm]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_ARM:{arm}") from exc
    return method(world, owner_packet)
