#!/usr/bin/env python3
"""Bounded, provenance-preserving orchestration for Towow research.

The controller may create runtime packets and candidate returns. Automated
workers never receive authority to mutate the canonical problem, NOW, decisions,
or stable claims.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import csv
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - surfaced as a clear environment error
    Draft202012Validator = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".research-runtime"
CONTRACTS = ROOT / "research" / "contracts"
DEFAULT_PROJECT = ROOT / "research" / "projects" / "joint-action-formation"
NOW_PATH = ROOT / "research" / "NOW.md"
DECISIONS_PATH = ROOT / "research" / "DECISIONS.md"
ARCHIVE_POINTER = ROOT / "research" / "sources" / "archive-v1.2.json"

BATCH_LIMIT_BYTES = 250 * 1024 * 1024
RUNTIME_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
DEFAULT_MAX_PARALLEL = 3

SCHEMA_BY_KIND = {
    "ProblemContract": CONTRACTS / "problem.schema.json",
    "ScenarioContract": CONTRACTS / "scenario.schema.json",
    "LineContract": CONTRACTS / "line.schema.json",
    "RunManifest": CONTRACTS / "run-manifest.schema.json",
    "ResearchResult": CONTRACTS / "research-result.schema.json",
    "ClaimCandidate": CONTRACTS / "claim-candidate.schema.json",
    "BlindReview": CONTRACTS / "blind-review.schema.json",
    "HistoricalInheritanceAudit": CONTRACTS / "historical-inheritance.schema.json",
    "MechanismProfile": CONTRACTS / "mechanism-profile.schema.json",
    "ProblemActivationBundle": CONTRACTS / "problem-activation-bundle.schema.json",
}

PROBLEM_ACTIVATION_ARTIFACT_ROLES = {
    "CANDIDATE_PROBLEM",
    "CANDIDATE_COMPANION",
    "HISTORICAL_INHERITANCE_AUDIT",
    "HISTORICAL_INHERITANCE_COMPANION",
    "CANONICAL_CAPABILITY_MATRIX",
}

PROTECTED_PATHS = [
    ROOT / "AGENTS.md",
    NOW_PATH,
    DECISIONS_PATH,
]

STATE_RE = re.compile(
    r"<!-- research-state:start -->\s*```json\s*(\{.*?\})\s*```\s*<!-- research-state:end -->",
    re.DOTALL,
)
DECISION_RE = re.compile(
    r"<!-- research-decision:start -->\s*```json\s*(\{.*?\})\s*```\s*<!-- research-decision:end -->",
    re.DOTALL,
)


class ResearchError(RuntimeError):
    """A user-facing research governance violation."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def run_input_hash(bundle: Mapping[str, Any]) -> str:
    """Hash every semantic input field without creating a self-reference."""
    payload = copy.deepcopy(dict(bundle))
    for runner_owned in ("batch_id", "run_id", "input_hash"):
        payload.pop(runner_owned, None)
    return json_hash(payload)


def compute_plan_fingerprint(plan: Mapping[str, Any]) -> str:
    """Hash every immutable planning field; runtime status is deliberately excluded."""
    immutable = {
        key: copy.deepcopy(plan.get(key))
        for key in (
            "schema_version",
            "batch_id",
            "created_at",
            "mode",
            "project",
            "problem_path",
            "problem_sha256",
            "scenario_path",
            "scenario_sha256",
            "max_parallel",
            "batch_limit_bytes",
            "runtime_limit_bytes",
            "runs",
        )
    }
    return json_hash(immutable)


def reject_duplicate_json_keys(
    pairs: Sequence[Tuple[str, Any]],
) -> Dict[str, Any]:
    value: Dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ResearchError(f"cannot read JSON {relative(path)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchError(f"expected JSON object: {relative(path)}")
    return value


def fsync_directory(path: Path) -> None:
    """Best-effort durability barrier for an atomic directory entry update."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_text(
    path: Path,
    text: str,
    *,
    replace_existing: bool = True,
    mode: int = 0o644,
) -> None:
    """Publish complete text bytes without exposing a torn destination file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(mode)
        if replace_existing:
            os.replace(temporary, path)
        else:
            try:
                os.link(temporary, path)
            except FileExistsError as exc:
                raise ResearchError(
                    f"atomic destination already exists: {relative(path)}"
                ) from exc
            temporary.unlink()
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
    )


def write_json_once(path: Path, value: Any) -> None:
    """Publish an immutable transaction artifact without replacing a prior one."""
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        replace_existing=False,
    )


def write_controller_seal(path: Path, value: Mapping[str, Any]) -> None:
    """Create a controller-owned, read-only seal; never overwrite in place."""
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        replace_existing=False,
        mode=0o444,
    )


def load_controller_seal(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise ResearchError(f"controller seal is missing: {relative(path)}")
    if path.stat().st_mode & 0o222:
        raise ResearchError(f"controller seal is writable: {relative(path)}")
    return load_json(path)


def plan_seal_document(
    plan: Mapping[str, Any],
    *,
    sealed_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the controller-owned statement for one immutable batch plan."""
    return {
        "schema_version": "1.0",
        "kind": "PlanControllerSeal",
        "batch_id": plan["batch_id"],
        "plan_fingerprint": plan["plan_fingerprint"],
        "protected_hashes": copy.deepcopy(plan["protected_hashes"]),
        "external_disclosure": copy.deepcopy(
            plan.get("external_disclosure")
        ),
        "run_inputs": {
            run["run_id"]: {
                "input_hash": run["input_hash"],
                "input_payload_sha256": run["input_payload_sha256"],
            }
            for run in plan["runs"]
        },
        "sealed_at": sealed_at or utc_now(),
    }


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def resolve_root_path(locator: str) -> Path:
    candidate = (ROOT / locator).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ResearchError(f"path escapes workspace: {locator}") from exc
    return candidate


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    return total


def schema_for(kind: str) -> Dict[str, Any]:
    path = SCHEMA_BY_KIND.get(kind)
    if path is None:
        raise ResearchError(f"unknown contract kind: {kind!r}")
    return load_json(path)


def validate_schema(document: Mapping[str, Any], path: Path) -> List[str]:
    if Draft202012Validator is None:
        return ["python package jsonschema is required"]
    kind = document.get("kind")
    if not isinstance(kind, str) or kind not in SCHEMA_BY_KIND:
        return [f"{relative(path)}: missing or unknown kind"]
    validator = Draft202012Validator(schema_for(kind))
    errors: List[str] = []
    for error in sorted(validator.iter_errors(document), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{relative(path)}:{location}: {error.message}")
    return errors


def read_state() -> Dict[str, Any]:
    text = NOW_PATH.read_text(encoding="utf-8")
    match = STATE_RE.search(text)
    if not match:
        raise ResearchError("research/NOW.md has no structured research-state block")
    try:
        state = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ResearchError(f"invalid research-state block: {exc}") from exc
    if not isinstance(state, dict):
        raise ResearchError("research-state block must be a JSON object")
    return state


def write_state(state: Mapping[str, Any]) -> None:
    text = NOW_PATH.read_text(encoding="utf-8")
    replacement = (
        "<!-- research-state:start -->\n```json\n"
        + json.dumps(state, ensure_ascii=False, indent=2)
        + "\n```\n<!-- research-state:end -->"
    )
    updated, count = STATE_RE.subn(replacement, text, count=1)
    if count != 1:
        raise ResearchError("could not replace research-state block")
    atomic_write_text(NOW_PATH, updated)


def read_decisions() -> Dict[str, Dict[str, Any]]:
    text = DECISIONS_PATH.read_text(encoding="utf-8")
    decisions: Dict[str, Dict[str, Any]] = {}
    for match in DECISION_RE.finditer(text):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            raise ResearchError(f"invalid structured decision: {exc}") from exc
        decision_id = value.get("decision_id")
        if not isinstance(decision_id, str):
            raise ResearchError("structured decision has no decision_id")
        if decision_id in decisions:
            raise ResearchError(f"duplicate structured decision: {decision_id}")
        decisions[decision_id] = value
    return decisions


def decision_allows(decision_id: Optional[str], action: str, target: Optional[Mapping[str, Any]] = None) -> bool:
    if not decision_id:
        return False
    decision = read_decisions().get(decision_id)
    if not decision or decision.get("status") != "APPROVED" or decision.get("decided_by") != "USER":
        return False
    if action not in decision.get("actions", []):
        return False
    declared_target = decision.get("target")
    if target is not None and declared_target is not None:
        for key in ("id", "version"):
            if declared_target.get(key) != target.get(key):
                return False
    return True


def mechanism_content_hash(document: Mapping[str, Any]) -> str:
    """Hash mechanism content independently of its formal transition fields."""
    content = copy.deepcopy(dict(document))
    content.pop("research_status", None)
    content.pop("decision_ref", None)
    return json_hash(content)


def mechanism_snapshot_hash(document: Mapping[str, Any]) -> str:
    """Hash the complete registered profile state except its decision pointer."""
    snapshot = copy.deepcopy(dict(document))
    snapshot.pop("decision_ref", None)
    return json_hash(snapshot)


def claim_definition_hash(claim: Mapping[str, Any]) -> str:
    """Bind evidence to the exact claim meaning, not its mutable status."""
    return json_hash(
        {
            key: claim.get(key)
            for key in (
                "id",
                "statement",
                "identity_criticality",
                "portability",
                "capability_ids",
                "falsifier",
            )
        }
    )


def hypothesis_definition_hash(hypothesis: Mapping[str, Any]) -> str:
    """Bind execution evidence to the exact hypothesis definition."""
    definition = copy.deepcopy(dict(hypothesis))
    definition.pop("execution_status", None)
    definition.pop("execution_evidence", None)
    return json_hash(definition)


def decision_allows_mechanism_transition(
    decision_id: Optional[str],
    action: str,
    document: Mapping[str, Any],
    path: Path,
) -> bool:
    """Require a user decision bound to one exact mechanism artifact."""
    if not decision_allows(decision_id, action, document):
        return False
    decision = read_decisions().get(str(decision_id))
    target = decision.get("target") if decision else None
    if not isinstance(target, Mapping):
        return False
    expected = {
        "kind": "MechanismProfile",
        "id": document.get("id"),
        "version": document.get("version"),
        "path": relative(path),
        "content_sha256": mechanism_content_hash(document),
    }
    return all(target.get(key) == value for key, value in expected.items())


def decision_allows_mechanism_registration(
    decision_id: Optional[str],
    document: Mapping[str, Any],
    path: Path,
) -> bool:
    """Require every canonical profile snapshot to be explicitly registered."""
    if not decision_allows(
        decision_id,
        "REGISTER_SCOPED_MECHANISM",
        document,
    ):
        return False
    decision = read_decisions().get(str(decision_id))
    target = decision.get("target") if decision else None
    if not isinstance(target, Mapping):
        return False
    expected = {
        "kind": "MechanismProfile",
        "id": document.get("id"),
        "version": document.get("version"),
        "path": relative(path),
        "content_sha256": mechanism_content_hash(document),
        "snapshot_sha256": mechanism_snapshot_hash(document),
    }
    return all(target.get(key) == value for key, value in expected.items())


def decision_allows_promotion(
    decision_id: Optional[str],
    action: str,
    candidate: Mapping[str, Any],
    candidate_path: Path,
) -> bool:
    """Bind activation/promotion authority to the exact candidate bytes."""
    if not decision_allows(decision_id, action, candidate):
        return False
    decision = read_decisions().get(str(decision_id))
    target = decision.get("target") if decision else None
    if not isinstance(target, Mapping):
        return False
    expected = {
        "id": candidate.get("id"),
        "version": candidate.get("version"),
        "source_path": relative(candidate_path),
        "source_sha256": sha256_file(candidate_path),
    }
    if (
        action == "ACTIVATE_PROBLEM"
        and candidate.get("schema_version") == "2.0"
    ):
        if verify_problem_activation_bundle(candidate, candidate_path):
            return False
        bundle_locator = candidate.get("activation_bundle_ref")
        if not isinstance(bundle_locator, str):
            return False
        bundle_path = resolve_root_path(bundle_locator)
        expected.update(
            {
                "activation_bundle_path": relative(bundle_path),
                "activation_bundle_sha256": sha256_file(bundle_path),
            }
        )
    return all(target.get(key) == value for key, value in expected.items())


def decision_allows_transfer(
    decision_id: Optional[str],
    action: str,
    target: Mapping[str, Any],
    disclosure: Mapping[str, Any],
    project: str,
) -> bool:
    if not decision_allows(decision_id, action, target):
        return False
    decision = read_decisions().get(str(decision_id))
    if not decision:
        return False
    scope = decision.get("standing_transfer_scope")
    if not isinstance(scope, dict):
        return True
    if scope.get("project") != project:
        return False
    destinations = scope.get("action_destinations", {}).get(action, [])
    if disclosure.get("destination") not in destinations:
        return False
    classification = disclosure.get("classification")
    if classification not in scope.get("allowed_classifications", []):
        return False
    payload_bytes = disclosure.get(
        "total_payload_bytes",
        disclosure.get("payload_size_bytes"),
    )
    if not isinstance(payload_bytes, int) or payload_bytes < 0:
        return False
    if payload_bytes > int(scope.get("max_payload_bytes", 0)):
        return False
    exclusions = {
        str(item).strip().lower()
        for item in disclosure.get("does_not_include", [])
    }
    required = scope.get("required_exclusions_by_classification", {}).get(
        classification,
        [],
    )
    if any(str(item).strip().lower() not in exclusions for item in required):
        return False
    return bool(scope.get("requires_frozen_disclosure_manifest"))


def project_path(value: Optional[str]) -> Path:
    if not value:
        return DEFAULT_PROJECT
    return resolve_root_path(value)


def project_contracts(project: Path) -> Tuple[Path, List[Path], List[Path], List[Path]]:
    problems = sorted((project / "problem").glob("*.json"))
    scenarios = sorted((project / "scenarios").glob("*.json"))
    lines = sorted((project / "lines").glob("*.json"))
    claims = sorted((project / "claims").rglob("*.json")) if (project / "claims").exists() else []
    if not problems:
        raise ResearchError(f"project has no problem contracts: {relative(project)}")
    return problems[0], scenarios, lines, claims


def check_companion(document: Mapping[str, Any], path: Path) -> List[str]:
    errors: List[str] = []
    locator = document.get("companion_markdown")
    if not isinstance(locator, str):
        return errors
    companion = resolve_root_path(locator)
    if not companion.is_file():
        return [f"{relative(path)}: companion missing: {locator}"]
    text = companion.read_text(encoding="utf-8")
    for key in ("id", "version"):
        value = str(document.get(key, ""))
        if value and value not in text:
            errors.append(f"{relative(path)}: companion does not name {key} {value}")
    if (
        document.get("kind") == "ProblemContract"
        and document.get("schema_version") == "2.0"
    ):
        expected_status = f"状态：`{document.get('status')}`"
        if expected_status not in text:
            errors.append(
                f"{relative(path)}: companion does not declare "
                f"{expected_status}"
            )
    if document.get("kind") == "MechanismProfile":
        actual_sha = sha256_file(companion)
        if document.get("companion_sha256") != actual_sha:
            errors.append(
                f"{relative(path)}: mechanism companion SHA-256 differs "
                f"for {locator}"
            )
        expected_status = f"状态：`{document.get('research_status')}`"
        if expected_status not in text:
            errors.append(
                f"{relative(path)}: mechanism companion does not declare "
                f"{expected_status}"
            )
    return errors


def check_problem_lineage(
    project: Path,
    path: Path,
    document: Mapping[str, Any],
) -> List[str]:
    lineage = document.get("lineage")
    if document.get("schema_version") != "2.0":
        return []
    if not isinstance(lineage, Mapping):
        return [f"{relative(path)}: ProblemContract 2.0 requires lineage"]

    errors: List[str] = []
    for locator_key, hash_key in (
        ("predecessor_ref", "predecessor_sha256"),
        ("predecessor_companion_ref", "predecessor_companion_sha256"),
        ("predecessor_audit_ref", "predecessor_audit_sha256"),
        (
            "predecessor_audit_companion_ref",
            "predecessor_audit_companion_sha256",
        ),
    ):
        locator = lineage.get(locator_key)
        expected_hash = lineage.get(hash_key)
        if not isinstance(locator, str):
            errors.append(f"{relative(path)}: lineage missing {locator_key}")
            continue
        predecessor_path = resolve_root_path(locator)
        if not predecessor_path.is_file():
            errors.append(f"{relative(path)}: lineage source missing: {locator}")
            continue
        if project not in predecessor_path.parents:
            errors.append(f"{relative(path)}: lineage source must stay in project: {locator}")
            continue
        actual_hash = sha256_file(predecessor_path)
        if actual_hash != expected_hash:
            errors.append(
                f"{relative(path)}: lineage {hash_key}={expected_hash!r}, "
                f"expected {actual_hash!r} for {locator}"
            )

    predecessor_ref = lineage.get("predecessor_ref")
    if isinstance(predecessor_ref, str):
        predecessor_path = resolve_root_path(predecessor_ref)
        if predecessor_path.is_file():
            predecessor = load_json(predecessor_path)
            if predecessor.get("kind") != "ProblemContract":
                errors.append(f"{relative(path)}: predecessor is not a ProblemContract")
            if predecessor.get("id") != document.get("id"):
                errors.append(f"{relative(path)}: predecessor problem id differs")
            current_version = str(document.get("version", ""))
            predecessor_version = str(predecessor.get("version", ""))
            if current_version == predecessor_version:
                errors.append(f"{relative(path)}: predecessor version must differ")
    return errors


def validate_historical_inheritance(
    document: Mapping[str, Any],
    path: Path,
) -> List[str]:
    errors = validate_schema(document, path)
    errors.extend(check_companion(document, path))
    if errors:
        return errors

    matrix_locator = document.get("canonical_capability_matrix")
    if not isinstance(matrix_locator, str):
        return [f"{relative(path)}: missing canonical_capability_matrix"]
    matrix_path = resolve_root_path(matrix_locator)
    if not matrix_path.is_file():
        return [f"{relative(path)}: capability matrix missing: {matrix_locator}"]

    try:
        with matrix_path.open(encoding="utf-8-sig", newline="") as handle:
            matrix_rows = list(csv.DictReader(handle))
    except (OSError, UnicodeError, csv.Error) as exc:
        return [f"{relative(path)}: cannot read capability matrix: {exc}"]

    matrix_by_id: Dict[str, Dict[str, str]] = {}
    for row in matrix_rows:
        capability_id = str(row.get("capability_id", ""))
        if not capability_id:
            errors.append(f"{matrix_locator}: capability row has no capability_id")
        elif capability_id in matrix_by_id:
            errors.append(f"{matrix_locator}: duplicate capability_id {capability_id}")
        else:
            matrix_by_id[capability_id] = row

    audit_by_id: Dict[str, Mapping[str, Any]] = {}
    for entry in document.get("capabilities", []):
        capability_id = str(entry.get("capability_id", ""))
        if capability_id in audit_by_id:
            errors.append(f"{relative(path)}: duplicate capability_id {capability_id}")
        else:
            audit_by_id[capability_id] = entry

    missing = sorted(set(matrix_by_id) - set(audit_by_id))
    extra = sorted(set(audit_by_id) - set(matrix_by_id))
    if missing:
        errors.append(
            f"{relative(path)}: inheritance audit omits canonical capabilities: {missing}"
        )
    if extra:
        errors.append(
            f"{relative(path)}: inheritance audit names unknown capabilities: {extra}"
        )

    for capability_id in sorted(set(matrix_by_id) & set(audit_by_id)):
        expected_status = matrix_by_id[capability_id].get("preservation_status")
        observed_status = audit_by_id[capability_id].get("archive_status")
        if observed_status != expected_status:
            errors.append(
                f"{relative(path)}: {capability_id} archive_status "
                f"{observed_status!r} differs from matrix {expected_status!r}"
            )

    coverage = {"EXPLICIT": 0, "PARTIAL": 0, "ABSENT": 0}
    for entry in audit_by_id.values():
        value = str(entry.get("problem_coverage", entry.get("v1_coverage", "")))
        if value in coverage:
            coverage[value] += 1
    declared = document.get("coverage_summary", {})
    for key, value in (
        ("explicit", coverage["EXPLICIT"]),
        ("partial", coverage["PARTIAL"]),
        ("absent", coverage["ABSENT"]),
    ):
        if declared.get(key) != value:
            errors.append(
                f"{relative(path)}: coverage_summary.{key}={declared.get(key)!r}, "
                f"expected {value}"
            )
    return errors


def check_problem_historical_inheritance(
    project: Path,
    path: Path,
    document: Mapping[str, Any],
) -> List[str]:
    errors: List[str] = []
    locator = document.get("historical_inheritance_ref")
    if project == DEFAULT_PROJECT and document.get("status") in {"CANDIDATE", "ACTIVE"}:
        if not isinstance(locator, str):
            return [
                f"{relative(path)}: CANDIDATE/ACTIVE problem requires "
                "historical_inheritance_ref"
            ]
    if not isinstance(locator, str):
        return errors

    audit_path = resolve_root_path(locator)
    if not audit_path.is_file():
        return [f"{relative(path)}: historical inheritance audit missing: {locator}"]
    if project not in audit_path.parents:
        errors.append(
            f"{relative(path)}: historical inheritance audit must stay in project: {locator}"
        )
        return errors

    audit = load_json(audit_path)
    errors.extend(validate_historical_inheritance(audit, audit_path))
    ref = audit.get("problem_ref", {})
    lineage = document.get("lineage", {})
    current_ref = (document.get("id"), document.get("version"))
    audit_ref = (ref.get("id"), ref.get("version"))
    requires_current_audit = (
        document.get("schema_version") == "2.0"
        or document.get("status") == "ACTIVE"
    )
    if requires_current_audit:
        if audit_ref != current_ref:
            errors.append(
                f"{relative(path)}: schema 2.0 or ACTIVE problem requires a "
                "current-version historical inheritance audit"
            )
    else:
        accepted_refs = {current_ref}
        predecessor_ref = (
            lineage.get("predecessor_ref")
            if isinstance(lineage, Mapping)
            else None
        )
        if isinstance(predecessor_ref, str):
            predecessor_path = resolve_root_path(predecessor_ref)
            if predecessor_path.is_file():
                predecessor = load_json(predecessor_path)
                accepted_refs.add(
                    (predecessor.get("id"), predecessor.get("version"))
                )
        if audit_ref not in accepted_refs:
            errors.append(
                f"{relative(audit_path)}: problem_ref does not match problem or "
                f"its exact predecessor"
            )

    if requires_current_audit:
        if audit.get("status") != "REVIEWED":
            errors.append(
                f"{relative(path)}: schema 2.0 or ACTIVE problem requires a "
                "REVIEWED historical inheritance audit"
            )
        if audit.get("activation_recommendation") != "READY":
            errors.append(
                f"{relative(path)}: schema 2.0 or ACTIVE problem requires "
                "historical activation_recommendation READY"
            )

    if document.get("schema_version") == "2.0":
        if not isinstance(lineage, Mapping):
            errors.append(
                f"{relative(path)}: ProblemContract 2.0 requires lineage "
                "before checking historical inheritance"
            )
            return errors
        predecessor_audit_locator = lineage.get("predecessor_audit_ref")
        predecessor_companion_locator = lineage.get(
            "predecessor_audit_companion_ref"
        )
        if isinstance(predecessor_audit_locator, str):
            predecessor_audit_path = resolve_root_path(
                predecessor_audit_locator
            )
            if predecessor_audit_path.resolve() == audit_path.resolve():
                errors.append(
                    f"{relative(path)}: current-version audit must have a "
                    "distinct path from predecessor audit"
                )
            if predecessor_audit_path.is_file():
                predecessor_audit = load_json(predecessor_audit_path)
                if predecessor_audit.get("id") == audit.get("id"):
                    errors.append(
                        f"{relative(path)}: current-version audit must have a "
                        "distinct id from predecessor audit"
                    )
        current_companion_locator = audit.get("companion_markdown")
        if (
            isinstance(predecessor_companion_locator, str)
            and isinstance(current_companion_locator, str)
            and resolve_root_path(predecessor_companion_locator).resolve()
            == resolve_root_path(current_companion_locator).resolve()
        ):
            errors.append(
                f"{relative(path)}: current-version audit companion must differ "
                "from predecessor audit companion"
            )
        for entry in audit.get("capabilities", []):
            if (
                not isinstance(entry, Mapping)
                or "problem_coverage" not in entry
                or "v1_coverage" in entry
            ):
                errors.append(
                    f"{relative(audit_path)}: ProblemContract 2.0 audit must use "
                    "problem_coverage for every capability"
                )
                break

    return errors


def verify_problem_activation_bundle(
    document: Mapping[str, Any],
    path: Path,
) -> List[str]:
    """Verify the immutable five-artifact preimage for ProblemContract 2.0."""
    if document.get("schema_version") != "2.0":
        return []

    errors: List[str] = []
    locator = document.get("activation_bundle_ref")
    if not isinstance(locator, str):
        return [
            f"{relative(path)}: ProblemContract 2.0 requires "
            "activation_bundle_ref"
        ]
    try:
        bundle_path = resolve_root_path(locator)
    except ResearchError as exc:
        return [str(exc)]
    if not bundle_path.is_file():
        return [
            f"{relative(path)}: problem activation bundle missing: {locator}"
        ]
    project = containing_project(path)
    if project is None:
        return [
            f"{relative(path)}: cannot locate project for problem activation "
            "bundle"
        ]
    expected_activation_dir = project / "problem" / "activation"
    if expected_activation_dir not in bundle_path.parents:
        errors.append(
            f"{relative(path)}: activation bundle must stay under "
            f"{relative(expected_activation_dir)}"
        )

    bundle = load_json(bundle_path)
    schema_errors = validate_schema(bundle, bundle_path)
    errors.extend(schema_errors)
    if schema_errors:
        return errors
    expected_ref = {
        "id": document.get("id"),
        "version": document.get("version"),
    }
    if bundle.get("problem_ref") != expected_ref:
        errors.append(
            f"{relative(bundle_path)}: problem_ref does not exactly match "
            f"{document.get('id')}@{document.get('version')}"
        )

    artifacts = bundle.get("artifacts", [])
    by_role: Dict[str, Mapping[str, Any]] = {}
    duplicate_roles: set[str] = set()
    for artifact in artifacts:
        if not isinstance(artifact, Mapping):
            continue
        role = str(artifact.get("role", ""))
        if role in by_role:
            duplicate_roles.add(role)
        else:
            by_role[role] = artifact
    if duplicate_roles:
        errors.append(
            f"{relative(bundle_path)}: duplicate activation artifact roles: "
            f"{sorted(duplicate_roles)}"
        )
    if set(by_role) != PROBLEM_ACTIVATION_ARTIFACT_ROLES:
        errors.append(
            f"{relative(bundle_path)}: activation artifact roles differ: "
            f"expected={sorted(PROBLEM_ACTIVATION_ARTIFACT_ROLES)} "
            f"actual={sorted(by_role)}"
        )
        return errors

    resolved_artifacts: Dict[str, Path] = {}
    for role, artifact in by_role.items():
        artifact_locator = artifact.get("path")
        if not isinstance(artifact_locator, str):
            errors.append(
                f"{relative(bundle_path)}: {role} has no artifact path"
            )
            continue
        try:
            artifact_path = resolve_root_path(artifact_locator)
        except ResearchError as exc:
            errors.append(str(exc))
            continue
        resolved_artifacts[role] = artifact_path
        if not artifact_path.is_file():
            errors.append(
                f"{relative(bundle_path)}: activation artifact missing: "
                f"{artifact_locator}"
            )
        elif artifact.get("sha256") != sha256_file(artifact_path):
            errors.append(
                f"{relative(bundle_path)}: activation artifact SHA-256 differs "
                f"for {role}: {artifact_locator}"
            )
    resolved_path_values = [
        artifact_path.resolve()
        for artifact_path in resolved_artifacts.values()
    ]
    if len(set(resolved_path_values)) != len(
        PROBLEM_ACTIVATION_ARTIFACT_ROLES
    ):
        errors.append(
            f"{relative(bundle_path)}: activation artifact roles must resolve "
            "to five distinct files"
        )

    candidate_path = resolved_artifacts.get("CANDIDATE_PROBLEM")
    if candidate_path is None or not candidate_path.is_file():
        return errors
    if bundle.get("candidate_path") != by_role["CANDIDATE_PROBLEM"].get(
        "path"
    ):
        errors.append(
            f"{relative(bundle_path)}: candidate_path must equal the "
            "CANDIDATE_PROBLEM artifact path"
        )
    candidate = load_json(candidate_path)
    errors.extend(check_companion(candidate, candidate_path))
    if (
        candidate.get("kind") != "ProblemContract"
        or candidate.get("schema_version") != "2.0"
        or candidate.get("status") != "CANDIDATE"
        or candidate.get("id") != document.get("id")
        or candidate.get("version") != document.get("version")
    ):
        errors.append(
            f"{relative(bundle_path)}: CANDIDATE_PROBLEM is not the exact "
            "schema 2.0 candidate for this problem"
        )
    if (
        document.get("status") == "CANDIDATE"
        and candidate_path.resolve() != path.resolve()
    ):
        errors.append(
            f"{relative(path)}: candidate problem must be the bundle's "
            "CANDIDATE_PROBLEM artifact"
        )
    if candidate.get("activation_bundle_ref") != locator:
        errors.append(
            f"{relative(candidate_path)}: activation_bundle_ref does not point "
            "back to the verified bundle"
        )

    expected_paths = {
        "CANDIDATE_COMPANION": candidate.get("companion_markdown"),
        "HISTORICAL_INHERITANCE_AUDIT": candidate.get(
            "historical_inheritance_ref"
        ),
    }
    for role, expected_locator in expected_paths.items():
        artifact_locator = by_role[role].get("path")
        if artifact_locator != expected_locator:
            errors.append(
                f"{relative(bundle_path)}: {role} path {artifact_locator!r} "
                f"does not match candidate reference {expected_locator!r}"
            )

    audit_path = resolved_artifacts.get("HISTORICAL_INHERITANCE_AUDIT")
    if audit_path is None or not audit_path.is_file():
        return errors
    audit = load_json(audit_path)
    if audit.get("problem_ref") != expected_ref:
        errors.append(
            f"{relative(audit_path)}: activation audit problem_ref does not "
            "match the candidate"
        )
    if audit.get("status") != "REVIEWED":
        errors.append(
            f"{relative(audit_path)}: activation audit must be REVIEWED"
        )
    if audit.get("activation_recommendation") != "READY":
        errors.append(
            f"{relative(audit_path)}: activation audit recommendation must be "
            "READY"
        )
    if by_role["HISTORICAL_INHERITANCE_COMPANION"].get(
        "path"
    ) != audit.get("companion_markdown"):
        errors.append(
            f"{relative(bundle_path)}: audit companion artifact does not match "
            "the current audit"
        )
    if by_role["CANONICAL_CAPABILITY_MATRIX"].get(
        "path"
    ) != audit.get("canonical_capability_matrix"):
        errors.append(
            f"{relative(bundle_path)}: capability matrix artifact does not "
            "match the current audit"
        )
    for entry in audit.get("capabilities", []):
        if (
            not isinstance(entry, Mapping)
            or "problem_coverage" not in entry
            or "v1_coverage" in entry
        ):
            errors.append(
                f"{relative(audit_path)}: activation audit must use "
                "problem_coverage for every capability"
            )
            break

    lineage = candidate.get("lineage", {})
    if isinstance(lineage, Mapping):
        predecessor_audit_locator = lineage.get("predecessor_audit_ref")
        predecessor_companion_locator = lineage.get(
            "predecessor_audit_companion_ref"
        )
        if isinstance(predecessor_audit_locator, str):
            predecessor_audit_path = resolve_root_path(
                predecessor_audit_locator
            )
            if predecessor_audit_path.resolve() == audit_path.resolve():
                errors.append(
                    f"{relative(bundle_path)}: current audit path equals "
                    "predecessor audit path"
                )
            if predecessor_audit_path.is_file():
                predecessor_audit = load_json(predecessor_audit_path)
                if predecessor_audit.get("id") == audit.get("id"):
                    errors.append(
                        f"{relative(bundle_path)}: current audit id equals "
                        "predecessor audit id"
                    )
        current_companion_locator = audit.get("companion_markdown")
        if (
            isinstance(predecessor_companion_locator, str)
            and isinstance(current_companion_locator, str)
            and resolve_root_path(predecessor_companion_locator).resolve()
            == resolve_root_path(current_companion_locator).resolve()
        ):
            errors.append(
                f"{relative(bundle_path)}: current audit companion equals "
                "predecessor audit companion"
            )
    return errors


def check_problem_scenario_line_semantics(
    project: Path,
    problems: Sequence[Path],
    scenarios: Sequence[Path],
    lines: Sequence[Path],
) -> List[str]:
    errors: List[str] = []
    problem_keys: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for path in problems:
        doc = load_json(path)
        problem_keys[(doc.get("id", ""), doc.get("version", ""))] = doc

    for path in scenarios:
        doc = load_json(path)
        ref = doc.get("problem_ref", {})
        key = (ref.get("id", ""), ref.get("version", ""))
        if key not in problem_keys:
            errors.append(f"{relative(path)}: unresolved problem_ref {key}")
        requires_user = bool(doc.get("activation", {}).get("requires_user_approval"))
        decision_id = doc.get("activation", {}).get("approval_decision_id")
        if doc.get("scenario_class") == "REAL":
            if not requires_user:
                errors.append(f"{relative(path)}: REAL scenario must require user approval")
            if doc.get("status") == "ACTIVE" and not decision_allows(
                decision_id, "ACTIVATE_REAL_SCENARIO", doc
            ):
                errors.append(f"{relative(path)}: active REAL scenario has no user activation decision")
        elif requires_user and doc.get("status") == "ACTIVE":
            if not decision_allows(decision_id, "ACTIVATE_SCENARIO", doc):
                errors.append(f"{relative(path)}: active scenario has no matching user decision")

    seen_lines: set[str] = set()
    for path in lines:
        doc = load_json(path)
        line_id = str(doc.get("id", ""))
        if line_id in seen_lines:
            errors.append(f"{relative(path)}: duplicate line id {line_id}")
        seen_lines.add(line_id)
        ref = doc.get("problem_ref", {})
        key = (ref.get("id", ""), ref.get("version", ""))
        if key not in problem_keys:
            errors.append(f"{relative(path)}: unresolved problem_ref {key}")
        if doc.get("schema_version") == "2.0":
            target = doc.get("research_target", {})
            mechanism_ref = target.get("mechanism_ref")
            if isinstance(mechanism_ref, str):
                mechanism_path = resolve_root_path(mechanism_ref)
                if not mechanism_path.is_file():
                    errors.append(
                        f"{relative(path)}: mechanism profile missing: {mechanism_ref}"
                    )
                else:
                    mechanism = load_json(mechanism_path)
                    if mechanism.get("kind") != "MechanismProfile":
                        errors.append(
                            f"{relative(path)}: mechanism_ref is not a MechanismProfile"
                        )
                    mechanism_problem = mechanism.get("problem_ref", {})
                    if (
                        mechanism_problem.get("id"),
                        mechanism_problem.get("version"),
                    ) != key:
                        errors.append(
                            f"{relative(path)}: mechanism problem_ref must exactly "
                            f"match line problem_ref {key}"
                        )
                    if mechanism.get("native_line") != doc.get("native_line"):
                        errors.append(
                            f"{relative(path)}: mechanism native_line must exactly "
                            "match line native_line"
                        )
                    profile_claims = {
                        claim.get("id") for claim in mechanism.get("scoped_claims", [])
                    }
                    unknown_claims = sorted(
                        set(target.get("scoped_claim_ids", [])) - profile_claims
                    )
                    if unknown_claims:
                        errors.append(
                            f"{relative(path)}: unknown mechanism scoped claims: "
                            f"{unknown_claims}"
                        )
                    hypothesis_by_id = {
                        hypothesis.get("id"): hypothesis
                        for hypothesis in mechanism.get("hypothesis_map", [])
                    }
                    selected_hypotheses = target.get("hypothesis_ids", [])
                    if not selected_hypotheses:
                        errors.append(
                            f"{relative(path)}: EXISTING_MECHANISM line requires "
                            "research_target.hypothesis_ids"
                        )
                    unknown_hypotheses = sorted(
                        set(selected_hypotheses) - set(hypothesis_by_id)
                    )
                    if unknown_hypotheses:
                        errors.append(
                            f"{relative(path)}: unknown mechanism hypotheses: "
                            f"{unknown_hypotheses}"
                        )
                    hypothesis_claims = {
                        claim_id
                        for hypothesis_id in selected_hypotheses
                        for claim_id in hypothesis_by_id.get(
                            hypothesis_id, {}
                        ).get("scoped_claim_ids", [])
                    }
                    declared_claims = set(target.get("scoped_claim_ids", []))
                    if not unknown_hypotheses and declared_claims != hypothesis_claims:
                        errors.append(
                            f"{relative(path)}: scoped_claim_ids must exactly match "
                            "the selected hypotheses' claim scope"
                        )
                    declared_unaffected = set(
                        doc.get("outcome_policy", {}).get(
                            "unaffected_claim_ids",
                            [],
                        )
                    )
                    expected_unaffected = profile_claims - declared_claims
                    if declared_unaffected != expected_unaffected:
                        errors.append(
                            f"{relative(path)}: outcome_policy.unaffected_claim_ids "
                            "must exactly enumerate every mechanism claim outside "
                            "the frozen test scope"
                        )
            if (
                doc.get("status") == "ACTIVE"
                and target.get("kind") == "NEW_GAP"
                and doc.get("prior_solution_review", {}).get("disposition")
                != "GAP_CONFIRMED"
            ):
                errors.append(
                    f"{relative(path)}: ACTIVE NEW_GAP line requires "
                    "prior_solution_review disposition GAP_CONFIRMED"
                )
            review = doc.get("prior_solution_review", {})
            checked_historical = review.get("checked_historical_refs", [])
            checked_existing = review.get("checked_existing_solution_refs", [])
            if (
                doc.get("status") == "ACTIVE"
                and review.get("disposition") == "UNRESOLVED"
            ):
                errors.append(
                    f"{relative(path)}: ACTIVE LineContract 2.0 requires "
                    "a resolved prior_solution_review disposition"
                )
            checked_refs = [*checked_historical, *checked_existing]
            for locator in checked_refs:
                if locator not in doc.get("source_allowlist", []):
                    errors.append(
                        f"{relative(path)}: prior-solution source must be in "
                        f"source_allowlist: {locator}"
                    )
                    continue
                try:
                    checked_path = resolve_root_path(locator)
                except ResearchError as exc:
                    errors.append(str(exc))
                    continue
                if not checked_path.is_file():
                    errors.append(
                        f"{relative(path)}: prior-solution source missing: "
                        f"{locator}"
                    )
            if (
                target.get("kind") == "NEW_GAP"
                and review.get("disposition") == "GAP_CONFIRMED"
            ):
                if not checked_historical or not checked_existing:
                    errors.append(
                        f"{relative(path)}: GAP_CONFIRMED requires non-empty "
                        "historical and existing-solution source refs"
                    )
                finding_refs = {
                    finding.get("source_ref")
                    for finding in review.get("coverage_findings", [])
                }
                missing_findings = sorted(set(checked_refs) - finding_refs)
                if missing_findings:
                    errors.append(
                        f"{relative(path)}: GAP_CONFIRMED lacks per-source "
                        f"coverage findings: {missing_findings}"
                    )
            problem = problem_keys.get(key, {})
            basis_ids = {
                item.get("id")
                for item in problem.get("shared_basis", {}).get(
                    "world_assumptions", []
                )
            }
            unknown_assumptions = sorted(
                set(target.get("applicable_assumptions", [])) - basis_ids
            )
            if unknown_assumptions:
                errors.append(
                    f"{relative(path)}: unknown shared-basis assumptions: "
                    f"{unknown_assumptions}"
                )
        for locator in doc.get("source_allowlist", []):
            try:
                source = resolve_root_path(locator)
            except ResearchError as exc:
                errors.append(str(exc))
                continue
            if not source.is_file():
                errors.append(f"{relative(path)}: allowed source missing: {locator}")
            if ".research-runtime" in source.parts:
                errors.append(f"{relative(path)}: runtime source cannot be allowlisted: {locator}")
            if ROOT / "research" not in source.parents:
                errors.append(f"{relative(path)}: allowed source must be under research/: {locator}")
            if source in {NOW_PATH, DECISIONS_PATH} or "candidates" in source.parts:
                errors.append(f"{relative(path)}: canonical state or candidate output cannot be a worker source: {locator}")

    if project == DEFAULT_PROJECT:
        expected = {
            "DISCOVERY_BOUNDARY",
            "RELATION_CONSTITUTION",
            "POSSIBILITY_FORMATION",
            "CAPABILITY_REALIZATION",
            "AUTHORITY_NORMS",
            "REALITY_EFFECT",
            "RUNTIME_EVOLUTION",
        }
        actual = {load_json(path).get("native_line") for path in lines}
        if actual != expected:
            errors.append(f"default project native lines differ: expected={sorted(expected)} actual={sorted(actual)}")
    return errors


def check_mechanism_result_binding(
    project: Path,
    profile: Mapping[str, Any],
    profile_path: Path,
    binding: Mapping[str, Any],
    *,
    claim: Optional[Mapping[str, Any]] = None,
    hypothesis: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    """Validate one immutable finalized result binding for a mechanism item."""
    errors: List[str] = []
    try:
        result_path = resolve_root_path(str(binding.get("result_path", "")))
        receipt_path = resolve_root_path(
            str(binding.get("evidence_receipt_path", ""))
        )
        manifest_path = resolve_root_path(
            str(binding.get("finalization_manifest_path", ""))
        )
        plan_snapshot_path = resolve_root_path(
            str(binding.get("plan_snapshot_path", ""))
        )
        plan_seal_path = resolve_root_path(
            str(binding.get("plan_seal_path", ""))
        )
        run_manifest_snapshot_path = resolve_root_path(
            str(binding.get("run_manifest_snapshot_path", ""))
        )
        input_snapshot_path = resolve_root_path(
            str(binding.get("input_snapshot_path", ""))
        )
        raw_result_snapshot_path = resolve_root_path(
            str(binding.get("raw_result_snapshot_path", ""))
        )
        events_snapshot_path = resolve_root_path(
            str(binding.get("events_snapshot_path", ""))
        )
        completion_seal_snapshot_path = resolve_root_path(
            str(binding.get("completion_seal_snapshot_path", ""))
        )
    except ResearchError as exc:
        return [str(exc)]
    candidates_root = project / "candidates"
    if candidates_root not in result_path.parents:
        errors.append(
            f"mechanism evidence result is not in finalized candidate space: "
            f"{relative(result_path)}"
        )
        return errors
    packet_root = result_path.parent
    if any(
        path.parent != packet_root
        for path in (
            receipt_path,
            manifest_path,
            plan_snapshot_path,
            plan_seal_path,
            run_manifest_snapshot_path,
            input_snapshot_path,
            raw_result_snapshot_path,
            events_snapshot_path,
            completion_seal_snapshot_path,
        )
    ):
        errors.append(
            "mechanism result, receipts, and frozen run snapshots belong to "
            "different candidate packets"
        )
        return errors
    if manifest_path != packet_root / "finalization-manifest.json":
        errors.append("mechanism binding does not name the packet finalization manifest")
        return errors
    required_artifacts = (
        result_path,
        receipt_path,
        manifest_path,
        plan_snapshot_path,
        plan_seal_path,
        run_manifest_snapshot_path,
        input_snapshot_path,
        raw_result_snapshot_path,
        events_snapshot_path,
        completion_seal_snapshot_path,
    )
    if any(not path.is_file() for path in required_artifacts):
        errors.append("mechanism evidence binding points to missing finalized artifacts")
        return errors
    manifest = load_json(manifest_path)
    result_sha = sha256_file(result_path)
    receipt_sha = sha256_file(receipt_path)
    manifest_sha = sha256_file(manifest_path)
    plan_snapshot_sha = sha256_file(plan_snapshot_path)
    plan_seal_sha = sha256_file(plan_seal_path)
    run_manifest_snapshot_sha = sha256_file(run_manifest_snapshot_path)
    input_snapshot_sha = sha256_file(input_snapshot_path)
    raw_result_snapshot_sha = sha256_file(raw_result_snapshot_path)
    events_snapshot_sha = sha256_file(events_snapshot_path)
    completion_seal_snapshot_sha = sha256_file(
        completion_seal_snapshot_path
    )
    if (
        manifest.get("status") != "CANDIDATE"
        or manifest.get("result_hashes", {}).get(result_path.name) != result_sha
        or manifest.get("result_hashes", {}).get(receipt_path.name) != receipt_sha
        or manifest.get("result_hashes", {}).get(plan_snapshot_path.name)
        != plan_snapshot_sha
        or manifest.get("result_hashes", {}).get(plan_seal_path.name)
        != plan_seal_sha
        or manifest.get("result_hashes", {}).get(run_manifest_snapshot_path.name)
        != run_manifest_snapshot_sha
        or manifest.get("result_hashes", {}).get(input_snapshot_path.name)
        != input_snapshot_sha
        or manifest.get("result_hashes", {}).get(raw_result_snapshot_path.name)
        != raw_result_snapshot_sha
        or manifest.get("result_hashes", {}).get(events_snapshot_path.name)
        != events_snapshot_sha
        or manifest.get("result_hashes", {}).get(
            completion_seal_snapshot_path.name
        )
        != completion_seal_snapshot_sha
    ):
        errors.append("mechanism evidence is not hash-bound by its candidate packet")
        return errors
    expected_binding_hashes = {
        "result_sha256": result_sha,
        "evidence_receipt_sha256": receipt_sha,
        "finalization_manifest_sha256": manifest_sha,
        "plan_snapshot_sha256": plan_snapshot_sha,
        "plan_seal_sha256": plan_seal_sha,
        "run_manifest_snapshot_sha256": run_manifest_snapshot_sha,
        "input_snapshot_sha256": input_snapshot_sha,
        "raw_result_snapshot_sha256": raw_result_snapshot_sha,
        "events_snapshot_sha256": events_snapshot_sha,
        "completion_seal_snapshot_sha256": completion_seal_snapshot_sha,
    }
    for field, expected_sha in expected_binding_hashes.items():
        if binding.get(field) != expected_sha:
            errors.append(
                f"mechanism evidence {field} differs from its finalized artifact"
            )

    result = load_json(result_path)
    receipt = load_json(receipt_path)
    plan_snapshot = load_json(plan_snapshot_path)
    plan_seal = load_controller_seal(plan_seal_path)
    run_manifest_snapshot = load_json(run_manifest_snapshot_path)
    input_snapshot = load_json(input_snapshot_path)
    raw_result_snapshot = load_json(raw_result_snapshot_path)
    completion_seal_snapshot = load_controller_seal(
        completion_seal_snapshot_path
    )
    if (
        plan_snapshot.get("schema_version") != "2.0"
        or plan_snapshot.get("plan_fingerprint")
        != compute_plan_fingerprint(plan_snapshot)
        or plan_seal.get("kind") != "PlanControllerSeal"
        or plan_seal.get("plan_fingerprint")
        != plan_snapshot.get("plan_fingerprint")
    ):
        errors.append("mechanism evidence plan snapshot has an invalid fingerprint")
    run_manifest_schema_errors = validate_schema(
        run_manifest_snapshot,
        run_manifest_snapshot_path,
    )
    if run_manifest_schema_errors:
        errors.append("mechanism evidence run manifest snapshot is invalid")
    if (
        run_manifest_snapshot.get("status") != "COMPLETED"
        or run_manifest_snapshot.get("run_id") != result.get("run_id")
        or run_manifest_snapshot.get("input_hash") != result.get("input_hash")
        or run_manifest_snapshot.get("result_sha256") != result_sha
        or run_manifest_snapshot.get("raw_result_sha256")
        != raw_result_snapshot_sha
        or run_manifest_snapshot.get("events_sha256")
        != events_snapshot_sha
        or run_manifest_snapshot.get("completion_seal_sha256")
        != completion_seal_snapshot_sha
        or run_manifest_snapshot.get("plan_fingerprint")
        != plan_snapshot.get("plan_fingerprint")
    ):
        errors.append(
            "mechanism evidence run snapshot does not prove the finalized "
            "completed result"
        )
    if (
        completion_seal_snapshot.get("kind")
        != "RunCompletionControllerSeal"
        or completion_seal_snapshot.get("run_id") != result.get("run_id")
        or completion_seal_snapshot.get("input_hash")
        != result.get("input_hash")
        or completion_seal_snapshot.get("result_sha256") != result_sha
        or completion_seal_snapshot.get("raw_result_sha256")
        != raw_result_snapshot_sha
        or completion_seal_snapshot.get("events_sha256")
        != events_snapshot_sha
    ):
        errors.append(
            "mechanism evidence completion seal does not bind its artifacts"
        )
    matching_planned_runs = [
        run
        for run in plan_snapshot.get("runs", [])
        if run.get("run_id") == result.get("run_id")
    ]
    if (
        len(matching_planned_runs) != 1
        or matching_planned_runs[0].get("input_hash") != result.get("input_hash")
        or matching_planned_runs[0].get("input_payload_sha256")
        != input_snapshot_sha
        or matching_planned_runs[0].get("research_focus")
        != run_manifest_snapshot.get("research_focus")
    ):
        errors.append(
            "mechanism evidence result is not an exact run in its frozen plan"
        )
    elif (
        input_snapshot.get("input_hash")
        != run_input_hash(input_snapshot)
        or input_snapshot.get("input_hash") != result.get("input_hash")
    ):
        errors.append(
            "mechanism evidence input snapshot has an invalid semantic hash"
        )
    else:
        errors.extend(
            frozen_bundle_binding_errors(
                plan_snapshot,
                matching_planned_runs[0],
                run_manifest_snapshot,
                input_snapshot,
            )
        )
    rebound = bind_result_envelope(raw_result_snapshot, input_snapshot)
    rebound_content = copy.deepcopy(rebound)
    result_content = copy.deepcopy(result)
    rebound_content.pop("cost", None)
    result_content.pop("cost", None)
    if canonical_bytes(rebound_content) != canonical_bytes(result_content):
        errors.append(
            "mechanism evidence result differs from its finalized raw output"
        )
    if claim is not None and result.get("status") != "COMPLETED":
        errors.append(
            "only a COMPLETED ResearchResult can support or refute a "
            "canonical mechanism claim"
        )
    expected_problem_ref = (
        f"{profile.get('problem_ref', {}).get('id')}@"
        f"{profile.get('problem_ref', {}).get('version')}"
    )
    if manifest.get("problem_ref") != expected_problem_ref:
        errors.append("mechanism evidence candidate packet uses another problem")
    for key in ("run_id", "input_hash"):
        if (
            binding.get(key) != result.get(key)
            or binding.get(key) != receipt.get(key)
        ):
            errors.append(f"mechanism evidence {key} is not consistently bound")
    if receipt.get("result_path") != relative(result_path):
        errors.append("mechanism evidence receipt points to another result path")
    if receipt.get("result_sha256") != result_sha:
        errors.append("mechanism evidence receipt has a different result hash")
    receipt_snapshots = {
        "plan_snapshot_path": relative(plan_snapshot_path),
        "plan_snapshot_sha256": plan_snapshot_sha,
        "plan_seal_path": relative(plan_seal_path),
        "plan_seal_sha256": plan_seal_sha,
        "run_manifest_snapshot_path": relative(run_manifest_snapshot_path),
        "run_manifest_snapshot_sha256": run_manifest_snapshot_sha,
        "input_snapshot_path": relative(input_snapshot_path),
        "input_snapshot_sha256": input_snapshot_sha,
        "raw_result_snapshot_path": relative(raw_result_snapshot_path),
        "raw_result_snapshot_sha256": raw_result_snapshot_sha,
        "events_snapshot_path": relative(events_snapshot_path),
        "events_snapshot_sha256": events_snapshot_sha,
        "completion_seal_snapshot_path": relative(
            completion_seal_snapshot_path
        ),
        "completion_seal_snapshot_sha256": completion_seal_snapshot_sha,
    }
    if any(receipt.get(key) != value for key, value in receipt_snapshots.items()):
        errors.append(
            "mechanism evidence receipt does not bind the frozen plan and "
            "completed run manifest snapshots"
        )
    if receipt.get("problem_ref") != expected_problem_ref:
        errors.append("mechanism evidence receipt uses another problem")
    if receipt.get("mechanism_ref") != relative(profile_path):
        errors.append("mechanism evidence receipt names another mechanism artifact")
    if (
        receipt.get("mechanism_id"),
        receipt.get("mechanism_version"),
    ) != (profile.get("id"), profile.get("version")):
        errors.append("mechanism evidence receipt names another mechanism version")
    if receipt.get("study_mode") not in {"MECHANISM", "REALITY_TEST"}:
        errors.append(
            "problem-definition or source-acquisition runs cannot change "
            "canonical mechanism evidence"
        )

    if claim is not None:
        claim_id = claim.get("id")
        definition_sha = claim_definition_hash(claim)
        if claim_id not in result.get("tested_claim_ids", []):
            errors.append(f"mechanism result did not test claim {claim_id}")
        owning_hypotheses = {
            item.get("id")
            for item in profile.get("hypothesis_map", [])
            if claim_id in item.get("scoped_claim_ids", [])
        }
        if not owning_hypotheses.intersection(result.get("hypothesis_ids", [])):
            errors.append(
                f"mechanism result does not bind claim {claim_id} to one of "
                "its declared hypotheses"
            )
        if binding.get("definition_sha256") != definition_sha:
            errors.append(f"mechanism claim definition changed after its evidence")
        if (
            receipt.get("claim_definition_sha256", {}).get(claim_id)
            != definition_sha
        ):
            errors.append(f"mechanism evidence receipt does not bind claim {claim_id}")
        updates = {
            item.get("claim_id"): item.get("proposed_status")
            for item in result.get("scoped_claim_updates", [])
        }
        expected_update = {
            "SUPPORTED_SYNTHETIC": "SUPPORTED_CANDIDATE",
            "SUPPORTED_LOCAL": "SUPPORTED_CANDIDATE",
            "REFUTED": "REFUTED_CANDIDATE",
        }.get(str(claim.get("evidence_status")))
        if updates.get(claim_id) != expected_update:
            errors.append(
                f"mechanism claim {claim_id} status is not supported by the "
                "candidate result"
            )
        if (
            claim.get("evidence_status") == "SUPPORTED_SYNTHETIC"
            and receipt.get("scenario_class") != "SYNTHETIC"
        ):
            errors.append("SUPPORTED_SYNTHETIC requires a synthetic scenario")
        if (
            claim.get("evidence_status") == "SUPPORTED_LOCAL"
            and receipt.get("scenario_class") not in {"LOCAL_SANDBOX", "REAL"}
        ):
            errors.append("SUPPORTED_LOCAL requires a local-sandbox or real scenario")

    if hypothesis is not None:
        hypothesis_id = hypothesis.get("id")
        definition_sha = hypothesis_definition_hash(hypothesis)
        if hypothesis_id not in result.get("hypothesis_ids", []):
            errors.append(
                f"mechanism result did not execute hypothesis {hypothesis_id}"
            )
        if binding.get("definition_sha256") != definition_sha:
            errors.append("mechanism hypothesis definition changed after execution")
        if (
            receipt.get("hypothesis_definition_sha256", {}).get(hypothesis_id)
            != definition_sha
        ):
            errors.append(
                f"mechanism evidence receipt does not bind hypothesis "
                f"{hypothesis_id}"
            )
        outcome_by_id = {
            item.get("hypothesis_id"): item.get("outcome")
            for item in result.get("hypothesis_outcomes", [])
        }
        expected_outcome = {
            "COMPLETED": "COMPLETED",
            "INCONCLUSIVE": "INCONCLUSIVE",
            "INVALIDATED": "INVALIDATED",
        }.get(str(hypothesis.get("execution_status")))
        if result.get("status") in {"FAILED", "REFUSED"}:
            errors.append(
                "FAILED or REFUSED ResearchResult cannot change canonical "
                "hypothesis execution state"
            )
        if outcome_by_id.get(hypothesis_id) != expected_outcome:
            errors.append(
                f"mechanism hypothesis {hypothesis_id} execution status is "
                "not supported by its structured result outcome"
            )
    return errors


def check_mechanism_semantics(
    project: Path,
    problems: Sequence[Path],
    lines: Sequence[Path],
    profiles: Sequence[Path],
) -> List[str]:
    errors: List[str] = []
    problem_keys = {
        (doc.get("id"), doc.get("version"))
        for doc in (load_json(path) for path in problems)
    }
    line_ids = {load_json(path).get("id") for path in lines}
    seen_profiles: set[str] = set()
    for path in profiles:
        doc = load_json(path)
        profile_id = str(doc.get("id", ""))
        if profile_id in seen_profiles:
            errors.append(f"{relative(path)}: duplicate mechanism profile id {profile_id}")
        seen_profiles.add(profile_id)
        if not decision_allows_mechanism_registration(
            doc.get("decision_ref"),
            doc,
            path,
        ):
            errors.append(
                f"{relative(path)}: canonical mechanism profile is not bound "
                "to an exact registered snapshot via "
                "REGISTER_SCOPED_MECHANISM"
            )
        ref = doc.get("problem_ref", {})
        if (ref.get("id"), ref.get("version")) not in problem_keys:
            errors.append(
                f"{relative(path)}: unresolved mechanism problem_ref "
                f"{(ref.get('id'), ref.get('version'))}"
            )
        claim_ids = [claim.get("id") for claim in doc.get("scoped_claims", [])]
        if len(claim_ids) != len(set(claim_ids)):
            errors.append(f"{relative(path)}: duplicate scoped claim id")
        hypothesis_ids = [
            hypothesis.get("id") for hypothesis in doc.get("hypothesis_map", [])
        ]
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            errors.append(f"{relative(path)}: duplicate hypothesis id")
        hypothesis_claims = {
            claim_id
            for hypothesis in doc.get("hypothesis_map", [])
            for claim_id in hypothesis.get("scoped_claim_ids", [])
        }
        unknown_hypothesis_claims = sorted(hypothesis_claims - set(claim_ids))
        if unknown_hypothesis_claims:
            errors.append(
                f"{relative(path)}: hypotheses reference unknown scoped claims: "
                f"{unknown_hypothesis_claims}"
            )
        profile_capabilities = set(doc.get("capability_ids", []))
        for claim in doc.get("scoped_claims", []):
            unknown_capabilities = sorted(
                set(claim.get("capability_ids", [])) - profile_capabilities
            )
            if unknown_capabilities:
                errors.append(
                    f"{relative(path)}: claim {claim.get('id')} references "
                    f"unknown capabilities: {unknown_capabilities}"
                )
        missing_owners = sorted(set(doc.get("owner_line_ids", [])) - line_ids)
        if missing_owners:
            errors.append(
                f"{relative(path)}: unknown owner_line_ids: {missing_owners}"
            )
        for locator in doc.get("evidence_refs", []):
            try:
                source = resolve_root_path(locator)
            except ResearchError as exc:
                errors.append(str(exc))
                continue
            if not source.is_file():
                errors.append(f"{relative(path)}: evidence source missing: {locator}")
            elif ROOT / "research" not in source.parents:
                errors.append(
                    f"{relative(path)}: mechanism evidence must be under research/: "
                    f"{locator}"
                )
        evidence_transition = False
        for claim in doc.get("scoped_claims", []):
            if claim.get("evidence_status") in {
                "SUPPORTED_SYNTHETIC",
                "SUPPORTED_LOCAL",
                "REFUTED",
            }:
                evidence_transition = True
                for binding in claim.get("status_evidence", []):
                    errors.extend(
                        f"{relative(path)}: {message}"
                        for message in check_mechanism_result_binding(
                            project,
                            doc,
                            path,
                            binding,
                            claim=claim,
                        )
                    )
        for hypothesis in doc.get("hypothesis_map", []):
            if hypothesis.get("execution_status") == "RUNNING":
                errors.append(
                    f"{relative(path)}: RUNNING is runtime state and cannot be "
                    "stored in a canonical MechanismProfile"
                )
            if (
                hypothesis.get("provenance_status") == "EMPIRICAL"
                or hypothesis.get("execution_status")
                in {"COMPLETED", "INCONCLUSIVE", "INVALIDATED"}
            ):
                evidence_transition = True
                if hypothesis.get("execution_status") not in {
                    "COMPLETED",
                    "INCONCLUSIVE",
                    "INVALIDATED",
                }:
                    errors.append(
                        f"{relative(path)}: EMPIRICAL hypothesis must declare "
                        "a finalized execution status"
                    )
                for binding in hypothesis.get("execution_evidence", []):
                    errors.extend(
                        f"{relative(path)}: {message}"
                        for message in check_mechanism_result_binding(
                            project,
                            doc,
                            path,
                            binding,
                            hypothesis=hypothesis,
                        )
                    )
        if evidence_transition and not decision_allows_mechanism_transition(
            doc.get("decision_ref"),
            "UPDATE_SCOPED_MECHANISM_EVIDENCE",
            doc,
            path,
        ):
            errors.append(
                f"{relative(path)}: canonical mechanism evidence changes require "
                "an exact content-bound user decision action "
                "UPDATE_SCOPED_MECHANISM_EVIDENCE"
            )
        if doc.get("research_status") == "VALIDATED_SCOPED":
            scope = doc.get("validated_scope") or {}
            claims_by_id = {
                claim.get("id"): claim
                for claim in doc.get("scoped_claims", [])
            }
            hypotheses_by_id = {
                hypothesis.get("id"): hypothesis
                for hypothesis in doc.get("hypothesis_map", [])
            }
            scoped_claim_ids = set(scope.get("claim_ids", []))
            scoped_hypothesis_ids = set(scope.get("hypothesis_ids", []))
            unknown_scope_claims = sorted(scoped_claim_ids - set(claims_by_id))
            unknown_scope_hypotheses = sorted(
                scoped_hypothesis_ids - set(hypotheses_by_id)
            )
            if unknown_scope_claims:
                errors.append(
                    f"{relative(path)}: validated_scope has unknown claims: "
                    f"{unknown_scope_claims}"
                )
            if unknown_scope_hypotheses:
                errors.append(
                    f"{relative(path)}: validated_scope has unknown hypotheses: "
                    f"{unknown_scope_hypotheses}"
                )
            for claim_id in scoped_claim_ids & set(claims_by_id):
                if claims_by_id[claim_id].get("evidence_status") not in {
                    "SUPPORTED_SYNTHETIC",
                    "SUPPORTED_LOCAL",
                }:
                    errors.append(
                        f"{relative(path)}: validated claim lacks supported "
                        f"evidence state: {claim_id}"
                    )
            for hypothesis_id in (
                scoped_hypothesis_ids & set(hypotheses_by_id)
            ):
                if (
                    hypotheses_by_id[hypothesis_id].get("execution_status")
                    != "COMPLETED"
                ):
                    errors.append(
                        f"{relative(path)}: validated hypothesis is not "
                        f"COMPLETED: {hypothesis_id}"
                    )
            covered_claims = {
                claim_id
                for hypothesis_id in scoped_hypothesis_ids
                for claim_id in hypotheses_by_id.get(
                    hypothesis_id, {}
                ).get("scoped_claim_ids", [])
            }
            if scoped_claim_ids - covered_claims:
                errors.append(
                    f"{relative(path)}: validated claims are not covered by "
                    "validated hypotheses"
                )
            for hypothesis_id in (
                scoped_hypothesis_ids & set(hypotheses_by_id)
            ):
                hypothesis_claim_ids = set(
                    hypotheses_by_id[hypothesis_id].get(
                        "scoped_claim_ids", []
                    )
                )
                if (
                    not hypothesis_claim_ids
                    or not hypothesis_claim_ids.issubset(scoped_claim_ids)
                ):
                    errors.append(
                        f"{relative(path)}: validated hypothesis "
                        f"{hypothesis_id} does not exclusively cover the "
                        "validated claim scope"
                    )
            expected_capabilities = {
                capability_id
                for claim_id in scoped_claim_ids
                for capability_id in claims_by_id.get(
                    claim_id, {}
                ).get("capability_ids", [])
            }
            if set(scope.get("capability_ids", [])) != expected_capabilities:
                errors.append(
                    f"{relative(path)}: validated_scope capability_ids must "
                    "exactly equal the validated claims' capabilities"
                )
        if doc.get("research_status") in {
            "REBASE_REQUIRED",
            "REFUTED_SCOPED",
        }:
            scope = doc.get("adverse_scope") or {}
            claims_by_id = {
                claim.get("id"): claim
                for claim in doc.get("scoped_claims", [])
            }
            hypotheses_by_id = {
                hypothesis.get("id"): hypothesis
                for hypothesis in doc.get("hypothesis_map", [])
            }
            affected_claims = set(scope.get("claim_ids", []))
            affected_hypotheses = set(scope.get("hypothesis_ids", []))
            unaffected_claims = set(scope.get("unaffected_claim_ids", []))
            if affected_claims - set(claims_by_id):
                errors.append(
                    f"{relative(path)}: adverse_scope has unknown claims"
                )
            if affected_hypotheses - set(hypotheses_by_id):
                errors.append(
                    f"{relative(path)}: adverse_scope has unknown hypotheses"
                )
            if affected_claims & unaffected_claims:
                errors.append(
                    f"{relative(path)}: adverse_scope marks a claim both "
                    "affected and unaffected"
                )
            if unaffected_claims != set(claims_by_id) - affected_claims:
                errors.append(
                    f"{relative(path)}: adverse_scope must enumerate every "
                    "unaffected mechanism claim"
                )
            hypothesis_claims = {
                claim_id
                for hypothesis_id in affected_hypotheses
                for claim_id in hypotheses_by_id.get(
                    hypothesis_id, {}
                ).get("scoped_claim_ids", [])
            }
            if not affected_claims.issubset(hypothesis_claims):
                errors.append(
                    f"{relative(path)}: adverse claims are not covered by "
                    "the affected hypotheses"
                )
            for hypothesis_id in affected_hypotheses & set(hypotheses_by_id):
                owned_claims = set(
                    hypotheses_by_id[hypothesis_id].get(
                        "scoped_claim_ids", []
                    )
                )
                if not owned_claims or not owned_claims.issubset(
                    affected_claims
                ):
                    errors.append(
                        f"{relative(path)}: adverse hypothesis "
                        f"{hypothesis_id} escapes the affected claim scope"
                    )
            expected_capabilities = {
                capability_id
                for claim_id in affected_claims
                for capability_id in claims_by_id.get(
                    claim_id, {}
                ).get("capability_ids", [])
            }
            if set(scope.get("capability_ids", [])) != expected_capabilities:
                errors.append(
                    f"{relative(path)}: adverse_scope capability_ids must "
                    "exactly equal the affected claims' capabilities"
                )
            for claim_id in affected_claims & set(claims_by_id):
                if (
                    claims_by_id[claim_id].get("evidence_status")
                    != "REFUTED"
                ):
                    errors.append(
                        f"{relative(path)}: adverse claim lacks REFUTED "
                        f"evidence state: {claim_id}"
                    )
            for hypothesis_id in (
                affected_hypotheses & set(hypotheses_by_id)
            ):
                hypothesis = hypotheses_by_id[hypothesis_id]
                if (
                    hypothesis.get("provenance_status") != "EMPIRICAL"
                    or hypothesis.get("execution_status") != "INVALIDATED"
                ):
                    errors.append(
                        f"{relative(path)}: adverse hypothesis lacks an "
                        "EMPIRICAL INVALIDATED execution state: "
                        f"{hypothesis_id}"
                    )
        if (
            doc.get("research_status") == "ACTIVE_RESEARCH"
            and not decision_allows_mechanism_transition(
                doc.get("decision_ref"),
                "CONTINUE_SCOPED_MECHANISM_RESEARCH",
                doc,
                path,
            )
        ):
            errors.append(
                f"{relative(path)}: ACTIVE_RESEARCH mechanism has no matching "
                "exact content-bound user decision"
            )
        formal_action = {
            "REBASE_REQUIRED": "REBASE_SCOPED_MECHANISM",
            "VALIDATED_SCOPED": "VALIDATE_SCOPED_MECHANISM",
            "REFUTED_SCOPED": "REFUTE_SCOPED_MECHANISM",
            "SUPERSEDED": "SUPERSEDE_SCOPED_MECHANISM",
        }.get(str(doc.get("research_status")))
        if formal_action and not decision_allows_mechanism_transition(
            doc.get("decision_ref"),
            formal_action,
            doc,
            path,
        ):
            errors.append(
                f"{relative(path)}: {doc.get('research_status')} mechanism "
                f"requires an exact content-bound user decision action "
                f"{formal_action}"
            )
    return errors


def containing_project(path: Path) -> Optional[Path]:
    for parent in path.parents:
        if (parent / "problem").is_dir() and (parent / "lines").is_dir():
            return parent
    return None


def expected_promoted_document(
    source: Mapping[str, Any],
    target_kind: str,
    decision_id: str,
    target_path: Path,
) -> Dict[str, Any]:
    """Deterministically derive the only canonical target a receipt may name."""
    promoted = copy.deepcopy(dict(source))
    if target_kind == "problem":
        promoted["status"] = "ACTIVE"
        promoted["companion_markdown"] = relative(
            target_path.with_suffix(".md")
        )
    elif target_kind == "scenario":
        promoted["status"] = "ACTIVE"
        promoted["activation"]["requires_user_approval"] = True
        promoted["activation"]["approval_decision_id"] = decision_id
    elif target_kind == "claim":
        promoted["status"] = "STABLE"
    else:
        raise ResearchError(f"unknown promotion target kind: {target_kind}")
    return promoted


def render_problem_active_companion(
    source: Mapping[str, Any],
    candidate_path: Path,
    decision_id: str,
) -> str:
    """Derive the ACTIVE explanation exactly from the frozen candidate text."""
    companion_locator = source.get("companion_markdown")
    if not isinstance(companion_locator, str):
        raise ResearchError(
            f"{relative(candidate_path)}: problem candidate has no companion"
        )
    source_companion = resolve_root_path(companion_locator)
    text = source_companion.read_text(encoding="utf-8")
    problem_id = str(source.get("id", ""))
    version = str(source.get("version", ""))
    bundle_locator = source.get("activation_bundle_ref")
    bundle_line = (
        f"\n激活材料闭包：`{bundle_locator}`。"
        if isinstance(bundle_locator, str)
        else ""
    )
    return (
        f"# Problem {version}：ACTIVE 快照\n\n"
        f"Contract：`{problem_id} / {version}`\n\n"
        f"状态：`ACTIVE`。由用户决定 `{decision_id}` 从候选快照 "
        f"`{relative(candidate_path)}` 激活。{bundle_line}\n\n"
        "下面保留用户确认时的候选说明原文。原文中的 `CANDIDATE`、"
        "“待激活”或同类表述只记录激活前状态；当前权威状态以上述 "
        "`ACTIVE` 记录和 promotion receipt 为准。\n\n"
        "<!-- activated-candidate-source:start -->\n"
        f"{text.rstrip()}\n"
        "<!-- activated-candidate-source:end -->\n"
    )


def check_exact_promotion_receipt(
    path: Path,
    document: Mapping[str, Any],
    target_kind: str,
) -> List[str]:
    project = containing_project(path)
    if project is None:
        return [f"{relative(path)}: cannot locate containing research project"]
    receipts = project / "promotions"
    action = {
        "problem": "ACTIVATE_PROBLEM",
        "claim": "PROMOTE_STABLE_CLAIM",
        "scenario": "ACTIVATE_REAL_SCENARIO"
        if document.get("scenario_class") == "REAL"
        else "ACTIVATE_SCENARIO",
    }[target_kind]
    failures: List[str] = []
    receipt_paths = sorted(receipts.glob("*.json")) if receipts.exists() else []
    for receipt_path in receipt_paths:
        try:
            receipt = load_json(receipt_path)
        except ResearchError as exc:
            failures.append(str(exc))
            continue
        if (
            receipt.get("target_kind") != target_kind
            or receipt.get("target_id") != document.get("id")
            or receipt.get("target_version") != document.get("version")
            or receipt.get("target") != relative(path)
            or receipt.get("target_sha256") != sha256_file(path)
        ):
            continue
        source_locator = receipt.get("source_candidate")
        if not isinstance(source_locator, str):
            continue
        source_path = resolve_root_path(source_locator)
        if (
            not source_path.is_file()
            or receipt.get("source_sha256") != sha256_file(source_path)
        ):
            continue
        source = load_json(source_path)
        if (
            target_kind == "problem"
            and source.get("schema_version") == "2.0"
        ):
            bundle_locator = source.get("activation_bundle_ref")
            if not isinstance(bundle_locator, str):
                failures.append(
                    f"{relative(receipt_path)}: source candidate has no "
                    "activation bundle"
                )
                continue
            bundle_path = resolve_root_path(bundle_locator)
            if (
                not bundle_path.is_file()
                or receipt.get("activation_bundle_path")
                != relative(bundle_path)
                or receipt.get("activation_bundle_sha256")
                != sha256_file(bundle_path)
            ):
                failures.append(
                    f"{relative(receipt_path)}: problem receipt does not bind "
                    "the current activation bundle path and SHA-256"
                )
                continue
        if target_kind == "problem":
            target_companion_locator = document.get("companion_markdown")
            if not isinstance(target_companion_locator, str):
                failures.append(
                    f"{relative(receipt_path)}: ACTIVE problem has no "
                    "companion reference"
                )
                continue
            target_companion = resolve_root_path(target_companion_locator)
            if (
                not target_companion.is_file()
                or receipt.get("target_companion")
                != relative(target_companion)
                or receipt.get("target_companion_sha256")
                != sha256_file(target_companion)
            ):
                failures.append(
                    f"{relative(receipt_path)}: problem receipt does not bind "
                    "the ACTIVE companion path and SHA-256"
                )
                continue
            try:
                expected_companion = render_problem_active_companion(
                    source,
                    source_path,
                    str(receipt.get("decision_id")),
                )
            except ResearchError as exc:
                failures.append(str(exc))
                continue
            if target_companion.read_text(
                encoding="utf-8"
            ) != expected_companion:
                failures.append(
                    f"{relative(receipt_path)}: ACTIVE companion is not the "
                    "deterministic projection of its candidate"
                )
                continue
        if decision_allows_promotion(
            receipt.get("decision_id"),
            action,
            source,
            source_path,
        ):
            expected = expected_promoted_document(
                source,
                target_kind,
                str(receipt.get("decision_id")),
                path,
            )
            if canonical_bytes(expected) == canonical_bytes(document):
                return []
            failures.append(
                f"{relative(receipt_path)}: target is not the deterministic "
                "promotion projection of its approved source"
            )
    suffix = f"; receipt errors={failures}" if failures else ""
    return [
        f"{relative(path)}: {document.get('status')} {target_kind} has no "
        f"exact source/target-hash user promotion receipt{suffix}"
    ]


def check_claim_semantics(path: Path, doc: Mapping[str, Any]) -> List[str]:
    if doc.get("status") == "STABLE":
        return check_exact_promotion_receipt(path, doc, "claim")
    return []


def check_candidate_packets(project: Path) -> List[str]:
    errors: List[str] = []
    candidates = project / "candidates"
    if not candidates.exists():
        return errors
    reserved_directories = {"interrupted-finalizations"}
    for packet in sorted(
        path
        for path in candidates.iterdir()
        if (
            path.is_dir()
            and not path.name.startswith(".")
            and path.name not in reserved_directories
        )
    ):
        manifest_path = packet / "finalization-manifest.json"
        if not manifest_path.is_file():
            errors.append(f"{relative(packet)}: candidate packet has no finalization manifest")
            continue
        manifest = load_json(manifest_path)
        if manifest.get("status") != "CANDIDATE":
            errors.append(f"{relative(manifest_path)}: finalized packet must remain CANDIDATE")
        hashes = manifest.get("result_hashes")
        if not isinstance(hashes, dict) or not hashes:
            errors.append(f"{relative(manifest_path)}: missing result_hashes")
            continue
        for name, expected in hashes.items():
            target = packet / name
            if not target.is_file():
                errors.append(f"{relative(manifest_path)}: missing finalized artifact {name}")
                continue
            if sha256_file(target) != expected:
                errors.append(f"{relative(manifest_path)}: hash mismatch for {name}")
                continue
            if name.endswith(".json") and name.startswith("LINE-"):
                result = load_json(target)
                errors.extend(validate_schema(result, target))
                if result.get("line_id") != name[:-5]:
                    errors.append(f"{relative(target)}: filename and line_id differ")
        plan_snapshot_path = packet / "plan-snapshot.json"
        if plan_snapshot_path.is_file():
            try:
                plan_snapshot = load_json(plan_snapshot_path)
            except ResearchError as exc:
                errors.append(f"{relative(packet)}: {exc}")
                continue
            if plan_snapshot.get("schema_version") == "2.0":
                try:
                    verify_candidate_packet(packet)
                except ResearchError as exc:
                    errors.append(
                        f"{relative(packet)}: deep candidate verification "
                        f"failed: {exc}"
                    )
    return errors


def validate_project(project: Path, strict: bool = False) -> List[str]:
    errors: List[str] = []
    problems = sorted((project / "problem").glob("*.json"))
    activation_bundles = (
        sorted((project / "problem" / "activation").glob("*.json"))
        if (project / "problem" / "activation").exists()
        else []
    )
    scenarios = sorted((project / "scenarios").glob("*.json"))
    lines = sorted((project / "lines").glob("*.json"))
    profiles = (
        sorted((project / "mechanisms").glob("*.json"))
        if (project / "mechanisms").exists()
        else []
    )
    claims = sorted((project / "claims").rglob("*.json")) if (project / "claims").exists() else []

    if not problems:
        errors.append(f"{relative(project)}: no problem contracts")
    if not scenarios:
        errors.append(f"{relative(project)}: no scenario contracts")
    if not lines:
        errors.append(f"{relative(project)}: no line contracts")

    for path in [*problems, *scenarios, *lines, *profiles, *claims]:
        doc = load_json(path)
        errors.extend(validate_schema(doc, path))
        errors.extend(check_companion(doc, path))
        if doc.get("kind") == "ClaimCandidate":
            errors.extend(check_claim_semantics(path, doc))
        if (
            doc.get("kind") == "ScenarioContract"
            and doc.get("status") == "ACTIVE"
        ):
            errors.extend(
                check_exact_promotion_receipt(path, doc, "scenario")
            )
        if doc.get("kind") == "ProblemContract":
            errors.extend(check_problem_lineage(project, path, doc))
            errors.extend(check_problem_historical_inheritance(project, path, doc))
            errors.extend(verify_problem_activation_bundle(doc, path))
            if doc.get("status") == "ACTIVE":
                errors.extend(
                    check_exact_promotion_receipt(path, doc, "problem")
                )
    for path in activation_bundles:
        bundle = load_json(path)
        errors.extend(validate_schema(bundle, path))

    errors.extend(check_problem_scenario_line_semantics(project, problems, scenarios, lines))
    errors.extend(check_mechanism_semantics(project, problems, lines, profiles))
    errors.extend(check_candidate_packets(project))

    try:
        state = read_state()
        for key in (
            "current_project",
            "seed_problem",
            "candidate_problem",
            "history_alignment",
            "validated_scenario",
            "canonical_source",
            "mechanism_profiles",
        ):
            locator = state.get(key)
            if key == "mechanism_profiles" and isinstance(locator, list):
                for profile_locator in locator:
                    if not resolve_root_path(profile_locator).exists():
                        errors.append(
                            f"NOW state mechanism_profiles points to missing path: "
                            f"{profile_locator}"
                        )
            elif locator and not resolve_root_path(locator).exists():
                errors.append(f"NOW state {key} points to missing path: {locator}")
        current_problem_locator = (
            state.get("candidate_problem") or state.get("active_problem")
        )
        if isinstance(current_problem_locator, str):
            current_problem_path = resolve_root_path(
                current_problem_locator
            )
            if current_problem_path.is_file():
                current_problem = load_json(current_problem_path)
                expected_alignment = current_problem.get(
                    "historical_inheritance_ref"
                )
                if (
                    isinstance(expected_alignment, str)
                    and state.get("history_alignment") != expected_alignment
                ):
                    errors.append(
                        "NOW history_alignment does not match the current "
                        f"problem's historical_inheritance_ref: "
                        f"{expected_alignment}"
                    )
        for preserved in state.get("preserved_problem_versions", []):
            if not isinstance(preserved, Mapping):
                errors.append("NOW preserved_problem_versions entry has no path")
                continue
            artifacts = preserved.get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                artifacts = [
                    {
                        "path": preserved.get("path"),
                        "sha256": preserved.get("sha256"),
                    }
                ]
            for artifact in artifacts:
                locator = (
                    artifact.get("path")
                    if isinstance(artifact, Mapping)
                    else None
                )
                expected_hash = (
                    artifact.get("sha256")
                    if isinstance(artifact, Mapping)
                    else None
                )
                if not isinstance(locator, str):
                    errors.append(
                        "NOW preserved problem artifact has no path"
                    )
                    continue
                preserved_path = resolve_root_path(locator)
                if not preserved_path.is_file():
                    errors.append(
                        "NOW preserved problem points to missing path: "
                        f"{locator}"
                    )
                elif expected_hash != sha256_file(preserved_path):
                    errors.append(
                        f"NOW preserved problem hash differs for {locator}"
                    )
        active_problem = state.get("active_problem")
        active_doc: Dict[str, Any] = {}
        if active_problem:
            active_doc = load_json(resolve_root_path(active_problem))
            if active_doc.get("status") != "ACTIVE":
                errors.append("NOW active_problem does not point to an ACTIVE problem")
        line_by_id = {
            load_json(line_path).get("id"): load_json(line_path)
            for line_path in lines
        }
        listed_line_ids: set[str] = set()
        for problem_key, group in state.get("lines_by_problem", {}).items():
            if not isinstance(group, Mapping) or "@" not in problem_key:
                errors.append(
                    f"NOW lines_by_problem has invalid group: {problem_key}"
                )
                continue
            problem_id, problem_version = problem_key.rsplit("@", 1)
            for line_id in group.get("lines", []):
                if line_id in listed_line_ids:
                    errors.append(
                        f"NOW lines_by_problem repeats line id: {line_id}"
                    )
                    continue
                listed_line_ids.add(line_id)
                line_doc = line_by_id.get(line_id)
                if not line_doc:
                    errors.append(
                        f"NOW lines_by_problem names unknown line: {line_id}"
                    )
                    continue
                ref = line_doc.get("problem_ref", {})
                if (ref.get("id"), ref.get("version")) != (
                    problem_id,
                    problem_version,
                ):
                    errors.append(
                        f"NOW lines_by_problem misbinds {line_id} to "
                        f"{problem_key}"
                    )
                if (
                    group.get("status") == "DRAFT"
                    and line_doc.get("status") not in {"DRAFT", "PAUSED"}
                ):
                    errors.append(
                        f"NOW DRAFT group contains non-draft line: {line_id}"
                    )
        unlisted_lines = sorted(set(line_by_id) - listed_line_ids)
        if unlisted_lines:
            errors.append(
                f"NOW lines_by_problem omits line contracts: {unlisted_lines}"
            )
        expected_active_lines = {
            line_id
            for line_id, line_doc in line_by_id.items()
            if active_doc
            and line_doc.get("status") == "ACTIVE"
            and line_doc.get("problem_ref", {}).get("id") == active_doc.get("id")
            and line_doc.get("problem_ref", {}).get("version")
            == active_doc.get("version")
        }
        state_active_lines = set(state.get("active_lines", []))
        if state_active_lines != expected_active_lines:
            errors.append(
                "NOW active_lines differs from ACTIVE lines for active_problem: "
                f"state={sorted(state_active_lines)} "
                f"expected={sorted(expected_active_lines)}"
            )
    except ResearchError as exc:
        errors.append(str(exc))

    try:
        decisions = read_decisions()
        if not decisions:
            errors.append("no structured user decisions found")
    except ResearchError as exc:
        errors.append(str(exc))

    if ARCHIVE_POINTER.is_file():
        pointer = load_json(ARCHIVE_POINTER)
        manifest = resolve_root_path(pointer["manifest_locator"])
        if manifest.is_file():
            actual = sha256_file(manifest)
            if actual != pointer.get("manifest_sha256"):
                errors.append("current archive manifest hash differs from source pointer")
        elif strict:
            errors.append("current archive manifest is unavailable")
    else:
        errors.append("archive source pointer is missing")
    return errors


def protected_paths(project: Path) -> List[Path]:
    paths = [
        *PROTECTED_PATHS,
        *sorted(CONTRACTS.glob("*.json")),
        *sorted((project / "problem").glob("*.json")),
        *sorted((project / "problem").glob("*.md")),
        *sorted((project / "scenarios").glob("*.json")),
        *sorted((project / "scenarios").glob("*.md")),
        *sorted((project / "lines").glob("*.json")),
        *sorted((project / "lines").glob("*.md")),
        *sorted((project / "mechanisms").glob("*.json")),
        *sorted((project / "mechanisms").glob("*.md")),
        *sorted((project / "promotions").glob("*.json")),
    ]
    stable_claims = project / "claims" / "stable"
    if stable_claims.exists():
        paths.extend(sorted(stable_claims.glob("*.json")))
    return paths


def hash_paths(paths: Iterable[Path]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for path in paths:
        values[relative(path)] = sha256_file(path) if path.is_file() else "MISSING"
    return values


def assert_runtime_budget(additional: int = 0) -> None:
    size = directory_size(RUNTIME)
    if size + additional > RUNTIME_LIMIT_BYTES:
        raise ResearchError(
            f"runtime budget exceeded: {size + additional} > {RUNTIME_LIMIT_BYTES}; "
            "nothing was deleted automatically"
        )


def source_snapshot(line: Mapping[str, Any]) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for locator in line["source_allowlist"]:
        source = resolve_root_path(locator)
        data = source.read_bytes()
        try:
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ResearchError(f"allowlisted source is not UTF-8 text: {locator}") from exc
        snapshots.append(
            {
                "locator": locator,
                "sha256": sha256_bytes(data),
                "content": content,
            }
        )
    return snapshots


def referenced_mechanism_profiles(
    line: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    target = line.get("research_target", {})
    if not isinstance(target, Mapping):
        return []
    locator = target.get("mechanism_ref")
    if not isinstance(locator, str):
        return []
    path = resolve_root_path(locator)
    if not path.is_file():
        raise ResearchError(f"mechanism profile missing: {locator}")
    profile = load_json(path)
    if profile.get("kind") != "MechanismProfile":
        raise ResearchError(f"not a MechanismProfile: {locator}")
    return [
        {
            "locator": locator,
            "sha256": sha256_file(path),
            "profile": profile,
        }
    ]


def make_batch_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"BATCH-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def select_problem(
    project: Path,
    state: Mapping[str, Any],
    value: Optional[str] = None,
) -> Tuple[Path, Dict[str, Any]]:
    if value:
        direct = resolve_root_path(value)
        if direct.is_file():
            path = direct
        else:
            candidates = [
                candidate
                for candidate in (project / "problem").glob("*.json")
                if (
                    load_json(candidate).get("version") == value
                    or load_json(candidate).get("id") == value
                )
            ]
            if len(candidates) != 1:
                raise ResearchError(f"cannot resolve problem: {value}")
            path = candidates[0]
    else:
        locator = state.get("active_problem")
        if not isinstance(locator, str) and state.get("candidate_problem"):
            raise ResearchError(
                "NOW has no ACTIVE problem and identifies a candidate; "
                "pass --problem explicitly to avoid silently running an older version"
            )
        locator = locator or state.get("seed_problem")
        if not isinstance(locator, str):
            raise ResearchError("NOW does not identify a seed or active problem")
        path = resolve_root_path(locator)
    if project not in path.parents:
        raise ResearchError("selected problem does not belong to selected project")
    return path, load_json(path)


def select_scenario(project: Path, value: Optional[str], state: Mapping[str, Any]) -> Tuple[Path, Dict[str, Any]]:
    if value:
        direct = resolve_root_path(value)
        if direct.is_file():
            path = direct
        else:
            candidates = [
                path
                for path in (project / "scenarios").glob("*.json")
                if load_json(path).get("id") == value
            ]
            active_candidates = [
                path
                for path in candidates
                if load_json(path).get("status") == "ACTIVE"
            ]
            if len(active_candidates) == 1:
                path = active_candidates[0]
            elif len(candidates) != 1:
                raise ResearchError(f"cannot resolve scenario: {value}")
            else:
                path = candidates[0]
    else:
        locator = state.get("active_mechanism_scenario") or state.get("validated_scenario")
        if not isinstance(locator, str):
            raise ResearchError("NOW does not identify a scenario")
        path = resolve_root_path(locator)
    if project not in path.parents:
        raise ResearchError("selected scenario does not belong to selected project")
    return path, load_json(path)


def select_active_lines(
    project: Path,
    problem: Mapping[str, Any],
    requested: Optional[Sequence[str]] = None,
) -> List[Tuple[Path, Dict[str, Any]]]:
    key = (problem.get("id"), problem.get("version"))
    available: List[Tuple[Path, Dict[str, Any]]] = []
    for path in sorted((project / "lines").glob("*.json")):
        line = load_json(path)
        ref = line.get("problem_ref", {})
        if (
            line.get("status") == "ACTIVE"
            and (ref.get("id"), ref.get("version")) == key
        ):
            available.append((path, line))

    if not requested:
        return available

    by_id = {line.get("id"): (path, line) for path, line in available}
    selected: List[Tuple[Path, Dict[str, Any]]] = []
    missing: List[str] = []
    for value in requested:
        if value in by_id:
            selected.append(by_id[value])
            continue
        direct = resolve_root_path(value)
        match = next((item for item in available if item[0] == direct), None)
        if match is None:
            missing.append(value)
        else:
            selected.append(match)
    if missing:
        raise ResearchError(
            "requested lines are not ACTIVE for selected problem "
            f"{problem.get('id')}@{problem.get('version')}: {missing}"
        )
    unique: Dict[str, Tuple[Path, Dict[str, Any]]] = {}
    for path, line in selected:
        unique[str(line.get("id"))] = (path, line)
    return list(unique.values())


def plan_batch(args: argparse.Namespace) -> int:
    project = project_path(args.project)
    errors = validate_project(project, strict=True)
    if errors:
        raise ResearchError("project validation failed:\n- " + "\n- ".join(errors))
    state = read_state()
    problem_path, problem = select_problem(
        project, state, getattr(args, "problem", None)
    )
    scenario_path, scenario = select_scenario(project, args.scenario, state)

    problem_ref = scenario.get("problem_ref", {})
    if (problem_ref.get("id"), problem_ref.get("version")) != (
        problem.get("id"),
        problem.get("version"),
    ):
        raise ResearchError("scenario and selected problem versions do not match")

    if scenario["study_mode"] == "PROBLEM_DEFINITION":
        if problem["status"] not in {"SEED", "CANDIDATE", "ACTIVE"}:
            raise ResearchError("problem-definition batch requires SEED, CANDIDATE, or ACTIVE problem")
        if scenario["status"] not in {"VALIDATED", "ACTIVE"}:
            raise ResearchError("problem-definition scenario must be VALIDATED or ACTIVE")
    else:
        if problem["status"] != "ACTIVE" or scenario["status"] != "ACTIVE":
            raise ResearchError("mechanism and reality batches require ACTIVE problem and scenario")

    if scenario["status"] == "ACTIVE":
        receipt_errors = check_exact_promotion_receipt(
            scenario_path,
            scenario,
            "scenario",
        )
        if receipt_errors:
            raise ResearchError("; ".join(receipt_errors))

    if args.mode not in {"mock", "codex"}:
        raise ResearchError(f"unsupported mode: {args.mode}")
    max_parallel = max(1, min(int(args.max_parallel), DEFAULT_MAX_PARALLEL))
    assert_runtime_budget(BATCH_LIMIT_BYTES)

    active_lines = select_active_lines(
        project, problem, getattr(args, "line", None)
    )
    if not active_lines:
        raise ResearchError(
            "no ACTIVE research lines match selected problem "
            f"{problem.get('id')}@{problem.get('version')}"
        )
    for _, line in active_lines:
        if problem.get("schema_version") == "2.0" and line.get(
            "schema_version"
        ) != "2.0":
            raise ResearchError(
                "ProblemContract 2.0 requires LineContract 2.0"
            )
        if scenario.get("study_mode") != "PROBLEM_DEFINITION" and line.get(
            "schema_version"
        ) != "2.0":
            raise ResearchError(
                "non-definition research requires LineContract 2.0"
            )
        if (
            scenario.get("study_mode") == "PROBLEM_DEFINITION"
            and line.get("schema_version") == "2.0"
            and line.get("research_target", {}).get("mechanism_ref")
            is not None
        ):
            raise ResearchError(
                "scoped mechanism research requires a mechanism or "
                "reality-test scenario"
            )

    batch_id = args.batch_id or make_batch_id()
    if not re.fullmatch(r"BATCH-[A-Z0-9-]+", batch_id):
        raise ResearchError("batch id must match BATCH-[A-Z0-9-]+")
    batch_dir = RUNTIME / batch_id
    if batch_dir.exists():
        raise ResearchError(f"batch already exists: {batch_id}")
    batch_dir.mkdir(parents=True)

    protected = hash_paths(protected_paths(project))
    plan: Dict[str, Any] = {
        "schema_version": "2.0",
        "batch_id": batch_id,
        "created_at": utc_now(),
        "status": "PLANNED",
        "mode": args.mode,
        "project": relative(project),
        "problem_path": relative(problem_path),
        "problem_sha256": sha256_file(problem_path),
        "scenario_path": relative(scenario_path),
        "scenario_sha256": sha256_file(scenario_path),
        "max_parallel": max_parallel,
        "batch_limit_bytes": BATCH_LIMIT_BYTES,
        "runtime_limit_bytes": RUNTIME_LIMIT_BYTES,
        "protected_hashes": protected,
        "runs": [],
    }
    disclosure_payloads: List[Dict[str, Any]] = []
    disclosed_sources: set[str] = set()

    for line_path, line in active_lines:
        run_id = f"{batch_id}-{line['id']}"
        run_dir = batch_dir / "runs" / line["id"]
        run_dir.mkdir(parents=True)
        sources = source_snapshot(line)
        mechanism_profiles = referenced_mechanism_profiles(line)
        input_components = {
            relative(problem_path): sha256_file(problem_path),
            relative(scenario_path): sha256_file(scenario_path),
            relative(line_path): sha256_file(line_path),
            **{
                item["locator"]: item["sha256"]
                for item in mechanism_profiles
            },
            **{item["locator"]: item["sha256"] for item in sources},
        }
        bundle = {
            "batch_id": batch_id,
            "run_id": run_id,
            "problem": problem,
            "scenario": scenario,
            "line": line,
            "research_focus": {
                "mechanism_ref": line.get("research_target", {}).get(
                    "mechanism_ref"
                ),
                "hypothesis_ids": line.get("research_target", {}).get(
                    "hypothesis_ids", []
                ),
                "tested_claim_ids": line.get("research_target", {}).get(
                    "scoped_claim_ids", []
                ),
            },
            "mechanism_profiles": mechanism_profiles,
            "input_components": input_components,
            "sources": sources,
        }
        input_hash = run_input_hash(bundle)
        bundle["input_hash"] = input_hash
        write_json(run_dir / "input.json", bundle)
        input_payload_sha256 = sha256_file(run_dir / "input.json")
        disclosure_payloads.append(
            {
                "run_id": run_id,
                "payload": relative(run_dir / "input.json"),
                "sha256": input_payload_sha256,
                "size_bytes": (run_dir / "input.json").stat().st_size,
            }
        )
        disclosed_sources.update(line["source_allowlist"])
        (run_dir / "WORKER_POLICY.md").write_text(
            "# Bounded worker policy\n\n"
            "Use only input.json. Do not inspect parent directories or other runs. "
            "Do not start sub-agents, browse the network, contact people, execute effects, "
            "or modify any file. Separate observations, source statements, inferences, "
            "design proposals, and negative results. Return JSON only.\n",
            encoding="utf-8",
        )
        manifest = {
            "schema_version": "1.0",
            "kind": "RunManifest",
            "run_id": run_id,
            "batch_id": batch_id,
            "line_id": line["id"],
            "mode": args.mode,
            "status": "PLANNED",
            "problem_ref": f"{problem['id']}@{problem['version']}",
            "scenario_ref": f"{scenario['id']}@{scenario['version']}",
            "input_hash": input_hash,
            "input_payload_sha256": input_payload_sha256,
            "source_allowlist": line["source_allowlist"],
            "research_focus": bundle["research_focus"],
            "protected_hashes": protected,
            "runner": {
                "command": "mock" if args.mode == "mock" else "codex exec --sandbox read-only --ephemeral",
                "version": mock_or_command_version(args.mode),
            },
            "attempt": 0,
            "started_at": None,
            "finished_at": None,
            "exit_code": None,
            "result_sha256": None,
            "raw_result_sha256": None,
            "events_sha256": None,
            "completion_seal_sha256": None,
            "cost": {"elapsed_seconds": 0, "output_bytes": 0},
        }
        write_json(run_dir / "manifest.json", manifest)
        plan["runs"].append(
            {
                "run_id": run_id,
                "line_id": line["id"],
                "line_path": relative(line_path),
                "line_sha256": sha256_file(line_path),
                "run_dir": relative(run_dir),
                "input_components": input_components,
                "input_hash": input_hash,
                "input_payload_sha256": input_payload_sha256,
                "research_focus": bundle["research_focus"],
            }
        )
    plan["plan_fingerprint"] = compute_plan_fingerprint(plan)
    for run in plan["runs"]:
        manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
        manifest = load_json(manifest_path)
        manifest["plan_fingerprint"] = plan["plan_fingerprint"]
        write_json(manifest_path, manifest)
    if args.mode == "codex":
        disclosure_core = {
            "schema_version": "1.0",
            "kind": "ExternalDisclosureManifest",
            "batch_id": batch_id,
            "destination": "OpenAI Codex",
            "classification": "NON_PUBLIC_RESEARCH",
            "purpose": (
                f"{len(plan['runs'])} isolated research line run(s) for "
                f"{problem['id']}@{problem['version']}"
            ),
            "payloads": disclosure_payloads,
            "unique_source_locators": sorted(disclosed_sources),
            "total_payload_bytes": sum(item["size_bytes"] for item in disclosure_payloads),
            "does_not_include": [
                "full immutable archive",
                "source_registry.csv",
                "full capability preservation matrix",
                "real participant data",
                "credentials",
                "other line results",
                "expected answer"
            ]
        }
        disclosure_sha = json_hash(disclosure_core)
        disclosure_manifest = {
            **disclosure_core,
            "disclosure_sha256": disclosure_sha,
            "plan_fingerprint": plan["plan_fingerprint"],
            "approval_decision_id": None,
        }
        write_json(batch_dir / "disclosure-manifest.json", disclosure_manifest)
        plan["external_disclosure"] = {
            "manifest": relative(batch_dir / "disclosure-manifest.json"),
            "disclosure_sha256": disclosure_sha,
            "approval_decision_id": None,
        }
    else:
        plan["external_disclosure"] = None
    write_json(batch_dir / "plan.json", plan)
    write_controller_seal(
        batch_dir / "plan-seal.json",
        plan_seal_document(plan),
    )
    print(f"[OK] planned {batch_id}: {len(plan['runs'])} isolated runs, mode={args.mode}, parallel={max_parallel}")
    print(relative(batch_dir / "plan.json"))
    if args.mode == "codex":
        print(
            "[BLOCKED] external transfer requires a structured user decision for "
            f"SEND_BATCH_TO_CODEX target={batch_id}@{plan['plan_fingerprint']}"
        )
        print(relative(batch_dir / "disclosure-manifest.json"))
    return 0


def mock_or_command_version(mode: str) -> str:
    if mode == "mock":
        return "researchctl-mock-v1"
    executable = shutil.which("codex")
    if not executable:
        return "codex-unavailable"
    try:
        proc = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (proc.stdout or proc.stderr).strip() or "unknown"
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


MOCK_CONTENT: Dict[str, Dict[str, str]] = {
    "LINE-01-DISCOVERY-BOUNDARY": {
        "observation": "v0 说有限边界，但尚未定义发现充分性与过度披露之间可观察的失败对。",
        "claim": "Problem v1 应把任务相关边界充分性作为待判别变量，而不是预设 NAC 为必要接口。",
        "negative": "当前档案不能证明 NAC 相较强自然语言查询具有普遍净增值。",
        "discriminator": "同一私有世界上比较静态卡片、自然语言 query 与预算化边界 Oracle 的漏配和披露成本。"
    },
    "LINE-02-RELATION-CONSTITUTION": {
        "observation": "v0 同时覆盖问题形成与关系运行，但二者可能有不同充分条件。",
        "claim": "Problem v1 应明确区分协调已有关系与构成新的关系事实。",
        "negative": "多轮修订本身不能证明发生了 relation constitution。",
        "discriminator": "要求参与者集合或目标因主体异议发生物质改变，并与预定义任务加审批比较。"
    },
    "LINE-03-POSSIBILITY-FORMATION": {
        "observation": "v0 提到条件创造，但没有把冻结前路径、operator 后路径和消融写入问题判据。",
        "claim": "Problem v1 应要求区分发现已有路径与因 operator 产生新路径。",
        "negative": "当前合成与档案证据不足以证明 PFE 是普遍核心引擎。",
        "discriminator": "冻结行动图，加入一个可定位 operator，再移除它并观察合格路径是否随之出现和消失。"
    },
    "LINE-04-CAPABILITY-REALIZATION": {
        "observation": "v0 容易把形成可能性与能力已兑现放在同一句中，缺少环境和权限版本。",
        "claim": "Problem v1 应把能力候选、probe 支持和目标域稳定兑现分层。",
        "negative": "语言自报与单次成功均不能支持长期 Capability Envelope。",
        "discriminator": "在未见留出任务和权限撤销后重复验证同一能力合同。"
    },
    "LINE-05-AUTHORITY-NORMS": {
        "observation": "v0 强调有限授权，但尚未明确同一 Entity 内多个 Authority Locus 冲突时的决定规则。",
        "claim": "Problem v1 应把 Entity 连续性与 Principal 原生认领严格分开。",
        "negative": "更强执行器不会自动提高授权安全或目标忠实。",
        "discriminator": "保持能力相同，只改变 Mandate Version，测试系统是否阻止目标改变和伪接受。"
    },
    "LINE-06-REALITY-EFFECT": {
        "observation": "v0 列出执行、采用和接受，但仍需明确各自权威 witness 和撤销条件。",
        "claim": "Problem v1 应把 Effect、Domain Adoption 与 Principal Acceptance 设为不可互相推出的观察。",
        "negative": "本问题定义批次产生的研究制品不是现实 Effect。",
        "discriminator": "分别构造执行成功但未采用、采用但未接受、接受后被 Defeater 重开的案例。"
    },
    "LINE-07-RUNTIME-EVOLUTION": {
        "observation": "v0 包含学习、退出和重开，但没有说明哪些改变应局部重开、哪些使整段关系失效。",
        "claim": "Problem v1 应把关系连续性定义为版本与责任谱系连续，而非所有事实不变。",
        "negative": "日志存在和进程存活不能证明关系长期有效。",
        "discriminator": "分别注入模型升级、授权撤销和证据失效，检验局部重开是否保留旧责任。"
    },
}


def mock_result(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    line = bundle["line"]
    content = MOCK_CONTENT.get(
        line["id"],
        {
            "observation": (
                f"{line['title']} 的 mock 只验证有界返回、版本绑定和来源隔离，"
                "不提供机制有效性证据。"
            ),
            "claim": (
                f"{line['title']} 的结果必须限制到本线声明的 scoped claims。"
            ),
            "negative": "mock 运行不能支持现实有效性、机制优越性或稳定主张。",
            "discriminator": (
                "用真实冻结输入和公平基线逐项检验 scoped claim，"
                "并列出未受影响主张。"
            ),
        },
    )
    native_source = next(
        (
            item["locator"]
            for item in bundle["sources"]
            if "/native_lines/" in item["locator"]
        ),
        bundle["sources"][0]["locator"],
    )
    result = {
        "schema_version": "1.0",
        "kind": "ResearchResult",
        "run_id": bundle["run_id"],
        "batch_id": bundle["batch_id"],
        "line_id": line["id"],
        "status": "COMPLETED",
        "question_version": bundle["problem"]["version"],
        "scenario_version": bundle["scenario"]["version"],
        "input_hash": bundle["input_hash"],
        "direct_observations": [content["observation"]],
        "source_statements": [
            {
                "statement": f"原生能力档案将{line['title']}作为独立问题线保存。",
                "source_locator": native_source,
                "source_range": "1-20"
            }
        ],
        "inferences": [content["claim"]],
        "design_proposals": [
            "保留本线的失败判别和反向结果，等待与其他线并列比较后再决定是否合并。"
        ],
        "negative_results": [content["negative"]],
        "alternative_explanations": [
            "强中心研究者可能在不拆分研究线的情况下得到相同区分，必须作为直接综合基线比较。"
        ],
        "evidence_refs": line["capability_ids"],
        "applicability": (
            f"仅适用于 {bundle['problem']['id']}@"
            f"{bundle['problem']['version']} 的本地 mock 批次。"
        ),
        "cannot_support": bundle["scenario"]["cannot_support"],
        "candidate_claims": [content["claim"]],
        "new_discriminators": [content["discriminator"]],
        "cost": {"elapsed_seconds": 0, "output_bytes": 0}
    }
    if line.get("schema_version") == "2.0":
        scoped_claim_ids = bundle.get("research_focus", {}).get(
            "tested_claim_ids",
            line.get("research_target", {}).get("scoped_claim_ids", []),
        )
        result["schema_version"] = "2.0"
        result["hypothesis_ids"] = list(
            bundle.get("research_focus", {}).get(
                "hypothesis_ids",
                line.get("research_target", {}).get("hypothesis_ids", []),
            )
        )
        result["hypothesis_outcomes"] = [
            {
                "hypothesis_id": hypothesis_id,
                "outcome": "INCONCLUSIVE",
                "rationale": (
                    "Mock execution verifies governance only and cannot decide "
                    "the bounded research hypothesis."
                ),
                "evidence_refs": [],
            }
            for hypothesis_id in result["hypothesis_ids"]
        ]
        result["tested_claim_ids"] = list(scoped_claim_ids)
        result["scoped_claim_updates"] = []
        result["unaffected_claim_ids"] = list(scoped_claim_ids)
    return result


def build_codex_prompt(bundle: Mapping[str, Any], input_json_text: str) -> str:
    scope_instruction = ""
    if bundle["line"].get("schema_version") == "2.0":
        scope_instruction = (
            "Only propose status changes for research_focus.tested_claim_ids. "
            "Treat research_focus.hypothesis_ids as the exact experiment scope. "
            "Return exactly one hypothesis_outcomes entry for every frozen "
            "hypothesis id. FAILED or REFUSED results must use NOT_RUN and "
            "cannot support or refute a scoped claim. "
            "List every claim not changed in unaffected_claim_ids. "
            "Do not put UNCHANGED claims in scoped_claim_updates. "
            "A failure that only targets research_target.non_claims or the "
            "profile non_responsibilities cannot change the mechanism. "
        )
    return (
        "You are one isolated research line. Use only the source text embedded in input.json. "
        "The exact authorized input.json bytes are included below; do not inspect the filesystem, "
        "call tools, browse, spawn sub-agents, or infer user approval. "
        f"Examine {bundle['problem']['id']}@{bundle['problem']['version']} "
        "from this line's declared scope and strongest alternative. "
        "Return a ResearchResult JSON matching the supplied schema. "
        f"{scope_instruction}"
        "Every source_statement.source_locator must exactly match one source_allowlist entry. "
        "Preserve negative and inconclusive results. Do not claim real Effect, Adoption, Acceptance, "
        "human authorization, or general validity.\n"
        "<AUTHORIZED_INPUT_JSON>\n"
        f"{input_json_text}"
        "</AUTHORIZED_INPUT_JSON>\n"
    )


def validate_result_semantics(
    result: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> List[str]:
    errors = validate_schema(result, Path(str(bundle["run_id"]) + "/result.json"))
    expected = {
        "run_id": bundle["run_id"],
        "batch_id": bundle["batch_id"],
        "line_id": bundle["line"]["id"],
        "question_version": bundle["problem"]["version"],
        "scenario_version": bundle["scenario"]["version"],
        "input_hash": bundle["input_hash"],
    }
    for key, value in expected.items():
        if result.get(key) != value:
            errors.append(f"result {key} mismatch: expected {value!r}, got {result.get(key)!r}")
    allowed = set(bundle["line"]["source_allowlist"])
    for statement in result.get("source_statements", []):
        if statement.get("source_locator") not in allowed:
            errors.append(f"result cites non-allowlisted source: {statement.get('source_locator')}")
    line = bundle["line"]
    if line.get("schema_version") == "2.0":
        if result.get("schema_version") != "2.0":
            errors.append("LineContract 2.0 requires ResearchResult 2.0")
        expected_hypotheses = list(
            bundle.get("research_focus", {}).get(
                "hypothesis_ids",
                line.get("research_target", {}).get("hypothesis_ids", []),
            )
        )
        expected_tested_claims = list(
            bundle.get("research_focus", {}).get(
                "tested_claim_ids",
                line.get("research_target", {}).get("scoped_claim_ids", []),
            )
        )
        if result.get("hypothesis_ids") != expected_hypotheses:
            errors.append("result hypothesis_ids differ from frozen run focus")
        outcome_items = result.get("hypothesis_outcomes", [])
        outcome_ids = [item.get("hypothesis_id") for item in outcome_items]
        if len(outcome_ids) != len(set(outcome_ids)):
            errors.append("result contains duplicate hypothesis outcomes")
        if set(outcome_ids) != set(expected_hypotheses):
            errors.append(
                "result hypothesis outcomes do not exactly cover frozen hypotheses"
            )
        for item in outcome_items:
            evidence_refs = item.get("evidence_refs", [])
            unknown_evidence = sorted(set(evidence_refs) - allowed)
            if unknown_evidence:
                errors.append(
                    "hypothesis outcome cites evidence outside source allowlist: "
                    f"{unknown_evidence}"
                )
            if (
                item.get("outcome") in {"COMPLETED", "INVALIDATED"}
                and not evidence_refs
            ):
                errors.append(
                    "completed or invalidated hypothesis outcome requires "
                    f"allowlisted evidence: {item.get('hypothesis_id')}"
                )
        if result.get("status") in {"FAILED", "REFUSED"} and any(
            item.get("outcome") != "NOT_RUN" for item in outcome_items
        ):
            errors.append(
                "FAILED or REFUSED result cannot complete, invalidate, or "
                "assess a hypothesis"
            )
        if result.get("status") == "INCONCLUSIVE" and any(
            item.get("outcome") not in {"INCONCLUSIVE", "NOT_RUN"}
            for item in outcome_items
        ):
            errors.append(
                "INCONCLUSIVE result cannot complete or invalidate a hypothesis"
            )
        if result.get("tested_claim_ids") != expected_tested_claims:
            errors.append("result tested_claim_ids differ from frozen run focus")
        allowed_claims = set(
            bundle.get("research_focus", {}).get(
                "tested_claim_ids",
                line.get("research_target", {}).get("scoped_claim_ids", []),
            )
        )
        update_items = result.get("scoped_claim_updates", [])
        update_ids = [item.get("claim_id") for item in update_items]
        unaffected_ids = result.get("unaffected_claim_ids", [])
        updated_claims = set(update_ids)
        unaffected_claims = set(unaffected_ids)
        if len(update_ids) != len(updated_claims):
            errors.append("result contains duplicate scoped claim updates")
        if len(unaffected_ids) != len(unaffected_claims):
            errors.append("result contains duplicate unaffected claim ids")
        unchanged_updates = sorted(
            item.get("claim_id")
            for item in update_items
            if item.get("proposed_status") == "UNCHANGED"
        )
        if unchanged_updates:
            errors.append(
                "result must list unchanged claims only in unaffected_claim_ids: "
                f"{unchanged_updates}"
            )
        unknown_updates = sorted(updated_claims - allowed_claims)
        unknown_unaffected = sorted(unaffected_claims - allowed_claims)
        if unknown_updates:
            errors.append(
                f"result updates claims outside line scope: {unknown_updates}"
            )
        if unknown_unaffected:
            errors.append(
                f"result names unaffected claims outside line scope: "
                f"{unknown_unaffected}"
            )
        contradictory = sorted(updated_claims & unaffected_claims)
        if contradictory:
            errors.append(
                f"result both changes and marks claims unaffected: {contradictory}"
            )
        missing_classification = sorted(
            allowed_claims - updated_claims - unaffected_claims
        )
        if missing_classification:
            errors.append(
                "result does not classify every scoped claim: "
                f"{missing_classification}"
            )
        for item in update_items:
            evidence_refs = item.get("evidence_refs", [])
            unknown_evidence = sorted(set(evidence_refs) - allowed)
            if unknown_evidence:
                errors.append(
                    "scoped claim update cites evidence outside source allowlist: "
                    f"{unknown_evidence}"
                )
            if (
                item.get("proposed_status")
                in {
                    "SUPPORTED_CANDIDATE",
                    "NARROWED",
                    "REFUTED_CANDIDATE",
                    "REBASE_REQUIRED_CANDIDATE",
                }
                and not evidence_refs
            ):
                errors.append(
                    "substantive scoped claim update requires allowlisted "
                    f"evidence: {item.get('claim_id')}"
                )
        if result.get("status") != "COMPLETED":
            invalid_updates = sorted(
                item.get("claim_id")
                for item in update_items
                if item.get("proposed_status")
                in {
                    "SUPPORTED_CANDIDATE",
                    "NARROWED",
                    "REFUTED_CANDIDATE",
                    "REBASE_REQUIRED_CANDIDATE",
                }
            )
            if invalid_updates:
                errors.append(
                    f"{result.get('status')} result cannot make substantive "
                    f"scoped claim updates: {invalid_updates}"
                )
    return errors


def bind_result_envelope(
    result: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> Dict[str, Any]:
    """Bind runner-owned identity fields without altering research content."""
    bound = dict(result)
    bound.update(
        {
            "run_id": bundle["run_id"],
            "batch_id": bundle["batch_id"],
            "line_id": bundle["line"]["id"],
            "question_version": bundle["problem"]["version"],
            "scenario_version": bundle["scenario"]["version"],
            "input_hash": bundle["input_hash"],
            "hypothesis_ids": bundle.get("research_focus", {}).get(
                "hypothesis_ids",
                bundle["line"].get("research_target", {}).get(
                    "hypothesis_ids", []
                ),
            ),
            "tested_claim_ids": bundle.get("research_focus", {}).get(
                "tested_claim_ids",
                bundle["line"].get("research_target", {}).get(
                    "scoped_claim_ids", []
                ),
            ),
        }
    )
    return bound


def verify_completed_run_artifacts(
    run_dir: Path,
    manifest: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> Dict[str, Any]:
    """Bind a completed result to the original model/mock output and events."""
    result_path = run_dir / "result.json"
    raw_path = run_dir / "result.raw.json"
    events_path = run_dir / "events.jsonl"
    completion_seal_path = run_dir / "completion-seal.json"
    if not all(
        path.is_file()
        for path in (
            result_path,
            raw_path,
            events_path,
            completion_seal_path,
        )
    ):
        raise ResearchError(
            "completed run is missing result, raw output, events, or "
            "controller seal"
        )
    expected_hashes = {
        "result_sha256": sha256_file(result_path),
        "raw_result_sha256": sha256_file(raw_path),
        "events_sha256": sha256_file(events_path),
    }
    if any(
        manifest.get(field) != value
        for field, value in expected_hashes.items()
    ):
        raise ResearchError(
            "completed run artifact hashes differ from its manifest"
        )
    completion_seal = load_controller_seal(completion_seal_path)
    if (
        manifest.get("completion_seal_sha256")
        != sha256_file(completion_seal_path)
        or completion_seal.get("kind")
        != "RunCompletionControllerSeal"
        or completion_seal.get("run_id") != bundle.get("run_id")
        or completion_seal.get("batch_id") != bundle.get("batch_id")
        or completion_seal.get("plan_fingerprint")
        != manifest.get("plan_fingerprint")
        or completion_seal.get("input_hash") != bundle.get("input_hash")
        or completion_seal.get("input_payload_sha256")
        != sha256_file(run_dir / "input.json")
        or any(
            completion_seal.get(field) != value
            for field, value in expected_hashes.items()
        )
    ):
        raise ResearchError(
            "completed run differs from its read-only controller seal"
        )
    result = load_json(result_path)
    raw_result = load_json(raw_path)
    rebound = bind_result_envelope(raw_result, bundle)
    rebound_content = copy.deepcopy(rebound)
    result_content = copy.deepcopy(result)
    rebound_content.pop("cost", None)
    result_content.pop("cost", None)
    if canonical_bytes(rebound_content) != canonical_bytes(result_content):
        raise ResearchError(
            "completed result research content differs from original raw output"
        )
    result_errors = validate_result_semantics(result, bundle)
    if result_errors:
        raise ResearchError("; ".join(result_errors))
    return result


INFRA_FAILURE_MARKERS = (
    "invalid_json_schema",
    "failed to initialize in-process app-server",
    "attempt to write a readonly database",
    "result run_id mismatch",
    "result batch_id mismatch",
    "result line_id mismatch",
    "result question_version mismatch",
    "result scenario_version mismatch",
    "result input_hash mismatch",
)


def is_infrastructure_failure(error_text: str) -> bool:
    return any(marker in error_text for marker in INFRA_FAILURE_MARKERS)


ACCESS_BLOCK_MARKERS = (
    "source text could not be accessed",
    "source text was unavailable",
    "source text is unavailable",
    "permitted evidence source was unavailable",
    "no authorized source text was available",
    "required file contents are supplied in-band",
    "provide the contents of worker_policy.md and input.json",
    "provide the complete contents of worker_policy.md and input.json",
)


def result_is_access_blocked(result: Mapping[str, Any]) -> bool:
    if result.get("source_statements") or result.get("candidate_claims"):
        return False
    text = json.dumps(result, ensure_ascii=False).lower()
    return any(marker in text for marker in ACCESS_BLOCK_MARKERS)


def preserve_attempt_artifacts(run_dir: Path, attempt: int) -> None:
    for source_name, target_name in (
        ("result.raw.json", f"attempt-{attempt}-result.raw.json"),
        ("events.jsonl", f"attempt-{attempt}-events.jsonl"),
    ):
        source = run_dir / source_name
        target = run_dir / target_name
        if source.is_file() and not target.exists():
            shutil.copy2(source, target)


def recover_interrupted_run(
    run_dir: Path,
    manifest: MutableMapping[str, Any],
) -> None:
    """Preserve a crash residue and retry the same attempt under the lock."""
    attempt = int(manifest.get("attempt", 0))
    history = (
        run_dir
        / "interruption-history"
        / (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + f"-attempt-{attempt}-{uuid.uuid4().hex[:6]}"
        )
    )
    history.mkdir(parents=True, exist_ok=False)
    for name in (
        "result.json",
        "result.raw.json",
        "events.jsonl",
        "completion-seal.json",
    ):
        source = run_dir / name
        if source.is_file():
            shutil.move(str(source), history / name)
    interruption = {
        "schema_version": "1.0",
        "kind": "InterruptedRunReceipt",
        "run_id": manifest.get("run_id"),
        "interrupted_attempt": attempt,
        "prior_started_at": manifest.get("started_at"),
        "recovered_at": utc_now(),
        "retry_consumed": False,
    }
    write_json(history / "interruption.json", interruption)
    manifest["status"] = "PLANNED"
    manifest["attempt"] = max(0, attempt - 1)
    manifest["started_at"] = None
    manifest["finished_at"] = None
    manifest["exit_code"] = None
    manifest["result_sha256"] = None
    manifest["raw_result_sha256"] = None
    manifest["events_sha256"] = None
    manifest["completion_seal_sha256"] = None
    manifest["cost"] = {"elapsed_seconds": 0, "output_bytes": 0}


def run_codex(run_dir: Path, bundle: Mapping[str, Any], timeout: int) -> Tuple[Dict[str, Any], int, str]:
    executable = shutil.which("codex")
    if not executable:
        raise ResearchError("codex executable is unavailable")
    output_path = run_dir / "result.raw.json"
    schema_path = CONTRACTS / "research-result.schema.json"
    command = [
        executable,
        "exec",
        "--sandbox",
        "read-only",
        "--ephemeral",
        "--skip-git-repo-check",
        "--json",
        "--output-schema",
        str(schema_path),
        "-o",
        str(output_path),
        "-C",
        str(run_dir),
        "-",
    ]
    try:
        proc = subprocess.run(
            command,
            input=build_codex_prompt(
                bundle,
                (run_dir / "input.json").read_text(encoding="utf-8"),
            ),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        (run_dir / "events.jsonl").write_text(
            (exc.stdout or "") + (exc.stderr or ""),
            encoding="utf-8",
        )
        raise ResearchError(f"codex run timed out after {timeout}s") from exc
    events = (proc.stdout or "") + (proc.stderr or "")
    (run_dir / "events.jsonl").write_text(events, encoding="utf-8")
    if proc.returncode != 0:
        diagnostic = events[-4000:]
        raise ResearchError(f"codex exited {proc.returncode}: {diagnostic}")
    result = load_json(output_path)
    return result, proc.returncode, events


def current_components(run: Mapping[str, Any]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for locator in run["input_components"]:
        path = resolve_root_path(locator)
        values[locator] = sha256_file(path) if path.is_file() else "MISSING"
    return values


def frozen_bundle_binding_errors(
    plan: Mapping[str, Any],
    run: Mapping[str, Any],
    manifest: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> List[str]:
    """Recheck version, state, and identity joins at every consumption stage."""
    errors: List[str] = []
    problem = bundle.get("problem", {})
    scenario = bundle.get("scenario", {})
    line = bundle.get("line", {})
    problem_key = (problem.get("id"), problem.get("version"))
    scenario_problem = scenario.get("problem_ref", {})
    line_problem = line.get("problem_ref", {})
    if (scenario_problem.get("id"), scenario_problem.get("version")) != problem_key:
        errors.append("scenario.problem_ref differs from the frozen problem")
    if (line_problem.get("id"), line_problem.get("version")) != problem_key:
        errors.append("line.problem_ref differs from the frozen problem")
    if (
        bundle.get("batch_id") != plan.get("batch_id")
        or bundle.get("run_id") != run.get("run_id")
        or line.get("id") != run.get("line_id")
    ):
        errors.append("bundle batch, run, or line identity differs from the plan")
    expected_problem_ref = f"{problem_key[0]}@{problem_key[1]}"
    expected_scenario_ref = (
        f"{scenario.get('id')}@{scenario.get('version')}"
    )
    if (
        manifest.get("run_id") != run.get("run_id")
        or manifest.get("batch_id") != plan.get("batch_id")
        or manifest.get("line_id") != run.get("line_id")
        or manifest.get("mode") != plan.get("mode")
        or manifest.get("problem_ref") != expected_problem_ref
        or manifest.get("scenario_ref") != expected_scenario_ref
    ):
        errors.append("run manifest identity or version refs differ from the plan")
    study_mode = scenario.get("study_mode")
    if line.get("status") != "ACTIVE":
        errors.append("frozen research line is not ACTIVE")
    if study_mode == "PROBLEM_DEFINITION":
        if problem.get("status") not in {"SEED", "CANDIDATE", "ACTIVE"}:
            errors.append("problem-definition run uses an invalid problem state")
        if scenario.get("status") not in {"VALIDATED", "ACTIVE"}:
            errors.append("problem-definition run requires a validated scenario")
        if (
            line.get("schema_version") == "2.0"
            and line.get("research_target", {}).get("mechanism_ref")
            is not None
        ):
            errors.append(
                "scoped mechanism research cannot run in a "
                "PROBLEM_DEFINITION scenario"
            )
    elif (
        problem.get("status") != "ACTIVE"
        or scenario.get("status") != "ACTIVE"
    ):
        errors.append(
            "mechanism, source-acquisition, and reality runs require ACTIVE "
            "problem, scenario, and line snapshots"
        )
    if problem.get("schema_version") == "2.0" and line.get(
        "schema_version"
    ) != "2.0":
        errors.append("ProblemContract 2.0 requires LineContract 2.0")
    if study_mode != "PROBLEM_DEFINITION" and line.get(
        "schema_version"
    ) != "2.0":
        errors.append("non-definition research requires LineContract 2.0")
    return errors


def verify_frozen_run_input(
    run: Mapping[str, Any],
    manifest: Optional[Mapping[str, Any]] = None,
    plan: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Verify the exact input bytes and their complete semantic payload."""
    run_dir = resolve_root_path(str(run["run_dir"]))
    input_path = run_dir / "input.json"
    expected_payload_sha = run.get("input_payload_sha256")
    if not isinstance(expected_payload_sha, str):
        raise ResearchError(f"{run.get('line_id')}: plan lacks input payload SHA-256")
    if not input_path.is_file() or sha256_file(input_path) != expected_payload_sha:
        raise ResearchError(f"{run.get('line_id')}: frozen input.json bytes changed")
    bundle = load_json(input_path)
    binding_errors = frozen_bundle_binding_errors(
        plan or {},
        run,
        manifest or {},
        bundle,
    )
    if binding_errors:
        raise ResearchError(
            f"{run.get('line_id')}: " + "; ".join(binding_errors)
        )
    expected_hash = run.get("input_hash")
    if (
        not isinstance(expected_hash, str)
        or bundle.get("input_hash") != expected_hash
        or run_input_hash(bundle) != expected_hash
    ):
        raise ResearchError(
            f"{run.get('line_id')}: frozen input semantic payload changed"
        )
    if bundle.get("input_components") != run.get("input_components"):
        raise ResearchError(
            f"{run.get('line_id')}: input component manifest changed"
        )
    if bundle.get("research_focus") != run.get("research_focus"):
        raise ResearchError(
            f"{run.get('line_id')}: hypothesis or tested-claim focus changed"
        )
    line_target = bundle.get("line", {}).get("research_target", {})
    expected_focus = {
        "mechanism_ref": line_target.get("mechanism_ref"),
        "hypothesis_ids": line_target.get("hypothesis_ids", []),
        "tested_claim_ids": line_target.get("scoped_claim_ids", []),
    }
    if bundle.get("research_focus") != expected_focus:
        raise ResearchError(
            f"{run.get('line_id')}: research focus differs from embedded line"
        )
    profile_locators = [
        item.get("locator") for item in bundle.get("mechanism_profiles", [])
    ]
    expected_profile_locators = (
        [expected_focus["mechanism_ref"]]
        if isinstance(expected_focus["mechanism_ref"], str)
        else []
    )
    if profile_locators != expected_profile_locators:
        raise ResearchError(
            f"{run.get('line_id')}: mechanism snapshots differ from run focus"
        )
    if manifest is not None and (
        manifest.get("input_hash") != expected_hash
        or manifest.get("input_payload_sha256") != expected_payload_sha
        or manifest.get("research_focus") != run.get("research_focus")
        or (
            plan is not None
            and manifest.get("plan_fingerprint")
            != plan.get("plan_fingerprint")
        )
    ):
        raise ResearchError(
            f"{run.get('line_id')}: run manifest differs from frozen input"
        )
    if plan is not None:
        if plan.get("plan_fingerprint") != compute_plan_fingerprint(plan):
            raise ResearchError(
                f"{run.get('line_id')}: plan fingerprint is no longer valid"
            )
        canonical_documents = (
            (
                "problem",
                str(plan["problem_path"]),
                plan.get("problem_sha256"),
            ),
            (
                "scenario",
                str(plan["scenario_path"]),
                plan.get("scenario_sha256"),
            ),
            (
                "line",
                str(run["line_path"]),
                run.get("line_sha256"),
            ),
        )
        for bundle_key, locator, declared_sha in canonical_documents:
            path = resolve_root_path(locator)
            actual_sha = sha256_file(path) if path.is_file() else "MISSING"
            if (
                actual_sha != declared_sha
                or run["input_components"].get(locator) != actual_sha
                or canonical_bytes(bundle.get(bundle_key))
                != canonical_bytes(load_json(path))
            ):
                raise ResearchError(
                    f"{run.get('line_id')}: embedded {bundle_key} differs "
                    "from its canonical snapshot"
                )
        for profile_item in bundle.get("mechanism_profiles", []):
            locator = profile_item.get("locator")
            if not isinstance(locator, str):
                raise ResearchError(
                    f"{run.get('line_id')}: mechanism profile has no locator"
                )
            path = resolve_root_path(locator)
            actual_sha = sha256_file(path) if path.is_file() else "MISSING"
            if (
                actual_sha != profile_item.get("sha256")
                or run["input_components"].get(locator) != actual_sha
                or canonical_bytes(profile_item.get("profile"))
                != canonical_bytes(load_json(path))
            ):
                raise ResearchError(
                    f"{run.get('line_id')}: embedded mechanism profile differs "
                    "from canonical content"
                )
        for source_item in bundle.get("sources", []):
            locator = source_item.get("locator")
            if not isinstance(locator, str):
                raise ResearchError(
                    f"{run.get('line_id')}: source snapshot has no locator"
                )
            path = resolve_root_path(locator)
            data = path.read_bytes() if path.is_file() else b""
            try:
                content = data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ResearchError(
                    f"{run.get('line_id')}: canonical source is not UTF-8"
                ) from exc
            actual_sha = sha256_bytes(data) if path.is_file() else "MISSING"
            if (
                source_item.get("sha256") != actual_sha
                or source_item.get("content") != content
                or run["input_components"].get(locator) != actual_sha
            ):
                raise ResearchError(
                    f"{run.get('line_id')}: embedded source differs from "
                    "canonical content"
                )
    return bundle


def run_one(plan: Mapping[str, Any], run: Mapping[str, Any]) -> Tuple[str, str]:
    run_dir = resolve_root_path(run["run_dir"])
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path)
    try:
        bundle = verify_frozen_run_input(run, manifest, plan)
    except ResearchError:
        manifest["status"] = "POLICY_VIOLATION"
        manifest["finished_at"] = utc_now()
        write_json(manifest_path, manifest)
        return run["line_id"], "POLICY_VIOLATION"
    if current_components(run) != run["input_components"]:
        manifest["status"] = "STALE_FOR_CURRENT"
        manifest["finished_at"] = utc_now()
        write_json(manifest_path, manifest)
        return run["line_id"], "STALE_FOR_CURRENT"
    if manifest["status"] == "RUNNING":
        recover_interrupted_run(run_dir, manifest)
        write_json(manifest_path, manifest)
    result_path = run_dir / "result.json"
    if manifest["status"] == "COMPLETED" and result_path.is_file():
        try:
            verify_completed_run_artifacts(run_dir, manifest, bundle)
            return run["line_id"], "COMPLETED"
        except ResearchError:
            manifest["status"] = "POLICY_VIOLATION"
            manifest["finished_at"] = utc_now()
            write_json(manifest_path, manifest)
            return run["line_id"], "POLICY_VIOLATION"

    budget = bundle["line"]["budget"]
    max_attempts = int(budget["max_attempts"])
    while manifest["attempt"] < max_attempts:
        manifest["attempt"] += 1
        manifest["status"] = "RUNNING"
        manifest["started_at"] = utc_now()
        manifest["finished_at"] = None
        write_json(manifest_path, manifest)
        started = time.monotonic()
        try:
            if plan["mode"] == "mock":
                result = mock_result(bundle)
                exit_code = 0
                events = "mock execution\n"
                write_json(run_dir / "result.raw.json", result)
                (run_dir / "events.jsonl").write_text(
                    events,
                    encoding="utf-8",
                )
            else:
                result, exit_code, events = run_codex(
                    run_dir,
                    bundle,
                    timeout=int(budget["max_minutes"]) * 60,
                )
            result = bind_result_envelope(result, bundle)
            elapsed = time.monotonic() - started
            raw = canonical_bytes(result)
            result["cost"] = {
                "elapsed_seconds": round(elapsed, 3),
                "output_bytes": len(raw),
            }
            errors = validate_result_semantics(result, bundle)
            encoded = canonical_bytes(result)
            if len(encoded) > int(budget["max_output_bytes"]):
                errors.append("result exceeds line output budget")
            if errors:
                raise ResearchError("; ".join(errors))
            write_json(result_path, result)
            manifest["status"] = "COMPLETED"
            manifest["finished_at"] = utc_now()
            manifest["exit_code"] = exit_code
            manifest["result_sha256"] = sha256_file(result_path)
            manifest["raw_result_sha256"] = sha256_file(
                run_dir / "result.raw.json"
            )
            manifest["events_sha256"] = sha256_file(
                run_dir / "events.jsonl"
            )
            completion_seal_path = run_dir / "completion-seal.json"
            write_controller_seal(
                completion_seal_path,
                {
                    "schema_version": "1.0",
                    "kind": "RunCompletionControllerSeal",
                    "run_id": run["run_id"],
                    "batch_id": plan["batch_id"],
                    "plan_fingerprint": plan["plan_fingerprint"],
                    "input_hash": run["input_hash"],
                    "input_payload_sha256": run[
                        "input_payload_sha256"
                    ],
                    "result_sha256": manifest["result_sha256"],
                    "raw_result_sha256": manifest[
                        "raw_result_sha256"
                    ],
                    "events_sha256": manifest["events_sha256"],
                    "finished_at": manifest["finished_at"],
                },
            )
            manifest["completion_seal_sha256"] = sha256_file(
                completion_seal_path
            )
            manifest["cost"] = {
                "elapsed_seconds": round(elapsed, 3),
                "output_bytes": result_path.stat().st_size + len(events.encode("utf-8")),
            }
            write_json(manifest_path, manifest)
            return run["line_id"], "COMPLETED"
        except (ResearchError, OSError, json.JSONDecodeError) as exc:
            elapsed = time.monotonic() - started
            error_text = str(exc)
            infra_failure = is_infrastructure_failure(error_text)
            (run_dir / f"attempt-{manifest['attempt']}-error.txt").write_text(
                error_text + "\n",
                encoding="utf-8",
            )
            preserve_attempt_artifacts(run_dir, manifest["attempt"])
            manifest["status"] = "INFRA_FAILED" if infra_failure else "FAILED"
            manifest["finished_at"] = utc_now()
            manifest["exit_code"] = 1
            manifest["cost"] = {
                "elapsed_seconds": round(elapsed, 3),
                "output_bytes": directory_size(run_dir),
            }
            write_json(manifest_path, manifest)
            if infra_failure:
                return run["line_id"], "INFRA_FAILED"
    return run["line_id"], "FAILED"


def load_plan(path: Path) -> Dict[str, Any]:
    plan = load_json(path)
    if plan.get("batch_id") != path.parent.name:
        raise ResearchError("plan batch_id does not match runtime directory")
    if plan.get("schema_version") != "2.0":
        raise ResearchError(
            "legacy plan is preserved read-only; create a new schema 2.0 batch"
        )
    actual_fingerprint = compute_plan_fingerprint(plan)
    if plan.get("plan_fingerprint") != actual_fingerprint:
        raise ResearchError("plan immutable fields changed after fingerprinting")
    seal = load_controller_seal(path.parent / "plan-seal.json")
    expected_inputs = {
        run["run_id"]: {
            "input_hash": run["input_hash"],
            "input_payload_sha256": run["input_payload_sha256"],
        }
        for run in plan.get("runs", [])
    }
    if (
        seal.get("kind") != "PlanControllerSeal"
        or seal.get("batch_id") != plan.get("batch_id")
        or seal.get("plan_fingerprint") != actual_fingerprint
        or seal.get("run_inputs") != expected_inputs
    ):
        raise ResearchError(
            "plan differs from its read-only controller seal"
        )
    initial_protected = seal.get("protected_hashes")
    initial_external = seal.get("external_disclosure")
    protected_changed = plan.get("protected_hashes") != initial_protected
    external_changed = plan.get("external_disclosure") != initial_external
    if protected_changed or external_changed:
        authorization_seal = load_controller_seal(
            path.parent / "authorization-seal.json"
        )
        old_map = authorization_seal.get("previous_protected_hashes")
        new_map = authorization_seal.get("authorized_protected_hashes")
        changed = {
            locator
            for locator in set(old_map or {}) | set(new_map or {})
            if (old_map or {}).get(locator) != (new_map or {}).get(locator)
        }
        if (
            authorization_seal.get("kind") != "AuthorizationControllerSeal"
            or authorization_seal.get("batch_id") != plan.get("batch_id")
            or authorization_seal.get("plan_fingerprint")
            != actual_fingerprint
            or old_map != initial_protected
            or new_map != plan.get("protected_hashes")
            or changed - {relative(DECISIONS_PATH)}
            or authorization_seal.get(
                "previous_external_disclosure"
            )
            != initial_external
            or authorization_seal.get(
                "authorized_external_disclosure"
            )
            != plan.get("external_disclosure")
            or authorization_seal.get("approval_decision_id")
            != (plan.get("external_disclosure") or {}).get(
                "approval_decision_id"
            )
        ):
            raise ResearchError(
                "plan protected hashes differ from its authorized transition"
            )
    return plan


def verify_external_disclosure(plan: Mapping[str, Any]) -> Dict[str, Any]:
    external = plan.get("external_disclosure")
    if not isinstance(external, dict):
        raise ResearchError("codex plan has no external disclosure manifest")
    disclosure_path = resolve_root_path(external["manifest"])
    disclosure = load_json(disclosure_path)
    core = {
        key: value
        for key, value in disclosure.items()
        if key not in {"disclosure_sha256", "plan_fingerprint", "approval_decision_id"}
    }
    actual_core_hash = json_hash(core)
    if actual_core_hash != disclosure.get("disclosure_sha256"):
        raise ResearchError("external disclosure contents changed after fingerprinting")
    if actual_core_hash != external.get("disclosure_sha256"):
        raise ResearchError("external disclosure hash does not match the plan")
    if disclosure.get("plan_fingerprint") != plan.get("plan_fingerprint"):
        raise ResearchError("external disclosure plan fingerprint differs")
    planned_payloads = {
        relative(resolve_root_path(run["run_dir"]) / "input.json"):
        run.get("input_payload_sha256")
        for run in plan.get("runs", [])
    }
    for payload in disclosure.get("payloads", []):
        path = resolve_root_path(payload["payload"])
        if not path.is_file():
            raise ResearchError(f"disclosed payload is missing: {payload['payload']}")
        if path.stat().st_size != payload["size_bytes"] or sha256_file(path) != payload["sha256"]:
            raise ResearchError(f"disclosed payload changed: {payload['payload']}")
        if planned_payloads.get(payload["payload"]) != payload["sha256"]:
            raise ResearchError(
                f"disclosed payload differs from frozen run input: "
                f"{payload['payload']}"
            )
    return disclosure


def run_batch(args: argparse.Namespace) -> int:
    plan_path = resolve_root_path(args.plan)
    lock_path = plan_path.parent / ".controller.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(
                lock_handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError as exc:
            raise ResearchError(
                f"batch controller is already running: "
                f"{plan_path.parent.name}"
            ) from exc
        return run_batch_locked(args, plan_path)


def run_batch_locked(
    args: argparse.Namespace,
    plan_path: Path,
) -> int:
    plan = load_plan(plan_path)
    project = resolve_root_path(plan["project"])
    scenario_path = resolve_root_path(plan["scenario_path"])
    scenario = load_json(scenario_path)
    if scenario.get("status") == "ACTIVE":
        receipt_errors = check_exact_promotion_receipt(
            scenario_path,
            scenario,
            "scenario",
        )
        if receipt_errors:
            raise ResearchError("; ".join(receipt_errors))
    if plan["mode"] == "codex":
        disclosure_document = verify_external_disclosure(plan)
        disclosure = plan.get("external_disclosure") or {}
        decision_id = disclosure.get("approval_decision_id")
        target = {"id": plan["batch_id"], "version": plan.get("plan_fingerprint")}
        if not decision_allows_transfer(
            decision_id,
            "SEND_BATCH_TO_CODEX",
            target,
            disclosure_document,
            plan["project"],
        ):
            raise ResearchError(
                "Codex batch is blocked until a structured user decision authorizes "
                f"SEND_BATCH_TO_CODEX for {target['id']}@{target['version']}"
            )
    before = hash_paths(protected_paths(project))
    if before != plan["protected_hashes"]:
        raise ResearchError("protected canonical inputs changed since planning; create a new batch")
    if directory_size(plan_path.parent) > BATCH_LIMIT_BYTES:
        raise ResearchError("batch already exceeds 250 MiB; nothing was deleted")
    assert_runtime_budget()

    plan["status"] = "RUNNING"
    write_json(plan_path, plan)
    results: List[Tuple[str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(plan["max_parallel"])) as pool:
        futures = [pool.submit(run_one, plan, run) for run in plan["runs"]]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
    after = hash_paths(protected_paths(project))
    if after != before:
        for run in plan["runs"]:
            manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
            manifest = load_json(manifest_path)
            manifest["status"] = "POLICY_VIOLATION"
            write_json(manifest_path, manifest)
        plan["status"] = "POLICY_VIOLATION"
        write_json(plan_path, plan)
        raise ResearchError("a protected canonical file changed during the batch")

    statuses = dict(results)
    plan["status"] = "COMPLETED" if all(value == "COMPLETED" for value in statuses.values()) else "NEEDS_ATTENTION"
    plan["finished_at"] = utc_now()
    write_json(plan_path, plan)
    for line_id, status in sorted(results):
        print(f"[{status}] {line_id}")
    if directory_size(plan_path.parent) > BATCH_LIMIT_BYTES:
        raise ResearchError("batch exceeded 250 MiB after execution; no further runs are allowed")
    if plan["status"] != "COMPLETED":
        return 1
    print(f"[OK] batch completed without canonical mutation: {plan['batch_id']}")
    return 0


def resume_batch(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan_path = batch_dir / "plan.json"
    if not plan_path.is_file():
        raise ResearchError(f"unknown batch: {args.batch}")
    args.plan = relative(plan_path)
    return run_batch(args)


def authorize_batch(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan_path = batch_dir / "plan.json"
    plan = load_plan(plan_path)
    if plan.get("mode") != "codex":
        raise ResearchError("only codex batches require external-transfer authorization")
    target = {"id": plan["batch_id"], "version": plan.get("plan_fingerprint")}
    disclosure = verify_external_disclosure(plan)
    if not decision_allows_transfer(
        args.decision_id,
        "SEND_BATCH_TO_CODEX",
        target,
        disclosure,
        plan["project"],
    ):
        raise ResearchError(
            f"user decision {args.decision_id} does not authorize "
            f"SEND_BATCH_TO_CODEX for {target['id']}@{target['version']}"
        )
    disclosure_path = resolve_root_path(
        plan["external_disclosure"]["manifest"]
    )
    disclosure["approval_decision_id"] = args.decision_id
    plan["external_disclosure"]["approval_decision_id"] = args.decision_id
    project = resolve_root_path(plan["project"])
    refreshed_protected = hash_paths(protected_paths(project))
    plan_seal = load_controller_seal(batch_dir / "plan-seal.json")
    previous_protected = plan_seal.get("protected_hashes", {})
    previous_external = plan_seal.get("external_disclosure")
    changed_protected = {
        locator
        for locator in set(previous_protected) | set(refreshed_protected)
        if previous_protected.get(locator) != refreshed_protected.get(locator)
    }
    decisions_locator = relative(DECISIONS_PATH)
    unexpected_changes = sorted(changed_protected - {decisions_locator})
    if unexpected_changes:
        raise ResearchError(
            "authorization cannot rebaseline protected research files: "
            f"{unexpected_changes}"
        )
    # An exact approval may be recorded after planning, so only DECISIONS.md
    # may advance here. Standing authorization normally changes nothing.
    if changed_protected and changed_protected != {decisions_locator}:
        raise ResearchError(
            "authorization observed an invalid protected-state transition"
        )
    for run in plan["runs"]:
        manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
        manifest = load_json(manifest_path)
        if manifest["status"] != "PLANNED":
            raise ResearchError(
                f"cannot authorize after a worker started: "
                f"{run['line_id']}={manifest['status']}"
            )
    authorization_document = {
        "schema_version": "1.0",
        "kind": "AuthorizationControllerSeal",
        "batch_id": plan["batch_id"],
        "plan_fingerprint": plan["plan_fingerprint"],
        "approval_decision_id": args.decision_id,
        "disclosure_sha256": disclosure["disclosure_sha256"],
        "previous_protected_hashes": previous_protected,
        "authorized_protected_hashes": refreshed_protected,
        "previous_external_disclosure": previous_external,
        "authorized_external_disclosure": copy.deepcopy(
            plan["external_disclosure"]
        ),
        "sealed_at": utc_now(),
    }
    authorization_path = batch_dir / "authorization-seal.json"
    if authorization_path.is_file():
        existing_authorization = load_controller_seal(
            authorization_path
        )
        for key, value in authorization_document.items():
            if key == "sealed_at":
                continue
            if existing_authorization.get(key) != value:
                raise ResearchError(
                    "existing authorization seal differs from the "
                    "requested exact authorization"
                )
    else:
        write_controller_seal(
            authorization_path,
            authorization_document,
        )
    plan["protected_hashes"] = refreshed_protected
    for run in plan["runs"]:
        manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
        manifest = load_json(manifest_path)
        manifest["protected_hashes"] = refreshed_protected
        write_json(manifest_path, manifest)
    write_json(disclosure_path, disclosure)
    write_json(plan_path, plan)
    print(
        f"[OK] authorized exact Codex payload: {target['id']}@{target['version']} "
        f"via {args.decision_id}"
    )
    return 0


def retry_infra_batch(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan_path = batch_dir / "plan.json"
    plan = load_plan(plan_path)
    if plan.get("mode") != "codex":
        raise ResearchError("infrastructure retry is only valid for codex batches")
    disclosure = verify_external_disclosure(plan)
    target = {"id": plan["batch_id"], "version": plan.get("plan_fingerprint")}
    decision_id = (plan.get("external_disclosure") or {}).get("approval_decision_id")
    if not decision_allows_transfer(
        decision_id,
        "SEND_BATCH_TO_CODEX",
        target,
        disclosure,
        plan["project"],
    ):
        raise ResearchError("the exact Codex payload is no longer authorized")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reset_count = 0
    for run in plan["runs"]:
        run_dir = resolve_root_path(run["run_dir"])
        manifest_path = run_dir / "manifest.json"
        manifest = load_json(manifest_path)
        if manifest["status"] not in {"FAILED", "INFRA_FAILED", "COMPLETED"}:
            raise ResearchError(
                f"cannot infrastructure-reset {run['line_id']} from {manifest['status']}"
            )
        result_path = run_dir / "result.json"
        access_blocked = False
        if result_path.exists():
            result = load_json(result_path)
            access_blocked = result_is_access_blocked(result)
            if not access_blocked:
                raise ResearchError(
                    f"cannot reset {run['line_id']}: substantive result already exists"
                )
        evidence_parts: List[str] = []
        for path in sorted(run_dir.glob("attempt-*-error.txt")):
            evidence_parts.append(path.read_text(encoding="utf-8", errors="replace"))
        events_path = run_dir / "events.jsonl"
        if events_path.is_file():
            evidence_parts.append(events_path.read_text(encoding="utf-8", errors="replace"))
        evidence = "\n".join(evidence_parts)
        if not is_infrastructure_failure(evidence) and not access_blocked:
            raise ResearchError(
                f"cannot classify {run['line_id']} as infrastructure failure"
            )
        history = run_dir / "infra-history" / timestamp
        history.mkdir(parents=True, exist_ok=False)
        evidence_files = set(run_dir.glob("attempt-*-error.txt"))
        evidence_files.update(run_dir.glob("attempt-*-events.jsonl"))
        evidence_files.update(run_dir.glob("attempt-*-result.raw.json"))
        for name in (
            "events.jsonl",
            "result.raw.json",
            "result.json",
            "completion-seal.json",
        ):
            path = run_dir / name
            if path.is_file():
                evidence_files.add(path)
        for path in sorted(evidence_files):
            shutil.copy2(path, history / path.name)
        if result_path.is_file():
            result_path.unlink()
        completion_seal_path = run_dir / "completion-seal.json"
        if completion_seal_path.is_file():
            completion_seal_path.unlink()
        manifest["status"] = "PLANNED"
        manifest["attempt"] = 0
        manifest["started_at"] = None
        manifest["finished_at"] = None
        manifest["exit_code"] = None
        manifest["result_sha256"] = None
        manifest["raw_result_sha256"] = None
        manifest["events_sha256"] = None
        manifest["completion_seal_sha256"] = None
        manifest["cost"] = {"elapsed_seconds": 0, "output_bytes": 0}
        write_json(manifest_path, manifest)
        reset_count += 1
    plan["status"] = "PLANNED"
    plan.pop("finished_at", None)
    write_json(plan_path, plan)
    print(
        f"[OK] preserved infrastructure evidence and reset {reset_count} runs "
        f"for the same authorized payload: {disclosure['disclosure_sha256']}"
    )
    return 0


def completed_results(plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for run in plan["runs"]:
        run_dir = resolve_root_path(run["run_dir"])
        manifest = load_json(run_dir / "manifest.json")
        if manifest["status"] != "COMPLETED":
            raise ResearchError(f"run is not complete: {run['line_id']} ({manifest['status']})")
        bundle = verify_frozen_run_input(run, manifest, plan)
        if current_components(run) != run["input_components"]:
            raise ResearchError(
                f"run input sources changed after execution: {run['line_id']}"
            )
        result = verify_completed_run_artifacts(
            run_dir,
            manifest,
            bundle,
        )
        results.append(result)
    return results


def build_bounded_review_target(
    input_bundle: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    focus = input_bundle.get("research_focus", {})
    tested_claim_ids = focus.get("tested_claim_ids", [])
    hypothesis_ids = focus.get("hypothesis_ids", [])
    mechanism_profiles = input_bundle.get("mechanism_profiles", [])
    if not (tested_claim_ids or hypothesis_ids) or not mechanism_profiles:
        return None
    profile = mechanism_profiles[0]["profile"]
    return {
        "mechanism": {
            "id": profile["id"],
            "version": profile["version"],
            "title": profile["title"],
            "origin_problem": profile["origin_problem"],
            "assumptions": profile["assumptions"],
            "selected_claims": [
                claim
                for claim in profile["scoped_claims"]
                if claim["id"] in tested_claim_ids
            ],
            "selected_hypotheses": [
                hypothesis
                for hypothesis in profile.get("hypothesis_map", [])
                if hypothesis["id"] in hypothesis_ids
            ],
            "non_responsibilities": profile["non_responsibilities"],
        },
        "tested_claim_ids": tested_claim_ids,
        "hypothesis_ids": hypothesis_ids,
        "line_non_claims": input_bundle["line"]
        .get("research_target", {})
        .get("non_claims", []),
        "outcome_policy": input_bundle["line"].get("outcome_policy"),
    }


def build_review_bundle(
    plan: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    input_bundles: Optional[
        Mapping[str, Mapping[str, Any]]
    ] = None,
) -> Dict[str, Any]:
    if input_bundles:
        first_bundle = next(iter(input_bundles.values()))
        problem = copy.deepcopy(first_bundle["problem"])
        scenario = copy.deepcopy(first_bundle["scenario"])
    else:
        problem = load_json(resolve_root_path(plan["problem_path"]))
        scenario = load_json(resolve_root_path(plan["scenario_path"]))
    run_by_line = {run["line_id"]: run for run in plan["runs"]}
    anonymized: List[Dict[str, Any]] = []
    scoped_flags: List[bool] = []
    for index, result in enumerate(sorted(results, key=lambda item: item["line_id"]), 1):
        run = run_by_line[result["line_id"]]
        if input_bundles is not None:
            input_bundle = input_bundles[result["line_id"]]
        else:
            input_bundle = load_json(
                resolve_root_path(run["run_dir"]) / "input.json"
            )
        focus = input_bundle.get("research_focus", {})
        tested_claim_ids = focus.get("tested_claim_ids", [])
        hypothesis_ids = focus.get("hypothesis_ids", [])
        scoped_flags.append(bool(tested_claim_ids or hypothesis_ids))
        bounded_target = build_bounded_review_target(input_bundle)
        anonymous_sources = [
            {
                "statement": statement["statement"],
                "source_locator": f"SRC-R{index:02d}-{source_index:02d}",
                "source_range": statement["source_range"],
            }
            for source_index, statement in enumerate(result["source_statements"], 1)
        ]
        anonymous_return = {
            "anonymous_return_id": f"R{index:02d}",
            "bounded_target": bounded_target,
            "direct_observations": result["direct_observations"],
            "source_statements": anonymous_sources,
            "inferences": result["inferences"],
            "design_proposals": result["design_proposals"],
            "negative_results": result["negative_results"],
            "alternative_explanations": result["alternative_explanations"],
            "candidate_claims": result["candidate_claims"],
            "new_discriminators": result["new_discriminators"],
            "scoped_claim_updates": result.get("scoped_claim_updates", []),
            "unaffected_claim_ids": result.get("unaffected_claim_ids", []),
            "applicability": result["applicability"],
            "cannot_support": result["cannot_support"],
        }
        anonymized.append(anonymous_return)
    if any(scoped_flags) and not all(scoped_flags):
        raise ResearchError(
            "blind review cannot mix problem-frame and scoped-mechanism returns"
        )
    review_scope = "SCOPED_MECHANISM" if any(scoped_flags) else "PROBLEM_FRAME"
    if review_scope == "SCOPED_MECHANISM":
        review_questions = [
            (
                "Assess every frozen anonymous-return / hypothesis / scoped-claim "
                "unit separately; use claim_id null for a hypothesis with no claim."
            ),
            "Which tested claim is actually supported, narrowed, refuted, or unaffected?",
            "Does any return escape its exact hypothesis or tested-claim scope?",
            "Which result belongs to a companion mechanism rather than the named mechanism?",
            "What strongest existing solution or baseline could explain the same result?",
            "Which portable capability survives if an identity-core claim fails?",
        ]
    else:
        review_questions = [
            "What is the strongest counterargument to the proposed problem frame?",
            "Which inference is not supported by the supplied observations?",
            "Which minority distinction would be erased by premature synthesis?",
            (
                "What evidence or scenario is still required before activating "
                f"{problem['id']}@{problem['version']}?"
            ),
            "Could a strong central researcher or existing institution explain the same results at lower cost?",
        ]
    bundle = {
        "schema_version": "2.0",
        "kind": "BlindReviewBundle",
        "batch_id": plan["batch_id"],
        "review_scope": review_scope,
        "required_output": {
            "schema_version": "2.0",
            "kind": "BlindReview",
            "review_scope": review_scope,
        },
        "problem": {
            "id": problem["id"],
            "version": problem["version"],
            "status": problem["status"],
            "question": problem["question"],
            "invariants": problem["invariants"],
            "shared_basis": problem.get("shared_basis"),
            "competing_explanations": problem["competing_explanations"],
            "strong_baselines": problem["strong_baselines"],
            "falsification_conditions": problem["falsification_conditions"],
        },
        "scenario": {
            "id": scenario["id"],
            "version": scenario["version"],
            "study_mode": scenario["study_mode"],
            "outcome_semantics": scenario["outcome_semantics"],
            "strongest_credible_baseline": scenario["strongest_credible_baseline"],
            "cannot_support": scenario["cannot_support"],
        },
        "anonymous_returns": anonymized,
        "review_questions": review_questions,
        "excluded": [
            "expected answer",
            "candidate synthesis",
            "formal line identities",
            "non-allowlisted archive material",
            "private participant data"
        ]
    }
    return bundle


def prepare_review(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan = load_plan(batch_dir / "plan.json")
    results = completed_results(plan)
    bundle = build_review_bundle(plan, results)
    problem = bundle["problem"]
    review_scope = bundle["review_scope"]
    review_dir = batch_dir / "review"
    review_dir.mkdir(exist_ok=True)
    write_json(review_dir / "review-bundle.json", bundle)
    (review_dir / "REVIEW_POLICY.md").write_text(
        "# Blind review policy\n\n"
        f"Review scope: {review_scope}. "
        "Attack only the supplied problem frame or exact scoped claims as applicable. "
        "For scoped mechanism review, return one assessment for every exact "
        "anonymous_return_id/hypothesis_id/claim_id unit; do not merge conflicts "
        "across returns or hypotheses, and use claim_id null when a hypothesis has "
        "no scoped claim. "
        "Never turn a companion-mechanism result into evidence for the target mechanism. "
        "Do not infer user approval or real-world validity. "
        "Do not use tools, workspace files, memory, web sources, or prior Towow knowledge. "
        "Base every criticism only on review-bundle.json and preserve minority distinctions.\n",
        encoding="utf-8",
    )
    review_disclosure = {
        "schema_version": "1.0",
        "kind": "ExternalDisclosureManifest",
        "batch_id": plan["batch_id"],
        "destination": "Anthropic Claude",
        "classification": "NON_PUBLIC_DERIVED_RESEARCH",
        "purpose": (
            f"Blind {review_scope.lower()} attack for "
            f"{problem['id']}@{problem['version']}"
        ),
        "payload": relative(review_dir / "review-bundle.json"),
        "payload_sha256": sha256_file(review_dir / "review-bundle.json"),
        "payload_size_bytes": (review_dir / "review-bundle.json").stat().st_size,
        "does_not_include": bundle["excluded"],
        "approval_decision_id": None,
    }
    write_json(review_dir / "review-disclosure.json", review_disclosure)
    print(f"[OK] blind review bundle prepared: {relative(review_dir / 'review-bundle.json')}")
    print(
        "[BLOCKED] Claude transfer requires SEND_BLIND_REVIEW_TO_CLAUDE for "
        f"{plan['batch_id']}@{review_disclosure['payload_sha256']}"
    )
    return 0


def expected_scoped_review_units(
    bundle: Mapping[str, Any],
) -> set[Tuple[str, str, Optional[str]]]:
    """Return each independently reviewable return/hypothesis/claim unit."""
    expected: set[Tuple[str, str, Optional[str]]] = set()
    for returned in bundle.get("anonymous_returns", []):
        return_id = returned.get("anonymous_return_id")
        target = returned.get("bounded_target")
        if not isinstance(return_id, str) or not isinstance(target, Mapping):
            continue
        tested_claims = set(target.get("tested_claim_ids", []))
        selected_hypotheses = (
            target.get("mechanism", {}).get("selected_hypotheses", [])
        )
        for hypothesis in selected_hypotheses:
            hypothesis_id = hypothesis.get("id")
            if not isinstance(hypothesis_id, str):
                continue
            claims = [
                claim_id
                for claim_id in hypothesis.get("scoped_claim_ids", [])
                if claim_id in tested_claims
            ]
            if claims:
                expected.update(
                    (return_id, hypothesis_id, claim_id)
                    for claim_id in claims
                )
            else:
                expected.add((return_id, hypothesis_id, None))
    return expected


def validate_blind_review_semantics(
    review: Mapping[str, Any],
    bundle: Mapping[str, Any],
    review_path: Path,
) -> List[str]:
    errors = validate_schema(review, review_path)
    if review.get("schema_version") != "2.0":
        errors.append("blind review must use schema_version 2.0")
    if review.get("review_scope") != bundle.get("review_scope"):
        errors.append(
            "blind review scope differs from frozen review bundle: "
            f"{review.get('review_scope')!r} != {bundle.get('review_scope')!r}"
        )
    if bundle.get("review_scope") != "SCOPED_MECHANISM":
        return errors

    for returned in bundle.get("anonymous_returns", []):
        target = returned.get("bounded_target")
        if not isinstance(target, Mapping):
            errors.append("scoped blind review return has no bounded target")
            continue
        declared_hypotheses = set(target.get("hypothesis_ids", []))
        selected_hypotheses = {
            item.get("id")
            for item in target.get("mechanism", {}).get(
                "selected_hypotheses", []
            )
        }
        if declared_hypotheses != selected_hypotheses:
            errors.append(
                "blind review bundle hypothesis definitions differ from "
                "its frozen hypothesis ids"
            )
        declared_claims = set(target.get("tested_claim_ids", []))
        selected_claims = {
            item.get("id")
            for item in target.get("mechanism", {}).get(
                "selected_claims", []
            )
        }
        if declared_claims != selected_claims:
            errors.append(
                "blind review bundle claim definitions differ from its "
                "frozen tested claims"
            )
    expected = expected_scoped_review_units(bundle)
    observed_items = review.get("scoped_assessments", [])
    observed = [
        (
            item.get("anonymous_return_id"),
            item.get("hypothesis_id"),
            item.get("claim_id"),
        )
        for item in observed_items
    ]
    observed_set = set(observed)
    if len(observed) != len(observed_set):
        errors.append(
            "blind review repeats an exact return/hypothesis/claim assessment"
        )
    unknown = sorted(
        observed_set - expected,
        key=lambda item: tuple("" if value is None else value for value in item),
    )
    if unknown:
        errors.append(
            f"blind review assesses units outside frozen scope: {unknown}"
        )
    missing = sorted(
        expected - observed_set,
        key=lambda item: tuple("" if value is None else value for value in item),
    )
    if missing:
        errors.append(f"blind review omits frozen scoped units: {missing}")
    return errors


def extract_structured_review(
    envelope: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    review = envelope.get("structured_output")
    if isinstance(review, dict):
        return review
    result_value = envelope.get("result")
    if isinstance(result_value, str):
        try:
            parsed = json.loads(result_value)
        except json.JSONDecodeError:
            return None
        if isinstance(parsed, dict):
            return parsed
    return None


def run_review(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    review_dir = batch_dir / "review"
    bundle_path = review_dir / "review-bundle.json"
    if not bundle_path.is_file():
        prepare_review(argparse.Namespace(batch=args.batch))
    disclosure_path = review_dir / "review-disclosure.json"
    disclosure = load_json(disclosure_path)
    review_target = {"id": args.batch, "version": disclosure["payload_sha256"]}
    plan = load_plan(batch_dir / "plan.json")
    if not decision_allows_transfer(
        args.decision_id,
        "SEND_BLIND_REVIEW_TO_CLAUDE",
        review_target,
        disclosure,
        plan["project"],
    ):
        raise ResearchError(
            f"user decision {args.decision_id} does not authorize "
            f"SEND_BLIND_REVIEW_TO_CLAUDE for {args.batch}@{disclosure['payload_sha256']}"
        )
    if sha256_file(bundle_path) != disclosure["payload_sha256"]:
        raise ResearchError("blind review payload changed after disclosure")
    disclosure["approval_decision_id"] = args.decision_id
    write_json(disclosure_path, disclosure)
    executable = shutil.which("claude")
    if not executable:
        raise ResearchError("claude executable is unavailable")
    bundle = load_json(bundle_path)
    schema = {
        key: value
        for key, value in schema_for("BlindReview").items()
        if key not in {"$schema", "$id"}
    }
    prompt = (
        (review_dir / "REVIEW_POLICY.md").read_text(encoding="utf-8")
        + "\n\nReview this isolated bundle:\n"
        + json.dumps(bundle, ensure_ascii=False)
    )
    raw_path = review_dir / "claude-raw.json"
    if raw_path.is_file():
        history = review_dir / "attempt-history"
        history.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for name in (
            "claude-raw.json",
            "claude-stderr.txt",
            "blind-review.json",
            "blind-review-execution.json",
            "blind-review-seal.json",
        ):
            prior = review_dir / name
            if prior.is_file():
                shutil.copy2(prior, history / f"{timestamp}-{name}")
                prior.unlink()
    command = [
        executable,
        "--safe-mode",
        "--no-session-persistence",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--model",
        args.model,
        "--effort",
        "high",
        "--max-budget-usd",
        str(args.max_budget_usd),
        "-p",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, ensure_ascii=False),
    ]
    try:
        proc = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            timeout=int(args.timeout_minutes) * 60,
            check=False,
            cwd=review_dir,
        )
    except subprocess.TimeoutExpired as exc:
        raise ResearchError(f"Claude blind review timed out after {args.timeout_minutes} minutes") from exc
    raw_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path = review_dir / "claude-stderr.txt"
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise ResearchError(f"Claude blind review exited {proc.returncode}")
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ResearchError("Claude did not return JSON output") from exc
    review = extract_structured_review(envelope)
    if review is None:
        raise ResearchError("Claude JSON envelope has no structured review")
    errors = validate_blind_review_semantics(
        review,
        bundle,
        review_dir / "blind-review.json",
    )
    if errors:
        raise ResearchError("; ".join(errors))
    review_path = review_dir / "blind-review.json"
    write_json(review_path, review)
    execution_receipt = {
        "schema_version": "1.0",
        "kind": "BlindReviewExecutionReceipt",
        "batch_id": plan["batch_id"],
        "reviewer": "Anthropic Claude",
        "model": args.model,
        "review_scope": bundle["review_scope"],
        "payload_path": relative(bundle_path),
        "payload_sha256": sha256_file(bundle_path),
        "disclosure_path": relative(disclosure_path),
        "disclosure_sha256": sha256_file(disclosure_path),
        "review_path": relative(review_path),
        "review_sha256": sha256_file(review_path),
        "raw_path": relative(raw_path),
        "raw_sha256": sha256_file(raw_path),
        "stderr_path": relative(stderr_path),
        "stderr_sha256": sha256_file(stderr_path),
        "process_exit_code": proc.returncode,
        "approval_decision_id": args.decision_id,
        "completed_at": utc_now(),
    }
    execution_path = review_dir / "blind-review-execution.json"
    write_json(execution_path, execution_receipt)
    write_controller_seal(
        review_dir / "blind-review-seal.json",
        {
            "schema_version": "1.0",
            "kind": "BlindReviewControllerSeal",
            "batch_id": plan["batch_id"],
            "execution_receipt_sha256": sha256_file(execution_path),
            "payload_sha256": execution_receipt["payload_sha256"],
            "review_sha256": execution_receipt["review_sha256"],
            "raw_sha256": execution_receipt["raw_sha256"],
            "stderr_sha256": execution_receipt["stderr_sha256"],
            "sealed_at": utc_now(),
        },
    )
    print(f"[OK] Claude blind review completed: {relative(review_path)}")
    return 0


def verify_blind_review_artifacts(
    batch_dir: Path,
    plan: Mapping[str, Any],
) -> Dict[str, Any]:
    """Verify review semantics, frozen payload, transfer authority, and provenance."""
    review_dir = batch_dir / "review"
    paths = {
        "bundle": review_dir / "review-bundle.json",
        "disclosure": review_dir / "review-disclosure.json",
        "review": review_dir / "blind-review.json",
        "raw": review_dir / "claude-raw.json",
        "stderr": review_dir / "claude-stderr.txt",
        "execution": review_dir / "blind-review-execution.json",
        "seal": review_dir / "blind-review-seal.json",
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise ResearchError(
            f"blind review provenance artifacts are missing: {missing}"
        )
    bundle = load_json(paths["bundle"])
    expected_bundle = build_review_bundle(plan, completed_results(plan))
    if canonical_bytes(bundle) != canonical_bytes(expected_bundle):
        raise ResearchError(
            "blind review bundle cannot be reproduced from the finalized "
            "plan and completed results"
        )
    disclosure = load_json(paths["disclosure"])
    review = load_json(paths["review"])
    execution = load_json(paths["execution"])
    try:
        raw_envelope = json.loads(paths["raw"].read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchError(
            f"blind review raw Claude envelope is invalid: {exc}"
        ) from exc
    if not isinstance(raw_envelope, dict):
        raise ResearchError("blind review raw Claude envelope is not an object")
    raw_review = extract_structured_review(raw_envelope)
    if raw_review is None or canonical_bytes(raw_review) != canonical_bytes(
        review
    ):
        raise ResearchError(
            "blind-review.json differs from Claude raw structured output"
        )
    payload_sha = sha256_file(paths["bundle"])
    if (
        disclosure.get("payload") != relative(paths["bundle"])
        or disclosure.get("payload_sha256") != payload_sha
        or disclosure.get("payload_size_bytes") != paths["bundle"].stat().st_size
    ):
        raise ResearchError(
            "blind review disclosure differs from its frozen payload"
        )
    target = {"id": plan["batch_id"], "version": payload_sha}
    decision_id = disclosure.get("approval_decision_id")
    if not decision_allows_transfer(
        decision_id,
        "SEND_BLIND_REVIEW_TO_CLAUDE",
        target,
        disclosure,
        str(plan["project"]),
    ):
        raise ResearchError(
            "blind review has no valid exact or standing Claude transfer authority"
        )
    review_errors = validate_blind_review_semantics(
        review,
        bundle,
        paths["review"],
    )
    if review_errors:
        raise ResearchError("; ".join(review_errors))
    expected_execution = {
        "schema_version": "1.0",
        "kind": "BlindReviewExecutionReceipt",
        "batch_id": plan["batch_id"],
        "reviewer": "Anthropic Claude",
        "review_scope": bundle.get("review_scope"),
        "payload_path": relative(paths["bundle"]),
        "payload_sha256": payload_sha,
        "disclosure_path": relative(paths["disclosure"]),
        "disclosure_sha256": sha256_file(paths["disclosure"]),
        "review_path": relative(paths["review"]),
        "review_sha256": sha256_file(paths["review"]),
        "raw_path": relative(paths["raw"]),
        "raw_sha256": sha256_file(paths["raw"]),
        "stderr_path": relative(paths["stderr"]),
        "stderr_sha256": sha256_file(paths["stderr"]),
        "process_exit_code": 0,
        "approval_decision_id": decision_id,
    }
    if any(execution.get(key) != value for key, value in expected_execution.items()):
        raise ResearchError(
            "blind review execution receipt does not bind the exact payload, "
            "review, raw output, disclosure, and approval"
        )
    if not isinstance(execution.get("model"), str) or not execution["model"]:
        raise ResearchError("blind review execution receipt has no model identity")
    if not isinstance(execution.get("completed_at"), str):
        raise ResearchError("blind review execution receipt has no completion time")
    seal = load_controller_seal(paths["seal"])
    if (
        seal.get("kind") != "BlindReviewControllerSeal"
        or seal.get("batch_id") != plan.get("batch_id")
        or seal.get("execution_receipt_sha256")
        != sha256_file(paths["execution"])
        or seal.get("payload_sha256") != payload_sha
        or seal.get("review_sha256") != sha256_file(paths["review"])
        or seal.get("raw_sha256") != sha256_file(paths["raw"])
        or seal.get("stderr_sha256") != sha256_file(paths["stderr"])
    ):
        raise ResearchError(
            "blind review differs from its read-only controller seal"
        )
    return {
        "bundle": bundle,
        "disclosure": disclosure,
        "review": review,
        "execution": execution,
        "paths": paths,
    }


def attach_verified_blind_review(
    target: Path,
    manifest: MutableMapping[str, Any],
    artifacts: Mapping[str, Any],
) -> None:
    """Copy verified review evidence while constructing candidate staging."""
    source_paths = artifacts["paths"]
    destination_names = {
        "bundle": "review-bundle.json",
        "disclosure": "review-disclosure.json",
        "review": "blind-review.json",
        "execution": "blind-review-execution.json",
        "raw": "claude-raw.json",
        "stderr": "claude-stderr.txt",
        "seal": "blind-review-seal.json",
    }
    copied: Dict[str, Path] = {}
    for key, name in destination_names.items():
        source = source_paths[key]
        destination = target / name
        if destination.is_file():
            if sha256_file(destination) != sha256_file(source):
                raise ResearchError(
                    f"candidate {name} differs from verified runtime artifact"
                )
        else:
            shutil.copy2(source, destination)
        manifest["result_hashes"][name] = sha256_file(destination)
        copied[key] = destination
    review = artifacts["review"]
    disclosure = artifacts["disclosure"]
    manifest["blind_review"] = {
        "reviewer": artifacts["execution"]["reviewer"],
        "model": artifacts["execution"]["model"],
        "bundle": copied["bundle"].name,
        "bundle_sha256": sha256_file(copied["bundle"]),
        "disclosure": copied["disclosure"].name,
        "disclosure_sha256": sha256_file(copied["disclosure"]),
        "result": copied["review"].name,
        "result_sha256": sha256_file(copied["review"]),
        "execution_receipt": copied["execution"].name,
        "execution_receipt_sha256": sha256_file(copied["execution"]),
        "raw_output": copied["raw"].name,
        "raw_output_sha256": sha256_file(copied["raw"]),
        "stderr_output": copied["stderr"].name,
        "stderr_output_sha256": sha256_file(copied["stderr"]),
        "controller_seal": copied["seal"].name,
        "controller_seal_sha256": sha256_file(copied["seal"]),
        "payload_sha256": disclosure["payload_sha256"],
        "approval_decision_id": disclosure["approval_decision_id"],
        "status": review["status"],
        "recommendation": review["recommendation"],
    }


def make_divergence_markdown(results: Sequence[Mapping[str, Any]], batch_id: str) -> str:
    lines = [
        f"# 研究线分歧矩阵：{batch_id}",
        "",
        "本文件逐线保留本批实际返回，不按票数合并。完全相同的句子只表示文本重合，不构成独立证据。",
        "",
        "| 研究线 | 候选主张 | 负结果 | 新判别器 |",
        "|---|---|---|---|",
    ]
    for result in sorted(results, key=lambda item: item["line_id"]):
        claim = "<br>".join(result["candidate_claims"]) or "—"
        negative = "<br>".join(result["negative_results"]) or "—"
        discriminator = "<br>".join(result["new_discriminators"]) or "—"
        lines.append(
            f"| {result['line_id']} | {claim.replace('|', '｜')} | "
            f"{negative.replace('|', '｜')} | {discriminator.replace('|', '｜')} |"
        )
    claim_counts: Dict[str, int] = {}
    for result in results:
        for claim in result["candidate_claims"]:
            claim_counts[claim] = claim_counts.get(claim, 0) + 1
    shared = [claim for claim, count in claim_counts.items() if count > 1]
    lines.extend(["", "## 逐字共享主张", ""])
    if shared:
        lines.extend(f"- {claim}" for claim in shared)
    else:
        lines.append("- 无。该结果不表示各线没有交集，只表示尚未进行会抹平差异的语义归并。")
    lines.extend(
        [
            "",
            "## 晋升边界",
            "",
            "- 本矩阵是候选导航，不自动成为任何 Problem 版本。",
            "- 少数线、拒绝、Unknown、中心方案更好和无净增值不得因综合而删除。",
            "- 用户必须单独决定激活、重写、拒绝或继续保持多个候选。",
            "",
        ]
    )
    scoped_results = [
        result
        for result in results
        if result.get("tested_claim_ids") or result.get("hypothesis_ids")
    ]
    if scoped_results:
        lines.extend(
            [
                "",
                "## 有界假说与主张影响",
                "",
                "| 研究线 | 冻结假说 | 本次可检验主张 | 候选变化 | 未受影响 |",
                "|---|---|---|---|---|",
            ]
        )
        for result in sorted(
            scoped_results, key=lambda item: item["line_id"]
        ):
            updates = "<br>".join(
                f"{item['claim_id']}: {item['proposed_status']}"
                for item in result.get("scoped_claim_updates", [])
            ) or "—"
            lines.append(
                f"| {result['line_id']} | "
                f"{'<br>'.join(result.get('hypothesis_ids', [])) or '—'} | "
                f"{'<br>'.join(result.get('tested_claim_ids', [])) or '—'} | "
                f"{updates} | "
                f"{'<br>'.join(result.get('unaffected_claim_ids', [])) or '—'} |"
            )
    return "\n".join(lines)


def verify_candidate_blind_review(
    target: Path,
    manifest: Mapping[str, Any],
    plan: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    input_bundles: Mapping[str, Mapping[str, Any]],
) -> None:
    metadata = manifest.get("blind_review")
    blind_names = {
        "bundle": "review-bundle.json",
        "disclosure": "review-disclosure.json",
        "review": "blind-review.json",
        "execution": "blind-review-execution.json",
        "raw": "claude-raw.json",
        "stderr": "claude-stderr.txt",
        "seal": "blind-review-seal.json",
    }
    present = {
        key: target / name
        for key, name in blind_names.items()
        if (target / name).is_file()
    }
    if metadata is None:
        if present:
            raise ResearchError(
                "candidate has blind-review artifacts without manifest "
                "metadata"
            )
        return
    if not isinstance(metadata, Mapping) or len(present) != len(
        blind_names
    ):
        raise ResearchError(
            "candidate blind-review evidence closure is incomplete"
        )
    paths = {key: target / name for key, name in blind_names.items()}
    bundle = load_json(paths["bundle"])
    expected_bundle = build_review_bundle(
        plan,
        results,
        input_bundles,
    )
    if canonical_bytes(bundle) != canonical_bytes(expected_bundle):
        raise ResearchError(
            "candidate blind-review bundle cannot be rebuilt from "
            "frozen inputs"
        )
    disclosure = load_json(paths["disclosure"])
    review = load_json(paths["review"])
    execution = load_json(paths["execution"])
    try:
        raw_envelope = json.loads(
            paths["raw"].read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchError(
            f"candidate Claude raw envelope is invalid: {exc}"
        ) from exc
    raw_review = (
        extract_structured_review(raw_envelope)
        if isinstance(raw_envelope, Mapping)
        else None
    )
    if raw_review is None or canonical_bytes(raw_review) != canonical_bytes(
        review
    ):
        raise ResearchError(
            "candidate blind review differs from Claude raw output"
        )
    payload_sha = sha256_file(paths["bundle"])
    if (
        disclosure.get("payload_sha256") != payload_sha
        or disclosure.get("payload_size_bytes")
        != paths["bundle"].stat().st_size
        or disclosure.get("batch_id") != plan.get("batch_id")
    ):
        raise ResearchError(
            "candidate blind-review disclosure differs from its payload"
        )
    decision_id = disclosure.get("approval_decision_id")
    if not decision_allows_transfer(
        decision_id,
        "SEND_BLIND_REVIEW_TO_CLAUDE",
        {"id": plan["batch_id"], "version": payload_sha},
        disclosure,
        str(plan["project"]),
    ):
        raise ResearchError(
            "candidate blind review has no valid transfer authority"
        )
    review_errors = validate_blind_review_semantics(
        review,
        bundle,
        paths["review"],
    )
    if review_errors:
        raise ResearchError("; ".join(review_errors))
    expected_execution = {
        "schema_version": "1.0",
        "kind": "BlindReviewExecutionReceipt",
        "batch_id": plan["batch_id"],
        "reviewer": "Anthropic Claude",
        "review_scope": bundle.get("review_scope"),
        "payload_sha256": payload_sha,
        "disclosure_sha256": sha256_file(paths["disclosure"]),
        "review_sha256": sha256_file(paths["review"]),
        "raw_sha256": sha256_file(paths["raw"]),
        "stderr_sha256": sha256_file(paths["stderr"]),
        "process_exit_code": 0,
        "approval_decision_id": decision_id,
    }
    if any(
        execution.get(key) != value
        for key, value in expected_execution.items()
    ):
        raise ResearchError(
            "candidate blind-review execution receipt does not bind "
            "its copied evidence"
        )
    if not isinstance(execution.get("model"), str) or not execution["model"]:
        raise ResearchError(
            "candidate blind-review receipt has no model identity"
        )
    seal = load_controller_seal(paths["seal"])
    if (
        seal.get("kind") != "BlindReviewControllerSeal"
        or seal.get("batch_id") != plan.get("batch_id")
        or seal.get("execution_receipt_sha256")
        != sha256_file(paths["execution"])
        or seal.get("payload_sha256") != payload_sha
        or seal.get("review_sha256") != sha256_file(paths["review"])
        or seal.get("raw_sha256") != sha256_file(paths["raw"])
        or seal.get("stderr_sha256") != sha256_file(paths["stderr"])
    ):
        raise ResearchError(
            "candidate blind review differs from its controller seal"
        )
    expected_metadata = {
        "reviewer": execution["reviewer"],
        "model": execution["model"],
        "bundle": paths["bundle"].name,
        "bundle_sha256": payload_sha,
        "disclosure": paths["disclosure"].name,
        "disclosure_sha256": sha256_file(paths["disclosure"]),
        "result": paths["review"].name,
        "result_sha256": sha256_file(paths["review"]),
        "execution_receipt": paths["execution"].name,
        "execution_receipt_sha256": sha256_file(paths["execution"]),
        "raw_output": paths["raw"].name,
        "raw_output_sha256": sha256_file(paths["raw"]),
        "stderr_output": paths["stderr"].name,
        "stderr_output_sha256": sha256_file(paths["stderr"]),
        "controller_seal": paths["seal"].name,
        "controller_seal_sha256": sha256_file(paths["seal"]),
        "payload_sha256": payload_sha,
        "approval_decision_id": decision_id,
        "status": review["status"],
        "recommendation": review["recommendation"],
    }
    if dict(metadata) != expected_metadata:
        raise ResearchError(
            "candidate blind-review manifest metadata was rewritten"
        )


def verify_candidate_packet(
    target: Path,
    *,
    published_target: Optional[Path] = None,
) -> Dict[str, Any]:
    """Verify a packet from frozen evidence, including pre-publication staging."""
    receipt_root = published_target or target
    manifest_path = target / "finalization-manifest.json"
    if not manifest_path.is_file():
        raise ResearchError(
            f"candidate directory exists without manifest: {relative(target)}"
        )
    manifest = load_json(manifest_path)
    if (
        manifest.get("schema_version") != "1.0"
        or manifest.get("kind") != "CandidateReturnPacket"
        or manifest.get("status") != "CANDIDATE"
        or manifest.get("promotion_authority") != "USER"
        or not isinstance(manifest.get("finalized_at"), str)
    ):
        raise ResearchError(
            "finalization manifest has invalid packet semantics"
        )
    result_hashes = manifest.get("result_hashes", {})
    if not isinstance(result_hashes, Mapping):
        raise ResearchError("candidate packet has no result hash map")
    actual_names = {
        path.name
        for path in target.iterdir()
        if path.is_file() and path.name != manifest_path.name
    }
    if set(result_hashes) != actual_names:
        raise ResearchError(
            "candidate result hash map does not exactly enumerate artifacts"
        )
    for name, expected_sha in result_hashes.items():
        artifact = target / str(name)
        if not artifact.is_file() or sha256_file(artifact) != expected_sha:
            raise ResearchError(
                f"candidate artifact hash mismatch: {relative(artifact)}"
            )
    plan_path = target / "plan-snapshot.json"
    plan_seal_path = target / "plan-seal.json"
    plan = load_json(plan_path)
    plan_seal = load_controller_seal(plan_seal_path)
    if (
        plan.get("schema_version") != "2.0"
        or plan.get("status") != "COMPLETED"
        or not isinstance(plan.get("finished_at"), str)
        or plan.get("plan_fingerprint") != compute_plan_fingerprint(plan)
        or plan_seal.get("kind") != "PlanControllerSeal"
        or plan_seal.get("batch_id") != plan.get("batch_id")
        or plan_seal.get("plan_fingerprint") != plan.get("plan_fingerprint")
    ):
        raise ResearchError("candidate packet has an invalid frozen plan seal")
    expected_inputs = {
        run["run_id"]: {
            "input_hash": run["input_hash"],
            "input_payload_sha256": run["input_payload_sha256"],
        }
        for run in plan.get("runs", [])
    }
    if (
        not expected_inputs
        or len(expected_inputs) != len(plan.get("runs", []))
        or plan_seal.get("run_inputs") != expected_inputs
    ):
        raise ResearchError("candidate plan seal names different run inputs")
    initial_protected = plan_seal.get("protected_hashes")
    initial_external = plan_seal.get("external_disclosure")
    protected_changed = plan.get("protected_hashes") != initial_protected
    external_changed = plan.get("external_disclosure") != initial_external
    authorization: Optional[Dict[str, Any]] = None
    if protected_changed or external_changed or plan.get("mode") == "codex":
        authorization_path = target / "authorization-seal.json"
        authorization = load_controller_seal(authorization_path)
        old_map = authorization.get("previous_protected_hashes")
        new_map = authorization.get("authorized_protected_hashes")
        changed = {
            locator
            for locator in set(old_map or {}) | set(new_map or {})
            if (old_map or {}).get(locator) != (new_map or {}).get(locator)
        }
        if (
            authorization.get("kind") != "AuthorizationControllerSeal"
            or authorization.get("batch_id") != plan.get("batch_id")
            or authorization.get("plan_fingerprint")
            != plan.get("plan_fingerprint")
            or old_map != initial_protected
            or new_map != plan.get("protected_hashes")
            or changed - {relative(DECISIONS_PATH)}
            or authorization.get("previous_external_disclosure")
            != initial_external
            or authorization.get("authorized_external_disclosure")
            != plan.get("external_disclosure")
            or authorization.get("approval_decision_id")
            != (plan.get("external_disclosure") or {}).get(
                "approval_decision_id"
            )
        ):
            raise ResearchError(
                "candidate has no exact authorization transition"
            )
    if plan.get("mode") == "codex":
        external = plan.get("external_disclosure")
        disclosure_path = target / "codex-disclosure-manifest.json"
        if not isinstance(external, Mapping) or not disclosure_path.is_file():
            raise ResearchError(
                "candidate Codex packet has no frozen disclosure"
            )
        disclosure = load_json(disclosure_path)
        core = {
            key: value
            for key, value in disclosure.items()
            if key
            not in {
                "disclosure_sha256",
                "plan_fingerprint",
                "approval_decision_id",
            }
        }
        core_sha = json_hash(core)
        payloads = {
            item.get("run_id"): item
            for item in disclosure.get("payloads", [])
        }
        if (
            core_sha != disclosure.get("disclosure_sha256")
            or core_sha != external.get("disclosure_sha256")
            or disclosure.get("plan_fingerprint")
            != plan.get("plan_fingerprint")
            or disclosure.get("approval_decision_id")
            != external.get("approval_decision_id")
            or set(payloads) != set(expected_inputs)
            or authorization is None
            or authorization.get("disclosure_sha256") != core_sha
        ):
            raise ResearchError(
                "candidate Codex disclosure differs from the frozen plan"
            )
    elif plan.get("external_disclosure") is not None:
        raise ResearchError(
            "candidate mock plan unexpectedly declares external disclosure"
        )
    candidate_results: List[Dict[str, Any]] = []
    candidate_inputs: Dict[str, Dict[str, Any]] = {}
    for run in plan.get("runs", []):
        line_id = run["line_id"]
        paths = {
            "result": target / f"{line_id}.json",
            "receipt": target / f"evidence-{line_id}.json",
            "run_manifest": target / f"run-manifest-{line_id}.json",
            "input": target / f"input-{line_id}.json",
            "raw": target / f"raw-result-{line_id}.json",
            "events": target / f"events-{line_id}.jsonl",
            "completion": target / f"completion-seal-{line_id}.json",
        }
        if any(not path.is_file() for path in paths.values()):
            raise ResearchError(
                f"candidate packet is missing frozen artifacts for {line_id}"
            )
        result = load_json(paths["result"])
        receipt = load_json(paths["receipt"])
        run_manifest = load_json(paths["run_manifest"])
        input_bundle = load_json(paths["input"])
        raw_result = load_json(paths["raw"])
        completion = load_controller_seal(paths["completion"])
        path_hashes = {
            key: sha256_file(path)
            for key, path in paths.items()
        }
        artifact_hashes = {
            "result_sha256": path_hashes["result"],
            "raw_result_sha256": path_hashes["raw"],
            "events_sha256": path_hashes["events"],
        }
        if (
            validate_schema(run_manifest, paths["run_manifest"])
            or run_manifest.get("status") != "COMPLETED"
            or run_manifest.get("completion_seal_sha256")
            != path_hashes["completion"]
            or any(
                run_manifest.get(field) != value
                for field, value in artifact_hashes.items()
            )
            or completion.get("kind") != "RunCompletionControllerSeal"
            or completion.get("run_id") != run.get("run_id")
            or completion.get("plan_fingerprint")
            != plan.get("plan_fingerprint")
            or completion.get("input_hash") != run.get("input_hash")
            or completion.get("input_payload_sha256")
            != path_hashes["input"]
            or any(
                completion.get(field) != value
                for field, value in artifact_hashes.items()
            )
        ):
            raise ResearchError(
                f"candidate completion seal mismatch for {line_id}"
            )
        if (
            input_bundle.get("input_hash") != run_input_hash(input_bundle)
            or input_bundle.get("input_hash") != run.get("input_hash")
            or path_hashes["input"] != run.get("input_payload_sha256")
        ):
            raise ResearchError(
                f"candidate input semantic hash mismatch for {line_id}"
            )
        relationship_errors = frozen_bundle_binding_errors(
            plan,
            run,
            run_manifest,
            input_bundle,
        )
        if relationship_errors:
            raise ResearchError("; ".join(relationship_errors))
        rebound = bind_result_envelope(raw_result, input_bundle)
        rebound.pop("cost", None)
        result_without_cost = copy.deepcopy(result)
        result_without_cost.pop("cost", None)
        if canonical_bytes(rebound) != canonical_bytes(result_without_cost):
            raise ResearchError(
                f"candidate result differs from raw output for {line_id}"
            )
        result_errors = validate_result_semantics(result, input_bundle)
        if result_errors:
            raise ResearchError("; ".join(result_errors))
        receipt_expectations = {
            "run_id": run["run_id"],
            "input_hash": run["input_hash"],
            "input_payload_sha256": path_hashes["input"],
            "research_focus": run.get("research_focus"),
            "result_path": relative(
                receipt_root / paths["result"].name
            ),
            "result_sha256": path_hashes["result"],
            "plan_snapshot_path": relative(
                receipt_root / plan_path.name
            ),
            "plan_snapshot_sha256": sha256_file(plan_path),
            "plan_seal_path": relative(
                receipt_root / plan_seal_path.name
            ),
            "plan_seal_sha256": sha256_file(plan_seal_path),
            "run_manifest_snapshot_path": relative(
                receipt_root / paths["run_manifest"].name
            ),
            "run_manifest_snapshot_sha256": path_hashes["run_manifest"],
            "input_snapshot_path": relative(
                receipt_root / paths["input"].name
            ),
            "input_snapshot_sha256": path_hashes["input"],
            "raw_result_snapshot_path": relative(
                receipt_root / paths["raw"].name
            ),
            "raw_result_snapshot_sha256": path_hashes["raw"],
            "events_snapshot_path": relative(
                receipt_root / paths["events"].name
            ),
            "events_snapshot_sha256": path_hashes["events"],
            "completion_seal_snapshot_path": relative(
                receipt_root / paths["completion"].name
            ),
            "completion_seal_snapshot_sha256": path_hashes["completion"],
        }
        if any(
            receipt.get(key) != value
            for key, value in receipt_expectations.items()
        ):
            raise ResearchError(
                f"candidate evidence receipt mismatch for {line_id}"
            )
        candidate_results.append(result)
        candidate_inputs[line_id] = input_bundle
    first_input = candidate_inputs[plan["runs"][0]["line_id"]]
    expected_problem_ref = (
        f"{first_input['problem']['id']}@"
        f"{first_input['problem']['version']}"
    )
    expected_scenario_ref = (
        f"{first_input['scenario']['id']}@"
        f"{first_input['scenario']['version']}"
    )
    expected_cannot_support = [
        f"{expected_problem_ref} activation",
        "stable claims",
        "real Effect, Domain Adoption, Acceptance, or net value",
    ]
    if (
        manifest.get("batch_id") != plan.get("batch_id")
        or manifest.get("problem_ref") != expected_problem_ref
        or manifest.get("scenario_ref") != expected_scenario_ref
        or manifest.get("cannot_support") != expected_cannot_support
    ):
        raise ResearchError(
            "candidate manifest differs from its frozen plan and inputs"
        )
    matrix_path = target / "divergence-matrix.md"
    if matrix_path.read_text(encoding="utf-8") != make_divergence_markdown(
        candidate_results,
        str(plan["batch_id"]),
    ):
        raise ResearchError(
            "candidate divergence matrix differs from frozen results"
        )
    if plan.get("mode") == "codex":
        disclosure = load_json(
            target / "codex-disclosure-manifest.json"
        )
        payloads = {
            item["run_id"]: item
            for item in disclosure["payloads"]
        }
        for run in plan["runs"]:
            item = payloads[run["run_id"]]
            input_path = target / f"input-{run['line_id']}.json"
            if (
                item.get("sha256") != sha256_file(input_path)
                or item.get("size_bytes") != input_path.stat().st_size
            ):
                raise ResearchError(
                    "candidate Codex disclosure payload differs from "
                    "the frozen input"
                )
        decision_id = (
            plan.get("external_disclosure") or {}
        ).get("approval_decision_id")
        if not decision_allows_transfer(
            decision_id,
            "SEND_BATCH_TO_CODEX",
            {
                "id": plan["batch_id"],
                "version": plan["plan_fingerprint"],
            },
            disclosure,
            str(plan["project"]),
        ):
            raise ResearchError(
                "candidate Codex packet has no valid transfer authority"
            )
    verify_candidate_blind_review(
        target,
        manifest,
        plan,
        candidate_results,
        candidate_inputs,
    )
    return manifest


def finalize_batch(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan = load_plan(batch_dir / "plan.json")
    project = resolve_root_path(plan["project"])
    candidates_root = project / "candidates"
    final_target = candidates_root / plan["batch_id"]
    if final_target.exists():
        manifest_path = final_target / "finalization-manifest.json"
        if manifest_path.is_file():
            verify_candidate_packet(final_target)
            review_path = batch_dir / "review" / "blind-review.json"
            packet_has_review = (
                load_json(manifest_path).get("blind_review") is not None
            )
            if review_path.is_file() and not packet_has_review:
                raise ResearchError(
                    "candidate packets are immutable; a blind review produced "
                    "after finalization must be preserved in a new batch or "
                    "append-only candidate revision"
                )
            print(
                f"[OK] candidate already finalized: "
                f"{relative(final_target)}"
            )
            return 0
        interrupted_root = candidates_root / "interrupted-finalizations"
        interrupted_root.mkdir(parents=True, exist_ok=True)
        preserved = interrupted_root / (
            f"{plan['batch_id']}-unsealed-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + f"-{uuid.uuid4().hex[:6]}"
        )
        shutil.move(str(final_target), preserved)
    results = completed_results(plan)
    if len(results) != len(plan["runs"]):
        raise ResearchError("not all planned runs returned")
    if hash_paths(protected_paths(project)) != plan["protected_hashes"]:
        for run in plan["runs"]:
            manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
            manifest = load_json(manifest_path)
            manifest["status"] = "STALE_FOR_CURRENT"
            write_json(manifest_path, manifest)
        raise ResearchError("canonical inputs changed; results were preserved but marked stale")
    candidates_root.mkdir(parents=True, exist_ok=True)
    target = candidates_root / f".{plan['batch_id']}.staging"
    if target.exists():
        interrupted_root = candidates_root / "interrupted-finalizations"
        interrupted_root.mkdir(parents=True, exist_ok=True)
        preserved = interrupted_root / (
            f"{plan['batch_id']}-staging-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + f"-{uuid.uuid4().hex[:6]}"
        )
        shutil.move(str(target), preserved)
    target.mkdir()
    result_hashes: Dict[str, str] = {}
    plan_snapshot_path = target / "plan-snapshot.json"
    write_json(plan_snapshot_path, plan)
    plan_snapshot_sha256 = sha256_file(plan_snapshot_path)
    result_hashes[plan_snapshot_path.name] = plan_snapshot_sha256
    plan_seal_path = target / "plan-seal.json"
    shutil.copy2(batch_dir / "plan-seal.json", plan_seal_path)
    result_hashes[plan_seal_path.name] = sha256_file(plan_seal_path)
    authorization_seal_path = batch_dir / "authorization-seal.json"
    if authorization_seal_path.is_file():
        authorization_snapshot_path = target / "authorization-seal.json"
        shutil.copy2(
            authorization_seal_path,
            authorization_snapshot_path,
        )
        result_hashes[authorization_snapshot_path.name] = sha256_file(
            authorization_snapshot_path
        )
    external_disclosure = plan.get("external_disclosure")
    if isinstance(external_disclosure, Mapping):
        disclosure_snapshot_path = (
            target / "codex-disclosure-manifest.json"
        )
        shutil.copy2(
            resolve_root_path(str(external_disclosure["manifest"])),
            disclosure_snapshot_path,
        )
        result_hashes[disclosure_snapshot_path.name] = sha256_file(
            disclosure_snapshot_path
        )
    run_by_line = {run["line_id"]: run for run in plan["runs"]}
    for result in results:
        run = run_by_line[result["line_id"]]
        runtime_manifest = load_json(
            resolve_root_path(run["run_dir"]) / "manifest.json"
        )
        bundle = verify_frozen_run_input(
            run,
            runtime_manifest,
            plan,
        )
        path = target / f"{result['line_id']}.json"
        write_json(path, result)
        result_sha = sha256_file(path)
        result_hashes[path.name] = result_sha
        run_manifest_snapshot_path = (
            target / f"run-manifest-{result['line_id']}.json"
        )
        write_json(run_manifest_snapshot_path, runtime_manifest)
        run_manifest_snapshot_sha256 = sha256_file(
            run_manifest_snapshot_path
        )
        result_hashes[run_manifest_snapshot_path.name] = (
            run_manifest_snapshot_sha256
        )
        input_snapshot_path = target / f"input-{result['line_id']}.json"
        raw_result_snapshot_path = (
            target / f"raw-result-{result['line_id']}.json"
        )
        events_snapshot_path = target / f"events-{result['line_id']}.jsonl"
        completion_seal_snapshot_path = (
            target / f"completion-seal-{result['line_id']}.json"
        )
        shutil.copy2(
            resolve_root_path(run["run_dir"]) / "input.json",
            input_snapshot_path,
        )
        shutil.copy2(
            resolve_root_path(run["run_dir"]) / "result.raw.json",
            raw_result_snapshot_path,
        )
        shutil.copy2(
            resolve_root_path(run["run_dir"]) / "events.jsonl",
            events_snapshot_path,
        )
        shutil.copy2(
            resolve_root_path(run["run_dir"]) / "completion-seal.json",
            completion_seal_snapshot_path,
        )
        input_snapshot_sha256 = sha256_file(input_snapshot_path)
        raw_result_snapshot_sha256 = sha256_file(
            raw_result_snapshot_path
        )
        events_snapshot_sha256 = sha256_file(events_snapshot_path)
        completion_seal_snapshot_sha256 = sha256_file(
            completion_seal_snapshot_path
        )
        result_hashes[input_snapshot_path.name] = input_snapshot_sha256
        result_hashes[raw_result_snapshot_path.name] = (
            raw_result_snapshot_sha256
        )
        result_hashes[events_snapshot_path.name] = events_snapshot_sha256
        result_hashes[completion_seal_snapshot_path.name] = (
            completion_seal_snapshot_sha256
        )
        focus = bundle.get("research_focus", {})
        mechanism_ref = focus.get("mechanism_ref")
        selected_profile: Optional[Mapping[str, Any]] = None
        for profile_item in bundle.get("mechanism_profiles", []):
            if profile_item.get("locator") == mechanism_ref:
                selected_profile = profile_item.get("profile")
                break
        claim_definition_sha256: Dict[str, str] = {}
        hypothesis_definition_sha256: Dict[str, str] = {}
        if isinstance(selected_profile, Mapping):
            claim_definition_sha256 = {
                claim["id"]: claim_definition_hash(claim)
                for claim in selected_profile.get("scoped_claims", [])
                if claim.get("id") in focus.get("tested_claim_ids", [])
            }
            hypothesis_definition_sha256 = {
                hypothesis["id"]: hypothesis_definition_hash(hypothesis)
                for hypothesis in selected_profile.get("hypothesis_map", [])
                if hypothesis.get("id") in focus.get("hypothesis_ids", [])
            }
        evidence_path = target / f"evidence-{result['line_id']}.json"
        evidence_receipt = {
            "schema_version": "1.0",
            "kind": "RunEvidenceReceipt",
            "run_id": result["run_id"],
            "input_hash": result["input_hash"],
            "input_payload_sha256": run["input_payload_sha256"],
            "research_focus": focus,
            "problem_ref": (
                f"{bundle['problem']['id']}@{bundle['problem']['version']}"
            ),
            "mechanism_ref": mechanism_ref,
            "mechanism_id": (
                selected_profile.get("id")
                if isinstance(selected_profile, Mapping)
                else None
            ),
            "mechanism_version": (
                selected_profile.get("version")
                if isinstance(selected_profile, Mapping)
                else None
            ),
            "scenario_class": bundle["scenario"]["scenario_class"],
            "study_mode": bundle["scenario"]["study_mode"],
            "result_path": relative(final_target / path.name),
            "result_sha256": result_sha,
            "plan_snapshot_path": relative(
                final_target / plan_snapshot_path.name
            ),
            "plan_snapshot_sha256": plan_snapshot_sha256,
            "plan_seal_path": relative(
                final_target / plan_seal_path.name
            ),
            "plan_seal_sha256": sha256_file(plan_seal_path),
            "run_manifest_snapshot_path": relative(
                final_target / run_manifest_snapshot_path.name
            ),
            "run_manifest_snapshot_sha256": run_manifest_snapshot_sha256,
            "input_snapshot_path": relative(
                final_target / input_snapshot_path.name
            ),
            "input_snapshot_sha256": input_snapshot_sha256,
            "raw_result_snapshot_path": relative(
                final_target / raw_result_snapshot_path.name
            ),
            "raw_result_snapshot_sha256": raw_result_snapshot_sha256,
            "events_snapshot_path": relative(
                final_target / events_snapshot_path.name
            ),
            "events_snapshot_sha256": events_snapshot_sha256,
            "completion_seal_snapshot_path": relative(
                final_target / completion_seal_snapshot_path.name
            ),
            "completion_seal_snapshot_sha256": (
                completion_seal_snapshot_sha256
            ),
            "claim_definition_sha256": claim_definition_sha256,
            "hypothesis_definition_sha256": hypothesis_definition_sha256,
        }
        write_json(evidence_path, evidence_receipt)
        result_hashes[evidence_path.name] = sha256_file(evidence_path)
    matrix_path = target / "divergence-matrix.md"
    matrix_path.write_text(
        make_divergence_markdown(results, plan["batch_id"]),
        encoding="utf-8",
    )
    result_hashes[matrix_path.name] = sha256_file(matrix_path)
    problem_document = load_json(resolve_root_path(plan["problem_path"]))
    manifest = {
        "schema_version": "1.0",
        "kind": "CandidateReturnPacket",
        "batch_id": plan["batch_id"],
        "finalized_at": utc_now(),
        "problem_ref": f"{problem_document['id']}@{problem_document['version']}",
        "scenario_ref": f"{load_json(resolve_root_path(plan['scenario_path']))['id']}@"
        f"{load_json(resolve_root_path(plan['scenario_path']))['version']}",
        "status": "CANDIDATE",
        "result_hashes": result_hashes,
        "promotion_authority": "USER",
        "cannot_support": [
            f"{problem_document['id']}@{problem_document['version']} activation",
            "stable claims",
            "real Effect, Domain Adoption, Acceptance, or net value"
        ]
    }
    review_path = batch_dir / "review" / "blind-review.json"
    if review_path.is_file():
        artifacts = verify_blind_review_artifacts(batch_dir, plan)
        attach_verified_blind_review(target, manifest, artifacts)
    write_json(target / "finalization-manifest.json", manifest)
    try:
        verify_candidate_packet(
            target,
            published_target=final_target,
        )
    except ResearchError:
        interrupted_root = candidates_root / "interrupted-finalizations"
        interrupted_root.mkdir(parents=True, exist_ok=True)
        preserved = interrupted_root / (
            f"{plan['batch_id']}-invalid-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + f"-{uuid.uuid4().hex[:6]}"
        )
        shutil.move(str(target), preserved)
        raise
    target.rename(final_target)
    verify_candidate_packet(final_target)
    print(
        f"[OK] finalized candidate packet without promotion: "
        f"{relative(final_target)}"
    )
    return 0


def promote(args: argparse.Namespace) -> int:
    candidate_path = resolve_root_path(args.candidate)
    candidate = load_json(candidate_path)
    source_sha256 = sha256_file(candidate_path)
    project = project_path(args.project)
    if project not in candidate_path.parents:
        raise ResearchError("promotion candidate does not belong to selected project")
    action_by_target = {
        "problem": "ACTIVATE_PROBLEM",
        "scenario": "ACTIVATE_REAL_SCENARIO"
        if candidate.get("scenario_class") == "REAL"
        else "ACTIVATE_SCENARIO",
        "claim": "PROMOTE_STABLE_CLAIM",
    }
    action = action_by_target[args.target]
    if (
        args.target == "problem"
        and candidate.get("schema_version") == "2.0"
    ):
        bundle_errors = verify_problem_activation_bundle(
            candidate,
            candidate_path,
        )
        if bundle_errors:
            raise ResearchError(
                "problem activation bundle preflight failed:\n- "
                + "\n- ".join(bundle_errors)
            )
    if not decision_allows_promotion(
        args.decision_id,
        action,
        candidate,
        candidate_path,
    ):
        raise ResearchError(
            f"user decision {args.decision_id} does not authorize {action} "
            "for the exact candidate path and SHA-256"
        )
    receipt_dir = project / "promotions"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    if args.target == "problem":
        if candidate.get("kind") != "ProblemContract" or candidate.get("status") != "CANDIDATE":
            raise ResearchError("problem promotion requires a CANDIDATE ProblemContract")
        promoted = copy.deepcopy(candidate)
        promoted["status"] = "ACTIVE"
        active_companion = (
            project / "problem" / f"{promoted['version']}.md"
        )
        promoted["companion_markdown"] = relative(active_companion)
        promotion_errors = validate_schema(promoted, candidate_path)
        promotion_errors.extend(check_companion(candidate, candidate_path))
        promotion_errors.extend(
            check_problem_lineage(project, candidate_path, promoted)
        )
        promotion_errors.extend(
            check_problem_historical_inheritance(
                project,
                candidate_path,
                promoted,
            )
        )
        if promotion_errors:
            raise ResearchError(
                "problem promotion preflight failed:\n- "
                + "\n- ".join(promotion_errors)
            )
        target = project / "problem" / f"{promoted['version']}.json"
        companion_text = render_problem_active_companion(
            candidate,
            candidate_path,
            args.decision_id,
        )
        if active_companion.is_file():
            if active_companion.read_text(
                encoding="utf-8"
            ) != companion_text:
                raise ResearchError(
                    f"existing ACTIVE problem companion differs from the "
                    f"deterministic projection: {relative(active_companion)}"
                )
        else:
            atomic_write_text(
                active_companion,
                companion_text,
                replace_existing=False,
            )
        if target.is_file():
            existing_target = load_json(target)
            if canonical_bytes(existing_target) != canonical_bytes(promoted):
                raise ResearchError(
                    f"existing ACTIVE problem differs from the deterministic "
                    f"projection: {relative(target)}"
                )
        else:
            write_json_once(target, promoted)

        receipt_path = (
            receipt_dir
            / f"{candidate.get('id')}-{args.decision_id}.json"
        )
        receipt = {
            "promotion_id": (
                f"PROM-{candidate.get('id')}-{args.decision_id}"
            ),
            "target_kind": args.target,
            "target_id": candidate.get("id"),
            "target_version": candidate.get("version"),
            "decision_id": args.decision_id,
            "promoted_at": utc_now(),
            "source_candidate": relative(candidate_path),
            "source_sha256": source_sha256,
            "target": relative(target),
            "target_sha256": sha256_file(target),
            "target_companion": relative(active_companion),
            "target_companion_sha256": sha256_file(active_companion),
        }
        if candidate.get("schema_version") == "2.0":
            bundle_path = resolve_root_path(
                str(candidate["activation_bundle_ref"])
            )
            receipt.update(
                {
                    "activation_bundle_path": relative(bundle_path),
                    "activation_bundle_sha256": sha256_file(bundle_path),
                }
            )
        if receipt_path.is_file():
            existing_receipt = load_json(receipt_path)
            for key, expected_value in receipt.items():
                if key == "promoted_at":
                    continue
                if existing_receipt.get(key) != expected_value:
                    raise ResearchError(
                        f"existing problem promotion receipt differs at "
                        f"{key}: {relative(receipt_path)}"
                    )
            receipt = existing_receipt
        else:
            write_json_once(receipt_path, receipt)
        postflight_errors = check_exact_promotion_receipt(
            target,
            promoted,
            "problem",
        )
        if postflight_errors:
            raise ResearchError(
                "problem promotion postflight failed before NOW update:\n- "
                + "\n- ".join(postflight_errors)
            )

        state = read_state()
        state["active_problem"] = relative(target)
        if state.get("candidate_problem") == relative(candidate_path):
            state["candidate_problem"] = None
        problem_key = f"{promoted['id']}@{promoted['version']}"
        if problem_key in state.get("lines_by_problem", {}):
            state["lines_by_problem"][problem_key]["status"] = (
                "ACTIVE_NO_ACTIVE_LINES"
            )
        state["active_lines"] = []
        state["pending_user_decisions"] = [
            item
            for item in state.get("pending_user_decisions", [])
            if not (
                relative(candidate_path) in item
                or "审阅、重写或激活" in item
            )
        ]
        state["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        write_state(state)
    elif args.target == "scenario":
        if candidate.get("kind") != "ScenarioContract" or candidate.get("status") not in {
            "PROPOSED",
            "VALIDATED",
        }:
            raise ResearchError("scenario promotion requires a PROPOSED or VALIDATED ScenarioContract")
        promoted = copy.deepcopy(candidate)
        promoted["status"] = "ACTIVE"
        promoted["activation"]["requires_user_approval"] = True
        promoted["activation"]["approval_decision_id"] = args.decision_id
        target = project / "scenarios" / f"{candidate_path.stem}-active.json"
        if target.resolve() == candidate_path.resolve():
            raise ResearchError("scenario candidate and ACTIVE target must differ")
        if target.exists():
            raise ResearchError(
                f"active scenario target already exists: {relative(target)}"
            )
        promotion_errors = validate_schema(promoted, target)
        promotion_errors.extend(check_companion(promoted, target))
        if promotion_errors:
            raise ResearchError(
                "scenario promotion preflight failed:\n- "
                + "\n- ".join(promotion_errors)
            )
        write_json(target, promoted)
        state = read_state()
        state["active_mechanism_scenario"] = relative(target)
        state["updated_at"] = datetime.now(timezone.utc).date().isoformat()
        write_state(state)
    else:
        if candidate.get("kind") != "ClaimCandidate" or candidate.get("status") not in {
            "CANDIDATE",
            "SUPPORTED_LOCAL",
        }:
            raise ResearchError("claim promotion requires CANDIDATE or SUPPORTED_LOCAL")
        promoted = copy.deepcopy(candidate)
        promoted["status"] = "STABLE"
        target = project / "claims" / "stable" / candidate_path.name
        if target.exists():
            raise ResearchError(f"stable claim target already exists: {relative(target)}")
        write_json(target, promoted)

    if args.target != "problem":
        receipt = {
            "promotion_id": (
                f"PROM-{candidate.get('id')}-{args.decision_id}"
            ),
            "target_kind": args.target,
            "target_id": candidate.get("id"),
            "target_version": candidate.get("version"),
            "decision_id": args.decision_id,
            "promoted_at": utc_now(),
            "source_candidate": relative(candidate_path),
            "source_sha256": source_sha256,
            "target": relative(target),
            "target_sha256": sha256_file(target),
        }
        write_json(
            receipt_dir / f"{candidate.get('id')}-{args.decision_id}.json",
            receipt,
        )
    print(f"[OK] promoted by explicit user decision: {relative(target)}")
    return 0


def show_status(args: argparse.Namespace) -> int:
    state = read_state()
    project = resolve_root_path(state["current_project"])
    errors = validate_project(project, strict=False)
    print("通爻研究现场")
    print(f"- 当前项目: {state['current_project']}")
    print(f"- Seed 问题: {state.get('seed_problem')}")
    print(f"- Candidate 问题: {state.get('candidate_problem') or '无'}")
    print(f"- Active 问题: {state.get('active_problem') or '无'}")
    current_problem_locator = (
        state.get("candidate_problem") or state.get("active_problem")
    )
    if isinstance(current_problem_locator, str):
        current_problem_path = resolve_root_path(current_problem_locator)
        current_problem = load_json(current_problem_path)
        bundle_locator = current_problem.get("activation_bundle_ref")
        if isinstance(bundle_locator, str):
            bundle_path = resolve_root_path(bundle_locator)
            bundle_hash = (
                sha256_file(bundle_path)
                if bundle_path.is_file()
                else "MISSING"
            )
            print(
                f"- 问题激活材料: {bundle_locator} "
                f"sha256={bundle_hash}"
            )
    preserved = state.get("preserved_problem_versions", [])
    print(f"- 保留的问题快照: {len(preserved)}")
    for item in preserved:
        if isinstance(item, Mapping):
            print(f"  - {item.get('version')}: {item.get('path')}")
    print(f"- 已验证场景: {state.get('validated_scenario') or '无'}")
    print(f"- Active 机制场景: {state.get('active_mechanism_scenario') or '无'}")
    profiles = state.get("mechanism_profiles", [])
    print(f"- 机制研究档案: {len(profiles)}")
    for profile in profiles:
        print(f"  - {profile}")
    print(f"- 活跃研究线: {len(state.get('active_lines', []))}")
    for line_id in state.get("active_lines", []):
        print(f"  - {line_id}")
    lines_by_problem = state.get("lines_by_problem", {})
    print(f"- 按问题版本隔离的研究线组: {len(lines_by_problem)}")
    for problem_key, group in lines_by_problem.items():
        if not isinstance(group, Mapping):
            continue
        lines = group.get("lines", [])
        print(
            f"  - {problem_key}: status={group.get('status')} "
            f"lines={len(lines)}"
        )
        for line_id in lines:
            print(f"    - {line_id}")
    batches = sorted(
        [path for path in RUNTIME.glob("BATCH-*") if (path / "plan.json").is_file()],
        key=lambda path: path.name,
    )
    if batches:
        latest = load_json(batches[-1] / "plan.json")
        stale = (
            sha256_file(resolve_root_path(latest["problem_path"])) != latest["problem_sha256"]
            or sha256_file(resolve_root_path(latest["scenario_path"])) != latest["scenario_sha256"]
        )
        effective_status = latest["status"]
        if latest["mode"] == "codex" and not (
            (latest.get("external_disclosure") or {}).get("approval_decision_id")
        ):
            effective_status = "BLOCKED_EXTERNAL_AUTHORIZATION"
        print(
            f"- 最近批次: {latest['batch_id']} status={effective_status} "
            f"mode={latest['mode']} stale={str(stale).lower()}"
        )
    else:
        print("- 最近批次: 无")
    print("- 待用户决定:")
    for item in state.get("pending_user_decisions", []):
        print(f"  - {item}")
    print(f"- Runtime: {directory_size(RUNTIME)} / {RUNTIME_LIMIT_BYTES} bytes")
    if errors:
        print("- 治理检查: FAIL")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("- 治理检查: PASS")
    return 0


def validate_command(args: argparse.Namespace) -> int:
    project = project_path(args.project)
    errors = validate_project(project, strict=args.strict)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        print(f"Research governance validation failed with {len(errors)} error(s).")
        return 1
    print(f"[OK] contracts and semantic gates: {relative(project)}")
    print("[OK] seven native lines remain independently addressable")
    print("[OK] bounded mechanism profiles and exact problem-line binding")
    print("[OK] archive pointer and structured decision boundary")
    print("[OK] automated promotion cannot create ACTIVE/STABLE state without a user decision")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate contracts and semantic gates")
    validate.add_argument("--project")
    validate.add_argument("--strict", action="store_true")
    validate.set_defaults(func=validate_command)

    status = sub.add_parser("status", help="show the current research truth surface")
    status.set_defaults(func=show_status)

    batch = sub.add_parser("batch", help="plan, run, or resume an isolated batch")
    batch_sub = batch.add_subparsers(dest="batch_command", required=True)
    plan = batch_sub.add_parser("plan")
    plan.add_argument("--project")
    plan.add_argument(
        "--problem",
        help="problem version (for example v2) or exact contract path",
    )
    plan.add_argument("--scenario")
    plan.add_argument(
        "--line",
        action="append",
        help="ACTIVE line id or path; repeat to select multiple lines",
    )
    plan.add_argument("--mode", choices=["mock", "codex"], default="mock")
    plan.add_argument("--batch-id")
    plan.add_argument("--max-parallel", type=int, default=DEFAULT_MAX_PARALLEL)
    plan.set_defaults(func=plan_batch)
    run = batch_sub.add_parser("run")
    run.add_argument("--plan", required=True)
    run.set_defaults(func=run_batch)
    resume = batch_sub.add_parser("resume")
    resume.add_argument("--batch", required=True)
    resume.set_defaults(func=resume_batch)
    authorize = batch_sub.add_parser("authorize")
    authorize.add_argument("--batch", required=True)
    authorize.add_argument("--decision-id", required=True)
    authorize.set_defaults(func=authorize_batch)
    retry_infra = batch_sub.add_parser("retry-infra")
    retry_infra.add_argument("--batch", required=True)
    retry_infra.set_defaults(func=retry_infra_batch)

    review = sub.add_parser("review", help="prepare or run a blind review")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    prepare = review_sub.add_parser("prepare")
    prepare.add_argument("--batch", required=True)
    prepare.set_defaults(func=prepare_review)
    review_run = review_sub.add_parser("run")
    review_run.add_argument("--batch", required=True)
    review_run.add_argument("--decision-id", required=True)
    review_run.add_argument("--timeout-minutes", type=int, default=30)
    review_run.add_argument("--max-budget-usd", type=float, default=2.0)
    review_run.add_argument("--model", default="sonnet")
    review_run.set_defaults(func=run_review)

    finalize = sub.add_parser("finalize", help="copy validated results into candidate space")
    finalize.add_argument("--batch", required=True)
    finalize.set_defaults(func=finalize_batch)

    promotion = sub.add_parser("promote", help="promote only with an explicit user decision")
    promotion.add_argument("--project")
    promotion.add_argument("--target", choices=["problem", "scenario", "claim"], required=True)
    promotion.add_argument("--candidate", required=True)
    promotion.add_argument("--decision-id", required=True)
    promotion.set_defaults(func=promote)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ResearchError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("[ERROR] interrupted; runtime state was preserved", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
