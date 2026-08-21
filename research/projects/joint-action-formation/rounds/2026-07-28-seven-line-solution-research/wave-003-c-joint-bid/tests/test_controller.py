from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("t4_controller", ROOT / "controller.py")
assert SPEC is not None and SPEC.loader is not None
controller = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(controller)


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def query(
    authority_id: str,
    request_type: str,
    purpose: str = "bounded decision",
    relation_version_ref: str = "JB-CANDIDATE-V1",
) -> dict[str, str]:
    return {
        "authority_id": authority_id,
        "request_type": request_type,
        "purpose": purpose,
        "relation_version_ref": relation_version_ref,
        "retention_scope": "RUN_ONLY",
    }


def batch(
    round_number: int,
    previous_round_hash: str | None,
    queries: list[dict[str, str]],
) -> dict:
    return {
        "schema_version": "1.0",
        "task_id": controller.TASK_ID,
        "method_id": "TEST-METHOD",
        "run_id": "TEST-RUN",
        "round": round_number,
        "previous_round_hash": previous_round_hash,
        "queries": queries,
    }


class ControllerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.blind = load("blind/input.json")
        self.oracle = load("oracle/truth.json")
        self.state = controller.initial_state()

    def run_round(
        self,
        round_number: int,
        previous_round_hash: str | None,
        queries: list[dict[str, str]],
    ) -> dict:
        return controller.process_batch(
            batch(round_number, previous_round_hash, queries),
            self.state,
            self.blind,
            self.oracle,
        )

    def test_interface_and_oracle_have_exact_pair_closure(self) -> None:
        _, allowed_pairs, _, disclosures = controller.build_indexes(
            self.blind, self.oracle
        )
        self.assertEqual(allowed_pairs, set(disclosures))
        self.assertEqual(28, len(allowed_pairs))

    def test_wrong_authority_does_not_hint_correct_authority(self) -> None:
        output = self.run_round(
            1,
            None,
            [query("PRIME-TECH", "REQUEST_FIELD_PRICE_BOUND")],
        )
        result = output["results"][0]
        self.assertEqual("REFUSE", result["decision"])
        self.assertEqual("REQUEST_NOT_ALLOWED_FOR_AUTHORITY", result["reason_code"])
        self.assertEqual({}, result["disclosed_fields"])

    def test_probe_is_deferred_until_all_exact_prerequisites_are_disclosed(
        self,
    ) -> None:
        first = self.run_round(
            1,
            None,
            [query("PRIME-TECH", "RUN_INTEROP_PROBE")],
        )
        self.assertEqual("DEFER", first["results"][0]["decision"])
        second = self.run_round(
            2,
            first["round_hash"],
            [
                query(
                    "CITY-PROCUREMENT",
                    "REQUEST_CURRENT_TENDER_VERSION",
                    "bind current target version",
                ),
                query(
                    "PRIME-TECH",
                    "REQUEST_LOCAL_EXECUTION_OPTION",
                    "check data locality",
                ),
                query(
                    "PRIME-TECH",
                    "REQUEST_INTEROP_PROBE_TERMS",
                    "bound exact qualification",
                ),
                query(
                    "FIELD-OPS",
                    "REQUEST_FIRMWARE_INTERFACE",
                    "bind field version",
                ),
                query("PRIME-TECH", "RUN_INTEROP_PROBE"),
            ],
        )
        self.assertEqual(
            ["DISCLOSE", "DISCLOSE", "DISCLOSE", "DISCLOSE", "DISCLOSE"],
            [item["decision"] for item in second["results"]],
        )
        probe = second["results"][-1]
        self.assertEqual("WITNESS", probe["response_type"])
        self.assertEqual("PASS", probe["disclosed_fields"]["result"])

    def test_deferred_reservation_can_be_retried_after_prerequisites(self) -> None:
        first = self.run_round(
            1,
            None,
            [query("FIELD-COMMERCIAL", "RESERVE_FIELD_CAPACITY")],
        )
        self.assertEqual("DEFER", first["results"][0]["decision"])
        second = self.run_round(
            2,
            first["round_hash"],
            [
                query(
                    "CITY-PROCUREMENT",
                    "REQUEST_CURRENT_TENDER_VERSION",
                    "bind current target version",
                ),
                query(
                    "FIELD-COMMERCIAL",
                    "REQUEST_KIT_RESERVATION_TERMS",
                    "bound owner reservation",
                ),
                query(
                    "FIELD-OPS",
                    "REQUEST_FIELD_CAPACITY_BOUND",
                    "check current capacity",
                ),
                query("FIELD-COMMERCIAL", "RESERVE_FIELD_CAPACITY"),
            ],
        )
        reservation = second["results"][-1]
        self.assertEqual("DISCLOSE", reservation["decision"])
        self.assertEqual("RESERVATION", reservation["response_type"])
        self.assertTrue(
            reservation["disclosed_fields"]["exclusive_for_relation_version"]
        )

    def test_successful_repeat_is_replay_without_repeating_disclosure(self) -> None:
        requested = query(
            "CITY-PROCUREMENT",
            "REQUEST_SUBMISSION_EVIDENCE_RULE",
            "separate outcome evidence",
        )
        first = self.run_round(1, None, [requested])
        second = self.run_round(2, first["round_hash"], [requested])
        initial = first["results"][0]
        replay = second["results"][0]
        self.assertEqual("DISCLOSE", initial["decision"])
        self.assertEqual("REPLAY", replay["decision"])
        self.assertEqual({}, replay["disclosed_fields"])
        self.assertEqual(initial["response_hash"], replay["response_hash"])
        self.assertEqual(
            initial["receipt"]["receipt_id"],
            replay["replay_of_receipt_id"],
        )

    def test_round_history_is_hash_chained_and_conflicts_are_rejected(self) -> None:
        first_batch = batch(
            1,
            None,
            [query("CITY-PROCUREMENT", "REQUEST_BUDGET_RULE")],
        )
        first = controller.process_batch(
            first_batch, self.state, self.blind, self.oracle
        )
        replay = controller.process_batch(
            first_batch, self.state, self.blind, self.oracle
        )
        self.assertEqual(first, replay)
        conflicting = batch(
            1,
            None,
            [query("CITY-PROCUREMENT", "REQUEST_TARGET_READBACK_RULE")],
        )
        with self.assertRaisesRegex(
            controller.ControllerError, "conflicting replay"
        ):
            controller.process_batch(
                conflicting, self.state, self.blind, self.oracle
            )


class EvaluationIsolationTests(unittest.TestCase):
    def test_evaluator_is_solution_neutral(self) -> None:
        evaluator = load("evaluator/spec.json")
        neutrality = evaluator["anti_answer_shaping"]
        self.assertEqual(0, neutrality["protocol_name_bonus"])
        self.assertEqual(0, neutrality["novelty_bonus"])
        self.assertIn(
            "CMMN/BPMN/DMN plus commitment, IAM/policy and workflow",
            neutrality["accepted_solution_families"],
        )
        oracle = load("oracle/truth.json")
        self.assertTrue(
            oracle["anti_answer_shaping"]["standards_stack_may_receive_full_credit"]
        )

    def test_mutations_cover_every_g2_to_g7_requirement(self) -> None:
        evaluator = load("evaluator/spec.json")
        mutations = load("mutations/negative_mutations.json")
        requirement_ids = {
            item["id"] for item in evaluator["requirements"]
        }
        self.assertEqual(
            {
                "R2-TASK-RELATION",
                "R3-FORM-REACHABILITY",
                "R4-CAPABILITY-QUALIFICATION",
                "R5-AUTHORITY-RESERVATION",
                "R6-OUTCOME-READBACK",
                "R7-REOPEN-REUSE-MIGRATION",
            },
            requirement_ids,
        )
        covered = {
            requirement
            for mutation in mutations["mutations"]
            for requirement in mutation["tests"]
        }
        self.assertEqual(requirement_ids, covered)
        self.assertEqual(
            len(mutations["mutations"]),
            len({item["id"] for item in mutations["mutations"]}),
        )

    def test_migration_variant_changes_entities_and_domain(self) -> None:
        migration = load("oracle/migration_variant.json")
        entities = {
            item["entity_id"]
            for item in migration["public_variant"]["independent_entities"]
        }
        self.assertTrue(entities.isdisjoint({"PRIME", "FIELD", "ASSURE"}))
        self.assertIn(
            "a Towow-specific object or protocol name",
            migration["migration_evaluation"]["must_not_require"],
        )


if __name__ == "__main__":
    unittest.main()
