from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from evidence_api import EvidenceAPI, load_json, reconstruct_cost  # noqa: E402
from evaluator import (  # noqa: E402
    BASELINE_COST_MODEL,
    evaluate,
    run_candidates,
)
from strategies import STRATEGIES  # noqa: E402


class Wave007CAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = load_json(BASE_DIR / "fixtures" / "evidence.json")
        cls.truth = load_json(BASE_DIR / "private" / "truth.json")
        cls.result = evaluate(cls.database, cls.truth)

    def test_public_fixture_and_hidden_truth_are_closed(self) -> None:
        public_tokens = set(self.database["worlds"])
        truth_tokens = {
            row["world_token"] for row in self.truth["worlds"]
        }
        self.assertEqual(public_tokens, truth_tokens)
        self.assertEqual(len(public_tokens), 15)
        serialized_public = json.dumps(self.database, sort_keys=True)
        for hidden_field in (
            '"safe_to_rely"',
            '"business_accepted"',
            '"pair"',
            '"variant"',
        ):
            self.assertNotIn(hidden_field, serialized_public)

    def test_candidates_do_not_reference_fixture_truth_or_private_keys(self) -> None:
        source = (
            (BASE_DIR / "strategies.py").read_text(encoding="utf-8")
            + (BASE_DIR / "evidence_api.py").read_text(encoding="utf-8")
        )
        self.assertNotIn("truth.json", source)
        self.assertNotIn("DEFAULT_TRUTH", source)
        self.assertNotIn("Ed25519PrivateKey", source)
        self.assertNotIn("build_public_fixture", source)

    def test_all_strategies_emit_actual_validation_operations(self) -> None:
        valid_token = next(
            row["world_token"]
            for row in self.truth["worlds"]
            if row["pair"] == "static" and row["variant"] == "VALID"
        )
        rows = run_candidates(self.database, STRATEGIES)
        for row in rows:
            if row["world_token"] != valid_token:
                continue
            operations = {
                entry["operation"] for entry in row["operation_log"]
            }
            self.assertTrue({
                "READ_EVIDENCE",
                "VERIFY_SIGNATURE",
                "VALIDATE_BINDING",
                "VALIDATE_FRESHNESS",
                "VALIDATE_AUTHORITY",
            }.issubset(operations), row["implementation_id"])

    def test_cost_is_reconstructed_from_raw_log_not_label(self) -> None:
        token = sorted(self.database["worlds"])[0]
        function = STRATEGIES["DECLARATION"]
        left = run_candidates(
            self.database, {"DECLARATION": function}
        )
        right = run_candidates(
            self.database, {"SLA_RECOVERY": function}
        )
        left_row = next(row for row in left if row["world_token"] == token)
        right_row = next(row for row in right if row["world_token"] == token)
        self.assertEqual(left_row["decision"], right_row["decision"])
        self.assertEqual(left_row["cost"], right_row["cost"])
        for log in right_row["operation_log"]:
            log["strategy_label"] = "ARBITRARY"
        self.assertEqual(
            reconstruct_cost(
                right_row["operation_log"], BASELINE_COST_MODEL
            ),
            right_row["cost"],
        )

    def test_pre_registered_attack_regressions(self) -> None:
        attacks = self.result["attacks"]
        self.assertTrue(
            attacks["opaque_rename"]["behavior_and_cost_invariant"]
        )
        self.assertTrue(
            attacks["label_function_swap"][
                "implementation_results_and_cost_invariant"
            ]
        )
        self.assertTrue(
            attacks["truth_label_flip"][
                "candidate_decisions_and_logs_invariant"
            ]
        )
        self.assertTrue(
            attacks["self_report_injection"][
                "independent_metrics_invariant"
            ]
        )
        self.assertTrue(
            attacks["missing_conflicting_observations"][
                "all_three_remain_distinct"
            ]
        )
        self.assertFalse(
            attacks["duplicate_evidence"]["rely"]
        )
        for field_rows in attacks["bytes_binding"].values():
            self.assertTrue(
                all(not row["rely"] for row in field_rows.values())
            )
        for field_rows in attacks[
            "signed_observation_bytes_binding"
        ].values():
            self.assertEqual(
                {row["decision_state"] for row in field_rows.values()},
                {"UNKNOWN"},
            )

    def test_decisive_evidence_deletion_changes_reliance(self) -> None:
        attacks = self.result["attacks"]
        for row in attacks["evidence_deletion"].values():
            self.assertEqual(row["relied_count"], 0)
        for row in attacks["dependency_deletion"][
            "authority_status"
        ].values():
            self.assertEqual(row["relied_count"], 0)
        self.assertEqual(
            attacks["dependency_deletion"]["probe_freshness"][
                "IMPL_LATEST_PROBE"
            ]["relied_count"],
            0,
        )
        baseline_sla_rely = self.result["per_strategy"][
            "IMPL_SLA_RECOVERY"
        ]["confusion"]["TP"]
        deleted_sla_rely = attacks["dependency_deletion"][
            "recovery_receipt"
        ]["IMPL_SLA_RECOVERY"]["relied_count"]
        self.assertLess(deleted_sla_rely, baseline_sla_rely)

    def test_repeated_access_and_log_mutations_have_explicit_cost(self) -> None:
        repeated = self.result["attacks"]["repeated_access_billing"]
        self.assertEqual(repeated["operation_counts"]["READ_EVIDENCE"], 2)
        self.assertEqual(
            repeated["operation_counts"]["VERIFY_SIGNATURE"], 2
        )
        self.assertEqual(
            repeated["operation_counts"]["VALIDATE_FRESHNESS"], 2
        )
        recomputed = self.result["attacks"]["operation_log_recompute"]
        self.assertEqual(recomputed["baseline"], recomputed["reordered"])
        self.assertLess(
            recomputed["one_operation_deleted"]["total_evidence_cost"],
            recomputed["baseline"]["total_evidence_cost"],
        )
        self.assertGreater(
            recomputed["one_operation_added"]["total_evidence_cost"],
            recomputed["baseline"]["total_evidence_cost"],
        )
        self.assertFalse(recomputed["candidate_cost_field_used"])

    def test_sensitivity_has_competing_regions_and_no_universal_winner(self) -> None:
        sensitivity = self.result["sensitivity"]
        self.assertGreater(
            sensitivity["unique_winner_counts"]["IMPL_DECLARATION"], 0
        )
        self.assertGreater(
            sensitivity["unique_winner_counts"]["IMPL_LATEST_PROBE"], 0
        )
        regions = self.result["frequency_and_cost_regions"]["profiles"]
        uniform = regions["UNIFORM"]["winner_counts_including_ties"]
        failure_heavy = regions["CURRENT_FAILURE_HEAVY"][
            "winner_counts_including_ties"
        ]
        self.assertNotEqual(uniform, failure_heavy)
        self.assertIn(
            "IMPL_RECEIPT_WINDOW",
            self.result["pareto"]["dominated_by"],
        )
        self.assertFalse(
            self.result["claims"][
                "single_aggregate_winner_is_universal_recommendation"
            ]
        )

    def test_committed_result_is_deterministic(self) -> None:
        committed = load_json(BASE_DIR / "results" / "evaluation.json")
        self.assertEqual(self.result, committed)

    def test_direct_mutation_rejects_stale_signature(self) -> None:
        mutated = copy.deepcopy(self.database)
        token = next(
            row["world_token"]
            for row in self.truth["worlds"]
            if row["pair"] == "static" and row["variant"] == "VALID"
        )
        record = mutated["worlds"][token]["evidence"]["declaration"][
            "record"
        ]
        record["payload"]["command_hash"] = "MUTATED-AFTER-SIGNING"
        api = EvidenceAPI(mutated, token, "DIRECT-MUTATION")
        self.assertFalse(api.verify_signature(record))


if __name__ == "__main__":
    unittest.main()
