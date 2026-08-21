from __future__ import annotations

import base64
from dataclasses import replace
import inspect
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g1prov.evaluator import (
    evaluate_trace,
    line_local_envelope_violations,
)
from g1prov.fixtures import EPISODE_IDS, make_world
from g1prov.method import EvidenceFirstDiscovery
from g1prov.model import EvidenceEvent, Trace, digest
from g1prov.runner import build_report, run_episode, validate_method_input
from g1prov.session import DiscoverySession


class G1ProvenanceModuleTests(unittest.TestCase):
    def _raw_trace(self, episode_id: str = "E1-EXTANT-MULTI-OWNER"):
        world = make_world(episode_id)
        trace = Trace(
            episode_id=episode_id,
            intervention="T0_REPLAY",
            method=EvidenceFirstDiscovery().name,
        )
        session = DiscoverySession(
            world,
            trace,
            allow_t0_queries=True,
            allow_operators=False,
        )
        EvidenceFirstDiscovery().run(session)
        return world, trace

    def test_clarification_prelude_is_linked_but_not_method_input(self) -> None:
        world = make_world("E1-EXTANT-MULTI-OWNER")
        self.assertEqual(
            digest(world.prelude),
            world.interface["clarification_prelude_receipt_hash"],
        )
        self.assertEqual("CLARIFICATION_PRELUDE", world.prelude["stage"])
        self.assertEqual(
            "IntentAtCoordinationInterface",
            world.interface["boundary"],
        )
        rendered = json.dumps(world.interface, sort_keys=True)
        for forbidden in (
            "vague_request",
            "questions",
            "intent_candidate_version",
            "explain_back",
            "o_q_claim",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_method_has_no_oracle_fixture_or_final_proposal_dependency(self) -> None:
        source = inspect.getsource(
            sys.modules[EvidenceFirstDiscovery.__module__]
        )
        self.assertNotIn("from .fixtures", source)
        self.assertNotIn("from .evaluator", source)
        self.assertNotIn("final_proposal", source)
        self.assertNotIn("controller_operator_ids", source)
        self.assertNotIn("apply_operator", source)
        interface = make_world("E1-EXTANT-MULTI-OWNER").interface
        for forbidden in (
            "L_benchmark",
            "D_actual",
            "correct_path",
            "t0_paths",
            "final_proposal",
        ):
            self.assertNotIn(forbidden, interface)
        with self.assertRaisesRegex(ValueError, "final_proposal"):
            validate_method_input(
                {
                    **interface,
                    "nested": {"deeper": [{"final_proposal": "leak"}]},
                }
            )

    def test_candidate_resource_partner_are_discovered_through_receipts(self) -> None:
        result = run_episode("E1-EXTANT-MULTI-OWNER")
        kinds = {
            item["kind"]
            for item in result["raw_trace"]["evidence"]
            if item["evidence_id"] in {
                evidence["evidence_id"]
                for evidence in result["g1_handoff"]["evidence"]
            }
        }
        self.assertEqual({"candidate", "resource", "partner"}, kinds)
        self.assertEqual("QUALIFIED_CANDIDATE", result["boundary"])
        self.assertEqual(
            ["candidate", "resource", "partner"],
            [query["kind"] for query in result["raw_trace"]["queries"]],
        )

    def test_discovery_service_enforces_query_scope_and_action_envelope(self) -> None:
        world = make_world("E1-EXTANT-MULTI-OWNER")
        trace = Trace(
            episode_id="E1-EXTANT-MULTI-OWNER",
            intervention="T0_REPLAY",
            method="ATTACK",
        )
        session = DiscoverySession(
            world,
            trace,
            allow_t0_queries=True,
            allow_operators=False,
        )
        interface = session.observe_interface()
        wrong_scope = {
            "q_version": interface["q_version"],
            "object_id": "Venue-V:Circuit-C8",
            "deadline": interface["constraints"]["deadline"],
            "power_kw": interface["constraints"]["power_kw"],
            "exact_target_only": True,
        }
        self.assertEqual([], session.discover("resource", wrong_scope))
        self.assertIn("query_scope_mismatch:resource", trace.notes)
        self.assertEqual([], session.discover("final_proposal", wrong_scope))
        self.assertIn("query_outside_envelope:final_proposal", trace.notes)

    def test_l_benchmark_and_d_actual_are_distinct_denominators(self) -> None:
        report = build_report()
        summary = report["baseline_summary"]
        self.assertEqual(9, summary["L_benchmark"]["denominator"])
        self.assertEqual(6, summary["D_actual"]["denominator"])
        self.assertEqual(1.0, summary["D_actual"]["recall"])
        self.assertEqual(6 / 9, summary["L_benchmark"]["recall"])
        self.assertEqual(2, summary["refused_or_unknown_not_actual_miss"])

    def test_invalidity_first_rejects_wrong_authority_source_alias_and_tamper(self) -> None:
        expected = {
            "WRONG_AUTHORITY": "WRONG_AUTHORITY",
            "SOURCE_ALIAS": "SAME_SOURCE_ALIAS",
            "TAMPER_PAYLOAD": "EVIDENCE_HASH_MISMATCH",
            "TRUTH_TRANSPLANT": "TRUTH_TRANSPLANT",
        }
        for injection, failure in expected.items():
            with self.subTest(injection=injection):
                result = run_episode(
                    "E1-EXTANT-MULTI-OWNER",
                    intervention="FAILURE_INJECTION",
                    failure_injection=injection,
                )
                self.assertEqual("INVALID", result["boundary"])
                self.assertIn(
                    failure,
                    result["invalidity_first_gate"]["failures"],
                )
                self.assertFalse(result["eligible_positive"])
                worker_init = next(
                    json.loads(base64.b64decode(frame["wire_b64"]))
                    for frame in result["process_boundary_receipt"][
                        "raw_boundary_trace"
                    ]
                    if frame["sender"] == "controller"
                    and frame["recipient"] == "worker"
                )
                self.assertNotIn("boundary_test_injection", worker_init)
                if injection != "TAMPER_PAYLOAD":
                    self.assertNotIn(
                        "EVIDENCE_HASH_MISMATCH",
                        result["invalidity_first_gate"]["failures"],
                    )

        post_treatment = run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FAILURE_INJECTION",
            failure_injection="POST_TREATMENT_T0",
        )
        self.assertEqual("INVALID", post_treatment["boundary"])
        self.assertIn(
            "POST_TREATMENT_EVIDENCE_IN_T0_REPLAY",
            post_treatment["invalidity_first_gate"]["failures"],
        )
        worker_init = next(
            json.loads(base64.b64decode(frame["wire_b64"]))
            for frame in post_treatment["process_boundary_receipt"][
                "raw_boundary_trace"
            ]
            if frame["sender"] == "controller"
            and frame["recipient"] == "worker"
        )
        self.assertNotIn("boundary_test_injection", worker_init)

    def test_status_and_exact_interface_fields_are_hard_gates(self) -> None:
        world, trace = self._raw_trace()
        assert trace.proposal is not None
        mutations = (
            (
                replace(trace.proposal, status="COMMITMENT"),
                "G1_STATUS_OVERPROMOTION",
            ),
            (
                replace(trace.proposal, object_id="Venue-V:Circuit-C8"),
                "OBJECT_ID_DRIFT",
            ),
            (
                replace(trace.proposal, q_version="Q@mutated"),
                "Q_VERSION_DRIFT",
            ),
        )
        for proposal, failure in mutations:
            with self.subTest(failure=failure):
                mutated = Trace(**{**trace.__dict__, "proposal": proposal})
                result = evaluate_trace(world, mutated)
                self.assertEqual("INVALID", result["boundary"])
                self.assertIn(failure, result["invalidity_first_gate"]["failures"])

    def test_new_owner_backed_candidate_is_preserved_outside_population(self) -> None:
        world, trace = self._raw_trace()
        assert trace.proposal is not None
        candidate_id = "CAND-NEXT-VERSION"
        changed_events = []
        changed_expected = dict(world.expected)
        for event in trace.evidence:
            fields = event.hash_payload()
            fields["candidate_id"] = candidate_id
            fields["payload"] = {
                **fields["payload"],
                "candidate_id": candidate_id,
            }
            changed = EvidenceEvent.issue(**fields)
            changed_events.append(changed)
            changed_expected[event.evidence_id] = {
                **changed_expected[event.evidence_id],
                "candidate_id": candidate_id,
                "payload": {
                    **changed_expected[event.evidence_id]["payload"],
                    "candidate_id": candidate_id,
                },
            }
        next_world = replace(world, expected=changed_expected)
        next_trace = Trace(
            **{
                **trace.__dict__,
                "evidence": changed_events,
                "proposal": replace(
                    trace.proposal,
                    candidate_id=candidate_id,
                ),
            }
        )
        result = evaluate_trace(next_world, next_trace)
        self.assertEqual("NOVEL_CANDIDATE_FOR_NEXT_VERSION", result["boundary"])
        self.assertTrue(result["invalidity_first_gate"]["passed"])
        self.assertFalse(result["eligible_positive"])
        self.assertEqual(
            "PRESERVE_AS_NEXT_VERSION_CANDIDATE",
            result["g1_handoff"]["frozen_population"]["disposition"],
        )

    def test_t0_replay_excludes_post_treatment_partner_receipt(self) -> None:
        t0 = run_episode("E2-CONDITION-FORMATION")
        full = run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
        )
        self.assertEqual("UNKNOWN", t0["boundary"])
        self.assertIsNone(t0["g1_handoff"]["candidate_id"])
        self.assertEqual("QUALIFIED_CANDIDATE", full["boundary"])
        self.assertTrue(full["event_vector"]["qualification_created"])
        self.assertTrue(full["event_vector"]["partner_discovery_changed"])
        self.assertTrue(
            all(
                item["observed_at"] == "t0"
                for item in t0["raw_trace"]["evidence"]
            )
        )

    def test_operator_removal_and_reversal_change_evidence_not_labels(self) -> None:
        actual = run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
        )
        removed = run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
            removed_operator="OP-PARTNER-INTRODUCTION",
        )
        reversed_result = run_episode(
            "E2-CONDITION-FORMATION",
            intervention="FULL_ACTUAL_TRACE",
            reversed_operator="OP-PARTNER-INTRODUCTION",
        )
        self.assertEqual("QUALIFIED_CANDIDATE", actual["boundary"])
        self.assertEqual("UNKNOWN", removed["boundary"])
        self.assertIn(
            "operator_removed:OP-PARTNER-INTRODUCTION",
            removed["raw_trace"]["notes"],
        )
        self.assertEqual("INVALID", reversed_result["boundary"])
        self.assertIn(
            "REVOKED_EVIDENCE",
            reversed_result["invalidity_first_gate"]["failures"],
        )
        self.assertEqual(
            "REVERSED",
            reversed_result["raw_trace"]["operators"][0]["mode"],
        )

    def test_ack_pair_is_g1_isomorphic_and_contains_no_future_effect_truth(self) -> None:
        left = make_world("E3A-ACK-LOST-EFFECT")
        right = make_world("E3B-ACK-LOST-NO-EFFECT")
        left_interface = dict(left.interface)
        right_interface = dict(right.interface)
        for value in (left_interface, right_interface):
            value.pop("episode_id")
            value.pop("clarification_prelude_receipt_hash")
        self.assertEqual(left_interface, right_interface)
        rendered = json.dumps(left_interface).lower()
        self.assertNotIn("effect_occurred", rendered)
        self.assertNotIn("actual_effect_state", rendered)
        self.assertNotIn("submit_ack", rendered)
        self.assertEqual(
            run_episode("E3A-ACK-LOST-EFFECT")["g1_handoff"]["candidate_id"],
            run_episode("E3B-ACK-LOST-NO-EFFECT")["g1_handoff"]["candidate_id"],
        )

    def test_handoff_is_composition_ready_without_other_line_claims(self) -> None:
        result = run_episode("E0-PLATFORM-DIRECT")
        handoff = result["g1_handoff"]
        self.assertEqual("ce001-g1-handoff-v1", handoff["schema_version"])
        self.assertEqual("G1", handoff["line"])
        self.assertEqual("Q@v1", handoff["Q_version"])
        self.assertEqual("Venue-V:Circuit-C7", handoff["object_id"])
        self.assertEqual("TEMPORARY_POWER:C7", handoff["operation_id"])
        self.assertEqual("CANDIDATE_NOT_COMMITMENT", handoff["status"])
        self.assertEqual(
            {"O_R", "O_V"},
            set(handoff["owner_ids"]),
        )
        self.assertEqual(3, len(handoff["evidence"]))
        self.assertEqual("BATTERY-V-01", handoff["resource_id"])
        self.assertEqual("VENUE-OPS", handoff["partner_id"])
        self.assertEqual(
            digest(result["raw_trace"]),
            handoff["raw_trace_sha256"],
        )
        output_hash = handoff.pop("output_hash")
        self.assertEqual(digest(handoff), output_hash)
        self.assertIn("EFFECT", handoff["explicit_non_claims"])
        self.assertIn("ACCEPTANCE", handoff["explicit_non_claims"])

    def test_namespaced_line_envelope_excludes_cross_line_contract_claims(self) -> None:
        result = run_episode("E0-PLATFORM-DIRECT")
        envelope = result["g1_line_envelope"]
        self.assertEqual(
            "towow-g1-provenance-line-envelope-v2",
            envelope["schema_version"],
        )
        self.assertEqual("G1_PROVENANCE", envelope["g1_namespace"])
        self.assertEqual(
            "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE",
            envelope["g1_owner_fixture_class"],
        )
        self.assertEqual("NOT_ESTABLISHED", envelope["g1_real_owner_truth"])
        self.assertEqual("NOT_ESTABLISHED", envelope["g1_real_owner_origin"])
        self.assertNotIn("g1_episode_id", envelope)
        self.assertEqual(
            digest({"episode_id": result["episode_id"]}),
            envelope["g1_episode_ref_sha256"],
        )
        self.assertEqual([], line_local_envelope_violations(envelope))
        self.assertTrue(
            line_local_envelope_violations(
                {"g1_nested": {"contract_exact_task_success": False}}
            )
        )
        self.assertTrue(
            line_local_envelope_violations(
                {"g1_nested": [{"g1_bad_claim": "EFFECT"}]}
            )
        )
        self.assertTrue(
            line_local_envelope_violations(
                {"g1_nested": [{"g1_bad_claim": "RELATION_ESTABLISHED"}]}
            )
        )
        self.assertTrue(
            all(
                "g1_claim_root_id" not in evidence
                for evidence in envelope["g1_evidence"]
            )
        )
        output_hash = envelope.pop("g1_output_hash")
        self.assertEqual(digest(envelope), output_hash)

    def test_runner_emits_raw_traces_failures_and_stable_population_receipt(self) -> None:
        report = build_report()
        self.assertEqual(set(EPISODE_IDS), set(report["population_receipt"]["episode_ids"]))
        self.assertEqual(8, len(report["baseline"]))
        self.assertEqual(3, len(report["operator_interventions"]))
        self.assertEqual(5, len(report["failure_injections"]))
        self.assertEqual(4, len(report["process_identity_injections"]))
        self.assertTrue(
            all("raw_trace" in result for result in report["baseline"])
        )
        self.assertTrue(
            all(
                not result["method_visible_input_receipt"]["recursive_scan_found"]
                for result in report["baseline"]
            )
        )
        self.assertEqual(
            [
                "deadline",
                "exact_target_only",
                "object_id",
                "power_kw",
                "q_version",
            ],
            report["baseline"][0]["method_visible_input_receipt"][
                "query_predicate_keys"
            ],
        )
        self.assertEqual(
            report["population_receipt"],
            build_report()["population_receipt"],
        )
        self.assertEqual(
            digest(report["population_receipt"]["entries"]),
            report["population_receipt"]["sha256"],
        )
        self.assertTrue(
            all(
                {"L_benchmark", "D_actual", "oracle_roots_sha256"}
                <= set(entry)
                for entry in report["population_receipt"]["entries"]
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            completed = subprocess.run(
                [sys.executable, "runner.py", "--output", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, completed.returncode, completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                "ce001-g1-provenance-module-output-v1",
                payload["schema_version"],
            )
            self.assertEqual("NOT_IMPLEMENTED", payload["scope"]["other_lines"])


if __name__ == "__main__":
    unittest.main()
