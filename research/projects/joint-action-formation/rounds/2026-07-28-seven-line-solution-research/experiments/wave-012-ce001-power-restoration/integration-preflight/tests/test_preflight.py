from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ce001_preflight", ROOT / "preflight.py")
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


class IntegrationPreflightTests(unittest.TestCase):
    def load(self, name: str):
        return PREFLIGHT.load_envelope(ROOT / "fixtures" / name)

    def assert_rejection(self, name: str, expected_code: str):
        report = PREFLIGHT.validate_envelope(self.load(name))
        codes = {item["code"] for item in report["rejections"]}
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertIn(expected_code, codes)
        self.assertEqual(
            "CONTRACT_SCORE_NOT_COMPUTED", report["contract_score_status"]
        )

    def test_qualified_e1_passes_without_contract_score(self):
        report = PREFLIGHT.validate_envelope(self.load("qualified-e1.json"))
        self.assertEqual("QUALIFIED_COMPONENT_OUTPUTS", report["preflight_status"])
        self.assertEqual([], report["rejections"])
        self.assertEqual(list(PREFLIGHT.EXPECTED_COMPONENTS), report["qualified_components"])
        self.assertEqual(
            "CONTRACT_SCORE_NOT_COMPUTED", report["contract_score_status"]
        )
        serialized = json.dumps(report)
        self.assertNotIn('"ExactTaskSuccess"', serialized)
        self.assertNotIn('"CorrectResolution"', serialized)
        self.assertNotIn('"RecoveryToValue"', serialized)

    def test_qualified_e6_requires_and_accepts_complete_migration_envelope(self):
        report = PREFLIGHT.validate_envelope(self.load("qualified-e6.json"))
        self.assertEqual("QUALIFIED_COMPONENT_OUTPUTS", report["preflight_status"])
        self.assertEqual([], report["rejections"])
        self.assertEqual(
            "CONTRACT_SCORE_NOT_COMPUTED", report["contract_score_status"]
        )

    def test_contract_field_passthrough_is_rejected(self):
        self.assert_rejection(
            "negative-contract-passthrough.json", "CONTRACT_FIELD_PASSTHROUGH"
        )

    def test_component_from_another_episode_is_rejected(self):
        envelope = self.load("qualified-e1.json")
        envelope["components"]["G3"]["binding"]["episode_id"] = (
            "ce001-foreign-synthetic"
        )
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertIn("COMPONENT_BINDING_MISMATCH", codes)

    def test_unknown_case_id_is_rejected(self):
        envelope = self.load("qualified-e1.json")
        envelope["episode"]["case_id"] = "E9-NOT-A-FROZEN-CASE"
        for component in envelope["components"].values():
            component["binding"]["case_id"] = "E9-NOT-A-FROZEN-CASE"
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertIn("UNKNOWN_CASE_ID", codes)

    def test_e5_success_shape_fails_closed_until_refusal_branch_exists(self):
        envelope = self.load("qualified-e1.json")
        envelope["episode"]["case_id"] = "E5-IMPOSSIBLE-REFUSAL"
        for component in envelope["components"].values():
            component["binding"]["case_id"] = "E5-IMPOSSIBLE-REFUSAL"
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertIn("CASE_ADMISSION_NOT_IMPLEMENTED", codes)

    def test_g4_y_prefixed_contract_field_passthrough_is_rejected(self):
        envelope = self.load("qualified-e1.json")
        envelope["components"]["G4"]["evidence"]["Y_effect"] = True
        envelope["components"]["G4"]["evidence"]["Y_acceptance"] = True
        report = PREFLIGHT.validate_envelope(envelope)
        rejected_paths = {
            item["path"]
            for item in report["rejections"]
            if item["code"] == "CONTRACT_FIELD_PASSTHROUGH"
        }
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertIn("$.components.G4.evidence.Y_effect", rejected_paths)
        self.assertIn("$.components.G4.evidence.Y_acceptance", rejected_paths)
        self.assertEqual(
            "CONTRACT_SCORE_NOT_COMPUTED", report["contract_score_status"]
        )

    def test_contract_prefixed_alias_is_rejected(self):
        envelope = self.load("qualified-e1.json")
        envelope["components"]["G6"]["evidence"][
            "contract_exact_task_success"
        ] = "NOT_COMPUTED_BY_G6"
        report = PREFLIGHT.validate_envelope(envelope)
        rejected = {
            item["path"]: item["code"] for item in report["rejections"]
        }
        self.assertEqual("REJECTED", report["preflight_status"])
        self.assertEqual(
            "CONTRACT_FIELD_PASSTHROUGH",
            rejected[
                "$.components.G6.evidence.contract_exact_task_success"
            ],
        )

    def test_simulated_multi_owner_is_rejected(self):
        self.assert_rejection(
            "negative-simulated-multi-owner.json", "SIMULATED_MULTI_OWNER"
        )

    def test_duplicate_acceptance_owner_is_rejected(self):
        self.assert_rejection(
            "negative-duplicate-acceptance.json", "DUPLICATE_ACCEPTANCE_OWNER"
        )

    def test_missing_target_consumed_authority_is_rejected(self):
        self.assert_rejection(
            "negative-authority-not-consumed.json",
            "TARGET_CONSUMED_AUTHORITY_MISSING",
        )

    def test_non_exact_effect_binding_is_rejected(self):
        self.assert_rejection(
            "negative-effect-binding.json", "EVIDENCE_BINDING_MISMATCH"
        )

    def test_changing_episode_and_effect_to_same_wrong_target_still_rejects_ce001_binding(self):
        envelope = self.load("qualified-e1.json")
        envelope["episode"]["object_id"] = "VenueV:CircuitC8"
        envelope["episode"]["target_id"] = "VenueV:CircuitC8"
        for component in envelope["components"].values():
            PREFLIGHT._replace_key_recursively(
                component, "object_id", "VenueV:CircuitC8"
            )
            PREFLIGHT._replace_key_recursively(
                component, "target_id", "VenueV:CircuitC8"
            )
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertIn("CE001_EPISODE_BINDING_MISMATCH", codes)

    def test_non_independent_op_is_rejected(self):
        self.assert_rejection("negative-op-not-independent.json", "OP_NOT_INDEPENDENT")

    def test_e6_without_runtime_and_old_epoch_evidence_is_rejected(self):
        self.assert_rejection(
            "negative-e6-migration-missing.json", "E6_RUNTIME_BOUNDARY_MISSING"
        )

    def test_e6_without_old_epoch_rejection_is_rejected(self):
        envelope = self.load("qualified-e6.json")
        restart = envelope["components"]["G7"]["evidence"]["migration"][
            "old_runtime_restart"
        ]
        restart["actually_restarted"] = False
        restart["fence_result"] = "NOT_OBSERVED"
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertIn("E6_OLD_EPOCH_EVIDENCE_MISSING", codes)

    def test_e6_same_source_target_process_is_rejected(self):
        envelope = self.load("qualified-e6.json")
        migration = envelope["components"]["G7"]["evidence"]["migration"]
        migration["target_runtime"]["process_id"] = migration["source_runtime"][
            "process_id"
        ]
        report = PREFLIGHT.validate_envelope(envelope)
        codes = {item["code"] for item in report["rejections"]}
        self.assertIn("E6_RUNTIME_BOUNDARY_NOT_DISTINCT", codes)


if __name__ == "__main__":
    unittest.main()
