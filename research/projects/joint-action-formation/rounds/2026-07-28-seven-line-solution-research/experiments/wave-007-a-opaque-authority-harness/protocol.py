#!/usr/bin/env python3
"""Public bytes, normalization and signature verification for Wave 007-A."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class EvidenceError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def normalize_request(raw: dict[str, Any]) -> dict[str, Any]:
    request = copy.deepcopy(raw)
    schema = request.get("schema")
    if schema == "towow.sterile-route-request.alias-v1":
        if "environment_version" in request and "environmentVersion" in request:
            raise EvidenceError("SCHEMA_ALIAS_CONFLICT")
        if "environmentVersion" not in request:
            raise EvidenceError("SCHEMA_ALIAS_INCOMPLETE")
        request["environment_version"] = request.pop("environmentVersion")
        request["schema"] = "towow.sterile-route-request.v1"
    elif schema != "towow.sterile-route-request.v1":
        raise EvidenceError("REQUEST_SCHEMA_UNSUPPORTED")

    expected = {
        "schema",
        "operation",
        "purpose",
        "retention",
        "environment_version",
        "idempotency_key",
        "command",
    }
    if set(request) != expected:
        raise EvidenceError("REQUEST_FIELDS_INVALID")
    if request["operation"] != "RUN-STERILE-ROUTE-SIM-v1":
        raise EvidenceError("OPERATION_MISMATCH")
    if request["purpose"] != "sterile-route-simulation":
        raise EvidenceError("PURPOSE_MISMATCH")
    if not isinstance(request["command"], dict):
        raise EvidenceError("COMMAND_INVALID")
    return request


def request_sha256(request: dict[str, Any]) -> str:
    return sha256_value(normalize_request(request))


def sign_envelope(
    private_key: Ed25519PrivateKey,
    *,
    issuer: str,
    kind: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    signing_body = {
        "issuer": issuer,
        "key_id": "w7-v1",
        "kind": kind,
        "body": body,
    }
    return {
        **signing_body,
        "body_sha256": sha256_value(body),
        "signature_hex": private_key.sign(
            canonical_bytes(signing_body)
        ).hex(),
    }


def envelope_sha256(envelope: dict[str, Any]) -> str:
    return sha256_value(envelope)


def verify_envelope(
    envelope: dict[str, Any],
    public_registry: dict[str, str],
    *,
    expected_issuer: str | None = None,
    expected_kind: str | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        raise EvidenceError("ENVELOPE_MISSING")
    issuer = envelope.get("issuer")
    kind = envelope.get("kind")
    if expected_issuer is not None and issuer != expected_issuer:
        raise EvidenceError("ISSUER_MISMATCH")
    if expected_kind is not None and kind != expected_kind:
        raise EvidenceError("KIND_MISMATCH")
    if issuer not in public_registry:
        raise EvidenceError("ISSUER_UNKNOWN")
    body = envelope.get("body")
    if not isinstance(body, dict) or envelope.get("body_sha256") != sha256_value(body):
        raise EvidenceError("BODY_HASH_INVALID")
    signing_body = {
        "issuer": issuer,
        "key_id": envelope.get("key_id"),
        "kind": kind,
        "body": body,
    }
    try:
        Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(public_registry[issuer])
        ).verify(
            bytes.fromhex(envelope.get("signature_hex", "")),
            canonical_bytes(signing_body),
        )
    except (InvalidSignature, ValueError):
        raise EvidenceError("SIGNATURE_INVALID")
    return body
