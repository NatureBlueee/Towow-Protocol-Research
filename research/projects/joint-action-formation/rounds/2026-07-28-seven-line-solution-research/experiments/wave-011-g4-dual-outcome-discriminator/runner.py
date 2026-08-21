#!/usr/bin/env python3
"""Broker, runner, and independent post-run scorer for the 14-world pilot."""

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

from evaluator import score_method
from primitive_services import EXECUTION_ACTIONS, FORMATION_ACTIONS, PrimitiveService, deep_merge


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixture.json"
ORACLE = HERE / "private_oracle.json"
WORKERS = {
    "STATIC_PACKET": HERE / "workers" / "static_packet_worker.py",
    "MATURE_COMPOSITE": HERE / "workers" / "mature_composite_worker.py",
    "SAME_PERMISSION_STRONG_CENTER": HERE / "workers" / "strong_center_worker.py",
    "LEGITIMATELY_DELEGATED_CENTER": HERE / "workers" / "delegated_center_worker.py",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(FIXTURE.read_text(encoding="utf-8")),
        json.loads(ORACLE.read_text(encoding="utf-8")),
    )


def expanded_public(fixture: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(fixture["templates"][world["template"]])


def run_worker(
    method: str,
    worker_path: Path,
    service: PrimitiveService,
    public_packet: dict[str, Any],
) -> dict[str, Any]:
    predictions: dict[str, dict[str, str]] = {}
    truths: dict[str, dict[str, bool]] = {"P0": service.initial_truth()}
    action_count = 0
    saw_attempt = False
    notes: list[str] = []
    with tempfile.TemporaryDirectory(prefix="wave011-g4-worker-") as tmp:
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
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(
            json.dumps(
                {
                    "type": "start",
                    "public_packet": public_packet,
                    "available_primitives": sorted(service.allowed_actions),
                },
                sort_keys=True,
            )
            + "\n"
        )
        process.stdin.flush()
        while True:
            line = process.stdout.readline()
            if not line:
                break
            message = json.loads(line)
            message_type = message.get("type")
            if message_type == "prediction":
                stage = message["stage"]
                if stage == "P0":
                    if predictions or action_count:
                        raise RuntimeError("P0 must be frozen before every action")
                elif stage == "P1":
                    if "P0" not in predictions or "P1" in predictions:
                        raise RuntimeError("P1 ordering violation")
                    truths["P1"] = service.freeze_p1()
                else:
                    raise RuntimeError(f"unexpected prediction stage: {stage}")
                predictions[stage] = message["predictions"]
                process.stdin.write('{"type":"ack"}\n')
                process.stdin.flush()
            elif message_type == "action":
                if "P0" not in predictions:
                    raise RuntimeError("action occurred before P0")
                action = message["action"]
                if "P1" not in predictions and action not in FORMATION_ACTIONS:
                    raise RuntimeError("attempt/recovery occurred before P1")
                if "P1" in predictions and action not in EXECUTION_ACTIONS:
                    raise RuntimeError("formation action occurred after P1")
                if action == "read_operation_status" and not saw_attempt:
                    raise RuntimeError("readback occurred before actual attempt")
                raw = service.call(action, message.get("args", {}))
                action_count += 1
                saw_attempt |= action == "submit_operation"
                process.stdin.write(
                    json.dumps({"type": "response", "raw": raw}, sort_keys=True)
                    + "\n"
                )
                process.stdin.flush()
            elif message_type == "result":
                notes = list(message.get("notes", []))
                break
            else:
                raise RuntimeError(f"unknown worker message: {message_type}")
        process.stdin.close()
        return_code = process.wait(timeout=10)
        stderr = process.stderr.read() if process.stderr is not None else ""
        process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        if return_code != 0:
            raise RuntimeError(f"{method} worker failed: {stderr}")
    if set(predictions) != {"P0", "P1"}:
        raise RuntimeError(f"{method} did not freeze both predictions")
    return {
        "predictions": predictions,
        "truth": truths,
        "outcomes": service.audit_outcomes(),
        "cost": service.cost_totals(),
        "trace": service.public_audit_log(),
        "notes": notes,
    }


def evaluate() -> dict[str, Any]:
    fixture, oracle = load()
    if fixture["fixture_id"] != oracle["fixture_id"]:
        raise RuntimeError("fixture/oracle identity mismatch")
    oracle_hash_before = sha256(ORACLE)
    pair_lookup = {pair["pair_ref"]: pair for pair in fixture["pairs"]}
    method_rows: dict[str, list[dict[str, Any]]] = {key: [] for key in WORKERS}
    for method, worker_path in WORKERS.items():
        for world in fixture["worlds"]:
            packet = expanded_public(fixture, world)
            service = PrimitiveService(
                world["world_ref"],
                packet,
                oracle["base_state"],
                oracle["worlds"][world["world_ref"]],
                world["allowed_actions"],
            )
            row = run_worker(method, worker_path, service, packet)
            pair = pair_lookup[world["pair_ref"]]
            method_rows[method].append(
                {
                    "world_ref": world["world_ref"],
                    "pair_ref": world["pair_ref"],
                    "pair_class": pair["pair_class"],
                    "split": world["split"],
                    **row,
                }
            )
    oracle_hash_after = sha256(ORACLE)
    return {
        "fixture_id": fixture["fixture_id"],
        "evidence_state": "LOCAL_SYNTHETIC_DISCRIMINATOR_PILOT",
        "world_count": len(fixture["worlds"]),
        "pair_count": len(fixture["pairs"]),
        "pair_class_counts": {
            pair_class: sum(
                pair["pair_class"] == pair_class for pair in fixture["pairs"]
            )
            for pair_class in ("PASSIVE", "ACTIVE", "HARD")
        },
        "oracle_sha256_before": oracle_hash_before,
        "oracle_sha256_after": oracle_hash_after,
        "oracle_unchanged": oracle_hash_before == oracle_hash_after,
        "worker_sha256": {method: sha256(path) for method, path in WORKERS.items()},
        "independent_worker_sources": len(
            {sha256(path) for path in WORKERS.values()}
        )
        == len(WORKERS),
        "methods": {
            method: {
                "score": score_method(rows),
                "worlds": rows,
            }
            for method, rows in method_rows.items()
        },
        "cannot_support": [
            "reality frequency or production reliability",
            "formal G4 claim promotion",
            "general strong-center superiority or inferiority",
            "necessity of a new protocol or derived Capability Claim",
            "unbounded mathematical impossibility beyond the finite action horizon",
        ],
    }


def compact(report: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(report)
    for method in result["methods"].values():
        method.pop("worlds", None)
    return result


def self_test(report: dict[str, Any]) -> None:
    assert report["world_count"] == 14
    assert report["pair_count"] == 7
    assert report["pair_class_counts"] == {"PASSIVE": 1, "ACTIVE": 4, "HARD": 2}
    assert report["oracle_unchanged"]
    assert report["independent_worker_sources"]
    assert len(report["worker_sha256"]) == 4
    for method in report["methods"].values():
        score = method["score"]
        assert set(score["by_pair_class"]) == {"ACTIVE", "HARD", "PASSIVE"}
        assert score["P1"]["success_confusion"]["abstention_rate"] is not None
        assert score["P1"]["resolution_confusion"]["false_reliance_all"] is not None


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
