"""Small cryptographic and canonicalization helpers shared by public code."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def public_key_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        Encoding.Raw,
        PublicFormat.Raw,
    ).hex()


def sign_envelope(
    key: Ed25519PrivateKey,
    *,
    domain: str,
    issuer: str,
    kind: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    unsigned = {
        "domain": domain,
        "issuer": issuer,
        "kind": kind,
        "body": body,
    }
    payload = canonical_bytes(unsigned)
    return {
        **unsigned,
        "payload_sha256": sha256_hex(payload),
        "signature_hex": key.sign(payload).hex(),
    }


def verify_envelope(
    envelope: dict[str, Any],
    contract: dict[str, Any],
    *,
    expected_domain: str,
) -> bool:
    try:
        if envelope["domain"] != expected_domain:
            return False
        unsigned = {
            "domain": envelope["domain"],
            "issuer": envelope["issuer"],
            "kind": envelope["kind"],
            "body": envelope["body"],
        }
        payload = canonical_bytes(unsigned)
        if sha256_hex(payload) != envelope["payload_sha256"]:
            return False
        public_hex = contract["issuer_keys"][envelope["issuer"]]
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
            bytes.fromhex(envelope["signature_hex"]),
            payload,
        )
        return True
    except (InvalidSignature, KeyError, TypeError, ValueError):
        return False


def opaque_id(namespace: str, coordinate: str, prefix: str) -> str:
    digest = hashlib.sha256(
        f"wave009-hidden-id-key|{namespace}|{coordinate}".encode("utf-8")
    ).hexdigest()[:20]
    return f"{prefix}-{digest}"
