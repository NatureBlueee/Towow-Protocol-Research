"""Root-session red-light attacks for the second G6 pass.

The assertions are derived from owner isolation and evidence-integrity
invariants.  They do not import or infer the expected case resolutions.
"""

from __future__ import annotations

import inspect
import json
import os
import unittest

from evaluator import evaluate, load_frozen_grader
from method import G6Method
from model import AcceptanceObservation, Obligation, Truth
from owner_api import OwnerClient, start_owner_session
from scenarios import build_world
from wire import WireProtocolError, read_response


def _run(world):
    with start_owner_session(world) as session:
        result = G6Method().run(world.plan, session.client)
        snapshots = session.snapshots()
        trace = tuple(session.client.trace)
        process_ids = session.client.owner_process_ids
    return result, snapshots, trace, process_ids


def _acceptance(
    owner_id: str,
    *,
    act_id: str,
    process_id: int,
) -> AcceptanceObservation:
    return AcceptanceObservation(
        owner_id=owner_id,
        effect_id="occ:E0-PLATFORM-DIRECT:op-platform",
        episode_id="CE-001:E0-PLATFORM-DIRECT",
        q_version="Q@v1",
        accepted=Truth.TRUE,
        observed_at=104,
        act_id=act_id,
        process_id=process_id,
    )


class ProcessAndObjectGraphAttacks(unittest.TestCase):
    def test_five_truth_owners_have_distinct_processes_and_state_shards(self):
        world = build_world("E0-PLATFORM-DIRECT")
        state_shards = world.owner_states()
        self.assertEqual(set(state_shards), {"O_S", "O_E", "O_Q", "O_V", "O_P"})
        self.assertEqual(len({id(value) for value in state_shards.values()}), 5)

        with start_owner_session(world) as session:
            process_ids = session.client.owner_process_ids
            snapshots = session.snapshots()

        self.assertEqual(len(set(process_ids.values())), 5)
        self.assertNotIn(os.getpid(), process_ids.values())
        self.assertEqual(
            {
                owner_id: snapshot["process_id"]
                for owner_id, snapshot in snapshots.items()
            },
            process_ids,
        )
        self.assertEqual(
            {
                owner_id: snapshot["owner_id"]
                for owner_id, snapshot in snapshots.items()
            },
            {owner_id: owner_id for owner_id in process_ids},
        )

    def test_method_client_object_graph_has_no_world_or_callable_closure(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            client = session.client
            self.assertFalse(hasattr(client, "_scenario"))
            self.assertFalse(hasattr(client, "_world"))
            self.assertFalse(hasattr(client, "_OwnerClient__call"))
            for slot in OwnerClient.__slots__:
                value = getattr(client, slot)
                self.assertFalse(callable(value), slot)
                if isinstance(value, dict):
                    self.assertFalse(
                        any(callable(item) for item in value.values()),
                        slot,
                    )

        for _name, member in inspect.getmembers(
            OwnerClient, predicate=inspect.isfunction
        ):
            closure = inspect.getclosurevars(member)
            self.assertEqual(closure.nonlocals, {})


class ByteTransportAndAcceptanceAttacks(unittest.TestCase):
    def test_owner_rpc_returns_only_canonical_response_bytes(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            response = session.client.authority("op-platform")
            receipt = session.client.trace[-1]
            verified = session.client.consume_response(
                response,
                owner_id="O_S",
                endpoint="authority",
            )
        self.assertIsInstance(response, bytes)
        self.assertEqual(response, receipt.response_bytes.encode("utf-8"))
        self.assertIsInstance(verified.payload, dict)

    def test_exact_o_q_response_bytes_transplanted_to_o_v_are_rejected(self):
        class ReplayOQAtOV:
            def __init__(self, inner):
                self.inner = inner
                self.requester_bytes = None

            @property
            def trace(self):
                return self.inner.trace

            def acceptance(
                self,
                effect,
                owner_id,
                episode_id,
                q_version,
            ):
                if owner_id == "O_Q":
                    self.requester_bytes = self.inner.acceptance(
                        effect, owner_id, episode_id, q_version
                    )
                    return self.requester_bytes
                return self.requester_bytes

            def __getattr__(self, name):
                return getattr(self.inner, name)

        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            result = G6Method().run(
                world.plan,
                ReplayOQAtOV(session.client),
            )
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])

    def test_wire_owner_binding_rejects_o_q_bytes_as_o_v(self):
        world = build_world("E0-PLATFORM-DIRECT")
        with start_owner_session(world) as session:
            effect = {
                "occurrence_id": "synthetic-effect",
                "owner_id": "O_E",
                "domain": "TARGET_NATIVE",
                "object_id": "Circuit-C7",
                "occurred_at": 101,
            }
            requester_bytes = session.client.acceptance(
                effect,
                "O_Q",
                world.plan.episode.episode_id,
                world.plan.episode.q_version,
            )
        with self.assertRaises(WireProtocolError):
            read_response(
                requester_bytes,
                expected_owner="O_V",
                expected_endpoint="acceptance",
            )

    def test_duplicate_acceptance_act_id_cannot_close(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.query.response_overrides["acceptance"] = _acceptance(
            "O_Q", act_id="act:duplicate", process_id=901
        )
        world.venue.response_overrides["acceptance"] = _acceptance(
            "O_V", act_id="act:duplicate", process_id=902
        )
        result, _snapshots, _trace, _process_ids = _run(world)
        self.assertEqual(result.resolution, "EFFECT_WITHOUT_ACCEPTANCE")
        self.assertEqual(result.settlements, [])

    def test_duplicate_acceptance_process_cannot_close(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.query.response_overrides["acceptance"] = _acceptance(
            "O_Q", act_id="act:q", process_id=999
        )
        world.venue.response_overrides["acceptance"] = _acceptance(
            "O_V", act_id="act:v", process_id=999
        )
        result, _snapshots, _trace, _process_ids = _run(world)
        self.assertEqual(result.resolution, "EFFECT_WITHOUT_ACCEPTANCE")
        self.assertEqual(result.settlements, [])

    def test_acceptance_payload_process_must_match_transport_process(self):
        """Distinct invented PIDs must not substitute for transport provenance."""

        world = build_world("E0-PLATFORM-DIRECT")
        world.query.response_overrides["acceptance"] = _acceptance(
            "O_Q", act_id="act:q:spoofed", process_id=2_000_000_001
        )
        world.venue.response_overrides["acceptance"] = _acceptance(
            "O_V", act_id="act:v:spoofed", process_id=2_000_000_002
        )
        result, _snapshots, _trace, process_ids = _run(world)
        self.assertNotIn(2_000_000_001, process_ids.values())
        self.assertNotIn(2_000_000_002, process_ids.values())
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertEqual(result.settlements, [])


class SettlementRecoveryAndGraderAttacks(unittest.TestCase):
    def test_non_o_p_obligation_cannot_become_final(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.payment.response_overrides["open_settlement"] = Obligation(
            obligation_id="obl:provider-self-report",
            owner_id="O_R",
            effect_id="occ:E0-PLATFORM-DIRECT:op-platform",
            scheme="CE_PAY_V1",
            debtor="requester",
            beneficiary="resource-provider",
            required_phases=("PAYOUT",),
            reversal_phases=("REVERSAL",),
            finality_horizon=105,
        )
        result, _snapshots, _trace, _process_ids = _run(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertFalse(any(item.discharged for item in result.settlements))

    def test_forged_o_p_finality_cannot_override_reversal(self):
        world = build_world("E0-PLATFORM-DIRECT")
        world.payment.reversal = True
        world.payment.force_finality = "FINAL"
        result, _snapshots, _trace, _process_ids = _run(world)
        self.assertNotEqual(result.resolution, "EXACT_EFFECT_ACCEPTED_SETTLED")
        self.assertFalse(any(item.discharged for item in result.settlements))

    def test_forged_no_mutation_recovery_and_readback_cannot_close(self):
        world = build_world("E3B-ACK-LOST-NO-EFFECT")
        world.effect.recovery_mode = "FORGED_NO_MUTATION"
        result, snapshots, trace, _process_ids = _run(world)
        endpoints = [item.endpoint for item in trace]
        self.assertIn("recovery_state", endpoints)
        self.assertIn("target_state", endpoints)
        self.assertEqual(result.resolution, "RECOVERY_UNKNOWN")
        self.assertNotIn("op-e3-fallback", [
            item.request.get("operation_id")
            for item in trace
            if item.endpoint == "execute"
        ])
        target = snapshots["O_E"]["state"]["targets"]["Circuit-C8"]
        self.assertEqual(target["state"], "POWERED")
        self.assertEqual(target["version"], 1)
        self.assertEqual(
            target["last_occurrence_id"],
            "occ:E3-ACK-LOST-OPAQUE:op-e3-primary",
        )

    def test_owner_payloads_contain_no_grader_truth(self):
        world = build_world("E0-PLATFORM-DIRECT")
        _result, snapshots, trace, _process_ids = _run(world)
        encoded = json.dumps(
            {
                "snapshots": snapshots,
                "trace": [item.as_dict() for item in trace],
            },
            ensure_ascii=False,
            sort_keys=True,
        ).lower()
        for forbidden in (
            "expected_resolution",
            "grader-input",
            "frozen_grader",
            "correct_resolution",
            "g6_line_local_closure",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_contract_exact_task_success_is_not_a_g6_boolean(self):
        world = build_world("E0-PLATFORM-DIRECT")
        result, _snapshots, _trace, _process_ids = _run(world)
        evaluation = evaluate(
            result,
            "E0-PLATFORM-DIRECT",
            load_frozen_grader(),
            expected_plan_sha256=result.plan_sha256,
        )
        self.assertNotIn("exact_task_success", evaluation)
        self.assertIsInstance(evaluation["g6_line_local_closure"], bool)
        self.assertEqual(
            evaluation["contract_exact_task_success"],
            "NOT_COMPUTED_BY_G6",
        )
        self.assertNotIsInstance(
            evaluation["contract_exact_task_success"],
            bool,
        )
        self.assertEqual(
            {
                key: evaluation["g6_line_local_components"][key]
                for key in (
                    "deadline",
                    "continuous_duration",
                    "full_safety_constraints",
                )
            },
            {
                "deadline": "UNKNOWN",
                "continuous_duration": "UNKNOWN",
                "full_safety_constraints": "UNKNOWN",
            },
        )
        self.assertEqual(
            [
                key for key in evaluation
                if key.startswith("contract_")
            ],
            ["contract_exact_task_success"],
        )


if __name__ == "__main__":
    unittest.main()
