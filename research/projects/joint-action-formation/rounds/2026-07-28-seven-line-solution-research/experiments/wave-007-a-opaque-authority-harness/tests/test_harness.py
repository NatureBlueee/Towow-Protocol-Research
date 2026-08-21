#!/usr/bin/env python3
"""Regression and attack tests for Wave 007-A.

These are implementer self-tests.  They do not replace root's independently
frozen mutation protocol.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
ROUND = HERE.parents[1]
sys.path.insert(0, str(HERE))

from evaluator import evaluate  # noqa: E402
from runner import build_report, load_fixtures, run_case  # noqa: E402


class Wave007AHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_report()
        cls.by_id = {
            item["opaque_case_id"]: item["evaluation"]
            for item in cls.report["cases"]
        }

    def test_frozen_input_hashes(self) -> None:
        repair = ROUND / "WAVE-007-REPAIR-HARNESS.md"
        self.assertEqual(
            hashlib.sha256(repair.read_bytes()).hexdigest(),
            "7b6fe448b16cbeb48b749b76b454c8b3fd10e1669605927b49c28e575cdee653",
        )
        public, _ = load_fixtures()
        self.assertEqual(
            public["shared_task_sha256"],
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3",
        )

    def test_all_normal_worlds_match_without_fp_or_fn(self) -> None:
        aggregate = self.report["aggregate"]
        self.assertEqual(aggregate["case_count"], 13)
        self.assertEqual(aggregate["terminal_match_count"], 13)
        self.assertEqual(aggregate["effect_delta_match_count"], 13)
        self.assertEqual(aggregate["false_positive_count"], 0)
        self.assertEqual(aggregate["false_negative_count"], 0)

    def test_paired_authority_worlds_are_distinguished(self) -> None:
        expected = {
            "X7-A03": "ACCEPTED",
            "X7-A91": "REFUSE",
            "X7-B17": "ACCEPTED",
            "X7-B64": "REFUSE",
            "X7-C28": "ACCEPTED",
            "X7-C73": "REFUSE",
            "X7-F39": "ACCEPTED",
            "X7-F88": "UNKNOWN",
            "X7-G52": "ABSENT",
        }
        self.assertEqual(
            {
                key: self.by_id[key]["actual_terminal"]
                for key in expected
            },
            expected,
        )

    def test_replay_alias_and_semantic_changes_have_correct_effects(self) -> None:
        self.assertEqual(self.by_id["X7-D11"]["actual_effect_delta"], 0)
        self.assertEqual(self.by_id["X7-E05"]["actual_effect_delta"], 0)
        self.assertEqual(self.by_id["X7-D82"]["actual_effect_delta"], 1)
        self.assertEqual(self.by_id["X7-E96"]["actual_effect_delta"], 1)
        self.assertFalse(self.by_id["X7-D11"]["duplicate_effect"])
        self.assertFalse(self.by_id["X7-E05"]["duplicate_effect"])

    def test_unknown_refuse_absent_are_not_collapsed(self) -> None:
        counts = self.report["aggregate"]["terminal_counts"]
        self.assertGreater(counts["UNKNOWN"], 0)
        self.assertGreater(counts["REFUSE"], 0)
        self.assertGreater(counts["ABSENT"], 0)

    def test_evidence_deletion_and_unauthorized_signature_fail(self) -> None:
        attacks = self.report["mutations"]
        self.assertFalse(
            attacks["evidence_deletion"]["accepted_after_deletion"]
        )
        self.assertFalse(
            attacks["unauthorized_signature"][
                "accepted_after_substitution"
            ]
        )
        duplicate = attacks["duplicate_non_quorum_evidence"]
        self.assertFalse(duplicate["duplicate_holder_counts_as_two"])
        self.assertFalse(
            duplicate["replayed_ack_substitutes_for_required_ack"]
        )

    def test_truth_flip_changes_confusion_not_candidate(self) -> None:
        attack = self.report["mutations"]["truth_label_flip"]
        self.assertTrue(attack["candidate_output_reused_without_rerun"])
        self.assertFalse(attack["base_false_positive"])
        self.assertTrue(attack["flipped_false_positive"])

    def test_name_and_function_label_do_not_change_cost(self) -> None:
        attacks = self.report["mutations"]
        self.assertTrue(attacks["opaque_rename"]["same_result"])
        self.assertTrue(attacks["opaque_rename"]["same_cost"])
        self.assertTrue(attacks["label_function_swap"]["same_terminal"])
        self.assertTrue(attacks["label_function_swap"]["same_cost"])

    def test_candidate_self_reports_are_ignored(self) -> None:
        attack = self.report["mutations"]["self_report_injection"]
        self.assertTrue(attack["accepted_recomputed"])
        self.assertIn("accepted", attack["ignored_fields"])
        self.assertIn("net_value", attack["ignored_fields"])
        self.assertNotEqual(attack["net_value_recomputed"], 9999)

    def test_changed_bytes_cannot_reuse_chain(self) -> None:
        attacks = self.report["mutations"]["bytes_binding_mutations"]
        for field in (
            "command",
            "purpose",
            "idempotency_key",
            "environment_version",
        ):
            self.assertFalse(attacks[field]["accepted"], field)
            self.assertTrue(attacks[field]["errors"], field)

    def test_same_idempotency_key_changed_command_is_refused(self) -> None:
        attack = self.report["mutations"][
            "same_idempotency_changed_command"
        ]
        self.assertEqual(attack["actual_terminal"], "REFUSE")
        self.assertFalse(attack["accepted"])
        self.assertEqual(attack["effect_delta"], 0)

    def test_quorum_counts_unique_allowlisted_bound_issuers(self) -> None:
        quorum = self.report["mutations"]["attestation_quorum"]
        self.assertTrue(quorum["valid_distinct_issuers"]["quorum"])
        for mutation in (
            "duplicate_same_object",
            "replayed_copy",
            "cross_checkpoint",
            "cross_slot",
        ):
            self.assertFalse(quorum[mutation]["quorum"], mutation)
            self.assertEqual(quorum[mutation]["unique_valid_count"], 1)

    def test_operation_log_cost_is_recomputed(self) -> None:
        cost = self.report["mutations"]["operation_log_recompute"]
        self.assertEqual(
            cost["deleted_call"]["coordination_operations"],
            cost["original"]["coordination_operations"] - 1,
        )
        self.assertEqual(
            cost["added_call"]["coordination_operations"],
            cost["original"]["coordination_operations"] + 1,
        )
        self.assertEqual(cost["reordered_same_multiset"], cost["original"])

    def test_candidate_output_has_no_evaluator_fields(self) -> None:
        run = run_case("X7-A03")
        output = run["candidate_output"]
        for forbidden in (
            "accepted",
            "false_positive",
            "false_negative",
            "promotion",
            "net_value",
            "cost",
        ):
            self.assertNotIn(forbidden, output)
        serialized = json.dumps(output)
        self.assertNotIn("X7-A03", serialized)
        self.assertNotIn("display_truth_label", serialized)
        self.assertNotIn("expected_terminal", serialized)

    def test_evaluator_rejects_environment_and_key_rebinding(self) -> None:
        public, hidden = load_fixtures()
        base = run_case("X7-A03")
        for field, value in (
            ("environment_version", "sterile-sim-env-evil"),
            ("idempotency_key", "stolen-key"),
        ):
            changed = copy.deepcopy(public["requests"]["X7-A03"])
            changed[field] = value
            outcome = evaluate(
                public_request=changed,
                world_truth=hidden["worlds"]["X7-A03"],
                public_registry=base["public_registry"],
                candidate_output=base["candidate_output"],
                operation_log=base["operation_log"],
                before_snapshot=base["before_snapshot"],
                after_snapshot=base["after_snapshot"],
            )
            self.assertFalse(outcome["accepted"], field)
            self.assertTrue(outcome["errors"], field)

    def test_no_same_process_candidate_facade_exists(self) -> None:
        from authorities import AuthorityNetwork

        self.assertFalse(hasattr(AuthorityNetwork, "candidate_api"))
        source = (HERE / "strategy.py").read_text(encoding="utf-8")
        for forbidden in (
            "hidden-worlds",
            "expected_terminal",
            "display_truth_label",
            "AuthorityNetwork",
            "private_key",
        ):
            self.assertNotIn(forbidden, source)

    def test_manifest_hashes_close_over_declared_outputs(self) -> None:
        manifest = json.loads(
            (HERE / "manifest.json").read_text(encoding="utf-8")
        )
        for relative, expected in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((HERE / relative).read_bytes()).hexdigest(),
                expected,
                relative,
            )


if __name__ == "__main__":
    unittest.main()
