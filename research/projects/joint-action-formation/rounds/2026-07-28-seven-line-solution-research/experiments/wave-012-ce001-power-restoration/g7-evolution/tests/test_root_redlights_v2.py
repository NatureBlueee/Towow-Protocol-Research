from __future__ import annotations

import base64
from copy import deepcopy
from hashlib import sha256
import importlib.util
import inspect
import json
from pathlib import Path
import sys
import unittest
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_ROOT = ROOT.parent / "integration-preflight"
sys.path.insert(0, str(ROOT))

from g7evo.model import EffectTarget, SettlementOwner, digest  # noqa: E402
from g7evo.runtime import EvolutionModule  # noqa: E402


def _load_preflight_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "ce001_integration_preflight",
        PREFLIGHT_ROOT / "preflight.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("integration preflight module is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PREFLIGHT = _load_preflight_module()


class G7RootRedlightsV2(unittest.TestCase):
    """Second-round root red lights frozen before the B-v2 implementation.

    These checks intentionally distinguish identifiers from actual process,
    durable-state, transmitted-byte, owner-act, and target-consumption
    boundaries.  A missing evidence surface is RED, not a skipped test.
    """

    FORBIDDEN_CONCLUSION_KEYS = {
        "exacttasksuccess",
        "tasksuccess",
        "correctresolution",
        "resolutioncorrect",
        "achievablesuccesscoverage",
        "allcaseresolutioncoverage",
        "recoverytovalue",
        "restoredtaskvalue",
        "unsafeeffect",
        "duplicateeffect",
        "wrongobjectreliance",
        "unreconciledeffect",
        "candidateexclusivesuccess",
        "authority",
        "legalauthority",
        "effect",
        "worldeffect",
        "acceptance",
        "owneracceptance",
        "settlement",
        "paymentsettlement",
        "contractscore",
        "contractsuccess",
        "completesolution",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(
            (ROOT / "fixtures" / "ce001-g7.json").read_text(encoding="utf-8")
        )
        cls.results = EvolutionModule(cls.fixture).run_all()

    def _mapping(self, value: Any, label: str) -> Mapping[str, Any]:
        self.assertIsInstance(value, Mapping, f"{label} evidence is missing")
        return value if isinstance(value, Mapping) else {}

    def _root_evidence(self) -> Mapping[str, Any]:
        return self._mapping(
            self.results.get("evidence"),
            "top-level line-local",
        )

    def _migration(self) -> Mapping[str, Any]:
        return self._mapping(
            self._root_evidence().get("migration"),
            "E6 migration",
        )

    @staticmethod
    def _normalized_key(key: Any) -> str:
        return "".join(character for character in str(key).lower() if character.isalnum())

    @classmethod
    def _walk_keys(cls, value: Any) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []

        def visit(node: Any, path: str) -> None:
            if isinstance(node, Mapping):
                for key, child in node.items():
                    child_path = f"{path}.{key}"
                    found.append((child_path, cls._normalized_key(key)))
                    visit(child, child_path)
            elif isinstance(node, list):
                for index, child in enumerate(node):
                    visit(child, f"{path}[{index}]")

        visit(value, "$")
        return found

    def _assert_bytes_hash(
        self,
        evidence: Any,
        *,
        label: str,
        bytes_field: str = "bytes_b64",
        hash_field: str = "bytes_hash",
    ) -> bytes:
        item = self._mapping(evidence, label)
        encoded = item.get(bytes_field)
        claimed_hash = item.get(hash_field)
        self.assertIsInstance(encoded, str, f"{label} must expose actual bytes")
        self.assertTrue(encoded, f"{label} bytes must be non-empty")
        try:
            raw = base64.b64decode(encoded or "", validate=True)
        except (ValueError, TypeError) as exc:
            self.fail(f"{label} bytes are not valid base64: {exc}")
        self.assertTrue(raw, f"{label} decoded bytes must be non-empty")
        expected = sha256(raw).hexdigest()
        self.assertIn(
            claimed_hash,
            {expected, f"sha256:{expected}"},
            f"{label} hash was not computed from the exposed bytes",
        )
        return raw

    def _assert_state_file_hash(self, runtime: Any, label: str) -> Path:
        item = self._mapping(runtime, label)
        raw_path = item.get("state_path")
        self.assertIsInstance(raw_path, str, f"{label} state_path is missing")
        path = Path(raw_path or "")
        self.assertTrue(path.is_absolute(), f"{label} state_path must be absolute")
        self.assertTrue(path.is_file(), f"{label} durable state file does not exist")
        raw = path.read_bytes()
        expected = sha256(raw).hexdigest()
        self.assertIn(
            item.get("state_bytes_hash"),
            {expected, f"sha256:{expected}"},
            f"{label} state hash is not derived from the persisted bytes",
        )
        return path

    def test_dispatch_has_no_controller_authority_boolean(self) -> None:
        """A controller boolean may not be the target's commit-time authority."""

        signature = inspect.signature(EffectTarget.dispatch)
        self.assertNotIn(
            "authority_allowed",
            signature.parameters,
            "target dispatch still accepts controller-injected authority_allowed",
        )
        receipt_parameters = {
            "authority_receipts",
            "authority_receipt_set",
            "current_receipt_set",
        }
        self.assertTrue(
            receipt_parameters.intersection(signature.parameters),
            "target dispatch exposes no current Authority receipt-set input",
        )

    def test_target_consumption_is_from_exact_transmitted_receipt_set(self) -> None:
        """The target must emit a native event for the exact received bytes."""

        evidence = self._root_evidence()
        consumption = self._mapping(
            evidence.get("target_receipt_consumption"),
            "target-native receipt consumption",
        )
        transmitted = consumption.get("transmitted_receipt_hashes")
        consumed = consumption.get("consumed_receipt_hashes")
        self.assertIsInstance(transmitted, list)
        self.assertTrue(transmitted)
        self.assertEqual(set(consumed or []), set(transmitted or []))
        self.assertEqual(len(consumed or []), len(set(consumed or [])))
        event_bytes = self._assert_bytes_hash(
            consumption,
            label="target-native receipt-consumption event",
            bytes_field="event_bytes_b64",
            hash_field="consumption_event_hash",
        )
        event = json.loads(event_bytes.decode("utf-8"))
        self.assertEqual(
            set(event.get("consumed_receipt_hashes", [])),
            set(transmitted or []),
        )
        self.assertEqual(event.get("consumer"), "TARGET_NATIVE")

    def test_wrong_stale_and_tampered_authority_receipts_fail_closed(self) -> None:
        """A logged/current label is insufficient without receipt verification."""

        attacks = self._mapping(
            self._root_evidence().get("receipt_consumption_attacks"),
            "Authority receipt attack matrix",
        )
        for attack_id in (
            "wrong_receipt",
            "stale_receipt",
            "tampered_receipt",
            "receipt_set_transplant",
        ):
            with self.subTest(attack=attack_id):
                outcome = self._mapping(attacks.get(attack_id), attack_id)
                self.assertFalse(
                    outcome.get("committed"),
                    f"{attack_id} reached target commit",
                )
                self.assertIn(
                    outcome.get("outcome"),
                    {
                        "DENIED",
                        "FENCED_OR_DENIED",
                        "REJECTED_RECEIPT_SET",
                        "FAIL_CLOSED",
                    },
                )
                self._assert_bytes_hash(
                    outcome,
                    label=f"{attack_id} target rejection event",
                    bytes_field="event_bytes_b64",
                    hash_field="event_hash",
                )

    def test_oq_ov_op_have_distinct_real_process_state_and_act_sources(self) -> None:
        """Three labels in one object graph are not three owner sources."""

        owners = self._mapping(
            self._root_evidence().get("owner_sources"),
            "owner source",
        )
        required = {"O_Q", "O_V", "O_P"}
        self.assertEqual(set(owners), required)
        process_ids: list[int] = []
        state_ids: list[str] = []
        act_ids: list[str] = []
        state_paths: list[Path] = []
        for owner_id in sorted(required):
            source = self._mapping(owners.get(owner_id), owner_id)
            self.assertIsInstance(source.get("process_id"), int)
            self.assertGreater(source.get("process_id", 0), 0)
            process_ids.append(source["process_id"])
            self.assertIsInstance(source.get("state_source_id"), str)
            self.assertTrue(source.get("state_source_id"))
            self.assertIsInstance(source.get("act_source_id"), str)
            self.assertTrue(source.get("act_source_id"))
            state_ids.append(source["state_source_id"])
            act_ids.append(source["act_source_id"])
            state_paths.append(self._assert_state_file_hash(source, owner_id))
            self._assert_bytes_hash(
                source,
                label=f"{owner_id} transmitted request",
                bytes_field="request_bytes_b64",
                hash_field="request_bytes_hash",
            )
            self._assert_bytes_hash(
                source,
                label=f"{owner_id} transmitted response",
                bytes_field="response_bytes_b64",
                hash_field="response_bytes_hash",
            )
        self.assertEqual(len(process_ids), len(set(process_ids)))
        self.assertEqual(len(state_ids), len(set(state_ids)))
        self.assertEqual(len(act_ids), len(set(act_ids)))
        self.assertEqual(len(state_paths), len(set(state_paths)))

    def test_duplicate_owner_and_response_transplant_do_not_create_finality(self) -> None:
        """Re-signing an O_Q response as O_V may not fool O_P."""

        legacy_e6 = EvolutionModule(self.fixture).run_e6()
        receipts = self._mapping(
            legacy_e6.get("owner_receipts")
            or legacy_e6.get("acceptance", {}).get("owner_receipts"),
            "owner response receipts",
        )
        oq = deepcopy(receipts.get("O_Q"))
        self.assertIsInstance(oq, dict, "O_Q response receipt is missing")
        duplicate = SettlementOwner().settle([oq, deepcopy(oq)])
        self.assertNotEqual(duplicate.get("status"), "SETTLED")

        transplanted = deepcopy(oq)
        transplanted["owner_id"] = "O_V"
        transplanted["evidence_hash"] = digest(
            {key: value for key, value in transplanted.items() if key != "evidence_hash"}
        )
        forged = SettlementOwner().settle([oq, transplanted])
        self.assertNotEqual(
            forged.get("status"),
            "SETTLED",
            "O_P accepted an O_Q response transplanted into the O_V label",
        )

    def test_owner_binding_attacks_reject_wrong_episode_q_effect_and_stale_response(
        self,
    ) -> None:
        """Owner responses must bind the request bytes, not copied result fields."""

        attacks = self._mapping(
            self._root_evidence().get("owner_binding_attacks"),
            "owner binding attack matrix",
        )
        for attack_id in (
            "duplicate_owner",
            "response_transplant",
            "stale_response",
            "wrong_episode",
            "wrong_q",
            "wrong_effect_occurrence",
        ):
            with self.subTest(attack=attack_id):
                outcome = self._mapping(attacks.get(attack_id), attack_id)
                self.assertFalse(outcome.get("accepted"))
                self.assertFalse(outcome.get("finalized"))
                self._assert_bytes_hash(
                    outcome,
                    label=f"{attack_id} rejection response",
                    bytes_field="response_bytes_b64",
                    hash_field="response_bytes_hash",
                )

    def test_op_response_follows_exact_oq_ov_response_hashes(self) -> None:
        """O_P must independently act after the exact transmitted owner responses."""

        owners = self._mapping(
            self._root_evidence().get("owner_sources"),
            "owner source",
        )
        oq = self._mapping(owners.get("O_Q"), "O_Q")
        ov = self._mapping(owners.get("O_V"), "O_V")
        op = self._mapping(owners.get("O_P"), "O_P")
        self.assertEqual(
            set(op.get("after_owner_response_hashes", [])),
            {oq.get("response_bytes_hash"), ov.get("response_bytes_hash")},
        )
        self.assertNotEqual(op.get("act_source_id"), oq.get("act_source_id"))
        self.assertNotEqual(op.get("act_source_id"), ov.get("act_source_id"))
        self.assertFalse(op.get("derived_from_owner_response_object", True))

    def test_e6_has_distinct_runtime_process_and_durable_state_boundaries(self) -> None:
        """Different runtime_id strings are not a process/state migration."""

        migration = self._migration()
        source = self._mapping(migration.get("source_runtime"), "source runtime")
        target = self._mapping(migration.get("target_runtime"), "target runtime")
        for field in ("runtime_id", "process_id", "state_boundary_id", "epoch"):
            self.assertIsNotNone(source.get(field), f"source {field} is missing")
            self.assertIsNotNone(target.get(field), f"target {field} is missing")
        self.assertNotEqual(source.get("runtime_id"), target.get("runtime_id"))
        self.assertNotEqual(source.get("process_id"), target.get("process_id"))
        self.assertNotEqual(
            source.get("state_boundary_id"),
            target.get("state_boundary_id"),
        )
        self.assertGreater(target.get("epoch", 0), source.get("epoch", 0))
        source_path = self._assert_state_file_hash(source, "source runtime")
        target_path = self._assert_state_file_hash(target, "target runtime")
        self.assertNotEqual(source_path, target_path)

    def test_source_was_terminated_target_started_and_old_runtime_restarted(self) -> None:
        """A newly allocated Python object is not an observed old-process restart."""

        migration = self._migration()
        source = self._mapping(migration.get("source_runtime"), "source runtime")
        target = self._mapping(migration.get("target_runtime"), "target runtime")
        restart = self._mapping(
            migration.get("old_runtime_restart"),
            "old runtime restart",
        )
        self.assertTrue(source.get("termination_observed"))
        self.assertIsInstance(source.get("exit_code"), int)
        self.assertTrue(target.get("start_observed"))
        self.assertTrue(restart.get("actually_restarted"))
        self.assertTrue(restart.get("restart_observed"))
        self.assertIsInstance(restart.get("process_id"), int)
        self.assertNotEqual(restart.get("process_id"), source.get("process_id"))
        self.assertNotEqual(restart.get("process_id"), target.get("process_id"))
        self.assertEqual(restart.get("presented_epoch"), source.get("epoch"))
        self.assertEqual(restart.get("current_epoch"), target.get("epoch"))
        self.assertEqual(restart.get("fence_result"), "REJECTED_OLD_EPOCH")

    def test_fence_is_owned_by_external_process_and_persisted_bytes(self) -> None:
        """The epoch must survive replacement of both coordinator processes."""

        migration = self._migration()
        source = self._mapping(migration.get("source_runtime"), "source runtime")
        target = self._mapping(migration.get("target_runtime"), "target runtime")
        fence = self._mapping(migration.get("fence_owner"), "external fence owner")
        self.assertIsInstance(fence.get("process_id"), int)
        self.assertNotIn(
            fence.get("process_id"),
            {source.get("process_id"), target.get("process_id")},
        )
        self._assert_state_file_hash(fence, "external fence owner")
        self.assertEqual(fence.get("installed_epoch"), target.get("epoch"))
        rejection = self._mapping(
            fence.get("old_epoch_rejection"),
            "old-epoch fence rejection",
        )
        self.assertEqual(rejection.get("presented_epoch"), source.get("epoch"))
        self.assertEqual(rejection.get("required_epoch"), target.get("epoch"))
        self._assert_bytes_hash(
            rejection,
            label="old-epoch fence rejection",
            bytes_field="event_bytes_b64",
            hash_field="event_hash",
        )

    def test_capsule_hash_is_from_actual_transmitted_bytes_not_fixture_label(self) -> None:
        """A digest of an in-memory fixture object is not wire provenance."""

        provenance = self._mapping(
            self._root_evidence().get("byte_provenance"),
            "byte provenance",
        )
        capsule = self._mapping(provenance.get("capsule"), "capsule provenance")
        self.assertEqual(capsule.get("source_kind"), "TRANSMITTED_BYTES")
        self._assert_bytes_hash(capsule, label="transmitted capsule")
        self.assertTrue(capsule.get("sender_process_id"))
        self.assertTrue(capsule.get("receiver_process_id"))
        self.assertNotEqual(
            capsule.get("sender_process_id"),
            capsule.get("receiver_process_id"),
        )

    def test_state_history_owner_and_occurrence_hashes_recompute_from_bytes(self) -> None:
        """Every lineage hash must have a byte preimage in the actual run."""

        provenance = self._mapping(
            self._root_evidence().get("byte_provenance"),
            "byte provenance",
        )
        for item_id in (
            "source_state",
            "target_state",
            "history_prefix",
            "owner_evidence",
            "effect_occurrence",
        ):
            with self.subTest(item=item_id):
                item = self._mapping(provenance.get(item_id), item_id)
                self.assertNotEqual(item.get("source_kind"), "FIXTURE_CONSTANT")
                self._assert_bytes_hash(item, label=item_id)

    def test_history_rewrite_attack_is_rejected_from_persisted_prefix_bytes(self) -> None:
        """The check must compare source and imported bytes, not a true flag."""

        attack = self._mapping(
            self._root_evidence().get("history_rewrite_attack"),
            "history rewrite attack",
        )
        original = self._assert_bytes_hash(
            attack,
            label="original history prefix",
            bytes_field="original_bytes_b64",
            hash_field="original_bytes_hash",
        )
        persisted = self._assert_bytes_hash(
            attack,
            label="persisted history prefix",
            bytes_field="persisted_bytes_b64",
            hash_field="persisted_bytes_hash",
        )
        candidate = self._assert_bytes_hash(
            attack,
            label="rewritten history candidate",
            bytes_field="candidate_bytes_b64",
            hash_field="candidate_bytes_hash",
        )
        self.assertEqual(original, persisted)
        self.assertNotEqual(candidate, original)
        self.assertTrue(attack.get("rewrite_rejected"))
        self.assertFalse(attack.get("history_fork_detected"))

    def test_g7_results_do_not_emit_contract_conclusions(self) -> None:
        """G7 may emit lineage/reopen/migration evidence, not a score."""

        violations = [
            path
            for path, normalized in self._walk_keys(self.results)
            if normalized in self.FORBIDDEN_CONCLUSION_KEYS
        ]
        self.assertEqual(
            violations,
            [],
            f"G7 still emits contract-level or synonymous conclusions: {violations}",
        )

    def test_g7_namespaced_envelope_has_no_contract_passthrough(self) -> None:
        envelope = self._mapping(
            self.results.get("integration_envelope"),
            "G7 integration envelope",
        )
        self.assertEqual(envelope.get("namespace"), "G7")
        self.assertEqual(
            envelope.get("qualification"),
            "QUALIFIED_COMPONENT_OUTPUT",
        )
        violations = [
            path
            for path, normalized in self._walk_keys(envelope)
            if normalized in self.FORBIDDEN_CONCLUSION_KEYS
        ]
        self.assertEqual(
            violations,
            [],
            f"integration envelope passes through contract conclusions: {violations}",
        )

    def test_g7_envelope_enters_current_integration_preflight(self) -> None:
        """Actual byte-derived G7 refs, not preflight fixture constants, must qualify."""

        g7 = self._mapping(
            self.results.get("integration_envelope"),
            "G7 integration envelope",
        )
        migration = self._mapping(
            g7.get("evidence", {}).get("migration"),
            "G7 integration migration",
        )
        lineage = self._mapping(
            migration.get("lineage_verification"),
            "G7 integration lineage",
        )
        recovery = self._mapping(
            migration.get("recovery"),
            "G7 integration owner recovery",
        )
        root_evidence = self._root_evidence()
        provenance = self._mapping(
            root_evidence.get("byte_provenance"),
            "byte provenance",
        )
        occurrence = self._mapping(
            provenance.get("effect_occurrence"),
            "occurrence byte provenance",
        )
        owners = self._mapping(
            root_evidence.get("owner_sources"),
            "owner source",
        )
        owner_response_hashes = {
            owner_id: self._mapping(owners.get(owner_id), owner_id).get(
                "response_bytes_hash"
            )
            for owner_id in ("O_Q", "O_V", "O_P")
        }

        effect_hash = lineage.get("effect_hash")
        acceptance_hashes = [
            owner_response_hashes["O_Q"],
            owner_response_hashes["O_V"],
        ]
        finality_hash = owner_response_hashes["O_P"]
        self.assertEqual(effect_hash, occurrence.get("bytes_hash"))
        self.assertEqual(
            set(recovery.get("acceptance_hashes", [])),
            set(acceptance_hashes),
        )
        self.assertEqual(recovery.get("finality_hash"), finality_hash)
        fixture_constants = {
            "sha256:effect-001",
            "sha256:accept-oq",
            "sha256:accept-ov",
            "sha256:op-finality",
        }
        self.assertFalse(
            fixture_constants.intersection(
                {effect_hash, finality_hash, *acceptance_hashes}
            ),
            "G7 copied qualified-e6 fixture digest labels instead of actual byte refs",
        )

        combined = PREFLIGHT.load_envelope(
            PREFLIGHT_ROOT / "fixtures" / "qualified-e6.json"
        )
        combined["components"]["G7"] = deepcopy(dict(g7))
        g6_evidence = combined["components"]["G6"]["evidence"]
        g6_evidence["effect_occurrence"]["effect_hash"] = effect_hash
        for receipt in g6_evidence["owner_acceptances"]:
            owner_id = receipt["owner_id"]
            receipt["effect_hash"] = effect_hash
            receipt["acceptance_hash"] = owner_response_hashes[owner_id]
        g6_evidence["op_finality"]["effect_hash"] = effect_hash
        g6_evidence["op_finality"]["after_acceptance_hashes"] = acceptance_hashes
        g6_evidence["op_finality"]["finality_hash"] = finality_hash

        report = PREFLIGHT.validate_envelope(combined)
        self.assertEqual(
            report.get("preflight_status"),
            "QUALIFIED_COMPONENT_OUTPUTS",
            report.get("rejections"),
        )
        self.assertEqual(
            report.get("contract_score_status"),
            "CONTRACT_SCORE_NOT_COMPUTED",
        )

    def test_unrun_and_unestablished_boundaries_remain_explicit(self) -> None:
        """Local process evidence must not promote real-world claims."""

        boundaries = self._mapping(
            self._root_evidence().get("evidence_boundaries"),
            "evidence boundaries",
        )
        expected = {
            "hidden_pair": "NOT_CONSTRUCTED",
            "safety_liveness_frontier": "NOT_RUN",
            "real_product_run": "NOT_RUN",
            "human_owner_run": "NOT_RUN",
            "legal_power_domain_run": "NOT_RUN",
            "physical_world_occurrence": "NOT_RUN",
            "production_split_brain": "NOT_RUN",
            "cross_product_portability": "NOT_ESTABLISHED",
            "full_lifecycle_net_value": "NOT_ESTABLISHED",
            "complete_ce001": "NOT_ESTABLISHED",
        }
        self.assertEqual(
            {key: boundaries.get(key) for key in expected},
            expected,
        )

    def test_existing_e4_e6_risk_boundaries_are_not_weakened(self) -> None:
        """Control: second-round work must preserve the first-round risk closure."""

        module = EvolutionModule(self.fixture)
        e4 = module.run_e4()
        e6 = module.run_e6()
        self.assertEqual(e4["dispatch"]["outcome"], "COMMITTED")
        self.assertEqual(
            e4["effect_readback"]["effect"]["origin_resource_id"],
            "battery-alternative",
        )
        self.assertTrue(e4["history_prefix_preserved"])
        self.assertEqual(e6["effect_count"], 1)
        self.assertTrue(e6["replay_suppressed"])
        self.assertTrue(e6["history_prefix_preserved"])
        self.assertEqual(
            e6["old_runtime_restart"]["outcome"],
            "FENCED_OR_DENIED",
        )

    def test_field_loss_cost_adapter_and_hidden_pair_boundaries_stay_honest(
        self,
    ) -> None:
        """Control: root repair may not erase the existing negative boundaries."""

        module = EvolutionModule(self.fixture)
        field_loss = module.run_capsule_field_loss()
        e4 = module.run_e4()
        e6 = module.run_e6()
        self.assertFalse(field_loss["migration_import"]["imported"])
        self.assertFalse(field_loss["dispatch_after_import"])
        self.assertEqual(field_loss["final_action"], "BOUNDED_UNKNOWN")
        self.assertEqual(
            e4["context"]["cost_comparison_status"],
            "NOT_MEASURED_FULL_LIFECYCLE",
        )
        self.assertEqual(
            e6["adapter_interfaces"]["semantic_independence"],
            "NOT_ESTABLISHED",
        )
        self.assertEqual(
            self.fixture["hidden_pair_status"],
            "NOT_CONSTRUCTED",
        )
        self.assertEqual(
            self.fixture["safety_liveness_frontier"],
            "NOT_RUN",
        )


if __name__ == "__main__":
    unittest.main()
