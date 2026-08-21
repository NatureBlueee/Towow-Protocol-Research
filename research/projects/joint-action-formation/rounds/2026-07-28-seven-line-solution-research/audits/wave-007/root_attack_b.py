#!/usr/bin/env python3
"""Independent root mutations against Wave 007-B."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROUND = Path(__file__).resolve().parents[2]
EXPERIMENT = ROUND / "experiments" / "wave-007-b-paired-relation-materiality"
sys.path.insert(0, str(EXPERIMENT))

from authority import (  # noqa: E402
    HiddenAuthorityService,
    PrivateWorldState,
    _private_key,
    build_contract,
)
from evaluator import evaluate_run  # noqa: E402
from simulator import load_json, run_one  # noqa: E402


def main() -> int:
    service = HiddenAuthorityService(
        PrivateWorldState(
            reuse_truth="EXPLICIT_BOUNDED_REUSE_AUTHORIZED",
            relation_evidence="VALID_BOUNDED_REUSE",
            withdraw_after_first_reuse=True,
        ),
        opaque_seed="root-closure-attack",
    )
    gateway, audit = service.create_gateway()
    closure_objects = [
        cell.cell_contents
        for cell in (gateway.read_evidence.__closure__ or ())
    ]
    leaked_service = next(
        item
        for item in closure_objects
        if isinstance(item, HiddenAuthorityService)
    )
    leaked_truth = leaked_service._HiddenAuthorityService__private_state
    leaked_log = leaked_service._HiddenAuthorityService__operation_log
    gateway.read_evidence("delivery")
    operations_before_clear = len(audit.operation_log)
    leaked_log.clear()

    contract = build_contract()
    derived_public = (
        _private_key("LAB-SEEK").public_key().public_bytes_raw().hex()
        if hasattr(
            _private_key("LAB-SEEK").public_key(),
            "public_bytes_raw",
        )
        else None
    )
    expected_public = next(
        row["public_key_hex"]
        for row in contract["verification_keys"]
        if row["issuer"] == "LAB-SEEK"
    )
    if derived_public is None:
        from cryptography.hazmat.primitives.serialization import (
            Encoding,
            PublicFormat,
        )

        derived_public = (
            _private_key("LAB-SEEK")
            .public_key()
            .public_bytes(Encoding.Raw, PublicFormat.Raw)
            .hex()
        )

    worlds = load_json("paired-worlds.json")["worlds"]
    representations = load_json("representations.json")["representations"]
    bounded = next(
        row
        for row in worlds
        if row["evaluator_world_id"] == "PW-BOUNDED-VALID"
    )
    relation = next(
        row
        for row in representations
        if row["representation_id"] == "BOUNDED_RELATION"
    )
    relabelled = run_one(
        bounded,
        relation,
        candidate_label="TASK_BOUND",
        opaque_seed="root-identity-attack",
    )
    relabelled_evaluation = evaluate_run(relabelled)

    print(json.dumps(
        {
            "gateway_closure_truth_leak": {
                "reuse_truth": leaked_truth.reuse_truth,
                "relation_evidence": leaked_truth.relation_evidence,
                "withdraw_after_first_reuse": (
                    leaked_truth.withdraw_after_first_reuse
                ),
            },
            "gateway_closure_log_mutation": {
                "operations_before_clear": operations_before_clear,
                "operations_after_clear": len(audit.operation_log),
            },
            "deterministic_private_key_reconstruction": (
                derived_public == expected_public
            ),
            "candidate_identity_self_report": {
                "runner_representation": "BOUNDED_RELATION",
                "evaluator_candidate_label": relabelled_evaluation[
                    "candidate_label"
                ],
                "relation_constituted": relabelled_evaluation[
                    "relation_constituted"
                ],
                "reuse_executed": relabelled_evaluation[
                    "reuse_executed"
                ],
            },
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

