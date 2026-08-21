from __future__ import annotations

from dataclasses import FrozenInstanceError
import inspect
from pathlib import Path
import unittest

from g3_discriminator import candidates
from g3_discriminator.candidates import (
    ActivationRunnerPolicy,
    FormationPolicy,
    ProducerOnlyPolicy,
    RemoveOperatorPolicy,
    ReverseOperatorPolicy,
    SameInformationStrongCenterHitlPolicy,
    StaticSearchPolicy,
    WrongAuthorityPolicy,
)
from g3_discriminator.runner import (
    build_summary,
    matched_worlds,
    run_main_matrix,
    run_policy,
)
from g3_discriminator.contract import ActionKind, CandidateAction
from g3_discriminator.truth import (
    HiddenWorld,
    OutcomeStatus,
    ReachabilityKind,
    TruthSession,
    WorldKind,
)


class G3DiscriminatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worlds = {world.kind: world for world in matched_worlds()}

    def test_contract_is_identical_across_d_a_f(self) -> None:
        contracts = [world.contract for world in self.worlds.values()]
        self.assertEqual(1, len({contract.fingerprint() for contract in contracts}))
        self.assertTrue(all(contract is contracts[0] for contract in contracts))
        self.assertEqual(
            (
                "principal:requester",
                "principal:provider",
                "principal:joint-authority-holder",
            ),
            contracts[0].necessary_principals,
        )
        self.assertEqual(
            "principal:joint-authority-holder",
            contracts[0].authority_locus,
        )
        self.assertEqual(
            "target://joint-path/readback",
            contracts[0].target_witness,
        )

    def test_contract_is_frozen(self) -> None:
        with self.assertRaises(FrozenInstanceError):
            self.worlds[WorldKind.DISCOVERY].contract.q = "lowered target"

    def test_d_is_discovery_not_formation(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.DISCOVERY], StaticSearchPolicy()
        )
        self.assertEqual(OutcomeStatus.SUCCESS, result.status)
        self.assertEqual(ReachabilityKind.DISCOVERY, result.reachability_kind)
        self.assertFalse(result.formation_supported)
        self.assertEqual("S0_EQUIVALENT_PATH_DISCOVERED", result.reason_code)

    def test_a_is_existing_resource_activation_not_formation(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.ACTIVATION], ActivationRunnerPolicy()
        )
        self.assertEqual(OutcomeStatus.SUCCESS, result.status)
        self.assertEqual(ReachabilityKind.ACTIVATION, result.reachability_kind)
        self.assertFalse(result.formation_supported)
        self.assertEqual("EXISTING_RESOURCE_ACTIVATED", result.reason_code)

    def test_f_is_operator_path_candidate_not_formation_proof(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.FORMATION], FormationPolicy()
        )
        self.assertEqual(OutcomeStatus.SUCCESS, result.status)
        self.assertEqual(
            ReachabilityKind.OPERATOR_PATH_CANDIDATE,
            result.reachability_kind,
        )
        self.assertFalse(result.formation_supported)
        self.assertIsNone(result.operator_necessary)
        self.assertTrue(result.authority_valid)
        self.assertTrue(result.target_witness_verified)
        self.assertEqual(
            "AUTHORIZED_OPERATOR_CREATED_PATH_CLOSURE_NOT_TESTED",
            result.reason_code,
        )

    def test_main_arm_matrix_preserves_unknown(self) -> None:
        matrix = {
            (report.world_id, report.policy): report
            for report in run_main_matrix()
        }
        expected = {
            ("D", "static_search"): OutcomeStatus.SUCCESS,
            ("D", "activation_runner"): OutcomeStatus.SUCCESS,
            ("D", "formation_policy"): OutcomeStatus.SUCCESS,
            (
                "D",
                "same_information_strong_center_hitl",
            ): OutcomeStatus.SUCCESS,
            ("A", "static_search"): OutcomeStatus.UNKNOWN,
            ("A", "activation_runner"): OutcomeStatus.SUCCESS,
            ("A", "formation_policy"): OutcomeStatus.SUCCESS,
            (
                "A",
                "same_information_strong_center_hitl",
            ): OutcomeStatus.SUCCESS,
            ("F", "static_search"): OutcomeStatus.UNKNOWN,
            ("F", "activation_runner"): OutcomeStatus.UNKNOWN,
            ("F", "formation_policy"): OutcomeStatus.SUCCESS,
            (
                "F",
                "same_information_strong_center_hitl",
            ): OutcomeStatus.SUCCESS,
        }
        self.assertEqual(expected, {key: value.status for key, value in matrix.items()})
        self.assertTrue(
            all(
                report.value_disposition == "UNKNOWN_PRESERVED"
                for report in matrix.values()
                if report.status is OutcomeStatus.UNKNOWN
            )
        )

    def test_wrong_authority_is_negative(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.FORMATION], WrongAuthorityPolicy()
        )
        self.assertEqual(OutcomeStatus.NEGATIVE, result.status)
        self.assertEqual("WRONG_AUTHORITY", result.reason_code)
        self.assertFalse(result.target_witness_verified)
        self.assertFalse(result.formation_supported)
        self.assertIsNone(result.operator_necessary)

    def test_producer_only_claim_is_not_target_effect(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.FORMATION], ProducerOnlyPolicy()
        )
        self.assertEqual(OutcomeStatus.NEGATIVE, result.status)
        self.assertEqual(
            "PRODUCER_ONLY_WITHOUT_TARGET_WITNESS", result.reason_code
        )
        self.assertFalse(result.final_reachable)
        self.assertFalse(result.target_witness_verified)
        self.assertIsNone(result.operator_necessary)

    def test_remove_operator_eliminates_path(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.FORMATION], RemoveOperatorPolicy()
        )
        self.assertEqual(OutcomeStatus.NEGATIVE, result.status)
        self.assertEqual(
            "REMOVE_OPERATOR_ELIMINATES_PATH", result.reason_code
        )
        self.assertIsNone(result.operator_necessary)
        self.assertTrue(result.current_effect_dependency)
        self.assertFalse(result.final_reachable)
        self.assertEqual(
            (
                "STATIC_SEARCH_COMPLETE",
                "ACTIVATION_RESULT",
                "FORMATION_OPERATOR_APPLIED",
                "TARGET_READBACK",
                "FORMATION_OPERATOR_REMOVED",
                "TARGET_READBACK",
            ),
            result.evidence,
        )

    def test_remove_absent_operator_is_noop_not_necessity_evidence(self) -> None:
        world = self.worlds[WorldKind.FORMATION]
        session = TruthSession(world)
        session.apply(
            CandidateAction(
                ActionKind.REMOVE_FORMATION_OPERATOR,
                authority_actor=world.contract.authority_locus,
            )
        )
        result = session.evaluate("direct_remove_without_apply")
        self.assertEqual(OutcomeStatus.UNKNOWN, result.status)
        self.assertEqual(
            "INSUFFICIENT_ACTION_OR_EVIDENCE", result.reason_code
        )
        self.assertIsNone(result.operator_necessary)
        self.assertEqual(
            ("FORMATION_OPERATOR_REMOVE_NOOP",),
            result.evidence,
        )

    def test_reverse_operator_eliminates_path(self) -> None:
        result = run_policy(
            self.worlds[WorldKind.FORMATION], ReverseOperatorPolicy()
        )
        self.assertEqual(OutcomeStatus.NEGATIVE, result.status)
        self.assertEqual(
            "REVERSE_OPERATOR_ELIMINATES_PATH", result.reason_code
        )
        self.assertIsNone(result.operator_necessary)
        self.assertTrue(result.current_effect_dependency)
        self.assertFalse(result.final_reachable)
        self.assertFalse(result.target_witness_verified)

    def test_same_policy_center_is_not_existing_solution_evidence(self) -> None:
        summary = build_summary()
        comparison = summary["comparative_result"]
        self.assertTrue(
            comparison["same_policy_central_topology_constructive_success"]
        )
        self.assertFalse(
            comparison["independent_existing_solution_baseline_implemented"]
        )
        self.assertEqual("NOT_TESTED", comparison["existing_solution_value"])
        self.assertEqual(
            "NOT_ESTABLISHED", comparison["pfe_a2a_unique_increment"]
        )
        self.assertFalse(comparison["novelty_scoring_used"])
        central = [
            report
            for report in summary["main"]
            if report["policy"] == "same_information_strong_center_hitl"
        ]
        self.assertTrue(
            all(
                report["value_disposition"]
                == "POSITIVE_SAME_POLICY_CENTRAL_TOPOLOGY_CONSTRUCTION"
                and report["novelty_score"] is None
                for report in central
            )
        )

    def test_classification_is_not_driven_by_world_kind_label(self) -> None:
        source = self.worlds[WorldKind.ACTIVATION]
        reports = []
        for kind in WorldKind:
            relabeled = HiddenWorld(
                world_id=f"same-flags-{kind.value}",
                kind=kind,
                contract=source.contract,
                s0_path_exists=source.s0_path_exists,
                inactive_existing_resource=source.inactive_existing_resource,
                authorized_formation_available=source.authorized_formation_available,
            )
            reports.append(run_policy(relabeled, ActivationRunnerPolicy()))
        self.assertEqual(
            {ReachabilityKind.ACTIVATION},
            {report.reachability_kind for report in reports},
        )

    def test_no_route_world_is_unknown_not_budget_failure(self) -> None:
        source = self.worlds[WorldKind.FORMATION]
        no_route = HiddenWorld(
            world_id="no-route",
            kind=WorldKind.FORMATION,
            contract=source.contract,
            s0_path_exists=False,
            inactive_existing_resource=False,
            authorized_formation_available=False,
        )
        result = run_policy(no_route, FormationPolicy())
        self.assertEqual(OutcomeStatus.UNKNOWN, result.status)
        self.assertEqual(
            "UNRESOLVED_OPERATOR_UNAVAILABLE", result.reason_code
        )
        self.assertEqual(3, result.actions_used)

    def test_truth_evaluator_is_separate_from_candidate_module(self) -> None:
        source = inspect.getsource(candidates)
        self.assertNotIn("from .truth", source)
        self.assertNotIn("import truth", source)
        candidate_path = Path(inspect.getfile(candidates))
        truth_path = candidate_path.with_name("truth.py")
        self.assertTrue(truth_path.exists())
        self.assertNotEqual(candidate_path, truth_path)

    def test_summary_is_deterministic_and_has_no_external_calls(self) -> None:
        first = build_summary()
        second = build_summary()
        self.assertEqual(first, second)
        self.assertEqual(0, first["external_model_calls"])
        self.assertTrue(first["matched_contract"]["all_equal"])
        self.assertEqual(
            {"NEGATIVE": 4, "SUCCESS": 9, "UNKNOWN": 3},
            first["status_counts"],
        )


if __name__ == "__main__":
    unittest.main()
