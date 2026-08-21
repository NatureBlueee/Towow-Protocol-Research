"""Third evaluator: public G2/G5 outputs only, never either truth owner."""

from __future__ import annotations

from typing import Any


def integrate(
    relation_output: dict[str, Any],
    authority_output: dict[str, Any],
) -> dict[str, Any]:
    evidence_anchor_sha256 = relation_output.get(
        "evidence_anchor_sha256"
    )
    anchor_match = (
        isinstance(evidence_anchor_sha256, str)
        and evidence_anchor_sha256
        == authority_output.get("evidence_anchor_sha256")
        and relation_output.get("record_anchor_valid") is True
        and authority_output.get("record_anchor_valid") is True
    )
    coordinates_match = all(
        [
            relation_output.get("run_id") == authority_output.get("run_id"),
            relation_output.get("world_id")
            == authority_output.get("world_id"),
            relation_output.get("version_id")
            == authority_output.get("current_relation_version"),
        ]
    )
    ready = all(
        [
            coordinates_match,
            anchor_match,
            relation_output.get("assertion_valid") is True,
            authority_output.get("assertion_valid") is True,
            relation_output.get("formed") is True,
            relation_output.get("stale") is False,
            authority_output.get("permit_status") == "PERMIT",
            authority_output.get("mandate_valid") is True,
            authority_output.get("commitment_valid") is True,
            authority_output.get("reservation_valid") is True,
            authority_output.get("standing_valid") is True,
        ]
    )
    return {
        "schema": "towow.wave009-integration-public-output.v1",
        "run_id": relation_output.get("run_id"),
        "world_id": relation_output.get("world_id"),
        "coordinates_match": coordinates_match,
        "record_anchor_match": anchor_match,
        "evidence_anchor_sha256": evidence_anchor_sha256,
        "execution_ready": ready,
        "status": "EXECUTION_READY" if ready else "NOT_READY",
        "relation_assertion_consumed": (
            relation_output.get("assertion_valid") is True
        ),
        "authority_assertion_consumed": (
            authority_output.get("assertion_valid") is True
        ),
    }
