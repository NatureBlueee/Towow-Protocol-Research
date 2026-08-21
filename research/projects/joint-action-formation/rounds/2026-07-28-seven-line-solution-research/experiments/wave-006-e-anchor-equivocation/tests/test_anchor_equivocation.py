import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import evaluate  # noqa: E402
from simulator import (  # noqa: E402
    SHARED_TASK_ID,
    SHARED_TASK_SHA256,
    Witness,
    build_contract,
    checkpoints_conflict,
    conflicting_receipts,
    honest_receipt,
    obtain_quorum,
    simulate,
    verify_anchor_head,
    verify_witness_response,
)


class AnchorEquivocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_contract()
        cls.simulation = simulate()
        cls.evaluation = evaluate()

    def test_shared_task_binding_and_denominator(self):
        self.assertEqual(
            "W6-STERILE-ROUTE-SIMULATION-001", SHARED_TASK_ID
        )
        self.assertEqual(
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3",
            SHARED_TASK_SHA256,
        )
        self.assertEqual(
            SHARED_TASK_SHA256, self.contract["shared_task_sha256"]
        )
        self.assertEqual(
            "RUN-STERILE-ROUTE-SIM-v1", self.contract["operation"]
        )

    def test_same_key_conflicting_branches_are_both_locally_valid(self):
        left, right = conflicting_receipts(self.contract)
        self.assertTrue(verify_anchor_head(left, self.contract))
        self.assertTrue(verify_anchor_head(right, self.contract))
        self.assertTrue(
            checkpoints_conflict(left, right, self.contract)
        )

    def test_single_pinned_view_cannot_detect_cross_view_fact(self):
        result = self.simulation["strategies"]["SINGLE_PINNED_VIEW"]
        self.assertTrue(result["local_validation_a"])
        self.assertTrue(result["local_validation_b"])
        self.assertFalse(result["detected_during_partition"])
        self.assertFalse(result["detected_after_rejoin"])
        self.assertEqual(2, result["accepted_branch_count"])
        self.assertEqual(1, result["conflicting_acceptances"])
        impossibility = self.simulation["impossibility_counterexample"]
        self.assertFalse(
            impossibility[
                "single_client_transcript_contains_cross_view_bit"
            ]
        )

    def test_gossip_detects_on_rejoin_not_during_partition(self):
        result = self.simulation["strategies"]["CLIENT_GOSSIP"]
        self.assertFalse(result["detected_during_partition"])
        self.assertTrue(result["detected_after_rejoin"])
        self.assertEqual(
            "CONTESTED_CHECKPOINTS_QUARANTINED_REOPEN_REQUIRED",
            result["recovery_status"],
        )
        self.assertEqual(2, result["partition_rejoin_recovery_steps"])

    def test_honest_replay_is_not_false_fork(self):
        receipt = honest_receipt(self.contract)
        self.assertFalse(
            checkpoints_conflict(receipt, receipt, self.contract)
        )
        self.assertEqual(
            0,
            self.simulation["strategies"]["CLIENT_GOSSIP"][
                "false_rejection_honest"
            ],
        )

    def test_two_of_three_quorum_intersects_and_blocks_second_branch(self):
        result = self.simulation["strategies"][
            "INDEPENDENT_WITNESS_QUORUM"
        ]
        self.assertTrue(result["branch_a_quorum"])
        self.assertFalse(result["branch_b_quorum"])
        self.assertTrue(result["detected_during_partition"])
        self.assertEqual(1, result["accepted_branch_count"])
        self.assertEqual(0, result["conflicting_acceptances"])
        self.assertGreaterEqual(result["equivocation_proof_count"], 1)
        intersection = self.evaluation["formal_boundary"][
            "quorum_intersection"
        ]
        self.assertTrue(intersection["holds"])

    def test_equivocation_proof_is_independently_signed(self):
        left, right = conflicting_receipts(self.contract)
        witness = Witness("WITNESS-2", self.contract)
        first = witness.observe(left)
        conflict = witness.observe(right)
        self.assertEqual(
            "WITNESS_CHECKPOINT_ATTESTATION", first["kind"]
        )
        self.assertEqual(
            "WITNESS_EQUIVOCATION_PROOF", conflict["kind"]
        )
        body = verify_witness_response(conflict, self.contract)
        self.assertEqual("EQUIVOCATION_DETECTED", body["status"])

    def test_witness_partition_is_deferred_not_false_rejection(self):
        result = self.simulation["strategies"][
            "INDEPENDENT_WITNESS_QUORUM"
        ]
        self.assertEqual("UNKNOWN_DEFERRED", result["partition_terminal_state"])
        self.assertEqual(
            1, result["missed_valid_action_under_witness_partition"]
        )
        self.assertEqual(0, result["false_rejection_honest"])

    def test_honest_quorum_succeeds_with_two_reachable_witnesses(self):
        receipt = honest_receipt(self.contract)
        witnesses = [
            Witness("WITNESS-1", self.contract),
            Witness("WITNESS-2", self.contract),
        ]
        outcome = obtain_quorum(receipt, witnesses, self.contract)
        self.assertTrue(outcome["quorum_met"])
        self.assertEqual(2, len(outcome["attestations"]))
        self.assertEqual([], outcome["conflict_proofs"])

    def test_cost_order_is_not_hidden(self):
        metrics = self.evaluation["metrics"]
        self.assertLess(
            metrics["SINGLE_PINNED_VIEW"]["message_cost"],
            metrics["CLIENT_GOSSIP"]["message_cost"],
        )
        self.assertLess(
            metrics["CLIENT_GOSSIP"]["message_cost"],
            metrics["INDEPENDENT_WITNESS_QUORUM"]["message_cost"],
        )
        self.assertGreater(
            metrics["INDEPENDENT_WITNESS_QUORUM"][
                "missed_valid_action"
            ],
            0,
        )

    def test_strategy_choice_depends_on_required_timing(self):
        objectives = self.evaluation["objectives"]
        self.assertEqual(
            "SINGLE_PINNED_VIEW",
            objectives["LOCAL_INTEGRITY_ONLY_NO_EQUIVOCATION_THREAT"][
                "recommended"
            ],
        )
        self.assertEqual(
            "CLIENT_GOSSIP",
            objectives["DETECT_IF_CLIENTS_EVENTUALLY_REJOIN"][
                "recommended"
            ],
        )
        self.assertEqual(
            "INDEPENDENT_WITNESS_QUORUM",
            objectives[
                "PREVENT_TWO_ACCEPTED_HEADS_DURING_CLIENT_PARTITION"
            ]["recommended"],
        )

    def test_existing_components_are_positive_solution(self):
        solution = self.evaluation["solution_result"]
        self.assertFalse(solution["new_protocol_required"])
        self.assertTrue(
            solution["selection_depends_on_threat_objective"]
        )

    def test_all_conclusions_remain_local_synthetic(self):
        self.assertEqual(
            "LOCAL_SYNTHETIC_ONLY",
            self.evaluation["evidence_boundary"],
        )


if __name__ == "__main__":
    unittest.main()
