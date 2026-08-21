#!/usr/bin/env python3
"""Parent evaluator for the Wave 010 G4 v2 audit response."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import secrets
import subprocess
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "WAVE-010-G4-RELIANCE-PUBLIC-FIXTURE-V2.json"
ORACLE = HERE / "WAVE-010-G4-RELIANCE-ORACLE-V2.json"
WORKER = HERE / "WAVE-010-G4-METHOD-WORKER-V2.py"
METHODS = (
    "DECLARATION_ONLY",
    "READINESS_ONLY",
    "PROBE_CI_IAM",
    "REFERENCE_COMPOSITION_HITL",
)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def randomized(value: Any, rng: random.SystemRandom) -> Any:
    if isinstance(value, dict):
        keys = list(value)
        rng.shuffle(keys)
        return {key: randomized(value[key], rng) for key in keys}
    if isinstance(value, list):
        return [randomized(item, rng) for item in value]
    return value


def randomized_payload(packet: dict[str, Any]) -> tuple[bytes, str]:
    rng = random.SystemRandom()
    payload = {
        "opaque_packet_id": secrets.token_hex(16),
        "run_nonce": secrets.token_hex(16),
        "method_packet": packet,
    }
    encoded = json.dumps(
        randomized(payload, rng),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return encoded, payload["opaque_packet_id"]


def run_worker(method: str, packet: dict[str, Any]) -> tuple[dict[str, Any], str]:
    encoded, opaque_id = randomized_payload(packet)
    with tempfile.TemporaryDirectory(prefix="wave010-g4-v2-worker-") as tmp:
        completed = subprocess.run(
            ["python3", "-I", str(WORKER), "--method", method],
            input=encoded,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp,
            env={
                "PATH": os.environ.get("PATH", ""),
                "PYTHONIOENCODING": "utf-8",
            },
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.decode("utf-8", errors="replace"))
    result = json.loads(completed.stdout)
    if result.pop("opaque_packet_id") != opaque_id:
        raise RuntimeError("worker response packet mismatch")
    return result, sha256_bytes(encoded)


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], str, str]:
    public_raw = PUBLIC.read_bytes()
    oracle_raw = ORACLE.read_bytes()
    return (
        json.loads(public_raw),
        json.loads(oracle_raw),
        sha256_bytes(public_raw),
        sha256_bytes(oracle_raw),
    )


def evaluate() -> dict[str, Any]:
    public, oracle, public_hash, oracle_hash_before = load_inputs()
    expanded: dict[str, dict[str, Any]] = {}
    case_meta: dict[str, dict[str, str]] = {}
    for case in public["cases"]:
        expanded[case["case_ref"]] = deep_merge(
            public["templates"][case["template"]], case["overrides"]
        )
        case_meta[case["case_ref"]] = {
            "task_family": case["task_family"],
            "split": case["split"],
        }
    if set(expanded) != set(oracle["cases"]):
        raise RuntimeError("public/oracle population mismatch")

    method_results: dict[str, Any] = {}
    for method in METHODS:
        tp = fp = tn = fn = abstain = 0
        unsafe_total = unsafe_false_rely = unsafe_label_match = 0
        held_out_total = held_out_false_rely = held_out_label_match = 0
        per_case: dict[str, Any] = {}
        for case_ref, packet in expanded.items():
            result, serialization_hash = run_worker(method, packet)
            truth = oracle["cases"][case_ref]
            relies = result["decision"] == "RELY"
            safe = truth["safe_to_rely"]
            if result["decision"] == "ABSTAIN":
                abstain += 1
            if safe and relies:
                tp += 1
            elif safe and not relies:
                fn += 1
            elif not safe and relies:
                fp += 1
            else:
                tn += 1

            label_match = (
                result["decision"] == truth["expected_decision"]
                and result["recovery_labels"]
                == truth["expected_recovery_labels"]
            )
            if not safe:
                unsafe_total += 1
                unsafe_false_rely += int(relies)
                unsafe_label_match += int(label_match)
            if case_meta[case_ref]["split"] == "HELD_OUT":
                held_out_total += 1
                held_out_false_rely += int(not safe and relies)
                held_out_label_match += int(label_match)
            per_case[case_ref] = {
                "decision": result["decision"],
                "recovery_labels": result["recovery_labels"],
                "serialization_sha256": serialization_hash,
                **case_meta[case_ref],
            }

        method_results[method] = {
            "confusion": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
            "safe_recall": tp / (tp + fn),
            "unsafe_false_rely": f"{unsafe_false_rely}/{unsafe_total}",
            "abstention": f"{abstain}/{len(expanded)}",
            "unsafe_label_match_only": f"{unsafe_label_match}/{unsafe_total}",
            "held_out_false_rely": f"{held_out_false_rely}/{held_out_total}",
            "held_out_label_match_only": f"{held_out_label_match}/{held_out_total}",
            "per_case": per_case,
        }

    hidden_left = expanded["T6-HIDDEN-DEPENDENCY-VALID"]
    hidden_right = expanded["T6-HIDDEN-DEPENDENCY-REVOKED"]
    oracle_hash_after = sha256_bytes(ORACLE.read_bytes())
    return {
        "fixture_id": public["fixture_id"],
        "public_fixture_sha256": public_hash,
        "oracle_sha256_before": oracle_hash_before,
        "oracle_sha256_after": oracle_hash_after,
        "oracle_unchanged_during_run": oracle_hash_before == oracle_hash_after,
        "world_count": len(expanded),
        "safe_count": sum(
            1 for value in oracle["cases"].values() if value["safe_to_rely"]
        ),
        "unsafe_count": sum(
            1 for value in oracle["cases"].values() if not value["safe_to_rely"]
        ),
        "held_out_cases": sorted(
            ref for ref, meta in case_meta.items() if meta["split"] == "HELD_OUT"
        ),
        "hidden_pair_method_packets_identical": hidden_left == hidden_right,
        "methods": method_results,
        "claim_boundary": {
            "recovery_metric": "exact evaluator label match only; no recovery action was executed",
            "process_boundary": "fixed Python worker in isolated mode and temporary cwd; not a hostile OS sandbox",
            "strong_center": "not implemented and not scored",
        },
    }


def compact(report: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in report.items()
        if key != "methods"
    } | {
        "methods": {
            method: {
                key: value
                for key, value in result.items()
                if key != "per_case"
            }
            for method, result in report["methods"].items()
        }
    }


def self_test(report: dict[str, Any]) -> None:
    assert report["world_count"] == 12
    assert report["safe_count"] == 4
    assert report["unsafe_count"] == 8
    assert report["oracle_unchanged_during_run"]
    assert report["hidden_pair_method_packets_identical"]
    assert len(report["held_out_cases"]) == 4
    assert "LAWFUL_STRONG_CENTER" not in report["methods"]
    reference = report["methods"]["REFERENCE_COMPOSITION_HITL"]
    assert reference["confusion"] == {"TP": 3, "FP": 0, "TN": 8, "FN": 1}
    assert reference["safe_recall"] == 0.75
    assert reference["unsafe_false_rely"] == "0/8"
    assert reference["abstention"] == "5/12"
    assert reference["unsafe_label_match_only"] == "8/8"
    assert reference["held_out_false_rely"] == "0/4"
    assert reference["held_out_label_match_only"] == "4/4"

    public = json.loads(PUBLIC.read_text(encoding="utf-8"))
    packet = deep_merge(public["templates"]["T2_CURRENT"], {})
    first, first_hash = run_worker("REFERENCE_COMPOSITION_HITL", packet)
    second, second_hash = run_worker("REFERENCE_COMPOSITION_HITL", packet)
    assert first == second
    assert first_hash != second_hash


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    report = evaluate()
    if args.self_test:
        self_test(report)
    print(
        json.dumps(
            report if args.full else compact(report),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    if args.self_test:
        print("SELF_TEST_PASS")


if __name__ == "__main__":
    main()
