"""Third-pass G6 currentness and native-ledger red-light attacks.

These tests are deliberately independent of the private grader and its
expected resolutions.  They assert only safety invariants: a detached or stale
owner response cannot stand in for a current request, current owner process,
or current native ledger; and an evaluator must not accept an unfrozen method
projection without the receipt trace that produced it.
"""

from __future__ import annotations

import inspect
import json
import unittest
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import evaluator
import owner_api
from method import G6Method
from owner_api import start_owner_session
from scenarios import build_world
from wire import (
    WireProtocolError,
    canonical_bytes,
    canonical_hash,
    decode_canonical,
    read_response,
)


def _run_honest(case_id: str):
    world = build_world(case_id)
    with start_owner_session(world) as session:
        result = G6Method().run(world.plan, session.client)
        snapshots = session.snapshots()
        trace = tuple(session.client.trace)
    return world, result, snapshots, trace


def _response(
    trace,
    owner_id: str,
    endpoint: str,
    *,
    first: bool = False,
) -> bytes:
    matches = [
        _receipt_response_bytes(item)
        for item in trace
        if item.owner_id == owner_id and item.endpoint == endpoint
    ]
    if not matches:
        raise AssertionError(f"missing captured response: {owner_id}.{endpoint}")
    return matches[0] if first else matches[-1]


def _receipt(trace, owner_id: str, endpoint: str):
    matches = [
        item
        for item in trace
        if item.owner_id == owner_id and item.endpoint == endpoint
    ]
    if not matches:
        raise AssertionError(f"missing captured receipt: {owner_id}.{endpoint}")
    return matches[-1]


def _receipt_response_bytes(receipt) -> bytes:
    value = getattr(receipt, "raw_response_bytes", None)
    if value is None:
        value = receipt.response_bytes
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def _receipt_request_bytes(receipt) -> bytes:
    value = getattr(receipt, "raw_request_bytes", None)
    if value is None:
        value = receipt.request_bytes
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


def _detached_response_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    return _receipt_response_bytes(value)


def _request_payload(receipt) -> dict[str, Any]:
    request = decode_canonical(_receipt_request_bytes(receipt))
    return request["payload"]


def _rewrite_response(
    value: bytes,
    transform: Callable[[dict[str, Any]], None],
) -> bytes:
    envelope = json.loads(json.dumps(decode_canonical(value)))
    transform(envelope)
    return canonical_bytes(envelope)


class ReplayClient:
    """Return selected detached response bytes while delegating all else."""

    def __init__(self, inner, replays: dict[tuple[str, str | None], Any]):
        self.inner = inner
        self.replays = dict(replays)

    def __getattr__(self, name):
        target = getattr(self.inner, name)
        if not callable(target):
            return target

        def call(*args, **kwargs):
            discriminator = None
            if name == "acceptance":
                discriminator = kwargs.get("owner_id")
                if discriminator is None and len(args) >= 2:
                    discriminator = args[1]
            replacement = self.replays.get((name, discriminator))
            if replacement is None:
                replacement = self.replays.get((name, None))
            if replacement is None:
                return target(*args, **kwargs)
            if callable(replacement):
                return replacement(*args, **kwargs)
            return replacement

        return call


def _has_discharged_settlement(result) -> bool:
    return any(item.discharged for item in result.settlements)


def _verify_trace_closure(closure) -> bool:
    verifier = getattr(evaluator, "verify_trace_closure", None)
    if verifier is not None:
        return bool(verifier(closure))
    verify = getattr(closure, "verify", None)
    if verify is None:
        raise AssertionError("no TraceClosure verifier is exposed")
    return bool(verify())


class CanonicalCurrentRequestBindingTests(unittest.TestCase):
    def test_response_envelope_binds_session_nonce_ordinal_and_ledger_head(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            raw = session.client.authority("op-platform")
            receipt = session.client.trace[-1]
            process_id = session.client.owner_process_ids["O_S"]

        request = decode_canonical(_receipt_request_bytes(receipt))
        response = decode_canonical(_detached_response_bytes(raw))
        for key in ("session_id", "nonce", "ordinal"):
            self.assertIn(key, request)
            self.assertIn(key, response)
            self.assertEqual(request[key], response[key])
        for key in ("owner_id", "endpoint", "request_id"):
            self.assertIn(key, request)
            self.assertEqual(request[key], response[key])
        self.assertEqual(
            response["request_sha256"],
            canonical_hash(_receipt_request_bytes(receipt)),
        )
        for key in (
            "owner_instance_id",
            "client_pid",
            "pre_state_head",
            "post_state_head",
            "pre_ledger_head",
            "post_ledger_head",
            "native_record_refs",
        ):
            self.assertIn(key, response)
        self.assertIsInstance(response["native_record_refs"], list)
        self.assertEqual(response["owner_process_id"], process_id)
        self.assertEqual(
            response["ordinal"],
            getattr(receipt, "ordinal", receipt.sequence),
        )

    def test_wire_rejects_cross_owner_endpoint_and_request_bytes(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            raw = _detached_response_bytes(
                session.client.authority("op-platform")
            )
            receipt = session.client.trace[-1]

        with self.assertRaises(WireProtocolError):
            read_response(
                raw,
                expected_owner="O_E",
                expected_endpoint="authority",
                expected_request_hash=receipt.request_hash,
            )
        with self.assertRaises(WireProtocolError):
            read_response(
                raw,
                expected_owner="O_S",
                expected_endpoint="effects",
                expected_request_hash=receipt.request_hash,
            )
        with self.assertRaises(WireProtocolError):
            read_response(
                raw,
                expected_owner="O_S",
                expected_endpoint="authority",
                expected_request_hash="0" * 64,
            )

    def test_same_session_stale_authority_response_cannot_authorize_new_request(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            stale = session.client.authority("op-platform")
            trace_cut = len(session.client.trace)
            result = G6Method().run(
                world.plan,
                ReplayClient(
                    session.client,
                    {("authority", None): stale},
                ),
            )
            current_trace = tuple(session.client.trace[trace_cut:])

        self.assertNotIn("execute", [item.endpoint for item in current_trace])
        self.assertFalse(_has_discharged_settlement(result))

    def test_tampered_pid_session_nonce_ordinal_and_ledger_head_fail_closed(self):
        tamper_values = {
            "owner_process_id": 2_000_000_001,
            "session_id": "not-the-current-session",
            "nonce": "not-the-current-request-nonce",
            "ordinal": 2_000_000_002,
            "post_ledger_head": "f" * 64,
        }
        for field, bad_value in tamper_values.items():
            with self.subTest(field=field):
                world = build_world("E0-PLATFORM-DIRECT")
                with start_owner_session(world) as session:
                    honest = _detached_response_bytes(
                        session.client.authority("op-platform")
                    )
                    tampered = _rewrite_response(
                        honest,
                        lambda envelope, f=field, v=bad_value: envelope.__setitem__(
                            f, v
                        ),
                    )
                    trace_cut = len(session.client.trace)
                    result = G6Method().run(
                        world.plan,
                        ReplayClient(
                            session.client,
                            {("authority", None): tampered},
                        ),
                    )
                    current_trace = tuple(session.client.trace[trace_cut:])

                self.assertNotIn(
                    "execute",
                    [item.endpoint for item in current_trace],
                    field,
                )
                self.assertFalse(_has_discharged_settlement(result), field)


class NativeLedgerCurrentnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (
            _world,
            _result,
            _snapshots,
            cls.e0_trace,
        ) = _run_honest("E0-PLATFORM-DIRECT")
        (
            _world,
            _result,
            _snapshots,
            cls.e3b_trace,
        ) = _run_honest("E3B-ACK-LOST-NO-EFFECT")

    def test_cross_session_o_q_and_o_v_acceptance_replay_cannot_close(self):
        world = build_world("E0-PLATFORM-DIRECT")
        replays = {
            ("acceptance", "O_Q"): _response(
                self.e0_trace, "O_Q", "acceptance"
            ),
            ("acceptance", "O_V"): _response(
                self.e0_trace, "O_V", "acceptance"
            ),
        }
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayClient(session.client, replays),
            )
            snapshots = session.snapshots()

        self.assertEqual(snapshots["O_Q"]["state"]["acts"], {})
        self.assertEqual(snapshots["O_V"]["state"]["acts"], {})
        self.assertFalse(_has_discharged_settlement(result))
        self.assertEqual(result.settlements, [])

    def test_formatted_o_e_bytes_without_native_occurrence_or_state_cannot_close(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.effect.operations["op-platform"].create_effect = False
        replayed_effect = _response(self.e0_trace, "O_E", "effects")
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayClient(
                    session.client,
                    {("effects", None): replayed_effect},
                ),
            )
            snapshots = session.snapshots()

        self.assertEqual(snapshots["O_E"]["state"]["occurrences"], [])
        self.assertEqual(snapshots["O_E"]["state"]["targets"], {})
        self.assertFalse(_has_discharged_settlement(result))
        self.assertEqual(result.settlements, [])

    def test_same_source_recovery_and_target_readback_replay_cannot_hide_powered_c8(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        world.effect.recovery_mode = "FORGED_NO_MUTATION"
        replays = {
            ("recovery_state", None): _response(
                self.e3b_trace, "O_E", "recovery_state"
            ),
            ("target_state", None): _response(
                self.e3b_trace, "O_E", "target_state"
            ),
        }
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayClient(session.client, replays),
            )
            snapshots = session.snapshots()
            trace = tuple(session.client.trace)

        c8 = snapshots["O_E"]["state"]["targets"]["Circuit-C8"]
        self.assertEqual(c8["state"], "POWERED")
        self.assertEqual(c8["version"], 1)
        self.assertNotIn(
            "op-e3-fallback",
            [
                item.request.get("operation_id")
                for item in trace
                if item.endpoint == "execute"
            ],
        )
        self.assertFalse(_has_discharged_settlement(result))

    def test_cross_session_o_p_obligation_and_finality_replay_cannot_settle(self):
        source_open = _receipt(self.e0_trace, "O_P", "open_settlement")
        replays = {
            ("open_settlement", None): _receipt_response_bytes(source_open),
            ("settlement_state", None): _response(
                self.e0_trace, "O_P", "settlement_state"
            ),
        }
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayClient(session.client, replays),
            )
            snapshots = session.snapshots()

        source_acceptance_pids = {
            item.get("owner_process_id", item.get("process_id"))
            for item in _request_payload(source_open)["acceptances"]
        }
        current_acceptance_pids = {
            item.process_id for item in result.acceptances
        }
        self.assertNotEqual(source_acceptance_pids, current_acceptance_pids)
        self.assertEqual(snapshots["O_P"]["state"]["obligations"], {})
        self.assertEqual(snapshots["O_P"]["state"]["phases"], {})
        self.assertFalse(_has_discharged_settlement(result))

    def test_wrong_scheme_phase_and_exact_acceptance_set_cannot_close_o_p(self):
        source_open = _receipt(self.e0_trace, "O_P", "open_settlement")
        source_state = _response(self.e0_trace, "O_P", "settlement_state")

        def rewrite_open(envelope):
            obligation = envelope["payload"]
            obligation["scheme"] = "ATTACK_SCHEME"
            obligation["required_phases"] = ["CAPTURE"]

        forged_open = _rewrite_response(
            _receipt_response_bytes(source_open),
            rewrite_open,
        )

        def rewrite_state(envelope):
            payload = envelope["payload"]
            payload["obligation"]["scheme"] = "ATTACK_SCHEME"
            payload["obligation"]["required_phases"] = ["CAPTURE"]
            for phase in payload["phases"]:
                phase["scheme"] = "ATTACK_SCHEME"

        forged_state = _rewrite_response(source_state, rewrite_state)
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayClient(
                    session.client,
                    {
                        ("open_settlement", None): forged_open,
                        ("settlement_state", None): forged_state,
                    },
                ),
            )
            snapshots = session.snapshots()

        self.assertEqual(snapshots["O_P"]["state"]["obligations"], {})
        self.assertEqual(snapshots["O_P"]["state"]["phases"], {})
        self.assertFalse(_has_discharged_settlement(result))


class FrozenEvidenceClosureTests(unittest.TestCase):
    def test_detached_response_bytes_have_no_free_payload_decoder(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            response = session.client.authority("op-platform")
            detached = _detached_response_bytes(response)

        decoder = getattr(owner_api, "response_payload", None)
        if decoder is None:
            return
        with self.assertRaises((TypeError, ValueError, WireProtocolError)):
            decoder(
                detached,
                owner_id="O_S",
                endpoint="authority",
            )

    def test_evaluator_requires_frozen_evidence_closure_not_detached_result(self):
        parameters = inspect.signature(evaluator.evaluate).parameters
        self.assertIn("trace_closure", parameters)
        self.assertFalse(
            len(parameters) == 3
            and tuple(parameters) == ("result", "case_id", "grader")
        )

    def test_trace_freeze_and_verifier_reject_drop_reorder_and_byte_tamper(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            result = G6Method().run(world.plan, session.client)
            self.assertTrue(hasattr(session, "freeze_closure"))
            closure = session.freeze_closure(
                canonical_hash(canonical_bytes(world.plan)),
                canonical_hash(canonical_bytes(result.as_dict())),
            )

        closure_bytes = canonical_bytes(closure)
        self.assertTrue(_verify_trace_closure(closure))

        decoded = decode_canonical(closure_bytes)
        self.assertIn("receipts", decoded)
        self.assertGreater(len(decoded["receipts"]), 2)

        receipts = tuple(closure.receipts)
        attacks = [
            replace(closure, receipts=receipts[:-1]),
            replace(
                closure,
                receipts=(receipts[1], receipts[0], *receipts[2:]),
            ),
            replace(
                closure,
                receipts=(
                    replace(
                        receipts[0],
                        raw_response_bytes=(
                            receipts[0].raw_response_bytes + b" "
                        ),
                    ),
                    *receipts[1:],
                ),
            ),
        ]
        for attack in attacks:
            self.assertFalse(_verify_trace_closure(attack))


if __name__ == "__main__":
    unittest.main()
