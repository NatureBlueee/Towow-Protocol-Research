#!/usr/bin/env python3
"""Independent reconstruction of Wave 007-B behavior and cost."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from authority import (
    OPERATION,
    PURPOSE,
    RETENTION,
    REUSE_OPERATION,
    SHARED_TASK_ID,
    SHARED_TASK_SHA256,
    STEP,
    WORLD_ID,
    envelope_hash,
)
from protocol import ProtocolError, verify_envelope
from simulator import load_json, simulate


ROOT = Path(__file__).resolve().parent


def _base_bound(body: dict[str, Any]) -> bool:
    return all(
        [
            body.get("shared_task_id") == SHARED_TASK_ID,
            body.get("shared_task_sha256") == SHARED_TASK_SHA256,
            body.get("world_id") == WORLD_ID,
            body.get("evaluation_step") == STEP,
            body.get("operation") == OPERATION,
            body.get("purpose") == PURPOSE,
            body.get("retention") == RETENTION,
        ]
    )


def _verified_present(
    run: dict[str, Any], name: str
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    returned = run["evidence_returns"].get(name)
    if not returned or returned.get("observation") != "PRESENT":
        return None
    evidence = returned.get("evidence")
    if not evidence:
        return None
    try:
        body = verify_envelope(
            evidence,
            run["contract"],
            expected_kind=evidence["kind"],
            expected_issuer=evidence["issuer"],
            step=STEP,
        )
    except (KeyError, ProtocolError):
        return None
    return evidence, body


def reconstruct_relation_evidence(
    run: dict[str, Any],
) -> dict[str, Any]:
    names = [
        "delivery",
        "ack_seek",
        "ack_offer",
        "explain_seek",
        "explain_offer",
        "proposal",
        "auth_seek",
        "auth_offer",
    ]
    verified = {name: _verified_present(run, name) for name in names}
    missing = [name for name, value in verified.items() if value is None]
    if missing:
        return {
            "valid": False,
            "missing_or_invalid": missing,
            "evidence_refs": [],
        }

    expected_envelopes = {
        "delivery": ("TASK_DELIVERY", "CONTROLLER-W7B"),
        "ack_seek": ("TASK_DELIVERY_ACK", "LAB-SEEK"),
        "ack_offer": ("TASK_DELIVERY_ACK", "LAB-OFFER"),
        "explain_seek": ("RELATION_EXPLAIN_BACK", "LAB-SEEK"),
        "explain_offer": ("RELATION_EXPLAIN_BACK", "LAB-OFFER"),
        "proposal": (
            "BOUNDED_RELATION_PROPOSAL",
            "CONTROLLER-W7B",
        ),
        "auth_seek": (
            "BOUNDED_REUSE_AUTHORIZATION",
            "LAB-SEEK",
        ),
        "auth_offer": (
            "BOUNDED_REUSE_AUTHORIZATION",
            "LAB-OFFER",
        ),
    }
    if any(
        verified[name][0]["kind"] != expected_kind
        or verified[name][0]["issuer"] != expected_issuer
        for name, (expected_kind, expected_issuer) in (
            expected_envelopes.items()
        )
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["kind_or_issuer_binding"],
            "evidence_refs": [],
        }
    if any(not _base_bound(verified[name][1]) for name in names):
        return {
            "valid": False,
            "missing_or_invalid": ["shared_coordinate_binding"],
            "evidence_refs": [],
        }

    delivery_env, delivery = verified["delivery"]
    if (
        delivery_env["issuer"] != "CONTROLLER-W7B"
        or delivery_env["kind"] != "TASK_DELIVERY"
        or delivery.get("operation") != OPERATION
        or delivery.get("purpose") != PURPOSE
        or delivery.get("retention") != RETENTION
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["delivery_binding"],
            "evidence_refs": [],
        }
    delivery_ref = envelope_hash(delivery_env)

    ack_items = [verified["ack_seek"], verified["ack_offer"]]
    ack_issuers = {item[0]["issuer"] for item in ack_items}
    if ack_issuers != {"LAB-SEEK", "LAB-OFFER"} or any(
        body.get("party") != env["issuer"]
        or body.get("delivery_sha256") != delivery_ref
        or body.get("ack_scope") != "THIS_OPERATION_ONLY"
        for env, body in ack_items
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["dual_ack_unique_binding"],
            "evidence_refs": [],
        }

    explain_items = [
        verified["explain_seek"],
        verified["explain_offer"],
    ]
    if {item[0]["issuer"] for item in explain_items} != {
        "LAB-SEEK",
        "LAB-OFFER",
    } or any(
        body.get("party") != env["issuer"]
        or body.get("understanding")
        != "EXPLICIT_BOUNDED_REUSE_AUTHORIZED"
        or body.get("reuse_operation") != REUSE_OPERATION
        or body.get("bounded_reuse_count") != 1
        for env, body in explain_items
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["dual_explain_back_binding"],
            "evidence_refs": [],
        }
    relation_ids = {body.get("relation_id") for _, body in explain_items}
    if len(relation_ids) != 1 or None in relation_ids:
        return {
            "valid": False,
            "missing_or_invalid": ["relation_id_conflict"],
            "evidence_refs": [],
        }
    relation_id = next(iter(relation_ids))

    proposal_env, proposal = verified["proposal"]
    proposal_ref = envelope_hash(proposal_env)
    if (
        proposal_env["issuer"] != "CONTROLLER-W7B"
        or proposal_env["kind"] != "BOUNDED_RELATION_PROPOSAL"
        or proposal.get("relation_id") != relation_id
        or proposal.get("status") != "PROPOSED_NOT_CONSTITUTED"
        or proposal.get("reuse_operation") != REUSE_OPERATION
        or proposal.get("bounded_reuse_count") != 1
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["proposal_binding"],
            "evidence_refs": [],
        }

    auth_items = [verified["auth_seek"], verified["auth_offer"]]
    auth_issuers = {item[0]["issuer"] for item in auth_items}
    if auth_issuers != {"LAB-SEEK", "LAB-OFFER"} or any(
        env["kind"] != "BOUNDED_REUSE_AUTHORIZATION"
        or body.get("party") != env["issuer"]
        or body.get("relation_id") != relation_id
        or body.get("proposal_sha256") != proposal_ref
        or body.get("reuse_operation") != REUSE_OPERATION
        or body.get("bounded_reuse_count") != 1
        or body.get("authorized") is not True
        for env, body in auth_items
    ):
        return {
            "valid": False,
            "missing_or_invalid": ["dual_authorization_unique_binding"],
            "evidence_refs": [],
        }

    refs = [envelope_hash(verified[name][0]) for name in names]
    return {
        "valid": True,
        "missing_or_invalid": [],
        "evidence_refs": refs,
        "relation_id": relation_id,
        "authorization_issuers": sorted(auth_issuers),
    }


def _valid_reuse_receipts(run: dict[str, Any]) -> list[dict[str, Any]]:
    receipts = []
    proposal = _verified_present(run, "proposal")
    proposal_ref = (
        envelope_hash(proposal[0]) if proposal is not None else None
    )
    for name, returned in run["evidence_returns"].items():
        if not name.startswith("reuse_response_"):
            continue
        if returned.get("observation") != "PRESENT":
            continue
        evidence = returned.get("evidence")
        if not evidence:
            continue
        try:
            body = verify_envelope(
                evidence,
                run["contract"],
                expected_kind="REUSE_EXECUTION_RECEIPT",
                expected_issuer="CONTROLLER-W7B",
                step=STEP,
            )
        except (KeyError, ProtocolError):
            continue
        if (
            body.get("status") == "EXECUTED"
            and _base_bound(body)
            and body.get("reuse_operation") == REUSE_OPERATION
            and body.get("reuse_count") == 1
            and body.get("proposal_sha256") == proposal_ref
            and body.get("authorization_issuers")
            == ["LAB-OFFER", "LAB-SEEK"]
        ):
            receipts.append(body)
    return receipts


def _withdrawal_observed(run: dict[str, Any]) -> bool:
    item = _verified_present(run, "withdrawal_poll")
    if item is None:
        return False
    evidence, body = item
    return (
        evidence["kind"] == "RELATION_WITHDRAWAL"
        and evidence["issuer"] in {"LAB-SEEK", "LAB-OFFER"}
        and _base_bound(body)
        and body.get("relation_id") == "REL-W7B-STERILE-REUSE-001"
        and body.get("relation_version") == 1
        and body.get("effective_after_reuse_count") == 1
        and body.get("status") == "WITHDRAWN"
    )


def recompute_cost(run: dict[str, Any]) -> dict[str, Any]:
    model = load_json("cost-model.json")
    weights = model["operation_weights"]
    log = run["operation_log"]
    operation_cost = sum(weights.get(item["op"], 0) for item in log)
    disclosure_units = sum(
        item.get("disclosure_units", 0) for item in log
    )
    byte_count = sum(item.get("bytes", 0) for item in log)
    byte_cost = byte_count / 1024 * model["byte_cost_per_1024"]
    return {
        "operation_count": len(log),
        "evidence_reads": sum(
            item["op"] == "READ_EVIDENCE" for item in log
        ),
        "signature_verifications": sum(
            item["op"] == "VERIFY_SIGNATURE" for item in log
        ),
        "authority_requests": sum(
            item["op"] == "AUTHORITY_REUSE_REQUEST" for item in log
        ),
        "bytes": byte_count,
        "disclosure_units": disclosure_units,
        "operation_cost": operation_cost,
        "byte_cost": round(byte_cost, 6),
        "evidence_cost": round(
            operation_cost
            + disclosure_units * model["disclosure_unit_cost"]
            + byte_cost,
            6,
        ),
    }


def evaluate_run(run: dict[str, Any]) -> dict[str, Any]:
    truth = run["evaluator_truth"]
    evidence = reconstruct_relation_evidence(run)
    decisions = [
        item
        for item in run["operation_log"]
        if item["op"] == "CANDIDATE_RELATION_DECISION"
    ]
    active_decisions = [
        item for item in decisions if item["state"] == "ACTIVE_BOUNDED"
    ]
    active_with_valid_refs = any(
        evidence["valid"]
        and set(item["evidence_refs"])
        == set(evidence["evidence_refs"])
        for item in active_decisions
    )
    legitimate = (
        truth["reuse_truth"]
        == "EXPLICIT_BOUNDED_REUSE_AUTHORIZED"
    )
    receipts = _valid_reuse_receipts(run)
    reuse_executed = len(receipts) == 1
    withdrawal = _withdrawal_observed(run)
    last_state = decisions[-1]["state"] if decisions else "NONE"
    withdrawn_index = next(
        (
            index
            for index, item in enumerate(run["operation_log"])
            if item["op"] == "CANDIDATE_RELATION_DECISION"
            and item["state"] == "INACTIVE_WITHDRAWN"
        ),
        None,
    )
    post_withdrawal_reuse_request = (
        withdrawn_index is not None
        and any(
            item["op"] == "AUTHORITY_REUSE_REQUEST"
            for item in run["operation_log"][withdrawn_index + 1 :]
        )
    )

    false_constitution = int(
        bool(active_decisions)
        and (not legitimate or not active_with_valid_refs)
    )
    missed_legitimate_reuse = int(legitimate and not reuse_executed)
    stale_reuse = int(
        post_withdrawal_reuse_request
        or (
            reuse_executed
            and (not legitimate or not evidence["valid"])
        )
    )
    withdrawal_residual = int(
        truth["withdraw_after_first_reuse"]
        and reuse_executed
        and (not withdrawal or last_state != "INACTIVE_WITHDRAWN")
    )
    cost = recompute_cost(run)
    model = load_json("cost-model.json")
    task_value = model["task_value"] if reuse_executed and legitimate else 0
    net_value = (
        task_value
        - false_constitution * model["false_constitution_loss"]
        - missed_legitimate_reuse
        * model["missed_legitimate_reuse_loss"]
        - stale_reuse * model["stale_reuse_loss"]
        - withdrawal_residual
        * model["withdrawal_residual_loss"]
        - cost["evidence_cost"]
    )
    observations = {
        state: sum(
            item["op"] == "READ_EVIDENCE"
            and item.get("observation") == state
            for item in run["operation_log"]
        )
        for state in ["UNKNOWN", "REFUSE", "ABSENT"]
    }
    return {
        "candidate_label": run["candidate_output"]["candidate_label"],
        "evaluator_world_id": truth["evaluator_world_id"],
        "relation_evidence_valid": evidence["valid"],
        "relation_constituted": active_with_valid_refs,
        "reuse_executed": reuse_executed,
        "false_constitution": false_constitution,
        "missed_legitimate_reuse": missed_legitimate_reuse,
        "stale_reuse": stale_reuse,
        "withdrawal_residual": withdrawal_residual,
        "terminal_observations": observations,
        "cost": cost,
        "net_value": round(net_value, 6),
        "candidate_self_report_ignored": True,
    }


def _behavior_signature(run: dict[str, Any]) -> dict[str, Any]:
    return {
        "decisions": [
            {
                "state": item["state"],
                "evidence_refs": item["evidence_refs"],
            }
            for item in run["operation_log"]
            if item["op"] == "CANDIDATE_RELATION_DECISION"
        ],
        "reuse_responses": [
            item["observation"]
            for item in run["operation_log"]
            if item["op"] == "AUTHORITY_REUSE_RESPONSE"
        ],
        "operations": [item["op"] for item in run["operation_log"]],
    }


def evaluate() -> dict[str, Any]:
    simulation = simulate()
    baseline = [
        {"run": run, "evaluation": evaluate_run(run)}
        for run in simulation["baseline_runs"]
    ]
    mutations = simulation["mutations"]
    bounded_relation = next(
        item
        for item in baseline
        if item["evaluation"]["evaluator_world_id"]
        == "PW-BOUNDED-VALID"
        and item["evaluation"]["candidate_label"]
        == "BOUNDED_RELATION"
    )
    base_eval = bounded_relation["evaluation"]
    base_run = bounded_relation["run"]

    deletion = {
        name: evaluate_run(run)
        for name, run in mutations["evidence_deletion"].items()
    }
    renamed_eval = evaluate_run(mutations["opaque_rename"])
    self_report_eval = evaluate_run(
        mutations["self_report_injection"]
    )
    label_swap_eval = evaluate_run(mutations["label_function_swap"])
    truth_flip_eval = evaluate_run(mutations["truth_label_flip"])
    duplicate_eval = evaluate_run(
        mutations["duplicate_authorization"]
    )
    unauthorized_eval = evaluate_run(
        mutations["unauthorized_authorization"]
    )
    bytes_eval = evaluate_run(mutations["bytes_binding_change"])
    post_withdrawal_eval = evaluate_run(
        mutations["post_withdrawal_reuse"]
    )
    wrong_kind_eval = evaluate_run(mutations["wrong_kind_ack"])
    cross_purpose_eval = evaluate_run(
        mutations["cross_purpose_authorization"]
    )
    unauthorized_withdrawal_eval = evaluate_run(
        mutations["unauthorized_withdrawal"]
    )

    by_world_rep = {
        (
            item["evaluation"]["evaluator_world_id"],
            item["evaluation"]["candidate_label"],
        ): item["evaluation"]
        for item in baseline
    }
    one_shot_task_bound = [
        value
        for (world, representation), value in by_world_rep.items()
        if world.startswith("PW-ONE")
        and representation == "TASK_BOUND"
    ]
    bounded_valid = {
        rep: by_world_rep[("PW-BOUNDED-VALID", rep)]
        for rep in [
            "TASK_BOUND",
            "EXPLAIN_BACK",
            "BOUNDED_RELATION",
            "NO_EVIDENCE",
        ]
    }

    claims = {
        "task_bound_evidence_sufficient_for_one_shot_non_constitution": {
            "status": "SUPPORTED_SCOPED"
            if all(
                item["false_constitution"] == 0
                and item["stale_reuse"] == 0
                for item in one_shot_task_bound
            )
            else "REFUTED",
            "scope": "ONE_OPERATION_ONLY paired worlds only",
        },
        "explicit_bounded_relation_evidence_enables_legitimate_reuse": {
            "status": "SUPPORTED_SCOPED"
            if (
                bounded_valid["BOUNDED_RELATION"]["reuse_executed"]
                and bounded_valid["TASK_BOUND"][
                    "missed_legitimate_reuse"
                ]
                and bounded_valid["EXPLAIN_BACK"][
                    "missed_legitimate_reuse"
                ]
            )
            else "REFUTED",
            "observable_increment": (
                "dual unique ACK + dual explain-back + exact proposal + "
                "dual unique bounded authorization"
            ),
        },
        "explain_back_alone_is_reuse_authority": {
            "status": "REFUTED"
            if not bounded_valid["EXPLAIN_BACK"]["reuse_executed"]
            else "SUPPORTED_SCOPED",
        },
        "no_evidence_zero_cost_is_adequate": {
            "status": "REFUTED"
            if bounded_valid["NO_EVIDENCE"][
                "missed_legitimate_reuse"
            ]
            else "UNKNOWN",
        },
        "withdrawal_clears_active_relation": {
            "status": "SUPPORTED_SCOPED"
            if bounded_valid["BOUNDED_RELATION"][
                "withdrawal_residual"
            ]
            == 0
            else "REFUTED",
        },
    }

    return {
        "schema": "towow.wave007b-evaluation.v1",
        "shared_task_id": "W6-STERILE-ROUTE-SIMULATION-001",
        "shared_task_sha256": (
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
        ),
        "baseline": baseline,
        "mutation_results": {
            "opaque_rename_behavior_unchanged": (
                _behavior_signature(base_run)
                == _behavior_signature(mutations["opaque_rename"])
            ),
            "opaque_rename_score_unchanged": (
                renamed_eval["net_value"] == base_eval["net_value"]
                and renamed_eval["cost"] == base_eval["cost"]
            ),
            "evidence_deletion": deletion,
            "all_decisive_deletions_change_action": all(
                not item["relation_constituted"]
                and item["missed_legitimate_reuse"] == 1
                for item in deletion.values()
            ),
            "self_report_score_unchanged": (
                self_report_eval["net_value"] == base_eval["net_value"]
                and self_report_eval["cost"] == base_eval["cost"]
            ),
            "label_function_swap_score_unchanged": (
                label_swap_eval["net_value"] == base_eval["net_value"]
                and label_swap_eval["cost"] == base_eval["cost"]
            ),
            "truth_label_flip_candidate_behavior_unchanged": (
                _behavior_signature(base_run)
                == _behavior_signature(mutations["truth_label_flip"])
            ),
            "truth_label_flip_confusion_changed": (
                truth_flip_eval["false_constitution"] == 1
                and truth_flip_eval["stale_reuse"] == 1
            ),
            "duplicate_authorization_rejected": (
                not duplicate_eval["relation_constituted"]
                and not duplicate_eval["reuse_executed"]
            ),
            "unauthorized_authorization_rejected": (
                not unauthorized_eval["relation_constituted"]
                and not unauthorized_eval["reuse_executed"]
            ),
            "changed_signed_bytes_rejected": (
                not bytes_eval["relation_constituted"]
                and not bytes_eval["reuse_executed"]
            ),
            "post_withdrawal_reuse_counted": (
                post_withdrawal_eval["stale_reuse"] == 1
                and post_withdrawal_eval["withdrawal_residual"] == 1
            ),
            "wrong_kind_evidence_rejected": (
                not wrong_kind_eval["relation_constituted"]
                and not wrong_kind_eval["reuse_executed"]
            ),
            "cross_purpose_authorization_rejected": (
                not cross_purpose_eval["relation_constituted"]
                and not cross_purpose_eval["reuse_executed"]
            ),
            "unauthorized_withdrawal_not_accepted": (
                unauthorized_withdrawal_eval[
                    "withdrawal_residual"
                ]
                == 1
            ),
        },
        "scoped_claims": claims,
        "overall_grade": None,
        "evidence_boundary": "LOCAL_SYNTHETIC_SELF_TEST_NOT_INDEPENDENT_AUDIT",
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
