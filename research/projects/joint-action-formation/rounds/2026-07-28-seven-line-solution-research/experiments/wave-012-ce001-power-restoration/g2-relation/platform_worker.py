#!/usr/bin/env python3
"""Independent platform-native applicability proof/readback process."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
import uuid
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def h(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def digest(value: Any) -> str:
    return h(canonical_bytes(value))


LOCAL_TRUST_CLASS = "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY"
REQUEST_SCHEMA_VERSION = "ce001-g2-request-v3"
RECEIPT_SCHEMA_VERSION = "ce001-platform-receipt-v2"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile-source", required=True)
    parser.add_argument("--profile-case", required=True)
    args = parser.parse_args()
    worker_path = Path(__file__).resolve()
    profile_path = Path(args.profile_source).resolve()
    profile_doc = json.loads(profile_path.read_text(encoding="utf-8"))
    profile = dict(profile_doc.get("cases", {}).get(args.profile_case, {}))
    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    process_instance_id = str(uuid.uuid4())
    key_id = f"ed25519:PLATFORM:{h(public_raw)[:24]}"
    source = {
        "id": worker_path.name,
        "path": str(worker_path),
        "sha256": h(worker_path.read_bytes()),
    }
    manifest = {
        "type": "platform_ready",
        "owner_id": "PLATFORM_VENUE_NATIVE",
        "pid": os.getpid(),
        "process_instance_id": process_instance_id,
        "key_id": key_id,
        "public_key_b64": base64.b64encode(public_raw).decode(),
        "source": source,
        "profile_source": {"id": profile_path.name, "sha256": h(profile_path.read_bytes())},
        "evidence_origin": LOCAL_TRUST_CLASS,
        "trust_anchor_status": "NOT_ESTABLISHED",
        "real_platform_identity": "NOT_ESTABLISHED",
        "real_platform_applicability": "NOT_ESTABLISHED",
    }
    print(json.dumps(manifest, sort_keys=True), flush=True)

    proof_hash: str | None = None
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        if request.get("request_schema_version") != REQUEST_SCHEMA_VERSION:
            raise ValueError("unsupported request schema")
        kind = request["kind"]
        if kind == "CAPABILITY_PROOF":
            applicable = (
                profile.get("native_target") == request["object_id"]
                and profile.get("complete_task_capability") is True
                and profile.get("authority_stratum") == "U"
            )
            decision = "APPLICABLE" if applicable else "NOT_APPLICABLE"
            payload = {
                "native_target": profile.get("native_target"),
                "complete_task_capability": profile.get("complete_task_capability", False),
                "local_fixture_profile_scope_label": profile.get(
                    "authority_stratum", "UNKNOWN"
                ),
                "relation_required": False if applicable else None,
                "effect_asserted": False,
            }
        elif kind == "CAPABILITY_READBACK":
            decision = "READBACK_CONFIRMED" if profile.get("readback_available") else "UNKNOWN"
            payload = {
                "capability_proof_hash": request["request_payload"]["capability_proof_hash"],
                "native_target": profile.get("native_target"),
                "capability_state": "AVAILABLE" if profile.get("readback_available") else "UNKNOWN",
                "effect_asserted": False,
            }
            if profile.get("wrong_readback_object"):
                request = {**request, "object_id": profile["wrong_readback_object"]}
        else:
            raise ValueError(f"unsupported platform query: {kind}")
        request_raw = canonical_bytes(request)
        preimage = {
            "schema_version": RECEIPT_SCHEMA_VERSION,
            "request_schema_version": request["request_schema_version"],
            "owner_id": "PLATFORM_VENUE_NATIVE",
            "run_id": request["run_id"],
            "episode_id": request["episode_id"],
            "query_id": request["query_id"],
            "q": request["q"],
            "object_id": request["object_id"],
            "purpose": request["purpose"],
            "relation_revision": request["relation_revision"],
            "relation_revision_hash": request["relation_revision_hash"],
            "relation_version_hash": None,
            "relation_schema_hash": request["relation_schema_hash"],
            "signed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "decision": decision,
            "kind": kind,
            "requested_kind": request["kind"],
            "scope": "PLATFORM_NATIVE_CAPABILITY",
            "payload": payload,
            "operation_ids": request["operation_ids"],
            "request_ordinal": request["request_ordinal"],
            "process_ordinal": request["process_ordinal"],
            "issuer_ordinal": request["process_ordinal"],
            "request_nonce": request["request_nonce"],
            "request_issued_at": request["issued_at"],
            "request_expires_at": request["expires_at"],
            "request_raw_bytes_b64": base64.b64encode(request_raw).decode(),
            "request_raw_bytes_sha256": h(request_raw),
            "request_payload_sha256": digest(request["request_payload"]),
            "endpoint_binding": request["endpoint_binding"],
            "endpoint_binding_sha256": request["endpoint_binding"]["sha256"],
            "evidence_origin": LOCAL_TRUST_CLASS,
            "trust_anchor_status": "NOT_ESTABLISHED",
            "real_platform_identity": "NOT_ESTABLISHED",
            "real_platform_applicability": "NOT_ESTABLISHED",
            "source": source,
            "process": {
                "pid": os.getpid(),
                "instance_id": process_instance_id,
                "key_id": key_id,
            },
        }
        raw = canonical_bytes(preimage)
        signature = private_key.sign(raw)
        receipt = {
            "type": "platform_receipt",
            "act_id": f"platform-{h(raw)[:20]}",
            "act_hash": h(raw),
            "raw_bytes_b64": base64.b64encode(raw).decode(),
            "raw_bytes_sha256": h(raw),
            "signature_b64": base64.b64encode(signature).decode(),
            "public_key_b64": base64.b64encode(public_raw).decode(),
            "key_id": key_id,
            "preimage": preimage,
        }
        if kind == "CAPABILITY_PROOF":
            proof_hash = receipt["act_hash"]
        print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
