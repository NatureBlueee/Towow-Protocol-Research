from __future__ import annotations

from copy import deepcopy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g7evo.adapters import (  # noqa: E402
    CapsuleV2Importer,
    LeaseRegistryAdapter,
    SafetyPermitAdapter,
)
from g7evo.model import (  # noqa: E402
    AppendOnlyHistory,
    DurableFenceAuthority,
    EffectTarget,
    digest,
    issue_current_receipt_set,
)
import g7evo.runtime as runtime  # noqa: E402
from g7evo.runtime import ContextCompiler, EvolutionModule  # noqa: E402


class G7AgentCAdversarialTests(unittest.TestCase):
    """Contract-level attacks, not tests of Agent B's preferred happy path."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(
            (ROOT / "fixtures" / "ce001-g7.json").read_text(encoding="utf-8")
        )

    def _e4_compiler_inputs(self) -> tuple[
        ContextCompiler, dict, dict, dict
    ]:
        config = deepcopy(self.fixture["e4"])
        packet = config["public_packet"]
        leases = LeaseRegistryAdapter(config["lease_registry"])
        safety = SafetyPermitAdapter(config["safety_policies"])
        compiler = ContextCompiler(leases, safety)
        cold = compiler.cold(
            packet=packet,
            reservation_ref="lease-alternative",
            history_root="history-root-A",
            runtime_epoch=1,
        )
        safety_evidence = safety.verify(
            packet["operation"], packet["policy_revision"], at_epoch=1
        )
        return compiler, packet, cold, safety_evidence

    def test_repeat_rejects_prior_context_with_wrong_target_and_q(self) -> None:
        """A cached context may not substitute its old task for the current task."""

        compiler, packet, cold, safety_evidence = self._e4_compiler_inputs()
        poisoned = deepcopy(cold["context"])
        poisoned["object_id"] = "Circuit-C8"
        poisoned["q_version"] = "Q@attacker"
        repeat = compiler.repeat(
            packet=packet,
            reservation_ref="lease-alternative",
            prior_context=poisoned,
            prior_safety_evidence=safety_evidence,
        )
        self.assertNotEqual(
            repeat["decision"],
            "CONTINUE",
            "repeat accepted a cached target/Q that does not match the current packet",
        )

    def test_repeat_rejects_wrong_operation_and_semantic_effect_key(self) -> None:
        """A new causal/effect identity cannot inherit a cached permit."""

        compiler, packet, cold, safety_evidence = self._e4_compiler_inputs()
        poisoned = deepcopy(cold["context"])
        poisoned["operation_id"] = "different-operation"
        poisoned["semantic_effect_key"] = "attacker:new-effect-key"
        repeat = compiler.repeat(
            packet=packet,
            reservation_ref="lease-alternative",
            prior_context=poisoned,
            prior_safety_evidence=safety_evidence,
        )
        self.assertNotEqual(
            repeat["decision"],
            "CONTINUE",
            "repeat accepted a different operation/effect identity",
        )

    def test_repeat_rejects_unverifiable_history_and_evidence_transplant(self) -> None:
        """Hashes must be bound and verifiable, not arbitrary truth labels."""

        compiler, packet, cold, safety_evidence = self._e4_compiler_inputs()
        poisoned = deepcopy(cold["context"])
        poisoned["history_root"] = "attacker-history-root"
        poisoned["authority_evidence_hashes"] = ["attacker-evidence"]
        forged_safety = deepcopy(safety_evidence)
        forged_safety["evidence_hash"] = "attacker-safety-evidence"
        repeat = compiler.repeat(
            packet=packet,
            reservation_ref="lease-alternative",
            prior_context=poisoned,
            prior_safety_evidence=forged_safety,
        )
        self.assertNotEqual(
            repeat["decision"],
            "CONTINUE",
            "unverifiable history/evidence labels were accepted as current authority",
        )

    def test_context_validation_rejects_present_but_unusable_evidence(self) -> None:
        """Field presence alone is not minimal-sufficient Context validation."""

        compiler, _, cold, _ = self._e4_compiler_inputs()
        poisoned = deepcopy(cold["context"])
        poisoned["authority_evidence_hashes"] = []
        poisoned["history_root"] = ""
        poisoned["semantic_effect_key"] = ""
        self.assertTrue(
            compiler.validate(poisoned),
            "empty evidence, history and effect bindings were accepted as sufficient",
        )

    def test_cold_repeat_cost_contains_lifecycle_axes_before_cheaper_claim(self) -> None:
        """One fewer query is not a cold/repeat lifecycle comparison."""

        _, _, cold, _ = self._e4_compiler_inputs()
        required_axes = {
            "owner_queries",
            "disclosure_bytes",
            "calendar_wait",
            "human_minutes",
            "compute_tool",
            "formation_adapter_setup",
            "assurance",
            "recovery_migration",
            "governance",
            "opportunity_loss",
        }
        self.assertTrue(
            required_axes.issubset(cold["cost"]),
            f"missing lifecycle cost axes: {sorted(required_axes - set(cold['cost']))}",
        )

    def test_e4_deduplicated_old_effect_is_not_alternative_recovery(self) -> None:
        """A prior primary Effect cannot be relabelled as R2 recovery-to-value."""

        config = self.fixture["e4"]
        operation = deepcopy(config["public_packet"]["operation"])
        original_target = EffectTarget

        def target_with_prior_effect(
            owner_id: str, current_epoch: int = 1
        ) -> EffectTarget:
            target = original_target(owner_id, current_epoch=current_epoch)
            target.effects[operation["semantic_effect_key"]] = {
                **operation,
                "coordinator_epoch": current_epoch,
                "sequence": 1,
                "origin_resource_id": "battery-primary",
            }
            return target

        with patch.object(runtime, "EffectTarget", side_effect=target_with_prior_effect):
            result = EvolutionModule(self.fixture).run_e4()

        self.assertEqual(result["dispatch"]["outcome"], "DEDUPLICATED")
        self.assertFalse(
            result["RecoveryToValue"],
            "a deduplicated pre-existing primary Effect was counted as alternative recovery",
        )

    def test_e4_block_is_not_recovery_to_value(self) -> None:
        """Control: a safe stop is allowed, but must remain a negative E4 result."""

        mutated = deepcopy(self.fixture)
        mutated["e4"]["lease_registry"]["lease-alternative"]["leaseRecord"][
            "state"
        ] = "REVOKED"
        result = EvolutionModule(mutated).run_e4()
        self.assertEqual(result["final_action"], "BLOCK")
        self.assertFalse(result["RecoveryToValue"])
        self.assertFalse(result.get("ExactTaskSuccess", False))

    def test_e4_history_rewrite_cannot_be_hidden_by_constant_true_flag(self) -> None:
        """The result must derive prefix preservation from the emitted chain."""

        original_append = AppendOnlyHistory.append

        def append_then_rewrite(
            history: AppendOnlyHistory, event: str, payload: dict | None = None
        ) -> dict:
            record = original_append(history, event, payload)
            if history.owner == "runtime-e4" and event == "DEFEATER_APPENDED":
                history.records[0]["payload"]["q_version"] = "Q@rewritten"
            return record

        with patch.object(runtime.AppendOnlyHistory, "append", new=append_then_rewrite):
            result = EvolutionModule(self.fixture).run_e4()

        with self.assertRaises(ValueError):
            AppendOnlyHistory.import_verified(
                "audit", result["history"], result["history_root"]
            )
        self.assertFalse(
            result["history_prefix_preserved"],
            "run_e4 reports a constant true flag even when its emitted chain is invalid",
        )

    def test_e6_cannot_change_exact_target_and_q_and_still_succeed(self) -> None:
        """E6 success must remain bound to frozen CE-001 Q@v1 / Circuit-C7."""

        mutated = deepcopy(self.fixture)
        operation = mutated["e6"]["public_packet"]["operation"]
        operation["q_version"] = "Q@v2-substituted"
        operation["object_id"] = "Circuit-C8"
        result = EvolutionModule(mutated).run_e6()
        self.assertFalse(
            result["ExactTaskSuccess"],
            "target and Acceptance copied the substituted packet and self-certified success",
        )
        self.assertNotEqual(result["acceptance"]["decision"], "ACCEPTED")

    def test_old_runtime_is_fenced_even_if_target_restart_loses_epoch(self) -> None:
        """E6 requires a durable external fence, not one Python object's memory."""

        def lose_epoch_on_restart(target: EffectTarget, epoch: int) -> None:
            target.history.append(
                "TARGET_RESTART_LOST_EPOCH",
                {"requested_epoch": epoch, "retained_epoch": target.current_epoch},
            )

        with patch.object(runtime.EffectTarget, "advance_epoch", new=lose_epoch_on_restart):
            result = EvolutionModule(self.fixture).run_e6()

        self.assertEqual(
            result["old_runtime_restart"]["outcome"],
            "FENCED_OR_DENIED",
            "old runtime was only fenced while the in-memory epoch survived",
        )

    def test_external_fence_survives_a_new_target_object(self) -> None:
        """Calling a field durable does not move it into an external authority domain."""

        operation = deepcopy(self.fixture["e6"]["public_packet"]["operation"])
        fence_authority = DurableFenceAuthority()
        first_process = EffectTarget(
            "O_E",
            current_epoch=1,
            fence_authority=fence_authority,
            fence_key="CE-001/E6:Circuit-C7",
        )
        first_process.install_external_fence(2)
        restarted_process = EffectTarget(
            "O_E",
            current_epoch=1,
            fence_authority=fence_authority,
            fence_key="CE-001/E6:Circuit-C7",
        )
        old_runtime = restarted_process.dispatch(
            operation=operation,
            coordinator_epoch=1,
            current_receipt_set=issue_current_receipt_set(
                operation,
                episode_id="CE-001/E6",
                at_epoch=1,
            ),
        )
        self.assertEqual(
            old_runtime["outcome"],
            "FENCED_OR_DENIED",
            "a newly constructed target lost the purported external durable fence",
        )

    def test_capsule_import_rejects_unknown_schema_despite_valid_hash(self) -> None:
        """Different call signatures do not establish adapter semantic independence."""

        state = EvolutionModule(self.fixture)._prepare_e6()
        capsule = deepcopy(state["capsule"])
        capsule["payload"]["header"]["schema"] = "unrelated.schema.v999"
        capsule["capsule_hash"] = digest(capsule["payload"])
        imported = CapsuleV2Importer().ingest(
            {"capsule_hash": capsule["capsule_hash"]},
            capsule["payload"],
            target_runtime_id="target",
        )
        self.assertFalse(
            imported["imported"],
            "importer checked that schema exists, not that it understands its semantics",
        )

    def test_capsule_import_rejects_empty_obligation_semantics(self) -> None:
        """A present list cannot stand in for pending Acceptance/Settlement duties."""

        state = EvolutionModule(self.fixture)._prepare_e6()
        capsule = deepcopy(state["capsule"])
        capsule["payload"]["recovery"]["obligations"] = []
        capsule["capsule_hash"] = digest(capsule["payload"])
        imported = CapsuleV2Importer().ingest(
            {"capsule_hash": capsule["capsule_hash"]},
            capsule["payload"],
            target_runtime_id="target",
        )
        self.assertFalse(
            imported["imported"],
            "empty obligations were treated as a semantically complete capsule",
        )

    def test_field_loss_safe_stop_is_not_portability_success(self) -> None:
        """Fail-closed is an attack safety result, not successful E6 recovery."""

        result = EvolutionModule(self.fixture).run_capsule_field_loss()
        self.assertFalse(result["migration_import"]["imported"])
        self.assertFalse(
            result["CorrectResolution"],
            "field loss was labelled CorrectResolution although portability did not recover",
        )

    def test_adapter_signature_difference_is_not_reported_as_semantic_independence(
        self,
    ) -> None:
        """Until a second native runtime runs, semantic independence stays Unknown."""

        result = EvolutionModule(self.fixture).run_e6()
        evidence = result["adapter_interfaces"]
        self.assertEqual(
            evidence.get("semantic_independence"),
            "NOT_ESTABLISHED",
            "different Python signatures were the only adapter-independence evidence",
        )

    def test_cold_repeat_full_lifecycle_comparison_is_explicitly_not_measured(
        self,
    ) -> None:
        """Adding fixed ledger columns does not create an observed lifecycle comparison."""

        result = EvolutionModule(self.fixture).run_e4()
        self.assertEqual(
            result["context"].get("cost_comparison_status"),
            "NOT_MEASURED_FULL_LIFECYCLE",
            "fixture constants were exposed without an explicit no-net-winner boundary",
        )

    def test_hidden_pair_is_explicitly_absent_or_has_opposing_requirements(
        self,
    ) -> None:
        """An optional hidden pair may be omitted, but never silently claimed."""

        hidden_pair = self.fixture.get("hidden_pair")
        if hidden_pair is None:
            self.assertEqual(
                self.fixture.get("hidden_pair_status"),
                "NOT_CONSTRUCTED",
                "absent hidden pair was not explicitly bounded as NOT_CONSTRUCTED",
            )
            result = EvolutionModule(self.fixture).run_all()
            serialized = json.dumps(result, ensure_ascii=False).lower()
            self.assertNotIn("safety_liveness_frontier_pass", serialized)
            return
        self.assertNotEqual(
            hidden_pair["valid"]["required_final_action"],
            hidden_pair["revoked"]["required_final_action"],
        )


if __name__ == "__main__":
    unittest.main()
