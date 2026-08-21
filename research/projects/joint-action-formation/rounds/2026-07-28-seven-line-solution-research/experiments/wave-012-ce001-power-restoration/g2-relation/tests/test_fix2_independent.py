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
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2_relation import (  # noqa: E402
    LOCAL_TRUST_CLASS,
    OWNER_RECEIPT_SCHEMA_VERSION,
    PLATFORM_LOCAL_ASSERTION,
    REQUEST_SCHEMA_VERSION,
    REQUEST_TTL_SECONDS,
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


E2_BASE = json.loads(
    (ROOT / "fixtures" / "e2.json").read_text(encoding="utf-8")
)[0]
PLATFORM_BASE = json.loads(
    (ROOT / "fixtures" / "e0.json").read_text(encoding="utf-8")
)[0]
OWNERS = ("O_Q", "O_V", "O_R", "O_S", "O_P")


def e2(profile_case: str = "EXACT_V1", **overrides):
    value = deepcopy(E2_BASE)
    value["episode_id"] = f"CE001-E2-FIX2-INDEPENDENT-{profile_case}"
    value["profile_case"] = profile_case
    value.update(overrides)
    return value


def local_signer():
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    manifest = {
        "type": "owner_ready",
        "owner_id": "O_Q",
        "pid": 93001,
        "process_instance_id": "independent-attack-process",
        "key_id": f"ed25519:O_Q:{sha256(public_raw).hexdigest()[:24]}",
        "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
        "source": {
            "id": "independent-attack-worker.py",
            "path": "/local-fixture/independent-attack-worker.py",
            "sha256": "1" * 64,
        },
        "profile_source": {"id": "O_Q.json", "sha256": "2" * 64},
        "endpoint_id": "fixture-endpoint:O_Q",
        "endpoint_descriptor_sha256": "3" * 64,
        "evidence_origin": LOCAL_TRUST_CLASS,
        "trust_anchor_status": "NOT_ESTABLISHED",
    }
    return private_key, manifest


def request_for(
    manifest: dict,
    *,
    kind: str = "EXPLAIN_BACK",
    ordinal: int = 1,
    process_ordinal: int = 1,
):
    payload = (
        {"required_clause_ids": ["EXACT_C7", "NO_OTHER_CIRCUIT"]}
        if kind == "EXPLAIN_BACK"
        else {"operation_ids": ["EP:OP:SUPPLY_C7", "EP:OP:CONNECT_C7"]}
        if kind in {"AUTHORIZE", "ACTIVATE"}
        else {}
    )
    q_without_hash = {
        "id": "CE001-Q",
        "version": "Q@v1",
        "statement": "exact independent attack Q",
    }
    return _query(
        episode_id="EP-FIX2-INDEPENDENT",
        run_id="fix2-independent",
        ordinal=ordinal,
        process_ordinal=process_ordinal,
        owner_id="O_Q",
        endpoint=endpoint_binding(manifest),
        kind=kind,
        q={**q_without_hash, "hash": digest(q_without_hash)},
        object_id="Venue-V/Circuit-C7",
        purpose="CE001_TEMPORARY_POWER_RELATION_FORMATION",
        revision="v1",
        revision_hash="4" * 64,
        version_hash="5" * 64,
        relation_schema_hash="6" * 64,
        **payload,
    )


def self_signed_receipt(
    private_key: Ed25519PrivateKey,
    manifest: dict,
    request: dict,
    *,
    response_kind: str | None = None,
    payload: dict | None = None,
    preimage_overrides: dict | None = None,
):
    request_raw = canonical_bytes(request)
    kind = response_kind or request["kind"]
    if payload is None:
        if request["kind"] == "EXPLAIN_BACK":
            payload = {
                "explained_clause_ids": request["request_payload"][
                    "required_clause_ids"
                ]
            }
        elif request["kind"] in {"AUTHORIZE", "ACTIVATE"}:
            payload = {"operation_ids": list(request["operation_ids"])}
            if request["kind"] == "ACTIVATE":
                payload["effect_asserted"] = False
        else:
            payload = {}
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
        "decision": "EXPLAINED" if kind == "EXPLAIN_BACK" else "SELF_SIGNED",
        "kind": kind,
        "requested_kind": request["kind"],
        "scope": request["scope"],
        "payload": payload,
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
    preimage.update(preimage_overrides or {})
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


def recursive_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key.casefold()
            yield from recursive_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from recursive_keys(child)


class IndependentRequestBindingAttacks(unittest.TestCase):
    def setUp(self):
        self.private_key, self.manifest = local_signer()

    def test_self_signed_wrong_kind_is_rejected(self):
        request = request_for(self.manifest, kind="EXPLAIN_BACK")
        receipt = self_signed_receipt(
            self.private_key,
            self.manifest,
            request,
            response_kind="CLAIM",
            payload={"claim": "EXACT_VERSION"},
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "response kind"):
            _verify_for_request(receipt, self.manifest, request)

    def test_self_signed_payload_and_request_hash_substitution_are_rejected(self):
        request = request_for(self.manifest)
        attacks = {
            "request_payload_sha256": "7" * 64,
            "request_raw_bytes_sha256": "8" * 64,
            "request_raw_bytes_b64": base64.b64encode(b"{}").decode("ascii"),
        }
        for field, value in attacks.items():
            with self.subTest(field=field):
                receipt = self_signed_receipt(
                    self.private_key,
                    self.manifest,
                    request,
                    preimage_overrides={field: value},
                )
                with self.assertRaisesRegex(ReceiptVerificationError, field):
                    _verify_for_request(receipt, self.manifest, request)

    def test_self_signed_operation_id_substitution_and_invalid_request_ids_fail(self):
        request = request_for(self.manifest, kind="AUTHORIZE")
        receipt = self_signed_receipt(
            self.private_key,
            self.manifest,
            request,
            payload={"operation_ids": list(reversed(request["operation_ids"]))},
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "operation_ids"):
            _verify_for_request(receipt, self.manifest, request)

        for operation_ids in ([], ["EP:OP:A", "EP:OP:A"], ["EP:OP:A", 7]):
            with self.subTest(operation_ids=operation_ids):
                bad_request = deepcopy(request)
                bad_request["operation_ids"] = operation_ids
                bad_receipt = self_signed_receipt(
                    self.private_key, self.manifest, bad_request
                )
                with self.assertRaisesRegex(ReceiptVerificationError, "operation_ids"):
                    _verify_for_request(bad_receipt, self.manifest, bad_request)

    def test_request_and_receipt_schema_substitution_fail_closed(self):
        request = request_for(self.manifest)
        for mutation in ("wrong-version", "extra-field"):
            with self.subTest(mutation=mutation):
                bad_request = deepcopy(request)
                if mutation == "wrong-version":
                    bad_request["request_schema_version"] = "attacker-schema"
                else:
                    bad_request["contract_exact_task_success"] = True
                receipt = self_signed_receipt(
                    self.private_key, self.manifest, bad_request
                )
                with self.assertRaisesRegex(
                    ReceiptVerificationError, "request schema"
                ):
                    _verify_for_request(receipt, self.manifest, bad_request)

        receipt = self_signed_receipt(
            self.private_key,
            self.manifest,
            request,
            preimage_overrides={"schema_version": "attacker-receipt-schema"},
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "schema_version"):
            _verify_for_request(receipt, self.manifest, request)

    def test_global_process_and_issuer_ordinal_attacks_fail_closed(self):
        attacks = (
            (2, 1, None, "global request ordinal"),
            (1, 2, None, "per-process ordinal"),
            (1, 1, 2, "per-process ordinal"),
        )
        for global_ordinal, process_ordinal, issuer_ordinal, message in attacks:
            with self.subTest(
                global_ordinal=global_ordinal,
                process_ordinal=process_ordinal,
                issuer_ordinal=issuer_ordinal,
            ):
                request = request_for(
                    self.manifest,
                    ordinal=global_ordinal,
                    process_ordinal=process_ordinal,
                )
                overrides = (
                    {"issuer_ordinal": issuer_ordinal}
                    if issuer_ordinal is not None
                    else None
                )
                receipt = self_signed_receipt(
                    self.private_key,
                    self.manifest,
                    request,
                    preimage_overrides=overrides,
                )
                with self.assertRaisesRegex(ReceiptVerificationError, message):
                    _verify_for_request(
                        receipt,
                        self.manifest,
                        request,
                        VerificationState(),
                    )

    def test_stale_future_oversized_window_and_out_of_window_signature_fail(self):
        now = utc_now()
        attacks = (
            (
                utc_text(now - timedelta(seconds=60)),
                utc_text(now - timedelta(seconds=30)),
                None,
                "stale",
            ),
            (
                utc_text(now + timedelta(seconds=5)),
                utc_text(now + timedelta(seconds=10)),
                None,
                "future-issued",
            ),
            (
                utc_text(now - timedelta(seconds=1)),
                utc_text(
                    now
                    + timedelta(seconds=REQUEST_TTL_SECONDS + 5)
                ),
                None,
                "freshness window exceeds",
            ),
            (
                utc_text(now - timedelta(seconds=2)),
                utc_text(now + timedelta(seconds=2)),
                utc_text(now + timedelta(seconds=3)),
                "outside request freshness",
            ),
        )
        for issued_at, expires_at, signed_at, message in attacks:
            with self.subTest(message=message):
                request = request_for(self.manifest)
                request["issued_at"] = issued_at
                request["expires_at"] = expires_at
                receipt = self_signed_receipt(
                    self.private_key,
                    self.manifest,
                    request,
                    preimage_overrides=(
                        {"signed_at": signed_at} if signed_at is not None else None
                    ),
                )
                with self.assertRaisesRegex(ReceiptVerificationError, message):
                    _verify_for_request(
                        receipt,
                        self.manifest,
                        request,
                        now=now,
                    )

    def test_query_nonce_and_exact_request_replay_fail_closed(self):
        request = request_for(self.manifest)
        receipt = self_signed_receipt(self.private_key, self.manifest, request)
        state = VerificationState()
        _verify_for_request(receipt, self.manifest, request, state)

        # Reset only ordering so each replay identity has a chance to be the
        # rejecting gate. The consumed query/nonce/request sets remain frozen.
        state.last_request_ordinal = 0
        state.process_ordinals = {}
        with self.assertRaisesRegex(ReceiptVerificationError, "replay"):
            _verify_for_request(receipt, self.manifest, request, state)


class IndependentScenarioAttacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exact = run_scenario(e2("EXACT_V1"), run_id="fix2-c-exact")
        cls.unknown = run_scenario(e2("MISSING_ALL"), run_id="fix2-c-unknown")
        cls.partial = run_scenario(
            e2("SAFETY_REFUSAL"), run_id="fix2-c-partial"
        )
        cls.opposition = run_scenario(
            e2("BLOCKING_OPPOSITION"), run_id="fix2-c-opposition"
        )
        cls.platform = run_scenario(
            deepcopy(PLATFORM_BASE), run_id="fix2-c-platform"
        )
        cls.injected = run_scenario(
            e2(
                "EXACT_V1",
                contract_exact_task_success=True,
                nested_injection={
                    "authority": "ESTABLISHED",
                    "effect": {"acceptance": {"settlement": "COMPLETE"}},
                },
            ),
            run_id="fix2-c-envelope-injection",
        )

    def test_private_column_unknown_is_verified_owner_unknown_not_controller_fill(self):
        private = self.unknown["private_column_evidence"]
        self.assertEqual(private["state"], "UNKNOWN")
        self.assertNotEqual(
            private["verified_act_hash"],
            "REJECTED",
            "PRIVATE_COLUMN_UNKNOWN must be retained as a verified O_R act",
        )
        private_unknown = [
            act
            for act in self.unknown["owner_acts"]
            if act["preimage"]["owner_id"] == "O_R"
            and act["preimage"]["kind"] == "PRIVATE_COLUMN_UNKNOWN"
        ]
        self.assertEqual(len(private_unknown), 1)
        self.assertFalse(
            any(
                item["receipt"]["preimage"].get("kind")
                == "PRIVATE_COLUMN_UNKNOWN"
                for item in self.unknown["rejected_receipts"]
            ),
            "Unknown must not be inferred after response-allowlist rejection",
        )

    def test_all_unknown_and_partial_constitution_never_open_relation_gate(self):
        unknown_relation = self.unknown["relation_version"]
        self.assertEqual(
            unknown_relation["evidence_status"],
            "DERIVED_CANDIDATE_WITH_UNRESOLVED_CONSTITUTION",
        )
        self.assertFalse(unknown_relation["relation_established"])
        self.assertFalse(unknown_relation["downstream_relation_gate_open"])
        self.assertTrue(
            all(
                state == "UNKNOWN_OWNER_POLICY_MISSING_OR_NO_DECISION"
                for state in self.unknown["axis_evidence"]["constituted"][
                    "owner_states"
                ].values()
            )
        )

        partial_relation = self.partial["relation_version"]
        closure = partial_relation["constitution_closure"]
        self.assertEqual(closure["status"], "UNRESOLVED_CONSTITUTION")
        self.assertFalse(closure["owner_exact_constitution"]["O_S"])
        self.assertTrue(
            all(
                closure["owner_exact_constitution"][owner]
                for owner in OWNERS
                if owner != "O_S"
            )
        )
        self.assertFalse(partial_relation["downstream_relation_gate_open"])
        self.assertFalse(
            any(
                act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in self.partial["owner_acts"]
            )
        )

    def test_platform_same_process_self_assertion_is_labeled_not_promoted(self):
        proof = self.platform["bypass_evidence"]["capability_proof"]
        readback = self.platform["bypass_evidence"]["capability_readback"]
        self.assertEqual(
            proof["preimage"]["process"],
            readback["preimage"]["process"],
            "proof and readback are same-process self-assertions in this fixture",
        )
        bypass = self.platform["bypass_evidence"]
        self.assertTrue(bypass["self_configured_profile_and_endpoint"])
        self.assertEqual(
            bypass["verification_classification"], PLATFORM_LOCAL_ASSERTION
        )
        self.assertEqual(bypass["real_platform_identity"], "NOT_ESTABLISHED")
        self.assertEqual(
            bypass["real_platform_applicability"], "NOT_ESTABLISHED"
        )
        self.assertNotIn("platform_native_scope_verified", bypass)
        self.assertEqual(
            self.platform["g2_line_local_envelope"]["external_truth_status"],
            "NOT_ESTABLISHED",
        )

    def test_recursive_envelope_and_config_injection_cannot_emit_adjacent_truth(self):
        forbidden = {
            "authority",
            "effect",
            "acceptance",
            "settlement",
            "y_effect",
            "y_acceptance",
            "success",
            "green",
            "result",
            "overall_status",
            "exacttasksuccess",
            "correctresolution",
            "achievablesuccesscoverage",
            "allcaseresolutioncoverage",
            "unsafeeffect",
            "duplicateeffect",
            "wrongobjectreliance",
            "recoverytovalue",
            "unreconciledeffect",
            "missedreopennodes",
            "overreopennodes",
            "candidateexclusivesuccess",
        }
        for output in (self.exact, self.platform, self.injected):
            with self.subTest(path=output["path"], run_id=output["run_id"]):
                envelope = output["g2_line_local_envelope"]
                keys = set(recursive_keys(envelope))
                self.assertTrue(forbidden.isdisjoint(keys))
                self.assertFalse(
                    any(
                        key.startswith("contract_")
                        and key != "contract_fields_emitted"
                        for key in keys
                    )
                )
                self.assertEqual(envelope["contract_fields_emitted"], [])

    def test_raw_ed25519_pid_and_key_uniqueness_did_not_regress(self):
        manifests = {
            item["owner_id"]: item for item in self.exact["process_manifests"]
        }
        self.assertEqual(len({item["pid"] for item in manifests.values()}), 5)
        self.assertEqual(len({item["key_id"] for item in manifests.values()}), 5)
        self.assertEqual(
            len({item["public_key_b64"] for item in manifests.values()}), 5
        )
        for receipt in self.exact["owner_acts"]:
            raw = base64.b64decode(receipt["raw_bytes_b64"], validate=True)
            public_raw = base64.b64decode(
                receipt["public_key_b64"], validate=True
            )
            signature = base64.b64decode(
                receipt["signature_b64"], validate=True
            )
            self.assertEqual(raw, canonical_bytes(receipt["preimage"]))
            self.assertEqual(sha256(raw).hexdigest(), receipt["act_hash"])
            self.assertEqual(
                receipt["key_id"],
                manifests[receipt["preimage"]["owner_id"]]["key_id"],
            )
            Ed25519PublicKey.from_public_bytes(public_raw).verify(
                signature, raw
            )

    def test_refusal_opposition_and_g5_g6_unverified_did_not_regress(self):
        self.assertEqual(
            self.partial["axis_evidence"]["claimed"]["owner_states"]["O_S"],
            "REFUSED_BLOCKING",
        )
        self.assertEqual(
            self.opposition["axis_evidence"]["claimed"]["owner_states"]["O_V"],
            "BLOCKING_OPPOSITION",
        )
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in self.opposition["owner_acts"]
            )
        )
        authorized = self.exact["axis_evidence"]["authorized"]
        activated = self.exact["axis_evidence"]["activated"]
        self.assertEqual(authorized["truth_owner_boundary"], "G5_UNVERIFIED")
        self.assertEqual(activated["truth_owner_boundary"], "G6_UNVERIFIED")
        self.assertEqual(activated["O_E_state"], "NOT_RUN")
        self.assertTrue(
            all(
                state == "G5_UNVERIFIED_OWNER_INTENT_ONLY"
                for state in authorized["owner_states"].values()
            )
        )
        self.assertTrue(
            all(
                state == "G6_UNVERIFIED_NO_EFFECT"
                for state in activated["owner_states"].values()
            )
        )


if __name__ == "__main__":
    unittest.main()
