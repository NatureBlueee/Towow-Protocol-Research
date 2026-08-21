from __future__ import annotations

import copy
import hashlib
import inspect
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUND_ROOT = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

import evaluator  # noqa: E402
import simulator  # noqa: E402
from authority import AuthorityBroker, PrivateWorldState  # noqa: E402
from public_api import JsonRpcEvidenceGateway  # noqa: E402


class FakeRpcClient:
    def call(self, method, params):
        return {"method": method, "params": params}


class Wave007B2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.simulation = simulator.simulate()
        cls.result = evaluator.evaluate()
        cls.baseline_runs = {
            (
                run["evaluator_truth"]["evaluator_world_id"],
                run["runner"]["implementation_id"],
            ): run
            for run in cls.simulation["baseline_runs"]
        }
        cls.baseline_eval = {
            (
                row["evaluator_world_id"],
                row["implementation_id"],
            ): row
            for row in cls.result["baseline"]
        }

    def test_frozen_input_hashes(self) -> None:
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

    def test_candidate_runs_in_distinct_spawned_process(self) -> None:
        run = self.baseline_runs[
            ("PW-BOUNDED-VALID", "BOUNDED_RELATION")
        ]
        runner = run["runner"]
        self.assertNotEqual(runner["parent_pid"], runner["worker_pid"])
        self.assertEqual(
            "SPAWNED_PROCESS_NDJSON_RPC", runner["transport"]
        )
        self.assertFalse(runner["broker_object_transferred"])
        self.assertFalse(runner["audit_handle_transferred"])

    def test_candidate_gateway_method_has_no_service_closure(self) -> None:
        gateway = JsonRpcEvidenceGateway("opaque", FakeRpcClient())
        method = gateway.read_evidence
        self.assertIsNone(method.__func__.__closure__)
        self.assertEqual({"opaque_handle", "_client"}, set(gateway.__slots__))
        self.assertNotIn("service", inspect.getsource(method.__func__))
        self.assertNotIn("audit", inspect.getsource(method.__func__))

    def test_candidate_and_worker_do_not_import_parent_authority(self) -> None:
        candidate_source = (ROOT / "candidate.py").read_text(
            encoding="utf-8"
        )
        worker_source = (ROOT / "candidate_worker.py").read_text(
            encoding="utf-8"
        )
        for source in [candidate_source, worker_source]:
            self.assertNotIn("from authority", source)
            self.assertNotIn("import authority", source)
            self.assertNotIn("import evaluator", source)
            self.assertNotIn("import simulator", source)
            self.assertNotIn("PrivateWorldState", source)

    def test_forbidden_truth_log_and_sign_rpcs_are_rejected(self) -> None:
        run = self.simulation["mutations"]["rpc_boundary_probe"]
        self.assertEqual(
            {
                "get_private_world_state": "METHOD_NOT_ALLOWED",
                "clear_audit_log": "METHOD_NOT_ALLOWED",
                "sign_for_authority": "METHOD_NOT_ALLOWED",
            },
            run["forbidden_rpc_probe_results"],
        )
        rejected = [
            item for item in run["operation_log"]
            if item["op"] == "RPC_REJECTED"
        ]
        self.assertEqual(3, len(rejected))
        self.assertTrue(evaluator.evaluate_run(run)["reuse_executed"])

    def test_exported_snapshot_cannot_clear_parent_log(self) -> None:
        broker = AuthorityBroker(
            PrivateWorldState(
                reuse_truth="ONE_OPERATION_ONLY",
                relation_evidence="VALID_NO_REUSE",
                withdraw_after_first_reuse=False,
            ),
            opaque_seed="snapshot-copy-test",
        )
        broker.dispatch("read_evidence", {"name": "delivery"})
        first = broker.snapshot()
        self.assertEqual(1, len(first.operation_log))
        first.operation_log.clear()
        first.evidence_returns.clear()
        second = broker.snapshot()
        self.assertEqual(1, len(second.operation_log))
        self.assertIn("delivery", second.evidence_returns)

    def test_runtime_signing_keys_are_random_not_derivable_helper(self) -> None:
        source = (ROOT / "authority.py").read_text(encoding="utf-8")
        self.assertNotIn("def _private_key", source)
        self.assertNotIn("private_key_from_hex", source)
        self.assertNotIn("towow-wave007b:", source)
        left = AuthorityBroker(
            PrivateWorldState(
                reuse_truth="ONE_OPERATION_ONLY",
                relation_evidence="VALID_NO_REUSE",
                withdraw_after_first_reuse=False,
            ),
            opaque_seed="random-left",
        ).snapshot().contract
        right = AuthorityBroker(
            PrivateWorldState(
                reuse_truth="ONE_OPERATION_ONLY",
                relation_evidence="VALID_NO_REUSE",
                withdraw_after_first_reuse=False,
            ),
            opaque_seed="random-right",
        ).snapshot().contract
        left_keys = {
            row["issuer"]: row["public_key_hex"]
            for row in left["verification_keys"]
        }
        right_keys = {
            row["issuer"]: row["public_key_hex"]
            for row in right["verification_keys"]
        }
        self.assertNotEqual(left_keys, right_keys)

    def test_runner_identity_ignores_candidate_claimed_label(self) -> None:
        world = next(
            row
            for row in simulator.load_json("paired-worlds.json")["worlds"]
            if row["evaluator_world_id"] == "PW-BOUNDED-VALID"
        )
        representation = next(
            row
            for row in simulator.load_json("representations.json")[
                "representations"
            ]
            if row["representation_id"] == "BOUNDED_RELATION"
        )
        run = simulator.run_one(
            world,
            representation,
            candidate_label="TASK_BOUND",
            opaque_seed="identity-root-replay",
        )
        row = evaluator.evaluate_run(run)
        self.assertEqual("TASK_BOUND", row["candidate_claimed_label_ignored"])
        self.assertEqual("BOUNDED_RELATION", row["implementation_id"])
        self.assertEqual(
            "RAW_OPERATIONS_MATCHED_TO_RUNNER_REGISTRY",
            row["identity_source"],
        )
        self.assertTrue(row["runner_identity_binding_valid"])
        self.assertTrue(row["reuse_executed"])

    def test_results_do_not_use_candidate_label_as_identity(self) -> None:
        evaluator_source = (ROOT / "evaluator.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(
            '["candidate_label"] == "BOUNDED_RELATION"',
            evaluator_source,
        )
        attacks = self.result["mutation_results"]
        self.assertTrue(attacks["runner_identity_ignores_candidate_label"])
        self.assertTrue(attacks["runner_identity_field_tamper_rejected"])
        self.assertTrue(attacks["label_function_swap_score_unchanged"])

    def test_task_bound_is_safe_in_one_operation_worlds(self) -> None:
        for world in ["PW-ONE-VALID", "PW-ONE-CONTRADICTORY"]:
            row = self.baseline_eval[(world, "TASK_BOUND")]
            self.assertFalse(row["relation_constituted"])
            self.assertFalse(row["reuse_executed"])
            self.assertEqual(0, row["false_constitution"])
            self.assertEqual(0, row["stale_reuse"])

    def test_bounded_evidence_materially_enables_reuse(self) -> None:
        bounded = {
            name: self.baseline_eval[("PW-BOUNDED-VALID", name)]
            for name in [
                "TASK_BOUND",
                "EXPLAIN_BACK",
                "BOUNDED_RELATION",
                "NO_EVIDENCE",
            ]
        }
        self.assertTrue(bounded["BOUNDED_RELATION"]["reuse_executed"])
        self.assertTrue(
            bounded["BOUNDED_RELATION"]["relation_constituted"]
        )
        for name in ["TASK_BOUND", "EXPLAIN_BACK", "NO_EVIDENCE"]:
            self.assertFalse(bounded[name]["reuse_executed"])
            self.assertEqual(1, bounded[name]["missed_legitimate_reuse"])

    def test_missing_relation_evidence_remains_missed_value(self) -> None:
        row = self.baseline_eval[
            ("PW-BOUNDED-CONTRADICTORY", "BOUNDED_RELATION")
        ]
        self.assertFalse(row["relation_constituted"])
        self.assertFalse(row["reuse_executed"])
        self.assertEqual(1, row["missed_legitimate_reuse"])

    def test_all_decisive_evidence_deletions_change_action(self) -> None:
        deletion = self.result["mutation_results"]["evidence_deletion"]
        self.assertEqual(8, len(deletion))
        for row in deletion.values():
            self.assertFalse(row["relation_constituted"])
            self.assertFalse(row["reuse_executed"])
            self.assertEqual(1, row["missed_legitimate_reuse"])

    def test_signature_authority_and_withdrawal_attacks_hold(self) -> None:
        attacks = self.result["mutation_results"]
        for key in [
            "duplicate_authorization_rejected",
            "unauthorized_authorization_rejected",
            "changed_signed_bytes_rejected",
            "wrong_kind_evidence_rejected",
            "cross_purpose_authorization_rejected",
            "unauthorized_withdrawal_not_accepted",
            "post_withdrawal_reuse_counted",
        ]:
            self.assertTrue(attacks[key], key)

    def test_truth_rename_self_report_and_cost_invariants_hold(self) -> None:
        attacks = self.result["mutation_results"]
        for key in [
            "opaque_rename_behavior_unchanged",
            "opaque_rename_score_unchanged",
            "self_report_score_unchanged",
            "truth_label_flip_candidate_behavior_unchanged",
            "truth_label_flip_confusion_changed",
            "forbidden_log_clear_did_not_clear_parent_log",
            "runtime_public_keys_differ_across_runs",
        ]:
            self.assertTrue(attacks[key], key)

    def test_raw_operation_log_drives_cost(self) -> None:
        run = copy.deepcopy(
            self.baseline_runs[
                ("PW-BOUNDED-VALID", "BOUNDED_RELATION")
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
                "name": "extra",
                "observation": "UNKNOWN",
                "bytes": 1024,
                "disclosure_units": 1,
            }
        )
        self.assertGreater(
            evaluator.recompute_cost(run)["evidence_cost"],
            baseline["evidence_cost"],
        )

    def test_unknown_refuse_absent_stay_distinct(self) -> None:
        valid = self.baseline_eval[
            ("PW-ONE-VALID", "BOUNDED_RELATION")
        ]["terminal_observations"]
        conflict = self.baseline_eval[
            ("PW-ONE-CONTRADICTORY", "BOUNDED_RELATION")
        ]["terminal_observations"]
        self.assertGreater(valid["REFUSE"], 0)
        self.assertGreater(valid["ABSENT"], 0)
        self.assertGreater(conflict["UNKNOWN"], 0)

    def test_scope_and_honest_isolation_boundary(self) -> None:
        self.assertIsNone(self.result["overall_grade"])
        self.assertEqual(
            "SAME_RESEARCHER_REPAIR_NOT_INDEPENDENT_EVIDENCE",
            self.result["repair_status"],
        )
        self.assertEqual(
            "LOCAL_SYNTHETIC_PROCESS_ISOLATION_SELF_TEST_PENDING_ROOT_REAUDIT",
            self.result["evidence_boundary"],
        )
        run = self.baseline_runs[
            ("PW-BOUNDED-VALID", "BOUNDED_RELATION")
        ]
        self.assertFalse(run["runner"]["filesystem_sandbox"])

    def test_evaluation_output_is_deterministic_despite_random_keys(self) -> None:
        second = evaluator.evaluate()
        self.assertEqual(self.result, second)

    def test_committed_result_matches_recomputation(self) -> None:
        committed = json.loads(
            (ROOT / "results.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.result, committed)


if __name__ == "__main__":
    unittest.main()
