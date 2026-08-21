"""Small paired-world population for the prototype B runner.

These are executable world configurations, not evaluator labels.  The worker
never receives the fields that differ only inside the simulated provider.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorldSpec:
    world_ref: str
    pair_ref: str
    pair_kind: str
    public_namespace: str
    revision: str
    policy_revision: str
    policy_state: str
    authority_response: str
    reservation_response: str
    execution_state: str
    submit_delivery: str
    status_visibility: str
    allow_formation: bool
    allow_submit: bool


WORLDS = (
    # Reads are identical.  The latent execution condition differs, but the
    # passive policy is not allowed to request a commitment or attempt.
    WorldSpec(
        world_ref="PASSIVE-LATENT-READY",
        pair_ref="PAIR-PASSIVE",
        pair_kind="PASSIVE",
        public_namespace="passive",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="GRANTED",
        execution_state="APPLIED",
        submit_delivery="DELIVERED",
        status_visibility="VISIBLE",
        allow_formation=False,
        allow_submit=False,
    ),
    WorldSpec(
        world_ref="PASSIVE-LATENT-BROKEN",
        pair_ref="PAIR-PASSIVE",
        pair_kind="PASSIVE",
        public_namespace="passive",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="GRANTED",
        execution_state="DECLINED",
        submit_delivery="DELIVERED",
        status_visibility="VISIBLE",
        allow_formation=False,
        allow_submit=False,
    ),
    # Initial reads are identical.  A lawful reservation request separates the
    # worlds.  The granted branch also exercises response-loss reconciliation.
    WorldSpec(
        world_ref="ACTIVE-RESERVATION-GRANTED",
        pair_ref="PAIR-ACTIVE",
        pair_kind="ACTIVE_QUERY_COMMITMENT",
        public_namespace="active",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="GRANTED",
        execution_state="APPLIED",
        submit_delivery="LOST",
        status_visibility="VISIBLE",
        allow_formation=True,
        allow_submit=True,
    ),
    WorldSpec(
        world_ref="ACTIVE-RESERVATION-REFUSED",
        pair_ref="PAIR-ACTIVE",
        pair_kind="ACTIVE_QUERY_COMMITMENT",
        public_namespace="active",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="REFUSED",
        execution_state="APPLIED",
        submit_delivery="DELIVERED",
        status_visibility="VISIBLE",
        allow_formation=True,
        allow_submit=True,
    ),
    # Every allowed pre-decision interaction is identical.  Only an excluded
    # latent dependency differs, so this is the prototype hard pair.
    WorldSpec(
        world_ref="HARD-LATENT-READY",
        pair_ref="PAIR-HARD",
        pair_kind="FULL_LAWFUL_INTERACTION_EQUIVALENT",
        public_namespace="hard",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="GRANTED",
        execution_state="APPLIED",
        submit_delivery="DELIVERED",
        status_visibility="HIDDEN",
        allow_formation=True,
        allow_submit=False,
    ),
    WorldSpec(
        world_ref="HARD-LATENT-BROKEN",
        pair_ref="PAIR-HARD",
        pair_kind="FULL_LAWFUL_INTERACTION_EQUIVALENT",
        public_namespace="hard",
        revision="artifact-r7",
        policy_revision="policy-r3",
        policy_state="PUBLISHED",
        authority_response="APPROVED",
        reservation_response="GRANTED",
        execution_state="DECLINED",
        submit_delivery="DELIVERED",
        status_visibility="HIDDEN",
        allow_formation=True,
        allow_submit=False,
    ),
)


def by_ref(world_ref: str) -> WorldSpec:
    for world in WORLDS:
        if world.world_ref == world_ref:
            return world
    raise KeyError(world_ref)
