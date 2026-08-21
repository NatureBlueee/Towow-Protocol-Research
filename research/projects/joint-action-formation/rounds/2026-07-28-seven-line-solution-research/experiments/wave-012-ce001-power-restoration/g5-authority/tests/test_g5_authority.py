from __future__ import annotations

import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ce001_g5.harness import run_experiment
from ce001_g5.model import (
    AUTHORITY_STRATA,
    REVOKE_BOUNDARIES,
    build_operation,
    material_operation_closure,
)


class G5AuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.results, cls.trace = run_experiment(
            ROOT, Path(cls.temp.name) / "current"
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_u_d_p_and_four_revoke_boundaries_ran(self) -> None:
        observed = {
            (row["stratum"], row["revoke_after"])
            for row in self.results["race_matrix"]
        }
        self.assertEqual(
            observed,
            {
                (stratum, boundary)
                for stratum in AUTHORITY_STRATA
                for boundary in REVOKE_BOUNDARIES
            },
        )
        self.assertTrue(
            all(row["native_resolution"] for row in self.results["race_matrix"])
        )

    def test_topology_is_derived_from_three_distinct_trusted_closures(self) -> None:
        topologies = self.results["topology_closures"]
        self.assertEqual(
            {item["closure_kind"] for item in topologies.values()},
            {
                "UNIFIED_PRINCIPAL_ACT",
                "EXACT_DELEGATED_ACT",
                "DIRECT_OWNER_ACT",
            },
        )
        self.assertEqual(
            len(
                {
                    item["topology_closure_sha256"]
                    for item in topologies.values()
                }
            ),
            3,
        )
        self.assertEqual(topologies["U"]["required_owners"], ["O_UNIFIED"])
        self.assertEqual(topologies["D"]["delegatee"], "C_COORDINATOR")
        self.assertIsNone(topologies["P"]["delegatee"])

    def test_u_still_uses_owner_channel_and_target_processes(self) -> None:
        rows = [
            row for row in self.results["race_matrix"] if row["stratum"] == "U"
        ]
        self.assertTrue(all(row["owner_service_pids"] for row in rows))
        self.assertTrue(all(row["authority_channel_pid"] for row in rows))
        services = {
            entry["service_id"]
            for entry in self.trace
            if entry["cell_id"].startswith("RACE-U")
        }
        self.assertIn("O_UNIFIED", services)
        self.assertIn("AUTHORITY_CHANNEL", services)
        self.assertTrue(any(item.startswith("O_E_TARGET") for item in services))

    def test_target_native_gate_rejects_required_attack_set(self) -> None:
        attacks = {
            row["attack"]: row
            for row in self.results["target_native_gate_attacks"]["rows"]
        }
        self.assertEqual(
            set(attacks),
            {
                "NO_OWNER_RECEIPTS",
                "NAKED_FENCE_INJECTION",
                "POST_CHECK_REVOKE",
                "WRONG_OWNER",
                "STALE_HEAD",
                "CHANGED_Q",
                "CHANGED_OBJECT_ID",
                "CHANGED_OBJECT_REVISION",
                "CHANGED_SCOPE",
                "CHANGED_EXPIRY",
                "RUNTIME_EXPIRED",
                "RELABELED_TOPOLOGY",
                "FORGED_RECEIPT",
                "ACTIVE_SNAPSHOT_COMPENSATION",
            },
        )
        self.assertTrue(
            all(
                row["target_native_outcome"] != "ENERGIZED"
                and row["transition_count"] == 0
                for row in attacks.values()
            )
        )
        self.assertEqual(
            attacks["NO_OWNER_RECEIPTS"]["target_native_outcome"],
            "TARGET_REJECTED_REQUIRED_OWNER_SET",
        )
        self.assertEqual(
            attacks["NAKED_FENCE_INJECTION"]["target_native_outcome"],
            "TARGET_REJECTED_NAKED_FENCE_INJECTION",
        )
        self.assertEqual(
            attacks["POST_CHECK_REVOKE"]["target_native_outcome"],
            "TARGET_REJECTED_OWNER_NOT_CURRENT",
        )
        self.assertEqual(
            attacks["STALE_HEAD"]["target_native_outcome"],
            "TARGET_REJECTED_STALE_OWNER_HEAD",
        )
        self.assertEqual(
            attacks["FORGED_RECEIPT"]["target_native_outcome"],
            "TARGET_REJECTED_FORGED_RECEIPT",
        )

    def test_q_object_revision_scope_and_expiry_are_independent_material_bindings(
        self,
    ) -> None:
        base = build_operation("P")
        variants = []
        for field, value in (
            ("q_version", "Q@v2"),
            ("object_id", "Venue-V/Circuit-C8"),
            ("object_revision", "C7@rev6"),
            ("expiry", base["expiry"] + 1),
        ):
            changed = deepcopy(base)
            changed[field] = value
            variants.append(changed)
        changed_scope = deepcopy(base)
        changed_scope["scope"]["power_kw"] = 4.0
        variants.append(changed_scope)
        self.assertTrue(
            all(
                material_operation_closure(item)
                != material_operation_closure(base)
                for item in variants
            )
        )

    def test_resource_fence_is_not_an_owner_head_namespace(self) -> None:
        strict = self.results["target_fence_failure_injections"]["rows"][0]
        self.assertEqual(
            strict["target_native_outcome"],
            "TARGET_REJECTED_STALE_RESOURCE_FENCE_RECEIPT",
        )
        owner_snapshots = [
            entry["response"]["native"]
            for entry in self.trace
            if entry["response"].get("native", {}).get("schema")
            == "ce001.g5.authority-channel-snapshot.v1"
        ]
        self.assertTrue(owner_snapshots)
        self.assertTrue(
            all(
                "owner_heads" in snapshot and "resource_fence" in snapshot
                for snapshot in owner_snapshots
            )
        )

    def test_failure_profiles_expose_ignored_or_lost_fence(self) -> None:
        rows = {
            row["mode"]: row
            for row in self.results["target_fence_failure_injections"]["rows"]
        }
        self.assertFalse(rows["strict"]["stale_effect_observed"])
        self.assertTrue(rows["ignore_fence"]["stale_effect_observed"])
        self.assertTrue(rows["restart_loses_fence"]["stale_effect_observed"])

    def test_saga_requires_signed_authority_loss_and_target_readback(self) -> None:
        execute_rows = [
            row
            for row in self.results["race_matrix"]
            if row["revoke_after"] == "execute"
        ]
        for row in execute_rows:
            self.assertEqual(row["target_execute_outcome"], "ENERGIZED")
            self.assertEqual(row["compensation_target_outcome"], "DEENERGIZED")
            state = row["target_final_readback"]["native"]["target_state"]
            self.assertEqual(state["power_state"], "OFF")
            self.assertEqual(
                [transition["action"] for transition in state["transitions"]],
                ["ENERGIZE", "DEENERGIZE"],
            )
        active_attack = next(
            row
            for row in self.results["target_native_gate_attacks"]["rows"]
            if row["attack"] == "ACTIVE_SNAPSHOT_COMPENSATION"
        )
        self.assertEqual(
            active_attack["target_native_outcome"],
            "TARGET_REJECTED_COMPENSATION_WITHOUT_AUTHORITY_LOSS",
        )

    def test_standing_unknown_fails_closed(self) -> None:
        attack = self.results["standing_attack"]
        self.assertTrue(attack["standing_fail_closed"])
        self.assertEqual(attack["transition_count"], 0)

    def test_migration_is_two_processes_over_one_shared_store_only(self) -> None:
        migration = self.results["migration"]
        self.assertTrue(migration["distinct_runtime_processes"])
        self.assertNotEqual(
            migration["source_runtime_pid"], migration["target_runtime_pid"]
        )
        self.assertEqual(
            len(
                {
                    migration["source_runtime_pid"],
                    migration["target_runtime_pid"],
                    migration["old_source_restarted_pid"],
                }
            ),
            3,
        )
        self.assertEqual(
            migration["old_runtime_replay_response_pid"],
            migration["old_source_restarted_pid"],
        )
        self.assertEqual(
            migration["old_runtime_replay_runtime_id"],
            "SOURCE-RUNTIME-RESTARTED@epoch1",
        )
        self.assertEqual(
            migration["durable_store_scope"],
            "SHARED_DURABLE_STORE_PROCESS_RESTART",
        )
        self.assertEqual(migration["cross_failure_domain"], "NOT_RUN")
        self.assertEqual(
            migration["restore_native_outcome"],
            "MIGRATION_PROCESS_RESTART_RESTORED",
        )
        self.assertEqual(
            migration["old_runtime_replay_outcome"],
            "STALE_COORDINATOR_EPOCH_REJECTED",
        )
        self.assertEqual(migration["new_runtime_replay_outcome"], "IDEMPOTENT_REPLAY")
        self.assertFalse(migration["duplicate_effect"])

    def test_old_and_forged_migration_state_fail_target_native(self) -> None:
        migration = self.results["migration"]
        self.assertNotEqual(
            migration["old_migration_state_reuse_outcome"],
            "MIGRATION_PROCESS_RESTART_RESTORED",
        )
        self.assertTrue(
            all(
                item["native_outcome"]
                == "TARGET_REJECTED_FORGED_TAKEOVER_LEASE"
                for item in migration["forgery_validations"].values()
            )
        )
        self.assertEqual(
            migration["controller_high_epoch_lease_request_outcome"],
            "TAKEOVER_EPOCH_NOT_NEXT",
        )
        self.assertEqual(
            migration["forged_high_epoch_lease_outcome"],
            "TARGET_REJECTED_FORGED_TAKEOVER_LEASE",
        )
        self.assertEqual(
            migration["unsigned_lease_outcome"],
            "TARGET_REJECTED_FORGED_TAKEOVER_LEASE",
        )
        self.assertEqual(
            migration["unissued_high_execute_outcome"],
            "UNISSUED_COORDINATOR_EPOCH_REJECTED",
        )

    def test_only_public_key_evidence_is_returned(self) -> None:
        self.assertTrue(self.results["public_keys"])
        self.assertFalse(
            any(
                "private" in key.lower()
                for record in self.results["public_keys"].values()
                for key in record
            )
        )

    def test_unrun_products_and_cross_domain_remain_not_run(self) -> None:
        status = self.results["engine_status"]
        for name in (
            "OPA",
            "Cedar",
            "OpenFGA",
            "XACML",
            "CROSS_FAILURE_DOMAIN_MIGRATION",
        ):
            self.assertEqual(status[name], "NOT_RUN")


if __name__ == "__main__":
    unittest.main()
