from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import private_oracle as attacks  # noqa: E402


class FixtureIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = attacks.load_public_fixture()
        cls.oracle = attacks.load_oracle()
        cls.public = attacks.index_worlds(cls.fixture)
        cls.private = attacks.index_worlds(cls.oracle)

    def test_world_count_and_ids(self) -> None:
        self.assertEqual(len(self.public), 18)
        self.assertEqual(set(self.public), set(self.private))

    def test_public_private_isolation(self) -> None:
        self.assertEqual(attacks.validate_isolation(self.fixture, self.oracle), [])

    def test_hidden_edge_pair_is_method_indistinguishable(self) -> None:
        left = attacks.canonicalize_opaque_ids(
            self.public["w010"], {"w010": "wPAIR", "c010": "cPAIR"}
        )
        right = attacks.canonicalize_opaque_ids(
            self.public["w011"], {"w011": "wPAIR", "c011": "cPAIR"}
        )
        self.assertEqual(left, right)
        self.assertNotEqual(
            self.private["w010"]["orthogonal_truth"]["normative_stance"],
            self.private["w011"]["orthogonal_truth"]["normative_stance"],
        )

    def test_private_oracle_preserves_orthogonal_coordinates(self) -> None:
        for world in self.private.values():
            self.assertEqual(
                set(world["orthogonal_truth"]),
                attacks.ORTHOGONAL_KEYS,
                msg=world["world_id"],
            )

    def test_public_fixture_contains_no_normalized_control_coordinate(self) -> None:
        self.assertEqual(attacks.public_leak_paths(self.fixture), [])


class AdversarialDetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = attacks.load_public_fixture()
        cls.oracle = attacks.load_oracle()
        cls.public = attacks.index_worlds(cls.fixture)
        cls.private = attacks.index_worlds(cls.oracle)

    def test_truth_to_api_direct_copy_is_detected(self) -> None:
        poisoned = copy.deepcopy(self.public["w001"])
        poisoned["provider_scenario"]["authority"]["responses"]["a1"][
            "normative_stance"
        ] = self.private["w001"]["orthogonal_truth"]["normative_stance"]
        leaks = attacks.truth_to_api_copy_paths(poisoned, self.private["w001"])
        self.assertTrue(
            any("normative_stance" in path for path in leaks),
            leaks,
        )

    def test_whole_truth_block_copy_is_detected(self) -> None:
        poisoned = copy.deepcopy(self.public["w001"])
        poisoned["public_packet"]["adapter_projection"] = copy.deepcopy(
            self.private["w001"]["orthogonal_truth"]
        )
        leaks = attacks.truth_to_api_copy_paths(poisoned, self.private["w001"])
        self.assertTrue(leaks)

    def test_expected_closure_injection_is_detected(self) -> None:
        payload = copy.deepcopy(self.public["w002"]["public_packet"])
        payload["planner_hint"] = {
            "expected_closure": self.private["w002"]["expected_closure"]
        }
        self.assertEqual(
            attacks.expected_closure_injection_paths(payload),
            ["planner_hint.expected_closure"],
        )

    def test_five_state_lookup_table_is_rejected_as_complete_policy(self) -> None:
        bad_policy = {
            "CURRENT": "CONTINUE",
            "REVOKED": "LOCAL_REOPEN",
            "UNKNOWN": "BLOCK",
            "REFUSED": "BLOCK",
            "STALE": "BLOCK",
        }
        orthogonal_policy = {
            ("UNKNOWN", "NONE", "NONE"): "BLOCK",
            ("UNKNOWN", "COMMIT_UNKNOWN", "CRASH_TAKEOVER"): "RECOVER",
        }
        self.assertTrue(attacks.detect_single_enum_policy(bad_policy))
        self.assertFalse(attacks.detect_single_enum_policy(orthogonal_policy))

    def test_unknown_no_dispatch_and_uncertain_effect_need_distinct_reconciliation(self) -> None:
        compressed = {
            "w003": {"action": "BLOCK", "reconciliation": []},
            "w004": {"action": "BLOCK", "reconciliation": []},
        }
        violations = attacks.five_state_compression_violations(compressed)
        self.assertGreaterEqual(len(violations), 1)

        orthogonal = {
            "w003": {"action": "BLOCK", "reconciliation": []},
            "w004": {
                "action": "RECOVER",
                "reconciliation": ["effect/c004/fulfil"],
            },
        }
        self.assertEqual(attacks.five_state_compression_violations(orthogonal), [])

    def test_method_alias_is_detected(self) -> None:
        def implementation(record: dict) -> str:
            return str(record.get("action"))

        aliases = attacks.method_alias_groups(
            {
                "mature_composite": implementation,
                "equal_authority_center": implementation,
            }
        )
        self.assertEqual(
            aliases,
            [["equal_authority_center", "mature_composite"]],
        )

    def test_capsule_field_drop_and_oracle_copy_are_detected(self) -> None:
        source_visible = {field: [] for field in attacks.CAPSULE_REQUIRED_FIELDS}
        complete = copy.deepcopy(source_visible)
        self.assertEqual(
            attacks.capsule_oracle_violations(
                complete, source_visible, self.private["w015"]
            ),
            [],
        )

        dropped = copy.deepcopy(complete)
        dropped.pop("acceptance_records")
        self.assertTrue(
            any(
                "acceptance_records" in violation
                for violation in attacks.capsule_oracle_violations(
                    dropped, source_visible, self.private["w015"]
                )
            )
        )

        perfect = copy.deepcopy(complete)
        perfect["oracle_truth"] = copy.deepcopy(
            self.private["w015"]["orthogonal_truth"]
        )
        violations = attacks.capsule_oracle_violations(
            perfect, source_visible, self.private["w015"]
        )
        self.assertTrue(any("oracle" in violation for violation in violations))

    def test_capsule_preserves_native_channel_outcome_without_truth_leak(self) -> None:
        source_visible = {field: [] for field in attacks.CAPSULE_REQUIRED_FIELDS}
        source_visible["authority_observations"] = [
            {
                "provider_id": "owner-a",
                "channel_outcome": "TIMEOUT",
                "native_body": {"retryAfterMs": 500},
            }
        ]
        capsule = copy.deepcopy(source_visible)
        self.assertEqual(
            attacks.capsule_oracle_violations(
                capsule, source_visible, self.private["w015"]
            ),
            [],
        )

    def test_history_rewrite_is_detected(self) -> None:
        before = [
            {"id": "e1", "kind": "Effect", "state": "CONFIRMED"},
            {"id": "a1", "kind": "Acceptance", "state": "REFUSED"},
        ]
        valid_after = before + [{"id": "d1", "kind": "Defeater", "future": False}]
        self.assertEqual(attacks.history_rewrite_violations(before, valid_after), [])

        rewritten = copy.deepcopy(valid_after)
        rewritten[1]["state"] = "ACCEPTED"
        self.assertEqual(
            attacks.history_rewrite_violations(before, rewritten),
            ["history record 1 rewritten"],
        )

    def test_low_drift_grade_does_not_accept_labels_in_place_of_trace(self) -> None:
        honest_record = {
            "world_id": "w001",
            "action": "CONTINUE",
            "closure": [],
            "reconciliation": [],
            "history_before": [
                {"id": "effect/c001/fulfil", "state": "CONFIRMED"}
            ],
            "history_after": [
                {"id": "effect/c001/fulfil", "state": "CONFIRMED"}
            ],
            "effect_count": 1,
        }
        grade = attacks.grade_run("w001", honest_record, self.oracle)
        self.assertTrue(grade["passed"], grade)

        label_only = copy.deepcopy(honest_record)
        label_only["action"] = "RECOVERY_SUCCEEDED"
        label_only["recovery_succeeded"] = True
        grade = attacks.grade_run("w001", label_only, self.oracle)
        self.assertFalse(grade["checks"]["safe_action"])

    def test_factual_unsafe_is_distinct_from_unjustified_continue(self) -> None:
        common = {
            "action": "CONTINUE",
            "closure": [],
            "reconciliation": [],
            "history_before": [],
            "history_after": [],
            "effect_count": 1,
            "dispatch_response": {
                "outcome": "COMMITTED",
                "duplicate_suppressed": False,
            },
        }
        hidden_valid = attacks.grade_run("w010", common, self.oracle)
        hidden_revoked = attacks.grade_run("w011", common, self.oracle)

        self.assertTrue(hidden_valid["checks"]["unsafe_continuation"])
        self.assertFalse(hidden_valid["checks"]["unjustified_continuation"])
        self.assertFalse(hidden_revoked["checks"]["unsafe_continuation"])
        self.assertFalse(hidden_revoked["checks"]["unjustified_continuation"])

    def test_oracle_and_fixture_are_distinct_physical_files(self) -> None:
        self.assertNotEqual(attacks.FIXTURE_PATH, attacks.ORACLE_PATH)
        self.assertEqual(
            json.loads(attacks.FIXTURE_PATH.read_text(encoding="utf-8"))[
                "fixture_id"
            ],
            "T6-G7-ORTHOGONAL-REPLAY-001",
        )
        self.assertEqual(
            json.loads(attacks.ORACLE_PATH.read_text(encoding="utf-8"))[
                "oracle_id"
            ],
            "T6-G7-ORTHOGONAL-REPLAY-001-PRIVATE-ORACLE",
        )


if __name__ == "__main__":
    unittest.main()
