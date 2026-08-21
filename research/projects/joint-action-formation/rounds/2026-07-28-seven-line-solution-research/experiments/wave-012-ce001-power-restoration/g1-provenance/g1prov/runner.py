from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .evaluator import evaluate_trace, summarize
from .fixtures import EPISODE_IDS, make_world
from .model import canonical_bytes, digest
from .process_boundary import (
    PRIVATE_INPUT_CANARY,
    ProcessBoundaryViolation,
    WORKER_SOURCE,
    run_process_episode,
    run_same_user_path_probe,
)


FORBIDDEN_METHOD_INPUT_KEYS = {
    "l_benchmark",
    "d_actual",
    "correct_path",
    "t0_paths",
    "final_proposal",
    "private_expected_label",
}


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested
            for item in value.values()
            for nested in _all_keys(item)
        }
    if isinstance(value, (list, tuple)):
        return {
            nested
            for item in value
            for nested in _all_keys(item)
        }
    return set()


def validate_method_input(interface: dict[str, Any]) -> list[str]:
    forbidden_found = sorted(
        _all_keys(interface) & FORBIDDEN_METHOD_INPUT_KEYS
    )
    if forbidden_found:
        raise ValueError(
            f"method-visible input contains forbidden keys: {forbidden_found}"
        )
    return forbidden_found


def run_episode(
    episode_id: str,
    *,
    intervention: str = "T0_REPLAY",
    removed_operator: str | None = None,
    reversed_operator: str | None = None,
    failure_injection: str | None = None,
) -> dict[str, Any]:
    world = make_world(episode_id)
    if failure_injection == "SOURCE_ALIAS":
        resource_source = next(
            record["source_id"]
            for record in world.records
            if record["kind"] == "resource"
        )
        world.source_aliases["alias-of-resource-ledger"] = resource_source
    if reversed_operator:
        spec = next(
            operator
            for operator in world.operators
            if operator["operator_id"] == reversed_operator
        )
        reversed_record = {
            **spec["created_record"],
            "evidence_id": spec["created_record"]["evidence_id"] + "-REVERSED",
            "current": False,
        }
        world.expected[reversed_record["evidence_id"]] = reversed_record
        world.source_aliases[reversed_record["source_id"]] = reversed_record[
            "source_id"
        ]
    trace, process_receipt = run_process_episode(
        world,
        intervention=intervention,
        removed_operator=removed_operator,
        reversed_operator=reversed_operator,
        failure_injection=failure_injection,
    )
    forbidden_found = validate_method_input(world.interface)
    result = evaluate_trace(world, trace)
    result_core_sha256 = digest(result)
    result["process_boundary_receipt"] = process_receipt
    result["frozen_artifact_binding"] = {
        "source_bundle_sha256": digest(process_receipt["source_artifacts"]),
        "method_input_bytes_sha256": process_receipt["worker_inbound_scan"][
            "sha256"
        ],
        "raw_boundary_trace_sha256": process_receipt[
            "raw_boundary_trace_sha256"
        ],
        "raw_trace_sha256": digest(result["raw_trace"]),
        "result_core_sha256": result_core_sha256,
    }
    result["frozen_artifact_binding"]["sha256"] = digest(
        result["frozen_artifact_binding"]
    )
    result["method_visible_input_receipt"] = {
        "sha256": digest(world.interface),
        "forbidden_fields_absent": sorted(FORBIDDEN_METHOD_INPUT_KEYS),
        "recursive_scan_found": forbidden_found,
        "actual_inbound_bytes_sha256": process_receipt["worker_inbound_scan"][
            "sha256"
        ],
        "actual_inbound_forbidden_marker_hits": process_receipt[
            "worker_inbound_scan"
        ]["forbidden_marker_hits"],
        "private_canary_absent": process_receipt["worker_inbound_scan"][
            "private_canary_absent"
        ],
        "query_predicate_keys": sorted(
            {
                key
                for query in trace.queries
                for key in query["predicates"]
            }
        ),
    }
    if failure_injection:
        result["failure_injection"] = failure_injection
    return result


def run_process_identity_injection(injection: str) -> dict[str, Any]:
    """Run an actual child-process mismatch and retain the fail-closed receipt."""

    supported = {
        "OWNER_PID_MISMATCH",
        "WORKER_PID_MISMATCH",
        "ORIGIN_SELF_REPORT_INCONSISTENCY",
        "WRONG_SOURCE_INSTANCE",
    }
    if injection not in supported:
        raise ValueError(f"unsupported process identity injection: {injection}")
    world = make_world("E1-EXTANT-MULTI-OWNER")
    try:
        run_process_episode(
            world,
            intervention="PROCESS_IDENTITY_FAILURE_INJECTION",
            removed_operator=None,
            reversed_operator=None,
            failure_injection=injection,
        )
    except ProcessBoundaryViolation as exc:
        return {
            "injection": injection,
            "status": "FAIL_CLOSED",
            "reason": exc.code,
            "receipt": exc.receipt,
        }
    raise AssertionError(f"{injection} did not fail closed")


def _source_tree_receipt() -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    entries = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        raw = path.read_bytes()
        entries.append(
            {
                "path": str(path.relative_to(root)),
                "byte_length": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return entries


def _input_receipts() -> dict[str, Any]:
    public_entries = []
    private_entries = []
    for episode_id in EPISODE_IDS:
        world = make_world(episode_id)
        public_bytes = canonical_bytes(world.interface)
        private_bytes = canonical_bytes(
            {
                "episode_id": episode_id,
                "prelude": world.prelude,
                "expected": world.expected,
                "L_benchmark": world.l_benchmark,
                "D_actual": world.d_actual,
                "source_aliases": world.source_aliases,
                "authority_aliases": world.authority_aliases,
                "private_canary": PRIVATE_INPUT_CANARY,
            }
        )
        public_entries.append(
            {
                "episode_id": episode_id,
                "byte_length": len(public_bytes),
                "sha256": hashlib.sha256(public_bytes).hexdigest(),
            }
        )
        private_entries.append(
            {
                "episode_id": episode_id,
                "byte_length": len(private_bytes),
                "sha256": hashlib.sha256(private_bytes).hexdigest(),
            }
        )
    return {
        "public_input_bytes": public_entries,
        "private_evaluator_input_bytes": private_entries,
    }


def _result_groups(report: dict[str, Any]) -> list[dict[str, Any]]:
    return (
        list(report["baseline"])
        + list(report["operator_interventions"])
        + list(report["failure_injections"])
    )


def _identity_failure_trace_entries(
    report: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {
            "injection": result["injection"],
            "reason": result["reason"],
            "sha256": digest(result["receipt"]["raw_boundary_trace"]),
        }
        for result in report["process_identity_injections"]
    ]


def verify_frozen_manifest(report: dict[str, Any]) -> dict[str, Any]:
    manifest = report["frozen_manifest"]
    source_entries = _source_tree_receipt()
    input_receipts = _input_receipts()
    results = _result_groups(report)
    raw_boundary_entries = [
        {
            "episode_id": result["episode_id"],
            "intervention": result["intervention"],
            "sha256": digest(
                result["process_boundary_receipt"]["raw_boundary_trace"]
            ),
        }
        for result in results
    ]
    raw_trace_entries = [
        {
            "episode_id": result["episode_id"],
            "intervention": result["intervention"],
            "sha256": digest(result["raw_trace"]),
        }
        for result in results
    ]
    identity_failure_entries = _identity_failure_trace_entries(report)
    core = {key: value for key, value in report.items() if key != "frozen_manifest"}
    expected = {
        "schema_version": "ce001-g1-frozen-manifest-v2",
        "source_tree": source_entries,
        "source_tree_sha256": digest(source_entries),
        "input_receipts": input_receipts,
        "input_receipts_sha256": digest(input_receipts),
        "raw_boundary_traces": raw_boundary_entries,
        "raw_boundary_traces_sha256": digest(raw_boundary_entries),
        "raw_result_traces": raw_trace_entries,
        "raw_result_traces_sha256": digest(raw_trace_entries),
        "process_identity_failure_traces": identity_failure_entries,
        "process_identity_failure_traces_sha256": digest(
            identity_failure_entries
        ),
        "result_bytes_sha256": hashlib.sha256(canonical_bytes(core)).hexdigest(),
    }
    expected["manifest_sha256"] = digest(expected)
    mismatches = sorted(
        key for key, value in expected.items() if manifest.get(key) != value
    )
    return {
        "valid": not mismatches,
        "mismatches": mismatches,
    }


def build_report() -> dict[str, Any]:
    baseline = [run_episode(episode_id) for episode_id in EPISODE_IDS]
    e2_operator = [
        run_episode("E2-CONDITION-FORMATION", intervention="FULL_ACTUAL_TRACE"),
        run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
            removed_operator="OP-PARTNER-INTRODUCTION",
        ),
        run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
            reversed_operator="OP-PARTNER-INTRODUCTION",
        ),
    ]
    failures = [
        run_episode(
            "E1-EXTANT-MULTI-OWNER",
            intervention="FAILURE_INJECTION",
            failure_injection=injection,
        )
        for injection in (
            "WRONG_AUTHORITY",
            "SOURCE_ALIAS",
            "TAMPER_PAYLOAD",
            "TRUTH_TRANSPLANT",
        )
    ]
    failures.append(
        run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FAILURE_INJECTION",
            failure_injection="POST_TREATMENT_T0",
        )
    )
    method_source = WORKER_SOURCE.read_bytes()
    population_entries = []
    for episode_id in EPISODE_IDS:
        world = make_world(episode_id)
        population_entries.append(
            {
                "episode_id": episode_id,
                "prelude_sha256": digest(world.prelude),
                "interface_sha256": digest(world.interface),
                "L_benchmark": list(world.l_benchmark),
                "D_actual": list(world.d_actual),
                "oracle_roots_sha256": digest(
                    {
                        "expected_evidence": world.expected,
                        "source_aliases": world.source_aliases,
                        "authority_aliases": world.authority_aliases,
                        "min_unique_sources": world.min_unique_sources,
                    }
                ),
            }
        )
    report = {
        "schema_version": "ce001-g1-provenance-module-output-v1",
        "module": "G1",
        "scope": {
            "ingress": "IntentAtCoordinationInterface",
            "clarification_prelude": "LINKED_BY_HASH_EXCLUDED_FROM_G1_SUCCESS",
            "output": "CANDIDATE_NOT_COMMITMENT",
            "evidence_level": "LOCAL_SYNTHETIC_COMPONENT_MODEL_ONLY",
            "other_lines": "NOT_IMPLEMENTED",
            "worker_isolation": "INDEPENDENT_PROCESS_EXACT_BYTE_BOUNDARY",
            "owner_service": (
                "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE_IN_SEPARATE_PROCESS"
            ),
            "owner_source": "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE",
            "real_owner_truth": "NOT_ESTABLISHED",
            "real_owner_origin": "NOT_ESTABLISHED",
            "controller_role": "EXACT_BYTE_RELAY_PLUS_LOCAL_EVALUATION",
            "same_user_hostile_os_isolation": "RED_NOT_ISOLATED",
            "real_product": "NOT_RUN",
        },
        "population_receipt": {
            "episode_ids": list(EPISODE_IDS),
            "entries": population_entries,
            "sha256": digest(population_entries),
            "method_sha256": hashlib.sha256(method_source).hexdigest(),
        },
        "baseline_summary": summarize(baseline),
        "baseline": baseline,
        "operator_interventions": e2_operator,
        "failure_injections": failures,
        "process_identity_injections": [
            run_process_identity_injection(injection)
            for injection in (
                "OWNER_PID_MISMATCH",
                "WORKER_PID_MISMATCH",
                "ORIGIN_SELF_REPORT_INCONSISTENCY",
                "WRONG_SOURCE_INSTANCE",
            )
        ],
        "isolation_attacks": {
            "closure_reflection": {
                "status": "BLOCKED_BY_PROCESS_BOUNDARY",
                "evidence": (
                    "worker runtime frames/modules/globals contain only the "
                    "standalone worker and stdlib; no controller closure or "
                    "bound session object is transmitted"
                ),
            },
            "bounded_worker_cwd_path_scan": {
                "status": "BLOCKED_IN_SANITIZED_CWD",
                "files_seen": baseline[0]["process_boundary_receipt"][
                    "worker_runtime_attestation"
                ]["bounded_cwd_path_scan"],
            },
            "same_user_absolute_path_scan": run_same_user_path_probe(),
        },
    }
    source_entries = _source_tree_receipt()
    input_receipts = _input_receipts()
    results = _result_groups(report)
    raw_boundary_entries = [
        {
            "episode_id": result["episode_id"],
            "intervention": result["intervention"],
            "sha256": digest(
                result["process_boundary_receipt"]["raw_boundary_trace"]
            ),
        }
        for result in results
    ]
    raw_trace_entries = [
        {
            "episode_id": result["episode_id"],
            "intervention": result["intervention"],
            "sha256": digest(result["raw_trace"]),
        }
        for result in results
    ]
    identity_failure_entries = _identity_failure_trace_entries(report)
    manifest = {
        "schema_version": "ce001-g1-frozen-manifest-v2",
        "source_tree": source_entries,
        "source_tree_sha256": digest(source_entries),
        "input_receipts": input_receipts,
        "input_receipts_sha256": digest(input_receipts),
        "raw_boundary_traces": raw_boundary_entries,
        "raw_boundary_traces_sha256": digest(raw_boundary_entries),
        "raw_result_traces": raw_trace_entries,
        "raw_result_traces_sha256": digest(raw_trace_entries),
        "process_identity_failure_traces": identity_failure_entries,
        "process_identity_failure_traces_sha256": digest(
            identity_failure_entries
        ),
        "result_bytes_sha256": hashlib.sha256(canonical_bytes(report)).hexdigest(),
    }
    manifest["manifest_sha256"] = digest(manifest)
    report["frozen_manifest"] = manifest
    return report
