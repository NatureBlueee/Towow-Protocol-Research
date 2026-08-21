"""Blinded matrix runner, oracle closure, causal replay, and sealed summaries."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import inspect

from .checker import (
    BoundedModelChecker,
    json_check_result,
    meta_refactored_encoding,
)
from .execution import Evaluation, TaskEvaluator, TrialRuntime
from .model import abstract_qualified, initial_state, transition
from .policies import (
    FormationCandidate,
    MatureWorkflowComposition,
    StrongCenterHitl,
)
from .replayer import orthogonal_vector, run_replays
from .spec import (
    ACTION_BY_NAME,
    ACTION_SPECS,
    OLD_TASK,
    fingerprint,
    frozen_package,
)
from .worlds import HiddenWorld, hidden_worlds


SYSTEMS = (
    StrongCenterHitl,
    MatureWorkflowComposition,
    FormationCandidate,
)


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


def _receipt_summary(runtime: TrialRuntime) -> list[dict]:
    return [
        {
            "receipt_id": receipt.receipt_id,
            "action": receipt.action,
            "holder": receipt.holder_id,
            "executor_object_id": receipt.executor_object_id,
            "payload_hash": receipt.payload_hash,
            "effect_log_id": receipt.effect_log_id,
            "before_state_digest": receipt.before_state_digest,
            "after_state_digest": receipt.after_state_digest,
            "verified": runtime.registry.verify(receipt),
        }
        for receipt in runtime.bundle().receipts
    ]


def _run_one(world: HiddenWorld, system_type, closure) -> dict:
    runtime = TrialRuntime(world)
    system = system_type()
    policy_result = system.run(runtime.gateway())
    bundle = runtime.bundle()
    trusted_anchor = runtime.trusted_anchor()
    observed_information_hash = fingerprint(policy_result.public_facts)
    evaluation = TaskEvaluator(
        runtime.package.package_fingerprint,
        runtime.registry,
        trusted_anchor,
    ).evaluate(bundle, observed_information_hash)
    if evaluation.qualified:
        outcome = "QUALIFIED_SUCCESS"
    elif (
        policy_result.requested_terminal == "NO_QUALIFIED_POLICY_FOUND"
        and closure.closure_status == "UNSAT"
    ):
        outcome = "BOUNDED_UNREACHABLE"
    elif policy_result.requested_terminal == "REQUESTED_SUCCESS":
        outcome = "INVALID_APPARENT_SUCCESS"
    else:
        outcome = "UNRESOLVED_MODEL"

    successful_actions = [
        event.action for event in bundle.trace if event.success
    ]
    max_used_layer = max(
        (ACTION_BY_NAME[action].layer for action in successful_actions),
        default=0,
    )
    prefix_result = BoundedModelChecker().check(world, max_used_layer)
    replays = (
        run_replays(
            world,
            bundle,
            runtime.registry,
            trusted_anchor,
            observed_information_hash,
        )
        if outcome == "QUALIFIED_SUCCESS"
        else None
    )
    vector = (
        orthogonal_vector(
            bundle,
            evaluation,
            prefix_sat=prefix_result.sat,
            trusted_registry=runtime.registry,
            trusted_anchor=trusted_anchor,
        )
        if outcome == "QUALIFIED_SUCCESS"
        else {
            "C": closure.closure_status,
            "N": "NONE",
            "E": "SAME",
            "T": "INVARIANT",
            "V": "NO_QUALIFIED_EFFECT",
            "operative_token_evidence": [],
            "depth_status": "DECLARED_EXPERIMENT_LAYER_ONLY_NOT_ONTOLOGY",
        }
    )
    return {
        "public_trial_id": world.public_trial_id,
        # Revealed only after the run is sealed by this parent runner.
        "truth_id": world.truth_id,
        "system": system.name,
        "requested_terminal": policy_result.requested_terminal,
        "outcome": outcome,
        "old_task_qualified": evaluation.qualified,
        "observed_information_hash": observed_information_hash,
        "evaluation": _evaluation_json(evaluation),
        "mechanism_disposition": (
            policy_result.mechanism_disposition
            if outcome == "QUALIFIED_SUCCESS"
            else "Unknown"
        ),
        "completed_actions": list(policy_result.completed_actions),
        "trace": [
            {
                "index": event.index,
                "action": event.action,
                "actor": event.actor,
                "success": event.success,
                "receipt_id": event.receipt_id,
                "response_hash": event.response_hash,
            }
            for event in bundle.trace
        ],
        "receipts": _receipt_summary(runtime),
        "cost": sum(entry.cost for entry in bundle.ledger_entries),
        "steps": len(bundle.ledger_entries),
        "declared_layer_depth": closure.formation_depth,
        "closure_status": closure.closure_status,
        "orthogonal_vector": vector,
        "replays": replays,
    }


def _oracle(world: HiddenWorld, closure) -> dict:
    package = frozen_package(world)
    return {
        "public_trial_id": world.public_trial_id,
        "truth_id": world.truth_id,
        "frozen_package_fingerprint": package.package_fingerprint,
        "fingerprints": package.fingerprints,
        "layers": [json_check_result(result) for result in closure.layers],
        "declared_layer_depth": closure.formation_depth,
        "closure_status": closure.closure_status,
        "depth_interpretation": (
            "relative to the frozen QHM1 L0/L1/L2 representation; not an ontology"
        ),
    }


def _apply_encoded_witness(
    world: HiddenWorld,
    witness: tuple[str, ...],
):
    aliases = {
        "PROPOSE_SPEC": "PROPOSE_NEW_OPERATOR",
        "INSTALL(spec)": "REGISTER_NEW_OPERATOR",
    }
    state = initial_state(world)
    for encoded_action in witness:
        next_state = transition(
            world,
            state,
            aliases.get(encoded_action, encoded_action),
        )
        if next_state is None:
            return None
        state = next_state
    return state


def _material_vector_from_state(state) -> dict:
    return {
        "N": (
            "NEW_TOKEN"
            if state.operator_registered
            else "EXTANT_ACTIVATED"
            if state.endpoint_enabled
            else "NONE"
        ),
        "E": "CHANGED" if state.operator_registered else "SAME",
        "T": (
            "INVARIANT"
            if state.task_version == OLD_TASK.task_version
            else "DRIFTED"
        ),
        "V": "VALID" if abstract_qualified(state) else "INVALID",
    }


def _meta_refactor_gate(world: HiddenWorld) -> dict:
    checker = BoundedModelChecker()
    encoding_a = checker.check_all_layers(world)
    encoding_b = checker.check_all_layers(
        world,
        encoding=meta_refactored_encoding(),
    )
    result_a = next(
        result for result in encoding_a.layers if result.sat
    )
    result_b = next(
        result for result in encoding_b.layers if result.sat
    )
    state_a = _apply_encoded_witness(world, result_a.witness)
    state_b = _apply_encoded_witness(world, result_b.witness)
    digest_a = state_a.digest() if state_a is not None else None
    digest_b = state_b.digest() if state_b is not None else None
    material_vector_a = (
        _material_vector_from_state(state_a)
        if state_a is not None
        else None
    )
    material_vector_b = (
        _material_vector_from_state(state_b)
        if state_b is not None
        else None
    )
    return {
        "encoding_a": {
            "operator_spelling": "register_new_operator",
            "declared_layer_depth": encoding_a.formation_depth,
            "witness": list(result_a.witness),
            "final_state_digest": digest_a,
        },
        "encoding_b": {
            "operator_spelling": "install(spec)",
            "declared_layer_depth": encoding_b.formation_depth,
            "witness": list(result_b.witness),
            "final_state_digest": digest_b,
        },
        "material_vector_a": material_vector_a,
        "material_vector_b": material_vector_b,
        "same_material_transition_result": digest_a == digest_b,
        "depth_changed": (
            encoding_a.formation_depth != encoding_b.formation_depth
        ),
        "passed": (
            digest_a is not None
            and digest_a == digest_b
            and material_vector_a == material_vector_b
            and encoding_a.formation_depth == 2
            and encoding_b.formation_depth == 1
        ),
        "interpretation": (
            "depth is representation-relative; operative/material deltas "
            "do not change under this semantic-preserving refactor"
        ),
    }


def build_report() -> dict:
    checker = BoundedModelChecker()
    worlds = hidden_worlds()
    closures = {
        world.truth_id: checker.check_all_layers(world) for world in worlds
    }
    runs = [
        _run_one(world, system_type, closures[world.truth_id])
        for world in worlds
        for system_type in SYSTEMS
    ]
    success_by_system = {
        system_type().name: sorted(
            run["truth_id"]
            for run in runs
            if run["system"] == system_type().name
            and run["outcome"] == "QUALIFIED_SUCCESS"
        )
        for system_type in SYSTEMS
    }
    bounded_by_system = {
        system_type().name: sorted(
            run["truth_id"]
            for run in runs
            if run["system"] == system_type().name
            and run["outcome"] == "BOUNDED_UNREACHABLE"
        )
        for system_type in SYSTEMS
    }
    central_successes = set(
        success_by_system["same_information_strong_center_hitl"]
    )
    workflow_successes = set(
        success_by_system["mature_workflow_composition"]
    )
    candidate_successes = set(
        success_by_system["formation_candidate"]
    )
    oracle_sat_worlds = {
        truth_id
        for truth_id, closure in closures.items()
        if closure.closure_status == "SAT"
    }
    oracle_unsat_worlds = {
        truth_id
        for truth_id, closure in closures.items()
        if closure.closure_status == "UNSAT"
    }
    dispositions = sorted(
        {run["mechanism_disposition"] for run in runs}
    )
    prefix_and_new_token = [
        {
            "truth_id": run["truth_id"],
            "system": run["system"],
            "C": run["orthogonal_vector"]["C"],
            "N": run["orthogonal_vector"]["N"],
            "E": run["orthogonal_vector"]["E"],
            "authority_bound_token_verified": bool(
                run["orthogonal_vector"]["operative_token_evidence"]
                and all(
                    item["holder_executed"] and item["receipt_verified"]
                    and item["effect_record_bound"]
                    for item in run["orthogonal_vector"][
                        "operative_token_evidence"
                    ]
                )
            ),
        }
        for run in runs
        if run["orthogonal_vector"]["C"] == "SAT"
        and run["orthogonal_vector"]["N"] == "NEW_TOKEN"
    ]
    commit_vectors = [
        run["orthogonal_vector"]
        for run in runs
        if run["truth_id"] == "commit"
        and run["outcome"] == "QUALIFIED_SUCCESS"
    ]
    open_runs = [
        run for run in runs if run["truth_id"] == "open-invent"
    ]
    successful_runs = [
        run for run in runs if run["outcome"] == "QUALIFIED_SUCCESS"
    ]
    policy_implementation_fingerprints = {
        system_type().name: hashlib.sha256(
            inspect.getsource(system_type.plan).encode("utf-8")
        ).hexdigest()
        for system_type in SYSTEMS
    }
    policy_implementations_distinct = (
        len(set(policy_implementation_fingerprints.values()))
        == len(SYSTEMS)
    )
    capability_vectors = {
        system_type().name: system_type().capabilities
        for system_type in SYSTEMS
    }
    capabilities_all_equal = (
        len(set(capability_vectors.values())) == 1
    )
    policy_behavior_signatures = {
        system_type().name: hashlib.sha256(
            repr(
                tuple(
                    (
                        run["truth_id"],
                        tuple(run["completed_actions"]),
                        run["outcome"],
                    )
                    for run in runs
                    if run["system"] == system_type().name
                )
            ).encode("utf-8")
        ).hexdigest()
        for system_type in SYSTEMS
    }
    behaviorally_distinct_on_fixture = (
        len(set(policy_behavior_signatures.values())) == len(SYSTEMS)
    )
    all_systems_match_bounded_oracle = bool(oracle_sat_worlds) and all(
        set(success_by_system[system_type().name]) == oracle_sat_worlds
        and set(bounded_by_system[system_type().name])
        == oracle_unsat_worlds
        for system_type in SYSTEMS
    )
    commit_receipts_verified = bool(commit_vectors) and all(
        vector["operative_token_evidence"]
        and all(
            item["holder_executed"]
            and item["receipt_verified"]
            and item["effect_record_bound"]
            for item in vector["operative_token_evidence"]
        )
        for vector in commit_vectors
    )
    theory_gates = {
        "TOKEN-COMMIT": {
            "expected": {"C": "SAT", "N": "NEW_TOKEN", "E": "SAME"},
            "observed": [
                {key: vector[key] for key in ("C", "N", "E", "T", "V")}
                for vector in commit_vectors
            ],
            "authority_bound_receipts_verified":
                commit_receipts_verified,
            "passed": commit_receipts_verified
            and all(
                vector["C"] == "SAT"
                and vector["N"] == "NEW_TOKEN"
                and vector["E"] == "SAME"
                for vector in commit_vectors
            ),
        },
        "META-REFACTOR": _meta_refactor_gate(
            next(world for world in worlds if world.truth_id == "extend")
        ),
        "KNOWLEDGE-PROVENANCE": {
            "passed": bool(successful_runs) and all(
                run["replays"]["knowledge_only"]["provenance"][
                    "trace_and_parent_ledger_bound"
                ]
                and run["replays"]["knowledge_only"][
                    "acquisition_cost_charged"
                ]
                == 1
                and run["replays"]["knowledge_only"][
                    "privacy_cost_charged"
                ]
                == 1
                and run["replays"]["knowledge_only"][
                    "obligations_preserved"
                ]
                and run["replays"]["knowledge_only"][
                    "forged_free_information_rejected"
                ]
                and run["replays"]["knowledge_only"][
                    "unbound_runtime_information_rejected"
                ]
                and not run["replays"]["knowledge_only"][
                    "free_information_injection_used"
                ]
                for run in successful_runs
            )
        },
        "OPEN-INVENT": {
            "closure_status": closures["open-invent"].closure_status,
            "run_outcomes": sorted({run["outcome"] for run in open_runs}),
            "passed": (
                closures["open-invent"].closure_status == "UNKNOWN"
                and {run["outcome"] for run in open_runs}
                == {"UNRESOLVED_MODEL"}
                and all(
                    result.unsat_certificate is None
                    and result.unresolved_reason is not None
                    for result in closures["open-invent"].layers
                )
            ),
        },
    }
    return {
        "schema_version": "1.0",
        "experiment": "wave-008-g3-qhm1",
        "evidence_status":
            "LOCAL_FINITE_SYNTHETIC_TRUSTED_PARENT_SELF_TEST_ONLY",
        "external_calls": 0,
        "reachability_quantifiers": {
            "closure_oracle":
                "PER_WORLD_EXISTENTIAL_SEQUENCE_IN_DECLARED_FINITE_MODEL",
            "runtime_planners":
                "DETERMINISTIC_ACTUAL_POLICY_AFTER_EXACT_INSPECTION",
            "robust_across_allowed_principal_response_families":
                "NOT_TESTED",
        },
        "blinding": {
            "kind": "interface_blinding_not_hostile_filesystem_containment",
            "public_trial_order": [
                world.public_trial_id for world in worlds
            ],
            "truth_revealed_after_run": True,
        },
        "capability_parity": {
            "all_equal": capabilities_all_equal,
            "actions": [spec.name for spec in ACTION_SPECS],
            "systems": [system_type().name for system_type in SYSTEMS],
            "policy_implementation_fingerprints":
                policy_implementation_fingerprints,
            "policy_implementations_distinct":
                policy_implementations_distinct,
            "policy_behavior_signatures": policy_behavior_signatures,
            "behaviorally_distinct_on_fixture":
                behaviorally_distinct_on_fixture,
            "implementation_independence":
                "NOT_ESTABLISHED_SAME_CODEBASE_SAME_AUTHORING_STREAM",
            "comparison_scope": (
                "three same-research-stream scheduling variants; shared "
                "blocker taxonomy, action mapping, stop conditions and "
                "execution loop"
            ),
        },
        "orthogonal_vector_domains": {
            "C_closure": ["SAT", "UNSAT", "UNKNOWN"],
            "N_operative_enabling_delta": [
                "NONE",
                "EXTANT_ACTIVATED",
                "NEW_TOKEN",
            ],
            "E_kernel_policy_delta": ["SAME", "CHANGED", "UNKNOWN"],
            "T_task": ["INVARIANT", "DRIFTED", "UNKNOWN"],
            "V_validity": ["VALID", "INVALID", "NO_QUALIFIED_EFFECT"],
        },
        "prefix_sat_and_new_authority_bound_token_cases": prefix_and_new_token,
        "theory_gates": theory_gates,
        "oracle": [
            _oracle(world, closures[world.truth_id]) for world in worlds
        ],
        "runs": runs,
        "outcome_counts": dict(
            sorted(Counter(run["outcome"] for run in runs).items())
        ),
        "mechanism_dispositions": dispositions,
        "comparative_result": {
            "success_by_system": success_by_system,
            "bounded_unreachable_by_system": bounded_by_system,
            "candidate_unique_successes": sorted(
                candidate_successes
                - central_successes
                - workflow_successes
            ),
            "synthetic_existing_compositions_close_all_bounded_worlds": (
                capabilities_all_equal
                and behaviorally_distinct_on_fixture
                and
                policy_implementations_distinct
                and all_systems_match_bounded_oracle
                and all(
                    run["outcome"] == "UNRESOLVED_MODEL"
                    for run in open_runs
                )
            ),
            "new_formation_method_needed": "NOT_ESTABLISHED",
            "strong_center_synthetic_success_is_positive": (
                central_successes == oracle_sat_worlds
                and bool(oracle_sat_worlds)
            ),
            "mature_workflow_synthetic_success_is_positive": (
                workflow_successes == oracle_sat_worlds
                and bool(oracle_sat_worlds)
            ),
            "oracle_sat_worlds": sorted(oracle_sat_worlds),
            "oracle_unsat_worlds": sorted(oracle_unsat_worlds),
            "all_systems_match_bounded_oracle":
                all_systems_match_bounded_oracle,
        },
        "claim_boundary": {
            "supports": (
                "trusted-parent finite declared closure, parent-anchored "
                "runtime verification and scheduling-variant coverage in "
                "these ten synthetic scripted worlds"
            ),
            "does_not_support": (
                "real-principal consent, absolute real-world unreachability, "
                "robust policy synthesis, independent implementation, "
                "hostile same-process containment, production security, "
                "generality, business value, or a formation ontology"
            ),
        },
    }
