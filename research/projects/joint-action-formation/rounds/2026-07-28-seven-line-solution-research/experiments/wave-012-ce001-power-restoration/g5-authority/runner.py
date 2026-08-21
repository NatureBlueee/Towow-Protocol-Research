#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce001_g5.common import sha256, write_json
from ce001_g5.harness import run_experiment
from ce001_g5.model import build_operation


def build_manifest(results: dict, artifact_paths: dict[str, Path]) -> dict:
    source_paths = sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and "artifacts" not in path.parts
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    return {
        "schema": "ce001.g5.run-manifest.v1",
        "result_status": results["status"],
        "artifacts": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path.read_bytes()),
            }
            for name, path in artifact_paths.items()
        },
        "source_files": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path.read_bytes()),
            }
            for path in source_paths
        ],
        "product_execution_truth": results["engine_status"],
        "formal_state_changes": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    results, trace = run_experiment(ROOT, artifacts / "runtime" / "current")
    results_path = artifacts / "results.json"
    trace_path = artifacts / "raw-trace.jsonl"
    input_path = artifacts / "input.json"
    key_path = artifacts / "public-keys.json"
    process_path = artifacts / "process-inventory.json"
    input_record = {
        "schema": "ce001.g5.frozen-run-input.v1",
        "operations": {
            stratum: build_operation(stratum)
            for stratum in ("U", "D", "P")
        },
        "trusted_topology_closures": results["topology_closures"],
        "target_gate_attack_ids": [
            row["attack"] for row in results["target_native_gate_attacks"]["rows"]
        ],
        "migration_runtime_scope": "SHARED_DURABLE_STORE_PROCESS_RESTART",
        "cross_failure_domain_migration": "NOT_RUN",
    }
    write_json(results_path, results)
    trace_path.write_text(
        "".join(
            json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
            for item in trace
        ),
        encoding="utf-8",
    )
    write_json(input_path, input_record)
    write_json(
        key_path,
        {
            "schema": "ce001.g5.public-key-evidence.v1",
            "note": "PUBLIC_KEYS_AND_FINGERPRINTS_ONLY_NO_PRIVATE_KEYS",
            "keys": results["public_keys"],
        },
    )
    write_json(
        process_path,
        {
            "schema": "ce001.g5.process-inventory.v1",
            "processes": results["process_inventory"],
            "migration": {
                "source_runtime_pid": results["migration"]["source_runtime_pid"],
                "target_runtime_pid": results["migration"]["target_runtime_pid"],
                "old_source_restarted_pid": results["migration"][
                    "old_source_restarted_pid"
                ],
                "distinct_runtime_processes": results["migration"][
                    "distinct_runtime_processes"
                ],
            },
        },
    )
    write_json(
        artifacts / "manifest.json",
        build_manifest(
            results,
            {
                "input": input_path,
                "public_keys": key_path,
                "process_inventory": process_path,
                "raw_trace": trace_path,
                "results": results_path,
            },
        ),
    )
    print(results["status"])
    print(json.dumps(results["metrics"], ensure_ascii=False, sort_keys=True))
    if args.check and results["status"] != "COMPLETE_LOCAL_COMPONENT_MODEL":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
