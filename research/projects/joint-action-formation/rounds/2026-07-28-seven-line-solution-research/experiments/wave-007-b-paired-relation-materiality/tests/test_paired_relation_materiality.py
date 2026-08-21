from __future__ import annotations

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
from authority import HiddenAuthorityService, PrivateWorldState  # noqa: E402
from protocol import canonical_bytes  # noqa: E402


class PairedRelationMaterialityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.simulation = simulator.simulate()
        cls.result = evaluator.evaluate()
        cls.baseline = {
            (
                item["evaluation"]["evaluator_world_id"],
                item["evaluation"]["candidate_label"],
            ): item
            for item in cls.result["baseline"]
        }

    def test_shared_task_and_current_protocol_bindings(self) -> None:
        expected = {
            "WAVE-006-SHARED-TASK.md": (
                "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
            ),
            "WAVE-007-REPAIR-HARNESS.md": (
                "7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653"
            ),
            "WAVE-007-INDEPENDENT-AUDIT-PROTOCOL.md": (
                "5eec08681a819d6c1ade908c127baa986da8db689b2f6df8765cf0d83ad7e98f"
            ),
        }
        for name, digest in expected.items():
            self.assertEqual(
                digest,
                hashlib.sha256((ROUND_ROOT / name).read_bytes()).hexdigest(),
            )
        self.assertEqual(
            expected["WAVE-006-SHARED-TASK.md"],
            self.result["shared_task_sha256"],
        )

    def test_candidate_surface_has_no_truth_or_signer_import(self) -> None:
        candidate_source = (ROOT / "candidate.py").read_text(
            encoding="utf-8"
        )
        public_source = (ROOT / "public_api.py").read_text(
            encoding="utf-8"
        )
        forbidden = [
            "evaluator_world_id",
            "reuse_truth",
            "_private_key",
            "sign_envelope",
            "HiddenAuthorityService",
            "import evaluator",
            "import simulator",
            "from authority",
        ]
        for token in forbidden:
            self.assertNotIn(token, candidate_source)
        for token in [
            "private_key",
            "sign_envelope",
            "reuse_truth",
            "relation_evidence",
        ]:
            self.assertNotIn(token, public_source)

    def test_gateway_exposes_no_service_log_or_signer(self) -> None:
        world = simulator.load_json("paired-worlds.json")["worlds"][0]
        representation = simulator.load_json("representations.json")[
            "representations"
        ][0]
        run = simulator.run_one(world, representation)
        self.assertNotIn("gateway", run)
        self.assertNotIn("private_state", json.dumps(run))
        self.assertNotIn("_private_key", json.dumps(run))

    def test_representations_change_visible_bytes_and_actual_operations(self) -> None:
        runs = {
            item["candidate_output"]["candidate_label"]: item
            for item in self.simulation["baseline_runs"]
            if item["evaluator_truth"]["evaluator_world_id"]
            == "PW-BOUNDED-VALID"
        }
        serialized = {
            name: canonical_bytes(
                {
                    key: run["evidence_returns"][key]
                    for key in sorted(run["evidence_returns"])
                    if not key.startswith("reuse_response_")
                }
            )
            for name, run in runs.items()
        }
        self.assertEqual(4, len(set(serialized.values())))
        operation_counts = {
            name: len(run["operation_log"]) for name, run in runs.items()
        }
        self.assertGreater(
            operation_counts["BOUNDED_RELATION"],
            operation_counts["EXPLAIN_BACK"],
        )
        self.assertGreater(
            operation_counts["EXPLAIN_BACK"],
            operation_counts["TASK_BOUND"],
        )
        self.assertGreater(
            operation_counts["TASK_BOUND"],
            operation_counts["NO_EVIDENCE"],
        )

    def test_task_bound_is_safe_in_both_one_shot_worlds(self) -> None:
        for world in ["PW-ONE-VALID", "PW-ONE-CONTRADICTORY"]:
            row = self.baseline[(world, "TASK_BOUND")]["evaluation"]
            self.assertEqual(0, row["false_constitution"])
            self.assertEqual(0, row["stale_reuse"])
            self.assertEqual(0, row["withdrawal_residual"])
            self.assertFalse(row["relation_constituted"])
            self.assertFalse(row["reuse_executed"])

    def test_bounded_authorization_materially_enables_reuse(self) -> None:
        bounded = {
            representation: self.baseline[
                ("PW-BOUNDED-VALID", representation)
            ]["evaluation"]
            for representation in [
                "TASK_BOUND",
                "EXPLAIN_BACK",
                "BOUNDED_RELATION",
                "NO_EVIDENCE",
            ]
        }
        self.assertTrue(bounded["BOUNDED_RELATION"]["reuse_executed"])
        self.assertTrue(bounded["BOUNDED_RELATION"]["relation_constituted"])
        for name in ["TASK_BOUND", "EXPLAIN_BACK", "NO_EVIDENCE"]:
            self.assertFalse(bounded[name]["reuse_executed"])
            self.assertEqual(1, bounded[name]["missed_legitimate_reuse"])

    def test_explain_back_alone_is_not_authority(self) -> None:
        row = self.baseline[
            ("PW-BOUNDED-VALID", "EXPLAIN_BACK")
        ]["evaluation"]
        self.assertFalse(row["relation_evidence_valid"])
        self.assertFalse(row["relation_constituted"])
        self.assertFalse(row["reuse_executed"])
        self.assertEqual(
            "REFUTED",
            self.result["scoped_claims"][
                "explain_back_alone_is_reuse_authority"
            ]["status"],
        )

    def test_no_evidence_is_not_promoted_by_low_cost(self) -> None:
        no_evidence = self.baseline[
            ("PW-BOUNDED-VALID", "NO_EVIDENCE")
        ]["evaluation"]
        task_bound = self.baseline[
            ("PW-BOUNDED-VALID", "TASK_BOUND")
        ]["evaluation"]
        self.assertLess(
            no_evidence["cost"]["evidence_cost"],
            task_bound["cost"]["evidence_cost"],
        )
        self.assertEqual(1, no_evidence["missed_legitimate_reuse"])
        self.assertLess(no_evidence["net_value"], 0)
        self.assertEqual(
            "REFUTED",
            self.result["scoped_claims"][
                "no_evidence_zero_cost_is_adequate"
            ]["status"],
        )

    def test_contradictory_evidence_does_not_constitute_relation(self) -> None:
        for world in [
            "PW-ONE-CONTRADICTORY",
            "PW-BOUNDED-CONTRADICTORY",
        ]:
            row = self.baseline[(world, "BOUNDED_RELATION")][
                "evaluation"
            ]
            self.assertFalse(row["relation_evidence_valid"])
            self.assertFalse(row["relation_constituted"])
            self.assertFalse(row["reuse_executed"])
            self.assertEqual(0, row["false_constitution"])
            self.assertEqual(0, row["stale_reuse"])
            if world == "PW-BOUNDED-CONTRADICTORY":
                self.assertEqual(1, row["missed_legitimate_reuse"])

    def test_unknown_refuse_absent_remain_distinct(self) -> None:
        one_valid = self.baseline[
            ("PW-ONE-VALID", "BOUNDED_RELATION")
        ]["evaluation"]["terminal_observations"]
        one_conflict = self.baseline[
            ("PW-ONE-CONTRADICTORY", "BOUNDED_RELATION")
        ]["evaluation"]["terminal_observations"]
        self.assertGreater(one_valid["REFUSE"], 0)
        self.assertGreater(one_valid["ABSENT"], 0)
        self.assertEqual(0, one_valid["UNKNOWN"])
        self.assertGreater(one_conflict["UNKNOWN"], 0)
        self.assertGreater(one_conflict["REFUSE"], 0)

    def test_each_decisive_evidence_deletion_changes_action(self) -> None:
        deletion = self.result["mutation_results"]["evidence_deletion"]
        self.assertEqual(
            {
                "delivery",
                "ack_seek",
                "ack_offer",
                "explain_seek",
                "explain_offer",
                "proposal",
                "auth_seek",
                "auth_offer",
            },
            set(deletion),
        )
        for row in deletion.values():
            self.assertFalse(row["relation_constituted"])
            self.assertFalse(row["reuse_executed"])
            self.assertEqual(1, row["missed_legitimate_reuse"])

    def test_opaque_rename_and_label_swap_are_invariant(self) -> None:
        attacks = self.result["mutation_results"]
        self.assertTrue(attacks["opaque_rename_behavior_unchanged"])
        self.assertTrue(attacks["opaque_rename_score_unchanged"])
        self.assertTrue(attacks["label_function_swap_score_unchanged"])

    def test_truth_flip_changes_only_evaluator_confusion(self) -> None:
        attacks = self.result["mutation_results"]
        self.assertTrue(
            attacks["truth_label_flip_candidate_behavior_unchanged"]
        )
        self.assertTrue(attacks["truth_label_flip_confusion_changed"])

    def test_self_report_is_ignored(self) -> None:
        attack = self.simulation["mutations"]["self_report_injection"]
        self.assertEqual(
            9999, attack["candidate_output"]["self_report"]["net_value"]
        )
        self.assertTrue(
            self.result["mutation_results"][
                "self_report_score_unchanged"
            ]
        )

    def test_duplicate_and_unauthorized_authorization_are_rejected(self) -> None:
        attacks = self.result["mutation_results"]
        self.assertTrue(attacks["duplicate_authorization_rejected"])
        self.assertTrue(attacks["unauthorized_authorization_rejected"])

    def test_authority_independently_rejects_bad_authorization_set(self) -> None:
        baseline = self.baseline[
            ("PW-BOUNDED-VALID", "BOUNDED_RELATION")
        ]["run"]
        valid_authorizations = [
            baseline["evidence_returns"][name]["evidence"]
            for name in ["auth_seek", "auth_offer"]
        ]

        def fresh_gateway():
            service = HiddenAuthorityService(
                PrivateWorldState(
                    reuse_truth="EXPLICIT_BOUNDED_REUSE_AUTHORIZED",
                    relation_evidence="VALID_BOUNDED_REUSE",
                    withdraw_after_first_reuse=True,
                ),
                opaque_seed="direct-authority-check",
            )
            return service.create_gateway()[0]

        accepted = fresh_gateway().request_reuse(valid_authorizations)
        self.assertEqual("PRESENT", accepted["observation"])

        duplicate = fresh_gateway().request_reuse(
            [valid_authorizations[0], valid_authorizations[0]]
        )
        self.assertEqual("REFUSE", duplicate["observation"])

        cross_purpose = self.simulation["mutations"][
            "cross_purpose_authorization"
        ]["evidence_returns"]["auth_offer"]["evidence"]
        rejected = fresh_gateway().request_reuse(
            [valid_authorizations[0], cross_purpose]
        )
        self.assertEqual("REFUSE", rejected["observation"])

    def test_changed_signed_bytes_are_rejected(self) -> None:
        self.assertTrue(
            self.result["mutation_results"][
                "changed_signed_bytes_rejected"
            ]
        )
        attack = self.simulation["mutations"]["bytes_binding_change"]
        self.assertFalse(
            evaluator.reconstruct_relation_evidence(attack)["valid"]
        )

    def test_wrong_kind_and_cross_purpose_signatures_are_rejected(self) -> None:
        attacks = self.result["mutation_results"]
        self.assertTrue(attacks["wrong_kind_evidence_rejected"])
        self.assertTrue(
            attacks["cross_purpose_authorization_rejected"]
        )
        for name in ["wrong_kind_ack", "cross_purpose_authorization"]:
            run = self.simulation["mutations"][name]
            self.assertFalse(
                evaluator.reconstruct_relation_evidence(run)["valid"]
            )

    def test_unauthorized_withdrawal_does_not_clear_relation(self) -> None:
        run = self.simulation["mutations"]["unauthorized_withdrawal"]
        row = evaluator.evaluate_run(run)
        self.assertEqual(1, row["withdrawal_residual"])
        self.assertNotEqual(
            "WITHDRAWN",
            run["candidate_output"]["withdrawal_status"],
        )
        self.assertTrue(
            self.result["mutation_results"][
                "unauthorized_withdrawal_not_accepted"
            ]
        )

    def test_cost_is_recomputed_from_raw_operation_log(self) -> None:
        run = copy.deepcopy(
            self.baseline[("PW-BOUNDED-VALID", "BOUNDED_RELATION")][
                "run"
            ]
        )
        baseline = evaluator.recompute_cost(run)
        run["candidate_output"]["cost"] = -9999
        self.assertEqual(baseline, evaluator.recompute_cost(run))
        run["operation_log"].reverse()
        self.assertEqual(baseline, evaluator.recompute_cost(run))
        run["operation_log"].append(
            {
                "op": "READ_EVIDENCE",
                "name": "extra-read",
                "observation": "UNKNOWN",
                "bytes": 1024,
                "disclosure_units": 1,
            }
        )
        changed = evaluator.recompute_cost(run)
        self.assertEqual(
            baseline["operation_count"] + 1,
            changed["operation_count"],
        )
        self.assertGreater(
            changed["evidence_cost"], baseline["evidence_cost"]
        )

    def test_malicious_active_without_evidence_is_false_constitution(self) -> None:
        run = copy.deepcopy(
            self.baseline[("PW-BOUNDED-VALID", "NO_EVIDENCE")]["run"]
        )
        run["operation_log"].append(
            {
                "op": "CANDIDATE_RELATION_DECISION",
                "state": "ACTIVE_BOUNDED",
                "evidence_refs": [],
                "bytes": 2,
                "disclosure_units": 0,
            }
        )
        row = evaluator.evaluate_run(run)
        self.assertEqual(1, row["false_constitution"])
        self.assertFalse(row["relation_constituted"])

    def test_post_withdrawal_active_state_is_residual(self) -> None:
        run = copy.deepcopy(
            self.baseline[("PW-BOUNDED-VALID", "BOUNDED_RELATION")][
                "run"
            ]
        )
        active = next(
            item
            for item in run["operation_log"]
            if item["op"] == "CANDIDATE_RELATION_DECISION"
            and item["state"] == "ACTIVE_BOUNDED"
        )
        run["operation_log"].append(copy.deepcopy(active))
        row = evaluator.evaluate_run(run)
        self.assertEqual(1, row["withdrawal_residual"])

    def test_post_withdrawal_reuse_request_is_stale_and_residual(self) -> None:
        row = evaluator.evaluate_run(
            self.simulation["mutations"]["post_withdrawal_reuse"]
        )
        self.assertEqual(1, row["stale_reuse"])
        self.assertEqual(1, row["withdrawal_residual"])
        self.assertTrue(
            self.result["mutation_results"][
                "post_withdrawal_reuse_counted"
            ]
        )

    def test_scoped_claims_have_no_overall_grade(self) -> None:
        self.assertIsNone(self.result["overall_grade"])
        self.assertEqual(
            "LOCAL_SYNTHETIC_SELF_TEST_NOT_INDEPENDENT_AUDIT",
            self.result["evidence_boundary"],
        )
        statuses = {
            item["status"]
            for item in self.result["scoped_claims"].values()
        }
        self.assertTrue(statuses.issubset({
            "SUPPORTED_SCOPED",
            "REFUTED",
            "UNKNOWN",
        }))


if __name__ == "__main__":
    unittest.main()
