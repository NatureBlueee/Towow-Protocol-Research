from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import (  # noqa: E402
    apply_mutation,
    evaluate,
    load_json,
    validate_submission_structure
)
from packet_builder import build_packets, write_packets  # noqa: E402


class HiddenWorldEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle = load_json(ROOT / "oracle_truth.json")
        cls.fixture = load_json(
            ROOT / "fixtures" / "scorer_conformance_receipt.json"
        )
        cls.mutations = load_json(
            ROOT / "mutations" / "negative_mutations.json"
        )["mutations"]
        cls.controller_input = load_json(ROOT / "controller_input.json")
        cls.submission_schema = load_json(ROOT / "submission_schema.json")

    def test_conformance_receipt_passes_all_requirements(self) -> None:
        result = evaluate(self.fixture, self.oracle)
        self.assertEqual("PASS", result["status"], result["critical_failures"])
        self.assertEqual([], result["critical_failures"])
        self.assertEqual(8, result["coverage"]["requirements_passed"])
        self.assertEqual(1.0, result["coverage"]["ratio"])
        self.assertEqual(3, result["metrics"]["correctly_discovered_opportunities"])
        self.assertEqual(0, result["metrics"]["false_wakeup_count"])

    def test_every_negative_mutation_is_detected(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["mutation_id"]):
                mutated = apply_mutation(self.fixture, mutation)
                result = evaluate(mutated, self.oracle)
                failure_codes = {
                    failure["code"] for failure in result["critical_failures"]
                }
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    set(mutation["expected_failure_codes"]) <= failure_codes,
                    (
                        f"{mutation['mutation_id']} expected "
                        f"{mutation['expected_failure_codes']}, got "
                        f"{sorted(failure_codes)}"
                    )
                )
                for requirement_id in mutation["expected_failed_requirements"]:
                    self.assertEqual(
                        "FAIL",
                        result["requirement_results"][requirement_id]["status"]
                    )

    def test_evaluator_is_deterministic_and_does_not_mutate_submission(self) -> None:
        before = json.dumps(self.fixture, sort_keys=True)
        first = evaluate(self.fixture, self.oracle)
        second = evaluate(self.fixture, self.oracle)
        after = json.dumps(self.fixture, sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_packet_builder_physically_separates_delivery_domains(self) -> None:
        packets = build_packets(self.controller_input)
        local_count = len(self.controller_input["local_execution_views"])
        self.assertEqual(local_count + 1, len(packets))
        self.assertNotIn(
            "local_execution_views",
            json.dumps(packets["coordinator.json"], sort_keys=True)
        )
        for path, packet in packets.items():
            if path == "coordinator.json":
                self.assertNotIn("local_view", packet)
            else:
                self.assertEqual("METHOD_VISIBLE_LOCAL_PACKET", packet["kind"])
                self.assertIn("local_view", packet)
                self.assertNotIn("public_view", packet)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            index = write_packets(packets, output_dir)
            self.assertTrue((output_dir / "coordinator.json").is_file())
            self.assertEqual(local_count + 1, index["packet_count"])
            for entry in index["packets"]:
                self.assertTrue((output_dir / entry["path"]).is_file())

    def test_oracle_ids_absent_from_every_method_visible_artifact(self) -> None:
        packets = build_packets(self.controller_input)
        visible_values = list(packets.values()) + [self.submission_schema]
        serialized = json.dumps(visible_values, sort_keys=True)
        secret_ids = [item["item_id"] for item in self.oracle["expected_items"]]
        for secret_id in secret_ids:
            self.assertNotIn(secret_id, serialized)
        self.assertNotIn('"expected_state"', serialized)
        self.assertNotIn("local_execution_views", serialized)

    def test_visible_packets_and_schema_can_form_structural_submission(self) -> None:
        packets = build_packets(self.controller_input)
        coordinator = packets["coordinator.json"]
        visible_claim = coordinator["public_view"]["claims_to_resolve"][0]
        submission = {
            "schema_version": "1.1",
            "world_id": coordinator["world_id"],
            "evaluation_step": coordinator["evaluation_step"],
            "method_id": "STRUCTURE-ONLY-NO-SOLUTION",
            "decisions": [
                {
                    "detection_id": "METHOD-OWNED-001",
                    "kind": "CLAIM",
                    "claim_key": visible_claim["claim_key"],
                    "subject": visible_claim["subject"],
                    "state": "UNKNOWN",
                    "evidence_refs": []
                }
            ],
            "probes": [],
            "disclosures": [],
            "projection_updates": [],
            "relation_handoffs": []
        }
        self.assertEqual([], validate_submission_structure(submission))
        self.assertEqual(
            "towow-t1-hidden-world-submission-1.1",
            self.submission_schema["$id"]
        )

    def test_legacy_oracle_identifier_interface_is_rejected(self) -> None:
        legacy_submission = {
            "schema_version": "1.1",
            "world_id": "T1-HW-20260728-A",
            "evaluation_step": 1,
            "method_id": "LEGACY-SECRET-ID-CLIENT",
            "decisions": [
                {
                    "detection_id": "METHOD-OWNED-001",
                    "item_id": "A-SECRET-TRUTH-ID",
                    "kind": "CLAIM",
                    "claim_key": "visible:key",
                    "subject": "P-VISIBLE",
                    "state": "UNKNOWN",
                    "evidence_refs": []
                }
            ],
            "probes": [],
            "disclosures": [],
            "projection_updates": [],
            "relation_handoffs": []
        }
        error_codes = {
            error["code"]
            for error in validate_submission_structure(legacy_submission)
        }
        self.assertIn("DECISION_FIELDS_FORBIDDEN", error_codes)
        self.assertIn("ORACLE_INTERFACE_FIELD_FORBIDDEN", error_codes)

    def test_conformance_fixture_is_explicitly_calibration_only(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        self.assertEqual(
            "MANUAL-ORACLE-CALIBRATION-NOT-A-CANDIDATE",
            self.fixture["method_id"]
        )
        self.assertFalse(manifest["claims"]["fixture_is_candidate_result"])

    def test_manifest_hashes_match_frozen_artifacts(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        for artifact in manifest["artifacts"]:
            path = ROOT / artifact["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(
                artifact["sha256"],
                digest,
                f"Hash mismatch for {artifact['path']}"
            )


if __name__ == "__main__":
    unittest.main()
