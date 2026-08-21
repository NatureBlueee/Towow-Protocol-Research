#!/usr/bin/env python3
"""Run the 12-pair × 3-stratum × 3-implementation G6 matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from owner_services import (
    FIXTURES,
    ROOT,
    build_owner_observations,
    owner_source_manifest,
    public_world_token,
)
from workers import WORKERS, run_worker, worker_manifest


PRIVATE_ORACLE = ROOT / "private_oracle" / "expected.json"
PAIR_INDEX = FIXTURES / "pairs.json"
STRATA = ("S1", "S2", "S3")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_pairs() -> dict[str, Any]:
    value = json.loads(PAIR_INDEX.read_text(encoding="utf-8"))
    pairs = value.get("pairs")
    if not isinstance(pairs, list) or len(pairs) != 12:
        raise ValueError("pair index must contain exactly 12 pairs")
    world_ids = [world for pair in pairs for world in pair.get("worlds", [])]
    if len(world_ids) != 24 or len(set(world_ids)) != 24:
        raise ValueError("pair index must contain 24 unique worlds")
    return value


def _packet_hash(packet: dict[str, Any]) -> str:
    body = json.dumps(
        packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def run_matrix() -> dict[str, Any]:
    pair_index = _load_pairs()
    oracle_hash_before = sha256_file(PRIVATE_ORACLE)
    records = []
    for pair in pair_index["pairs"]:
        for stratum in STRATA:
            for implementation in WORKERS:
                pair_runs = []
                for world_id in pair["worlds"]:
                    method_packet = build_owner_observations(world_id, stratum)
                    if "pair" in method_packet or "world_id" in method_packet:
                        raise RuntimeError("pair/side label leaked into worker packet")
                    if method_packet.get("world_token") != public_world_token(world_id):
                        raise RuntimeError("opaque world token mismatch")
                    method_output = run_worker(implementation, method_packet)
                    pair_runs.append((world_id, method_packet, method_output))
                owner_query_count = sum(
                    item[1]["owner_query_cost"]["query_count"] for item in pair_runs
                )
                disclosure_units = sum(
                    item[1]["owner_query_cost"]["disclosure_units"] for item in pair_runs
                )
                compute_units = sum(
                    int(item[2].get("worker_cost", {}).get("compute_units", 0))
                    for item in pair_runs
                )
                records.append(
                    {
                        "pair": pair["pair"],
                        "world": [item[0] for item in pair_runs],
                        "public_world_token": [item[1]["world_token"] for item in pair_runs],
                        "stratum": stratum,
                        "implementation": implementation,
                        "method_output": {
                            item[1]["world_token"]: item[2] for item in pair_runs
                        },
                        "owner_observations": {
                            item[1]["world_token"]: item[1]["observations"]
                            for item in pair_runs
                        },
                        "cost": {
                            "owner_query_count": owner_query_count,
                            "owner_disclosure_units": disclosure_units,
                            "worker_compute_units": compute_units,
                        },
                        "latency_ms": sum(
                            item[1]["owner_query_cost"]["latency_ms"]
                            + int(
                                item[2].get("worker_cost", {}).get(
                                    "added_latency_ms", 0
                                )
                            )
                            for item in pair_runs
                        ),
                        "hitl_calls": sum(
                            int(item[2].get("worker_cost", {}).get("hitl_calls", 0))
                            for item in pair_runs
                        ),
                        "trace_refs": {
                            item[1]["world_token"]: item[1]["trace_refs"]
                            for item in pair_runs
                        },
                        "method_packet_hash": [
                            _packet_hash(item[1]) for item in pair_runs
                        ],
                    }
                )
    oracle_hash_after = sha256_file(PRIVATE_ORACLE)
    if oracle_hash_after != oracle_hash_before:
        raise RuntimeError("private oracle changed while workers ran")
    if len(records) != 108:
        raise RuntimeError(f"expected 108 records, got {len(records)}")
    return {
        "schema_version": "1.0",
        "kind": "G6_12_PAIR_3X3_RUN",
        "run_validity": "PENDING_GATES",
        "pair_count": 12,
        "world_count": 24,
        "authority_strata": list(STRATA),
        "implementation_count": 3,
        "record_count": len(records),
        "records": records,
        "worker_executable_source_hashes": worker_manifest(),
        "oracle_hash_before": oracle_hash_before,
        "oracle_hash_after": oracle_hash_after,
        "owner_source_identities": owner_source_manifest(),
        "cannot_support": [
            "X2 scoreable population or X2 result",
            "real-world Effect, Adoption, Acceptance or Settlement",
            "production recovery, payment or authorized external action",
            "general cross-domain sufficiency",
            "formal LineContract, MechanismProfile, NOW or PROGRAM status change",
            "novel protocol necessity",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_matrix()
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
