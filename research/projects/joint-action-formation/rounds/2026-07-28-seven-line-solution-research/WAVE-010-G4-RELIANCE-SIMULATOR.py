#!/usr/bin/env python3
"""Method-neutral evaluator for the Wave 010 G4 synthetic fixture.

Policies receive only method_packet. Ground truth is read only by score().
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "WAVE-010-G4-RELIANCE-FIXTURE.json"

Decision = dict[str, str]
Policy = Callable[[dict[str, Any]], Decision]


def decision(state: str, recovery: str = "NONE") -> Decision:
    return {"decision": state, "recovery_action": recovery}


def declaration_only(packet: dict[str, Any]) -> Decision:
    if packet["declaration"] == "ACTIVE":
        return decision("RELY")
    return decision("ABSTAIN")


def readiness_only(packet: dict[str, Any]) -> Decision:
    if packet["readiness"] == "HEALTHY":
        return decision("RELY")
    return decision("BLOCK", "RECOVER_SERVICE")


def probe_ci_iam(packet: dict[str, Any]) -> Decision:
    probe = packet["exact_probe"]
    permission = packet["permission"]
    if permission["status"] == "REVOKED" and permission["head_current"]:
        return decision("BLOCK", "REAUTHORIZE")
    if permission["status"] != "ACTIVE" or not permission["head_current"]:
        return decision("ABSTAIN", "REAUTHORIZE")
    if probe["status"] == "FAIL" and probe["head_current"]:
        return decision("BLOCK", "REQUALIFY_OPERATION")
    if (
        probe["status"] != "PASS"
        or not probe["binding_matches"]
        or not probe["head_current"]
    ):
        return decision("ABSTAIN", "REQUALIFY_OPERATION")
    return decision("RELY")


def mature_composition(packet: dict[str, Any]) -> Decision:
    probe_decision = probe_ci_iam(packet)
    if probe_decision["decision"] != "RELY":
        return probe_decision

    reservation = packet["reservation"]
    if reservation["required"]:
        if reservation["status"] == "CONFLICT" and reservation["current"]:
            return decision("BLOCK", "RE_RESERVE")
        if reservation["status"] != "VALID" or not reservation["current"]:
            return decision("ABSTAIN", "RE_RESERVE")

    if packet["telemetry"] == "SHIFTED":
        return decision("ABSTAIN", "REQUALIFY_OPERATION")
    if packet["attestation"] != "CURRENT":
        return decision("ABSTAIN", "REATTEST")
    if packet["recovery_evidence"] != "PASS":
        return decision("ABSTAIN", "RECOVERY_REHEARSAL")

    dependency = packet["dependency"]
    if dependency["kind"] == "HIDDEN" and not dependency["query_supported"]:
        return decision("ABSTAIN", "GLOBAL_REOPEN")
    if dependency["query_supported"]:
        if dependency["query_result"] == "REVOKED":
            return decision("BLOCK", "REAUTHORIZE_DEPENDENCY")
        if dependency["query_result"] != "ACTIVE":
            return decision("ABSTAIN", "GLOBAL_REOPEN")

    human = packet["human"]
    if human["required"]:
        if human["owner_stance"] == "REFUSE":
            return decision("BLOCK", "HUMAN_AMEND")
        if human["owner_stance"] != "APPROVE":
            return decision("ABSTAIN", "HUMAN_AMEND")

    return decision("RELY")


def strong_center(packet: dict[str, Any]) -> Decision:
    # Same lawful observations and actions imply the same causal policy here.
    return mature_composition(packet)


def human_interface(packet: dict[str, Any]) -> Decision:
    human = packet["human"]
    if human["required"] and human["owner_stance"] == "UNKNOWN":
        return decision("ABSTAIN", "HUMAN_AMEND")
    if human["required"] and human["owner_stance"] == "REFUSE":
        return decision("BLOCK", "HUMAN_AMEND")
    if packet["declaration"] == "ACTIVE":
        return decision("RELY")
    return decision("ABSTAIN")


POLICIES: dict[str, Policy] = {
    "DECLARATION_ONLY": declaration_only,
    "READINESS_ONLY": readiness_only,
    "PROBE_CI_IAM": probe_ci_iam,
    "MATURE_COMPOSITION_HITL": mature_composition,
    "LAWFUL_STRONG_CENTER": strong_center,
    "HUMAN_INTERFACE_ONLY": human_interface,
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def world_index(fixture: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {world["world_id"]: world for world in fixture["worlds"]}


def differing_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix]
    if isinstance(left, dict):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left or key not in right:
                paths.append(path)
            else:
                paths.extend(differing_paths(left[key], right[key], path))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [prefix]
        paths = []
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            paths.extend(differing_paths(left_item, right_item, f"{prefix}[{index}]"))
        return paths
    return [] if left == right else [prefix]


def score(fixture: dict[str, Any]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for policy_name, policy in POLICIES.items():
        tp = fp = tn = fn = abstain = 0
        false_commitments: list[str] = []
        drift_unsafe_total = 0
        drift_unsafe_detected = 0
        recovery_total = 0
        recovery_correct = 0
        per_world: dict[str, Decision] = {}

        for world in fixture["worlds"]:
            output = policy(copy.deepcopy(world["method_packet"]))
            truth = world["private_oracle"]
            safe = truth["safe_to_rely"]
            relies = output["decision"] == "RELY"
            if output["decision"] == "ABSTAIN":
                abstain += 1
            if safe and relies:
                tp += 1
            elif safe and not relies:
                fn += 1
            elif not safe and relies:
                fp += 1
                false_commitments.append(world["world_id"])
            else:
                tn += 1

            if world["drift_case"] and not safe:
                drift_unsafe_total += 1
                if not relies:
                    drift_unsafe_detected += 1

            if not safe:
                recovery_total += 1
                if (
                    not relies
                    and output["recovery_action"]
                    == truth["required_recovery_action"]
                ):
                    recovery_correct += 1

            per_world[world["world_id"]] = output

        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        results[policy_name] = {
            "confusion": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
            "precision": precision,
            "recall": recall,
            "abstention_rate": abstain / len(fixture["worlds"]),
            "false_commitment_count": fp,
            "false_commitment_worlds": false_commitments,
            "drift_unsafe_detection_recall": (
                drift_unsafe_detected / drift_unsafe_total
                if drift_unsafe_total
                else None
            ),
            "recovery_action_accuracy_on_unsafe": (
                recovery_correct / recovery_total if recovery_total else None
            ),
            "per_world": per_world,
        }
    return results


def run_invariance_checks(
    fixture: dict[str, Any], results: dict[str, Any]
) -> list[dict[str, Any]]:
    worlds = world_index(fixture)
    checks: list[dict[str, Any]] = []
    for check in fixture["invariance_checks"]:
        left = worlds[check["left"]]["method_packet"]
        right = worlds[check["right"]]["method_packet"]
        paths = differing_paths(left, right)
        if check["id"] == "HIDDEN-PAIR-IDENTICAL-METHOD-PACKETS":
            passed = paths == []
            same_policy_outputs = all(
                result["per_world"][check["left"]]
                == result["per_world"][check["right"]]
                for result in results.values()
            )
            passed = passed and same_policy_outputs
        else:
            passed = paths == [check["allowed_difference_path"]]
        checks.append(
            {
                "id": check["id"],
                "passed": passed,
                "observed_difference_paths": paths,
            }
        )
    return checks


def build_report() -> dict[str, Any]:
    fixture = load_fixture()
    results = score(fixture)
    checks = run_invariance_checks(fixture, results)
    return {
        "fixture_id": fixture["fixture_id"],
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "world_count": len(fixture["worlds"]),
        "task_counts": {
            task: sum(1 for world in fixture["worlds"] if world["task_family"] == task)
            for task in ("T2", "T4", "T6")
        },
        "policies": results,
        "invariance_checks": checks,
        "evidence_boundary": fixture["evidence_boundary"],
    }


def self_test(report: dict[str, Any]) -> None:
    assert report["world_count"] == 12
    assert report["task_counts"] == {"T2": 4, "T4": 3, "T6": 5}
    assert all(check["passed"] for check in report["invariance_checks"])
    mature = report["policies"]["MATURE_COMPOSITION_HITL"]
    center = report["policies"]["LAWFUL_STRONG_CENTER"]
    assert mature == center
    assert mature["false_commitment_count"] == 0
    assert mature["precision"] == 1.0
    assert mature["recall"] == 0.75
    assert mature["drift_unsafe_detection_recall"] == 1.0
    assert mature["recovery_action_accuracy_on_unsafe"] == 1.0
    assert report["policies"]["PROBE_CI_IAM"]["false_commitment_count"] == 5
    hidden_left = "T6-HIDDEN-DEPENDENCY-VALID"
    hidden_right = "T6-HIDDEN-DEPENDENCY-REVOKED"
    for policy_result in report["policies"].values():
        assert policy_result["per_world"][hidden_left] == policy_result["per_world"][
            hidden_right
        ]


def compact(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": report["fixture_id"],
        "fixture_sha256": report["fixture_sha256"],
        "world_count": report["world_count"],
        "task_counts": report["task_counts"],
        "metrics": {
            policy: {
                key: values[key]
                for key in (
                    "confusion",
                    "precision",
                    "recall",
                    "abstention_rate",
                    "false_commitment_count",
                    "drift_unsafe_detection_recall",
                    "recovery_action_accuracy_on_unsafe",
                )
            }
            for policy, values in report["policies"].items()
        },
        "invariance_checks": report["invariance_checks"],
        "evidence_boundary": report["evidence_boundary"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    report = build_report()
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
