#!/usr/bin/env python3
"""Parent broker for the prototype B mature-composite worker."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from fixtures import WORLDS, WorldSpec, by_ref
from primitive_service import PrimitiveService


HERE = Path(__file__).resolve().parent
WORKER = HERE / "mature_composite_worker.py"


def run_world(spec: WorldSpec) -> dict[str, Any]:
    service = PrimitiveService(spec)
    predictions: list[dict[str, Any]] = []
    worker_events: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="g4-prototype-b-") as tmp:
        process = subprocess.Popen(
            ["python3", "-I", str(WORKER)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=tmp,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
            },
        )
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(
            json.dumps({"type": "init", **service.public_bootstrap()}) + "\n"
        )
        process.stdin.flush()

        final: dict[str, Any] | None = None
        for line in process.stdout:
            event = json.loads(line)
            worker_events.append(event)
            if event["type"] == "prediction":
                predictions.append(event)
            elif event["type"] == "call":
                raw = service.call(event["primitive"], event["arguments"])
                process.stdin.write(
                    json.dumps(
                        {
                            "type": "response",
                            "primitive": event["primitive"],
                            "raw": raw,
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                process.stdin.flush()
            elif event["type"] == "final":
                final = event
                break
            else:
                raise RuntimeError(f"unknown worker event: {event}")
        process.stdin.close()
        stderr = process.stderr.read() if process.stderr is not None else ""
        returncode = process.wait(timeout=5)
        process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
    if returncode != 0:
        raise RuntimeError(stderr)
    if final is None:
        raise RuntimeError("worker exited without final event")
    return {
        "world_ref": spec.world_ref,
        "pair_ref": spec.pair_ref,
        "pair_kind": spec.pair_kind,
        "predictions": predictions,
        "final": final,
        "broker_log": service.broker_log,
        "state_after": service.snapshot(),
        "worker_event_count": len(worker_events),
    }


def compact(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "world_ref": result["world_ref"],
        "pair_ref": result["pair_ref"],
        "pair_kind": result["pair_kind"],
        "predictions": result["predictions"],
        "final": result["final"],
        "calls": [entry["primitive"] for entry in result["broker_log"]],
        "cost": {
            "query_count": len(result["broker_log"]),
            "latency_ms": sum(
                entry["latency_ms"] for entry in result["broker_log"]
            ),
            "response_bytes": sum(
                entry["response_bytes"] for entry in result["broker_log"]
            ),
            "disclosures": [
                entry["sensitivity"] for entry in result["broker_log"]
            ],
        },
        "state_after": result["state_after"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--world")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    population = (by_ref(args.world),) if args.world else WORLDS
    results = [run_world(spec) for spec in population]
    print(
        json.dumps(
            results if args.full else [compact(result) for result in results],
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
