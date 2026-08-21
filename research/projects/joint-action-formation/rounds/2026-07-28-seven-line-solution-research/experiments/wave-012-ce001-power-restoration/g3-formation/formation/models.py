from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .canonical import sha256


@dataclass
class FrozenState:
    case_handle: str
    episode_handle: str
    task: dict[str, Any]
    inventory_status: str
    world_state: dict[str, Any]
    kernel_actions: list[str]
    operator_registry: list[dict[str, Any]]
    owner_routing: dict[str, str]
    owner_state_versions: dict[str, str]
    owner_policy_versions: dict[str, str]
    owner_policy_heads: dict[str, str]
    response_family_sha256: str
    response_family_status: str
    budget: dict[str, Any]
    horizon: dict[str, Any]
    clock_seed: str
    public_packet_sha256: str

    def body(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return sha256(self.body())


@dataclass
class RunRecord:
    run_id: str
    case_handle: str
    intervention: str
    intervention_delta: dict[str, Any]
    frozen_s0: dict[str, Any]
    frozen_s0_sha256: str
    result_task: dict[str, Any]
    final_state: dict[str, Any]
    trace: list[dict[str, Any]] = field(default_factory=list)
    observed_inventory_status: str = "COMPLETE"

    def append(self, event: dict[str, Any]) -> None:
        self.trace.append({"seq": len(self.trace), **event})

    def body(self) -> dict[str, Any]:
        return asdict(self)
