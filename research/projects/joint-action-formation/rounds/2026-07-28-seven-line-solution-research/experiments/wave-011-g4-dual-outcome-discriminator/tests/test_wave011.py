from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from evaluator import confusion  # noqa: E402
from pair_auditor import audit as audit_pairs  # noqa: E402
from primitive_services import FORBIDDEN_RESPONSE_FIELDS, PrimitiveService, _walk_keys  # noqa: E402
from runner import WORKERS, evaluate, expanded_public, load, run_worker  # noqa: E402


class Wave011Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture, cls.oracle = load()
        cls.report = evaluate()

    def test_population_is_candidate_sized_and_balanced_by_quantifier(self) -> None:
        self.assertEqual(len(self.fixture["worlds"]), 14)
        self.assertEqual(len(self.fixture["pairs"]), 7)
        counts = {
            pair_class: sum(
                pair["pair_class"] == pair_class for pair in self.fixture["pairs"]
            )
            for pair_class in ("PASSIVE", "ACTIVE", "HARD")
        }
        self.assertEqual(counts, {"PASSIVE": 1, "ACTIVE": 4, "HARD": 2})

    def test_primitive_responses_never_return_pre_adjudicated_fields(self) -> None:
        for world in self.fixture["worlds"]:
            packet = expanded_public(self.fixture, world)
            for action in world["allowed_actions"]:
                service = PrimitiveService(
                    world["world_ref"],
                    packet,
                    self.oracle["base_state"],
                    self.oracle["worlds"][world["world_ref"]],
                    world["allowed_actions"],
                )
                raw = service.call(action, {})
                self.assertFalse(
                    FORBIDDEN_RESPONSE_FIELDS & _walk_keys(raw),
                    (world["world_ref"], action, raw),
                )

    def test_pair_quantifiers_are_separate_and_discriminating(self) -> None:
        result = audit_pairs()
        self.assertTrue(result["all_pairs_pass"])
        by_class = {
            value["pair_class"] for value in result["results"].values()
        }
        self.assertEqual(by_class, {"PASSIVE", "ACTIVE", "HARD"})
        hard = [
            value
            for value in result["results"].values()
            if value["pair_class"] == "HARD"
        ]
        self.assertTrue(all(item["enumerated_plans"] == 73 for item in hard))
        self.assertTrue(all(not item["unequal_transcript_plans"] for item in hard))

    def test_evaluator_penalizes_always_rely_and_all_abstain_differently(self) -> None:
        truths = [True, False, True, False]
        always_rely = [
            {
                "predictions": {"P1": {"Y_success": "YES"}},
                "truth": {"P1": {"Y_success": truth}},
            }
            for truth in truths
        ]
        all_abstain = [
            {
                "predictions": {"P1": {"Y_success": "ABSTAIN"}},
                "truth": {"P1": {"Y_success": truth}},
            }
            for truth in truths
        ]
        rely_score = confusion(always_rely, "P1", "Y_success")
        abstain_score = confusion(all_abstain, "P1", "Y_success")
        self.assertEqual(rely_score["false_reliance_conditional"], 0.5)
        self.assertEqual(rely_score["safe_recall"], 1.0)
        self.assertEqual(abstain_score["false_reliance_all"], 0.0)
        self.assertEqual(abstain_score["safe_recall"], 0.0)
        self.assertEqual(abstain_score["abstention_rate"], 1.0)

    def test_workers_are_distinct_process_sources_not_function_aliases(self) -> None:
        hashes = self.report["worker_sha256"]
        self.assertEqual(len(set(hashes.values())), len(WORKERS))
        sources = {name: path.read_text(encoding="utf-8") for name, path in WORKERS.items()}
        self.assertNotIn("mature_composite_worker", sources["SAME_PERMISSION_STRONG_CENTER"])
        self.assertNotIn("strong_center_worker", sources["MATURE_COMPOSITE"])

    def test_sabotaging_mature_binary_does_not_change_center_binary(self) -> None:
        world = next(
            item
            for item in self.fixture["worlds"]
            if item["world_ref"] == "A-STALE-PINNED-ALLOWED"
        )
        packet = expanded_public(self.fixture, world)

        def fresh_service() -> PrimitiveService:
            return PrimitiveService(
                world["world_ref"],
                packet,
                self.oracle["base_state"],
                self.oracle["worlds"][world["world_ref"]],
                world["allowed_actions"],
            )

        before = run_worker(
            "CENTER_BEFORE",
            WORKERS["SAME_PERMISSION_STRONG_CENTER"],
            fresh_service(),
            packet,
        )
        sabotage = run_worker(
            "MATURE_SABOTAGE",
            HERE / "tests" / "always_abstain_worker.py",
            fresh_service(),
            packet,
        )
        after = run_worker(
            "CENTER_AFTER",
            WORKERS["SAME_PERMISSION_STRONG_CENTER"],
            fresh_service(),
            packet,
        )
        self.assertEqual(before["predictions"], after["predictions"])
        self.assertNotEqual(before["predictions"]["P1"], sabotage["predictions"]["P1"])

    def test_p0_and_p1_are_frozen_separately(self) -> None:
        rows = self.report["methods"]["MATURE_COMPOSITE"]["worlds"]
        self.assertTrue(
            any(row["truth"]["P0"] != row["truth"]["P1"] for row in rows)
        )
        for row in rows:
            self.assertEqual(set(row["predictions"]), {"P0", "P1"})
            self.assertEqual(
                set(row["predictions"]["P1"]),
                {"Y_success", "Y_resolution", "Y_effect", "Y_acceptance"},
            )

    def test_response_lost_executes_readback_without_duplicate_effect(self) -> None:
        rows = {
            row["world_ref"]: row
            for row in self.report["methods"]["MATURE_COMPOSITE"]["worlds"]
        }
        executed = rows["A-LOST-EXECUTED"]
        no_effect = rows["A-LOST-NO-EFFECT"]
        self.assertTrue(executed["outcomes"]["Y_success"])
        self.assertTrue(executed["outcomes"]["correct_object_readback_observed"])
        self.assertFalse(executed["outcomes"]["duplicate_effect"])
        self.assertFalse(no_effect["outcomes"]["Y_success"])
        self.assertTrue(no_effect["outcomes"]["Y_resolution"])
        self.assertFalse(no_effect["outcomes"]["duplicate_effect"])

    def test_target_rejects_missing_authority_and_reservation_tokens(self) -> None:
        world = next(
            item
            for item in self.fixture["worlds"]
            if item["world_ref"] == "A-LOST-EXECUTED"
        )
        packet = expanded_public(self.fixture, world)
        service = PrimitiveService(
            world["world_ref"],
            packet,
            self.oracle["base_state"],
            self.oracle["worlds"][world["world_ref"]],
            world["allowed_actions"],
        )
        service.call(
            "submit_operation",
            {
                "operation_id": packet["operation"]["operation_id"],
                "target_id": packet["operation"]["target_id"],
            },
        )
        self.assertFalse(service.audit_outcomes()["Y_success"])
        self.assertFalse(service.audit_outcomes()["Y_effect"])

    def test_wrong_object_never_counts_as_valid_readback(self) -> None:
        rows = {
            row["world_ref"]: row
            for row in self.report["methods"]["MATURE_COMPOSITE"]["worlds"]
        }
        for world_ref in (
            "H-WRONG-OBJECT-ACTUAL-SUCCESS",
            "H-WRONG-OBJECT-ACTUAL-NO-EFFECT",
        ):
            self.assertFalse(
                rows[world_ref]["outcomes"]["correct_object_readback_observed"]
            )
            self.assertFalse(rows[world_ref]["outcomes"]["Y_resolution"])

    def test_effect_and_acceptance_are_not_inferred_from_each_other(self) -> None:
        rows = {
            row["world_ref"]: row
            for row in self.report["methods"]["MATURE_COMPOSITE"]["worlds"]
        }
        machine = rows["A-RESERVED-OWNER-APPROVES"]["outcomes"]
        self.assertTrue(machine["Y_effect"])
        self.assertFalse(machine["Y_acceptance"])

    def test_delegation_is_obtained_through_costed_owner_channel(self) -> None:
        rows = self.report["methods"]["LEGITIMATELY_DELEGATED_CENTER"]["worlds"]
        binding = next(
            row
            for row in rows
            if row["world_ref"] == "A-BINDING-WINDOW-AFTER-CHECK"
        )
        actions = [
            entry["action"] for entry in binding["trace"] if "action" in entry
        ]
        self.assertIn("request_delegation", actions)
        self.assertGreater(binding["cost"]["human_interruptions"], 0)
        self.assertTrue(binding["outcomes"]["Y_success"])

    def test_oracle_is_unchanged_and_not_in_worker_source(self) -> None:
        self.assertTrue(self.report["oracle_unchanged"])
        for path in WORKERS.values():
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("private_oracle", source)
            self.assertNotIn("world_ref", source)


if __name__ == "__main__":
    unittest.main()
