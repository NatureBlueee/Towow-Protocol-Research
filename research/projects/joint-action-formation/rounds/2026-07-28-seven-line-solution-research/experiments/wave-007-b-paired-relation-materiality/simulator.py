#!/usr/bin/env python3
"""Generate opaque paired-world candidate traces for Wave 007-B."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from authority import HiddenAuthorityService, PrivateWorldState
from candidate import run_candidate


ROOT = Path(__file__).resolve().parent


def load_json(name: str) -> dict[str, Any]:
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def run_one(
    world: dict[str, Any],
    representation: dict[str, Any],
    *,
    candidate_label: str | None = None,
    opaque_seed: str | None = None,
    deleted_evidence: set[str] | None = None,
    evidence_overrides: dict[str, dict[str, Any]] | None = None,
    self_report: dict[str, Any] | None = None,
    evaluator_attack: str | None = None,
) -> dict[str, Any]:
    service = HiddenAuthorityService(
        PrivateWorldState(
            reuse_truth=world["reuse_truth"],
            relation_evidence=world["relation_evidence"],
            withdraw_after_first_reuse=world[
                "withdraw_after_first_reuse"
            ],
        ),
        opaque_seed=opaque_seed or world["opaque_seed"],
        deleted_evidence=deleted_evidence,
        evidence_overrides=evidence_overrides,
        evaluator_attack=evaluator_attack,
    )
    gateway, audit = service.create_gateway()
    output = run_candidate(
        gateway,
        visible_evidence=copy.deepcopy(
            representation["visible_evidence"]
        ),
        candidate_label=candidate_label
        or representation["representation_id"],
        self_report=self_report,
    )
    return {
        "schema": "towow.wave007b-run-transcript.v1",
        "candidate_output": output,
        "operation_log": copy.deepcopy(audit.operation_log),
        "evidence_returns": copy.deepcopy(audit.evidence_returns),
        "contract": copy.deepcopy(audit.contract),
        "evaluator_truth": {
            "evaluator_world_id": world["evaluator_world_id"],
            "reuse_truth": world["reuse_truth"],
            "relation_evidence": world["relation_evidence"],
            "withdraw_after_first_reuse": world[
                "withdraw_after_first_reuse"
            ],
        },
        "actual_visible_evidence": copy.deepcopy(
            representation["visible_evidence"]
        ),
    }


def simulate() -> dict[str, Any]:
    worlds = load_json("paired-worlds.json")["worlds"]
    representations = load_json("representations.json")[
        "representations"
    ]
    runs = []
    for world in worlds:
        for representation in representations:
            runs.append(run_one(world, representation))

    bounded_valid = next(
        item
        for item in worlds
        if item["evaluator_world_id"] == "PW-BOUNDED-VALID"
    )
    relation_representation = next(
        item
        for item in representations
        if item["representation_id"] == "BOUNDED_RELATION"
    )
    baseline = run_one(bounded_valid, relation_representation)

    deletion_runs = {
        name: run_one(
            bounded_valid,
            relation_representation,
            deleted_evidence={name},
            opaque_seed=f"deletion-{name}",
        )
        for name in [
            "delivery",
            "ack_seek",
            "ack_offer",
            "explain_seek",
            "explain_offer",
            "proposal",
            "auth_seek",
            "auth_offer",
        ]
    }

    renamed = run_one(
        bounded_valid,
        relation_representation,
        candidate_label="RANDOM-LABEL-9F3A",
        opaque_seed="renamed-opaque-handle",
    )
    self_report = run_one(
        bounded_valid,
        relation_representation,
        self_report={
            "accepted": True,
            "false_positive": 0,
            "net_value": 9999,
            "trace": [
                {"event": "FAKE_REUSE", "status": "EXECUTED"}
            ],
        },
    )
    label_swap = run_one(
        bounded_valid,
        relation_representation,
        candidate_label="NO_EVIDENCE",
        opaque_seed="label-function-swap",
    )
    truth_flip = copy.deepcopy(baseline)
    truth_flip["evaluator_truth"]["reuse_truth"] = "ONE_OPERATION_ONLY"
    truth_flip["evaluator_truth"]["relation_evidence"] = "VALID_NO_REUSE"

    duplicate_source = baseline["evidence_returns"]["auth_seek"]
    duplicate_auth = run_one(
        bounded_valid,
        relation_representation,
        evidence_overrides={
            "auth_offer": copy.deepcopy(duplicate_source)
        },
        opaque_seed="duplicate-auth",
    )
    changed_proposal = copy.deepcopy(
        baseline["evidence_returns"]["proposal"]
    )
    changed_proposal["evidence"]["body"]["relation_version"] = 99
    bytes_binding = run_one(
        bounded_valid,
        relation_representation,
        evidence_overrides={"proposal": changed_proposal},
        opaque_seed="changed-proposal-bytes",
    )
    unauthorized_authorization = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="UNAUTHORIZED_AUTH_OFFER",
        opaque_seed="unauthorized-auth-offer",
    )
    wrong_kind_ack = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="WRONG_KIND_ACK_OFFER",
        opaque_seed="wrong-kind-ack-offer",
    )
    cross_purpose_authorization = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="CROSS_PURPOSE_AUTH_OFFER",
        opaque_seed="cross-purpose-auth-offer",
    )
    unauthorized_withdrawal = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="UNAUTHORIZED_WITHDRAWAL",
        opaque_seed="unauthorized-withdrawal",
    )
    post_withdrawal_reuse = copy.deepcopy(baseline)
    active_decision = next(
        item
        for item in post_withdrawal_reuse["operation_log"]
        if item["op"] == "CANDIDATE_RELATION_DECISION"
        and item["state"] == "ACTIVE_BOUNDED"
    )
    post_withdrawal_reuse["operation_log"].extend(
        [
            {
                "op": "AUTHORITY_REUSE_REQUEST",
                "authorization_refs": [],
                "bytes": 2,
                "disclosure_units": 0,
            },
            copy.deepcopy(active_decision),
        ]
    )

    return {
        "schema": "towow.wave007b-simulation.v1",
        "baseline_runs": runs,
        "mutations": {
            "opaque_rename": renamed,
            "evidence_deletion": deletion_runs,
            "self_report_injection": self_report,
            "label_function_swap": label_swap,
            "truth_label_flip": truth_flip,
            "duplicate_authorization": duplicate_auth,
            "unauthorized_authorization": unauthorized_authorization,
            "bytes_binding_change": bytes_binding,
            "wrong_kind_ack": wrong_kind_ack,
            "cross_purpose_authorization": (
                cross_purpose_authorization
            ),
            "unauthorized_withdrawal": unauthorized_withdrawal,
            "post_withdrawal_reuse": post_withdrawal_reuse,
        },
    }


def main() -> int:
    print(
        json.dumps(
            simulate(), ensure_ascii=False, sort_keys=True, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
