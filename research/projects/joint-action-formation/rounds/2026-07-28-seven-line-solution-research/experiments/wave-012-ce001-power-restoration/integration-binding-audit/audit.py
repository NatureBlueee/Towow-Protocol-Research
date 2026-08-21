#!/usr/bin/env python3
"""Audit whether current G1-G7 artifacts belong to one CE-001 episode.

This is deliberately not a contract evaluator.  It checks the prerequisite
that seven component outputs came from one frozen world/run/source registry
before any cross-line score is allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


EXPECTED_LINES = tuple(f"G{index}" for index in range(1, 8))
REQUIRED_COMMON_BINDINGS = (
    "selected_case_id",
    "episode_manifest_sha256",
    "run_root",
    "q_version",
    "canonical_object_id",
    "operation_id",
    "owner_registry_sha256",
    "target_registry_sha256",
)

HERE = Path(__file__).resolve().parent
WAVE_ROOT = HERE.parent


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def recursive_values(value: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            if child_key == key:
                found.append(child)
            found.extend(recursive_values(child, key))
    elif isinstance(value, list):
        for child in value:
            found.extend(recursive_values(child, key))
    return found


def strings(values: Iterable[Any]) -> list[str]:
    return sorted(
        {
            value
            for value in values
            if isinstance(value, str) and value.strip()
        }
    )


def current_artifact_records(wave_root: Path = WAVE_ROOT) -> list[dict[str, Any]]:
    """Extract only coordinates actually present in the current artifacts."""

    sources: dict[str, tuple[Path | None, Path | None]] = {
        "G1": (wave_root / "g1-provenance/frozen-output.json", None),
        "G2": (wave_root / "g2-relation/outputs/rerun-1.json", None),
        "G3": (wave_root / "g3-formation/outputs/report.json", None),
        # G4 currently returns its envelope to stdout; there is no persisted
        # component artifact that another process can bind by digest.
        "G4": (None, None),
        "G5": (wave_root / "g5-authority/artifacts/results.json", None),
        "G6": (
            wave_root / "g6-effect/artifacts/integration-fragment.json",
            wave_root / "g6-effect/artifacts/e2e-results.json",
        ),
        "G7": (wave_root / "g7-evolution/results.json", None),
    }

    records: list[dict[str, Any]] = []
    for line in EXPECTED_LINES:
        path, detail_path = sources[line]
        if path is None or not path.exists():
            records.append(
                {
                    "line": line,
                    "persisted_output": False,
                    "source_path": None,
                    "source_artifact_sha256": None,
                    "declared_case_refs": [],
                    "declared_episode_refs": [],
                    "declared_object_ids": [],
                    "declared_operation_ids": [],
                    "selected_case_id": None,
                    "episode_manifest_sha256": None,
                    "run_root": None,
                    "q_version": None,
                    "canonical_object_id": None,
                    "operation_id": None,
                    "owner_registry_sha256": None,
                    "target_registry_sha256": None,
                    "cross_refs": {},
                }
            )
            continue

        document = load_json(path)
        detail = load_json(detail_path) if detail_path is not None else document
        case_refs = strings(
            recursive_values(detail, "case_id")
            + recursive_values(detail, "case_ref")
            + recursive_values(detail, "case_handle")
        )
        episode_refs = strings(
            recursive_values(detail, "episode_id")
            + recursive_values(detail, "episode_handle")
        )
        object_ids = strings(recursive_values(detail, "object_id"))
        operation_ids = strings(recursive_values(detail, "operation_id"))
        q_versions = strings(
            recursive_values(detail, "q_version")
            + recursive_values(detail, "Q_version")
        )
        run_roots = strings(recursive_values(document, "run_root"))

        records.append(
            {
                "line": line,
                "persisted_output": True,
                "source_path": str(path.relative_to(wave_root)),
                "source_artifact_sha256": file_sha256(path),
                "detail_source_path": (
                    str(detail_path.relative_to(wave_root))
                    if detail_path is not None
                    else None
                ),
                "detail_source_sha256": (
                    file_sha256(detail_path) if detail_path is not None else None
                ),
                "declared_case_refs": case_refs,
                "declared_episode_refs": episode_refs,
                "declared_object_ids": object_ids,
                "declared_operation_ids": operation_ids,
                "declared_q_versions": q_versions,
                "declared_run_roots": run_roots,
                # None is intentional: a value found somewhere in a family
                # artifact is not a selected-case binding receipt.
                "selected_case_id": None,
                "episode_manifest_sha256": None,
                "run_root": None,
                "q_version": None,
                "canonical_object_id": None,
                "operation_id": None,
                "owner_registry_sha256": None,
                "target_registry_sha256": None,
                "cross_refs": {},
            }
        )
    return records


def assess_binding_records(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    by_line = {str(record.get("line")): record for record in records}
    failures: list[dict[str, Any]] = []

    def fail(code: str, detail: Any) -> None:
        failures.append({"code": code, "detail": detail})

    if set(by_line) != set(EXPECTED_LINES):
        fail(
            "LINE_SET_INCOMPLETE",
            {
                "expected": list(EXPECTED_LINES),
                "actual": sorted(by_line),
            },
        )

    for line in EXPECTED_LINES:
        record = by_line.get(line)
        if record is None:
            continue
        if record.get("persisted_output") is not True:
            fail("PERSISTED_OUTPUT_MISSING", {"line": line})
        missing = [
            field for field in REQUIRED_COMMON_BINDINGS if not record.get(field)
        ]
        if missing:
            fail(
                "COMMON_BINDING_MISSING",
                {"line": line, "fields": missing},
            )
        if not record.get("source_artifact_sha256"):
            fail("SOURCE_DIGEST_MISSING", {"line": line})

    for field in REQUIRED_COMMON_BINDINGS:
        values = {
            record.get(field)
            for record in by_line.values()
            if record.get(field) is not None
        }
        if len(values) > 1:
            fail(
                "COMMON_BINDING_MISMATCH",
                {"field": field, "values": sorted(values)},
            )

    g5 = by_line.get("G5", {})
    g6 = by_line.get("G6", {})
    g7 = by_line.get("G7", {})
    if (
        g6.get("cross_refs", {}).get("g5_source_artifact_sha256")
        != g5.get("source_artifact_sha256")
    ):
        fail(
            "G5_TO_G6_SOURCE_LINK_MISSING",
            {
                "expected": g5.get("source_artifact_sha256"),
                "actual": g6.get("cross_refs", {}).get(
                    "g5_source_artifact_sha256"
                ),
            },
        )
    if (
        g7.get("cross_refs", {}).get("g6_source_artifact_sha256")
        != g6.get("source_artifact_sha256")
    ):
        fail(
            "G6_TO_G7_SOURCE_LINK_MISSING",
            {
                "expected": g6.get("source_artifact_sha256"),
                "actual": g7.get("cross_refs", {}).get(
                    "g6_source_artifact_sha256"
                ),
            },
        )

    return {
        "status": (
            "JOINABLE_SINGLE_EPISODE"
            if not failures
            else "NOT_JOINABLE_CURRENT_ARTIFACTS"
        ),
        "contract_score_status": "NOT_COMPUTED",
        "failures": failures,
        "checked_lines": sorted(by_line),
    }


def audit_current_artifacts(wave_root: Path = WAVE_ROOT) -> dict[str, Any]:
    records = current_artifact_records(wave_root)
    assessment = assess_binding_records(records)

    declared_object_ids = {
        record["line"]: record["declared_object_ids"] for record in records
    }
    declared_operation_ids = {
        record["line"]: record["declared_operation_ids"] for record in records
    }
    declared_case_refs = {
        record["line"]: record["declared_case_refs"] for record in records
    }
    declared_episode_refs = {
        record["line"]: record["declared_episode_refs"] for record in records
    }

    g6_report = load_json(wave_root / "g6-effect/artifacts/e2e-results.json")
    g6_serialized = canonical_bytes(g6_report).decode("utf-8")
    g7 = load_json(wave_root / "g7-evolution/results.json")
    g7_migration = (
        g7.get("integration_envelope", {})
        .get("evidence", {})
        .get("migration", {})
    )
    g7_lineage = g7_migration.get("lineage_verification", {})
    g7_recovery = g7_migration.get("recovery", {})
    g7_refs = strings(
        [
            g7_lineage.get("effect_hash"),
            g7_recovery.get("finality_hash"),
            *g7_recovery.get("acceptance_hashes", []),
        ]
    )

    assessment["observations"] = {
        "declared_case_refs": declared_case_refs,
        "declared_episode_refs": declared_episode_refs,
        "declared_object_ids": declared_object_ids,
        "declared_operation_ids": declared_operation_ids,
        "g4_persisted_component_output": False,
        "g7_recovery_refs_present_in_g6_report": {
            reference: reference in g6_serialized for reference in g7_refs
        },
        "handwritten_preflight_fixtures_are_not_component_runs": True,
    }
    assessment["records"] = records
    assessment["evidence_boundary"] = (
        "CURRENT_LOCAL_ARTIFACT_BINDING_AUDIT_ONLY; "
        "NOT_A_CONTRACT_EVALUATION; NOT_A_PRODUCT_RUN"
    )
    return assessment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "actual-artifact-binding-audit.json",
    )
    args = parser.parse_args()

    report = audit_current_artifacts()
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    print(report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
