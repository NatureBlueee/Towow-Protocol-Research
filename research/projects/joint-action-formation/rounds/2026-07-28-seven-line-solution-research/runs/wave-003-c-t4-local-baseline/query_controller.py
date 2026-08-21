#!/usr/bin/env python3
"""Run a method-neutral exhaustive-minimal T4 controller query baseline.

The solver reads only the public blind input and uses controller.py as the
declared disclosure interface. It never opens the oracle or evaluator-only
artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


METHOD_ID = "T4-LOCAL-DETERMINISTIC-AUTHORITY-WORKFLOW-V1"
RUN_ID = "T4-LOCAL-BASELINE-20260728-001"
TASK_ID = "T4-JOINT-BID-BLIND-V1"
RELATION_VERSION = "REL-T4-LOCAL-CANDIDATE-V1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def all_public_queries(blind: dict[str, Any]) -> list[dict[str, str]]:
    queries: list[dict[str, str]] = []
    for interface in blind["authority_interfaces"]:
        for request_type in interface["allowed_request_types"]:
            queries.append(
                {
                    "authority_id": interface["authority_id"],
                    "request_type": request_type,
                    "purpose": (
                        "Evaluate the exact current joint-bid requirement "
                        "before commitment"
                    ),
                    "relation_version_ref": RELATION_VERSION,
                    "retention_scope": "RUN_ONLY",
                }
            )
    return queries


def run_controller(
    controller: Path,
    batch: dict[str, Any],
    batch_path: Path,
    state_path: Path,
    response_path: Path,
) -> dict[str, Any]:
    write_json(batch_path, batch)
    subprocess.run(
        [
            sys.executable,
            str(controller),
            "--input",
            str(batch_path),
            "--state",
            str(state_path),
            "--output",
            str(response_path),
        ],
        check=True,
    )
    return load_json(response_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blind", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    blind = load_json(args.blind)
    queries = all_public_queries(blind)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state_path = args.output_dir / "controller-state.json"
    previous_hash: str | None = None
    history_hash: str | None = None
    pending = queries
    all_receipts: list[dict[str, Any]] = []
    all_results: list[dict[str, Any]] = []
    all_responses: list[dict[str, Any]] = []

    for round_number in range(1, 5):
        batch = {
            "schema_version": "1.0",
            "task_id": TASK_ID,
            "method_id": METHOD_ID,
            "run_id": RUN_ID,
            "round": round_number,
            "previous_round_hash": previous_hash,
            "queries": pending,
        }
        response = run_controller(
            args.controller,
            batch,
            args.output_dir / f"query-round-{round_number}.json",
            state_path,
            args.output_dir / f"response-round-{round_number}.json",
        )
        all_responses.append(response)
        all_results.extend(response["results"])
        receipts = [result["receipt"] for result in response["results"]]
        all_receipts.extend(receipts)
        deferred_keys = {
            (
                receipt["authority_id"],
                receipt["request_type"],
            )
            for receipt in receipts
            if receipt["response_type"] == "DEFER"
        }
        pending = [
            query
            for query in queries
            if (query["authority_id"], query["request_type"]) in deferred_keys
        ]
        previous_hash = response["round_hash"]
        history_hash = response["history_hash"]
        if not pending:
            break

    summary = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "method_id": METHOD_ID,
        "run_id": RUN_ID,
        "relation_version_ref": RELATION_VERSION,
        "blind_input_hash": hashlib.sha256(args.blind.read_bytes()).hexdigest(),
        "controller_history_hash": history_hash,
        "rounds": len(all_responses),
        "receipt_count": len(all_receipts),
        "deferred_after_last_round": len(pending),
        "receipt_chain_hash": digest(
            [receipt["receipt_hash"] for receipt in all_receipts]
        ),
        "receipts": all_receipts,
        "results": all_results,
    }
    write_json(args.output_dir / "disclosure-summary.json", summary)
    if pending:
        raise SystemExit("controller prerequisites did not close within four rounds")


if __name__ == "__main__":
    main()
