#!/usr/bin/env python3
"""Run Wave 007-B2 candidates in spawned JSON-RPC processes."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from authority import AuthorityBroker, PrivateWorldState


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
    self_report: dict[str, Any] | None = None,
    evaluator_attack: str | None = None,
    forbidden_rpc_probes: list[str] | None = None,
) -> dict[str, Any]:
    broker = AuthorityBroker(
        PrivateWorldState(
            reuse_truth=world["reuse_truth"],
            relation_evidence=world["relation_evidence"],
            withdraw_after_first_reuse=world[
                "withdraw_after_first_reuse"
            ],
        ),
        opaque_seed=opaque_seed or world["opaque_seed"],
        deleted_evidence=deleted_evidence,
        evaluator_attack=evaluator_attack,
    )
    bootstrap = {
        **broker.runner_bootstrap(),
        "visible_evidence": copy.deepcopy(
            representation["visible_evidence"]
        ),
        "candidate_claimed_label": candidate_label
        or representation["representation_id"],
        "self_report": copy.deepcopy(self_report),
        "forbidden_rpc_probes": list(forbidden_rpc_probes or []),
    }
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "candidate_worker.py")],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=environment,
    )
    if process.stdin is None or process.stdout is None:
        raise RuntimeError("CANDIDATE_RPC_PIPE_UNAVAILABLE")
    process.stdin.write(
        json.dumps(bootstrap, ensure_ascii=False, sort_keys=True) + "\n"
    )
    process.stdin.flush()

    worker_result: dict[str, Any] | None = None
    while True:
        line = process.stdout.readline()
        if not line:
            break
        message = json.loads(line)
        if message.get("type") == "request":
            try:
                result = broker.dispatch(
                    message["method"], message.get("params", {})
                )
                response = {
                    "type": "response",
                    "id": message["id"],
                    "ok": True,
                    "result": result,
                }
            except (KeyError, PermissionError, TypeError) as exc:
                response = {
                    "type": "response",
                    "id": message.get("id"),
                    "ok": False,
                    "error": str(exc),
                }
            process.stdin.write(
                json.dumps(
                    response, ensure_ascii=False, sort_keys=True
                )
                + "\n"
            )
            process.stdin.flush()
            continue
        if message.get("type") == "result":
            worker_result = message
            break
        raise RuntimeError("CANDIDATE_RPC_UNKNOWN_MESSAGE")

    process.stdin.close()
    return_code = process.wait(timeout=10)
    stderr = process.stderr.read() if process.stderr is not None else ""
    process.stdout.close()
    if process.stderr is not None:
        process.stderr.close()
    if return_code != 0 or worker_result is None:
        raise RuntimeError(
            f"CANDIDATE_PROCESS_FAILED rc={return_code}: {stderr}"
        )
    snapshot = broker.snapshot()
    return {
        "schema": "towow.wave007b2-run-transcript.v1",
        "candidate_output": worker_result["candidate_output"],
        "forbidden_rpc_probe_results": worker_result[
            "forbidden_rpc_probe_results"
        ],
        "operation_log": snapshot.operation_log,
        "evidence_returns": snapshot.evidence_returns,
        "contract": snapshot.contract,
        "runner": {
            "implementation_id": representation["representation_id"],
            "parent_pid": os.getpid(),
            "worker_pid": process.pid,
            "transport": "SPAWNED_PROCESS_NDJSON_RPC",
            "broker_object_transferred": False,
            "audit_handle_transferred": False,
            "filesystem_sandbox": False,
        },
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
    runner_identity_tamper = copy.deepcopy(baseline)
    runner_identity_tamper["runner"][
        "implementation_id"
    ] = "TASK_BOUND"

    duplicate_auth = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="DUPLICATE_AUTHORIZATION",
        opaque_seed="duplicate-auth",
    )
    bytes_binding = run_one(
        bounded_valid,
        relation_representation,
        evaluator_attack="CHANGED_PROPOSAL_BYTES",
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
    rpc_boundary_probe = run_one(
        bounded_valid,
        relation_representation,
        forbidden_rpc_probes=[
            "get_private_world_state",
            "clear_audit_log",
            "sign_for_authority",
        ],
        opaque_seed="rpc-boundary-probe",
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
            "runner_identity_tamper": runner_identity_tamper,
            "duplicate_authorization": duplicate_auth,
            "unauthorized_authorization": unauthorized_authorization,
            "bytes_binding_change": bytes_binding,
            "wrong_kind_ack": wrong_kind_ack,
            "cross_purpose_authorization": (
                cross_purpose_authorization
            ),
            "unauthorized_withdrawal": unauthorized_withdrawal,
            "rpc_boundary_probe": rpc_boundary_probe,
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
