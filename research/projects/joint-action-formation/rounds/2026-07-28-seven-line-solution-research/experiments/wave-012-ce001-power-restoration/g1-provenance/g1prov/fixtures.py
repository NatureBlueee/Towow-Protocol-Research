from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .model import digest


EPISODE_IDS = (
    "E0-PLATFORM-DIRECT",
    "E1-EXTANT-MULTI-OWNER",
    "E2-CONDITION-FORMATION",
    "E3A-ACK-LOST-EFFECT",
    "E3B-ACK-LOST-NO-EFFECT",
    "E4-REVOKE-WITH-ALTERNATIVE",
    "E5-IMPOSSIBLE-REFUSAL",
    "E6-MIGRATION-REPLAY",
)

Q_TEXT = (
    "Before T0+90min provide Venue V Circuit C7 at 3kW +/-5% for at least "
    "45min, obey noise, safety, and exact-target limits, and energize no "
    "other circuit. The requester and Venue V must each provide Acceptance "
    "for the exact Q_version and the actual Effect; only afterwards may the "
    "corresponding Settlement begin."
)


def _prelude(episode_id: str) -> dict[str, Any]:
    return {
        "episode_id": episode_id,
        "stage": "CLARIFICATION_PRELUDE",
        "vague_request": "Today's community workshop must not be cancelled; handle it.",
        "questions": [
            "Which venue circuit is the exact target?",
            "What duration, power, safety, and noise constraints apply?",
        ],
        "intent_candidate_version": "Q@draft-3",
        "explain_back": Q_TEXT,
        "o_q_claim": "CLAIMED_EXACT_BYTES",
    }


def _interface(episode_id: str) -> dict[str, Any]:
    prelude = _prelude(episode_id)
    return {
        "boundary": "IntentAtCoordinationInterface",
        "episode_id": episode_id,
        "q_version": "Q@v1",
        "intent_text": Q_TEXT,
        "object_id": "Venue-V:Circuit-C7",
        "operation_id": "TEMPORARY_POWER:C7",
        "constraints": {
            "deadline": "T0+90min",
            "duration_min": 45,
            "power_kw": 3.0,
            "power_tolerance_pct": 5,
            "exact_target_only": True,
            "noise_policy": "VENUE-V-NOISE-v3",
            "safety_policy": "O_S-POLICY-v7",
        },
        "necessary_owner_roles": ["O_V", "O_R"],
        "clarification_prelude_receipt_hash": digest(prelude),
        "discovery_api": {
            "query_kinds": ["candidate", "resource", "partner"],
            "max_queries": 3,
            "purpose": "CE-001:G1-candidate-qualification",
        },
    }


def _record(
    episode_id: str,
    *,
    evidence_id: str,
    kind: str,
    subject_id: str,
    candidate_id: str,
    issuer_id: str,
    authority_id: str,
    source_id: str,
    recipient_id: str = "CE-001-COORDINATOR",
    purpose: str = "CE-001:G1-candidate-qualification",
    scope_version: str = "Q@v1",
    observed_at: str = "t0",
    existed_at_t0: bool = True,
    disclosure_allowed: bool = True,
    current: bool = True,
    via_operator: str | None = None,
    response: str = "WITNESS",
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "episode_id": episode_id,
        "kind": kind,
        "subject_id": subject_id,
        "candidate_id": candidate_id,
        "issuer_id": issuer_id,
        "authority_id": authority_id,
        "source_id": source_id,
        "recipient_id": recipient_id,
        "purpose": purpose,
        "scope_version": scope_version,
        "observed_at": observed_at,
        "existed_at_t0": existed_at_t0,
        "disclosure_allowed": disclosure_allowed,
        "current": current,
        "via_operator": via_operator,
        "response": response,
        "payload": {
            "candidate_id": candidate_id,
            "subject_id": subject_id,
            "object_id": "Venue-V:Circuit-C7",
            "q_version": "Q@v1",
        },
    }


def _bundle(
    episode_id: str,
    candidate_id: str,
    resource_id: str,
    partner_id: str,
    *,
    suffix: str,
    disclose: bool = True,
) -> list[dict[str, Any]]:
    return [
        _record(
            episode_id,
            evidence_id=f"{suffix}-C",
            kind="candidate",
            subject_id=candidate_id,
            candidate_id=candidate_id,
            issuer_id="O_R",
            authority_id="O_R",
            source_id=f"resource-catalog:{suffix}",
            disclosure_allowed=disclose,
        ),
        _record(
            episode_id,
            evidence_id=f"{suffix}-R",
            kind="resource",
            subject_id=resource_id,
            candidate_id=candidate_id,
            issuer_id="O_R",
            authority_id="O_R",
            source_id=f"resource-ledger:{suffix}",
            disclosure_allowed=disclose,
        ),
        _record(
            episode_id,
            evidence_id=f"{suffix}-P",
            kind="partner",
            subject_id=partner_id,
            candidate_id=candidate_id,
            issuer_id="O_V",
            authority_id="O_V",
            source_id=f"venue-ledger:{suffix}",
            disclosure_allowed=disclose,
        ),
    ]


@dataclass(frozen=True)
class World:
    prelude: dict[str, Any]
    interface: dict[str, Any]
    records: tuple[dict[str, Any], ...]
    operators: tuple[dict[str, Any], ...]
    l_benchmark: tuple[str, ...]
    d_actual: tuple[str, ...]
    expected: dict[str, dict[str, Any]]
    source_aliases: dict[str, str]
    authority_aliases: dict[str, str]
    min_unique_sources: int = 3


def make_world(episode_id: str) -> World:
    if episode_id not in EPISODE_IDS:
        raise KeyError(episode_id)
    prelude = _prelude(episode_id)
    interface = _interface(episode_id)
    operators: list[dict[str, Any]] = []

    if episode_id == "E0-PLATFORM-DIRECT":
        records = _bundle(
            episode_id, "CAND-VENUE-BATTERY", "BATTERY-V-01", "VENUE-OPS", suffix="E0"
        )
        l_benchmark = ("CAND-VENUE-BATTERY",)
        d_actual = l_benchmark
    elif episode_id == "E1-EXTANT-MULTI-OWNER":
        records = _bundle(
            episode_id, "CAND-RENTAL-A", "BATTERY-RENTAL-A", "PARTNER-A", suffix="E1"
        )
        l_benchmark = ("CAND-RENTAL-A",)
        d_actual = l_benchmark
    elif episode_id == "E2-CONDITION-FORMATION":
        candidate_id = "CAND-FORMED-A"
        records = _bundle(
            episode_id, candidate_id, "BATTERY-FORMED-A", "PARTNER-FORMED-A", suffix="E2"
        )[:2]
        created = _record(
            episode_id,
            evidence_id="E2-P",
            kind="partner",
            subject_id="PARTNER-FORMED-A",
            candidate_id=candidate_id,
            issuer_id="O_V",
            authority_id="O_V",
            source_id="venue-ledger:E2",
            observed_at="t1",
            existed_at_t0=False,
            via_operator="OP-PARTNER-INTRODUCTION",
        )
        operators = [
            {
                "operator_id": "OP-PARTNER-INTRODUCTION",
                "operator_type": "PARTNER_DISCLOSURE_FORMATION",
                "owner_id": "O_V",
                "authority_id": "O_V",
                "created_record": created,
            }
        ]
        l_benchmark = (candidate_id,)
        d_actual = ()
    elif episode_id in {"E3A-ACK-LOST-EFFECT", "E3B-ACK-LOST-NO-EFFECT"}:
        records = _bundle(
            episode_id, "CAND-ACK-PAIR", "BATTERY-ACK-PAIR", "PARTNER-ACK", suffix="E3"
        )
        l_benchmark = ("CAND-ACK-PAIR",)
        d_actual = l_benchmark
    elif episode_id == "E4-REVOKE-WITH-ALTERNATIVE":
        hidden = _bundle(
            episode_id, "CAND-PRIMARY", "BATTERY-PRIMARY", "PARTNER-PRIMARY", suffix="E4A",
            disclose=False,
        )
        alternative = _bundle(
            episode_id, "CAND-ALTERNATIVE", "BATTERY-ALT", "PARTNER-ALT", suffix="E4B"
        )
        records = hidden + alternative
        l_benchmark = ("CAND-PRIMARY", "CAND-ALTERNATIVE")
        d_actual = ("CAND-ALTERNATIVE",)
    elif episode_id == "E5-IMPOSSIBLE-REFUSAL":
        records = _bundle(
            episode_id, "CAND-REFUSED", "BATTERY-REFUSED", "PARTNER-REFUSED", suffix="E5",
            disclose=False,
        )
        for record in records:
            record["response"] = "REFUSED"
        l_benchmark = ("CAND-REFUSED",)
        d_actual = ()
    else:
        records = _bundle(
            episode_id, "CAND-MIGRATION", "BATTERY-MIGRATION", "PARTNER-MIGRATION", suffix="E6"
        )
        l_benchmark = ("CAND-MIGRATION",)
        d_actual = l_benchmark

    all_records = records + [
        operator["created_record"] for operator in operators
    ]
    expected = {record["evidence_id"]: deepcopy(record) for record in all_records}
    source_aliases = {
        record["source_id"]: record["source_id"]
        for record in all_records
    }
    authority_aliases = {"O_R": "O_R", "O_V": "O_V", "controller-admin": "CONTROLLER"}
    return World(
        prelude=prelude,
        interface=interface,
        records=tuple(deepcopy(records)),
        operators=tuple(deepcopy(operators)),
        l_benchmark=tuple(l_benchmark),
        d_actual=tuple(d_actual),
        expected=expected,
        source_aliases=source_aliases,
        authority_aliases=authority_aliases,
    )
