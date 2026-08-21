#!/usr/bin/env python3
"""Blind broker and G4 line-local evidence CLI."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from module import (
    FORECAST_COORDINATES,
    OwnerTargetService,
    audit_e3_pair,
    score,
)


HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "public_fixture.json"
HOLDOUT = HERE / "private_holdout.json"
WORKER = HERE / "worker.py"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    holdout = json.loads(HOLDOUT.read_text(encoding="utf-8"))
    if public["fixture_id"] != holdout["fixture_id"]:
        raise RuntimeError("public/holdout fixture mismatch")
    return public, holdout


def _validate_prediction(message: dict[str, Any]) -> None:
    predictions = message.get("predictions")
    if not isinstance(predictions, dict) or set(predictions) != set(
        FORECAST_COORDINATES
    ):
        raise RuntimeError("prediction must preserve G4 line-local coordinates")
    if not set(predictions.values()) <= {"YES", "NO", "ABSTAIN"}:
        raise RuntimeError("invalid prediction value")


def run_case(
    worker_path: Path,
    public: dict[str, Any],
    private_case: dict[str, Any],
) -> dict[str, Any]:
    service = OwnerTargetService(public["episode"], private_case)
    predictions: dict[str, dict[str, str]] = {}
    truth = {"P0": service.initial_truth()}
    phase_trace: list[str] = []
    saw_interaction = False
    saw_reservation = False
    saw_commit = False
    reconciliation_succeeded = False
    worker_result: dict[str, Any] = {}
    start = {
        "type": "start",
        "episode": copy.deepcopy(public["episode"]),
        "available_actions": list(public["available_actions"]),
    }
    try:
        with tempfile.TemporaryDirectory(prefix="ce001-g4-blind-") as tmp:
            process = subprocess.Popen(
                ["python3", "-I", str(worker_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=tmp,
                env={
                    "PATH": os.environ.get("PATH", ""),
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONDONTWRITEBYTECODE": "1",
                },
            )
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(json.dumps(start, sort_keys=True) + "\n")
            process.stdin.flush()
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                message = json.loads(line)
                kind = message.get("type")
                if kind == "prediction":
                    _validate_prediction(message)
                    stage = message.get("stage")
                    if stage == "P0":
                        if phase_trace:
                            raise RuntimeError("P0 must precede every interaction")
                        phase_trace.append("P0")
                    elif stage == "P1":
                        if not saw_interaction or saw_reservation or saw_commit:
                            raise RuntimeError(
                                "P1 must follow read-only interaction and "
                                "precede reservation/commit"
                            )
                        truth["P1"] = service.p1_truth()
                        phase_trace.append("P1")
                    else:
                        raise RuntimeError("unknown prediction stage")
                    if stage in predictions:
                        raise RuntimeError("duplicate prediction stage")
                    predictions[stage] = message["predictions"]
                    process.stdin.write('{"type":"ack"}\n')
                    process.stdin.flush()
                    continue
                if kind == "action":
                    action = message.get("action")
                    if action not in public["available_actions"]:
                        raise RuntimeError(f"action outside public interface: {action}")
                    if "P0" not in predictions:
                        raise RuntimeError("action before P0")
                    if "P1" not in predictions:
                        if action != "inspect_interfaces":
                            raise RuntimeError(
                                "only read-only inspection allowed before P1"
                            )
                        if not saw_interaction:
                            phase_trace.append("INTERACTION")
                        saw_interaction = True
                    else:
                        if action == "inspect_interfaces":
                            raise RuntimeError("interaction phase already frozen")
                        if action == "reserve":
                            phase_trace.append("RESERVATION")
                            saw_reservation = True
                        elif action == "read_commit_evidence":
                            if not saw_reservation:
                                raise RuntimeError(
                                    "commit evidence before reservation"
                                )
                            phase_trace.append("COMMIT_EVIDENCE")
                            saw_commit = True
                        elif action == "submit_operation":
                            if not saw_reservation or not saw_commit:
                                raise RuntimeError(
                                    "attempt before reservation/commit evidence"
                                )
                            phase_trace.append("ATTEMPT")
                        elif action == "readback_operation":
                            phase_trace.append("READBACK")
                        elif action == "reconcile_operation":
                            phase_trace.append("RECONCILIATION")
                        elif action == "retry_idempotent":
                            phase_trace.append("RETRY")
                        elif action in {
                            "request_q_acceptance",
                            "request_venue_acceptance",
                        }:
                            if not reconciliation_succeeded:
                                raise RuntimeError(
                                    "owner act requested before exact SUCCEEDED "
                                    "reconciliation"
                                )
                            phase_trace.append("OWNER_ACT")
                    raw = service.call(action, message.get("args", {}))
                    if (
                        action == "reconcile_operation"
                        and isinstance(raw, dict)
                        and raw.get("state") == "SUCCEEDED"
                        and all(
                            raw.get(key) == value
                            for key, value in service._bound().items()
                        )
                    ):
                        reconciliation_succeeded = True
                    process.stdin.write(
                        json.dumps(
                            {"type": "response", "raw": raw}, sort_keys=True
                        )
                        + "\n"
                    )
                    process.stdin.flush()
                    continue
                if kind == "result":
                    worker_result = dict(message.get("result", {}))
                    break
                raise RuntimeError(f"unknown worker message: {message}")
            process.stdin.close()
            return_code = process.wait(timeout=15)
            stderr = process.stderr.read() if process.stderr is not None else ""
            process.stdout.close()
            if process.stderr is not None:
                process.stderr.close()
            if return_code != 0:
                raise RuntimeError(f"worker failed: {stderr}")
        if set(predictions) != {"P0", "P1"}:
            raise RuntimeError("worker did not freeze P0 and P1")
        result = {
            "case_ref": private_case["case_ref"],
            "predictions": predictions,
            "truth": truth,
            "phase_trace": phase_trace,
            "raw_trace": copy.deepcopy(service.raw_trace),
            "hidden_failure_trace": copy.deepcopy(service.hidden_trace),
            "submit_responses": copy.deepcopy(service.submit_responses),
            "worker_result": worker_result,
            "observations": service.observations(worker_result),
        }
        return result
    finally:
        service.close()


def _matched_no_interaction_occurrences(
    public: dict[str, Any], cases: list[dict[str, Any]]
) -> int:
    occurrences = 0
    for private_case in cases:
        if private_case["revoke_after_reservation"]:
            continue
        with OwnerTargetService(public["episode"], private_case) as twin:
            twin.call("submit_operation", twin._bound())
            occurrences += twin.occurrence_count
    return occurrences


def _has_expected_label_keys(value: Any) -> bool:
    if isinstance(value, dict):
        if any(
            "expected" in str(key).lower() or "label" in str(key).lower()
            for key in value
        ):
            return True
        return any(_has_expected_label_keys(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_expected_label_keys(child) for child in value)
    return False


def _failure_injection_counts(
    rows: list[dict[str, Any]], cases: list[dict[str, Any]]
) -> dict[str, int]:
    by_ref = {case["case_ref"]: case for case in cases}
    attempted = [
        row
        for row in rows
        if row["observations"]["attempt"]["count"] > 0
    ]
    mutations = [
        by_ref[row["case_ref"]].get("acceptance_mutation", "NONE")
        for row in rows
    ]
    return {
        "DROP_SUBMIT_ACK@target-record": sum(
            by_ref[row["case_ref"]]["first_submit"] == "EFFECT_ACK_LOST"
            for row in attempted
        ),
        "DROP_SUBMIT_ACK@no-record": sum(
            by_ref[row["case_ref"]]["first_submit"] == "NO_EFFECT_ACK_LOST"
            for row in attempted
        ),
        "WRONG_OBJECT_READBACK": sum(
            any(
                event["action"] == "readback_operation"
                for event in row["raw_trace"]
            )
            for row in rows
        ),
        "CONCURRENT_DOUBLE_DELIVERY": sum(
            row["observations"]["attempt"]["concurrent_barrier_parties"] == 2
            for row in rows
        ),
        "REVOKE_AFTER_RESERVATION_BEFORE_COMMIT": sum(
            any(
                event["event"] == "OWNER_REVOCATION_AFTER_RESERVATION"
                for event in row["hidden_failure_trace"]
            )
            for row in rows
        ),
        "OWNER_REFUSAL_AFTER_TARGET_RECORD": mutations.count("O_V_REFUSE"),
        "OWNER_ACT_WRONG_EPISODE": mutations.count("O_V_WRONG_EPISODE"),
        "OWNER_ACT_WRONG_Q": mutations.count("O_V_WRONG_Q"),
        "OWNER_ACT_WRONG_OCCURRENCE": mutations.count("O_V_WRONG_EFFECT"),
        "OWNER_ACT_STALE_REVISION": mutations.count("O_V_STALE"),
        "OWNER_ACT_DUPLICATED_ISSUER": mutations.count(
            "O_V_DUPLICATE_ISSUER"
        ),
        "NONTERMINAL_EXACT_READBACK": sum(
            any(
                event["action"] == "reconcile_operation"
                and isinstance(event["raw_response"], dict)
                and event["raw_response"].get("state") == "PENDING"
                for event in row["raw_trace"]
            )
            for row in rows
        ),
    }


def evaluate() -> dict[str, Any]:
    public, holdout = load_inputs()
    before = file_sha256(HOLDOUT)
    rows = [
        run_case(WORKER, public, private_case)
        for private_case in holdout["cases"]
    ]
    after = file_sha256(HOLDOUT)
    e3a = next(
        case
        for case in holdout["cases"]
        if case["case_ref"] == "E3A-ACK-LOST-EFFECT"
    )
    e3b = next(
        case
        for case in holdout["cases"]
        if case["case_ref"] == "E3B-ACK-LOST-NO-EFFECT"
    )
    baseline = _matched_no_interaction_occurrences(
        public, holdout["cases"]
    )
    return {
        "namespace": "G4",
        "qualification": "QUALIFIED_COMPONENT_OUTPUT",
        "evidence": {
            "fixture_id": public["fixture_id"],
            "evidence_state": "LOCAL_LINE_COMPONENT_MODEL",
            "case_count": len(rows),
            "object_adapter": copy.deepcopy(
                public["episode"]["object_adapter"]
            ),
            "ack_pair_audit": audit_e3_pair(
                public["episode"], e3a, e3b
            ),
            "scores": score(rows, baseline),
            "blind_holdout": {
                "holdout_sha256_before": before,
                "holdout_sha256_after": after,
                "holdout_unchanged": before == after,
                "worker_start_fields": sorted(
                    ["type", "episode", "available_actions"]
                ),
                "expected_label_table_exists": _has_expected_label_keys(
                    holdout
                ),
                "isolation_boundary": (
                    "The worker receives only public start bytes and requested "
                    "raw responses. O_E/O_Q/O_V are actual child processes with "
                    "per-process private keys; this is not hostile same-user "
                    "OS isolation or real owner identity."
                ),
            },
            "failure_injections": _failure_injection_counts(
                rows, holdout["cases"]
            ),
            "cases": rows,
            "claim_limits": [
                "real temporary-power restoration is NOT_RUN",
                "real owner act and human acceptance are NOT_RUN",
                "real product or arm comparison is NOT_RUN",
                "general reliance calibration is NOT_ESTABLISHED",
                "complete CE-001 contract evaluation is NOT_RUN",
            ],
        },
    }


def compact(report: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(report)
    result["evidence"]["cases"] = [
        {
            "case_ref": row["case_ref"],
            "phase_trace": row["phase_trace"],
            "observations": row["observations"],
        }
        for row in result["evidence"]["cases"]
    ]
    return result


def self_test(report: dict[str, Any]) -> None:
    evidence = report["evidence"]
    assert evidence["case_count"] == 10
    audit = evidence["ack_pair_audit"]
    assert audit["classification"] == "ACTIVE"
    assert audit["active"]["pre_attempt_isomorphic"]
    assert audit["active"]["distinguishing_witness_exists"]
    assert evidence["blind_holdout"]["holdout_unchanged"]
    assert not evidence["blind_holdout"]["expected_label_table_exists"]
    attempt = evidence["scores"]["attempt_readback_evidence"]
    assert attempt["matched_no_interaction_target_occurrences"] == 0
    assert attempt["duplicate_target_occurrence_cases"] == 0
    assert attempt["attempt_authorization_violation_cases"] == 0
    p1 = evidence["scores"]["reliance_calibration"]["P1"][
        "terminal_reconciliation"
    ]
    assert p1["TP"] == 9
    assert p1["FP"] == 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    report = evaluate()
    if args.self_test:
        self_test(report)
    print(
        json.dumps(
            report if args.full else compact(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    if args.self_test:
        print("SELF_TEST_PASS")


if __name__ == "__main__":
    main()
