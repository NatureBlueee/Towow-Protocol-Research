import unittest

from towow_fieldkit.opc import CoordinationContext, CoordinationMode, OPCOperatingEnvelope
from towow_fieldkit.router import route_coordination
from towow_fieldkit.reopen import affected_dependency_closure
from towow_fieldkit.stability import EnactmentAssurance, StabilityVector
from towow_fieldkit.frames import FrameScope, RelationFrameRef


class OPCExtensionTests(unittest.TestCase):
    def test_standard_api_collapses(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.95, standardization=.95,
            private_context_intensity=.1, authority_plurality=1,
            externality_risk=.1, irreversibility=.2, volatility=.1,
            evidence_burden=.2, platform_frame_sufficient=True,
            centralizable_within_grants=True, deterministic_interface_available=True,
        )
        r = route_coordination(c)
        self.assertTrue(r.collapse_safe)
        self.assertEqual(r.steps[0].mode, CoordinationMode.DETERMINISTIC_SERVICE)

    def test_private_custom_work_requires_formation(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.35, standardization=.2,
            private_context_intensity=.9, authority_plurality=3,
            externality_risk=.5, irreversibility=.7, volatility=.6,
            evidence_burden=.8, platform_frame_sufficient=False,
            centralizable_within_grants=False, broker_available=True,
            human_acceptance_required=True, capacity_pressure=.8,
        )
        r = route_coordination(c)
        self.assertTrue(r.open_formation_required)
        self.assertEqual([s.mode for s in r.steps], [CoordinationMode.HUMAN_BROKER, CoordinationMode.BILATERAL_FORMATION])
        self.assertIn('minimal disclosure / local oracle', r.steps[-1].mandatory_controls)

    def test_multi_party_relation_uses_temporary_coalition(self):
        c = CoordinationContext(
            participants=4, schema_completeness=.55, standardization=.4,
            private_context_intensity=.5, authority_plurality=4,
            externality_risk=.3, irreversibility=.4, volatility=.5,
            evidence_burden=.5, platform_frame_sufficient=False,
            centralizable_within_grants=False,
        )
        r = route_coordination(c)
        self.assertEqual(r.steps[-1].mode, CoordinationMode.TEMPORARY_COALITION)

    def test_active_dispute_goes_to_adjudication(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.8, standardization=.8,
            private_context_intensity=.2, authority_plurality=2,
            externality_risk=.2, irreversibility=.8, volatility=.2,
            evidence_burden=.8, platform_frame_sufficient=True,
            centralizable_within_grants=True, dispute_active=True,
        )
        r = route_coordination(c)
        self.assertEqual(r.steps[0].mode, CoordinationMode.HUMAN_ADJUDICATION)

    def test_self_execution(self):
        c = CoordinationContext(
            participants=1, schema_completeness=.7, standardization=.4,
            private_context_intensity=.9, authority_plurality=1,
            externality_risk=.1, irreversibility=.2, volatility=.2,
            evidence_burden=.2, platform_frame_sufficient=False,
            centralizable_within_grants=True, self_executable=True,
        )
        r = route_coordination(c)
        self.assertEqual(r.steps[0].mode, CoordinationMode.SELF_EXECUTION)

    def test_repeated_relation_adds_compile_stage(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.65, standardization=.55,
            private_context_intensity=.6, authority_plurality=2,
            externality_risk=.2, irreversibility=.3, volatility=.2,
            evidence_burden=.4, platform_frame_sufficient=False,
            centralizable_within_grants=False, repeated_relation=True,
        )
        r = route_coordination(c)
        self.assertEqual(r.steps[-1].mode, CoordinationMode.DETERMINISTIC_SERVICE)

    def test_local_reopen_closure(self):
        edges = {'data_grant':['analysis'], 'analysis':['report','invoice'], 'report':['acceptance']}
        self.assertEqual(affected_dependency_closure(['data_grant'], edges), ['acceptance','analysis','data_grant','invoice','report'])

    def test_stability_and_enactment(self):
        s=StabilityVector(True,True,True,False,True)
        self.assertFalse(s.passed())
        self.assertEqual(s.failures(), ['normative_legitimacy'])
        a=EnactmentAssurance(True,True,True,True,True,False)
        self.assertFalse(a.enacted())

    def test_opc_envelope_validates(self):
        e=OPCOperatingEnvelope('person:1',('owner','delivery'),cash_capacity=1000,attention_hours_available=8)
        self.assertEqual(e.validate(),[])

    def test_multi_party_scheduler_centralizes_computation_and_reserves_slots(self):
        c = CoordinationContext(
            participants=3, schema_completeness=.95, standardization=.9,
            private_context_intensity=.3, authority_plurality=1,
            externality_risk=.05, irreversibility=.05, volatility=.2,
            evidence_burden=.1, platform_frame_sufficient=True,
            centralizable_within_grants=True, optimization_problem=True,
        )
        d = route_coordination(c)
        self.assertEqual([x.mode for x in d.steps], [CoordinationMode.CENTRAL_OPTIMIZER])
        self.assertIn("resource reservation", d.steps[0].mandatory_controls)

    def test_candidate_computation_can_be_centralized_without_authority_collapse(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.85, standardization=.8,
            private_context_intensity=.35, authority_plurality=2,
            externality_risk=.15, irreversibility=.25, volatility=.5,
            evidence_burden=.4, platform_frame_sufficient=True,
            centralizable_within_grants=True, optimization_problem=True,
        )
        d = route_coordination(c)
        self.assertEqual([x.mode for x in d.steps], [CoordinationMode.CENTRAL_OPTIMIZER])
        self.assertFalse(d.collapse_safe)
        self.assertFalse(d.open_formation_required)
        self.assertIn("do not mutate local authority", d.steps[0].mandatory_controls)

    def test_high_evidence_deterministic_filing_can_compile_with_preflight(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.98, standardization=.98,
            private_context_intensity=.7, authority_plurality=1,
            externality_risk=.2, irreversibility=.5, volatility=.1,
            evidence_burden=.9, platform_frame_sufficient=True,
            centralizable_within_grants=True, deterministic_interface_available=True,
        )
        d = route_coordination(c)
        self.assertEqual([x.mode for x in d.steps], [CoordinationMode.DETERMINISTIC_SERVICE])
        self.assertIn("pre-effect validation", d.steps[0].mandatory_controls)

    def test_dispute_preserves_relation_and_separates_effect_from_acceptance(self):
        c = CoordinationContext(
            participants=2, schema_completeness=.65, standardization=.5,
            private_context_intensity=.5, authority_plurality=2,
            externality_risk=.2, irreversibility=.75, volatility=.2,
            evidence_burden=.9, platform_frame_sufficient=True,
            centralizable_within_grants=False, dispute_active=True,
            human_acceptance_required=True,
        )
        d = route_coordination(c)
        controls=set(d.steps[0].mandatory_controls)
        self.assertEqual(d.steps[0].mode, CoordinationMode.HUMAN_ADJUDICATION)
        self.assertIn("preserve prior versions", controls)
        self.assertIn("effect/acceptance separation", controls)
        self.assertIn("minimal disclosure / local oracle", controls)

    def test_relation_frame_reference_blocks_unresolved_conflict(self):
        f=RelationFrameRef(
            frame_id='relation:course-collab', frame_scope=FrameScope.RELATION,
            frame_version='2', inherits_from=('platform:payments:v4',),
            overrides=('A.approval','D.training_rights'), unresolved_conflicts=('D.training_rights',),
        )
        self.assertEqual(f.validate(),[])
        self.assertFalse(f.compile_ready())



if __name__ == '__main__':
    unittest.main()

