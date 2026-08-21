#!/usr/bin/env python3
"""Local two-client anchor-equivocation simulation for Wave 006-E."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


KERNEL = (
    Path(__file__).resolve().parents[1]
    / "wave-005-b-cross-authority-receipts"
)
sys.path.insert(0, str(KERNEL))

from protocol import (  # noqa: E402
    ProtocolError,
    envelope_hash,
    private_key_from_hex,
    sha256_value,
    sign_envelope,
    verify_envelope,
)


SHARED_TASK_ID = "W6-STERILE-ROUTE-SIMULATION-001"
SHARED_TASK_SHA256 = (
    "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
)
WORLD_ID = "W6-STERILE-ROUTE-WORLD"
OPERATION = "RUN-STERILE-ROUTE-SIM-v1"
STEP = 7
ANCHOR_ID = "ANCHOR-W6"
WITNESSES = ["WITNESS-1", "WITNESS-2", "WITNESS-3"]


def _seed(authority: str) -> str:
    return hashlib.sha256(
        f"towow-wave006-anchor:{authority}:v1".encode("utf-8")
    ).hexdigest()


def private_key(authority: str):
    return private_key_from_hex(_seed(authority))


def public_key_hex(authority: str) -> str:
    return (
        private_key(authority)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )


def build_contract() -> dict[str, Any]:
    authorities = [ANCHOR_ID, *WITNESSES]
    return {
        "schema": "towow.anchor-equivocation-contract.v1",
        "contract_id": "W6-ANCHOR-EQUIVOCATION-001",
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "world_id": WORLD_ID,
        "evaluation_step": STEP,
        "operation": OPERATION,
        "anchor_id": ANCHOR_ID,
        "genesis_head": None,
        "witness_ids": WITNESSES,
        "witness_quorum": 2,
        "verification_keys": [
            {
                "issuer": authority,
                "key_id": "v1",
                "public_key_hex": public_key_hex(authority),
                "valid_from_step": 1,
                "valid_through_step": 20,
            }
            for authority in authorities
        ],
    }


def action_digest() -> str:
    return sha256_value(
        {
            "shared_task_id": SHARED_TASK_ID,
            "world_id": WORLD_ID,
            "evaluation_step": STEP,
            "operation": OPERATION,
            "purpose": "sterile-route-simulation",
            "retention": "PT7M",
        }
    )


def sign_anchor_head(
    contract: dict[str, Any],
    *,
    event: dict[str, Any],
    sequence: int = 1,
    previous_head: str | None = None,
) -> dict[str, Any]:
    head = sha256_value(
        {
            "sequence": sequence,
            "previous_head": previous_head,
            "event": event,
        }
    )
    body = {
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "world_id": WORLD_ID,
        "evaluation_step": STEP,
        "operation": OPERATION,
        "action_digest": action_digest(),
        "sequence": sequence,
        "previous_head": previous_head,
        "event": copy.deepcopy(event),
        "head": head,
    }
    return sign_envelope(
        private_key(ANCHOR_ID),
        kind="ANCHOR_CHECKPOINT",
        issuer=ANCHOR_ID,
        key_id="v1",
        body=body,
    )


def verify_anchor_head(
    receipt: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    body = verify_envelope(
        receipt,
        contract,
        expected_kind="ANCHOR_CHECKPOINT",
        expected_issuer=ANCHOR_ID,
        step=STEP,
    )
    fixed = {
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "world_id": WORLD_ID,
        "evaluation_step": STEP,
        "operation": OPERATION,
        "action_digest": action_digest(),
    }
    for field, expected in fixed.items():
        if body.get(field) != expected:
            raise ProtocolError(
                "ANCHOR_COORDINATE_MISMATCH",
                f"Anchor changed {field}.",
            )
    expected_head = sha256_value(
        {
            "sequence": body["sequence"],
            "previous_head": body["previous_head"],
            "event": body["event"],
        }
    )
    if body["head"] != expected_head:
        raise ProtocolError(
            "ANCHOR_HEAD_INVALID", "Checkpoint head does not match event."
        )
    return body


def honest_receipt(contract: dict[str, Any]) -> dict[str, Any]:
    return sign_anchor_head(
        contract,
        event={
            "decision": "SIMULATION_ACCEPTED",
            "effect_sha256": sha256_value(
                {
                    "route_status": "STERILE_ROUTE_FEASIBLE",
                    "capacity_units": 2,
                }
            ),
        },
    )


def conflicting_receipts(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    branch_a = honest_receipt(contract)
    branch_b = sign_anchor_head(
        contract,
        event={
            "decision": "SIMULATION_REJECTED",
            "effect_sha256": sha256_value(
                {
                    "route_status": "STERILE_ROUTE_INFEASIBLE",
                    "capacity_units": 0,
                }
            ),
        },
    )
    return branch_a, branch_b


def checkpoints_conflict(
    left: dict[str, Any],
    right: dict[str, Any],
    contract: dict[str, Any],
) -> bool:
    left_body = verify_anchor_head(left, contract)
    right_body = verify_anchor_head(right, contract)
    return (
        left_body["sequence"] == right_body["sequence"]
        and left_body["previous_head"] == right_body["previous_head"]
        and left_body["head"] != right_body["head"]
    )


class Witness:
    """Independent monotonic signer for one task/sequence/previous-head slot."""

    def __init__(self, witness_id: str, contract: dict[str, Any]):
        self.witness_id = witness_id
        self.contract = contract
        self.signed_slots: dict[str, dict[str, Any]] = {}

    def observe(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        body = verify_anchor_head(checkpoint, self.contract)
        slot = sha256_value(
            {
                "shared_task_id": body["shared_task_id"],
                "sequence": body["sequence"],
                "previous_head": body["previous_head"],
            }
        )
        existing = self.signed_slots.get(slot)
        if existing is not None:
            if existing["checkpoint_sha256"] == envelope_hash(checkpoint):
                return copy.deepcopy(existing["attestation"])
            proof_body = {
                "shared_task_id": SHARED_TASK_ID,
                "slot_sha256": slot,
                "first_checkpoint_sha256": existing[
                    "checkpoint_sha256"
                ],
                "conflicting_checkpoint_sha256": envelope_hash(checkpoint),
                "status": "EQUIVOCATION_DETECTED",
            }
            return sign_envelope(
                private_key(self.witness_id),
                kind="WITNESS_EQUIVOCATION_PROOF",
                issuer=self.witness_id,
                key_id="v1",
                body=proof_body,
            )
        attestation = sign_envelope(
            private_key(self.witness_id),
            kind="WITNESS_CHECKPOINT_ATTESTATION",
            issuer=self.witness_id,
            key_id="v1",
            body={
                "shared_task_id": SHARED_TASK_ID,
                "slot_sha256": slot,
                "checkpoint_sha256": envelope_hash(checkpoint),
                "status": "OBSERVED_ONCE",
            },
        )
        self.signed_slots[slot] = {
            "checkpoint_sha256": envelope_hash(checkpoint),
            "attestation": attestation,
        }
        return copy.deepcopy(attestation)


def verify_witness_response(
    response: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    if response["kind"] == "WITNESS_CHECKPOINT_ATTESTATION":
        expected_kind = "WITNESS_CHECKPOINT_ATTESTATION"
    elif response["kind"] == "WITNESS_EQUIVOCATION_PROOF":
        expected_kind = "WITNESS_EQUIVOCATION_PROOF"
    else:
        raise ProtocolError(
            "WITNESS_RESPONSE_KIND_INVALID", "Unknown witness response."
        )
    return verify_envelope(
        response,
        contract,
        expected_kind=expected_kind,
        expected_issuer=response["issuer"],
        step=STEP,
    )


def obtain_quorum(
    checkpoint: dict[str, Any],
    witnesses: list[Witness],
    contract: dict[str, Any],
) -> dict[str, Any]:
    attestations = []
    conflict_proofs = []
    for witness in witnesses:
        response = witness.observe(checkpoint)
        body = verify_witness_response(response, contract)
        if response["kind"] == "WITNESS_CHECKPOINT_ATTESTATION":
            if body["checkpoint_sha256"] == envelope_hash(checkpoint):
                attestations.append(response)
        else:
            conflict_proofs.append(response)
    return {
        "checkpoint": checkpoint,
        "attestations": attestations,
        "conflict_proofs": conflict_proofs,
        "quorum_met": len(attestations) >= contract["witness_quorum"],
        "request_messages": len(witnesses),
        "response_messages": len(witnesses),
    }


def simulate() -> dict[str, Any]:
    contract = build_contract()
    honest = honest_receipt(contract)
    branch_a, branch_b = conflicting_receipts(contract)

    single = {
        "strategy": "SINGLE_PINNED_VIEW",
        "local_validation_a": bool(verify_anchor_head(branch_a, contract)),
        "local_validation_b": bool(verify_anchor_head(branch_b, contract)),
        "detected_during_partition": False,
        "detected_after_rejoin": False,
        "accepted_branch_count": 2,
        "conflicting_acceptances": 1,
        "false_rejection_honest": 0,
        "message_cost": 0,
        "evidence_cost": 2,
        "partition_rejoin_recovery_steps": None,
        "recovery_status": "UNAVAILABLE_WITHOUT_NEW_CROSS_VIEW_INPUT",
    }

    gossip_detected = checkpoints_conflict(branch_a, branch_b, contract)
    gossip = {
        "strategy": "CLIENT_GOSSIP",
        "local_validation_a": True,
        "local_validation_b": True,
        "detected_during_partition": False,
        "detected_after_rejoin": gossip_detected,
        "accepted_branch_count": 2,
        "conflicting_acceptances": 1,
        "false_rejection_honest": int(
            checkpoints_conflict(honest, honest, contract)
        ),
        "message_cost": 2,
        "evidence_cost": 2,
        "partition_rejoin_recovery_steps": 2,
        "recovery_status": "CONTESTED_CHECKPOINTS_QUARANTINED_REOPEN_REQUIRED",
    }

    witness_set = [Witness(item, contract) for item in WITNESSES]
    quorum_a = obtain_quorum(
        branch_a, witness_set[:2], contract
    )
    quorum_b = obtain_quorum(
        branch_b, witness_set[1:], contract
    )
    witness_partition_set = [Witness(WITNESSES[0], contract)]
    honest_partition = obtain_quorum(
        honest, witness_partition_set, contract
    )
    quorum = {
        "strategy": "INDEPENDENT_WITNESS_QUORUM",
        "branch_a_quorum": quorum_a["quorum_met"],
        "branch_b_quorum": quorum_b["quorum_met"],
        "detected_during_partition": bool(
            quorum_b["conflict_proofs"]
        ),
        "detected_after_rejoin": True,
        "accepted_branch_count": int(quorum_a["quorum_met"])
        + int(quorum_b["quorum_met"]),
        "conflicting_acceptances": int(
            quorum_a["quorum_met"] and quorum_b["quorum_met"]
        ),
        "false_rejection_honest": 0,
        "missed_valid_action_under_witness_partition": int(
            not honest_partition["quorum_met"]
        ),
        "partition_terminal_state": "UNKNOWN_DEFERRED"
        if not honest_partition["quorum_met"]
        else "ACCEPTED",
        "message_cost": quorum_a["request_messages"]
        + quorum_a["response_messages"]
        + quorum_b["request_messages"]
        + quorum_b["response_messages"],
        "evidence_cost": len(quorum_a["attestations"])
        + len(quorum_b["attestations"])
        + len(quorum_b["conflict_proofs"]),
        "partition_rejoin_recovery_steps": 1,
        "recovery_status": "FETCH_QUORUM_BRANCH_AND_RESUME",
        "equivocation_proof_count": len(quorum_b["conflict_proofs"]),
    }

    return {
        "schema": "towow.anchor-equivocation-simulation.v1",
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "contract_sha256": sha256_value(contract),
        "honest_checkpoint_sha256": envelope_hash(honest),
        "equivocation": {
            "branch_a_sha256": envelope_hash(branch_a),
            "branch_b_sha256": envelope_hash(branch_b),
            "both_locally_valid": True,
            "conflict": checkpoints_conflict(
                branch_a, branch_b, contract
            ),
        },
        "strategies": {
            "SINGLE_PINNED_VIEW": single,
            "CLIENT_GOSSIP": gossip,
            "INDEPENDENT_WITNESS_QUORUM": quorum,
        },
        "impossibility_counterexample": {
            "observation_a": envelope_hash(branch_a),
            "observation_b": envelope_hash(branch_b),
            "each_observation_is_compatible_with_an_honest_single_branch_anchor": True,
            "single_client_transcript_contains_cross_view_bit": False,
            "conclusion": "No verifier limited to one signed branch can distinguish honest-single-branch from same-key equivocation.",
        },
    }
