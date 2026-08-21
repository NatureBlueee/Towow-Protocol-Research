import inspect
import unittest

import method
from evaluator import evaluate, load_frozen_grader
from method import G6Method
from model import AuthorityObservation, AuthorityStatus
from owner_api import start_owner_session
from scenarios import CASE_IDS, build_world
from wire import canonical_bytes, canonical_hash


class EndToEndTests(unittest.TestCase):
    def run_case(self, case_id):
        world = build_world(case_id)
        with start_owner_session(world) as session:
            client = session.client
            result = G6Method().run(world.plan, client)
            snapshots = session.snapshots()
            plan_sha256 = canonical_hash(canonical_bytes(world.plan))
            trace_closure = session.freeze_closure(
                plan_sha256,
                canonical_hash(canonical_bytes(result.as_dict())),
            )
        return (
            world,
            snapshots,
            client,
            result,
            evaluate(
                result,
                case_id,
                load_frozen_grader(),
                trace_closure=trace_closure,
                expected_plan_sha256=plan_sha256,
            ),
        )

    def test_all_cases_have_correct_resolution(self):
        evaluations = [self.run_case(case_id)[4] for case_id in CASE_IDS]
        self.assertEqual(sum(item["correct_resolution"] for item in evaluations), 8)

    def test_ack_lost_after_effect_does_not_repeat(self):
        _world, snapshots, _client, result, _evaluation = self.run_case(
            "E3A-ACK-LOST-EFFECT"
        )
        self.assertEqual(
            len(snapshots["O_E"]["state"]["occurrences"]), 1
        )
        self.assertFalse(result.duplicate_effect)
        self.assertEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")

    def test_wrong_target_real_damage_is_recovered_then_rebuilt(self):
        _world, snapshots, _client, result, evaluation = self.run_case(
            "E3B-ACK-LOST-NO-EFFECT"
        )
        self.assertEqual(evaluation["wrong_target_real_effect_count"], 1)
        self.assertEqual(evaluation["recovery_count"], 1)
        self.assertEqual(
            len(snapshots["O_E"]["state"]["recoveries"]), 1
        )
        self.assertEqual(
            result.resolution,
            "RECOVERED_WRONG_TARGET_THEN_EXACT_EFFECT_ACCEPTED_SETTLED",
        )
        self.assertFalse(evaluation["g6_line_local_closure"])

    def test_e3_pair_is_method_visible_isomorphic_before_interaction(self):
        plan_a = build_world("E3A-ACK-LOST-EFFECT").plan
        plan_b = build_world("E3B-ACK-LOST-NO-EFFECT").plan
        self.assertEqual(plan_a, plan_b)
        self.assertEqual(plan_a.case_id, "E3-ACK-LOST-OPAQUE")
        self.assertEqual(len(plan_a.attempts), 2)

    def test_revoked_primary_is_not_executed_and_alternative_recovers_value(self):
        _world, _snapshots, client, result, evaluation = self.run_case(
            "E4-REVOKE-WITH-ALTERNATIVE"
        )
        executed = [
            receipt.request["operation_id"]
            for receipt in client.trace
            if receipt.endpoint == "execute"
        ]
        self.assertNotIn("op-revoked", executed)
        self.assertIn("op-alternative", executed)
        self.assertTrue(evaluation["g6_line_local_closure"])
        self.assertEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")

    def test_impossible_refusal_has_no_effect_or_settlement(self):
        _world, snapshots, client, result, evaluation = self.run_case(
            "E5-IMPOSSIBLE-REFUSAL"
        )
        self.assertEqual(snapshots["O_E"]["state"]["occurrences"], [])
        self.assertEqual(result.settlements, [])
        self.assertEqual(evaluation["raw_occurrence_count"], 0)
        self.assertEqual(result.resolution, "BOUNDED_REFUSAL_NO_EFFECT")
        self.assertEqual(
            [receipt.endpoint for receipt in client.trace], ["authority"]
        )

    def test_migration_readback_avoids_second_submit(self):
        _world, snapshots, client, result, _evaluation = self.run_case(
            "E6-MIGRATION-REPLAY"
        )
        self.assertEqual(
            len(snapshots["O_E"]["state"]["occurrences"]), 1
        )
        self.assertNotIn(
            "execute", [receipt.endpoint for receipt in client.trace]
        )
        self.assertEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")

    def test_effect_adoption_acceptance_and_settlement_are_distinct_calls(self):
        _world, _snapshots, client, result, _evaluation = self.run_case(
            "E0-PLATFORM-DIRECT"
        )
        calls = [(receipt.owner_id, receipt.endpoint) for receipt in client.trace]
        self.assertIn(("O_E", "effects"), calls)
        self.assertIn(("O_V", "adoption"), calls)
        self.assertIn(("O_Q", "acceptance"), calls)
        self.assertIn(("O_V", "acceptance"), calls)
        self.assertIn(("O_P", "open_settlement"), calls)
        self.assertEqual({item.owner_id for item in result.acceptances}, {"O_Q", "O_V"})
        self.assertEqual(len(set(client.owner_process_ids.values())), 5)

    def test_method_has_no_oracle_fixture_or_world_import(self):
        source = inspect.getsource(method)
        for forbidden in (
            "EXPECTED_RESOLUTION",
            "build_world",
            "PrivateWorld",
            "scenarios",
            "fixtures",
            "open(",
            "read_text",
            "json.load",
        ):
            self.assertNotIn(forbidden, source)

    def test_raw_trace_contains_only_endpoint_receipts_not_owner_packet(self):
        _world, _snapshots, client, _result, _evaluation = self.run_case(
            "E0-PLATFORM-DIRECT"
        )
        endpoints = [receipt.endpoint for receipt in client.trace]
        self.assertGreater(len(endpoints), 1)
        for receipt in client.trace:
            encoded = str(receipt.as_dict())
            self.assertNotIn("expected_resolution", encoded)
            self.assertNotIn("private_world", encoded)
            self.assertNotIn("owner_packet", encoded)

    def test_owner_failure_stays_unknown_and_does_not_settle(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.fail_endpoint("O_E", "effects")
        with start_owner_session(world) as session:
            result = G6Method().run(world.plan, session.client)
        self.assertEqual(result.resolution, "BOUNDED_UNKNOWN_OWNER_UNAVAILABLE")
        self.assertEqual(result.settlements, [])

    def test_malformed_authority_never_reaches_execute(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.safety.response_overrides["authority"] = AuthorityObservation(
            "O_R",
            "op-platform",
            "wrong-actor",
            "Circuit-C7",
            "Q@v1",
            AuthorityStatus.AUTHORIZED,
            999,
            "self-assertion",
        )
        with start_owner_session(world) as session:
            result = G6Method().run(world.plan, session.client)
            called = [item.endpoint for item in session.client.trace]
        self.assertEqual(called, ["authority"])
        self.assertEqual(result.resolution, "BOUNDED_UNKNOWN")
        self.assertEqual(result.effects, [])


if __name__ == "__main__":
    unittest.main()
