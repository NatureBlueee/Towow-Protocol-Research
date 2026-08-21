import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from model import (  # noqa: E402
    AuthorityAssessment,
    AuthorityStratum,
    AuthorityStatus,
    Claim,
    ControlEdge,
    ControlEdgeKind,
    CountsTowardQ,
    Episode,
    EpisodeBinding,
    ObjectRef,
    Obligation,
    Occurrence,
    OwnerLedger,
    QualificationAssessment,
    QualificationStatus,
    RecoveryAssessment,
    RecoveryRelevance,
    Role,
    RoleAssignment,
    SchemePhaseRecord,
    SemanticError,
    SemanticModel,
    SettlementPhase,
    SubjectType,
    TruthValue,
)


def object_ref(local_id="asset-17", revision="v1"):
    return ObjectRef(
        authority_domain="target-owner",
        namespace="production",
        local_id=local_id,
        revision=revision,
        schema_version="object-v1",
        policy_version="policy-v1",
    )


def claim(
    claim_id,
    ledger_id,
    issuer,
    sequence,
    start,
    end,
    value=TruthValue.TRUE,
):
    return Claim(
        claim_id=claim_id,
        ledger_id=ledger_id,
        issuer_id=issuer,
        authority_scope="native-current-head",
        subject_id="asset-17",
        predicate="current-state",
        value=value,
        object_ref=object_ref(),
        observed_at_event=start,
        effective_from_event=start,
        effective_until_event=end,
        head_sequence=sequence,
    )


class SemanticModelTests(unittest.TestCase):
    def setUp(self):
        self.model = SemanticModel()
        self.model.add_episode(Episode("episode-a", "q-v1", "control-v1"))
        self.model.add_episode(Episode("episode-b", "q-v2", "control-v2"))

    def add_assignment_bundle(
        self,
        *,
        assignment_id,
        episode_id,
        occurrence,
        role,
        exact_binding=TruthValue.TRUE,
        authority_status=AuthorityStatus.AUTHORIZED,
        counts=TruthValue.TRUE,
        recovery=RecoveryRelevance.NONE,
        affected=None,
        obligation_id=None,
    ):
        if occurrence.occurrence_id not in self.model.occurrences:
            self.model.add_occurrence(occurrence)
        binding = EpisodeBinding(
            binding_id="bind-" + assignment_id,
            episode_id=episode_id,
            subject_id=occurrence.occurrence_id,
            episode_object_ref=object_ref(),
            observed_object_ref=occurrence.object_ref,
            exact_binding=exact_binding,
            current_version=TruthValue.TRUE,
            valid_time=TruthValue.TRUE,
            rule_version="binding-v1",
        )
        qualification = QualificationAssessment(
            qualification_id="qual-" + assignment_id,
            assignment_id=assignment_id,
            episode_id=episode_id,
            status=QualificationStatus.QUALIFIES,
            reason="native occurrence satisfies role predicate",
        )
        authority = AuthorityAssessment(
            authority_id="auth-" + assignment_id,
            episode_id=episode_id,
            assignment_id=assignment_id,
            principal_id="principal",
            acting_subject_id=occurrence.actor_id,
            authority_locus="owner-policy",
            scope_role=role,
            object_ref=occurrence.object_ref,
            status=authority_status,
            decided_at_event=occurrence.occurred_at_event,
        )
        q_count = CountsTowardQ(
            counts_id="count-" + assignment_id,
            assignment_id=assignment_id,
            episode_id=episode_id,
            counts=counts,
            q_version=self.model.episodes[episode_id].q_version,
            reason="explicit episode qualification decision",
        )
        recovery_assessment = RecoveryAssessment(
            recovery_id="recovery-" + assignment_id,
            assignment_id=assignment_id,
            episode_id=episode_id,
            occurrence_id=occurrence.occurrence_id,
            relevance=recovery,
            affected_objects=tuple(affected or ()),
            reason="explicit recovery decision",
        )
        self.model.add_binding(binding)
        self.model.add_qualification(qualification)
        self.model.add_authority(authority)
        self.model.add_counts_toward_q(q_count)
        self.model.add_recovery(recovery_assessment)
        assignment = RoleAssignment(
            assignment_id=assignment_id,
            subject_type=SubjectType.OCCURRENCE,
            subject_id=occurrence.occurrence_id,
            episode_id=episode_id,
            role=role,
            subtype="task-specific",
            qualification_rule_version="role-v1",
            binding_id=binding.binding_id,
            qualification_id=qualification.qualification_id,
            authority_id=authority.authority_id,
            counts_id=q_count.counts_id,
            recovery_id=recovery_assessment.recovery_id,
            obligation_id=obligation_id,
        )
        self.model.add_assignment(assignment)
        return self.model.evaluate_assignment(assignment_id)

    def test_role_is_many_to_many_without_copying_occurrence(self):
        payment = Occurrence(
            occurrence_id="occ-payment",
            domain="bank",
            native_kind="balance-transfer",
            actor_id="bank",
            object_ref=object_ref("payment-9"),
            occurred_at_event=4,
        )
        first = self.add_assignment_bundle(
            assignment_id="effect-role",
            episode_id="episode-a",
            occurrence=payment,
            role=Role.EFFECT,
        )
        self.model.add_obligation(
            Obligation(
                "payment-obligation",
                "episode-b",
                "payment-scheme",
                "debtor",
                "beneficiary",
                100,
                "USD",
                (SettlementPhase.PAYOUT,),
                (),
            )
        )
        second = self.add_assignment_bundle(
            assignment_id="settlement-role",
            episode_id="episode-b",
            occurrence=payment,
            role=Role.SETTLEMENT,
            obligation_id="payment-obligation",
        )
        self.assertEqual(len(self.model.occurrences), 1)
        self.assertEqual(
            {item.role for item in self.model.assignments_for_subject("occ-payment")},
            {Role.EFFECT, Role.SETTLEMENT},
        )
        self.assertEqual(first.assignment.subject_id, second.assignment.subject_id)

    def test_unauthorized_real_effect_remains_recoverable_but_does_not_count(self):
        occurrence = Occurrence(
            occurrence_id="occ-illegal-effect",
            domain="cnc",
            native_kind="parameter-transition",
            actor_id="replayed-worker",
            object_ref=object_ref(),
            occurred_at_event=7,
            transition_from="safe",
            transition_to="changed",
        )
        evaluation = self.add_assignment_bundle(
            assignment_id="illegal-effect",
            episode_id="episode-a",
            occurrence=occurrence,
            role=Role.EFFECT,
            authority_status=AuthorityStatus.UNAUTHORIZED,
            counts=TruthValue.FALSE,
            recovery=RecoveryRelevance.REQUIRED,
            affected=(object_ref(),),
        )
        self.assertEqual(
            evaluation.qualification.status, QualificationStatus.QUALIFIES
        )
        self.assertEqual(
            evaluation.authority.status, AuthorityStatus.UNAUTHORIZED
        )
        self.assertEqual(evaluation.counts_toward_q.counts, TruthValue.FALSE)
        self.assertEqual(
            evaluation.recovery.relevance, RecoveryRelevance.REQUIRED
        )
        self.assertIn("occ-illegal-effect", self.model.occurrences)

    def test_wrong_target_damage_is_not_erased_by_episode_binding(self):
        damaged = object_ref("asset-71")
        occurrence = Occurrence(
            occurrence_id="occ-wrong-target",
            domain="cnc",
            native_kind="physical-damage",
            actor_id="authorized-worker",
            object_ref=damaged,
            occurred_at_event=8,
        )
        evaluation = self.add_assignment_bundle(
            assignment_id="wrong-target",
            episode_id="episode-a",
            occurrence=occurrence,
            role=Role.EFFECT,
            exact_binding=TruthValue.FALSE,
            counts=TruthValue.FALSE,
            recovery=RecoveryRelevance.REQUIRED,
            affected=(damaged,),
        )
        self.assertEqual(evaluation.binding.exact_binding, TruthValue.FALSE)
        self.assertEqual(evaluation.counts_toward_q.counts, TruthValue.FALSE)
        self.assertEqual(
            evaluation.recovery.affected_objects[0].local_id, "asset-71"
        )
        self.assertEqual(
            evaluation.qualification.status, QualificationStatus.QUALIFIES
        )

    def test_claim_subject_can_receive_multiple_roles(self):
        ledger = OwnerLedger("owner-ledger", "owner")
        self.model.add_ledger(ledger)
        owner_claim = claim("claim-accepted", "owner-ledger", "owner", 1, 1, None)
        self.model.append_claim(owner_claim)
        for assignment_id, role in (
            ("claim-as-acceptance", Role.ACCEPTANCE),
            ("claim-as-effect", Role.EFFECT),
        ):
            binding = EpisodeBinding(
                "bind-" + assignment_id,
                "episode-a",
                owner_claim.claim_id,
                object_ref(),
                object_ref(),
                TruthValue.TRUE,
                TruthValue.TRUE,
                TruthValue.TRUE,
                "binding-v1",
            )
            qualification = QualificationAssessment(
                "qual-" + assignment_id,
                assignment_id,
                "episode-a",
                QualificationStatus.QUALIFIES,
                "claim fits episode-relative role",
            )
            self.model.add_binding(binding)
            self.model.add_qualification(qualification)
            self.model.add_assignment(
                RoleAssignment(
                    assignment_id,
                    SubjectType.CLAIM,
                    owner_claim.claim_id,
                    "episode-a",
                    role,
                    "claim-role",
                    "role-v1",
                    binding.binding_id,
                    qualification.qualification_id,
                )
            )
        self.assertEqual(
            len(self.model.assignments_for_subject(owner_claim.claim_id)), 2
        )

    def test_owner_ledger_rejects_non_owner_claim(self):
        ledger = OwnerLedger("owner-ledger", "owner")
        with self.assertRaises(SemanticError):
            ledger.append_claim(
                claim("bad", "owner-ledger", "not-owner", 1, 0, None)
            )

    def test_stale_and_fresh_claims_are_distinct_from_current_truth(self):
        ledger = OwnerLedger("target-ledger", "target-owner")
        self.model.add_ledger(ledger)
        stale = claim("head-v1", "target-ledger", "target-owner", 1, 0, 5)
        fresh = claim(
            "head-v2",
            "target-ledger",
            "target-owner",
            2,
            5,
            None,
            TruthValue.FALSE,
        )
        self.model.append_claim(stale)
        self.model.append_claim(fresh)
        self.assertEqual(ledger.current_head(4), stale)
        self.assertEqual(ledger.current_head(5), fresh)
        self.assertTrue(stale.value == TruthValue.TRUE)
        self.assertFalse(stale.is_effective(5))

    def test_read_skew_has_no_consistent_cut(self):
        acceptance = OwnerLedger("acceptance-ledger", "acceptance-owner")
        settlement = OwnerLedger("settlement-ledger", "settlement-owner")
        self.model.add_ledger(acceptance)
        self.model.add_ledger(settlement)
        old_acceptance = claim(
            "accepted-v4",
            "acceptance-ledger",
            "acceptance-owner",
            1,
            0,
            5,
        )
        late_settlement = claim(
            "settled-v4",
            "settlement-ledger",
            "settlement-owner",
            1,
            6,
            None,
        )
        self.model.append_claim(old_acceptance)
        self.model.append_claim(late_settlement)
        result = self.model.assess_head_vector(
            {
                "acceptance-ledger": "accepted-v4",
                "settlement-ledger": "settled-v4",
            }
        )
        self.assertFalse(result.consistent)
        self.assertIn("no common validity window", result.reasons[0])

    def test_consistent_cut_requires_each_claim_to_be_current_head(self):
        first = OwnerLedger("first-ledger", "first-owner")
        second = OwnerLedger("second-ledger", "second-owner")
        self.model.add_ledger(first)
        self.model.add_ledger(second)
        first_claim = claim("first-head", "first-ledger", "first-owner", 1, 2, None)
        second_claim = claim(
            "second-head", "second-ledger", "second-owner", 1, 2, None
        )
        self.model.append_claim(first_claim)
        self.model.append_claim(second_claim)
        result = self.model.assess_head_vector(
            {"first-ledger": "first-head", "second-ledger": "second-head"}
        )
        self.assertTrue(result.consistent)
        self.assertEqual(result.cut_event, 2)

    def test_provider_settled_is_not_payout(self):
        self._add_settlement_setup()
        self._add_phase(
            "provider-settled",
            SettlementPhase.SCHEME_SETTLEMENT,
            TruthValue.TRUE,
            1,
        )
        result = self.model.settlement_status("obligation-1", 2)
        self.assertEqual(result.status, QualificationStatus.UNKNOWN)
        self.assertTrue(any("PAYOUT" in reason for reason in result.reasons))

    def test_open_chargeback_blocks_completed_payout(self):
        self._add_settlement_setup()
        self._add_phase("payout", SettlementPhase.PAYOUT, TruthValue.TRUE, 1)
        self._add_phase(
            "beneficiary-receipt",
            SettlementPhase.BENEFICIARY_RECEIPT,
            TruthValue.TRUE,
            2,
        )
        self._add_phase(
            "chargeback-open",
            SettlementPhase.CHARGEBACK,
            TruthValue.TRUE,
            3,
        )
        result = self.model.settlement_status("obligation-1", 4)
        self.assertEqual(result.status, QualificationStatus.DISPUTED)
        self.assertIn("CHARGEBACK is open", result.reasons)

    def test_closed_blocker_allows_scheme_specific_discharge(self):
        self._add_settlement_setup()
        self._add_phase("payout", SettlementPhase.PAYOUT, TruthValue.TRUE, 1)
        self._add_phase(
            "beneficiary-receipt",
            SettlementPhase.BENEFICIARY_RECEIPT,
            TruthValue.TRUE,
            2,
        )
        self._add_phase(
            "chargeback-closed",
            SettlementPhase.CHARGEBACK,
            TruthValue.FALSE,
            3,
        )
        self._add_phase(
            "reversal-closed",
            SettlementPhase.REVERSAL,
            TruthValue.FALSE,
            4,
        )
        result = self.model.settlement_status("obligation-1", 5)
        self.assertEqual(result.status, QualificationStatus.QUALIFIES)

    def test_lawful_delegation_requires_chain_and_scope(self):
        with self.assertRaises(SemanticError):
            self.model.add_authority(
                AuthorityAssessment(
                    authority_id="bad-delegation",
                    episode_id="episode-a",
                    assignment_id="future-assignment",
                    principal_id="owner",
                    acting_subject_id="center",
                    authority_locus="delegation",
                    scope_role=Role.ACCEPTANCE,
                    object_ref=object_ref(),
                    status=AuthorityStatus.AUTHORIZED,
                    decided_at_event=1,
                    stratum=AuthorityStratum.S3_LAWFULLY_DELEGATED,
                )
            )

    def test_graph_layers_reject_cross_layer_edges(self):
        occurrence = Occurrence(
            "occ-one",
            "target",
            "transition",
            "actor",
            object_ref(),
            1,
        )
        self.model.add_occurrence(occurrence)
        self.model.add_obligation(
            Obligation(
                "obligation-cross",
                "episode-a",
                "scheme",
                "debtor",
                "beneficiary",
                1,
                "USD",
                (SettlementPhase.PAYOUT,),
                (),
            )
        )
        with self.assertRaises(SemanticError):
            self.model.add_control_edge(
                ControlEdge(
                    "bad-cross-edge",
                    occurrence.occurrence_id,
                    "obligation-cross",
                    ControlEdgeKind.REQUIRES,
                    "control-v1",
                )
            )
        self.model.validate_graph_separation()

    def _add_settlement_setup(self):
        ledger = OwnerLedger("scheme-ledger", "scheme-owner")
        self.model.add_ledger(ledger)
        self.model.add_obligation(
            Obligation(
                obligation_id="obligation-1",
                episode_id="episode-a",
                scheme_id="payment-scheme-v1",
                debtor_id="buyer",
                beneficiary_id="seller",
                amount_minor=1000,
                currency="USD",
                required_phases=(
                    SettlementPhase.PAYOUT,
                    SettlementPhase.BENEFICIARY_RECEIPT,
                ),
                blocking_phases=(
                    SettlementPhase.CHARGEBACK,
                    SettlementPhase.REVERSAL,
                ),
            )
        )

    def _add_phase(self, record_id, phase, value, sequence):
        claim_id = "claim-" + record_id
        self.model.append_claim(
            Claim(
                claim_id=claim_id,
                ledger_id="scheme-ledger",
                issuer_id="scheme-owner",
                authority_scope=phase.value,
                subject_id="obligation-1",
                predicate=phase.value,
                value=value,
                object_ref=None,
                observed_at_event=sequence,
                effective_from_event=sequence,
                effective_until_event=None,
                head_sequence=sequence,
            )
        )
        self.model.add_scheme_phase_record(
            SchemePhaseRecord(
                phase_record_id=record_id,
                obligation_id="obligation-1",
                scheme_id="payment-scheme-v1",
                phase=phase,
                value=value,
                owner_id="scheme-owner",
                claim_id=claim_id,
                effective_from_event=sequence,
                effective_until_event=None,
                head_sequence=sequence,
            )
        )


if __name__ == "__main__":
    unittest.main()
