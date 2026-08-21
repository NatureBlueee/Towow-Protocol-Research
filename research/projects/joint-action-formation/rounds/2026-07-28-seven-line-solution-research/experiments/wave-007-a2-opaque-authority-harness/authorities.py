#!/usr/bin/env python3
"""Wave 007-A2 authority state.

A2 reuses A v1's signed stage chain but moves idempotency binding to the first
valid EFFECT_ATTEMPT and tracks L3 postconditions independently from L4
beneficiary acceptances.
"""

from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path
from typing import Any

from protocol import (
    EvidenceError,
    envelope_sha256,
    normalize_request,
    sha256_value,
)


V1_DIR = (
    Path(__file__).resolve().parents[1]
    / "wave-007-a-opaque-authority-harness"
)
_SPEC = importlib.util.spec_from_file_location(
    "wave007_a_v1_authorities_for_a2",
    V1_DIR / "authorities.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load Wave 007-A authority dependency")
_BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BASE
_SPEC.loader.exec_module(_BASE)

AUTHORITY_IDS = _BASE.AUTHORITY_IDS
WITNESS_ALLOWLIST = _BASE.WITNESS_ALLOWLIST
WITNESS_THRESHOLD = _BASE.WITNESS_THRESHOLD
SigningAuthority = _BASE.SigningAuthority
verify_witness_quorum = _BASE.verify_witness_quorum


class AuthorityNetwork(_BASE.AuthorityNetwork):
    """A2 network with attempt-time binding and separate L3/L4 ledgers."""

    def __init__(
        self,
        public_request: dict[str, Any],
        hidden_state: dict[str, Any],
    ):
        super().__init__(public_request, hidden_state)
        self.__attempt_bindings: dict[str, str] = {}
        self.__attempt_binding_lock = threading.Lock()
        self.domain_postconditions: set[str] = set()

    def controller_attempt(
        self,
        request: dict[str, Any],
        authorizations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        if len(authorizations) != 2:
            raise EvidenceError("HOLDER_AUTHORIZATION_SET_INCOMPLETE")
        for holder_id, envelope in zip(
            ["LAB-SEEK", "LAB-OFFER"], authorizations
        ):
            self._verify_for_service(
                envelope,
                issuer=holder_id,
                kind="HOLDER_AUTHORIZATION",
                request_sha=request_sha,
            )

        # This compare-and-bind is the authoritative idempotency transition.
        # It occurs before an EFFECT_ATTEMPT receipt is issued.  Therefore a
        # prior attempt remains binding even if delivery, L3, or L4 never occurs.
        with self.__attempt_binding_lock:
            key = canonical["idempotency_key"]
            previous = self.__attempt_bindings.get(key)
            if previous is not None and previous != request_sha:
                return self._observation(
                    "CONTROLLER-W7",
                    request_sha,
                    "EFFECT_ATTEMPT",
                    "REFUSE",
                    "idempotency-key-already-bound-at-first-attempt",
                )
            self.__attempt_bindings[key] = request_sha

        return self._issue(
            "CONTROLLER-W7",
            "EFFECT_ATTEMPT",
            {
                "request_sha256": request_sha,
                "holder_authorization_sha256": [
                    envelope_sha256(item) for item in authorizations
                ],
                "idempotency_key": canonical["idempotency_key"],
                "binding_stage": "FIRST_VALID_EFFECT_ATTEMPT",
                "status": "ATTEMPTED",
            },
            request_sha,
            "REQUEST_EFFECT_ATTEMPT",
        )

    def domain_postcondition(
        self, request: dict[str, Any], ack: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        envelope = super().domain_postcondition(canonical, ack)
        if (
            envelope.get("kind") == "DOMAIN_POSTCONDITION"
            and not self.operation_log[-1]["cache_hit"]
        ):
            self.domain_postconditions.add(request_sha)
        return envelope

    def snapshot(self) -> dict[str, Any]:
        snapshot = super().snapshot()
        snapshot.update(
            {
                "attempt_binding_count": len(self.__attempt_bindings),
                "attempt_bindings": dict(self.__attempt_bindings),
                "attempt_binding_sha256": sorted(
                    self.__attempt_bindings.values()
                ),
                "domain_postcondition_count": len(
                    self.domain_postconditions
                ),
                "domain_postcondition_sha256": sorted(
                    self.domain_postconditions
                ),
            }
        )
        return snapshot
