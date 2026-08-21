#!/usr/bin/env python3
"""One-command local synthetic Wave 011 G6 experiment."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

from evaluator import evaluate_matrix
from gate_runner import evaluate_main_run
from runner import run_matrix


ROOT = Path(__file__).resolve().parent


def run_experiment() -> dict[str, Any]:
    matrix = run_matrix()
    gates = evaluate_main_run(matrix).to_dict()
    evaluation = evaluate_matrix(matrix) if gates["coverage_allowed"] else None
    valid = bool(gates["overall_valid"])
    matrix["run_validity"] = (
        "VALID_LOCAL_SYNTHETIC_GATES_PASS" if valid else "INVALID"
    )
    return {
        "schema_version": "1.0",
        "kind": "G6_WAVE011_EXPERIMENT_RESULT",
        "status": matrix["run_validity"],
        "gates": gates,
        "evaluation": evaluation,
        "matrix": matrix,
    }


def _compact(result: dict[str, Any], raw_archive: Path, raw_bytes: bytes) -> dict[str, Any]:
    evaluation = dict(result["evaluation"] or {})
    evaluation.pop("rows", None)
    matrix = {
        key: value
        for key, value in result["matrix"].items()
        if key != "records"
    }
    return {
        "schema_version": result["schema_version"],
        "kind": result["kind"],
        "status": result["status"],
        "gates": result["gates"],
        "evaluation": evaluation,
        "matrix_summary": matrix,
        "raw_archive": {
            "path": raw_archive.name,
            "format": "gzip-compressed JSON",
            "sha256": hashlib.sha256(raw_archive.read_bytes()).hexdigest(),
            "uncompressed_bytes": len(raw_bytes),
            "compressed_bytes": raw_archive.stat().st_size,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "RESULTS.json",
    )
    parser.add_argument(
        "--raw-output",
        type=Path,
        default=ROOT / "RUN-RAW.json.gz",
    )
    args = parser.parse_args()
    result = run_experiment()
    raw_bytes = (
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    with args.raw_output.open("wb") as raw_handle:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_handle,
            mtime=0,
        ) as handle:
            handle.write(raw_bytes)
    compact_result = _compact(result, args.raw_output, raw_bytes)
    args.output.write_text(
        json.dumps(compact_result, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    compact = {
        "status": result["status"],
        "gate_status": result["gates"]["round_status"],
        "pair_count": result["matrix"]["pair_count"],
        "record_count": result["matrix"]["record_count"],
        "passed_record_count": (
            result["evaluation"]["passed_record_count"]
            if result["evaluation"] is not None
            else 0
        ),
        "result_path": str(args.output),
    }
    print(json.dumps(compact, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] != "INVALID" else 2


if __name__ == "__main__":
    raise SystemExit(main())
