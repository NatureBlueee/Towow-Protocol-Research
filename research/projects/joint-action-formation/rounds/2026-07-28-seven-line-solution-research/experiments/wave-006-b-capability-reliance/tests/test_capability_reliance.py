from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
ROUND = ROOT.parents[1]
sys.path.insert(0, str(ROOT))

from evaluator import evaluate  # noqa: E402
from simulator import STRATEGIES, load_json, run_simulation, visible_snapshot  # noqa: E402


class CapabilityRelianceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = load_json(ROOT / "fixtures" / "timeline.json")
        cls.result = evaluate(cls.fixture)
        cls.simulation = run_simulation(cls.fixture)

    def _row(self, scenario_id: str, label: str) -> dict:
        return next(
            row for row in self.simulation["rows"]
            if row["scenario_id"] == scenario_id and row["label"] == label
        )

    def test_01_shared_task_bytes_are_frozen(self) -> None:
        shared_task = ROUND / "WAVE-006-SHARED-TASK.md"
        actual = hashlib.sha256(shared_task.read_bytes()).hexdigest()
        self.assertEqual(
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3",
            actual,
        )
        self.assertEqual(actual, self.fixture["shared_task"]["source_sha256"])
        self.assertEqual(
            "W6-STERILE-ROUTE-SIMULATION-001",
            self.fixture["shared_task"]["task_id"],
        )

    def test_02_exactly_four_strategies_face_each_row(self) -> None:
        expected = {
            "DECLARATION",
            "LATEST_PROBE",
            "RECEIPT_HISTORY",
            "SLA_RECOVERY",
        }
        self.assertEqual(expected, set(STRATEGIES))
        for row in self.simulation["rows"]:
            self.assertEqual(expected, set(row["decisions"]))

    def test_03_strategies_never_receive_truth(self) -> None:
        scenario = self.fixture["scenarios"][0]
        snapshot = scenario["snapshots"][0]
        visible = visible_snapshot(self.fixture, snapshot)
        self.assertNotIn("truth", visible)
        first = {
            name: strategy(copy.deepcopy(visible))
            for name, strategy in STRATEGIES.items()
        }
        changed = copy.deepcopy(snapshot)
        changed["truth"] = {
            "operation_success": False,
            "safe_to_rely": False,
            "business_effect_accepted": False,
            "epistemic_truth": "UNKNOWN",
        }
        same_visible = visible_snapshot(self.fixture, changed)
        second = {
            name: strategy(copy.deepcopy(same_visible))
            for name, strategy in STRATEGIES.items()
        }
        self.assertEqual(first, second)

    def test_04_low_risk_steady_state_rewards_simple_declaration(self) -> None:
        scenario = self.result["per_scenario"]["steady-low-risk"]
        self.assertEqual(["DECLARATION"], scenario["winners"])
        for metrics in scenario["strategy_metrics"].values():
            self.assertEqual(0, metrics["false_reliance"])
            self.assertEqual(0, metrics["missed_opportunity"])

    def test_05_probe_success_then_revocation_is_discriminating(self) -> None:
        row = self._row(
            "probe-success-then-revocation-recovery",
            "holder-revoked-after-probe",
        )
        self.assertFalse(row["truth"]["safe_to_rely"])
        self.assertTrue(row["decisions"]["DECLARATION"]["rely"])
        self.assertTrue(row["decisions"]["LATEST_PROBE"]["rely"])
        self.assertFalse(row["decisions"]["RECEIPT_HISTORY"]["rely"])
        self.assertFalse(row["decisions"]["SLA_RECOVERY"]["rely"])

    def test_06_key_rotation_creates_different_recovery_delays(self) -> None:
        recovered = self._row(
            "probe-success-then-revocation-recovery",
            "re-authorized-with-key-rotation",
        )
        self.assertTrue(recovered["truth"]["safe_to_rely"])
        self.assertTrue(recovered["decisions"]["DECLARATION"]["rely"])
        self.assertFalse(recovered["decisions"]["LATEST_PROBE"]["rely"])
        self.assertFalse(recovered["decisions"]["RECEIPT_HISTORY"]["rely"])
        self.assertTrue(recovered["decisions"]["SLA_RECOVERY"]["rely"])
        self.assertEqual(
            1,
            self.result["per_strategy"]["LATEST_PROBE"]["recovery_time_steps"],
        )
        self.assertGreater(
            self.result["per_strategy"]["RECEIPT_HISTORY"]["recovery_time_steps"],
            1,
        )

    def test_07_environment_drift_and_recovery_are_not_one_state(self) -> None:
        drift = self._row(
            "environment-drift-and-adapter-recovery",
            "environment-version-drift",
        )
        recovered = self._row(
            "environment-drift-and-adapter-recovery",
            "adapter-validated-recovery",
        )
        self.assertFalse(drift["truth"]["safe_to_rely"])
        self.assertTrue(drift["decisions"]["DECLARATION"]["rely"])
        self.assertFalse(drift["decisions"]["SLA_RECOVERY"]["rely"])
        self.assertTrue(recovered["truth"]["safe_to_rely"])
        self.assertTrue(recovered["decisions"]["LATEST_PROBE"]["rely"])
        self.assertTrue(recovered["decisions"]["SLA_RECOVERY"]["rely"])

    def test_08_delayed_ack_is_operation_failure_not_missing_capability_label(self) -> None:
        row = self._row("delayed-ack", "ack-misses-operation-deadline")
        self.assertFalse(row["truth"]["operation_success"])
        self.assertTrue(row["decisions"]["DECLARATION"]["rely"])
        self.assertFalse(row["decisions"]["SLA_RECOVERY"]["rely"])

    def test_09_partial_failure_and_recovery_are_measured(self) -> None:
        partial = self._row(
            "partial-materialization-and-recovery",
            "single-side-partial-materialization",
        )
        recovered = self._row(
            "partial-materialization-and-recovery",
            "recovered-after-compensation",
        )
        self.assertFalse(partial["truth"]["operation_success"])
        self.assertTrue(partial["decisions"]["DECLARATION"]["rely"])
        self.assertFalse(partial["decisions"]["RECEIPT_HISTORY"]["rely"])
        self.assertTrue(recovered["truth"]["safe_to_rely"])
        self.assertTrue(recovered["decisions"]["SLA_RECOVERY"]["rely"])

    def test_10_false_reliance_and_missed_opportunity_are_both_counted(self) -> None:
        self.assertGreater(
            self.result["per_strategy"]["DECLARATION"]["false_reliance"],
            0,
        )
        self.assertGreater(
            self.result["per_strategy"]["LATEST_PROBE"]["missed_opportunity"],
            0,
        )
        self.assertGreater(
            self.result["per_strategy"]["RECEIPT_HISTORY"]["missed_opportunity"],
            0,
        )

    def test_11_metrics_include_cost_recovery_and_net_value(self) -> None:
        for metrics in self.result["per_strategy"].values():
            for field in (
                "false_reliance",
                "missed_opportunity",
                "recovery_time_steps",
                "disclosure_units",
                "coordination_operations",
                "evidence_cost",
                "net_task_value",
            ):
                self.assertIn(field, metrics)

    def test_12_unknown_refuse_and_absent_remain_distinct(self) -> None:
        for strategy_id, states in self.result["epistemic_states_preserved"].items():
            with self.subTest(strategy=strategy_id):
                self.assertEqual(["ABSENT", "REFUSE", "UNKNOWN"], states)

    def test_13_operation_success_does_not_imply_business_effect(self) -> None:
        row = self._row(
            "beneficiary-refusal",
            "operation-success-but-beneficiary-refuses",
        )
        self.assertTrue(row["truth"]["operation_success"])
        self.assertTrue(row["truth"]["safe_to_rely"])
        self.assertFalse(row["truth"]["business_effect_accepted"])
        self.assertGreater(
            self.result["per_strategy"]["DECLARATION"][
                "operation_success_without_business_effect"
            ],
            0,
        )

    def test_14_anchor_fork_defeats_pretty_operation_success(self) -> None:
        row = self._row(
            "anchor-fork",
            "physical-operation-but-untrusted-anchor",
        )
        self.assertTrue(row["truth"]["operation_success"])
        self.assertFalse(row["truth"]["safe_to_rely"])
        self.assertFalse(row["decisions"]["RECEIPT_HISTORY"]["rely"])
        self.assertFalse(row["decisions"]["SLA_RECOVERY"]["rely"])

    def test_15_exact_replay_and_changed_command_differ(self) -> None:
        exact = self._row("replay-and-command-change", "exact-replay")
        changed = self._row(
            "replay-and-command-change",
            "same-key-changed-command",
        )
        self.assertTrue(exact["truth"]["safe_to_rely"])
        self.assertFalse(changed["truth"]["safe_to_rely"])
        self.assertTrue(exact["decisions"]["SLA_RECOVERY"]["rely"])
        self.assertFalse(changed["decisions"]["SLA_RECOVERY"]["rely"])

    def test_16_schema_alias_and_material_change_differ(self) -> None:
        alias = self._row(
            "schema-alias-versus-material-change",
            "schema-compatible-alias",
        )
        changed = self._row(
            "schema-alias-versus-material-change",
            "material-semantic-change",
        )
        self.assertTrue(alias["truth"]["safe_to_rely"])
        self.assertFalse(changed["truth"]["safe_to_rely"])
        self.assertTrue(alias["decisions"]["SLA_RECOVERY"]["rely"])
        self.assertFalse(changed["decisions"]["SLA_RECOVERY"]["rely"])

    def test_17_scope_distinctions_are_reconstructable(self) -> None:
        self.assertEqual(
            {"operation_success", "capability", "reliance", "business_effect"},
            set(self.result["scope_distinctions"]),
        )
        self.assertFalse(
            self.result["claims"]["business_effect_inferred_from_operation_success"]
        )

    def test_18_generated_baseline_matches_evaluator(self) -> None:
        frozen = load_json(ROOT / "results" / "baseline.json")
        self.assertEqual(self.result, frozen)

    def test_19_manifest_hashes_match(self) -> None:
        manifest = load_json(ROOT / "manifest.json")
        for artifact in manifest["artifacts"]:
            path = ROOT / artifact["path"]
            self.assertEqual(
                artifact["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
                artifact["path"],
            )


if __name__ == "__main__":
    unittest.main()
