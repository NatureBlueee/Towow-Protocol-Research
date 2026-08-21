from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "private"))

from packet_builder import build_packets, canonical_bytes, load_json, write_packets  # noqa: E402
from scorer import apply_mutation, evaluate, validate_submission_structure  # noqa: E402


class HiddenWorldCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.oracle = load_json(ROOT / "private" / "oracle_truth.json")
        cls.source = load_json(ROOT / "controller_input.json")
        cls.fixture = load_json(
            ROOT / "private" / "fixtures" / "scorer_conformance_receipt.json"
        )
        cls.mutations = load_json(
            ROOT / "private" / "mutations" / "negative_mutations.json"
        )["mutations"]
        cls.schema = load_json(
            ROOT / "method-visible" / "submission_schema.json"
        )

    def test_01_calibration_passes_all_requirements(self) -> None:
        result = evaluate(self.fixture, self.oracle)
        self.assertEqual("PASS", result["status"], result["critical_failures"])
        self.assertEqual([], result["critical_failures"])
        self.assertEqual(8, result["coverage"]["requirements_passed"])
        self.assertEqual(1.0, result["coverage"]["ratio"])
        self.assertEqual(3, result["metrics"]["correctly_discovered_count"])
        self.assertEqual(0, result["metrics"]["false_wakeup_count"])

    def test_02_every_frozen_negative_mutation_is_detected(self) -> None:
        for mutation in self.mutations:
            with self.subTest(mutation=mutation["mutation_id"]):
                result = evaluate(
                    apply_mutation(self.fixture, mutation),
                    self.oracle,
                )
                codes = {row["code"] for row in result["critical_failures"]}
                self.assertEqual("FAIL", result["status"])
                self.assertTrue(
                    set(mutation["expected_failure_codes"]) <= codes,
                    f"{mutation['mutation_id']}: {sorted(codes)}",
                )
                for requirement_id in mutation["expected_failed_requirements"]:
                    self.assertEqual(
                        "FAIL",
                        result["requirement_results"][requirement_id]["status"],
                    )

    def _mutation_result(self, mutation_id: str) -> dict:
        mutation = next(
            row for row in self.mutations if row["mutation_id"] == mutation_id
        )
        return evaluate(apply_mutation(self.fixture, mutation), self.oracle)

    def test_03_self_signed_execution_is_rejected(self) -> None:
        result = self._mutation_result("HWC-M01-SELF-SIGNED-CONTROLLER-RECEIPT")
        self.assertIn(
            "EXECUTION_RECEIPT_UNTRUSTED",
            {row["code"] for row in result["critical_failures"]},
        )

    def test_04_missing_recipient_ack_is_rejected(self) -> None:
        result = self._mutation_result("HWC-M02-MISSING-RECIPIENT-ACK")
        self.assertIn(
            "RECIPIENT_ACK_SET_MISMATCH",
            {row["code"] for row in result["critical_failures"]},
        )

    def test_05_wrong_external_anchor_is_rejected(self) -> None:
        result = self._mutation_result("HWC-M03-WRONG-EXTERNAL-ANCHOR")
        self.assertIn(
            "EXTERNAL_ANCHOR_MISMATCH",
            {row["code"] for row in result["critical_failures"]},
        )

    def test_06_replay_and_tamper_are_rejected(self) -> None:
        replay = self._mutation_result("HWC-M05-IDEMPOTENCY-REPLAY-CONFLICT")
        tamper = self._mutation_result("HWC-M04-TAMPERED-ACTION-DIGEST")
        self.assertIn(
            "IDEMPOTENCY_REPLAY_CONFLICT",
            {row["code"] for row in replay["critical_failures"]},
        )
        self.assertIn(
            "EXECUTION_BINDING_MISMATCH",
            {row["code"] for row in tamper["critical_failures"]},
        )

    def test_07_depth_is_zero_at_first_recipient_and_one_after_onward(self) -> None:
        result = self._mutation_result("HWC-M06-ONWARD-DEPTH-OFF-BY-ONE")
        self.assertIn(
            "DELIVERY_PATH_MISMATCH",
            {row["code"] for row in result["critical_failures"]},
        )

    def test_08_direction_version_and_status_boundaries_are_rejected(self) -> None:
        mutation_ids = [
            "HWC-M07-RECIPROCAL-ORIENTATION-REVERSED",
            "HWC-M08-STALE-VERSION-WAKEUP",
            "HWC-M09-UNKNOWN-AS-ABSENT",
            "HWC-M10-REFUSE-AS-UNKNOWN",
            "HWC-M11-ABSENT-AS-UNKNOWN",
            "HWC-M12-POLICY-UNFINDABLE-AS-ABSENT",
            "HWC-M13-COMPATIBILITY-VERSION-DECOY",
        ]
        for mutation_id in mutation_ids:
            with self.subTest(mutation_id=mutation_id):
                self.assertEqual("FAIL", self._mutation_result(mutation_id)["status"])

    def test_09_packets_are_physically_split(self) -> None:
        packets = build_packets(self.source)
        self.assertEqual(
            len(self.source["local_execution_views"]) + 1,
            len(packets),
        )
        coordinator = packets["coordinator.json"]
        self.assertNotIn("local_view", coordinator)
        self.assertNotIn("local_execution_views", json.dumps(coordinator))
        for path, packet in packets.items():
            if path == "coordinator.json":
                self.assertEqual("COORDINATOR_ONLY", packet["delivery_scope"])
            else:
                self.assertEqual("METHOD_VISIBLE_LOCAL_PACKET", packet["kind"])
                self.assertIn("local_view", packet)
                self.assertNotIn("public_view", packet)
                self.assertNotIn("local_execution_views", packet)

    def test_10_method_contract_defines_depth_orientation_and_three_domains(self) -> None:
        text = (ROOT / "method-visible" / "README.md").read_text(encoding="utf-8")
        for phrase in (
            "`depth = 0`",
            "`depth` 增加 1",
            "`seeker = SEEK holder`",
            "reciprocal exchange 的执行是对称的",
            "`controller execution receipt`",
            "`recipient ACK`",
            "`external anchor`",
            "`UNKNOWN / REFUSE / ABSENT`",
        ):
            self.assertIn(phrase, text)

    def test_11_method_visible_artifacts_do_not_leak_oracle(self) -> None:
        packets = build_packets(self.source)
        visible_text = (
            (ROOT / "method-visible" / "README.md").read_text(encoding="utf-8")
            + json.dumps(self.schema, ensure_ascii=False, sort_keys=True)
            + json.dumps(list(packets.values()), ensure_ascii=False, sort_keys=True)
        )
        for item in self.oracle["expected_items"]:
            self.assertNotIn(item["item_id"], visible_text)
        for action in self.oracle["execution_actions"]:
            self.assertNotIn(action["controller_receipt_ref"], visible_text)
            self.assertNotIn(action["external_anchor_ref"], visible_text)
            for ack_ref in action["recipient_ack_refs"]:
                self.assertNotIn(ack_ref, visible_text)
        self.assertNotIn('"expected_state"', visible_text)
        self.assertNotIn('"required_evidence_refs"', visible_text)
        self.assertNotIn('"target_item_id"', visible_text)

    def test_12_schema_has_no_hidden_exact_world_or_answer_constants(self) -> None:
        schema_text = json.dumps(self.schema, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(self.oracle["world_id"], schema_text)
        self.assertNotIn("CEDAR-72", schema_text)
        self.assertNotIn("W-HWC-", schema_text)
        self.assertNotIn("CR-HWC-", schema_text)
        self.assertNotIn("ANCHOR-HWC-", schema_text)
        self.assertEqual(
            "towow-t1-hidden-world-c-submission-2.0",
            self.schema["$id"],
        )

    def test_13_schema_supports_structural_non_solution(self) -> None:
        coordinator = build_packets(self.source)["coordinator.json"]
        claim = coordinator["public_view"]["claims_to_resolve"][0]
        submission = {
            "schema_version": "2.0",
            "world_id": coordinator["world_id"],
            "evaluation_step": coordinator["evaluation_step"],
            "method_id": "STRUCTURE-ONLY-NO-SOLUTION",
            "decisions": [{
                "detection_id": "METHOD-OWNED-1",
                "kind": "CLAIM",
                "state": "UNKNOWN",
                "claim_key": claim["claim_key"],
                "subject": claim["subject"],
                "evidence_refs": [],
            }],
            "projection_updates": [],
            "execution_proofs": [],
            "relation_handoffs": [],
        }
        structural = validate_submission_structure(submission)
        self.assertEqual([], structural)
        self.assertEqual("FAIL", evaluate(submission, self.oracle)["status"])

    def test_14_secret_interface_fields_are_rejected(self) -> None:
        invalid = json.loads(json.dumps(self.fixture))
        invalid["decisions"][0]["truth_id"] = "forbidden"
        codes = {
            row["code"] for row in validate_submission_structure(invalid)
        }
        self.assertIn("FIELDS_FORBIDDEN", codes)
        self.assertIn("ORACLE_INTERFACE_FIELD_FORBIDDEN", codes)

    def test_15_score_does_not_expose_oracle_ids(self) -> None:
        incomplete = {
            **self.fixture,
            "method_id": "EMPTY",
            "decisions": [],
            "projection_updates": [],
            "execution_proofs": [],
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
        self.assertNotIn('"expected_state"', output)

    def test_16_builder_matches_frozen_delivery_packets(self) -> None:
        packets = build_packets(self.source)
        with tempfile.TemporaryDirectory() as temp_dir:
            index = write_packets(packets, Path(temp_dir))
            for entry in index["packets"]:
                generated = Path(temp_dir) / entry["path"]
                frozen = ROOT / "delivery-packets" / entry["path"]
                self.assertEqual(generated.read_bytes(), frozen.read_bytes())
                self.assertEqual(
                    hashlib.sha256(canonical_bytes(packets[entry["path"]])).hexdigest(),
                    entry["sha256"],
                )

    def test_17_world_is_not_hwb_entity_or_fact_renaming(self) -> None:
        source_text = json.dumps(self.source, ensure_ascii=False, sort_keys=True)
        for old_marker in (
            "AURORA-17",
            "HELIOS-44",
            "ION-06",
            "JUNIPER-28",
            "cold-chain-gap-audit",
            "microgrid-anomaly-replay",
            "sterile-route-simulation",
        ):
            self.assertNotIn(old_marker, source_text)
        self.assertIn("canopy-echo-comparison", source_text)
        self.assertIn("tidal-sensor-replay", source_text)

    def test_18_no_candidate_was_generated(self) -> None:
        self.assertEqual([], list(ROOT.glob("candidate*.json")))
        self.assertEqual(
            "MANUAL-HWC-ORACLE-CALIBRATION-NOT-A-CANDIDATE",
            self.fixture["method_id"],
        )

    def test_19_manifest_hashes_and_packet_closure(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        self.assertFalse(manifest["claims"]["candidate_generated"])
        for artifact in manifest["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertEqual(
                artifact["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
                artifact["path"],
            )
        index = load_json(
            ROOT / manifest["packet_closure"]["index_path"]
        )
        self.assertEqual(12, index["packet_count"])
        for entry in index["packets"]:
            path = ROOT / "delivery-packets" / entry["path"]
            self.assertEqual(
                entry["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
                entry["path"],
            )


if __name__ == "__main__":
    unittest.main()
