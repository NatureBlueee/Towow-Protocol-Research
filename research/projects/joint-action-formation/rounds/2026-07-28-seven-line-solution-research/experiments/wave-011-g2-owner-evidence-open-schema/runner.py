#!/usr/bin/env python3
"""Run the 12-world G2-O1 owner-evidence/open-schema discriminator."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from g2o1.actors import canonical_bytes, digest  # noqa: E402
from g2o1.evaluators import evaluate_run  # noqa: E402
from g2o1.methods import ARM_IDS  # noqa: E402


def _discover(candidates: list[str]) -> Path:
    for name in candidates:
        path = ROOT / name
        if path.exists():
            return path
    raise FileNotFoundError(
        "NONE_OF_THE_EXPECTED_INPUTS_EXIST:" + ",".join(candidates)
    )


def _load_worlds(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(document, list):
        worlds = document
        metadata = {}
    else:
        worlds = document.get("worlds", [])
        metadata = {
            key: value for key, value in document.items() if key != "worlds"
        }
    if not isinstance(worlds, list):
        raise TypeError("PUBLIC_WORLDS_MUST_BE_A_LIST")
    ids = [row.get("world_id") for row in worlds]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("WORLD_IDS_MUST_BE_PRESENT_AND_UNIQUE")
    return metadata, worlds


def _invoke_owner(
    world: dict[str, Any], oracle_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = canonical_bytes({"world": world})
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "workers" / "owner_worker.py"),
            "--oracle",
            str(oracle_path),
        ],
        cwd=ROOT,
        input=raw,
        capture_output=True,
        timeout=30,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if process.returncode != 0:
        raise RuntimeError(
            "OWNER_WORKER_FAILED:"
            + process.stderr.decode("utf-8", errors="replace")
        )
    packet = json.loads(process.stdout)
    return packet, {
        "pid": packet["owner_worker_pid"],
        "stdin_digest": digest({"world": world}),
        "stdout_digest": digest(packet),
        "returncode": process.returncode,
    }


def _invoke_method(
    arm: str,
    world: dict[str, Any],
    owner_packet: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = {"world": world, "owner_packet": owner_packet}
    raw = canonical_bytes(packet)
    process = subprocess.run(
        [
            sys.executable,
            str(ROOT / "workers" / "method_worker.py"),
            arm,
        ],
        cwd=ROOT,
        input=raw,
        capture_output=True,
        timeout=20,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"METHOD_WORKER_FAILED:{arm}:"
            + process.stderr.decode("utf-8", errors="replace")
        )
    candidate = json.loads(process.stdout)
    return candidate, {
        "pid": candidate["method_worker_pid"],
        "stdin_digest": digest(packet),
        "stdout_digest": digest(candidate),
        "returncode": process.returncode,
    }


def run_experiment(
    fixture_path: Path,
    oracle_path: Path,
) -> dict[str, Any]:
    metadata, worlds = _load_worlds(fixture_path)
    runs: list[dict[str, Any]] = []
    owner_workers: dict[str, Any] = {}
    method_workers: list[dict[str, Any]] = []
    owner_key_processes: dict[str, int] = {}
    for world in worlds:
        world_id = str(world["world_id"])
        owner_packet, owner_transport = _invoke_owner(world, oracle_path)
        owner_workers[world_id] = owner_transport
        for principal_id, pid in owner_packet["owner_key_processes"].items():
            owner_key_processes[f"{world_id}/{principal_id}"] = pid
        for arm in ARM_IDS:
            candidate, method_transport = _invoke_method(
                arm, world, owner_packet
            )
            method_workers.append(
                {"world_id": world_id, "arm": arm, **method_transport}
            )
            evaluation = evaluate_run(world, candidate, owner_packet)
            runs.append(
                {
                    "world_id": world_id,
                    "family": world.get("family"),
                    "task_skin": world.get("task_skin"),
                    "authority_topology": world.get("authority_topology"),
                    "state_placement": candidate.get("state_placement"),
                    "arm": arm,
                    "owner_events": owner_packet["owner_events"],
                    "method_output": candidate,
                    **evaluation,
                }
            )
    family_counts = Counter(str(world.get("family")) for world in worlds)
    axis_totals = {
        axis: sum(int(run["axes"][axis]) for run in runs)
        for axis in (
            "constituted",
            "understood",
            "claimed",
            "authorized",
            "activated",
        )
    }
    correct = sum(
        sum(map(int, run["axis_correctness"].values())) for run in runs
    )
    total_axis_decisions = len(runs) * 5
    return {
        "schema_version": "g2-o1-results-v1",
        "experiment": metadata.get(
            "experiment_id", "G2-O1-OWNER-EVIDENCE-OPEN-SCHEMA"
        ),
        "world_count": len(worlds),
        "run_count": len(runs),
        "arms": list(ARM_IDS),
        "family_counts": dict(family_counts),
        "security": {
            "controller_received_owner_keys": False,
            "methods_received_owner_keys": False,
            "key_material_exported": False,
            "owner_key_processes": owner_key_processes,
            "owner_actor_process_count": len(
                set(owner_key_processes.values())
            ),
        },
        "worker_processes": {
            "owner_workers": owner_workers,
            "method_workers": method_workers,
        },
        "runs": runs,
        "summary": {
            "axis_true_counts": axis_totals,
            "axis_decision_accuracy": (
                correct / total_axis_decisions
                if total_axis_decisions
                else 0.0
            ),
            "all_methods_covered_per_world": all(
                {
                    run["arm"]
                    for run in runs
                    if run["world_id"] == world["world_id"]
                }
                == set(ARM_IDS)
                for world in worlds
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--oracle", type=Path)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "outputs" / "results.json"
    )
    args = parser.parse_args()
    fixture = args.fixture or _discover(
        ["fixtures/public_worlds.json", "fixtures/worlds.json", "fixture.json"]
    )
    oracle = args.oracle or _discover(
        ["private/oracle.json", "private_oracle.json"]
    )
    result = run_experiment(fixture.resolve(), oracle.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "world_count": result["world_count"],
                "run_count": result["run_count"],
                "security": result["security"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
