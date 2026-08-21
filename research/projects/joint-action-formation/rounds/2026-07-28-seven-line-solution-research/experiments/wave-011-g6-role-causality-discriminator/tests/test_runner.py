from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT_DIR))

import evaluator  # noqa: E402
import gate_runner  # noqa: E402
import runner  # noqa: E402


class RunnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = runner.run_matrix()

    def test_matrix_dimensions_and_oracle_immutability(self) -> None:
        self.assertEqual(12, self.matrix["pair_count"])
        self.assertEqual(24, self.matrix["world_count"])
        self.assertEqual(108, self.matrix["record_count"])
        self.assertEqual(
            self.matrix["oracle_hash_before"], self.matrix["oracle_hash_after"]
        )

    def test_worker_packets_use_opaque_tokens(self) -> None:
        for record in self.matrix["records"]:
            for token in record["public_world_token"]:
                self.assertTrue(token.startswith("world-"))
                self.assertNotIn(record["pair"], token)
                self.assertNotRegex(token, r"P\d+[-_][AB]")

    def test_three_workers_have_independent_source_identity(self) -> None:
        manifest = self.matrix["worker_executable_source_hashes"]
        self.assertEqual(3, len(manifest))
        self.assertEqual(3, len({row["source_sha256"] for row in manifest.values()}))
        self.assertEqual(
            3, len({row["executable_identity"] for row in manifest.values()})
        )

    def test_main_matrix_passes_all_five_invalidation_gates(self) -> None:
        gates = gate_runner.evaluate_main_run(self.matrix)
        self.assertTrue(gates.overall_valid)
        self.assertTrue(gates.coverage_allowed)
        for gate in gates.gate_results.values():
            self.assertTrue(gate.passed)

    def test_truth_owner_sources_are_not_private_oracle_paths(self) -> None:
        for row in self.matrix["owner_source_identities"].values():
            self.assertTrue(row["path"].startswith("fixtures/"))
            self.assertNotIn("private_oracle", row["path"])

    def test_private_evaluator_accepts_all_finite_fixture_records(self) -> None:
        result = evaluator.evaluate_matrix(self.matrix)
        self.assertTrue(result["all_records_passed"])
        self.assertEqual(108, result["passed_record_count"])
        self.assertEqual(
            set(f"P{index}" for index in range(1, 13)),
            set(result["pair_discrimination"]),
        )

    def test_wrong_target_mutation_invalidates_round(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        for record in mutated["records"]:
            if record["pair"] == "P3":
                for output in record["method_output"].values():
                    output["recovery_relevance"]["effect_ids"] = []
                    output["recovery_relevance"]["required"] = False
        gates = gate_runner.evaluate_main_run(mutated)
        self.assertFalse(gates.overall_valid)
        self.assertFalse(gates.gate_results["wrong_object"].passed)

    def test_read_skew_mutation_invalidates_round(self) -> None:
        mutated = copy.deepcopy(self.matrix)
        for record in mutated["records"]:
            if record["pair"] == "P11":
                for output in record["method_output"].values():
                    if output["consistent_cut"] is False:
                        output["consistent_cut"] = True
                        output["counts_toward_q"]["effect_ids"] = ["forged-effect"]
                        output["control_action"] = "OBSERVE"
        gates = gate_runner.evaluate_main_run(mutated)
        self.assertFalse(gates.overall_valid)
        self.assertFalse(gates.gate_results["read_skew"].passed)


if __name__ == "__main__":
    unittest.main()
