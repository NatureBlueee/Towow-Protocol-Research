from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import evaluator  # noqa: E402


class CollapseSafeEvaluatorTests(unittest.TestCase):
    def load(self, name: str) -> dict:
        return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))

    def test_manifest_hashes_match_frozen_artifacts(self) -> None:
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for artifact in manifest["artifacts"]:
            digest = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
            self.assertEqual(artifact["sha256"], digest, artifact["path"])

    def test_direct_platform_path_passes_real_state_machine(self) -> None:
        result = evaluator.evaluate(self.load("platform-direct.json"))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["coverage"]["requirements_passed"], 6)
        self.assertEqual(6, len(result["success_receipts"]))

    def test_stateless_non_authoritative_adapter_also_passes(self) -> None:
        result = evaluator.evaluate(self.load("stateless-adapter.json"))
        self.assertEqual(result["status"], "PASS")

    def test_zero_action_label_only_candidate_is_invalid(self) -> None:
        candidate = self.load("overengineered.json")
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["status"], "INVALID")
        self.assertEqual(result["coverage"]["requirements_passed"], 0)

    def test_packed_or_unknown_operation_is_invalid(self) -> None:
        candidate = self.load("platform-direct.json")
        candidate["operations"][0]["op"] = "DO_EVERYTHING"
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["status"], "INVALID")

    def test_field_alias_leakage_fails_exact_disclosure(self) -> None:
        candidate = self.load("platform-direct.json")
        candidate["disclosures"][0]["fields"].append("credential_secret")
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["requirement_results"]["R3"]["status"], "FAIL")

    def test_r3_reconstructs_disclosure_from_adapter_trace(self) -> None:
        candidate = self.load("stateless-adapter.json")
        execution = evaluator.execute_method(candidate)
        reconstructed = evaluator.disclosures_from_trace(execution)
        self.assertEqual(
            sorted(item["recipient"] for item in candidate["disclosures"]),
            sorted(item["recipient"] for item in reconstructed),
        )
        self.assertTrue(evaluator.exact_disclosures(reconstructed))

    def test_unbound_adapter_artifact_fails_r2_r4_r6(self) -> None:
        candidate = self.load("stateless-adapter.json")
        candidate["adapter"]["artifact_sha256"] = "0" * 64
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["requirement_results"]["R2"]["status"], "FAIL")
        self.assertEqual(result["requirement_results"]["R4"]["status"], "FAIL")
        self.assertEqual(result["requirement_results"]["R6"]["status"], "FAIL")

    def test_adapter_name_is_not_used_as_behavior_evidence(self) -> None:
        candidate = self.load("stateless-adapter.json")
        candidate["adapter"]["id"] = (
            "STATEFUL-AUTHORITATIVE-SHADOW-LEDGER-LEAKS-PII-AND-RETRIES"
        )
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(
            result["adapter_execution"]["program_hash"],
            candidate["adapter"]["artifact_sha256"],
        )

    def test_missing_failure_state_is_invalid(self) -> None:
        candidate = self.load("platform-direct.json")
        del candidate["failure_handling"]["PAYMENT_FAILED"]
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["status"], "INVALID")

    def test_wrong_price_cannot_reach_success_postcondition(self) -> None:
        candidate = self.load("platform-direct.json")
        candidate["operations"][3]["inputs"]["amount_cny"] = 1
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["requirement_results"]["R1"]["status"], "FAIL")
        self.assertEqual(result["requirement_results"]["R5"]["status"], "FAIL")

    def test_wrong_authority_cannot_execute_order(self) -> None:
        candidate = self.load("platform-direct.json")
        candidate["operations"][2]["authority_source"] = "MODEL"
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["requirement_results"]["R1"]["status"], "FAIL")
        self.assertEqual(result["requirement_results"]["R2"]["status"], "FAIL")

    def test_every_failure_branch_has_authoritative_terminal(self) -> None:
        result = evaluator.evaluate(self.load("platform-direct.json"))
        self.assertEqual(
            {
                "ORDER_REJECTED": "ORDER_REJECTED",
                "PAYMENT_FAILED": "PAYMENT_FAILED",
                "PROVISIONING_FAILED": "PROVISIONING_FAILED",
                "CANCELLED": "CANCELLED",
            },
            result["failure_terminals"],
        )
        for trace in result["failure_handler_traces"].values():
            self.assertTrue(trace["executed"])
            self.assertTrue(trace["no_retry"])
            self.assertEqual(trace["side_effects_after_terminal"], 0)

    def test_invalid_predecessor_cannot_masquerade_as_injected_failure(self) -> None:
        candidate = self.load("platform-direct.json")
        candidate["operations"][2]["inputs"]["seat_count"] = 999
        result = evaluator.evaluate(candidate)
        self.assertEqual(result["failure_terminals"]["PAYMENT_FAILED"], "INVALID_OPERATION")
        self.assertEqual(result["requirement_results"]["R5"]["status"], "FAIL")

    def test_mutating_order_is_detected(self) -> None:
        candidate = self.load("platform-direct.json")
        mutated = copy.deepcopy(candidate)
        mutated["operations"][0], mutated["operations"][1] = (
            mutated["operations"][1],
            mutated["operations"][0],
        )
        result = evaluator.evaluate(mutated)
        self.assertEqual(result["requirement_results"]["R1"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
