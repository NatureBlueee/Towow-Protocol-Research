#!/usr/bin/env python3
"""CE-001 integration preflight.

This validator only decides whether seven namespaced component envelopes are
qualified enough to enter a future independent contract evaluator.  It never
computes CE-001 success, coverage, recovery, or a contract score.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


EXPECTED_COMPONENTS = tuple(f"G{index}" for index in range(1, 8))
EXPECTED_OWNERS = ("O_Q", "O_V", "O_R", "O_S", "O_P", "O_E")
REQUIRED_ACCEPTANCE_OWNERS = {"O_Q", "O_V"}
FROZEN_CASE_IDS = {
    "E0-PLATFORM-DIRECT",
    "E1-EXTANT-MULTI-OWNER",
    "E2-CONDITION-FORMATION",
    "E3A-ACK-LOST-EFFECT",
    "E3B-ACK-LOST-NO-EFFECT",
    "E4-REVOKE-WITH-ALTERNATIVE",
    "E5-IMPOSSIBLE-REFUSAL",
    "E6-MIGRATION-REPLAY",
}
# The current validator implements only the positive success-closure branch
# plus E6 migration structure. Other frozen cases must fail closed until
# success/refusal/unknown-or-reopen admission branches exist.
PREFLIGHT_SUPPORTED_CASE_IDS = {
    "E1-EXTANT-MULTI-OWNER",
    "E6-MIGRATION-REPLAY",
}

# These are conclusions that only the future independent contract evaluator may
# create.  A same-named field anywhere under one component is pass-through.
CONTRACT_LEVEL_FIELDS = {
    "exacttasksuccess",
    "correctresolution",
    "achievablesuccesscoverage",
    "allcaseresolutioncoverage",
    "recoverytovalue",
    "unsafeeffect",
    "duplicateeffect",
    "wrongobjectreliance",
    "unreconciledeffect",
    "candidateexclusivesuccess",
    "ysuccess",
    "yresolution",
    "yeffect",
    "yacceptance",
    "commitment",
    "authority",
    "effect",
    "acceptance",
    "settlement",
    "contractscore",
    "contractsuccess",
    "complete_solution",
    "ce001",
}

LINE_FORBIDDEN_FIELDS = {
    "G1": {"commitment", "authority", "effect", "acceptance"},
    "G2": {"authorized", "activated"},
    "G3": {"contract_recovery"},
    "G4": {"independent_owner_acceptance", "contract_causal_advantage"},
    "G5": {"effect", "acceptance", "settlement"},
    "G6": {"migration_continuity", "history_continuity"},
    "G7": {"authority", "effect", "acceptance"},
}


def _walk(value: Any, path: str) -> Iterable[tuple[str, Any, str]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield str(key), child, child_path
            yield from _walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _at(value: Mapping[str, Any], *path: str) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _nonempty_strings(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item.strip()) for item in value)
    )


def validate_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Return a deterministic fail-closed preflight report.

    A passing report deliberately contains ``CONTRACT_SCORE_NOT_COMPUTED``.
    """

    errors: list[dict[str, str]] = []

    def reject(code: str, path: str, message: str) -> None:
        item = {"code": code, "path": path, "message": message}
        if item not in errors:
            errors.append(item)

    if not isinstance(envelope, Mapping):
        return _report(
            [
                {
                    "code": "INVALID_ENVELOPE",
                    "path": "$",
                    "message": "input must be a JSON object",
                }
            ],
            [],
        )

    episode = envelope.get("episode")
    if not isinstance(episode, Mapping):
        reject("EPISODE_BINDING_MISSING", "$.episode", "episode binding is required")
        episode = {}

    binding_fields = (
        "episode_id",
        "case_id",
        "q_version",
        "object_id",
        "operation_id",
        "target_id",
    )
    for field in binding_fields:
        if not isinstance(episode.get(field), str) or not episode.get(field):
            reject(
                "EPISODE_BINDING_MISSING",
                f"$.episode.{field}",
                f"{field} must be a non-empty string",
            )
    frozen_values = {
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "target_id": "VenueV:CircuitC7",
    }
    for field, expected in frozen_values.items():
        if episode.get(field) != expected:
            reject(
                "CE001_EPISODE_BINDING_MISMATCH",
                f"$.episode.{field}",
                f"CE-001 requires {field}={expected}",
            )
    case_id = episode.get("case_id")
    if case_id not in FROZEN_CASE_IDS:
        reject(
            "UNKNOWN_CASE_ID",
            "$.episode.case_id",
            "case_id must be one of the eight frozen CE-001 cases",
        )
    elif case_id not in PREFLIGHT_SUPPORTED_CASE_IDS:
        reject(
            "CASE_ADMISSION_NOT_IMPLEMENTED",
            "$.episode.case_id",
            (
                "the current preflight implements only E1 success closure "
                "and E6 migration-success structure"
            ),
        )

    for _key, value, path in _walk(envelope, "$"):
        if value == "SIMULATED_MULTI_OWNER":
            reject(
                "SIMULATED_MULTI_OWNER",
                path,
                "a single simulated multi-owner source cannot establish owner separation",
            )

    components = envelope.get("components")
    if not isinstance(components, Mapping):
        reject(
            "COMPONENT_NAMESPACES_MISSING",
            "$.components",
            "components must contain exactly G1 through G7",
        )
        components = {}

    actual_names = set(components)
    expected_names = set(EXPECTED_COMPONENTS)
    if actual_names != expected_names:
        reject(
            "COMPONENT_NAMESPACE_SET_MISMATCH",
            "$.components",
            f"expected {sorted(expected_names)}, received {sorted(actual_names)}",
        )

    qualified_components: list[str] = []
    for line in EXPECTED_COMPONENTS:
        component = components.get(line)
        if not isinstance(component, Mapping):
            reject(
                "MISSING_COMPONENT_NAMESPACE",
                f"$.components.{line}",
                f"{line} namespaced envelope is required",
            )
            continue
        if component.get("namespace") != line:
            reject(
                "NAMESPACE_MISMATCH",
                f"$.components.{line}.namespace",
                f"component at {line} must declare namespace={line}",
            )
        if component.get("qualification") != "QUALIFIED_COMPONENT_OUTPUT":
            reject(
                "UNQUALIFIED_COMPONENT_OUTPUT",
                f"$.components.{line}.qualification",
                "only explicitly qualified local component output may enter preflight",
            )
        else:
            qualified_components.append(line)

        component_binding = component.get("binding")
        binding_path = f"$.components.{line}.binding"
        if not isinstance(component_binding, Mapping):
            reject(
                "COMPONENT_BINDING_MISSING",
                binding_path,
                f"{line} must bind its output to the selected episode",
            )
        else:
            for field in binding_fields:
                if component_binding.get(field) != episode.get(field):
                    reject(
                        "COMPONENT_BINDING_MISMATCH",
                        f"{binding_path}.{field}",
                        f"{line} binding must equal episode.{field}",
                    )

        forbidden = CONTRACT_LEVEL_FIELDS | LINE_FORBIDDEN_FIELDS[line]
        for key, value, path in _walk(component, f"$.components.{line}"):
            normalized = key.replace("_", "").lower()
            direct_normalized = key.lower()
            if (
                normalized in {
                    item.replace("_", "") for item in CONTRACT_LEVEL_FIELDS
                }
                or normalized.startswith("contract")
            ):
                reject(
                    "CONTRACT_FIELD_PASSTHROUGH",
                    path,
                    f"{key} is a contract-level conclusion, not {line} evidence",
                )
            elif direct_normalized in forbidden:
                reject(
                    "LINE_SCOPE_PASSTHROUGH",
                    path,
                    f"{line} is not authoritative for field {key}",
                )
    owners = envelope.get("owner_sources")
    if not isinstance(owners, Mapping):
        reject(
            "OWNER_SOURCES_MISSING",
            "$.owner_sources",
            "owner state and act source declarations are required",
        )
        owners = {}

    owner_pairs: dict[str, tuple[Any, Any]] = {}
    for owner in EXPECTED_OWNERS:
        source = owners.get(owner)
        if not isinstance(source, Mapping):
            reject(
                "OWNER_SOURCE_MISSING",
                f"$.owner_sources.{owner}",
                f"{owner} source declaration is required",
            )
            continue
        state_source = source.get("state_source_id")
        act_source = source.get("act_source_id")
        if not isinstance(state_source, str) or not state_source:
            reject(
                "OWNER_SOURCE_MISSING",
                f"$.owner_sources.{owner}.state_source_id",
                "state_source_id must be non-empty",
            )
        if not isinstance(act_source, str) or not act_source:
            reject(
                "OWNER_SOURCE_MISSING",
                f"$.owner_sources.{owner}.act_source_id",
                "act_source_id must be non-empty",
            )
        owner_pairs[owner] = (state_source, act_source)

    valid_pairs = [pair for pair in owner_pairs.values() if all(pair)]
    state_sources = [pair[0] for pair in valid_pairs]
    act_sources = [pair[1] for pair in valid_pairs]
    if (
        len(valid_pairs) != len(set(valid_pairs))
        or len(state_sources) != len(set(state_sources))
        or len(act_sources) != len(set(act_sources))
    ):
        reject(
            "OWNER_SOURCES_NOT_INDEPENDENT",
            "$.owner_sources",
            "owners must not reuse state or act sources",
        )
    op_pair = owner_pairs.get("O_P")
    if op_pair and any(
        op_pair[0] == pair[0] or op_pair[1] == pair[1]
        for owner, pair in owner_pairs.items()
        if owner != "O_P"
    ):
        reject(
            "OP_NOT_INDEPENDENT",
            "$.owner_sources.O_P",
            "O_P must not reuse another owner's state/act source",
        )

    g5 = components.get("G5") if isinstance(components.get("G5"), Mapping) else {}
    g6 = components.get("G6") if isinstance(components.get("G6"), Mapping) else {}
    g7 = components.get("G7") if isinstance(components.get("G7"), Mapping) else {}
    authority = _at(g5, "evidence", "authority_closure")
    consumption = _at(g6, "evidence", "target_authority_consumption")
    effect = _at(g6, "evidence", "effect_occurrence")
    acceptances = _at(g6, "evidence", "owner_acceptances")
    finality = _at(g6, "evidence", "op_finality")

    authority_hashes: list[str] = []
    if not isinstance(authority, Mapping) or authority.get("current") is not True:
        reject(
            "CURRENT_AUTHORITY_CLOSURE_MISSING",
            "$.components.G5.evidence.authority_closure",
            "G5 must provide a current qualified Authority closure",
        )
    else:
        _check_binding(authority, episode, reject, "$.components.G5.evidence.authority_closure")
        receipts = authority.get("receipts")
        if not isinstance(receipts, list) or not receipts:
            reject(
                "AUTHORITY_RECEIPTS_MISSING",
                "$.components.G5.evidence.authority_closure.receipts",
                "at least one current Authority receipt is required",
            )
        else:
            authority_hashes = [
                receipt.get("receipt_hash")
                for receipt in receipts
                if isinstance(receipt, Mapping)
                and isinstance(receipt.get("receipt_hash"), str)
                and receipt.get("receipt_hash")
            ]
            if len(authority_hashes) != len(receipts):
                reject(
                    "AUTHORITY_RECEIPTS_MISSING",
                    "$.components.G5.evidence.authority_closure.receipts",
                    "every Authority receipt needs a receipt_hash",
                )
            elif len(authority_hashes) != len(set(authority_hashes)):
                reject(
                    "DUPLICATE_AUTHORITY_RECEIPT",
                    "$.components.G5.evidence.authority_closure.receipts",
                    "repeating one Authority receipt does not increase closure coverage",
                )

    if (
        not isinstance(consumption, Mapping)
        or consumption.get("consumed_by_target") is not True
        or not consumption.get("consumption_event_hash")
    ):
        reject(
            "TARGET_CONSUMED_AUTHORITY_MISSING",
            "$.components.G6.evidence.target_authority_consumption",
            "a target-native consumption event is required; a logged receipt is insufficient",
        )
    else:
        _check_binding(
            consumption,
            episode,
            reject,
            "$.components.G6.evidence.target_authority_consumption",
        )
        consumed = consumption.get("consumed_receipt_hashes")
        if not _nonempty_strings(consumed) or set(consumed) != set(authority_hashes):
            reject(
                "AUTHORITY_RECEIPT_SET_MISMATCH",
                "$.components.G6.evidence.target_authority_consumption.consumed_receipt_hashes",
                "target must consume the exact current G5 Authority receipt set",
            )

    effect_hash: Any = None
    if not isinstance(effect, Mapping) or effect.get("occurred") is not True:
        reject(
            "EXACT_EFFECT_BINDING_MISSING",
            "$.components.G6.evidence.effect_occurrence",
            "an operation-bound target-native occurrence is required",
        )
    else:
        _check_binding(effect, episode, reject, "$.components.G6.evidence.effect_occurrence")
        effect_hash = effect.get("effect_hash")
        if not isinstance(effect_hash, str) or not effect_hash:
            reject(
                "EXACT_EFFECT_BINDING_MISSING",
                "$.components.G6.evidence.effect_occurrence.effect_hash",
                "effect_hash is required",
            )
        constraints = effect.get("exact_constraints")
        required_constraints = {
            "circuit_id": "C7",
            "power_kw": 3.0,
            "power_tolerance_percent": 5,
            "safety_approved": True,
            "no_other_circuit": True,
            "deadline_satisfied": True,
        }
        if not isinstance(constraints, Mapping):
            reject(
                "EXACT_EFFECT_BINDING_MISSING",
                "$.components.G6.evidence.effect_occurrence.exact_constraints",
                "exact CE-001 constraints are required",
            )
        else:
            for key, expected in required_constraints.items():
                if constraints.get(key) != expected:
                    reject(
                        "EFFECT_CONSTRAINT_MISMATCH",
                        f"$.components.G6.evidence.effect_occurrence.exact_constraints.{key}",
                        f"expected {expected!r}",
                    )
            if not isinstance(constraints.get("duration_minutes"), (int, float)) or constraints.get(
                "duration_minutes", 0
            ) < 45:
                reject(
                    "EFFECT_CONSTRAINT_MISMATCH",
                    "$.components.G6.evidence.effect_occurrence.exact_constraints.duration_minutes",
                    "duration must be at least 45 minutes",
                )

    acceptance_hashes: list[str] = []
    if not isinstance(acceptances, list):
        reject(
            "ACCEPTANCE_CLOSURE_MISSING",
            "$.components.G6.evidence.owner_acceptances",
            "separate O_Q and O_V Acceptance receipts are required",
        )
    else:
        acceptance_owners = [
            item.get("owner_id") for item in acceptances if isinstance(item, Mapping)
        ]
        if len(acceptance_owners) != len(set(acceptance_owners)):
            reject(
                "DUPLICATE_ACCEPTANCE_OWNER",
                "$.components.G6.evidence.owner_acceptances",
                "repeating one owner does not increase Acceptance coverage",
            )
        if set(acceptance_owners) != REQUIRED_ACCEPTANCE_OWNERS:
            reject(
                "ACCEPTANCE_OWNER_SET_MISMATCH",
                "$.components.G6.evidence.owner_acceptances",
                "Acceptance owner set must be exactly O_Q and O_V",
            )
        for index, receipt in enumerate(acceptances):
            path = f"$.components.G6.evidence.owner_acceptances[{index}]"
            if not isinstance(receipt, Mapping):
                reject("ACCEPTANCE_BINDING_MISMATCH", path, "receipt must be an object")
                continue
            owner = receipt.get("owner_id")
            expected_source = owner_pairs.get(owner, (None, None))[1]
            if receipt.get("act_source_id") != expected_source:
                reject(
                    "ACCEPTANCE_SOURCE_MISMATCH",
                    f"{path}.act_source_id",
                    "Acceptance must come from the declared owner's act source",
                )
            _check_binding(receipt, episode, reject, path)
            if receipt.get("effect_hash") != effect_hash:
                reject(
                    "ACCEPTANCE_BINDING_MISMATCH",
                    f"{path}.effect_hash",
                    "Acceptance must bind the exact Effect",
                )
            acceptance_hash = receipt.get("acceptance_hash")
            if not isinstance(acceptance_hash, str) or not acceptance_hash:
                reject(
                    "ACCEPTANCE_BINDING_MISMATCH",
                    f"{path}.acceptance_hash",
                    "acceptance_hash is required",
                )
            else:
                acceptance_hashes.append(acceptance_hash)

    if not isinstance(finality, Mapping) or finality.get("owner_id") != "O_P":
        reject(
            "OP_FINALITY_MISSING",
            "$.components.G6.evidence.op_finality",
            "O_P must issue its own post-Acceptance obligation/finality act",
        )
    else:
        if finality.get("act_source_id") != owner_pairs.get("O_P", (None, None))[1]:
            reject(
                "OP_NOT_INDEPENDENT",
                "$.components.G6.evidence.op_finality.act_source_id",
                "O_P finality does not originate from O_P's independent act source",
            )
        if finality.get("derived_from_acceptance_object") is not False:
            reject(
                "OP_NOT_INDEPENDENT",
                "$.components.G6.evidence.op_finality.derived_from_acceptance_object",
                "O_P finality cannot be synthesized by an Acceptance object",
            )
        _check_binding(finality, episode, reject, "$.components.G6.evidence.op_finality")
        if finality.get("effect_hash") != effect_hash:
            reject(
                "OP_FINALITY_BINDING_MISMATCH",
                "$.components.G6.evidence.op_finality.effect_hash",
                "O_P finality must bind the exact Effect",
            )
        after = finality.get("after_acceptance_hashes")
        if not isinstance(after, list) or set(after) != set(acceptance_hashes):
            reject(
                "OP_FINALITY_BINDING_MISMATCH",
                "$.components.G6.evidence.op_finality.after_acceptance_hashes",
                "O_P finality must follow both exact Acceptance acts",
            )

    if str(episode.get("case_id", "")).startswith("E6"):
        _check_e6(g7, episode, effect_hash, acceptance_hashes, finality, reject)

    return _report(errors, qualified_components)


def _check_binding(
    evidence: Mapping[str, Any],
    episode: Mapping[str, Any],
    reject: Any,
    path: str,
) -> None:
    for field in ("episode_id", "q_version", "object_id", "operation_id", "target_id"):
        if evidence.get(field) != episode.get(field):
            reject(
                "EVIDENCE_BINDING_MISMATCH",
                f"{path}.{field}",
                f"must equal episode.{field}",
            )


def _check_e6(
    g7: Mapping[str, Any],
    episode: Mapping[str, Any],
    effect_hash: Any,
    acceptance_hashes: list[str],
    finality: Any,
    reject: Any,
) -> None:
    migration = _at(g7, "evidence", "migration")
    base = "$.components.G7.evidence.migration"
    if not isinstance(migration, Mapping):
        reject(
            "E6_RUNTIME_BOUNDARY_MISSING",
            base,
            "E6 requires source runtime, target runtime, and old-runtime evidence",
        )
        return

    source = migration.get("source_runtime")
    target = migration.get("target_runtime")
    if not isinstance(source, Mapping) or not isinstance(target, Mapping):
        reject(
            "E6_RUNTIME_BOUNDARY_MISSING",
            base,
            "source_runtime and target_runtime are required",
        )
    else:
        for field in ("runtime_id", "process_id", "state_boundary_id", "epoch"):
            if source.get(field) is None:
                reject(
                    "E6_RUNTIME_BOUNDARY_MISSING",
                    f"{base}.source_runtime.{field}",
                    f"source {field} is required",
                )
            if target.get(field) is None:
                reject(
                    "E6_RUNTIME_BOUNDARY_MISSING",
                    f"{base}.target_runtime.{field}",
                    f"target {field} is required",
                )
        for field in ("runtime_id", "process_id", "state_boundary_id"):
            if source.get(field) == target.get(field):
                reject(
                    "E6_RUNTIME_BOUNDARY_NOT_DISTINCT",
                    base,
                    f"source and target {field} must differ",
                )
        if (
            not isinstance(source.get("epoch"), int)
            or not isinstance(target.get("epoch"), int)
            or target.get("epoch") <= source.get("epoch")
        ):
            reject(
                "E6_RUNTIME_EPOCH_MISMATCH",
                base,
                "target runtime epoch must be an integer greater than source runtime epoch",
            )

    old = migration.get("old_runtime_restart")
    if (
        not isinstance(old, Mapping)
        or old.get("actually_restarted") is not True
        or old.get("restart_observed") is not True
        or old.get("fence_result") != "REJECTED_OLD_EPOCH"
        or old.get("presented_epoch") == old.get("current_epoch")
        or (
            isinstance(source, Mapping)
            and old.get("presented_epoch") != source.get("epoch")
        )
        or (
            isinstance(target, Mapping)
            and old.get("current_epoch") != target.get("epoch")
        )
    ):
        reject(
            "E6_OLD_EPOCH_EVIDENCE_MISSING",
            f"{base}.old_runtime_restart",
            "old runtime must actually restart and be rejected by the new epoch/fence",
        )

    lineage = migration.get("lineage_verification")
    required_hashes = (
        "capsule_hash",
        "source_runtime_hash",
        "target_runtime_hash",
        "history_prefix_hash",
    )
    if (
        not isinstance(lineage, Mapping)
        or any(not lineage.get(field) for field in required_hashes)
        or lineage.get("owner_evidence_hashes_verified") is not True
        or lineage.get("effect_hash") != effect_hash
        or lineage.get("q_version") != episode.get("q_version")
        or lineage.get("object_id") != episode.get("object_id")
        or lineage.get("history_fork_detected") is not False
        or lineage.get("effect_occurrence_count_for_operation") != 1
    ):
        reject(
            "E6_LINEAGE_EVIDENCE_MISSING",
            f"{base}.lineage_verification",
            "E6 lineage must bind capsule, runtimes, history, owner evidence, and one exact Effect occurrence",
        )

    recovery = migration.get("recovery")
    finality_hash = finality.get("finality_hash") if isinstance(finality, Mapping) else None
    if (
        not isinstance(recovery, Mapping)
        or set(recovery.get("acceptance_hashes", [])) != set(acceptance_hashes)
        or recovery.get("finality_hash") != finality_hash
        or recovery.get("recovered_from_owner_sources") is not True
    ):
        reject(
            "E6_RECOVERY_EVIDENCE_MISSING",
            f"{base}.recovery",
            "Acceptance and Settlement/finality must be recovered from owner sources",
        )


def _report(errors: list[dict[str, str]], qualified_components: list[str]) -> dict[str, Any]:
    return {
        "preflight_status": "REJECTED" if errors else "QUALIFIED_COMPONENT_OUTPUTS",
        "contract_score_status": "CONTRACT_SCORE_NOT_COMPUTED",
        "qualified_components": sorted(qualified_components),
        "rejections": errors,
        "evidence_boundary": (
            "LOCAL_SYNTHETIC_PREFLIGHT_ONLY; NOT_A_REAL_PRODUCT_RUN; "
            "NOT_CE001_CONTRACT_EVALUATION"
        ),
    }


def load_envelope(path: Path) -> dict[str, Any]:
    """Load a standalone fixture or a small explicit ``extends`` fixture."""

    with path.open(encoding="utf-8") as handle:
        document = json.load(handle)
    if "extends" not in document:
        return document

    base_path = path.parent / document["extends"]
    envelope = copy.deepcopy(load_envelope(base_path))
    for dotted_path, value in document.get("patch", {}).items():
        if dotted_path == "all_component_episode_ids":
            for component in envelope.get("components", {}).values():
                _replace_key_recursively(component, "episode_id", value)
            continue
        if dotted_path == "all_component_case_ids":
            for component in envelope.get("components", {}).values():
                _replace_key_recursively(component, "case_id", value)
            continue
        _set_dotted(envelope, dotted_path, value)
    return envelope


def _replace_key_recursively(value: Any, key: str, replacement: Any) -> None:
    if isinstance(value, dict):
        for child_key, child in value.items():
            if child_key == key:
                value[child_key] = copy.deepcopy(replacement)
            else:
                _replace_key_recursively(child, key, replacement)
    elif isinstance(value, list):
        for child in value:
            _replace_key_recursively(child, key, replacement)


def _set_dotted(document: dict[str, Any], dotted_path: str, value: Any) -> None:
    parts: list[str | int] = []
    for name, index in re.findall(r"([^\.\[\]]+)|\[(\d+)\]", dotted_path):
        parts.append(int(index) if index else name)
    current: Any = document
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = copy.deepcopy(value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("envelope", type=Path)
    args = parser.parse_args()
    envelope = load_envelope(args.envelope)
    report = validate_envelope(envelope)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["preflight_status"] == "QUALIFIED_COMPONENT_OUTPUTS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
