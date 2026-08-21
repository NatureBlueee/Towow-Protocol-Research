from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIM_ROOT = ROOT.parent / "wave-003-b-t2-bounded-probe-simulator"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SIM_ROOT))

from bridge import classify  # noqa: E402
from simulator import load_json, simulate  # noqa: E402


class ProbeToRelationBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.probe_input = load_json(SIM_ROOT / "probe_input.json")
        cls.truth = load_json(SIM_ROOT / "scenario_truth.json")

    def run_branch(self, scenario: str) -> dict:
        return classify(simulate(self.probe_input, self.truth, scenario))

    def test_manifest_hashes_match_frozen_artifacts(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for artifact in manifest["artifacts"]:
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(artifact["sha256"], digest, artifact["path"])

    def test_success_only_qualifies_exact_synthetic_probe(self) -> None:
        result = self.run_branch("success")
        qualification = result["operation_qualification"]
        self.assertTrue(qualification["qualifies_exact_frozen_probe"])
        self.assertFalse(qualification["qualifies_formal_pilot"])
        self.assertEqual("NOT_ESTABLISHED", result["outcomes"]["effect"])
        self.assertTrue(
            result["relation_transition"]["may_request_post_probe_stances"]
        )
        self.assertFalse(result["relation_transition"]["commitment_created"])

    def test_environment_mismatch_reopens_binding(self) -> None:
        result = self.run_branch("environment_mismatch")
        self.assertEqual(
            "BLOCKED_BEFORE_OPERATION",
            result["operation_qualification"]["state"]
        )
        self.assertEqual(
            "SCOPED_REOPEN_ENVIRONMENT_BINDING",
            result["relation_transition"]["next_action"]
        )

    def test_revocation_stops_and_requires_new_authorization(self) -> None:
        result = self.run_branch("credential_revoked_mid_run")
        self.assertEqual(
            "NOT_QUALIFIED_CREDENTIAL_REVOKED",
            result["operation_qualification"]["state"]
        )
        self.assertEqual(
            "STOP_AND_REQUEST_NEW_DATA_AUTHORIZATION",
            result["relation_transition"]["next_action"]
        )

    def test_missing_witness_does_not_qualify_reliance(self) -> None:
        result = self.run_branch("audit_witness_missing")
        self.assertEqual(
            "PRODUCER_COMPLETED_BUYER_WITNESS_MISSING",
            result["operation_qualification"]["state"]
        )
        self.assertFalse(
            result["operation_qualification"]["qualifies_exact_frozen_probe"]
        )
        self.assertEqual("NOT_ESTABLISHED", result["outcomes"]["effect"])

    def test_duplicate_retry_creates_no_new_evidence(self) -> None:
        result = self.run_branch("duplicate_retry")
        self.assertEqual(
            "NO_NEW_EVIDENCE_PRIOR_RECEIPT_ONLY",
            result["operation_qualification"]["state"]
        )
        self.assertFalse(
            result["relation_transition"]["may_request_post_probe_stances"]
        )


if __name__ == "__main__":
    unittest.main()
