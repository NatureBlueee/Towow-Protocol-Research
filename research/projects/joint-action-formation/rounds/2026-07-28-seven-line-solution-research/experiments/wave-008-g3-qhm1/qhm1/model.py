"""Finite abstract transition system used by the exhaustive closure checker."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json

from .spec import ACTION_BY_NAME, OLD_TASK, RESOURCE_ACCOUNT
from .worlds import HiddenWorld


@dataclass(frozen=True)
class AbstractState:
    endpoint_enabled: bool
    owner_authorized: bool
    commitment_signed: bool
    adapter_built: bool
    adapter_installed: bool
    operator_proposed: bool
    operator_registered: bool
    transfer_count: int
    project_count: int
    accepted: bool
    readback: bool
    inspected: bool
    inspection_provenance_bound: bool
    inspection_obligation_bound: bool
    value_floor_ok: bool
    task_version: str
    ledger_intact: bool
    steps_used: int
    cost_used: int
    privacy_cost_used: int
    human_escalations_used: int

    def digest(self) -> str:
        payload = json.dumps(
            asdict(self), sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


def initial_state(world: HiddenWorld) -> AbstractState:
    return AbstractState(
        endpoint_enabled=world.route_state
        in {
            "ALTERNATE_ACTIVE_UNADVERTISED",
            "COMPATIBLE_ACTIVE",
            "SCHEMA_BLOCKED",
        },
        owner_authorized=world.authorization_policy == "PRESENT",
        commitment_signed=False,
        adapter_built=False,
        adapter_installed=False,
        operator_proposed=False,
        operator_registered=False,
        transfer_count=0,
        project_count=0,
        accepted=False,
        readback=False,
        inspected=False,
        inspection_provenance_bound=False,
        inspection_obligation_bound=False,
        value_floor_ok=world.value_floor_ok,
        task_version=OLD_TASK.task_version,
        ledger_intact=True,
        steps_used=0,
        cost_used=0,
        privacy_cost_used=0,
        human_escalations_used=0,
    )


def route_ready(world: HiddenWorld, state: AbstractState) -> bool:
    if not state.endpoint_enabled:
        return False
    schema_ready = (
        world.schema_policy == "COMPATIBLE"
        or state.adapter_installed
        or state.operator_registered
    )
    return schema_ready


def abstract_qualified(state: AbstractState) -> bool:
    return (
        state.transfer_count == 1
        and state.project_count == 1
        and state.accepted
        and state.readback
        and state.owner_authorized
        and state.value_floor_ok
        and state.task_version == OLD_TASK.task_version
        and state.ledger_intact
        and (
            not state.inspected
            or (
                state.inspection_provenance_bound
                and state.inspection_obligation_bound
            )
        )
        and state.steps_used <= RESOURCE_ACCOUNT.horizon
        and state.cost_used <= RESOURCE_ACCOUNT.max_cost
        and state.privacy_cost_used
        <= RESOURCE_ACCOUNT.max_privacy_cost
        and state.human_escalations_used
        <= RESOURCE_ACCOUNT.human_escalation_quota
    )


def transition(
    world: HiddenWorld,
    state: AbstractState,
    action: str,
) -> AbstractState | None:
    spec = ACTION_BY_NAME[action]
    if (
        state.steps_used + 1 > RESOURCE_ACCOUNT.horizon
        or state.cost_used + spec.cost > RESOURCE_ACCOUNT.max_cost
        or state.privacy_cost_used + spec.privacy_cost
        > RESOURCE_ACCOUNT.max_privacy_cost
    ):
        return None

    updates: dict[str, object] = {}
    if action == "TRANSFER":
        if not route_ready(world, state) or not state.owner_authorized:
            return None
        if state.transfer_count >= 2:
            return None
        updates["transfer_count"] = state.transfer_count + 1
    elif action == "PROJECT":
        if state.transfer_count < 1 or state.project_count >= 2:
            return None
        updates["project_count"] = state.project_count + 1
    elif action == "ACCEPT":
        if state.project_count != 1 or state.accepted:
            return None
        updates["accepted"] = True
    elif action == "READBACK":
        if state.project_count < 1 or state.readback:
            return None
        updates["readback"] = True
    elif action == "INSPECT":
        if state.inspected:
            return None
        updates["inspected"] = True
        updates["inspection_provenance_bound"] = True
        updates["inspection_obligation_bound"] = True
    elif action == "ENABLE_ENDPOINT":
        if not world.enable_allowed or state.endpoint_enabled:
            return None
        updates["endpoint_enabled"] = True
    elif action == "SIGN_COMMITMENT":
        if (
            world.authorization_policy != "CONDITIONAL_COMMITMENT"
            or state.commitment_signed
        ):
            return None
        updates["commitment_signed"] = True
    elif action == "ISSUE_AUTHORIZATION":
        if (
            world.authorization_policy != "CONDITIONAL_COMMITMENT"
            or not state.commitment_signed
            or state.owner_authorized
        ):
            return None
        updates["owner_authorized"] = True
    elif action == "BUILD_KNOWN_ADAPTER":
        if (
            world.schema_policy != "KNOWN_ADAPTER"
            or state.adapter_built
            or state.human_escalations_used
            >= RESOURCE_ACCOUNT.human_escalation_quota
        ):
            return None
        updates["adapter_built"] = True
        updates["human_escalations_used"] = (
            state.human_escalations_used + 1
        )
    elif action == "INSTALL_KNOWN_ADAPTER":
        if not state.adapter_built or state.adapter_installed:
            return None
        updates["adapter_installed"] = True
    elif action == "PROPOSE_NEW_OPERATOR":
        if (
            world.schema_policy != "NOVEL_OPERATOR"
            or not world.extension_allowed
            or state.operator_proposed
        ):
            return None
        updates["operator_proposed"] = True
    elif action == "REGISTER_NEW_OPERATOR":
        if (
            not world.extension_allowed
            or not state.operator_proposed
            or state.operator_registered
        ):
            return None
        updates["operator_registered"] = True
    else:
        raise ValueError(f"unknown action: {action}")

    updates["steps_used"] = state.steps_used + 1
    updates["cost_used"] = state.cost_used + spec.cost
    updates["privacy_cost_used"] = (
        state.privacy_cost_used + spec.privacy_cost
    )
    return replace(state, **updates)
