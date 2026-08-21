"""G5 evaluator.  It has no access to G2 truth or private state."""

from __future__ import annotations

from typing import Any

from authority_truth_broker import AuthorityTruthBroker


FIELDS = (
    "permit_status",
    "mandate_valid",
    "commitment_valid",
    "reservation_valid",
    "standing_valid",
    "authority_chain_valid",
    "error",
    "current_relation_version",
)


def evaluate_authority(
    broker: AuthorityTruthBroker,
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
    return {
        "schema": "towow.wave009-authority-public-output.v1",
        "run_id": run_id,
        "world_id": world_id,
        "permit_status": candidate.get("permit_status", "UNKNOWN"),
        "mandate_valid": candidate.get("mandate_valid") is True,
        "commitment_valid": candidate.get("commitment_valid") is True,
        "reservation_valid": candidate.get("reservation_valid") is True,
        "standing_valid": candidate.get("standing_valid") is True,
        "authority_chain_valid": (
            candidate.get("authority_chain_valid") is True
        ),
        "error": candidate.get("error"),
        "current_relation_version": candidate.get(
            "current_relation_version"
        ),
        "assertion_valid": exact,
        "operation_cost": operation_cost,
        "evidence_anchor_sha256": evidence_anchor_sha256,
        "record_anchor_valid": anchor_valid,
    }
