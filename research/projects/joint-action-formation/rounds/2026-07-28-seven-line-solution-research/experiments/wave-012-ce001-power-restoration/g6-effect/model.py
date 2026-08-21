"""Lossless G6 semantic objects.

These are projections over owner observations.  They are neither an oracle nor
an execution policy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from typing import Any


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"


class AuthorityStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    UNAUTHORIZED = "UNAUTHORIZED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class Causality(str, Enum):
    EXACT_ATTEMPT = "EXACT_ATTEMPT"
    PRE_EXISTING = "PRE_EXISTING"
    OTHER_ATTEMPT = "OTHER_ATTEMPT"
    UNKNOWN = "UNKNOWN"


class Recovery(str, Enum):
    NONE = "NONE"
    REQUIRED = "REQUIRED"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"


class Finality(str, Enum):
    PENDING = "PENDING"
    FINAL = "FINAL"
    DISPUTED = "DISPUTED"
    REVERSED = "REVERSED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Episode:
    episode_id: str
    q_version: str
    target_id: str
    required_kw: float = 3.0


@dataclass(frozen=True)
class Attempt:
    attempt_id: str
    operation_id: str
    actor_id: str
    target_id: str
    episode_id: str
    q_version: str
    attempted_at: int


@dataclass(frozen=True)
class RawOccurrence:
    occurrence_id: str
    owner_id: str
    domain: str
    native_kind: str
    object_id: str
    occurred_at: int
    operation_id: str | None
    from_state: str | None
    to_state: str | None
    power_kw: float | None = None
    damage: bool = False
    reverses_occurrence_id: str | None = None
    state_version: int | None = None


@dataclass(frozen=True)
class TargetStateObservation:
    owner_id: str
    domain: str
    object_id: str
    state: str
    observed_at: int
    state_version: int = 0
    last_occurrence_id: str | None = None


@dataclass(frozen=True)
class AuthorityObservation:
    owner_id: str
    operation_id: str
    actor_id: str
    object_id: str
    q_version: str
    status: AuthorityStatus
    observed_at: int
    scope_ref: str


@dataclass(frozen=True)
class EpisodeBinding:
    episode_id: str
    q_version: str
    occurrence_id: str
    observed_object_id: str
    expected_object_id: str
    exact_object: bool
    exact_q_version: bool


@dataclass(frozen=True)
class EffectAssessment:
    occurrence: RawOccurrence
    binding: EpisodeBinding
    authority: AuthorityObservation
    causality: Causality
    qualifies_as_effect: bool
    current_state_matches_q: bool
    exact_attempt_causality: bool
    authority_covers_actual_object: bool
    episode_contribution: Truth
    counts_toward_q: bool
    recovery: Recovery
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class AdoptionObservation:
    owner_id: str
    effect_id: str
    episode_id: str
    adopted: Truth
    observed_at: int


@dataclass(frozen=True)
class AcceptanceObservation:
    owner_id: str
    effect_id: str
    episode_id: str
    q_version: str
    accepted: Truth
    observed_at: int
    act_id: str = ""
    process_id: int = -1
    response_hash: str = ""


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    owner_id: str
    effect_id: str
    scheme: str
    debtor: str
    beneficiary: str
    required_phases: tuple[str, ...]
    reversal_phases: tuple[str, ...]
    finality_horizon: int


@dataclass(frozen=True)
class SchemePhase:
    obligation_id: str
    scheme: str
    phase: str
    state: Truth
    observed_at: int
    occurrence_id: str
    reverses_occurrence_id: str | None = None


@dataclass(frozen=True)
class SettlementAssessment:
    obligation: Obligation
    phases: tuple[SchemePhase, ...]
    finality: Finality
    discharged: bool
    graph: dict[str, Any]


@dataclass
class MethodResult:
    case_id: str
    resolution: str
    plan_sha256: str = ""
    effects: list[EffectAssessment] = field(default_factory=list)
    adoptions: list[AdoptionObservation] = field(default_factory=list)
    acceptances: list[AcceptanceObservation] = field(default_factory=list)
    settlements: list[SettlementAssessment] = field(default_factory=list)
    recovery_occurrences: list[RawOccurrence] = field(default_factory=list)
    duplicate_effect: bool = False
    owner_query_count: int = 0
    evidence_start_sequence: int = 0
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    evidence_closure: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    def evidence_payload(self) -> dict[str, Any]:
        """Result bytes committed by the frozen receipt closure."""
        value = asdict(self)
        value.pop("evidence_closure", None)
        return _jsonable(value)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, set):
        return [_jsonable(item) for item in sorted(value)]
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def assess_effect(
    episode: Episode,
    attempt: Attempt,
    occurrence: RawOccurrence,
    authority: AuthorityObservation,
) -> EffectAssessment:
    exact_object = occurrence.object_id == episode.target_id == attempt.target_id
    attempt_episode_matches = attempt.episode_id == episode.episode_id
    attempt_q_matches = attempt.q_version == episode.q_version
    if occurrence.operation_id is None or occurrence.occurred_at < attempt.attempted_at:
        causality = Causality.PRE_EXISTING
    elif occurrence.operation_id == attempt.operation_id:
        causality = Causality.EXACT_ATTEMPT
    else:
        causality = Causality.OTHER_ATTEMPT

    target_native_observation = (
        occurrence.owner_id == "O_E" and occurrence.domain == "TARGET_NATIVE"
    )
    qualifies = (
        target_native_observation
        and
        occurrence.native_kind == "POWER_STATE_TRANSITION"
        and occurrence.to_state == "POWERED"
    )
    authority_covers_actual = (
        authority.owner_id == "O_S"
        and
        authority.status == AuthorityStatus.AUTHORIZED
        and authority.operation_id == attempt.operation_id
        and authority.actor_id == attempt.actor_id
        and authority.object_id == occurrence.object_id
        and authority.q_version == episode.q_version
        and authority.observed_at <= attempt.attempted_at
    )
    power_ok = occurrence.power_kw is not None and 2.85 <= occurrence.power_kw <= 3.15
    current_state_matches_q = all((
        target_native_observation,
        occurrence.native_kind == "POWER_STATE_TRANSITION",
        occurrence.to_state == "POWERED",
        occurrence.object_id == episode.target_id,
        power_ok,
    ))
    exact_attempt_causality = causality == Causality.EXACT_ATTEMPT
    contributes = all((
        current_state_matches_q,
        exact_attempt_causality,
        authority_covers_actual,
        attempt_episode_matches,
        attempt_q_matches,
    ))
    episode_contribution = Truth.TRUE if contributes else Truth.FALSE
    counts = episode_contribution == Truth.TRUE
    reasons: list[str] = []
    if not exact_object:
        reasons.append("WRONG_TARGET")
    if not attempt_episode_matches:
        reasons.append("EPISODE_MISMATCH")
    if not attempt_q_matches:
        reasons.append("Q_VERSION_MISMATCH")
    if not target_native_observation:
        reasons.append("NOT_O_E_TARGET_NATIVE")
    if causality != Causality.EXACT_ATTEMPT:
        reasons.append(causality.value)
    if not authority_covers_actual:
        reasons.append("AUTHORITY_DOES_NOT_COVER_ACTUAL_OBJECT")
        reasons.append("AUTHORITY_NOT_CURRENT_EXACT")
    if not power_ok:
        reasons.append("POWER_OUT_OF_RANGE_OR_UNKNOWN")

    real_harm = occurrence.damage or (
        qualifies and (not exact_object or not authority_covers_actual)
    )
    recovery = Recovery.REQUIRED if real_harm else Recovery.NONE
    return EffectAssessment(
        occurrence=occurrence,
        binding=EpisodeBinding(
            episode_id=episode.episode_id,
            q_version=episode.q_version,
            occurrence_id=occurrence.occurrence_id,
            observed_object_id=occurrence.object_id,
            expected_object_id=episode.target_id,
            exact_object=exact_object,
            exact_q_version=(
                attempt_q_matches
                and attempt_episode_matches
                and exact_attempt_causality
            ),
        ),
        authority=authority,
        causality=causality,
        qualifies_as_effect=qualifies,
        current_state_matches_q=current_state_matches_q,
        exact_attempt_causality=exact_attempt_causality,
        authority_covers_actual_object=authority_covers_actual,
        episode_contribution=episode_contribution,
        counts_toward_q=counts,
        recovery=recovery,
        reasons=tuple(reasons),
    )


def assess_settlement(
    obligation: Obligation,
    phases: list[SchemePhase],
    observed_at: int,
    expected_effect_id: str | None = None,
) -> SettlementAssessment:
    authoritative_obligation = (
        obligation.owner_id == "O_P"
        and (
            expected_effect_id is None
            or obligation.effect_id == expected_effect_id
        )
    )
    valid_phases = [
        phase for phase in phases
        if phase.obligation_id == obligation.obligation_id
        and phase.scheme == obligation.scheme
        and phase.observed_at <= observed_at
    ]
    by_phase = {phase.phase: phase for phase in valid_phases}
    reversal_records = [
        phase for phase in valid_phases
        if phase.phase in obligation.reversal_phases and phase.state == Truth.TRUE
    ]
    required_known = all(
        phase in by_phase and by_phase[phase].state == Truth.TRUE
        for phase in obligation.required_phases
    )
    unknown_blocker = any(
        phase not in by_phase or by_phase[phase].state == Truth.UNKNOWN
        for phase in obligation.reversal_phases
    )
    if not authoritative_obligation:
        finality = Finality.UNKNOWN
    elif any(phase.phase == "DISPUTE" for phase in reversal_records):
        finality = Finality.DISPUTED
    elif reversal_records:
        finality = Finality.REVERSED
    elif unknown_blocker:
        finality = Finality.UNKNOWN
    elif not required_known or observed_at < obligation.finality_horizon:
        finality = Finality.PENDING
    else:
        finality = Finality.FINAL

    nodes = [
        {"id": obligation.obligation_id, "type": "O_P_OBLIGATION",
         "scheme": obligation.scheme}
    ]
    edges: list[dict[str, str]] = []
    for phase in phases:
        phase_matches_obligation = (
            phase.obligation_id == obligation.obligation_id
            and phase.scheme == obligation.scheme
            and phase.observed_at <= observed_at
        )
        nodes.append({
            "id": phase.occurrence_id,
            "type": "SCHEME_PHASE" if phase_matches_obligation else "FOREIGN_PHASE",
            "phase": phase.phase,
            "state": phase.state.value,
        })
        if not phase_matches_obligation:
            edge_kind = "DOES_NOT_ADVANCE"
        elif phase.phase not in obligation.reversal_phases:
            edge_kind = "ADVANCES"
        elif phase.state == Truth.TRUE:
            edge_kind = "REVERSES"
        elif phase.state == Truth.FALSE:
            edge_kind = "CLEARS_BLOCKER"
        else:
            edge_kind = "BLOCKER_UNKNOWN"
        edges.append({
            "from": phase.occurrence_id,
            "to": obligation.obligation_id,
            "kind": edge_kind,
        })
    return SettlementAssessment(
        obligation=obligation,
        phases=tuple(phases),
        finality=finality,
        discharged=finality == Finality.FINAL,
        graph={"nodes": nodes, "edges": edges},
    )
