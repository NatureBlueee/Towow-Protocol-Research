from __future__ import annotations

import copy
import inspect
import json
import sys
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from authority_truth_broker import AuthorityTruthBroker  # noqa: E402
import baselines  # noqa: E402
import runner  # noqa: E402
from relation_truth_broker import RelationTruthBroker  # noqa: E402
from runner import (  # noqa: E402
    BASELINE_IDS,
    execute_t5_platform,
    run_experiment,
    run_single,
)
from world_factory import (  # noqa: E402
    AuthorityPrivateWorld,
    build_core_worlds,
    build_mutation_pairs,
    build_t5_case,
)


class Wave009CrossedSquareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.core = build_core_worlds()
        cls.mutations = build_mutation_pairs()
        cls.report = run_experiment(write_outputs=False)

    def test_core_is_exact_24_world_crossed_square(self) -> None:
        coordinates = {
            (
                item.relation_private.task_kind,
                item.relation_private.horizon,
                item.relation_private.relation_valid,
                item.authority_private.authority_valid,
            )
            for item in self.core
        }
        expected = {
            (task, horizon, relation_valid, authority_valid)
            for task in ("T3", "T4")
            for horizon in ("ONE_SHOT", "BOUNDED", "DURABLE")
            for relation_valid in (False, True)
            for authority_valid in (False, True)
        }
        self.assertEqual(expected, coordinates)
        self.assertEqual(24, len(self.core))

    def test_t3_and_t4_are_not_misreported_as_real_tasks(self) -> None:
        for item in self.core:
            expected = (
                "SYNTHETIC_TASK_SPEC"
                if item.public_packet["task"]["task_kind"] in {"T3", "T4"}
                else None
            )
            self.assertEqual(expected, item.public_packet["task"]["truth_status"])

    def test_world_and_run_ids_are_opaque(self) -> None:
        forbidden = (
            "T3",
            "T4",
            "VALID",
            "INVALID",
            "ONE",
            "BOUND",
            "DURABLE",
            "RELATION",
            "AUTH",
        )
        for item in self.core:
            world_id = item.public_packet["world_id"].upper()
            self.assertTrue(world_id.startswith("W-"))
            self.assertFalse(any(token in world_id for token in forbidden))
        for row in self.report["runs"]:
            run_id = row["parent_record"]["run_id"].upper()
            self.assertTrue(run_id.startswith("R-"))
            self.assertFalse(any(token in run_id for token in forbidden))

    def test_truth_brokers_have_independent_runtime_keys_and_state(self) -> None:
        item = self.core[0]
        relation = RelationTruthBroker(item.relation_private)
        authority = AuthorityTruthBroker(item.authority_private)
        self.assertNotEqual(
            relation.public_contract()["broker_public_key"],
            authority.public_contract()["broker_public_key"],
        )
        self.assertNotEqual(
            set(relation.public_contract()["issuer_keys"]),
            set(authority.public_contract()["issuer_keys"]),
        )
        self.assertNotIn(
            "authority",
            json.dumps(relation.private_state_shape(), sort_keys=True).lower(),
        )
        self.assertNotIn(
            "relation_valid",
            json.dumps(authority.private_state_shape(), sort_keys=True).lower(),
        )

    def test_evaluators_cannot_import_the_other_truth_domain(self) -> None:
        relation_source = (ROOT / "relation_evaluator.py").read_text(
            encoding="utf-8"
        )
        authority_source = (ROOT / "authority_evaluator.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("authority_truth_broker", relation_source)
        self.assertNotIn("authority_private", relation_source)
        self.assertNotIn("relation_truth_broker", authority_source)
        self.assertNotIn("relation_private", authority_source)

    def test_worker_has_no_truth_broker_or_evaluator_import(self) -> None:
        source = (ROOT / "baseline_worker.py").read_text(encoding="utf-8")
        for forbidden in (
            "relation_truth_broker",
            "authority_truth_broker",
            "relation_evaluator",
            "authority_evaluator",
            "world_factory",
        ):
            self.assertNotIn(forbidden, source)

    def test_parent_owns_exact_bytes_operations_ledgers_and_exit_log(self) -> None:
        row = self.report["runs"][0]
        record = row["parent_record"]
        self.assertEqual("PARENT_PIPE_CAPTURE", record["byte_provenance"])
        self.assertEqual(
            len(bytes.fromhex(record["stdin_hex"])),
            record["stdin_byte_count"],
        )
        self.assertEqual(
            len(bytes.fromhex(record["stdout_hex"])),
            record["stdout_byte_count"],
        )
        self.assertEqual(0, record["exit"]["returncode"])
        self.assertGreater(len(record["operations"]), 0)
        self.assertGreater(len(record["relation_broker_ledger"]), 0)
        self.assertGreater(len(record["authority_broker_ledger"]), 0)
        tampered = copy.deepcopy(record)
        tampered["operations"].clear()
        self.assertGreater(
            len(
                run_single(
                    self.core[0],
                    BASELINE_IDS[0],
                )["parent_record"]["operations"]
            ),
            0,
        )

    def test_only_b0_through_b5_exist_and_b6_is_not_implemented(self) -> None:
        self.assertEqual(
            ("B0", "B1", "B2", "B3A", "B3B", "B4", "B5"),
            BASELINE_IDS,
        )
        self.assertFalse((ROOT / "b6_adapter.py").exists())
        self.assertEqual(
            "NOT_IMPLEMENTED_NO_OBSERVED_RESIDUAL",
            self.report["b6_status"],
        )

    def test_b0_and_b5_fully_solve_the_frozen_core(self) -> None:
        summary = self.report["summary"]["core_by_baseline"]
        for baseline in ("B0", "B5"):
            self.assertEqual(24, summary[baseline]["relation_exact"])
            self.assertEqual(24, summary[baseline]["authority_exact"])
            self.assertEqual(24, summary[baseline]["integration_exact"])
            self.assertEqual(24, summary[baseline]["worlds"])
        self.assertEqual(
            "POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED",
            self.report["existing_solution_result"],
        )

    def test_crossed_square_blocks_all_non_implications(self) -> None:
        b5 = [
            row
            for row in self.report["runs"]
            if row["baseline_id"] == "B5"
        ]
        by_truth = {}
        for row in b5:
            key = (
                row["truth_summary"]["relation_valid"],
                row["truth_summary"]["authority_valid"],
            )
            by_truth.setdefault(key, []).append(row)
        for row in by_truth[(True, False)]:
            self.assertTrue(row["relation_public"]["formed"])
            self.assertFalse(row["integration_public"]["execution_ready"])
        for row in by_truth[(False, True)]:
            self.assertFalse(row["relation_public"]["formed"])
            self.assertTrue(row["authority_public"]["authority_chain_valid"])
            self.assertFalse(row["integration_public"]["execution_ready"])
        for row in by_truth[(True, True)]:
            self.assertTrue(row["integration_public"]["execution_ready"])

    def test_relation_output_has_no_authority_conclusions(self) -> None:
        forbidden = {
            "allow",
            "permit_status",
            "mandate_valid",
            "commitment_valid",
            "reservation_valid",
            "effect",
            "acceptance",
        }
        for row in self.report["runs"]:
            self.assertTrue(
                forbidden.isdisjoint(row["relation_public"]),
                forbidden.intersection(row["relation_public"]),
            )

    def test_authority_output_has_no_relation_conclusions(self) -> None:
        forbidden = {
            "formed",
            "relation_stage",
            "horizon",
            "material_change",
            "semantic_loss",
        }
        for row in self.report["runs"]:
            self.assertTrue(
                forbidden.isdisjoint(row["authority_public"]),
                forbidden.intersection(row["authority_public"]),
            )

    def test_six_paired_mutations_and_presentation_controls(self) -> None:
        self.assertEqual(
            {
                "PARAMETER_VS_MATERIAL",
                "RETAINED_VS_LOST",
                "CURRENT_VS_STALE",
                "PRINCIPAL_VS_CONTROLLER",
                "ACTIVE_VS_REVOKED",
                "UNIQUE_VS_DUPLICATE",
            },
            set(self.mutations),
        )
        mutation_result = self.report["mutation_results"]
        self.assertTrue(mutation_result["all_six_pairs_distinguished"])
        self.assertTrue(
            mutation_result[
                "same_presentation_different_structured_semantics"
            ]
        )
        self.assertTrue(
            mutation_result[
                "different_presentation_same_structured_semantics"
            ]
        )
        self.assertEqual(
            "PRESENTATION_NOOP_CONTROL_NOT_LANGUAGE_UNDERSTANDING_EVIDENCE",
            mutation_result["language_claim"],
        )

    def test_controller_stale_revocation_and_concurrency_attacks(self) -> None:
        attacks = self.report["mutation_results"]["attacks"]
        self.assertEqual("CONTROLLER_NOT_PRINCIPAL", attacks["controller"])
        self.assertEqual("STALE_RELATION_VERSION", attacks["stale"])
        self.assertEqual("MANDATE_REVOKED", attacks["revoked"])
        self.assertEqual(
            "DUPLICATE_RESERVATION_CONFLICT",
            attacks["duplicate"],
        )
        self.assertEqual(
            1,
            self.report["mutation_results"]["duplicate_pair"][
                "successful_reservations"
            ],
        )

    def test_ack_explain_counter_commit_reserve_are_not_collapsed(self) -> None:
        gates = self.report["non_implication_gate_results"]
        for gate in (
            "ACK_NOT_EXPLAIN_BACK",
            "EXPLAIN_BACK_NOT_STANCE",
            "COUNTER_NOT_COMMITMENT",
            "COMMITMENT_NOT_RESERVATION",
            "RESERVATION_NOT_MANDATE",
            "DURABLE_RELATION_NOT_BLANKET_AUTHORITY",
            "REVOCATION_DOES_NOT_DELETE_RELATION_HISTORY",
            "MATERIALITY_DOES_NOT_GRANT_ACCEPTANCE_AUTHORITY",
        ):
            self.assertTrue(gates[gate], gate)

    def test_t5_bypasses_relation_and_authority_by_actual_execution(self) -> None:
        case = build_t5_case()
        result = execute_t5_platform(case)
        self.assertEqual("NEGATIVE_CONTROL_SPEC", case["truth_status"])
        self.assertEqual("BYPASS_COMPLETE", result["status"])
        self.assertEqual(
            [
                "VALIDATE_EXACT_REQUEST",
                "CREATE_REQUEST",
                "BUYER_APPROVE",
                "PROVISION_SEATS",
                "TARGET_READBACK",
                "CLOSE_REQUEST",
            ],
            [row["operation"] for row in result["operations"]],
        )
        self.assertEqual(5, result["target_readback"]["active_seats"])
        self.assertEqual(0, result["relation_objects_created"])
        self.assertEqual(0, result["extra_authority_objects_created"])
        broken = copy.deepcopy(case)
        del broken["platform_contract"]["authoritative_state_machine"]
        self.assertEqual(
            "BYPASS_UNAVAILABLE",
            execute_t5_platform(broken)["status"],
        )

    def test_b0_b1_b5_have_checkably_distinct_high_level_paths(self) -> None:
        names = (
            "center_relation_path",
            "workflow_relation_path",
            "composition_relation_path",
            "center_authority_path",
            "workflow_authority_path",
            "composition_authority_path",
        )
        functions = [getattr(baselines, name) for name in names]
        fingerprints = {
            inspect.getsource(function) for function in functions
        }
        self.assertEqual(len(names), len(fingerprints))
        self.assertIsNot(
            baselines.center_relation_path,
            baselines.composition_relation_path,
        )
        self.assertIsNot(
            baselines.center_authority_path,
            baselines.composition_authority_path,
        )
        self.assertEqual(
            "DISTINCT_PATHS_SAME_AUTHORING_STREAM",
            self.report["implementation_independence"],
        )

    def test_authority_section_and_events_bind_full_parent_context(self) -> None:
        attacks = self.report["binding_attack_results"]
        for name in (
            "cross_world_section_transplant",
            "cross_world_event_transplant",
            "top_level_world_id_tamper",
            "top_level_text_tamper",
            "old_complete_section_replay_after_head_change",
            "old_complete_section_replay_after_version_change",
        ):
            self.assertTrue(attacks[name]["rejected"], name)
            self.assertIn(
                attacks[name]["error"],
                {
                    "SECTION_CONTEXT_INVALID",
                    "EVENT_CONTEXT_OWNERSHIP_INVALID",
                },
            )

    def test_b1_and_b5_diverge_on_atomic_reservation_requirement(self) -> None:
        summary = self.report["summary"]["core_by_baseline"]
        self.assertEqual(21, summary["B1"]["authority_exact"])
        self.assertEqual(24, summary["B5"]["authority_exact"])
        b1_duplicate = [
            row
            for row in self.report["runs"]
            if row["baseline_id"] == "B1"
            and row["truth_summary"]["authority_mode"]
            == "DUPLICATE_RESERVATION"
        ]
        self.assertEqual(3, len(b1_duplicate))
        self.assertTrue(
            all(
                row["authority_public"]["assertion_valid"] is False
                for row in b1_duplicate
            )
        )

    def test_sequence_and_proposal_cardinality_attacks_are_rejected(self) -> None:
        attacks = self.report["sequence_cardinality_attack_results"]
        for baseline in ("B0", "B1", "B5"):
            for attack in (
                "relation_events_reversed",
                "authority_events_reversed",
                "unique_proposal_deleted",
                "proposal_duplicated",
            ):
                self.assertTrue(attacks[baseline][attack]["rejected"])
                self.assertIn(
                    attacks[baseline][attack]["error"],
                    {
                        "RELATION_SEQUENCE_OR_CARDINALITY_INVALID",
                        "AUTHORITY_SEQUENCE_OR_CARDINALITY_INVALID",
                    },
                )

    def test_residual_decision_consumes_every_required_matrix_row(self) -> None:
        matrix = self.report["residual_matrix"]
        self.assertTrue(matrix)
        self.assertTrue(all(matrix.values()))
        self.assertTrue(self.report["residual_matrix_all_pass"])
        decide = getattr(runner, "decide_residual")
        for name in matrix:
            mutated = copy.deepcopy(matrix)
            mutated[name] = False
            decision = decide(mutated)
            self.assertNotEqual(
                "POSITIVE_LOCAL_SYNTHETIC_EXISTING_COMPOSITION_SCOPED",
                decision["existing_solution_result"],
            )
            self.assertEqual(
                "NOT_IMPLEMENTED_PENDING_RESIDUAL_DIAGNOSIS",
                decision["b6_status"],
            )

    def test_authority_mode_is_the_only_private_truth_representation(self) -> None:
        self.assertNotIn(
            "authority_valid",
            {item.name for item in fields(AuthorityPrivateWorld)},
        )
        for item in self.core:
            self.assertEqual(
                item.authority_private.authority_mode == "NONE",
                item.authority_private.authority_valid,
            )

    def test_completed_run_seal_invalidates_in_place_log_tampering(self) -> None:
        verify = getattr(runner, "verify_completed_run_record")
        row = self.report["runs"][0]
        self.assertTrue(verify(row))
        self.assertNotIn("public_key_hex", row["completion_seal"])
        self.assertFalse(
            verify(row, trusted_public_key_hex="00" * 32)
        )
        anchor = row["parent_record"]["evidence_anchor_sha256"]
        self.assertEqual(
            anchor, row["relation_public"]["evidence_anchor_sha256"]
        )
        self.assertEqual(
            anchor, row["authority_public"]["evidence_anchor_sha256"]
        )
        self.assertEqual(
            anchor, row["integration_public"]["evidence_anchor_sha256"]
        )
        for mutate in (
            lambda value: value["parent_record"]["operations"].clear(),
            lambda value: value["parent_record"][
                "relation_broker_ledger"
            ].clear(),
            lambda value: value["parent_record"][
                "authority_broker_ledger"
            ].clear(),
            lambda value: value["parent_record"]["exit"].update(
                returncode=99
            ),
        ):
            tampered = copy.deepcopy(row)
            mutate(tampered)
            self.assertFalse(verify(tampered))

    def test_non_implication_stance_and_explain_are_isolated(self) -> None:
        details = self.report["non_implication_probe_details"]
        explain = details["remove_explain_back_only"]
        stance = details["remove_stance_only"]
        self.assertTrue(explain["base_relation_formed"])
        self.assertEqual(0, explain["remaining_explain_back"])
        self.assertGreater(explain["remaining_stance"], 0)
        self.assertFalse(explain["mutated_relation_formed"])
        self.assertTrue(stance["base_relation_formed"])
        self.assertGreater(stance["remaining_explain_back"], 0)
        self.assertEqual(0, stance["remaining_stance"])
        self.assertFalse(stance["mutated_relation_formed"])

    def test_core_invalid_authority_covers_all_four_attack_classes(self) -> None:
        invalid_modes = {
            item.authority_private.authority_mode
            for item in self.core
            if not item.authority_private.authority_valid
        }
        self.assertEqual(
            {
                "STALE_VERSION",
                "CONTROLLER_SUBSTITUTION",
                "REVOKED",
                "DUPLICATE_RESERVATION",
            },
            invalid_modes,
        )

    def test_reservation_broker_is_atomic_under_real_thread_race(self) -> None:
        task = self.core[0].public_packet["task"]
        for _ in range(20):
            broker = AuthorityTruthBroker(self.core[0].authority_private)
            probe = broker.concurrent_reservation_probe(task)
            self.assertEqual(1, probe["successful"])
            self.assertEqual(1, probe["conflicts"])
            self.assertEqual(
                {"RESERVATION", "RESERVATION_CONFLICT"},
                {item["kind"] for item in probe["events"]},
            )

    def test_t5_parent_state_machine_has_readback_and_idempotency(self) -> None:
        platform_class = getattr(runner, "T5AuthoritativePlatform")
        platform = platform_class(build_t5_case()["platform_contract"])
        case = build_t5_case()
        first = execute_t5_platform(
            case, platform=platform, idempotency_key="T5-REQ-1"
        )
        replay = execute_t5_platform(
            case, platform=platform, idempotency_key="T5-REQ-1"
        )
        self.assertEqual("BYPASS_COMPLETE", first["status"])
        self.assertEqual("IDEMPOTENT_REPLAY", replay["status"])
        self.assertEqual(
            first["target_readback"], replay["target_readback"]
        )
        self.assertEqual(5, platform.authoritative_readback("BUYER-01")[
            "active_seats"
        ])
        self.assertEqual(
            1,
            sum(
                row["operation"] == "PROVISION_SEATS"
                for row in platform.ledger_snapshot()
            ),
        )
        conflict = copy.deepcopy(case)
        conflict["request"]["seat_count"] = 4
        self.assertEqual(
            "IDEMPOTENCY_CONFLICT",
            execute_t5_platform(
                conflict,
                platform=platform,
                idempotency_key="T5-REQ-1",
            )["status"],
        )
        missing_buyer = copy.deepcopy(case)
        del missing_buyer["request"]["buyer"]
        self.assertEqual(
            "BYPASS_UNAVAILABLE",
            execute_t5_platform(
                missing_buyer,
                platform=platform,
                idempotency_key="T5-REQ-2",
            )["status"],
        )

    def test_report_is_honest_about_scope_and_isolation(self) -> None:
        limits = self.report["limitations"]
        self.assertIn("LOCAL_SYNTHETIC", limits)
        self.assertIn("NO_FILESYSTEM_SANDBOX", limits)
        self.assertIn("SAME_AUTHORING_STREAM", limits)
        self.assertIn("T3_NOT_REAL_TASK", limits)
        self.assertIn("T4_SYNTHETIC_TASK", limits)
        self.assertNotIn("PRODUCTION_VALIDATED", limits)


if __name__ == "__main__":
    unittest.main()
