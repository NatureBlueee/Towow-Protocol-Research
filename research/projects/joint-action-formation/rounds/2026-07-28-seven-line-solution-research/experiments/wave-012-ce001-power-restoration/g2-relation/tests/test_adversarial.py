from __future__ import annotations

import base64
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2_relation import (  # noqa: E402
    ReceiptVerificationError,
    run_scenario,
    verify_receipt,
)


BASE = json.loads((ROOT / "fixtures" / "e2.json").read_text(encoding="utf-8"))[0]
PLATFORM = json.loads((ROOT / "fixtures" / "e0.json").read_text(encoding="utf-8"))[0]


def e2(profile_case: str = "EXACT_V1", **overrides):
    config = deepcopy(BASE)
    config["episode_id"] = f"CE001-E2-ADV-{profile_case}"
    config["profile_case"] = profile_case
    config.update(overrides)
    return config


class G2AdversarialTests(unittest.TestCase):
    def test_controller_visible_profiles_are_rejected(self):
        config = e2(owner_profiles={"O_Q": {"support": True}})
        with self.assertRaisesRegex(ValueError, "owner_profiles"):
            run_scenario(config)

    def test_missing_owner_policy_stays_unknown(self):
        output = run_scenario(e2("MISSING_ALL"))
        for axis in ("constituted", "understood", "claimed", "authorized", "activated"):
            states = output["axis_evidence"][axis]["owner_states"]
            self.assertTrue(all(state.startswith("UNKNOWN") for state in states.values()))

    def test_blocking_opposition_survives_and_stops_owner_downstream(self):
        output = run_scenario(e2("BLOCKING_OPPOSITION"))
        self.assertEqual(
            output["axis_evidence"]["claimed"]["owner_states"]["O_V"],
            "BLOCKING_OPPOSITION",
        )
        self.assertTrue(output["axis_evidence"]["claimed"]["opposing_act_ids"])
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_wrong_q_signed_receipt_is_rejected_and_cannot_flow_downstream(self):
        output = run_scenario(e2("WRONG_Q"))
        rejected = [item for item in output["rejected_receipts"] if item["owner_id"] == "O_V"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("exact binding mismatch: q", rejected[0]["reason"])
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_wrong_object_signed_receipt_is_rejected_and_cannot_flow_downstream(self):
        output = run_scenario(e2("WRONG_OBJECT"))
        rejected = [item for item in output["rejected_receipts"] if item["owner_id"] == "O_V"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("exact binding mismatch: object_id", rejected[0]["reason"])

    def test_wrong_relation_version_is_rejected_not_digest_filtered(self):
        output = run_scenario(e2("WRONG_VERSION", version="v2"))
        rejected = [item for item in output["rejected_receipts"] if item["owner_id"] == "O_R"]
        self.assertEqual(len(rejected), 1)
        self.assertIn("exact binding mismatch: relation_version_hash", rejected[0]["reason"])
        self.assertEqual(
            output["axis_evidence"]["understood"]["owner_states"]["O_R"],
            "UNKNOWN_NO_VERIFIED_EXACT_BOUND_OWNER_ACT",
        )

    def test_forged_act_hash_fails_closed_even_when_display_preimage_is_unchanged(self):
        output = run_scenario(e2())
        receipt = deepcopy(output["owner_acts"][0])
        manifest = next(
            item for item in output["process_manifests"] if item["owner_id"] == receipt["preimage"]["owner_id"]
        )
        receipt["act_hash"] = "0" * 64
        with self.assertRaisesRegex(ReceiptVerificationError, "hash mismatch"):
            verify_receipt(receipt, manifest, {})

    def test_tampered_raw_bytes_or_signature_fail_closed(self):
        output = run_scenario(e2())
        original = output["owner_acts"][0]
        manifest = next(
            item for item in output["process_manifests"] if item["owner_id"] == original["preimage"]["owner_id"]
        )
        bad_raw = deepcopy(original)
        raw = bytearray(base64.b64decode(bad_raw["raw_bytes_b64"]))
        raw[-2] ^= 1
        bad_raw["raw_bytes_b64"] = base64.b64encode(bytes(raw)).decode()
        with self.assertRaises(ReceiptVerificationError):
            verify_receipt(bad_raw, manifest, {})
        bad_sig = deepcopy(original)
        sig = bytearray(base64.b64decode(bad_sig["signature_b64"]))
        sig[0] ^= 1
        bad_sig["signature_b64"] = base64.b64encode(bytes(sig)).decode()
        with self.assertRaisesRegex(ReceiptVerificationError, "signature"):
            verify_receipt(bad_sig, manifest, {})

    def test_q_hash_in_config_must_match_exact_q_bytes(self):
        config = e2(
            q={
                "id": "CE001-Q",
                "version": "Q@v1",
                "statement": "forged statement",
                "hash": "copied-old-hash",
            }
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "Q hash"):
            run_scenario(config)

    def test_platform_bypass_rejects_bare_boolean(self):
        config = deepcopy(PLATFORM)
        config["platform_direct_applicable"] = True
        with self.assertRaisesRegex(ValueError, "bare"):
            run_scenario(config)

    def test_platform_bypass_requires_signed_applicable_proof(self):
        config = deepcopy(PLATFORM)
        config["platform_profile_case"] = "MISSING_PROOF"
        with self.assertRaisesRegex(ReceiptVerificationError, "not applicable"):
            run_scenario(config)

    def test_platform_bypass_rejects_wrong_object_readback(self):
        config = deepcopy(PLATFORM)
        config["platform_profile_case"] = "WRONG_READBACK_OBJECT"
        with self.assertRaisesRegex(ReceiptVerificationError, "object_id"):
            run_scenario(config)

    def test_platform_proof_and_readback_are_independently_signed_and_no_effect(self):
        output = run_scenario(deepcopy(PLATFORM))
        proof = output["bypass_evidence"]["capability_proof"]
        readback = output["bypass_evidence"]["capability_readback"]
        self.assertNotEqual(proof["act_hash"], readback["act_hash"])
        self.assertEqual(proof["preimage"]["decision"], "APPLICABLE")
        self.assertEqual(readback["preimage"]["decision"], "READBACK_CONFIRMED")
        self.assertFalse(proof["preimage"]["payload"]["effect_asserted"])
        self.assertFalse(readback["preimage"]["payload"]["effect_asserted"])
        self.assertEqual(output["bypass_evidence"]["effect"], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
