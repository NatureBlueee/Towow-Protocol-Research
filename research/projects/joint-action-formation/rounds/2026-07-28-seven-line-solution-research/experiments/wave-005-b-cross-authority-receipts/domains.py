"""Independent authority-domain simulators.

Each class owns its private signing key and durable state.  The controller is
given only method endpoints and the public registry, never recipient, holder,
or anchor private-key bytes.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from protocol import (
    ProtocolError,
    envelope_hash,
    load_json,
    save_json_atomic,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


def _initial_state(schema: str, authority_id: str) -> dict[str, Any]:
    return {"schema": schema, "authority_id": authority_id}


class SigningDomain:
    def __init__(
        self,
        authority_id: str,
        key_id: str,
        private_key: Ed25519PrivateKey,
        state_path: Path,
    ):
        self.authority_id = authority_id
        self.key_id = key_id
        self.__private_key = private_key
        self.state_path = state_path

    def _sign(self, kind: str, body: dict[str, Any]) -> dict[str, Any]:
        return sign_envelope(
            self.__private_key,
            kind=kind,
            issuer=self.authority_id,
            key_id=self.key_id,
            body=body,
        )

    def _load_or_create(self, default: dict[str, Any]) -> dict[str, Any]:
        if self.state_path.exists():
            return load_json(self.state_path)
        save_json_atomic(self.state_path, default)
        return copy.deepcopy(default)


class HolderAuthority(SigningDomain):
    def _state(self) -> dict[str, Any]:
        return self._load_or_create(
            {
                **_initial_state("towow.holder-domain-state.v1", self.authority_id),
                "issued": {},
                "revoked": {},
                "status_epoch": 0,
            }
        )

    def issue_authorization(self, body: dict[str, Any]) -> dict[str, Any]:
        if body.get("holder_authority") != self.authority_id:
            raise ProtocolError(
                "HOLDER_BODY_ISSUER_MISMATCH",
                "Holder will not sign another authority's authorization.",
            )
        envelope = self._sign("HOLDER_AUTHORIZATION", body)
        state = self._state()
        state["issued"][body["authorization_id"]] = envelope_hash(envelope)
        save_json_atomic(self.state_path, state)
        return envelope

    def status(self, authorization_id: str, step: int) -> dict[str, Any]:
        state = self._state()
        return self._sign(
            "AUTHORIZATION_STATUS",
            {
                "authorization_id": authorization_id,
                "holder_authority": self.authority_id,
                "revoked": authorization_id in state["revoked"],
                "revocation": state["revoked"].get(authorization_id),
                "status_epoch": state["status_epoch"],
                "observed_at_step": step,
            },
        )

    def revoke(
        self, authorization_id: str, *, step: int, reason: str
    ) -> dict[str, Any]:
        state = self._state()
        if authorization_id not in state["issued"]:
            raise ProtocolError(
                "UNKNOWN_AUTHORIZATION",
                "The holder cannot revoke an authorization it never issued.",
            )
        state["status_epoch"] += 1
        body = {
            "authorization_id": authorization_id,
            "holder_authority": self.authority_id,
            "revoked_at_step": step,
            "reason": reason,
            "status_epoch": state["status_epoch"],
        }
        state["revoked"][authorization_id] = body
        save_json_atomic(self.state_path, state)
        return self._sign("AUTHORIZATION_REVOCATION", body)


class RecipientAuthority(SigningDomain):
    def __init__(
        self,
        authority_id: str,
        key_id: str,
        private_key: Ed25519PrivateKey,
        state_path: Path,
        contract: dict[str, Any],
    ):
        super().__init__(authority_id, key_id, private_key, state_path)
        self.contract = contract

    def _state(self) -> dict[str, Any]:
        return self._load_or_create(
            {
                **_initial_state(
                    "towow.recipient-domain-state.v1", self.authority_id
                ),
                "prepared": {},
                "committed": {},
                "aborted": {},
                "onward_authorizations": {},
            }
        )

    def prepare(
        self,
        *,
        transaction_id: str,
        delivery: dict[str, Any],
        command_sha256: str,
        step: int,
    ) -> dict[str, Any]:
        if delivery.get("recipient") != self.authority_id:
            raise ProtocolError(
                "RECIPIENT_MISMATCH",
                "Delivery is addressed to a different recipient authority.",
            )
        state = self._state()
        body = {
            "transaction_id": transaction_id,
            "recipient": self.authority_id,
            "delivery_sha256": sha256_value(delivery),
            "command_sha256": command_sha256,
            "prepared_at_step": step,
        }
        existing = state["prepared"].get(transaction_id)
        if existing is not None:
            if existing["body"] != body:
                raise ProtocolError(
                    "RECIPIENT_TRANSACTION_CONFLICT",
                    "Recipient transaction id is already bound to other bytes.",
                )
            return existing["ack"]
        if transaction_id in state["aborted"]:
            raise ProtocolError(
                "RECIPIENT_TRANSACTION_ABORTED",
                "Recipient transaction was already aborted.",
            )
        ack = self._sign("RECIPIENT_PREPARED_ACK", body)
        state["prepared"][transaction_id] = {
            "body": body,
            "delivery": copy.deepcopy(delivery),
            "ack": ack,
        }
        save_json_atomic(self.state_path, state)
        return ack

    def finalize(
        self,
        *,
        transaction_id: str,
        decision_receipt: dict[str, Any],
        step: int,
    ) -> dict[str, Any]:
        decision = verify_envelope(
            decision_receipt,
            self.contract,
            expected_kind="ANCHOR_RECEIPT",
            expected_issuer=self.contract["anchor_authority"],
            step=step,
        )
        event = decision["event"]
        if event.get("decision") != "COMMIT":
            raise ProtocolError(
                "ANCHOR_DECISION_NOT_COMMIT",
                "Recipient only finalizes an anchored COMMIT decision.",
            )
        if transaction_id not in event.get("leg_transaction_ids", []):
            raise ProtocolError(
                "ANCHOR_TRANSACTION_MISMATCH",
                "Anchor decision does not include this delivery transaction.",
            )

        state = self._state()
        existing = state["committed"].get(transaction_id)
        if existing is not None:
            return existing["ack"]
        prepared = state["prepared"].get(transaction_id)
        if prepared is None:
            raise ProtocolError(
                "RECIPIENT_NOT_PREPARED",
                "Recipient has no prepared delivery for this transaction.",
            )
        prepared_hash = envelope_hash(prepared["ack"])
        if prepared_hash not in event.get("prepared_ack_sha256", []):
            raise ProtocolError(
                "PREPARED_ACK_NOT_ANCHORED",
                "The anchor decision does not bind this recipient's prepare ACK.",
            )

        body = {
            "transaction_id": transaction_id,
            "recipient": self.authority_id,
            "delivery_sha256": prepared["body"]["delivery_sha256"],
            "decision_receipt_sha256": envelope_hash(decision_receipt),
            "committed_at_step": step,
        }
        ack = self._sign("RECIPIENT_COMMIT_ACK", body)
        state["committed"][transaction_id] = {
            "delivery": prepared["delivery"],
            "ack": ack,
        }
        save_json_atomic(self.state_path, state)
        return ack

    def abort(
        self, *, transaction_id: str, reason: str, step: int
    ) -> dict[str, Any]:
        state = self._state()
        if transaction_id in state["committed"]:
            raise ProtocolError(
                "CANNOT_ABORT_COMMITTED",
                "An anchored committed delivery cannot be retroactively aborted.",
            )
        body = {
            "transaction_id": transaction_id,
            "recipient": self.authority_id,
            "reason": reason,
            "aborted_at_step": step,
        }
        existing = state["aborted"].get(transaction_id)
        if existing is not None:
            return existing
        ack = self._sign("RECIPIENT_ABORT_ACK", body)
        state["prepared"].pop(transaction_id, None)
        state["aborted"][transaction_id] = ack
        save_json_atomic(self.state_path, state)
        return ack

    def authorize_onward(
        self,
        *,
        origin_transaction_id: str,
        onward_transaction_id: str,
        onward_delivery: dict[str, Any],
        source_authorization_sha256: str,
        step: int,
    ) -> dict[str, Any]:
        state = self._state()
        origin = state["committed"].get(origin_transaction_id)
        if origin is None:
            raise ProtocolError(
                "ORIGIN_NOT_COMMITTED",
                "Recipient will not authorize onward disclosure before commit.",
            )
        body = {
            "origin_transaction_id": origin_transaction_id,
            "origin_commit_ack_sha256": envelope_hash(origin["ack"]),
            "onward_transaction_id": onward_transaction_id,
            "from_recipient_authority": self.authority_id,
            "onward_delivery": copy.deepcopy(onward_delivery),
            "source_authorization_sha256": source_authorization_sha256,
            "authorized_at_step": step,
        }
        existing = state["onward_authorizations"].get(onward_transaction_id)
        if existing is not None:
            if existing["body"] != body:
                raise ProtocolError(
                    "ONWARD_AUTHORIZATION_CONFLICT",
                    "Onward transaction id is already bound to another route.",
                )
            return existing["envelope"]
        envelope = self._sign("ONWARD_AUTHORIZATION", body)
        state["onward_authorizations"][onward_transaction_id] = {
            "body": body,
            "envelope": envelope,
        }
        save_json_atomic(self.state_path, state)
        return envelope


class ExternalAnchor(SigningDomain):
    def _state(self) -> dict[str, Any]:
        return self._load_or_create(
            {
                **_initial_state(
                    "towow.external-anchor-state.v1", self.authority_id
                ),
                "head": None,
                "entries": [],
            }
        )

    def append(
        self,
        *,
        event_id: str,
        event: dict[str, Any],
        expected_previous_head: str | None,
        step: int,
    ) -> dict[str, Any]:
        state = self._state()
        for entry in state["entries"]:
            receipt = entry["receipt"]
            body = receipt["body"]
            if body["event_id"] != event_id:
                continue
            if body["event"] != event:
                raise ProtocolError(
                    "ANCHOR_EVENT_CONFLICT",
                    "Anchor event id is already bound to different bytes.",
                )
            return receipt
        if state["head"] != expected_previous_head:
            raise ProtocolError(
                "ANCHOR_HEAD_MISMATCH",
                "Append expected a different anchor head.",
            )
        sequence = len(state["entries"]) + 1
        new_head = sha256_value(
            {
                "sequence": sequence,
                "previous_head": state["head"],
                "event_id": event_id,
                "event": event,
            }
        )
        body = {
            "anchor_authority": self.authority_id,
            "sequence": sequence,
            "previous_head": state["head"],
            "new_head": new_head,
            "event_id": event_id,
            "event": copy.deepcopy(event),
            "anchored_at_step": step,
        }
        receipt = self._sign("ANCHOR_RECEIPT", body)
        state["entries"].append({"receipt": receipt})
        state["head"] = new_head
        save_json_atomic(self.state_path, state)
        return receipt

    def head(self) -> str | None:
        return self._state()["head"]
