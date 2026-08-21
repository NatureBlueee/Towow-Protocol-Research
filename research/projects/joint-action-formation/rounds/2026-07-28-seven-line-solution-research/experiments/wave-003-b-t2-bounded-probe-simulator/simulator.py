#!/usr/bin/env python3
"""Deterministic synthetic T2 bounded-probe runner.

This runner models execution truth only. It emits ActionAttempt and
buyer-domain witness as separate objects and never decides capability, Effect,
Adoption, Acceptance, or relation formation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "probe_input.json"
DEFAULT_SCENARIOS = BASE_DIR / "scenario_truth.json"
SCENARIO_IDS = {
    "success",
    "environment_mismatch",
    "credential_revoked_mid_run",
    "audit_witness_missing",
    "duplicate_retry"
}


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_probe_input(probe_input: dict[str, Any]) -> None:
    if probe_input.get("kind") != "SYNTHETIC_BOUNDED_PROBE_INPUT":
        raise ValueError("input kind must be SYNTHETIC_BOUNDED_PROBE_INPUT")
    if probe_input.get("evidence_level") != "ARCHIVAL_DESIGN_DERIVED_SYNTHETIC":
        raise ValueError("input must retain the synthetic evidence boundary")
    binding = probe_input.get("binding", {})
    for key in ("executor", "environment", "version", "permission", "resource"):
        if key not in binding:
            raise ValueError(f"binding.{key} is required")
    queries = probe_input.get("queries")
    if not isinstance(queries, list) or len(queries) != 3:
        raise ValueError("exactly three queries are required")
    query_ids = [query.get("query_id") for query in queries]
    if len(set(query_ids)) != 3 or None in query_ids:
        raise ValueError("the three query IDs must be unique and non-null")
    permission = binding["permission"]
    if permission.get("allowed_query_ids") != query_ids:
        raise ValueError("permission must bind the exact ordered query set")
    if binding["resource"].get("query_budget") != 3:
        raise ValueError("resource query_budget must equal three")
    for query in queries:
        if query.get("mode") != "AGGREGATE_READ_ONLY":
            raise ValueError("all queries must be AGGREGATE_READ_ONLY")
        if query.get("approved") is not True:
            raise ValueError("all queries must be explicitly approved")
        if query.get("raw_rows_returned") is not False:
            raise ValueError("raw rows are forbidden")
    if permission.get("state_at_start") != "ACTIVE":
        raise ValueError("the frozen probe starts with active bounded permission")
    if permission.get("repeat_run_authorized") is not False:
        raise ValueError("the frozen permission must not authorize repeat runs")
    if probe_input["audit_requirement"].get("buyer_domain_witness_required") is not True:
        raise ValueError("buyer-domain witness must be required")
    if probe_input["audit_requirement"].get("producer_evidence_is_sufficient") is not False:
        raise ValueError("producer evidence cannot close the buyer witness")


def validate_scenarios(scenario_truth: dict[str, Any]) -> None:
    if scenario_truth.get("kind") != "SYNTHETIC_EXECUTION_BRANCH_TRUTH":
        raise ValueError("scenario kind must be SYNTHETIC_EXECUTION_BRANCH_TRUTH")
    scenarios = scenario_truth.get("scenarios")
    if not isinstance(scenarios, list):
        raise ValueError("scenarios must be a list")
    ids = [scenario.get("scenario_id") for scenario in scenarios]
    if set(ids) != SCENARIO_IDS or len(ids) != len(SCENARIO_IDS):
        raise ValueError("the five required scenarios must be frozen exactly once")
    if scenario_truth.get("evidence_boundary", {}).get("synthetic_only") is not True:
        raise ValueError("scenario truth must remain synthetic-only")


def _query_output_hash(
    input_hash: str,
    scenario_id: str,
    query: dict[str, Any]
) -> str:
    synthetic_output_descriptor = {
        "input_sha256": input_hash,
        "scenario_id": scenario_id,
        "query_id": query["query_id"],
        "operation": query["operation"],
        "synthetic_aggregate_fixture_version": "T2-W003-B-DATA-001",
        "raw_rows": []
    }
    return sha256_value(synthetic_output_descriptor)


def _attempt_id(
    probe_input: dict[str, Any],
    scenario: dict[str, Any],
    suffix: str
) -> str:
    seed = {
        "probe_id": probe_input["probe_id"],
        "scenario_id": scenario["scenario_id"],
        "idempotency_key": probe_input["idempotency"]["key"],
        "suffix": suffix
    }
    return "ATT-" + sha256_value(seed)[:24]


def _primary_action_attempt(
    probe_input: dict[str, Any],
    scenario: dict[str, Any],
    input_hash: str
) -> dict[str, Any]:
    binding = probe_input["binding"]
    query_ids = [query["query_id"] for query in probe_input["queries"]]
    observed_environment = scenario["observed_environment_version"]
    expected_environment = binding["environment"]["environment_version"]
    credential_event = scenario["credential_event"]

    if observed_environment != expected_environment:
        executed_query_ids: list[str] = []
        status = "BLOCKED_PRE_EXECUTION"
        stop_reason = "ENVIRONMENT_VERSION_MISMATCH"
        container_started = False
        exit_status: int | None = None
    elif credential_event == "REVOKED_AFTER_QUERY_2":
        executed_query_ids = query_ids[:2]
        status = "ABORTED_CREDENTIAL_REVOKED"
        stop_reason = "CREDENTIAL_REVOKED_BEFORE_QUERY_3"
        container_started = True
        exit_status = 75
    else:
        executed_query_ids = query_ids
        status = "COMPLETED"
        stop_reason = None
        container_started = True
        exit_status = 0

    query_by_id = {
        query["query_id"]: query for query in probe_input["queries"]
    }
    output_hashes = {
        query_id: _query_output_hash(
            input_hash,
            scenario["scenario_id"],
            query_by_id[query_id]
        )
        for query_id in executed_query_ids
    }
    return {
        "schema_version": "1.0",
        "domain": "ACTION_EXECUTOR",
        "attempt_id": _attempt_id(probe_input, scenario, "primary"),
        "probe_id": probe_input["probe_id"],
        "scenario_id": scenario["scenario_id"],
        "status": status,
        "new_execution": container_started,
        "binding_snapshot": copy.deepcopy(binding),
        "requested_query_ids": query_ids,
        "executed_query_ids": executed_query_ids,
        "stop_reason": stop_reason,
        "producer_evidence": {
            "container_started": container_started,
            "exit_status": exit_status,
            "query_output_hashes": output_hashes,
            "producer_evidence_establishes_buyer_effect": False
        }
    }


def _primary_buyer_witness(
    probe_input: dict[str, Any],
    scenario: dict[str, Any],
    action_attempt: dict[str, Any]
) -> dict[str, Any]:
    if scenario["audit_mode"] == "MISSING":
        return {
            "schema_version": "1.0",
            "domain": "BUYER_CONTROLLED_AUDIT",
            "status": "MISSING",
            "new_witness": False,
            "audit_channel": probe_input["binding"]["resource"]["buyer_audit_channel"],
            "observed_attempt_id": None,
            "observed_environment_version": None,
            "observed_query_ids": [],
            "query_output_hashes": {},
            "raw_row_export_count": None,
            "credential_events": [],
            "missing_reason": "BUYER_AUDIT_RECEIPT_NOT_EMITTED"
        }

    attempted_query_ids = action_attempt["executed_query_ids"]
    output_hashes = action_attempt["producer_evidence"]["query_output_hashes"]
    credential_events = [
        {
            "credential_id": probe_input["binding"]["permission"]["credential_id"],
            "event": scenario["credential_event"]
        }
    ]
    witness_seed = {
        "attempt_id": action_attempt["attempt_id"],
        "scenario_id": scenario["scenario_id"],
        "domain": "BUYER_CONTROLLED_AUDIT"
    }
    return {
        "schema_version": "1.0",
        "domain": "BUYER_CONTROLLED_AUDIT",
        "status": "PRESENT",
        "new_witness": True,
        "audit_receipt_id": "BAUD-" + sha256_value(witness_seed)[:24],
        "audit_channel": probe_input["binding"]["resource"]["buyer_audit_channel"],
        "observed_attempt_id": action_attempt["attempt_id"],
        "observed_environment_version": scenario["observed_environment_version"],
        "observed_query_ids": attempted_query_ids,
        "query_output_hashes": output_hashes,
        "raw_row_export_count": 0,
        "credential_events": credential_events,
        "missing_reason": None
    }


def _recovery(
    probe_input: dict[str, Any],
    scenario: dict[str, Any]
) -> dict[str, Any]:
    state = scenario["recovery_state"]
    if state == "NO_RECOVERY_REQUIRED":
        return {
            "state": state,
            "retry_allowed": False,
            "retry_condition": "NEW_RUN_REQUIRES_FRESH_PERMISSION_AND_IDEMPOTENCY_KEY",
            "must_revalidate": []
        }
    if state == "STOP_AND_REBIND_ENVIRONMENT":
        required = [
            "environment_id",
            "environment_version",
            "container_digest",
            "permission",
            "resource"
        ]
        retry_allowed = True
        condition = "REBIND_EXACT_ENVIRONMENT_AND_ISSUE_NEW_AUTHORIZED_RUN"
    elif state == "STOP_AND_REQUIRE_NEW_AUTHORIZATION":
        required = [
            "credential",
            "permission",
            "allowed_query_ids",
            "container_digest",
            "environment_version",
            "resource"
        ]
        retry_allowed = False
        condition = "NEW_BUYER_DATA_AUTHORIZATION_REQUIRED"
    elif state == "STOP_QUALIFICATION_AND_REPAIR_AUDIT_CHANNEL":
        required = [
            "buyer_audit_channel",
            "buyer_audit_receipt",
            "current_permission",
            "idempotency_disposition"
        ]
        retry_allowed = False
        condition = "DO_NOT_RERUN_QUERY_EFFECTS_WITHOUT_NEW_AUTHORIZED_IDEMPOTENCY_KEY"
    else:
        required = []
        retry_allowed = False
        condition = probe_input["idempotency"]["duplicate_policy"]
    return {
        "state": state,
        "retry_allowed": retry_allowed,
        "retry_condition": condition,
        "must_revalidate": required
    }


def _hash_receipt(
    probe_input: dict[str, Any],
    scenario: dict[str, Any],
    action_attempt: dict[str, Any],
    buyer_witness: dict[str, Any],
    idempotency: dict[str, Any],
    recovery: dict[str, Any],
    prior_receipt_hash: str | None
) -> dict[str, Any]:
    body = {
        "probe_input_sha256": sha256_value(probe_input),
        "scenario_sha256": sha256_value(scenario),
        "action_attempt_sha256": sha256_value(action_attempt),
        "buyer_domain_witness_sha256": sha256_value(buyer_witness),
        "idempotency_sha256": sha256_value(idempotency),
        "recovery_sha256": sha256_value(recovery),
        "prior_receipt_sha256": prior_receipt_hash
    }
    return {
        **body,
        "receipt_sha256": sha256_value(body)
    }


def _result(
    probe_input: dict[str, Any],
    scenario: dict[str, Any],
    action_attempt: dict[str, Any],
    buyer_witness: dict[str, Any],
    idempotency: dict[str, Any],
    recovery: dict[str, Any],
    prior_receipt_hash: str | None = None
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "kind": "SYNTHETIC_BOUNDED_PROBE_RESULT",
        "probe_id": probe_input["probe_id"],
        "scenario_id": scenario["scenario_id"],
        "action_attempt": action_attempt,
        "buyer_domain_witness": buyer_witness,
        "idempotency": idempotency,
        "recovery": recovery,
        "hash_receipt": _hash_receipt(
            probe_input,
            scenario,
            action_attempt,
            buyer_witness,
            idempotency,
            recovery,
            prior_receipt_hash
        ),
        "evidence_boundary": {
            "synthetic_only": True,
            "real_action_attempt": False,
            "real_buyer_witness": False,
            "capability_conclusion": "NOT_DECIDED_BY_THIS_RUNNER",
            "effect_conclusion": "NOT_DECIDED_BY_THIS_RUNNER",
            "relation_conclusion": "NOT_DECIDED_BY_THIS_RUNNER"
        }
    }


def _simulate_primary(
    probe_input: dict[str, Any],
    scenario: dict[str, Any]
) -> dict[str, Any]:
    input_hash = sha256_value(probe_input)
    action_attempt = _primary_action_attempt(probe_input, scenario, input_hash)
    buyer_witness = _primary_buyer_witness(
        probe_input, scenario, action_attempt
    )
    idempotency = {
        "key": probe_input["idempotency"]["key"],
        "decision": (
            "EXECUTED_NEW_ATTEMPT"
            if action_attempt["new_execution"]
            else "RECORDED_PRE_EXECUTION_BLOCK"
        ),
        "new_execution": action_attempt["new_execution"],
        "new_witness": buyer_witness["new_witness"],
        "prior_receipt_sha256": None
    }
    return _result(
        probe_input,
        scenario,
        action_attempt,
        buyer_witness,
        idempotency,
        _recovery(probe_input, scenario)
    )


def simulate(
    probe_input: dict[str, Any],
    scenario_truth: dict[str, Any],
    scenario_id: str
) -> dict[str, Any]:
    validate_probe_input(probe_input)
    validate_scenarios(scenario_truth)
    scenarios = {
        item["scenario_id"]: item for item in scenario_truth["scenarios"]
    }
    if scenario_id not in scenarios:
        raise ValueError(f"unknown scenario: {scenario_id}")
    scenario = scenarios[scenario_id]
    if scenario_id != "duplicate_retry":
        return _simulate_primary(probe_input, scenario)

    prior_scenario = scenarios[scenario["preseed_scenario"]]
    prior_result = _simulate_primary(probe_input, prior_scenario)
    prior_receipt_hash = prior_result["hash_receipt"]["receipt_sha256"]
    prior_attempt = prior_result["action_attempt"]
    prior_witness = prior_result["buyer_domain_witness"]
    action_attempt = {
        "schema_version": "1.0",
        "domain": "ACTION_EXECUTOR",
        "attempt_id": _attempt_id(probe_input, scenario, "duplicate"),
        "probe_id": probe_input["probe_id"],
        "scenario_id": scenario_id,
        "status": "DEDUPLICATED_REPLAY",
        "new_execution": False,
        "binding_snapshot": copy.deepcopy(probe_input["binding"]),
        "requested_query_ids": [
            query["query_id"] for query in probe_input["queries"]
        ],
        "executed_query_ids": [],
        "stop_reason": "IDEMPOTENCY_KEY_ALREADY_COMPLETED",
        "producer_evidence": {
            "container_started": False,
            "exit_status": None,
            "query_output_hashes": {},
            "producer_evidence_establishes_buyer_effect": False,
            "prior_attempt_sha256": sha256_value(prior_attempt)
        }
    }
    buyer_witness = {
        "schema_version": "1.0",
        "domain": "BUYER_CONTROLLED_AUDIT",
        "status": "REUSED_PRIOR_WITNESS",
        "new_witness": False,
        "audit_channel": probe_input["binding"]["resource"]["buyer_audit_channel"],
        "prior_witness_sha256": sha256_value(prior_witness),
        "prior_audit_receipt_id": prior_witness["audit_receipt_id"],
        "observed_attempt_id": None,
        "observed_environment_version": None,
        "observed_query_ids": [],
        "query_output_hashes": {},
        "raw_row_export_count": None,
        "credential_events": [],
        "missing_reason": None
    }
    idempotency = {
        "key": probe_input["idempotency"]["key"],
        "decision": "RETURN_PRIOR_RECEIPT_WITHOUT_NEW_EXECUTION",
        "new_execution": False,
        "new_witness": False,
        "prior_receipt_sha256": prior_receipt_hash
    }
    return _result(
        probe_input,
        scenario,
        action_attempt,
        buyer_witness,
        idempotency,
        _recovery(probe_input, scenario),
        prior_receipt_hash
    )


def verify_result_receipt(
    result: dict[str, Any],
    probe_input: dict[str, Any],
    scenario_truth: dict[str, Any]
) -> bool:
    scenarios = {
        item["scenario_id"]: item for item in scenario_truth["scenarios"]
    }
    scenario = scenarios[result["scenario_id"]]
    expected = _hash_receipt(
        probe_input,
        scenario,
        result["action_attempt"],
        result["buyer_domain_witness"],
        result["idempotency"],
        result["recovery"],
        result["idempotency"].get("prior_receipt_sha256")
    )
    return expected == result["hash_receipt"]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scenario", choices=sorted(SCENARIO_IDS))
    group.add_argument("--all", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()

    probe_input = load_json(args.input)
    scenario_truth = load_json(args.scenarios)
    if args.all:
        if args.output_dir is None:
            parser.error("--all requires --output-dir")
        for scenario_id in sorted(SCENARIO_IDS):
            write_json(
                args.output_dir / f"{scenario_id}.json",
                simulate(probe_input, scenario_truth, scenario_id)
            )
        return 0
    result = simulate(probe_input, scenario_truth, args.scenario)
    if args.output is not None:
        write_json(args.output, result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
