import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import executor  # noqa: E402


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class ControllerExecutorTests(unittest.TestCase):
    def setUp(self):
        self.contract = load("contract.json")
        self.direct = load("inputs/direct-projection.json")
        self.onward = load("inputs/derived-onward.json")
        self.reciprocal = load("inputs/reciprocal-exchange.json")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.state_path = Path(self.temporary.name) / "state.json"

    def run_request(self, request):
        return executor.execute_persisted(
            self.contract, request, self.state_path
        )

    def assert_rejected(self, request, code):
        existed_before = self.state_path.exists()
        bytes_before = self.state_path.read_bytes() if existed_before else None
        result = self.run_request(request)
        self.assertEqual("REJECTED", result["outcome"]["status"])
        self.assertEqual(code, result["outcome"]["code"])
        self.assertFalse(result["state_changed"])
        self.assertIsNone(result["execution_receipt"])
        self.assertEqual(existed_before, self.state_path.exists())
        if existed_before:
            self.assertEqual(bytes_before, self.state_path.read_bytes())
        return result

    def assert_success_evidence(
        self,
        result,
        expected_deliveries,
        contract=None,
    ):
        contract = self.contract if contract is None else contract
        self.assertEqual("EXECUTED", result["outcome"]["status"])
        receipt = result["execution_receipt"]
        evidence = result["outcome"]["authority_evidence"]
        self.assertEqual(
            evidence["recipient_delivery_event_sha256"],
            receipt["authoritative_event_sha256"],
        )
        self.assertEqual(
            evidence["authoritative_state_root"],
            receipt["authoritative_state_root"],
        )
        self.assertEqual(
            evidence["readback_sha256"], receipt["readback_sha256"]
        )
        self.assertEqual(
            expected_deliveries,
            evidence["readback"]["delivery_count"],
        )
        receipt_body = {
            key: value
            for key, value in receipt.items()
            if key != "receipt_sha256"
        }
        self.assertEqual(
            executor.sha256_value(receipt_body), receipt["receipt_sha256"]
        )
        self.assertEqual(
            executor.sha256_value(result["outcome"]),
            receipt["output_sha256"],
        )
        self.assertEqual(
            executor.sha256_value(contract), receipt["contract_sha256"]
        )

    def test_direct_projection_commits_then_reads_back_then_issues_receipt(self):
        snapshots = []
        real_save = executor.save_state_atomic

        def capture(path, state):
            snapshots.append(copy.deepcopy(state))
            real_save(path, state)

        with mock.patch.object(executor, "save_state_atomic", side_effect=capture):
            result = self.run_request(self.direct)

        self.assert_success_evidence(result, 1)
        self.assertGreaterEqual(len(snapshots), 2)
        first, final = snapshots[0], snapshots[-1]
        self.assertEqual(1, len(first["delivery_store"]))
        self.assertEqual(1, len(first["pending_transactions"]))
        self.assertEqual(0, len(first["events"]))
        self.assertEqual(1, len(final["delivery_store"]))
        self.assertEqual(0, len(final["pending_transactions"]))
        self.assertEqual(1, len(final["events"]))
        self.assertEqual(
            1, len(final["recipient_stores"]["COORDINATOR-A"])
        )

    def test_derived_onward_is_one_atomic_two_delivery_transaction(self):
        result = self.run_request(self.onward)
        self.assert_success_evidence(result, 2)
        self.assertEqual(
            1, len(result["outcome"]["derived_authorizations"])
        )
        state = executor.load_json(self.state_path)
        transaction = state["delivery_store"][0]
        self.assertTrue(transaction["atomic"])
        self.assertEqual(2, len(transaction["deliveries"]))
        self.assertEqual(
            transaction["derived_authorizations"][0]["receipt_sha256"],
            transaction["deliveries"][1][
                "derived_authorization_sha256"
            ],
        )

    def test_reciprocal_exchange_is_all_or_nothing(self):
        result = self.run_request(self.reciprocal)
        self.assert_success_evidence(result, 2)
        state = executor.load_json(self.state_path)
        transaction = state["delivery_store"][0]
        self.assertTrue(transaction["atomic"])
        self.assertEqual(2, len(transaction["deliveries"]))
        self.assertEqual(
            "PERFORMED", transaction["reciprocal_exchange"]["status"]
        )
        self.assertEqual(
            "NOT_ESTABLISHED", result["outcome"]["relation_status"]
        )
        self.assertEqual(
            "CENTRAL_RECIPROCAL_PROJECTION_COLLECTION",
            transaction["reciprocal_exchange"]["scope"],
        )
        self.assertEqual(
            {"RECIPROCAL-CONTROLLER"},
            set(state["recipient_stores"]),
        )

    def test_reciprocal_counterparty_exchange_reads_back_both_parties(self):
        contract = copy.deepcopy(self.contract)
        request = copy.deepcopy(self.reciprocal)
        request["route"]["delivery_mode"] = "COUNTERPARTY_EXCHANGE"
        holders = [
            envelope["payload"] for envelope in request["authorizations"]
        ]
        for index, (side, holder) in enumerate(
            zip(request["route"]["sides"], holders)
        ):
            other = holders[1 - index]
            holder["policy"]["recipient"] = other["issuer"]
            side["delivery"] = {
                "recipient": other["issuer"],
                "purpose": holder["policy"]["purpose"],
                "retention": holder["policy"]["retention"],
                "depth": 0,
            }
            digest = executor.sha256_value(holder)
            request["authorizations"][index]["declared_sha256"] = digest
            trusted = next(
                item
                for item in contract["trusted_holder_receipts"]
                if item["receipt_id"] == holder["receipt_id"]
            )
            trusted["sha256"] = digest

        result = executor.execute_persisted(
            contract, request, self.state_path
        )
        self.assert_success_evidence(result, 2, contract)
        state = executor.load_json(self.state_path)
        self.assertEqual(
            {"HOLDER-GAMMA", "HOLDER-DELTA"},
            set(state["recipient_stores"]),
        )
        self.assertEqual(
            {
                ("HOLDER-GAMMA", "HOLDER-DELTA"),
                ("HOLDER-DELTA", "HOLDER-GAMMA"),
            },
            {
                (item["from"], item["to"])
                for item in result["outcome"]["disclosures"]
            },
        )
        self.assertEqual(
            "RECIPROCAL_COUNTERPARTY_PROJECTION_EXCHANGE",
            result["outcome"]["reciprocal_exchange"]["scope"],
        )

    def test_success_receipt_binds_holder_envelopes_and_policy(self):
        result = self.run_request(self.direct)
        receipt = result["execution_receipt"]
        authorization_hash, policy_hash = executor._authorization_bindings(
            self.direct
        )
        self.assertEqual(
            authorization_hash,
            receipt["trusted_holder_envelopes_sha256"],
        )
        self.assertEqual(policy_hash, receipt["policy_snapshot_sha256"])

    def test_exact_duplicate_returns_same_receipt_event_root_without_write(self):
        first = self.run_request(self.direct)
        state_before = self.state_path.read_bytes()
        second = self.run_request(self.direct)
        state_after = self.state_path.read_bytes()
        self.assertEqual("IDEMPOTENT_REPLAY", second["replay"])
        self.assertFalse(second["state_changed"])
        self.assertEqual(first["outcome"], second["outcome"])
        self.assertEqual(
            first["execution_receipt"], second["execution_receipt"]
        )
        self.assertEqual(state_before, state_after)
        state = executor.load_json(self.state_path)
        self.assertEqual(1, len(state["delivery_store"]))
        self.assertEqual(1, len(state["events"]))

    def test_exact_replay_rejects_changed_contract(self):
        self.run_request(self.direct)
        state_before = self.state_path.read_bytes()
        changed_contract = copy.deepcopy(self.contract)
        changed_contract["max_disclosure_units"] += 1
        result = executor.execute_persisted(
            changed_contract, self.direct, self.state_path
        )
        self.assertEqual(
            "CONTRACT_STATE_MISMATCH", result["outcome"]["code"]
        )
        self.assertFalse(result["state_changed"])
        self.assertEqual(state_before, self.state_path.read_bytes())

    def test_exact_replay_rejects_tampered_audit_event(self):
        self.run_request(self.direct)
        state = executor.load_json(self.state_path)
        state["events"][0]["outcome"]["relation_status"] = "ESTABLISHED"
        executor.save_state_atomic(self.state_path, state)
        tampered_state = self.state_path.read_bytes()
        result = self.run_request(self.direct)
        self.assertEqual(
            "AUDIT_CHAIN_INTEGRITY_INVALID", result["outcome"]["code"]
        )
        self.assertFalse(result["state_changed"])
        self.assertEqual(tampered_state, self.state_path.read_bytes())

    def test_exact_replay_rejects_missing_recipient_store(self):
        self.run_request(self.direct)
        state = executor.load_json(self.state_path)
        state["recipient_stores"] = {}
        executor.save_state_atomic(self.state_path, state)
        tampered_state = self.state_path.read_bytes()
        result = self.run_request(self.direct)
        self.assertEqual(
            "RECIPIENT_STORE_INTEGRITY_INVALID",
            result["outcome"]["code"],
        )
        self.assertFalse(result["state_changed"])
        self.assertEqual(tampered_state, self.state_path.read_bytes())

    def test_pending_recovery_rejects_changed_contract(self):
        with mock.patch.object(
            executor,
            "_finalize_pending",
            side_effect=RuntimeError("injected crash before receipt"),
        ):
            with self.assertRaisesRegex(RuntimeError, "injected crash"):
                self.run_request(self.direct)
        pending_state = self.state_path.read_bytes()
        changed_contract = copy.deepcopy(self.contract)
        changed_contract["max_disclosure_units"] += 1
        result = executor.execute_persisted(
            changed_contract, self.direct, self.state_path
        )
        self.assertEqual(
            "CONTRACT_STATE_MISMATCH", result["outcome"]["code"]
        )
        self.assertFalse(result["state_changed"])
        self.assertEqual(pending_state, self.state_path.read_bytes())

    def test_duplicate_key_with_changed_request_is_conflict(self):
        self.run_request(self.direct)
        state_before = self.state_path.read_bytes()
        changed = copy.deepcopy(self.direct)
        changed["route"]["purpose"] = "different-purpose"
        result = self.run_request(changed)
        self.assertEqual("IDEMPOTENCY_CONFLICT", result["outcome"]["code"])
        self.assertFalse(result["state_changed"])
        self.assertEqual(state_before, self.state_path.read_bytes())
        state = executor.load_json(self.state_path)
        self.assertEqual(1, len(state["delivery_store"]))
        self.assertEqual(1, len(state["events"]))

    def test_hash_mismatch_branch(self):
        request = copy.deepcopy(self.direct)
        request["authorizations"][0]["declared_sha256"] = "0" * 64
        self.assert_rejected(request, "HOLDER_RECEIPT_HASH_MISMATCH")

    def test_missing_idempotency_key_is_zero_state_rejection(self):
        request = copy.deepcopy(self.direct)
        del request["idempotency_key"]
        self.assert_rejected(request, "IDEMPOTENCY_KEY_INVALID")

    def test_wrong_world_branch(self):
        request = copy.deepcopy(self.direct)
        request["world_id"] = "OTHER-WORLD"
        self.assert_rejected(request, "WORLD_MISMATCH")

    def test_wrong_world_step_branch(self):
        request = copy.deepcopy(self.direct)
        request["evaluation_step"] = 8
        self.assert_rejected(request, "WORLD_STEP_MISMATCH")

    def test_wrong_direction_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["projection"]["direction"] = "SEEK"
        self.assert_rejected(request, "DIRECTION_MISMATCH")

    def test_wrong_compatibility_key_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["projection"]["compatibility_key"] = "wrong-key"
        self.assert_rejected(request, "COMPATIBILITY_KEY_MISMATCH")

    def test_wrong_counterparty_branch(self):
        request = copy.deepcopy(self.reciprocal)
        request["route"]["sides"][0]["counterparty"] = "HOLDER-EPSILON"
        self.assert_rejected(request, "COUNTERPARTY_MISMATCH")

    def test_recipient_policy_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["recipient"] = "UNAUTHORIZED-RECIPIENT"
        self.assert_rejected(request, "RECIPIENT_POLICY_DENIED")

    def test_purpose_policy_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["purpose"] = "profiling"
        self.assert_rejected(request, "PURPOSE_POLICY_DENIED")

    def test_retention_policy_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["retention"] = "forever"
        self.assert_rejected(request, "RETENTION_POLICY_DENIED")

    def test_depth_policy_branch(self):
        request = copy.deepcopy(self.direct)
        request["route"]["depth"] = 1
        self.assert_rejected(request, "DEPTH_POLICY_DENIED")

    def test_revoked_branch(self):
        state = executor.new_state(self.contract)
        state["revoked_holder_receipts"].append(
            self.direct["authorizations"][0]["declared_sha256"]
        )
        executor.save_state_atomic(self.state_path, state)
        self.assert_rejected(self.direct, "AUTHORIZATION_REVOKED")

    def test_controller_audit_events_are_hash_chained(self):
        results = [
            self.run_request(self.direct),
            self.run_request(self.onward),
            self.run_request(self.reciprocal),
        ]
        state = executor.load_json(self.state_path)
        self.assertEqual(3, len(state["events"]))
        self.assertEqual(3, len(state["delivery_store"]))
        self.assertIsNone(state["events"][0]["prior_event_sha256"])
        self.assertEqual(
            state["events"][0]["event_sha256"],
            state["events"][1]["prior_event_sha256"],
        )
        self.assertEqual(
            state["events"][1]["event_sha256"],
            state["events"][2]["prior_event_sha256"],
        )
        self.assertEqual(
            [
                item["execution_receipt"]["receipt_sha256"]
                for item in state["events"]
            ],
            [
                item["execution_receipt"]["receipt_sha256"]
                for item in results
            ],
        )


if __name__ == "__main__":
    unittest.main()
