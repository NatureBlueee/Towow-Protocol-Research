"""Private scenario construction with one state shard per truth owner.

The method imports neither this module nor any owner state.  ``ScenarioSpec`` is
only a trusted runner input used to start five isolated owner processes.
"""

from __future__ import annotations

from dataclasses import dataclass

from model import AuthorityStatus, Episode, RawOccurrence, Truth
from owner_process import (
    AuthorityGrant,
    EffectOperation,
    EffectOwnerState,
    PaymentOwnerState,
    QueryOwnerState,
    SafetyOwnerState,
    VenueOwnerState,
    VersionedTarget,
)


@dataclass(frozen=True)
class AttemptPlan:
    attempt_id: str
    operation_id: str
    actor_id: str
    target_id: str
    attempted_at: int


@dataclass(frozen=True)
class PublicPlan:
    case_id: str
    episode: Episode
    attempts: tuple[AttemptPlan, ...]
    resume_operation_id: str | None = None


@dataclass
class OperationBehavior:
    actual_target: str
    create_effect: bool
    ack_lost: bool = False
    damage: bool = False


@dataclass
class ScenarioSpec:
    private_case_id: str
    plan: PublicPlan
    safety: SafetyOwnerState
    effect: EffectOwnerState
    query: QueryOwnerState
    venue: VenueOwnerState
    payment: PaymentOwnerState

    @property
    def behaviors(self) -> dict[str, EffectOperation]:
        return self.effect.operations

    @property
    def occurrences(self) -> list[RawOccurrence]:
        return self.effect.occurrences

    @property
    def recoveries(self) -> list[RawOccurrence]:
        return self.effect.recoveries

    def fail_endpoint(self, owner_id: str, endpoint: str) -> None:
        owner = self.owner_states()[owner_id]
        owner.fail_endpoints.add(endpoint)

    def owner_states(self) -> dict[str, object]:
        return {
            "O_S": self.safety,
            "O_E": self.effect,
            "O_Q": self.query,
            "O_V": self.venue,
            "O_P": self.payment,
        }


def _plan(
    case_id: str,
    operations: tuple[tuple[str, str], ...],
    *,
    public_case_id: str | None = None,
) -> PublicPlan:
    visible_case_id = public_case_id or case_id
    episode = Episode(
        episode_id=f"CE-001:{visible_case_id}",
        q_version="Q@v1",
        target_id="Circuit-C7",
    )
    attempts = tuple(
        AttemptPlan(
            attempt_id=f"attempt:{visible_case_id}:{index}",
            operation_id=operation_id,
            actor_id=actor,
            target_id="Circuit-C7",
            attempted_at=100 + index,
        )
        for index, (operation_id, actor) in enumerate(operations, 1)
    )
    return PublicPlan(
        case_id=visible_case_id,
        episode=episode,
        attempts=attempts,
    )


def _scenario(
    private_case_id: str,
    plan: PublicPlan,
    authorities: dict[str, AuthorityStatus],
    behaviors: dict[str, OperationBehavior],
) -> ScenarioSpec:
    grants = {}
    operations = {}
    for attempt in plan.attempts:
        grants[attempt.operation_id] = AuthorityGrant(
            operation_id=attempt.operation_id,
            actor_id=attempt.actor_id,
            object_id=attempt.target_id,
            q_version=plan.episode.q_version,
            status=authorities[attempt.operation_id],
            observed_at=100,
            scope_ref=f"scope:{attempt.operation_id}:{attempt.target_id}",
        )
        behavior = behaviors[attempt.operation_id]
        operations[attempt.operation_id] = EffectOperation(
            operation_id=attempt.operation_id,
            attempted_at=attempt.attempted_at,
            actual_target=behavior.actual_target,
            create_effect=behavior.create_effect,
            ack_lost=behavior.ack_lost,
            damage=behavior.damage,
        )
    return ScenarioSpec(
        private_case_id=private_case_id,
        plan=plan,
        safety=SafetyOwnerState(grants=grants),
        effect=EffectOwnerState(
            case_id=plan.case_id,
            expected_target_id=plan.episode.target_id,
            operations=operations,
        ),
        query=QueryOwnerState(
            episode_id=plan.episode.episode_id,
            q_version=plan.episode.q_version,
            target_id=plan.episode.target_id,
        ),
        venue=VenueOwnerState(
            episode_id=plan.episode.episode_id,
            q_version=plan.episode.q_version,
            target_id=plan.episode.target_id,
        ),
        payment=PaymentOwnerState(
            case_id=plan.case_id,
            episode_id=plan.episode.episode_id,
            q_version=plan.episode.q_version,
        ),
    )


def build_world(case_id: str) -> ScenarioSpec:
    if case_id == "E0-PLATFORM-DIRECT":
        plan = _plan(case_id, (("op-platform", "venue-operator"),))
        world = _scenario(
            case_id,
            plan,
            {"op-platform": AuthorityStatus.AUTHORIZED},
            {"op-platform": OperationBehavior("Circuit-C7", True)},
        )
    elif case_id == "E1-EXTANT-MULTI-OWNER":
        plan = _plan(case_id, (("op-extant", "resource-provider"),))
        world = _scenario(
            case_id,
            plan,
            {"op-extant": AuthorityStatus.AUTHORIZED},
            {"op-extant": OperationBehavior("Circuit-C7", True)},
        )
    elif case_id == "E2-CONDITION-FORMATION":
        plan = _plan(case_id, (("op-formed", "delegated-provider"),))
        world = _scenario(
            case_id,
            plan,
            {"op-formed": AuthorityStatus.AUTHORIZED},
            {"op-formed": OperationBehavior("Circuit-C7", True)},
        )
    elif case_id == "E3A-ACK-LOST-EFFECT":
        plan = _plan(
            case_id,
            (
                ("op-e3-primary", "resource-provider"),
                ("op-e3-fallback", "resource-provider"),
            ),
            public_case_id="E3-ACK-LOST-OPAQUE",
        )
        world = _scenario(
            case_id,
            plan,
            {
                "op-e3-primary": AuthorityStatus.AUTHORIZED,
                "op-e3-fallback": AuthorityStatus.AUTHORIZED,
            },
            {
                "op-e3-primary": OperationBehavior(
                    "Circuit-C7", True, ack_lost=True
                ),
                "op-e3-fallback": OperationBehavior("Circuit-C7", True),
            },
        )
    elif case_id == "E3B-ACK-LOST-NO-EFFECT":
        plan = _plan(
            case_id,
            (
                ("op-e3-primary", "resource-provider"),
                ("op-e3-fallback", "resource-provider"),
            ),
            public_case_id="E3-ACK-LOST-OPAQUE",
        )
        world = _scenario(
            case_id,
            plan,
            {
                "op-e3-primary": AuthorityStatus.AUTHORIZED,
                "op-e3-fallback": AuthorityStatus.AUTHORIZED,
            },
            {
                "op-e3-primary": OperationBehavior(
                    "Circuit-C8", True, ack_lost=True, damage=True
                ),
                "op-e3-fallback": OperationBehavior("Circuit-C7", True),
            },
        )
    elif case_id == "E4-REVOKE-WITH-ALTERNATIVE":
        plan = _plan(
            case_id,
            (
                ("op-revoked", "provider-a"),
                ("op-alternative", "provider-b"),
            ),
        )
        world = _scenario(
            case_id,
            plan,
            {
                "op-revoked": AuthorityStatus.REVOKED,
                "op-alternative": AuthorityStatus.AUTHORIZED,
            },
            {
                "op-revoked": OperationBehavior("Circuit-C7", False),
                "op-alternative": OperationBehavior("Circuit-C7", True),
            },
        )
    elif case_id == "E5-IMPOSSIBLE-REFUSAL":
        plan = _plan(case_id, (("op-refused", "resource-provider"),))
        world = _scenario(
            case_id,
            plan,
            {"op-refused": AuthorityStatus.UNAUTHORIZED},
            {"op-refused": OperationBehavior("Circuit-C7", False)},
        )
    elif case_id == "E6-MIGRATION-REPLAY":
        base = _plan(case_id, (("op-before-crash", "resource-provider"),))
        plan = PublicPlan(
            case_id=base.case_id,
            episode=base.episode,
            attempts=base.attempts,
            resume_operation_id="op-before-crash",
        )
        world = _scenario(
            case_id,
            plan,
            {"op-before-crash": AuthorityStatus.AUTHORIZED},
            {"op-before-crash": OperationBehavior("Circuit-C7", True)},
        )
        attempt = plan.attempts[0]
        occurrence = RawOccurrence(
            occurrence_id=f"occ:{plan.case_id}:{attempt.operation_id}",
            owner_id="O_E",
            domain="TARGET_NATIVE",
            native_kind="POWER_STATE_TRANSITION",
            object_id="Circuit-C7",
            occurred_at=attempt.attempted_at + 1,
            operation_id=attempt.operation_id,
            from_state="UNPOWERED",
            to_state="POWERED",
            power_kw=3.0,
            state_version=1,
        )
        world.effect.occurrences.append(occurrence)
        world.effect.submissions[attempt.operation_id] = occurrence.occurrence_id
        world.effect.targets["Circuit-C7"] = VersionedTarget(
            state="POWERED",
            version=1,
            observed_at=occurrence.occurred_at,
            last_occurrence_id=occurrence.occurrence_id,
        )
    else:
        raise KeyError(case_id)
    return world


CASE_IDS = (
    "E0-PLATFORM-DIRECT",
    "E1-EXTANT-MULTI-OWNER",
    "E2-CONDITION-FORMATION",
    "E3A-ACK-LOST-EFFECT",
    "E3B-ACK-LOST-NO-EFFECT",
    "E4-REVOKE-WITH-ALTERNATIVE",
    "E5-IMPOSSIBLE-REFUSAL",
    "E6-MIGRATION-REPLAY",
)
