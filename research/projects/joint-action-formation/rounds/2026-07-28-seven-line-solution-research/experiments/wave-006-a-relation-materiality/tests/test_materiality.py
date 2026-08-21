import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUND_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

import evaluator  # noqa: E402
import simulator  # noqa: E402


class RelationMaterialityTests(unittest.TestCase):
    def setUp(self):
        self.world, self.registry, self.costs = simulator.frozen_inputs()
        self.strategies = {
            item["strategy_id"]: item
            for item in self.registry["strategies"]
        }

    def test_shared_task_binding_matches_frozen_bytes(self):
        shared_path = ROUND_ROOT / "WAVE-006-SHARED-TASK.md"
        actual = hashlib.sha256(shared_path.read_bytes()).hexdigest()
        self.assertEqual(self.world["shared_task_sha256"], actual)
        self.assertEqual(
            "W6-STERILE-ROUTE-SIMULATION-001",
            self.world["shared_task_id"],
        )

    def test_all_safe_strategies_face_the_same_event_sequence(self):
        traces = [
            simulator.safe_trace(strategy, self.world)
            for strategy in self.registry["strategies"]
        ]
        for trace in traces:
            self.assertEqual(
                [f"E{index}" for index in range(9)],
                [item["event"] for item in trace],
            )
        base = copy.deepcopy(traces[0])
        for trace in traces[1:]:
            normalized = copy.deepcopy(trace)
            normalized[5]["relation_proposal_status"] = "NOT_PRESENT"
            self.assertEqual(base, normalized)

    def test_a_b_c_all_preserve_one_operation_only_boundary(self):
        for strategy in self.registry["strategies"]:
            candidate = simulator.candidate_for(strategy, self.world)
            result = evaluator.evaluate_candidate(
                self.world, strategy, self.costs, candidate
            )
            self.assertTrue(result["passed"], result)
            self.assertEqual(
                0, result["metrics"]["false_relation_constitution"]
            )
            self.assertEqual(1, result["metrics"]["reuse_success"])
            self.assertEqual(0, result["metrics"]["stale_reuse"])
            self.assertEqual(0, result["metrics"]["withdrawal_residual"])

    def test_relation_version_has_no_material_increment_over_dual_ack(self):
        result = simulator.run_experiment()
        selection = result["selection"]
        self.assertFalse(
            selection["relation_version_material_increment_over_dual_ack"]
        )
        self.assertLess(
            selection["relation_version_net_value_delta_over_dual_ack"], 0
        )
        self.assertEqual(
            "USE_SIMPLER_EXISTING_EVIDENCE; DO_NOT_CONSTITUTE_A_RELATION",
            selection["decision"],
        )

    def test_simple_delivery_representation_can_win_without_false_success(self):
        result = simulator.run_experiment()
        self.assertEqual(
            "A_DELIVERY_RECEIPT_ONLY",
            result["selection"]["winner_at_relation_representation_scope"],
        )
        evaluations = {
            item["strategy_id"]: item for item in result["evaluations"]
        }
        self.assertGreater(
            evaluations["A_DELIVERY_RECEIPT_ONLY"]["metrics"][
                "net_task_value"
            ],
            evaluations["B_DUAL_RECIPIENT_ACK"]["metrics"][
                "net_task_value"
            ],
        )

    def test_one_shot_as_relation_attack_is_reconstructed_and_rejected(self):
        strategy = self.strategies["A_DELIVERY_RECEIPT_ONLY"]
        attack = simulator.strongest_false_relation_attack(
            strategy, self.world
        )
        result = evaluator.evaluate_candidate(
            self.world,
            {**strategy, "strategy_id": attack["strategy_id"]},
            self.costs,
            attack,
        )
        self.assertFalse(result["passed"])
        self.assertGreater(
            result["metrics"]["false_relation_constitution"], 0
        )
        self.assertEqual(1, result["metrics"]["stale_reuse"])
        self.assertEqual(1, result["metrics"]["withdrawal_residual"])
        self.assertTrue(result["claim_mismatches"])

    def test_unknown_refuse_absent_remain_distinct(self):
        strategy = self.strategies["B_DUAL_RECIPIENT_ACK"]
        candidate = simulator.candidate_for(strategy, self.world)
        result = evaluator.evaluate_candidate(
            self.world, strategy, self.costs, candidate
        )
        self.assertEqual(
            {"UNKNOWN": 2, "REFUSE": 4, "ABSENT": 2},
            result["metrics"]["status_classes"],
        )

    def test_changed_shared_task_binding_is_rejected(self):
        strategy = self.strategies["A_DELIVERY_RECEIPT_ONLY"]
        candidate = simulator.candidate_for(strategy, self.world)
        candidate["shared_task_sha256"] = "0" * 64
        result = evaluator.evaluate_candidate(
            self.world, strategy, self.costs, candidate
        )
        self.assertFalse(result["passed"])
        self.assertEqual(
            ["shared_task_sha256"], result["coordinate_mismatches"]
        )

    def test_beneficiary_refusal_does_not_constitute_relation(self):
        strategy = self.strategies["C_ACK_EXPLAINBACK_RELATION_PROPOSAL"]
        candidate = simulator.candidate_for(strategy, self.world)
        e7 = next(item for item in candidate["trace"] if item["event"] == "E7")
        self.assertEqual("REFUSE", e7["decisions"]["BENEFICIARY_REFUSAL"])
        result = evaluator.evaluate_candidate(
            self.world, strategy, self.costs, candidate
        )
        self.assertTrue(result["passed"])
        self.assertEqual(
            0, result["metrics"]["false_relation_constitution"]
        )

    def test_saved_summary_matches_reconstructed_result(self):
        result = simulator.run_experiment()
        saved = json.loads(
            (ROOT / "outputs" / "result-summary.json").read_text(
                encoding="utf-8"
            )
        )
        evaluations = {
            item["strategy_id"]: item["metrics"]
            for item in result["evaluations"]
        }
        for row in saved["safe_strategy_results"]:
            metrics = evaluations[row["strategy_id"]]
            for field, value in row.items():
                if field != "strategy_id":
                    self.assertEqual(value, metrics[field])
        attack_metrics = result["strongest_counterexample"]["evaluation"][
            "metrics"
        ]
        for field, value in saved["strongest_counterexample"].items():
            if field not in {"name", "passed"}:
                self.assertEqual(value, attack_metrics[field])
        for field, value in saved["selection"].items():
            self.assertEqual(value, result["selection"][field])


if __name__ == "__main__":
    unittest.main()
