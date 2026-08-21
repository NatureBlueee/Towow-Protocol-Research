"""Agent C adversarial tests.

These tests intentionally state the stronger safety properties required by the
CE-001 contract.  A failure is evidence of an open boundary, not a reason to
weaken the assertion.
"""

import unittest

from method import G6Method
from model import (
    AcceptanceObservation,
    AdoptionObservation,
    Attempt,
    AuthorityObservation,
    AuthorityStatus,
    Episode,
    Finality,
    Obligation,
    RawOccurrence,
    SchemePhase,
    Truth,
    assess_effect,
    assess_settlement,
)
from owner_api import start_owner_session
from scenarios import AttemptPlan, PublicPlan, build_world


class EffectBindingAttacks(unittest.TestCase):
    def setUp(self):
        self.episode = Episode("CE-001:attack", "Q@v1", "Circuit-C7")
        self.attempt = Attempt(
            "attempt-attack",
            "op-attack",
            "provider",
            "Circuit-C7",
            self.episode.episode_id,
            self.episode.q_version,
            100,
        )
        self.occurrence = RawOccurrence(
            "occ-attack",
            "O_E",
            "TARGET_NATIVE",
            "POWER_STATE_TRANSITION",
            "Circuit-C7",
            101,
            "op-attack",
            "UNPOWERED",
            "POWERED",
            3.0,
        )
        self.authority = AuthorityObservation(
            "O_S",
            "op-attack",
            "provider",
            "Circuit-C7",
            "Q@v1",
            AuthorityStatus.AUTHORIZED,
            100,
            "scope:op-attack:Circuit-C7",
        )

    def test_owner_response_transplant_cannot_become_target_native_effect(self):
        transplanted = RawOccurrence(
            "occ-resource",
            "O_R",
            "RESOURCE_ACCOUNTING",
            "POWER_STATE_TRANSITION",
            "Circuit-C7",
            101,
            "op-attack",
            "UNPOWERED",
            "POWERED",
            3.0,
        )
        result = assess_effect(
            self.episode, self.attempt, transplanted, self.authority
        )
        self.assertFalse(result.counts_toward_q)

    def test_wrong_target_effect_does_not_present_attempt_authority_as_applicable(self):
        wrong_target = RawOccurrence(
            "occ-wrong-target",
            "O_E",
            "TARGET_NATIVE",
            "POWER_STATE_TRANSITION",
            "Circuit-C8",
            101,
            "op-attack",
            "UNPOWERED",
            "POWERED",
            3.0,
            True,
        )
        result = assess_effect(
            self.episode, self.attempt, wrong_target, self.authority
        )
        # The raw O_S response remains AUTHORIZED history, but it must not be
        # presented as authority over the actual C8 occurrence.
        self.assertEqual(result.authority.status, AuthorityStatus.AUTHORIZED)
        self.assertFalse(result.authority_covers_actual_object)
        self.assertIn("AUTHORITY_DOES_NOT_COVER_ACTUAL_OBJECT", result.reasons)

    def test_preexisting_occurrence_does_not_inherit_current_q_binding(self):
        preexisting = RawOccurrence(
            "occ-preexisting",
            "O_E",
            "TARGET_NATIVE",
            "POWER_STATE_TRANSITION",
            "Circuit-C7",
            90,
            None,
            "UNPOWERED",
            "POWERED",
            3.0,
        )
        result = assess_effect(
            self.episode, self.attempt, preexisting, self.authority
        )
        # A current state may match Q while remaining causally unrelated to
        # this attempt.  The two coordinates must not collapse.
        self.assertTrue(result.current_state_matches_q)
        self.assertFalse(result.exact_attempt_causality)
        self.assertFalse(result.counts_toward_q)

    def test_attempt_from_another_episode_cannot_count(self):
        substituted_attempt = Attempt(
            self.attempt.attempt_id,
            self.attempt.operation_id,
            self.attempt.actor_id,
            self.attempt.target_id,
            "CE-001:other-episode",
            self.attempt.q_version,
            self.attempt.attempted_at,
        )
        result = assess_effect(
            self.episode, substituted_attempt, self.occurrence, self.authority
        )
        self.assertFalse(result.counts_toward_q)

    def test_post_effect_or_wrong_actor_authority_cannot_count(self):
        post_hoc = AuthorityObservation(
            "O_R",
            "op-attack",
            "different-actor",
            "Circuit-C7",
            "Q@v1",
            AuthorityStatus.AUTHORIZED,
            999,
            "provider-self-assertion",
        )
        result = assess_effect(
            self.episode, self.attempt, self.occurrence, post_hoc
        )
        self.assertFalse(result.counts_toward_q)

    def test_authority_observed_after_attempt_but_before_effect_is_too_late(self):
        post_commit = AuthorityObservation(
            "O_S",
            "op-attack",
            "provider",
            "Circuit-C7",
            "Q@v1",
            AuthorityStatus.AUTHORIZED,
            101,
            "scope:op-attack:Circuit-C7",
        )
        result = assess_effect(
            self.episode, self.attempt, self.occurrence, post_commit
        )
        self.assertFalse(result.authority_covers_actual_object)
        self.assertFalse(result.counts_toward_q)


class NoFreeTruthAttacks(unittest.TestCase):
    def test_zero_owner_queries_cannot_be_graded_as_correct_refusal(self):
        world = build_world("E5-IMPOSSIBLE-REFUSAL")
        world.plan = PublicPlan(
            case_id="E5-IMPOSSIBLE-REFUSAL",
            episode=Episode(
                "CE-001:E5-IMPOSSIBLE-REFUSAL", "Q@v1", "Circuit-C7"
            ),
            attempts=(),
        )

        with start_owner_session(world) as session:
            result = G6Method().run(world.plan, session.client)
        self.assertGreater(result.owner_query_count, 0)
        self.assertEqual(result.resolution, "BOUNDED_UNKNOWN")

    def test_e3_hidden_pair_has_same_opaque_method_visible_plan_shape(self):
        plan_a = build_world("E3A-ACK-LOST-EFFECT").plan
        plan_b = build_world("E3B-ACK-LOST-NO-EFFECT").plan

        def visible_shape(plan):
            return (
                plan.case_id,
                plan.episode.q_version,
                plan.episode.target_id,
                tuple(
                    (
                        item.actor_id,
                        item.target_id,
                        item.attempted_at,
                    )
                    for item in plan.attempts
                ),
                plan.resume_operation_id is not None,
            )

        self.assertEqual(visible_shape(plan_a), visible_shape(plan_b))


def _run_world(world):
    with start_owner_session(world) as session:
        result = G6Method().run(world.plan, session.client)
        snapshots = session.snapshots()
        trace = list(session.client.trace)
    return result, snapshots, trace


class DomainSeparationAttacks(unittest.TestCase):
    def test_wrong_authority_owner_cannot_trigger_execute(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.safety.response_overrides["authority"] = AuthorityObservation(
            "O_R",
            "op-platform",
            "venue-operator",
            "Circuit-C7",
            "Q@v1",
            AuthorityStatus.AUTHORIZED,
            100,
            "provider-self-report",
        )
        _result, _snapshots, trace = _run_world(world)
        self.assertNotIn("execute", [item.endpoint for item in trace])

    def test_transplanted_adoption_for_other_effect_and_episode_cannot_settle(self):
        adoption = AdoptionObservation(
            "O_R", "other-effect", "other-episode", Truth.TRUE, 103
        )
        world = build_world("E0-PLATFORM-DIRECT")
        world.venue.response_overrides["adoption"] = adoption
        result, _snapshots, _trace = _run_world(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_one_owner_response_cannot_satisfy_both_acceptances(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.venue.response_overrides["acceptance"] = AcceptanceObservation(
            "O_Q",
            "occ:E0-PLATFORM-DIRECT:op-platform",
            world.plan.episode.episode_id,
            "Q@v1",
            Truth.TRUE,
            104,
            "act:O_Q:transplanted",
            999,
        )
        result, _snapshots, _trace = _run_world(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_wrong_q_version_acceptance_is_rejected_control(self):
        world = build_world("E0-PLATFORM-DIRECT")
        effect_id = "occ:E0-PLATFORM-DIRECT:op-platform"
        world.query.response_overrides["acceptance"] = AcceptanceObservation(
            "O_Q", effect_id, world.plan.episode.episode_id, "Q@v2",
            Truth.TRUE, 104, "act:O_Q:wrong-q", 901
        )
        world.venue.response_overrides["acceptance"] = AcceptanceObservation(
            "O_V", effect_id, world.plan.episode.episode_id, "Q@v2",
            Truth.TRUE, 104, "act:O_V:wrong-q", 902
        )
        result, _snapshots, _trace = _run_world(world)
        self.assertEqual(result.resolution, "EFFECT_WITHOUT_ACCEPTANCE")
        self.assertEqual(result.settlements, [])

    def test_pre_effect_adoption_and_acceptance_cannot_settle(self):
        adoption = AdoptionObservation(
            "O_V",
            "occ:attack-method",
            "CE-001:attack-method",
            Truth.TRUE,
            50,
        )

        world = build_world("E0-PLATFORM-DIRECT")
        world.venue.response_overrides["adoption"] = adoption
        effect_id = "occ:E0-PLATFORM-DIRECT:op-platform"
        world.query.response_overrides["acceptance"] = AcceptanceObservation(
            "O_Q", effect_id, world.plan.episode.episode_id, "Q@v1",
            Truth.TRUE, 50, "act:O_Q:pre", 901
        )
        world.venue.response_overrides["acceptance"] = AcceptanceObservation(
            "O_V", effect_id, world.plan.episode.episode_id, "Q@v1",
            Truth.TRUE, 50, "act:O_V:pre", 902
        )
        result, _snapshots, _trace = _run_world(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])


class SettlementAndRecoveryAttacks(unittest.TestCase):
    def test_o_p_obligation_for_other_effect_cannot_settle_current_effect(self):
        obligation = Obligation(
            "obl:other-effect",
            "O_P",
            "other-effect",
            "CE_PAY_V1",
            "requester",
            "provider",
            ("CAPTURE", "PAYOUT"),
            ("REVERSAL",),
            105,
        )
        phases = [
            SchemePhase(
                obligation.obligation_id,
                obligation.scheme,
                "CAPTURE",
                Truth.TRUE,
                102,
                "other:capture",
            ),
            SchemePhase(
                obligation.obligation_id,
                obligation.scheme,
                "PAYOUT",
                Truth.TRUE,
                103,
                "other:payout",
            ),
            SchemePhase(
                obligation.obligation_id,
                obligation.scheme,
                "REVERSAL",
                Truth.FALSE,
                104,
                "other:reversal",
            ),
        ]
        world = build_world("E0-PLATFORM-DIRECT")
        world.payment.force_obligation_effect_id = "other-effect"
        result, _snapshots, _trace = _run_world(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")

    def test_provider_phases_for_wrong_obligation_and_scheme_cannot_be_final(self):
        obligation = Obligation(
            "obl-canonical",
            "resource-provider",
            "effect-canonical",
            "CE_PAY_V1",
            "requester",
            "provider",
            ("CAPTURE", "PAYOUT"),
            ("REVERSAL",),
            10,
        )
        phases = [
            SchemePhase(
                "obl-other", "PROVIDER_SELF_REPORT", "CAPTURE",
                Truth.TRUE, 2, "provider-capture"
            ),
            SchemePhase(
                "obl-other", "PROVIDER_SELF_REPORT", "PAYOUT",
                Truth.TRUE, 3, "provider-payout"
            ),
            SchemePhase(
                "obl-other", "PROVIDER_SELF_REPORT", "REVERSAL",
                Truth.FALSE, 4, "provider-reversal"
            ),
        ]
        result = assess_settlement(obligation, phases, observed_at=20)
        self.assertNotEqual(result.finality, Finality.FINAL)
        self.assertFalse(result.discharged)

    def test_recovery_receipt_without_target_state_change_cannot_close_episode(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        world.effect.recovery_mode = "BOGUS_TRANSPLANT"
        result, snapshots, _trace = _run_world(world)
        self.assertEqual(result.resolution, "RECOVERY_UNKNOWN")
        self.assertEqual(snapshots["O_E"]["state"]["recoveries"], [])

    def test_structurally_valid_recovery_event_without_state_mutation_cannot_close(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        world.effect.recovery_mode = "FORGED_NO_MUTATION"
        result, snapshots, _trace = _run_world(world)
        self.assertIn(
            result.resolution,
            {"RECOVERY_UNKNOWN", "BOUNDED_UNKNOWN"},
        )
        target = snapshots["O_E"]["state"]["targets"]["Circuit-C8"]
        self.assertEqual(target["state"], "POWERED")
        self.assertEqual(target["last_occurrence_id"], "occ:E3-ACK-LOST-OPAQUE:op-e3-primary")

    def test_future_scheme_phases_cannot_establish_current_finality(self):
        obligation = Obligation(
            "obl-future",
            "O_P",
            "effect",
            "CE_PAY_V1",
            "requester",
            "provider",
            ("PAYOUT",),
            ("REVERSAL",),
            10,
        )
        phases = [
            SchemePhase(
                "obl-future", "CE_PAY_V1", "PAYOUT",
                Truth.TRUE, 999, "future-payout"
            ),
            SchemePhase(
                "obl-future", "CE_PAY_V1", "REVERSAL",
                Truth.FALSE, 999, "future-reversal"
            ),
        ]
        result = assess_settlement(obligation, phases, observed_at=20)
        self.assertNotEqual(result.finality, Finality.FINAL)

    def test_distinct_occurrences_from_one_operation_are_duplicate_effects(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.occurrences.append(
            RawOccurrence(
                "occ:preloaded-duplicate",
                "O_E",
                "TARGET_NATIVE",
                "POWER_STATE_TRANSITION",
                "Circuit-C7",
                201,
                "op-platform",
                "UNPOWERED",
                "POWERED",
                3.0,
            )
        )
        result, _snapshots, _trace = _run_world(world)
        self.assertTrue(result.duplicate_effect)

    def test_e3b_success_resolution_preserves_wrong_target_history(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        result, _snapshots, _trace = _run_world(world)
        wrong_target = [
            effect for effect in result.effects
            if effect.occurrence.object_id == "Circuit-C8"
        ]
        self.assertEqual(len(wrong_target), 1)
        self.assertTrue(wrong_target[0].qualifies_as_effect)
        self.assertFalse(wrong_target[0].counts_toward_q)
        self.assertEqual(
            wrong_target[0].recovery.value,
            "REQUIRED",
        )


if __name__ == "__main__":
    unittest.main()
