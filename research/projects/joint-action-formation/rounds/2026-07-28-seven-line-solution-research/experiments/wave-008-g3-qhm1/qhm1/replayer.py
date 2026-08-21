"""Automatic causal replays for every independently qualified runtime success."""

from __future__ import annotations

from dataclasses import asdict, replace
from itertools import combinations

from .checker import BoundedModelChecker, json_check_result
from .authorities import HolderRegistry
from .execution import (
    Evaluation,
    PublicFacts,
    TaskEvaluator,
    TrustedEvidenceAnchor,
    VerificationBundle,
)
from .model import abstract_qualified, initial_state, transition
from .spec import ACTION_BY_NAME
from .spec import fingerprint, frozen_package
from .worlds import HiddenWorld


def _evaluation_json(evaluation: Evaluation) -> dict:
    return {
        "qualified": evaluation.qualified,
        "reasons": list(evaluation.reasons),
        "authority_valid": evaluation.authority_valid,
        "target_valid": evaluation.target_valid,
        "acceptance_valid": evaluation.acceptance_valid,
        "cost_valid": evaluation.cost_valid,
        "information_valid": evaluation.information_valid,
        "evidence_seal_valid": evaluation.evidence_seal_valid,
        "task_invariant": evaluation.task_invariant,
    }


def _apply_ordered_subset(
    world: HiddenWorld,
    actions: tuple[str, ...],
    selected_indices: frozenset[int],
):
    state = initial_state(world)
    for index, action in enumerate(actions):
        if index not in selected_indices:
            continue
        next_state = transition(world, state, action)
        if next_state is None:
            return None
        state = next_state
    return state


def _intervention_ablation(
    world: HiddenWorld,
    intervention_actions: tuple[str, ...],
) -> dict:
    checker = BoundedModelChecker()
    cases = []
    sufficient: list[tuple[int, ...]] = []
    indices = tuple(range(len(intervention_actions)))
    for size in range(len(indices) + 1):
        for subset in combinations(indices, size):
            state = _apply_ordered_subset(
                world,
                intervention_actions,
                frozenset(subset),
            )
            result = (
                checker.check(world, 0, initial_override=state)
                if state is not None
                else None
            )
            sat = bool(result and result.sat)
            if sat:
                sufficient.append(subset)
            cases.append(
                {
                    "selected_indices": list(subset),
                    "selected_actions": [
                        intervention_actions[index] for index in subset
                    ],
                    "preconditions_valid": state is not None,
                    "sat": sat,
                    "l0_witness": list(result.witness) if result and result.sat else [],
                }
            )
    minimal = [
        subset
        for subset in sufficient
        if not any(
            set(other) < set(subset)
            for other in sufficient
        )
    ]
    return {
        "interventions": list(intervention_actions),
        "cases": cases,
        "minimal_sufficient_sets": [
            [intervention_actions[index] for index in subset]
            for subset in minimal
        ],
    }


def _model_diff_replay(
    world: HiddenWorld,
    l2_actions: tuple[str, ...],
) -> dict:
    checker = BoundedModelChecker()
    state = initial_state(world)
    valid = True
    for action in l2_actions:
        next_state = transition(world, state, action)
        if next_state is None:
            valid = False
            break
        state = next_state
    result = (
        checker.check(world, 0, initial_override=state)
        if valid
        else None
    )
    return {
        "exact_diff": list(l2_actions),
        "diff_preconditions_valid": valid,
        "sat": bool(result and result.sat),
        "l0_witness_after_exact_diff": (
            list(result.witness) if result and result.sat else []
        ),
        "no_diff_case_computed": not l2_actions,
    }


def _l0_plan_from_observation(
    facts: PublicFacts,
) -> tuple[str, ...] | None:
    if (
        facts.value_floor != "PASS"
        or facts.authorization != "PRESENT"
        or facts.route not in {"READY_UNADVERTISED", "READY_COMPATIBLE"}
        or facts.schema != "COMPATIBLE"
    ):
        return None
    return ("TRANSFER", "PROJECT", "ACCEPT", "READBACK")


def _execute_observation_plan(
    world: HiddenWorld,
    start,
    facts: PublicFacts,
) -> tuple[object | None, tuple[str, ...]]:
    plan = _l0_plan_from_observation(facts)
    if plan is None:
        return None, tuple()
    state = start
    for action in plan:
        next_state = transition(world, state, action)
        if next_state is None:
            return None, plan
        state = next_state
    return state, plan


def run_replays(
    world: HiddenWorld,
    bundle: VerificationBundle,
    trusted_registry: HolderRegistry,
    trusted_anchor: TrustedEvidenceAnchor,
    observed_information_hash: str,
) -> dict:
    checker = BoundedModelChecker()
    evaluator = TaskEvaluator(
        frozen_package(world).package_fingerprint,
        trusted_registry,
        trusted_anchor,
    )
    inspect_events = [
        event
        for event in bundle.trace
        if event.action == "INSPECT" and event.success and event.actor == "C"
    ]
    inspect_ledger = [
        entry
        for entry in bundle.ledger_entries
        if entry.action == "INSPECT"
        and entry.success
        and entry.actor == "C"
    ]
    inspection_records = bundle.inspection_records
    provenance_valid = (
        len(inspect_events) == 1
        and len(inspect_ledger) == 1
        and len(inspection_records) == 1
        and inspect_events[0].response_hash
        == inspection_records[0].facts_hash
        and inspect_ledger[0].response_hash
        == inspection_records[0].facts_hash
        and fingerprint(inspection_records[0].facts)
        == inspection_records[0].facts_hash
        and observed_information_hash
        == inspection_records[0].facts_hash
    )
    knowledge_start = initial_state(world)
    knowledge_start = (
        transition(world, knowledge_start, "INSPECT")
        if provenance_valid
        else None
    )
    trusted_facts = (
        inspection_records[0].facts
        if provenance_valid
        else None
    )
    knowledge_state, knowledge_plan = (
        _execute_observation_plan(
            world,
            knowledge_start,
            trusted_facts,
        )
        if knowledge_start is not None and trusted_facts is not None
        else (None, tuple())
    )
    forged_knowledge_start = replace(
        initial_state(world),
        inspected=True,
        inspection_provenance_bound=False,
        inspection_obligation_bound=False,
    )
    forged_knowledge_state, forged_knowledge_plan = (
        _execute_observation_plan(
            world,
            forged_knowledge_start,
            inspection_records[0].facts,
        )
        if inspection_records
        else (None, tuple())
    )
    fixed = checker.check(world, 1)
    successful_actions = tuple(
        event.action for event in bundle.trace if event.success
    )
    intervention_actions = tuple(
        action
        for action in successful_actions
        if ACTION_BY_NAME[action].layer in (1, 2) and action != "INSPECT"
    )
    l2_actions = tuple(
        action
        for action in successful_actions
        if ACTION_BY_NAME[action].layer == 2
    )

    authority_cases = []
    for index, receipt in enumerate(bundle.receipts):
        forged = replace(
            receipt,
            holder_id="C",
            executor_object_id="controller:self-report",
            signature="forged",
        )
        receipts = list(bundle.receipts)
        receipts[index] = forged
        evaluation = evaluator.evaluate(
            replace(bundle, receipts=tuple(receipts)),
            observed_information_hash,
        )
        authority_cases.append(
            {
                "replaced_action": receipt.action,
                "original_holder": receipt.holder_id,
                **_evaluation_json(evaluation),
            }
        )

    duplicate_records = bundle.target_records + bundle.target_records[:1]
    duplicate_evaluation = evaluator.evaluate(
        replace(bundle, target_records=duplicate_records),
        observed_information_hash,
    )
    missing_cost_evaluation = evaluator.evaluate(
        replace(bundle, ledger_entries=bundle.ledger_entries[:-1]),
        observed_information_hash,
    )
    task_drift_evaluation = evaluator.evaluate(
        replace(
            bundle,
            task_version="weak-v2",
            state=replace(bundle.state, task_version="weak-v2"),
        ),
        observed_information_hash,
    )
    unbound_information_evaluation = evaluator.evaluate(
        replace(
            bundle,
            state=replace(
                bundle.state,
                inspection_provenance_bound=False,
                inspection_obligation_bound=False,
            ),
        ),
        observed_information_hash,
    )
    old_task = evaluator.evaluate(bundle, observed_information_hash)

    return {
        "knowledge_only": {
            "sat": bool(
                knowledge_state
                and abstract_qualified(knowledge_state)
            ),
            "witness": list(knowledge_plan),
            "meaning": (
                "exact S0 plus a parent-bound observation consumed by an "
                "observation-only L0 policy; no hidden-world search for plan"
            ),
            "provenance": {
                "source_action": "INSPECT",
                "source_actor": "C",
                "trace_and_parent_ledger_bound": provenance_valid,
            },
            "acquisition_cost_charged": (
                inspect_ledger[0].cost if provenance_valid else None
            ),
            "privacy_cost_charged": (
                inspect_ledger[0].privacy_cost if provenance_valid else None
            ),
            "obligations_preserved": (
                bool(
                    knowledge_start
                    and knowledge_start.inspection_obligation_bound
                )
            ),
            "obligations": (
                ["task-bound use only", "no authority inferred from disclosure"]
                if knowledge_start
                and knowledge_start.inspection_obligation_bound
                else []
            ),
            "free_information_injection_used": bool(
                knowledge_start
                and not knowledge_start.inspection_provenance_bound
            ),
            "forged_free_information_rejected": not bool(
                forged_knowledge_state
                and abstract_qualified(forged_knowledge_state)
            ),
            "forged_free_information_result": {
                "sat": bool(
                    forged_knowledge_state
                    and abstract_qualified(forged_knowledge_state)
                ),
                "witness": list(forged_knowledge_plan),
                "reason": (
                    "inspection content lacks parent provenance and "
                    "obligation binding"
                ),
            },
            "unbound_runtime_information_rejected":
                not unbound_information_evaluation.qualified,
            "unbound_runtime_information_evaluation":
                _evaluation_json(unbound_information_evaluation),
        },
        "fixed_model_prefix": json_check_result(fixed),
        "model_diff": _model_diff_replay(world, l2_actions),
        "old_task": _evaluation_json(old_task),
        "authority_substitution": {"cases": authority_cases},
        "effect_and_cost_tampering": {
            "duplicate_effect": _evaluation_json(duplicate_evaluation),
            "missing_cost_entry": _evaluation_json(missing_cost_evaluation),
            "task_drift": _evaluation_json(task_drift_evaluation),
        },
        "intervention_subset_ablation": _intervention_ablation(
            world,
            intervention_actions,
        ),
    }


def orthogonal_vector(
    bundle: VerificationBundle,
    evaluation: Evaluation,
    prefix_sat: bool,
    trusted_registry: HolderRegistry,
    trusted_anchor: TrustedEvidenceAnchor,
) -> dict:
    actions = tuple(
        event.action for event in bundle.trace if event.success
    )
    if "ISSUE_AUTHORIZATION" in actions:
        enabling_delta = "NEW_TOKEN"
        token_action = "ISSUE_AUTHORIZATION"
    elif "REGISTER_NEW_OPERATOR" in actions:
        enabling_delta = "NEW_TOKEN"
        token_action = "REGISTER_NEW_OPERATOR"
    elif "BUILD_KNOWN_ADAPTER" in actions:
        enabling_delta = "NEW_TOKEN"
        token_action = "BUILD_KNOWN_ADAPTER"
    elif "ENABLE_ENDPOINT" in actions:
        enabling_delta = "EXTANT_ACTIVATED"
        token_action = "ENABLE_ENDPOINT"
    else:
        enabling_delta = "NONE"
        token_action = None
    receipts = [
        receipt
        for receipt in bundle.receipts
        if receipt.action == token_action
    ]
    effect_by_id = {
        record.effect_log_id: record
        for record in trusted_anchor.effect_records
    }
    token_evidence = [
        {
            "action": receipt.action,
            "holder": receipt.holder_id,
            "holder_executed": receipt.executor_object_id.startswith(
                "holder-object:"
            ),
            "receipt_verified": trusted_registry.verify(receipt),
            "effect_record_bound": bool(
                receipt.effect_log_id in effect_by_id
                and effect_by_id[
                    receipt.effect_log_id
                ].receipt_id == receipt.receipt_id
                and effect_by_id[
                    receipt.effect_log_id
                ].after_state_digest
                == receipt.after_state_digest
            ),
        }
        for receipt in receipts
    ]
    return {
        "C": "SAT" if prefix_sat else "UNSAT",
        "N": enabling_delta,
        "E": "CHANGED" if "REGISTER_NEW_OPERATOR" in actions else "SAME",
        "T": "INVARIANT" if evaluation.task_invariant else "DRIFTED",
        "V": "VALID" if evaluation.qualified else "INVALID",
        "operative_token_evidence": token_evidence,
        "depth_status": (
            "DECLARED_EXPERIMENT_LAYER_ONLY_NOT_ONTOLOGY"
        ),
    }
