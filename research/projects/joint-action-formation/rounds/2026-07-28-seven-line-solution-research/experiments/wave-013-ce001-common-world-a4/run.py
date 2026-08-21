#!/usr/bin/env python3
"""Run the E1/E5 A4 vertical slice and freeze auditable bundles."""

from __future__ import annotations

import argparse
import copy
import json
import multiprocessing
import os
import pathlib
import sys
import tempfile
import time
import uuid
from typing import Any, Mapping

from arm_a4 import arm_process
from services import (
    OWNER_IDS,
    canonical_bytes,
    owner_worker,
    sha256_value,
    target_worker,
)
from world import case_definition, make_episode_manifest, registry_projection


HERE = pathlib.Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"


def _bind(endpoint: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    endpoint["control_queue"].put({"command": "BIND", "manifest": dict(manifest)})
    response = endpoint["control_response_queue"].get(timeout=10)
    if response.get("status") != "BOUND":
        raise RuntimeError("service did not bind manifest")


def _freeze(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    endpoint["control_queue"].put({"command": "FREEZE"})
    return endpoint["control_response_queue"].get(timeout=20)


def _endpoint(ctx: multiprocessing.context.BaseContext) -> dict[str, Any]:
    return {
        "request_queue": ctx.Queue(),
        "response_queue": ctx.Queue(),
        "control_queue": ctx.Queue(),
        "control_response_queue": ctx.Queue(),
    }


def _public_endpoint(endpoint: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "request_queue": endpoint["request_queue"],
        "response_queue": endpoint["response_queue"],
    }


def _scan_for_canary(value: Any, canary: str) -> bool:
    return canary in canonical_bytes(value).decode("utf-8", errors="replace")


def _source_ref(owner_id: str, record: Mapping[str, Any]) -> str:
    digest = record.get("response_sha256") or record.get("event_sha256")
    prefix = "target" if owner_id == "TARGET" else f"owner:{owner_id}"
    return f"{prefix}:{digest}"


def _component_fragments(
    manifest: Mapping[str, Any],
    owner_logs: Mapping[str, Mapping[str, Any]],
    target_log: Mapping[str, Any],
) -> dict[str, Any]:
    owners = {owner: log["entries"] for owner, log in owner_logs.items()}
    target_entries = target_log["entries"]

    def owner_kind(owner: str, kind: str) -> list[dict[str, Any]]:
        return [
            record
            for record in owners.get(owner, [])
            if record.get("payload", {}).get("kind") == kind
        ]

    if manifest["case_id"] == "E1-EXTANT-MULTI-OWNER":
        selected = {
            "G1": owner_kind("O_R", "DISCOVERY"),
            "G2": owner_kind("O_R", "AUTHORITY"),
            "G3": sum(
                (owner_kind(owner, "AUTHORITY") for owner in ("O_V", "O_R", "O_S")),
                [],
            ),
            "G4": owner_kind("O_Q", "ACCEPTANCE") + owner_kind("O_V", "ACCEPTANCE"),
            "G5": [r for r in target_entries if r.get("kind") == "OCCURRENCE"],
            "G6": list(target_entries),
            "G7": owner_kind("O_P", "FINALITY"),
        }
    else:
        refusal = owner_kind("O_V", "AUTHORITY")
        selected = {
            "G1": refusal,
            "G2": refusal,
            "G3": refusal,
            "G4": refusal,
            "G5": refusal,
            "G6": refusal,
            "G7": refusal,
        }
    fragments: dict[str, Any] = {}
    for namespace, records in selected.items():
        refs = []
        for record in records:
            owner_id = record.get("owner_id", "TARGET")
            refs.append(_source_ref(owner_id, record))
        fragments[namespace] = {
            "namespace": namespace,
            "disposition": (
                "OBSERVED_LINE_LOCAL"
                if records
                else "NO_NATIVE_EVENT_IN_CASE_BRANCH"
            ),
            "run_id": manifest["run_id"],
            "world_root": manifest["world_root"],
            "case_id": manifest["case_id"],
            "manifest_sha256": manifest["manifest_sha256"],
            "q_version": manifest["q_version"],
            "object_id": manifest["object_id"],
            "operation_id": manifest["operation_id"],
            "source_log_refs": refs,
            "source_artifact_sha256": sha256_value(records),
            "evidence_boundary": "LOCAL_SYNTHETIC_COMMON_WORLD_COMPONENT_ONLY",
        }
    return fragments


def run_case(
    case_id: str,
    artifacts_dir: pathlib.Path = ARTIFACTS,
    *,
    duplicate_execute_probe: bool = False,
    feasible_alternatives_override: list[str] | None = None,
) -> tuple[pathlib.Path, pathlib.Path]:
    started = time.monotonic()
    ctx = multiprocessing.get_context("spawn")
    # The evaluator-private bundle retains case_id, but every identifier that the
    # arm can observe must be opaque.  A semantic run id would be an answer key
    # even if case_id itself were removed from the arm manifest.
    # Digits-only avoids accidental human-readable substrings such as "e1" or
    # "e5" appearing in otherwise random process/run names.
    opaque_run_token = f"{uuid.uuid4().int % (10 ** 32):032d}"
    run_id = f"ce001-run-{opaque_run_token[:20]}"
    private_world = case_definition(
        case_id,
        run_id,
        feasible_alternatives_override=feasible_alternatives_override,
    )

    ready_queue = ctx.Queue()
    owner_endpoints = {owner: _endpoint(ctx) for owner in OWNER_IDS}
    head_update_queues = {owner: ctx.Queue() for owner in OWNER_IDS}
    owner_processes: dict[str, multiprocessing.Process] = {}
    for owner_id in OWNER_IDS:
        endpoint = owner_endpoints[owner_id]
        process = ctx.Process(
            target=owner_worker,
            name=f"ce001-{owner_id}",
            args=(
                owner_id,
                private_world["owner_shards"][owner_id],
                endpoint["request_queue"],
                endpoint["response_queue"],
                endpoint["control_queue"],
                endpoint["control_response_queue"],
                head_update_queues[owner_id],
                ready_queue,
            ),
        )
        process.start()
        owner_processes[owner_id] = process
    owner_ready: dict[str, dict[str, Any]] = {}
    for _ in OWNER_IDS:
        ready = ready_queue.get(timeout=15)
        owner_ready[ready["service_id"]] = ready
    if set(owner_ready) != set(OWNER_IDS):
        raise RuntimeError("owner readiness set incomplete")

    # Fail closed if process-private identities accidentally alias.
    for key in ("actual_pid", "public_key_hex", "state_source_id", "state_head_at_start"):
        values = [entry[key] for entry in owner_ready.values()]
        if len(set(values)) != len(values):
            raise RuntimeError(f"owner service identity collision: {key}")

    target_endpoint = _endpoint(ctx)
    target_process = ctx.Process(
        target=target_worker,
        name="ce001-TARGET",
        args=(
            owner_ready,
            head_update_queues,
            target_endpoint["request_queue"],
            target_endpoint["response_queue"],
            target_endpoint["control_queue"],
            target_endpoint["control_response_queue"],
            ready_queue,
        ),
    )
    target_process.start()
    target_ready = ready_queue.get(timeout=15)
    if target_ready.get("service_id") != "TARGET":
        raise RuntimeError("target readiness missing")

    owner_registry_snapshot = {
        owner: registry_projection(entry) for owner, entry in owner_ready.items()
    }
    target_registry_snapshot = registry_projection(target_ready)
    manifest = make_episode_manifest(
        case_id=case_id,
        run_id=run_id,
        world_root=private_world["world_root"],
        owner_registry_sha256=sha256_value(owner_registry_snapshot),
        target_registry_sha256=sha256_value(target_registry_snapshot),
    )
    for endpoint in owner_endpoints.values():
        _bind(endpoint, manifest)
    _bind(target_endpoint, manifest)

    result_queue = ctx.Queue()
    arm_manifest = {
        key: value
        for key, value in manifest.items()
        if key not in {"case_id", "manifest_sha256"}
    }
    arm_manifest["episode_instance_id"] = sha256_value(
        {
            "run_id": manifest["run_id"],
            "arm_binding_token": manifest["arm_binding_token"],
            "purpose": "OPAQUE_ARM_EPISODE_INSTANCE",
        }
    )
    with tempfile.TemporaryDirectory(prefix=f"ce001-arm-{opaque_run_token[20:]}-") as arm_cwd:
        start_payload = {
            "episode_manifest": arm_manifest,
            "owner_request_endpoint": sorted(OWNER_IDS),
            "target_request_endpoint": "TARGET",
            "runtime_policy": {
                "cwd": arm_cwd,
                "minimal_environment": {
                    "LANG": "C.UTF-8",
                    "PATH": "/usr/bin:/bin",
                    "PYTHONHASHSEED": "0",
                },
                "network_allowlist": [],
                "file_allowlist": [],
                "duplicate_execute_probe": duplicate_execute_probe,
                "enforcement_boundary": (
                    "COOPERATIVE_CHILD_POLICY; HOSTILE_SAME_USER_FILESYSTEM_AND_NETWORK_NOT_COVERED"
                ),
            },
        }
        arm = ctx.Process(
            target=arm_process,
            name=f"ce001-A4-{opaque_run_token[:12]}",
            args=(
                start_payload,
                {
                    owner: _public_endpoint(endpoint)
                    for owner, endpoint in owner_endpoints.items()
                },
                _public_endpoint(target_endpoint),
                result_queue,
            ),
        )
        # multiprocessing.spawn copies parent sys.argv into the child before
        # importing the target module.  Sanitise it around spawn so a CLI
        # `--case E1...` argument cannot become an import-time answer channel.
        parent_argv = list(sys.argv)
        sys.argv[:] = [sys.argv[0], "--opaque-arm-child"]
        try:
            arm.start()
        finally:
            sys.argv[:] = parent_argv
        transcript = result_queue.get(timeout=30)
        arm.join(timeout=10)
        if arm.exitcode != 0:
            raise RuntimeError(f"A4 child exit code {arm.exitcode}")
        cwd_files = sorted(str(p.relative_to(arm_cwd)) for p in pathlib.Path(arm_cwd).rglob("*"))

    owner_logs = {
        owner: _freeze(owner_endpoints[owner]) for owner in OWNER_IDS
    }
    target_log = _freeze(target_endpoint)
    for process in owner_processes.values():
        process.join(timeout=10)
    target_process.join(timeout=10)
    exit_codes = {
        "A4": arm.exitcode,
        **{owner: process.exitcode for owner, process in owner_processes.items()},
        "TARGET": target_process.exitcode,
    }
    if set(exit_codes.values()) != {0}:
        raise RuntimeError(f"non-zero service exit: {exit_codes}")

    service_owners = copy.deepcopy(owner_ready)
    for owner in OWNER_IDS:
        service_owners[owner]["current_owner_state_head"] = owner_logs[owner]["state_head"]
        service_owners[owner]["current_owner_state_epoch"] = owner_logs[owner][
            "current_owner_state_epoch"
        ]
    service_target = copy.deepcopy(target_ready)
    service_target["current_state_head"] = target_log["state_head"]
    service_manifest = {
        "schema": "CE001_SERVICE_MANIFEST_V1",
        "owner_registry_snapshot": owner_registry_snapshot,
        "target_registry_snapshot": target_registry_snapshot,
        "owners": service_owners,
        "target": service_target,
    }

    canary = private_world["private_canary"]
    request_view = transcript["requests"] + transcript["target_requests"]
    scan_results = {
        "start_payload": _scan_for_canary(start_payload, canary),
        "arm_transcript": _scan_for_canary(transcript, canary),
        "owner_requests": _scan_for_canary(request_view, canary),
        "arm_cwd": any(canary in path for path in cwd_files),
        "arm_environment": any(
            canary in str(value)
            for value in start_payload["runtime_policy"]["minimal_environment"].values()
        ),
    }
    visibility_observation = transcript["events"][0]
    visibility_receipt = {
        "actual_pid": transcript["process_id"],
        "process_start_method": "spawn",
        "start_payload": start_payload,
        "start_payload_bytes": canonical_bytes(start_payload).decode("utf-8"),
        "start_payload_sha256": sha256_value(start_payload),
        "field_list": sorted(start_payload),
        "private_canary_sha256": private_world["private_case_receipt"][
            "private_canary_sha256"
        ],
        "private_canary_absent": not any(scan_results.values()),
        "scan_results": {
            "cwd": scan_results["arm_cwd"],
            "environment": scan_results["arm_environment"],
            "start_payload": scan_results["start_payload"],
            "arm_transcript": scan_results["arm_transcript"],
            "owner_requests": scan_results["owner_requests"],
        },
        "cwd_files": cwd_files,
        "inherited_file_descriptor_inventory": visibility_observation[
            "inherited_file_descriptors"
        ],
        "network_allowlist": [],
        "file_allowlist": [],
        "minimal_environment_keys": sorted(
            start_payload["runtime_policy"]["minimal_environment"]
        ),
        "isolation_boundary": (
            "SPAWN_AND_COOPERATIVE_IPC_ONLY; HOSTILE_SAME_OS_USER_NOT_COVERED"
        ),
    }
    visibility_receipt["receipt_sha256"] = sha256_value(visibility_receipt)
    if not visibility_receipt["private_canary_absent"]:
        raise RuntimeError("private canary visible to arm")

    fragments = _component_fragments(manifest, owner_logs, target_log)
    runtime_log = {
        "schema": "CE001_RUNTIME_LOG_V1",
        "arm_visibility_receipt": visibility_receipt,
        "process_exit_codes": exit_codes,
        "logs_frozen": True,
        "native_logs_frozen_before_service_exit": True,
        "all_processes_exited_before_bundle_freeze": True,
        "native_logs_frozen": True,
        "bundle_frozen_after_process_exit": True,
        "controller_seal_boundary": (
            "SAME_USER_RUN_SEAL_DETECTS_ORDINARY_REPLACEMENT; "
            "COORDINATED_SAME_PERMISSION_REWRITE_NOT_COVERED"
        ),
    }
    bundle = {
        "episode_manifest": manifest,
        "service_manifest": service_manifest,
        "public_case": private_world["public_case"],
        "private_case_receipt": private_world["private_case_receipt"],
        "private_case_reveal": private_world["private_case_reveal"],
        "arm_transcript": transcript,
        "owner_native_logs": owner_logs,
        "target_native_log": target_log,
        "runtime_log": runtime_log,
        "component_fragments": fragments,
        "cost_log": {
            "wall_seconds": round(time.monotonic() - started, 6),
            "child_process_count": 8,
            "owner_request_count": len(transcript["requests"]),
            "target_native_record_count": len(target_log["entries"]),
            "monetary_cost": 0,
            "boundary": "LOCAL_SYNTHETIC_RUNTIME_MEASUREMENT",
        },
    }
    bundle["bundle_sha256"] = sha256_value(bundle)

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    run_dir = artifacts_dir / run_id
    run_dir.mkdir(parents=False, exist_ok=False)
    bundle_path = run_dir / "bundle.json"
    seal_path = run_dir / "run-seal.json"
    bundle_path.write_bytes(canonical_bytes(bundle) + b"\n")
    terminal_heads = {
        **{owner: owner_logs[owner]["state_head"] for owner in OWNER_IDS},
        "TARGET": target_log["state_head"],
    }
    freeze_receipt_hashes = {
        **{
            owner: owner_logs[owner]["freeze_receipt"]["receipt_sha256"]
            for owner in OWNER_IDS
        },
        "TARGET": target_log["freeze_receipt"]["receipt_sha256"],
    }
    seal = {
        "schema": "CE001_LOCAL_RUN_SEAL_V1",
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "bundle_file": bundle_path.name,
        "bundle_sha256": bundle["bundle_sha256"],
        "native_log_terminal_heads": terminal_heads,
        "freeze_receipt_sha256s": freeze_receipt_hashes,
        "process_exit_codes": exit_codes,
        "threat_boundary": "SAME_USER_WHOLE_RUN_REWRITE_NOT_COVERED",
    }
    seal["seal_sha256"] = sha256_value(seal)
    seal_path.write_bytes(canonical_bytes(seal) + b"\n")
    case_slug = case_id.lower().replace("_", "-")
    latest_path = artifacts_dir / f"latest-{case_slug}.json"
    latest_temp_path = artifacts_dir / f".latest-{case_slug}-{run_id}.tmp"
    latest = {
        "schema": "CE001_LATEST_RUN_POINTER_V1",
        "case_id": case_id,
        "run_id": run_id,
        "run_dir": run_dir.name,
        "bundle_file": str(bundle_path.relative_to(artifacts_dir)),
        "seal_file": str(seal_path.relative_to(artifacts_dir)),
        "manifest_sha256": manifest["manifest_sha256"],
        "bundle_sha256": bundle["bundle_sha256"],
        "seal_sha256": seal["seal_sha256"],
    }
    latest_temp_path.write_bytes(canonical_bytes(latest) + b"\n")
    os.replace(latest_temp_path, latest_path)
    return bundle_path, seal_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--case",
        choices=("E1-EXTANT-MULTI-OWNER", "E5-IMPOSSIBLE-REFUSAL", "both"),
        default="both",
    )
    parser.add_argument("--artifacts-dir", type=pathlib.Path, default=ARTIFACTS)
    args = parser.parse_args()
    cases = (
        ("E1-EXTANT-MULTI-OWNER", "E5-IMPOSSIBLE-REFUSAL")
        if args.case == "both"
        else (args.case,)
    )
    for case_id in cases:
        bundle, seal = run_case(case_id, args.artifacts_dir)
        print(json.dumps({"case_id": case_id, "bundle": str(bundle), "seal": str(seal)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
