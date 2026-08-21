from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import runner  # noqa: E402
from g3disc.common import canonical_sha256, load_json  # noqa: E402


class QuantifierDiscriminatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public = load_json(runner.PUBLIC_PATH)
        cls.private = load_json(runner.PRIVATE_PATH)
        cls.report = runner.run()
        cls.by_pair = {
            (item["world_id"], item["arm_id"]): item
            for item in cls.report["results"]
        }

    def world(self, world_id: str) -> dict:
        return next(
            world
            for world in self.public["worlds"]
            if world["world_id"] == world_id
        )

    def results_for(self, world_id: str) -> list[dict]:
        return [
            item
            for item in self.report["results"]
            if item["world_id"] == world_id
        ]

    def test_fixture_has_six_opaque_worlds_and_no_expected_label(self) -> None:
        self.assertEqual(
            [world["world_id"] for world in self.public["worlds"]],
            ["E01", "E02", "E03", "E04", "E05", "E06"],
        )
        serialized = json.dumps(self.public, sort_keys=True)
        for forbidden in [
            "expected_label",
            "expected_category",
            "policy_hint",
            "bounded_unreachable_hint",
        ]:
            self.assertNotIn(forbidden, serialized)

    def test_full_run_uses_five_arms_and_separate_workers(self) -> None:
        self.assertEqual(self.report["world_count"], 6)
        self.assertEqual(self.report["arm_count"], 5)
        self.assertEqual(self.report["result_count"], 30)
        self.assertFalse(
            self.report["separation"][
                "actual_policy_worker_received_private_oracle"
            ]
        )
        self.assertFalse(
            self.report["separation"][
                "method_formation_witness_received_private_oracle"
            ]
        )
        sample = self.report["results"][0]["oracle_receipts"]
        self.assertEqual(sample["closure"]["worker"], "closure-oracle-v1")
        self.assertEqual(
            sample["measurable"]["worker"], "measurable-oracle-v1"
        )
        self.assertEqual(
            sample["robust"]["worker"], "robust-tree-checker-v1"
        )

    def test_all_receipts_bind_required_coordinates_and_evidence(self) -> None:
        required_r = {
            "R_physical_exists",
            "R_measurable_exists",
            "R_actual",
            "R_effect_robust",
            "R_safe_robust",
            "R_terminal_robust",
        }
        for item in self.report["results"]:
            receipt = item["g3_receipt"]
            body = receipt["body"]
            self.assertEqual(canonical_sha256(body), receipt["body_sha256"])
            self.assertEqual(set(body["R"]), required_r)
            self.assertEqual(body["task_diff"], item["exact_task_diff"])
            binding = copy.deepcopy(item["evidence_binding"])
            claimed_hash = binding.pop("binding_sha256")
            self.assertEqual(canonical_sha256(binding), claimed_hash)
            self.assertEqual(
                binding["actual_policy_transcript_sha256"],
                canonical_sha256(item["actual_policy_transcript"]),
            )

    def test_w1_direct_path_is_preexisting_not_formation(self) -> None:
        for item in self.results_for("E01"):
            body = item["g3_receipt"]["body"]
            self.assertEqual(item["category"], "PREEXISTING_QUALIFIED_PATH")
            self.assertEqual(
                (body["C"], body["N"], body["E"], body["T"], body["V"]),
                ("SAT", "NONE", "SAME", "INVARIANT", "VALID"),
            )

    def test_w2_binds_old_unsat_and_post_extension_sat(self) -> None:
        for item in self.results_for("E02"):
            body = item["g3_receipt"]["body"]
            closure = item["oracle_receipts"]["closure"]
            self.assertEqual(item["category"], "QUALIFIED_CONDITION_FORMATION")
            self.assertEqual(closure["old_closure"]["result"], "UNSAT")
            self.assertEqual(closure["extended_closure"]["result"], "SAT")
            self.assertEqual(
                (body["C"], body["N"], body["E"], body["T"], body["V"]),
                ("UNSAT", "NEW_TOKEN", "CHANGED", "INVARIANT", "VALID"),
            )
            self.assertEqual(body["counterfactual"]["remove_result"], "UNSAT")

    def test_w3_prefix_sat_new_token_preserves_same_kernel(self) -> None:
        for item in self.results_for("E03"):
            body = item["g3_receipt"]["body"]
            self.assertEqual(item["category"], "PREFIX_SAT_NEW_TOKEN")
            self.assertEqual(
                (body["C"], body["N"], body["E"], body["T"], body["V"]),
                ("SAT", "NEW_TOKEN", "SAME", "INVARIANT", "VALID"),
            )
            self.assertEqual(body["counterfactual"]["remove_result"], "UNSAT")
            raw = item["oracle_receipts"]["counterfactual"]
            self.assertTrue(raw["derived_effect_graph_valid"])
            self.assertTrue(raw["derived_effect_reset_verified"])

    def test_w4_is_actual_policy_miss_not_bounded_unreachable(self) -> None:
        action_variants = set()
        for item in self.results_for("E04"):
            body = item["g3_receipt"]["body"]
            self.assertEqual(item["category"], "ACTUAL_POLICY_MISS")
            self.assertNotEqual(item["category"], "BOUNDED_UNREACHABLE")
            self.assertEqual(body["C"], "SAT")
            self.assertEqual(body["R"]["R_measurable_exists"], "TRUE")
            self.assertEqual(body["R"]["R_actual"], "FALSE")
            action_variants.add(
                tuple(
                    item["actual_policy_transcript"]["method_return"][
                        "action_ids"
                    ]
                )
            )
        self.assertEqual(action_variants, {("execute_with_token",)})

    def test_w5_open_inventory_is_unknown_even_after_frontier_exhaustion(self) -> None:
        for item in self.results_for("E05"):
            body = item["g3_receipt"]["body"]
            self.assertEqual(item["category"], "UNKNOWN")
            self.assertEqual(body["C"], "UNKNOWN")
            self.assertEqual(body["R"]["R_physical_exists"], "UNKNOWN")
            self.assertEqual(body["R"]["R_measurable_exists"], "UNKNOWN")
            self.assertEqual(body["R"]["R_actual"], "TRUE")
            self.assertEqual(body["R"]["R_safe_robust"], "TRUE")
            self.assertEqual(body["R"]["R_terminal_robust"], "TRUE")

    def test_closed_complete_variant_can_be_bounded_unreachable(self) -> None:
        public_world = copy.deepcopy(self.world("E05"))
        public_world["inventory"].update(
            {
                "action_inventory": "COMPLETE",
                "response_family": "COMPLETE",
                "transition_semantics": "COMPLETE",
                "unresolved_items": [],
            }
        )
        result = runner.evaluate_one(
            public_world,
            copy.deepcopy(self.private["worlds"]["E05"]),
            "B-MATURE-PLANNER-WORKFLOW",
            self.public["baseline_envelopes"][
                "B-MATURE-PLANNER-WORKFLOW"
            ],
        )
        self.assertEqual(result["category"], "BOUNDED_UNREACHABLE")
        self.assertEqual(result["g3_receipt"]["body"]["C"], "UNSAT")

    def test_w6_owner_fork_has_exact_diff_and_owner_receipt(self) -> None:
        for item in self.results_for("E06"):
            body = item["g3_receipt"]["body"]
            diff = body["task_diff"]
            self.assertEqual(item["category"], "AUTHORIZED_NEW_EPISODE")
            self.assertEqual(body["T"], "OWNER_AUTHORIZED_NEW_EPISODE")
            self.assertEqual(
                diff["classification"], "OWNER_AUTHORIZED_NEW_EPISODE"
            )
            self.assertNotEqual(
                diff["original_task_sha256"], diff["result_task_sha256"]
            )
            self.assertEqual(
                diff["material_fields"],
                ["/q", "/v0/minimum_integrity"],
            )
            self.assertTrue(diff["owner_authorization_receipts"])
            self.assertFalse(diff["controller_claim_refs"])

    def test_controller_substitution_is_distinct_and_exact(self) -> None:
        world = self.world("E06")
        t_value, diff = runner.make_task_diff(
            world,
            {"action_ids": ["controller_rewrite"]},
            self.private["worlds"]["E06"],
        )
        self.assertEqual(t_value, "CONTROLLER_SUBSTITUTION")
        self.assertEqual(diff["classification"], "CONTROLLER_SUBSTITUTION")
        self.assertFalse(diff["owner_authorization_receipts"])
        self.assertTrue(diff["controller_claim_refs"])
        owner_item = copy.deepcopy(self.by_pair[("E06", "C-FORMATION")])
        body = owner_item["g3_receipt"]["body"]
        body["T"] = t_value
        body["V"] = "INVALID"
        body["task_diff"] = diff
        category, _ = runner.classify(
            body,
            old_result="UNSAT",
            extended_result="UNSAT",
        )
        self.assertEqual(category, "INVALID_SUBSTITUTION")

    def test_owner_refusal_is_not_controller_substitution(self) -> None:
        oracle = copy.deepcopy(self.private["worlds"]["E06"])
        oracle["actual_response"] = "REFUSE"
        t_value, diff = runner.make_task_diff(
            self.world("E06"),
            {"action_ids": ["request_owner_change"]},
            oracle,
        )
        self.assertEqual(t_value, "INVARIANT")
        self.assertEqual(diff["classification"], "UNCHANGED")
        self.assertFalse(diff["controller_claim_refs"])

    def test_invalid_trace_is_not_safe_or_terminal(self) -> None:
        for item in self.results_for("E04"):
            robust = item["oracle_receipts"]["robust"]
            self.assertFalse(robust["effect_robust"])
            self.assertFalse(robust["safe_robust"])
            self.assertFalse(robust["terminal_robust"])

    def test_counterfactual_fails_closed_on_incomplete_derived_effect_graph(self) -> None:
        oracle = copy.deepcopy(self.private["worlds"]["E03"])
        oracle["derived_effects"]["holder_sign"] = ["purpose_token"]
        result = runner.evaluate_one(
            self.world("E03"),
            oracle,
            "C-FORMATION",
            self.public["baseline_envelopes"]["C-FORMATION"],
        )
        raw = result["oracle_receipts"]["counterfactual"]
        self.assertFalse(raw["derived_effect_graph_valid"])
        self.assertEqual(
            result["g3_receipt"]["body"]["counterfactual"]["status"],
            "UNKNOWN",
        )
        self.assertEqual(result["g3_receipt"]["body"]["V"], "INVALID")
        self.assertNotEqual(result["category"], "PREFIX_SAT_NEW_TOKEN")

    def test_method_witness_is_public_only_and_does_not_claim_verdict(self) -> None:
        for item in self.report["results"]:
            proposal = item["actual_policy_transcript"]["method_return"][
                "formation_witness_proposal"
            ]
            self.assertEqual(
                proposal["source"],
                "PUBLIC_PACKET_AND_SELECTED_ACTIONS_ONLY",
            )
            self.assertFalse(proposal["claims_oracle_verdict"])
        source = (runner.WORKERS / "actual_policy_worker.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("oracles.json", source)
        self.assertNotIn("expected_category", source)

    def test_baselines_do_not_change_actions_by_arm_name(self) -> None:
        for world in self.public["worlds"]:
            variants = {
                tuple(
                    self.by_pair[(world["world_id"], arm)][
                        "actual_policy_transcript"
                    ]["method_return"]["action_ids"]
                )
                for arm in runner.ARMS
            }
            self.assertEqual(len(variants), 1, world["world_id"])
        legal = self.by_pair[("E02", "B-CENTER-LEGAL-CONTROL")]
        equal = self.by_pair[("E02", "B-CENTER-EQUAL-ENVELOPE")]
        self.assertEqual(
            legal["actual_policy_transcript"]["method_return"]["action_ids"],
            equal["actual_policy_transcript"]["method_return"]["action_ids"],
        )
        self.assertEqual(
            legal["comparison_scope"],
            "DIFFERENT_ENVIRONMENT_CONSTRUCTIVE_COUNTEREXAMPLE",
        )
        self.assertEqual(equal["comparison_scope"], "SAME_WORLD_SAME_ENVELOPE")


if __name__ == "__main__":
    unittest.main()
