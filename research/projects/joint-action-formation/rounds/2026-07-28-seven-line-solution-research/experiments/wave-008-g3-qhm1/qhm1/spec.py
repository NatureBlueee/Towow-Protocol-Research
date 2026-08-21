"""Frozen executable task, action layers, authority map, and resource account."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    if hasattr(value, "__dataclass_fields__"):
        value = asdict(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: asdict(item) if is_dataclass(item) else str(item),
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    task_version: str
    artifact_hash: str
    source_schema: str
    target_schema: str
    exact_once: bool
    required_principals: tuple[str, ...]
    value_floor: str
    target_witness: str
    acceptance_required: bool


@dataclass(frozen=True)
class ResourceAccount:
    horizon: int
    max_cost: int
    max_privacy_cost: int
    human_escalation_quota: int


@dataclass(frozen=True)
class ActionSpec:
    name: str
    layer: int
    cost: int
    holder: str | None
    changes_model: bool = False
    privacy_cost: int = 0

    @property
    def privileged(self) -> bool:
        return self.holder is not None


OLD_TASK = TaskSpec(
    task_id="QHM1-OLD-TASK-v1",
    task_version="old-v1",
    artifact_hash="sha256:artifact-qhm1-a17",
    source_schema="alpha",
    target_schema="beta",
    exact_once=True,
    required_principals=("O", "P", "T"),
    value_floor="no-loss-below-vmin",
    target_witness="W:target-store-readback",
    acceptance_required=True,
)

RESOURCE_ACCOUNT = ResourceAccount(
    horizon=10,
    max_cost=10,
    max_privacy_cost=2,
    human_escalation_quota=1,
)

# The tuple order is part of the frozen action-model fingerprint and the common
# capability vector supplied to all systems.
ACTION_SPECS = (
    ActionSpec("TRANSFER", 0, 1, "P"),
    ActionSpec("PROJECT", 0, 1, "T"),
    ActionSpec("ACCEPT", 0, 1, "T"),
    ActionSpec("READBACK", 0, 1, "W"),
    ActionSpec("INSPECT", 1, 1, None, privacy_cost=1),
    ActionSpec("ENABLE_ENDPOINT", 1, 1, "T"),
    ActionSpec("SIGN_COMMITMENT", 1, 1, "T"),
    ActionSpec("ISSUE_AUTHORIZATION", 1, 1, "O"),
    ActionSpec("BUILD_KNOWN_ADAPTER", 1, 1, "H"),
    ActionSpec("INSTALL_KNOWN_ADAPTER", 1, 1, "T"),
    ActionSpec("PROPOSE_NEW_OPERATOR", 2, 1, None, changes_model=True),
    ActionSpec("REGISTER_NEW_OPERATOR", 2, 1, "A", changes_model=True),
)

ACTION_BY_NAME = {spec.name: spec for spec in ACTION_SPECS}
AUTHORITY_MAP = tuple(
    (spec.name, spec.holder)
    for spec in ACTION_SPECS
    if spec.holder is not None
) + (("INITIAL_AUTHORIZATION", "O"),)


def expected_holder(action: str) -> str | None:
    if action == "INITIAL_AUTHORIZATION":
        return "O"
    spec = ACTION_BY_NAME.get(action)
    return spec.holder if spec else None


def authorization_payload() -> dict[str, str]:
    return {
        "task_id": OLD_TASK.task_id,
        "task_version": OLD_TASK.task_version,
        "artifact_hash": OLD_TASK.artifact_hash,
        "target": "T",
        "operation": "TRANSFER_AND_PROJECT",
        "nonce": "qhm1-frozen-nonce-01",
        "expiry": "horizon:10",
    }


def expected_action_payload(action: str) -> dict[str, str]:
    if action in {"INITIAL_AUTHORIZATION", "ISSUE_AUTHORIZATION"}:
        return authorization_payload()
    if action not in ACTION_BY_NAME:
        raise ValueError(f"unknown action: {action}")
    return {
        "task_id": OLD_TASK.task_id,
        "task_version": OLD_TASK.task_version,
        "artifact_hash": OLD_TASK.artifact_hash,
        "target": "T",
        "action": action,
    }


@dataclass(frozen=True)
class FrozenPackage:
    task: TaskSpec
    action_specs: tuple[ActionSpec, ...]
    authority_map: tuple[tuple[str, str | None], ...]
    principal_policies: tuple[tuple[str, str], ...]
    resource_account: ResourceAccount
    fingerprints: dict[str, str]
    package_fingerprint: str

    @property
    def action_model_fingerprint(self) -> str:
        return self.fingerprints["action_model"]

    def recompute_fingerprint(self) -> str:
        objects = {
            "task": fingerprint(self.task),
            "action_model": fingerprint(self.action_specs),
            "authority_map": fingerprint(self.authority_map),
            "principal_policies": fingerprint(self.principal_policies),
            "resource_account": fingerprint(self.resource_account),
        }
        return fingerprint(objects)


def frozen_package(world: Any) -> FrozenPackage:
    policies = tuple(sorted(world.policy_snapshot().items()))
    objects = {
        "task": fingerprint(OLD_TASK),
        "action_model": fingerprint(ACTION_SPECS),
        "authority_map": fingerprint(AUTHORITY_MAP),
        "principal_policies": fingerprint(policies),
        "resource_account": fingerprint(RESOURCE_ACCOUNT),
    }
    return FrozenPackage(
        task=OLD_TASK,
        action_specs=ACTION_SPECS,
        authority_map=AUTHORITY_MAP,
        principal_policies=policies,
        resource_account=RESOURCE_ACCOUNT,
        fingerprints=objects,
        package_fingerprint=fingerprint(objects),
    )
