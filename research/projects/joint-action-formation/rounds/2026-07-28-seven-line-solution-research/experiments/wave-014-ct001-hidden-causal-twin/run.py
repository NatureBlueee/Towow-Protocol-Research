#!/usr/bin/env python3
"""Run the hidden CT-001 causal twin and freeze its actual artifacts."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import pathlib
import sys
import tempfile
import uuid
from typing import Any

from evaluator import evaluate_causal, evaluate_legacy
from runtime import (
    MODE_EXTERNAL,
    MODE_FORWARD,
    a4_worker,
    alpha_shape,
    canonical_bytes,
    helper_worker,
    router_worker,
    sha256_value,
    target_worker,
    verify_signed,
)


HERE = pathlib.Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
FORBIDDEN_ARM_LABELS = (
    "W_G",
    "W_F",
    MODE_FORWARD,
    MODE_EXTERNAL,
    "HELPER",
    "hidden-causal-twin",
    "causal_twin",
)


def _digits(length: int) -> str:
    value = str(uuid.uuid4().int)
    return (value * ((length // len(value)) + 1))[:length]


def _queue(ctx: multiprocessing.context.BaseContext) -> Any:
    return ctx.Queue()


def _start_with_opaque_a4_view(
    process: multiprocessing.Process, opaque_cwd: str
) -> None:
    original_argv = list(sys.argv)
    original_cwd = os.getcwd()
    try:
        sys.argv = [pathlib.Path(sys.argv[0]).name, "--opaque-a4-child"]
        os.chdir(opaque_cwd)
        process.start()
    finally:
        os.chdir(original_cwd)
        sys.argv = original_argv


def _assert_identity_set(ready: dict[str, dict[str, Any]]) -> None:
    if set(ready) != {"A4", "ROUTER", "HELPER", "TARGET"}:
        raise RuntimeError("worker readiness set incomplete")
    for field in ("actual_pid", "public_key_hex", "state_source_id"):
        values = [ready[worker]["start_receipt"][field] for worker in ready]
        if len(set(values)) != 4:
            raise RuntimeError(f"worker identity collision: {field}")
    for worker, payload in ready.items():
        receipt = payload["start_receipt"]
        if not verify_signed(receipt, receipt["public_key_hex"]):
            raise RuntimeError(f"{worker} start receipt invalid")


def run_world(
    *,
    mode: str,
    pair_id: str,
    signed_router_lie: bool = False,
) -> dict[str, Any]:
    if mode not in {MODE_FORWARD, MODE_EXTERNAL}:
        raise ValueError("unsupported hidden mode")
    ctx = multiprocessing.get_context("spawn")
    ready_queue = _queue(ctx)
    bind_queues = {worker: _queue(ctx) for worker in ("A4", "ROUTER", "HELPER", "TARGET")}
    result_queues = {
        worker: _queue(ctx) for worker in ("A4", "ROUTER", "HELPER", "TARGET")
    }
    arm_router_request = _queue(ctx)
    arm_router_response = _queue(ctx)
    router_target_request = _queue(ctx)
    router_target_response = _queue(ctx)
    helper_target_request = _queue(ctx)
    helper_target_response = _queue(ctx)
    helper_trigger = _queue(ctx)
    helper_router_result = _queue(ctx)

    opaque_process_suffix = _digits(16)
    processes = {
        "ROUTER": ctx.Process(
            target=router_worker,
            name=f"p-{_digits(16)}",
            args=(
                arm_router_request,
                arm_router_response,
                router_target_request,
                router_target_response,
                helper_trigger,
                helper_router_result,
                ready_queue,
                bind_queues["ROUTER"],
                result_queues["ROUTER"],
            ),
        ),
        "HELPER": ctx.Process(
            target=helper_worker,
            name=f"p-{_digits(16)}",
            args=(
                helper_target_request,
                helper_target_response,
                helper_trigger,
                helper_router_result,
                ready_queue,
                bind_queues["HELPER"],
                result_queues["HELPER"],
            ),
        ),
        "TARGET": ctx.Process(
            target=target_worker,
            name=f"p-{_digits(16)}",
            args=(
                router_target_request,
                router_target_response,
                helper_target_request,
                helper_target_response,
                ready_queue,
                bind_queues["TARGET"],
                result_queues["TARGET"],
            ),
        ),
        "A4": ctx.Process(
            target=a4_worker,
            name=f"p-{opaque_process_suffix}",
            args=(
                arm_router_request,
                arm_router_response,
                ready_queue,
                bind_queues["A4"],
                result_queues["A4"],
            ),
        ),
    }
    processes["ROUTER"].start()
    processes["HELPER"].start()
    processes["TARGET"].start()
    with tempfile.TemporaryDirectory(prefix="") as opaque_cwd:
        _start_with_opaque_a4_view(processes["A4"], opaque_cwd)
        ready: dict[str, dict[str, Any]] = {}
        for _ in range(4):
            item = ready_queue.get(timeout=20)
            ready[item["worker_id"]] = item
        _assert_identity_set(ready)

        run_binding = _digits(32)
        object_id = "circuit-17"
        operation_id = "energize-window-09"
        window_token = _digits(32)
        plan_id = _digits(32)
        public_manifest = {
            "run_binding": run_binding,
            "object_id": object_id,
            "operation_id": operation_id,
            "requested_state": {"energized": True},
        }
        actor_registry = {
            actor: ready[actor]["start_receipt"]["public_key_hex"]
            for actor in ("A4", "HELPER")
        }
        actor_process_ids = {
            actor: ready[actor]["start_receipt"]["actual_pid"]
            for actor in ("A4", "HELPER")
        }

        # Bind the private plan before releasing A4.
        bind_queues["HELPER"].put(
            {
                "mode": mode,
                "plan_id": plan_id,
                "window_token": window_token,
                **public_manifest,
            }
        )
        bind_queues["ROUTER"].put(
            {
                "mode": mode,
                "signed_lie": signed_router_lie,
                "window_token": window_token,
                "a4_public_key_hex": actor_registry["A4"],
                **public_manifest,
            }
        )
        bind_queues["TARGET"].put(
            {
                "actor_registry": actor_registry,
                "actor_process_ids": actor_process_ids,
                **public_manifest,
            }
        )
        bind_queues["A4"].put(public_manifest)

        results = {
            worker: result_queues[worker].get(timeout=30)
            for worker in ("A4", "ROUTER", "HELPER", "TARGET")
        }
        for process in processes.values():
            process.join(timeout=20)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
        exit_codes = {worker: process.exitcode for worker, process in processes.items()}
        if set(exit_codes.values()) != {0}:
            raise RuntimeError(f"child process failure: {exit_codes}")

    arm_view = {
        "public_manifest": public_manifest,
        "transcript": results["A4"]["transcript"],
    }
    arm_view_bytes = canonical_bytes(arm_view).decode("utf-8", errors="replace")
    forbidden_hits = [
        label for label in FORBIDDEN_ARM_LABELS if label.lower() in arm_view_bytes.lower()
    ]
    pre_decision = results["A4"]["transcript"]["events"][
        : results["A4"]["transcript"]["pre_decision_event_count"]
    ]
    bundle = {
        "contract_id": "CT-001",
        "pair_id": pair_id,
        "public_manifest": public_manifest,
        "service_manifest": {
            worker: ready[worker]["start_receipt"]
            for worker in ("A4", "ROUTER", "HELPER", "TARGET")
        },
        "arm_view": arm_view,
        "arm_native": {
            "request_envelope": results["A4"]["request_envelope"],
            "pre_decision_alpha_shape": alpha_shape(pre_decision),
            "forbidden_label_hits": forbidden_hits,
        },
        "router_native": results["ROUTER"],
        "helper_native": results["HELPER"],
        "target_native": results["TARGET"],
        "controller_private": {
            "hidden_mode": mode,
            "plan_id": plan_id,
            "window_token_sha256": sha256_value(window_token),
            "helper_plan_frozen_before_a4_release": True,
            "signed_router_lie": signed_router_lie,
        },
        "runtime": {
            "multiprocessing_start_method": ctx.get_start_method(),
            "process_exit_codes": exit_codes,
        },
    }
    unsigned = dict(bundle)
    bundle["bundle_sha256"] = sha256_value(unsigned)
    return bundle


def run_pair(
    artifacts_dir: pathlib.Path = ARTIFACTS,
    *,
    signed_router_lie_in_external_world: bool = False,
) -> pathlib.Path:
    pair_id = f"p-{_digits(20)}"
    good = run_world(mode=MODE_FORWARD, pair_id=pair_id)
    external = run_world(
        mode=MODE_EXTERNAL,
        pair_id=pair_id,
        signed_router_lie=signed_router_lie_in_external_world,
    )
    if (
        good["target_native"]["state_projection_sha256"]
        != external["target_native"]["state_projection_sha256"]
    ):
        raise RuntimeError("causal twin target projections diverged")
    if (
        good["arm_native"]["pre_decision_alpha_shape"]
        != external["arm_native"]["pre_decision_alpha_shape"]
    ):
        raise RuntimeError("causal twin pre-decision alpha shapes diverged")
    if good["arm_native"]["forbidden_label_hits"] or external["arm_native"][
        "forbidden_label_hits"
    ]:
        raise RuntimeError("hidden label leaked into A4 view")

    pair = {
        "contract_id": "CT-001",
        "pair_id": pair_id,
        "worlds": {"W_G": good, "W_F": external},
        "state_projection_hash_equal": True,
        "pre_decision_alpha_shape_equal": True,
        "legacy_evaluations": {
            "W_G": evaluate_legacy(good),
            "W_F": evaluate_legacy(external),
        },
        "causal_evaluations": {
            "W_G": evaluate_causal(good),
            "W_F": evaluate_causal(external),
        },
    }
    pair["pair_sha256"] = sha256_value(pair)
    output_dir = artifacts_dir / f"ct001-{pair_id}"
    output_dir.mkdir(parents=True, exist_ok=False)
    output_path = output_dir / "causal-twin.json"
    output_path.write_text(
        json.dumps(pair, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts-dir", type=pathlib.Path, default=ARTIFACTS)
    args = parser.parse_args()
    path = run_pair(args.artifacts_dir)
    print(json.dumps({"artifact": str(path)}, sort_keys=True))


if __name__ == "__main__":
    main()

