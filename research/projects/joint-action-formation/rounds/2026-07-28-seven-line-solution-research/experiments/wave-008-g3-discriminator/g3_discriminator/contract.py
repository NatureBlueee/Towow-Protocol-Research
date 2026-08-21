"""Public contract shared with candidates.

This module intentionally contains no hidden-world state and no evaluator.
Candidates receive only ``PublicObservation`` values from this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Protocol


class ActionKind(str, Enum):
    STATIC_SEARCH = "STATIC_SEARCH"
    ACTIVATE_EXISTING = "ACTIVATE_EXISTING"
    APPLY_FORMATION_OPERATOR = "APPLY_FORMATION_OPERATOR"
    PRODUCER_ONLY_CLAIM = "PRODUCER_ONLY_CLAIM"
    REMOVE_FORMATION_OPERATOR = "REMOVE_FORMATION_OPERATOR"
    REVERSE_FORMATION_OPERATOR = "REVERSE_FORMATION_OPERATOR"
    STOP = "STOP"


class EventKind(str, Enum):
    STATIC_SEARCH_COMPLETE = "STATIC_SEARCH_COMPLETE"
    ACTIVATION_RESULT = "ACTIVATION_RESULT"
    FORMATION_OPERATOR_APPLIED = "FORMATION_OPERATOR_APPLIED"
    FORMATION_OPERATOR_REMOVED = "FORMATION_OPERATOR_REMOVED"
    FORMATION_OPERATOR_REMOVE_NOOP = "FORMATION_OPERATOR_REMOVE_NOOP"
    FORMATION_OPERATOR_REVERSED = "FORMATION_OPERATOR_REVERSED"
    FORMATION_OPERATOR_UNAVAILABLE = "FORMATION_OPERATOR_UNAVAILABLE"
    AUTHORITY_REJECTED = "AUTHORITY_REJECTED"
    PRODUCER_ASSERTION = "PRODUCER_ASSERTION"
    TARGET_READBACK = "TARGET_READBACK"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True)
class ResourceBudget:
    max_actions: int
    max_cost_units: int


@dataclass(frozen=True)
class EpisodeContract:
    contract_id: str
    q: str
    v0: tuple[str, ...]
    necessary_principals: tuple[str, ...]
    authority_locus: str
    target_witness: str
    resource_budget: ResourceBudget

    def fingerprint(self) -> str:
        payload = json.dumps(
            asdict(self),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class PublicEvent:
    kind: EventKind
    attributes: tuple[tuple[str, str], ...] = ()

    def get(self, key: str) -> str | None:
        return dict(self.attributes).get(key)


@dataclass(frozen=True)
class PublicObservation:
    contract: EpisodeContract
    events: tuple[PublicEvent, ...]
    actions_used: int
    cost_units_used: int


@dataclass(frozen=True)
class CandidateAction:
    kind: ActionKind
    authority_actor: str | None = None
    claimed_success: bool = False


class CandidatePolicy(Protocol):
    name: str

    def decide(self, observation: PublicObservation) -> CandidateAction:
        """Choose an action using public observations only."""
