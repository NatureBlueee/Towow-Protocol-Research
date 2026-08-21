#!/usr/bin/env python3
"""Run every frozen G2 scenario twice and preserve exact and semantic evidence."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from g2_relation import canonical_bytes, digest, run_scenario, semantic_projection


ROOT = Path(__file__).resolve().parent


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    scenarios = []
    fixture_paths = [ROOT / "fixtures" / name for name in ("e2.json", "e0.json")]
    for path in fixture_paths:
        scenarios.extend(json.loads(path.read_text(encoding="utf-8")))

    runs: list[list[dict[str, Any]]] = []
    for run_number in (1, 2):
        run_id = f"rerun-{run_number}"
        runs.append([run_scenario(scenario, run_id=run_id) for scenario in scenarios])

    semantic_runs = [
        [semantic_projection(output) for output in outputs]
        for outputs in runs
    ]
    semantic_equal = semantic_runs[0] == semantic_runs[1]
    all_exits = [
        exit_record
        for outputs in runs
        for output in outputs
        for exit_record in output["process_exits"]
    ]
    all_exit_zero = all(record["returncode"] == 0 for record in all_exits)
    manifests = [
        {
            "run_id": output["run_id"],
            "episode_id": output["episode_id"],
            "process_manifests": output["process_manifests"],
            "process_exits": output["process_exits"],
        }
        for outputs in runs
        for output in outputs
    ]
    traces = [
        record
        for outputs in runs
        for output in outputs
        for record in output["trace"]
    ]

    output_dir = ROOT / "outputs"
    output_dir.mkdir(exist_ok=True)
    write_json(output_dir / "rerun-1.json", runs[0])
    write_json(output_dir / "rerun-2.json", runs[1])
    write_json(output_dir / "raw-trace.json", traces)
    write_json(output_dir / "semantic-rerun.json", semantic_runs)
    source_manifest = {
        "runner": {"path": "run.py", "sha256": file_sha256(ROOT / "run.py")},
        "controller": {
            "path": "g2_relation.py",
            "sha256": file_sha256(ROOT / "g2_relation.py"),
        },
        "owner_worker": {
            "path": "owner_worker.py",
            "sha256": file_sha256(ROOT / "owner_worker.py"),
        },
        "platform_worker": {
            "path": "platform_worker.py",
            "sha256": file_sha256(ROOT / "platform_worker.py"),
        },
        "fixtures": [
            {"path": str(path.relative_to(ROOT)), "sha256": file_sha256(path)}
            for path in fixture_paths + [ROOT / "fixtures" / "endpoints.json"]
        ],
        "worker_runtime_manifests": manifests,
        "profile_source_note": (
            "controller and runner did not load profile contents; each worker returned "
            "only its own profile source id/hash in its public manifest; all manifests "
            "declare LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY and no pinned trust root"
        ),
    }
    write_json(output_dir / "process-source-manifest.json", source_manifest)

    receipts = [
        act
        for outputs in runs
        for output in outputs
        for act in output["owner_acts"]
    ] + [
        receipt
        for outputs in runs
        for output in outputs
        if output["path"] == "T5_PLATFORM_DIRECT_BYPASS"
        for receipt in (
            output["bypass_evidence"]["capability_proof"],
            output["bypass_evidence"]["capability_readback"],
        )
    ]
    summary = {
        "runs": 2,
        "scenarios_per_run": len(scenarios),
        "relation_scenarios_per_run": sum(
            scenario["kind"] == "E2_RELATION" for scenario in scenarios
        ),
        "platform_bypasses_per_run": sum(
            scenario["kind"] == "PLATFORM_DIRECT" for scenario in scenarios
        ),
        "signed_receipts": len(receipts),
        "process_instances": len(all_exits),
        "unique_pids": len({record["pid"] for record in all_exits}),
        "unique_key_ids": len(
            {
                process["key_id"]
                for item in manifests
                for process in item["process_manifests"]
            }
        ),
        "trace_records": len(traces),
        "trace_canonical_sha256": digest(traces),
        "semantic_rerun_equal": semantic_equal,
        "semantic_rerun_sha256": digest(semantic_runs),
        "all_process_exit_zero": all_exit_zero,
        "raw_bytes_preserved": all(
            "raw_bytes_b64" in receipt and "signature_b64" in receipt for receipt in receipts
        ),
        "evidence_boundaries": {
            "evidence_origin": "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY",
            "real_owner_identity": "NOT_ESTABLISHED",
            "real_platform_identity": "NOT_ESTABLISHED",
            "authority": "NOT_ESTABLISHED",
            "legal_sufficiency": "NOT_ESTABLISHED",
            "real_owner": "NOT_RUN",
            "effect": "NOT_RUN",
            "acceptance": "NOT_RUN",
            "settlement": "NOT_RUN",
            "g5": "UNVERIFIED",
            "g6": "UNVERIFIED",
        },
        "result": (
            "LOCAL_SYNTHETIC_EPHEMERAL_SELF_KEY_CONFORMANCE_REPRODUCED"
            if semantic_equal and all_exit_zero
            else "RUNNER_RED"
        ),
    }
    summary["summary_canonical_sha256"] = sha256(canonical_bytes(summary)).hexdigest()
    write_json(output_dir / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0 if semantic_equal and all_exit_zero else 1


if __name__ == "__main__":
    raise SystemExit(main())
