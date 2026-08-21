"""Candidate policies.

There is deliberately no import from ``truth``. Policies can see the frozen
public contract, budget counters, and public events, but not world kind or
hidden state.
"""

from __future__ import annotations

from .contract import (
    ActionKind,
    CandidateAction,
    EventKind,
    PublicObservation,
)


def _events(observation: PublicObservation, kind: EventKind):
    return tuple(event for event in observation.events if event.kind is kind)


def _target_reachable(observation: PublicObservation) -> bool:
    return any(
        event.get("reachable") == "true"
        for event in _events(observation, EventKind.TARGET_READBACK)
    )


class StaticSearchPolicy:
    name = "static_search"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        if not _events(observation, EventKind.STATIC_SEARCH_COMPLETE):
            return CandidateAction(ActionKind.STATIC_SEARCH)
        return CandidateAction(ActionKind.STOP)


class ActivationRunnerPolicy:
    name = "activation_runner"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        if _target_reachable(observation):
            return CandidateAction(ActionKind.STOP)
        if not _events(observation, EventKind.STATIC_SEARCH_COMPLETE):
            return CandidateAction(ActionKind.STATIC_SEARCH)
        if not _events(observation, EventKind.ACTIVATION_RESULT):
            return CandidateAction(ActionKind.ACTIVATE_EXISTING)
        return CandidateAction(ActionKind.STOP)


class FormationPolicy:
    name = "formation_policy"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        if _target_reachable(observation):
            return CandidateAction(ActionKind.STOP)
        if not _events(observation, EventKind.STATIC_SEARCH_COMPLETE):
            return CandidateAction(ActionKind.STATIC_SEARCH)
        if not _events(observation, EventKind.ACTIVATION_RESULT):
            return CandidateAction(ActionKind.ACTIVATE_EXISTING)
        if _events(observation, EventKind.FORMATION_OPERATOR_UNAVAILABLE):
            return CandidateAction(ActionKind.STOP)
        if not _events(observation, EventKind.FORMATION_OPERATOR_APPLIED):
            return CandidateAction(
                ActionKind.APPLY_FORMATION_OPERATOR,
                authority_actor=observation.contract.authority_locus,
            )
        return CandidateAction(ActionKind.STOP)


class SameInformationStrongCenterHitlPolicy(FormationPolicy):
    """Same-policy central-topology construction, not an independent baseline.

    This class deliberately inherits the exact policy implementation. It can
    show that the same rule can be placed behind a central controller name, but
    it does not test a mature planner, workflow stack, real HITL service, or an
    independent Authority holder.
    """

    name = "same_information_strong_center_hitl"


class WrongAuthorityPolicy(FormationPolicy):
    name = "attack_wrong_authority"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        if _events(observation, EventKind.AUTHORITY_REJECTED):
            return CandidateAction(ActionKind.STOP)
        next_action = super().decide(observation)
        if next_action.kind is ActionKind.APPLY_FORMATION_OPERATOR:
            return CandidateAction(
                ActionKind.APPLY_FORMATION_OPERATOR,
                authority_actor="principal:producer",
                claimed_success=True,
            )
        return next_action


class ProducerOnlyPolicy(FormationPolicy):
    name = "attack_producer_only"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        if _events(observation, EventKind.PRODUCER_ASSERTION):
            return CandidateAction(ActionKind.STOP)
        next_action = super().decide(observation)
        if next_action.kind is ActionKind.APPLY_FORMATION_OPERATOR:
            return CandidateAction(
                ActionKind.PRODUCER_ONLY_CLAIM,
                authority_actor=observation.contract.authority_locus,
                claimed_success=True,
            )
        return next_action


class RemoveOperatorPolicy(FormationPolicy):
    name = "attack_remove_operator"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        applied = _events(observation, EventKind.FORMATION_OPERATOR_APPLIED)
        removed = _events(observation, EventKind.FORMATION_OPERATOR_REMOVED)
        if applied and not removed:
            return CandidateAction(
                ActionKind.REMOVE_FORMATION_OPERATOR,
                authority_actor=observation.contract.authority_locus,
            )
        if _events(observation, EventKind.FORMATION_OPERATOR_REMOVED):
            return CandidateAction(ActionKind.STOP)
        return super().decide(observation)


class ReverseOperatorPolicy(FormationPolicy):
    name = "attack_reverse_operator"

    def decide(self, observation: PublicObservation) -> CandidateAction:
        applied = _events(observation, EventKind.FORMATION_OPERATOR_APPLIED)
        reversed_events = _events(
            observation, EventKind.FORMATION_OPERATOR_REVERSED
        )
        if applied and not reversed_events:
            return CandidateAction(
                ActionKind.REVERSE_FORMATION_OPERATOR,
                authority_actor=observation.contract.authority_locus,
            )
        if reversed_events:
            return CandidateAction(ActionKind.STOP)
        return super().decide(observation)
