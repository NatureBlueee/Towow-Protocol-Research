from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceEvent:
    event_id: str
    path_id: str
    source_id: str
    canonical_source: str
    authority_root: str
    claim: str
    observed_at: str
    existed_at_t0: bool
    legal_at_t0: bool
    recipient: str
    purpose: str
    sensitivity: int = 1
    retention: int = 1
    onward_hops: int = 0


@dataclass(frozen=True)
class OperatorEvent:
    operator_id: str
    operator_type: str
    mode: str
    authority_root: str
    valid_authority: bool
    disclosure_legal: bool
    created_evidence: tuple[EvidenceEvent, ...] = ()


@dataclass(frozen=True)
class Proposal:
    path_id: str
    target: str
    quality_floor: str
    necessary_principals: tuple[str, ...]


@dataclass
class Cost:
    actions: int = 0
    disclosure_exposure: int = 0
    model_calls: int = 0
    human_minutes: int = 0
    raw_exposure: int = 0


@dataclass
class Trace:
    world_id: str
    arm: str
    intervention: str
    candidate_sources: list[str] = field(default_factory=list)
    evidence: list[EvidenceEvent] = field(default_factory=list)
    operators: list[OperatorEvent] = field(default_factory=list)
    refusals: list[dict[str, Any]] = field(default_factory=list)
    proposal: Proposal | None = None
    cost: Cost = field(default_factory=Cost)
    notes: list[str] = field(default_factory=list)


def serialize(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(item) for item in value]
    return value

