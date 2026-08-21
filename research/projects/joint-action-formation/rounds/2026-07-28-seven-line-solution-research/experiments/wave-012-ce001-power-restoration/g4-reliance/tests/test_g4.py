from __future__ import annotations

import base64
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from module import (  # noqa: E402
    OwnerTargetService,
    canonical,
    canonical_bytes,
    digest_bytes,
    explicit_object_adapter,
)
from runner import (  # noqa: E402
    HOLDOUT,
    WORKER,
    compact,
    evaluate,
    load_inputs,
)


class CE001G4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public, cls.holdout = load_inputs()
        cls.report = evaluate()
        cls.evidence = cls.report["evidence"]
        cls.rows = {
            row["case_ref"]: row for row in cls.evidence["cases"]
        }

    def case(self, case_ref: str) -> dict:
        return copy.deepcopy(
            next(
                case
                for case in self.holdout["cases"]
                if case["case_ref"] == case_ref
            )
        )

    def drive_target(
        self,
        service: OwnerTargetService,
        reconcile: bool = True,
    ) -> tuple[dict, dict, dict | None]:
        bound = service._bound()
        reserve = service.call("reserve", bound)
        commit = service.call("read_commit_evidence", bound)
        attempt = {
            **bound,
            "reservation_id": reserve["reservation_id"],
            "fence_epoch": reserve["fence_epoch"],
            "commit_revisions": {
                record["issuer"]: record["revision"]
                for record in commit["owner_records"]
            },
        }
        service.call("submit_operation", attempt)
        exact = service.call("reconcile_operation", bound) if reconcile else None
        return bound, attempt, exact

    def request_both(self, service: OwnerTargetService) -> list[dict]:
        assert service.target_record is not None
        args = {
            **service._bound(),
            "effect_occurrence_id": service.target_record[
                "effect_occurrence_id"
            ],
            "effect_revision": service.target_record["effect_revision"],
        }
        return [
            service.call("request_q_acceptance", args),
            service.call("request_venue_acceptance", args),
        ]

    # The original 19 risk checks remain, upgraded to the new process/signature
    # and line-local output boundary.

    def test_01_worker_gets_blind_interface_not_private_case_or_label(self) -> None:
        blind = self.evidence["blind_holdout"]
        self.assertTrue(blind["holdout_unchanged"])
        self.assertEqual(
            blind["worker_start_fields"],
            ["available_actions", "episode", "type"],
        )
        self.assertFalse(blind["expected_label_table_exists"])
        source = WORKER.read_text(encoding="utf-8")
        self.assertNotIn("private_holdout", source)
        for case in self.holdout["cases"]:
            self.assertNotIn(case["case_ref"], source)

    def test_02_p0_interaction_p1_attempt_order_is_enforced(self) -> None:
        for row in self.rows.values():
            phases = row["phase_trace"]
            self.assertLess(phases.index("P0"), phases.index("INTERACTION"))
            self.assertLess(phases.index("INTERACTION"), phases.index("P1"))
            self.assertLess(phases.index("P1"), phases.index("RESERVATION"))
            self.assertLess(
                phases.index("RESERVATION"), phases.index("COMMIT_EVIDENCE")
            )
            if "ATTEMPT" in phases:
                self.assertLess(
                    phases.index("COMMIT_EVIDENCE"), phases.index("ATTEMPT")
                )
            if "OWNER_ACT" in phases:
                self.assertLess(
                    phases.index("RECONCILIATION"),
                    phases.index("OWNER_ACT"),
                )

    def test_03_commit_and_reservation_bind_canonical_operation(self) -> None:
        row = self.rows["E3A-ACK-LOST-EFFECT"]
        reserve = next(
            event["raw_response"]
            for event in row["raw_trace"]
            if event["action"] == "reserve"
        )
        commit = next(
            event["raw_response"]
            for event in row["raw_trace"]
            if event["action"] == "read_commit_evidence"
        )
        for record in [reserve, *commit["owner_records"]]:
            self.assertEqual(
                record["object_id"], "VenueV:CircuitC7"
            )
            self.assertEqual(
                record["Q_version"], self.public["episode"]["Q_version"]
            )
            self.assertEqual(
                record["operation_id"],
                self.public["episode"]["operation_id"],
            )
        self.assertEqual(reserve["reservation_status"], "RESERVED")

    def test_04_expired_reservation_and_commit_block_target_change(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            bound = service._bound()
            reserve = service.call("reserve", bound)
            commit = service.call("read_commit_evidence", bound)
            for _ in range(70):
                service.call("inspect_interfaces", bound)
            service.call(
                "submit_operation",
                {
                    **bound,
                    "reservation_id": reserve["reservation_id"],
                    "fence_epoch": reserve["fence_epoch"],
                    "commit_revisions": {
                        record["issuer"]: record["revision"]
                        for record in commit["owner_records"]
                    },
                },
            )
            self.assertGreater(service.tick, reserve["expires_tick"])
            self.assertEqual(service.occurrence_count, 0)
            self.assertEqual(service.target_delivery_count, 0)

    def test_05_e3_ack_loss_pair_reconciles_by_exact_readback(self) -> None:
        left = self.rows["E3A-ACK-LOST-EFFECT"]
        right = self.rows["E3B-ACK-LOST-NO-EFFECT"]
        self.assertIsNone(left["submit_responses"][0])
        self.assertIsNone(right["submit_responses"][0])
        self.assertTrue(
            left["observations"]["attempt"]["first_attempt_target_record"]
        )
        self.assertFalse(
            right["observations"]["attempt"]["first_attempt_target_record"]
        )
        self.assertEqual(left["observations"]["attempt"]["count"], 1)
        self.assertEqual(right["observations"]["attempt"]["count"], 2)
        for row in (left, right):
            self.assertTrue(
                row["observations"]["reconciliation"]["terminal_observed"]
            )
            self.assertEqual(
                row["observations"]["attempt"]["target_occurrence_count"], 1
            )
            self.assertFalse(
                row["observations"]["readback"][
                    "wrong_object_without_exact_followup"
                ]
            )

    def test_06_wrong_object_judgment_ignores_worker_self_report(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            wrong = service.call("readback_operation", service._bound())
            self.assertNotEqual(wrong["object_id"], service._bound()["object_id"])
            lied = service.observations({"wrong_object_rejected": True})
            self.assertTrue(
                lied["readback"]["wrong_object_without_exact_followup"]
            )
            service.call("reconcile_operation", service._bound())
            contradicted = service.observations(
                {"wrong_object_rejected": False}
            )
            self.assertFalse(
                contradicted["readback"][
                    "wrong_object_without_exact_followup"
                ]
            )

    def test_07_passive_active_full_quantifiers_remain_distinct(self) -> None:
        audit = self.evidence["ack_pair_audit"]
        self.assertTrue(audit["passive"]["initial_packet_equivalent"])
        self.assertTrue(audit["active"]["pre_attempt_isomorphic"])
        self.assertTrue(audit["active"]["distinguishing_witness_exists"])
        self.assertFalse(
            audit["full_interaction"]["interaction_equivalent"]
        )
        self.assertEqual(audit["full_interaction"]["plans_enumerated"], 7)

    def test_08_double_submit_delivery_is_idempotent(self) -> None:
        row = self.rows["PRESSURE-DOUBLE-SUBMIT"]["observations"]["attempt"]
        self.assertEqual(row["target_delivery_count"], 2)
        self.assertEqual(row["target_occurrence_count"], 1)
        self.assertFalse(row["duplicate_target_occurrence"])
        self.assertEqual(row["concurrent_barrier_parties"], 2)

    def test_09_revoke_blocks_attempt_and_target_change(self) -> None:
        row = self.rows["PRESSURE-REVOKE-AFTER-RESERVE"]
        self.assertEqual(row["observations"]["attempt"]["count"], 0)
        self.assertEqual(
            row["observations"]["attempt"]["target_occurrence_count"], 0
        )
        self.assertTrue(
            row["observations"]["reconciliation"]["terminal_observed"]
        )
        commit = next(
            event["raw_response"]
            for event in row["raw_trace"]
            if event["action"] == "read_commit_evidence"
        )
        self.assertIn(
            "REVOKED",
            {record["owner_decision"] for record in commit["owner_records"]},
        )

    def test_10_calibration_is_separate_and_twin_claim_is_narrow(self) -> None:
        scores = self.evidence["scores"]
        self.assertEqual(
            set(scores),
            {"reliance_calibration", "attempt_readback_evidence"},
        )
        attempt = scores["attempt_readback_evidence"]
        self.assertEqual(
            attempt["eligible_target_record_coverage"],
            {"numerator": 9, "denominator": 9},
        )
        self.assertEqual(
            attempt["matched_no_interaction_target_occurrences"], 0
        )
        self.assertEqual(
            attempt["causal_status"],
            "LOCAL_STATE_MACHINE_NECESSARY_CONDITION_ONLY",
        )
        self.assertNotIn("advantage", set(attempt))
        self.assertIn(
            "not a method advantage",
            attempt["necessary_precondition_observation"],
        )

    def test_11_target_record_does_not_imply_owner_act_closure(self) -> None:
        obs = self.rows["PRESSURE-DOUBLE-SUBMIT"]["observations"]
        self.assertEqual(obs["attempt"]["target_occurrence_count"], 1)
        self.assertFalse(obs["owner_act_closure"]["closed"])

    def test_12_target_actor_never_issues_owner_acts(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            bindings = service.trust_bindings()
            self.assertEqual(service.owner_act_records, [])
            self.assertNotEqual(
                bindings["O_E"]["act_source_id"],
                bindings["O_Q"]["act_source_id"],
            )
            self.assertEqual(service._actors["O_Q"].signed_response_count, 0)
            self.assertEqual(service._actors["O_V"].signed_response_count, 0)

    def test_13_closure_requires_two_independent_signed_owner_acts(self) -> None:
        for case_ref in (
            "E3A-ACK-LOST-EFFECT",
            "E3B-ACK-LOST-NO-EFFECT",
        ):
            with self.subTest(case_ref=case_ref):
                closure = self.rows[case_ref]["observations"][
                    "owner_act_closure"
                ]
                self.assertTrue(closure["closed"])
                self.assertEqual(closure["record_count"], 2)
                self.assertEqual(
                    set(closure["issuers"]), {"O_Q", "O_V"}
                )
                self.assertEqual(closure["failures"], [])
                bindings = self.rows[case_ref]["observations"][
                    "source_process_evidence"
                ]
                for field in (
                    "actual_child_pid",
                    "process_instance_id",
                    "service_id",
                    "state_source_id",
                    "act_source_id",
                    "public_key_b64",
                ):
                    self.assertEqual(
                        len({bindings["O_Q"][field], bindings["O_V"][field]}),
                        2,
                    )

    def test_14_signature_binds_complete_transmitted_act_bytes(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            self.request_both(service)
            original = service.owner_act_records[1]
            actor = service._actors["O_V"]
            self.assertEqual(
                actor.verify_envelope(original["envelope"]),
                original["payload"],
            )
            for field, replacement in {
                "decision": "REFUSE",
                "episode_id": "WRONG",
                "Q_version": "Q@wrong",
                "object_id": "VenueV:CircuitC9",
                "effect_occurrence_id": "wrong-occurrence",
                "owner_revision": actor.current_revision + 1,
            }.items():
                with self.subTest(field=field):
                    tampered = copy.deepcopy(original["envelope"])
                    payload = copy.deepcopy(original["payload"])
                    payload[field] = replacement
                    payload_bytes = canonical_bytes(payload)
                    tampered["payload_b64"] = base64.b64encode(
                        payload_bytes
                    ).decode("ascii")
                    tampered["payload_sha256"] = digest_bytes(payload_bytes)
                    with self.assertRaises(ValueError):
                        actor.verify_envelope(tampered)

    def test_15_owner_act_mutations_do_not_close(self) -> None:
        expected = {
            "PRESSURE-DOUBLE-SUBMIT": "O_V:NOT_ACCEPT",
            "ACCEPTANCE-WRONG-EPISODE": "O_V:WRONG_EPISODE_ID",
            "ACCEPTANCE-WRONG-Q": "O_V:WRONG_Q_VERSION",
            "ACCEPTANCE-WRONG-EFFECT": "O_V:WRONG_EFFECT_OCCURRENCE_ID",
            "ACCEPTANCE-STALE-OWNER-REVISION": "O_V:STALE_OWNER_REVISION",
            "ACCEPTANCE-DUPLICATED-OWNER": "DUPLICATE_ISSUER",
        }
        for case_ref, failure in expected.items():
            with self.subTest(case_ref=case_ref):
                closure = self.rows[case_ref]["observations"][
                    "owner_act_closure"
                ]
                self.assertFalse(closure["closed"])
                self.assertIn(failure, closure["failures"])

    def test_16_duplicate_required_owner_declaration_cannot_close(self) -> None:
        episode = copy.deepcopy(self.public["episode"])
        episode["acceptance_owners"] = ["O_Q", "O_Q"]
        with OwnerTargetService(
            episode, self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            self.request_both(service)
            closure = service.observations({})["owner_act_closure"]
            self.assertFalse(closure["closed"])
            self.assertIn(
                "INVALID_REQUIRED_OWNER_DECLARATION",
                closure["failures"],
            )

    def test_17_p1_terminal_reconciliation_has_real_negative(self) -> None:
        truths = {
            row["truth"]["P1"]["terminal_reconciliation"]
            for row in self.rows.values()
        }
        self.assertEqual(truths, {False, True})
        row = self.rows["RESOLUTION-NONTERMINAL-READBACK"]
        self.assertEqual(
            row["observations"]["reconciliation"]["final_state"], "PENDING"
        )
        self.assertFalse(
            row["observations"]["reconciliation"]["terminal_observed"]
        )
        self.assertEqual(
            row["observations"]["attempt"]["target_occurrence_count"], 1
        )
        p1 = self.evidence["scores"]["reliance_calibration"]["P1"][
            "terminal_reconciliation"
        ]
        self.assertEqual((p1["TP"], p1["FP"]), (9, 1))

    def test_18_failure_injection_counts_come_from_observed_traces(self) -> None:
        counts = self.evidence["failure_injections"]
        self.assertEqual(counts["DROP_SUBMIT_ACK@target-record"], 8)
        self.assertEqual(counts["DROP_SUBMIT_ACK@no-record"], 1)
        self.assertEqual(counts["WRONG_OBJECT_READBACK"], 9)
        self.assertEqual(counts["CONCURRENT_DOUBLE_DELIVERY"], 1)
        self.assertEqual(
            counts["REVOKE_AFTER_RESERVATION_BEFORE_COMMIT"], 1
        )
        for key in (
            "OWNER_REFUSAL_AFTER_TARGET_RECORD",
            "OWNER_ACT_WRONG_EPISODE",
            "OWNER_ACT_WRONG_Q",
            "OWNER_ACT_WRONG_OCCURRENCE",
            "OWNER_ACT_STALE_REVISION",
            "OWNER_ACT_DUPLICATED_ISSUER",
            "NONTERMINAL_EXACT_READBACK",
        ):
            self.assertEqual(counts[key], 1)

    def test_19_private_holdout_bytes_are_not_mutated(self) -> None:
        before = canonical(json.loads(HOLDOUT.read_text(encoding="utf-8")))
        evaluate()
        after = canonical(json.loads(HOLDOUT.read_text(encoding="utf-8")))
        self.assertEqual(before, after)

    # Third-round root mutations.

    def test_20_actual_child_pid_process_and_sources_are_distinct(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            bindings = service.trust_bindings()
            for binding in bindings.values():
                self.assertEqual(
                    binding["actual_child_pid"], binding["reported_pid"]
                )
                self.assertIsNone(
                    service._actors[binding["role"]].process.poll()
                )
            for field in (
                "actual_child_pid",
                "process_instance_id",
                "service_id",
                "state_source_id",
                "act_source_id",
            ):
                self.assertEqual(
                    len({item[field] for item in bindings.values()}), 3
                )

    def test_21_duplicate_service_id_signed_mutation_cannot_close(self) -> None:
        case = self.case("E3A-ACK-LOST-EFFECT")
        case["acceptance_mutation"] = "O_V_DUPLICATE_SERVICE"
        with OwnerTargetService(self.public["episode"], case) as service:
            self.drive_target(service)
            self.request_both(service)
            closure = service.observations({})["owner_act_closure"]
            self.assertFalse(closure["closed"])
            self.assertIn(
                "O_V:SERVICE_ID_BINDING_MISMATCH", closure["failures"]
            )

    def test_22_duplicate_pid_process_state_or_act_source_cannot_close(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            self.request_both(service)
            q = service.owner_act_records[0]["payload"]
            v = service.owner_act_records[1]
            replacements = {
                "reported_pid": q["reported_pid"],
                "process_instance_id": q["process_instance_id"],
                "state_source_id": q["state_source_id"],
                "act_source_id": q["act_source_id"],
            }
            original = copy.deepcopy(v["payload"])
            for field, replacement in replacements.items():
                with self.subTest(field=field):
                    v["payload"] = copy.deepcopy(original)
                    v["payload"][field] = replacement
                    closure = service.observations({})["owner_act_closure"]
                    self.assertFalse(closure["closed"])
            v["payload"] = original

    def test_23_public_digest_recompute_cannot_forge_owner_act(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            service._ensure_actors()
            for owner_id in ("O_Q", "O_V"):
                actor = service._actors[owner_id]
                payload = {
                    "kind": "OWNER_ACT",
                    **service._bound(),
                    "issuer": owner_id,
                    "decision": "ACCEPT",
                    "owner_revision": actor.current_revision,
                    "effect_occurrence_id": service.target_record[
                        "effect_occurrence_id"
                    ],
                    "effect_revision": 1,
                    "target_payload_sha256": service.target_envelope[
                        "payload_sha256"
                    ],
                    "reported_pid": actor.trust_binding["actual_child_pid"],
                    **{
                        field: actor.trust_binding[field]
                        for field in (
                            "service_id",
                            "state_source_id",
                            "act_source_id",
                            "process_instance_id",
                        )
                    },
                }
                payload_bytes = canonical_bytes(payload)
                envelope = {
                    "type": "SIGNED_TRANSMITTED_BYTES",
                    "public_key_b64": actor.public_key_b64,
                    "payload_b64": base64.b64encode(payload_bytes).decode(
                        "ascii"
                    ),
                    "payload_sha256": digest_bytes(payload_bytes),
                    "signature_b64": base64.b64encode(b"\x00" * 64).decode(
                        "ascii"
                    ),
                }
                service.owner_act_records.append(
                    {
                        "requested_owner": owner_id,
                        "envelope": envelope,
                        "payload": payload,
                        "request_sha256": digest_bytes(b"forged"),
                        "response_sha256": digest_bytes(
                            canonical_bytes(envelope)
                        ),
                    }
                )
            closure = service.observations({})["owner_act_closure"]
            self.assertFalse(closure["closed"])
            self.assertIn("O_Q:SIGNATURE_INVALID", closure["failures"])
            self.assertEqual(service._actors["O_Q"].request_count, 0)
            self.assertEqual(service._actors["O_V"].request_count, 0)

    def test_24_signature_replay_across_owner_pin_cannot_close(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            self.request_both(service)
            service.owner_act_records[1] = copy.deepcopy(
                service.owner_act_records[0]
            )
            service.owner_act_records[1]["requested_owner"] = "O_V"
            closure = service.observations({})["owner_act_closure"]
            self.assertFalse(closure["closed"])
            self.assertIn("O_V:SIGNATURE_INVALID", closure["failures"])

    def test_25_pending_reconciliation_never_requests_owner_act(self) -> None:
        with OwnerTargetService(
            self.public["episode"],
            self.case("RESOLUTION-NONTERMINAL-READBACK"),
        ) as service:
            _, _, exact = self.drive_target(service)
            self.assertEqual(exact["state"], "PENDING")
            responses = self.request_both(service)
            self.assertEqual(
                {response["status"] for response in responses},
                {"PRE_ACT_GATE_REJECTED"},
            )
            self.assertEqual(service._actors["O_Q"].request_count, 0)
            self.assertEqual(service._actors["O_V"].request_count, 0)

    def test_26_zero_power_never_requests_owner_act(self) -> None:
        self._assert_target_mutation_blocked(
            "O_E_ZERO_POWER", "TARGET_POWER_OUT_OF_RANGE"
        )

    def test_27_wrong_circuit_never_requests_owner_act(self) -> None:
        self._assert_target_mutation_blocked(
            "O_E_WRONG_CIRCUIT", "TARGET_WRONG_CIRCUIT"
        )

    def test_28_other_circuit_never_requests_owner_act(self) -> None:
        self._assert_target_mutation_blocked(
            "O_E_OTHER_CIRCUIT", "TARGET_OTHER_CIRCUIT_PRESENT"
        )

    def test_29_short_duration_never_requests_owner_act(self) -> None:
        self._assert_target_mutation_blocked(
            "O_E_SHORT_DURATION", "TARGET_DURATION_TOO_SHORT"
        )

    def test_30_deadline_miss_never_requests_owner_act(self) -> None:
        self._assert_target_mutation_blocked(
            "O_E_DEADLINE_MISS", "TARGET_DEADLINE_MISSED"
        )

    def _assert_target_mutation_blocked(
        self, mutation: str, expected_failure: str
    ) -> None:
        case = self.case("E3A-ACK-LOST-EFFECT")
        case["effect_mutation"] = mutation
        with OwnerTargetService(self.public["episode"], case) as service:
            self.drive_target(service)
            responses = self.request_both(service)
            self.assertEqual(
                {response["status"] for response in responses},
                {"PRE_ACT_GATE_REJECTED"},
            )
            for response in responses:
                self.assertIn(expected_failure, response["gate_failures"])
            self.assertEqual(service._actors["O_Q"].request_count, 0)
            self.assertEqual(service._actors["O_V"].request_count, 0)

    def test_31_wrong_oe_provenance_never_requests_owner_act(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            signature = service.target_envelope["signature_b64"]
            service.target_envelope["signature_b64"] = (
                ("A" if signature[0] != "A" else "B") + signature[1:]
            )
            responses = self.request_both(service)
            for response in responses:
                self.assertIn(
                    "O_E_PROVENANCE_INVALID", response["gate_failures"]
                )
            self.assertEqual(service._actors["O_Q"].request_count, 0)
            self.assertEqual(service._actors["O_V"].request_count, 0)

    def test_32_absent_exact_reconciliation_never_requests_owner_act(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service, reconcile=False)
            responses = self.request_both(service)
            for response in responses:
                self.assertIn(
                    "EXACT_RECONCILIATION_MISSING",
                    response["gate_failures"],
                )
            self.assertEqual(service._actors["O_Q"].request_count, 0)
            self.assertEqual(service._actors["O_V"].request_count, 0)

    def test_33_explicit_adapter_is_exact_and_fail_closed(self) -> None:
        adapter = explicit_object_adapter(self.public["episode"])
        self.assertEqual(
            adapter["canonical_object_id"], "VenueV:CircuitC7"
        )
        for field, wrong in {
            "object_id": "Venue-V/Circuit-C7",
            "native_object_id": "Venue-V/Circuit-C8",
        }.items():
            with self.subTest(field=field):
                episode = copy.deepcopy(self.public["episode"])
                episode[field] = wrong
                with self.assertRaises(ValueError):
                    explicit_object_adapter(episode)

    def test_34_g4_output_has_no_contract_level_field_passthrough(self) -> None:
        preflight = (
            HERE.parents[0] / "integration-preflight" / "preflight.py"
        )
        spec = importlib.util.spec_from_file_location(
            "integration_preflight_for_g4", preflight
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        forbidden = {
            item.replace("_", "").lower()
            for item in module.CONTRACT_LEVEL_FIELDS
        }
        forbidden.update({"independentowneracceptance", "contractcausaladvantage"})

        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key
                    yield from keys(child)
            elif isinstance(value, list):
                for child in value:
                    yield from keys(child)

        emitted = compact(self.report)
        normalized = {
            str(key).replace("_", "").lower() for key in keys(emitted)
        }
        self.assertEqual(forbidden & normalized, set())
        self.assertFalse(
            any(key.startswith("contract") for key in normalized)
        )
        fixture = json.loads(
            (
                HERE.parents[0]
                / "integration-preflight"
                / "fixtures"
                / "qualified-e1.json"
            ).read_text(encoding="utf-8")
        )
        fixture["components"]["G4"] = copy.deepcopy(emitted)
        report = module.validate_envelope(fixture)
        self.assertEqual(
            report["preflight_status"], "QUALIFIED_COMPONENT_OUTPUTS"
        )
        self.assertEqual(report["rejections"], [])

    def test_35_controller_consumes_only_child_transmitted_bytes(self) -> None:
        with OwnerTargetService(
            self.public["episode"], self.case("E3A-ACK-LOST-EFFECT")
        ) as service:
            self.drive_target(service)
            self.request_both(service)
            for actor in service._actors.values():
                directions = {
                    item["direction"] for item in actor.transmitted
                }
                self.assertIn("CHILD_TO_CONTROLLER", directions)
                if actor.role in {"O_Q", "O_V"}:
                    self.assertIn("CONTROLLER_TO_CHILD", directions)
                    self.assertGreater(actor.signed_response_count, 0)
            source = (HERE / "module.py").read_text(encoding="utf-8")
            self.assertNotIn("class AcceptanceOwnerService", source)


if __name__ == "__main__":
    unittest.main()
