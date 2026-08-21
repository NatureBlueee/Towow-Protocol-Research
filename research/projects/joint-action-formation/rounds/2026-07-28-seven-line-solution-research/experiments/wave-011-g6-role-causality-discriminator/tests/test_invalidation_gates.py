from __future__ import annotations

import sys
import unittest
import copy
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))

import gate_runner  # noqa: E402
import runner  # noqa: E402


class InvalidationGateTests(unittest.TestCase):
    def test_reference_doubles_pass_all_five_gates(self) -> None:
        result = gate_runner.run_invalidation_gates()
        self.assertTrue(result.overall_valid)
        self.assertEqual("GATES_PASS", result.round_status)
        self.assertTrue(result.coverage_allowed)
        self.assertEqual(set(gate_runner.GATE_NAMES), set(result.gate_results))
        for gate in result.gate_results.values():
            self.assertTrue(gate.attack_present)
            self.assertTrue(gate.attack_detected)
            self.assertTrue(gate.benign_control_accepted)
            self.assertTrue(gate.passed)

    def test_each_missing_detector_invalidates_whole_round(self) -> None:
        for name in gate_runner.GATE_NAMES:
            with self.subTest(gate=name):
                result = gate_runner.run_invalidation_gates([name])
                self.assertFalse(result.overall_valid)
                self.assertEqual("INVALID", result.round_status)
                self.assertFalse(result.coverage_allowed)
                self.assertFalse(result.gate_results[name].passed)

    def test_truth_copy_checks_actual_source_access(self) -> None:
        result = gate_runner.gate_truth_copy()
        self.assertGreater(
            result.evidence["malicious_trace"]["grader_private_oracle_reads"], 0
        )
        self.assertEqual(
            0, result.evidence["control_trace"]["grader_private_oracle_reads"]
        )

    def test_method_alias_checks_executable_and_decision_root(self) -> None:
        result = gate_runner.gate_method_alias()
        fields = {
            row["identity_field"] for row in result.evidence["attack_collisions"]
        }
        self.assertEqual(
            {"executable_sha256", "decision_root_sha256"},
            fields,
        )
        self.assertEqual([], result.evidence["control_collisions"])

    def test_wrong_object_requires_real_damage_and_recovery(self) -> None:
        result = gate_runner.gate_wrong_object()
        self.assertIn("raw_occurred", result.evidence["attack_mismatches"])
        self.assertIn("actual_target", result.evidence["attack_mismatches"])
        self.assertIn("recovery_relevant", result.evidence["attack_mismatches"])
        self.assertIn("affected_targets", result.evidence["attack_mismatches"])

    def test_read_skew_requires_a_real_common_cut(self) -> None:
        result = gate_runner.gate_read_skew()
        self.assertIsNone(result.evidence["attack_common_valid_index"])
        self.assertEqual(12, result.evidence["control_common_valid_index"])

    def test_unauthorized_effect_preserves_four_independent_dimensions(self) -> None:
        result = gate_runner.gate_unauthorized_real_effect()
        required = result.evidence["required_joint_result"]
        self.assertTrue(required["raw_occurred"])
        self.assertEqual("UNAUTHORIZED", required["authority"])
        self.assertFalse(required["counts_toward_q"])
        self.assertTrue(required["recovery_relevant"])

    def test_main_run_adapter_passes_structural_gate_artifact(self) -> None:
        methods = [
            {
                "method_id": name,
                "executable_sha256": gate_runner._digest(f"exec:{name}"),
                "decision_root_sha256": gate_runner._digest(f"root:{name}"),
                "implementation_owner": name,
            }
            for name in ("center", "composition", "human")
        ]
        payload = {
            "attack_manifest": {"truth_copy": True, "method_alias": True},
            "attack_detections": {"truth_copy": True, "method_alias": True},
            "provenance": {
                "owner_api_sources": [
                    {
                        "source_kind": "owner_native_store",
                        "accessed_private_oracle": False,
                    },
                    {
                        "source_kind": "owner_sensor",
                        "accessed_private_oracle": False,
                    },
                ]
            },
            "methods": methods,
            "occurrence_assessments": [
                {
                    "raw_occurred": True,
                    "episode_target": "CNC-17",
                    "actual_target": "CNC-71",
                    "authority": "AUTHORIZED_FOR_CNC_17_ONLY",
                    "counts_toward_q": False,
                    "recovery_relevant": True,
                    "affected_targets": ["CNC-71"],
                },
                {
                    "raw_occurred": True,
                    "episode_target": "CNC-17",
                    "actual_target": "CNC-17",
                    "authority": "UNAUTHORIZED",
                    "counts_toward_q": False,
                    "recovery_relevant": True,
                    "affected_targets": ["CNC-17"],
                },
            ],
            "done_evaluations": [
                {
                    "derived_done": False,
                    "heads": [
                        {
                            "owner_id": "buyer",
                            "claim_type": "Acceptance",
                            "state": "ACCEPT",
                            "valid_from": 8,
                            "valid_through": 10,
                            "cut_id": "cut-10",
                        },
                        {
                            "owner_id": "rail",
                            "claim_type": "Settlement",
                            "state": "PAID_OUT",
                            "valid_from": 12,
                            "valid_through": None,
                            "cut_id": "cut-12",
                        },
                    ],
                }
            ],
        }
        result = gate_runner.evaluate_main_run(payload)
        self.assertTrue(result.overall_valid)

    def test_main_run_adapter_fails_closed_when_attack_evidence_missing(self) -> None:
        result = gate_runner.evaluate_main_run({})
        self.assertFalse(result.overall_valid)
        self.assertEqual("INVALID", result.round_status)
        for gate in result.gate_results.values():
            self.assertFalse(gate.passed)

    def test_concrete_matrix_and_five_mutations(self) -> None:
        matrix = runner.run_matrix()
        baseline = gate_runner.evaluate_matrix_run(matrix)
        self.assertTrue(baseline.overall_valid)

        truth_copy = copy.deepcopy(matrix)
        first_source = next(iter(truth_copy["owner_source_identities"].values()))
        first_source["path"] = "private_oracle/expected.json"
        result = gate_runner.evaluate_matrix_run(truth_copy)
        self.assertFalse(result.gate_results["truth_copy"].passed)
        self.assertFalse(result.overall_valid)

        alias = copy.deepcopy(matrix)
        method_rows = list(alias["worker_executable_source_hashes"].values())
        method_rows[1]["source_sha256"] = method_rows[0]["source_sha256"]
        method_rows[1]["executable_identity"] = method_rows[0]["executable_identity"]
        result = gate_runner.evaluate_matrix_run(alias)
        self.assertFalse(result.gate_results["method_alias"].passed)
        self.assertFalse(result.overall_valid)

        wrong_object = copy.deepcopy(matrix)
        wrong_mutated = 0
        for _, _, observations, output in gate_runner._matrix_cells(wrong_object):
            target = observations["target"]["payload"]
            exact = target.get("exact_object")
            wrong_ids = {
                str(row.get("occurrence"))
                for row in target.get("transitions", ())
                if row.get("object") != exact
            }
            if wrong_ids:
                output["recovery_relevance"]["effect_ids"] = [
                    value
                    for value in output["recovery_relevance"].get("effect_ids", ())
                    if value not in wrong_ids
                ]
                wrong_mutated += len(wrong_ids)
        self.assertGreater(wrong_mutated, 0)
        result = gate_runner.evaluate_matrix_run(wrong_object)
        self.assertFalse(result.gate_results["wrong_object"].passed)
        self.assertFalse(result.overall_valid)

        read_skew = copy.deepcopy(matrix)
        skew_mutated = 0
        for _, _, observations, output in gate_runner._matrix_cells(read_skew):
            if gate_runner._cut_is_consistent(
                observations["cut"]["payload"]
            ) is False:
                output["control_action"] = "OBSERVE"
                skew_mutated += 1
        self.assertGreater(skew_mutated, 0)
        result = gate_runner.evaluate_matrix_run(read_skew)
        self.assertFalse(result.gate_results["read_skew"].passed)
        self.assertFalse(result.overall_valid)

        unauthorized = copy.deepcopy(matrix)
        unauthorized_mutated = 0
        for _, _, observations, output in gate_runner._matrix_cells(unauthorized):
            execution = observations["execution"]["payload"]
            authorized = gate_runner._authorized_attempt_ids(observations)
            attempts = {
                str(row.get("id"))
                for row in execution.get("attempts", ())
                if row.get("crossed_boundary")
            }
            target = observations["target"]["payload"]
            unauthorized_ids = {
                str(row.get("occurrence"))
                for row in target.get("transitions", ())
                if str(row.get("operation_id")) in attempts
                and str(row.get("operation_id")) not in authorized
            }
            if unauthorized_ids:
                output["raw_occurrences"] = [
                    row
                    for row in output.get("raw_occurrences", ())
                    if str(row.get("occurrence_id")) not in unauthorized_ids
                ]
                unauthorized_mutated += len(unauthorized_ids)
        self.assertGreater(unauthorized_mutated, 0)
        result = gate_runner.evaluate_matrix_run(unauthorized)
        self.assertFalse(result.gate_results["unauthorized_real_effect"].passed)
        self.assertFalse(result.overall_valid)


if __name__ == "__main__":
    unittest.main()
