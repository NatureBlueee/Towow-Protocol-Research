#!/usr/bin/env python3
"""Mandatory invalidation gates for the Wave 011 G6 discriminator.

The gates are deliberately separate from coverage.  A gate passes only when an
adversarial specimen is detected while its benign control is accepted.  If any
gate cannot make that distinction, the whole run is INVALID.

This module has two entry points:

* ``run_invalidation_gates`` runs self-contained malicious doubles.
* ``evaluate_main_run`` audits a main-run artifact using provenance and
  semantic invariants rather than an expected-answer table.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


GATE_NAMES = (
    "truth_copy",
    "method_alias",
    "wrong_object",
    "read_skew",
    "unauthorized_real_effect",
)


@dataclass
class GateResult:
    name: str
    attack_present: bool
    attack_detected: bool
    benign_control_accepted: bool
    passed: bool
    evidence: dict[str, Any] = field(default_factory=dict)
    failure: str | None = None


@dataclass
class GateSuiteResult:
    schema: str
    gate_results: dict[str, GateResult]
    overall_valid: bool
    round_status: str
    coverage_allowed: bool
    evidence_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "gate_results": {
                name: asdict(result) for name, result in self.gate_results.items()
            },
            "overall_valid": self.overall_valid,
            "round_status": self.round_status,
            "coverage_allowed": self.coverage_allowed,
            "evidence_boundary": self.evidence_boundary,
        }


@dataclass
class AccessTrace:
    grader_private_oracle_reads: int = 0
    owner_native_store_reads: int = 0


@dataclass(frozen=True)
class OwnerHead:
    owner_id: str
    object_ref: str
    state: str
    revision: int
    source_kind: str


class PrivateOracle:
    """A grader-only source. Owner services must never call ``read``."""

    def __init__(self, head: OwnerHead, trace: AccessTrace):
        self._head = head
        self._trace = trace

    def read(self) -> OwnerHead:
        self._trace.grader_private_oracle_reads += 1
        return self._head


class OwnerNativeStore:
    def __init__(self, head: OwnerHead, trace: AccessTrace):
        self._head = head
        self._trace = trace

    def read(self) -> OwnerHead:
        self._trace.owner_native_store_reads += 1
        return self._head


class NativeOwnerService:
    def __init__(self, store: OwnerNativeStore):
        self._store = store

    def readback(self) -> OwnerHead:
        return self._store.read()


class TruthCopyOwnerService:
    """Malicious double reproducing Wave 010's truth-to-API copy."""

    def __init__(self, oracle: PrivateOracle):
        self._oracle = oracle

    def readback(self) -> OwnerHead:
        source = self._oracle.read()
        return OwnerHead(
            owner_id=source.owner_id,
            object_ref=source.object_ref,
            state=source.state,
            revision=source.revision,
            source_kind="grader_private_oracle",
        )


@dataclass(frozen=True)
class MethodDescriptor:
    method_id: str
    executable_sha256: str
    decision_root_sha256: str
    implementation_owner: str


@dataclass(frozen=True)
class EffectAssessment:
    occurrence_id: str
    raw_occurred: bool
    episode_target: str
    actual_target: str | None
    authority: str
    episode_bound: bool
    counts_toward_q: bool
    recovery_relevant: bool
    affected_targets: tuple[str, ...]


@dataclass(frozen=True)
class TemporalHead:
    owner_id: str
    claim_type: str
    state: str
    valid_from: int
    valid_through: int | None
    cut_id: str | None = None


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _result(
    name: str,
    *,
    attack_present: bool,
    attack_detected: bool,
    benign_control_accepted: bool,
    evidence: Mapping[str, Any],
    failure: str | None = None,
) -> GateResult:
    passed = attack_present and attack_detected and benign_control_accepted
    return GateResult(
        name=name,
        attack_present=attack_present,
        attack_detected=attack_detected,
        benign_control_accepted=benign_control_accepted,
        passed=passed,
        evidence=dict(evidence),
        failure=None if passed else (failure or "invalidation gate did not discriminate"),
    )


def _assemble(results: Iterable[GateResult]) -> GateSuiteResult:
    by_name = {result.name: result for result in results}
    missing = sorted(set(GATE_NAMES) - set(by_name))
    if missing:
        for name in missing:
            by_name[name] = _result(
                name,
                attack_present=False,
                attack_detected=False,
                benign_control_accepted=False,
                evidence={},
                failure="gate result missing",
            )
    overall_valid = all(by_name[name].passed for name in GATE_NAMES)
    return GateSuiteResult(
        schema="towow.wave011.g6.invalidation-gates.v1",
        gate_results=by_name,
        overall_valid=overall_valid,
        round_status="GATES_PASS" if overall_valid else "INVALID",
        coverage_allowed=overall_valid,
        evidence_boundary=(
            "local synthetic gate discrimination only; not X2, production, "
            "real Effect, human Acceptance, or formal promotion evidence"
        ),
    )


def _truth_copy_detector(response: OwnerHead, trace: AccessTrace) -> bool:
    return (
        trace.grader_private_oracle_reads > 0
        or response.source_kind == "grader_private_oracle"
    )


def gate_truth_copy(enabled: bool = True) -> GateResult:
    malicious_trace = AccessTrace()
    oracle_head = OwnerHead("TARGET", "obj-v5", "TRUE", 5, "grader_truth")
    owner_head = OwnerHead("TARGET", "obj-v4", "FALSE", 4, "owner_native_store")
    malicious = TruthCopyOwnerService(PrivateOracle(oracle_head, malicious_trace))
    malicious_response = malicious.readback()

    control_trace = AccessTrace()
    control = NativeOwnerService(OwnerNativeStore(owner_head, control_trace))
    control_response = control.readback()

    detected = enabled and _truth_copy_detector(malicious_response, malicious_trace)
    control_rejected = enabled and _truth_copy_detector(control_response, control_trace)
    return _result(
        "truth_copy",
        attack_present=True,
        attack_detected=detected,
        benign_control_accepted=not control_rejected,
        evidence={
            "oracle_and_owner_diverge": oracle_head.state != owner_head.state,
            "malicious_trace": asdict(malicious_trace),
            "control_trace": asdict(control_trace),
            "malicious_source_kind": malicious_response.source_kind,
            "control_source_kind": control_response.source_kind,
        },
        failure="grader-private-oracle access was not rejected",
    )


def _method_aliases(methods: Sequence[MethodDescriptor]) -> list[dict[str, Any]]:
    collisions: list[dict[str, Any]] = []
    for field_name in ("executable_sha256", "decision_root_sha256"):
        groups: dict[str, list[str]] = {}
        for method in methods:
            groups.setdefault(getattr(method, field_name), []).append(method.method_id)
        for digest, ids in groups.items():
            if len(ids) > 1:
                collisions.append(
                    {"identity_field": field_name, "digest": digest, "methods": ids}
                )
    return collisions


def gate_method_alias(enabled: bool = True) -> GateResult:
    shared_exec = _digest("shared-method-decision")
    aliased = [
        MethodDescriptor(name, shared_exec, shared_exec, f"owner-{index}")
        for index, name in enumerate(("strong-center", "mature-composition", "human"))
    ]
    independent = [
        MethodDescriptor(name, _digest(f"exec:{name}"), _digest(f"root:{name}"), name)
        for name in ("strong-center", "mature-composition", "human")
    ]
    attack_collisions = _method_aliases(aliased)
    control_collisions = _method_aliases(independent)
    return _result(
        "method_alias",
        attack_present=True,
        attack_detected=enabled and bool(attack_collisions),
        benign_control_accepted=not (enabled and bool(control_collisions)),
        evidence={
            "attack_collisions": attack_collisions,
            "control_collisions": control_collisions,
            "required_identity_fields": [
                "executable_sha256",
                "decision_root_sha256",
            ],
        },
        failure="same executable or decision root was accepted under renamed methods",
    )


def _assessment_mismatches(
    expected: EffectAssessment, reported: EffectAssessment
) -> list[str]:
    fields = (
        "occurrence_id",
        "raw_occurred",
        "episode_target",
        "actual_target",
        "authority",
        "episode_bound",
        "counts_toward_q",
        "recovery_relevant",
        "affected_targets",
    )
    return [
        field_name
        for field_name in fields
        if getattr(expected, field_name) != getattr(reported, field_name)
    ]


def gate_wrong_object(enabled: bool = True) -> GateResult:
    expected = EffectAssessment(
        occurrence_id="occ-wrong-target-damage",
        raw_occurred=True,
        episode_target="CNC-17",
        actual_target="CNC-71",
        authority="AUTHORIZED_FOR_CNC_17_ONLY",
        episode_bound=False,
        counts_toward_q=False,
        recovery_relevant=True,
        affected_targets=("CNC-71",),
    )
    collapsed = EffectAssessment(
        occurrence_id=expected.occurrence_id,
        raw_occurred=False,
        episode_target="CNC-17",
        actual_target=None,
        authority=expected.authority,
        episode_bound=False,
        counts_toward_q=False,
        recovery_relevant=False,
        affected_targets=(),
    )
    attack_mismatches = _assessment_mismatches(expected, collapsed)
    control_mismatches = _assessment_mismatches(expected, expected)
    semantic_detected = {
        "raw_occurrence_preserved": collapsed.raw_occurred,
        "actual_target_preserved": collapsed.actual_target == expected.actual_target,
        "recovery_preserved": collapsed.recovery_relevant,
        "affected_target_preserved": expected.actual_target in collapsed.affected_targets,
    }
    return _result(
        "wrong_object",
        attack_present=True,
        attack_detected=enabled and bool(attack_mismatches),
        benign_control_accepted=not (enabled and bool(control_mismatches)),
        evidence={
            "attack_mismatches": attack_mismatches,
            "control_mismatches": control_mismatches,
            "malicious_output_checks": semantic_detected,
        },
        failure="wrong-target real damage was allowed to disappear behind non-qualification",
    )


def _common_valid_index(heads: Sequence[TemporalHead]) -> int | None:
    if not heads:
        return None
    lower = max(head.valid_from for head in heads)
    finite_ends = [
        head.valid_through for head in heads if head.valid_through is not None
    ]
    upper = min(finite_ends) if finite_ends else None
    if upper is not None and lower > upper:
        return None
    return lower


def _is_read_skew(heads: Sequence[TemporalHead], derived_done: bool) -> bool:
    if not derived_done:
        return False
    explicit_cuts = {head.cut_id for head in heads if head.cut_id is not None}
    different_explicit_cuts = len(explicit_cuts) > 1
    no_temporal_intersection = _common_valid_index(heads) is None
    return different_explicit_cuts or no_temporal_intersection


def gate_read_skew(enabled: bool = True) -> GateResult:
    skewed_heads = (
        TemporalHead("buyer", "Acceptance", "ACCEPT", 8, 10, "cut-10"),
        TemporalHead("rail", "Settlement", "PAID_OUT", 12, None, "cut-12"),
    )
    consistent_heads = (
        TemporalHead("buyer", "Acceptance", "ACCEPT", 8, None, "cut-12"),
        TemporalHead("rail", "Settlement", "PAID_OUT", 12, None, "cut-12"),
    )
    attack_detected = enabled and _is_read_skew(skewed_heads, derived_done=True)
    control_rejected = enabled and _is_read_skew(consistent_heads, derived_done=True)
    return _result(
        "read_skew",
        attack_present=True,
        attack_detected=attack_detected,
        benign_control_accepted=not control_rejected,
        evidence={
            "attack_common_valid_index": _common_valid_index(skewed_heads),
            "control_common_valid_index": _common_valid_index(consistent_heads),
            "attack_cut_ids": [head.cut_id for head in skewed_heads],
            "control_cut_ids": [head.cut_id for head in consistent_heads],
        },
        failure="non-overlapping or differently cut heads were allowed to derive Done",
    )


def gate_unauthorized_real_effect(enabled: bool = True) -> GateResult:
    expected = EffectAssessment(
        occurrence_id="occ-unauthorized-real-effect",
        raw_occurred=True,
        episode_target="CNC-17",
        actual_target="CNC-17",
        authority="UNAUTHORIZED",
        episode_bound=True,
        counts_toward_q=False,
        recovery_relevant=True,
        affected_targets=("CNC-17",),
    )
    collapsed = EffectAssessment(
        occurrence_id=expected.occurrence_id,
        raw_occurred=False,
        episode_target="CNC-17",
        actual_target=None,
        authority="UNAUTHORIZED",
        episode_bound=True,
        counts_toward_q=False,
        recovery_relevant=False,
        affected_targets=(),
    )
    attack_mismatches = _assessment_mismatches(expected, collapsed)
    control_mismatches = _assessment_mismatches(expected, expected)
    return _result(
        "unauthorized_real_effect",
        attack_present=True,
        attack_detected=enabled and bool(attack_mismatches),
        benign_control_accepted=not (enabled and bool(control_mismatches)),
        evidence={
            "attack_mismatches": attack_mismatches,
            "required_joint_result": {
                "raw_occurred": True,
                "authority": "UNAUTHORIZED",
                "counts_toward_q": False,
                "recovery_relevant": True,
            },
        },
        failure=(
            "unauthorized real Effect was not preserved as raw occurrence with "
            "CountsTowardQ=false and recovery relevance"
        ),
    )


def run_invalidation_gates(
    disabled_gates: Iterable[str] = (),
) -> GateSuiteResult:
    disabled = set(disabled_gates)
    unknown = sorted(disabled - set(GATE_NAMES))
    if unknown:
        raise ValueError(f"unknown gates: {', '.join(unknown)}")
    return _assemble(
        (
            gate_truth_copy("truth_copy" not in disabled),
            gate_method_alias("method_alias" not in disabled),
            gate_wrong_object("wrong_object" not in disabled),
            gate_read_skew("read_skew" not in disabled),
            gate_unauthorized_real_effect(
                "unauthorized_real_effect" not in disabled
            ),
        )
    )


def _as_methods(rows: Sequence[Mapping[str, Any]]) -> list[MethodDescriptor]:
    return [
        MethodDescriptor(
            method_id=str(row["method_id"]),
            executable_sha256=str(row["executable_sha256"]),
            decision_root_sha256=str(row["decision_root_sha256"]),
            implementation_owner=str(row.get("implementation_owner", "UNDECLARED")),
        )
        for row in rows
    ]


def _effect_row_is_preserved(row: Mapping[str, Any], kind: str) -> bool:
    raw = bool(row.get("raw_occurred"))
    episode_target = row.get("episode_target")
    actual_target = row.get("actual_target")
    counts = bool(row.get("counts_toward_q"))
    recovery = bool(row.get("recovery_relevant"))
    affected = set(row.get("affected_targets", ()))
    authority = row.get("authority")
    if kind == "wrong_object":
        return (
            raw
            and actual_target is not None
            and actual_target != episode_target
            and not counts
            and recovery
            and actual_target in affected
        )
    return (
        raw
        and authority == "UNAUTHORIZED"
        and not counts
        and recovery
        and actual_target in affected
    )


def _artifact_gate(
    name: str,
    attack_rows: Sequence[Mapping[str, Any]],
    passed_rows: Sequence[Mapping[str, Any]],
    evidence: Mapping[str, Any],
    failure: str,
    *,
    benign_control_accepted: bool = True,
) -> GateResult:
    return _result(
        name,
        attack_present=bool(attack_rows),
        attack_detected=bool(attack_rows) and len(passed_rows) == len(attack_rows),
        benign_control_accepted=benign_control_accepted,
        evidence=evidence,
        failure=failure,
    )


def evaluate_main_run(payload: Mapping[str, Any]) -> GateSuiteResult:
    """Evaluate machine-readable gate evidence emitted by the main runner.

    Required top-level fields:

    ``provenance.owner_api_sources``
        Source audit rows. Any grader/private-oracle access invalidates the gate.
        At least one owner-native store/sensor/institutional-act row is required.
    ``methods``
        Three or more executable descriptors with independent executable and
        decision-root hashes.
    ``occurrence_assessments``
        Rows for wrong-object and unauthorized-real-effect attacks. Rows are
        selected by their semantic properties, not by expected labels.
    ``done_evaluations``
        Derived Done rows with the exact heads used in the evaluation.
    """

    if payload.get("kind") == "G6_12_PAIR_3X3_RUN":
        return evaluate_matrix_run(payload)

    provenance = payload.get("provenance", {})
    source_rows = list(provenance.get("owner_api_sources", ()))
    truth_copy_attacks = [
        row
        for row in source_rows
        if row.get("accessed_private_oracle")
        or row.get("source_kind") in {"grader_truth", "grader_private_oracle"}
    ]
    native_sources = [
        row
        for row in source_rows
        if row.get("source_kind")
        in {"owner_native_store", "owner_sensor", "institutional_act"}
        and not row.get("accessed_private_oracle")
    ]
    truth_copy = _result(
        "truth_copy",
        attack_present=bool(payload.get("attack_manifest", {}).get("truth_copy")),
        attack_detected=(
            bool(payload.get("attack_manifest", {}).get("truth_copy"))
            and bool(payload.get("attack_detections", {}).get("truth_copy"))
            and not truth_copy_attacks
        ),
        benign_control_accepted=bool(native_sources),
        evidence={
            "source_count": len(source_rows),
            "native_source_count": len(native_sources),
            "forbidden_source_rows": truth_copy_attacks,
        },
        failure="owner API provenance did not exclude grader truth direct-copy",
    )

    method_rows = list(payload.get("methods", ()))
    try:
        methods = _as_methods(method_rows)
        alias_collisions = _method_aliases(methods)
    except (KeyError, TypeError, ValueError):
        methods = []
        alias_collisions = [{"error": "invalid method descriptors"}]
    method_alias = _result(
        "method_alias",
        attack_present=bool(payload.get("attack_manifest", {}).get("method_alias")),
        attack_detected=(
            bool(payload.get("attack_manifest", {}).get("method_alias"))
            and bool(payload.get("attack_detections", {}).get("method_alias"))
            and len(methods) >= 3
            and not alias_collisions
        ),
        benign_control_accepted=len(methods) >= 3 and not alias_collisions,
        evidence={
            "method_count": len(methods),
            "alias_collisions": alias_collisions,
        },
        failure="method executable or decision-root identity is aliased",
    )

    occurrences = list(payload.get("occurrence_assessments", ()))
    wrong_rows = [
        row
        for row in occurrences
        if row.get("raw_occurred")
        and row.get("actual_target") is not None
        and row.get("actual_target") != row.get("episode_target")
    ]
    wrong_passed = [
        row for row in wrong_rows if _effect_row_is_preserved(row, "wrong_object")
    ]
    wrong_object = _artifact_gate(
        "wrong_object",
        wrong_rows,
        wrong_passed,
        {
            "attack_rows": len(wrong_rows),
            "preserved_rows": len(wrong_passed),
        },
        "wrong-target real damage was not preserved for recovery",
    )

    unauthorized_rows = [
        row
        for row in occurrences
        if row.get("raw_occurred") and row.get("authority") == "UNAUTHORIZED"
    ]
    unauthorized_passed = [
        row
        for row in unauthorized_rows
        if _effect_row_is_preserved(row, "unauthorized_real_effect")
    ]
    unauthorized = _artifact_gate(
        "unauthorized_real_effect",
        unauthorized_rows,
        unauthorized_passed,
        {
            "attack_rows": len(unauthorized_rows),
            "preserved_rows": len(unauthorized_passed),
        },
        "unauthorized real Effect did not retain recovery relevance",
    )

    done_rows = list(payload.get("done_evaluations", ()))
    skew_attacks: list[Mapping[str, Any]] = []
    skew_rejected: list[Mapping[str, Any]] = []
    for row in done_rows:
        heads = [
            TemporalHead(
                owner_id=str(head["owner_id"]),
                claim_type=str(head["claim_type"]),
                state=str(head["state"]),
                valid_from=int(head["valid_from"]),
                valid_through=(
                    None
                    if head.get("valid_through") is None
                    else int(head["valid_through"])
                ),
                cut_id=head.get("cut_id"),
            )
            for head in row.get("heads", ())
        ]
        input_is_skewed = _is_read_skew(heads, derived_done=True)
        if input_is_skewed:
            skew_attacks.append(row)
            if not bool(row.get("derived_done")):
                skew_rejected.append(row)
    read_skew = _artifact_gate(
        "read_skew",
        skew_attacks,
        skew_rejected,
        {
            "attack_rows": len(skew_attacks),
            "rejected_done_rows": len(skew_rejected),
        },
        "read-skew heads were allowed to produce derived Done",
    )

    return _assemble(
        (truth_copy, method_alias, wrong_object, read_skew, unauthorized)
    )


def _matrix_cells(
    payload: Mapping[str, Any],
) -> Iterable[tuple[Mapping[str, Any], str, Mapping[str, Any], Mapping[str, Any]]]:
    for record in payload.get("records", ()):
        observations_by_token = record.get("owner_observations", {})
        outputs_by_token = record.get("method_output", {})
        if not isinstance(observations_by_token, Mapping) or not isinstance(
            outputs_by_token, Mapping
        ):
            continue
        for token, observations in observations_by_token.items():
            output = outputs_by_token.get(token)
            if isinstance(observations, Mapping) and isinstance(output, Mapping):
                yield record, str(token), observations, output


def _authorized_attempt_ids(observations: Mapping[str, Any]) -> set[str]:
    execution = observations.get("execution", {}).get("payload", {})
    authority = observations.get("authority", {}).get("payload", {})
    result: set[str] = set()
    for attempt in execution.get("attempts", ()):
        if not attempt.get("crossed_boundary"):
            continue
        for grant in authority.get("attempt_grants", ()):
            if (
                attempt.get("actor") == grant.get("actor")
                and attempt.get("operation") in grant.get("operations", ())
                and attempt.get("object") in grant.get("objects", ())
            ):
                result.add(str(attempt.get("id")))
                break
    return result


def _output_effect_sets(output: Mapping[str, Any]) -> tuple[set[str], set[str], set[str]]:
    raw = {
        str(row.get("occurrence_id"))
        for row in output.get("raw_occurrences", ())
        if row.get("native_kind") == "TARGET_TRANSITION"
    }
    counted = {
        str(value)
        for value in output.get("counts_toward_q", {}).get("effect_ids", ())
    }
    recovery = {
        str(value)
        for value in output.get("recovery_relevance", {}).get("effect_ids", ())
    }
    return raw, counted, recovery


def _cut_is_consistent(cut: Mapping[str, Any]) -> bool | None:
    if "consistent" in cut:
        return bool(cut["consistent"])
    intervals = list(cut.get("head_intervals", ()))
    if not intervals:
        return None
    lower = max(int(row["valid_from"]) for row in intervals)
    finite_ends = [
        int(row["valid_through"])
        for row in intervals
        if row.get("valid_through") is not None
    ]
    upper = min(finite_ends) if finite_ends else None
    return upper is None or lower <= upper


def evaluate_matrix_run(payload: Mapping[str, Any]) -> GateSuiteResult:
    """Audit the concrete 12-pair runner artifact without loading its oracle.

    Attack rows are found from owner-native observations themselves:
    wrong-target transitions, transitions tied to unauthorized attempts, and
    inconsistent owner cuts.  Pair IDs and the private expected table are not
    used to decide whether an output preserves the required semantics.
    """

    source_rows = payload.get("owner_source_identities", {})
    if not isinstance(source_rows, Mapping):
        source_rows = {}
    forbidden_sources = []
    native_source_count = 0
    source_paths: set[str] = set()
    for name, row in source_rows.items():
        if not isinstance(row, Mapping):
            forbidden_sources.append({"name": name, "reason": "malformed source row"})
            continue
        path = str(row.get("path", ""))
        source_paths.add(path)
        if (
            not path.startswith("fixtures/")
            or "private_oracle" in path
            or not row.get("sha256")
            or not row.get("owner_id")
        ):
            forbidden_sources.append({"name": name, "path": path})
        else:
            native_source_count += 1
    reference_truth_gate = gate_truth_copy()
    unchanged_oracle = (
        bool(payload.get("oracle_hash_before"))
        and payload.get("oracle_hash_before") == payload.get("oracle_hash_after")
    )
    truth_copy = _result(
        "truth_copy",
        attack_present=reference_truth_gate.attack_present,
        attack_detected=(
            reference_truth_gate.attack_detected
            and not forbidden_sources
            and unchanged_oracle
        ),
        benign_control_accepted=(
            reference_truth_gate.benign_control_accepted
            and native_source_count >= 3
            and len(source_paths) == native_source_count
        ),
        evidence={
            "reference_attack_detected": reference_truth_gate.attack_detected,
            "owner_native_source_count": native_source_count,
            "forbidden_sources": forbidden_sources,
            "distinct_source_paths": len(source_paths),
            "oracle_unchanged": unchanged_oracle,
        },
        failure="matrix owner sources do not establish a non-oracle native path",
    )

    worker_rows = payload.get("worker_executable_source_hashes", {})
    if not isinstance(worker_rows, Mapping):
        worker_rows = {}
    methods = [
        MethodDescriptor(
            method_id=str(name),
            executable_sha256=str(row.get("source_sha256", "")),
            decision_root_sha256=_digest(
                f"{row.get('decision_module', '')}:{row.get('source_sha256', '')}"
            ),
            implementation_owner=str(name),
        )
        for name, row in worker_rows.items()
        if isinstance(row, Mapping)
    ]
    alias_collisions = _method_aliases(methods)
    executable_identities = {
        row.get("executable_identity")
        for row in worker_rows.values()
        if isinstance(row, Mapping)
    }
    reference_alias_gate = gate_method_alias()
    independent_actual_methods = (
        len(methods) >= 3
        and len(executable_identities) == len(methods)
        and None not in executable_identities
        and not alias_collisions
    )
    method_alias = _result(
        "method_alias",
        attack_present=reference_alias_gate.attack_present,
        attack_detected=(
            reference_alias_gate.attack_detected and independent_actual_methods
        ),
        benign_control_accepted=(
            reference_alias_gate.benign_control_accepted
            and independent_actual_methods
        ),
        evidence={
            "reference_attack_collisions": reference_alias_gate.evidence[
                "attack_collisions"
            ],
            "actual_method_count": len(methods),
            "actual_alias_collisions": alias_collisions,
            "distinct_executable_identities": len(executable_identities),
        },
        failure="matrix methods share or omit executable/decision-root identity",
    )

    wrong_attacks: list[dict[str, Any]] = []
    wrong_passed: list[dict[str, Any]] = []
    wrong_controls = 0
    wrong_controls_accepted = 0
    unauthorized_attacks: list[dict[str, Any]] = []
    unauthorized_passed: list[dict[str, Any]] = []
    unauthorized_controls = 0
    unauthorized_controls_accepted = 0
    skew_attacks: list[dict[str, Any]] = []
    skew_passed: list[dict[str, Any]] = []
    skew_controls = 0
    skew_controls_accepted = 0

    for record, token, observations, output in _matrix_cells(payload):
        target = observations.get("target", {}).get("payload", {})
        execution = observations.get("execution", {}).get("payload", {})
        cut = observations.get("cut", {}).get("payload", {})
        cut_consistent = _cut_is_consistent(cut)
        exact_object = target.get("exact_object")
        transitions = list(target.get("transitions", ()))
        attempts = {
            str(row.get("id")): row
            for row in execution.get("attempts", ())
            if row.get("crossed_boundary")
        }
        authorized = _authorized_attempt_ids(observations)
        raw, counted, recovery = _output_effect_sets(output)
        coordinate = {
            "stratum": record.get("stratum"),
            "implementation": record.get("implementation"),
            "world_token": token,
        }

        for transition in transitions:
            occurrence = str(transition.get("occurrence"))
            operation_id = str(transition.get("operation_id"))
            if transition.get("object") != exact_object:
                attack = {
                    **coordinate,
                    "occurrence_id": occurrence,
                    "actual_target": transition.get("object"),
                    "episode_target": exact_object,
                }
                wrong_attacks.append(attack)
                if occurrence in raw and occurrence not in counted and occurrence in recovery:
                    wrong_passed.append(attack)
            elif (
                operation_id in authorized
                and target.get("read_status") == "FRESH"
                and cut_consistent is True
            ):
                wrong_controls += 1
                if occurrence in raw and occurrence in counted:
                    wrong_controls_accepted += 1

            if operation_id in attempts and operation_id not in authorized:
                attack = {
                    **coordinate,
                    "occurrence_id": occurrence,
                    "operation_id": operation_id,
                }
                unauthorized_attacks.append(attack)
                if occurrence in raw and occurrence not in counted and occurrence in recovery:
                    unauthorized_passed.append(attack)

        if attempts and all(attempt_id in authorized for attempt_id in attempts):
            unauthorized_controls += 1
            unauthorized_control_ok = all(
                str(transition.get("occurrence")) not in recovery
                for transition in transitions
                if str(transition.get("operation_id")) in authorized
                and transition.get("object") == exact_object
                and target.get("read_status") == "FRESH"
                and cut_consistent is True
            )
            if unauthorized_control_ok:
                unauthorized_controls_accepted += 1

        if cut_consistent is False:
            attack = coordinate
            skew_attacks.append(attack)
            output_safe = (
                output.get("consistent_cut") is False
                and not counted
                and output.get("control_action")
                in {"BOUNDED_UNKNOWN", "RECOVER_AND_BLOCK", "BLOCK_DISPUTED"}
            )
            if output_safe:
                skew_passed.append(attack)
        elif cut_consistent is True and transitions:
            skew_controls += 1
            if output.get("consistent_cut") is True:
                skew_controls_accepted += 1

    wrong_object = _artifact_gate(
        "wrong_object",
        wrong_attacks,
        wrong_passed,
        {
            "attack_rows": len(wrong_attacks),
            "preserved_rows": len(wrong_passed),
            "benign_control_rows": wrong_controls,
            "benign_controls_accepted": wrong_controls_accepted,
        },
        "wrong-target transition disappeared or counted toward the episode",
        benign_control_accepted=(
            wrong_controls > 0 and wrong_controls_accepted == wrong_controls
        ),
    )
    unauthorized = _artifact_gate(
        "unauthorized_real_effect",
        unauthorized_attacks,
        unauthorized_passed,
        {
            "attack_rows": len(unauthorized_attacks),
            "preserved_rows": len(unauthorized_passed),
            "benign_control_rows": unauthorized_controls,
            "benign_controls_accepted": unauthorized_controls_accepted,
        },
        "unauthorized real transition lost raw/recovery or counted toward Q",
        benign_control_accepted=(
            unauthorized_controls > 0
            and unauthorized_controls_accepted == unauthorized_controls
        ),
    )
    read_skew = _artifact_gate(
        "read_skew",
        skew_attacks,
        skew_passed,
        {
            "attack_rows": len(skew_attacks),
            "safe_rows": len(skew_passed),
            "benign_control_rows": skew_controls,
            "benign_controls_accepted": skew_controls_accepted,
        },
        "inconsistent owner cut was not blocked from counts/continuation",
        benign_control_accepted=(
            skew_controls > 0 and skew_controls_accepted == skew_controls
        ),
    )

    return _assemble(
        (truth_copy, method_alias, wrong_object, read_skew, unauthorized)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--disable-gate",
        action="append",
        default=[],
        choices=GATE_NAMES,
        help="test-only mutation: make a detector fail",
    )
    parser.add_argument(
        "--main-run",
        type=Path,
        help="audit a main-run JSON artifact instead of malicious doubles",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.main_run:
        payload = json.loads(args.main_run.read_text(encoding="utf-8"))
        if payload.get("kind") == "G6_12_PAIR_3X3_RUN":
            result = evaluate_matrix_run(payload)
        else:
            result = evaluate_main_run(payload)
    else:
        result = run_invalidation_gates(args.disable_gate)
    rendered = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result.overall_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
