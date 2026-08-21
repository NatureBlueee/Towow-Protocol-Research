"""Hidden paired worlds and the truth-only evaluator.

Candidate-provided success claims are recorded as producer assertions only.
Success and classification are derived from hidden S0/S1 state, authority
checks, and the target-authoritative readback.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .contract import (
    ActionKind,
    CandidateAction,
    EpisodeContract,
    EventKind,
    PublicEvent,
)


class WorldKind(str, Enum):
    DISCOVERY = "D"
    ACTIVATION = "A"
    FORMATION = "F"


class OutcomeStatus(str, Enum):
    SUCCESS = "SUCCESS"
    UNKNOWN = "UNKNOWN"
    NEGATIVE = "NEGATIVE"


class ReachabilityKind(str, Enum):
    DISCOVERY = "DISCOVERY"
    ACTIVATION = "ACTIVATION"
    OPERATOR_PATH_CANDIDATE = "OPERATOR_PATH_CANDIDATE"


@dataclass(frozen=True)
class HiddenWorld:
    world_id: str
    kind: WorldKind
    contract: EpisodeContract
    s0_path_exists: bool
    inactive_existing_resource: bool
    authorized_formation_available: bool


@dataclass(frozen=True)
class EvaluationReport:
    policy: str
    world_id: str
    contract_fingerprint: str
    status: OutcomeStatus
    reachability_kind: ReachabilityKind | None
    reason_code: str
    final_reachable: bool
    target_witness_verified: bool
    formation_supported: bool
    operator_necessary: bool | None
    current_effect_dependency: bool | None
    authority_valid: bool | None
    actions_used: int
    cost_units_used: int
    evidence: tuple[str, ...]
    novelty_score: None
    value_disposition: str


def event(kind: EventKind, **attributes: str) -> PublicEvent:
    return PublicEvent(kind, tuple(sorted(attributes.items())))


class TruthSession:
    """Mutable evaluator-owned state for one hidden world."""

    def __init__(self, world: HiddenWorld):
        self.world = world
        self.events: list[PublicEvent] = []
        self.actions_used = 0
        self.cost_units_used = 0
        self.resource_activated = False
        self.operator_applied = False
        self.operator_reversed = False
        self.applied_authority_valid: bool | None = None

    @property
    def final_reachable(self) -> bool:
        if self.world.s0_path_exists:
            return True
        if self.world.inactive_existing_resource and self.resource_activated:
            return True
        return self.operator_applied and not self.operator_reversed

    def _target_readback(self) -> PublicEvent:
        return event(
            EventKind.TARGET_READBACK,
            reachable=str(self.final_reachable).lower(),
            witness=self.world.contract.target_witness,
        )

    def _spend(self) -> bool:
        budget = self.world.contract.resource_budget
        if (
            self.actions_used + 1 > budget.max_actions
            or self.cost_units_used + 1 > budget.max_cost_units
        ):
            self.events.append(event(EventKind.BUDGET_EXHAUSTED))
            return False
        self.actions_used += 1
        self.cost_units_used += 1
        return True

    def apply(self, action: CandidateAction) -> None:
        if not self._spend():
            return

        if action.kind is ActionKind.STATIC_SEARCH:
            self.events.append(
                event(
                    EventKind.STATIC_SEARCH_COMPLETE,
                    found=str(self.world.s0_path_exists).lower(),
                )
            )
            if self.world.s0_path_exists:
                self.events.append(self._target_readback())
            return

        if action.kind is ActionKind.ACTIVATE_EXISTING:
            activated = self.world.inactive_existing_resource
            self.resource_activated = activated
            self.events.append(
                event(
                    EventKind.ACTIVATION_RESULT,
                    activated=str(activated).lower(),
                )
            )
            if activated:
                self.events.append(self._target_readback())
            return

        if action.kind is ActionKind.PRODUCER_ONLY_CLAIM:
            self.events.append(
                event(
                    EventKind.PRODUCER_ASSERTION,
                    claimed_success=str(action.claimed_success).lower(),
                )
            )
            return

        if action.kind is ActionKind.REMOVE_FORMATION_OPERATOR:
            authority_valid = (
                action.authority_actor == self.world.contract.authority_locus
            )
            self.applied_authority_valid = authority_valid
            if not authority_valid:
                self.events.append(
                    event(
                        EventKind.AUTHORITY_REJECTED,
                        actor=action.authority_actor or "NONE",
                    )
                )
                return
            if not self.operator_applied or self.operator_reversed:
                self.events.append(
                    event(EventKind.FORMATION_OPERATOR_REMOVE_NOOP)
                )
                return
            self.operator_applied = False
            self.events.append(event(EventKind.FORMATION_OPERATOR_REMOVED))
            self.events.append(self._target_readback())
            return

        if action.kind is ActionKind.APPLY_FORMATION_OPERATOR:
            authority_valid = (
                action.authority_actor == self.world.contract.authority_locus
            )
            self.applied_authority_valid = authority_valid
            if not authority_valid:
                self.events.append(
                    event(
                        EventKind.AUTHORITY_REJECTED,
                        actor=action.authority_actor or "NONE",
                    )
                )
                self.events.append(self._target_readback())
                return
            if not self.world.authorized_formation_available:
                self.events.append(
                    event(EventKind.FORMATION_OPERATOR_UNAVAILABLE)
                )
                return
            self.operator_applied = True
            self.events.append(event(EventKind.FORMATION_OPERATOR_APPLIED))
            if action.claimed_success:
                self.events.append(
                    event(
                        EventKind.PRODUCER_ASSERTION,
                        claimed_success="true",
                    )
                )
            self.events.append(self._target_readback())
            return

        if action.kind is ActionKind.REVERSE_FORMATION_OPERATOR:
            authority_valid = (
                action.authority_actor == self.world.contract.authority_locus
            )
            if not authority_valid:
                self.events.append(
                    event(
                        EventKind.AUTHORITY_REJECTED,
                        actor=action.authority_actor or "NONE",
                    )
                )
                return
            if self.operator_applied:
                self.operator_reversed = True
                self.events.append(event(EventKind.FORMATION_OPERATOR_REVERSED))
                self.events.append(self._target_readback())
            return

        raise ValueError(f"unsupported action: {action.kind}")

    def evaluate(self, policy_name: str) -> EvaluationReport:
        evidence = tuple(item.kind.value for item in self.events)
        target_events = [
            item
            for item in self.events
            if item.kind is EventKind.TARGET_READBACK
        ]
        final_target_verified = bool(
            target_events
            and target_events[-1].get("reachable") == "true"
            and target_events[-1].get("witness")
            == self.world.contract.target_witness
        )

        status = OutcomeStatus.UNKNOWN
        reachability_kind: ReachabilityKind | None = None
        reason_code = "INSUFFICIENT_ACTION_OR_EVIDENCE"
        formation_supported = False
        operator_necessary: bool | None = None
        current_effect_dependency: bool | None = None
        authority_valid: bool | None = None

        if EventKind.BUDGET_EXHAUSTED.value in evidence:
            status = OutcomeStatus.NEGATIVE
            reason_code = "RESOURCE_BUDGET_EXCEEDED"
        elif EventKind.AUTHORITY_REJECTED.value in evidence:
            status = OutcomeStatus.NEGATIVE
            reason_code = "WRONG_AUTHORITY"
            # A rejected actor establishes an authority failure, not that this
            # particular operator was causally necessary.
            operator_necessary = None
            authority_valid = False
        elif EventKind.PRODUCER_ASSERTION.value in evidence and not final_target_verified:
            status = OutcomeStatus.NEGATIVE
            reason_code = "PRODUCER_ONLY_WITHOUT_TARGET_WITNESS"
            # Self-report without a target witness establishes invalid
            # evidence only. It cannot by itself establish operator necessity.
            operator_necessary = None
            authority_valid = self.applied_authority_valid
        elif (
            EventKind.FORMATION_OPERATOR_APPLIED.value in evidence
            and EventKind.FORMATION_OPERATOR_REMOVED.value in evidence
            and not final_target_verified
            and not self.final_reachable
        ):
            status = OutcomeStatus.NEGATIVE
            reason_code = "REMOVE_OPERATOR_ELIMINATES_PATH"
            current_effect_dependency = True
            authority_valid = True
        elif EventKind.FORMATION_OPERATOR_REVERSED.value in evidence:
            status = OutcomeStatus.NEGATIVE
            reason_code = "REVERSE_OPERATOR_ELIMINATES_PATH"
            current_effect_dependency = True
            authority_valid = True
        elif (
            self.world.s0_path_exists
            and EventKind.STATIC_SEARCH_COMPLETE.value in evidence
            and final_target_verified
        ):
            status = OutcomeStatus.SUCCESS
            reachability_kind = ReachabilityKind.DISCOVERY
            reason_code = "S0_EQUIVALENT_PATH_DISCOVERED"
        elif (
            self.world.inactive_existing_resource
            and self.resource_activated
            and final_target_verified
        ):
            status = OutcomeStatus.SUCCESS
            reachability_kind = ReachabilityKind.ACTIVATION
            reason_code = "EXISTING_RESOURCE_ACTIVATED"
        elif (
            self.operator_applied
            and not self.operator_reversed
            and self.applied_authority_valid
            and final_target_verified
        ):
            status = OutcomeStatus.SUCCESS
            reachability_kind = ReachabilityKind.OPERATOR_PATH_CANDIDATE
            reason_code = (
                "AUTHORIZED_OPERATOR_CREATED_PATH_CLOSURE_NOT_TESTED"
            )
            # A before/after trace does not establish that the old L0+L1
            # closure was UNSAT. Necessity is adjudicated only by a bound
            # remove/reverse replay, not copied into this result.
            formation_supported = False
            operator_necessary = None
            authority_valid = True
        elif EventKind.FORMATION_OPERATOR_UNAVAILABLE.value in evidence:
            status = OutcomeStatus.UNKNOWN
            reason_code = "UNRESOLVED_OPERATOR_UNAVAILABLE"

        if status is OutcomeStatus.SUCCESS:
            value_disposition = (
                "POSITIVE_SAME_POLICY_CENTRAL_TOPOLOGY_CONSTRUCTION"
                if policy_name == "same_information_strong_center_hitl"
                else "POSITIVE_REACHABILITY_RESULT"
            )
        elif status is OutcomeStatus.NEGATIVE:
            value_disposition = "NEGATIVE_RESULT_PRESERVED"
        else:
            value_disposition = "UNKNOWN_PRESERVED"

        return EvaluationReport(
            policy=policy_name,
            world_id=self.world.world_id,
            contract_fingerprint=self.world.contract.fingerprint(),
            status=status,
            reachability_kind=reachability_kind,
            reason_code=reason_code,
            final_reachable=self.final_reachable,
            target_witness_verified=final_target_verified,
            formation_supported=formation_supported,
            operator_necessary=operator_necessary,
            current_effect_dependency=current_effect_dependency,
            authority_valid=authority_valid,
            actions_used=self.actions_used,
            cost_units_used=self.cost_units_used,
            evidence=evidence,
            novelty_score=None,
            value_disposition=value_disposition,
        )
