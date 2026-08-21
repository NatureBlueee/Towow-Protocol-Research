#!/usr/bin/env python3
"""Cross-authority receipt controller for the bounded Wave 005-B simulation."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from domains import ExternalAnchor, HolderAuthority, RecipientAuthority
from protocol import (
    ProtocolError,
    envelope_hash,
    load_json,
    save_json_atomic,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


class InjectedCrash(RuntimeError):
    pass


class CrossAuthorityController:
    """Coordinator with no holder, recipient, or anchor signing key."""

    def __init__(
        self,
        *,
        contract: dict[str, Any],
        controller_key_id: str,
        controller_private_key: Ed25519PrivateKey,
        state_path: Path,
        holders: dict[str, HolderAuthority],
        recipients: dict[str, RecipientAuthority],
        anchor: ExternalAnchor,
    ):
        self.contract = contract
        self.controller_key_id = controller_key_id
        self.__controller_private_key = controller_private_key
        self.state_path = state_path
        self.holders = holders
        self.recipients = recipients
        self.anchor = anchor

    @property
    def step(self) -> int:
        return self.contract["evaluation_step"]

    def _new_state(self) -> dict[str, Any]:
        return {
            "schema": "towow.cross-authority-controller-state.v1",
            "controller_id": self.contract["controller_authority"],
            "contract_sha256": sha256_value(self.contract),
            "pinned_anchor_head": None,
            "pinned_anchor_sequence": 0,
            "commands": {},
        }

    def _state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return self._new_state()
        state = load_json(self.state_path)
        if state["contract_sha256"] != sha256_value(self.contract):
            raise ProtocolError(
                "CONTRACT_STATE_MISMATCH",
                "Controller state is bound to another contract.",
            )
        return state

    def _save(self, state: dict[str, Any]) -> None:
        save_json_atomic(self.state_path, state)

    @staticmethod
    def _maybe_crash(fault_after: str | None, point: str) -> None:
        if fault_after == point:
            raise InjectedCrash(f"Injected crash at {point}")

    def _verify_holder_authorization(
        self, envelope: dict[str, Any], expected_holder: str
    ) -> dict[str, Any]:
        body = verify_envelope(
            envelope,
            self.contract,
            expected_kind="HOLDER_AUTHORIZATION",
            expected_issuer=expected_holder,
            step=self.step,
        )
        if body.get("holder_authority") != expected_holder:
            raise ProtocolError(
                "AUTHORIZATION_HOLDER_MISMATCH",
                "Authorization body names a different holder authority.",
            )
        if body.get("world_id") != self.contract["world_id"]:
            raise ProtocolError(
                "WORLD_MISMATCH", "Authorization belongs to another world."
            )
        if body.get("evaluation_step") != self.step:
            raise ProtocolError(
                "WORLD_STEP_MISMATCH",
                "Authorization belongs to another evaluation step.",
            )
        return body

    def _holder_status(
        self, holder_id: str, authorization_id: str
    ) -> dict[str, Any]:
        endpoint = self.holders[holder_id]
        envelope = endpoint.status(authorization_id, self.step)
        body = verify_envelope(
            envelope,
            self.contract,
            expected_kind="AUTHORIZATION_STATUS",
            expected_issuer=holder_id,
            step=self.step,
        )
        if (
            body["authorization_id"] != authorization_id
            or body["holder_authority"] != holder_id
            or body["observed_at_step"] != self.step
        ):
            raise ProtocolError(
                "AUTHORIZATION_STATUS_BINDING_INVALID",
                "Holder status is not bound to this authorization and step.",
            )
        return body

    def _validate_request(
        self, request: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if request.get("world_id") != self.contract["world_id"]:
            raise ProtocolError("WORLD_MISMATCH", "Request world mismatch.")
        if request.get("evaluation_step") != self.step:
            raise ProtocolError(
                "WORLD_STEP_MISMATCH", "Request evaluation-step mismatch."
            )
        if not request.get("idempotency_key"):
            raise ProtocolError(
                "IDEMPOTENCY_KEY_INVALID", "A non-empty key is required."
            )
        route_type = request.get("route_type")
        if route_type not in {
            "DIRECT",
            "DERIVED",
            "RECIPROCAL",
        }:
            raise ProtocolError("ROUTE_TYPE_INVALID", "Unknown route type.")

        envelopes = request.get("authorizations", [])
        expected_count = 2 if route_type == "RECIPROCAL" else 1
        if len(envelopes) != expected_count:
            raise ProtocolError(
                "AUTHORIZATION_COUNT_INVALID",
                f"{route_type} requires {expected_count} authorization(s).",
            )
        holder_ids = request.get("holder_authorities", [])
        if len(holder_ids) != expected_count:
            raise ProtocolError(
                "HOLDER_COUNT_INVALID", "Holder coordinates are incomplete."
            )
        bodies = [
            self._verify_holder_authorization(envelope, holder_id)
            for envelope, holder_id in zip(envelopes, holder_ids)
        ]
        for body in bodies:
            if body.get("route_type") != route_type:
                raise ProtocolError(
                    "AUTHORIZED_ROUTE_TYPE_MISMATCH",
                    "Authorization does not permit this route type.",
                )
        self._validate_route_binding(request, bodies)
        return bodies, envelopes

    def _validate_route_binding(
        self, request: dict[str, Any], bodies: list[dict[str, Any]]
    ) -> None:
        route = request["route"]
        if request["route_type"] == "DIRECT":
            authorized = bodies[0]["route"]
            if route != authorized:
                raise ProtocolError(
                    "DIRECT_ROUTE_NOT_AUTHORIZED",
                    "Direct route differs from the signed holder route.",
                )
            return
        if request["route_type"] == "DERIVED":
            policy = bodies[0]["route_policy"]
            required = {
                "first_recipient": route.get("first_recipient"),
                "purpose": route.get("purpose"),
                "retention": route.get("retention"),
                "projection": route.get("projection"),
                "max_depth": 1,
            }
            if policy != required or route.get("onward_recipient") == route.get(
                "first_recipient"
            ):
                raise ProtocolError(
                    "DERIVED_ROUTE_NOT_AUTHORIZED",
                    "Source policy does not authorize the first hop and depth.",
                )
            return

        left, right = bodies
        if left["route"]["recipient"] != request["recipient_authorities"][1]:
            raise ProtocolError(
                "RECIPROCAL_COUNTERPARTY_MISMATCH",
                "First authorization does not name the other recipient.",
            )
        if right["route"]["recipient"] != request["recipient_authorities"][0]:
            raise ProtocolError(
                "RECIPROCAL_COUNTERPARTY_MISMATCH",
                "Second authorization does not name the other recipient.",
            )
        if request["route"]["compatibility_key"] != left["route"][
            "compatibility_key"
        ] or request["route"]["compatibility_key"] != right["route"][
            "compatibility_key"
        ]:
            raise ProtocolError(
                "RECIPROCAL_COMPATIBILITY_MISMATCH",
                "Reciprocal authorizations do not bind the same key.",
            )
        if {left["route"]["direction"], right["route"]["direction"]} != {
            "SEEK",
            "OFFER",
        }:
            raise ProtocolError(
                "RECIPROCAL_DIRECTION_MISMATCH",
                "Reciprocal exchange requires SEEK and OFFER.",
            )

    def _all_active(
        self, bodies: list[dict[str, Any]]
    ) -> tuple[bool, list[dict[str, Any]]]:
        statuses = [
            self._holder_status(
                body["holder_authority"], body["authorization_id"]
            )
            for body in bodies
        ]
        return not any(status["revoked"] for status in statuses), statuses

    def _verify_recipient_ack(
        self,
        envelope: dict[str, Any],
        *,
        kind: str,
        recipient: str,
        transaction_id: str,
    ) -> dict[str, Any]:
        body = verify_envelope(
            envelope,
            self.contract,
            expected_kind=kind,
            expected_issuer=recipient,
            step=self.step,
        )
        if (
            body.get("transaction_id") != transaction_id
            or body.get("recipient") != recipient
        ):
            raise ProtocolError(
                "RECIPIENT_ACK_BINDING_INVALID",
                "Recipient ACK does not bind this transaction and authority.",
            )
        return body

    def _verify_anchor_receipt(
        self,
        state: dict[str, Any],
        receipt: dict[str, Any],
        event: dict[str, Any],
        *,
        update_pin: bool,
    ) -> dict[str, Any]:
        body = verify_envelope(
            receipt,
            self.contract,
            expected_kind="ANCHOR_RECEIPT",
            expected_issuer=self.contract["anchor_authority"],
            step=self.step,
        )
        if body["event"] != event:
            raise ProtocolError(
                "ANCHOR_EVENT_BINDING_INVALID",
                "Anchor receipt binds different event bytes.",
            )
        if body["previous_head"] != state["pinned_anchor_head"]:
            raise ProtocolError(
                "ANCHOR_FORK_DETECTED",
                "Signed anchor receipt does not extend the pinned head.",
            )
        if body["sequence"] != state["pinned_anchor_sequence"] + 1:
            raise ProtocolError(
                "ANCHOR_SEQUENCE_INVALID",
                "Signed anchor receipt skips or rewinds sequence.",
            )
        expected_head = sha256_value(
            {
                "sequence": body["sequence"],
                "previous_head": body["previous_head"],
                "event_id": body["event_id"],
                "event": body["event"],
            }
        )
        if body["new_head"] != expected_head:
            raise ProtocolError(
                "ANCHOR_HEAD_INVALID",
                "Signed anchor head does not match canonical event bytes.",
            )
        if update_pin:
            state["pinned_anchor_head"] = body["new_head"]
            state["pinned_anchor_sequence"] = body["sequence"]
        return body

    def _append_anchor(
        self,
        state: dict[str, Any],
        *,
        event_id: str,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        receipt = self.anchor.append(
            event_id=event_id,
            event=event,
            expected_previous_head=state["pinned_anchor_head"],
            step=self.step,
        )
        self._verify_anchor_receipt(
            state, receipt, event, update_pin=True
        )
        return receipt

    def _prepare_leg(
        self,
        command: dict[str, Any],
        leg_name: str,
        *,
        fault_after: str | None,
        state: dict[str, Any],
    ) -> None:
        leg = command["legs"][leg_name]
        if "prepare_ack" in leg:
            return
        ack = self.recipients[leg["recipient"]].prepare(
            transaction_id=leg["transaction_id"],
            delivery=leg["delivery"],
            command_sha256=command["request_sha256"],
            step=self.step,
        )
        body = self._verify_recipient_ack(
            ack,
            kind="RECIPIENT_PREPARED_ACK",
            recipient=leg["recipient"],
            transaction_id=leg["transaction_id"],
        )
        if body["delivery_sha256"] != sha256_value(leg["delivery"]):
            raise ProtocolError(
                "PREPARE_ACK_DELIVERY_MISMATCH",
                "Recipient prepared different delivery bytes.",
            )
        leg["prepare_ack"] = ack
        self._save(state)
        self._maybe_crash(fault_after, f"after_prepare:{leg_name}")

    def _commit_group(
        self,
        command: dict[str, Any],
        leg_names: list[str],
        *,
        group_name: str,
        fault_after: str | None,
        state: dict[str, Any],
    ) -> None:
        group = command.setdefault("groups", {}).setdefault(group_name, {})
        if "decision_receipt" not in group:
            for leg_name in leg_names:
                leg = command["legs"][leg_name]
                prepared_body = self._verify_recipient_ack(
                    leg["prepare_ack"],
                    kind="RECIPIENT_PREPARED_ACK",
                    recipient=leg["recipient"],
                    transaction_id=leg["transaction_id"],
                )
                if prepared_body["delivery_sha256"] != sha256_value(
                    leg["delivery"]
                ):
                    raise ProtocolError(
                        "PREPARE_ACK_DELIVERY_MISMATCH",
                        "Persisted prepare ACK binds different delivery bytes.",
                    )
            active, statuses = self._all_active(command["authorization_bodies"])
            if not active:
                self._abort_before_decision(
                    command,
                    leg_names,
                    statuses=statuses,
                    state=state,
                )
                return
            event = {
                "decision": "COMMIT",
                "transaction_id": command["transaction_id"],
                "group_name": group_name,
                "leg_transaction_ids": [
                    command["legs"][name]["transaction_id"]
                    for name in leg_names
                ],
                "prepared_ack_sha256": [
                    envelope_hash(command["legs"][name]["prepare_ack"])
                    for name in leg_names
                ],
                "holder_status_sha256": [
                    sha256_value(status) for status in statuses
                ],
                "request_sha256": command["request_sha256"],
            }
            receipt = self._append_anchor(
                state,
                event_id=f"{command['transaction_id']}:{group_name}:decision",
                event=event,
            )
            group["decision_event"] = event
            group["decision_receipt"] = receipt
            self._save(state)
            self._maybe_crash(fault_after, f"after_decision:{group_name}")

        for index, leg_name in enumerate(leg_names):
            leg = command["legs"][leg_name]
            if "commit_ack" in leg:
                continue
            ack = self.recipients[leg["recipient"]].finalize(
                transaction_id=leg["transaction_id"],
                decision_receipt=group["decision_receipt"],
                step=self.step,
            )
            self._verify_recipient_ack(
                ack,
                kind="RECIPIENT_COMMIT_ACK",
                recipient=leg["recipient"],
                transaction_id=leg["transaction_id"],
            )
            leg["commit_ack"] = ack
            self._save(state)
            self._maybe_crash(
                fault_after, f"after_commit:{group_name}:{index + 1}"
            )

        if "completion_receipt" not in group:
            event = {
                "decision": "GROUP_COMPLETE",
                "transaction_id": command["transaction_id"],
                "group_name": group_name,
                "decision_receipt_sha256": envelope_hash(
                    group["decision_receipt"]
                ),
                "commit_ack_sha256": [
                    envelope_hash(command["legs"][name]["commit_ack"])
                    for name in leg_names
                ],
            }
            group["completion_event"] = event
            group["completion_receipt"] = self._append_anchor(
                state,
                event_id=f"{command['transaction_id']}:{group_name}:complete",
                event=event,
            )
            self._save(state)

    def _abort_before_decision(
        self,
        command: dict[str, Any],
        leg_names: list[str],
        *,
        statuses: list[dict[str, Any]],
        state: dict[str, Any],
    ) -> None:
        if command.get("outcome") is not None:
            return
        abort_acks = []
        for leg_name in leg_names:
            leg = command["legs"][leg_name]
            ack = self.recipients[leg["recipient"]].abort(
                transaction_id=leg["transaction_id"],
                reason="holder-authorization-revoked-before-decision",
                step=self.step,
            )
            self._verify_recipient_ack(
                ack,
                kind="RECIPIENT_ABORT_ACK",
                recipient=leg["recipient"],
                transaction_id=leg["transaction_id"],
            )
            abort_acks.append(ack)
        event = {
            "decision": "ABORT",
            "transaction_id": command["transaction_id"],
            "reason": "AUTHORIZATION_REVOKED",
            "holder_status_sha256": [sha256_value(item) for item in statuses],
            "abort_ack_sha256": [envelope_hash(item) for item in abort_acks],
        }
        receipt = self._append_anchor(
            state,
            event_id=f"{command['transaction_id']}:abort",
            event=event,
        )
        command["outcome"] = {
            "status": "REJECTED",
            "code": "AUTHORIZATION_REVOKED",
            "anchor_receipt": receipt,
            "state_changed": True,
        }
        self._save(state)

    def _build_command(
        self,
        request: dict[str, Any],
        bodies: list[dict[str, Any]],
        envelopes: list[dict[str, Any]],
    ) -> dict[str, Any]:
        request_hash = sha256_value(request)
        tx = f"tx-{request_hash[:24]}"
        route_type = request["route_type"]
        command: dict[str, Any] = {
            "request_sha256": request_hash,
            "transaction_id": tx,
            "route_type": route_type,
            "authorization_bodies": copy.deepcopy(bodies),
            "authorization_sha256": [
                envelope_hash(item) for item in envelopes
            ],
            "legs": {},
            "groups": {},
            "outcome": None,
        }
        if route_type == "DIRECT":
            route = request["route"]
            command["legs"]["direct"] = {
                "transaction_id": f"{tx}:direct",
                "recipient": route["recipient"],
                "delivery": {
                    "route_type": "DIRECT",
                    "source_holder": bodies[0]["holder_authority"],
                    "recipient": route["recipient"],
                    "purpose": route["purpose"],
                    "retention": route["retention"],
                    "projection": route["projection"],
                    "source_authorization_sha256": envelope_hash(
                        envelopes[0]
                    ),
                },
            }
        elif route_type == "DERIVED":
            route = request["route"]
            first = {
                "route_type": "DERIVED_FIRST_HOP",
                "source_holder": bodies[0]["holder_authority"],
                "recipient": route["first_recipient"],
                "purpose": route["purpose"],
                "retention": route["retention"],
                "projection": route["projection"],
                "source_authorization_sha256": envelope_hash(envelopes[0]),
            }
            onward = {
                "route_type": "DERIVED_ONWARD",
                "source_recipient": route["first_recipient"],
                "recipient": route["onward_recipient"],
                "purpose": route["purpose"],
                "retention": route["retention"],
                "projection": route["projection"],
                "source_authorization_sha256": envelope_hash(envelopes[0]),
            }
            command["legs"]["first"] = {
                "transaction_id": f"{tx}:first",
                "recipient": route["first_recipient"],
                "delivery": first,
            }
            command["legs"]["onward"] = {
                "transaction_id": f"{tx}:onward",
                "recipient": route["onward_recipient"],
                "delivery": onward,
            }
        else:
            for index, (body, envelope, recipient) in enumerate(
                zip(
                    bodies,
                    envelopes,
                    request["recipient_authorities"],
                )
            ):
                route = body["route"]
                command["legs"][f"side-{index + 1}"] = {
                    "transaction_id": f"{tx}:side-{index + 1}",
                    "recipient": route["recipient"],
                    "delivery": {
                        "route_type": "RECIPROCAL",
                        "source_holder": body["holder_authority"],
                        "recipient": route["recipient"],
                        "purpose": route["purpose"],
                        "retention": route["retention"],
                        "projection": route["projection"],
                        "compatibility_key": route["compatibility_key"],
                        "source_authorization_sha256": envelope_hash(
                            envelope
                        ),
                    },
                }
        return command

    def _finish(
        self, command: dict[str, Any], state: dict[str, Any]
    ) -> dict[str, Any]:
        for leg in command["legs"].values():
            self._verify_recipient_ack(
                leg["commit_ack"],
                kind="RECIPIENT_COMMIT_ACK",
                recipient=leg["recipient"],
                transaction_id=leg["transaction_id"],
            )
        final_event = {
            "decision": "ROUTE_COMPLETE",
            "transaction_id": command["transaction_id"],
            "route_type": command["route_type"],
            "group_completion_receipt_sha256": [
                envelope_hash(group["completion_receipt"])
                for group in command["groups"].values()
            ],
            "recipient_commit_ack_sha256": [
                envelope_hash(leg["commit_ack"])
                for leg in command["legs"].values()
            ],
            "onward_authorization_sha256": (
                envelope_hash(command["onward_authorization"])
                if command.get("onward_authorization")
                else None
            ),
        }
        receipt = self._append_anchor(
            state,
            event_id=f"{command['transaction_id']}:route-complete",
            event=final_event,
        )
        receipt_body = {
            "transaction_id": command["transaction_id"],
            "request_sha256": command["request_sha256"],
            "route_type": command["route_type"],
            "authorization_sha256": command["authorization_sha256"],
            "recipient_commit_ack_sha256": final_event[
                "recipient_commit_ack_sha256"
            ],
            "anchor_route_completion_sha256": envelope_hash(receipt),
            "anchor_head": state["pinned_anchor_head"],
            "status": "EXECUTED",
            "relation_status": "NOT_ESTABLISHED",
            "commitment_status": "NOT_CREATED",
            "real_world_effect_status": "NOT_CLAIMED",
        }
        controller_receipt = sign_envelope(
            self.__controller_private_key,
            kind="CONTROLLER_EXECUTION_RECEIPT",
            issuer=self.contract["controller_authority"],
            key_id=self.controller_key_id,
            body=receipt_body,
        )
        command["outcome"] = {
            "status": "EXECUTED",
            "route_type": command["route_type"],
            "controller_receipt": controller_receipt,
            "anchor_receipt": receipt,
            "recipient_commit_acks": [
                copy.deepcopy(leg["commit_ack"])
                for leg in command["legs"].values()
            ],
            "onward_authorization": copy.deepcopy(
                command.get("onward_authorization")
            ),
            "state_changed": True,
        }
        self._save(state)
        return copy.deepcopy(command["outcome"])

    def _execute_reserved(
        self,
        command: dict[str, Any],
        state: dict[str, Any],
        *,
        fault_after: str | None,
    ) -> dict[str, Any]:
        if command["outcome"] is not None:
            if command["outcome"]["status"] == "EXECUTED":
                for leg in command["legs"].values():
                    self._verify_recipient_ack(
                        leg["commit_ack"],
                        kind="RECIPIENT_COMMIT_ACK",
                        recipient=leg["recipient"],
                        transaction_id=leg["transaction_id"],
                    )
                anchor_body = verify_envelope(
                    command["outcome"]["anchor_receipt"],
                    self.contract,
                    expected_kind="ANCHOR_RECEIPT",
                    expected_issuer=self.contract["anchor_authority"],
                    step=self.step,
                )
                if (
                    anchor_body["new_head"] != state["pinned_anchor_head"]
                    or self.anchor.head() != state["pinned_anchor_head"]
                ):
                    raise ProtocolError(
                        "ANCHOR_FORK_DETECTED",
                        "Completed replay no longer matches the pinned anchor.",
                    )
                verify_envelope(
                    command["outcome"]["controller_receipt"],
                    self.contract,
                    expected_kind="CONTROLLER_EXECUTION_RECEIPT",
                    expected_issuer=self.contract["controller_authority"],
                    step=self.step,
                )
            replay = copy.deepcopy(command["outcome"])
            replay["state_changed"] = False
            replay["replay"] = "IDEMPOTENT_REPLAY"
            return replay

        route_type = command["route_type"]
        if route_type == "DIRECT":
            self._prepare_leg(
                command,
                "direct",
                fault_after=fault_after,
                state=state,
            )
            self._commit_group(
                command,
                ["direct"],
                group_name="direct",
                fault_after=fault_after,
                state=state,
            )
        elif route_type == "DERIVED":
            self._prepare_leg(
                command,
                "first",
                fault_after=fault_after,
                state=state,
            )
            self._commit_group(
                command,
                ["first"],
                group_name="first",
                fault_after=fault_after,
                state=state,
            )
            if command["outcome"] is not None:
                return copy.deepcopy(command["outcome"])
            if "onward_authorization" not in command:
                first = command["legs"]["first"]
                onward = command["legs"]["onward"]
                envelope = self.recipients[first["recipient"]].authorize_onward(
                    origin_transaction_id=first["transaction_id"],
                    onward_transaction_id=onward["transaction_id"],
                    onward_delivery=onward["delivery"],
                    source_authorization_sha256=command[
                        "authorization_sha256"
                    ][0],
                    step=self.step,
                )
                body = verify_envelope(
                    envelope,
                    self.contract,
                    expected_kind="ONWARD_AUTHORIZATION",
                    expected_issuer=first["recipient"],
                    step=self.step,
                )
                if body["onward_delivery"] != onward["delivery"]:
                    raise ProtocolError(
                        "ONWARD_AUTHORIZATION_BINDING_INVALID",
                        "First recipient signed a different onward delivery.",
                    )
                command["onward_authorization"] = envelope
                onward["delivery"]["onward_authorization_sha256"] = (
                    envelope_hash(envelope)
                )
                self._save(state)
                self._maybe_crash(fault_after, "after_onward_authorization")
            self._prepare_leg(
                command,
                "onward",
                fault_after=fault_after,
                state=state,
            )
            self._commit_group(
                command,
                ["onward"],
                group_name="onward",
                fault_after=fault_after,
                state=state,
            )
        else:
            for name in ["side-1", "side-2"]:
                self._prepare_leg(
                    command,
                    name,
                    fault_after=fault_after,
                    state=state,
                )
            self._commit_group(
                command,
                ["side-1", "side-2"],
                group_name="reciprocal",
                fault_after=fault_after,
                state=state,
            )

        if command["outcome"] is not None:
            return copy.deepcopy(command["outcome"])
        return self._finish(command, state)

    def execute(
        self, request: dict[str, Any], *, fault_after: str | None = None
    ) -> dict[str, Any]:
        try:
            bodies, envelopes = self._validate_request(request)
            state = self._state()
            key = request["idempotency_key"]
            request_hash = sha256_value(request)
            existing = state["commands"].get(key)
            if existing is not None:
                if existing["request_sha256"] != request_hash:
                    raise ProtocolError(
                        "IDEMPOTENCY_CONFLICT",
                        "Idempotency key is bound to different request bytes.",
                    )
                return self._execute_reserved(
                    existing, state, fault_after=fault_after
                )

            active, statuses = self._all_active(bodies)
            if not active:
                return {
                    "status": "REJECTED",
                    "code": "AUTHORIZATION_REVOKED",
                    "state_changed": False,
                    "holder_status": statuses,
                }
            command = self._build_command(request, bodies, envelopes)
            state["commands"][key] = command
            self._save(state)
            self._maybe_crash(fault_after, "after_reservation")
            return self._execute_reserved(
                command, state, fault_after=fault_after
            )
        except ProtocolError as error:
            return {
                "status": "REJECTED",
                "code": error.code,
                "message": error.message,
                "state_changed": False,
            }
