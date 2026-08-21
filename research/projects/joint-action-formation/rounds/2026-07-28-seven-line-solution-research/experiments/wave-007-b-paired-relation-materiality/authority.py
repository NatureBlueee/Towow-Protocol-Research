"""Opaque authority and evidence gateway for Wave 007-B.

Candidate code receives only the callable ``EvidenceGateway``.  Private world
state, authority keys, evidence inventory, raw operation log, and evaluator
truth remain outside that object.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from public_api import (
    EvidenceGateway,
    OPERATION,
    PURPOSE,
    RETENTION,
    REUSE_OPERATION,
    SHARED_TASK_ID,
    SHARED_TASK_SHA256,
    STEP,
    WORLD_ID,
)


KERNEL = (
    Path(__file__).resolve().parents[1]
    / "wave-005-b-cross-authority-receipts"
)
sys.path.insert(0, str(KERNEL))

from protocol import (  # noqa: E402
    ProtocolError,
    canonical_bytes,
    envelope_hash,
    private_key_from_hex,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


AUTHORITIES = [
    "CONTROLLER-W7B",
    "LAB-SEEK",
    "LAB-OFFER",
    "SIM-RECIPIENT",
]
DISCLOSURE_UNITS = {
    "delivery": 2,
    "ack_seek": 0,
    "ack_offer": 0,
    "explain_seek": 1,
    "explain_offer": 1,
    "proposal": 1,
    "auth_seek": 1,
    "auth_offer": 1,
    "withdrawal": 1,
}


def _seed(authority: str) -> str:
    return hashlib.sha256(
        f"towow-wave007b:{authority}:v1".encode("utf-8")
    ).hexdigest()


def _private_key(authority: str):
    return private_key_from_hex(_seed(authority))


def _public_key_hex(authority: str) -> str:
    return (
        _private_key(authority)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )


def build_contract() -> dict[str, Any]:
    return {
        "schema": "towow.wave007b-contract.v1",
        "contract_id": "W7B-PAIRED-RELATION-001",
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "world_id": WORLD_ID,
        "evaluation_step": STEP,
        "operation": OPERATION,
        "reuse_operation": REUSE_OPERATION,
        "purpose": PURPOSE,
        "retention": RETENTION,
        "verification_keys": [
            {
                "issuer": authority,
                "key_id": "v1",
                "public_key_hex": _public_key_hex(authority),
                "valid_from_step": 1,
                "valid_through_step": 20,
            }
            for authority in AUTHORITIES
        ],
    }


@dataclass(frozen=True)
class PrivateWorldState:
    reuse_truth: str
    relation_evidence: str
    withdraw_after_first_reuse: bool


@dataclass
class AuditHandle:
    contract: dict[str, Any]
    operation_log: list[dict[str, Any]]
    evidence_returns: dict[str, dict[str, Any]]


class HiddenAuthorityService:
    def __init__(
        self,
        private_state: PrivateWorldState,
        *,
        opaque_seed: str,
        deleted_evidence: set[str] | None = None,
        evidence_overrides: dict[str, dict[str, Any]] | None = None,
        evaluator_attack: str | None = None,
    ):
        self.__private_state = private_state
        self.__contract = build_contract()
        self.__opaque_handle = hashlib.sha256(
            f"opaque:{opaque_seed}".encode("utf-8")
        ).hexdigest()[:20]
        self.__deleted_evidence = deleted_evidence or set()
        self.__operation_log: list[dict[str, Any]] = []
        self.__returns: dict[str, dict[str, Any]] = {}
        self.__reuse_count = 0
        self.__evidence = self.__build_evidence()
        if evaluator_attack == "UNAUTHORIZED_AUTH_OFFER":
            self.__evidence["auth_offer"] = self.__present(
                self.__sign(
                    "SIM-RECIPIENT",
                    "BOUNDED_REUSE_AUTHORIZATION",
                    {
                        **self.__base(),
                        "party": "SIM-RECIPIENT",
                        "relation_id": "REL-W7B-STERILE-REUSE-001",
                        "relation_version": 1,
                        "proposal_sha256": envelope_hash(
                            self.__evidence["proposal"]["evidence"]
                        ),
                        "reuse_operation": REUSE_OPERATION,
                        "bounded_reuse_count": 1,
                        "authorized": True,
                    },
                )
            )
        elif evaluator_attack == "WRONG_KIND_ACK_OFFER":
            ack_body = copy.deepcopy(
                self.__evidence["ack_offer"]["evidence"]["body"]
            )
            self.__evidence["ack_offer"] = self.__present(
                self.__sign(
                    "LAB-OFFER",
                    "RELATION_EXPLAIN_BACK",
                    ack_body,
                )
            )
        elif evaluator_attack == "CROSS_PURPOSE_AUTH_OFFER":
            auth_body = copy.deepcopy(
                self.__evidence["auth_offer"]["evidence"]["body"]
            )
            auth_body["purpose"] = "different-signed-purpose"
            self.__evidence["auth_offer"] = self.__present(
                self.__sign(
                    "LAB-OFFER",
                    "BOUNDED_REUSE_AUTHORIZATION",
                    auth_body,
                )
            )
        elif evaluator_attack == "UNAUTHORIZED_WITHDRAWAL":
            withdrawal_body = copy.deepcopy(
                self.__evidence["withdrawal"]["evidence"]["body"]
            )
            withdrawal_body["party"] = "SIM-RECIPIENT"
            self.__evidence["withdrawal"] = self.__present(
                self.__sign(
                    "SIM-RECIPIENT",
                    "RELATION_WITHDRAWAL",
                    withdrawal_body,
                )
            )
        for name, value in (evidence_overrides or {}).items():
            self.__evidence[name] = copy.deepcopy(value)

    def __sign(
        self, issuer: str, kind: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        return sign_envelope(
            _private_key(issuer),
            kind=kind,
            issuer=issuer,
            key_id="v1",
            body=body,
        )

    def __base(self) -> dict[str, Any]:
        return {
            "shared_task_id": SHARED_TASK_ID,
            "shared_task_sha256": SHARED_TASK_SHA256,
            "world_id": WORLD_ID,
            "evaluation_step": STEP,
            "operation": OPERATION,
            "purpose": PURPOSE,
            "retention": RETENTION,
        }

    def __present(
        self, envelope: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "observation": "PRESENT",
            "evidence": envelope,
            "evidence_ref": envelope_hash(envelope),
        }

    def __observation(
        self,
        state: str,
        *,
        issuer: str,
        category: str,
        reason: str,
    ) -> dict[str, Any]:
        envelope = self.__sign(
            issuer,
            "EVIDENCE_OBSERVATION",
            {
                **self.__base(),
                "category": category,
                "observation": state,
                "reason": reason,
            },
        )
        return {
            "observation": state,
            "evidence": envelope,
            "evidence_ref": envelope_hash(envelope),
        }

    def __build_evidence(self) -> dict[str, dict[str, Any]]:
        base = self.__base()
        delivery = self.__sign(
            "CONTROLLER-W7B",
            "TASK_DELIVERY",
            {
                **base,
                "delivery_id": "DELIVERY-W7B-001",
                "projection_origins": ["LAB-SEEK", "LAB-OFFER"],
                "recipient": "SIM-RECIPIENT",
                "event_sha256": sha256_value(
                    {
                        "seek": "minimal-route-constraints",
                        "offer": "minimal-window-capacity",
                    }
                ),
            },
        )
        evidence: dict[str, dict[str, Any]] = {
            "delivery": self.__present(delivery)
        }
        for party, suffix in [
            ("LAB-SEEK", "seek"),
            ("LAB-OFFER", "offer"),
        ]:
            ack = self.__sign(
                party,
                "TASK_DELIVERY_ACK",
                {
                    **base,
                    "party": party,
                    "delivery_sha256": envelope_hash(delivery),
                    "ack_scope": "THIS_OPERATION_ONLY",
                },
            )
            evidence[f"ack_{suffix}"] = self.__present(ack)

        if self.__private_state.reuse_truth == "ONE_OPERATION_ONLY":
            if (
                self.__private_state.relation_evidence
                == "VALID_NO_REUSE"
            ):
                for party, suffix in [
                    ("LAB-SEEK", "seek"),
                    ("LAB-OFFER", "offer"),
                ]:
                    explain = self.__sign(
                        party,
                        "RELATION_EXPLAIN_BACK",
                        {
                            **base,
                            "party": party,
                            "understanding": "FRESH_TASK_AUTHORIZATION_REQUIRED",
                            "bounded_reuse_count": 0,
                        },
                    )
                    evidence[f"explain_{suffix}"] = self.__present(
                        explain
                    )
                evidence["proposal"] = self.__observation(
                    "ABSENT",
                    issuer="CONTROLLER-W7B",
                    category="proposal",
                    reason="closed-snapshot-no-relation-proposal",
                )
                for party, suffix in [
                    ("LAB-SEEK", "seek"),
                    ("LAB-OFFER", "offer"),
                ]:
                    evidence[f"auth_{suffix}"] = self.__observation(
                        "REFUSE",
                        issuer=party,
                        category=f"auth_{suffix}",
                        reason="one-operation-only",
                    )
            else:
                explain = self.__sign(
                    "LAB-SEEK",
                    "RELATION_EXPLAIN_BACK",
                    {
                        **base,
                        "party": "LAB-SEEK",
                        "understanding": "CONTINUING_INTEREST_NOT_AUTHORITY",
                        "bounded_reuse_count": 1,
                    },
                )
                evidence["explain_seek"] = self.__present(explain)
                evidence["explain_offer"] = self.__observation(
                    "UNKNOWN",
                    issuer="LAB-OFFER",
                    category="explain_offer",
                    reason="no-response-in-window",
                )
                evidence["proposal"] = self.__observation(
                    "UNKNOWN",
                    issuer="CONTROLLER-W7B",
                    category="proposal",
                    reason="proposal-status-not-established",
                )
                evidence["auth_seek"] = self.__observation(
                    "REFUSE",
                    issuer="LAB-SEEK",
                    category="auth_seek",
                    reason="no-bounded-authorization",
                )
                evidence["auth_offer"] = self.__observation(
                    "UNKNOWN",
                    issuer="LAB-OFFER",
                    category="auth_offer",
                    reason="no-response-in-window",
                )
            evidence["withdrawal"] = self.__observation(
                "ABSENT",
                issuer="CONTROLLER-W7B",
                category="withdrawal",
                reason="no-continuing-relation-exists",
            )
            return evidence

        relation_id = "REL-W7B-STERILE-REUSE-001"
        valid = (
            self.__private_state.relation_evidence
            == "VALID_BOUNDED_REUSE"
        )
        for party, suffix in [
            ("LAB-SEEK", "seek"),
            ("LAB-OFFER", "offer"),
        ]:
            understanding = (
                "EXPLICIT_BOUNDED_REUSE_AUTHORIZED"
                if valid or party == "LAB-SEEK"
                else "FRESH_TASK_AUTHORIZATION_REQUIRED"
            )
            explain = self.__sign(
                party,
                "RELATION_EXPLAIN_BACK",
                {
                    **base,
                    "party": party,
                    "understanding": understanding,
                    "relation_id": relation_id,
                    "bounded_reuse_count": 1,
                    "reuse_operation": REUSE_OPERATION,
                },
            )
            evidence[f"explain_{suffix}"] = self.__present(explain)
        proposal = self.__sign(
            "CONTROLLER-W7B",
            "BOUNDED_RELATION_PROPOSAL",
            {
                **base,
                "relation_id": relation_id,
                "relation_version": 1,
                "reuse_operation": REUSE_OPERATION,
                "bounded_reuse_count": 1,
                "status": "PROPOSED_NOT_CONSTITUTED",
            },
        )
        evidence["proposal"] = self.__present(proposal)
        for party, suffix in [
            ("LAB-SEEK", "seek"),
            ("LAB-OFFER", "offer"),
        ]:
            if not valid and party == "LAB-OFFER":
                evidence[f"auth_{suffix}"] = self.__observation(
                    "UNKNOWN",
                    issuer=party,
                    category=f"auth_{suffix}",
                    reason="authorization-missing",
                )
                continue
            authorization = self.__sign(
                party,
                "BOUNDED_REUSE_AUTHORIZATION",
                {
                    **base,
                    "party": party,
                    "relation_id": relation_id,
                    "relation_version": 1,
                    "proposal_sha256": envelope_hash(proposal),
                    "reuse_operation": REUSE_OPERATION,
                    "bounded_reuse_count": 1,
                    "authorized": True,
                },
            )
            evidence[f"auth_{suffix}"] = self.__present(authorization)
        withdrawal = self.__sign(
            "LAB-OFFER",
            "RELATION_WITHDRAWAL",
            {
                **base,
                "party": "LAB-OFFER",
                "relation_id": relation_id,
                "relation_version": 1,
                "effective_after_reuse_count": 1,
                "status": "WITHDRAWN",
            },
        )
        evidence["withdrawal"] = self.__present(withdrawal)
        return evidence

    def create_gateway(self) -> tuple[EvidenceGateway, AuditHandle]:
        service = self

        def read_evidence(name: str) -> dict[str, Any]:
            if name in service.__deleted_evidence:
                returned = service.__observation(
                    "UNKNOWN",
                    issuer="CONTROLLER-W7B",
                    category=name,
                    reason="evidence-deleted-by-mutation",
                )
            else:
                returned = copy.deepcopy(
                    service.__evidence.get(
                        name,
                        service.__observation(
                            "UNKNOWN",
                            issuer="CONTROLLER-W7B",
                            category=name,
                            reason="evidence-not-available",
                        ),
                    )
                )
            raw_bytes = len(canonical_bytes(returned))
            service.__operation_log.append(
                {
                    "op": "READ_EVIDENCE",
                    "name": name,
                    "observation": returned["observation"],
                    "evidence_ref": returned["evidence_ref"],
                    "bytes": raw_bytes,
                    "disclosure_units": DISCLOSURE_UNITS.get(name, 0),
                }
            )
            service.__returns[name] = copy.deepcopy(returned)
            return returned

        def verify_evidence(
            evidence: dict[str, Any]
        ) -> dict[str, Any]:
            try:
                body = verify_envelope(
                    evidence,
                    service.__contract,
                    expected_kind=evidence["kind"],
                    expected_issuer=evidence["issuer"],
                    step=STEP,
                )
                valid = True
                error = None
            except (KeyError, ProtocolError) as exc:
                body = {}
                valid = False
                error = getattr(exc, "code", "MALFORMED")
            service.__operation_log.append(
                {
                    "op": "VERIFY_SIGNATURE",
                    "evidence_ref": envelope_hash(evidence)
                    if evidence
                    else None,
                    "issuer": evidence.get("issuer"),
                    "kind": evidence.get("kind"),
                    "valid": valid,
                    "error": error,
                    "bytes": len(canonical_bytes(evidence)),
                    "disclosure_units": 0,
                }
            )
            return {"valid": valid, "body": body, "error": error}

        def record_relation_decision(
            state: str, evidence_refs: list[str]
        ) -> None:
            service.__operation_log.append(
                {
                    "op": "CANDIDATE_RELATION_DECISION",
                    "state": state,
                    "evidence_refs": list(evidence_refs),
                    "bytes": len(canonical_bytes(evidence_refs)),
                    "disclosure_units": 0,
                }
            )

        def request_reuse(
            authorizations: list[dict[str, Any]],
        ) -> dict[str, Any]:
            service.__operation_log.append(
                {
                    "op": "AUTHORITY_REUSE_REQUEST",
                    "authorization_refs": [
                        envelope_hash(item) for item in authorizations
                    ],
                    "bytes": len(canonical_bytes(authorizations)),
                    "disclosure_units": 0,
                }
            )
            valid_issuers = set()
            proposal_hashes = set()
            relation_ids = set()
            relation_versions = set()
            expected_proposal_hash = envelope_hash(
                service.__evidence["proposal"]["evidence"]
            )
            for item in authorizations:
                try:
                    body = verify_envelope(
                        item,
                        service.__contract,
                        expected_kind="BOUNDED_REUSE_AUTHORIZATION",
                        expected_issuer=item["issuer"],
                        step=STEP,
                    )
                except (KeyError, ProtocolError):
                    continue
                if (
                    item["issuer"] in {"LAB-SEEK", "LAB-OFFER"}
                    and body.get("shared_task_id") == SHARED_TASK_ID
                    and body.get("shared_task_sha256")
                    == SHARED_TASK_SHA256
                    and body.get("world_id") == WORLD_ID
                    and body.get("evaluation_step") == STEP
                    and body.get("operation") == OPERATION
                    and body.get("purpose") == PURPOSE
                    and body.get("retention") == RETENTION
                    and body.get("party") == item["issuer"]
                    and body.get("relation_id")
                    == "REL-W7B-STERILE-REUSE-001"
                    and body.get("relation_version") == 1
                    and body.get("proposal_sha256")
                    == expected_proposal_hash
                    and body.get("reuse_operation") == REUSE_OPERATION
                    and body.get("bounded_reuse_count") == 1
                    and body.get("authorized") is True
                ):
                    valid_issuers.add(item["issuer"])
                    proposal_hashes.add(body.get("proposal_sha256"))
                    relation_ids.add(body.get("relation_id"))
                    relation_versions.add(
                        body.get("relation_version")
                    )
            authorized = (
                service.__private_state.reuse_truth
                == "EXPLICIT_BOUNDED_REUSE_AUTHORIZED"
                and service.__private_state.relation_evidence
                == "VALID_BOUNDED_REUSE"
                and valid_issuers == {"LAB-SEEK", "LAB-OFFER"}
                and proposal_hashes == {expected_proposal_hash}
                and relation_ids == {"REL-W7B-STERILE-REUSE-001"}
                and relation_versions == {1}
                and service.__reuse_count == 0
            )
            if authorized:
                service.__reuse_count += 1
                response = service.__sign(
                    "CONTROLLER-W7B",
                    "REUSE_EXECUTION_RECEIPT",
                    {
                        **service.__base(),
                        "reuse_operation": REUSE_OPERATION,
                        "reuse_count": service.__reuse_count,
                        "authorization_issuers": sorted(valid_issuers),
                        "proposal_sha256": next(iter(proposal_hashes)),
                        "status": "EXECUTED",
                    },
                )
                observation = "PRESENT"
            else:
                response = service.__sign(
                    "CONTROLLER-W7B",
                    "REUSE_EXECUTION_REFUSAL",
                    {
                        **service.__base(),
                        "reuse_operation": REUSE_OPERATION,
                        "status": "REFUSE",
                        "reason": "bounded-reuse-authority-not-established",
                    },
                )
                observation = "REFUSE"
            returned = {
                "observation": observation,
                "evidence": response,
                "evidence_ref": envelope_hash(response),
            }
            service.__operation_log.append(
                {
                    "op": "AUTHORITY_REUSE_RESPONSE",
                    "observation": observation,
                    "evidence_ref": returned["evidence_ref"],
                    "bytes": len(canonical_bytes(returned)),
                    "disclosure_units": 0,
                }
            )
            service.__returns[
                f"reuse_response_{service.__reuse_count}"
            ] = copy.deepcopy(returned)
            return returned

        def poll_withdrawal() -> dict[str, Any]:
            service.__operation_log.append(
                {
                    "op": "POLL_WITHDRAWAL",
                    "after_reuse_count": service.__reuse_count,
                    "bytes": 0,
                    "disclosure_units": 0,
                }
            )
            if (
                service.__private_state.withdraw_after_first_reuse
                and service.__reuse_count >= 1
            ):
                returned = copy.deepcopy(service.__evidence["withdrawal"])
            elif (
                service.__private_state.reuse_truth
                == "ONE_OPERATION_ONLY"
            ):
                returned = copy.deepcopy(service.__evidence["withdrawal"])
            else:
                returned = service.__observation(
                    "UNKNOWN",
                    issuer="LAB-OFFER",
                    category="withdrawal",
                    reason="withdrawal-not-yet-effective",
                )
            service.__returns["withdrawal_poll"] = copy.deepcopy(returned)
            return returned

        gateway = EvidenceGateway(
            opaque_handle=self.__opaque_handle,
            read_evidence=read_evidence,
            verify_evidence=verify_evidence,
            record_relation_decision=record_relation_decision,
            request_reuse=request_reuse,
            poll_withdrawal=poll_withdrawal,
        )
        audit = AuditHandle(
            contract=copy.deepcopy(self.__contract),
            operation_log=self.__operation_log,
            evidence_returns=self.__returns,
        )
        return gateway, audit
