"""Data model and fixture loaders."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VISIBLE_FIXTURE = ROOT / "fixtures" / "method_visible_worlds.json"
PRIVATE_ORACLE = ROOT / "oracle" / "private_oracle.json"


@dataclass(frozen=True)
class Candidate:
    world_id: str
    proposal_id: str
    status: str = "CANDIDATE_NOT_COMMITMENT"
    target: str = "restore_service_without_lowering_security"
    q_version: str = "Q-G1-v1"
    principals: tuple[str, ...] = ("product-owner", "dependency-owner")
    evidence_ids: tuple[str, ...] = ()
    source_arm: str = ""
    response_state: str | None = None
    declared_labels: tuple[str, ...] = ()
    operator_ids: tuple[str, ...] = ()
    cost: dict[str, float] = field(default_factory=dict)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_worlds(path: Path = VISIBLE_FIXTURE) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    if payload["intent_boundary"] != "IntentAtCoordinationInterface":
        raise ValueError("fixture silently crossed the V2 Intent boundary")
    defaults = payload["world_defaults"]
    return {
        world["world_id"]: {**defaults, **world}
        for world in payload["worlds"]
    }


def load_oracle(path: Path = PRIVATE_ORACLE) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    defaults = payload["oracle_defaults"]
    return {
        world["world_id"]: {**defaults, **world}
        for world in payload["worlds"]
    }


def candidate_from_dict(data: dict[str, Any], *, source_arm: str) -> Candidate:
    return Candidate(
        world_id=data["world_id"],
        proposal_id=data["proposal_id"],
        status=data.get("status", "CANDIDATE_NOT_COMMITMENT"),
        target=data.get("target", "restore_service_without_lowering_security"),
        q_version=data.get("q_version", "Q-G1-v1"),
        principals=tuple(data.get("principals", ())),
        evidence_ids=tuple(data.get("evidence_ids", ())),
        source_arm=source_arm,
        response_state=data.get("response_state"),
        declared_labels=tuple(data.get("declared_labels", ())),
        operator_ids=tuple(data.get("operator_ids", ())),
        cost=dict(data.get("cost", {})),
    )
