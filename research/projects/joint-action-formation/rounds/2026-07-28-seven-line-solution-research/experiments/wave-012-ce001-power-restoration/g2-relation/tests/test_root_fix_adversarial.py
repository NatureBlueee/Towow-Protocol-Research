from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import g2_relation  # noqa: E402
from g2_relation import (  # noqa: E402
    AXES,
    ReceiptVerificationError,
    canonical_bytes,
    run_scenario,
    semantic_projection,
    verify_receipt,
)


E2_BASE = json.loads((ROOT / "fixtures" / "e2.json").read_text(encoding="utf-8"))[0]
PLATFORM_BASE = json.loads(
    (ROOT / "fixtures" / "e0.json").read_text(encoding="utf-8")
)[0]
OWNERS = ("O_Q", "O_V", "O_R", "O_S", "O_P")

COLLIDING_OWNER_WORKER = r'''
from __future__ import annotations
import argparse, base64, json, sys
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def h(raw):
    return sha256(raw).hexdigest()

parser = argparse.ArgumentParser()
parser.add_argument("--owner-id", required=True)
parser.add_argument("--profile-source", required=True)
parser.add_argument("--profile-case", required=True)
args = parser.parse_args()
worker_path = Path(__file__).resolve()
profile_path = Path(args.profile_source).resolve()
private_key = Ed25519PrivateKey.from_private_bytes(bytes([17]) * 32)
public_raw = private_key.public_key().public_bytes(
    serialization.Encoding.Raw, serialization.PublicFormat.Raw
)
source = {
    "id": worker_path.name,
    "path": str(worker_path),
    "sha256": h(worker_path.read_bytes()),
}
key_id = "ed25519:REUSED-ACROSS-ALL-OWNERS:" + h(public_raw)[:16]
manifest = {
    "type": "owner_ready",
    "owner_id": args.owner_id,
    "pid": 424242,
    "process_instance_id": "REUSED-PROCESS-INSTANCE",
    "key_id": key_id,
    "public_key_b64": base64.b64encode(public_raw).decode(),
    "source": source,
    "profile_source": {"id": profile_path.name, "sha256": h(profile_path.read_bytes())},
}
print(json.dumps(manifest, sort_keys=True), flush=True)
ordinal = 0
for line in sys.stdin:
    if not line.strip():
        continue
    request = json.loads(line)
    ordinal += 1
    requested_kind = request["kind"]
    if requested_kind == "PRIVATE_COLUMN":
        kind, decision = "PRIVATE_COLUMN_DISCLOSED", "DISCLOSED"
        payload = {
            "column_state": "DISCLOSED",
            "column": {
                "role": "RESOURCE_PROVIDER",
                "action": "SUPPLY_C7",
                "capacity_kw": 3.0,
                "duration_minutes": 45,
            },
        }
    elif requested_kind == "CONSTITUTE":
        kind, decision = "CONSTITUTE", "CONSTITUTED"
        payload = {"stance": "CONSTITUTE_EXACT_REVISION"}
    elif requested_kind == "EXPLAIN_BACK":
        kind, decision = "EXPLAIN_BACK", "EXPLAINED"
        payload = {
            "explained_clause_ids": request["request_payload"]["required_clause_ids"]
        }
    elif requested_kind == "CLAIM":
        kind, decision, payload = "CLAIM", "CLAIMED", {"claim": "EXACT_VERSION"}
    elif requested_kind == "AUTHORIZE":
        kind, decision = "AUTHORIZE", "AUTHORIZATION_INTENT"
        payload = {"operation_ids": request["request_payload"]["operation_ids"]}
    elif requested_kind == "ACTIVATE":
        kind, decision = "ACTIVATE", "ACTIVATION_INTENT"
        payload = {
            "operation_ids": request["request_payload"]["operation_ids"],
            "effect_asserted": False,
        }
    else:
        raise RuntimeError(requested_kind)
    preimage = {
        "schema_version": "ce001-owner-act-v2",
        "owner_id": args.owner_id,
        "episode_id": request["episode_id"],
        "query_id": request["query_id"],
        "q": request["q"],
        "object_id": request["object_id"],
        "purpose": request["purpose"],
        "relation_revision": request["relation_revision"],
        "relation_revision_hash": request["relation_revision_hash"],
        "relation_version_hash": request["relation_version_hash"],
        "time": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "kind": kind,
        "scope": request["scope"],
        "payload": payload,
        "ordinal": ordinal,
        "source": source,
        "process": {
            "pid": 424242,
            "instance_id": "REUSED-PROCESS-INSTANCE",
            "key_id": key_id,
        },
    }
    raw = canonical(preimage)
    raw_hash = h(raw)
    receipt = {
        "type": "owner_receipt",
        "act_id": "act-" + raw_hash[:20],
        "act_hash": raw_hash,
        "raw_bytes_b64": base64.b64encode(raw).decode(),
        "raw_bytes_sha256": raw_hash,
        "signature_b64": base64.b64encode(private_key.sign(raw)).decode(),
        "public_key_b64": base64.b64encode(public_raw).decode(),
        "key_id": key_id,
        "preimage": preimage,
    }
    print(json.dumps(receipt, sort_keys=True), flush=True)
'''


def e2(profile_case: str = "EXACT_V1", **overrides):
    value = deepcopy(E2_BASE)
    value["episode_id"] = f"CE001-E2-ROOT-FIX-C-{profile_case}"
    value["profile_case"] = profile_case
    value.update(overrides)
    return value


def platform(**overrides):
    value = deepcopy(PLATFORM_BASE)
    value.update(overrides)
    return value


def manifest_for(output, owner_id):
    return next(
        item for item in output["process_manifests"] if item["owner_id"] == owner_id
    )


def receipt_binding(receipt):
    preimage = receipt["preimage"]
    return {
        "owner_id": preimage["owner_id"],
        "episode_id": preimage["episode_id"],
        "query_id": preimage["query_id"],
        "q": preimage["q"],
        "object_id": preimage["object_id"],
        "purpose": preimage["purpose"],
        "relation_revision": preimage["relation_revision"],
        "relation_revision_hash": preimage["relation_revision_hash"],
        "relation_version_hash": preimage["relation_version_hash"],
        "scope": preimage["scope"],
    }


class FixtureIsolationAttacks(unittest.TestCase):
    def test_private_profile_sentinels_do_not_reflect_and_mutation_is_owner_local(self):
        marker_prefix = "PRIVATE_PROFILE_MUST_NOT_LEAK_"
        with tempfile.TemporaryDirectory(prefix="g2-c-profile-isolation-") as tmp:
            tmp_path = Path(tmp)
            owner_descriptors = {}
            for owner_id in OWNERS:
                source = json.loads(
                    (ROOT / "profiles" / f"{owner_id}.json").read_text(
                        encoding="utf-8"
                    )
                )
                private_case = {
                    "support": owner_id != "O_V",
                    "authorize": True,
                    "activate": True,
                    "private_secret_marker": marker_prefix + owner_id,
                    "private_full_profile_blob": {
                        "only_for": owner_id,
                        "must_not_cross_process": True,
                    },
                }
                if owner_id == "O_R":
                    private_case["column_state"] = "DISCLOSED"
                source["cases"]["PRIVACY_ATTACK"] = private_case
                profile_path = tmp_path / f"{owner_id}-private.json"
                profile_path.write_text(
                    json.dumps(source, ensure_ascii=False),
                    encoding="utf-8",
                )
                owner_descriptors[owner_id] = {
                    "worker_source": str(ROOT / "owner_worker.py"),
                    "profile_source": str(profile_path),
                }
            endpoint_path = tmp_path / "endpoints.json"
            endpoint_path.write_text(
                json.dumps({"owners": owner_descriptors}),
                encoding="utf-8",
            )

            config = e2(
                "PRIVACY_ATTACK",
                endpoint_manifest=str(endpoint_path),
            )
            output = run_scenario(config)
            visible_controller_surface = json.dumps(
                {"config": config, "output": output},
                ensure_ascii=False,
                sort_keys=True,
            )

            for owner_id in OWNERS:
                self.assertNotIn(marker_prefix + owner_id, visible_controller_surface)
            self.assertNotIn("private_full_profile_blob", visible_controller_surface)
            self.assertEqual(
                output["axis_evidence"]["claimed"]["owner_states"]["O_V"],
                "UNKNOWN_OWNER_POLICY_MISSING_OR_NO_DECISION",
            )
            self.assertEqual(
                output["axis_evidence"]["claimed"]["owner_states"]["O_Q"],
                "SUPPORTED_BY_VERIFIED_OWNER_ACT",
            )
            for item in output["process_manifests"]:
                self.assertEqual(set(item["profile_source"]), {"id", "sha256"})
                self.assertNotIn("path", item["profile_source"])
                self.assertNotIn("cases", item["profile_source"])

    def test_controller_visible_complete_profiles_are_rejected(self):
        exposed = {
            owner: json.loads(
                (ROOT / "profiles" / f"{owner}.json").read_text(encoding="utf-8")
            )
            for owner in OWNERS
        }
        with self.assertRaisesRegex(ValueError, "owner_profiles"):
            run_scenario(e2(owner_profiles=exposed))


class ProcessAndEvidenceAttacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = run_scenario(e2(), run_id="c-fix-rerun-1")
        cls.second = run_scenario(e2(), run_id="c-fix-rerun-2")

    def test_five_owners_do_not_reuse_pid_process_instance_or_key(self):
        first = self.first["process_manifests"]
        second = self.second["process_manifests"]
        for manifests in (first, second):
            self.assertEqual({item["owner_id"] for item in manifests}, set(OWNERS))
            self.assertEqual(len({item["pid"] for item in manifests}), 5)
            self.assertEqual(len({item["process_instance_id"] for item in manifests}), 5)
            self.assertEqual(len({item["key_id"] for item in manifests}), 5)
            self.assertEqual(len({item["public_key_b64"] for item in manifests}), 5)
        self.assertEqual(len({item["pid"] for item in first + second}), 10)
        self.assertEqual(
            len({item["process_instance_id"] for item in first + second}), 10
        )
        self.assertEqual(len({item["key_id"] for item in first + second}), 10)
        self.assertTrue(
            all(
                record["returncode"] == 0
                for output in (self.first, self.second)
                for record in output["process_exits"]
            )
        )

    def test_reused_pid_process_instance_and_key_are_rejected_not_just_reported(self):
        with tempfile.TemporaryDirectory(prefix="g2-c-owner-collision-") as tmp:
            tmp_path = Path(tmp)
            worker_path = tmp_path / "colliding_owner_worker.py"
            worker_path.write_text(COLLIDING_OWNER_WORKER, encoding="utf-8")
            endpoint_path = tmp_path / "endpoints.json"
            endpoint_path.write_text(
                json.dumps(
                    {
                        "owners": {
                            owner_id: {
                                "worker_source": str(worker_path),
                                "profile_source": str(
                                    ROOT / "profiles" / f"{owner_id}.json"
                                ),
                            }
                            for owner_id in OWNERS
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                (ReceiptVerificationError, ValueError),
                "reuse|duplicate|distinct|collision",
            ):
                run_scenario(
                    e2(endpoint_manifest=str(endpoint_path)),
                    run_id="c-fix-colliding-owner-identities",
                )

    def test_raw_bytes_signatures_queries_and_manifests_verify_independently(self):
        for output in (self.first, self.second):
            manifests = {
                item["owner_id"]: item for item in output["process_manifests"]
            }
            for owner_id, manifest in manifests.items():
                source_path = Path(manifest["source"]["path"])
                self.assertEqual(
                    sha256(source_path.read_bytes()).hexdigest(),
                    manifest["source"]["sha256"],
                )
                profile_path = ROOT / "profiles" / manifest["profile_source"]["id"]
                self.assertEqual(
                    sha256(profile_path.read_bytes()).hexdigest(),
                    manifest["profile_source"]["sha256"],
                )
                self.assertEqual(manifest["owner_id"], owner_id)

            for receipt in output["owner_acts"]:
                raw = base64.b64decode(receipt["raw_bytes_b64"], validate=True)
                signature = base64.b64decode(
                    receipt["signature_b64"], validate=True
                )
                public_raw = base64.b64decode(
                    receipt["public_key_b64"], validate=True
                )
                preimage = json.loads(raw)
                manifest = manifests[preimage["owner_id"]]
                self.assertEqual(raw, canonical_bytes(receipt["preimage"]))
                self.assertEqual(preimage, receipt["preimage"])
                self.assertEqual(sha256(raw).hexdigest(), receipt["act_hash"])
                self.assertEqual(
                    sha256(raw).hexdigest(), receipt["raw_bytes_sha256"]
                )
                self.assertEqual(
                    receipt["public_key_b64"], manifest["public_key_b64"]
                )
                self.assertEqual(receipt["key_id"], manifest["key_id"])
                self.assertEqual(preimage["source"], manifest["source"])
                self.assertEqual(preimage["process"]["pid"], manifest["pid"])
                self.assertEqual(
                    preimage["process"]["instance_id"],
                    manifest["process_instance_id"],
                )
                self.assertEqual(
                    preimage["process"]["key_id"], manifest["key_id"]
                )
                try:
                    Ed25519PublicKey.from_public_bytes(public_raw).verify(
                        signature, raw
                    )
                except InvalidSignature as exc:  # pragma: no cover - assertion aid
                    self.fail(f"independent Ed25519 verification failed: {exc}")

            for record in output["trace"]:
                if record["event"] != "owner_query":
                    continue
                request_raw = base64.b64decode(
                    record["request_raw_bytes_b64"], validate=True
                )
                request = json.loads(request_raw)
                self.assertEqual(
                    sha256(request_raw).hexdigest(),
                    record["request_raw_bytes_sha256"],
                )
                self.assertEqual(request["owner_id"], record["owner_id"])
                self.assertEqual(request["episode_id"], output["episode_id"])
                self.assertEqual(request["q"], output["q"])
                self.assertEqual(request["object_id"], output["object_id"])
                self.assertEqual(request["purpose"], output["purpose"])

    def test_dual_run_semantics_reproduce_without_runtime_identity_reuse(self):
        self.assertEqual(
            semantic_projection(self.first),
            semantic_projection(self.second),
        )
        self.assertNotEqual(
            {act["act_hash"] for act in self.first["owner_acts"]},
            {act["act_hash"] for act in self.second["owner_acts"]},
        )
        for output in (self.first, self.second):
            self.assertEqual(
                output["evidence_boundaries"],
                {
                    "evidence_origin": "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY",
                    "real_owner_identity": "NOT_ESTABLISHED",
                    "real_owner": "NOT_RUN",
                    "authority": "NOT_ESTABLISHED",
                    "legal_sufficiency": "NOT_ESTABLISHED",
                    "effect": "NOT_RUN",
                    "acceptance": "NOT_RUN",
                    "settlement": "NOT_RUN",
                    "relation_version": (
                        "DERIVED_ESTABLISHED_G2_SNAPSHOT_NOT_OWNER_OR_AUTHORITY_OR_EFFECT_OR_ACCEPTANCE"
                    ),
                },
            )


class PersistedEvidenceAttacks(unittest.TestCase):
    def test_saved_dual_runs_raw_trace_and_manifests_are_independently_checkable(self):
        output_dir = ROOT / "outputs"
        runs = [
            json.loads(
                (output_dir / f"rerun-{number}.json").read_text(encoding="utf-8")
            )
            for number in (1, 2)
        ]
        raw_trace = json.loads(
            (output_dir / "raw-trace.json").read_text(encoding="utf-8")
        )
        saved_semantic = json.loads(
            (output_dir / "semantic-rerun.json").read_text(encoding="utf-8")
        )
        source_manifest = json.loads(
            (output_dir / "process-source-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        summary = json.loads(
            (output_dir / "summary.json").read_text(encoding="utf-8")
        )

        expected_scenario_count = sum(
            len(json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8")))
            for name in ("e2.json", "e0.json")
        )
        self.assertEqual(
            [len(run) for run in runs],
            [expected_scenario_count, expected_scenario_count],
        )
        self.assertEqual(summary["scenarios_per_run"], expected_scenario_count)
        self.assertEqual(
            raw_trace,
            [
                record
                for run in runs
                for output in run
                for record in output["trace"]
            ],
        )
        recomputed_semantic = [
            [semantic_projection(output) for output in run] for run in runs
        ]
        self.assertEqual(saved_semantic, recomputed_semantic)
        self.assertEqual(saved_semantic[0], saved_semantic[1])
        self.assertTrue(summary["semantic_rerun_equal"])
        self.assertEqual(
            summary["trace_canonical_sha256"],
            sha256(canonical_bytes(raw_trace)).hexdigest(),
        )

        runtime_records = {
            (item["run_id"], item["episode_id"]): item
            for item in source_manifest["worker_runtime_manifests"]
        }
        receipt_count = 0
        all_manifests = []
        for run in runs:
            for output in run:
                record = runtime_records[(output["run_id"], output["episode_id"])]
                self.assertEqual(
                    record["process_manifests"], output["process_manifests"]
                )
                self.assertEqual(record["process_exits"], output["process_exits"])
                manifests = {
                    item["owner_id"]: item for item in output["process_manifests"]
                }
                all_manifests.extend(output["process_manifests"])
                receipts = list(output["owner_acts"])
                if output["path"] == "T5_PLATFORM_DIRECT_BYPASS":
                    receipts.extend(
                        [
                            output["bypass_evidence"]["capability_proof"],
                            output["bypass_evidence"]["capability_readback"],
                        ]
                    )
                receipt_count += len(receipts)
                for receipt in receipts:
                    raw = base64.b64decode(
                        receipt["raw_bytes_b64"], validate=True
                    )
                    signature = base64.b64decode(
                        receipt["signature_b64"], validate=True
                    )
                    public_raw = base64.b64decode(
                        receipt["public_key_b64"], validate=True
                    )
                    preimage = json.loads(raw)
                    manifest = manifests[preimage["owner_id"]]
                    self.assertEqual(raw, canonical_bytes(receipt["preimage"]))
                    self.assertEqual(sha256(raw).hexdigest(), receipt["act_hash"])
                    self.assertEqual(
                        sha256(raw).hexdigest(), receipt["raw_bytes_sha256"]
                    )
                    self.assertEqual(
                        receipt["public_key_b64"], manifest["public_key_b64"]
                    )
                    self.assertEqual(receipt["key_id"], manifest["key_id"])
                    self.assertEqual(preimage["source"], manifest["source"])
                    self.assertEqual(preimage["episode_id"], output["episode_id"])
                    self.assertEqual(preimage["q"], output["q"])
                    self.assertEqual(preimage["object_id"], output["object_id"])
                    self.assertEqual(preimage["process"]["pid"], manifest["pid"])
                    self.assertEqual(
                        preimage["process"]["instance_id"],
                        manifest["process_instance_id"],
                    )
                    Ed25519PublicKey.from_public_bytes(public_raw).verify(
                        signature, raw
                    )

        self.assertEqual(receipt_count, summary["signed_receipts"])
        self.assertEqual(len(all_manifests), summary["process_instances"])
        self.assertEqual(
            len({item["pid"] for item in all_manifests}),
            summary["unique_pids"],
        )
        self.assertEqual(
            len({item["key_id"] for item in all_manifests}),
            summary["unique_key_ids"],
        )
        source_drift = []
        for field in (
            "runner",
            "controller",
            "owner_worker",
            "platform_worker",
        ):
            record = source_manifest[field]
            if sha256((ROOT / record["path"]).read_bytes()).hexdigest() != record["sha256"]:
                source_drift.append(field)
        for record in source_manifest["fixtures"]:
            self.assertEqual(
                sha256((ROOT / record["path"]).read_bytes()).hexdigest(),
                record["sha256"],
            )
        if source_drift:
            # fix2 intentionally leaves outputs untouched until root review.
            # Drift must remain explicit: the prior dual-run package is not
            # evidence for the changed implementation.
            self.assertTrue(
                {"runner", "controller", "owner_worker", "platform_worker"}
                <= set(source_drift)
            )


class ReceiptForgeryAttacks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output = run_scenario(e2(), run_id="c-fix-receipt-attacks")

    def test_forged_act_hash_alone_is_rejected(self):
        receipt = deepcopy(self.output["owner_acts"][0])
        manifest = manifest_for(self.output, receipt["preimage"]["owner_id"])
        receipt["act_hash"] = "0" * 64
        with self.assertRaisesRegex(ReceiptVerificationError, "hash mismatch"):
            verify_receipt(receipt, manifest, receipt_binding(receipt))

    def test_payload_tamper_with_recomputed_digest_is_still_rejected_by_signature(self):
        receipt = deepcopy(
            next(
                act
                for act in self.output["owner_acts"]
                if act["preimage"]["kind"] == "CLAIM"
            )
        )
        manifest = manifest_for(self.output, receipt["preimage"]["owner_id"])
        expected = receipt_binding(receipt)
        receipt["preimage"]["payload"]["claim"] = "FORGED_EXACT_VERSION"
        forged_raw = canonical_bytes(receipt["preimage"])
        forged_hash = sha256(forged_raw).hexdigest()
        receipt["raw_bytes_b64"] = base64.b64encode(forged_raw).decode("ascii")
        receipt["raw_bytes_sha256"] = forged_hash
        receipt["act_hash"] = forged_hash
        receipt["act_id"] = "act-" + forged_hash[:20]
        self.assertEqual(
            sha256(base64.b64decode(receipt["raw_bytes_b64"])).hexdigest(),
            receipt["act_hash"],
        )
        with self.assertRaisesRegex(ReceiptVerificationError, "signature"):
            verify_receipt(receipt, manifest, expected)

    def test_bad_signature_is_rejected(self):
        receipt = deepcopy(self.output["owner_acts"][0])
        manifest = manifest_for(self.output, receipt["preimage"]["owner_id"])
        signature = bytearray(base64.b64decode(receipt["signature_b64"]))
        signature[-1] ^= 1
        receipt["signature_b64"] = base64.b64encode(signature).decode("ascii")
        with self.assertRaisesRegex(ReceiptVerificationError, "signature"):
            verify_receipt(receipt, manifest, receipt_binding(receipt))

    def test_wrong_owner_key_substitution_is_rejected(self):
        receipt = deepcopy(
            next(
                act
                for act in self.output["owner_acts"]
                if act["preimage"]["owner_id"] == "O_V"
            )
        )
        wrong_manifest = manifest_for(self.output, "O_Q")
        expected = receipt_binding(receipt)
        expected["owner_id"] = "O_Q"
        with self.assertRaisesRegex(ReceiptVerificationError, "public key"):
            verify_receipt(receipt, wrong_manifest, expected)

    def test_every_exact_binding_dimension_rejects_substitution(self):
        receipt = next(
            act
            for act in self.output["owner_acts"]
            if act["preimage"]["kind"] == "CLAIM"
        )
        manifest = manifest_for(self.output, receipt["preimage"]["owner_id"])
        attacks = {
            "episode_id": "CE001-WRONG-EPISODE",
            "q": {**receipt["preimage"]["q"], "version": "Q@wrong"},
            "object_id": "Venue-V/Circuit-C8",
            "purpose": "WRONG_PURPOSE",
            "relation_revision": "v999",
            "relation_revision_hash": "wrong-revision-hash",
            "relation_version_hash": "wrong-relation-version-hash",
        }
        for field, wrong_value in attacks.items():
            with self.subTest(field=field):
                expected = receipt_binding(receipt)
                expected[field] = wrong_value
                with self.assertRaisesRegex(
                    ReceiptVerificationError,
                    f"exact binding mismatch: {field}",
                ):
                    verify_receipt(receipt, manifest, expected)


class OwnerPolicyAndOppositionAttacks(unittest.TestCase):
    def test_missing_owner_policy_keeps_all_five_axes_unknown(self):
        output = run_scenario(e2("MISSING_ALL"))
        for axis in AXES:
            with self.subTest(axis=axis):
                states = output["axis_evidence"][axis]["owner_states"]
                self.assertEqual(set(states), set(OWNERS))
                self.assertTrue(
                    all(state.startswith("UNKNOWN") for state in states.values())
                )
        self.assertFalse(
            any(
                act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_refusal_is_blocking_and_stops_refuser_downstream(self):
        output = run_scenario(e2("SAFETY_REFUSAL"))
        self.assertEqual(
            output["axis_evidence"]["claimed"]["owner_states"]["O_S"],
            "REFUSED_BLOCKING",
        )
        self.assertTrue(
            output["axis_evidence"]["claimed"]["opposing_act_ids"]
        )
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_S"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_blocking_opposition_is_preserved_and_stops_owner_downstream(self):
        output = run_scenario(e2("BLOCKING_OPPOSITION"))
        self.assertEqual(
            output["axis_evidence"]["claimed"]["owner_states"]["O_V"],
            "BLOCKING_OPPOSITION",
        )
        self.assertEqual(
            output["opposition"][0]["opposition"]["position"],
            "DO_NOT_SUPPLY_C7",
        )
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] in {"AUTHORIZE", "ACTIVATE"}
                for act in output["owner_acts"]
            )
        )

    def test_nonblocking_opposition_is_preserved_without_erasing_support(self):
        output = run_scenario(e2())
        self.assertEqual(
            output["axis_evidence"]["claimed"]["owner_states"]["O_V"],
            "CLAIMED_WITH_SCOPED_OPPOSITION",
        )
        claim = next(
            act
            for act in output["owner_acts"]
            if act["preimage"]["owner_id"] == "O_V"
            and act["preimage"]["kind"] == "CLAIM_WITH_OPPOSITION"
        )
        self.assertIn(
            claim["act_id"],
            output["axis_evidence"]["claimed"]["supporting_act_ids"],
        )
        self.assertIn(
            claim["act_id"],
            output["axis_evidence"]["claimed"]["opposing_act_ids"],
        )
        self.assertEqual(
            claim["preimage"]["payload"]["opposition"]["position"],
            "BATTERY_ONLY",
        )
        self.assertTrue(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] == "AUTHORIZE"
                for act in output["owner_acts"]
            )
        )
        self.assertTrue(
            any(
                act["preimage"]["owner_id"] == "O_V"
                and act["preimage"]["kind"] == "ACTIVATE"
                for act in output["owner_acts"]
            )
        )


class PlatformNativeAttacks(unittest.TestCase):
    def test_t5_rejects_bare_boolean(self):
        with self.assertRaisesRegex(ValueError, "bare"):
            run_scenario(platform(platform_direct_applicable=True))

    def test_t5_rejects_missing_native_proof(self):
        with self.assertRaisesRegex(ReceiptVerificationError, "not applicable"):
            run_scenario(platform(platform_profile_case="MISSING_PROOF"))

    def test_t5_rejects_missing_native_readback(self):
        with tempfile.TemporaryDirectory(prefix="g2-c-platform-readback-") as tmp:
            tmp_path = Path(tmp)
            profile_path = tmp_path / "platform.json"
            profile_path.write_text(
                json.dumps(
                    {
                        "owner_id": "PLATFORM_VENUE_NATIVE",
                        "cases": {
                            "NO_READBACK": {
                                "native_target": "Venue-V/Circuit-C7",
                                "complete_task_capability": True,
                                "authority_stratum": "U",
                                "readback_available": False,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            endpoint_path = tmp_path / "endpoints.json"
            endpoint_path.write_text(
                json.dumps(
                    {
                        "platform": {
                            "worker_source": str(ROOT / "platform_worker.py"),
                            "profile_source": str(profile_path),
                        }
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ReceiptVerificationError, "missing or wrong-bound"
            ):
                run_scenario(
                    platform(
                        endpoint_manifest=str(endpoint_path),
                        platform_profile_case="NO_READBACK",
                    )
                )

    def test_t5_rejects_wrong_object_binding(self):
        with self.assertRaisesRegex(ReceiptVerificationError, "object_id"):
            run_scenario(
                platform(platform_profile_case="WRONG_READBACK_OBJECT")
            )

    def test_t5_rejects_bad_platform_signature(self):
        original_query = g2_relation.SignedProcess.query

        def corrupt_signature(process, request, trace):
            receipt = original_query(process, request, trace)
            if (
                process.owner_id == "PLATFORM_VENUE_NATIVE"
                and request["kind"] == "CAPABILITY_PROOF"
            ):
                signature = bytearray(
                    base64.b64decode(receipt["signature_b64"])
                )
                signature[0] ^= 1
                receipt["signature_b64"] = base64.b64encode(signature).decode(
                    "ascii"
                )
            return receipt

        with mock.patch.object(
            g2_relation.SignedProcess,
            "query",
            new=corrupt_signature,
        ):
            with self.assertRaisesRegex(ReceiptVerificationError, "signature"):
                run_scenario(platform())

    def test_t5_rejects_signed_source_manifest_substitution(self):
        original_query = g2_relation.SignedProcess.query

        def substitute_manifest_source(process, request, trace):
            receipt = original_query(process, request, trace)
            if (
                process.owner_id == "PLATFORM_VENUE_NATIVE"
                and request["kind"] == "CAPABILITY_PROOF"
            ):
                process.manifest["source"] = {
                    **process.manifest["source"],
                    "sha256": "0" * 64,
                }
            return receipt

        with mock.patch.object(
            g2_relation.SignedProcess,
            "query",
            new=substitute_manifest_source,
        ):
            with self.assertRaisesRegex(ReceiptVerificationError, "source"):
                run_scenario(platform())


class AxisAndClaimBoundaryAttacks(unittest.TestCase):
    def test_authorized_activated_remain_g5_g6_unverified_without_green_total(self):
        output = run_scenario(e2())
        authorized = output["axis_evidence"]["authorized"]
        activated = output["axis_evidence"]["activated"]
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
        self.assertFalse(
            any(
                act["preimage"]["owner_id"] == "O_E"
                for act in output["owner_acts"]
            )
        )
        self.assertTrue(
            all(
                act["preimage"]["payload"]["effect_asserted"] is False
                for act in output["owner_acts"]
                if act["preimage"]["kind"] == "ACTIVATE"
            )
        )
        self.assertTrue(
            {
                "green",
                "success",
                "relation_valid",
                "overall_status",
                "result",
            }.isdisjoint(output)
        )
        self.assertTrue(
            all(
                output["axis_evidence"][axis]["global_status"]
                == "NOT_COMPUTED"
                for axis in AXES
            )
        )
        self.assertTrue(
            {
                "NOT_AN_OWNER_ACT",
                "NOT_AUTHORITY",
                "NOT_EFFECT",
                "NOT_ACCEPTANCE",
            }
            <= set(output["relation_version"]["non_entailments"])
        )
        self.assertEqual(output["evidence_boundaries"]["real_owner"], "NOT_RUN")
        self.assertEqual(
            output["evidence_boundaries"]["legal_sufficiency"], "NOT_ESTABLISHED"
        )
        self.assertEqual(output["evidence_boundaries"]["effect"], "NOT_RUN")
        self.assertEqual(
            output["evidence_boundaries"]["acceptance"], "NOT_RUN"
        )


if __name__ == "__main__":
    unittest.main()
