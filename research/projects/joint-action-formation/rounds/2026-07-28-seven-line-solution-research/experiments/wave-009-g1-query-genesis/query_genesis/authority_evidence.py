"""Synthetic Authority evidence signing shared by broker and evaluator.

Keys are deterministic fixtures, not production credentials or security
claims.  Sharing one verifier prevents broker/evaluator kind/scope drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
from typing import Iterable


AUTHORITY_EVIDENCE_MODEL_VERSION = "wave009-authority-evidence-v3"


@dataclass(frozen=True)
class SignedAuthorityEvidence:
    kind: str
    signer: str
    scope: str
    version: int
    nonce: str
    signature: str


def semantic_scope(
    purpose: str,
    direction: str,
    constraints: tuple[str, ...],
) -> str:
    payload = {
        "purpose": purpose,
        "direction": direction,
        "constraints": tuple(sorted(constraints)),
    }
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixture_key(signer: str) -> bytes:
    return sha256(f"wave009-fixture-key:{signer}".encode()).digest()


def _payload(
    *,
    kind: str,
    signer: str,
    scope: str,
    version: int,
    nonce: str,
) -> bytes:
    return json.dumps(
        {
            "kind": kind,
            "signer": signer,
            "scope": scope,
            "version": version,
            "nonce": nonce,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def sign_authority_evidence(
    kind: str,
    signer: str,
    scope: str,
    *,
    version: int = 1,
    nonce: str,
) -> SignedAuthorityEvidence:
    payload = _payload(
        kind=kind,
        signer=signer,
        scope=scope,
        version=version,
        nonce=nonce,
    )
    signature = hmac.new(_fixture_key(signer), payload, sha256).hexdigest()
    return SignedAuthorityEvidence(
        kind=kind,
        signer=signer,
        scope=scope,
        version=version,
        nonce=nonce,
        signature=signature,
    )


def verify_authority_evidence(
    evidence: SignedAuthorityEvidence | None,
    *,
    allowed_kinds: Iterable[str],
    expected_scope: str,
    expected_signer: str | None = None,
) -> bool:
    if not isinstance(evidence, SignedAuthorityEvidence):
        return False
    if evidence.kind not in set(allowed_kinds):
        return False
    if evidence.scope != expected_scope:
        return False
    if expected_signer is not None and evidence.signer != expected_signer:
        return False
    payload = _payload(
        kind=evidence.kind,
        signer=evidence.signer,
        scope=evidence.scope,
        version=evidence.version,
        nonce=evidence.nonce,
    )
    expected = hmac.new(
        _fixture_key(evidence.signer),
        payload,
        sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, evidence.signature)
