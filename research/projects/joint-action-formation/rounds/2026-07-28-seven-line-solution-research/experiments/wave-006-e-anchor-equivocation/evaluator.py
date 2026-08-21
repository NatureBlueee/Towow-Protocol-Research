#!/usr/bin/env python3
"""Evaluate anchor-equivocation strategies under explicit threat objectives."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from simulator import SHARED_TASK_ID, SHARED_TASK_SHA256, simulate


def evaluate() -> dict[str, Any]:
    simulation = simulate()
    strategies = simulation["strategies"]
    metrics = {}
    for name, result in strategies.items():
        detected = int(
            result["detected_during_partition"]
            or result["detected_after_rejoin"]
        )
        recovery_steps = result["partition_rejoin_recovery_steps"]
        recovery_cost = recovery_steps if recovery_steps is not None else 5
        availability_loss = result.get(
            "missed_valid_action_under_witness_partition", 0
        )
        metrics[name] = {
            "equivocation_detection": detected,
            "detection_during_partition": int(
                result["detected_during_partition"]
            ),
            "false_rejection": result["false_rejection_honest"],
            "accepted_branch_count": result["accepted_branch_count"],
            "conflicting_acceptances": result["conflicting_acceptances"],
            "message_cost": result["message_cost"],
            "evidence_cost": result["evidence_cost"],
            "partition_rejoin_recovery_steps": recovery_steps,
            "missed_valid_action": availability_loss,
            "cost_score": result["message_cost"]
            + result["evidence_cost"]
            + recovery_cost
            + availability_loss * 3,
        }

    objectives = {
        "LOCAL_INTEGRITY_ONLY_NO_EQUIVOCATION_THREAT": {
            "required": [
                "signature verification",
                "local hash-chain continuity",
            ],
            "recommended": "SINGLE_PINNED_VIEW",
            "reason": "No cross-view fact is required; the cheapest existing verifier is sufficient.",
        },
        "DETECT_IF_CLIENTS_EVENTUALLY_REJOIN": {
            "required": ["post-partition conflicting-head detection"],
            "recommended": "CLIENT_GOSSIP",
            "reason": "Gossip adds exactly the missing cross-view bit at lower cost than an always-on witness quorum.",
        },
        "PREVENT_TWO_ACCEPTED_HEADS_DURING_CLIENT_PARTITION": {
            "required": [
                "detection before second conflicting acceptance",
                "quorum intersection",
            ],
            "recommended": "INDEPENDENT_WITNESS_QUORUM",
            "reason": "A 2-of-3 quorum intersects; an honest witness refuses the second head, but witness partition can delay valid work.",
        },
    }
    return {
        "schema": "towow.anchor-equivocation-evaluation.v1",
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "simulation": simulation,
        "metrics": metrics,
        "objectives": objectives,
        "formal_boundary": {
            "single_view_impossibility": True,
            "indistinguishability_statement": (
                "For each client transcript Ti containing one valid signed "
                "branch, there exists an honest single-branch execution with "
                "the same Ti. Therefore a detector using only Ti cannot "
                "soundly distinguish equivocation."
            ),
            "quorum_intersection": {
                "witnesses_n": 3,
                "quorum_q": 2,
                "condition": "2q > n",
                "holds": True,
            },
        },
        "solution_result": {
            "new_protocol_required": False,
            "existing_components": [
                "pinned signed checkpoints",
                "client checkpoint gossip",
                "standard intersecting witness quorum",
            ],
            "selection_depends_on_threat_objective": True,
        },
        "evidence_boundary": "LOCAL_SYNTHETIC_ONLY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate()
    encoded = json.dumps(
        result, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
