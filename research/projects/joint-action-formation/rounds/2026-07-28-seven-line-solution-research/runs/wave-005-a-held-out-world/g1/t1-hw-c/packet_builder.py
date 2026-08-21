#!/usr/bin/env python3
"""Deterministically split the controller-only source into isolated packets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SOURCE = BASE_DIR / "controller_input.json"


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON top level must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _base_packet(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "world_id": source["world_id"],
        "evaluation_step": source["evaluation_step"],
        "query": source["query"],
        "available_actions": source["available_actions"],
        "submission_schema_ref": "submission_schema.json",
        "semantic_contract": {
            "depth_origin_to_first_recipient": 0,
            "depth_increment_per_authorized_onward_hop": 1,
            "pair_orientation": "SEEK_TO_OFFER",
            "reciprocal_exchange_is_symmetric": True,
            "unknown_without_visible_evidence": True
        }
    }


def build_packets(source: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if source.get("kind") != "CONTROLLER_ONLY_PACKET_SOURCE":
        raise ValueError("source must be CONTROLLER_ONLY_PACKET_SOURCE")
    if source.get("execution_contract", {}).get("source_is_method_visible") is not False:
        raise ValueError("controller source must not be method-visible")
    base = _base_packet(source)
    packets: dict[str, dict[str, Any]] = {
        "coordinator.json": {
            **base,
            "kind": "METHOD_VISIBLE_COORDINATOR_PACKET",
            "recipient": "HWC-COORDINATOR",
            "delivery_scope": "COORDINATOR_ONLY",
            "public_view": source["public_view"],
            "execution_contract": {
                "may_read_local_packets": False,
                "may_invent_party_authority": False,
                "may_self_attest_execution": False,
                "may_receive_only_authorized_receipts": True
            }
        }
    }
    seen_holders: set[str] = set()
    for local_view in sorted(
        source["local_execution_views"], key=lambda item: item["holder"]
    ):
        holder = local_view["holder"]
        if holder in seen_holders:
            raise ValueError(f"duplicate holder: {holder}")
        seen_holders.add(holder)
        packets[f"local/{holder}.json"] = {
            **base,
            "kind": "METHOD_VISIBLE_LOCAL_PACKET",
            "recipient": holder,
            "delivery_scope": local_view["delivery_scope"],
            "local_view": {
                "holder": holder,
                "observations": local_view["observations"]
            },
            "execution_contract": {
                "may_read_coordinator_packet": False,
                "may_read_other_local_packets": False,
                "raw_local_fact_disclosure": False,
                "must_not_infer_other_party_state": True,
                "execution_requires_three_evidence_domains": True
            }
        }
    return packets


def packet_index(packets: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entries = []
    for path, packet in sorted(packets.items()):
        entries.append({
            "path": path,
            "kind": packet["kind"],
            "recipient": packet["recipient"],
            "sha256": hashlib.sha256(canonical_bytes(packet)).hexdigest()
        })
    return {
        "schema_version": "2.0",
        "kind": "CONTROLLER_ONLY_PACKET_INDEX",
        "packet_count": len(entries),
        "packets": entries,
        "delivery_rule": (
            "Deliver exactly one recipient packet to each isolated execution "
            "domain. Never expose this cross-recipient index to a solver."
        )
    }


def write_packets(
    packets: dict[str, dict[str, Any]], output_dir: Path
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative_path, packet in packets.items():
        target = output_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(canonical_bytes(packet))
    index = packet_index(packets)
    (output_dir / "controller-index.json").write_bytes(canonical_bytes(index))
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    index = write_packets(build_packets(load_json(args.source)), args.output_dir)
    print(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
