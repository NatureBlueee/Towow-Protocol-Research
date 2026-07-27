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


def load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ResearchError(f"cannot read JSON {relative(path)}: {exc}") from exc
    if not isinstance(value, dict):
        raise ResearchError(f"expected JSON object: {relative(path)}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


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
    NOW_PATH.write_text(updated, encoding="utf-8")


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


def check_claim_semantics(path: Path, doc: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    if doc.get("status") == "STABLE":
        project = path
        while project != ROOT and project.name != "joint-action-formation":
            project = project.parent
        receipts = project / "promotions"
        if not receipts.exists() or not list(receipts.glob(f"{doc.get('id')}-*.json")):
            errors.append(f"{relative(path)}: STABLE claim has no user-approved promotion receipt")
    return errors


def check_candidate_packets(project: Path) -> List[str]:
    errors: List[str] = []
    candidates = project / "candidates"
    if not candidates.exists():
        return errors
    for packet in sorted(path for path in candidates.iterdir() if path.is_dir()):
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
    return errors


def validate_project(project: Path, strict: bool = False) -> List[str]:
    errors: List[str] = []
    problems = sorted((project / "problem").glob("*.json"))
    scenarios = sorted((project / "scenarios").glob("*.json"))
    lines = sorted((project / "lines").glob("*.json"))
    claims = sorted((project / "claims").rglob("*.json")) if (project / "claims").exists() else []

    if not problems:
        errors.append(f"{relative(project)}: no problem contracts")
    if not scenarios:
        errors.append(f"{relative(project)}: no scenario contracts")
    if not lines:
        errors.append(f"{relative(project)}: no line contracts")

    for path in [*problems, *scenarios, *lines, *claims]:
        doc = load_json(path)
        errors.extend(validate_schema(doc, path))
        errors.extend(check_companion(doc, path))
        if doc.get("kind") == "ClaimCandidate":
            errors.extend(check_claim_semantics(path, doc))

    errors.extend(check_problem_scenario_line_semantics(project, problems, scenarios, lines))
    errors.extend(check_candidate_packets(project))

    try:
        state = read_state()
        for key in ("current_project", "seed_problem", "validated_scenario", "canonical_source"):
            locator = state.get(key)
            if locator and not resolve_root_path(locator).exists():
                errors.append(f"NOW state {key} points to missing path: {locator}")
        active_problem = state.get("active_problem")
        if active_problem:
            active_doc = load_json(resolve_root_path(active_problem))
            if active_doc.get("status") != "ACTIVE":
                errors.append("NOW active_problem does not point to an ACTIVE problem")
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
    return [
        *PROTECTED_PATHS,
        *sorted((project / "problem").glob("*.json")),
        *sorted((project / "scenarios").glob("*.json")),
    ]


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


def make_batch_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"BATCH-{stamp}-{uuid.uuid4().hex[:6].upper()}"


def select_problem(project: Path, state: Mapping[str, Any]) -> Tuple[Path, Dict[str, Any]]:
    locator = state.get("active_problem") or state.get("seed_problem")
    if not isinstance(locator, str):
        raise ResearchError("NOW does not identify a seed or active problem")
    path = resolve_root_path(locator)
    if project not in path.parents:
        raise ResearchError("NOW problem does not belong to selected project")
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
            if len(candidates) != 1:
                raise ResearchError(f"cannot resolve scenario: {value}")
            path = candidates[0]
    else:
        locator = state.get("active_mechanism_scenario") or state.get("validated_scenario")
        if not isinstance(locator, str):
            raise ResearchError("NOW does not identify a scenario")
        path = resolve_root_path(locator)
    return path, load_json(path)


def plan_batch(args: argparse.Namespace) -> int:
    project = project_path(args.project)
    errors = validate_project(project, strict=True)
    if errors:
        raise ResearchError("project validation failed:\n- " + "\n- ".join(errors))
    state = read_state()
    problem_path, problem = select_problem(project, state)
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

    if scenario["scenario_class"] == "REAL":
        decision_id = scenario["activation"]["approval_decision_id"]
        if not decision_allows(decision_id, "ACTIVATE_REAL_SCENARIO", scenario):
            raise ResearchError("REAL scenario has no matching user activation decision")

    if args.mode not in {"mock", "codex"}:
        raise ResearchError(f"unsupported mode: {args.mode}")
    max_parallel = max(1, min(int(args.max_parallel), DEFAULT_MAX_PARALLEL))
    assert_runtime_budget(BATCH_LIMIT_BYTES)

    line_paths = sorted((project / "lines").glob("*.json"))
    active_lines = [(path, load_json(path)) for path in line_paths if load_json(path).get("status") == "ACTIVE"]
    if not active_lines:
        raise ResearchError("no ACTIVE research lines")

    batch_id = args.batch_id or make_batch_id()
    if not re.fullmatch(r"BATCH-[A-Z0-9-]+", batch_id):
        raise ResearchError("batch id must match BATCH-[A-Z0-9-]+")
    batch_dir = RUNTIME / batch_id
    if batch_dir.exists():
        raise ResearchError(f"batch already exists: {batch_id}")
    batch_dir.mkdir(parents=True)

    protected = hash_paths(protected_paths(project))
    plan: Dict[str, Any] = {
        "schema_version": "1.0",
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
        input_components = {
            relative(problem_path): sha256_file(problem_path),
            relative(scenario_path): sha256_file(scenario_path),
            relative(line_path): sha256_file(line_path),
            **{item["locator"]: item["sha256"] for item in sources},
        }
        input_hash = json_hash(input_components)
        bundle = {
            "batch_id": batch_id,
            "run_id": run_id,
            "problem": problem,
            "scenario": scenario,
            "line": line,
            "input_components": input_components,
            "input_hash": input_hash,
            "sources": sources,
        }
        write_json(run_dir / "input.json", bundle)
        disclosure_payloads.append(
            {
                "run_id": run_id,
                "payload": relative(run_dir / "input.json"),
                "sha256": sha256_file(run_dir / "input.json"),
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
            "source_allowlist": line["source_allowlist"],
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
            }
        )
    fingerprint_input = {
        "batch_id": batch_id,
        "mode": args.mode,
        "problem_sha256": plan["problem_sha256"],
        "scenario_sha256": plan["scenario_sha256"],
        "run_input_hashes": [run["input_hash"] for run in plan["runs"]],
    }
    plan["plan_fingerprint"] = json_hash(fingerprint_input)
    if args.mode == "codex":
        disclosure_core = {
            "schema_version": "1.0",
            "kind": "ExternalDisclosureManifest",
            "batch_id": batch_id,
            "destination": "OpenAI Codex",
            "classification": "NON_PUBLIC_RESEARCH",
            "purpose": "Seven isolated Problem v0 definition reviews",
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
    content = MOCK_CONTENT[line["id"]]
    native_source = next(
        item["locator"]
        for item in bundle["sources"]
        if "/native_lines/" in item["locator"]
    )
    return {
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
        "applicability": "仅适用于 Problem v0 的本地档案问题定义批次。",
        "cannot_support": bundle["scenario"]["cannot_support"],
        "candidate_claims": [content["claim"]],
        "new_discriminators": [content["discriminator"]],
        "cost": {"elapsed_seconds": 0, "output_bytes": 0}
    }


def build_codex_prompt(bundle: Mapping[str, Any]) -> str:
    return (
        "Read WORKER_POLICY.md and input.json in the current directory. "
        "You are one isolated research line. Use only the source text embedded in input.json. "
        "Do not inspect the workspace, call tools, browse, spawn sub-agents, or infer user approval. "
        "Attack Problem v0 from this line's native capability and strongest alternative. "
        "Return a ResearchResult JSON matching the supplied schema. "
        "Every source_statement.source_locator must exactly match one source_allowlist entry. "
        "Preserve negative and inconclusive results. Do not claim real Effect, Adoption, Acceptance, "
        "human authorization, or general validity."
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
    return errors


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
            input=build_codex_prompt(bundle),
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
        raise ResearchError(f"codex exited {proc.returncode}")
    result = load_json(output_path)
    return result, proc.returncode, events


def current_components(run: Mapping[str, Any]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for locator in run["input_components"]:
        path = resolve_root_path(locator)
        values[locator] = sha256_file(path) if path.is_file() else "MISSING"
    return values


def run_one(plan: Mapping[str, Any], run: Mapping[str, Any]) -> Tuple[str, str]:
    run_dir = resolve_root_path(run["run_dir"])
    bundle = load_json(run_dir / "input.json")
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path)
    if bundle.get("input_hash") != run.get("input_hash") or json_hash(
        run["input_components"]
    ) != run.get("input_hash"):
        manifest["status"] = "POLICY_VIOLATION"
        manifest["finished_at"] = utc_now()
        write_json(manifest_path, manifest)
        return run["line_id"], "POLICY_VIOLATION"
    if current_components(run) != run["input_components"]:
        manifest["status"] = "STALE_FOR_CURRENT"
        manifest["finished_at"] = utc_now()
        write_json(manifest_path, manifest)
        return run["line_id"], "STALE_FOR_CURRENT"
    result_path = run_dir / "result.json"
    if manifest["status"] == "COMPLETED" and result_path.is_file():
        if sha256_file(result_path) == manifest.get("result_sha256"):
            return run["line_id"], "COMPLETED"

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
            else:
                result, exit_code, events = run_codex(
                    run_dir,
                    bundle,
                    timeout=int(budget["max_minutes"]) * 60,
                )
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
            manifest["cost"] = {
                "elapsed_seconds": round(elapsed, 3),
                "output_bytes": result_path.stat().st_size + len(events.encode("utf-8")),
            }
            write_json(manifest_path, manifest)
            return run["line_id"], "COMPLETED"
        except (ResearchError, OSError, json.JSONDecodeError) as exc:
            elapsed = time.monotonic() - started
            (run_dir / f"attempt-{manifest['attempt']}-error.txt").write_text(
                str(exc) + "\n",
                encoding="utf-8",
            )
            manifest["status"] = "FAILED"
            manifest["finished_at"] = utc_now()
            manifest["exit_code"] = 1
            manifest["cost"] = {
                "elapsed_seconds": round(elapsed, 3),
                "output_bytes": directory_size(run_dir),
            }
            write_json(manifest_path, manifest)
    return run["line_id"], "FAILED"


def load_plan(path: Path) -> Dict[str, Any]:
    plan = load_json(path)
    if plan.get("batch_id") != path.parent.name:
        raise ResearchError("plan batch_id does not match runtime directory")
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
    for payload in disclosure.get("payloads", []):
        path = resolve_root_path(payload["payload"])
        if not path.is_file():
            raise ResearchError(f"disclosed payload is missing: {payload['payload']}")
        if path.stat().st_size != payload["size_bytes"] or sha256_file(path) != payload["sha256"]:
            raise ResearchError(f"disclosed payload changed: {payload['payload']}")
    return disclosure


def run_batch(args: argparse.Namespace) -> int:
    plan_path = resolve_root_path(args.plan)
    plan = load_plan(plan_path)
    project = resolve_root_path(plan["project"])
    if plan["mode"] == "codex":
        verify_external_disclosure(plan)
        disclosure = plan.get("external_disclosure") or {}
        decision_id = disclosure.get("approval_decision_id")
        target = {"id": plan["batch_id"], "version": plan.get("plan_fingerprint")}
        if not decision_allows(decision_id, "SEND_BATCH_TO_CODEX", target):
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
    if not decision_allows(args.decision_id, "SEND_BATCH_TO_CODEX", target):
        raise ResearchError(
            f"user decision {args.decision_id} does not authorize "
            f"SEND_BATCH_TO_CODEX for {target['id']}@{target['version']}"
        )
    disclosure = verify_external_disclosure(plan)
    disclosure_path = resolve_root_path(plan["external_disclosure"]["manifest"])
    disclosure["approval_decision_id"] = args.decision_id
    plan["external_disclosure"]["approval_decision_id"] = args.decision_id
    write_json(disclosure_path, disclosure)
    write_json(plan_path, plan)
    print(
        f"[OK] authorized exact Codex payload: {target['id']}@{target['version']} "
        f"via {args.decision_id}"
    )
    return 0


def completed_results(plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for run in plan["runs"]:
        run_dir = resolve_root_path(run["run_dir"])
        manifest = load_json(run_dir / "manifest.json")
        if manifest["status"] != "COMPLETED":
            raise ResearchError(f"run is not complete: {run['line_id']} ({manifest['status']})")
        result_path = run_dir / "result.json"
        if not result_path.is_file() or sha256_file(result_path) != manifest["result_sha256"]:
            raise ResearchError(f"result hash mismatch: {run['line_id']}")
        bundle = load_json(run_dir / "input.json")
        result = load_json(result_path)
        errors = validate_result_semantics(result, bundle)
        if errors:
            raise ResearchError("; ".join(errors))
        results.append(result)
    return results


def prepare_review(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan = load_plan(batch_dir / "plan.json")
    results = completed_results(plan)
    problem = load_json(resolve_root_path(plan["problem_path"]))
    scenario = load_json(resolve_root_path(plan["scenario_path"]))
    anonymized: List[Dict[str, Any]] = []
    for index, result in enumerate(sorted(results, key=lambda item: item["line_id"]), 1):
        anonymous_sources = [
            {
                "statement": statement["statement"],
                "source_locator": f"SRC-R{index:02d}-{source_index:02d}",
                "source_range": statement["source_range"],
            }
            for source_index, statement in enumerate(result["source_statements"], 1)
        ]
        anonymized.append(
            {
                "anonymous_return_id": f"R{index:02d}",
                "direct_observations": result["direct_observations"],
                "source_statements": anonymous_sources,
                "inferences": result["inferences"],
                "design_proposals": result["design_proposals"],
                "negative_results": result["negative_results"],
                "alternative_explanations": result["alternative_explanations"],
                "candidate_claims": result["candidate_claims"],
                "new_discriminators": result["new_discriminators"],
                "applicability": result["applicability"],
                "cannot_support": result["cannot_support"],
            }
        )
    bundle = {
        "schema_version": "1.0",
        "kind": "BlindReviewBundle",
        "batch_id": plan["batch_id"],
        "problem": {
            "id": problem["id"],
            "version": problem["version"],
            "status": problem["status"],
            "question": problem["question"],
            "invariants": problem["invariants"],
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
        "review_questions": [
            "What is the strongest counterargument to the proposed problem frame?",
            "Which inference is not supported by the supplied observations?",
            "Which minority distinction would be erased by premature synthesis?",
            "What evidence or scenario is still required before activating Problem v1?",
            "Could a strong central researcher or existing institution explain the same results at lower cost?"
        ],
        "excluded": [
            "expected answer",
            "candidate synthesis",
            "formal line identities",
            "non-allowlisted archive material",
            "private participant data"
        ]
    }
    review_dir = batch_dir / "review"
    review_dir.mkdir(exist_ok=True)
    write_json(review_dir / "review-bundle.json", bundle)
    (review_dir / "REVIEW_POLICY.md").write_text(
        "# Blind review policy\n\n"
        "Attack the problem framing. Do not infer user approval or real-world validity. "
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
        "purpose": "Blind attack on candidate Problem v1 framing",
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


def run_review(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    review_dir = batch_dir / "review"
    bundle_path = review_dir / "review-bundle.json"
    if not bundle_path.is_file():
        prepare_review(argparse.Namespace(batch=args.batch))
    disclosure_path = review_dir / "review-disclosure.json"
    disclosure = load_json(disclosure_path)
    review_target = {"id": args.batch, "version": disclosure["payload_sha256"]}
    if not decision_allows(args.decision_id, "SEND_BLIND_REVIEW_TO_CLAUDE", review_target):
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
    schema = schema_for("BlindReview")
    prompt = (
        (review_dir / "REVIEW_POLICY.md").read_text(encoding="utf-8")
        + "\n\nReview this isolated bundle:\n"
        + json.dumps(bundle, ensure_ascii=False)
    )
    command = [
        executable,
        "--safe-mode",
        "--no-session-persistence",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
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
    (review_dir / "claude-raw.json").write_text(
        (proc.stdout or "") + (proc.stderr or ""),
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise ResearchError(f"Claude blind review exited {proc.returncode}")
    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ResearchError("Claude did not return JSON output") from exc
    review = envelope.get("structured_output")
    if review is None:
        result_value = envelope.get("result")
        if isinstance(result_value, str):
            try:
                review = json.loads(result_value)
            except json.JSONDecodeError:
                review = None
    if not isinstance(review, dict):
        raise ResearchError("Claude JSON envelope has no structured review")
    errors = validate_schema(review, review_dir / "blind-review.json")
    if errors:
        raise ResearchError("; ".join(errors))
    write_json(review_dir / "blind-review.json", review)
    print(f"[OK] Claude blind review completed: {relative(review_dir / 'blind-review.json')}")
    return 0


def make_divergence_markdown(results: Sequence[Mapping[str, Any]], batch_id: str) -> str:
    lines = [
        f"# 七线分歧矩阵：{batch_id}",
        "",
        "本文件逐线保留结果，不按票数合并。完全相同的句子只表示文本重合，不构成独立证据。",
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
        lines.append("- 无。该结果不表示七线没有交集，只表示尚未进行会抹平差异的语义归并。")
    lines.extend(
        [
            "",
            "## 晋升边界",
            "",
            "- 本矩阵是候选导航，不是 Problem v1。",
            "- 少数线、拒绝、Unknown、中心方案更好和无净增值不得因综合而删除。",
            "- 用户必须单独决定激活、重写、拒绝或继续保持多个候选。",
            "",
        ]
    )
    return "\n".join(lines)


def finalize_batch(args: argparse.Namespace) -> int:
    batch_dir = RUNTIME / args.batch
    plan = load_plan(batch_dir / "plan.json")
    results = completed_results(plan)
    if len(results) != len(plan["runs"]):
        raise ResearchError("not all planned runs returned")
    project = resolve_root_path(plan["project"])
    if hash_paths(protected_paths(project)) != plan["protected_hashes"]:
        for run in plan["runs"]:
            manifest_path = resolve_root_path(run["run_dir"]) / "manifest.json"
            manifest = load_json(manifest_path)
            manifest["status"] = "STALE_FOR_CURRENT"
            write_json(manifest_path, manifest)
        raise ResearchError("canonical inputs changed; results were preserved but marked stale")

    target = project / "candidates" / plan["batch_id"]
    if target.exists():
        manifest_path = target / "finalization-manifest.json"
        if manifest_path.is_file():
            print(f"[OK] candidate already finalized: {relative(target)}")
            return 0
        raise ResearchError(f"candidate directory exists without manifest: {relative(target)}")
    target.mkdir(parents=True)
    result_hashes: Dict[str, str] = {}
    for result in results:
        path = target / f"{result['line_id']}.json"
        write_json(path, result)
        result_hashes[path.name] = sha256_file(path)
    matrix_path = target / "divergence-matrix.md"
    matrix_path.write_text(
        make_divergence_markdown(results, plan["batch_id"]),
        encoding="utf-8",
    )
    result_hashes[matrix_path.name] = sha256_file(matrix_path)
    manifest = {
        "schema_version": "1.0",
        "kind": "CandidateReturnPacket",
        "batch_id": plan["batch_id"],
        "finalized_at": utc_now(),
        "problem_ref": f"{load_json(resolve_root_path(plan['problem_path']))['id']}@"
        f"{load_json(resolve_root_path(plan['problem_path']))['version']}",
        "scenario_ref": f"{load_json(resolve_root_path(plan['scenario_path']))['id']}@"
        f"{load_json(resolve_root_path(plan['scenario_path']))['version']}",
        "status": "CANDIDATE",
        "result_hashes": result_hashes,
        "promotion_authority": "USER",
        "cannot_support": [
            "Problem v1 activation",
            "stable claims",
            "real Effect, Domain Adoption, Acceptance, or net value"
        ]
    }
    write_json(target / "finalization-manifest.json", manifest)
    print(f"[OK] finalized candidate packet without promotion: {relative(target)}")
    return 0


def promote(args: argparse.Namespace) -> int:
    candidate_path = resolve_root_path(args.candidate)
    candidate = load_json(candidate_path)
    action_by_target = {
        "problem": "ACTIVATE_PROBLEM",
        "scenario": "ACTIVATE_REAL_SCENARIO"
        if candidate.get("scenario_class") == "REAL"
        else "ACTIVATE_SCENARIO",
        "claim": "PROMOTE_STABLE_CLAIM",
    }
    action = action_by_target[args.target]
    if not decision_allows(args.decision_id, action, candidate):
        raise ResearchError(f"user decision {args.decision_id} does not authorize {action}")
    project = project_path(args.project)
    receipt_dir = project / "promotions"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    if args.target == "problem":
        if candidate.get("kind") != "ProblemContract" or candidate.get("status") != "CANDIDATE":
            raise ResearchError("problem promotion requires a CANDIDATE ProblemContract")
        promoted = copy.deepcopy(candidate)
        promoted["status"] = "ACTIVE"
        target = project / "problem" / f"{promoted['version']}.json"
        if target.exists():
            raise ResearchError(f"active problem target already exists: {relative(target)}")
        write_json(target, promoted)
        state = read_state()
        state["active_problem"] = relative(target)
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
        target = project / "scenarios" / candidate_path.name
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

    receipt = {
        "promotion_id": f"PROM-{candidate.get('id')}-{args.decision_id}",
        "target_kind": args.target,
        "target_id": candidate.get("id"),
        "target_version": candidate.get("version"),
        "decision_id": args.decision_id,
        "promoted_at": utc_now(),
        "source_candidate": relative(candidate_path),
        "source_sha256": sha256_file(candidate_path),
        "target": relative(target),
        "target_sha256": sha256_file(target),
    }
    write_json(receipt_dir / f"{candidate.get('id')}-{args.decision_id}.json", receipt)
    print(f"[OK] promoted by explicit user decision: {relative(target)}")
    return 0


def show_status(args: argparse.Namespace) -> int:
    state = read_state()
    project = resolve_root_path(state["current_project"])
    errors = validate_project(project, strict=False)
    print("通爻研究现场")
    print(f"- 当前项目: {state['current_project']}")
    print(f"- Seed 问题: {state.get('seed_problem')}")
    print(f"- Active 问题: {state.get('active_problem') or '无'}")
    print(f"- 已验证场景: {state.get('validated_scenario') or '无'}")
    print(f"- Active 机制场景: {state.get('active_mechanism_scenario') or '无'}")
    print(f"- 活跃研究线: {len(state.get('active_lines', []))}")
    for line_id in state.get("active_lines", []):
        print(f"  - {line_id}")
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
    plan.add_argument("--scenario")
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
