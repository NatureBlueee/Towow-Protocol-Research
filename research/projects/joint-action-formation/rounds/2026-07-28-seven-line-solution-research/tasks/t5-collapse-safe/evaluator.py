#!/usr/bin/env python3
"""Evidence-based evaluator for the T5 collapse-safe negative control."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

from platform_simulator import execute


ROOT = Path(__file__).resolve().parent
INPUT = json.loads((ROOT / "input.json").read_text(encoding="utf-8"))
SCHEMA = json.loads(
    (ROOT / "submission.schema.json").read_text(encoding="utf-8")
)
ADAPTER_PROGRAM_PATH = ROOT / "adapter_program.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def exact_disclosures(items: list[dict[str, Any]]) -> bool:
    def normalized(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            [
                {
                    "recipient": item["recipient"],
                    "purpose": item["purpose"],
                    "retention": item["retention"],
                    "fields": sorted(item["fields"]),
                }
                for item in values
            ],
            key=lambda item: (item["recipient"], item["purpose"]),
        )

    return normalized(items) == normalized(INPUT["minimal_disclosures"])


def disclosures_from_trace(method_execution: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "recipient": event["recipient"],
            "purpose": event["purpose"],
            "retention": event["retention"],
            "fields": event["fields"],
        }
        for event in method_execution["trace"].get("events", [])
        if event.get("kind") == "DISCLOSURE_FORWARD"
    ]


def execute_method(candidate: dict[str, Any]) -> dict[str, Any]:
    """Execute the only supported adapter runtime or the direct path.

    Candidate names and self-descriptions are deliberately ignored. A
    lightweight adapter is evidence-bearing only when it binds the exact
    artifact bytes and the evaluator can interpret that artifact in the
    bounded JSON-transducer runtime.
    """

    if candidate["path_kind"] == "DIRECT":
        verified = candidate["adapter"] == {
            "id": None,
            "artifact_sha256": None,
        }
        return {
            "verified": verified,
            "program_hash": None,
            "operations": candidate["operations"] if verified else [],
            "disclosures": candidate["disclosures"] if verified else [],
            "trace": {
                "runtime": "DIRECT",
                "executed": verified,
                "authoritative": False,
                "writes_state": False,
                "caches_state": False,
                "transforms_semantics": False,
                "added_approvals": 0,
                "added_wait_units": 0,
                "added_governance_objects": 0,
                "added_recovery_systems": 0,
                "events": [
                    {
                        "kind": "DISCLOSURE_FORWARD",
                        "index": index,
                        "recipient": item["recipient"],
                        "purpose": item["purpose"],
                        "retention": item["retention"],
                        "fields": sorted(item["fields"]),
                        "recipient_allowed": True,
                    }
                    for index, item in enumerate(candidate["disclosures"])
                ]
                if verified
                else [],
            },
        }

    program_bytes = ADAPTER_PROGRAM_PATH.read_bytes()
    program_hash = sha256_bytes(program_bytes)
    adapter = candidate["adapter"]
    if adapter["artifact_sha256"] != program_hash:
        return {
            "verified": False,
            "program_hash": program_hash,
            "operations": [],
            "disclosures": [],
            "trace": {
                "runtime": "UNVERIFIED",
                "executed": False,
                "reason": "ARTIFACT_HASH_MISMATCH",
                "events": [],
            },
        }

    program = json.loads(program_bytes)
    expected_program = {
        "schema_version": "1.0",
        "runtime": "T5_BOUNDED_JSON_TRANSDUCER_V1",
        "operation_mapping": "IDENTITY",
        "input_projection": "IDENTITY",
        "authority_projection": "PRESERVE",
        "disclosure_projection": "IDENTITY",
        "persistence": "NONE",
        "cache": "NONE",
        "semantic_transform": "NONE",
        "allowed_recipients": [
            "BUYER-APPROVER-1",
            "STANDARD-SAAS-PLATFORM",
        ],
        "added_wait_units": 0,
        "added_approvals": 0,
        "added_governance_objects": 0,
        "added_recovery_systems": 0,
        "failure_policy": "PASS_AUTHORITATIVE_TERMINAL_NO_RETRY",
    }
    if program != expected_program:
        return {
            "verified": False,
            "program_hash": program_hash,
            "operations": [],
            "disclosures": [],
            "trace": {
                "runtime": "UNSUPPORTED",
                "executed": False,
                "reason": "PROGRAM_SEMANTICS_NOT_SUPPORTED",
                "events": [],
            },
        }

    operation_events = [
        {
            "kind": "OPERATION_FORWARD",
            "index": index,
            "op": item["op"],
            "authority_source": item["authority_source"],
            "inputs_hash": canonical_hash(item["inputs"]),
            "storage_write": False,
            "cache_write": False,
            "semantic_transform": False,
        }
        for index, item in enumerate(candidate["operations"])
    ]
    disclosure_events = [
        {
            "kind": "DISCLOSURE_FORWARD",
            "index": index,
            "recipient": item["recipient"],
            "purpose": item["purpose"],
            "retention": item["retention"],
            "fields": sorted(item["fields"]),
            "recipient_allowed": item["recipient"] in program["allowed_recipients"],
        }
        for index, item in enumerate(candidate["disclosures"])
    ]
    recipients_allowed = all(
        event["recipient_allowed"] for event in disclosure_events
    )
    return {
        "verified": recipients_allowed,
        "program_hash": program_hash,
        "operations": json.loads(json.dumps(candidate["operations"])),
        "disclosures": json.loads(json.dumps(candidate["disclosures"])),
        "trace": {
            "runtime": program["runtime"],
            "executed": True,
            "authoritative": False,
            "writes_state": any(
                event["storage_write"] for event in operation_events
            ),
            "caches_state": any(
                event["cache_write"] for event in operation_events
            ),
            "transforms_semantics": any(
                event["semantic_transform"] for event in operation_events
            ),
            "added_approvals": program["added_approvals"],
            "added_wait_units": program["added_wait_units"],
            "added_governance_objects": program[
                "added_governance_objects"
            ],
            "added_recovery_systems": program["added_recovery_systems"],
            "events": operation_events + disclosure_events,
        },
    }


def derived_cost(method_execution: dict[str, Any]) -> dict[str, int]:
    trace = method_execution["trace"]
    if not method_execution["verified"]:
        return {
            "external_wait_units": INPUT["baseline_cost_ceiling"][
                "external_wait_units"
            ]
            + 1,
            "human_decisions": INPUT["baseline_cost_ceiling"][
                "human_decisions"
            ]
            + 1,
            "cognitive_units": INPUT["baseline_cost_ceiling"][
                "cognitive_units"
            ]
            + 1,
            "governance_objects": INPUT["baseline_cost_ceiling"][
                "governance_objects"
            ]
            + 1,
            "extra_recovery_systems": INPUT["baseline_cost_ceiling"][
                "extra_recovery_systems"
            ]
            + 1,
        }
    return {
        "external_wait_units": 2 + trace["added_wait_units"],
        "human_decisions": 1 + trace["added_approvals"],
        "cognitive_units": len(method_execution["operations"]),
        "governance_objects": trace["added_governance_objects"],
        "extra_recovery_systems": trace["added_recovery_systems"],
    }


def execute_failure_handler(
    run: dict[str, Any],
    handler: str,
    expected_failure: str,
) -> dict[str, Any]:
    """Interpret the bounded handler and expose its actual recovery trace."""

    valid_predecessor = (
        run.get("status") == expected_failure
        and bool(run.get("events"))
        and all(event.get("valid") is True for event in run["events"])
    )
    if handler != "READ_PLATFORM_STATE_AND_STOP" or not valid_predecessor:
        return {
            "executed": False,
            "valid": False,
            "events": [],
            "reason": "HANDLER_OR_PREDECESSOR_INVALID",
        }
    readback = {
        "op": "READ_PLATFORM_STATE",
        "authority_source": INPUT["platform"]["id"],
        "observed_terminal": run["status"],
        "state_hash": canonical_hash(run["state"]),
    }
    stop = {
        "op": "STOP",
        "retry": False,
        "side_effects_after_terminal": 0,
    }
    return {
        "executed": True,
        "valid": True,
        "events": [readback, stop],
        "no_retry": True,
        "side_effects_after_terminal": 0,
    }


def invalid_result(candidate: dict[str, Any], schema_error: str) -> dict[str, Any]:
    return {
        "schema_version": "3.0",
        "task_id": INPUT["task_id"],
        "method_id": candidate.get("method_id"),
        "status": "INVALID",
        "schema_error": schema_error,
        "coverage": {
            "requirements_passed": 0,
            "requirements_total": 6,
            "ratio": 0.0,
        },
        "requirement_results": {},
        "evidence_boundary": "Synthetic negative control only.",
    }


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    try:
        jsonschema.validate(candidate, SCHEMA)
    except jsonschema.ValidationError as exc:
        return invalid_result(candidate, exc.message)

    method_execution = execute_method(candidate)
    executable_candidate = {
        **candidate,
        "operations": method_execution["operations"],
        "disclosures": method_execution["disclosures"],
    }
    success_run = execute(INPUT, executable_candidate, "NONE")
    failure_runs = {
        failure: execute(INPUT, executable_candidate, failure)
        for failure in INPUT["failure_branches"]
    }
    handler_runs = {
        failure: execute_failure_handler(
            run,
            candidate["failure_handling"][failure],
            failure,
        )
        for failure, run in failure_runs.items()
    }
    platform = INPUT["platform"]["id"]
    approver = INPUT["authority"]["buyer_approver"]
    authoritative_operations = all(
        (
            item["op"] == "REQUEST_BUYER_APPROVAL"
            and item["authority_source"] == approver
        )
        or (
            item["op"] != "REQUEST_BUYER_APPROVAL"
            and item["authority_source"] == platform
        )
        for item in method_execution["operations"]
    )
    trace = method_execution["trace"]
    adapter_non_authoritative = (
        method_execution["verified"]
        and trace.get("executed") is True
        and trace.get("authoritative") is False
        and trace.get("writes_state") is False
        and trace.get("caches_state") is False
        and trace.get("transforms_semantics") is False
    )
    cost = derived_cost(method_execution)
    within_cost = all(
        cost[key] <= ceiling
        for key, ceiling in INPUT["baseline_cost_ceiling"].items()
    )
    failure_truth = all(
        run.get("authoritative_source") == platform
        and run["status"] == failure
        and handler_runs[failure]["valid"] is True
        and handler_runs[failure]["no_retry"] is True
        and handler_runs[failure]["side_effects_after_terminal"] == 0
        for failure, run in failure_runs.items()
    )

    checks = {
        "R1": (
            success_run.get("postcondition_verified") is True
            and len(success_run["events"]) == 6,
            "The authoritative platform state machine reaches ACTIVE / 5 seats / ISSUED.",
        ),
        "R2": (
            authoritative_operations and adapter_non_authoritative,
            "Authority remains in the platform and buyer; adapter behavior comes from a hash-bound execution trace.",
        ),
        "R3": (
            method_execution["verified"]
            and exact_disclosures(disclosures_from_trace(method_execution)),
            "Observed disclosures exactly match recipient, purpose, retention and field allowlist.",
        ),
        "R4": (
            within_cost,
            "Trace-derived wait, human, cognition, governance and recovery costs do not exceed the platform baseline.",
        ),
        "R5": (
            failure_truth,
            "Each failure is actually reached after valid predecessors; authoritative readback then stops without retry.",
        ),
        "R6": (
            adapter_non_authoritative,
            "The method is direct or uses the executed, hash-bound, stateless non-authoritative transducer.",
        ),
    }
    results = {
        requirement: {
            "status": "PASS" if passed else "FAIL",
            "description": description,
        }
        for requirement, (passed, description) in checks.items()
    }
    passed = sum(item["status"] == "PASS" for item in results.values())
    return {
        "schema_version": "3.0",
        "task_id": INPUT["task_id"],
        "method_id": candidate["method_id"],
        "status": "PASS" if passed == 6 else "FAIL",
        "coverage": {
            "requirements_passed": passed,
            "requirements_total": 6,
            "ratio": passed / 6,
        },
        "requirement_results": results,
        "derived_cost": cost,
        "adapter_execution": method_execution,
        "success_receipts": [
            event["receipt_sha256"] for event in success_run["events"]
        ],
        "failure_terminals": {
            failure: run.get("status") for failure, run in failure_runs.items()
        },
        "failure_handler_traces": handler_runs,
        "evidence_boundary": (
            "This is a synthetic negative control. PASS means only that the "
            "candidate collapses to the existing platform under frozen inputs."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submission", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    candidate = json.loads(Path(args.submission).read_text(encoding="utf-8"))
    result = evaluate(candidate)
    rendered = json.dumps(
        result, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
