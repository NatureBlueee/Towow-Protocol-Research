from __future__ import annotations

import base64
from hashlib import sha256
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g7evo.model import EffectTarget  # noqa: E402
from g7evo.runtime import EvolutionModule  # noqa: E402


class G7ProcessBoundaryV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture = json.loads(
            (ROOT / "fixtures" / "ce001-g7.json").read_text(encoding="utf-8")
        )
        cls.results = EvolutionModule(fixture).run_all()
        cls.evidence = cls.results["evidence"]

    def test_all_owner_binding_attacks_are_real_worker_rejections(self) -> None:
        expected = {
            "duplicate_owner",
            "response_transplant",
            "stale_response",
            "wrong_episode",
            "wrong_q",
            "wrong_object",
            "wrong_operation",
            "wrong_target",
            "wrong_effect_occurrence",
        }
        attacks = self.evidence["owner_binding_attacks"]
        self.assertEqual(set(attacks), expected)
        process_ids = []
        for attack_id, outcome in attacks.items():
            with self.subTest(attack=attack_id):
                self.assertFalse(outcome["accepted"])
                self.assertFalse(outcome["finalized"])
                self.assertEqual(outcome["state_act_count"], 0)
                self.assertEqual(outcome["worker_exit_code"], 0)
                process_ids.append(outcome["process_id"])
                path = Path(outcome["state_path"])
                self.assertTrue(path.is_file())
                self.assertEqual(
                    outcome["state_bytes_hash"],
                    sha256(path.read_bytes()).hexdigest(),
                )
        self.assertEqual(len(process_ids), len(set(process_ids)))

    def test_all_receipt_mutations_leave_zero_target_transition(self) -> None:
        expected = {
            "wrong_receipt",
            "stale_receipt",
            "tampered_receipt",
            "receipt_set_transplant",
            "missing_receipt",
            "duplicate_receipt",
            "wrong_current_head",
        }
        attacks = self.evidence["receipt_consumption_attacks"]
        self.assertEqual(set(attacks), expected)
        for attack_id, outcome in attacks.items():
            with self.subTest(attack=attack_id):
                self.assertFalse(outcome["committed"])
                self.assertEqual(outcome["target_transition_count"], 0)
                path = Path(outcome["target_state_path"])
                self.assertEqual(
                    outcome["target_state_bytes_hash"],
                    sha256(path.read_bytes()).hexdigest(),
                )

    def test_receipts_come_from_independent_owner_issuer_processes(self) -> None:
        issuers = self.evidence["receipt_issuer_sources"]
        target_pid = self.evidence["target_receipt_consumption"][
            "target_process_id"
        ]
        self.assertEqual(set(issuers), {"O_R", "O_S"})
        self.assertNotEqual(
            issuers["O_R"]["process_id"],
            issuers["O_S"]["process_id"],
        )
        self.assertNotIn(
            target_pid,
            {issuers["O_R"]["process_id"], issuers["O_S"]["process_id"]},
        )
        self.assertNotEqual(
            issuers["O_R"]["state_source_id"],
            issuers["O_S"]["state_source_id"],
        )
        self.assertNotEqual(
            issuers["O_R"]["act_source_id"],
            issuers["O_S"]["act_source_id"],
        )
        for owner_id, issuer in issuers.items():
            with self.subTest(owner=owner_id):
                state_path = Path(issuer["state_path"])
                self.assertEqual(
                    issuer["state_bytes_hash"],
                    sha256(state_path.read_bytes()).hexdigest(),
                )
                receipt_raw = base64.b64decode(
                    issuer["receipt_bytes_b64"], validate=True
                )
                self.assertEqual(
                    issuer["receipt_bytes_hash"],
                    sha256(receipt_raw).hexdigest(),
                )
        public_source = (ROOT / "g7evo" / "boundary.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("owner_signature", public_source)
        self.assertNotIn("issue_current_receipt_set", public_source)

    def test_controller_boolean_is_not_an_authorizing_compatibility_path(self) -> None:
        operation = {
            "semantic_effect_key": "test:key",
            "operation_id": "deliver-3kw-45m",
            "operation_version": "v1",
            "object_id": "VenueV:CircuitC7",
            "q_version": "Q@v1",
            "delivered_kw": 3.0,
            "duration_minutes": 45,
        }
        target = EffectTarget("O_E")
        with self.assertRaises(TypeError):
            target.dispatch(
                operation=operation,
                coordinator_epoch=1,
                authority_allowed=True,
            )
        self.assertEqual(target.effects, {})

    def test_rewritten_prefix_and_capsule_field_loss_are_process_rejected(self) -> None:
        rewrite = self.evidence["history_rewrite_attack"]
        self.assertTrue(rewrite["rewrite_rejected"])
        self.assertNotEqual(
            rewrite["candidate_bytes_hash"],
            rewrite["persisted_bytes_hash"],
        )
        field_loss = self.evidence["capsule_field_loss_attack"]
        self.assertFalse(field_loss["imported"])
        self.assertFalse(field_loss["dispatch_after_import"])
        self.assertEqual(field_loss["worker_exit_code"], 0)
        self.assertTrue(Path(field_loss["state_path"]).is_file())

    def test_external_fence_is_reloaded_by_a_replacement_process(self) -> None:
        migration = self.evidence["migration"]
        fence = migration["fence_owner"]
        restart = migration["old_runtime_restart"]
        self.assertNotEqual(fence["process_id"], fence["restart_process_id"])
        self.assertEqual(restart["fence_result"], "REJECTED_OLD_EPOCH")
        self.assertEqual(
            restart["external_fence_event_hash"],
            fence["old_epoch_rejection"]["event_hash"],
        )


if __name__ == "__main__":
    unittest.main()
