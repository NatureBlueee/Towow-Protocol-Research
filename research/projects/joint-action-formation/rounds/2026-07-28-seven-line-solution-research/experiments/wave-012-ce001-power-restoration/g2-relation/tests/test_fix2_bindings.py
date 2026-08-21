from __future__ import annotations

import base64
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2_relation import (  # noqa: E402
    LOCAL_TRUST_CLASS,
    OWNER_RECEIPT_SCHEMA_VERSION,
    PLATFORM_LOCAL_ASSERTION,
    ReceiptVerificationError,
    VerificationState,
    _query,
    _verify_for_request,
    canonical_bytes,
    digest,
    endpoint_binding,
    run_scenario,
    utc_now,
    utc_text,
)


BASE = json.loads((ROOT / "fixtures" / "e2.json").read_text(encoding="utf-8"))[0]
PLATFORM = json.loads((ROOT / "fixtures" / "e0.json").read_text(encoding="utf-8"))[0]


def e2(profile_case: str) -> dict:
    value = deepcopy(BASE)
    value["episode_id"] = f"CE001-E2-FIX2-{profile_case}"
    value["profile_case"] = profile_case
    return value


def fake_endpoint():
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    public_b64 = base64.b64encode(public_raw).decode("ascii")
    manifest = {
        "type": "owner_ready",
        "owner_id": "O_Q",
        "pid": 77123,
        "process_instance_id": "fix2-fake-process",
        "key_id": f"ed25519:O_Q:{sha256(public_raw).hexdigest()[:24]}",
        "public_key_b64": public_b64,
        "source": {
            "id": "fix2-test-worker.py",
            "path": "/local-fixture/fix2-test-worker.py",
            "sha256": "1" * 64,
        },
        "profile_source": {"id": "O_Q.json", "sha256": "2" * 64},
        "endpoint_id": "fixture-endpoint:O_Q",
        "endpoint_descriptor_sha256": "3" * 64,
        "evidence_origin": LOCAL_TRUST_CLASS,
        "trust_anchor_status": "NOT_ESTABLISHED",
    }
    return private_key, manifest


def request_for(manifest: dict, *, kind: str = "EXPLAIN_BACK") -> dict:
    payload = (
        {"required_clause_ids": ["EXACT_C7"]}
        if kind == "EXPLAIN_BACK"
        else {"operation_ids": ["EP:OP:A", "EP:OP:B"]}
        if kind in {"AUTHORIZE", "ACTIVATE"}
        else {}
    )
    return _query(
        episode_id="EP-FIX2",
        run_id="fix2-unit",
        ordinal=1,
        process_ordinal=1,
        owner_id="O_Q",
        endpoint=endpoint_binding(manifest),
        kind=kind,
        q={"id": "Q", "version": "v1", "statement": "exact", "hash": digest(
            {"id": "Q", "version": "v1", "statement": "exact"}
        )},
        object_id="OBJ",
        purpose="PURPOSE",
        revision="v1",
        revision_hash="4" * 64,
        version_hash="5" * 64,
        relation_schema_hash="6" * 64,
        **payload,
    )


def signed_receipt(
    private_key: Ed25519PrivateKey,
    manifest: dict,
    request: dict,
    *,
    response_kind: str | None = None,
    decision: str | None = None,
    payload: dict | None = None,
    overrides: dict | None = None,
) -> dict:
    request_raw = canonical_bytes(request)
    kind = response_kind or request["kind"]
    response_payload = payload
    if response_payload is None:
        if request["kind"] in {"AUTHORIZE", "ACTIVATE"}:
            response_payload = {"operation_ids": request["operation_ids"]}
            if request["kind"] == "ACTIVATE":
                response_payload["effect_asserted"] = False
        elif request["kind"] == "EXPLAIN_BACK":
            response_payload = {
                "explained_clause_ids": request["request_payload"]["required_clause_ids"]
            }
        else:
            response_payload = {}
    preimage = {
        "schema_version": OWNER_RECEIPT_SCHEMA_VERSION,
        "request_schema_version": request["request_schema_version"],
        "owner_id": request["owner_id"],
        "run_id": request["run_id"],
        "episode_id": request["episode_id"],
        "query_id": request["query_id"],
        "q": request["q"],
        "object_id": request["object_id"],
        "purpose": request["purpose"],
        "relation_revision": request["relation_revision"],
        "relation_revision_hash": request["relation_revision_hash"],
        "relation_version_hash": request["relation_version_hash"],
        "relation_schema_hash": request["relation_schema_hash"],
        "signed_at": request["issued_at"],
        "decision": decision or ("EXPLAINED" if kind == "EXPLAIN_BACK" else "CLAIMED"),
        "kind": kind,
        "requested_kind": request["kind"],
        "scope": request["scope"],
        "payload": response_payload,
        "operation_ids": request["operation_ids"],
        "request_ordinal": request["request_ordinal"],
        "process_ordinal": request["process_ordinal"],
        "issuer_ordinal": request["process_ordinal"],
        "request_nonce": request["request_nonce"],
        "request_issued_at": request["issued_at"],
        "request_expires_at": request["expires_at"],
        "request_raw_bytes_b64": base64.b64encode(request_raw).decode("ascii"),
        "request_raw_bytes_sha256": sha256(request_raw).hexdigest(),
        "request_payload_sha256": digest(request["request_payload"]),
        "endpoint_binding": request["endpoint_binding"],
        "endpoint_binding_sha256": request["endpoint_binding"]["sha256"],
        "evidence_origin": LOCAL_TRUST_CLASS,
        "trust_anchor_status": "NOT_ESTABLISHED",
        "source": manifest["source"],
        "process": {
            "pid": manifest["pid"],
            "instance_id": manifest["process_instance_id"],
            "key_id": manifest["key_id"],
        },
    }
    preimage.update(overrides or {})
    raw = canonical_bytes(preimage)
    raw_hash = sha256(raw).hexdigest()
    return {
        "type": "owner_receipt",
        "act_id": f"act-{raw_hash[:20]}",
        "act_hash": raw_hash,
        "raw_bytes_b64": base64.b64encode(raw).decode("ascii"),
        "raw_bytes_sha256": raw_hash,
        "signature_b64": base64.b64encode(private_key.sign(raw)).decode("ascii"),
        "public_key_b64": manifest["public_key_b64"],
        "key_id": manifest["key_id"],
        "preimage": preimage,
    }


class ExactRequestReceiptBindingTests(unittest.TestCase):
    def setUp(self):
        self.private_key, self.manifest = fake_endpoint()

    def test_wrong_kind_self_signed_response_is_rejected(self):
        request = request_for(self.manifest, kind="EXPLAIN_BACK")
        receipt = signed_receipt(
            self.private_key,
            self.manifest,
            request,
            response_kind="CLAIM",
            payload={"claim": "WRONG_KIND"},
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "response kind"):
            _verify_for_request(receipt, self.manifest, request)

    def test_payload_operation_schema_and_endpoint_substitution_fail_closed(self):
        request = request_for(self.manifest, kind="AUTHORIZE")
        bad_operation = signed_receipt(
            self.private_key,
            self.manifest,
            request,
            payload={"operation_ids": ["EP:OP:B", "EP:OP:A"]},
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "operation_ids"):
            _verify_for_request(bad_operation, self.manifest, request)

        for field, value, message in (
            ("schema_version", "arbitrary-schema", "schema_version"),
            ("relation_schema_hash", "9" * 64, "relation_schema_hash"),
            ("request_payload_sha256", "8" * 64, "request_payload_sha256"),
            ("endpoint_binding_sha256", "7" * 64, "endpoint_binding_sha256"),
        ):
            receipt = signed_receipt(
                self.private_key, self.manifest, request, overrides={field: value}
            )
            with self.assertRaisesRegex(ReceiptVerificationError, message):
                _verify_for_request(receipt, self.manifest, request)

    def test_stale_future_malformed_and_issuer_jump_fail_closed(self):
        for mode in ("stale", "future", "malformed"):
            request = request_for(self.manifest)
            now = utc_now()
            if mode == "stale":
                request["issued_at"] = utc_text(now - timedelta(seconds=60))
                request["expires_at"] = utc_text(now - timedelta(seconds=30))
            elif mode == "future":
                request["issued_at"] = utc_text(now + timedelta(seconds=30))
                request["expires_at"] = utc_text(now + timedelta(seconds=60))
            else:
                request["issued_at"] = "not-a-time"
                request["expires_at"] = "also-not-a-time"
            receipt = signed_receipt(self.private_key, self.manifest, request)
            with self.assertRaises(ReceiptVerificationError, msg=mode):
                _verify_for_request(receipt, self.manifest, request)

        request = request_for(self.manifest)
        receipt = signed_receipt(
            self.private_key, self.manifest, request, overrides={"issuer_ordinal": 2}
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "per-process ordinal"):
            _verify_for_request(
                receipt, self.manifest, request, VerificationState()
            )

    def test_nonce_query_and_request_hash_replay_fails_closed(self):
        request = request_for(self.manifest)
        receipt = signed_receipt(self.private_key, self.manifest, request)
        state = VerificationState()
        _verify_for_request(receipt, self.manifest, request, state)
        state.last_request_ordinal = 0
        state.process_ordinals = {}
        with self.assertRaisesRegex(ReceiptVerificationError, "replay"):
            _verify_for_request(receipt, self.manifest, request, state)


class ConstitutionAndTruthBoundaryTests(unittest.TestCase):
    def test_all_unknown_is_unresolved_candidate_and_never_authorizes(self):
        output = run_scenario(e2("MISSING_ALL"))
        relation = output["relation_version"]
        self.assertEqual(
            relation["evidence_status"],
            "DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION",
        )
        self.assertFalse(relation["relation_established"])
        self.assertFalse(relation["downstream_relation_gate_open"])
        self.assertTrue(
            all(
                value is False
                for value in relation["constitution_closure"][
                    "owner_exact_constitution"
                ].values()
            )
        )
        self.assertFalse(
            any(
                act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_runtime_wrong_kind_self_signed_worker_receipt_is_rejected(self):
        output = run_scenario(e2("WRONG_KIND"))
        rejected = [
            item
            for item in output["rejected_receipts"]
            if item["owner_id"] == "O_V"
        ]
        self.assertEqual(len(rejected), 1)
        self.assertIn("response kind", rejected[0]["reason"])

    def test_owner_and_platform_are_only_local_ephemeral_self_assertions(self):
        owner = run_scenario(e2("EXACT_V1"))
        self.assertTrue(
            all(
                manifest["evidence_origin"] == LOCAL_TRUST_CLASS
                and manifest["real_owner_identity"] == "NOT_ESTABLISHED"
                and manifest["authority"] == "NOT_ESTABLISHED"
                for manifest in owner["process_manifests"]
            )
        )
        platform = run_scenario(deepcopy(PLATFORM))
        bypass = platform["bypass_evidence"]
        self.assertEqual(
            bypass["verification_classification"], PLATFORM_LOCAL_ASSERTION
        )
        self.assertNotIn("platform_native_scope_verified", bypass)
        self.assertEqual(bypass["real_platform_identity"], "NOT_ESTABLISHED")
        self.assertEqual(bypass["real_platform_applicability"], "NOT_ESTABLISHED")

    def test_line_local_envelope_emits_no_contract_or_downstream_truth_fields(self):
        envelope = run_scenario(e2("EXACT_V1"))["g2_line_local_envelope"]
        self.assertEqual(envelope["line_id"], "G2")
        self.assertEqual(envelope["contract_fields_emitted"], [])
        forbidden = {
            "success",
            "green",
            "result",
            "overall_status",
            "authority",
            "effect",
            "acceptance",
            "settlement",
            "y_effect",
            "y_acceptance",
        }

        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key.lower()
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)

        self.assertTrue(forbidden.isdisjoint(set(keys(envelope))))


if __name__ == "__main__":
    unittest.main()
