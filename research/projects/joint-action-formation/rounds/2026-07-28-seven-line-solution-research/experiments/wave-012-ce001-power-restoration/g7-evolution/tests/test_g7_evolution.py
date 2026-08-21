from __future__ import annotations

import inspect
import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g7evo.adapters import (  # noqa: E402
    CapsuleV1Exporter,
    CapsuleV2Importer,
    LeaseRegistryAdapter,
    SafetyPermitAdapter,
)
from g7evo.model import AppendOnlyHistory, causal_closure  # noqa: E402
from g7evo.audit import audit_results  # noqa: E402
from g7evo.runtime import (  # noqa: E402
    ContextCompiler,
    EvolutionModule,
    REQUIRED_CONTEXT_FIELDS,
)
import runner  # noqa: E402


class G7EvolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(
            (ROOT / "fixtures" / "ce001-g7.json").read_text(encoding="utf-8")
        )
        cls.module = EvolutionModule(cls.fixture)

    def test_identity_and_fixture_have_no_private_expected_label(self) -> None:
        self.assertEqual(self.module.identity, "G7_INTERNAL_AGENT_B")
        self.assertEqual(self.fixture["private_expected_label"], "ABSENT")
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "g7evo").glob("*.py")
        )
        self.assertNotIn("private_oracle", source)
        self.assertNotIn("expected_action", source)
        self.assertNotIn("choose(packet)", source)
        self.assertNotIn("_common_candidate", source)

    def test_two_owner_adapter_interfaces_are_distinct(self) -> None:
        self.assertNotEqual(
            inspect.signature(LeaseRegistryAdapter.fetch_lease),
            inspect.signature(SafetyPermitAdapter.verify),
        )
        self.assertNotEqual(
            inspect.signature(CapsuleV1Exporter.export),
            inspect.signature(CapsuleV2Importer.ingest),
        )

    def test_e4_revocation_cannot_continue_on_primary(self) -> None:
        result = self.module.run_e4()
        events = [record["event"] for record in result["history"]]
        self.assertIn("DEFEATER_APPENDED", events)
        self.assertIn("LOCAL_CAUSAL_REOPEN", events)
        self.assertEqual(result["final_action"], "CONTINUE_AFTER_LOCAL_REOPEN")
        commitment = next(
            record
            for record in result["history"]
            if record["event"] == "ALTERNATIVE_COMMITMENT_FORMED"
        )
        self.assertEqual(
            commitment["payload"]["owner_commitment"]["resource_id"],
            "battery-alternative",
        )
        self.assertEqual(
            commitment["payload"]["owner_commitment"]["decision"],
            "COMMITTED_EXACT_SCOPE",
        )

    def test_e4_recovers_to_exact_task_value(self) -> None:
        result = self.module.run_e4()
        self.assertTrue(result["ExactTaskSuccess"])
        self.assertTrue(result["CorrectResolution"])
        self.assertTrue(result["RecoveryToValue"])
        self.assertEqual(result["UnsafeEffect"], 0)
        self.assertEqual(result["DuplicateEffect"], 0)
        self.assertEqual(result["WrongObjectReliance"], 0)
        self.assertEqual(result["UnreconciledEffect"], 0)
        self.assertEqual(
            set(result["acceptance"]["owner_receipts"]),
            {"O_Q", "O_V"},
        )
        self.assertEqual(
            set(result["settlement"]["acceptance_evidence_hashes"]),
            {
                receipt["evidence_hash"]
                for receipt in result["acceptance"]["owner_receipts"].values()
            },
        )

    def test_e4_active_lease_with_wrong_exact_scope_is_rejected(self) -> None:
        mutated = deepcopy(self.fixture)
        scope = mutated["e4"]["lease_registry"]["lease-alternative"][
            "leaseRecord"
        ]["scope"]
        scope["objectRef"] = "Circuit-C8"
        result = EvolutionModule(mutated).run_e4()
        self.assertEqual(result["final_action"], "BLOCK")
        self.assertFalse(result["RecoveryToValue"])
        blocked = result["history"][-1]["payload"]["owner_commitment"]
        self.assertEqual(blocked["decision"], "REFUSED_SCOPE_MISMATCH")

    def test_local_reopen_is_exact_causal_closure(self) -> None:
        result = self.module.run_e4()
        graph = self.fixture["e4"]["public_packet"]["dependency_graph"]
        expected = causal_closure(["resource-primary"], graph["edges"])
        self.assertEqual(result["local_reopen"]["closure"], expected)
        self.assertNotIn("resource-alternative", expected)
        self.assertNotIn("safety-root", expected)

    def test_global_reopen_reaches_all_nodes_from_shared_root(self) -> None:
        result = self.module.run_e4()
        graph = self.fixture["e4"]["public_packet"]["dependency_graph"]
        self.assertEqual(
            result["global_reopen_intervention"]["closure"],
            sorted(graph["nodes"]),
        )

    def test_cold_repeat_context_is_minimal_and_repeat_is_cheaper(self) -> None:
        context = self.module.run_e4()["context"]
        cold = context["cold"]
        repeat = context["repeat"]
        self.assertEqual(set(cold["context"]), REQUIRED_CONTEXT_FIELDS)
        self.assertEqual(set(repeat["context"]), REQUIRED_CONTEXT_FIELDS)
        self.assertEqual(cold["decision"], "CONTINUE")
        self.assertEqual(repeat["decision"], "CONTINUE")
        self.assertLess(
            repeat["cost"]["owner_queries"],
            cold["cost"]["owner_queries"],
        )

    def test_each_context_field_is_required(self) -> None:
        context = self.module.run_e4()["context"]["cold"]["context"]
        for field in REQUIRED_CONTEXT_FIELDS:
            mutated = dict(context)
            mutated.pop(field)
            self.assertIn(
                f"missing:{field}",
                ContextCompiler.validate(mutated),
            )

    def test_e6_crash_takeover_reconciles_without_duplicate_effect(self) -> None:
        result = self.module.run_e6()
        self.assertTrue(result["migration_import"]["imported"])
        self.assertTrue(result["replay_suppressed"])
        self.assertEqual(result["effect_count"], 1)
        self.assertEqual(result["DuplicateEffect"], 0)
        self.assertEqual(result["UnreconciledEffect"], 0)
        self.assertTrue(result["reconciliation"]["complete"])
        self.assertEqual(result["reconciliation"]["after"], [])
        self.assertEqual(result["acceptance"]["decision"], "ACCEPTED")
        self.assertEqual(result["settlement"]["status"], "SETTLED")
        self.assertEqual(
            set(result["acceptance"]["owner_receipts"]),
            {"O_Q", "O_V"},
        )
        self.assertTrue(result["RecoveryToValue"])

    def test_e6_old_runtime_restart_is_fenced(self) -> None:
        result = self.module.run_e6()
        restart = result["old_runtime_restart"]
        self.assertEqual(restart["outcome"], "FENCED_OR_DENIED")
        self.assertFalse(restart["committed"])
        self.assertEqual(result["effect_count"], 1)

    def test_e6_history_is_append_only_across_runtime(self) -> None:
        result = self.module.run_e6()
        self.assertTrue(result["history_prefix_preserved"])
        prefix = result["source_history"]
        self.assertEqual(result["history"][: len(prefix)], prefix)
        imported = AppendOnlyHistory.import_verified(
            "audit",
            result["history"],
            result["history"][-1]["record_hash"],
        )
        self.assertEqual(imported.root, result["history"][-1]["record_hash"])

    def test_capsule_field_loss_fails_closed_even_when_rehashed(self) -> None:
        result = self.module.run_capsule_field_loss()
        self.assertFalse(result["migration_import"]["imported"])
        self.assertTrue(result["migration_import"]["valid_hash"])
        self.assertIn(
            "recovery.pending_acceptance",
            result["migration_import"]["missing_fields"],
        )
        self.assertEqual(result["final_action"], "BOUNDED_UNKNOWN")
        self.assertFalse(result["dispatch_after_import"])
        self.assertEqual(result["effect_count"], 1)

    def test_saved_raw_trace_matches_live_public_boundary_if_present(self) -> None:
        trace = ROOT / "raw" / "run-traces.json"
        if not trace.exists():
            self.skipTest("raw trace not generated yet")
        saved = json.loads(trace.read_text(encoding="utf-8"))
        live = runner.run()
        self.assertEqual(saved["schema"], live["schema"])
        self.assertEqual(saved["evidence_level"], live["evidence_level"])
        self.assertEqual(
            saved["evidence"]["evidence_boundaries"],
            live["evidence"]["evidence_boundaries"],
        )
        self.assertEqual(
            saved["evidence"]["migration"]["old_runtime_restart"]["fence_result"],
            live["evidence"]["migration"]["old_runtime_restart"]["fence_result"],
        )

    def test_audit_rejects_old_runtime_split_brain_mutant(self) -> None:
        results = self.module.run_regressions()
        results["cases"]["E6"]["old_runtime_restart"]["outcome"] = "COMMITTED"
        self.assertIn(
            "E6 old runtime restart was not fenced",
            audit_results(results),
        )

    def test_audit_rejects_safe_stop_without_e4_recovery_to_value(self) -> None:
        results = self.module.run_regressions()
        results["cases"]["E4"]["RecoveryToValue"] = False
        self.assertIn(
            "E4 did not recover to exact task value",
            audit_results(results),
        )


if __name__ == "__main__":
    unittest.main()
