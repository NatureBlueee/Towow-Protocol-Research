"""G2 evaluator.  It has no access to G5 truth or private state."""

from __future__ import annotations

from typing import Any

from relation_truth_broker import RelationTruthBroker


FIELDS = (
    "stage",
    "formed",
    "horizon",
    "version_id",
    "material_change",
    "semantic_loss",
    "stale",
    "source_provenance",
    "opposition_preserved",
)


def evaluate_relation(
    broker: RelationTruthBroker,
    candidate: dict[str, Any],
    *,
    run_id: str,
    world_id: str,
    operation_cost: int,
    evidence_anchor_sha256: str,
) -> dict[str, Any]:
    expected = broker.expected_outcome()
    anchor_valid = (
        len(evidence_anchor_sha256) == 64
        and all(
            character in "0123456789abcdef"
            for character in evidence_anchor_sha256
        )
    )
    exact = anchor_valid and all(
        candidate.get(name) == expected[name] for name in FIELDS
    )
    formed = candidate.get("formed") is True
    stage = candidate.get("stage", "UNKNOWN")
    return {
        "schema": "towow.wave009-relation-public-output.v1",
        "run_id": run_id,
        "world_id": world_id,
        "stage": stage,
        "formed": formed,
        "horizon": candidate.get("horizon"),
        "version_id": candidate.get("version_id"),
        "material_change": candidate.get("material_change") is True,
        "semantic_loss": candidate.get("semantic_loss") is True,
        "stale": candidate.get("stale") is True,
        "source_provenance": candidate.get("source_provenance"),
        "opposition_preserved": (
            candidate.get("opposition_preserved") is True
        ),
        "overconstitution": int(formed and not expected["formed"]),
        "missed_constitution": int(not formed and expected["formed"]),
        "assertion_valid": exact,
        "operation_cost": operation_cost,
        "evidence_anchor_sha256": evidence_anchor_sha256,
        "record_anchor_valid": anchor_valid,
    }
