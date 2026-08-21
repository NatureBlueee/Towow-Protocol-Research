from __future__ import annotations

import importlib.util
import math
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "power_audit.py"
MODULE_SPEC = importlib.util.spec_from_file_location("wave025_power_audit", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
power = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(power)


class PowerAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = power.audit()

    def test_CP_upper_direction_and_closed_form_edges(self) -> None:
        n = 20
        alpha = 0.025
        expected_k0 = 1.0 - alpha ** (1.0 / n)
        self.assertAlmostEqual(power.clopper_pearson_upper_float(0, n, alpha), expected_k0, places=14)
        self.assertEqual(power.clopper_pearson_upper_float(n, n, alpha), 1.0)
        values = [power.clopper_pearson_upper_float(k, n, alpha) for k in range(n + 1)]
        self.assertTrue(all(left < right for left, right in zip(values, values[1:])))
        # Smaller tail alpha means a higher-confidence and therefore larger upper endpoint.
        self.assertGreater(
            power.clopper_pearson_upper_float(10, n, 0.025),
            power.clopper_pearson_upper_float(10, n, 0.05),
        )

    def test_float_CP_matches_80_digit_decimal_and_root_residual(self) -> None:
        checks = self.audit["decimal_cross_checks"]
        for n in (400, 800, 1200):
            item = checks[str(n)]
            self.assertLess(item["absolute_difference"], 1e-13)
            self.assertLess(item["float_cdf_residual"], 1e-12)

    def test_note_central_CP_values(self) -> None:
        expected = {
            "400": 0.5500921123,
            "800": 0.5352179696,
            "1200": 0.5286767909,
        }
        for n, target in expected.items():
            self.assertAlmostEqual(self.audit["single_attack"][n]["central_cp_upper"], target, places=10)

    def test_optimized_two_binomial_enumeration_matches_literal_small_n(self) -> None:
        n = 12
        upper = power.cp_upper_table(n)
        literal = power.literal_double_binomial_probability(
            n, upper, power.AVERAGE_UPPER_THRESHOLD
        )
        optimized = power.double_binomial_pass_probability(n)["pass_probability_fraction"]
        self.assertEqual(optimized, literal)

    def test_single_attack_pass_probabilities_match_V3_note(self) -> None:
        expected = {
            "400": 0.488072095,
            "800": 0.880009801,
            "1200": 0.9822552469,
        }
        for n, target in expected.items():
            self.assertAlmostEqual(self.audit["single_attack"][n]["pass_probability"], target, places=9)

    def test_pass_lattice_is_numerically_separated_from_threshold(self) -> None:
        for n in ("400", "800", "1200"):
            item = self.audit["single_attack"][n]
            self.assertGreater(item["pass_boundary_margin"], 1e-8)
            self.assertGreater(item["fail_boundary_margin"], 1e-8)
            error = self.audit["decimal_cross_checks"][n]["absolute_difference"]
            self.assertGreater(item["pass_boundary_margin"], 1_000_000 * error)
            self.assertGreater(item["fail_boundary_margin"], 1_000_000 * error)

    def test_five_attack_union_bound_matches_and_does_not_assume_attack_independence(self) -> None:
        union = self.audit["n1200_union_bounds"]
        self.assertAlmostEqual(union["five_attacks"], 0.9112762343, places=10)
        self.assertFalse(union["attack_independence_required"])
        self.assertTrue(union["within_attack_episode_and_class_count_model_required"])

    def test_six_gated_attacks_are_not_covered_by_the_five_attack_power_claim(self) -> None:
        union = self.audit["n1200_union_bounds"]
        self.assertAlmostEqual(union["six_attacks"], 0.8935314811, places=10)
        self.assertLess(union["six_attacks"], 0.90)

    def test_block_balance_matches_n_per_class_and_3200_total(self) -> None:
        blocks = self.audit["block_balance"]
        self.assertEqual(blocks["block_size"], 20)
        self.assertEqual(blocks["per_role_per_block"], 10)
        self.assertEqual(blocks["total_slots"], 3200)
        self.assertEqual(blocks["total_blocks"], 160)
        self.assertEqual(blocks["T_holdout_n_per_class"], 1200)
        t_holdout = blocks["strata"]["T-OCI-ISOLATED"]["holdout"]
        self.assertEqual(t_holdout, {"slots": 2400, "blocks": 120, "per_role": 1200})

    def test_input_guards_reject_invalid_CP_parameters(self) -> None:
        for args in ((-1, 10, 0.025), (11, 10, 0.025), (5, 10, 0.0), (5, 10, 1.0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                power.clopper_pearson_upper_float(*args)
        with self.assertRaises(ValueError):
            power.binomial_cdf_float(5, 10, math.nan)


if __name__ == "__main__":
    unittest.main()
