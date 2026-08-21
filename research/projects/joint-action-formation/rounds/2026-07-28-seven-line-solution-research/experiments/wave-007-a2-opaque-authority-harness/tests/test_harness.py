#!/usr/bin/env python3
"""A2 same-researcher repair tests; these are not independent evidence."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from evaluator import evaluate  # noqa: E402
from runner import (  # noqa: E402
    ROOT_ATTACK,
    build_report,
    load_fixtures,
    run_case,
)


class Wave007A2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = build_report()
        cls.by_id = {
            item["opaque_case_id"]: item["evaluation"]
            for item in cls.report["cases"]
        }

    def test_old_root_attack_is_bound_and_reproduces_v1_failure(self) -> None:
        self.assertEqual(
            hashlib.sha256(ROOT_ATTACK.read_bytes()).hexdigest(),
            self.report["root_attack_sha256"],
        )
        old = json.loads(
            subprocess.check_output(
                [sys.executable, str(ROOT_ATTACK)], text=True
            )
        )
        attack = old["partial_then_changed_same_idempotency"]
        self.assertFalse(attack["controller_refused_at_attempt"])
        self.assertTrue(attack["new_domain_postcondition_called"])

    def test_a2_repairs_exact_root_attack(self) -> None:
        attack = self.report["root_attack_reproduction_and_repair"]
        self.assertEqual(attack["actual_terminal"], "REFUSE")
        self.assertTrue(attack["controller_refused_at_attempt"])
        self.assertFalse(attack["new_delivery_called"])
        self.assertFalse(attack["new_domain_postcondition_called"])
        self.assertEqual(attack["attempt_binding_delta"], 0)
        self.assertEqual(attack["l3_delta"], 0)
        self.assertEqual(attack["l4_delta"], 0)
        self.assertTrue(attack["all_level_deltas_match"])

    def test_same_key_changed_bytes_block_after_every_partial_level(self) -> None:
        for level, attack in self.report[
            "partial_then_changed_matrix"
        ].items():
            self.assertTrue(
                attack["controller_refused_at_attempt"], level
            )
            self.assertFalse(attack["new_delivery_called"], level)
            self.assertFalse(
                attack["new_domain_postcondition_called"], level
            )
            self.assertEqual(attack["l3_delta"], 0, level)
            self.assertEqual(attack["l4_delta"], 0, level)

    def test_l3_and_l4_are_independently_observed(self) -> None:
        refusal = self.report[
            "l3_l4_separation_beneficiary_refuse"
        ]
        self.assertEqual(refusal["actual_terminal"], "REFUSE")
        self.assertEqual(refusal["l3_domain_postcondition_delta"], 1)
        self.assertEqual(refusal["l4_beneficiary_acceptance_delta"], 0)

    def test_all_normal_worlds_match_at_all_three_levels(self) -> None:
        aggregate = self.report["aggregate"]
        self.assertEqual(aggregate["case_count"], 13)
        self.assertEqual(aggregate["terminal_match_count"], 13)
        self.assertEqual(
            aggregate["attempt_binding_delta_match_count"], 13
        )
        self.assertEqual(aggregate["l3_delta_match_count"], 13)
        self.assertEqual(aggregate["l4_delta_match_count"], 13)
        self.assertEqual(aggregate["false_positive_count"], 0)
        self.assertEqual(aggregate["false_negative_count"], 0)

    def test_exact_replay_and_alias_do_not_repeat_l3_or_l4(self) -> None:
        for case_id in ("X7-D11", "X7-E05"):
            result = self.by_id[case_id]
            self.assertEqual(
                result["actual_l3_domain_postcondition_delta"], 0
            )
            self.assertEqual(
                result["actual_l4_beneficiary_acceptance_delta"], 0
            )

    def test_new_material_and_environment_bind_new_attempt_l3_l4(self) -> None:
        for case_id in ("X7-D82", "X7-E96"):
            result = self.by_id[case_id]
            self.assertEqual(
                result["actual_attempt_binding_delta"], 1
            )
            self.assertEqual(
                result["actual_l3_domain_postcondition_delta"], 1
            )
            self.assertEqual(
                result["actual_l4_beneficiary_acceptance_delta"], 1
            )

    def test_unknown_refuse_absent_remain_distinct(self) -> None:
        self.assertEqual(self.by_id["X7-F88"]["actual_terminal"], "UNKNOWN")
        self.assertEqual(self.by_id["X7-A91"]["actual_terminal"], "REFUSE")
        self.assertEqual(self.by_id["X7-G52"]["actual_terminal"], "ABSENT")

    def test_quorum_verifier_retains_only_bounded_condition(self) -> None:
        quorum = self.report["quorum_verifier_conditions"]
        self.assertTrue(quorum["valid_distinct"])
        self.assertFalse(quorum["duplicate"])
        self.assertFalse(quorum["replay"])
        self.assertFalse(quorum["cross_checkpoint"])
        self.assertFalse(quorum["cross_slot"])

    def test_anchor_claim_is_explicitly_narrowed(self) -> None:
        scope = self.report["anchor_scope"]
        self.assertEqual(
            scope["equivocation_fixture"],
            "CENTRAL_HIDDEN_STATE_DETECTOR_FIXTURE_ONLY",
        )
        self.assertEqual(
            scope["malicious_anchor_self_proof"], "NOT_CLAIMED"
        )

    def test_filesystem_truth_isolation_is_refuted_not_claimed(self) -> None:
        scope = self.report["truth_isolation_scope"]
        self.assertTrue(
            scope["same_os_permission_peer_can_read_hidden_fixture"]
        )
        self.assertEqual(
            scope["filesystem_truth_isolation_claim"],
            "REFUTED_NOT_CLAIMED",
        )

    def test_fixed_candidate_source_has_no_truth_file_read(self) -> None:
        tree = ast.parse(
            (HERE / "strategy.py").read_text(encoding="utf-8")
        )
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
        }
        attrs = {
            node.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        }
        self.assertFalse(
            imported.intersection({"pathlib", "json", "os"})
        )
        self.assertNotIn("open", called)
        self.assertNotIn("read_text", attrs)

    def test_evidence_deletion_and_unauthorized_acceptance_fail(self) -> None:
        public, hidden = load_fixtures()
        base = run_case("X7-A03")
        for mutation in ("delete_ack", "controller_as_beneficiary"):
            output = copy.deepcopy(base["candidate_output"])
            if mutation == "delete_ack":
                del output["evidence"]["recipient_ack"]
            else:
                output["evidence"]["beneficiary_acceptance"] = output[
                    "evidence"
                ]["attempt"]
            result = evaluate(
                public_request=public["requests"]["X7-A03"],
                world_truth=hidden["worlds"]["X7-A03"],
                public_registry=base["public_registry"],
                candidate_output=output,
                operation_log=base["operation_log"],
                before_snapshot=base["before_snapshot"],
                after_snapshot=base["after_snapshot"],
            )
            self.assertFalse(result["accepted"], mutation)
            self.assertTrue(result["errors"], mutation)

    def test_candidate_self_report_is_ignored(self) -> None:
        public, hidden = load_fixtures()
        base = run_case("X7-A03")
        output = copy.deepcopy(base["candidate_output"])
        output.update(
            {
                "accepted": False,
                "false_positive": 0,
                "net_value": 9999,
                "cost": 0,
            }
        )
        result = evaluate(
            public_request=public["requests"]["X7-A03"],
            world_truth=hidden["worlds"]["X7-A03"],
            public_registry=base["public_registry"],
            candidate_output=output,
            operation_log=base["operation_log"],
            before_snapshot=base["before_snapshot"],
            after_snapshot=base["after_snapshot"],
        )
        self.assertTrue(result["accepted"])
        self.assertNotEqual(result["net_task_value"], 9999)
        self.assertIn("net_value", result["ignored_self_report_fields"])

    def test_truth_flip_changes_confusion_without_candidate_rerun(self) -> None:
        public, hidden = load_fixtures()
        base = run_case("X7-A03")
        flipped = copy.deepcopy(hidden["worlds"]["X7-A03"])
        flipped["expected_terminal"] = "REFUSE"
        result = evaluate(
            public_request=public["requests"]["X7-A03"],
            world_truth=flipped,
            public_registry=base["public_registry"],
            candidate_output=base["candidate_output"],
            operation_log=base["operation_log"],
            before_snapshot=base["before_snapshot"],
            after_snapshot=base["after_snapshot"],
        )
        self.assertTrue(result["false_positive"])

    def test_function_label_does_not_change_cost_or_result(self) -> None:
        base = run_case("X7-A03")
        relabelled = run_case(
            "X7-A03", strategy_name="bounded_reopen_relabelled"
        )
        self.assertEqual(
            base["evaluation"]["actual_terminal"],
            relabelled["evaluation"]["actual_terminal"],
        )
        self.assertEqual(
            base["evaluation"]["cost"],
            relabelled["evaluation"]["cost"],
        )

    def test_manifest_hashes_close_declared_outputs(self) -> None:
        manifest = json.loads(
            (HERE / "manifest.json").read_text(encoding="utf-8")
        )
        for relative, expected in manifest["files"].items():
            self.assertEqual(
                hashlib.sha256((HERE / relative).read_bytes()).hexdigest(),
                expected,
                relative,
            )
        for relative, expected in manifest["input_files"].items():
            self.assertEqual(
                hashlib.sha256((HERE / relative).read_bytes()).hexdigest(),
                expected,
                relative,
            )


if __name__ == "__main__":
    unittest.main()
