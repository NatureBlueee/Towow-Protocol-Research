import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from controller import CrossAuthorityController, InjectedCrash  # noqa: E402
from domains import ExternalAnchor, HolderAuthority, RecipientAuthority  # noqa: E402
from protocol import (  # noqa: E402
    ProtocolError,
    envelope_hash,
    load_json,
    private_key_from_hex,
    save_json_atomic,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


LAB_SEEDS = {
    ("HOLDER-ALPHA", "v1"): "1675e08e4f47e5e13c1268030b70fcf8704e44196a0c9c2f02fc09951b296060",
    ("HOLDER-ALPHA", "v2"): "2a2028f447c91a7e1547ba9d09973d208222d7f0b8dcff5e754f0746f4e2530d",
    ("HOLDER-BETA", "v2"): "a59592954fde6187c1eb484e24897c66f0c19599cd1b1f2c72919c99c4c03290",
    ("HOLDER-GAMMA", "v2"): "f60e03ccc85230912eaea8381e8d299e5ed20d9e6e3cde99e9f1418b2bda926f",
    ("HOLDER-DELTA", "v2"): "82470d0ff02c32ad987e2aeb8ba221a0cfdcbbaa021112f988f177a41341dbd8",
    ("RECIPIENT-A", "v2"): "d6e6d916136bd18a799e6ed1ead575f732b269e68e65f699d279fb3033b2c6af",
    ("RECIPIENT-B", "v2"): "8c1a0c55e0cee5b18513690a467837b5fdf519eaf5bfae723adcc67cc38ca050",
    ("RECIPIENT-GAMMA", "v2"): "d34b8c60c91647e663f3f6bb84fb22b616e854f33b4704915bd3ecce1f8d96f5",
    ("RECIPIENT-DELTA", "v2"): "fd4516e7041cd35eec6862123bc6f38a7accc83275f2c96577acebbdcecef230",
    ("CONTROLLER-W5B", "v2"): "dc62c4b88c8bbf57d5dcda3363a209ce94931d8a222bcc7bfc6e741f0c94f2c5",
    ("ANCHOR-W5B", "v2"): "9673f1e142f32d0982e8a6359815f1e20b74fa9b7fe536bdf9386725d2b8d761",
}


def key(authority_id, key_id="v2"):
    return private_key_from_hex(LAB_SEEDS[(authority_id, key_id)])


class Lab:
    def __init__(self, root: Path):
        self.root = root
        self.contract = json.loads(
            (ROOT / "contract.json").read_text(encoding="utf-8")
        )
        self.holders = {
            authority_id: HolderAuthority(
                authority_id,
                "v2",
                key(authority_id),
                root / "holders" / f"{authority_id}.json",
            )
            for authority_id in [
                "HOLDER-ALPHA",
                "HOLDER-BETA",
                "HOLDER-GAMMA",
                "HOLDER-DELTA",
            ]
        }
        self.recipients = {
            authority_id: RecipientAuthority(
                authority_id,
                "v2",
                key(authority_id),
                root / "recipients" / f"{authority_id}.json",
                self.contract,
            )
            for authority_id in [
                "RECIPIENT-A",
                "RECIPIENT-B",
                "RECIPIENT-GAMMA",
                "RECIPIENT-DELTA",
            ]
        }
        self.anchor = ExternalAnchor(
            "ANCHOR-W5B",
            "v2",
            key("ANCHOR-W5B"),
            root / "anchor.json",
        )
        self.state_path = root / "controller.json"

    def controller(self, *, anchor=None, recipients=None):
        return CrossAuthorityController(
            contract=self.contract,
            controller_key_id="v2",
            controller_private_key=key("CONTROLLER-W5B"),
            state_path=self.state_path,
            holders=self.holders,
            recipients=recipients or self.recipients,
            anchor=anchor or self.anchor,
        )

    def request(self, name, *, holder_key_overrides=None):
        template = json.loads(
            (ROOT / "fixtures" / f"{name}.json").read_text(encoding="utf-8")
        )
        bodies = template.pop("authorization_bodies")
        overrides = holder_key_overrides or {}
        envelopes = []
        for body in bodies:
            holder = body["holder_authority"]
            key_id = overrides.get(holder, "v2")
            if key_id == "v2":
                envelopes.append(
                    self.holders[holder].issue_authorization(body)
                )
            else:
                envelopes.append(
                    sign_envelope(
                        key(holder, key_id),
                        kind="HOLDER_AUTHORIZATION",
                        issuer=holder,
                        key_id=key_id,
                        body=body,
                    )
                )
        template["authorizations"] = envelopes
        return template


class ForgingRecipient:
    """Attack endpoint: labels a controller signature as a recipient ACK."""

    def __init__(self, authority_id):
        self.authority_id = authority_id

    def prepare(self, **kwargs):
        body = {
            "transaction_id": kwargs["transaction_id"],
            "recipient": self.authority_id,
            "delivery_sha256": sha256_value(kwargs["delivery"]),
            "command_sha256": kwargs["command_sha256"],
            "prepared_at_step": kwargs["step"],
        }
        return sign_envelope(
            key("CONTROLLER-W5B"),
            kind="RECIPIENT_PREPARED_ACK",
            issuer=self.authority_id,
            key_id="v2",
            body=body,
        )


class ForkingAnchor(ExternalAnchor):
    """Malicious anchor that signs a branch not extending the client's pin."""

    def append(self, *, event_id, event, expected_previous_head, step):
        sequence = 1
        previous_head = "malicious-fork-head"
        new_head = sha256_value(
            {
                "sequence": sequence,
                "previous_head": previous_head,
                "event_id": event_id,
                "event": event,
            }
        )
        return self._sign(
            "ANCHOR_RECEIPT",
            {
                "anchor_authority": self.authority_id,
                "sequence": sequence,
                "previous_head": previous_head,
                "new_head": new_head,
                "event_id": event_id,
                "event": copy.deepcopy(event),
                "anchored_at_step": step,
            },
        )


class CrossAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.lab = Lab(Path(self.temporary.name))

    def test_direct_requires_recipient_ack_and_external_anchor(self):
        result = self.lab.controller().execute(self.lab.request("direct"))
        self.assertEqual("EXECUTED", result["status"])
        self.assertEqual(1, len(result["recipient_commit_acks"]))
        ack = result["recipient_commit_acks"][0]
        verify_envelope(
            ack,
            self.lab.contract,
            expected_kind="RECIPIENT_COMMIT_ACK",
            expected_issuer="RECIPIENT-A",
            step=7,
        )
        verify_envelope(
            result["anchor_receipt"],
            self.lab.contract,
            expected_kind="ANCHOR_RECEIPT",
            expected_issuer="ANCHOR-W5B",
            step=7,
        )
        controller_body = verify_envelope(
            result["controller_receipt"],
            self.lab.contract,
            expected_kind="CONTROLLER_EXECUTION_RECEIPT",
            expected_issuer="CONTROLLER-W5B",
            step=7,
        )
        self.assertEqual("NOT_ESTABLISHED", controller_body["relation_status"])
        self.assertNotEqual(
            result["recipient_commit_acks"][0]["signature"],
            result["controller_receipt"]["signature"],
        )

    def test_derived_requires_first_recipient_onward_authorization(self):
        result = self.lab.controller().execute(self.lab.request("derived"))
        self.assertEqual("EXECUTED", result["status"])
        self.assertEqual(2, len(result["recipient_commit_acks"]))
        onward = result["onward_authorization"]
        body = verify_envelope(
            onward,
            self.lab.contract,
            expected_kind="ONWARD_AUTHORIZATION",
            expected_issuer="RECIPIENT-A",
            step=7,
        )
        self.assertEqual("RECIPIENT-B", body["onward_delivery"]["recipient"])
        self.assertIn(
            body["onward_transaction_id"],
            load_json(
                self.lab.recipients["RECIPIENT-B"].state_path
            )["committed"],
        )

    def test_reciprocal_success_has_both_independent_commit_acks(self):
        result = self.lab.controller().execute(self.lab.request("reciprocal"))
        self.assertEqual("EXECUTED", result["status"])
        self.assertEqual(
            {"RECIPIENT-GAMMA", "RECIPIENT-DELTA"},
            {item["issuer"] for item in result["recipient_commit_acks"]},
        )
        anchor_entries = load_json(self.lab.anchor.state_path)["entries"]
        decisions = [
            item["receipt"]["body"]["event"]["decision"]
            for item in anchor_entries
        ]
        self.assertIn("COMMIT", decisions)
        self.assertIn("GROUP_COMPLETE", decisions)
        self.assertEqual("ROUTE_COMPLETE", decisions[-1])

    def test_controller_self_signed_fake_recipient_ack_is_rejected(self):
        request = self.lab.request("direct")
        recipients = dict(self.lab.recipients)
        recipients["RECIPIENT-A"] = ForgingRecipient("RECIPIENT-A")
        result = self.lab.controller(recipients=recipients).execute(request)
        self.assertEqual("REJECTED", result["status"])
        self.assertEqual("SIGNATURE_INVALID", result["code"])
        self.assertFalse(self.lab.anchor.state_path.exists())

    def test_forged_ack_payload_or_signature_is_rejected(self):
        request = self.lab.request("direct")
        with self.assertRaises(InjectedCrash):
            self.lab.controller().execute(
                request, fault_after="after_prepare:direct"
            )
        state = load_json(self.lab.state_path)
        command = state["commands"][request["idempotency_key"]]
        command["legs"]["direct"]["prepare_ack"]["signature"] = "00" * 64
        save_json_atomic(self.lab.state_path, state)
        result = self.lab.controller().execute(request)
        self.assertEqual("REJECTED", result["status"])
        self.assertEqual("SIGNATURE_INVALID", result["code"])
        self.assertFalse(self.lab.anchor.state_path.exists())

    def test_revoked_before_reservation_is_zero_controller_state(self):
        request = self.lab.request("direct")
        self.lab.holders["HOLDER-ALPHA"].revoke(
            "W5B-AUTH-DIRECT-ALPHA-001",
            step=7,
            reason="holder-withdrew",
        )
        result = self.lab.controller().execute(request)
        self.assertEqual("REJECTED", result["status"])
        self.assertEqual("AUTHORIZATION_REVOKED", result["code"])
        self.assertFalse(self.lab.state_path.exists())
        self.assertFalse(self.lab.anchor.state_path.exists())

    def test_revocation_after_prepare_aborts_before_commit_decision(self):
        request = self.lab.request("direct")
        with self.assertRaises(InjectedCrash):
            self.lab.controller().execute(
                request, fault_after="after_prepare:direct"
            )
        self.lab.holders["HOLDER-ALPHA"].revoke(
            "W5B-AUTH-DIRECT-ALPHA-001",
            step=7,
            reason="withdrew-after-prepare",
        )
        result = self.lab.controller().execute(request)
        self.assertEqual("REJECTED", result["status"])
        self.assertEqual("AUTHORIZATION_REVOKED", result["code"])
        entries = load_json(self.lab.anchor.state_path)["entries"]
        self.assertEqual(
            ["ABORT"],
            [
                item["receipt"]["body"]["event"]["decision"]
                for item in entries
            ],
        )
        recipient = load_json(
            self.lab.recipients["RECIPIENT-A"].state_path
        )
        self.assertEqual({}, recipient["committed"])
        self.assertEqual(1, len(recipient["aborted"]))

    def test_signed_anchor_fork_is_rejected_against_pinned_head(self):
        request = self.lab.request("direct")
        evil = ForkingAnchor(
            "ANCHOR-W5B",
            "v2",
            key("ANCHOR-W5B"),
            Path(self.temporary.name) / "evil-anchor.json",
        )
        result = self.lab.controller(anchor=evil).execute(request)
        self.assertEqual("REJECTED", result["status"])
        self.assertEqual("ANCHOR_FORK_DETECTED", result["code"])

    def test_completed_replay_detects_rewritten_anchor_head(self):
        request = self.lab.request("direct")
        first = self.lab.controller().execute(request)
        self.assertEqual("EXECUTED", first["status"])
        anchor_state = load_json(self.lab.anchor.state_path)
        anchor_state["head"] = "rewritten-fork-head"
        save_json_atomic(self.lab.anchor.state_path, anchor_state)
        replay = self.lab.controller().execute(request)
        self.assertEqual("REJECTED", replay["status"])
        self.assertEqual("ANCHOR_FORK_DETECTED", replay["code"])

    def test_reciprocal_partial_materialization_recovers_before_success(self):
        request = self.lab.request("reciprocal")
        with self.assertRaises(InjectedCrash):
            self.lab.controller().execute(
                request, fault_after="after_commit:reciprocal:1"
            )
        controller_state = load_json(self.lab.state_path)
        command = controller_state["commands"][request["idempotency_key"]]
        self.assertIsNone(command["outcome"])
        committed_counts = [
            len(load_json(recipient.state_path)["committed"])
            if recipient.state_path.exists()
            else 0
            for recipient in [
                self.lab.recipients["RECIPIENT-GAMMA"],
                self.lab.recipients["RECIPIENT-DELTA"],
            ]
        ]
        self.assertEqual([0, 1], sorted(committed_counts))
        result = self.lab.controller().execute(request)
        self.assertEqual("EXECUTED", result["status"])
        self.assertEqual(2, len(result["recipient_commit_acks"]))

    def test_crash_after_anchor_decision_recovers_without_second_decision(self):
        request = self.lab.request("direct")
        with self.assertRaises(InjectedCrash):
            self.lab.controller().execute(
                request, fault_after="after_decision:direct"
            )
        before = load_json(self.lab.anchor.state_path)
        self.assertEqual(1, len(before["entries"]))
        result = self.lab.controller().execute(request)
        self.assertEqual("EXECUTED", result["status"])
        after = load_json(self.lab.anchor.state_path)
        decisions = [
            item["receipt"]["body"]["event"]["decision"]
            for item in after["entries"]
        ]
        self.assertEqual(1, decisions.count("COMMIT"))

    def test_exact_replay_is_read_only_and_conflict_is_rejected(self):
        request = self.lab.request("direct")
        first = self.lab.controller().execute(request)
        controller_bytes = self.lab.state_path.read_bytes()
        anchor_bytes = self.lab.anchor.state_path.read_bytes()
        second = self.lab.controller().execute(request)
        self.assertEqual("IDEMPOTENT_REPLAY", second["replay"])
        self.assertFalse(second["state_changed"])
        self.assertEqual(controller_bytes, self.lab.state_path.read_bytes())
        self.assertEqual(anchor_bytes, self.lab.anchor.state_path.read_bytes())
        changed = copy.deepcopy(request)
        changed["caller_nonce"] = "same-key-different-command"
        conflict = self.lab.controller().execute(changed)
        self.assertEqual("IDEMPOTENCY_CONFLICT", conflict["code"])
        self.assertEqual("EXECUTED", first["status"])

    def test_expired_key_fails_and_rotated_key_succeeds(self):
        expired = self.lab.request(
            "direct", holder_key_overrides={"HOLDER-ALPHA": "v1"}
        )
        rejected = self.lab.controller().execute(expired)
        self.assertEqual("REJECTED", rejected["status"])
        self.assertEqual("SIGNING_KEY_NOT_VALID", rejected["code"])
        rotated = self.lab.request("direct")
        accepted = self.lab.controller().execute(rotated)
        self.assertEqual("EXECUTED", accepted["status"])


if __name__ == "__main__":
    unittest.main()
