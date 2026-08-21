from __future__ import annotations

import inspect
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest

import query_genesis.evidence as evidence_module
from query_genesis.authority_evidence import semantic_scope
from query_genesis.evaluator import (
    evaluate_truth,
    expected_q_state,
    principal_accepts_query,
)
from query_genesis.evidence import ParentRuntime, QueryDraft
from query_genesis.runner import (
    STRATEGY_TYPES,
    build_report,
    run_one,
)
from query_genesis.strategies import (
    ExpressedIndexARD,
    LocalProjection,
    PlatformDirectControl,
    PrivacyPredicateProvider,
    ReciprocalProbe,
    RouterComposition,
    StrongCenterLocalOracle,
)
from query_genesis.worlds import (
    derive_truth,
    hidden_worlds,
)


class QueryGenesisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worlds = {world.truth_id: world for world in hidden_worlds()}

    def form_query(self, gateway):
        seed = gateway.observe_goal_seed().seed
        clarifications = tuple(
            gateway.request_principal_clarification(seed, facet).clarification
            for facet in ("PURPOSE", "DIRECTION", "CONSTRAINTS", "VERSION")
        )
        values = {item.facet: item.value for item in clarifications}
        draft = QueryDraft(
            origin=seed.origin,
            purpose=values["PURPOSE"],
            direction=values["DIRECTION"],
            constraints=values["CONSTRAINTS"],
            version=values["VERSION"],
            provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
        )
        return gateway.form_query(seed, clarifications, draft)

    def test_query_genesis_starts_vague_and_candidate_forms_query(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="audit:true-query-genesis",
        )
        gateway = runtime.gateway()
        issued = gateway.observe_goal_seed()
        self.assertEqual("VAGUE_VALUE_SEED_ISSUED", issued.status)
        self.assertEqual("timely confidential language help", issued.seed.value)
        self.assertFalse(hasattr(issued.seed, "purpose"))
        self.assertFalse(hasattr(issued.seed, "direction"))
        self.assertFalse(hasattr(issued.seed, "constraints"))

        formed = self.form_query(gateway)
        self.assertEqual("QUERY_ACCEPTED_BY_PRINCIPAL", formed.status)
        self.assertEqual(
            "SYNTHETIC_PRINCIPAL_CLARIFICATION",
            formed.query.provenance,
        )
        self.assertEqual(
            "DIRECTION_FOUND",
            gateway.search_index(formed.query).status,
        )
        self.assertTrue(
            principal_accepts_query(
                self.worlds["E-INDEXED"],
                formed.query,
            )
        )
        second_seed = gateway.observe_goal_seed().seed
        second_clarifications = tuple(
            gateway.request_principal_clarification(second_seed, facet).clarification
            for facet in ("PURPOSE", "DIRECTION", "CONSTRAINTS", "VERSION")
        )
        wrong_draft = QueryDraft(
            origin=second_seed.origin,
            purpose="discover_translation_partner",
            direction="provide_finance",
            constraints=("confidential", "within_24h"),
            version=1,
            provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
        )
        rejected = gateway.form_query(
            second_seed,
            second_clarifications,
            wrong_draft,
        )
        self.assertEqual("QUERY_REJECTED_BY_PRINCIPAL", rejected.status)
        self.assertFalse(
            principal_accepts_query(
                self.worlds["E-INDEXED"],
                wrong_draft,
            )
        )

    def test_ambiguity_refusal_and_zero_disclosure_are_frozen(self) -> None:
        cases = {
            "N-NO-FACT": "CLARIFICATION_AMBIGUOUS",
            "P-NO-PREDICATE": "PRINCIPAL_REFUSED_CLARIFICATION",
            "Z-EXISTS": "ZERO_DISCLOSURE",
            "Z-ABSENT": "ZERO_DISCLOSURE",
        }
        for truth_id, expected in cases.items():
            gateway = ParentRuntime(
                self.worlds[truth_id],
                canonical_strategy_id=f"audit:{truth_id}",
            ).gateway()
            seed = gateway.observe_goal_seed().seed
            response = gateway.request_principal_clarification(seed, "PURPOSE")
            self.assertEqual(expected, response.status, truth_id)
            self.assertIsNone(response.clarification)
        self.assertEqual(
            self.worlds["Z-EXISTS"].public_initial_transcript,
            self.worlds["Z-ABSENT"].public_initial_transcript,
        )

    def test_ten_families_and_all_twenty_two_worlds_are_frozen(self) -> None:
        self.assertEqual(22, len(self.worlds))
        self.assertEqual(
            {"E", "U", "S", "N", "Q", "Z", "R", "P", "C", "T5"},
            {world.family for world in self.worlds.values()},
        )
        self.assertEqual(
            4,
            sum(world.family == "Q" for world in self.worlds.values()),
        )
        self.assertEqual(
            2,
            sum(world.family == "Z" for world in self.worlds.values()),
        )
        public_ids = {world.public_trial_id for world in self.worlds.values()}
        self.assertEqual(22, len(public_ids))
        self.assertTrue(
            all(
                world.truth_id not in world.public_trial_id
                for world in self.worlds.values()
            )
        )

    def test_runner_derives_l_d_h_truth_from_frozen_action_graph(self) -> None:
        import query_genesis.evaluator as evaluator

        evaluator_source = inspect.getsource(evaluator)
        self.assertNotIn("d_actual_truth", evaluator_source)
        self.assertNotIn("handoff_truth", evaluator_source)
        derived = {
            truth_id: evaluate_truth(world)
            for truth_id, world in self.worlds.items()
        }
        for truth_id, truth in derived.items():
            world = self.worlds[truth_id]
            self.assertEqual(world.latent_truth, truth.latent, truth_id)
            self.assertEqual(world.d_actual_truth, truth.d_actual, truth_id)
            self.assertEqual(world.handoff_truth, truth.handoff, truth_id)
        self.assertEqual(10, sum(item.d_actual for item in derived.values()))
        self.assertEqual(10, sum(item.handoff for item in derived.values()))
        self.assertFalse(derived["Z-EXISTS"].d_actual)
        self.assertFalse(derived["Z-ABSENT"].d_actual)

    def test_public_seed_pairs_change_truth_without_label_leakage(self) -> None:
        self.assertEqual(
            self.worlds["N-NEW-FACT"].public_value_seed,
            self.worlds["N-NO-FACT"].public_value_seed,
        )
        self.assertNotEqual(
            evaluate_truth(self.worlds["N-NEW-FACT"]).d_actual,
            evaluate_truth(self.worlds["N-NO-FACT"]).d_actual,
        )
        self.assertEqual(
            self.worlds["Z-EXISTS"].public_value_seed,
            self.worlds["Z-ABSENT"].public_value_seed,
        )
        self.assertNotEqual(
            evaluate_truth(self.worlds["Z-EXISTS"]).latent,
            evaluate_truth(self.worlds["Z-ABSENT"]).latent,
        )
        self.assertEqual(
            self.worlds["Z-EXISTS"].public_initial_transcript,
            self.worlds["Z-ABSENT"].public_initial_transcript,
        )

    def test_query_is_semantic_signed_and_content_tamper_is_rejected(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="attack:semantic-query",
        )
        gateway = runtime.gateway()
        issued = self.form_query(gateway)
        query = issued.query
        self.assertEqual("requester:A", query.origin)
        self.assertEqual("discover_translation_partner", query.purpose)
        self.assertEqual("provide_translation", query.direction)
        self.assertEqual(("confidential", "within_24h"), query.constraints)
        self.assertEqual(1, query.version)
        self.assertEqual("SYNTHETIC_PRINCIPAL_CLARIFICATION", query.provenance)
        self.assertTrue(query.signature)

        forged = replace(query, direction="provide_finance")
        rejected = gateway.search_index(forged)
        self.assertEqual("INVALID_QUERY_PROVENANCE", rejected.status)
        accepted = gateway.search_index(query)
        self.assertEqual("DIRECTION_FOUND", accepted.status)

    def test_gateway_is_request_only_and_rejects_query_injection(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="mutation:query-injector",
        )
        gateway = runtime.gateway()
        self.assertFalse(hasattr(gateway, "truth"))
        self.assertFalse(hasattr(gateway, "log"))
        self.assertFalse(hasattr(gateway, "cost"))
        self.assertFalse(hasattr(gateway, "identity"))
        result = gateway.search_index("fabricated-oracle-query")
        self.assertEqual("INVALID_QUERY_PROVENANCE", result.status)
        self.assertEqual(0, len(runtime.handoffs))
        self.assertTrue(runtime.query_injection_rejected)

    def test_strategies_do_not_import_hidden_worlds_or_share_one_run(self) -> None:
        import query_genesis.strategies as strategies

        source = inspect.getsource(strategies)
        self.assertNotIn("from .worlds", source)
        self.assertNotIn("import worlds", source)
        run_sources = {
            inspect.getsource(strategy_type.run)
            for strategy_type in STRATEGY_TYPES
        }
        self.assertEqual(len(STRATEGY_TYPES), len(run_sources))

        report = build_report()
        independence = report["strategy_independence"]
        signatures = independence["causal_behavior_signatures"]
        code_ids = independence["implementation_code_identities"]
        self.assertEqual(len(STRATEGY_TYPES), len(set(code_ids.values())))
        self.assertEqual(
            signatures["strong_center_local_oracle"],
            signatures["router_composition"],
        )
        self.assertNotIn("trial", independence["causal_signature_basis"])
        self.assertTrue(report["strategy_independence"]["gate_passed"])

    def test_all_end_to_end_arms_have_exact_gateway_capability_parity(self) -> None:
        capability_sets = {
            strategy_type.capabilities
            for strategy_type in STRATEGY_TYPES
        }
        self.assertEqual(1, len(capability_sets))
        self.assertEqual(
            (
                "observe_goal_seed",
                "request_principal_clarification",
                "form_query",
                "poll_local_trigger",
                "emit_projection",
                "search_index",
                "read_current_head",
                "private_match",
                "request_probe",
                "handoff",
                "platform_direct",
                "stop",
            ),
            next(iter(capability_sets)),
        )

    def test_zero_disclosure_pair_is_indistinguishable_for_every_arm(self) -> None:
        report = build_report()
        gate = report["gates"]["ZERO-DISCLOSURE-INDISTINGUISHABILITY"]
        self.assertTrue(gate["passed"])
        self.assertEqual(set(report["strategy_ids"]), set(gate["per_strategy"]))
        self.assertTrue(all(gate["per_strategy"].values()))

    def test_stale_revocation_one_sided_and_four_state_gates(self) -> None:
        report = build_report()
        self.assertTrue(report["gates"]["STALE-REVOCATION"]["passed"])
        self.assertTrue(report["gates"]["ONE-SIDED-PROBE"]["passed"])
        self.assertTrue(report["gates"]["FOUR-STATE-SEPARATION"]["passed"])
        self.assertEqual(
            {
                "Q-UNEXPRESSED": "UNEXPRESSED",
                "Q-UNKNOWN": "UNKNOWN",
                "Q-UNWILLING": "UNWILLING_TO_DISCLOSE",
                "Q-ABSENT": "ABSENT",
            },
            report["gates"]["FOUR-STATE-SEPARATION"]["router_observed"],
        )
        self.assertTrue(self.worlds["R-ONE-SIDED"].latent_resources)
        self.assertEqual(
            "SIGNED_REFUSAL",
            self.worlds["R-ONE-SIDED"].reciprocal_response.kind,
        )

    def test_q_states_are_evidence_constructed_not_direct_labels(self) -> None:
        expected = {
            "Q-UNEXPRESSED": "UNEXPRESSED",
            "Q-UNKNOWN": "UNKNOWN",
            "Q-UNWILLING": "UNWILLING_TO_DISCLOSE",
            "Q-ABSENT": "ABSENT",
        }
        self.assertEqual(
            expected,
            {
                truth_id: expected_q_state(self.worlds[truth_id])
                for truth_id in expected
            },
        )
        report = build_report()
        constructors = report["gates"]["FOUR-STATE-SEPARATION"][
            "evidence_constructors"
        ]
        self.assertEqual("LOCAL_TRUTH_PERMITTED_PROJECTION", constructors["Q-UNEXPRESSED"])
        self.assertEqual("AUTHORITY_TIMEOUT", constructors["Q-UNKNOWN"])
        self.assertEqual("AUTHORITY_SIGNED_REFUSAL", constructors["Q-UNWILLING"])
        self.assertEqual(
            "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
            constructors["Q-ABSENT"],
        )

    def test_malformed_or_unrelated_q_evidence_becomes_unknown_invalid(self) -> None:
        original = self.worlds["Q-UNWILLING"]
        for field, value in (
            ("kind", "POPULATION_COMPLETENESS"),
            ("scope", semantic_scope("unrelated", "scope", ())),
        ):
            malformed_refusal = replace(
                original.local_authority.refusal,
                **{field: value},
            )
            malformed_world = replace(
                original,
                local_authority=replace(
                    original.local_authority,
                    refusal=malformed_refusal,
                ),
            )
            self.assertEqual("UNKNOWN", expected_q_state(malformed_world))
            runtime = ParentRuntime(
                malformed_world,
                canonical_strategy_id=f"audit:malformed-{field}",
            )
            gateway = runtime.gateway()
            query = self.form_query(gateway).query
            observed = gateway.poll_local_trigger(query, "STANDARD")
            self.assertEqual("INVALID_AUTHORITY_EVIDENCE", observed.status)
            self.assertIsNone(
                runtime.trusted_summary()["q_evidence_constructor"]
            )

    def test_handoff_never_promotes_g2_or_other_lines(self) -> None:
        report = build_report()
        gate = report["gates"]["NO-CROSS-LINE-PROMOTION"]
        self.assertTrue(gate["passed"])
        self.assertGreater(gate["handoff_count"], 0)
        self.assertTrue(
            all(
                item["status"] == "CANDIDATE_NOT_COMMITMENT"
                and not item["commitment"]
                and not item["authority"]
                and not item["capability"]
                for item in gate["handoffs"]
            )
        )

    def test_t5_bypass_has_no_disclosure_or_probe_for_every_arm(self) -> None:
        report = build_report()
        gate = report["gates"]["T5-BYPASS"]
        self.assertTrue(gate["passed"])
        self.assertEqual(set(report["strategy_ids"]), set(gate["per_strategy"]))
        for metrics in gate["per_strategy"].values():
            self.assertEqual(0, metrics["disclosure_events"])
            self.assertEqual(0, metrics["probe_calls"])
            self.assertEqual(
                {"PLATFORM_COMPLETED", "PLATFORM_NO_MATCH"},
                set(metrics["terminals"]),
            )
            self.assertTrue(all(metrics["canonical_parent_state_machine"]))
            self.assertTrue(all(metrics["readback_confirmed"]))
            self.assertEqual(
                {"INTERNAL_SYNTHETIC"},
                set(metrics["domain_kinds"]),
            )

    def test_t5_rejects_unregistered_target_domain(self) -> None:
        base = self.worlds["T5-DIRECT"]
        unregistered = replace(
            base,
            platform_task=replace(
                base.platform_task,
                target_domain="external_unregistered_domain",
            ),
        )
        runtime = ParentRuntime(
            unregistered,
            canonical_strategy_id="audit:t5-domain-registry",
        )
        result = runtime.gateway().platform_direct()
        self.assertEqual("UNREGISTERED_TARGET_DOMAIN", result.status)
        run = runtime.trusted_summary()["platform_runs"][0]
        self.assertFalse(run["effect_applied"])
        self.assertEqual(run["before"], run["after"])
        self.assertEqual("INTERNAL_SYNTHETIC", run["domain_kind"])

    def test_dynamic_qualification_then_revoke_and_exact_once(self) -> None:
        revoked = ParentRuntime(
            self.worlds["S-REVOKED"],
            canonical_strategy_id="attack:post-qualification-revoke",
        )
        gateway = revoked.gateway()
        query = self.form_query(gateway).query
        candidate = gateway.search_index(query)
        current = gateway.read_current_head(candidate.candidate_ref)
        self.assertEqual("CURRENT_COMPAT", current.status)
        denied = gateway.handoff((current.ref,))
        self.assertEqual("GOAL_QUERY_HEAD_ADVANCED", denied.status)
        self.assertEqual([], revoked.handoffs)

        active = ParentRuntime(
            self.worlds["S-ACTIVE"],
            canonical_strategy_id="attack:exact-once",
        )
        active_gateway = active.gateway()
        active_query = self.form_query(active_gateway).query
        active_candidate = active_gateway.search_index(active_query)
        active_current = active_gateway.read_current_head(
            active_candidate.candidate_ref
        )
        first = active_gateway.handoff((active_current.ref,))
        second = active_gateway.handoff((active_current.ref,))
        self.assertEqual("CANDIDATE_NOT_COMMITMENT", first.status)
        self.assertEqual("EVIDENCE_ALREADY_CONSUMED", second.status)
        self.assertEqual(1, len(active.handoffs))

    def test_same_reference_twice_in_one_handoff_is_atomic_rejection(self) -> None:
        runtime = ParentRuntime(
            self.worlds["S-ACTIVE"],
            canonical_strategy_id="attack:same-ref-twice",
        )
        gateway = runtime.gateway()
        query = self.form_query(gateway).query
        candidate = gateway.search_index(query)
        current = gateway.read_current_head(candidate.candidate_ref)
        duplicate = gateway.handoff((current.ref, current.ref))
        self.assertEqual("DUPLICATE_REFERENCE_IN_HANDOFF", duplicate.status)
        self.assertEqual([], runtime.handoffs)
        single = gateway.handoff((current.ref,))
        self.assertEqual("CANDIDATE_NOT_COMMITMENT", single.status)
        self.assertEqual(1, len(runtime.handoffs))

    def test_qualified_evidence_expires_before_handoff(self) -> None:
        runtime = ParentRuntime(
            self.worlds["S-ACTIVE"],
            canonical_strategy_id="attack:expiry",
        )
        gateway = runtime.gateway()
        query = self.form_query(gateway).query
        candidate = gateway.search_index(query)
        current = gateway.read_current_head(candidate.candidate_ref)
        for _ in range(21):
            gateway.observe_goal_seed()
        expired = gateway.handoff((current.ref,))
        self.assertEqual("EVIDENCE_EXPIRED", expired.status)
        self.assertEqual([], runtime.handoffs)

    def test_parent_owns_identity_cost_log_heads_and_bundle_seal(self) -> None:
        baseline = run_one(
            self.worlds["S-ACTIVE"],
            RouterComposition,
        )
        malicious = run_one(
            self.worlds["S-ACTIVE"],
            RouterComposition,
            candidate_claims={
                "identity": "candidate:forged",
                "cost": -999,
                "clear_log": True,
                "current_head": "ACTIVE-v0",
                "truth": "HANDOFF",
            },
        )
        self.assertEqual(
            baseline["trusted_metrics"],
            malicious["trusted_metrics"],
        )
        self.assertEqual(
            "router_composition",
            malicious["strategy_id"],
        )
        self.assertTrue(malicious["parent_evidence_seal_valid"])
        self.assertEqual(
            "IGNORED_UNTRUSTED_CANDIDATE_CLAIMS",
            malicious["candidate_claims_disposition"],
        )

    def test_unregistered_candidate_cannot_claim_a_registered_identity(self) -> None:
        class ForgedRouter:
            strategy_id = "router_composition"
            capabilities = RouterComposition.capabilities

            @staticmethod
            def run(gateway):
                return {
                    "identity": "router_composition",
                    "cost": -1000,
                    "truth": "HANDOFF",
                }

        with self.assertRaises(ValueError):
            run_one(self.worlds["E-INDEXED"], ForgedRouter)

    def test_opaque_evidence_cannot_be_replayed_across_parent_runtimes(self) -> None:
        first = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="attack:first",
        )
        first_gateway = first.gateway()
        query = self.form_query(first_gateway)
        direction = first_gateway.search_index(query.query)
        current = first_gateway.read_current_head(direction.candidate_ref)

        second = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="attack:second",
        )
        replay = second.gateway().handoff((current.ref,))
        self.assertEqual("HANDOFF_REJECTED", replay.status)
        self.assertEqual([], second.handoffs)

    def test_component_native_and_end_to_end_tables_are_separate(self) -> None:
        report = build_report()
        component = report["component_native_table"]
        end_to_end = report["end_to_end_table"]
        self.assertEqual(7, len(component))
        self.assertEqual(7, len(end_to_end))
        self.assertTrue(
            all(row["scope"] == "COMPONENT_NATIVE" for row in component)
        )
        self.assertTrue(
            all(row["scope"] == "END_TO_END_22_WORLDS" for row in end_to_end)
        )
        self.assertTrue(
            all("native_world_count" in row for row in component)
        )
        self.assertTrue(
            all(row["world_count"] == 22 for row in end_to_end)
        )

    def test_metrics_use_d_actual_and_report_disclosure_pareto(self) -> None:
        report = build_report()
        self.assertEqual(10, report["denominators"]["d_actual"])
        self.assertEqual(10, report["denominators"]["handoff_truth"])
        router = next(
            row
            for row in report["end_to_end_table"]
            if row["strategy_id"] == "router_composition"
        )
        center = next(
            row
            for row in report["end_to_end_table"]
            if row["strategy_id"] == "strong_center_local_oracle"
        )
        self.assertEqual(1.0, router["actual_policy_recall"])
        self.assertEqual(1.0, router["robust_safety"])
        self.assertEqual(1.0, center["actual_policy_recall"])
        self.assertEqual(1.0, center["robust_safety"])
        for key in (
            "actual_policy_recall",
            "robust_safety",
            "operation_cost",
            "latency_units",
            "disclosure_vector",
        ):
            self.assertEqual(center[key], router[key], key)
        self.assertEqual(
            "CAUSALLY_IDENTICAL_UNDER_FROZEN_MATRIX",
            report["optimized_center_vs_router"]["result"],
        )
        for row in report["end_to_end_table"]:
            vector = row["disclosure_vector"]
            self.assertEqual(
                {
                    "origin_facts",
                    "recipients",
                    "sensitivity",
                    "retention_units",
                    "onward_hops",
                    "depth",
                    "cryptographic_leakage_bits",
                    "policy_violations",
                },
                set(vector),
            )
        self.assertTrue(report["pareto_frontier"])

    def test_report_preserves_not_run_unknown_and_no_candidate_advantage_claim(self) -> None:
        report = build_report()
        self.assertEqual(0, report["external_calls"])
        self.assertEqual(
            "NOT_RUN",
            report["migration_status"]["T4_FULL_JOINT_BID"],
        )
        self.assertEqual(
            "LOCAL_SYNTHETIC_RUN",
            report["migration_status"]["QUERY_GENESIS"],
        )
        self.assertTrue(report["gates"]["SYNTHETIC-QUERY-GENESIS"]["passed"])
        self.assertEqual(
            "UNKNOWN",
            report["research_claims"]["real_world_effectiveness"],
        )
        self.assertEqual(
            "NOT_ESTABLISHED",
            report["research_claims"]["candidate_only_advantage"],
        )
        self.assertEqual(
            "LOCAL_SYNTHETIC_SAME_AUTHORING_STREAM",
            report["evidence_status"],
        )
        self.assertFalse(report["security_claims"]["hostile_same_process_isolation"])
        self.assertTrue(
            report["security_claims"][
                "same_process_reflection_can_reach_parent_hidden_world"
            ]
        )
        self.assertEqual(
            "COOPERATIVE_NON_REFLECTIVE_API_CONTRACT_ONLY",
            report["security_claims"]["logical_request_only_gateway"],
        )
        self.assertTrue(
            report["security_claims"][
                "class_or_module_callable_rebinding_detected"
            ]
        )
        self.assertTrue(
            report["security_claims"]["instance_level_shadowing_out_of_scope"]
        )
        self.assertTrue(
            report["security_claims"]["seal_verifier_replacement_out_of_scope"]
        )
        self.assertNotIn("HOSTILE-SAME-PROCESS", report["gates"])

    def test_parent_seals_bind_models_policies_costs_and_versions(self) -> None:
        report = build_report()
        bindings = report["gates"]["PARENT-OWNED-ANCHORS"]["seal_bindings"]
        self.assertEqual(
            {
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
            },
            set(bindings),
        )

    def test_runtime_method_replacement_invalidates_existing_seal(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="audit:method-replacement",
        )
        self.form_query(runtime.gateway())
        bundle = runtime.evidence_bundle()
        self.assertTrue(runtime.verify_bundle(bundle))
        original = ParentRuntime._request_handoff
        try:
            ParentRuntime._request_handoff = lambda self, refs: None
            self.assertFalse(runtime.verify_bundle(bundle))
        finally:
            ParentRuntime._request_handoff = original

    def test_unlisted_valid_query_replacement_also_invalidates_seal(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="audit:unlisted-method-replacement",
        )
        self.form_query(runtime.gateway())
        bundle = runtime.evidence_bundle()
        self.assertTrue(runtime.verify_bundle(bundle))
        original = ParentRuntime._valid_query
        try:
            ParentRuntime._valid_query = lambda self, query: True
            self.assertFalse(runtime.verify_bundle(bundle))
        finally:
            ParentRuntime._valid_query = original

    def test_consumed_verify_authority_alias_rebinding_invalidates_seal(self) -> None:
        runtime = ParentRuntime(
            self.worlds["Q-UNWILLING"],
            canonical_strategy_id="audit:authority-alias-rebinding",
        )
        bundle = runtime.evidence_bundle()
        original = evidence_module.verify_authority_evidence
        try:
            evidence_module.verify_authority_evidence = (
                lambda *args, **kwargs: True
            )
            self.assertFalse(runtime.verify_bundle(bundle))
        finally:
            evidence_module.verify_authority_evidence = original

    def test_consumed_semantic_scope_alias_rebinding_invalidates_seal(self) -> None:
        runtime = ParentRuntime(
            self.worlds["E-INDEXED"],
            canonical_strategy_id="audit:scope-alias-rebinding",
        )
        bundle = runtime.evidence_bundle()
        original = evidence_module.semantic_scope
        try:
            evidence_module.semantic_scope = lambda *args, **kwargs: "forged"
            self.assertFalse(runtime.verify_bundle(bundle))
        finally:
            evidence_module.semantic_scope = original

    def test_executable_preimage_is_stable_across_python_processes(self) -> None:
        script = textwrap.dedent(
            """
            from query_genesis.evidence import ParentRuntime
            from query_genesis.worlds import hidden_worlds
            world = next(item for item in hidden_worlds() if item.truth_id == "E-INDEXED")
            runtime = ParentRuntime(world, canonical_strategy_id="audit:subprocess-stability")
            print(runtime.evidence_bundle()["anchors"]["executable_preimage"])
            """
        )
        cwd = str(Path(__file__).resolve().parents[1])
        outputs = [
            subprocess.check_output(
                [sys.executable, "-c", script],
                cwd=cwd,
                env={**os.environ, "PYTHONHASHSEED": hash_seed},
                text=True,
            ).strip()
            for hash_seed in ("1", "2")
        ]
        self.assertEqual(outputs[0], outputs[1])


if __name__ == "__main__":
    unittest.main()
