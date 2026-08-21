import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import (  # noqa: E402
    compare_strategies,
    evaluate,
    forgery_mutations,
    normalize_schema_alias,
)
from simulator import (  # noqa: E402
    OPERATION,
    SHARED_TASK_ID,
    SHARED_TASK_SHA256,
    TRUTH,
    _sign,
    action_coordinates,
    anchor_fork,
    build_contract,
    build_effect,
    build_scenarios,
    schema_alias,
    sha256_value,
)


class EffectReopenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = build_contract()
        cls.scenarios = build_scenarios()
        cls.comparison = compare_strategies()

    def test_shared_task_and_denominator_are_frozen(self):
        self.assertEqual(
            "W6-STERILE-ROUTE-SIMULATION-001", SHARED_TASK_ID
        )
        self.assertEqual(
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3",
            SHARED_TASK_SHA256,
        )
        expected_truth = sha256_value(TRUTH)
        for scenario in self.scenarios.values():
            for contract in [
                scenario["archived_contract"],
                scenario["current_contract"],
            ]:
                self.assertEqual(OPERATION, contract["operation"])
                self.assertEqual(expected_truth, contract["frozen_truth_sha256"])

    def test_complete_ladder_needs_five_distinct_evidence_roles(self):
        package = build_effect(self.contract)
        result = evaluate(package, self.contract)
        self.assertTrue(result["current_accepted"])
        self.assertEqual(4, result["highest_level"])
        self.assertEqual(
            [
                "ATTEMPT",
                "DELIVERY",
                "RECIPIENT_ACK",
                "DOMAIN_POSTCONDITION",
                "BENEFICIARY_ACCEPTANCE",
            ],
            result["levels_valid"],
        )
        self.assertEqual(
            {
                "CONTROLLER-W6",
                "ANCHOR-W6",
                "SIM-RECIPIENT",
                "SIMULATOR-W6",
                "BENEFICIARY-REVIEWER",
            },
            {
                package["attempt"]["issuer"],
                package["delivery"]["receipt"]["issuer"],
                package["delivery"]["anchor"]["issuer"],
                package["recipient_ack"]["issuer"],
                package["domain_postcondition"]["issuer"],
                package["beneficiary_acceptance"]["issuer"],
            },
        )

    def test_each_missing_stage_stops_at_predecessor(self):
        for level in range(5):
            package = build_effect(self.contract, stop_level=level)
            result = evaluate(package, self.contract)
            self.assertEqual(level, result["highest_level"])

    def test_predecessor_self_claim_never_promotes(self):
        mutations = forgery_mutations()
        self.assertEqual(4, len(mutations))
        self.assertEqual(0, sum(item["false_promotion"] for item in mutations))
        for item in mutations:
            self.assertEqual(
                item["predecessor_level"], item["accepted_level"]
            )

    def test_pretty_delivery_without_postcondition_is_not_effect(self):
        package = build_effect(self.contract, stop_level=2)
        result = evaluate(package, self.contract)
        self.assertEqual(2, result["highest_level"])
        self.assertFalse(result["current_accepted"])

    def test_exact_replay_prefers_immutable(self):
        case = self.comparison["cases"]["exact_replay"]
        self.assertEqual("IMMUTABLE_REPLAY", case["best_strategy"])
        self.assertEqual(
            0,
            case["strategies"]["IMMUTABLE_REPLAY"][
                "recovery_time_steps"
            ],
        )

    def test_schema_alias_prefers_adapter_without_hiding_refusal(self):
        case = self.comparison["cases"]["schema_alias"]
        self.assertEqual("MIGRATION_ADAPTER", case["best_strategy"])
        refusal = build_effect(
            self.contract, stop_level=3, beneficiary_refusal=True
        )
        normalized = normalize_schema_alias(schema_alias(refusal))
        result = evaluate(normalized, self.contract)
        self.assertEqual("REFUSE", result["terminal_state"])
        self.assertFalse(result["current_accepted"])

    def test_material_contract_environment_and_key_changes_need_reauth(self):
        for case_id in [
            "contract_change",
            "key_rotation",
            "material_semantic_change",
        ]:
            case = self.comparison["cases"][case_id]
            self.assertEqual("REAUTHORIZE", case["best_strategy"])
            self.assertFalse(
                case["strategies"]["IMMUTABLE_REPLAY"][
                    "current_accepted"
                ]
            )
            self.assertFalse(
                case["strategies"]["MIGRATION_ADAPTER"][
                    "current_accepted"
                ]
            )
            self.assertTrue(
                case["strategies"]["REAUTHORIZE"]["current_accepted"]
            )

    def test_recipient_withdrawal_archives_old_effect(self):
        case = self.comparison["cases"]["recipient_withdrawal"]
        self.assertEqual("REAUTHORIZE", case["best_strategy"])
        self.assertEqual(
            "HISTORICAL_ONLY_NO_CURRENT_EFFECT",
            case["strategies"]["IMMUTABLE_REPLAY"][
                "residual_state_after_withdrawal"
            ],
        )
        self.assertEqual(
            "OLD_EVIDENCE_ARCHIVED_NEW_EFFECT_ISOLATED",
            case["strategies"]["REAUTHORIZE"][
                "residual_state_after_withdrawal"
            ],
        )

    def test_anchor_fork_is_not_repaired_by_alias_adapter(self):
        case = self.comparison["cases"]["anchor_fork"]
        self.assertFalse(
            case["strategies"]["MIGRATION_ADAPTER"]["current_accepted"]
        )
        fork_alias = schema_alias(
            anchor_fork(build_effect(self.contract), self.contract)
        )
        result = evaluate(
            normalize_schema_alias(fork_alias), self.contract
        )
        self.assertFalse(result["current_accepted"])
        self.assertIn("ANCHOR_FORK", result["errors"])

    def test_partial_and_delayed_recovery_prefer_immutable_resume(self):
        for case_id in ["partial_recovery", "delayed_ack"]:
            case = self.comparison["cases"][case_id]
            self.assertEqual("IMMUTABLE_REPLAY", case["best_strategy"])
            self.assertTrue(
                case["strategies"]["IMMUTABLE_REPLAY"][
                    "current_accepted"
                ]
            )
            self.assertLess(
                case["strategies"]["IMMUTABLE_REPLAY"][
                    "recovery_time_steps"
                ],
                case["strategies"]["REAUTHORIZE"][
                    "recovery_time_steps"
                ],
            )

    def test_single_side_partial_never_becomes_delivery(self):
        package = self.scenarios["single_side_partial"]["input"]
        result = evaluate(package, self.contract)
        self.assertEqual(0, result["highest_level"])
        self.assertIn("DELIVERY_SET_INCOMPLETE", result["errors"])

    def test_beneficiary_refusal_and_holder_revocation_are_safe_rejection(self):
        for case_id in ["beneficiary_refusal", "holder_revocation"]:
            case = self.comparison["cases"][case_id]
            self.assertEqual("SAFE_REJECTION", case["best_strategy"])
            self.assertFalse(
                any(
                    item["current_accepted"]
                    for item in case["strategies"].values()
                )
            )
        self.assertEqual(
            "REFUSE",
            self.comparison["cases"]["beneficiary_refusal"][
                "strategies"
            ]["IMMUTABLE_REPLAY"]["current_terminal_state"],
        )

    def test_same_idempotency_key_changed_command_is_rejected(self):
        package = build_effect(self.contract, stop_level=0)
        body = copy.deepcopy(package["attempt"]["body"])
        original_key = body["idempotency_key"]
        body["action_digest"] = "f" * 64
        package["attempt"] = _sign(
            self.contract, "CONTROLLER-W6", "EFFECT_ATTEMPT", body
        )
        result = evaluate(package, self.contract)
        self.assertEqual(original_key, body["idempotency_key"])
        self.assertEqual(-1, result["highest_level"])
        self.assertIn("EFFECT_COORDINATE_MISMATCH", result["errors"])

    def test_metrics_include_false_positive_negative_cost_and_recovery(self):
        for case in self.comparison["cases"].values():
            for result in case["strategies"].values():
                for field in [
                    "false_positive",
                    "false_negative",
                    "recovery_time_steps",
                    "disclosure_units",
                    "evidence_coordination_operations",
                    "net_task_value",
                    "stale_reuse",
                ]:
                    self.assertIn(field, result)
                self.assertEqual(0, result["stale_reuse"])

    def test_unknown_refuse_absent_remain_distinct(self):
        self.assertEqual(
            ["UNKNOWN", "REFUSE", "ABSENT"],
            self.comparison["terminal_states_preserved"],
        )
        observations = build_effect(self.contract)[
            "terminal_observations"
        ]
        self.assertEqual(3, len(set(observations.values())))


if __name__ == "__main__":
    unittest.main()
