"""Authority-only truth owner with a private transactional reservation ledger."""

from __future__ import annotations

import copy
import threading
from dataclasses import fields
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from common import canonical_bytes, public_key_hex, sign_envelope
from world_factory import AuthorityPrivateWorld


DOMAIN = "TOWOW-WAVE009-AUTHORITY"


class AuthorityTruthBroker:
    def __init__(self, state: AuthorityPrivateWorld) -> None:
        self.__state = state
        self.__broker_key = Ed25519PrivateKey.generate()
        principals = (
            ["SEEKER", "RESOURCE_OWNER"]
            if state.task_kind == "T3"
            else ["PRIME", "FIELD", "ASSURE"]
        )
        names = [f"AUTH-{name}" for name in principals]
        names.extend(["AUTH-CONTROLLER", "AUTH-STANDING"])
        self.__keys = {
            name: Ed25519PrivateKey.generate() for name in names
        }
        self.__ledger: list[dict[str, Any]] = []
        self.__reservation_index: dict[str, dict[str, Any]] = {}
        self.__reservation_lock = threading.Lock()

    def private_state_shape(self) -> list[str]:
        return [item.name for item in fields(self.__state)]

    def public_contract(self) -> dict[str, Any]:
        return {
            "schema": "towow.wave009-authority-contract.v1",
            "domain": DOMAIN,
            "broker_public_key": public_key_hex(self.__broker_key),
            "issuer_keys": {
                issuer: public_key_hex(key)
                for issuer, key in self.__keys.items()
            }
            | {"AUTH-BROKER": public_key_hex(self.__broker_key)},
            "current_revoke_head": (
                5
                if self.__state.authority_mode == "REVOKED"
                else self.__state.current_revoke_head
            ),
        }

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
                "operation": "ISSUE_AUTHORITY_EVIDENCE",
                "kind": kind,
                "issuer": issuer,
                "payload_sha256": envelope["payload_sha256"],
                "byte_count": len(canonical_bytes(envelope)),
            }
        )
        return envelope

    def _reserve(
        self,
        *,
        issuer: str,
        task: dict[str, Any],
        reservation_id: str,
        idempotency_key: str,
        context_sha256: str,
    ) -> dict[str, Any]:
        slot_key = "|".join(
            [task["resource"], task["time_window"], task["purpose"]]
        )
        body = {
            "world_id": self.__state.world_id,
            "task_fingerprint": task["task_fingerprint"],
            "reservation_id": reservation_id,
            "idempotency_key": idempotency_key,
            "resource": task["resource"],
            "time_window": task["time_window"],
            "purpose": task["purpose"],
            "relation_version": self.__state.current_relation_version,
            "lease_expiry_step": 10,
            "issuance_context_sha256": context_sha256,
            "event_owner_domain": DOMAIN,
        }
        with self.__reservation_lock:
            existing = self.__reservation_index.get(slot_key)
            if existing is None:
                self.__reservation_index[slot_key] = copy.deepcopy(body)
                kind = "RESERVATION"
                body["status"] = "RESERVED"
            else:
                kind = "RESERVATION_CONFLICT"
                body["status"] = "REJECTED_DUPLICATE"
                body["conflicts_with"] = existing["reservation_id"]
            return self._issue(issuer, kind, body)

    def issue_public_evidence(
        self,
        task: dict[str, Any],
        issuance_context: dict[str, Any],
    ) -> dict[str, Any]:
        state = self.__state
        principals = task["principals"]
        events: list[dict[str, Any]] = []
        context_envelope = sign_envelope(
            self.__broker_key,
            domain=DOMAIN,
            issuer="AUTH-BROKER",
            kind="SECTION_CONTEXT",
            body=issuance_context,
        )
        context_sha256 = context_envelope["payload_sha256"]
        self.__ledger.append(
            {
                "operation": "SEAL_AUTHORITY_SECTION_CONTEXT",
                "payload_sha256": context_sha256,
                "byte_count": len(canonical_bytes(context_envelope)),
            }
        )
        current_head = (
            5 if state.authority_mode == "REVOKED" else state.current_revoke_head
        )
        for index, principal in enumerate(principals):
            principal_issuer = f"AUTH-{principal}"
            issuer = (
                "AUTH-CONTROLLER"
                if state.authority_mode == "CONTROLLER_SUBSTITUTION"
                and index == 0
                else principal_issuer
            )
            version = (
                "REL-V1"
                if state.authority_mode == "STALE_VERSION" and index == 0
                else state.current_relation_version
            )
            events.append(
                self._issue(
                    issuer,
                    "MANDATE",
                    {
                        "world_id": state.world_id,
                        "task_fingerprint": task["task_fingerprint"],
                        "principal_id": principal,
                        "actor_entity": principal,
                        "controller": "CONTROLLER",
                        "action": task["required_action"],
                        "purpose": task["purpose"],
                        "resource": task["resource"],
                        "time_window": task["time_window"],
                        "counterparty": task["counterparty"],
                        "relation_version": version,
                        "revoke_head": state.current_revoke_head,
                        "issuance_context_sha256": context_sha256,
                        "event_owner_domain": DOMAIN,
                    },
                )
            )
            events.append(
                self._issue(
                    principal_issuer,
                    "COMMITMENT",
                    {
                        "world_id": state.world_id,
                        "task_fingerprint": task["task_fingerprint"],
                        "principal_id": principal,
                        "action": task["required_action"],
                        "purpose": task["purpose"],
                        "relation_version": state.current_relation_version,
                        "status": "PROMISED_NOT_EXECUTED",
                        "issuance_context_sha256": context_sha256,
                        "event_owner_domain": DOMAIN,
                    },
                )
            )
        if state.authority_mode == "REVOKED":
            events.append(
                self._issue(
                    f"AUTH-{principals[0]}",
                    "REVOCATION",
                    {
                        "world_id": state.world_id,
                        "task_fingerprint": task["task_fingerprint"],
                        "principal_id": principals[0],
                        "new_revoke_head": current_head,
                        "scope": task["required_action"],
                        "historical_relation_unchanged": True,
                        "issuance_context_sha256": context_sha256,
                        "event_owner_domain": DOMAIN,
                    },
                )
            )
        owner = f"AUTH-{principals[0]}"
        if state.authority_mode == "DUPLICATE_RESERVATION":
            race = self.concurrent_reservation_probe(
                task,
                context_sha256=context_sha256,
            )
            events.extend(race["events"])
        else:
            events.append(
                self._reserve(
                    issuer=owner,
                    task=task,
                    reservation_id="RSV-PRIMARY",
                    idempotency_key="IDEM-PRIMARY",
                    context_sha256=context_sha256,
                )
            )
        events.append(
            self._issue(
                "AUTH-STANDING",
                "STANDING",
                {
                    "world_id": state.world_id,
                    "task_fingerprint": task["task_fingerprint"],
                    "acceptance_authority": task["acceptance_authority"],
                    "action": task["required_action"],
                    "active": state.authority_mode != "REVOKED",
                    "issuance_context_sha256": context_sha256,
                    "event_owner_domain": DOMAIN,
                },
            )
        )
        return {
            "schema": "towow.wave009-authority-evidence.v1",
            "current_relation_version": state.current_relation_version,
            "current_revoke_head": current_head,
            "section_context": context_envelope,
            "events": events,
            "contract": self.public_contract(),
        }

    def concurrent_reservation_probe(
        self,
        task: dict[str, Any],
        *,
        context_sha256: str = "CONCURRENCY-PROBE",
        include_existing: bool = False,
    ) -> dict[str, Any]:
        """Run two actual threads against the same atomic reservation index."""

        principals = task["principals"]
        owner = f"AUTH-{principals[0]}"
        barrier = threading.Barrier(2)
        results: list[dict[str, Any]] = []
        results_lock = threading.Lock()

        if include_existing:
            # issue_public_evidence already inserted the primary reservation.
            reservation_ids = ["RSV-RACING-SECOND", "RSV-RACING-THIRD"]
        else:
            reservation_ids = ["RSV-RACE-A", "RSV-RACE-B"]

        def attempt(reservation_id: str) -> None:
            barrier.wait()
            event = self._reserve(
                issuer=owner,
                task=task,
                reservation_id=reservation_id,
                idempotency_key=f"IDEM-{reservation_id}",
                context_sha256=context_sha256,
            )
            with results_lock:
                results.append(event)

        threads = [
            threading.Thread(target=attempt, args=(reservation_id,))
            for reservation_id in reservation_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        if any(thread.is_alive() for thread in threads):
            raise RuntimeError("RESERVATION_RACE_DID_NOT_TERMINATE")
        successful = sum(
            event["kind"] == "RESERVATION" for event in results
        )
        conflicts = sum(
            event["kind"] == "RESERVATION_CONFLICT" for event in results
        )
        return {
            "events": results,
            "successful": successful,
            "conflicts": conflicts,
        }

    def expected_outcome(self) -> dict[str, Any]:
        mode = self.__state.authority_mode
        mandate_valid = mode not in {
            "STALE_VERSION",
            "CONTROLLER_SUBSTITUTION",
            "REVOKED",
        }
        commitment_valid = True
        reservation_valid = mode != "DUPLICATE_RESERVATION"
        standing_valid = mode != "REVOKED"
        error = {
            "NONE": None,
            "STALE_VERSION": "STALE_RELATION_VERSION",
            "CONTROLLER_SUBSTITUTION": "CONTROLLER_NOT_PRINCIPAL",
            "REVOKED": "MANDATE_REVOKED",
            "DUPLICATE_RESERVATION": "DUPLICATE_RESERVATION_CONFLICT",
        }[mode]
        return {
            "permit_status": "PERMIT" if mandate_valid else "DENY",
            "mandate_valid": mandate_valid,
            "commitment_valid": commitment_valid,
            "reservation_valid": reservation_valid,
            "standing_valid": standing_valid,
            "authority_chain_valid": all(
                [
                    mandate_valid,
                    commitment_valid,
                    reservation_valid,
                    standing_valid,
                ]
            ),
            "error": error,
            "current_relation_version": self.__state.current_relation_version,
        }

    def ledger_snapshot(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self.__ledger)

    def successful_reservation_count(self) -> int:
        return len(self.__reservation_index)
