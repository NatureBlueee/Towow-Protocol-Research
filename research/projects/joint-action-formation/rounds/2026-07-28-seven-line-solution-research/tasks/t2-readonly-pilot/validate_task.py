#!/usr/bin/env python3
"""Deterministic structural and byte-closure checks for the T2 truth task.

This validator does not solve the task and does not assign semantic scores.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "manifest.json"
TASK_ID = "T2-ENTERPRISE-PILOT-BLIND-V1"

REQUIRED_FILES = {
    "README.md",
    "blind/input.json",
    "controller.py",
    "schemas/query-batch.schema.json",
    "schemas/final-submission.schema.json",
    "oracle/truth.json",
    "evaluator/spec.json",
    "tests/test_controller.py",
    "validate_task.py",
}

BLIND_FORBIDDEN_TOKENS = {
    "REL-T2-V2-REFERENCE",
    "PROBE-T2-REF-1",
    "buyer_controlled_sandbox",
    "fixed_container",
    "raw_row_export_count_is_zero",
    "T2-ENTERPRISE-PILOT-ORACLE-V1",
    "../oracle/truth.json",
    "sample_case",
    "04_示例案例_企业AI只读试点.md",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(relative_path: str) -> dict:
    path = ROOT / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{relative_path}: {exc}")
    if not isinstance(value, dict):
        fail(f"{relative_path}: top level must be an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_keys(value: dict, keys: set[str], label: str) -> None:
    missing = sorted(keys - value.keys())
    if missing:
        fail(f"{label}: missing keys {missing}")


blind = load_json("blind/input.json")
oracle = load_json("oracle/truth.json")
evaluator = load_json("evaluator/spec.json")
query_schema = load_json("schemas/query-batch.schema.json")
submission_schema = load_json("schemas/final-submission.schema.json")
manifest = load_json("manifest.json")

for label, value in (("blind", blind), ("oracle", oracle), ("evaluator", evaluator)):
    if value.get("task_id") != TASK_ID:
        fail(f"{label}: task_id mismatch")

require_keys(
    blind,
    {
        "frozen_prestate",
        "frozen_value_floor",
        "frozen_qualification_predicate",
        "authority_interfaces",
        "disclosure_protocol",
        "initial_relation_version",
        "key_bottomlines",
        "expected_solver_return",
    },
    "blind/input.json",
)
require_keys(
    oracle,
    {
        "evidence_boundary",
        "private_local_states_at_s0",
        "disclosure_transitions",
        "world_state_sequence",
        "reference_probe",
        "reference_relation_v2",
        "reference_transition_truth",
        "formation_truth",
        "outcome_truth",
        "repeat_run_truth",
        "pseudo_success_mutations",
        "alternate_solution_policy",
    },
    "oracle/truth.json",
)
require_keys(
    evaluator,
    {
        "anti_cheat",
        "candidate_submission_contract",
        "requirements",
        "scoring",
        "mutation_tests",
        "evaluator_output_contract",
    },
    "evaluator/spec.json",
)
require_keys(
    query_schema,
    {
        "$schema",
        "$id",
        "type",
        "additionalProperties",
        "required",
        "properties",
    },
    "schemas/query-batch.schema.json",
)
require_keys(
    submission_schema,
    {
        "$schema",
        "$id",
        "type",
        "additionalProperties",
        "required",
        "properties",
        "$defs",
    },
    "schemas/final-submission.schema.json",
)

blind_text = (ROOT / "blind/input.json").read_text(encoding="utf-8")
for token in sorted(BLIND_FORBIDDEN_TOKENS):
    if token in blind_text:
        fail(f"blind/input.json leaks forbidden oracle/source token: {token}")

method_visible_paths = [
    "blind/input.json",
    "evaluator/spec.json",
    "schemas/query-batch.schema.json",
    "schemas/final-submission.schema.json",
]
expected_solver_allowlist = method_visible_paths
if manifest.get("solver_payload_allowlist") != expected_solver_allowlist:
    fail("manifest solver_payload_allowlist mismatch")
method_visible_text = "\n".join(
    (ROOT / relative_path).read_text(encoding="utf-8")
    for relative_path in method_visible_paths
)
for token in sorted(BLIND_FORBIDDEN_TOKENS):
    if token in method_visible_text:
        fail(f"method-visible payload leaks forbidden oracle/source token: {token}")

authority_ids = {item.get("authority_id") for item in blind["authority_interfaces"]}
expected_authorities = {
    "BUYER-BUSINESS",
    "BUYER-DATA",
    "PROVIDER-BUSINESS",
    "PROVIDER-TECH",
}
if authority_ids != expected_authorities:
    fail(f"blind authority set mismatch: {sorted(authority_ids)}")

allowed_requests = {
    (item["authority_id"], request_type)
    for item in blind["authority_interfaces"]
    for request_type in item.get("allowed_request_types", [])
}
oracle_requests = {
    (item.get("authority_id"), item.get("request_type"))
    for item in oracle["disclosure_transitions"]
}
missing_responses = sorted(allowed_requests - oracle_requests)
extra_responses = sorted(oracle_requests - allowed_requests)
if missing_responses or extra_responses:
    fail(
        "disclosure allowlist/oracle mismatch: "
        f"missing={missing_responses}, extra={extra_responses}"
    )

requirement_ids = [item.get("id") for item in evaluator["requirements"]]
if len(requirement_ids) != len(set(requirement_ids)):
    fail("evaluator requirement ids are not unique")
if set(requirement_ids) != {
    "R2-RELATION-FROM-TASK",
    "R3-FORM-REACHABILITY",
    "R4-CAPABILITY-TO-RELIANCE",
    "R5-AUTHORITY-COMPOSITION",
    "R6-EFFECT-THAT-COUNTS",
    "R7-REUSE-AND-SAFE-REOPEN",
    "R8-CLAIM-BOUNDARY",
}:
    fail("evaluator requirement set mismatch")

mutation_ids = [item.get("id") for item in oracle["pseudo_success_mutations"]]
if len(mutation_ids) != len(set(mutation_ids)):
    fail("oracle mutation ids are not unique")

artifacts = manifest.get("artifacts")
if not isinstance(artifacts, list):
    fail("manifest artifacts must be a list")
manifest_paths = {item.get("path") for item in artifacts}
if manifest_paths != REQUIRED_FILES:
    fail(
        "manifest artifact set mismatch: "
        f"expected={sorted(REQUIRED_FILES)}, actual={sorted(manifest_paths)}"
    )
for item in artifacts:
    relative_path = item.get("path")
    expected_hash = item.get("sha256")
    path = ROOT / relative_path
    if not path.is_file():
        fail(f"manifest artifact does not exist: {relative_path}")
    actual_hash = sha256(path)
    if actual_hash != expected_hash:
        fail(
            f"hash mismatch for {relative_path}: "
            f"expected={expected_hash}, actual={actual_hash}"
        )

source_closure = manifest.get("source_closure")
if not isinstance(source_closure, list) or not source_closure:
    fail("manifest source_closure must be a non-empty list")
for item in source_closure:
    relative_to_repo = item.get("path")
    expected_hash = item.get("sha256")
    source_path = ROOT
    while source_path.name != "通爻协议研究" and source_path.parent != source_path:
        source_path = source_path.parent
    if source_path.name != "通爻协议研究":
        fail("cannot locate repository root for source closure")
    source_path = source_path / relative_to_repo
    if not source_path.is_file():
        fail(f"source closure file does not exist: {relative_to_repo}")
    actual_hash = sha256(source_path)
    if actual_hash != expected_hash:
        fail(
            f"source hash mismatch for {relative_to_repo}: "
            f"expected={expected_hash}, actual={actual_hash}"
        )

print(
    "PASS: JSON structure, blind leak guards, disclosure closure, "
    "artifact hashes and source hashes are consistent."
)
