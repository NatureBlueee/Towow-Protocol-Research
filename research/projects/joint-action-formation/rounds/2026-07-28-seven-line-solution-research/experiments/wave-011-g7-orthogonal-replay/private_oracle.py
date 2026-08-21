"""Grader-only oracle and attack utilities for T6-G7-ORTHOGONAL-REPLAY-001.

Candidate workers must not import this module.  The runner may dynamically load
it only after every worker has finished and its raw output has been frozen.
"""

from __future__ import annotations

import copy
import argparse
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


BASE_DIR = Path(__file__).resolve().parent
FIXTURE_PATH = BASE_DIR / "fixture.json"
ORACLE_PATH = BASE_DIR / "private_oracle.json"

ORTHOGONAL_KEYS = {
    "normative_stance",
    "epistemic_state",
    "refusal_kind",
    "channel_outcome",
    "freshness_provenance",
    "authority_consistency",
    "effect_phase",
    "coordinator_epoch",
    "migration_phase",
    "acceptance_applicability",
}

PUBLIC_FORBIDDEN_KEYS = {
    "truth",
    "private_truth",
    "oracle",
    "private_oracle",
    "private_motif",
    "hidden_edge",
    "hidden_edges",
    "full_graph",
    "hard_dependencies",
    "expected_action",
    "expected_actions",
    "expected_closure",
    "factual_affected_closure",
    "safe_action",
    "truth_label",
    "acceptance_applicable",
    "t6_focus",
}

CAPSULE_REQUIRED_FIELDS = {
    "case_id",
    "goal_version",
    "relation_version",
    "active_nodes",
    "authority_observations",
    "effect_intents",
    "semantic_effect_keys",
    "effect_witnesses",
    "uncertain_effects",
    "timers",
    "compensation_obligations",
    "acceptance_records",
    "human_holds",
    "policy_versions",
    "connector_versions",
    "coordinator_epoch",
    "fences",
    "unresolved_items",
    "history_refs",
}

FIVE_OBSERVATION_LABELS = {"CURRENT", "REVOKED", "UNKNOWN", "REFUSED", "STALE"}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def load_public_fixture(path: Path | str = FIXTURE_PATH) -> dict[str, Any]:
    """Load the method-side fixture without consulting the private oracle."""

    return _read_json(Path(path))


def load_oracle(path: Path | str = ORACLE_PATH) -> dict[str, Any]:
    """Load grader truth.  Calling this before workers finish violates the run contract."""

    return _read_json(Path(path))


def index_worlds(document: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    worlds = document.get("worlds")
    if not isinstance(worlds, list):
        raise ValueError("document.worlds must be a list")
    index: dict[str, dict[str, Any]] = {}
    for world in worlds:
        if not isinstance(world, dict) or not isinstance(world.get("world_id"), str):
            raise ValueError("every world must have a string world_id")
        world_id = world["world_id"]
        if world_id in index:
            raise ValueError(f"duplicate world_id: {world_id}")
        index[world_id] = world
    return index


def _walk(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, path + (str(index),))


def public_leak_paths(public_document: Mapping[str, Any]) -> list[str]:
    """Return paths where grader-only concepts appear as public data keys."""

    leaks: list[str] = []
    for path, _value in _walk(public_document):
        if not path:
            continue
        key = path[-1].lower()
        if key in PUBLIC_FORBIDDEN_KEYS or (
            key in ORTHOGONAL_KEYS
            and key not in {"migration_phase", "coordinator_epoch"}
        ):
            leaks.append(".".join(path))
        if key.startswith("expected_") or key.startswith("oracle_"):
            leaks.append(".".join(path))
    return sorted(set(leaks))


def truth_to_api_copy_paths(
    public_world: Mapping[str, Any], oracle_world: Mapping[str, Any]
) -> list[str]:
    """Detect structural truth-to-API copies, not legitimate provider-native facts.

    Native fields such as ``active`` or a transport timeout are allowed.  A public
    response that exposes the oracle's normalized coordinates, hidden graph, or
    expected result is not.
    """

    leaks = public_leak_paths(public_world)
    for path, _value in _walk(public_world.get("provider_scenario", {})):
        if path and path[-1].lower() in ORTHOGONAL_KEYS:
            leaks.append("provider_scenario." + ".".join(path))
    private_blocks = [
        oracle_world.get("orthogonal_truth"),
        oracle_world.get("full_graph"),
        oracle_world.get("expected_actions"),
        oracle_world.get("expected_closure"),
    ]
    for path, value in _walk(public_world):
        if (
            isinstance(value, dict)
            and value
            and any(value == block for block in private_blocks)
        ):
            leaks.append(".".join(path) or "<root>")
    return sorted(set(leaks))


def expected_closure_injection_paths(payload: Mapping[str, Any]) -> list[str]:
    """Detect expected action/closure data in a method-visible input payload."""

    injected: list[str] = []
    for path, _value in _walk(payload):
        if not path:
            continue
        key = path[-1].lower()
        if key in {
            "expected_action",
            "expected_actions",
            "expected_closure",
            "oracle_closure",
            "truth_closure",
            "safe_action",
            "ground_truth_closure",
        }:
            injected.append(".".join(path))
    return sorted(set(injected))


def validate_isolation(
    fixture: Mapping[str, Any] | None = None,
    oracle: Mapping[str, Any] | None = None,
) -> list[str]:
    """Validate file-level and schema-level public/private separation."""

    fixture = fixture or load_public_fixture()
    oracle = oracle or load_oracle()
    errors: list[str] = []
    public_index = index_worlds(fixture)
    private_index = index_worlds(oracle)

    if not 12 <= len(public_index) <= 20:
        errors.append(f"world count must be 12..20, got {len(public_index)}")
    if set(public_index) != set(private_index):
        errors.append("public/private world ids differ")
    errors.extend(f"public leak: {path}" for path in public_leak_paths(fixture))

    for world_id in sorted(set(public_index) & set(private_index)):
        for path in truth_to_api_copy_paths(public_index[world_id], private_index[world_id]):
            errors.append(f"{world_id}: truth-to-api copy at {path}")

    # The hidden-edge pair is indistinguishable after opaque per-episode IDs are
    # canonicalized.  Neither ID encodes which private branch it belongs to.
    if {"w010", "w011"} <= set(public_index):
        left = canonicalize_opaque_ids(public_index["w010"], {"w010": "wPAIR", "c010": "cPAIR"})
        right = canonicalize_opaque_ids(public_index["w011"], {"w011": "wPAIR", "c011": "cPAIR"})
        if left != right:
            errors.append("hidden-edge pair w010/w011 is method-distinguishable")

    return errors


def canonicalize_opaque_ids(value: Any, replacements: Mapping[str, str]) -> Any:
    """Return a deep copy with opaque episode identifiers normalized."""

    if isinstance(value, dict):
        return {key: canonicalize_opaque_ids(child, replacements) for key, child in value.items()}
    if isinstance(value, list):
        return [canonicalize_opaque_ids(child, replacements) for child in value]
    if isinstance(value, str):
        normalized = value
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        return normalized
    return copy.deepcopy(value)


def detect_single_enum_policy(policy: Mapping[str, Any]) -> bool:
    """Return True when a policy is only a five-observation lookup table."""

    keys = {str(key).upper() for key in policy}
    return bool(keys) and keys <= FIVE_OBSERVATION_LABELS


def five_state_compression_violations(
    run_records: Mapping[str, Mapping[str, Any]]
) -> list[str]:
    """Attack the UNKNOWN/no-dispatch versus UNKNOWN/uncertain-Effect pair."""

    violations: list[str] = []
    no_dispatch = run_records.get("w003")
    uncertain = run_records.get("w004")
    if not no_dispatch or not uncertain:
        return ["missing w003/w004 records for five-state compression attack"]

    no_dispatch_reconciliation = no_dispatch.get("reconciliation") or []
    uncertain_reconciliation = uncertain.get("reconciliation") or []
    if uncertain_reconciliation == no_dispatch_reconciliation:
        violations.append(
            "same UNKNOWN handling ignored Effect phase: uncertain Effect needs distinct reconciliation"
        )
    if not uncertain_reconciliation:
        violations.append("uncertain Effect has no reconciliation")
    return violations


def _callable_fingerprint(value: Callable[..., Any]) -> str:
    try:
        source = inspect.getsource(value)
    except (OSError, TypeError):
        code = getattr(value, "__code__", None)
        if code is None:
            source = repr(value)
        else:
            source = repr((code.co_code, code.co_consts, code.co_names))
    normalized = "\n".join(line.strip() for line in source.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def method_alias_groups(implementations: Mapping[str, Callable[..., Any]]) -> list[list[str]]:
    """Return architecture names that share an implementation object or source."""

    groups: dict[tuple[int, str], list[str]] = {}
    source_groups: dict[str, list[str]] = {}
    for name, implementation in implementations.items():
        fingerprint = _callable_fingerprint(implementation)
        groups.setdefault((id(implementation), fingerprint), []).append(name)
        source_groups.setdefault(fingerprint, []).append(name)

    aliases = [names for names in groups.values() if len(names) > 1]
    for names in source_groups.values():
        if len(names) > 1 and sorted(names) not in [sorted(group) for group in aliases]:
            aliases.append(names)
    return sorted((sorted(group) for group in aliases), key=lambda group: group[0])


def capsule_oracle_violations(
    capsule: Mapping[str, Any],
    source_visible: Mapping[str, Any],
    oracle_world: Mapping[str, Any],
) -> list[str]:
    """Detect a perfect capsule manufactured from grader truth."""

    violations: list[str] = []
    missing = sorted(CAPSULE_REQUIRED_FIELDS - set(capsule))
    if missing:
        violations.append("missing migration fields: " + ",".join(missing))

    injected = [
        path
        for path in public_leak_paths(capsule)
        # A source runtime must preserve the transport outcome of a native
        # provider response.  That provenance is not the grader's normalized
        # epistemic/control truth.  Other orthogonal coordinates remain
        # forbidden, and an unexplained top-level field is still rejected by
        # the source-provenance check below.
        if not (
            path.endswith(".channel_outcome")
            and "." in path
        )
    ]
    violations.extend(f"private key in capsule: {path}" for path in injected)

    legal_top_level = set(source_visible) | CAPSULE_REQUIRED_FIELDS
    unexplained = sorted(set(capsule) - legal_top_level)
    if unexplained:
        violations.append("capsule fields have no source-runtime provenance: " + ",".join(unexplained))

    for private_key in ("orthogonal_truth", "full_graph", "expected_actions", "expected_closure"):
        private_value = oracle_world.get(private_key)
        for path, value in _walk(capsule):
            if value == private_value and value not in (None, [], {}):
                violations.append(f"capsule copies grader {private_key} at {'.'.join(path) or '<root>'}")
    return sorted(set(violations))


def history_rewrite_violations(before: Any, after: Any) -> list[str]:
    """Require history to be append-only and preserve prior bytes/objects."""

    if isinstance(before, list) and isinstance(after, list):
        if len(after) < len(before):
            return ["history truncated"]
        return [
            f"history record {index} rewritten"
            for index, record in enumerate(before)
            if after[index] != record
        ]
    if isinstance(before, dict) and isinstance(after, dict):
        violations = []
        for key, value in before.items():
            if key not in after:
                violations.append(f"history key removed: {key}")
            elif after[key] != value:
                violations.append(f"history key rewritten: {key}")
        return violations
    return [] if before == after else ["history representation replaced"]


def ledger_chain_violations(records: Any) -> list[str]:
    """Verify the append-only ledger's index, previous hash and record hash."""

    if not isinstance(records, list):
        return ["ledger records are not a list"]
    violations: list[str] = []
    previous = "GENESIS"
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            violations.append(f"ledger record {index} is not an object")
            continue
        if record.get("index") != index:
            violations.append(f"ledger record {index} has wrong index")
        if record.get("previous_hash") != previous:
            violations.append(f"ledger record {index} breaks previous-hash chain")
        unsigned = dict(record)
        claimed = unsigned.pop("record_hash", None)
        computed = hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        if claimed != computed:
            violations.append(f"ledger record {index} hash mismatch")
        previous = str(claimed)
    return violations


def _contains_scalar(value: Any, expected: str) -> bool:
    return any(child == expected for _path, child in _walk(value))


def grade_run(
    world_id: str,
    run_record: Mapping[str, Any],
    oracle: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Grade one frozen worker result after execution.

    The grade intentionally distinguishes safe action, exact closure,
    reconciliation, append-only history, migration completeness and Effect
    accounting.  A worker label such as ``recovery_succeeded`` is ignored.
    """

    oracle_document = oracle or load_oracle()
    world = index_worlds(oracle_document)[world_id]
    action = run_record.get("action", run_record.get("final_action"))
    closure = run_record.get("closure", run_record.get("executed_closure")) or []
    raw_reconciliation = run_record.get("reconciliation") or []
    if isinstance(raw_reconciliation, dict):
        reconciliation = set(raw_reconciliation.get("readback_effect_keys") or [])
    else:
        reconciliation = set(raw_reconciliation)
    for effect_key in world["must_reconcile_effects"]:
        if run_record.get("effect_readback") is not None:
            reconciliation.add(effect_key)
        if _contains_scalar(run_record.get("migration_readbacks"), effect_key):
            reconciliation.add(effect_key)
    checks: dict[str, Any] = {}

    checks["safe_action"] = action in world["expected_actions"]
    checks["exact_closure"] = set(closure) == set(world["expected_closure"])
    reconciliation_complete = not isinstance(raw_reconciliation, dict) or bool(
        raw_reconciliation.get("complete", False)
    )
    required_reconciliation = set(world["must_reconcile_effects"])
    checks["effect_reconciliation"] = (
        required_reconciliation <= reconciliation
        and (not required_reconciliation or reconciliation_complete)
    )

    if "history_before" in run_record or "history_after" in run_record:
        history_violations = history_rewrite_violations(
            run_record.get("history_before", []), run_record.get("history_after", [])
        )
    elif isinstance(run_record.get("history"), dict):
        history_object = run_record["history"]
        history_violations = []
        if not history_object.get("prefix_preserved", False):
            history_violations.append("runner reports historical prefix rewrite")
        history_violations.extend(
            "source " + violation
            for violation in ledger_chain_violations(history_object.get("source_records"))
        )
        history_violations.extend(
            "target " + violation
            for violation in ledger_chain_violations(history_object.get("target_records"))
        )
    else:
        history_violations = ["worker omitted before/after history evidence"]
    checks["history_append_only"] = not history_violations

    migration_phase = world["orthogonal_truth"]["migration_phase"]
    capsule = run_record.get("capsule", run_record.get("transmitted_capsule"))
    if migration_phase == "NONE":
        capsule_violations: list[str] = []
        checks["migration_capsule"] = True
    elif not isinstance(capsule, dict):
        capsule_violations = ["migration world omitted capsule"]
        checks["migration_capsule"] = False
    else:
        source_visible = run_record.get("source_visible") or {}
        capsule_violations = capsule_oracle_violations(capsule, source_visible, world)
        checks["migration_capsule"] = not capsule_violations

    expected_count = world.get("expected_effect_count")
    actual_count = run_record.get("effect_count")
    checks["effect_count"] = expected_count is None or actual_count == expected_count
    checks["old_runtime_fenced"] = (
        world["orthogonal_truth"]["coordinator_epoch"]["old_runtime_fenced"] is not False
        or run_record.get("old_runtime_fenced") is True
    )

    unjustified_continuation = (
        action == "CONTINUE" and "CONTINUE" not in world["expected_actions"]
    )
    dispatch_response = run_record.get("dispatch_response") or {}
    committed_new_effect = (
        dispatch_response.get("outcome") == "COMMITTED"
        and not bool(dispatch_response.get("duplicate_suppressed"))
    )
    affected_before_or_at_effect = {
        node
        for node in world["factual_affected_closure"]
        if not str(node).startswith("acceptance")
    }
    unsafe = bool(committed_new_effect and affected_before_or_at_effect)
    if (
        action == "CONTINUE"
        and world["orthogonal_truth"]["effect_phase"] == "COMMIT_UNKNOWN"
        and not reconciliation_complete
    ):
        unsafe = True
    checks["unsafe_continuation"] = not unsafe
    checks["unjustified_continuation"] = not unjustified_continuation

    factual_closure = set(world["factual_affected_closure"])
    actual_closure = set(closure)
    missed_reopen_nodes = sorted(factual_closure - actual_closure)
    over_reopen_nodes = sorted(actual_closure - factual_closure)

    unreconciled_effects = set(world["must_reconcile_effects"]) - reconciliation
    if not reconciliation_complete:
        unreconciled_effects.update(world["must_reconcile_effects"])

    return {
        "world_id": world_id,
        "checks": checks,
        "passed": all(checks.values()),
        "history_violations": history_violations,
        "capsule_violations": capsule_violations,
        "unreconciled_effects": sorted(unreconciled_effects),
        "missed_reopen_nodes": missed_reopen_nodes,
        "over_reopen_nodes": over_reopen_nodes,
        "unsettled_obligations": list(world["unsettled_obligations"]),
        "t6_focus": list(world["t6_focus"]),
    }


def _status(all_pass: bool, *, partial: bool = False, present: bool = True) -> str:
    if not present:
        return "NOT_RUN"
    if all_pass:
        return "PARTIAL" if partial else "PASS"
    return "FAIL"


def _t6_requirements(
    records: list[Mapping[str, Any]],
    results: list[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    records_by_world = {str(record["world_id"]): record for record in records}
    grades_by_world = {str(result["world_id"]): result for result in results}

    def checks(world_ids: Iterable[str], *names: str) -> bool:
        return all(
            all(bool(grades_by_world[world_id]["checks"].get(name)) for name in names)
            for world_id in world_ids
            if world_id in grades_by_world
        ) and all(world_id in grades_by_world for world_id in world_ids)

    def present(world_ids: Iterable[str]) -> bool:
        return all(world_id in grades_by_world for world_id in world_ids)

    r1_worlds = ["w001", "w013", "w015"]
    cost_present = all(
        bool(records_by_world.get(world_id, {}).get("cost_records"))
        for world_id in r1_worlds
    )
    r1_safety = checks(r1_worlds, "unsafe_continuation", "effect_count")
    r2_worlds = ["w003", "w004", "w007"]
    no_dispatch = records_by_world.get("w003", {})
    uncertain = records_by_world.get("w004", {})
    r2_distinguished = (
        no_dispatch.get("effect_readback") is None
        and uncertain.get("effect_readback") is not None
    )
    r3_worlds = ["w002", "w005", "w011", "w013", "w014", "w017"]
    r4_worlds = ["w002", "w004", "w005", "w006", "w008", "w011", "w012", "w016", "w017", "w018"]
    r6_worlds = ["w003", "w004", "w007", "w010", "w011"]
    r7_worlds = ["w006", "w012", "w014"]
    r7_actions = {"GLOBAL_REOPEN", "HUMAN_AMEND", "BLOCK"}
    r7_ok = all(
        records_by_world.get(world_id, {}).get("final_action") in r7_actions
        for world_id in r7_worlds
    )
    r8_worlds = ["w004", "w015", "w016", "w017", "w018"]

    return {
        "R1": {
            "status": _status(
                r1_safety and cost_present,
                partial=True,
                present=present(r1_worlds),
            ),
            "reason": "repeat safety and recorded cost were checked; cold-vs-repeat cost reduction was not run",
            "worlds": r1_worlds,
        },
        "R2": {
            "status": _status(
                checks(r2_worlds, "unsafe_continuation") and r2_distinguished,
                present=present(r2_worlds),
            ),
            "reason": "offline/refusal observations must not erase the distinct uncertain-Effect reconciliation path",
            "worlds": r2_worlds,
        },
        "R3": {
            "status": _status(
                checks(r3_worlds, "unsafe_continuation", "exact_closure"),
                present=present(r3_worlds),
            ),
            "reason": "revocation must block the affected closure while preserving unrelated nodes",
            "worlds": r3_worlds,
        },
        "R4": {
            "status": _status(
                checks(r4_worlds, "history_append_only", "unsafe_continuation"),
                present=present(r4_worlds),
            ),
            "reason": "future applicability may change, but prior Effect, refusal and Acceptance records must remain append-only",
            "worlds": r4_worlds,
        },
        "R5": {
            "status": _status(
                checks(["w012"], "unsafe_continuation", "history_append_only")
                and records_by_world.get("w012", {}).get("final_action")
                in {"GLOBAL_REOPEN", "HUMAN_AMEND", "BLOCK"},
                present=present(["w012"]),
            ),
            "reason": "material goal change must return to relation/problem formation",
            "worlds": ["w012"],
        },
        "R6": {
            "status": _status(
                checks(r6_worlds, "unsafe_continuation"),
                present=present(r6_worlds),
            ),
            "reason": "hidden or unavailable dependency truth must yield bounded Unknown, broader block, human amendment or equivalent safe action",
            "worlds": r6_worlds,
        },
        "R7": {
            "status": _status(
                checks(r7_worlds, "unsafe_continuation") and r7_ok,
                present=present(r7_worlds),
            ),
            "reason": "fork, goal-root and shared-root worlds permit honest global reopen",
            "worlds": r7_worlds,
        },
        "R8": {
            "status": _status(
                checks(
                    r8_worlds,
                    "migration_capsule",
                    "history_append_only",
                    "old_runtime_fenced",
                ),
                present=present(r8_worlds),
            ),
            "reason": "target runtime must reconstruct obligations from a provenance-bound capsule and fence the old epoch",
            "worlds": r8_worlds,
        },
    }


def _summarize_arm(
    method: str,
    records: list[Mapping[str, Any]],
    results: list[Mapping[str, Any]],
) -> dict[str, Any]:
    numeric_cost: dict[str, float] = {}
    for record in records:
        for cost_record in record.get("cost_records", []):
            if not isinstance(cost_record, Mapping):
                continue
            for key, value in cost_record.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    numeric_cost[str(key)] = numeric_cost.get(str(key), 0.0) + float(value)
    summary = {
        "world_count": len(results),
        "passed_worlds": sum(bool(result["passed"]) for result in results),
        "unsafe_continuations": sum(
            not bool(result["checks"]["unsafe_continuation"]) for result in results
        ),
        "unjustified_continuations": sum(
            not bool(result["checks"]["unjustified_continuation"]) for result in results
        ),
        "missed_reopen_nodes": sum(
            len(result["missed_reopen_nodes"]) for result in results
        ),
        "over_reopen_nodes": sum(
            len(result["over_reopen_nodes"]) for result in results
        ),
        "history_rewrites": sum(
            not bool(result["checks"]["history_append_only"]) for result in results
        ),
        "unreconciled_effect_worlds": sum(bool(result["unreconciled_effects"]) for result in results),
        "unsettled_obligation_count": sum(
            len(result["unsettled_obligations"]) for result in results
        ),
        "cost": numeric_cost,
        "T6": _t6_requirements(records, results),
        "results": results,
    }
    delegated_worlds = [
        str(record["world_id"])
        for record in records
        if record.get("authority_stratum") == "LEGITIMATELY_DELEGATED"
    ]
    if method == "DELEGATED_CENTER":
        summary["applicability"] = {
            "status": (
                "BOUNDED_STRATUM_ONLY"
                if delegated_worlds
                else "NOT_RUN_NO_DELEGATED_WORLD"
            ),
            "applicable_worlds": delegated_worlds,
            "nonapplicable_world_count": len(records) - len(delegated_worlds),
        }
        summary["T6"] = {
            requirement: {
                "status": "NOT_APPLICABLE",
                "reason": (
                    "only the explicitly delegated stratum is admissible; "
                    "one low-drift control cannot support a T6 requirement"
                ),
                "worlds": delegated_worlds,
            }
            for requirement in (
                "R1",
                "R2",
                "R3",
                "R4",
                "R5",
                "R6",
                "R7",
                "R8",
            )
        }
    else:
        summary["applicability"] = {
            "status": "FULL_WORLD_SET",
            "applicable_world_count": len(records),
        }
    return summary


def grade_runs(run_records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Grade all frozen records without sharing a closure function with any arm."""

    frozen_records = [dict(record) for record in run_records]
    oracle = load_oracle()
    results = [
        grade_run(str(record["world_id"]), record, oracle) for record in frozen_records
    ]
    by_method_records: dict[str, list[Mapping[str, Any]]] = {}
    by_method_results: dict[str, list[Mapping[str, Any]]] = {}
    for record, result in zip(frozen_records, results):
        method = str(record.get("method", "UNSPECIFIED"))
        by_method_records.setdefault(method, []).append(record)
        by_method_results.setdefault(method, []).append(result)

    return {
        "fixture_id": "T6-G7-ORTHOGONAL-REPLAY-001",
        "world_count": len(results),
        "passed_worlds": sum(bool(result["passed"]) for result in results),
        "unsafe_continuations": sum(
            not bool(result["checks"]["unsafe_continuation"]) for result in results
        ),
        "unjustified_continuations": sum(
            not bool(result["checks"]["unjustified_continuation"]) for result in results
        ),
        "missed_reopen_nodes": sum(
            len(result["missed_reopen_nodes"]) for result in results
        ),
        "over_reopen_nodes": sum(
            len(result["over_reopen_nodes"]) for result in results
        ),
        "history_rewrites": sum(
            not bool(result["checks"]["history_append_only"]) for result in results
        ),
        "unreconciled_effect_worlds": sum(
            not bool(result["checks"]["effect_reconciliation"]) for result in results
        ),
        "by_method": {
            method: _summarize_arm(
                method, by_method_records[method], by_method_results[method]
            )
            for method in sorted(by_method_records)
        },
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade frozen G7 runner records after all workers finish."
    )
    parser.add_argument("records", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    document = _read_json(args.records)
    records = document.get("records")
    if not isinstance(records, list):
        raise ValueError("runner result must contain records[]")
    result = grade_runs(records)
    raw_summary = {
        key: copy.deepcopy(value)
        for key, value in document.items()
        if key != "records"
    }
    raw_bytes = args.records.read_bytes()
    result["raw_runner"] = {
        "input_path": str(args.records),
        "input_bytes_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "record_count": len(records),
        "summary": raw_summary,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
