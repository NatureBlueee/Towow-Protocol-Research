"""Shared message, signature, and persistence primitives for Wave 005-B.

The experiment uses Ed25519 from the already-installed ``cryptography``
package.  Keys in this experiment are deterministic synthetic test keys; they
must never be reused outside this local simulation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class ProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(
                value,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def sign_envelope(
    private_key: Ed25519PrivateKey,
    *,
    kind: str,
    issuer: str,
    key_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    unsigned = {
        "schema": "towow.cross-authority-envelope.v1",
        "kind": kind,
        "issuer": issuer,
        "key_id": key_id,
        "body": copy.deepcopy(body),
    }
    signature = private_key.sign(canonical_bytes(unsigned)).hex()
    return {**unsigned, "signature": signature}


def envelope_hash(envelope: dict[str, Any]) -> str:
    return sha256_value(envelope)


def public_key_entry(
    contract: dict[str, Any], issuer: str, key_id: str
) -> dict[str, Any]:
    for entry in contract.get("verification_keys", []):
        if entry["issuer"] == issuer and entry["key_id"] == key_id:
            return entry
    raise ProtocolError(
        "UNKNOWN_SIGNING_KEY",
        f"No verification key is registered for {issuer}/{key_id}.",
    )


def verify_envelope(
    envelope: dict[str, Any],
    contract: dict[str, Any],
    *,
    expected_kind: str,
    step: int,
    expected_issuer: str | None = None,
) -> dict[str, Any]:
    required = {
        "schema",
        "kind",
        "issuer",
        "key_id",
        "body",
        "signature",
    }
    if set(envelope) != required:
        raise ProtocolError(
            "SIGNED_ENVELOPE_MALFORMED",
            "Signed envelope fields are missing or unexpected.",
        )
    if envelope["schema"] != "towow.cross-authority-envelope.v1":
        raise ProtocolError("SIGNED_ENVELOPE_MALFORMED", "Unknown schema.")
    if envelope["kind"] != expected_kind:
        raise ProtocolError(
            "SIGNED_KIND_MISMATCH",
            f"Expected {expected_kind}, got {envelope['kind']}.",
        )
    if expected_issuer is not None and envelope["issuer"] != expected_issuer:
        raise ProtocolError(
            "SIGNED_ISSUER_MISMATCH",
            f"Expected issuer {expected_issuer}, got {envelope['issuer']}.",
        )

    entry = public_key_entry(
        contract, envelope["issuer"], envelope["key_id"]
    )
    if not entry["valid_from_step"] <= step <= entry["valid_through_step"]:
        raise ProtocolError(
            "SIGNING_KEY_NOT_VALID",
            "The signing key is not valid at the frozen evaluation step.",
        )

    unsigned = {key: envelope[key] for key in required if key != "signature"}
    try:
        signature = bytes.fromhex(envelope["signature"])
        public_key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(entry["public_key_hex"])
        )
        public_key.verify(signature, canonical_bytes(unsigned))
    except (ValueError, InvalidSignature) as error:
        raise ProtocolError(
            "SIGNATURE_INVALID",
            "The envelope signature does not verify.",
        ) from error
    return copy.deepcopy(envelope["body"])


def private_key_from_hex(seed_hex: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))

