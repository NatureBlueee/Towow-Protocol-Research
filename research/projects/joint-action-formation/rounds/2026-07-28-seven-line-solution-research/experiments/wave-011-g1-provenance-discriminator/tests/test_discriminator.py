from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from provenance_discriminator.evaluator import evaluate_candidate, summarize
from provenance_discriminator.model import Candidate, load_oracle, load_worlds
from provenance_discriminator.runner import build_report
from provenance_discriminator.workers import (
    equal_access_center,
    final_proposal_only,
    full_trace,
    human_equal_envelope,
    public_baseline,
    raw_upper,
)


class ProvenanceDiscriminatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.worlds = load_worlds()
        self.oracle = load_oracle()

    def evaluate(self, world_id: str, candidate: Candidate):
        trusted_arm = candidate.source_arm
        intervention = {
            "PUBLIC_BASELINE": "PUBLIC_BASELINE",
            "FINAL_PROPOSAL_ONLY": "FINAL_PROPOSAL_ONLY",
            "C_EQUAL_ACCESS": "T0_LEGAL_EVIDENCE_PATH",
            "H_EQUAL_ENVELOPE": "T0_LEGAL_EVIDENCE_PATH",
            "C_RAW_UPPER": "T0_LEGAL_EVIDENCE_PATH",
            "FULL_TRACE": "FULL_ACTUAL_TRACE",
            "FULL_TRACE_NONE": "FULL_ACTUAL_TRACE",
            "FULL_TRACE_REMOVE_OPERATOR": "REMOVE_OPERATOR",
            "FULL_TRACE_REVERSE_OPERATOR": "REVERSE_OPERATOR",
        }.get(trusted_arm, "T0_LEGAL_EVIDENCE_PATH")
        return evaluate_candidate(
            candidate,
            self.worlds[world_id],
            self.oracle[world_id],
            trusted_arm=trusted_arm,
            intervention=intervention,
        )

    def test_fixture_is_small_and_starts_at_v2_intent_interface(self) -> None:
        self.assertEqual(10, len(self.worlds))
        payload = json.loads(
            (ROOT / "fixtures" / "method_visible_worlds.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            "IntentAtCoordinationInterface",
            payload["intent_boundary"],
        )
        self.assertEqual(
            "vague-goal-to-Intent generation",
            payload["explicit_non_goal"],
        )
        self.assertTrue(
            all(re.fullmatch(r"CASE-\d{3}", world_id) for world_id in self.worlds)
        )

    def test_private_oracle_is_not_imported_by_workers(self) -> None:
        source = (
            ROOT / "provenance_discriminator" / "workers.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("load_oracle", source)
        self.assertNotIn("private_oracle", source)

    def test_indistinguishable_pair_has_same_legal_output(self) -> None:
        exists = self.worlds["CASE-006"]
        absent = self.worlds["CASE-007"]
        self.assertEqual(exists["public_transcript"], absent["public_transcript"])
        for worker in (
            public_baseline,
            equal_access_center,
            human_equal_envelope,
            raw_upper,
        ):
            left = worker(exists)
            right = worker(absent)
            self.assertEqual(left.proposal_id, right.proposal_id, worker.__name__)
            self.assertEqual(left.response_state, right.response_state, worker.__name__)

    def test_l_benchmark_and_d_actual_are_separate_denominators(self) -> None:
        self.assertEqual(9, sum(item["l_benchmark"] for item in self.oracle.values()))
        self.assertEqual(2, sum(item["d_actual"] for item in self.oracle.values()))

        public_results = [
            self.evaluate(world_id, public_baseline(world))
            for world_id, world in self.worlds.items()
        ]
        public_summary = summarize(public_results)
        self.assertEqual(9, public_summary["L_benchmark"]["denominator"])
        self.assertEqual(2, public_summary["D_actual"]["denominator"])
        self.assertEqual(["CASE-002"], public_summary["actual_policy_misses"])
        self.assertFalse(public_summary["hard_gate_pass"])

        equal_results = [
            self.evaluate(world_id, equal_access_center(world))
            for world_id, world in self.worlds.items()
        ]
        equal_summary = summarize(equal_results)
        self.assertEqual(1.0, equal_summary["D_actual"]["recall"])
        self.assertFalse(equal_summary["hard_gate_pass"])

    def test_refusal_and_indistinguishability_are_not_actual_policy_misses(self) -> None:
        for world_id in (
            "CASE-006",
            "CASE-008",
        ):
            result = self.evaluate(
                world_id,
                equal_access_center(self.worlds[world_id]),
            )
            self.assertFalse(result.d_actual)
            self.assertFalse(result.counts_as_actual_policy_miss)
            self.assertNotEqual("ABSENT", result.response_state)

    def test_invalidity_gate_runs_before_declared_positive_label(self) -> None:
        candidate = public_baseline(self.worlds["CASE-004"])
        candidate = replace(candidate, declared_labels=("INDEX_HIT", "PASS"))
        result = self.evaluate("CASE-004", candidate)
        self.assertEqual("INVALID", result.validity)
        self.assertIn("WRONG_AUTHORITY", result.invalidity_reasons)
        self.assertFalse(result.discovered)

    def test_g1_handoff_cannot_overpromote_lifecycle_state(self) -> None:
        candidate = replace(
            public_baseline(self.worlds["CASE-001"]),
            status="COMMITMENT",
        )
        result = self.evaluate("CASE-001", candidate)
        self.assertEqual("INVALID", result.validity)
        self.assertIn("G1_STATUS_OVERPROMOTION", result.invalidity_reasons)

    def test_target_q_and_necessary_principals_are_hard_gates(self) -> None:
        valid = public_baseline(self.worlds["CASE-001"])
        mutations = (
            (replace(valid, target="ship_without_security"), "TARGET_DRIFT"),
            (replace(valid, q_version="Q-G1-mutated"), "Q_DRIFT"),
            (
                replace(valid, principals=("product-owner",)),
                "NECESSARY_PRINCIPAL_REMOVED",
            ),
        )
        for candidate, reason in mutations:
            with self.subTest(reason=reason):
                result = self.evaluate("CASE-001", candidate)
                self.assertIn(reason, result.invalidity_reasons)
                self.assertFalse(result.discovered)

    def test_truth_transplant_is_rejected(self) -> None:
        source = equal_access_center(self.worlds["CASE-002"])
        transplanted = replace(
            source,
            world_id="CASE-001",
            proposal_id="P01",
        )
        result = self.evaluate("CASE-001", transplanted)
        self.assertEqual("INVALID", result.validity)
        self.assertIn(
            "UNKNOWN_OR_CROSS_WORLD_EVIDENCE",
            result.invalidity_reasons,
        )

    def test_post_treatment_evidence_cannot_enter_t0_replay(self) -> None:
        candidate = Candidate(
            world_id="CASE-003",
            proposal_id="P03",
            evidence_ids=("E03-T1-RECEIPT",),
            source_arm="FINAL_PROPOSAL_ONLY",
        )
        result = self.evaluate("CASE-003", candidate)
        self.assertEqual("INVALID", result.validity)
        self.assertIn("POST_TREATMENT_EVIDENCE", result.invalidity_reasons)

        replayed = final_proposal_only(
            self.worlds["CASE-003"]
        )
        self.assertEqual((), replayed.evidence_ids)
        self.assertIn(
            "MISSING_QUALIFICATION_EVIDENCE",
            self.evaluate("CASE-003", replayed).invalidity_reasons,
        )

    def test_forbidden_disclosure_is_rejected_even_with_true_fact(self) -> None:
        candidate = Candidate(
            world_id="CASE-005",
            proposal_id="P05",
            evidence_ids=("E05-FORBIDDEN",),
            source_arm="C_EQUAL_ACCESS",
        )
        result = self.evaluate("CASE-005", candidate)
        self.assertIn("FORBIDDEN_DISCLOSURE", result.invalidity_reasons)
        self.assertFalse(result.discovered)

    def test_same_source_alias_cannot_satisfy_independence(self) -> None:
        result = self.evaluate(
            "CASE-010",
            public_baseline(self.worlds["CASE-010"]),
        )
        self.assertEqual("INVALID", result.validity)
        self.assertIn("SAME_SOURCE_ALIAS", result.invalidity_reasons)

    def test_operator_removal_and_reversal_are_causal_not_labels(self) -> None:
        cases = {
            "CASE-003": "capability_changed",
            "CASE-009": "terms_changed",
        }
        for world_id, event_key in cases.items():
            world = self.worlds[world_id]
            actual = self.evaluate(world_id, full_trace(world))
            removed = self.evaluate(
                world_id,
                full_trace(world, mutation="REMOVE_OPERATOR"),
            )
            reversed_result = self.evaluate(
                world_id,
                full_trace(world, mutation="REVERSE_OPERATOR"),
            )
            self.assertEqual("VALID", actual.validity, world_id)
            self.assertTrue(actual.event_vector[event_key], world_id)
            self.assertTrue(actual.event_vector["qualification_created"], world_id)
            self.assertEqual("NON_SUCCESS", removed.validity, world_id)
            self.assertEqual("INVALID", reversed_result.validity, world_id)
            self.assertIn("REVOKED_EVIDENCE", reversed_result.invalidity_reasons)

    def test_event_vector_keeps_multiple_events(self) -> None:
        result = self.evaluate(
            "CASE-009",
            full_trace(self.worlds["CASE-009"]),
        )
        self.assertTrue(result.event_vector["terms_changed"])
        self.assertTrue(result.event_vector["claimability_changed"])
        self.assertTrue(result.event_vector["qualification_created"])
        self.assertFalse(result.event_vector["authority_changed"])

    def test_center_and_human_share_action_envelope_but_costs_are_counted(self) -> None:
        world = self.worlds["CASE-002"]
        self.assertEqual(
            set(world["equal_action_envelope"]),
            set(world["human_action_envelope"]),
        )
        center = self.evaluate("CASE-002", equal_access_center(world))
        human = self.evaluate("CASE-002", human_equal_envelope(world))
        self.assertTrue(center.discovered)
        self.assertTrue(human.discovered)
        self.assertEqual(0, center.cost_account["human_minutes"])
        self.assertGreater(human.cost_account["human_minutes"], 0)

    def test_raw_upper_is_separate_and_pays_exposure(self) -> None:
        world = self.worlds["CASE-002"]
        upper = self.evaluate("CASE-002", raw_upper(world))
        equal = self.evaluate("CASE-002", equal_access_center(world))
        self.assertTrue(upper.discovered)
        self.assertGreater(
            upper.cost_account["exposure_units"],
            equal.cost_account["exposure_units"],
        )

    def test_candidate_cannot_self_report_cost(self) -> None:
        world = self.worlds["CASE-002"]
        candidate = replace(
            equal_access_center(world),
            cost={
                "model_calls": 0,
                "exposure_units": 0,
                "human_minutes": 0,
                "wait_units": 0,
            },
        )
        result = self.evaluate("CASE-002", candidate)
        self.assertEqual(world["arm_costs"]["C_EQUAL_ACCESS"], result.cost_account)

    def test_candidate_cannot_change_trusted_arm_or_intervention(self) -> None:
        world = self.worlds["CASE-003"]
        candidate = Candidate(
            world_id="CASE-003",
            proposal_id="P03",
            evidence_ids=("E03-T1-RECEIPT",),
            source_arm="FULL_TRACE",
            cost={"exposure_units": 0},
        )
        result = evaluate_candidate(
            candidate,
            world,
            self.oracle["CASE-003"],
            trusted_arm="C_EQUAL_ACCESS",
            intervention="T0_LEGAL_EVIDENCE_PATH",
        )
        self.assertIn("POST_TREATMENT_EVIDENCE", result.invalidity_reasons)
        self.assertEqual(
            world["arm_costs"]["C_EQUAL_ACCESS"],
            result.cost_account,
        )

    def test_runner_is_executable_and_emits_all_replays(self) -> None:
        report = build_report()
        self.assertEqual(
            {
                "PUBLIC_BASELINE",
                "C_EQUAL_ACCESS",
                "H_EQUAL_ENVELOPE",
                "C_RAW_UPPER",
                "FINAL_PROPOSAL_ONLY",
                "FULL_TRACE",
                "REMOVE_OPERATOR",
                "REVERSE_OPERATOR",
            },
            set(report["arms"]),
        )
        self.assertEqual(
            len(report["worker_implementation_sha256"]),
            len(set(report["worker_implementation_sha256"].values())),
        )
        self.assertEqual(
            "LEAK_FREE_EVALUATION_AGAINST_REFLECTIVE_OR_MALICIOUS_WORKER",
            report["cannot_support"],
        )
        self.assertEqual(
            report["population_receipt"],
            build_report()["population_receipt"],
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "provenance_discriminator.runner",
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            self.assertEqual(
                "wave011-g1-provenance-discriminator-v1",
                json.loads(output.read_text(encoding="utf-8"))["schema_version"],
            )


if __name__ == "__main__":
    unittest.main()
