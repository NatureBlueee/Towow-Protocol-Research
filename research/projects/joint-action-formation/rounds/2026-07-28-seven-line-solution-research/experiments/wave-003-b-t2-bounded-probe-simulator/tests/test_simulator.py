from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from simulator import (  # noqa: E402
    SCENARIO_IDS,
    load_json,
    sha256_value,
    simulate,
    validate_probe_input,
    verify_result_receipt
)


class BoundedProbeSimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.probe_input = load_json(ROOT / "probe_input.json")
        cls.scenario_truth = load_json(ROOT / "scenario_truth.json")
        cls.scenario_by_id = {
            item["scenario_id"]: item
            for item in cls.scenario_truth["scenarios"]
        }

    def test_input_binds_exact_dependencies_and_three_queries(self) -> None:
        validate_probe_input(self.probe_input)
        binding = self.probe_input["binding"]
        self.assertEqual(
            {"executor", "environment", "version", "permission", "resource"},
            set(binding)
        )
        query_ids = [item["query_id"] for item in self.probe_input["queries"]]
        self.assertEqual(3, len(query_ids))
        self.assertEqual(
            query_ids,
            binding["permission"]["allowed_query_ids"]
        )
        self.assertEqual(3, binding["resource"]["query_budget"])
        self.assertTrue(
            all(item["mode"] == "AGGREGATE_READ_ONLY" for item in self.probe_input["queries"])
        )

    def test_all_five_frozen_branches_are_deterministic_and_receipted(self) -> None:
        self.assertEqual(
            SCENARIO_IDS,
            set(self.scenario_by_id)
        )
        for scenario_id in sorted(SCENARIO_IDS):
            with self.subTest(scenario=scenario_id):
                first = simulate(
                    self.probe_input,
                    self.scenario_truth,
                    scenario_id
                )
                second = simulate(
                    self.probe_input,
                    self.scenario_truth,
                    scenario_id
                )
                self.assertEqual(first, second)
                self.assertTrue(
                    verify_result_receipt(
                        first,
                        self.probe_input,
                        self.scenario_truth
                    )
                )
                scenario = self.scenario_by_id[scenario_id]
                self.assertEqual(
                    scenario["expected_attempt_status"],
                    first["action_attempt"]["status"]
                )
                self.assertEqual(
                    scenario["expected_executed_query_count"],
                    len(first["action_attempt"]["executed_query_ids"])
                )
                self.assertEqual(
                    scenario["recovery_state"],
                    first["recovery"]["state"]
                )

    def test_action_attempt_and_buyer_witness_remain_separate(self) -> None:
        success = simulate(
            self.probe_input, self.scenario_truth, "success"
        )
        attempt = success["action_attempt"]
        witness = success["buyer_domain_witness"]
        self.assertEqual("ACTION_EXECUTOR", attempt["domain"])
        self.assertEqual("BUYER_CONTROLLED_AUDIT", witness["domain"])
        self.assertNotIn("audit_receipt_id", attempt)
        self.assertNotIn("raw_row_export_count", attempt)
        self.assertNotIn("producer_evidence", witness)
        self.assertFalse(
            attempt["producer_evidence"]["producer_evidence_establishes_buyer_effect"]
        )
        self.assertEqual(
            attempt["producer_evidence"]["query_output_hashes"],
            witness["query_output_hashes"]
        )

    def test_environment_mismatch_stops_before_execution(self) -> None:
        result = simulate(
            self.probe_input,
            self.scenario_truth,
            "environment_mismatch"
        )
        self.assertEqual("BLOCKED_PRE_EXECUTION", result["action_attempt"]["status"])
        self.assertEqual([], result["action_attempt"]["executed_query_ids"])
        self.assertFalse(
            result["action_attempt"]["producer_evidence"]["container_started"]
        )
        self.assertFalse(result["action_attempt"]["new_execution"])
        self.assertEqual(
            "RECORDED_PRE_EXECUTION_BLOCK",
            result["idempotency"]["decision"]
        )
        self.assertFalse(result["idempotency"]["new_execution"])
        self.assertEqual(
            "STOP_AND_REBIND_ENVIRONMENT",
            result["recovery"]["state"]
        )

    def test_credential_revocation_stops_before_third_query(self) -> None:
        result = simulate(
            self.probe_input,
            self.scenario_truth,
            "credential_revoked_mid_run"
        )
        self.assertEqual(
            ["Q-T2-AGG-01", "Q-T2-AGG-02"],
            result["action_attempt"]["executed_query_ids"]
        )
        self.assertEqual(
            "ABORTED_CREDENTIAL_REVOKED",
            result["action_attempt"]["status"]
        )
        self.assertFalse(result["recovery"]["retry_allowed"])
        self.assertIn(
            "credential",
            result["recovery"]["must_revalidate"]
        )

    def test_missing_buyer_witness_does_not_erase_action_attempt(self) -> None:
        result = simulate(
            self.probe_input,
            self.scenario_truth,
            "audit_witness_missing"
        )
        self.assertEqual("COMPLETED", result["action_attempt"]["status"])
        self.assertEqual("MISSING", result["buyer_domain_witness"]["status"])
        self.assertEqual(
            3,
            len(result["action_attempt"]["producer_evidence"]["query_output_hashes"])
        )
        self.assertEqual(
            {},
            result["buyer_domain_witness"]["query_output_hashes"]
        )
        self.assertEqual(
            "NOT_DECIDED_BY_THIS_RUNNER",
            result["evidence_boundary"]["effect_conclusion"]
        )

    def test_duplicate_retry_produces_no_new_execution_or_witness(self) -> None:
        result = simulate(
            self.probe_input,
            self.scenario_truth,
            "duplicate_retry"
        )
        self.assertEqual(
            "DEDUPLICATED_REPLAY",
            result["action_attempt"]["status"]
        )
        self.assertFalse(result["action_attempt"]["new_execution"])
        self.assertEqual([], result["action_attempt"]["executed_query_ids"])
        self.assertEqual(
            "REUSED_PRIOR_WITNESS",
            result["buyer_domain_witness"]["status"]
        )
        self.assertFalse(result["buyer_domain_witness"]["new_witness"])
        self.assertEqual(
            result["idempotency"]["prior_receipt_sha256"],
            result["hash_receipt"]["prior_receipt_sha256"]
        )
        self.assertIsNotNone(result["idempotency"]["prior_receipt_sha256"])

    def test_mutated_query_scope_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.probe_input)
        mutated["queries"].pop()
        with self.assertRaisesRegex(ValueError, "exactly three queries"):
            validate_probe_input(mutated)

    def test_cli_all_writes_one_result_per_branch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "simulator.py"),
                    "--all",
                    "--output-dir",
                    temp_dir
                ],
                check=False,
                capture_output=True,
                text=True
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            outputs = sorted(
                path.stem for path in Path(temp_dir).glob("*.json")
            )
            self.assertEqual(sorted(SCENARIO_IDS), outputs)

    def test_manifest_hashes_match(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        for artifact in manifest["artifacts"]:
            path = ROOT / artifact["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(
                artifact["sha256"],
                digest,
                artifact["path"]
            )

    def test_result_hash_receipt_binds_both_domains(self) -> None:
        result = simulate(
            self.probe_input, self.scenario_truth, "success"
        )
        receipt = result["hash_receipt"]
        self.assertEqual(
            sha256_value(result["action_attempt"]),
            receipt["action_attempt_sha256"]
        )
        self.assertEqual(
            sha256_value(result["buyer_domain_witness"]),
            receipt["buyer_domain_witness_sha256"]
        )


if __name__ == "__main__":
    unittest.main()
