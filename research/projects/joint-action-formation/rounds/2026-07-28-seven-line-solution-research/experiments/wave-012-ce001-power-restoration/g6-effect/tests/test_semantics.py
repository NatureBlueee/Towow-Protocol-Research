import unittest

from model import (
    Attempt,
    AuthorityObservation,
    AuthorityStatus,
    Causality,
    Episode,
    Finality,
    Obligation,
    RawOccurrence,
    Recovery,
    SchemePhase,
    Truth,
    assess_effect,
    assess_settlement,
)


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.episode = Episode("ep", "Q@v1", "Circuit-C7")
        self.attempt = Attempt(
            "att", "op", "provider", "Circuit-C7", "ep", "Q@v1", 100
        )
        self.authority = AuthorityObservation(
            "O_S", "op", "provider", "Circuit-C7", "Q@v1",
            AuthorityStatus.AUTHORIZED, 100, "scope"
        )

    def occurrence(self, **overrides):
        values = {
            "occurrence_id": "occ",
            "owner_id": "O_E",
            "domain": "TARGET_NATIVE",
            "native_kind": "POWER_STATE_TRANSITION",
            "object_id": "Circuit-C7",
            "occurred_at": 101,
            "operation_id": "op",
            "from_state": "UNPOWERED",
            "to_state": "POWERED",
            "power_kw": 3.0,
            "damage": False,
        }
        values.update(overrides)
        return RawOccurrence(**values)

    def test_exact_attempt_authorized_effect_counts(self):
        value = assess_effect(
            self.episode, self.attempt, self.occurrence(), self.authority
        )
        self.assertTrue(value.qualifies_as_effect)
        self.assertTrue(value.counts_toward_q)
        self.assertTrue(value.current_state_matches_q)
        self.assertTrue(value.exact_attempt_causality)
        self.assertTrue(value.authority_covers_actual_object)
        self.assertEqual(value.episode_contribution, Truth.TRUE)
        self.assertEqual(value.causality, Causality.EXACT_ATTEMPT)

    def test_preexisting_state_does_not_inherit_attempt_causality(self):
        value = assess_effect(
            self.episode,
            self.attempt,
            self.occurrence(
                occurrence_id="pre", occurred_at=90, operation_id=None
            ),
            self.authority,
        )
        self.assertTrue(value.qualifies_as_effect)
        self.assertEqual(value.causality, Causality.PRE_EXISTING)
        self.assertTrue(value.current_state_matches_q)
        self.assertFalse(value.exact_attempt_causality)
        self.assertEqual(value.episode_contribution, Truth.FALSE)
        self.assertFalse(value.counts_toward_q)

    def test_wrong_target_damage_is_not_erased(self):
        value = assess_effect(
            self.episode,
            self.attempt,
            self.occurrence(object_id="Circuit-C8", damage=True),
            self.authority,
        )
        self.assertTrue(value.qualifies_as_effect)
        self.assertFalse(value.binding.exact_object)
        self.assertFalse(value.counts_toward_q)
        self.assertFalse(value.authority_covers_actual_object)
        self.assertEqual(value.episode_contribution, Truth.FALSE)
        self.assertIn("AUTHORITY_DOES_NOT_COVER_ACTUAL_OBJECT", value.reasons)
        self.assertEqual(value.recovery, Recovery.REQUIRED)

    def test_unauthorized_real_effect_is_not_erased(self):
        authority = AuthorityObservation(
            "O_S", "op", "provider", "Circuit-C7", "Q@v1",
            AuthorityStatus.REVOKED, 100, "scope"
        )
        value = assess_effect(
            self.episode, self.attempt, self.occurrence(), authority
        )
        self.assertTrue(value.qualifies_as_effect)
        self.assertFalse(value.counts_toward_q)
        self.assertEqual(value.recovery, Recovery.REQUIRED)

    def test_reversal_reopens_only_its_obligation(self):
        obligation = Obligation(
            "obl-a", "O_P", "effect-a", "SCHEME-A", "d", "b",
            ("CAPTURE", "PAYOUT"), ("DISPUTE", "REVERSAL"), 10
        )
        phases = [
            SchemePhase(
                "obl-a", "SCHEME-A", "CAPTURE", Truth.TRUE, 2, "cap"
            ),
            SchemePhase(
                "obl-a", "SCHEME-A", "PAYOUT", Truth.TRUE, 3, "pay"
            ),
            SchemePhase(
                "obl-a", "SCHEME-A", "DISPUTE", Truth.FALSE, 4, "disp"
            ),
            SchemePhase(
                "obl-a", "SCHEME-A", "REVERSAL", Truth.TRUE, 11, "rev", "pay"
            ),
        ]
        value = assess_settlement(obligation, phases, 12)
        self.assertEqual(value.finality, Finality.REVERSED)
        self.assertFalse(value.discharged)
        self.assertTrue(
            any(edge["kind"] == "REVERSES" for edge in value.graph["edges"])
        )

    def test_missing_reversal_head_is_unknown_not_false(self):
        obligation = Obligation(
            "obl-a", "O_P", "effect-a", "SCHEME-A", "d", "b",
            ("PAYOUT",), ("REVERSAL",), 10
        )
        phases = [
            SchemePhase(
                "obl-a", "SCHEME-A", "PAYOUT", Truth.TRUE, 3, "pay"
            )
        ]
        value = assess_settlement(obligation, phases, 12)
        self.assertEqual(value.finality, Finality.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
