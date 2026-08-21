#!/usr/bin/env python3
"""Structural validator for the Wave 003-C T4 blind truth task."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parent
TASK_ID = "T4-JOINT-BID-BLIND-V1"
SOLVER_ALLOWLIST = [
    "blind/input.json",
    "evaluator/spec.json",
    "schemas/query-batch.schema.json",
    "schemas/final-submission.schema.json",
]
EXPECTED_ARTIFACTS = {
    "README.md",
    "blind/input.json",
    "controller.py",
    "evaluator/spec.json",
    "mutations/negative_mutations.json",
    "oracle/migration_variant.json",
    "oracle/truth.json",
    "schemas/final-submission.schema.json",
    "schemas/query-batch.schema.json",
    "tests/test_controller.py",
    "validate_task.py",
}
REQUIREMENT_IDS = {
    "R2-TASK-RELATION",
    "R3-FORM-REACHABILITY",
    "R4-CAPABILITY-QUALIFICATION",
    "R5-AUTHORITY-RESERVATION",
    "R6-OUTCOME-READBACK",
    "R7-REOPEN-REUSE-MIGRATION",
}
HIDDEN_SENTINELS = {
    "CITY-RFC-17-V2",
    "ADD-DATA-LOCAL-02",
    "120000",
    "145000",
    "70000",
    "edge-orchestrator@2.3.1",
    "firmware@4.2",
    "RSV-PRIME-72H-01",
    "RSV-FIELD-12KIT-72H-01",
    "RSV-ASSURE-2AUD-72H-01",
    "MUSEUM-RFP-09-V3",
}


class ValidationError(ValueError):
    pass


def read_json(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON artifact: {relative}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"top-level JSON must be an object: {relative}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_identity() -> dict[str, dict[str, Any]]:
    artifacts = {
        relative: read_json(relative)
        for relative in [
            "blind/input.json",
            "evaluator/spec.json",
            "mutations/negative_mutations.json",
            "oracle/migration_variant.json",
            "oracle/truth.json",
            "schemas/final-submission.schema.json",
            "schemas/query-batch.schema.json",
            "manifest.json",
        ]
    }
    for relative, value in artifacts.items():
        if relative.startswith("schemas/"):
            actual = value.get("properties", {}).get("task_id", {}).get("const")
        else:
            actual = value.get("task_id")
        ensure(actual == TASK_ID, f"task identity mismatch: {relative}")
    return artifacts


def validate_disclosure_closure(
    blind: dict[str, Any], oracle: dict[str, Any]
) -> None:
    public_pairs: set[tuple[str, str]] = set()
    authority_ids: set[str] = set()
    for interface in blind.get("authority_interfaces", []):
        authority_id = interface.get("authority_id")
        ensure(
            isinstance(authority_id, str) and authority_id not in authority_ids,
            "authority ids must be unique strings",
        )
        authority_ids.add(authority_id)
        for request_type in interface.get("allowed_request_types", []):
            pair = (authority_id, request_type)
            ensure(
                isinstance(request_type, str) and pair not in public_pairs,
                "public Authority/request pairs must be unique",
            )
            public_pairs.add(pair)

    hidden_pairs: set[tuple[str, str]] = set()
    prerequisites: list[str] = []
    for transition in oracle.get("disclosure_transitions", []):
        pair = (
            transition.get("authority_id"),
            transition.get("request_type"),
        )
        ensure(
            all(isinstance(item, str) for item in pair) and pair not in hidden_pairs,
            "oracle Authority/request pairs must be unique strings",
        )
        hidden_pairs.add(pair)
        ensure(
            transition.get("response_type")
            in blind["disclosure_protocol"]["response_types"],
            "oracle response type is not public-allowed",
        )
        ensure(
            isinstance(transition.get("disclosed_fields"), dict),
            "oracle disclosure must be a field object",
        )
        prerequisites.extend(transition.get("prerequisites", []))

    ensure(public_pairs == hidden_pairs, "public/oracle disclosure closure mismatch")
    pair_keys = {f"{authority}|{request}" for authority, request in public_pairs}
    ensure(
        all(item in pair_keys for item in prerequisites),
        "oracle prerequisite points outside the public interface",
    )


def validate_isolation() -> None:
    visible_text = "\n".join(
        (ROOT / relative).read_text(encoding="utf-8")
        for relative in SOLVER_ALLOWLIST
    )
    leaked = sorted(token for token in HIDDEN_SENTINELS if token in visible_text)
    ensure(not leaked, f"hidden sentinel leaked into solver-visible files: {leaked}")


def validate_evaluator(
    evaluator: dict[str, Any],
    mutations: dict[str, Any],
    migration: dict[str, Any],
) -> None:
    requirements = evaluator.get("requirements", [])
    actual_ids = {item.get("id") for item in requirements}
    ensure(actual_ids == REQUIREMENT_IDS, "G2-G7 requirement closure mismatch")
    ensure(
        {item.get("gate") for item in requirements}
        == {"G2", "G3", "G4", "G5", "G6", "G7"},
        "gate closure mismatch",
    )
    neutrality = evaluator.get("anti_answer_shaping", {})
    ensure(neutrality.get("protocol_name_bonus") == 0, "protocol name bias")
    ensure(neutrality.get("novelty_bonus") == 0, "novelty bias")
    ensure(neutrality.get("existing_standards_penalty") == 0, "standards bias")
    ensure(
        any(
            "CMMN/BPMN/DMN" in item
            for item in neutrality.get("accepted_solution_families", [])
        ),
        "mature standards solution family is not explicitly eligible",
    )

    mutation_list = mutations.get("mutations", [])
    mutation_ids = [item.get("id") for item in mutation_list]
    ensure(
        len(mutation_ids) == len(set(mutation_ids)) and len(mutation_ids) >= 8,
        "negative mutations must be unique and nontrivial",
    )
    covered = {
        requirement
        for mutation in mutation_list
        for requirement in mutation.get("tests", [])
    }
    ensure(covered == REQUIREMENT_IDS, "mutation requirement closure mismatch")
    ensure(
        migration.get("visibility") == "EVALUATOR_ONLY",
        "migration variant must remain evaluator-only",
    )
    ensure(
        "a Towow-specific object or protocol name"
        in migration.get("migration_evaluation", {}).get("must_not_require", []),
        "migration neutrality is not frozen",
    )


def validate_manifest(manifest: dict[str, Any]) -> dict[str, str]:
    ensure(
        manifest.get("solver_allowlist") == SOLVER_ALLOWLIST,
        "manifest solver allowlist mismatch",
    )
    ensure(
        manifest.get("candidate_method_implemented") is False,
        "task package must not contain a candidate method",
    )
    listed = manifest.get("artifacts", {})
    ensure(isinstance(listed, dict), "manifest artifacts must be an object")
    ensure(set(listed) == EXPECTED_ARTIFACTS, "manifest artifact closure mismatch")
    actual_hashes: dict[str, str] = {}
    for relative in sorted(EXPECTED_ARTIFACTS):
        path = ROOT / relative
        ensure(path.is_file(), f"missing artifact: {relative}")
        actual = sha256_file(path)
        actual_hashes[relative] = actual
        record = listed[relative]
        ensure(record.get("sha256") == actual, f"hash mismatch: {relative}")
        ensure(record.get("bytes") == path.stat().st_size, f"size mismatch: {relative}")
    return actual_hashes


def main() -> int:
    try:
        artifacts = validate_identity()
        validate_disclosure_closure(
            artifacts["blind/input.json"], artifacts["oracle/truth.json"]
        )
        validate_isolation()
        validate_evaluator(
            artifacts["evaluator/spec.json"],
            artifacts["mutations/negative_mutations.json"],
            artifacts["oracle/migration_variant.json"],
        )
        actual_hashes = validate_manifest(artifacts["manifest.json"])
        receipt = {
            "schema_version": "1.0",
            "task_id": TASK_ID,
            "status": "PASS",
            "artifact_count": len(actual_hashes),
            "solver_allowlist_hash": canonical_hash(SOLVER_ALLOWLIST),
            "artifact_set_hash": canonical_hash(actual_hashes),
            "blind_input_hash": actual_hashes["blind/input.json"],
            "evaluator_hash": actual_hashes["evaluator/spec.json"],
            "oracle_hash": actual_hashes["oracle/truth.json"],
            "migration_hash": actual_hashes["oracle/migration_variant.json"],
            "mutations_hash": actual_hashes["mutations/negative_mutations.json"],
        }
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except ValidationError as exc:
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "task_id": TASK_ID,
                    "status": "FAIL",
                    "error": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
