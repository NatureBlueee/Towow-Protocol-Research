#!/usr/bin/env python3
"""Fixed G4 policy worker.

The worker reads one randomized JSON payload from stdin. It has no oracle path,
truth labels, case id, or evaluator code.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


ALLOWED_TOP_LEVEL = {"opaque_packet_id", "run_nonce", "method_packet"}
FORBIDDEN_TEXT = (
    "case_ref",
    "safe_to_rely",
    "private_oracle",
    "expected_decision",
    "expected_recovery",
)


def output(state: str, labels: list[str] | None = None) -> dict[str, Any]:
    return {
        "decision": state,
        "recovery_labels": sorted(set(labels or [])),
    }


def declaration_only(packet: dict[str, Any]) -> dict[str, Any]:
    return output("RELY") if packet["declaration"] == "ACTIVE" else output("ABSTAIN")


def readiness_only(packet: dict[str, Any]) -> dict[str, Any]:
    return output("RELY") if packet["readiness"] == "HEALTHY" else output(
        "BLOCK", ["RECOVER_SERVICE"]
    )


def probe_ci_iam(packet: dict[str, Any]) -> dict[str, Any]:
    labels: list[str] = []
    hard_block = False
    uncertain = False
    probe = packet["exact_probe"]
    permission = packet["permission"]

    if probe["status"] == "FAIL" and probe["head_current"]:
        labels.append("REQUALIFY_OPERATION")
        hard_block = True
    elif (
        probe["status"] != "PASS"
        or not probe["binding_matches"]
        or not probe["head_current"]
    ):
        labels.append("REQUALIFY_OPERATION")
        uncertain = True

    if permission["status"] == "REVOKED" and permission["head_current"]:
        labels.append("REAUTHORIZE")
        hard_block = True
    elif permission["status"] != "ACTIVE" or not permission["head_current"]:
        labels.append("REAUTHORIZE")
        uncertain = True

    if hard_block:
        return output("BLOCK", labels)
    if uncertain:
        return output("ABSTAIN", labels)
    return output("RELY")


def reference_composition(packet: dict[str, Any]) -> dict[str, Any]:
    labels: list[str] = []
    hard_block = False
    uncertain = False

    probe = packet["exact_probe"]
    if probe["status"] == "FAIL" and probe["head_current"]:
        labels.append("REQUALIFY_OPERATION")
        hard_block = True
    elif (
        probe["status"] != "PASS"
        or not probe["binding_matches"]
        or not probe["head_current"]
    ):
        labels.append("REQUALIFY_OPERATION")
        uncertain = True

    permission = packet["permission"]
    if permission["status"] == "REVOKED" and permission["head_current"]:
        labels.append("REAUTHORIZE")
        hard_block = True
    elif permission["status"] != "ACTIVE" or not permission["head_current"]:
        labels.append("REAUTHORIZE")
        uncertain = True

    reservation = packet["reservation"]
    if reservation["required"]:
        if reservation["status"] == "CONFLICT" and reservation["current"]:
            labels.append("RE_RESERVE")
            hard_block = True
        elif reservation["status"] != "VALID" or not reservation["current"]:
            labels.append("RE_RESERVE")
            uncertain = True

    if packet["telemetry"] == "SHIFTED":
        labels.append("REQUALIFY_OPERATION")
        uncertain = True
    if packet["attestation"] != "CURRENT":
        labels.append("REATTEST")
        uncertain = True
    if packet["recovery_evidence"] != "PASS":
        labels.append("RECOVERY_REHEARSAL")
        uncertain = True

    dependency = packet["dependency"]
    if not dependency["query_supported"] and dependency["kind"] in {
        "HIDDEN",
        "DECLARED",
    }:
        labels.append("GLOBAL_REOPEN")
        uncertain = True
    elif dependency["query_supported"]:
        if dependency["query_result"] == "REVOKED":
            labels.append("REAUTHORIZE_DEPENDENCY")
            hard_block = True
        elif dependency["query_result"] != "ACTIVE":
            labels.append("GLOBAL_REOPEN")
            uncertain = True

    human = packet["human"]
    if human["required"]:
        if human["owner_stance"] == "REFUSE":
            labels.append("HUMAN_AMEND")
            hard_block = True
        elif human["owner_stance"] != "APPROVE":
            labels.append("HUMAN_AMEND")
            uncertain = True

    if hard_block:
        return output("BLOCK", labels)
    if uncertain:
        return output("ABSTAIN", labels)
    return output("RELY")


POLICIES = {
    "DECLARATION_ONLY": declaration_only,
    "READINESS_ONLY": readiness_only,
    "PROBE_CI_IAM": probe_ci_iam,
    "REFERENCE_COMPOSITION_HITL": reference_composition,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True, choices=sorted(POLICIES))
    args = parser.parse_args()
    raw = sys.stdin.buffer.read()
    payload = json.loads(raw)
    if set(payload) != ALLOWED_TOP_LEVEL:
        raise SystemExit("invalid worker payload boundary")
    lowered = raw.decode("utf-8").lower()
    if any(text in lowered for text in FORBIDDEN_TEXT):
        raise SystemExit("truth-bearing text reached worker")
    result = POLICIES[args.method](payload["method_packet"])
    result["opaque_packet_id"] = payload["opaque_packet_id"]
    sys.stdout.write(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
