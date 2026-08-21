#!/usr/bin/env python3
"""Independent signing services and the narrow candidate API for Wave 007-A."""

from __future__ import annotations

import copy
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from protocol import (
    EvidenceError,
    canonical_bytes,
    envelope_sha256,
    normalize_request,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


AUTHORITY_IDS = [
    "LAB-SEEK",
    "LAB-OFFER",
    "CONTROLLER-W7",
    "ANCHOR-W7",
    "WITNESS-1",
    "WITNESS-2",
    "WITNESS-3",
    "SIM-RECIPIENT",
    "SIMULATOR-W7",
    "BENEFICIARY-REVIEWER",
    "REGISTRY-W7",
]
WITNESS_ALLOWLIST = ["WITNESS-1", "WITNESS-2", "WITNESS-3"]
WITNESS_THRESHOLD = 2


class SigningAuthority:
    """Owns one domain key; callers can request signatures but cannot export it."""

    __slots__ = ("authority_id", "__private_key", "__cache")

    def __init__(self, authority_id: str):
        self.authority_id = authority_id
        # Generated inside the authority process/object.  There is deliberately
        # no public deterministic helper from which a candidate can recreate it.
        self.__private_key = Ed25519PrivateKey.generate()
        self.__cache: dict[tuple[str, str], dict[str, Any]] = {}

    def public_key_hex(self) -> str:
        return self.__private_key.public_key().public_bytes(
            Encoding.Raw, PublicFormat.Raw
        ).hex()

    def issue(
        self, kind: str, body: dict[str, Any], cache_key: str
    ) -> tuple[dict[str, Any], bool]:
        key = (kind, cache_key)
        if key in self.__cache:
            return copy.deepcopy(self.__cache[key]), True
        envelope = sign_envelope(
            self.__private_key,
            issuer=self.authority_id,
            kind=kind,
            body=copy.deepcopy(body),
        )
        self.__cache[key] = envelope
        return copy.deepcopy(envelope), False


def verify_witness_quorum(
    attestations: list[dict[str, Any]],
    public_registry: dict[str, str],
    *,
    allowlist: list[str],
    threshold: int,
    checkpoint_sha256: str,
    slot: str,
    branch_sha256: str,
) -> dict[str, Any]:
    """Count only unique allowlisted issuers bound to one checkpoint/slot/branch."""

    valid_unique: set[str] = set()
    rejected: list[dict[str, str]] = []
    for attestation in attestations:
        issuer = attestation.get("issuer", "<missing>")
        try:
            body = verify_envelope(
                attestation,
                public_registry,
                expected_kind="ANCHOR_WITNESS_ATTESTATION",
            )
            if issuer not in allowlist:
                raise EvidenceError("WITNESS_NOT_ALLOWLISTED")
            if body.get("checkpoint_sha256") != checkpoint_sha256:
                raise EvidenceError("WITNESS_CHECKPOINT_MISMATCH")
            if body.get("slot") != slot:
                raise EvidenceError("WITNESS_SLOT_MISMATCH")
            if body.get("branch_sha256") != branch_sha256:
                raise EvidenceError("WITNESS_BRANCH_MISMATCH")
            if issuer in valid_unique:
                rejected.append(
                    {"issuer": issuer, "code": "DUPLICATE_WITNESS"}
                )
                continue
            valid_unique.add(issuer)
        except EvidenceError as error:
            rejected.append({"issuer": issuer, "code": error.code})
    return {
        "quorum": len(valid_unique) >= threshold,
        "threshold": threshold,
        "unique_valid_issuers": sorted(valid_unique),
        "unique_valid_count": len(valid_unique),
        "rejected": rejected,
    }


class AuthorityNetwork:
    """Harness-owned network. Candidate receives only `candidate_api()`."""

    def __init__(
        self,
        public_request: dict[str, Any],
        hidden_state: dict[str, Any],
    ):
        self.__public_request = copy.deepcopy(public_request)
        self.__hidden_state = copy.deepcopy(hidden_state)
        self.__services = {
            authority: SigningAuthority(authority)
            for authority in AUTHORITY_IDS
        }
        self.__public_registry = {
            authority: service.public_key_hex()
            for authority, service in self.__services.items()
        }
        self.operation_log: list[dict[str, Any]] = []
        self.accepted_effects: set[str] = set()
        self.__idempotency_registry: dict[str, str] = {}

    def public_registry(self) -> dict[str, str]:
        return copy.deepcopy(self.__public_registry)

    def _append_log(
        self,
        operation: str,
        authority: str,
        response: dict[str, Any] | None,
        *,
        cache_hit: bool = False,
        outcome: str = "OK",
    ) -> None:
        self.operation_log.append(
            {
                "sequence": len(self.operation_log) + 1,
                "operation": operation,
                "authority": authority,
                "outcome": outcome,
                "cache_hit": cache_hit,
                "response_bytes": (
                    len(canonical_bytes(response)) if response else 0
                ),
                "response_sha256": (
                    sha256_value(response) if response else None
                ),
            }
        )

    def _issue(
        self,
        authority: str,
        kind: str,
        body: dict[str, Any],
        cache_key: str,
        operation: str,
    ) -> dict[str, Any]:
        envelope, cache_hit = self.__services[authority].issue(
            kind, body, cache_key
        )
        self._append_log(
            operation,
            authority,
            envelope,
            cache_hit=cache_hit,
            outcome=body.get("state", body.get("status", "OK")),
        )
        return envelope

    def _observation(
        self,
        authority: str,
        request_sha: str,
        stage: str,
        state: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._issue(
            authority,
            "AUTHORITY_OBSERVATION",
            {
                "request_sha256": request_sha,
                "stage": stage,
                "state": state,
                "reason": reason,
            },
            f"{request_sha}:{stage}:{state}",
            f"REQUEST_{stage}",
        )

    def _verify_for_service(
        self,
        envelope: dict[str, Any],
        *,
        issuer: str,
        kind: str,
        request_sha: str,
    ) -> dict[str, Any]:
        body = verify_envelope(
            envelope,
            self.__public_registry,
            expected_issuer=issuer,
            expected_kind=kind,
        )
        if body.get("request_sha256") != request_sha:
            raise EvidenceError("REQUEST_BINDING_MISMATCH")
        return body

    def read_request(self) -> dict[str, Any]:
        request = copy.deepcopy(self.__public_request)
        self._append_log("READ_PUBLIC_REQUEST", "PUBLIC-INPUT", request)
        return request

    def verify_for_candidate(
        self, envelope: dict[str, Any]
    ) -> dict[str, Any]:
        body = verify_envelope(envelope, self.__public_registry)
        self._append_log(
            "VERIFY_EVIDENCE",
            envelope["issuer"],
            None,
            outcome=envelope["kind"],
        )
        return body

    def holder_authorize(
        self, holder_id: str, request: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        state_key = "holder_seek" if holder_id == "LAB-SEEK" else "holder_offer"
        state = self.__hidden_state[state_key]
        if state == "ABSENT":
            return self._observation(
                "REGISTRY-W7",
                request_sha,
                "HOLDER_AUTHORIZATION",
                "ABSENT",
                f"{holder_id}-not-in-closed-registry",
            )
        if state != "ACTIVE":
            return self._observation(
                holder_id,
                request_sha,
                "HOLDER_AUTHORIZATION",
                "REFUSE",
                f"{holder_id}-authorization-{state.lower()}",
            )
        return self._issue(
            holder_id,
            "HOLDER_AUTHORIZATION",
            {
                "request_sha256": request_sha,
                "operation": canonical["operation"],
                "purpose": canonical["purpose"],
                "retention": canonical["retention"],
                "environment_version": canonical["environment_version"],
                "status": "AUTHORIZED",
            },
            request_sha,
            "REQUEST_HOLDER_AUTHORIZATION",
        )

    def controller_attempt(
        self,
        request: dict[str, Any],
        authorizations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        previous = self.__idempotency_registry.get(
            canonical["idempotency_key"]
        )
        if previous is not None and previous != request_sha:
            return self._observation(
                "CONTROLLER-W7",
                request_sha,
                "EFFECT_ATTEMPT",
                "REFUSE",
                "idempotency-key-material-conflict",
            )
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
        return self._issue(
            "CONTROLLER-W7",
            "EFFECT_ATTEMPT",
            {
                "request_sha256": request_sha,
                "holder_authorization_sha256": [
                    envelope_sha256(item) for item in authorizations
                ],
                "status": "ATTEMPTED",
            },
            request_sha,
            "REQUEST_EFFECT_ATTEMPT",
        )

    def controller_delivery(
        self, request: dict[str, Any], attempt: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        self._verify_for_service(
            attempt,
            issuer="CONTROLLER-W7",
            kind="EFFECT_ATTEMPT",
            request_sha=request_sha,
        )
        deliveries = [
            {
                "origin": "LAB-SEEK",
                "facet": "route-constraints",
                "recipient": "SIM-RECIPIENT",
            },
            {
                "origin": "LAB-OFFER",
                "facet": "window-capacity",
                "recipient": "SIM-RECIPIENT",
            },
        ]
        return self._issue(
            "CONTROLLER-W7",
            "DELIVERY_RECEIPT",
            {
                "request_sha256": request_sha,
                "attempt_sha256": envelope_sha256(attempt),
                "deliveries": deliveries,
                "status": "DELIVERED",
            },
            request_sha,
            "REQUEST_DELIVERY",
        )

    def _witness_attestation(
        self,
        witness: str,
        checkpoint_sha256: str,
        slot: str,
        branch_sha256: str,
    ) -> dict[str, Any]:
        return self._issue(
            witness,
            "ANCHOR_WITNESS_ATTESTATION",
            {
                "checkpoint_sha256": checkpoint_sha256,
                "slot": slot,
                "branch_sha256": branch_sha256,
                "status": "ATTESTED",
            },
            f"{checkpoint_sha256}:{slot}:{branch_sha256}",
            "REQUEST_ANCHOR_WITNESS",
        )

    def anchor_commit(
        self, request: dict[str, Any], delivery: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        self._verify_for_service(
            delivery,
            issuer="CONTROLLER-W7",
            kind="DELIVERY_RECEIPT",
            request_sha=request_sha,
        )
        checkpoint = envelope_sha256(delivery)
        slot = "W7-DELIVERY-COMMIT-SLOT-1"
        branch = sha256_value(
            {
                "checkpoint_sha256": checkpoint,
                "slot": slot,
                "request_sha256": request_sha,
            }
        )
        if self.__hidden_state["anchor"] == "EQUIVOCATED":
            other_branch = sha256_value({"fork_of": branch})
            first = self._witness_attestation(
                "WITNESS-1", checkpoint, slot, branch
            )
            second = self._witness_attestation(
                "WITNESS-2", checkpoint, slot, other_branch
            )
            quorum = verify_witness_quorum(
                [first, first, second, second],
                self.__public_registry,
                allowlist=WITNESS_ALLOWLIST,
                threshold=WITNESS_THRESHOLD,
                checkpoint_sha256=checkpoint,
                slot=slot,
                branch_sha256=branch,
            )
            if not quorum["quorum"]:
                return self._observation(
                    "ANCHOR-W7",
                    request_sha,
                    "ANCHOR_COMMIT",
                    "UNKNOWN",
                    "equivocated-branch-has-no-unique-quorum",
                )
        attestations = [
            self._witness_attestation(
                witness, checkpoint, slot, branch
            )
            for witness in ["WITNESS-1", "WITNESS-2"]
        ]
        quorum = verify_witness_quorum(
            attestations,
            self.__public_registry,
            allowlist=WITNESS_ALLOWLIST,
            threshold=WITNESS_THRESHOLD,
            checkpoint_sha256=checkpoint,
            slot=slot,
            branch_sha256=branch,
        )
        if not quorum["quorum"]:
            return self._observation(
                "ANCHOR-W7",
                request_sha,
                "ANCHOR_COMMIT",
                "UNKNOWN",
                "anchor-quorum-not-observed",
            )
        return self._issue(
            "ANCHOR-W7",
            "ANCHOR_COMMIT",
            {
                "request_sha256": request_sha,
                "delivery_sha256": checkpoint,
                "checkpoint_sha256": checkpoint,
                "slot": slot,
                "branch_sha256": branch,
                "witness_attestations": attestations,
                "status": "COMMITTED",
            },
            request_sha,
            "REQUEST_ANCHOR_COMMIT",
        )

    def recipient_ack(
        self,
        request: dict[str, Any],
        delivery: dict[str, Any],
        anchor: dict[str, Any],
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        if self.__hidden_state["recipient"] != "ACTIVE":
            return self._observation(
                "SIM-RECIPIENT",
                request_sha,
                "RECIPIENT_ACK",
                "REFUSE",
                "recipient-withdrawn",
            )
        self._verify_for_service(
            delivery,
            issuer="CONTROLLER-W7",
            kind="DELIVERY_RECEIPT",
            request_sha=request_sha,
        )
        self._verify_for_service(
            anchor,
            issuer="ANCHOR-W7",
            kind="ANCHOR_COMMIT",
            request_sha=request_sha,
        )
        return self._issue(
            "SIM-RECIPIENT",
            "RECIPIENT_ACK",
            {
                "request_sha256": request_sha,
                "delivery_sha256": envelope_sha256(delivery),
                "anchor_sha256": envelope_sha256(anchor),
                "status": "ACKED",
            },
            request_sha,
            "REQUEST_RECIPIENT_ACK",
        )

    def domain_postcondition(
        self, request: dict[str, Any], ack: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        self._verify_for_service(
            ack,
            issuer="SIM-RECIPIENT",
            kind="RECIPIENT_ACK",
            request_sha=request_sha,
        )
        output = {
            "route_status": "STERILE_ROUTE_FEASIBLE",
            "command": canonical["command"],
            "environment_version": canonical["environment_version"],
        }
        return self._issue(
            "SIMULATOR-W7",
            "DOMAIN_POSTCONDITION",
            {
                "request_sha256": request_sha,
                "recipient_ack_sha256": envelope_sha256(ack),
                "output": output,
                "output_sha256": sha256_value(output),
                "status": "SATISFIED",
            },
            request_sha,
            "REQUEST_DOMAIN_POSTCONDITION",
        )

    def beneficiary_decision(
        self, request: dict[str, Any], postcondition: dict[str, Any]
    ) -> dict[str, Any]:
        canonical = normalize_request(request)
        request_sha = sha256_value(canonical)
        self._verify_for_service(
            postcondition,
            issuer="SIMULATOR-W7",
            kind="DOMAIN_POSTCONDITION",
            request_sha=request_sha,
        )
        if self.__hidden_state["beneficiary"] != "ACCEPT":
            return self._observation(
                "BENEFICIARY-REVIEWER",
                request_sha,
                "BENEFICIARY_DECISION",
                "REFUSE",
                "beneficiary-refused-exact-output",
            )
        envelope = self._issue(
            "BENEFICIARY-REVIEWER",
            "BENEFICIARY_ACCEPTANCE",
            {
                "request_sha256": request_sha,
                "postcondition_sha256": envelope_sha256(postcondition),
                "accepted_output_sha256": postcondition["body"][
                    "output_sha256"
                ],
                "status": "ACCEPTED",
            },
            request_sha,
            "REQUEST_BENEFICIARY_DECISION",
        )
        if not self.operation_log[-1]["cache_hit"]:
            self.accepted_effects.add(request_sha)
            self.__idempotency_registry[
                canonical["idempotency_key"]
            ] = request_sha
        return envelope

    def preload(self, request: dict[str, Any]) -> None:
        request = normalize_request(request)
        a1 = self.holder_authorize("LAB-SEEK", request)
        a2 = self.holder_authorize("LAB-OFFER", request)
        attempt = self.controller_attempt(request, [a1, a2])
        delivery = self.controller_delivery(request, attempt)
        anchor = self.anchor_commit(request, delivery)
        ack = self.recipient_ack(request, delivery, anchor)
        postcondition = self.domain_postcondition(request, ack)
        self.beneficiary_decision(request, postcondition)
        self.operation_log.clear()

    def snapshot(self) -> dict[str, Any]:
        return {
            "accepted_effect_count": len(self.accepted_effects),
            "accepted_effect_sha256": sorted(self.accepted_effects),
        }
