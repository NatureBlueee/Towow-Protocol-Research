from __future__ import annotations

import inspect
import unittest
from copy import deepcopy

from b_candidate.fixtures import ORACLE_BY_ID, PUBLIC_BY_ID
from b_candidate.model import EvidenceEvent, Proposal, Trace
from b_candidate.oracle import evaluate
from b_candidate.runner import (
    aggregate,
    run_all,
    run_arm,
    run_intervention,
    run_operator_variants,
)
from b_candidate import workers


class DiscriminatorTests(unittest.TestCase):
    def test_fixture_is_small_and_intent_ingress_is_frozen(self) -> None:
        self.assertEqual(len(PUBLIC_BY_ID), 12)
        for world in PUBLIC_BY_ID.values():
            self.assertEqual(
                world["intent"]["kind"], "IntentAtCoordinationInterface"
            )
            self.assertEqual(
                world["intent"]["upstream_vague_goal_generation"],
                "EXCLUDED_FROM_EXPERIMENT",
            )

    def test_workers_do_not_import_private_oracle_registry(self) -> None:
        source = inspect.getsource(workers)
        self.assertNotIn("ORACLE_BY_ID", source)
        self.assertNotIn("PRIVATE_ORACLES", source)
        self.assertNotIn("from .oracle", source)

    def test_public_baseline_and_t0_legal_evidence_are_separate(self) -> None:
        indexed = run_intervention("W01_PUBLIC_INDEX", "PUBLIC_BASELINE")["vector"]
        hidden = run_intervention("W02_T0_LEGAL_PATH", "PUBLIC_BASELINE")["vector"]
        legal = run_intervention(
            "W02_T0_LEGAL_PATH", "T0_LEGAL_EVIDENCE_PATH"
        )["vector"]
        self.assertTrue(indexed["eligible_positive"])
        self.assertFalse(hidden["eligible_positive"])
        self.assertTrue(legal["eligible_positive"])
        self.assertEqual(
            set(legal["candidate_sources"]), {"FROZEN_FINAL_PROPOSAL"}
        )

    def test_final_proposal_only_never_receives_t1_receipt(self) -> None:
        direct = run_intervention(
            "W03_FINAL_PROPOSAL_ONLY", "FINAL_PROPOSAL_ONLY"
        )["vector"]
        authority = run_intervention(
            "W06_POST_TREATMENT_AUTHORITY", "FINAL_PROPOSAL_ONLY"
        )["vector"]
        self.assertTrue(direct["eligible_positive"])
        self.assertFalse(authority["eligible_positive"])
        self.assertEqual(authority["observed_evidence"], [])
        self.assertFalse(authority["authority_changed"])

    def test_full_trace_returns_multi_event_vector(self) -> None:
        explanation = run_intervention(
            "W04_EXPLANATION_OPERATOR", "FULL_ACTUAL_TRACE"
        )["vector"]
        terms = run_intervention(
            "W05_TERM_CHANGE_OPERATOR", "FULL_ACTUAL_TRACE"
        )["vector"]
        authority = run_intervention(
            "W06_POST_TREATMENT_AUTHORITY", "FULL_ACTUAL_TRACE"
        )["vector"]
        capability = run_intervention(
            "W07_CAPABILITY_ADAPTER", "FULL_ACTUAL_TRACE"
        )["vector"]
        self.assertTrue(explanation["understanding_changed"])
        self.assertTrue(explanation["claimability_changed"])
        self.assertTrue(terms["terms_changed"])
        self.assertTrue(authority["authority_changed"])
        self.assertTrue(authority["qualification_created"])
        self.assertTrue(capability["capability_changed"])
        self.assertTrue(capability["qualification_created"])
        self.assertTrue(all(
            item["eligible_positive"]
            for item in (explanation, terms, authority, capability)
        ))

    def test_operator_removal_and_reversal_break_causal_success(self) -> None:
        for world_id in (
            "W04_EXPLANATION_OPERATOR",
            "W05_TERM_CHANGE_OPERATOR",
            "W06_POST_TREATMENT_AUTHORITY",
            "W07_CAPABILITY_ADAPTER",
        ):
            full = run_intervention(world_id, "FULL_ACTUAL_TRACE")["vector"]
            self.assertTrue(full["eligible_positive"], world_id)
            variants = run_operator_variants(world_id)
            self.assertEqual(len(variants), 2)
            self.assertTrue(
                all(not item["vector"]["eligible_positive"] for item in variants),
                world_id,
            )

    def test_invalidity_gate_precedes_positive_for_wrong_authority(self) -> None:
        vector = run_intervention(
            "W08_WRONG_AUTHORITY", "FULL_ACTUAL_TRACE"
        )["vector"]
        self.assertEqual(vector["boundary"], "INVALID")
        self.assertIn("WRONG_AUTHORITY", vector["validity"]["failures"])
        self.assertFalse(vector["eligible_positive"])

    def test_invalidity_gate_precedes_positive_for_forbidden_disclosure(self) -> None:
        vector = run_intervention(
            "W09_FORBIDDEN_DISCLOSURE", "FULL_ACTUAL_TRACE"
        )["vector"]
        self.assertEqual(vector["boundary"], "INVALID")
        self.assertIn("FORBIDDEN_DISCLOSURE", vector["validity"]["failures"])
        self.assertFalse(vector["eligible_positive"])

    def test_post_treatment_evidence_in_t0_arm_is_rejected(self) -> None:
        oracle = ORACLE_BY_ID["W06_POST_TREATMENT_AUTHORITY"]
        canonical = oracle["canonical_proposal"]
        trace = Trace(
            world_id=oracle["world_id"],
            arm="MALICIOUS",
            intervention="FINAL_PROPOSAL_ONLY",
            proposal=Proposal(
                path_id=canonical["path_id"],
                target=canonical["target"],
                quality_floor=canonical["quality_floor"],
                necessary_principals=tuple(canonical["necessary_principals"]),
            ),
            evidence=[
                EvidenceEvent(
                    event_id="injected",
                    path_id="P06",
                    source_id="security-receipt-t1",
                    canonical_source="security-receipt-t1",
                    authority_root="security-authority",
                    claim="grant:P06",
                    observed_at="t1",
                    existed_at_t0=False,
                    legal_at_t0=False,
                    recipient="coordinator",
                    purpose="g1_candidate_qualification",
                )
            ],
        )
        vector = evaluate(oracle, trace)
        self.assertEqual(vector["boundary"], "INVALID")
        self.assertIn(
            "POST_TREATMENT_EVIDENCE_IN_T0_ARM",
            vector["validity"]["failures"],
        )

    def test_same_source_alias_cannot_satisfy_independent_evidence(self) -> None:
        vector = run_intervention(
            "W10_SAME_SOURCE_ALIAS", "T0_LEGAL_EVIDENCE_PATH"
        )["vector"]
        self.assertEqual(vector["boundary"], "INVALID")
        self.assertIn("SAME_SOURCE_ALIAS", vector["validity"]["failures"])
        self.assertFalse(vector["eligible_positive"])

    def test_zero_disclosure_truth_transplant_does_not_change_method_output(self) -> None:
        exists_oracle = deepcopy(ORACLE_BY_ID["W11_ZERO_DISCLOSURE_EXISTS"])
        absent_oracle = deepcopy(exists_oracle)
        absent_oracle["fact_existed_at_t0"] = False
        exists = run_arm(
            "W11_ZERO_DISCLOSURE_EXISTS",
            "C_EQUAL_ACCESS",
            oracle_override=exists_oracle,
        )
        transplanted = run_arm(
            "W11_ZERO_DISCLOSURE_EXISTS",
            "C_EQUAL_ACCESS",
            oracle_override=absent_oracle,
        )
        for key in ("candidate_sources", "observed_evidence", "refusals", "boundary"):
            self.assertEqual(exists["vector"][key], transplanted["vector"][key])
        self.assertNotEqual(
            exists["vector"]["fact_existed_at_t0"],
            transplanted["vector"]["fact_existed_at_t0"],
        )

    def test_refusal_or_indistinguishability_is_not_actual_policy_miss(self) -> None:
        results = [
            run_arm(world_id, "C_EQUAL_ACCESS")
            for world_id in ("W11_ZERO_DISCLOSURE_EXISTS", "W12_ZERO_DISCLOSURE_ABSENT")
        ]
        for result in results:
            self.assertEqual(result["vector"]["d_actual"], [])
            self.assertEqual(
                result["vector"]["boundary"], "UNWILLING_TO_DISCLOSE"
            )
        summary = aggregate(results)["C_EQUAL_ACCESS"]
        self.assertEqual(summary["d_actual_denominator"], 0)
        self.assertEqual(
            summary["refused_or_indistinguishable_not_actual_miss"], 2
        )

    def test_l_benchmark_and_d_actual_are_distinct(self) -> None:
        exists = run_arm("W11_ZERO_DISCLOSURE_EXISTS", "C_EQUAL_ACCESS")["vector"]
        absent = run_arm("W12_ZERO_DISCLOSURE_ABSENT", "C_EQUAL_ACCESS")["vector"]
        self.assertEqual(exists["l_benchmark"], ["P11"])
        self.assertEqual(exists["d_actual"], [])
        self.assertEqual(absent["l_benchmark"], [])
        self.assertEqual(absent["d_actual"], [])

    def test_raw_upper_and_equal_access_are_not_conflated(self) -> None:
        raw = run_arm("W02_T0_LEGAL_PATH", "C_RAW_UPPER")["vector"]
        equal = run_arm("W02_T0_LEGAL_PATH", "C_EQUAL_ACCESS")["vector"]
        forbidden_raw = run_arm(
            "W04_EXPLANATION_OPERATOR", "C_RAW_UPPER"
        )["vector"]
        self.assertGreater(raw["cost"]["raw_exposure"], 0)
        self.assertEqual(equal["cost"]["raw_exposure"], 0)
        self.assertGreater(
            raw["cost"]["disclosure_exposure"],
            equal["cost"]["disclosure_exposure"],
        )
        self.assertTrue(raw["eligible_positive"])
        self.assertTrue(equal["eligible_positive"])
        self.assertFalse(forbidden_raw["eligible_positive"])

    def test_human_proxy_uses_same_action_envelope_and_pays_human_cost(self) -> None:
        human = run_arm("W02_T0_LEGAL_PATH", "H_EQUAL_ENVELOPE")["vector"]
        center = run_arm("W02_T0_LEGAL_PATH", "C_EQUAL_ACCESS")["vector"]
        max_actions = PUBLIC_BY_ID["W02_T0_LEGAL_PATH"]["action_envelope"][
            "max_actions"
        ]
        self.assertLessEqual(human["cost"]["actions"], max_actions)
        self.assertLessEqual(center["cost"]["actions"], max_actions)
        self.assertGreater(human["cost"]["human_minutes"], 0)
        self.assertEqual(center["cost"]["human_minutes"], 0)

    def test_target_drift_is_invalid_even_if_path_is_true(self) -> None:
        oracle = ORACLE_BY_ID["W03_FINAL_PROPOSAL_ONLY"]
        trace = Trace(
            world_id=oracle["world_id"],
            arm="MALICIOUS",
            intervention="FINAL_PROPOSAL_ONLY",
            proposal=Proposal(
                path_id="P03",
                target="ship_without_security",
                quality_floor="signed_tests_and_rollback",
                necessary_principals=("requester", "provider"),
            ),
        )
        vector = evaluate(oracle, trace)
        self.assertEqual(vector["boundary"], "INVALID")
        self.assertIn("TARGET_DRIFT", vector["validity"]["failures"])

    def test_full_fixture_expected_boundaries(self) -> None:
        for world_id, oracle in ORACLE_BY_ID.items():
            vector = run_intervention(world_id, "FULL_ACTUAL_TRACE")["vector"]
            self.assertEqual(
                vector["boundary"], oracle["expected_boundary"], world_id
            )

    def test_no_t1_receipts_in_any_t0_intervention(self) -> None:
        payload = run_all()
        for item in payload["interventions"]:
            vector = item["vector"]
            if vector["intervention"] in {
                "PUBLIC_BASELINE",
                "T0_LEGAL_EVIDENCE_PATH",
                "FINAL_PROPOSAL_ONLY",
            }:
                self.assertTrue(
                    all(
                        event["observed_at"] == "t0"
                        and event["existed_at_t0"]
                        for event in vector["observed_evidence"]
                    )
                )


if __name__ == "__main__":
    unittest.main()
