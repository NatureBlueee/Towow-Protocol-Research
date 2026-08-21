from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcb_g5.common import load_json, sha256
from mcb_g5.native_adapter import derive_business_outcome
from mcb_g5.simulation import (
    OwnerCluster,
    audit_adversarial_corpus,
    run_fence_matrix,
    run_materiality_standing_migration,
    run_native_conformance,
    run_owner_independence,
)


class DiscriminatorTests(unittest.TestCase):
    def test_native_worker_never_receives_business_oracle(self) -> None:
        inputs = load_json(ROOT / "fixtures" / "native-inputs.json")
        raw = str(inputs)
        self.assertNotIn("business_outcome", raw)
        result = run_native_conformance(ROOT)
        self.assertTrue(result["all_native_exact"])
        self.assertTrue(result["all_business_exact"])
        self.assertTrue(result["provider_adapter_corpus"]["all_business_exact"])
        self.assertEqual(len(result["provider_adapter_corpus"]["rows"]), 13)
        self.assertEqual(result["engine_runs"]["OPA"], "NOT_RUN_ENGINE_NOT_INSTALLED")

    def test_stale_permit_is_not_allow(self) -> None:
        native = {
            "native_outcome": "PERMIT",
            "source_freshness": "STALE",
            "input_complete": True,
            "negative_authority_fact": False,
            "resolver": "owner",
        }
        mapped = derive_business_outcome(native)
        self.assertEqual(mapped["business_outcome"], "DEFER")
        self.assertEqual(mapped["native_record"]["native_outcome"], "PERMIT")

    def test_four_owner_process_store_key_and_faults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cluster = OwnerCluster(ROOT, Path(tmp))
            try:
                result = run_owner_independence(cluster)
            finally:
                cluster.close()
        self.assertTrue(result["distinct_processes"])
        self.assertTrue(result["distinct_stores"])
        self.assertTrue(result["distinct_public_keys"])
        self.assertTrue(
            all(
                item["other_owner_state_unchanged"]
                for item in result["fault_observations"].values()
            )
        )
        self.assertEqual(
            result["fault_observations"]["program-coordinator"]["owner_read_after"][
                "envelope"
            ]["payload"]["body"]["stance"],
            "REJECT",
        )
        self.assertEqual(
            result["fault_observations"]["delta-calibration"]["owner_read_after"][
                "envelope"
            ]["payload"]["body"]["mandate"],
            "REVOKED",
        )
        self.assertEqual(
            result["fault_observations"]["independent-validation"][
                "owner_read_after"
            ]["status"],
            "OUTAGE",
        )
        self.assertTrue(
            result["fault_observations"]["site-data-steward"]["owner_read_after"][
                "envelope"
            ]["payload"]["body"]["fork_views"]
        )

    def test_target_fence_matrix_exposes_enforcement_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_fence_matrix(ROOT, Path(tmp), sha256({"operation": 1}))
        self.assertTrue(result["all_failure_modes_exposed"])
        rows = {row["mode"]: row for row in result["rows"]}
        self.assertFalse(rows["strict"]["stale_effect_by_authoritative_epoch"])
        self.assertTrue(rows["ignore"]["stale_effect_by_authoritative_epoch"])
        self.assertTrue(rows["restart_loss"]["stale_effect_by_authoritative_epoch"])
        self.assertTrue(
            rows["cross_region_reorder"]["stale_effect_by_authoritative_epoch"]
        )

    def test_materiality_standing_and_migration_boundaries(self) -> None:
        result = run_materiality_standing_migration(ROOT)
        self.assertTrue(result["material_operation_closure"]["all_exact"])
        self.assertTrue(result["standing_lifecycle"]["all_exact"])
        migrations = {
            row["mapping"]: row for row in result["migration"]["rows"]
        }
        self.assertEqual(
            migrations["FAITHFUL"]["declaration"],
            "WITNESSED_EQUIVALENT_ON_THIS_CORPUS",
        )
        self.assertEqual(
            migrations["LOSSY"]["declaration"], "SEMANTIC_LOSS_DETECTED"
        )
        self.assertEqual(migrations["FAITHFUL"]["outside_corpus"], "UNKNOWN")

    def test_adversarial_corpus_has_all_required_families_and_boundaries(self) -> None:
        result = audit_adversarial_corpus(ROOT)
        self.assertEqual(result["case_count"], 34)
        self.assertTrue(result["unique_ids"])
        self.assertTrue(result["families_complete"])
        self.assertTrue(result["race_boundaries_complete"])


if __name__ == "__main__":
    unittest.main()
