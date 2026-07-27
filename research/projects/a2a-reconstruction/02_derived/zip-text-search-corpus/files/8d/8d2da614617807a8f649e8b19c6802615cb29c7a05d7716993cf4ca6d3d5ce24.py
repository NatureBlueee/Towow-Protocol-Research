from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class CoordinationMode(str, Enum):
    SELF_EXECUTION = "SELF_EXECUTION"
    DETERMINISTIC_SERVICE = "DETERMINISTIC_SERVICE"
    PLATFORM_MARKET = "PLATFORM_MARKET"
    CENTRAL_OPTIMIZER = "CENTRAL_OPTIMIZER"
    HUMAN_BROKER = "HUMAN_BROKER"
    BILATERAL_FORMATION = "BILATERAL_FORMATION"
    TEMPORARY_COALITION = "TEMPORARY_COALITION"
    HUMAN_ADJUDICATION = "HUMAN_ADJUDICATION"


@dataclass(frozen=True)
class OPCOperatingEnvelope:
    """A derived operating view, not a new canonical aggregate root.

    The envelope makes the characteristic constraints of a one-person company
    explicit without equating one legal owner with one internal role or one AI.
    """

    accountability_root: str
    active_roles: tuple[str, ...]
    agent_instances: tuple[str, ...] = ()
    cash_capacity: float = 0.0
    attention_hours_available: float = 0.0
    reputation_at_risk: float = 0.0
    legal_exposure: float = 0.0
    data_exposure: float = 0.0
    irreversible_commitments: tuple[str, ...] = ()
    reserved_resources: dict[str, float] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.accountability_root:
            errors.append("accountability_root is required")
        if not self.active_roles:
            errors.append("at least one active role is required")
        for name in (
            "cash_capacity", "attention_hours_available", "reputation_at_risk",
            "legal_exposure", "data_exposure",
        ):
            if getattr(self, name) < 0:
                errors.append(f"{name} cannot be negative")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CoordinationContext:
    participants: int
    schema_completeness: float
    standardization: float
    private_context_intensity: float
    authority_plurality: int
    externality_risk: float
    irreversibility: float
    volatility: float
    evidence_burden: float
    platform_frame_sufficient: bool
    centralizable_within_grants: bool
    dispute_active: bool = False
    repeated_relation: bool = False
    human_acceptance_required: bool = False
    marketplace_available: bool = False
    deterministic_interface_available: bool = False
    broker_available: bool = False
    optimization_problem: bool = False
    self_executable: bool = False
    capacity_pressure: float = 0.0

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.participants < 1:
            errors.append("participants must be >= 1")
        if self.authority_plurality < 1:
            errors.append("authority_plurality must be >= 1")
        for name in (
            "schema_completeness", "standardization", "private_context_intensity",
            "externality_risk", "irreversibility", "volatility", "evidence_burden",
            "capacity_pressure",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                errors.append(f"{name} must be between 0 and 1")
        return errors
