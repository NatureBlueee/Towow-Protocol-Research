#!/usr/bin/env python3
"""Validate the A2A historical design capability audit.

This checks provenance and cross-reference integrity. It does not decide whether
the research claims are true.
"""

from __future__ import annotations

import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "research/projects/a2a-reconstruction"
AUDIT = PROJECT / "04_audit"
CATALOG = PROJECT / "01_catalog"

PRESERVATION = {"PRESERVED", "TRANSFORMED", "PARTIAL", "LOST", "DUPLICATED", "UNTESTED"}
CLAIM_STATUS = {"STABLE", "SCOPED", "HYPOTHESIS", "DOWNGRADED", "REFUTED", "OPEN"}
EVIDENCE_TYPE = {
    "DECISIONAL_EVIDENCE",
    "NEGATIVE_EVIDENCE",
    "ARCHIVAL_CALIBRATION",
    "IMPLEMENTATION_ASSURANCE",
    "CI_REGRESSION",
    "SELF_CONSISTENCY",
    "RESEARCH_PLAN",
}
DELTA_KIND = {
    "OBSERVED_DESIGN_FLIP",
    "EVIDENCE_DRIVEN_LIMITATION",
    "PREDECIDED_CONFIRMATION",
    "IMPLEMENTATION_REPAIR",
    "USER_SCOPE_CHANGE",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]


def check_unique(rows: list[dict[str, str]], field: str, label: str, errors: list[str]) -> None:
    values = [row.get(field, "") for row in rows]
    for value, count in Counter(values).items():
        if not value:
            errors.append(f"{label}: empty {field}")
        elif count > 1:
            errors.append(f"{label}: duplicate {field} {value}")


def resolve_readable(row: dict[str, str]) -> Path:
    path = Path(row["readable_path"])
    if row["source_kind"] == "ZIP_MEMBER":
        return PROJECT / path
    return ROOT / path


def max_anchor(value: str) -> int:
    result = 0
    for part in value.split(";"):
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", part.strip())
        if not match:
            raise ValueError(f"invalid line anchor {part!r}")
        result = max(result, int(match.group(2) or match.group(1)))
    return result


def main() -> int:
    errors: list[str] = []
    required = [
        AUDIT / "README.md",
        AUDIT / "AUDIT_PROTOCOL.md",
        AUDIT / "source_registry.csv",
        AUDIT / "current_system_capability_map.md",
        AUDIT / "AUDIT_FINDINGS.md",
        AUDIT / "research_priority_after_audit.md",
        AUDIT / "ledgers/capability_preservation_matrix.csv",
        AUDIT / "ledgers/claim_ledger.csv",
        AUDIT / "ledgers/evidence_ledger.csv",
        AUDIT / "ledgers/decision_timeline.csv",
        AUDIT / "ledgers/component_capability_index.csv",
        AUDIT / "ledgers/formal_fact_ownership.csv",
    ]
    native = sorted((AUDIT / "native_lines").glob("*.md"))
    if len(native) != 7:
        errors.append(f"expected 7 native research line dossiers, found {len(native)}")
    for path in required:
        if not path.is_file():
            errors.append(f"missing audit artifact: {path.relative_to(ROOT)}")
    if errors:
        return fail(errors)

    physical = {r["record_id"]: r for r in read_csv(CATALOG / "physical_files.csv")}
    zip_members = {r["record_id"]: r for r in read_csv(CATALOG / "zip_members.csv")}
    sources = read_csv(AUDIT / "source_registry.csv")
    check_unique(sources, "source_id", "source registry", errors)
    source_by_id = {r["source_id"]: r for r in sources}

    for row in sources:
        sid = row["source_id"]
        kind = row["source_kind"]
        record_id = row["catalog_record_id"]
        readable = resolve_readable(row)
        if not readable.is_file():
            errors.append(f"{sid}: readable source missing: {readable}")
            continue
        actual = sha256(readable)
        if actual != row["sha256"]:
            errors.append(f"{sid}: readable SHA mismatch")
        catalog_row = physical.get(record_id) if kind == "PHYSICAL" else zip_members.get(record_id)
        if catalog_row is None:
            errors.append(f"{sid}: catalog record missing: {record_id}")
        elif catalog_row["sha256"] != row["sha256"]:
            errors.append(f"{sid}: catalog SHA mismatch for {record_id}")
        if kind not in {"PHYSICAL", "ZIP_MEMBER"}:
            errors.append(f"{sid}: invalid source kind {kind}")
        try:
            last = max_anchor(row["line_anchors"])
            line_count = sum(1 for _ in readable.open(encoding="utf-8", errors="replace"))
            if last > line_count:
                errors.append(f"{sid}: anchor {last} exceeds {line_count} lines")
        except ValueError as exc:
            errors.append(f"{sid}: {exc}")

    capability_rows = read_csv(AUDIT / "ledgers/capability_preservation_matrix.csv")
    check_unique(capability_rows, "capability_id", "capability matrix", errors)
    capability_ids = {r["capability_id"] for r in capability_rows}
    for row in capability_rows:
        cid = row["capability_id"]
        if row["preservation_status"] not in PRESERVATION:
            errors.append(f"{cid}: invalid preservation status {row['preservation_status']}")
        for sid in split_ids(row["source_ids"]):
            if sid not in source_by_id:
                errors.append(f"{cid}: unknown source {sid}")
        evidence = row["original_evidence"]
        if "positive:" not in evidence or "removal_failure:" not in evidence:
            errors.append(f"{cid}: missing positive/removal_failure reconstruction")
        if not row["current_owner"] or not row["required_recovery"]:
            errors.append(f"{cid}: missing current owner or recovery decision")
        if row["preservation_status"] == "PRESERVED" and "manual_reconstruction=PASS" not in row["review_notes"]:
            errors.append(f"{cid}: PRESERVED without manual reconstruction PASS")

    native_text = "\n".join(path.read_text(encoding="utf-8") for path in native)
    system_map = (AUDIT / "current_system_capability_map.md").read_text(encoding="utf-8")
    for cid in sorted(capability_ids):
        if cid not in native_text:
            errors.append(f"{cid}: absent from native research line dossiers")
        if cid not in system_map:
            errors.append(f"{cid}: absent from current system capability map")

    claims = read_csv(AUDIT / "ledgers/claim_ledger.csv")
    check_unique(claims, "claim_id", "claim ledger", errors)
    claim_ids = {r["claim_id"] for r in claims}
    for row in claims:
        if row["current_status"] not in CLAIM_STATUS:
            errors.append(f"{row['claim_id']}: invalid claim status {row['current_status']}")
        for sid in split_ids(row["primary_sources"]):
            if sid not in source_by_id:
                errors.append(f"{row['claim_id']}: unknown source {sid}")

    evidence_rows = read_csv(AUDIT / "ledgers/evidence_ledger.csv")
    check_unique(evidence_rows, "evidence_id", "evidence ledger", errors)
    evidence_ids = {r["evidence_id"] for r in evidence_rows}
    for row in evidence_rows:
        eid = row["evidence_id"]
        if row["evidence_type"] not in EVIDENCE_TYPE:
            errors.append(f"{eid}: invalid evidence type {row['evidence_type']}")
        for sid in split_ids(row["primary_sources"]):
            if sid not in source_by_id:
                errors.append(f"{eid}: unknown source {sid}")
        for cid in split_ids(row["claim_ids"]):
            if cid not in claim_ids:
                errors.append(f"{eid}: unknown claim {cid}")

    for row in claims:
        for eid in split_ids(row["supporting_evidence"]) + split_ids(row["contradicting_evidence"]):
            if eid not in evidence_ids:
                errors.append(f"{row['claim_id']}: unknown evidence {eid}")

    decisions = read_csv(AUDIT / "ledgers/decision_timeline.csv")
    check_unique(decisions, "decision_id", "decision timeline", errors)
    delta_kinds = set()
    for row in decisions:
        did = row["decision_id"]
        delta_kinds.add(row["delta_kind"])
        if row["delta_kind"] not in DELTA_KIND:
            errors.append(f"{did}: invalid delta kind {row['delta_kind']}")
        for sid in split_ids(row["source_ids"]):
            if sid not in source_by_id:
                errors.append(f"{did}: unknown source {sid}")
        for cid in split_ids(row["affected_capabilities"]):
            if cid not in capability_ids:
                errors.append(f"{did}: unknown capability {cid}")
        for field in ("decision_before_experiment", "observed_result", "decision_after_experiment"):
            if not row[field]:
                errors.append(f"{did}: empty {field}")
    for expected in {"USER_SCOPE_CHANGE", "OBSERVED_DESIGN_FLIP", "PREDECIDED_CONFIRMATION"}:
        if expected not in delta_kinds:
            errors.append(f"decision timeline does not distinguish {expected}")

    facts = read_csv(AUDIT / "ledgers/formal_fact_ownership.csv")
    check_unique(facts, "fact_key", "formal fact ownership", errors)
    for row in facts:
        owner = row["canonical_owner"].strip()
        duplicates = split_ids(row["prohibited_duplicate_owners"])
        if not owner:
            errors.append(f"{row['fact_key']}: no canonical owner")
        if owner in duplicates:
            errors.append(f"{row['fact_key']}: canonical owner also listed as duplicate")
        for cid in split_ids(row["capability_ids"]):
            if cid not in capability_ids:
                errors.append(f"{row['fact_key']}: unknown capability {cid}")
        for sid in split_ids(row["source_ids"]):
            if sid not in source_by_id:
                errors.append(f"{row['fact_key']}: unknown source {sid}")

    components = read_csv(AUDIT / "ledgers/component_capability_index.csv")
    check_unique(components, "component_id", "component capability index", errors)
    component_caps: set[str] = set()
    for row in components:
        for cid in split_ids(row["capability_ids"]):
            component_caps.add(cid)
            if cid not in capability_ids:
                errors.append(f"{row['component_id']}: unknown capability {cid}")
        for sid in split_ids(row["source_ids"]):
            if sid not in source_by_id:
                errors.append(f"{row['component_id']}: unknown source {sid}")
    for cid in sorted(capability_ids - component_caps):
        errors.append(f"{cid}: no reverse index from a current component")

    # Validate every inline source locator in audit Markdown.
    citation = re.compile(r"\[(SRC-[A-Z0-9-]+):(\d+)(?:-(\d+))?\]")
    for path in sorted(AUDIT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for sid, start, end in citation.findall(text):
            if sid not in source_by_id:
                errors.append(f"{path.relative_to(ROOT)}: unknown inline source {sid}")
                continue
            source_lines = sum(
                1 for _ in resolve_readable(source_by_id[sid]).open(encoding="utf-8", errors="replace")
            )
            cited_end = int(end or start)
            if cited_end > source_lines:
                errors.append(
                    f"{path.relative_to(ROOT)}: {sid} citation ends at {cited_end}, source has {source_lines}"
                )

    # Core R5 families must use original evidence sources, not only later synthesis.
    used_sources = {
        sid
        for row in capability_rows + claims + evidence_rows + decisions
        for sid in split_ids(row.get("source_ids", "") or row.get("primary_sources", ""))
    }
    required_direct = {
        "SRC-R5-SUMMARY",
        "SRC-R5-DECISION",
        "SRC-R52-EFFECT",
        "SRC-R52-CAPABILITY",
        "SRC-R54-CORE",
        "SRC-R54-CAUSALITY",
        "SRC-R5C-SUMMARY",
        "SRC-R5C-ABLATION",
        "SRC-R5C-HOLDOUT",
        "SRC-R5C-HUMAN",
    }
    for sid in sorted(required_direct - used_sources):
        errors.append(f"core direct evidence source is not used: {sid}")

    findings = (AUDIT / "AUDIT_FINDINGS.md").read_text(encoding="utf-8")
    lost_ids = {r["capability_id"] for r in capability_rows if r["preservation_status"] == "LOST"}
    for cid in lost_ids:
        if cid not in findings:
            errors.append(f"{cid}: lost capability absent from explicit loss list")

    if errors:
        return fail(errors)

    statuses = Counter(r["preservation_status"] for r in capability_rows)
    print(f"[OK] {len(sources)} sources: catalog IDs, SHA-256 and line anchors verified")
    print(f"[OK] {len(capability_rows)} capabilities: positive/removal failures and owners linked")
    print("[OK] capability status: " + ", ".join(f"{k}={v}" for k, v in sorted(statuses.items())))
    print(f"[OK] {len(claims)} claims, {len(evidence_rows)} evidence records, {len(decisions)} decisions")
    print(f"[OK] {len(facts)} canonical formal facts have one declared owner")
    print(f"[OK] {len(components)} current components reverse-link all historical capabilities")
    print("[OK] seven native dossiers and current system map are bidirectionally addressable")
    print("[OK] R5/R5.2/R5.4/R5C use direct evidence sources")
    return 0


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"[ERROR] {error}")
    print(f"\nA2A design audit check failed with {len(errors)} error(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
