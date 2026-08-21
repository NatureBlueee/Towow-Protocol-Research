from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import inspect
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g1prov.evaluator import evaluate_trace, summarize
from g1prov.fixtures import World, make_world
from g1prov.method import EvidenceFirstDiscovery
from g1prov.model import CandidateProposal, Trace, digest
from g1prov.runner import run_episode
from g1prov.session import DiscoverySession


class G1AdversarialTests(unittest.TestCase):
    """Independent C attacks.

    Expected failures are retained as executable red history. They state the
    stronger invariant required by the frozen CE-001 contract; they are not
    converted into implementation success merely because the current runner
    detects a weaker downstream symptom.
    """

    def _run_world(
        self,
        world: World,
        *,
        intervention: str = "T0_REPLAY",
        apply_operators: bool = False,
    ) -> tuple[Trace, dict]:
        trace = Trace(
            episode_id=world.interface["episode_id"],
            intervention=intervention,
            method=EvidenceFirstDiscovery().name,
        )
        session = DiscoverySession(
            world,
            trace,
            allow_t0_queries=True,
            allow_operators=apply_operators,
        )
        if apply_operators:
            for operator_id in session.controller_operator_ids:
                session.apply_operator(operator_id)
        EvidenceFirstDiscovery().run(session)
        return trace, evaluate_trace(world, trace)

    def _dynamic_bundle(
        self,
        world: World,
        *,
        candidate_id: str,
        suffix: str,
        object_id: str = "Venue-V:Circuit-C7",
    ) -> tuple[list[dict], dict[str, dict], dict[str, str]]:
        subjects = {
            "candidate": candidate_id,
            "resource": f"BATTERY-{suffix}",
            "partner": f"PARTNER-{suffix}",
        }
        records: list[dict] = []
        for original in world.records[:3]:
            record = deepcopy(original)
            kind = record["kind"]
            record["evidence_id"] = f"{suffix}-{kind.upper()}"
            record["candidate_id"] = candidate_id
            record["subject_id"] = subjects[kind]
            record["source_id"] = f"dynamic-owner:{suffix}:{kind}"
            record["payload"] = {
                **record["payload"],
                "candidate_id": candidate_id,
                "subject_id": subjects[kind],
                "object_id": object_id,
            }
            records.append(record)
        expected = {
            record["evidence_id"]: deepcopy(record)
            for record in records
        }
        aliases = {
            record["source_id"]: record["source_id"]
            for record in records
        }
        return records, expected, aliases

    def test_method_source_and_interface_contain_no_forbidden_answer_keys(self) -> None:
        source = inspect.getsource(
            sys.modules[EvidenceFirstDiscovery.__module__]
        ).lower()
        interface = make_world("E1-EXTANT-MULTI-OWNER").interface
        rendered = json.dumps(interface, sort_keys=True).lower()
        for forbidden in (
            "l_benchmark",
            "d_actual",
            "correct_path",
            "expected_path",
            "t0_paths",
            "final_proposal",
            "private_expected_label",
        ):
            self.assertNotIn(forbidden, source)
            self.assertNotIn(forbidden, rendered)

    def test_dynamic_owner_backed_candidate_is_not_hardcoded_in_method(self) -> None:
        base = make_world("E1-EXTANT-MULTI-OWNER")
        candidate_id = "CAND-DYNAMIC-OWNER-BACKED"
        records, expected, aliases = self._dynamic_bundle(
            base,
            candidate_id=candidate_id,
            suffix="DYNAMIC",
        )
        world = replace(
            base,
            records=tuple(records),
            l_benchmark=(candidate_id,),
            d_actual=(candidate_id,),
            expected=expected,
            source_aliases=aliases,
        )
        trace, result = self._run_world(world)
        self.assertEqual(candidate_id, trace.proposal.candidate_id)
        self.assertEqual("QUALIFIED_CANDIDATE", result["boundary"])
        self.assertEqual(
            ["candidate", "resource", "partner"],
            [query["kind"] for query in trace.queries],
        )

    def test_valid_novel_candidate_is_next_version_not_hard_invalid(self) -> None:
        """A valid owner-backed path outside frozen L must not rewrite L.

        The current run should preserve the population hash and retain the path
        as a next-version candidate. Treating it as an invalid act confuses
        benchmark membership with evidence validity.
        """

        base = make_world("E1-EXTANT-MULTI-OWNER")
        novel_id = "CAND-NOVEL-OWNER-BACKED"
        records, expected, aliases = self._dynamic_bundle(
            base,
            candidate_id=novel_id,
            suffix="NOVEL",
        )
        world = replace(
            base,
            records=tuple(records),
            expected=expected,
            source_aliases=aliases,
            # Deliberately preserve the frozen current-run denominators.
            l_benchmark=base.l_benchmark,
            d_actual=base.d_actual,
        )
        _, result = self._run_world(world)
        self.assertEqual(
            "NOVEL_CANDIDATE_FOR_NEXT_VERSION",
            result["boundary"],
        )
        self.assertEqual(list(base.l_benchmark), result["L_benchmark"])
        self.assertEqual(list(base.d_actual), result["D_actual"])

    def test_dynamic_decoy_cannot_obtain_false_positive(self) -> None:
        base = make_world("E1-EXTANT-MULTI-OWNER")
        decoy_id = "AAA-DECOY"
        records, expected, aliases = self._dynamic_bundle(
            base,
            candidate_id=decoy_id,
            suffix="DECOY",
            object_id="Venue-V:Circuit-C8",
        )
        world = replace(
            base,
            records=tuple(records) + base.records,
            expected={**base.expected, **expected},
            source_aliases={**base.source_aliases, **aliases},
        )
        trace, result = self._run_world(world)
        self.assertEqual("CAND-RENTAL-A", trace.proposal.candidate_id)
        self.assertEqual("QUALIFIED_CANDIDATE", result["boundary"])
        self.assertFalse(
            any(
                event.payload["object_id"] == "Venue-V:Circuit-C8"
                for event in trace.evidence
            )
        )
        self.assertTrue(result["eligible_positive"])

    def test_discovery_service_enforces_query_predicates_before_disclosure(self) -> None:
        """Wrong-object records should not be returned by a C7 query.

        Downstream rejection prevents false success, but returning the C8
        records still leaks unrelated owner data and can crowd out the valid
        candidate chosen by the current first-complete heuristic.
        """

        base = make_world("E1-EXTANT-MULTI-OWNER")
        records, expected, aliases = self._dynamic_bundle(
            base,
            candidate_id="AAA-WRONG-OBJECT",
            suffix="WRONG-OBJECT",
            object_id="Venue-V:Circuit-C8",
        )
        world = replace(
            base,
            records=tuple(records) + base.records,
            expected={**base.expected, **expected},
            source_aliases={**base.source_aliases, **aliases},
        )
        trace, _ = self._run_world(world)
        returned_wrong_object = [
            event
            for event in trace.evidence
            if event.payload["object_id"] == "Venue-V:Circuit-C8"
        ]
        self.assertEqual([], returned_wrong_object)

    def test_wrong_authority_and_source_alias_are_hard_failures(self) -> None:
        for injection, reason in (
            ("WRONG_AUTHORITY", "WRONG_AUTHORITY"),
            ("SOURCE_ALIAS", "SAME_SOURCE_ALIAS"),
        ):
            with self.subTest(injection=injection):
                result = run_episode(
                    "E1-EXTANT-MULTI-OWNER",
                    intervention="FAILURE_INJECTION",
                    failure_injection=injection,
                )
                self.assertEqual("INVALID", result["boundary"])
                self.assertIn(
                    reason,
                    result["invalidity_first_gate"]["failures"],
                )
                self.assertFalse(result["eligible_positive"])

    def test_final_proposal_string_without_evidence_gets_no_credit(self) -> None:
        world = make_world("E1-EXTANT-MULTI-OWNER")
        trace = Trace(
            episode_id=world.interface["episode_id"],
            intervention="T0_REPLAY",
            method="ATTACK_FINAL_PROPOSAL_ORACLE",
            intent_boundary="IntentAtCoordinationInterface",
            prelude_receipt_hash=world.interface[
                "clarification_prelude_receipt_hash"
            ],
            proposal=CandidateProposal.synthesize(
                episode_id=world.interface["episode_id"],
                q_version=world.interface["q_version"],
                object_id=world.interface["object_id"],
                operation_id=world.interface["operation_id"],
                candidate_id=world.l_benchmark[0],
                resource_id="BATTERY-RENTAL-A",
                partner_id="PARTNER-A",
                owner_ids=("O_R", "O_V"),
                evidence_ids=(),
            ),
        )
        result = evaluate_trace(world, trace)
        self.assertEqual("INVALID", result["boundary"])
        self.assertIn(
            "MISSING_EVIDENCE_KIND",
            result["invalidity_first_gate"]["failures"],
        )
        self.assertFalse(result["eligible_positive"])

    def test_full_trace_t1_receipt_cannot_be_copied_into_t0_replay(self) -> None:
        world = make_world("E2-CONDITION-FORMATION")
        trace, full = self._run_world(
            world,
            intervention="FULL_ACTUAL_TRACE",
            apply_operators=True,
        )
        self.assertEqual("QUALIFIED_CANDIDATE", full["boundary"])
        trace.intervention = "T0_REPLAY"
        replay = evaluate_trace(world, trace)
        self.assertEqual("INVALID", replay["boundary"])
        self.assertIn(
            "POST_TREATMENT_EVIDENCE_IN_T0_REPLAY",
            replay["invalidity_first_gate"]["failures"],
        )

    def test_operator_remove_and_reverse_change_owner_backed_evidence(self) -> None:
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
        self.assertTrue(actual["event_vector"]["partner_discovery_changed"])
        self.assertEqual("UNKNOWN", removed["boundary"])
        self.assertEqual("INVALID", reversed_result["boundary"])
        self.assertIn(
            "REVOKED_EVIDENCE",
            reversed_result["invalidity_first_gate"]["failures"],
        )

    def test_query_budget_is_enforced_by_invalidity_gate(self) -> None:
        """A valid proposal must not erase an over-budget discovery trace."""

        world = make_world("E1-EXTANT-MULTI-OWNER")
        trace = Trace(
            episode_id=world.interface["episode_id"],
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
        session.discover(
            "candidate",
            {
                "q_version": "Q@v1",
                "object_id": "Venue-V:Circuit-C7",
            },
        )
        result = evaluate_trace(world, trace)
        self.assertEqual("INVALID", result["boundary"])
        self.assertIn(
            "ACTION_ENVELOPE_BREACH",
            result["invalidity_first_gate"]["failures"],
        )

    def test_prelude_lineage_is_recomputed_not_only_echoed(self) -> None:
        world = make_world("E1-EXTANT-MULTI-OWNER")
        world.prelude["vague_request"] = "transplanted upstream request"
        trace, result = self._run_world(world)
        self.assertNotEqual(
            digest(world.prelude),
            world.interface["clarification_prelude_receipt_hash"],
        )
        self.assertEqual("INVALID", result["boundary"])
        self.assertIn(
            "PRELUDE_LINEAGE_MISMATCH",
            result["invalidity_first_gate"]["failures"],
        )
        self.assertIsNotNone(trace.proposal)

    def test_interface_preserves_full_frozen_q_acceptance_clause(self) -> None:
        intent = make_world("E1-EXTANT-MULTI-OWNER").interface["intent_text"]
        self.assertIn("requester", intent.lower())
        self.assertIn("venue", intent.lower())
        self.assertIn("acceptance", intent.lower())
        self.assertIn("settlement", intent.lower())

    def test_summary_scopes_candidate_identity_by_episode(self) -> None:
        """Same candidate_id in E3A/E3B must not transfer qualification."""

        valid = run_episode("E3A-ACK-LOST-EFFECT")
        invalid = run_episode(
            "E3B-ACK-LOST-NO-EFFECT",
            intervention="FAILURE_INJECTION",
            failure_injection="WRONG_AUTHORITY",
        )
        self.assertEqual(
            valid["g1_handoff"]["candidate_id"],
            invalid["g1_handoff"]["candidate_id"],
        )
        self.assertTrue(valid["eligible_positive"])
        self.assertFalse(invalid["eligible_positive"])
        summary = summarize([valid, invalid])
        self.assertEqual(1, summary["D_actual"]["discovered"])
        self.assertEqual(0.5, summary["D_actual"]["recall"])


if __name__ == "__main__":
    unittest.main()
