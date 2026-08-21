from __future__ import annotations

import copy
from typing import Any

from .canonical import sha256


class OwnerService:
    """The only component allowed to hold scripted owner decisions.

    The formation service receives this interface, not the underlying truth
    document. Responses are exact owner events and never scorer labels.
    """

    def __init__(self, case_truth: dict[str, Any], intervention: str) -> None:
        self.__truth = copy.deepcopy(case_truth)
        self.intervention = intervention
        self._phase_calls: dict[str, int] = {}

    def initial_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.__truth["initial_state"])

    def initial_kernel(self) -> list[str]:
        return list(self.__truth["initial_kernel"])

    def frozen_anchors(self) -> dict[str, Any]:
        owner_ids = {"O_Q", "O_V", "O_R", "O_S", "O_E"}
        for phase in self.__truth["owner_events"].values():
            values = phase.values() if isinstance(phase, dict) else []
            for value in values:
                if isinstance(value, dict) and value.get("owner_id"):
                    owner_ids.add(value["owner_id"])
        default_head = f'HEAD-{sha256(self.__truth["owner_events"])[:16]}'
        heads = {
            owner_id: self.__truth.get("owner_policy_heads", {}).get(
                owner_id, default_head
            )
            for owner_id in sorted(owner_ids)
        }
        state_versions = {
            owner_id: self.__truth.get("owner_state_versions", {}).get(
                owner_id, f"STATE-{owner_id}-v1"
            )
            for owner_id in sorted(owner_ids)
        }
        policy_versions = {
            owner_id: self.__truth.get("owner_policy_versions", {}).get(
                owner_id, f"POLICY-{owner_id}-v1"
            )
            for owner_id in sorted(owner_ids)
        }
        return {
            "owner_state_versions": state_versions,
            "owner_policy_versions": policy_versions,
            "owner_policy_heads": heads,
            "response_family_sha256": sha256(
                {
                    "owner_events": self.__truth["owner_events"],
                    "target_readback": self.__truth["target_readback"],
                    "acceptance": self.__truth.get("acceptance", {}),
                }
            ),
            "response_family_status": (
                "SCRIPTED_OBSERVED_FAMILY_NOT_COMPLETE"
            ),
            "budget": copy.deepcopy(
                self.__truth.get(
                    "budget",
                    {"max_cost_units": 20, "max_owner_queries": 12},
                )
            ),
            "horizon": copy.deepcopy(
                self.__truth.get(
                    "horizon",
                    {"deadline_min": 90, "max_steps": 40},
                )
            ),
            "clock_seed": self.__truth.get("clock_seed", "CE001-CLOCK-SEED-1"),
        }

    def operator_registry(self) -> list[dict[str, Any]]:
        return [
            {
                "operator_id": action,
                "action_kind": (
                    "FORM_PURPOSE_TOKEN_AND_DELEGATION"
                    if action == "REQUEST_PURPOSE_DELEGATION"
                    else action
                ),
                "executable": True,
            }
            for action in self.__truth["initial_kernel"]
        ]

    def owner_event(
        self,
        phase: str,
        resource_id: str | None = None,
        proposal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._phase_calls[phase] = self._phase_calls.get(phase, 0) + 1
        phase_truth = copy.deepcopy(self.__truth["owner_events"].get(phase, {}))
        if resource_id is not None:
            event = phase_truth.get(resource_id, {"decision": "UNKNOWN"})
        else:
            event = phase_truth

        event = copy.deepcopy(event)
        event["phase"] = phase
        event["resource_id"] = resource_id
        if phase == "sign" and proposal is not None:
            proposal_sha256 = sha256(proposal)
            signer = event.get("owner_id", "UNKNOWN_OWNER")
            head = self.frozen_anchors()["owner_policy_heads"].get(
                signer, "UNKNOWN_HEAD"
            )
            receipt_body = {
                "receipt_id": f"RCPT-{proposal_sha256[:16]}",
                "decision": event.get("decision"),
                "signer_owner_id": signer,
                "proposal_sha256": proposal_sha256,
                "owner_policy_head": head,
            }
            receipt_body["receipt_sha256"] = sha256(receipt_body)
            event["proposal"] = copy.deepcopy(proposal)
            event["proposal_sha256"] = proposal_sha256
            event["owner_receipt"] = receipt_body
            if event.get("purpose_token"):
                event["purpose_token"].update(
                    {
                        "proposal_sha256": proposal_sha256,
                        "resource_id": proposal["resource_id"],
                        "q_version": proposal["q_version"],
                        "purpose": proposal["purpose"],
                    }
                )
            if event.get("delegation"):
                event["delegation"].update(
                    {
                        "proposal_sha256": proposal_sha256,
                        "resource_id": proposal["resource_id"],
                        "q_version": proposal["q_version"],
                        "scope": copy.deepcopy(proposal["scope"]),
                        "expiry": proposal["expiry"],
                    }
                )
        event["owner_event_sha256"] = sha256(event)

        reverse_phase = {
            "REVERSE_OWNER_DECISION@read": "read",
            "REVERSE_OWNER_DECISION@sign": "sign",
            "REVERSE_OWNER_DECISION@reserve": "reserve",
            "REVERSE_OWNER_DECISION@execute": "execute",
        }.get(self.intervention)
        if reverse_phase == phase:
            event = {
                "phase": phase,
                "resource_id": resource_id,
                "decision": "REVERSED_REFUSAL",
                "owner_id": event.get("owner_id", "UNKNOWN_OWNER"),
                "reverses": event["owner_event_sha256"],
            }
            event["owner_event_sha256"] = sha256(event)

        return event

    def target_readback(
        self, resource_id: str, operation_id: str, attempt: int
    ) -> dict[str, Any]:
        readback = copy.deepcopy(
            self.__truth["target_readback"].get(
                f"{resource_id}:{attempt}",
                self.__truth["target_readback"].get(resource_id, {}),
            )
        )
        readback["resource_id"] = resource_id
        readback.setdefault("operation_id", operation_id)
        readback["attempt"] = attempt
        readback.setdefault("timestamp_min", 60)
        readback.setdefault(
            "constraints",
            {
                "noise_compliant": True,
                "safety_compliant": True,
                "exact_target": True,
                "other_circuits_energized": [],
            },
        )
        readback["readback_sha256"] = sha256(readback)
        return readback

    def accept_effect(
        self,
        owner_id: str,
        task_sha256: str,
        effect_readback_sha256: str,
        operation_id: str,
    ) -> dict[str, Any]:
        scripted = copy.deepcopy(
            self.__truth.get("acceptance", {}).get(
                owner_id, {"decision": "ACCEPT"}
            )
        )
        body = {
            "owner_id": owner_id,
            "decision": scripted.get("decision", "REFUSE"),
            "q_version": scripted.get("q_version", "CE-001-Q@v1"),
            "task_sha256": task_sha256,
            "effect_readback_sha256": effect_readback_sha256,
            "operation_id": operation_id,
            "owner_policy_head": self.frozen_anchors()[
                "owner_policy_heads"
            ][owner_id],
        }
        body["acceptance_sha256"] = sha256(body)
        return body
