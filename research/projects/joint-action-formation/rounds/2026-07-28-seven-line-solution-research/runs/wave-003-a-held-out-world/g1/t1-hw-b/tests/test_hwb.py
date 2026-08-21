from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packet_builder import build_packets, canonical_bytes, load_json, write_packets  # noqa: E402
from scorer import apply_mutation, evaluate, validate_submission_structure  # noqa: E402


class HiddenWorldBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle = load_json(ROOT / "oracle_truth.json")
        cls.source = load_json(ROOT / "controller_input.json")
        cls.fixture = load_json(
            ROOT / "fixtures" / "scorer_conformance_receipt.json"
        )
        cls.mutations = load_json(
            ROOT / "mutations" / "negative_mutations.json"
        )["mutations"]
        cls.schema = load_json(
            ROOT / "method-visible" / "submission_schema.json"
        )

    def test_calibration_receipt_passes_all_eight_requirements(self) -> None:
        result = evaluate(self.fixture, self.oracle)
        self.assertEqual("PASS", result["status"], result["critical_failures"])
        self.assertEqual([], result["critical_failures"])
        self.assertEqual(8, result["coverage"]["requirements_passed"])
        self.assertEqual(8, result["coverage"]["requirements_total"])
        self.assertEqual(1.0, result["coverage"]["ratio"])
        self.assertEqual(3, result["metrics"]["correctly_discovered_count"])
        self.assertEqual(0, result["metrics"]["false_wakeup_count"])

    def test_every_negative_mutation_is_detected(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["mutation_id"]):
                mutated = apply_mutation(self.fixture, mutation)
                result = evaluate(mutated, self.oracle)
                failure_codes = {
                    item["code"] for item in result["critical_failures"]
                }
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    set(mutation["expected_failure_codes"]) <= failure_codes,
                    (
                        f"{mutation['mutation_id']} expected "
                        f"{mutation['expected_failure_codes']}, got "
                        f"{sorted(failure_codes)}"
                    ),
                )
                for requirement_id in mutation["expected_failed_requirements"]:
                    self.assertEqual(
                        "FAIL",
                        result["requirement_results"][requirement_id]["status"],
                    )

    def test_scorer_is_deterministic_and_does_not_mutate_input(self) -> None:
        before = json.dumps(self.fixture, ensure_ascii=False, sort_keys=True)
        first = evaluate(self.fixture, self.oracle)
        second = evaluate(self.fixture, self.oracle)
        after = json.dumps(self.fixture, ensure_ascii=False, sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(before, after)

    def test_packets_are_physically_scoped_and_holder_names_do_not_encode_role(
        self,
    ) -> None:
        packets = build_packets(self.source)
        local_count = len(self.source["local_execution_views"])
        self.assertEqual(local_count + 1, len(packets))
        coordinator = packets["coordinator.json"]
        self.assertNotIn("local_view", coordinator)
        self.assertNotIn("local_execution_views", json.dumps(coordinator))
        for path, packet in packets.items():
            if path == "coordinator.json":
                self.assertNotIn("local_view", packet)
            else:
                self.assertEqual("METHOD_VISIBLE_LOCAL_PACKET", packet["kind"])
                self.assertIn("local_view", packet)
                self.assertNotIn("public_view", packet)
                self.assertNotRegex(packet["recipient"], r"(SEEK|OFFER|PROVIDER)")

    def test_local_projection_and_reciprocal_roles_are_explicit(self) -> None:
        packets = build_packets(self.source)
        projection_holders = {"HELIOS-44", "ION-06"}
        reciprocal_holders = {"JUNIPER-28", "KITE-15"}
        for holder in projection_holders:
            observation = packets[f"local/{holder}.json"]["local_view"][
                "observations"
            ][0]
            projection = observation["permitted_projection"]
            self.assertIn(projection["direction"], {"SEEK", "OFFER"})
            self.assertTrue(projection["compatibility_key"])
            self.assertTrue(projection["facet"])
        for holder in reciprocal_holders:
            observation = packets[f"local/{holder}.json"]["local_view"][
                "observations"
            ][0]
            self.assertIn(observation["direction"], {"SEEK", "OFFER"})
            self.assertTrue(observation["compatibility_key"])
            self.assertTrue(observation["requested_counterfact_id"])

    def test_dynamic_packet_maps_update_to_public_signature(self) -> None:
        packets = build_packets(self.source)
        observation = packets["local/DELTA-09.json"]["local_view"][
            "observations"
        ][0]
        signature = observation["invalidates_public_signature"]
        public_signatures = {
            item["signature_id"]
            for item in packets["coordinator.json"]["public_view"]["signals"]
        }
        self.assertIn(signature, public_signatures)
        self.assertEqual(2, observation["step"])

    def test_oracle_ids_absent_from_every_method_visible_artifact(self) -> None:
        packets = build_packets(self.source)
        visible_values = list(packets.values()) + [self.schema]
        visible_text = json.dumps(visible_values, ensure_ascii=False, sort_keys=True)
        visible_text += (
            ROOT / "method-visible" / "README.md"
        ).read_text(encoding="utf-8")
        for item in self.oracle["expected_items"]:
            self.assertNotIn(item["item_id"], visible_text)
        self.assertNotIn('"expected_state"', visible_text)
        self.assertNotIn("required_disclosure_paths", visible_text)
        self.assertNotIn("required_reciprocal_probe", visible_text)

    def test_method_visible_schema_builds_structural_non_solution(self) -> None:
        coordinator = build_packets(self.source)["coordinator.json"]
        claim = coordinator["public_view"]["claims_to_resolve"][0]
        submission = {
            "schema_version": "1.1",
            "world_id": coordinator["world_id"],
            "evaluation_step": coordinator["evaluation_step"],
            "method_id": "STRUCTURE-ONLY-NO-SOLUTION",
            "decisions": [
                {
                    "detection_id": "METHOD-OWNED-1",
                    "kind": "CLAIM",
                    "state": "UNKNOWN",
                    "claim_key": claim["claim_key"],
                    "subject": claim["subject"],
                    "evidence_refs": [],
                }
            ],
            "probes": [],
            "disclosures": [],
            "projection_updates": [],
            "relation_handoffs": [],
        }
        self.assertEqual([], validate_submission_structure(submission))
        self.assertEqual(
            "towow-t1-hidden-world-b-submission-1.1",
            self.schema["$id"],
        )

    def test_secret_identifier_interface_is_rejected(self) -> None:
        invalid = {
            "schema_version": "1.1",
            "world_id": "T1-HW-20260728-B",
            "evaluation_step": 2,
            "method_id": "INVALID-SECRET-CLIENT",
            "decisions": [
                {
                    "detection_id": "METHOD-OWNED-1",
                    "kind": "CLAIM",
                    "state": "UNKNOWN",
                    "claim_key": "visible:key",
                    "subject": "visible-subject",
                    "evidence_refs": [],
                    "truth_id": "secret",
                }
            ],
            "probes": [],
            "disclosures": [],
            "projection_updates": [],
            "relation_handoffs": [],
        }
        codes = {
            item["code"] for item in validate_submission_structure(invalid)
        }
        self.assertIn("FIELDS_FORBIDDEN", codes)
        self.assertIn("ORACLE_INTERFACE_FIELD_FORBIDDEN", codes)

    def test_score_output_does_not_expose_oracle_item_ids(self) -> None:
        incomplete = {
            **self.fixture,
            "method_id": "EMPTY-TEST",
            "decisions": [],
            "probes": [],
            "disclosures": [],
            "projection_updates": [],
            "relation_handoffs": [],
        }
        output = json.dumps(
            evaluate(incomplete, self.oracle),
            ensure_ascii=False,
            sort_keys=True,
        )
        for item in self.oracle["expected_items"]:
            self.assertNotIn(item["item_id"], output)
        self.assertNotIn('"truth_id"', output)

    def test_builder_output_matches_frozen_delivery_packets(self) -> None:
        packets = build_packets(self.source)
        with tempfile.TemporaryDirectory() as temp_dir:
            temporary = Path(temp_dir)
            index = write_packets(packets, temporary)
            frozen = ROOT / "delivery-packets"
            self.assertEqual(len(packets), index["packet_count"])
            for entry in index["packets"]:
                generated = temporary / entry["path"]
                committed = frozen / entry["path"]
                self.assertTrue(committed.is_file(), entry["path"])
                self.assertEqual(generated.read_bytes(), committed.read_bytes())
                self.assertEqual(
                    hashlib.sha256(canonical_bytes(packets[entry["path"]])).hexdigest(),
                    entry["sha256"],
                )

    def test_calibration_fixture_is_not_a_candidate_result(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        self.assertEqual(
            "MANUAL-HWB-ORACLE-CALIBRATION-NOT-A-CANDIDATE",
            self.fixture["method_id"],
        )
        self.assertFalse(manifest["claims"]["fixture_is_candidate_result"])

    def test_manifest_hashes_match_frozen_artifacts(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        for artifact in manifest["artifacts"]:
            path = ROOT / artifact["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(artifact["sha256"], actual, artifact["path"])
        index = load_json(ROOT / manifest["packet_closure"]["index_path"])
        for entry in index["packets"]:
            path = ROOT / "delivery-packets" / entry["path"]
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(entry["sha256"], actual, entry["path"])


if __name__ == "__main__":
    unittest.main()
