"""Relation-only truth owner.

This module deliberately has no authority imports or state.  Runtime signing
keys, private truth and the broker ledger remain parent-side.
"""

from __future__ import annotations

import copy
from dataclasses import fields
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common import canonical_bytes, public_key_hex, sha256_hex, sign_envelope
from world_factory import RelationPrivateWorld


DOMAIN = "TOWOW-WAVE009-RELATION"


class RelationTruthBroker:
    def __init__(self, state: RelationPrivateWorld) -> None:
        self.__state = state
        self.__broker_key = Ed25519PrivateKey.generate()
        self.__keys = {
            f"REL-{name}": Ed25519PrivateKey.generate()
            for name in self._principals()
        }
        self.__keys["REL-CONTROLLER"] = Ed25519PrivateKey.generate()
        self.__ledger: list[dict[str, Any]] = []

    def _principals(self) -> list[str]:
        if self.__state.task_kind == "T3":
            return ["SEEKER", "RESOURCE_OWNER"]
        return ["PRIME", "FIELD", "ASSURE"]

    def public_contract(self) -> dict[str, Any]:
        return {
            "schema": "towow.wave009-relation-contract.v1",
            "domain": DOMAIN,
            "broker_public_key": public_key_hex(self.__broker_key),
            "issuer_keys": {
                issuer: public_key_hex(key)
                for issuer, key in self.__keys.items()
            }
            | {"REL-BROKER": public_key_hex(self.__broker_key)},
        }

    def private_state_shape(self) -> list[str]:
        return [item.name for item in fields(self.__state)]

    def _issue(
        self,
        issuer: str,
        kind: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        envelope = sign_envelope(
            self.__keys[issuer],
            domain=DOMAIN,
            issuer=issuer,
            kind=kind,
            body=body,
        )
        self.__ledger.append(
            {
                "operation": "ISSUE_RELATION_EVIDENCE",
                "kind": kind,
                "issuer": issuer,
                "payload_sha256": envelope["payload_sha256"],
                "byte_count": len(canonical_bytes(envelope)),
            }
        )
        return envelope

    def issue_public_evidence(
        self,
        task: dict[str, Any],
        issuance_context: dict[str, Any],
    ) -> dict[str, Any]:
        principals = self._principals()
        state = self.__state
        context_envelope = sign_envelope(
            self.__broker_key,
            domain=DOMAIN,
            issuer="REL-BROKER",
            kind="SECTION_CONTEXT",
            body=issuance_context,
        )
        context_sha256 = context_envelope["payload_sha256"]
        self.__ledger.append(
            {
                "operation": "SEAL_RELATION_SECTION_CONTEXT",
                "payload_sha256": context_sha256,
                "byte_count": len(canonical_bytes(context_envelope)),
            }
        )
        base = {
            "world_id": state.world_id,
            "task_fingerprint": task["task_fingerprint"],
            "relation_version": state.current_version,
            "source_provenance": "PRINCIPAL_SIGNED_EVENT_STREAM",
            "issuance_context_sha256": context_sha256,
            "event_owner_domain": DOMAIN,
        }
        events: list[dict[str, Any]] = [
            self._issue(
                "REL-CONTROLLER",
                "PROPOSAL",
                {
                    **base,
                    "status": "CANDIDATE_ONLY",
                    "horizon": state.horizon,
                },
            )
        ]
        for principal in principals:
            issuer = f"REL-{principal}"
            events.append(
                self._issue(
                    issuer,
                    "ACK",
                    {
                        **base,
                        "principal_id": principal,
                        "ack_scope": "RECEIPT_ONLY",
                    },
                )
            )
        explain_principals = list(principals)
        if state.invalid_mode == "MISSING_EXPLAIN_BACK":
            explain_principals = explain_principals[:-1]
        for principal in explain_principals:
            events.append(
                self._issue(
                    f"REL-{principal}",
                    "EXPLAIN_BACK",
                    {
                        **base,
                        "principal_id": principal,
                        "understanding_hash": sha256_hex(
                            canonical_bytes(state.semantic_payload)
                        ),
                    },
                )
            )
        for principal in principals:
            events.append(
                self._issue(
                    f"REL-{principal}",
                    "STANCE",
                    {
                        **base,
                        "principal_id": principal,
                        "stance": "ACCEPT_CURRENT_RELATION_VERSION",
                    },
                )
            )
        events.append(
            self._issue(
                "REL-CONTROLLER",
                "COUNTER",
                {
                    **base,
                    "status": "CANDIDATE_CHANGE_ONLY",
                    "changes_commitment": False,
                },
            )
        )
        source_fingerprint = sha256_hex(
            canonical_bytes(state.semantic_payload)
        )
        compiled_fingerprint = (
            source_fingerprint
            if state.semantic_retained
            else sha256_hex(canonical_bytes({"purpose": "TRUNCATED"}))
        )
        version_body: dict[str, Any] = {
            **base,
            "principals": principals,
            "horizon": state.horizon,
            "source_text": state.source_text,
            "source_semantic_fingerprint": source_fingerprint,
            "compiled_semantic_fingerprint": compiled_fingerprint,
            "material_change": state.material_change,
            "opposition_preserved": True,
            "current_step": 4,
        }
        if state.horizon == "ONE_SHOT":
            version_body.update(
                reuse_limit=0,
                expiry_step=4,
                purpose=task["purpose"],
                exit_rule="END_AFTER_OPERATION",
            )
        elif state.horizon == "BOUNDED":
            version_body.update(
                reuse_limit=2,
                expiry_step=(
                    None
                    if state.invalid_mode == "MISSING_EXPIRY"
                    else 10
                ),
                purpose=task["purpose"],
                exit_rule="END_AT_LIMIT_OR_EXPIRY",
            )
        else:
            version_body.update(
                reuse_limit=None,
                expiry_step=None,
                purpose=task["purpose"],
                exit_rule="PRINCIPAL_WITHDRAWAL_OR_SUPERSEDING_VERSION",
                amendment_governance=(
                    None
                    if state.invalid_mode
                    == "MISSING_AMENDMENT_GOVERNANCE"
                    else "ALL_AFFECTED_PRINCIPALS_SIGN_MATERIAL_CHANGE"
                ),
                evidence_governance="PERIODIC_CURRENT_VERSION_READBACK",
                review_interval_steps=5,
            )
        events.append(
            self._issue(
                "REL-CONTROLLER",
                "RELATION_VERSION",
                version_body,
            )
        )
        return {
            "schema": "towow.wave009-relation-evidence.v1",
            "current_version": state.current_version,
            "section_context": context_envelope,
            "events": events,
            "contract": self.public_contract(),
        }

    def expected_outcome(self) -> dict[str, Any]:
        state = self.__state
        formed = state.relation_valid
        if state.invalid_mode in {"MATERIAL_CHANGE", "SEMANTIC_LOST"}:
            stage = "REOPEN_REQUIRED"
        else:
            stage = "FORMED" if formed else "PROPOSED"
        return {
            "stage": stage,
            "formed": formed,
            "horizon": state.horizon,
            "version_id": state.current_version,
            "material_change": state.material_change,
            "semantic_loss": not state.semantic_retained,
            "stale": False,
            "source_provenance": "PRINCIPAL_SIGNED_EVENT_STREAM",
            "opposition_preserved": True,
        }

    def ledger_snapshot(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.__ledger)
