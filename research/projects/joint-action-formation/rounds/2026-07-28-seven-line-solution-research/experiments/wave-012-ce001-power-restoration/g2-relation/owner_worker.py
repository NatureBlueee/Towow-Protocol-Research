#!/usr/bin/env python3
"""Owner-local CE-001 decision process.

The controller starts one long-lived instance per owner.  This process alone
loads that owner's private profile and creates that owner's private signing
key.  Stdout is a JSON-lines protocol containing a public manifest followed by
signed receipts; private profile contents and private key bytes never cross the
process boundary.
"""

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
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def hash_bytes(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def digest(value: Any) -> str:
    return hash_bytes(canonical_bytes(value))


LOCAL_TRUST_CLASS = "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY"
REQUEST_SCHEMA_VERSION = "ce001-g2-request-v3"
RECEIPT_SCHEMA_VERSION = "ce001-owner-receipt-v3"


def source_descriptor(path: Path) -> dict[str, str]:
    raw = path.read_bytes()
    return {"id": path.name, "path": str(path), "sha256": hash_bytes(raw)}


def decide(kind: str, profile: dict[str, Any], request: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    has_policy = bool(profile)
    if kind == "PRIVATE_COLUMN":
        state = profile.get("column_state", "UNKNOWN")
        payload: dict[str, Any] = {"column_state": state}
        if state == "DISCLOSED":
            payload["column"] = {
                "role": "RESOURCE_PROVIDER",
                "action": "SUPPLY_C7",
                "capacity_kw": 3.0,
                "duration_minutes": 45,
            }
        return f"PRIVATE_COLUMN_{state}", state, payload

    if profile.get("refuse"):
        return (
            "REFUSE",
            "REFUSED",
            {"reason": profile.get("refusal_reason", "OWNER_REFUSAL")},
        )
    if not has_policy:
        return "UNKNOWN", "UNKNOWN", {"reason": "OWNER_POLICY_MISSING"}

    if kind == "CONSTITUTE":
        return "CONSTITUTE", "CONSTITUTED", {"stance": "CONSTITUTE_EXACT_REVISION"}
    if kind == "EXPLAIN_BACK":
        clauses = list(request["request_payload"]["required_clause_ids"])
        if profile.get("misunderstand") and clauses:
            clauses = clauses[:-1]
        return "EXPLAIN_BACK", "EXPLAINED", {"explained_clause_ids": clauses}
    if kind == "CLAIM":
        if profile.get("opposition"):
            opposition = profile["opposition"]
            blocking = bool(opposition.get("blocking")) or str(
                opposition.get("position", "")
            ).upper().startswith(("DO_NOT", "DENY", "REFUSE", "WITHDRAW"))
            return (
                "CLAIM_WITH_OPPOSITION",
                "OPPOSED_BLOCKING" if blocking else "CLAIMED_SCOPED",
                {"claim": "SCOPED", "opposition": opposition},
            )
        if profile.get("support") is not True:
            return "UNKNOWN", "UNKNOWN", {"reason": "NO_OWNER_CLAIM"}
        return "CLAIM", "CLAIMED", {"claim": "EXACT_VERSION"}
    if kind == "AUTHORIZE":
        if profile.get("authorize") is not True:
            return "UNKNOWN", "UNKNOWN", {"reason": "NO_OWNER_AUTHORIZATION_INTENT"}
        return (
            "AUTHORIZE",
            "AUTHORIZATION_INTENT",
            {"operation_ids": list(request["operation_ids"])},
        )
    if kind == "ACTIVATE":
        if profile.get("activate") is not True:
            return "UNKNOWN", "UNKNOWN", {"reason": "NO_OWNER_ACTIVATION_INTENT"}
        return (
            "ACTIVATE",
            "ACTIVATION_INTENT",
            {
                "operation_ids": list(request["operation_ids"]),
                "effect_asserted": False,
            },
        )
    raise ValueError(f"unsupported owner query kind: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-id", required=True)
    parser.add_argument("--profile-source", required=True)
    parser.add_argument("--profile-case", required=True)
    args = parser.parse_args()

    worker_path = Path(__file__).resolve()
    profile_path = Path(args.profile_source).resolve()
    profile_document = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile_document.get("owner_id") != args.owner_id:
        raise SystemExit("profile owner does not match process owner")
    profile = dict(profile_document.get("cases", {}).get(args.profile_case, {}))

    private_key = Ed25519PrivateKey.generate()
    public_raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    key_id = f"ed25519:{args.owner_id}:{hash_bytes(public_raw)[:24]}"
    process_instance_id = str(uuid.uuid4())
    source = source_descriptor(worker_path)
    profile_source = {
        "id": profile_path.name,
        "sha256": hash_bytes(profile_path.read_bytes()),
    }
    manifest = {
        "type": "owner_ready",
        "owner_id": args.owner_id,
        "pid": os.getpid(),
        "process_instance_id": process_instance_id,
        "key_id": key_id,
        "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
        "source": source,
        "profile_source": profile_source,
        "evidence_origin": LOCAL_TRUST_CLASS,
        "trust_anchor_status": "NOT_ESTABLISHED",
        "real_owner_identity": "NOT_ESTABLISHED",
        "authority": "NOT_ESTABLISHED",
        "legal_sufficiency": "NOT_ESTABLISHED",
    }
    print(json.dumps(manifest, sort_keys=True), flush=True)

    ordinal = 0
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if request.get("owner_id") != args.owner_id:
                raise ValueError("request owner does not match owner process")
            if request.get("request_schema_version") != REQUEST_SCHEMA_VERSION:
                raise ValueError("unsupported request schema")
            ordinal += 1
            kind, decision, payload = decide(request["kind"], profile, request)
            if profile.get("wrong_response_kind") and request["kind"] == "EXPLAIN_BACK":
                kind, decision, payload = "CLAIM", "CLAIMED", {"claim": "WRONG_KIND"}
            relation_version_hash = request.get("relation_version_hash")
            if profile.get("wrong_version_hash") and request["kind"] == "EXPLAIN_BACK":
                relation_version_hash = profile["wrong_version_hash"]
            if profile.get("wrong_q_hash") and request["kind"] == "CLAIM":
                request = {
                    **request,
                    "q": {**request["q"], "hash": profile["wrong_q_hash"]},
                }
            if profile.get("wrong_object_id") and request["kind"] == "CLAIM":
                request = {**request, "object_id": profile["wrong_object_id"]}
            request_raw = canonical_bytes(request)
            preimage = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "request_schema_version": request["request_schema_version"],
                "owner_id": args.owner_id,
                "run_id": request["run_id"],
                "episode_id": request["episode_id"],
                "query_id": request["query_id"],
                "q": request["q"],
                "object_id": request["object_id"],
                "purpose": request["purpose"],
                "relation_revision": request["relation_revision"],
                "relation_revision_hash": request["relation_revision_hash"],
                "relation_version_hash": relation_version_hash,
                "relation_schema_hash": request["relation_schema_hash"],
                "signed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "decision": decision,
                "kind": kind,
                "requested_kind": request["kind"],
                "scope": request["scope"],
                "payload": payload,
                "operation_ids": request["operation_ids"],
                "request_ordinal": request["request_ordinal"],
                "process_ordinal": request["process_ordinal"],
                "issuer_ordinal": ordinal,
                "request_nonce": request["request_nonce"],
                "request_issued_at": request["issued_at"],
                "request_expires_at": request["expires_at"],
                "request_raw_bytes_b64": base64.b64encode(request_raw).decode("ascii"),
                "request_raw_bytes_sha256": hash_bytes(request_raw),
                "request_payload_sha256": digest(request["request_payload"]),
                "endpoint_binding": request["endpoint_binding"],
                "endpoint_binding_sha256": request["endpoint_binding"]["sha256"],
                "evidence_origin": LOCAL_TRUST_CLASS,
                "trust_anchor_status": "NOT_ESTABLISHED",
                "real_owner_identity": "NOT_ESTABLISHED",
                "authority": "NOT_ESTABLISHED",
                "legal_sufficiency": "NOT_ESTABLISHED",
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
                "type": "owner_receipt",
                "act_id": f"act-{hash_bytes(raw)[:20]}",
                "act_hash": hash_bytes(raw),
                "raw_bytes_b64": base64.b64encode(raw).decode("ascii"),
                "raw_bytes_sha256": hash_bytes(raw),
                "signature_b64": base64.b64encode(signature).decode("ascii"),
                "public_key_b64": base64.b64encode(public_raw).decode("ascii"),
                "key_id": key_id,
                "preimage": preimage,
            }
            print(json.dumps(receipt, sort_keys=True), flush=True)
        except Exception as exc:  # pragma: no cover - protocol failure guard
            print(
                json.dumps({"type": "owner_error", "error": type(exc).__name__, "message": str(exc)}),
                flush=True,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
