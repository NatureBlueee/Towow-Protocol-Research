from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from broker import load_json, reconstruct_cost  # noqa: E402
from evaluator import evaluate  # noqa: E402
from runner import (  # noqa: E402
    BASELINE_COST_MODEL,
    DEFAULT_REGISTRY,
    run_candidates,
    run_worker,
)


class Wave007C2AcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.database = load_json(BASE_DIR / "fixtures" / "evidence.json")
        cls.truth = load_json(BASE_DIR / "private" / "truth.json")
        cls.result = evaluate(cls.database, cls.truth)

    def test_public_fixture_and_hidden_truth_are_closed(self) -> None:
        self.assertEqual(
            set(self.database["worlds"]),
            {row["world_token"] for row in self.truth["worlds"]},
        )
        public = json.dumps(self.database, sort_keys=True)
        for hidden in (
            '"safe_to_rely"',
            '"business_accepted"',
            '"pair"',
            '"variant"',
        ):
            self.assertNotIn(hidden, public)

    def test_candidate_module_does_not_import_parent_or_private_modules(
        self,
    ) -> None:
        source = (
            (BASE_DIR / "candidate_worker.py").read_text(
                encoding="utf-8"
            )
            + (BASE_DIR / "candidate_strategies.py").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("from broker", source)
        self.assertNotIn("from runner", source)
        self.assertNotIn("private.build", source)
        self.assertNotIn("Ed25519PrivateKey", source)

    def test_exact_audit_authority_replay_is_rejected(self) -> None:
        mutated = copy.deepcopy(self.database)
        mutated["worlds"]["w7c-a76e20"]["evidence"][
            "authority_status"
        ] = copy.deepcopy(
            mutated["worlds"]["w7c-50de71"]["evidence"][
                "authority_status"
            ]
        )
        rows = run_candidates(
            mutated, world_tokens=["w7c-a76e20"]
        )
        self.assertTrue(all(not row["decision"]["rely"] for row in rows))
        for row in rows:
            self.assertTrue(any(
                log["operation"] == "VALIDATE_AUTHORITY_HEAD"
                and not log["success"]
                for log in row["operation_log"]
            ))
        forged = run_worker(
            mutated,
            "w7c-a76e20",
            "IMPL_DECLARATION",
            "FORGE_AUTHORITY_CONTEXT",
            "DECLARATION",
        )
        self.assertFalse(forged["decision"]["rely"])

    def test_authority_status_carries_current_head_epoch_contract(
        self,
    ) -> None:
        active = self.database["worlds"]["w7c-50de71"]
        revoked = self.database["worlds"]["w7c-a76e20"]
        for world in (active, revoked):
            context = world["request"]
            payload = world["evidence"]["authority_status"][
                "record"
            ]["payload"]
            for field in (
                "authority_head",
                "authority_epoch",
                "authority_contract_version",
            ):
                self.assertEqual(payload[field], context[field])
        self.assertNotEqual(
            active["request"]["authority_head"],
            revoked["request"]["authority_head"],
        )

    def test_exact_audit_candidate_cannot_clear_parent_log(self) -> None:
        row = run_worker(
            self.database,
            "w7c-8f13a0",
            "IMPL_DECLARATION",
            "MALICIOUS_CLEAR_LOG",
            "DECLARATION",
        )
        self.assertTrue(row["decision"]["rely"])
        self.assertTrue(
            row["decision"]["mutation_attempt"]["local_clear_blocked"]
        )
        self.assertTrue(
            row["decision"]["mutation_attempt"]["broker_clear_blocked"]
        )
        self.assertGreater(row["cost"]["api_operations"], 0)
        self.assertEqual(
            sum(
                log["operation"] == "DENIED_RPC"
                for log in row["operation_log"]
            ),
            1,
        )

    def test_exact_audit_candidate_identity_spoof_is_ignored(self) -> None:
        row = run_worker(
            self.database,
            "w7c-8f13a0",
            "IMPL_DECLARATION",
            "SPOOF_IMPLEMENTATION_ID",
            "DECLARATION",
        )
        self.assertEqual(row["implementation_id"], "IMPL_DECLARATION")
        self.assertEqual(
            row["candidate_claimed_implementation_id"],
            "IMPL_SLA_RECOVERY",
        )
        attack = self.result["direct_mutations"][
            "audit_failure_3_identity_spoof"
        ]
        self.assertEqual(
            attack["evaluator_group_identity"],
            "IMPL_DECLARATION",
        )

    def test_candidate_runtime_private_state_read_is_blocked(self) -> None:
        row = run_worker(
            self.database,
            "w7c-8f13a0",
            "IMPL_DECLARATION",
            "PRIVATE_STATE_READ_ATTEMPT",
            "DECLARATION",
        )
        self.assertTrue(row["decision"]["private_state_read_blocked"])

    def test_all_strategies_actually_validate_evidence(self) -> None:
        rows = run_candidates(
            self.database, world_tokens=["w7c-8f13a0"]
        )
        for row in rows:
            operations = {
                log["operation"] for log in row["operation_log"]
            }
            self.assertTrue({
                "READ_EVIDENCE",
                "VERIFY_SIGNATURE",
                "VALIDATE_BINDING",
                "VALIDATE_FRESHNESS",
                "VALIDATE_AUTHORITY_HEAD",
            }.issubset(operations), row["implementation_id"])

    def test_cost_comes_only_from_parent_log(self) -> None:
        attack = self.result["direct_mutations"][
            "operation_log_recompute"
        ]
        self.assertEqual(attack["baseline"], attack["reordered"])
        self.assertLess(
            attack["one_deleted"]["total_evidence_cost"],
            attack["baseline"]["total_evidence_cost"],
        )
        self.assertGreater(
            attack["one_added"]["total_evidence_cost"],
            attack["baseline"]["total_evidence_cost"],
        )
        self.assertFalse(attack["candidate_cost_field_used"])
        row = run_worker(
            self.database,
            "w7c-8f13a0",
            "IMPL_DECLARATION",
            "DECLARATION",
            "ANY-DISPLAY-LABEL",
        )
        self.assertEqual(
            row["cost"],
            reconstruct_cost(
                row["operation_log"], BASELINE_COST_MODEL
            ),
        )

    def test_previous_attack_classes_are_rerun_in_c2(self) -> None:
        attacks = self.result["direct_mutations"]
        self.assertTrue(
            attacks["opaque_rename"]["decisions_and_cost_invariant"]
        )
        self.assertTrue(
            attacks["self_report_injection"][
                "independent_metrics_invariant"
            ]
        )
        self.assertTrue(
            attacks["label_only_rename"][
                "decisions_and_cost_invariant"
            ]
        )
        self.assertTrue(
            attacks["truth_label_flip"][
                "candidate_decisions_and_logs_invariant"
            ]
        )
        self.assertTrue(
            attacks["missing_conflicting_observations"][
                "all_three_remain_distinct"
            ]
        )

    def test_evidence_deletion_signature_binding_and_duplicate_fail(
        self,
    ) -> None:
        attacks = self.result["direct_mutations"]
        for row in attacks["primary_evidence_deletion"].values():
            self.assertEqual(row["relied_count"], 0)
        for row in attacks["authority_status_deletion"].values():
            self.assertFalse(row["rely"])
        self.assertFalse(attacks["probe_freshness_deletion"]["rely"])
        self.assertFalse(attacks["recovery_receipt_deletion"]["rely"])
        for row in attacks["unauthorized_signature"].values():
            self.assertFalse(row["rely"])
            self.assertGreater(row["signature_failure_count"], 0)
        for mutation in attacks["bytes_binding"].values():
            self.assertTrue(
                all(not row["rely"] for row in mutation.values())
            )
        self.assertFalse(attacks["duplicate_receipt"]["rely"])

    def test_repeated_access_is_billed_without_implicit_cache(self) -> None:
        repeated = self.result["direct_mutations"][
            "repeated_access_billing"
        ]
        self.assertEqual(repeated["operation_counts"], {
            "READ_EVIDENCE": 2,
            "VALIDATE_FRESHNESS": 2,
            "VERIFY_SIGNATURE": 2,
        })
        self.assertEqual(repeated["cost"]["api_operations"], 7)

    def test_sensitivity_and_pareto_remain_conditional(self) -> None:
        self.assertEqual(
            set(self.result["pareto"]["frontier"]),
            {"IMPL_DECLARATION", "IMPL_LATEST_PROBE"},
        )
        counts = self.result["sensitivity"][
            "unique_winner_counts"
        ]
        self.assertGreater(counts["IMPL_DECLARATION"], 0)
        self.assertGreater(counts["IMPL_LATEST_PROBE"], 0)
        profiles = self.result["frequency_and_cost_regions"][
            "profiles"
        ]
        self.assertNotEqual(
            profiles["UNIFORM"]["winner_counts_including_ties"],
            profiles["CURRENT_FAILURE_HEAVY"][
                "winner_counts_including_ties"
            ],
        )
        self.assertFalse(
            self.result["claims"]["universal_winner_claimed"]
        )

    def test_committed_result_is_deterministic(self) -> None:
        self.assertEqual(
            self.result,
            load_json(BASE_DIR / "results" / "evaluation.json"),
        )

    def test_same_researcher_tests_are_not_independent_evidence(
        self,
    ) -> None:
        self.assertFalse(
            self.result["claims"][
                "implementation_self_check_is_independent_evidence"
            ]
        )


if __name__ == "__main__":
    unittest.main()
