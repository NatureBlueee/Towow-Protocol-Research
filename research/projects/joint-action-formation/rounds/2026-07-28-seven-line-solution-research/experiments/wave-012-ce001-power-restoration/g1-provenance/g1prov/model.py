from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any


SYNTHETIC_OWNER_SOURCE = "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class EvidenceEvent:
    evidence_id: str
    episode_id: str
    kind: str
    subject_id: str
    candidate_id: str
    issuer_id: str
    authority_id: str
    source_id: str
    recipient_id: str
    purpose: str
    scope_version: str
    observed_at: str
    existed_at_t0: bool
    disclosure_allowed: bool
    current: bool
    payload: dict[str, Any]
    request_hash: str
    owner_state_version: int
    origin_process_id: int
    owner_source_type: str
    owner_source_instance_id: str
    owner_state_instance_id: str
    owner_process_instance_id: str
    evidence_hash: str
    via_operator: str | None = None

    @classmethod
    def issue(cls, **fields: Any) -> "EvidenceEvent":
        unsigned = dict(fields)
        unsigned.setdefault("request_hash", "IN_PROCESS_TEST_REQUEST")
        unsigned.setdefault("owner_state_version", 0)
        unsigned.setdefault("origin_process_id", 0)
        unsigned.setdefault("owner_source_type", SYNTHETIC_OWNER_SOURCE)
        unsigned.setdefault(
            "owner_source_instance_id",
            "CONTROLLER_ASSIGNED_IN_PROCESS_SOURCE_INSTANCE",
        )
        unsigned.setdefault(
            "owner_state_instance_id",
            "CONTROLLER_ASSIGNED_IN_PROCESS_STATE_INSTANCE",
        )
        unsigned.setdefault(
            "owner_process_instance_id",
            "CONTROLLER_ASSIGNED_IN_PROCESS_PROCESS_INSTANCE",
        )
        return cls(**unsigned, evidence_hash=digest(unsigned))

    def hash_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("evidence_hash")
        return value


@dataclass(frozen=True)
class OperatorEvent:
    operator_id: str
    operator_type: str
    mode: str
    owner_id: str
    authority_id: str
    created_evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateProposal:
    episode_id: str
    q_version: str
    object_id: str
    operation_id: str
    candidate_id: str
    resource_id: str
    partner_id: str
    owner_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    status: str = "CANDIDATE_NOT_COMMITMENT"
    proposal_id: str = ""

    @classmethod
    def synthesize(
        cls,
        *,
        episode_id: str,
        q_version: str,
        object_id: str,
        operation_id: str,
        candidate_id: str,
        resource_id: str,
        partner_id: str,
        owner_ids: tuple[str, ...],
        evidence_ids: tuple[str, ...],
    ) -> "CandidateProposal":
        proposal_id = "g1p-" + digest(
            {
                "episode_id": episode_id,
                "q_version": q_version,
                "object_id": object_id,
                "operation_id": operation_id,
                "candidate_id": candidate_id,
                "resource_id": resource_id,
                "partner_id": partner_id,
            }
        )[:16]
        return cls(
            episode_id=episode_id,
            q_version=q_version,
            object_id=object_id,
            operation_id=operation_id,
            candidate_id=candidate_id,
            resource_id=resource_id,
            partner_id=partner_id,
            owner_ids=owner_ids,
            evidence_ids=evidence_ids,
            proposal_id=proposal_id,
        )


@dataclass
class Cost:
    interface_reads: int = 0
    owner_queries: int = 0
    evidence_items: int = 0
    disclosure_units: int = 0


@dataclass
class Trace:
    episode_id: str
    intervention: str
    method: str
    intent_boundary: str = ""
    prelude_receipt_hash: str = ""
    queries: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[EvidenceEvent] = field(default_factory=list)
    refusals: list[dict[str, Any]] = field(default_factory=list)
    operators: list[OperatorEvent] = field(default_factory=list)
    proposal: CandidateProposal | None = None
    notes: list[str] = field(default_factory=list)
    cost: Cost = field(default_factory=Cost)


def serialize(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    return value
