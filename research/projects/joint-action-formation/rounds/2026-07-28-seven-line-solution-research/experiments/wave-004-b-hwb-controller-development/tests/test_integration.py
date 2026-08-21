from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import adapter  # noqa: E402
import export_candidate_controller  # noqa: E402


class HWBControllerIntegrationTests(unittest.TestCase):
    def test_frozen_source_hashes_match_exact_bytes(self) -> None:
        for party, path in adapter.SOURCE_FILES.items():
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, adapter.FROZEN_SOURCE_SHA256[party])

    def test_normalization_binds_source_hashes(self) -> None:
        contract, requests = adapter.build_contract()
        trusted = {
            item["issuer"]: item for item in contract["trusted_holder_receipts"]
        }
        for request in requests.values():
            for envelope in request["authorizations"]:
                payload = envelope["payload"]
                party = payload["issuer"]
                self.assertEqual(
                    payload["source_file_sha256"],
                    adapter.FROZEN_SOURCE_SHA256[party],
                )
                self.assertEqual(
                    envelope["declared_sha256"],
                    adapter.EXECUTOR.sha256_value(payload),
                )
                self.assertEqual(
                    trusted[party]["source_file_sha256"],
                    payload["source_file_sha256"],
                )

    def test_direct_and_derived_execute_in_same_state(self) -> None:
        contract, requests = adapter.build_contract()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            direct = adapter.EXECUTOR.execute_persisted(
                contract, requests["direct"], state_path
            )
            derived = adapter.EXECUTOR.execute_persisted(
                contract, requests["derived"], state_path
            )
            self.assertEqual(direct["outcome"]["status"], "EXECUTED")
            self.assertEqual(
                direct["outcome"]["disclosures"][0]["to"],
                "NODE-COPPER-ROUTER",
            )
            self.assertEqual(derived["outcome"]["status"], "EXECUTED")
            disclosures = derived["outcome"]["disclosures"]
            self.assertEqual(
                [(item["from"], item["to"], item["depth"]) for item in disclosures],
                [
                    ("ION-06", "NODE-SILVER-RELAY", 0),
                    ("NODE-SILVER-RELAY", "NODE-COPPER-ROUTER", 1),
                ],
            )
            self.assertEqual(len(derived["outcome"]["derived_authorizations"]), 1)
            self.assertEqual(
                disclosures[1]["derived_authorization_sha256"],
                derived["outcome"]["derived_authorizations"][0][
                    "receipt_sha256"
                ],
            )
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(len(state["events"]), 2)
            self.assertEqual(len(state["delivery_store"]), 2)

    def test_reciprocal_counterparty_exchange_executes_to_each_party(self) -> None:
        contract, requests = adapter.build_contract()
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "state.json"
            adapter.EXECUTOR.execute_persisted(
                contract, requests["direct"], state_path
            )
            result = adapter.EXECUTOR.execute_persisted(
                contract, requests["reciprocal"], state_path
            )
            self.assertEqual(result["outcome"]["status"], "EXECUTED")
            self.assertEqual(
                result["outcome"]["reciprocal_exchange"]["delivery_mode"],
                "COUNTERPARTY_EXCHANGE",
            )
            self.assertTrue(result["state_changed"])
            policies = [
                envelope["payload"]["policy"]["recipient"]
                for envelope in requests["reciprocal"]["authorizations"]
            ]
            self.assertEqual(policies, ["KITE-15", "JUNIPER-28"])
            self.assertEqual(
                [
                    (item["from"], item["to"])
                    for item in result["outcome"]["disclosures"]
                ],
                [
                    ("JUNIPER-28", "KITE-15"),
                    ("KITE-15", "JUNIPER-28"),
                ],
            )

    def test_candidate_exports_derive_from_verified_outputs(self) -> None:
        exports = export_candidate_controller.build_exports()
        self.assertEqual(
            set(exports),
            {
                "route-helios-direct.json",
                "route-ion-relay.json",
                "reciprocal-juniper-kite.json",
            },
        )
        reciprocal = exports["reciprocal-juniper-kite.json"]
        visible = reciprocal["coordinator_visible"]
        self.assertEqual(
            [
                (item["sender"], item["recipient"])
                for item in visible["disclosures"]
            ],
            [
                ("JUNIPER-28", "KITE-15"),
                ("KITE-15", "JUNIPER-28"),
            ],
        )
        self.assertEqual(
            visible["probe"]["status"],
            "COMPLETED_RECIPROCAL_RECEIPT",
        )
        for record in exports.values():
            self.assertEqual(
                record["development_label"],
                "DEVELOPMENT_POST_FEEDBACK_NOT_BLIND",
            )
            self.assertEqual(
                record["controller_result"]["outcome"]["status"],
                "EXECUTED",
            )


if __name__ == "__main__":
    unittest.main()
