#!/usr/bin/env python3
"""Stateful raw-response services for the Wave 011 G4 pilot.

The service owns hidden state. Candidate workers can invoke only named
primitives and receive the raw owner/provider response. Interpretation such as
"current", "fenced", "authoritative", or "safe" is deliberately absent.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any


FORBIDDEN_RESPONSE_FIELDS = {
    "head_current",
    "fenced",
    "authoritative",
    "safe_to_rely",
    "ground_truth",
    "expected_decision",
}

FORMATION_ACTIONS = {
    "read_revision",
    "read_policy",
    "get_token_state",
    "read_dependency",
    "request_authority",
    "request_reservation",
    "request_delegation",
    "discover_status_api",
}
EXECUTION_ACTIONS = {"submit_operation", "read_operation_status"}

ACTION_COSTS = {
    "read_revision": (2, 80, 1, 0),
    "read_policy": (3, 180, 2, 0),
    "get_token_state": (3, 140, 3, 0),
    "read_dependency": (5, 120, 4, 0),
    "request_authority": (7, 220, 5, 1),
    "request_reservation": (5, 200, 3, 0),
    "request_delegation": (9, 260, 5, 1),
    "discover_status_api": (2, 110, 1, 0),
    "submit_operation": (8, 160, 4, 0),
    "read_operation_status": (6, 190, 4, 0),
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _walk_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for child in value.values():
            keys.update(_walk_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_walk_keys(child))
        return keys
    return set()


@dataclass(frozen=True)
class Cost:
    latency_ticks: int
    disclosed_bytes: int
    sensitivity: int
    human_interruptions: int

    def as_dict(self) -> dict[str, int]:
        return {
            "latency_ticks": self.latency_ticks,
            "disclosed_bytes": self.disclosed_bytes,
            "sensitivity": self.sensitivity,
            "human_interruptions": self.human_interruptions,
        }


class PrimitiveService:
    """One deterministic hidden world and its immutable audit log."""

    def __init__(
        self,
        world_ref: str,
        public_packet: dict[str, Any],
        base_state: dict[str, Any],
        override: dict[str, Any],
        allowed_actions: list[str],
    ) -> None:
        self.world_ref = world_ref
        self.public_packet = copy.deepcopy(public_packet)
        self.state = deep_merge(base_state, override)
        self.allowed_actions = set(allowed_actions)
        self.operation = self.public_packet["operation"]
        self.tick = 0
        self.log: list[dict[str, Any]] = []
        self.target_record: dict[str, Any] | None = None
        self.acceptance_record: dict[str, Any] | None = None
        self.attempts: list[dict[str, Any]] = []
        self.authority_observed = False
        self.delegation_observed = False
        self.reservation_observed = False
        self.authority_revoked = False
        self.p1_snapshot: dict[str, bool] | None = None
        self._bind_request_values()

    def _bind_request_values(self) -> None:
        op_hash = self.operation["arguments_hash"]
        for key in ("authority_record", "reservation_record"):
            if self.state[key].get("operation_hash") == "MATCH_REQUEST":
                self.state[key]["operation_hash"] = op_hash
        self.state["token_record"]["token_id"] = self.operation["token_id"]
        self.state["reservation_record"]["resource_id"] = self.operation["resource_id"]

    def initial_truth(self) -> dict[str, bool]:
        return copy.deepcopy(self.state["p0"])

    def freeze_p1(self) -> dict[str, bool]:
        if self.p1_snapshot is not None:
            raise RuntimeError("P1 already frozen")
        self.p1_snapshot = {
            "Y_success": self._would_submit_succeed(),
            "Y_resolution": self._resolution_path_available(),
        }
        self.log.append(
            {
                "event": "P1_TRUTH_FROZEN",
                "tick": self.tick,
                "private_truth": copy.deepcopy(self.p1_snapshot),
            }
        )
        return copy.deepcopy(self.p1_snapshot)

    def call(self, action: str, args: dict[str, Any]) -> dict[str, Any] | None:
        if action not in self.allowed_actions:
            raise PermissionError(f"action not exposed in this world: {action}")
        if action not in ACTION_COSTS:
            raise ValueError(f"unknown action: {action}")
        latency, disclosed, sensitivity, human = ACTION_COSTS[action]
        self.tick += latency
        handler = getattr(self, f"_do_{action}")
        raw = handler(copy.deepcopy(args))
        if raw is not None:
            forbidden = FORBIDDEN_RESPONSE_FIELDS & _walk_keys(raw)
            if forbidden:
                raise RuntimeError(f"primitive leaked pre-adjudicated fields: {sorted(forbidden)}")
            encoded_size = len(
                json.dumps(raw, ensure_ascii=False, sort_keys=True).encode("utf-8")
            )
        else:
            encoded_size = 0
        cost = Cost(latency, max(disclosed, encoded_size), sensitivity, human)
        self.log.append(
            {
                "event": "PRIMITIVE_CALL",
                "tick": self.tick,
                "action": action,
                "args": copy.deepcopy(args),
                "raw_response": copy.deepcopy(raw),
                "cost": cost.as_dict(),
            }
        )
        return raw

    def _do_read_revision(self, args: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(self.state["revision_record"])

    def _do_read_policy(self, args: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(self.state["policy_record"])

    def _do_get_token_state(self, args: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(self.state["token_record"])

    def _do_read_dependency(self, args: dict[str, Any]) -> dict[str, Any]:
        record = copy.deepcopy(self.state["dependency_record"])
        if record.get("query_mode") == "DECLARED_UNQUERYABLE":
            return {
                "issuer": record.get("issuer", "dependency-owner"),
                "dependency_id": record.get("dependency_id", "dep-7"),
                "provider_response": "REFUSE_DISCLOSURE",
                "query_mode": "DECLARED_UNQUERYABLE",
                "revision": record.get("revision", 2),
            }
        return record

    def _do_request_authority(self, args: dict[str, Any]) -> dict[str, Any]:
        record = copy.deepcopy(self.state["authority_record"])
        self.authority_observed = record.get("owner_decision") == "APPROVE"
        self._apply_post_authority_event()
        return record

    def _do_request_delegation(self, args: dict[str, Any]) -> dict[str, Any]:
        record = copy.deepcopy(self.state["delegation_record"])
        self.delegation_observed = record.get("delegation_decision") == "APPROVE"
        self._apply_post_authority_event()
        return record

    def _apply_post_authority_event(self) -> None:
        if (
            self.state.get("event_after_authority") == "REVOKE_AUTHORITY"
            and not self.authority_revoked
        ):
            self.authority_revoked = True
            self.log.append(
                {
                    "event": "HIDDEN_AUTHORITY_REVOCATION",
                    "tick": self.tick + 1,
                    "issuer": self.state["authority_record"]["issuer"],
                    "revision": self.state["authority_record"].get("revision", 0) + 1,
                }
            )

    def _do_request_reservation(self, args: dict[str, Any]) -> dict[str, Any]:
        record = copy.deepcopy(self.state["reservation_record"])
        self.reservation_observed = record.get("reservation_decision") == "RESERVED"
        return record

    def _do_discover_status_api(self, args: dict[str, Any]) -> dict[str, Any]:
        return copy.deepcopy(self.state["status_api_record"])

    def _do_submit_operation(self, args: dict[str, Any]) -> dict[str, Any] | None:
        attempt_no = len(self.attempts) + 1
        mode = self.state["submit_mode"]
        direct_revision_matches = (
            args.get("authority_revision")
            == self.state["authority_record"].get("revision")
        )
        delegation_revision_matches = (
            args.get("delegation_revision")
            == self.state["delegation_record"].get("revision")
            and args.get("delegate") == self.state["delegation_record"].get("delegate")
        )
        authority_basis_present = direct_revision_matches or delegation_revision_matches
        reservation_sequence_matches = (
            args.get("reservation_sequence")
            == self.state["reservation_record"].get("fence_sequence")
        )
        success = (
            self._would_submit_succeed()
            and authority_basis_present
            and (
                reservation_sequence_matches
                or not self.state.get("target_requires_reservation_sequence", True)
            )
        )
        if mode in {"NO_EFFECT_RESPONSE_LOST", "REJECT_NO_EFFECT"}:
            success = False
        if mode in {"EXECUTE_RESPONSE_LOST", "RETURN_SUCCESS"} and success:
            self.target_record = {
                "issuer": self.public_packet["source_contract"]["effect_owner"],
                "operation_id": self.operation["operation_id"],
                "object_id": self.operation["target_id"],
                "state": "SUCCEEDED",
                "attempt_no": attempt_no,
                "effect_revision": attempt_no,
            }
            if self.state.get("acceptance_mode") == "ACCEPT_ON_SUCCESS":
                self.acceptance_record = {
                    "issuer": self.public_packet["source_contract"]["acceptance_owner"],
                    "operation_id": self.operation["operation_id"],
                    "decision": "ACCEPT",
                    "revision": 1,
                }
        attempt = {
            "attempt_no": attempt_no,
            "executor_result": "SUCCESS" if success else "NO_EFFECT",
            "operation_id": self.operation["operation_id"],
            "object_id": self.operation["target_id"],
        }
        self.attempts.append(attempt)
        if mode in {"EXECUTE_RESPONSE_LOST", "NO_EFFECT_RESPONSE_LOST"}:
            return None
        if success:
            return {
                "issuer": "execution-provider",
                "operation_id": self.operation["operation_id"],
                "provider_result": "COMPLETED",
                "attempt_no": attempt_no,
            }
        return {
            "issuer": "execution-provider",
            "operation_id": self.operation["operation_id"],
            "provider_result": "REJECTED_NO_EFFECT",
            "attempt_no": attempt_no,
        }

    def _do_read_operation_status(self, args: dict[str, Any]) -> dict[str, Any]:
        mode = self.state["readback_mode"]
        if mode == "WRONG_OBJECT":
            return {
                "issuer": self.public_packet["source_contract"]["effect_owner"],
                "operation_id": "refund-OTHER-K0",
                "object_id": "charge-OTHER",
                "state": "SUCCEEDED",
                "effect_revision": 4,
            }
        if self.target_record is not None:
            return copy.deepcopy(self.target_record)
        return {
            "issuer": self.public_packet["source_contract"]["effect_owner"],
            "operation_id": self.operation["operation_id"],
            "object_id": self.operation["target_id"],
            "state": "NO_RECORD",
            "effect_revision": 0,
        }

    def _policy_allows_artifact(self) -> bool:
        policy = self.state["policy_record"]
        exact = self.operation["artifact_revision"]
        current = self.state["revision_record"]["revision"]
        if exact in policy.get("revoked_revisions", []):
            return False
        if policy.get("mode") == "CURRENT_SECURITY_HEAD_REQUIRED":
            return exact == current and exact in policy.get("allowed_revisions", [])
        return exact in policy.get("allowed_revisions", [])

    def _authority_allows(self) -> bool:
        record = self.state["authority_record"]
        delegation = self.state["delegation_record"]
        if record.get("owner_decision") == "REFUSE_DISCLOSURE":
            return bool(self.state.get("call_time_authority_allows", False))
        direct_ok = record.get("owner_decision") == "APPROVE"
        delegated_ok = (
            self.delegation_observed
            and delegation.get("delegation_decision") == "APPROVE"
            and delegation.get("scope") == "exact-operation"
        )
        terms = (
            delegation.get("revocation_terms")
            if delegated_ok
            else record.get("revocation_terms")
        )
        if self.authority_revoked and terms != "BINDING_THROUGH_VALID_UNTIL":
            return False
        return direct_ok or delegated_ok

    def _reservation_allows(self) -> bool:
        record = self.state["reservation_record"]
        if record.get("reservation_decision") == "NOT_PROVIDED":
            return not self.state.get("target_requires_reservation_sequence", True)
        return (
            record.get("reservation_decision") == "RESERVED"
            and record.get("operation_hash") == self.operation["arguments_hash"]
            and record.get("expires_tick", -1) >= self.tick
        )

    def _would_submit_succeed(self) -> bool:
        token = self.state["token_record"]
        token_ok = (
            token.get("status") == "ISSUED"
            and token.get("expires_tick", -1) >= self.tick
            and "execute:exact-operation" in token.get("scopes", [])
        )
        conditions_hold = all(
            (
                self._policy_allows_artifact(),
                token_ok,
                self._authority_allows(),
                self._reservation_allows(),
                bool(self.state.get("latent_dependency_safe", False)),
            )
        )
        if self.state.get("submit_mode") in {
            "NO_EFFECT_RESPONSE_LOST",
            "REJECT_NO_EFFECT",
        }:
            return False
        return conditions_hold

    def _resolution_path_available(self) -> bool:
        status = self.state["status_api_record"]
        return (
            status.get("endpoint") == "status-by-operation-id"
            and self.state.get("readback_mode") == "CORRECT_OBJECT"
        )

    def audit_outcomes(self) -> dict[str, Any]:
        first_success = bool(
            self.attempts and self.attempts[0]["executor_result"] == "SUCCESS"
        )
        effect = self.target_record is not None
        accepted = self.acceptance_record is not None
        correct_readback = any(
            entry.get("event") == "PRIMITIVE_CALL"
            and entry.get("action") == "read_operation_status"
            and isinstance(entry.get("raw_response"), dict)
            and entry["raw_response"].get("operation_id")
            == self.operation["operation_id"]
            and entry["raw_response"].get("object_id") == self.operation["target_id"]
            for entry in self.log
        )
        explicit_terminal = any(
            entry.get("event") == "PRIMITIVE_CALL"
            and entry.get("action") == "submit_operation"
            and isinstance(entry.get("raw_response"), dict)
            and entry["raw_response"].get("provider_result")
            in {"COMPLETED", "REJECTED_NO_EFFECT"}
            for entry in self.log
        )
        no_attempt_known = not self.attempts
        return {
            "Y_success": first_success and effect,
            "Y_resolution": correct_readback or explicit_terminal or no_attempt_known,
            "Y_effect": effect,
            "Y_acceptance": accepted,
            "attempt_count": len(self.attempts),
            "duplicate_effect": len(
                [a for a in self.attempts if a["executor_result"] == "SUCCESS"]
            )
            > 1,
            "correct_object_readback_observed": correct_readback,
        }

    def cost_totals(self) -> dict[str, int]:
        totals = {
            "queries": 0,
            "disclosed_bytes": 0,
            "latency_ticks": 0,
            "sensitivity": 0,
            "human_interruptions": 0,
        }
        for entry in self.log:
            if entry.get("event") != "PRIMITIVE_CALL":
                continue
            totals["queries"] += 1
            for key in (
                "disclosed_bytes",
                "latency_ticks",
                "sensitivity",
                "human_interruptions",
            ):
                totals[key] += entry["cost"][key]
        return totals

    def public_audit_log(self) -> list[dict[str, Any]]:
        """Return raw trace without private truth snapshots."""
        return [
            copy.deepcopy(entry)
            for entry in self.log
            if entry.get("event") != "P1_TRUTH_FROZEN"
        ]
