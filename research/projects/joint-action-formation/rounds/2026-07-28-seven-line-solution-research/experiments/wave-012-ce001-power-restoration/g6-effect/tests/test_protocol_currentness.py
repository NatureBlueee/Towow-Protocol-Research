"""Implementation-side regression tests for third-pass response currentness.

These tests are intentionally independent of the private grader labels.  They
exercise the transport/native-evidence boundary that the second pass left
open.  Agent C's separate ``test_fix2_redlights.py`` remains untouched.
"""

from __future__ import annotations

import copy
import json
import os
import unittest

from evaluator import evaluate, load_frozen_grader
from method import G6Method
from model import RawOccurrence, TargetStateObservation
from owner_api import (
    response_payload,
    start_owner_session,
    verified_acceptance_payload,
)
from scenarios import build_world
from wire import WireProtocolError, canonical_bytes, canonical_hash


def _run(world, client_wrapper=None):
    with start_owner_session(world) as session:
        client = session.client
        method_client = client_wrapper(client) if client_wrapper else client
        result = G6Method().run(world.plan, method_client)
        snapshots = session.snapshots()
        trace = tuple(client.trace)
    return result, snapshots, trace


class _ReplayEndpoint:
    def __init__(self, inner, endpoint, replay_bytes):
        self.inner = inner
        self.endpoint = endpoint
        self.replay_bytes = replay_bytes

    @property
    def trace(self):
        return self.inner.trace

    def __getattr__(self, name):
        if name == self.endpoint:
            return lambda *args, **kwargs: self.replay_bytes
        return getattr(self.inner, name)


class CurrentResponseProtocolTests(unittest.TestCase):
    def test_detached_decoders_are_not_evidence_paths(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            authority = session.client.authority("op-platform")
        with self.assertRaises(WireProtocolError):
            response_payload(
                authority,
                owner_id="O_S",
                endpoint="authority",
            )
        with self.assertRaises(WireProtocolError):
            verified_acceptance_payload(
                authority,
                owner_id="O_Q",
            )

    def test_owner_client_rejects_current_process_drift(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            session.client._client_pid = os.getpid() + 1_000_000
            with self.assertRaises(WireProtocolError):
                session.client.authority("op-platform")
            self.assertEqual(session.client.trace, ())

    def test_response_envelope_binds_session_nonce_ordinal_and_native_heads(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            response = session.client.authority("op-platform")
        envelope = json.loads(response)
        for field in (
            "session_id",
            "request_id",
            "request_nonce",
            "request_ordinal",
            "native_attestation",
        ):
            self.assertIn(field, envelope)
        native = envelope["native_attestation"]
        for field in (
            "ledger_head",
            "ledger_length",
            "previous_ledger_head",
            "state_head",
            "native_payload_sha256",
        ):
            self.assertIn(field, native)

    def test_cross_session_effect_response_replay_fails_closed(self):
        old_world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(old_world) as old_session:
            old_session.client.authority("op-platform")
            old_session.client.execute("op-platform")
            old_effects = old_session.client.effects("op-platform")

        new_world = build_world("E0-PLATFORM-DIRECT")
        result, _snapshots, _trace = _run(
            new_world,
            lambda client: _ReplayEndpoint(client, "effects", old_effects),
        )
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_format_correct_effect_payload_without_native_occurrence_fails(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.effect.operations["op-platform"].create_effect = False
        world.effect.response_overrides["effects"] = [
            RawOccurrence(
                occurrence_id="occ:E0-PLATFORM-DIRECT:op-platform",
                owner_id="O_E",
                domain="TARGET_NATIVE",
                native_kind="POWER_STATE_TRANSITION",
                object_id="Circuit-C7",
                occurred_at=102,
                operation_id="op-platform",
                from_state="UNPOWERED",
                to_state="POWERED",
                power_kw=3.0,
                state_version=1,
            )
        ]
        result, snapshots, _trace = _run(world)
        self.assertEqual(snapshots["O_E"]["state"]["occurrences"], [])
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_cross_session_acceptance_bytes_fail_with_empty_current_act_ledgers(self):
        old_world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(old_world) as old_session:
            old_result = G6Method().run(old_world.plan, old_session.client)
            self.assertEqual(old_result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
            old_q = next(
                item.response_bytes.encode("utf-8")
                for item in old_session.client.trace
                if item.owner_id == "O_Q" and item.endpoint == "acceptance"
            )
            old_v = next(
                item.response_bytes.encode("utf-8")
                for item in old_session.client.trace
                if item.owner_id == "O_V" and item.endpoint == "acceptance"
            )

        class ReplayAcceptances:
            def __init__(self, inner):
                self.inner = inner

            @property
            def trace(self):
                return self.inner.trace

            def acceptance(self, _effect, owner_id, _episode_id, _q_version):
                return old_q if owner_id == "O_Q" else old_v

            def __getattr__(self, name):
                return getattr(self.inner, name)

        new_world = build_world("E0-PLATFORM-DIRECT")
        result, snapshots, _trace = _run(new_world, ReplayAcceptances)
        self.assertEqual(snapshots["O_Q"]["state"]["acts"], {})
        self.assertEqual(snapshots["O_V"]["state"]["acts"], {})
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_forged_recovery_readback_cannot_replace_native_state(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        world.effect.recovery_mode = "FORGED_NO_MUTATION"
        world.effect.response_overrides["target_state"] = TargetStateObservation(
            owner_id="O_E",
            domain="TARGET_NATIVE",
            object_id="Circuit-C8",
            state="UNPOWERED",
            observed_at=105,
            state_version=2,
            last_occurrence_id=(
                "recovery:occ:E3-ACK-LOST-OPAQUE:op-e3-primary"
            ),
        )
        result, snapshots, _trace = _run(world)
        target = snapshots["O_E"]["state"]["targets"]["Circuit-C8"]
        self.assertEqual(target["state"], "POWERED")
        self.assertEqual(result.resolution, "RECOVERY_UNKNOWN")

    def test_cross_session_o_p_finality_bytes_fail_with_empty_current_ledger(self):
        old_world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(old_world) as old_session:
            old_result = G6Method().run(old_world.plan, old_session.client)
            self.assertEqual(old_result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
            old_open = next(
                item.response_bytes.encode("utf-8")
                for item in old_session.client.trace
                if item.endpoint == "open_settlement"
            )
            old_state = next(
                item.response_bytes.encode("utf-8")
                for item in old_session.client.trace
                if item.endpoint == "settlement_state"
            )

        class ReplayPayment:
            def __init__(self, inner):
                self.inner = inner

            @property
            def trace(self):
                return self.inner.trace

            def open_settlement(self, _effect, _acceptances):
                return old_open

            def settlement_state(self, _obligation_id, _effect_id):
                return old_state

            def __getattr__(self, name):
                return getattr(self.inner, name)

        new_world = build_world("E0-PLATFORM-DIRECT")
        result, snapshots, _trace = _run(new_world, ReplayPayment)
        self.assertEqual(snapshots["O_P"]["state"]["obligations"], {})
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_evaluator_rejects_detached_result_without_frozen_receipt_closure(self):
        world = build_world("E0-PLATFORM-DIRECT")
        result, _snapshots, _trace = _run(world)
        detached = copy.deepcopy(result)
        detached.evidence_closure = {}
        evaluation = evaluate(
            detached,
            "E0-PLATFORM-DIRECT",
            load_frozen_grader(),
            expected_plan_sha256=detached.plan_sha256,
        )
        self.assertFalse(evaluation["evidence_closure_valid"])
        self.assertFalse(evaluation["g6_line_local_closure"])

    def test_evaluator_rejects_plan_transplant(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            result = G6Method().run(world.plan, session.client)
            closure = session.freeze_closure(
                result.plan_sha256,
                canonical_hash(canonical_bytes(result.as_dict())),
            )
        wrong_plan = copy.deepcopy(closure)
        object.__setattr__(wrong_plan, "plan_sha256", "f" * 64)
        transplanted = evaluate(
            result,
            "E0-PLATFORM-DIRECT",
            load_frozen_grader(),
            trace_closure=wrong_plan,
            expected_plan_sha256=result.plan_sha256,
        )
        self.assertFalse(transplanted["evidence_closure_valid"])

    def test_native_acceptance_records_bind_exact_effect_and_current_request(self):
        world = build_world("E0-PLATFORM-DIRECT")
        result, snapshots, _trace = _run(world)
        effect = result.effects[0].occurrence
        expected_effect_hash = canonical_hash(canonical_bytes(effect))
        for owner_id in ("O_Q", "O_V"):
            records = [
                item
                for item in snapshots[owner_id]["state"]["native_records"]
                if item["endpoint"] == "acceptance"
            ]
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(
                record["bindings"]["effect_sha256"],
                expected_effect_hash,
            )
            self.assertEqual(
                record["bindings"]["native_act_effect_id"],
                effect.occurrence_id,
            )
            self.assertEqual(record["session_id"], result.evidence_closure["session_id"])
            self.assertTrue(record["nonce"])
            self.assertGreater(record["ordinal"], 0)

    def test_native_o_p_records_bind_exact_acceptance_set_and_phase_scheme(self):
        world = build_world("E0-PLATFORM-DIRECT")
        result, snapshots, trace = _run(world)
        open_receipt = next(
            item for item in trace if item.endpoint == "open_settlement"
        )
        exact_set = sorted(
            open_receipt.request["acceptances"],
            key=lambda item: (item["owner_id"], item["act_id"]),
        )
        expected_set_hash = canonical_hash(canonical_bytes(exact_set))
        records = snapshots["O_P"]["state"]["native_records"]
        opened = next(
            item for item in records if item["endpoint"] == "open_settlement"
        )
        finality = next(
            item for item in records if item["endpoint"] == "settlement_state"
        )
        self.assertEqual(
            opened["bindings"]["exact_acceptance_set_sha256"],
            expected_set_hash,
        )
        self.assertEqual(
            opened["bindings"]["exact_acceptance_owners"],
            ["O_Q", "O_V"],
        )
        self.assertEqual(opened["bindings"]["native_scheme"], "CE_PAY_V1")
        self.assertEqual(
            finality["bindings"]["native_obligation_id"],
            result.settlements[0].obligation.obligation_id,
        )
        self.assertEqual(
            finality["bindings"]["required_phases"],
            list(result.settlements[0].obligation.required_phases),
        )
        self.assertTrue(finality["bindings"]["native_phase_set_sha256"])


if __name__ == "__main__":
    unittest.main()
