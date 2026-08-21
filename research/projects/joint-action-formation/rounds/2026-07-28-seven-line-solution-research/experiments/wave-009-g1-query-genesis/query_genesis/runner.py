"""Trusted experiment runner and report construction."""

from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import inspect
import json
from typing import Any, Iterable

from .evaluator import (
    evaluate_truth,
    expected_q_state,
    principal_accepts_query,
    q_evidence_constructor,
)
from .evidence import ParentRuntime, QueryDraft
from .spec import DISCLOSURE_VECTOR_KEYS
from .strategies import (
    ExpressedIndexARD,
    LocalProjection,
    PlatformDirectControl,
    PrivacyPredicateProvider,
    ReciprocalProbe,
    RouterComposition,
    StrongCenterLocalOracle,
)
from .worlds import HiddenWorld, derive_truth, hidden_worlds


STRATEGY_TYPES = (
    ExpressedIndexARD,
    LocalProjection,
    StrongCenterLocalOracle,
    PrivacyPredicateProvider,
    ReciprocalProbe,
    RouterComposition,
    PlatformDirectControl,
)

TRUSTED_STRATEGY_REGISTRY = {
    ExpressedIndexARD: "expressed_index_ard",
    LocalProjection: "local_projection",
    StrongCenterLocalOracle: "strong_center_local_oracle",
    PrivacyPredicateProvider: "privacy_predicate_provider",
    ReciprocalProbe: "reciprocal_probe",
    RouterComposition: "router_composition",
    PlatformDirectControl: "platform_direct_control",
}

NATIVE_FAMILIES = {
    "expressed_index_ard": {"E", "U", "S"},
    "local_projection": {"E", "N", "Q", "Z", "C"},
    "strong_center_local_oracle": {"E", "U", "S", "N", "Q", "Z", "R", "P", "C"},
    "privacy_predicate_provider": {"P"},
    "reciprocal_probe": {"R"},
    "router_composition": {"E", "U", "S", "N", "Q", "Z", "R", "P", "C"},
    "platform_direct_control": {"T5"},
}


def _form_audit_query(gateway):
    seed = gateway.observe_goal_seed().seed
    clarifications = []
    for facet in ("PURPOSE", "DIRECTION", "CONSTRAINTS", "VERSION"):
        response = gateway.request_principal_clarification(seed, facet)
        if response.clarification is None:
            return None
        clarifications.append(response.clarification)
    values = {item.facet: item.value for item in clarifications}
    draft = QueryDraft(
        origin=seed.origin,
        purpose=values["PURPOSE"],
        direction=values["DIRECTION"],
        constraints=tuple(values["CONSTRAINTS"]),
        version=values["VERSION"],
        provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
    )
    return gateway.form_query(seed, tuple(clarifications), draft).query


def run_one(
    world: HiddenWorld,
    strategy_type: type,
    *,
    candidate_claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a candidate while deriving all trusted fields in the parent."""

    canonical_strategy_id = TRUSTED_STRATEGY_REGISTRY.get(strategy_type)
    if canonical_strategy_id is None:
        raise ValueError("candidate type is absent from the parent strategy registry")
    runtime = ParentRuntime(
        world,
        canonical_strategy_id=canonical_strategy_id,
        strategy_code_identity=sha256(
            inspect.getsource(strategy_type.run).encode()
        ).hexdigest(),
    )
    runtime.note_candidate_claims(candidate_claims)
    candidate_return = strategy_type.run(runtime.gateway())
    bundle = runtime.evidence_bundle()
    return {
        "public_trial_id": world.public_trial_id,
        "truth_id": world.truth_id,
        "family": world.family,
        "strategy_id": runtime.strategy_id,
        "candidate_diagnostic": {
            "status": "UNTRUSTED_NOT_USED_FOR_SCORING",
            "returned_keys": sorted(candidate_return)
            if isinstance(candidate_return, dict)
            else [],
        },
        "trusted_metrics": bundle["summary"],
        "handoffs": tuple(bundle["handoffs"]),
        "parent_anchor_names": tuple(sorted(bundle["anchors"])),
        "parent_evidence_seal_valid": runtime.verify_bundle(bundle),
        "candidate_claims_disposition": bundle["candidate_claims_disposition"],
    }


def _empty_vector() -> dict[str, Any]:
    return {
        "origin_facts": 0,
        "recipients": 0,
        "sensitivity": {},
        "retention_units": 0,
        "onward_hops": 0,
        "depth": 0,
        "cryptographic_leakage_bits": 0,
        "policy_violations": 0,
    }


def _aggregate_vector(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    aggregate = _empty_vector()
    for result in results:
        vector = result["trusted_metrics"]["disclosure_vector"]
        for key in (
            "origin_facts",
            "recipients",
            "retention_units",
            "onward_hops",
            "cryptographic_leakage_bits",
            "policy_violations",
        ):
            aggregate[key] += vector[key]
        aggregate["depth"] = max(aggregate["depth"], vector["depth"])
        for level, count in vector["sensitivity"].items():
            aggregate["sensitivity"][level] = (
                aggregate["sensitivity"].get(level, 0) + count
            )
    return aggregate


def _metrics_row(
    strategy_id: str,
    results: list[dict[str, Any]],
    worlds_by_id: dict[str, HiddenWorld],
    *,
    scope: str,
) -> dict[str, Any]:
    t1_results = [result for result in results if result["family"] != "T5"]
    positives = [
        result
        for result in t1_results
        if evaluate_truth(worlds_by_id[result["truth_id"]]).d_actual
    ]
    negatives = [
        result
        for result in t1_results
        if not evaluate_truth(worlds_by_id[result["truth_id"]]).handoff
    ]
    hits = sum(result["trusted_metrics"]["handoff"] for result in positives)
    safe = sum(
        not result["trusted_metrics"]["handoff"]
        and result["trusted_metrics"]["disclosure_vector"]["policy_violations"] == 0
        for result in negatives
    )
    recall = hits / len(positives) if positives else 0.0
    robust_safety = safe / len(negatives) if negatives else 1.0
    vector = _aggregate_vector(results)
    row = {
        "strategy_id": strategy_id,
        "scope": scope,
        "actual_policy_recall": round(recall, 6),
        "robust_safety": round(robust_safety, 6),
        "qualified_handoffs": sum(
            result["trusted_metrics"]["handoff"] for result in results
        ),
        "operation_cost": round(
            sum(result["trusted_metrics"]["operation_cost"] for result in results),
            3,
        ),
        "latency_units": round(
            sum(result["trusted_metrics"]["latency_units"] for result in results),
            3,
        ),
        "disclosure_vector": vector,
    }
    if scope == "COMPONENT_NATIVE":
        row["native_world_count"] = len(results)
    else:
        row["world_count"] = len(results)
    return row


def _pareto(rows: list[dict[str, Any]]) -> list[str]:
    def dominates(left: dict[str, Any], right: dict[str, Any]) -> bool:
        left_values = (
            left["actual_policy_recall"],
            left["robust_safety"],
            -left["operation_cost"],
            -left["latency_units"],
            -left["disclosure_vector"]["cryptographic_leakage_bits"],
        )
        right_values = (
            right["actual_policy_recall"],
            right["robust_safety"],
            -right["operation_cost"],
            -right["latency_units"],
            -right["disclosure_vector"]["cryptographic_leakage_bits"],
        )
        return all(a >= b for a, b in zip(left_values, right_values)) and any(
            a > b for a, b in zip(left_values, right_values)
        )

    return [
        row["strategy_id"]
        for row in rows
        if not any(
            other is not row and dominates(other, row)
            for other in rows
        )
    ]


def build_report() -> dict[str, Any]:
    worlds = hidden_worlds()
    worlds_by_id = {world.truth_id: world for world in worlds}
    frozen_truth = [
        {
            "truth_id": world.truth_id,
            "family": world.family,
            "L": evaluate_truth(world).latent,
            "D_actual": evaluate_truth(world).d_actual,
            "H": evaluate_truth(world).handoff,
            "reachable_paths": evaluate_truth(world).reachable_paths,
        }
        for world in worlds
    ]
    frozen_truth_sha256 = sha256(
        json.dumps(frozen_truth, sort_keys=True).encode()
    ).hexdigest()
    strategy_ids = [
        TRUSTED_STRATEGY_REGISTRY[strategy] for strategy in STRATEGY_TYPES
    ]
    matrix = {
        TRUSTED_STRATEGY_REGISTRY[strategy]: [
            run_one(world, strategy)
            for world in worlds
        ]
        for strategy in STRATEGY_TYPES
    }

    end_to_end = [
        _metrics_row(
            TRUSTED_STRATEGY_REGISTRY[strategy],
            matrix[TRUSTED_STRATEGY_REGISTRY[strategy]],
            worlds_by_id,
            scope="END_TO_END_22_WORLDS",
        )
        for strategy in STRATEGY_TYPES
    ]
    component = []
    for strategy in STRATEGY_TYPES:
        strategy_id = TRUSTED_STRATEGY_REGISTRY[strategy]
        native = [
            result
            for result in matrix[strategy_id]
            if result["family"] in NATIVE_FAMILIES[strategy_id]
        ]
        component.append(
            _metrics_row(
                strategy_id,
                native,
                worlds_by_id,
                scope="COMPONENT_NATIVE",
            )
        )

    causal_behavior_signatures: dict[str, str] = {}
    implementation_code_identities: dict[str, str] = {}
    for strategy in STRATEGY_TYPES:
        strategy_id = TRUSTED_STRATEGY_REGISTRY[strategy]
        semantic = [
            {
                "trace": result["trusted_metrics"]["semantic_trace"],
                "handoff": result["trusted_metrics"]["handoff"],
                "terminal": result["trusted_metrics"]["terminal"],
                "q_evidence_constructor": result["trusted_metrics"][
                    "q_evidence_constructor"
                ],
            }
            for result in matrix[strategy_id]
        ]
        causal_behavior_signatures[strategy_id] = sha256(
            json.dumps(semantic, sort_keys=True).encode()
        ).hexdigest()
        implementation_code_identities[strategy_id] = sha256(
            inspect.getsource(strategy.run).encode()
        ).hexdigest()

    zero_pair = ("Z-EXISTS", "Z-ABSENT")
    zero_gate: dict[str, bool] = {}
    for strategy in STRATEGY_TYPES:
        strategy_id = TRUSTED_STRATEGY_REGISTRY[strategy]
        by_truth = {
            result["truth_id"]: result
            for result in matrix[strategy_id]
        }
        left = by_truth[zero_pair[0]]["trusted_metrics"]
        right = by_truth[zero_pair[1]]["trusted_metrics"]
        zero_gate[strategy_id] = (
            left["semantic_trace"] == right["semantic_trace"]
            and left["handoff"] == right["handoff"]
            and left["disclosure_events"] == right["disclosure_events"]
            and left["terminal"] == right["terminal"]
        )

    router_by_truth = {
        result["truth_id"]: result
        for result in matrix["router_composition"]
    }
    q_constructor_to_state = {
        "LOCAL_TRUTH_PERMITTED_PROJECTION": "UNEXPRESSED",
        "AUTHORITY_TIMEOUT": "UNKNOWN",
        "AUTHORITY_SIGNED_REFUSAL": "UNWILLING_TO_DISCLOSE",
        "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION": "ABSENT",
    }
    q_ids = (
        "Q-UNEXPRESSED",
        "Q-UNKNOWN",
        "Q-UNWILLING",
        "Q-ABSENT",
    )
    q_observed = {
        truth_id: q_constructor_to_state.get(
            router_by_truth[truth_id]["trusted_metrics"][
                "q_evidence_constructor"
            ],
            "UNKNOWN",
        )
        for truth_id in q_ids
    }
    expected_q = {
        truth_id: expected_q_state(worlds_by_id[truth_id])
        for truth_id in q_ids
    }
    q_constructors = {
        truth_id: q_evidence_constructor(worlds_by_id[truth_id])
        for truth_id in q_ids
    }
    all_handoffs = [
        handoff
        for results in matrix.values()
        for result in results
        for handoff in result["handoffs"]
    ]

    t5_gate: dict[str, dict[str, Any]] = {}
    for strategy in STRATEGY_TYPES:
        strategy_id = TRUSTED_STRATEGY_REGISTRY[strategy]
        t5 = [
            result
            for result in matrix[strategy_id]
            if result["family"] == "T5"
        ]
        t5_gate[strategy_id] = {
            "disclosure_events": sum(
                result["trusted_metrics"]["disclosure_events"] for result in t5
            ),
            "probe_calls": sum(
                result["trusted_metrics"]["probe_calls"] for result in t5
            ),
            "terminals": [
                result["trusted_metrics"]["terminal"] for result in t5
            ],
            "canonical_parent_state_machine": [
                run["canonical_parent_state_machine"]
                for result in t5
                for run in result["trusted_metrics"]["platform_runs"]
            ],
            "readback_confirmed": [
                run["readback_confirmed"]
                for result in t5
                for run in result["trusted_metrics"]["platform_runs"]
            ],
            "domain_kinds": [
                run["domain_kind"]
                for result in t5
                for run in result["trusted_metrics"]["platform_runs"]
            ],
            "target_domain_effects": [
                {
                    "target_domain": run["target_domain"],
                    "effect_applied": run["effect_applied"],
                    "before": run["before"],
                    "after": run["after"],
                }
                for result in t5
                for run in result["trusted_metrics"]["platform_runs"]
            ],
        }

    stale_results = [
        result
        for results in matrix.values()
        for result in results
        if result["truth_id"] == "S-REVOKED"
    ]
    one_sided_results = [
        result
        for results in matrix.values()
        for result in results
        if result["truth_id"] == "R-ONE-SIDED"
    ]

    invalid_runtime = ParentRuntime(
        worlds_by_id["E-INDEXED"],
        canonical_strategy_id="runner_query_injection_check",
    )
    invalid_response = invalid_runtime.gateway().search_index(
        "candidate-supplied-oracle-query"
    )

    exact_once_runtime = ParentRuntime(
        worlds_by_id["S-ACTIVE"],
        canonical_strategy_id="runner_exact_once_check",
    )
    exact_gateway = exact_once_runtime.gateway()
    exact_query = _form_audit_query(exact_gateway)
    exact_candidate = exact_gateway.search_index(exact_query)
    exact_current = exact_gateway.read_current_head(exact_candidate.candidate_ref)
    exact_first = exact_gateway.handoff((exact_current.ref,))
    exact_second = exact_gateway.handoff((exact_current.ref,))

    dynamic_runtime = ParentRuntime(
        worlds_by_id["S-REVOKED"],
        canonical_strategy_id="runner_dynamic_revoke_check",
    )
    dynamic_gateway = dynamic_runtime.gateway()
    dynamic_query = _form_audit_query(dynamic_gateway)
    dynamic_candidate = dynamic_gateway.search_index(dynamic_query)
    dynamic_current = dynamic_gateway.read_current_head(
        dynamic_candidate.candidate_ref
    )
    dynamic_handoff = dynamic_gateway.handoff((dynamic_current.ref,))

    duplicate_runtime = ParentRuntime(
        worlds_by_id["S-ACTIVE"],
        canonical_strategy_id="runner_duplicate_ref_check",
    )
    duplicate_gateway = duplicate_runtime.gateway()
    duplicate_query = _form_audit_query(duplicate_gateway)
    duplicate_candidate = duplicate_gateway.search_index(duplicate_query)
    duplicate_current = duplicate_gateway.read_current_head(
        duplicate_candidate.candidate_ref
    )
    duplicate_same_call = duplicate_gateway.handoff(
        (duplicate_current.ref, duplicate_current.ref)
    )

    clarification_statuses = {}
    for truth_id in ("N-NO-FACT", "P-NO-PREDICATE", "Z-EXISTS", "Z-ABSENT"):
        clarification_runtime = ParentRuntime(
            worlds_by_id[truth_id],
            canonical_strategy_id=f"runner_clarification:{truth_id}",
        )
        clarification_gateway = clarification_runtime.gateway()
        value_seed = clarification_gateway.observe_goal_seed().seed
        clarification_statuses[truth_id] = (
            clarification_gateway.request_principal_clarification(
                value_seed,
                "PURPOSE",
            ).status
        )
    genesis_runtime = ParentRuntime(
        worlds_by_id["E-INDEXED"],
        canonical_strategy_id="runner_genesis_acceptance_check",
    )
    genesis_query = _form_audit_query(genesis_runtime.gateway())
    executable_preimage_sha256 = genesis_runtime.evidence_bundle()[
        "anchors"
    ]["executable_preimage"]

    unregistered_world = replace(
        worlds_by_id["T5-DIRECT"],
        platform_task=replace(
            worlds_by_id["T5-DIRECT"].platform_task,
            target_domain="unregistered_external_domain",
        ),
    )
    unregistered_runtime = ParentRuntime(
        unregistered_world,
        canonical_strategy_id="runner_unregistered_domain_check",
    )
    unregistered_result = unregistered_runtime.gateway().platform_direct()

    all_seals_valid = all(
        result["parent_evidence_seal_valid"]
        for results in matrix.values()
        for result in results
    )
    center_row = next(
        row
        for row in end_to_end
        if row["strategy_id"] == "strong_center_local_oracle"
    )
    router_row = next(
        row
        for row in end_to_end
        if row["strategy_id"] == "router_composition"
    )
    comparison_fields = (
        "actual_policy_recall",
        "robust_safety",
        "operation_cost",
        "latency_units",
        "disclosure_vector",
    )
    center_router_identical = all(
        center_row[field] == router_row[field] for field in comparison_fields
    )
    return {
        "experiment_id": "T1-HW-C/QUERY-GENESIS-DISCOVERY",
        "strategy_ids": strategy_ids,
        "world_count": len(worlds),
        "family_count": len({world.family for world in worlds}),
        "denominators": {
            "latent": sum(evaluate_truth(world).latent for world in worlds),
            "d_actual": sum(evaluate_truth(world).d_actual for world in worlds),
            "handoff_truth": sum(
                evaluate_truth(world).handoff for world in worlds
            ),
        },
        "frozen_truth": frozen_truth,
        "frozen_truth_sha256": frozen_truth_sha256,
        "executable_preimage_sha256": executable_preimage_sha256,
        "component_native_table": component,
        "end_to_end_table": end_to_end,
        "pareto_frontier": _pareto(end_to_end),
        "optimized_center_vs_router": {
            "result": (
                "CAUSALLY_IDENTICAL_UNDER_FROZEN_MATRIX"
                if center_router_identical
                else "DIFFERENT"
            ),
            "compared_fields": comparison_fields,
            "router_cost_advantage_claimed": False,
        },
        "strategy_independence": {
            "implementation_code_identities": implementation_code_identities,
            "causal_behavior_signatures": causal_behavior_signatures,
            "causal_signature_basis": "ordered semantic operation/status, handoff, terminal, authority-evidence constructor; no public identifiers",
            "causal_equivalence_classes": {
                signature: sorted(
                    strategy_id
                    for strategy_id, value in causal_behavior_signatures.items()
                    if value == signature
                )
                for signature in sorted(set(causal_behavior_signatures.values()))
            },
            "gate_passed": (
                len(set(implementation_code_identities.values()))
                == len(STRATEGY_TYPES)
                and center_router_identical
                and causal_behavior_signatures["strong_center_local_oracle"]
                == causal_behavior_signatures["router_composition"]
            ),
            "shared_run_implementation": False,
        },
        "gates": {
            "ZERO-DISCLOSURE-INDISTINGUISHABILITY": {
                "passed": all(zero_gate.values()),
                "per_strategy": zero_gate,
            },
            "STALE-REVOCATION": {
                "passed": all(
                    not result["trusted_metrics"]["handoff"]
                    for result in stale_results
                )
                and dynamic_current.status == "CURRENT_COMPAT"
                and dynamic_handoff.status == "GOAL_QUERY_HEAD_ADVANCED",
                "dynamic_qualification_then_revoke": dynamic_handoff.status,
            },
            "ONE-SIDED-PROBE": {
                "passed": all(
                    not result["trusted_metrics"]["handoff"]
                    for result in one_sided_results
                ),
            },
            "FOUR-STATE-SEPARATION": {
                "passed": q_observed == expected_q,
                "router_observed": q_observed,
                "evaluator_expected": expected_q,
                "evidence_constructors": q_constructors,
            },
            "NO-CROSS-LINE-PROMOTION": {
                "passed": bool(all_handoffs)
                and all(
                    handoff["status"] == "CANDIDATE_NOT_COMMITMENT"
                    and not handoff["commitment"]
                    and not handoff["authority"]
                    and not handoff["capability"]
                    for handoff in all_handoffs
                ),
                "handoff_count": len(all_handoffs),
                "handoffs": all_handoffs,
            },
            "T5-BYPASS": {
                "passed": all(
                    values["disclosure_events"] == 0
                    and values["probe_calls"] == 0
                    and set(values["terminals"])
                    == {"PLATFORM_COMPLETED", "PLATFORM_NO_MATCH"}
                    and len(values["canonical_parent_state_machine"]) == 2
                    and len(values["readback_confirmed"]) == 2
                    and all(values["canonical_parent_state_machine"])
                    and all(values["readback_confirmed"])
                    and set(values["domain_kinds"]) == {"INTERNAL_SYNTHETIC"}
                    for values in t5_gate.values()
                )
                and unregistered_result.status
                == "UNREGISTERED_TARGET_DOMAIN",
                "per_strategy": t5_gate,
                "unregistered_target_domain": unregistered_result.status,
            },
            "NO-ORACLE-DERIVED-QUERY-INJECTION": {
                "passed": invalid_response.status
                == "INVALID_QUERY_PROVENANCE"
                and invalid_runtime.query_injection_rejected,
            },
            "PARENT-OWNED-ANCHORS": {
                "passed": all_seals_valid,
                "candidate_identity_cost_log_head_truth_accepted": False,
                "seal_bindings": [
                    "world_modes_and_policies",
                    "cost_table",
                    "strategy_registry",
                    "strategy_implementation",
                    "evaluator_version",
                    "world_model_version",
                    "operation_log",
                    "current_heads",
                    "semantic_queries",
                    "target_domain_registry",
                    "executable_preimage",
                ],
            },
            "HANDOFF-EXACTLY-ONCE": {
                "passed": exact_first.status == "CANDIDATE_NOT_COMMITMENT"
                and exact_second.status == "EVIDENCE_ALREADY_CONSUMED"
                and len(exact_once_runtime.handoffs) == 1
                and duplicate_same_call.status
                == "DUPLICATE_REFERENCE_IN_HANDOFF"
                and not duplicate_runtime.handoffs,
                "same_call_duplicate_rejected": (
                    duplicate_same_call.status
                    == "DUPLICATE_REFERENCE_IN_HANDOFF"
                    and not duplicate_runtime.handoffs
                ),
                "first": exact_first.status,
                "duplicate": exact_second.status,
                "same_reference_same_call": duplicate_same_call.status,
            },
            "SYNTHETIC-QUERY-GENESIS": {
                "passed": genesis_query is not None
                and principal_accepts_query(
                    worlds_by_id["E-INDEXED"],
                    genesis_query,
                )
                and clarification_statuses
                == {
                    "N-NO-FACT": "CLARIFICATION_AMBIGUOUS",
                    "P-NO-PREDICATE": "PRINCIPAL_REFUSED_CLARIFICATION",
                    "Z-EXISTS": "ZERO_DISCLOSURE",
                    "Z-ABSENT": "ZERO_DISCLOSURE",
                },
                "candidate_visible_start": (
                    "PUBLIC_LOGICAL_API_VAGUE_VALUE_SEED_ONLY_"
                    "FOR_COOPERATIVE_NON_REFLECTIVE_CANDIDATE"
                ),
                "visibility_scope": (
                    "PUBLIC_LOGICAL_API_ONLY; SAME_PROCESS_REFLECTION_EXCLUDED"
                ),
                "formation": "PRINCIPAL_CLARIFICATION_TO_CANDIDATE_DRAFT_TO_ACCEPTANCE",
                "independent_evaluator_acceptance": (
                    genesis_query is not None
                    and principal_accepts_query(
                        worlds_by_id["E-INDEXED"],
                        genesis_query,
                    )
                ),
                "paired_outcomes": clarification_statuses,
            },
            "TRUTH-FREEZE-INDEPENDENT-EVALUATOR": {
                "passed": all(
                    world.latent_truth == evaluate_truth(world).latent
                    and world.d_actual_truth == evaluate_truth(world).d_actual
                    and world.handoff_truth == evaluate_truth(world).handoff
                    for world in worlds
                ),
            },
        },
        "truth_layer_boundary": {
            "primary_recall_denominator": "D_actual",
            "latent_not_discoverable_counted_as_miss": False,
            "false_absence_in_open_world": "PROHIBITED",
        },
        "migration_status": {
            "T4_FULL_JOINT_BID": "NOT_RUN",
            "G2_COMMITMENT_FORMATION": "NOT_RUN",
            "QUERY_GENESIS": "LOCAL_SYNTHETIC_RUN",
        },
        "research_claims": {
            "real_world_effectiveness": "UNKNOWN",
            "candidate_only_advantage": "NOT_ESTABLISHED",
            "existing_center_platform_composition": "POSITIVE_LOCAL_SYNTHETIC",
            "query_genesis_scope": (
                "COOPERATIVE_NON_REFLECTIVE_CANDIDATE_OVER_PUBLIC_LOGICAL_API"
            ),
        },
        "security_claims": {
            "hostile_same_process_isolation": False,
            "same_process_reflection_can_reach_parent_hidden_world": True,
            "logical_request_only_gateway": (
                "COOPERATIVE_NON_REFLECTIVE_API_CONTRACT_ONLY"
            ),
            "class_or_module_callable_rebinding_detected": True,
            "instance_level_shadowing_out_of_scope": True,
            "seal_verifier_replacement_out_of_scope": True,
            "not_a_hard_gate": True,
        },
        "external_calls": 0,
        "evidence_status": "LOCAL_SYNTHETIC_SAME_AUTHORING_STREAM",
        "limitations": [
            "Only the public logical API gives a cooperative non-reflective candidate a vague seed; same-process reflection can reach ParentRuntime and its hidden world.",
            "Controller/candidate isolation is an in-process discipline, not an OS security boundary or hard gate.",
            "Worlds, strategies, and evaluator share one authoring stream; this is not independent evidence.",
            "No real participant, production authority, long-duration drift, or full T4 joint-bid task was run.",
            "Executable-preimage checks cover class/module callable rebinding, including consumed imported aliases; instance-level shadowing, direct replacement of the seal verifier, and same-permission malicious processes are outside the trusted-parent threat model.",
        ],
    }


def main() -> None:
    print(json.dumps(build_report(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
