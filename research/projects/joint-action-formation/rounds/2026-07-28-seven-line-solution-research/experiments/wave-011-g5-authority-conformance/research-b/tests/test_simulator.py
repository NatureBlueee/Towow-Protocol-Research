from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT))

from authority_sim import (  # noqa: E402
    OWNER_NAMES,
    RacePlan,
    SimulationConfig,
    SimulationHarness,
    run_fence_probe,
)


def run_sim(config: SimulationConfig) -> dict:
    with tempfile.TemporaryDirectory(prefix="g5-test-") as temp:
        return SimulationHarness(config, Path(temp)).run()


class IndependentOwnerTests(unittest.TestCase):
    def test_four_processes_stores_and_public_keys_are_distinct(self) -> None:
        with tempfile.TemporaryDirectory(prefix="g5-owner-test-") as temp:
            runtime = Path(temp)
            report = SimulationHarness(
                SimulationConfig(strategy="no_common_transaction"),
                runtime,
            ).run()
            owners = report["owner_processes"]
            self.assertEqual(set(owners), set(OWNER_NAMES))
            self.assertEqual(len({owner["pid"] for owner in owners.values()}), 4)
            self.assertEqual(
                len(
                    {
                        owner["public_modulus_fingerprint"]
                        for owner in owners.values()
                    }
                ),
                4,
            )
            self.assertEqual(len({owner["store"] for owner in owners.values()}), 4)
            self.assertEqual(
                len({owner["private_key"] for owner in owners.values()}), 4
            )
            for owner in owners.values():
                self.assertTrue(Path(owner["store"]).exists())
                self.assertTrue(Path(owner["private_key"]).exists())
                self.assertTrue(Path(owner["public_key"]).exists())
            self.assertEqual(report["metrics"]["signature_failures"], 0)

    def test_outage_remains_native_error_not_prefilled_business_label(self) -> None:
        report = run_sim(
            SimulationConfig(
                strategy="no_common_transaction",
                race=RacePlan(
                    boundary="read:request_owner",
                    owner="budget_owner",
                    action="outage",
                ),
            )
        )
        self.assertEqual(report["method_status"], "UNKNOWN_NATIVE_STATE")
        native_errors = [
            event["detail"]["native"].get("native_error")
            for event in report["trace"]
            if event["event"] == "owner_native_response"
        ]
        self.assertIn("SERVICE_UNAVAILABLE", native_errors)

    def test_each_owner_failure_mode_is_injectable_and_signed(self) -> None:
        for action in ("reject", "revoke", "outage", "fork"):
            with self.subTest(action=action):
                report = run_sim(
                    SimulationConfig(
                        strategy="no_common_transaction",
                        race=RacePlan(
                            boundary="read:request_owner",
                            owner="budget_owner",
                            action=action,
                        ),
                    )
                )
                self.assertEqual(report["metrics"]["race_injections"], 1)
                self.assertEqual(report["metrics"]["signature_failures"], 0)
                self.assertNotEqual(report["method_status"], "EFFECT_ATTEMPTED")


class CoordinationStrategyTests(unittest.TestCase):
    def test_serial_reread_is_not_claimed_as_cross_authority_atomic(self) -> None:
        report = run_sim(
            SimulationConfig(
                strategy="no_common_transaction",
                race=RacePlan(
                    boundary="reserve:resource_owner",
                    owner="budget_owner",
                    action="revoke",
                ),
            )
        )
        self.assertIn("NOT_CROSS_AUTHORITY_ATOMIC", report["atomicity_claim"])
        self.assertEqual(report["metrics"]["unsafe_effects"], 1)
        self.assertEqual(report["metrics"]["residual_unsafe_effects"], 1)

    def test_bounded_owner_lease_defers_mid_commit_revocation(self) -> None:
        report = run_sim(
            SimulationConfig(
                strategy="bounded_lease_confirm",
                race=RacePlan(
                    boundary="reserve:resource_owner",
                    owner="budget_owner",
                    action="revoke",
                ),
            )
        )
        self.assertEqual(report["metrics"]["race_deferred"], 1)
        self.assertEqual(report["metrics"]["unsafe_effects"], 0)
        self.assertEqual(report["metrics"]["effect_accepted"], 1)
        self.assertIn("NOT_SIMULTANEOUS_SNAPSHOT", report["atomicity_claim"])

    def test_two_phase_hold_is_safe_for_race_but_blocks_on_crash(self) -> None:
        safe = run_sim(
            SimulationConfig(
                strategy="two_phase_hold",
                race=RacePlan(
                    boundary="reserve:resource_owner",
                    owner="supplier_owner",
                    action="revoke",
                ),
            )
        )
        self.assertEqual(safe["metrics"]["race_deferred"], 1)
        self.assertEqual(safe["metrics"]["unsafe_effects"], 0)
        crashed = run_sim(
            SimulationConfig(
                strategy="two_phase_hold",
                crash_after_prepare=True,
            )
        )
        self.assertEqual(
            crashed["method_status"], "COORDINATOR_CRASH_BLOCKING_HOLDS"
        )
        self.assertEqual(crashed["metrics"]["blocked_owner_holds"], 4)
        self.assertEqual(crashed["metrics"]["effect_attempted"], 0)

    def test_saga_compensates_but_does_not_become_atomic(self) -> None:
        report = run_sim(
            SimulationConfig(
                strategy="saga_compensation",
                race=RacePlan(
                    boundary="reserve:resource_owner",
                    owner="budget_owner",
                    action="revoke",
                ),
            )
        )
        self.assertEqual(report["metrics"]["unsafe_effects"], 1)
        self.assertEqual(report["metrics"]["compensations"], 1)
        self.assertEqual(report["metrics"]["residual_unsafe_effects"], 0)
        self.assertIn("COMPENSATION_NOT_ATOMIC", report["atomicity_claim"])

    def test_unified_center_requires_real_unified_authority_topology(self) -> None:
        invalid = run_sim(
            SimulationConfig(
                strategy="unified_center",
                authority_topology="independent",
            )
        )
        self.assertEqual(
            invalid["method_status"],
            "NOT_APPLICABLE_EXTERNAL_NON_DELEGABLE_RIGHT",
        )
        self.assertEqual(invalid["metrics"]["effect_attempted"], 0)
        valid = run_sim(
            SimulationConfig(
                strategy="unified_center",
                authority_topology="unified",
                race=RacePlan(
                    boundary="reserve:resource_owner",
                    owner="budget_owner",
                    action="revoke",
                ),
            )
        )
        self.assertEqual(valid["method_status"], "UNIFIED_SINGLE_DOMAIN_COMMIT")
        self.assertEqual(valid["metrics"]["effect_accepted"], 1)
        self.assertEqual(valid["metrics"]["race_deferred"], 1)

    def test_every_declared_boundary_can_trigger_a_fresh_race(self) -> None:
        fixture = json.loads(
            (ROOT / "fixtures" / "race_matrix.json").read_text(encoding="utf-8")
        )
        for boundary in fixture["inject_after"]:
            with self.subTest(boundary=boundary):
                report = run_sim(
                    SimulationConfig(
                        strategy="no_common_transaction",
                        race=RacePlan(
                            boundary=boundary,
                            owner="budget_owner",
                            action="revoke",
                        ),
                    )
                )
                self.assertEqual(report["metrics"]["race_injections"], 1)


class FenceTests(unittest.TestCase):
    def test_only_durable_global_enforcement_rejects_older_epoch(self) -> None:
        enforce = run_fence_probe("enforce")
        self.assertFalse(enforce["older_after_newer"]["accepted"])
        self.assertFalse(enforce["stale_effect_observed"])
        for mode in ("ignore", "restart_loss", "cross_region_reorder"):
            with self.subTest(mode=mode):
                report = run_fence_probe(mode)
                self.assertTrue(report["older_after_newer"]["accepted"])
                self.assertTrue(report["stale_effect_observed"])


if __name__ == "__main__":
    unittest.main()
