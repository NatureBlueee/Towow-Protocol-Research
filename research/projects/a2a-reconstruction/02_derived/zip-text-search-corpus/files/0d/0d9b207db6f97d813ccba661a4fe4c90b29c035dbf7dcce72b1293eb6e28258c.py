#!/usr/bin/env python3
"""Role process for the macOS sandbox-exec sovereignty experiment."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def probe_read(path: Path) -> dict[str, Any]:
    try:
        path.read_bytes()
        return {"allowed": True, "error": None}
    except OSError as exc:
        return {"allowed": False, "error": f"{type(exc).__name__}:{exc.errno}"}


def load_private(path: Path) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(path.read_bytes())


def load_public(path: Path) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(path.read_bytes())


def sign_json(key: Ed25519PrivateKey, value: Any) -> str:
    return base64.b64encode(key.sign(canonical(value))).decode("ascii")


def verify_json(key: Ed25519PublicKey, value: Any, signature_b64: str) -> bool:
    try:
        key.verify(base64.b64decode(signature_b64), canonical(value))
        return True
    except Exception:
        return False


def audit(packet: Path, repo: Path) -> dict[str, Any]:
    baseline = packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv"
    rows: list[dict[str, Any]] = []
    with baseline.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            artifact = row["artifact"].strip()
            candidates = [(packet / artifact).resolve(), (repo / artifact).resolve()]
            chosen = next((candidate for candidate in candidates if candidate.is_file()), None)
            rows.append(
                {
                    "claim_id": row["claim_id"],
                    "reachable": chosen is not None,
                    "sha256": (
                        hashlib.sha256(chosen.read_bytes()).hexdigest() if chosen else None
                    ),
                }
            )
    reachable = sum(bool(row["reachable"]) for row in rows)
    return {
        "claims": len(rows),
        "reachable": reachable,
        "missing": len(rows) - reachable,
        "rows": rows,
        "absolute_paths_disclosed": False,
    }


def producer(args: argparse.Namespace) -> int:
    other_probe = probe_read(args.other_canary)
    other_key_probe = probe_read(args.other_private_key_probe)
    report = audit(args.packet, args.repo)
    key = load_private(args.private_key)
    signature = sign_json(key, report)
    write_json(args.shared / "report.json", report)
    (args.shared / "report.sig").write_text(signature + "\n", encoding="ascii")
    write_json(
        args.output,
        {
            "role": "producer",
            "other_private_read": other_probe,
            "other_private_key_read": other_key_probe,
            "report_sha256": sha256_bytes(canonical(report)),
            "signed": True,
        },
    )
    return 0


def validator(args: argparse.Namespace) -> int:
    other_probe = probe_read(args.other_canary)
    other_key_probe = probe_read(args.other_private_key_probe)
    report = read_json(args.shared / "report.json")
    signature = (args.shared / "report.sig").read_text(encoding="ascii").strip()
    signature_valid = verify_json(
        load_public(args.producer_public_key), report, signature
    )
    policy = read_json(args.policy)
    counts_valid = (
        report.get("claims") == policy["expected_claims"]
        and report.get("reachable") == policy["expected_reachable"]
        and report.get("missing") == policy["expected_missing"]
        and report.get("reachable", 0) + report.get("missing", 0)
        == report.get("claims")
    )
    accepted = signature_valid and counts_valid and not report.get(
        "absolute_paths_disclosed", True
    )
    reason = (
        "accepted"
        if accepted
        else "invalid_producer_signature"
        if not signature_valid
        else "policy_or_count_mismatch"
    )
    verdict = {
        "accepted": accepted,
        "reason": reason,
        "report_sha256": sha256_bytes(canonical(report)),
        "signature_valid": signature_valid,
        "counts_valid": counts_valid,
    }
    verdict_signature = sign_json(load_private(args.private_key), verdict)
    write_json(args.shared / "verdict.json", verdict)
    (args.shared / "verdict.sig").write_text(
        verdict_signature + "\n", encoding="ascii"
    )
    write_json(
        args.output,
        {
            "role": "validator",
            "other_private_read": other_probe,
            "other_private_key_read": other_key_probe,
            "verdict": verdict,
            "signed": True,
        },
    )
    return 0 if accepted else 4


def coordinator_preflight(args: argparse.Namespace) -> int:
    probes = {
        "producer_private": probe_read(args.producer_canary),
        "validator_private": probe_read(args.validator_canary),
        "packet_baseline": probe_read(
            args.packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv"
        ),
        "producer_private_key": probe_read(args.producer_private_key_probe),
        "validator_private_key": probe_read(args.validator_private_key_probe),
    }
    cards = read_json(args.shared / "capability_cards.json")
    status = "report_available" if (args.shared / "report.json").is_file() else "unknown"
    write_json(
        args.shared / "request.json",
        {
            "task": "audit baseline artifact reachability",
            "required_output": "signed report without absolute paths",
        },
    )
    write_json(
        args.output,
        {
            "role": "coordinator_preflight",
            "private_and_packet_probes": probes,
            "capability_cards": cards,
            "status": status,
            "static_profile_can_complete": status == "report_available",
        },
    )
    return 0


def coordinator_finalize(args: argparse.Namespace) -> int:
    probes = {
        "producer_private": probe_read(args.producer_canary),
        "validator_private": probe_read(args.validator_canary),
        "packet_baseline": probe_read(
            args.packet / "baseline" / "CLAIM_EVIDENCE_BASELINE_R5.csv"
        ),
        "producer_private_key": probe_read(args.producer_private_key_probe),
        "validator_private_key": probe_read(args.validator_private_key_probe),
    }
    report = read_json(args.shared / "report.json")
    verdict = read_json(args.shared / "verdict.json")
    verdict_signature = (args.shared / "verdict.sig").read_text(
        encoding="ascii"
    ).strip()
    validator_signature_valid = verify_json(
        load_public(args.validator_public_key), verdict, verdict_signature
    )
    report_hash_matches = verdict["report_sha256"] == sha256_bytes(canonical(report))
    accepted = (
        validator_signature_valid and report_hash_matches and verdict["accepted"]
    )
    write_json(
        args.output,
        {
            "role": "coordinator_finalize",
            "private_and_packet_probes": probes,
            "validator_signature_valid": validator_signature_valid,
            "report_hash_matches": report_hash_matches,
            "accepted": accepted,
            "verdict_reason": verdict["reason"],
        },
    )
    return 0 if accepted else 5


def central(args: argparse.Namespace) -> int:
    producer_canary_read = args.producer_canary.read_bytes() is not None
    validator_canary_read = args.validator_canary.read_bytes() is not None
    report = audit(args.packet, args.repo)
    policy = read_json(args.policy)
    accepted = (
        report["claims"] == policy["expected_claims"]
        and report["reachable"] == policy["expected_reachable"]
        and report["missing"] == policy["expected_missing"]
    )
    write_json(
        args.output,
        {
            "role": "centralized_omniscient",
            "accepted": accepted,
            "private_canaries_read": {
                "producer": producer_canary_read,
                "validator": validator_canary_read,
            },
            "report": report,
        },
    )
    return 0 if accepted else 6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "role",
        choices=[
            "producer",
            "validator",
            "coordinator_preflight",
            "coordinator_finalize",
            "central",
        ],
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--shared", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--producer-canary", type=Path)
    parser.add_argument("--validator-canary", type=Path)
    parser.add_argument("--other-canary", type=Path)
    parser.add_argument("--other-private-key-probe", type=Path)
    parser.add_argument("--private-key", type=Path)
    parser.add_argument("--producer-public-key", type=Path)
    parser.add_argument("--validator-public-key", type=Path)
    parser.add_argument("--producer-private-key-probe", type=Path)
    parser.add_argument("--validator-private-key-probe", type=Path)
    parser.add_argument("--policy", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return {
        "producer": producer,
        "validator": validator,
        "coordinator_preflight": coordinator_preflight,
        "coordinator_finalize": coordinator_finalize,
        "central": central,
    }[args.role](args)


if __name__ == "__main__":
    raise SystemExit(main())
