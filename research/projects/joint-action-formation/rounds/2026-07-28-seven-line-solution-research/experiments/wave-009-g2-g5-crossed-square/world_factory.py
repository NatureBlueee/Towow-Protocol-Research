"""Frozen synthetic world construction for Wave 009.

The factory is parent-side experiment infrastructure.  Public packets never
contain the truth coordinates used to create opaque IDs.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from common import canonical_bytes, opaque_id, sha256_hex


@dataclass(frozen=True)
class RelationPrivateWorld:
    truth_id: str
    world_id: str
    task_kind: str
    horizon: str
    relation_valid: bool
    invalid_mode: str
    current_version: str
    material_change: bool
    semantic_retained: bool
    source_text: str
    semantic_payload: dict[str, Any]


@dataclass(frozen=True)
class AuthorityPrivateWorld:
    truth_id: str
    world_id: str
    task_kind: str
    authority_mode: str
    current_relation_version: str
    current_revoke_head: int

    @property
    def authority_valid(self) -> bool:
        return self.authority_mode == "NONE"


@dataclass(frozen=True)
class WorldBundle:
    public_packet: dict[str, Any]
    relation_private: RelationPrivateWorld
    authority_private: AuthorityPrivateWorld


def _task(task_kind: str) -> dict[str, Any]:
    if task_kind == "T3":
        principals = ["SEEKER", "RESOURCE_OWNER"]
        request = {
            "task_kind": "T3",
            "truth_status": "SYNTHETIC_TASK_SPEC",
            "source_status": "EXECUTION_RESOURCE_REQUIREMENT_ONLY",
            "complete_task": (
                "Obtain one revocable city-sandbox slot for a bounded "
                "interoperability rehearsal without treating discovery, "
                "delivery or ACK as authorization."
            ),
            "principals": principals,
            "required_action": "RESERVE_SANDBOX_SLOT",
            "purpose": "INTEROP_REHEARSAL",
            "resource": "CITY_SANDBOX_SLOT_14",
            "time_window": "D+2T09:00/D+2T11:00",
            "counterparty": "RESOURCE_OWNER",
            "acceptance_authority": "RESOURCE_OWNER",
        }
    elif task_kind == "T4":
        principals = ["PRIME", "FIELD", "ASSURE"]
        request = {
            "task_kind": "T4",
            "truth_status": "SYNTHETIC_TASK_SPEC",
            "source_status": "FROZEN_SYNTHETIC_WORLD",
            "complete_task": (
                "Form a three-principal joint bid for CITY-RFC-17-V2, "
                "bind roles and current local-data terms, and reserve the "
                "scarce submission resources without inferring award."
            ),
            "principals": principals,
            "required_action": "SUBMIT_JOINT_BID",
            "purpose": "CITY_RFC_17_V2",
            "resource": "BID_TEAM_CAPACITY_72H",
            "time_window": "D+0/D+5",
            "counterparty": "CITY_PROCUREMENT",
            "acceptance_authority": "CITY_PROCUREMENT",
        }
    else:
        raise ValueError(f"UNKNOWN_TASK_KIND:{task_kind}")
    request["task_fingerprint"] = sha256_hex(canonical_bytes(request))
    return request


def _relation_invalid_mode(horizon: str) -> str:
    return {
        "ONE_SHOT": "MISSING_EXPLAIN_BACK",
        "BOUNDED": "MISSING_EXPIRY",
        "DURABLE": "MISSING_AMENDMENT_GOVERNANCE",
    }[horizon]


def _authority_invalid_mode(index: int) -> str:
    return (
        "STALE_VERSION",
        "CONTROLLER_SUBSTITUTION",
        "REVOKED",
        "DUPLICATE_RESERVATION",
    )[index % 4]


def _bundle(
    *,
    coordinate: str,
    task_kind: str,
    horizon: str,
    relation_valid: bool,
    relation_mode: str | None = None,
    authority_mode: str = "NONE",
    material_change: bool = False,
    semantic_retained: bool = True,
    source_text: str = "Terms remain aligned for the declared purpose.",
    semantic_payload: dict[str, Any] | None = None,
) -> WorldBundle:
    world_id = f"w-{secrets.token_hex(10)}"
    task = _task(task_kind)
    current_version = "REL-V2"
    relation = RelationPrivateWorld(
        truth_id=opaque_id("relation-truth", coordinate, "rt"),
        world_id=world_id,
        task_kind=task_kind,
        horizon=horizon,
        relation_valid=relation_valid,
        invalid_mode=relation_mode
        or ("NONE" if relation_valid else _relation_invalid_mode(horizon)),
        current_version=current_version,
        material_change=material_change,
        semantic_retained=semantic_retained,
        source_text=source_text,
        semantic_payload=semantic_payload
        or {
            "roles": task["principals"],
            "purpose": task["purpose"],
            "scope": task["required_action"],
            "data_boundary": "DECLARED_PURPOSE_ONLY",
        },
    )
    authority = AuthorityPrivateWorld(
        truth_id=opaque_id("authority-truth", coordinate, "at"),
        world_id=world_id,
        task_kind=task_kind,
        authority_mode=authority_mode,
        current_relation_version=current_version,
        current_revoke_head=4,
    )
    public_packet = {
        "schema": "towow.wave009-public-world.v1",
        "world_id": world_id,
        "task": task,
        "presentation": {
            "source_text": source_text,
            "role": "PRESENTATION_ONLY_NO_SEMANTIC_INTERPRETATION",
        },
    }
    return WorldBundle(public_packet, relation, authority)


def build_core_worlds() -> list[WorldBundle]:
    worlds: list[WorldBundle] = []
    index = 0
    invalid_authority_index = 0
    for task_kind in ("T3", "T4"):
        for horizon in ("ONE_SHOT", "BOUNDED", "DURABLE"):
            for relation_valid in (False, True):
                for authority_valid in (False, True):
                    coordinate = (
                        f"core:{index}:{task_kind}:{horizon}:"
                        f"{relation_valid}:{authority_valid}"
                    )
                    worlds.append(
                        _bundle(
                            coordinate=coordinate,
                            task_kind=task_kind,
                            horizon=horizon,
                            relation_valid=relation_valid,
                            authority_mode=(
                                "NONE"
                                if authority_valid
                                else _authority_invalid_mode(
                                    invalid_authority_index
                                )
                            ),
                        )
                    )
                    if not authority_valid:
                        invalid_authority_index += 1
                    index += 1
    return worlds


def build_mutation_pairs() -> dict[str, tuple[WorldBundle, WorldBundle]]:
    shared_semantics = {
        "roles": ["PRIME", "FIELD", "ASSURE"],
        "purpose": "CITY_RFC_17_V2",
        "scope": "SUBMIT_JOINT_BID",
        "data_boundary": "RAW_IN_CITY_TENANT",
    }
    parameter = _bundle(
        coordinate="mutation:parameter",
        task_kind="T4",
        horizon="DURABLE",
        relation_valid=True,
        authority_mode="NONE",
        relation_mode="PARAMETER_UPDATE",
        material_change=False,
        source_text="The delivery window shifts by a single morning.",
        semantic_payload=shared_semantics,
    )
    material = _bundle(
        coordinate="mutation:material",
        task_kind="T4",
        horizon="DURABLE",
        relation_valid=False,
        authority_mode="NONE",
        relation_mode="MATERIAL_CHANGE",
        material_change=True,
        source_text="The delivery window shifts by a single morning.",
        semantic_payload={
            **shared_semantics,
            "data_boundary": "RAW_MAY_LEAVE_CITY_TENANT",
        },
    )
    retained = _bundle(
        coordinate="mutation:retained",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=True,
        authority_mode="NONE",
        relation_mode="SEMANTIC_RETAINED",
        semantic_retained=True,
        source_text="Keep raw telemetry city-side; export aggregates only.",
        semantic_payload=shared_semantics,
    )
    lost = _bundle(
        coordinate="mutation:lost",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=False,
        authority_mode="NONE",
        relation_mode="SEMANTIC_LOST",
        semantic_retained=False,
        source_text=(
            "Unprocessed sensor records stay inside the municipal tenant; "
            "only approved summaries cross the boundary."
        ),
        semantic_payload=shared_semantics,
    )

    def authority_pair(
        name: str,
        good_mode: str,
        bad_mode: str,
    ) -> tuple[WorldBundle, WorldBundle]:
        return (
            _bundle(
                coordinate=f"mutation:{name}:good",
                task_kind="T3",
                horizon="BOUNDED",
                relation_valid=True,
                authority_mode=good_mode,
            ),
            _bundle(
                coordinate=f"mutation:{name}:bad",
                task_kind="T3",
                horizon="BOUNDED",
                relation_valid=True,
                authority_mode=bad_mode,
            ),
        )

    return {
        "PARAMETER_VS_MATERIAL": (parameter, material),
        "RETAINED_VS_LOST": (retained, lost),
        "CURRENT_VS_STALE": authority_pair(
            "current-stale", "NONE", "STALE_VERSION"
        ),
        "PRINCIPAL_VS_CONTROLLER": authority_pair(
            "principal-controller", "NONE", "CONTROLLER_SUBSTITUTION"
        ),
        "ACTIVE_VS_REVOKED": authority_pair(
            "active-revoked", "NONE", "REVOKED"
        ),
        "UNIQUE_VS_DUPLICATE": authority_pair(
            "unique-duplicate", "NONE", "DUPLICATE_RESERVATION"
        ),
    }


def build_presentation_controls() -> dict[
    str, tuple[WorldBundle, WorldBundle]
]:
    semantics = {
        "roles": ["PRIME", "FIELD", "ASSURE"],
        "purpose": "CITY_RFC_17_V2",
        "scope": "SUBMIT_JOINT_BID",
        "data_boundary": "RAW_IN_CITY_TENANT",
    }
    same_words_parameter = _bundle(
        coordinate="language:same-words:parameter",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=True,
        authority_mode="NONE",
        source_text="The operating window changes slightly.",
        semantic_payload=semantics,
    )
    same_words_material = _bundle(
        coordinate="language:same-words:material",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=False,
        authority_mode="NONE",
        relation_mode="MATERIAL_CHANGE",
        material_change=True,
        source_text="The operating window changes slightly.",
        semantic_payload={
            **semantics,
            "data_boundary": "RAW_EXPORT_ALLOWED",
        },
    )
    different_words_left = _bundle(
        coordinate="language:different-words:left",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=True,
        authority_mode="NONE",
        source_text="Raw telemetry remains in the city tenant.",
        semantic_payload=semantics,
    )
    different_words_right = _bundle(
        coordinate="language:different-words:right",
        task_kind="T4",
        horizon="BOUNDED",
        relation_valid=True,
        authority_mode="NONE",
        source_text=(
            "Unprocessed sensor records never cross the municipal "
            "execution boundary."
        ),
        semantic_payload=semantics,
    )
    return {
        "SAME_PRESENTATION_DIFFERENT_STRUCTURED_SEMANTICS": (
            same_words_parameter,
            same_words_material,
        ),
        "DIFFERENT_PRESENTATION_SAME_STRUCTURED_SEMANTICS": (
            different_words_left,
            different_words_right,
        ),
    }


def build_t5_case() -> dict[str, Any]:
    return {
        "schema": "towow.wave009-t5-platform-case.v1",
        "truth_status": "NEGATIVE_CONTROL_SPEC",
        "request": {
            "sku": "SKU-CRM",
            "seat_count": 5,
            "billing_cadence": "MONTHLY",
            "total_price_cny": 600,
            "buyer": "BUYER-01",
            "buyer_approval": "APPROVED",
        },
        "platform_contract": {
            "contract_id": "STANDARD-SAAS-PROCUREMENT-V3",
            "authoritative_state_machine": [
                "REQUEST_VALIDATED",
                "REQUEST_CREATED",
                "BUYER_APPROVED",
                "SEATS_PROVISIONED",
                "TARGET_READBACK",
                "CLOSED",
            ],
            "catalog": {
                "SKU-CRM": {
                    "monthly_price_cny": 600,
                    "seat_count": 5,
                }
            },
        },
    }
