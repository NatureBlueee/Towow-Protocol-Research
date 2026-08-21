#!/usr/bin/env python3
"""Parent runner: owns registry identity, broker state, and raw operation log."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from broker import EvidenceBroker, reconstruct_cost


BASE_DIR = Path(__file__).resolve().parent
WORKER = BASE_DIR / "candidate_worker.py"
BASELINE_COST_MODEL = {
    "operation_cost": 0.1,
    "byte_cost": 0.00005,
    "latency_ms_cost": 0.01,
    "disclosure_unit_cost": 1.0,
    "retry_cost": 0.5,
}
DEFAULT_REGISTRY = {
    "IMPL_DECLARATION": {
        "worker_strategy": "DECLARATION",
        "display_label": "DECLARATION",
    },
    "IMPL_LATEST_PROBE": {
        "worker_strategy": "LATEST_PROBE",
        "display_label": "LATEST_PROBE",
    },
    "IMPL_RECEIPT_WINDOW": {
        "worker_strategy": "RECEIPT_WINDOW",
        "display_label": "RECEIPT_WINDOW",
    },
    "IMPL_SLA_RECOVERY": {
        "worker_strategy": "SLA_RECOVERY",
        "display_label": "SLA_RECOVERY",
    },
}


def run_worker(
    database: dict[str, Any],
    world_token: str,
    registry_owner: str,
    worker_strategy: str,
    display_label: str,
) -> dict[str, Any]:
    broker = EvidenceBroker(
        database, world_token, registry_owner, display_label
    )
    process = subprocess.Popen(
        [sys.executable, "-B", str(WORKER), worker_strategy],
        cwd=BASE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    decision: dict[str, Any] | None = None
    protocol_error: str | None = None
    for raw_line in process.stdout:
        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError as error:
            protocol_error = f"worker emitted non-JSON: {error}"
            break
        message_type = message.get("type")
        if message_type == "decision":
            value = message.get("decision")
            if not isinstance(value, dict):
                protocol_error = "worker decision must be an object"
            else:
                decision = value
            break
        if message_type != "rpc":
            protocol_error = f"unknown worker message type: {message_type}"
            break
        response = {"id": message.get("id")}
        try:
            arguments = message.get("arguments", {})
            if not isinstance(arguments, dict):
                raise TypeError("RPC arguments must be an object")
            response.update({
                "ok": True,
                "result": broker.handle(
                    str(message.get("method")), arguments
                ),
            })
        except Exception as error:  # broker boundary returns typed refusal
            response.update({
                "ok": False,
                "error": f"{type(error).__name__}: {error}",
            })
        process.stdin.write(
            json.dumps(response, sort_keys=True) + "\n"
        )
        process.stdin.flush()
    process.stdin.close()
    try:
        return_code = process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()
        raise RuntimeError("candidate worker timed out")
    stderr = process.stderr.read()
    process.stdout.close()
    process.stderr.close()
    if protocol_error:
        raise RuntimeError(protocol_error)
    if return_code != 0:
        raise RuntimeError(
            f"candidate worker failed ({return_code}): {stderr.strip()}"
        )
    if decision is None:
        raise RuntimeError("candidate worker exited without decision")
    operation_log = broker.snapshot_operation_log()
    return {
        "world_token": world_token,
        "implementation_id": registry_owner,
        "display_label": display_label,
        "worker_strategy": worker_strategy,
        "candidate_claimed_implementation_id": (
            decision.get("implementation_id")
        ),
        "decision": decision,
        "operation_log": operation_log,
        "cost": reconstruct_cost(
            operation_log, BASELINE_COST_MODEL
        ),
    }


def run_candidates(
    database: dict[str, Any],
    registry: dict[str, dict[str, str]] | None = None,
    *,
    world_tokens: list[str] | None = None,
) -> list[dict[str, Any]]:
    selected_registry = registry or DEFAULT_REGISTRY
    selected_worlds = (
        sorted(database["worlds"])
        if world_tokens is None
        else world_tokens
    )
    rows = []
    for world_token in selected_worlds:
        for owner, registration in selected_registry.items():
            rows.append(run_worker(
                database,
                world_token,
                owner,
                registration["worker_strategy"],
                registration["display_label"],
            ))
    return rows
