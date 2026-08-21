from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyzer import load_json, main_analysis, resolve_and_verify, score  # noqa: E402


class CostSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_json(ROOT / "config.json")
        cls.result = main_analysis(cls.config)
        cls.frozen = load_json(ROOT / "results" / "sensitivity.json")

    def test_01_frozen_shared_task_and_abc_hashes_match(self) -> None:
        resolved = resolve_and_verify(self.config)
        self.assertEqual(
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3",
            resolved["shared_task"]["sha256"],
        )
        self.assertEqual(
            "2f8c2315dacfee16c414b8310cad2a18146f5c334c2b41a42a746a64fc8a214f",
            resolved["wave_006_a"]["sha256"],
        )
        self.assertEqual(
            "2bac5fe9dbda16cc82cb7117ef6d1c68b385b97d52ebfd776801295e03ad1862",
            resolved["wave_006_b"]["sha256"],
        )
        self.assertEqual(
            "c5176fdfcee3015429a8aec1645d3f0114b96cab0a67293e73b9aae7ae1dd4a0",
            resolved["wave_006_c"]["sha256"],
        )

    def test_02_scan_has_7200_explicit_weight_points(self) -> None:
        self.assertEqual(
            7200,
            self.result["g2_relation_representation"]["sensitivity"][
                "grid_point_count"
            ],
        )
        self.assertEqual(
            7200,
            self.result["g4_capability_reliance"]["sensitivity"][
                "grid_point_count"
            ],
        )

    def test_03_baseline_scores_reproduce_g4_baseline(self) -> None:
        scores = self.result["g4_capability_reliance"]["sensitivity"][
            "baseline"
        ]["scores"]
        self.assertEqual(
            {
                "DECLARATION": 78.9,
                "LATEST_PROBE": 109.7,
                "RECEIPT_HISTORY": 34.5,
                "SLA_RECOVERY": 159.7,
            },
            scores,
        )

    def test_04_g2_a_is_always_in_winner_set(self) -> None:
        sensitivity = self.result["g2_relation_representation"]["sensitivity"]
        self.assertEqual(
            sensitivity["grid_point_count"],
            sensitivity["winner_counts_including_ties"][
                "A_DELIVERY_RECEIPT_ONLY"
            ],
        )
        self.assertEqual(
            5760,
            sensitivity["unique_winner_counts"]["A_DELIVERY_RECEIPT_ONLY"],
        )

    def test_05_g2_complex_strategies_never_uniquely_win(self) -> None:
        unique = self.result["g2_relation_representation"]["sensitivity"][
            "unique_winner_counts"
        ]
        self.assertEqual(0, unique["B_DUAL_RECIPIENT_ACK"])
        self.assertEqual(0, unique["C_ACK_EXPLAINBACK_RELATION_PROPOSAL"])

    def test_06_g2_sampled_dominance_is_explicit(self) -> None:
        dominance = self.result["g2_relation_representation"]["sensitivity"][
            "sampled_weak_dominance"
        ]
        self.assertEqual(
            [
                "B_DUAL_RECIPIENT_ACK",
                "C_ACK_EXPLAINBACK_RELATION_PROPOSAL",
            ],
            dominance["A_DELIVERY_RECEIPT_ONLY"],
        )
        self.assertEqual(
            ["C_ACK_EXPLAINBACK_RELATION_PROPOSAL"],
            dominance["B_DUAL_RECIPIENT_ACK"],
        )

    def test_07_g2_zero_coordination_creates_ties_not_complex_gain(self) -> None:
        sensitivity = self.result["g2_relation_representation"]["sensitivity"]
        self.assertEqual(1440, sensitivity["tie_count"])
        self.assertEqual(
            "ROBUST_WITH_NONNEGATIVE_COSTS_BUT_TIES_AT_ZERO_COORDINATION",
            self.result["g2_relation_representation"]["claim_stability"],
        )

    def test_08_g4_baseline_winner_is_not_globally_stable(self) -> None:
        g4 = self.result["g4_capability_reliance"]
        self.assertEqual(
            "CONDITION_DEPENDENT_BASELINE_WINNER_NOT_GLOBALLY_STABLE",
            g4["claim_stability"],
        )
        unique = g4["sensitivity"]["unique_winner_counts"]
        self.assertLess(unique["SLA_RECOVERY"], 7200)
        self.assertGreater(unique["DECLARATION"], 0)
        self.assertGreater(unique["LATEST_PROBE"], 0)

    def test_09_g4_unique_winner_regions_are_frozen(self) -> None:
        unique = self.result["g4_capability_reliance"]["sensitivity"][
            "unique_winner_counts"
        ]
        self.assertEqual(
            {
                "DECLARATION": 2421,
                "LATEST_PROBE": 170,
                "RECEIPT_HISTORY": 0,
                "SLA_RECOVERY": 4547,
            },
            unique,
        )

    def test_10_receipt_history_has_no_winner_region_in_range(self) -> None:
        sensitivity = self.result["g4_capability_reliance"]["sensitivity"]
        self.assertEqual(
            0,
            sensitivity["winner_counts_including_ties"]["RECEIPT_HISTORY"],
        )
        dominance = sensitivity["sampled_strict_dominance"]
        self.assertIn("RECEIPT_HISTORY", dominance["LATEST_PROBE"])
        self.assertIn("RECEIPT_HISTORY", dominance["SLA_RECOVERY"])

    def test_11_no_conclusion_regions_are_reported(self) -> None:
        g2 = self.result["g2_relation_representation"]["sensitivity"]
        g4 = self.result["g4_capability_reliance"]["sensitivity"]
        self.assertGreater(g2["tie_count"], 0)
        self.assertEqual(62, g4["tie_count"])
        self.assertEqual(75, g4["near_tie_or_no_conclusion_count"])

    def test_12_sla_declaration_threshold_matches_direct_scores(self) -> None:
        metrics = self.result["g4_capability_reliance"]["source_metrics"]
        weights = dict(self.config["baseline_weights"])
        weights["failure_loss"] = 6.457143
        sla = score(metrics["SLA_RECOVERY"], weights, 20.0)
        declaration = score(metrics["DECLARATION"], weights, 20.0)
        self.assertAlmostEqual(sla, declaration, places=5)

    def test_13_declaration_probe_threshold_matches_direct_scores(self) -> None:
        metrics = self.result["g4_capability_reliance"]["source_metrics"]
        weights = dict(self.config["baseline_weights"])
        weights["failure_loss"] = 12.866667
        declaration = score(metrics["DECLARATION"], weights, 20.0)
        probe = score(metrics["LATEST_PROBE"], weights, 20.0)
        self.assertAlmostEqual(declaration, probe, places=5)

    def test_14_failure_loss_flip_changes_sla_vs_declaration(self) -> None:
        metrics = self.result["g4_capability_reliance"]["source_metrics"]
        low = dict(self.config["baseline_weights"], failure_loss=5.0)
        high = dict(self.config["baseline_weights"], failure_loss=10.0)
        self.assertGreater(
            score(metrics["DECLARATION"], low, 20.0),
            score(metrics["SLA_RECOVERY"], low, 20.0),
        )
        self.assertGreater(
            score(metrics["SLA_RECOVERY"], high, 20.0),
            score(metrics["DECLARATION"], high, 20.0),
        )

    def test_15_generated_result_is_deterministic(self) -> None:
        self.assertEqual(self.result, self.frozen)

    def test_16_wave006c_is_bound_but_not_rescored(self) -> None:
        self.assertTrue(
            self.result["scope"]["wave_006_c_used_as_bound_denominator_not_rescored"]
        )
        result_text = json.dumps(self.result, sort_keys=True)
        self.assertNotIn("effect_ladder", result_text)

    def test_17_simple_solution_winning_is_positive(self) -> None:
        self.assertTrue(
            self.result["scope"]["simple_solution_winning_is_positive_result"]
        )
        self.assertEqual(
            "A_DELIVERY_RECEIPT_ONLY",
            self.result["g2_relation_representation"]["baseline_claim"],
        )

    def test_18_manifest_hashes_match(self) -> None:
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
