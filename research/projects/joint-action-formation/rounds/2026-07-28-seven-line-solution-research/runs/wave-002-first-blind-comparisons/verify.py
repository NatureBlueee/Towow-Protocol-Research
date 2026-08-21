#!/usr/bin/env python3
"""Verify the frozen Wave 002 evidence without upgrading its claim boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def verify_hashes() -> None:
    for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, relative_path = line.split("  ", 1)
        actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        if actual != expected:
            raise AssertionError(f"hash mismatch: {relative_path}")


def verify_g1_comparison() -> None:
    expected = {
        "g1/method-a-public-catalog.score.json": (0.0, 0, 1 / 3, 1),
        "g1/method-b-local-projections-only.score.json": (0.125, 1, 0.0, 0),
        "g1/method-ab-public-plus-local.score.json": (0.625, 5, 2 / 3, 1),
    }
    observed = {}
    for relative_path, target in expected.items():
        score = load(relative_path)
        value = (
            score["coverage"]["ratio"],
            score["coverage"]["requirements_passed"],
            score["metrics"]["opportunity_recall"],
            score["metrics"]["false_wakeup_count"],
        )
        if value != target:
            raise AssertionError(f"unexpected G1 result: {relative_path}: {value}")
        observed[relative_path] = value

    a = observed["g1/method-a-public-catalog.score.json"][0]
    b = observed["g1/method-b-local-projections-only.score.json"][0]
    combined = observed["g1/method-ab-public-plus-local.score.json"][0]
    if combined - max(a, b) != 0.5:
        raise AssertionError("the frozen A+B gain is no longer 0.5")


def verify_t2_boundary() -> None:
    candidate = load("t2/final-submission.json")
    evaluation = load("t2/model-evaluation.json")
    last_response = load("t2/response-round-4.json")

    if evaluation["overall_status"] != "PASS":
        raise AssertionError("the frozen model evaluation is no longer PASS")
    if len(evaluation["requirements"]) != 8:
        raise AssertionError("the frozen model evaluation no longer contains R1-R8")
    if {item["status"] for item in evaluation["requirements"]} != {"PASS"}:
        raise AssertionError("the frozen model evaluation contains a non-PASS requirement")

    capability = candidate["capability_claims"][0]
    relation_v2 = candidate["relation_versions"][1]
    outcomes = candidate["outcomes"]

    if capability["status"] != "UNKNOWN_UNQUALIFIED_PROBE_CANDIDATE":
        raise AssertionError("capability was improperly upgraded")
    if capability["evidence_available_at_claim_time"] != "none_for_this_environment":
        raise AssertionError("the missing capability evidence was erased")
    if relation_v2["probe"]["status"] != "NOT_RUN":
        raise AssertionError("the synthetic probe was improperly marked as run")
    if outcomes["action_attempt"]["status"] != "NOT_RUN":
        raise AssertionError("ActionAttempt was improperly marked as run")
    for name in ("effect", "adoption", "acceptance", "settlement"):
        if outcomes[name]["status"] != "NOT_OCCURRED":
            raise AssertionError(f"{name} was improperly upgraded")

    if candidate["controller_history_hash"] != last_response["history_hash"]:
        raise AssertionError("candidate/controller history mismatch")
    if len(candidate["queries_and_disclosures"]) != 15:
        raise AssertionError("the frozen run no longer has 15 disclosure receipts")


def main() -> None:
    verify_hashes()
    verify_g1_comparison()
    verify_t2_boundary()
    print("[OK] Wave 002 hashes, A/B/A+B comparison, and T2 reality boundary")


if __name__ == "__main__":
    main()
