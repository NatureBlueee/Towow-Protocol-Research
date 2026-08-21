from __future__ import annotations

from dataclasses import replace
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch

from qhm1.authorities import ActionRequest
from qhm1.checker import BoundedModelChecker
from qhm1.execution import PublicFacts, TaskEvaluator, TrialGateway, TrialRuntime
from qhm1.policies import (
    FormationCandidate,
    MatureWorkflowComposition,
    StrongCenterHitl,
)
from qhm1.runner import build_report
from qhm1.spec import (
    ACTION_SPECS,
    OLD_TASK,
    expected_action_payload,
    expected_holder,
    fingerprint,
    frozen_package,
)
from qhm1.worlds import hidden_worlds


EXPECTED_DEPTHS = {
    "discover": 0,
    "enable": 1,
    "commit": 1,
    "build-known": 1,
    "extend": 2,
    "drift": None,
    "substitute": None,
    "unsat": None,
}


def _always_stop_a(self, facts):
    return None


def _always_stop_b(self, facts):
    _ = facts
    return None


def _always_stop_c(self, facts):
    if facts:
        return None
    return tuple()


def _dead_transition(world, state, action):
    return None


class Qhm1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.worlds = {world.truth_id: world for world in hidden_worlds()}

    def test_frozen_executable_package_binds_required_objects(self) -> None:
        package = frozen_package(self.worlds["discover"])
        self.assertEqual("QHM1-OLD-TASK-v1", OLD_TASK.task_id)
        self.assertEqual(10, package.resource_account.horizon)
        self.assertEqual(10, package.resource_account.max_cost)
        self.assertEqual(2, package.resource_account.max_privacy_cost)
        self.assertEqual({0, 1, 2}, {spec.layer for spec in ACTION_SPECS})
        self.assertIn("task", package.fingerprints)
        self.assertIn("action_model", package.fingerprints)
        self.assertIn("authority_map", package.fingerprints)
        self.assertIn("principal_policies", package.fingerprints)
        self.assertIn("resource_account", package.fingerprints)
        self.assertNotEqual(
            package.package_fingerprint,
            replace(
                package,
                resource_account=replace(
                    package.resource_account,
                    max_cost=package.resource_account.max_cost + 1,
                ),
            ).recompute_fingerprint(),
        )

    def test_exhaustive_checker_derives_expected_l0_l1_l2_depths(self) -> None:
        checker = BoundedModelChecker()
        for truth_id, expected_depth in EXPECTED_DEPTHS.items():
            closure = checker.check_all_layers(self.worlds[truth_id])
            self.assertEqual(expected_depth, closure.formation_depth, truth_id)
            for level, result in enumerate(closure.layers):
                self.assertEqual(level, result.max_layer)
                self.assertGreater(result.explored_states, 0)
                if result.sat:
                    self.assertTrue(result.witness)
                    self.assertIsNone(result.unsat_certificate)
                else:
                    self.assertFalse(result.witness)
                    self.assertIsNotNone(result.unsat_certificate)
                    self.assertTrue(result.unsat_certificate.frontier_exhausted)
                    self.assertEqual(
                        frozen_package(self.worlds[truth_id]).action_model_fingerprint,
                        result.unsat_certificate.action_model_fingerprint,
                    )

    def test_world_labels_are_not_available_to_system_policies(self) -> None:
        import qhm1.policies as policies

        source = inspect.getsource(policies)
        self.assertNotIn("from .worlds", source)
        self.assertNotIn("import worlds", source)
        public_ids = {world.public_trial_id for world in self.worlds.values()}
        self.assertEqual(10, len(public_ids))
        self.assertTrue(
            all(world.truth_id not in world.public_trial_id for world in self.worlds.values())
        )

    def test_systems_have_exact_capability_parity(self) -> None:
        systems = (
            StrongCenterHitl(),
            MatureWorkflowComposition(),
            FormationCandidate(),
        )
        capabilities = {system.capabilities for system in systems}
        self.assertEqual(1, len(capabilities))
        self.assertEqual(
            tuple(spec.name for spec in ACTION_SPECS),
            systems[0].capabilities,
        )
        self.assertIsNot(
            StrongCenterHitl.plan, MatureWorkflowComposition.plan
        )
        self.assertIsNot(
            StrongCenterHitl.plan, FormationCandidate.plan
        )
        self.assertIsNot(
            MatureWorkflowComposition.plan, FormationCandidate.plan
        )
        report = build_report()
        self.assertTrue(
            report["capability_parity"][
                "policy_implementations_distinct"
            ]
        )
        self.assertTrue(
            report["capability_parity"][
                "behaviorally_distinct_on_fixture"
            ]
        )
        self.assertEqual(
            3,
            len(
                set(
                    report["capability_parity"][
                        "policy_implementation_fingerprints"
                    ].values()
                )
            ),
        )
        combo_actions = {
            tuple(run["completed_actions"])
            for run in report["runs"]
            if run["truth_id"] == "combo"
        }
        self.assertEqual(3, len(combo_actions))

    def test_privileged_effects_are_executed_by_holder_objects(self) -> None:
        runtime = TrialRuntime(self.worlds["extend"])
        result = StrongCenterHitl().run(runtime.gateway())
        trusted_anchor = runtime.trusted_anchor()
        evaluation = TaskEvaluator(
            runtime.package.package_fingerprint,
            runtime.registry,
            trusted_anchor,
        ).evaluate(
            runtime.bundle(),
            fingerprint(result.public_facts),
        )
        self.assertEqual("REQUESTED_SUCCESS", result.requested_terminal)
        self.assertTrue(evaluation.qualified)
        privileged = [
            receipt
            for receipt in runtime.bundle().receipts
            if expected_holder(receipt.action) is not None
        ]
        self.assertTrue(privileged)
        effect_by_id = {
            effect.effect_log_id: effect
            for effect in trusted_anchor.effect_records
        }
        self.assertTrue(
            all(
                receipt.holder_id == expected_holder(receipt.action)
                and receipt.executor_object_id.startswith("holder-object:")
                and receipt.holder_id != "C"
                and receipt.effect_log_id in effect_by_id
                and effect_by_id[
                    receipt.effect_log_id
                ].receipt_id == receipt.receipt_id
                for receipt in privileged
            )
        )
        forged = replace(
            privileged[0],
            holder_id="C",
            executor_object_id="controller:self-report",
            signature="forged",
        )
        self.assertFalse(runtime.registry.verify(forged))
        self.assertFalse(hasattr(runtime.bundle(), "registry"))
        package_tamper = replace(
            runtime.bundle(),
            package_fingerprint="0" * 64,
        )
        self.assertFalse(
            TaskEvaluator(
                runtime.package.package_fingerprint,
                runtime.registry,
                trusted_anchor,
            ).evaluate(
                package_tamper,
                fingerprint(result.public_facts),
            ).qualified
        )

        wrong_payload_receipt = runtime.registry.dispatch(
            ActionRequest(
                action="ACCEPT",
                payload={"claimant_supplied": "wrong-payload"},
                task_fingerprint=fingerprint(OLD_TASK),
            )
        )
        self.assertIsNone(wrong_payload_receipt)

        unsat_runtime = TrialRuntime(self.worlds["unsat"])
        refused_receipt = unsat_runtime.registry.dispatch(
            ActionRequest(
                action="ISSUE_AUTHORIZATION",
                payload=expected_action_payload("ISSUE_AUTHORIZATION"),
                task_fingerprint=fingerprint(OLD_TASK),
            )
        )
        self.assertIsNone(refused_receipt)
        with self.assertRaises(TypeError):
            unsat_runtime.registry.dispatch(
                ActionRequest(
                    action="ISSUE_AUTHORIZATION",
                    payload=expected_action_payload(
                        "ISSUE_AUTHORIZATION"
                    ),
                    task_fingerprint=fingerprint(OLD_TASK),
                ),
                lambda _: True,
                lambda _: None,
            )

        bundle = runtime.bundle()
        original_acceptance = next(
            receipt
            for receipt in bundle.receipts
            if receipt.action == "ACCEPT"
        )
        renamed_acceptance = replace(
            original_acceptance,
            receipt_id="T:renamed:ACCEPT",
        )
        bad_receipts = tuple(
            renamed_acceptance
            if receipt.receipt_id == original_acceptance.receipt_id
            else receipt
            for receipt in bundle.receipts
        )
        bad_trace = tuple(
            replace(event, receipt_id=renamed_acceptance.receipt_id)
            if event.action == "ACCEPT"
            else event
            for event in bundle.trace
        )
        wrong_payload_evaluation = TaskEvaluator(
            runtime.package.package_fingerprint,
            runtime.registry,
            trusted_anchor,
        ).evaluate(
            replace(
                bundle,
                receipts=bad_receipts,
                trace=bad_trace,
            ),
            fingerprint(result.public_facts),
        )
        self.assertFalse(wrong_payload_evaluation.qualified)
        self.assertFalse(wrong_payload_evaluation.authority_valid)

        broken_target = replace(
            bundle.target_records[0],
            project_receipt_id="T:missing:PROJECT",
        )
        broken_target_evaluation = TaskEvaluator(
            runtime.package.package_fingerprint,
            runtime.registry,
            trusted_anchor,
        ).evaluate(
            replace(bundle, target_records=(broken_target,)),
            fingerprint(result.public_facts),
        )
        self.assertFalse(broken_target_evaluation.qualified)
        self.assertFalse(broken_target_evaluation.target_valid)

        record = bundle.inspection_records[0]
        forged_facts = replace(
            record.facts,
            initial_message="COORDINATED FORGERY",
            route="UNAVAILABLE",
            authorization="REFUSE",
            value_floor="FAIL",
        )
        forged_hash = fingerprint(forged_facts)
        forged_record = replace(
            record,
            facts=forged_facts,
            facts_hash=forged_hash,
        )
        forged_trace = tuple(
            replace(event, response_hash=forged_hash)
            if event.action == "INSPECT"
            else event
            for event in bundle.trace
        )
        forged_ledger = tuple(
            replace(entry, response_hash=forged_hash)
            if entry.action == "INSPECT"
            else entry
            for entry in bundle.ledger_entries
        )
        coordinated_forgery = TaskEvaluator(
            runtime.package.package_fingerprint,
            runtime.registry,
            trusted_anchor,
        ).evaluate(
            replace(
                bundle,
                inspection_records=(forged_record,),
                trace=forged_trace,
                ledger_entries=forged_ledger,
            ),
            forged_hash,
        )
        self.assertFalse(coordinated_forgery.qualified)
        self.assertFalse(coordinated_forgery.information_valid)
        self.assertFalse(coordinated_forgery.evidence_seal_valid)

    def test_unsat_certificate_binds_executable_transition(self) -> None:
        checker = BoundedModelChecker()
        original = checker.check(self.worlds["discover"], 0)
        self.assertTrue(original.sat)
        with patch("qhm1.checker.transition", _dead_transition):
            mutated = checker.check(self.worlds["discover"], 0)
        self.assertFalse(mutated.sat)
        self.assertIsNotNone(mutated.unsat_certificate)
        self.assertEqual(
            frozen_package(
                self.worlds["discover"]
            ).action_model_fingerprint,
            mutated.unsat_certificate.action_model_fingerprint,
        )
        self.assertNotEqual(
            original.executable_model_fingerprint,
            mutated.executable_model_fingerprint,
        )
        self.assertEqual(
            mutated.executable_model_fingerprint,
            mutated.unsat_certificate.executable_model_fingerprint,
        )

    def test_full_matrix_is_qualified_or_correct_bounded_unreachable(self) -> None:
        report = build_report()
        self.assertEqual(0, report["external_calls"])
        self.assertEqual(
            "PER_WORLD_EXISTENTIAL_SEQUENCE_IN_DECLARED_FINITE_MODEL",
            report["reachability_quantifiers"]["closure_oracle"],
        )
        self.assertEqual(
            "NOT_TESTED",
            report["reachability_quantifiers"][
                "robust_across_allowed_principal_response_families"
            ],
        )
        self.assertEqual(30, len(report["runs"]))
        self.assertEqual(
            {
                "BOUNDED_UNREACHABLE": 9,
                "QUALIFIED_SUCCESS": 18,
                "UNRESOLVED_MODEL": 3,
            },
            report["outcome_counts"],
        )
        self.assertEqual([], report["comparative_result"]["candidate_unique_successes"])
        self.assertTrue(
            report["comparative_result"][
                "synthetic_existing_compositions_close_all_bounded_worlds"
            ]
        )
        self.assertTrue(
            report["comparative_result"][
                "all_systems_match_bounded_oracle"
            ]
        )
        self.assertEqual(
            {
                "build-known",
                "commit",
                "combo",
                "discover",
                "enable",
                "extend",
            },
            set(report["comparative_result"]["oracle_sat_worlds"]),
        )
        self.assertEqual(
            {
                "Unknown",
                "adapter",
                "central",
                "combined",
                "human",
                "new",
                "none-needed",
            },
            set(report["mechanism_dispositions"]),
        )

    def test_empty_policy_mutation_cannot_vacuously_pass_comparison(self) -> None:
        with (
            patch.object(StrongCenterHitl, "plan", _always_stop_a),
            patch.object(MatureWorkflowComposition, "plan", _always_stop_b),
            patch.object(FormationCandidate, "plan", _always_stop_c),
        ):
            report = build_report()
        comparison = report["comparative_result"]
        self.assertFalse(
            comparison[
                "synthetic_existing_compositions_close_all_bounded_worlds"
            ]
        )
        self.assertFalse(comparison["all_systems_match_bounded_oracle"])
        self.assertFalse(
            comparison["strong_center_synthetic_success_is_positive"]
        )
        self.assertFalse(
            comparison["mature_workflow_synthetic_success_is_positive"]
        )
        self.assertFalse(
            report["theory_gates"]["KNOWLEDGE-PROVENANCE"]["passed"]
        )

    def test_unbound_inspection_response_cannot_pass(self) -> None:
        original_inspect = TrialGateway.inspect

        def forged_inspect(gateway):
            original_inspect(gateway)
            return PublicFacts(
                public_trial_id=gateway.public_trial_id,
                initial_message="UNBOUND FORGED RESPONSE",
                route="READY_COMPATIBLE",
                authorization="PRESENT",
                schema="COMPATIBLE",
                value_floor="PASS",
            )

        with patch.object(TrialGateway, "inspect", forged_inspect):
            report = build_report()
        self.assertFalse(
            report["comparative_result"][
                "synthetic_existing_compositions_close_all_bounded_worlds"
            ]
        )
        self.assertFalse(
            report["theory_gates"]["KNOWLEDGE-PROVENANCE"]["passed"]
        )
        self.assertTrue(
            all(
                not run["evaluation"]["information_valid"]
                for run in report["runs"]
                if run["requested_terminal"] == "REQUESTED_SUCCESS"
            )
        )

    def test_every_success_receives_all_required_causal_replays(self) -> None:
        report = build_report()
        success_runs = [
            run for run in report["runs"] if run["outcome"] == "QUALIFIED_SUCCESS"
        ]
        self.assertEqual(18, len(success_runs))
        required = {
            "knowledge_only",
            "fixed_model_prefix",
            "model_diff",
            "old_task",
            "authority_substitution",
            "effect_and_cost_tampering",
            "intervention_subset_ablation",
        }
        for run in success_runs:
            replay = run["replays"]
            self.assertEqual(required, set(replay))
            self.assertTrue(replay["old_task"]["qualified"])
            self.assertTrue(
                all(
                    not item["qualified"]
                    for item in replay["authority_substitution"]["cases"]
                )
            )
            self.assertFalse(
                replay["effect_and_cost_tampering"]["duplicate_effect"][
                    "qualified"
                ]
            )
            self.assertFalse(
                replay["effect_and_cost_tampering"]["missing_cost_entry"][
                    "qualified"
                ]
            )
            self.assertFalse(
                replay["effect_and_cost_tampering"]["task_drift"][
                    "qualified"
                ]
            )
            self.assertTrue(
                replay["intervention_subset_ablation"]["minimal_sufficient_sets"]
            )
            knowledge = replay["knowledge_only"]
            self.assertTrue(
                knowledge["provenance"]["trace_and_parent_ledger_bound"]
            )
            self.assertEqual(1, knowledge["acquisition_cost_charged"])
            self.assertEqual(1, knowledge["privacy_cost_charged"])
            self.assertTrue(knowledge["obligations_preserved"])
            self.assertFalse(knowledge["free_information_injection_used"])
            self.assertTrue(knowledge["forged_free_information_rejected"])
            self.assertFalse(
                knowledge["forged_free_information_result"]["sat"]
            )
            self.assertTrue(
                knowledge["unbound_runtime_information_rejected"]
            )
            self.assertFalse(
                knowledge["unbound_runtime_information_evaluation"][
                    "qualified"
                ]
            )
            self.assertIn(
                "INFORMATION_PROVENANCE_OR_OBLIGATION_INVALID",
                knowledge["unbound_runtime_information_evaluation"][
                    "reasons"
                ],
            )

    def test_replays_distinguish_discovery_preparation_and_extension(self) -> None:
        report = build_report()
        central = {
            run["truth_id"]: run
            for run in report["runs"]
            if run["system"] == "same_information_strong_center_hitl"
        }
        self.assertTrue(central["discover"]["replays"]["knowledge_only"]["sat"])
        for truth_id in ("enable", "commit", "build-known", "extend"):
            self.assertFalse(
                central[truth_id]["replays"]["knowledge_only"]["sat"],
                truth_id,
            )
        for truth_id in ("discover", "enable", "commit", "build-known"):
            self.assertTrue(
                central[truth_id]["replays"]["fixed_model_prefix"]["sat"],
                truth_id,
            )
        self.assertFalse(central["extend"]["replays"]["fixed_model_prefix"]["sat"])
        self.assertTrue(central["extend"]["replays"]["model_diff"]["sat"])
        self.assertEqual(
            ["PROPOSE_NEW_OPERATOR", "REGISTER_NEW_OPERATOR"],
            central["extend"]["replays"]["model_diff"]["exact_diff"],
        )

    def test_drift_substitution_and_unsat_are_not_surface_successes(self) -> None:
        report = build_report()
        for run in report["runs"]:
            if run["truth_id"] in {"drift", "substitute", "unsat"}:
                self.assertEqual("BOUNDED_UNREACHABLE", run["outcome"])
                self.assertFalse(run["old_task_qualified"])
                self.assertEqual("Unknown", run["mechanism_disposition"])
        oracle = {item["truth_id"]: item for item in report["oracle"]}
        for truth_id in ("drift", "substitute", "unsat"):
            self.assertTrue(all(not layer["sat"] for layer in oracle[truth_id]["layers"]))

    def test_theory_gates_keep_closure_token_and_representation_orthogonal(self) -> None:
        report = build_report()
        gates = report["theory_gates"]
        self.assertTrue(gates["TOKEN-COMMIT"]["passed"])
        self.assertTrue(
            gates["TOKEN-COMMIT"]["authority_bound_receipts_verified"]
        )
        self.assertEqual(
            [
                {
                    "C": "SAT",
                    "N": "NEW_TOKEN",
                    "E": "SAME",
                    "T": "INVARIANT",
                    "V": "VALID",
                }
            ]
            * 3,
            gates["TOKEN-COMMIT"]["observed"],
        )
        refactor = gates["META-REFACTOR"]
        self.assertTrue(refactor["passed"])
        self.assertEqual(
            2, refactor["encoding_a"]["declared_layer_depth"]
        )
        self.assertEqual(
            1, refactor["encoding_b"]["declared_layer_depth"]
        )
        self.assertEqual(
            refactor["material_vector_a"], refactor["material_vector_b"]
        )
        self.assertTrue(refactor["same_material_transition_result"])
        self.assertTrue(refactor["depth_changed"])
        self.assertTrue(gates["KNOWLEDGE-PROVENANCE"]["passed"])

    def test_incomplete_action_inventory_is_unknown_not_false_unsat(self) -> None:
        checker = BoundedModelChecker()
        closure = checker.check_all_layers(self.worlds["open-invent"])
        self.assertEqual("UNKNOWN", closure.closure_status)
        self.assertIsNone(closure.formation_depth)
        self.assertTrue(
            all(
                result.unsat_certificate is None
                and result.unresolved_reason is not None
                for result in closure.layers
            )
        )
        report = build_report()
        self.assertTrue(report["theory_gates"]["OPEN-INVENT"]["passed"])
        outcomes = {
            run["outcome"]
            for run in report["runs"]
            if run["truth_id"] == "open-invent"
        }
        self.assertEqual({"UNRESOLVED_MODEL"}, outcomes)

    def test_report_is_deterministic_and_stays_inside_new_directory(self) -> None:
        self.assertEqual(build_report(), build_report())
        root = Path(__file__).resolve().parents[1]
        self.assertEqual("wave-008-g3-qhm1", root.name)


if __name__ == "__main__":
    unittest.main()
