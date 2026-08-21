from __future__ import annotations

import copy
from typing import Any

from .canonical import sha256
from .models import FrozenState, RunRecord


class FormationExecutionService:
    """A single G3 line module, not an arm-comparison decision root."""

    def __init__(self, owner_service: Any) -> None:
        self.owner = owner_service

    def freeze(self, public_case: dict[str, Any]) -> FrozenState:
        snapshot = self.owner.freeze_snapshot(public_case)
        anchors = snapshot["anchors"]
        return FrozenState(
            case_handle=public_case["case_handle"],
            episode_handle=public_case["episode_handle"],
            task=copy.deepcopy(public_case["task"]),
            inventory_status=public_case["inventory"]["status"],
            world_state=snapshot["initial_state"],
            kernel_actions=snapshot["initial_kernel"],
            operator_registry=snapshot["operator_registry"],
            owner_routing=snapshot["owner_routing"],
            owner_state_versions=anchors["owner_state_versions"],
            owner_policy_versions=anchors["owner_policy_versions"],
            owner_policy_heads=anchors["owner_policy_heads"],
            response_family_sha256=anchors["response_family_sha256"],
            response_family_status=anchors["response_family_status"],
            budget=anchors["budget"],
            horizon=anchors["horizon"],
            clock_seed=anchors["clock_seed"],
            public_packet_sha256=sha256(public_case),
        )

    def execute(
        self,
        public_case: dict[str, Any],
        intervention: str = "NONE",
    ) -> RunRecord:
        s0 = self.freeze(public_case)
        result_task = copy.deepcopy(s0.task)
        state = copy.deepcopy(s0.world_state)
        executable_kernel = list(s0.kernel_actions)
        executable_operators = copy.deepcopy(s0.operator_registry)
        intervention_delta: dict[str, Any] = {
            "intervention": intervention,
            "removed_actions": [],
            "owner_response_override": None,
        }
        reverse_phase = {
            "REVERSE_OWNER_DECISION@read": "read",
            "REVERSE_OWNER_DECISION@sign": "sign",
            "REVERSE_OWNER_DECISION@reserve": "reserve",
            "REVERSE_OWNER_DECISION@execute": "execute",
        }.get(intervention)
        if reverse_phase is not None:
            intervention_delta["owner_response_override"] = {
                "phase": reverse_phase,
                "mode": "REVERSED_REFUSAL",
            }
        if intervention == "REMOVE_FORMATION_OPERATOR":
            removed = "REQUEST_PURPOSE_DELEGATION"
            executable_kernel = [
                action for action in executable_kernel if action != removed
            ]
            intervention_delta["removed_actions"] = [removed]
            executable_operators = [
                item
                for item in executable_operators
                if item["operator_id"] != removed
            ]
        record = RunRecord(
            run_id=f'{public_case["case_handle"]}::{intervention}',
            case_handle=public_case["case_handle"],
            intervention=intervention,
            intervention_delta=intervention_delta,
            frozen_s0=s0.body(),
            frozen_s0_sha256=s0.digest,
            result_task=result_task,
            final_state=state,
            observed_inventory_status=s0.inventory_status,
        )
        record.append(
            {
                "type": "S0_FROZEN",
                "s0_sha256": s0.digest,
                "task_sha256": sha256(s0.task),
                "kernel_sha256": sha256(s0.kernel_actions),
                "response_family_sha256": s0.response_family_sha256,
                "owner_policy_heads": s0.owner_policy_heads,
                "owner_state_versions": s0.owner_state_versions,
                "owner_policy_versions": s0.owner_policy_versions,
            }
        )
        if intervention != "NONE":
            record.append(
                {
                    "type": "INTERVENTION_DELTA_APPLIED",
                    "delta": copy.deepcopy(intervention_delta),
                    "executable_kernel_sha256": sha256(executable_kernel),
                    "executable_operator_registry_sha256": sha256(
                        executable_operators
                    ),
                }
            )
        record.append(
            {
                "type": "OPERATOR_INVENTORY_OBSERVATION",
                "action_kind": "FORM_PURPOSE_TOKEN_AND_DELEGATION",
                "executable_operator_ids": [
                    item["operator_id"]
                    for item in executable_operators
                    if item.get("executable")
                    and item.get("action_kind")
                    == "FORM_PURPOSE_TOKEN_AND_DELEGATION"
                ],
            }
        )

        if intervention == "MATERIAL_Q_CHANGE_BY_CONTROLLER":
            result_task["target"]["circuit_id"] = "C8"
            record.append(
                {
                    "type": "CONTROLLER_TASK_REWRITE",
                    "original_task_sha256": sha256(s0.task),
                    "result_task_sha256": sha256(result_task),
                    "authority_receipt": None,
                }
            )

        try:
            read = self.owner.owner_event("read")
        except ValueError as error:
            record.append(
                {"type": "OWNER_RESPONSE_REJECTED", "reason": str(error)}
            )
            record.append({"type": "BOUNDED_STOP", "reason": "INVALID_OWNER_RESPONSE"})
            record.final_state = state
            return record
        record.append({"type": "OWNER_INTERACTION", "event": read})
        if read.get("decision") in {"UNKNOWN", "DEFER", "REVERSED_REFUSAL"}:
            record.append({"type": "BOUNDED_STOP", "reason": read["decision"]})
            record.final_state = state
            return record

        resources = list(read.get("resources", []))
        rediscovered = False
        index = 0
        while index < len(resources):
            resource = resources[index]
            index += 1
            resource_id = resource["resource_id"]
            token_missing = (
                resource.get("requires_token")
                and not self._has_token(state, resource_id)
            )
            adapter_missing = (
                resource.get("requires_adapter")
                and not self._has_adapter(
                    state, resource["requires_adapter"]
                )
            )
            if token_missing or adapter_missing:
                formation_operators = [
                    item
                    for item in executable_operators
                    if item.get("executable")
                    and item.get("action_kind")
                    == "FORM_PURPOSE_TOKEN_AND_DELEGATION"
                ]
                if len(formation_operators) != 1:
                    record.append(
                        {
                            "type": "RESOURCE_SKIPPED",
                            "resource_id": resource_id,
                            "reason": (
                                "FORMATION_OPERATOR_CLOSED_REGISTRY_NOT_SINGLETON"
                            ),
                            "matching_operator_ids": [
                                item["operator_id"]
                                for item in formation_operators
                            ],
                        }
                    )
                    continue
                try:
                    sign = self._dispatch_formation_operator(
                        formation_operators[0],
                        s0,
                        resource_id,
                        record,
                    )
                except ValueError as error:
                    record.append(
                        {
                            "type": "OWNER_RESPONSE_REJECTED",
                            "phase": "sign",
                            "reason": str(error),
                        }
                    )
                    continue
                record.append({"type": "OWNER_INTERACTION", "event": sign})
                if sign.get("decision") not in {"SIGNED", "APPROVED"}:
                    continue
                if sign.get("kernel_extension"):
                    operator_id = sign["kernel_extension"]["operator_id"]
                    state.setdefault("installed_operators", []).append(operator_id)
                    record.append(
                        {
                            "type": "KERNEL_EXTENSION_INSTALLED",
                            "operator": sign["kernel_extension"],
                            "authority_owner": sign.get("owner_id"),
                        }
                    )
                if sign.get("purpose_token") and sign.get("delegation"):
                    token = sign["purpose_token"]
                    delegation = sign["delegation"]
                    state.setdefault("purpose_tokens", []).append(token)
                    state.setdefault("delegations", []).append(delegation)
                    record.append(
                        {
                            "type": "PURPOSE_TOKEN_DELEGATION_FORMED",
                            "resource_id": resource_id,
                            "purpose_token": token,
                            "delegation": delegation,
                            "owner_event_sha256": sign["owner_event_sha256"],
                        }
                    )
            elif resource.get("requires_token"):
                record.append(
                    {
                        "type": "EXTANT_PURPOSE_TOKEN_DELEGATION_USED",
                        "resource_id": resource_id,
                        "q_version": s0.task["q_version"],
                    }
                )

            if resource.get("requires_token") and not self._has_token(state, resource_id):
                record.append(
                    {
                        "type": "RESOURCE_SKIPPED",
                        "resource_id": resource_id,
                        "reason": "PURPOSE_TOKEN_OR_DELEGATION_ABSENT",
                    }
                )
                continue
            if resource.get("requires_adapter") and not self._has_adapter(
                state, resource["requires_adapter"]
            ):
                record.append(
                    {
                        "type": "RESOURCE_SKIPPED",
                        "resource_id": resource_id,
                        "reason": "KERNEL_OPERATOR_ABSENT",
                    }
                )
                continue

            try:
                reserve = self.owner.owner_event("reserve", resource_id)
            except ValueError as error:
                record.append(
                    {
                        "type": "OWNER_RESPONSE_REJECTED",
                        "phase": "reserve",
                        "reason": str(error),
                    }
                )
                continue
            record.append({"type": "OWNER_INTERACTION", "event": reserve})
            if reserve.get("decision") == "REVOKED":
                record.append(
                    {
                        "type": "RESERVATION_REVOKED",
                        "resource_id": resource_id,
                        "recovery_next_resource": False,
                    }
                )
                if not rediscovered:
                    record.append(
                        {
                            "type": "RECOVERY_REDISCOVERY_QUERY",
                            "after_revocation_resource_id": resource_id,
                        }
                    )
                    try:
                        rediscovery = self.owner.owner_event("rediscover")
                    except ValueError as error:
                        record.append(
                            {
                                "type": "OWNER_RESPONSE_REJECTED",
                                "phase": "rediscover",
                                "reason": str(error),
                            }
                        )
                        continue
                    record.append(
                        {"type": "OWNER_INTERACTION", "event": rediscovery}
                    )
                    resources.extend(rediscovery.get("resources", []))
                    rediscovered = True
                continue
            if reserve.get("decision") != "RESERVED":
                continue

            try:
                execute = self.owner.owner_event("execute", resource_id)
            except ValueError as error:
                record.append(
                    {
                        "type": "OWNER_RESPONSE_REJECTED",
                        "phase": "execute",
                        "reason": str(error),
                    }
                )
                continue
            record.append({"type": "OWNER_INTERACTION", "event": execute})
            if execute.get("decision") != "EXECUTE":
                continue
            max_attempts = int(execute.get("max_attempts", 1))
            for attempt in range(1, max_attempts + 1):
                record.append(
                    {
                        "type": "TARGET_SUBMIT",
                        "resource_id": resource_id,
                        "operation_id": execute.get("operation_id"),
                        "attempt": attempt,
                        "task_sha256": sha256(result_task),
                        "submitted_at_min": execute.get(
                            "submitted_at_min", 45
                        ),
                    }
                )
                try:
                    readback = self.owner.target_readback(
                        resource_id, execute.get("operation_id"), attempt
                    )
                except ValueError as error:
                    record.append(
                        {
                            "type": "OWNER_RESPONSE_REJECTED",
                            "phase": "target_readback",
                            "reason": str(error),
                        }
                    )
                    continue
                record.append({"type": "TARGET_READBACK", "readback": readback})
                if readback.get("effect_occurred"):
                    state["effect"] = copy.deepcopy(readback)
                    state["selected_resource"] = resource_id
                    acceptances = []
                    for owner_id in ("O_Q", "O_V"):
                        try:
                            acceptance = self.owner.observe_outcome(
                                owner_id,
                                sha256(s0.task),
                                readback["readback_sha256"],
                                execute.get("operation_id"),
                            )
                        except ValueError as error:
                            record.append(
                                {
                                    "type": "OWNER_RESPONSE_REJECTED",
                                    "phase": "outcome_observation",
                                    "owner_id": owner_id,
                                    "reason": str(error),
                                }
                            )
                            continue
                        acceptances.append(acceptance)
                        record.append(
                            {
                                "type": "OWNER_ACCEPTANCE",
                                "acceptance": acceptance,
                            }
                        )
                    state["acceptances"] = acceptances
                    state["executable_kernel"] = executable_kernel
                    state["executable_operator_registry"] = executable_operators
                    record.append(
                        {
                            "type": "EFFECT_READBACK_OBSERVED",
                            "resource_id": resource_id,
                            "readback_sha256": readback["readback_sha256"],
                        }
                    )
                    record.final_state = state
                    return record
        record.append({"type": "BOUNDED_STOP", "reason": "NO_EXECUTABLE_RESOURCE"})
        state["executable_kernel"] = executable_kernel
        state["executable_operator_registry"] = executable_operators
        record.final_state = state
        return record

    @staticmethod
    def _make_proposal(
        s0: FrozenState, resource_id: str
    ) -> dict[str, Any]:
        task = s0.task
        target = task["target"]
        proposal = {
            "task_sha256": sha256(task),
            "q_version": task["q_version"],
            "resource_id": resource_id,
            "purpose": f'temporary-power-{target["circuit_id"]}',
            "scope": {
                "venue_id": target["venue_id"],
                "circuit_id": target["circuit_id"],
                "power_kw": task["power_kw"],
                "power_tolerance_percent": task[
                    "power_tolerance_percent"
                ],
                "minimum_duration_min": task["minimum_duration_min"],
                "constraints": copy.deepcopy(task["constraints"]),
            },
            "expiry": task["deadline"],
            "recipient_owner_id": "O_V",
            "cost": {
                "units": 3,
                "budget_limit": s0.budget["max_cost_units"],
            },
            "nonce": sha256(
                {
                    "case_handle": s0.case_handle,
                    "resource_id": resource_id,
                    "clock_seed": s0.clock_seed,
                    "task_sha256": sha256(task),
                }
            )[:24],
        }
        return proposal

    def _dispatch_formation_operator(
        self,
        operator: dict[str, Any],
        s0: FrozenState,
        resource_id: str,
        record: RunRecord,
    ) -> dict[str, Any]:
        if operator.get("operator_id") != "REQUEST_PURPOSE_DELEGATION":
            raise ValueError("FORMATION_OPERATOR_DISPATCH_ID_INVALID")
        proposal = self._make_proposal(s0, resource_id)
        record.append(
            {
                "type": "FORMATION_PROPOSAL_CREATED",
                "operator_id": operator["operator_id"],
                "operator_registry_sha256": sha256(
                    s0.operator_registry
                ),
                "proposal": proposal,
                "proposal_sha256": sha256(proposal),
            }
        )
        return self.owner.owner_event("sign", resource_id, proposal)

    @staticmethod
    def _has_token(state: dict[str, Any], resource_id: str) -> bool:
        tokens = state.get("purpose_tokens", [])
        delegations = state.get("delegations", [])
        token_ok = any(item.get("resource_id") == resource_id for item in tokens)
        delegation_ok = any(
            item.get("resource_id") == resource_id for item in delegations
        )
        return token_ok and delegation_ok

    @staticmethod
    def _has_adapter(state: dict[str, Any], operator_id: str) -> bool:
        return operator_id in state.get("installed_operators", [])
