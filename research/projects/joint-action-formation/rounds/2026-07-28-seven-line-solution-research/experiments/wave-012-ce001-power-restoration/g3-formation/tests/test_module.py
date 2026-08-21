from __future__ import annotations

import copy
import importlib.util
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from formation.canonical import sha256  # noqa: E402
from formation.runner import (  # noqa: E402
    E2_INTERVENTIONS,
    PRIVATE_TRUTH,
    PUBLIC_CASES,
    execute_one,
    load_json,
    run_experiment,
    score_one,
    worker_command,
    worker_environment,
)


class CE001G3FormationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.public_document = load_json(PUBLIC_CASES)
        cls.private_document = load_json(PRIVATE_TRUTH)
        cls.public_cases = {
            cls.private_document["manifest"][item["case_handle"]]: {
                **item,
                "task": copy.deepcopy(cls.public_document["task"]),
                "owner_endpoint_verification_key": cls.public_document[
                    "owner_endpoint_verification_key"
                ],
            }
            for item in cls.public_document["cases"]
        }
        cls.report = run_experiment(write_outputs=True)
        cls.results = {
            (
                cls.private_document["manifest"][
                    item["body"]["case_handle"]
                ],
                item["body"]["T"],
            ): item
            for item in cls.report["body"]["line_evidence"]
        }

    def baseline(self, case_id: str) -> dict:
        return self.results[(case_id, "INVARIANT")]["body"]

    def test_public_packet_has_no_answer_or_operator_proposal(self) -> None:
        public_text = PUBLIC_CASES.read_text(encoding="utf-8")
        for forbidden in (
            "expected_label",
            "expected_category",
            "operator_proposal",
            "expected_path_class",
            "private_truth",
            "purpose_token",
            "delegation_id",
            "OP-TRANSFER-V2",
            "E2-CONDITION-FORMATION",
            "E4-REVOKE-WITH-ALTERNATIVE",
            "G3-OPEN-INVENTORY-CONTROL",
            "G3-MODEL-KERNEL-CHANGE-CONTROL",
        ):
            self.assertNotIn(forbidden, public_text)
        self.assertEqual(
            {item["case_handle"] for item in self.public_document["cases"]},
            {f"H{index:03d}" for index in range(1, 11)},
        )

    def test_is_single_line_module_not_aliased_arm_comparison(self) -> None:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "formation").glob("*.py")
        )
        self.assertNotIn("choose(packet)", source)
        self.assertNotIn("_common_candidate", source)
        self.assertFalse(
            self.report["body"]["separation"]["arm_comparison_implemented"]
        )

    def test_direct_and_old_full_policy_paths_are_distinct(self) -> None:
        e0 = self.baseline("E0-PLATFORM-DIRECT")
        e1 = self.baseline("E1-EXTANT-MULTI-OWNER")
        self.assertEqual(e0["path_class"], "DIRECT_PATH")
        self.assertEqual(e1["path_class"], "OLD_FULL_POLICY_CLOSURE")
        self.assertEqual((e0["C"], e1["C"]), ("SAT", "SAT"))
        self.assertEqual((e0["N"], e1["N"]), ("NONE", "EXTANT_ACTIVATED"))

    def test_e2_forms_purpose_token_and_delegation_by_owner_interaction(self) -> None:
        case_id = "E2-CONDITION-FORMATION"
        public_case = self.public_cases[case_id]
        truth = self.private_document["cases"][case_id]
        run = execute_one(public_case, truth)
        formed = [
            item
            for item in run.trace
            if item["type"] == "PURPOSE_TOKEN_DELEGATION_FORMED"
        ]
        self.assertEqual(len(formed), 1)
        formed_seq = formed[0]["seq"]
        proposals = [
            item
            for item in run.trace
            if item["type"] == "FORMATION_PROPOSAL_CREATED"
        ]
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]["proposal"]
        self.assertEqual(proposal["task_sha256"], sha256(public_case["task"]))
        self.assertEqual(proposal["resource_id"], "GEN-R2")
        self.assertEqual(proposal["recipient_owner_id"], "O_V")
        self.assertEqual(proposal["expiry"], "T0+90min")
        self.assertIn("cost", proposal)
        self.assertTrue(proposal["nonce"])
        self.assertTrue(
            any(
                item["type"] == "OWNER_INTERACTION"
                and item["event"]["phase"] == "sign"
                and item["seq"] < formed_seq
                for item in run.trace
            )
        )
        self.assertEqual(run.frozen_s0["world_state"]["purpose_tokens"], [])
        self.assertEqual(run.frozen_s0["world_state"]["delegations"], [])
        body = self.baseline(case_id)
        self.assertEqual(
            (body["C"], body["N"], body["E"], body["T"], body["V"]),
            ("SAT", "NEW_TOKEN", "SAME", "INVARIANT", "VALID"),
        )
        self.assertEqual(body["path_class"], "OLD_FULL_POLICY_NEW_TOKEN")

    def test_e2_remove_and_reverse_all_replay_exact_s0(self) -> None:
        body = self.baseline("E2-CONDITION-FORMATION")
        receipts = body["intervention_trace"]["runs"]
        self.assertEqual(
            {item["intervention"] for item in receipts},
            set(E2_INTERVENTIONS),
        )
        self.assertTrue(all(item["exact_s0_replay"] for item in receipts))
        self.assertTrue(
            all(not item["frozen_coordinate_observed"] for item in receipts)
        )
        removal = next(
            item
            for item in receipts
            if item["intervention"] == "REMOVE_FORMATION_OPERATOR"
        )
        self.assertTrue(removal["formation_action_actually_removed"])
        registry_observation = removal["closed_registry_observation"]
        self.assertEqual(
            registry_observation["matching_action_operator_ids"], []
        )
        for key in (
            "proposal_count",
            "sign_request_count",
            "token_formed_count",
            "target_submit_count",
        ):
            self.assertEqual(registry_observation[key], 0)
        source = (ROOT / "formation" / "execution_service.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            source.count('self.owner.owner_event("sign"'), 1
        )
        public_case = self.public_cases["E2-CONDITION-FORMATION"]
        truth = self.private_document["cases"]["E2-CONDITION-FORMATION"]
        removal_run = execute_one(
            public_case, truth, "REMOVE_FORMATION_OPERATOR"
        )
        self.assertIn(
            "REQUEST_PURPOSE_DELEGATION",
            removal_run.frozen_s0["kernel_actions"],
        )
        self.assertNotIn(
            "REQUEST_PURPOSE_DELEGATION",
            removal_run.final_state["executable_kernel"],
        )
        self.assertFalse(
            any(
                item["type"] == "OWNER_INTERACTION"
                and item["event"]["phase"] == "sign"
                for item in removal_run.trace
            )
        )
        inventory = next(
            item
            for item in removal_run.trace
            if item["type"] == "OPERATOR_INVENTORY_OBSERVATION"
        )
        self.assertEqual(inventory["executable_operator_ids"], [])
        self.assertFalse(
            any(
                item.get("action_kind")
                == "FORM_PURPOSE_TOKEN_AND_DELEGATION"
                and item.get("executable")
                for item in removal_run.final_state[
                    "executable_operator_registry"
                ]
            )
        )
        self.assertTrue(
            body["intervention_trace"][
                "removal_blocks_bounded_witness"
            ]
        )
        self.assertEqual(body["reachability"]["robust"], "UNKNOWN")

    def test_e4_recovers_from_revocation_to_exact_task_value(self) -> None:
        case_id = "E4-REVOKE-WITH-ALTERNATIVE"
        run = execute_one(
            self.public_cases[case_id],
            self.private_document["cases"][case_id],
        )
        revoked = [
            item for item in run.trace if item["type"] == "RESERVATION_REVOKED"
        ]
        self.assertEqual(
            [item["resource_id"] for item in revoked],
            ["BAT-R1-REVOKED"],
        )
        self.assertTrue(
            any(
                item["type"] == "RECOVERY_REDISCOVERY_QUERY"
                for item in run.trace
            )
        )
        initial_read = next(
            item["event"]
            for item in run.trace
            if item["type"] == "OWNER_INTERACTION"
            and item["event"]["phase"] == "read"
        )
        self.assertEqual(
            [item["resource_id"] for item in initial_read["resources"]],
            ["BAT-R1-REVOKED"],
        )
        self.assertEqual(run.final_state["selected_resource"], "GEN-R3-ALT")
        self.assertEqual(
            {item["owner_id"] for item in run.final_state["acceptances"]},
            {"O_Q", "O_V"},
        )
        body = self.baseline(case_id)
        self.assertTrue(
            body["post_revoke_observation"][
                "trace_complete_for_frozen_coordinates"
            ]
        )
        self.assertTrue(
            body["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertEqual(body["reachability"]["robust"], "UNKNOWN")

    def test_open_inventory_is_unknown_not_bounded_unsat(self) -> None:
        body = self.baseline("G3-OPEN-INVENTORY-CONTROL")
        self.assertEqual(body["C"], "UNKNOWN")
        self.assertEqual(body["path_class"], "OPEN_INVENTORY_UNKNOWN")
        self.assertEqual(body["reachability"]["physical"], "UNKNOWN")
        self.assertEqual(body["reachability"]["measurable"], "UNKNOWN")
        self.assertEqual(body["reachability"]["robust"], "UNKNOWN")

    def test_model_kernel_change_is_not_old_closure_or_task_change(self) -> None:
        body = self.baseline("G3-MODEL-KERNEL-CHANGE-CONTROL")
        self.assertEqual(
            (body["C"], body["N"], body["E"], body["T"], body["V"]),
            ("UNSAT", "NEW_TOKEN", "CHANGED", "INVARIANT", "VALID"),
        )
        self.assertEqual(body["path_class"], "MODEL_KERNEL_CHANGE")
        self.assertTrue(
            body["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )

    def test_controller_task_change_is_invalid_substitution(self) -> None:
        body = self.results[
            ("E2-CONDITION-FORMATION", "CONTROLLER_SUBSTITUTION")
        ]["body"]
        self.assertEqual(body["path_class"], "TASK_CHANGE")
        self.assertEqual(body["V"], "INVALID")
        self.assertFalse(
            body["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertEqual(body["reachability"]["actual"], "FALSE")
        self.assertNotEqual(
            body["bindings"]["result_task_sha256"],
            body["bindings"]["frozen_task_sha256"],
        )

    def test_every_result_returns_cnetv_and_native_reachability_axes(self) -> None:
        for receipt in self.report["body"]["line_evidence"]:
            body = receipt["body"]
            self.assertEqual(
                set(("C", "N", "E", "T", "V")).difference(body),
                set(),
            )
            self.assertEqual(
                set(body["reachability"]),
                {
                    "physical",
                    "measurable",
                    "actual",
                    "robust",
                    "robust_summary_semantics",
                },
            )
            self.assertEqual(
                set(body["R"]),
                {
                    "R_physical_exists",
                    "R_measurable_exists",
                    "R_actual",
                    "R_branch_robust",
                    "R_safety_robust",
                    "R_terminal_robust",
                },
            )
            for value in body["R"].values():
                self.assertIn(value, {"TRUE", "FALSE", "UNKNOWN"})
            self.assertEqual(
                {
                    body["R"]["R_branch_robust"],
                    body["R"]["R_safety_robust"],
                    body["R"]["R_terminal_robust"],
                },
                {"UNKNOWN"},
            )
            self.assertEqual(
                body["robust_denominator"]["status"],
                "UNKNOWN_UNFROZEN_COMPLETE_RESPONSE_TREE",
            )
            self.assertEqual(receipt["body_sha256"], sha256(body))

    def test_measurable_is_independent_of_actual_effect(self) -> None:
        case_id = "E1-EXTANT-MULTI-OWNER"
        public_case = self.public_cases[case_id]
        truth = self.private_document["cases"][case_id]
        run = execute_one(public_case, truth)
        run.final_state["effect"] = None
        receipt = score_one(public_case, truth, case_id, run)
        self.assertEqual(receipt["body"]["R"]["R_measurable_exists"], "TRUE")
        self.assertEqual(receipt["body"]["R"]["R_actual"], "FALSE")

    def test_wrong_object_effect_is_not_valid_success(self) -> None:
        case_id = "E1-EXTANT-MULTI-OWNER"
        public_case = self.public_cases[case_id]
        truth = self.private_document["cases"][case_id]
        run = execute_one(public_case, truth)
        run.final_state["effect"]["circuit_id"] = "C8"
        receipt = score_one(public_case, truth, case_id, run)
        self.assertEqual(receipt["body"]["V"], "INVALID")
        self.assertFalse(
            receipt["body"]["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )

    def test_e2_receipt_rejects_scope_signer_stale_and_tamper(self) -> None:
        case_id = "E2-CONDITION-FORMATION"
        public_case = self.public_cases[case_id]
        truth = self.private_document["cases"][case_id]
        mutations = {}

        wrong_scope = execute_one(public_case, truth)
        formed = next(
            item
            for item in wrong_scope.trace
            if item["type"] == "PURPOSE_TOKEN_DELEGATION_FORMED"
        )
        formed["delegation"]["scope"]["circuit_id"] = "C8"
        mutations["wrong_scope"] = wrong_scope

        wrong_signer = execute_one(public_case, truth)
        sign = next(
            item["event"]
            for item in wrong_signer.trace
            if item["type"] == "OWNER_INTERACTION"
            and item["event"]["phase"] == "sign"
        )
        sign["owner_id"] = "CONTROLLER"
        sign["owner_receipt"]["signer_owner_id"] = "CONTROLLER"
        receipt_body = copy.deepcopy(sign["owner_receipt"])
        receipt_body.pop("receipt_sha256")
        sign["owner_receipt"]["receipt_sha256"] = sha256(receipt_body)
        mutations["wrong_signer"] = wrong_signer

        stale = execute_one(public_case, truth)
        sign = next(
            item["event"]
            for item in stale.trace
            if item["type"] == "OWNER_INTERACTION"
            and item["event"]["phase"] == "sign"
        )
        sign["owner_receipt"]["owner_policy_head"] = "STALE-HEAD"
        receipt_body = copy.deepcopy(sign["owner_receipt"])
        receipt_body.pop("receipt_sha256")
        sign["owner_receipt"]["receipt_sha256"] = sha256(receipt_body)
        mutations["stale_head"] = stale

        tampered = execute_one(public_case, truth)
        sign = next(
            item["event"]
            for item in tampered.trace
            if item["type"] == "OWNER_INTERACTION"
            and item["event"]["phase"] == "sign"
        )
        sign["owner_receipt"]["proposal_sha256"] = "0" * 64
        mutations["receipt_tamper"] = tampered

        proposal_tamper = execute_one(public_case, truth)
        proposal_event = next(
            item
            for item in proposal_tamper.trace
            if item["type"] == "FORMATION_PROPOSAL_CREATED"
        )
        proposal_event["proposal"]["nonce"] = "TAMPERED-NONCE"
        mutations["proposal_tamper"] = proposal_tamper

        for name, run in mutations.items():
            with self.subTest(name=name):
                body = score_one(public_case, truth, case_id, run)["body"]
                self.assertEqual(body["V"], "INVALID")
                self.assertFalse(
                    body["bounded_reachability_witness"][
                        "frozen_coordinate_observed"
                    ]
                )

    def test_s0_binds_owner_response_family_and_transplant_changes_hash(self) -> None:
        case_id = "E2-CONDITION-FORMATION"
        public_case = self.public_cases[case_id]
        truth = self.private_document["cases"][case_id]
        baseline = execute_one(public_case, truth)
        transplanted_truth = copy.deepcopy(truth)
        transplanted_truth["owner_events"]["sign"]["GEN-R2"][
            "decision"
        ] = "REFUSED"
        transplanted = execute_one(public_case, transplanted_truth)
        self.assertNotEqual(
            baseline.frozen_s0_sha256, transplanted.frozen_s0_sha256
        )
        for field in (
            "owner_policy_heads",
            "response_family_sha256",
            "budget",
            "horizon",
            "clock_seed",
            "public_packet_sha256",
        ):
            self.assertIn(field, baseline.frozen_s0)

    def test_e4_deadline_operation_and_acceptance_mutations_fail_value(self) -> None:
        case_id = "E4-REVOKE-WITH-ALTERNATIVE"
        truth = self.private_document["cases"][case_id]

        late_case = copy.deepcopy(self.public_cases[case_id])
        late_case["task"]["deadline"] = "T0-1min"
        late_run = execute_one(late_case, truth)
        late = score_one(late_case, truth, case_id, late_run)["body"]
        self.assertFalse(
            late["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertFalse(
            late["post_revoke_observation"][
                "trace_complete_for_frozen_coordinates"
            ]
        )

        wrong_operation_truth = copy.deepcopy(truth)
        wrong_operation_truth["target_readback"]["GEN-R3-ALT:1"][
            "operation_id"
        ] = "WRONG-OP"
        operation_run = execute_one(
            self.public_cases[case_id], wrong_operation_truth
        )
        operation = score_one(
            self.public_cases[case_id],
            wrong_operation_truth,
            case_id,
            operation_run,
        )["body"]
        self.assertFalse(
            operation["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertFalse(
            operation["post_revoke_observation"][
                "trace_complete_for_frozen_coordinates"
            ]
        )

        acceptance_run = execute_one(self.public_cases[case_id], truth)
        acceptance_run.final_state["acceptances"][0]["decision"] = "REFUSE"
        outcome = score_one(
            self.public_cases[case_id], truth, case_id, acceptance_run
        )["body"]
        self.assertFalse(
            outcome["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertFalse(
            outcome["post_revoke_observation"][
                "trace_complete_for_frozen_coordinates"
            ]
        )

    def test_raw_effect_event_is_neutral_not_producer_exact_claim(self) -> None:
        case_id = "E2-CONDITION-FORMATION"
        run = execute_one(
            self.public_cases[case_id],
            self.private_document["cases"][case_id],
        )
        event_types = {item["type"] for item in run.trace}
        self.assertIn("EFFECT_READBACK_OBSERVED", event_types)
        self.assertNotIn("EXACT_TASK_EFFECT_OBSERVED", event_types)

    def test_failure_control_is_bounded_refusal_not_false_success(self) -> None:
        body = self.baseline("E5-IMPOSSIBLE-REFUSAL")
        self.assertEqual(body["C"], "UNSAT")
        self.assertFalse(
            body["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )
        self.assertEqual(
            body["bounded_reachability_witness"]["terminal_observation"],
            "NO_EXECUTABLE_RESOURCE",
        )
        self.assertEqual(body["reachability"]["actual"], "FALSE")

    def test_raw_outputs_bind_live_report_and_runs(self) -> None:
        report_path = ROOT / "outputs" / "report.json"
        trace_path = ROOT / "outputs" / "traces.jsonl"
        on_disk = json.loads(report_path.read_text(encoding="utf-8"))
        traces = [
            json.loads(line)
            for line in trace_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(on_disk["body_sha256"], self.report["body_sha256"])
        self.assertEqual(len(traces), self.report["body"]["raw_run_count"])
        self.assertEqual(len(traces), 16)

    def test_owner_worker_grader_are_distinct_processes_with_frozen_handoff(
        self,
    ) -> None:
        for receipt in self.report["body"]["line_evidence"]:
            boundary = receipt["process_boundary"]
            self.assertTrue(boundary["transcript_frozen_before_grading"])
            self.assertTrue(boundary["worker_terminated_before_grader_start"])
            self.assertTrue(
                boundary["owner_endpoint_terminated_before_grader_start"]
            )
        traces = [
            json.loads(line)
            for line in (ROOT / "outputs" / "traces.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        for run in traces:
            topology = next(
                item
                for item in run["trace"]
                if item["type"] == "PROCESS_TOPOLOGY_OBSERVATION"
            )
            self.assertNotEqual(
                topology["worker_pid"], topology["owner_endpoint_pid"]
            )
            self.assertTrue(topology["transmitted_equals_consumed"])
            self.assertTrue(topology["owner_emitted_equals_forwarded"])
            self.assertEqual(
                topology["owner_transmitted_bytes_sha256"],
                topology["worker_consumed_bytes_sha256"],
            )
            self.assertEqual(
                topology["owner_emitted_wire_line_sha256"],
                topology["broker_forwarded_wire_line_sha256"],
            )
            self.assertEqual(
                topology["broker_forwarded_wire_line_sha256"],
                topology["worker_consumed_wire_line_sha256"],
            )

    def test_worker_capsule_actually_denies_private_and_reflection_reads(
        self,
    ) -> None:
        denied = (
            ROOT / "private" / "owner_truth.json",
            ROOT / "formation" / "owner_service.py",
            ROOT / "formation" / "scorer.py",
            ROOT / "formation" / "runner.py",
            ROOT / "formation" / "__pycache__" / "runner.cpython-39.pyc",
            ROOT / "outputs" / "report.json",
            ROOT / "tests" / "test_module.py",
            ROOT / "internal" / "A-problem-reconstruction.md",
            ROOT.parents[2]
            / "external"
            / "codex-cli-cohort-003"
            / "G3-final.md",
        )
        for path in denied:
            with self.subTest(path=path.name):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        str(ROOT / "worker_capsule.py"),
                        "--probe-denied-read",
                        str(path),
                    ],
                    cwd="/private/tmp",
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 77)
                self.assertIn("WORKER_CAPSULE_READ_DENIED", completed.stdout)
        for module in (
            "formation.owner_service",
            "formation.scorer",
            "formation.runner",
        ):
            with self.subTest(module=module):
                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        str(ROOT / "worker_capsule.py"),
                        "--probe-denied-import",
                        module,
                    ],
                    cwd="/private/tmp",
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 78)
                self.assertTrue(
                    "WORKER_CAPSULE_IMPORT_DENIED" in completed.stdout
                    or "WORKER_CAPSULE_READ_DENIED" in completed.stdout
                )
        source = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in (
                "formation/runner.py",
                "formation/worker_process.py",
                "formation/execution_service.py",
            )
        )
        self.assertNotIn("from .owner_service import", source)
        self.assertNotIn("from .scorer import", source)
        self.assertNotIn("OwnerService(", source)
        self.assertNotIn("FormationScorer(", source)

    def test_owner_response_transplant_stale_tamper_and_wrong_target_fail(
        self,
    ) -> None:
        public_case = self.public_cases["E2-CONDITION-FORMATION"]
        truth = self.private_document["cases"]["E2-CONDITION-FORMATION"]
        expected_codes = {
            "TRANSPLANT": "OWNER_EPISODE_TRANSPLANT",
            "STALE": "OWNER_RESPONSE_STALE",
            "WRONG_OWNER": "OWNER_IDENTITY_MISMATCH",
            "STALE_STATE": "OWNER_STATE_VERSION_STALE",
            "STALE_POLICY_VERSION": "OWNER_POLICY_VERSION_STALE",
            "STALE_POLICY_HEAD": "OWNER_POLICY_HEAD_STALE",
            "WRONG_Q": "OWNER_Q_TRANSPLANT",
            "WRONG_TARGET": "OWNER_WRONG_TARGET",
            "WRONG_OPERATION": "OWNER_OPERATION_TRANSPLANT",
            "WRONG_REQUEST": "OWNER_REQUEST_TRANSPLANT",
            "WRONG_REQUEST_NONCE": "OWNER_REQUEST_NONCE_TRANSPLANT",
            "WRONG_PROPOSAL": "OWNER_PROPOSAL_TRANSPLANT",
            "TAMPER": "OWNER_RESPONSE_AUTHENTICATOR_INVALID",
            "TAMPER_REHASH": "OWNER_RESPONSE_AUTHENTICATOR_INVALID",
        }
        for fault, expected in expected_codes.items():
            with self.subTest(fault=fault):
                run = execute_one(
                    public_case,
                    truth,
                    response_fault=fault,
                )
                rejections = [
                    item
                    for item in run.trace
                    if item["type"] == "OWNER_RESPONSE_REJECTED"
                ]
                self.assertTrue(rejections)
                self.assertIn(expected, {item["reason"] for item in rejections})
                body = score_one(
                    public_case,
                    truth,
                    "E2-CONDITION-FORMATION",
                    run,
                )["body"]
                self.assertEqual(body["V"], "VALID")
                self.assertFalse(
                    body["bounded_reachability_witness"][
                        "frozen_coordinate_observed"
                    ]
                )

    def test_worker_start_surface_has_minimal_argv_and_environment(self) -> None:
        command = worker_command()
        environment = worker_environment()
        serialized = json.dumps(
            {"argv": command, "env": environment}, sort_keys=True
        )
        self.assertIn("worker_capsule.py", command[-1])
        self.assertNotIn("owner_truth", serialized)
        self.assertNotIn("scorer", serialized)
        self.assertNotIn("grader", serialized)
        self.assertNotIn("semantic", serialized)
        self.assertNotIn("PYTHONPATH", environment)
        self.assertLessEqual(
            set(environment),
            {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "PYTHONDONTWRITEBYTECODE"},
        )

    def test_worker_and_owner_do_not_consume_private_expected_resolution(
        self,
    ) -> None:
        for path in (
            ROOT / "formation" / "execution_service.py",
            ROOT / "formation" / "worker_process.py",
            ROOT / "formation" / "owner_service.py",
            ROOT / "formation" / "runner.py",
            ROOT / "formation" / "scorer.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("resolution_requirement", source)
            self.assertNotIn("expected_path", source)
        private_text = (ROOT / "private" / "owner_truth.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("resolution_requirement", private_text)
        self.assertNotIn("expected_path", private_text)

    def test_owner_wire_whitespace_and_key_order_are_forwarded_byte_exact(
        self,
    ) -> None:
        public_case = self.public_cases["E2-CONDITION-FORMATION"]
        truth = self.private_document["cases"]["E2-CONDITION-FORMATION"]
        run = execute_one(
            public_case,
            truth,
            response_fault="WIRE_VARIANT",
        )
        topology = next(
            item
            for item in run.trace
            if item["type"] == "PROCESS_TOPOLOGY_OBSERVATION"
        )
        self.assertTrue(any(topology["owner_wire_variant_observed"]))
        self.assertTrue(topology["owner_emitted_equals_forwarded"])
        self.assertTrue(topology["transmitted_equals_consumed"])
        self.assertEqual(
            topology["owner_emitted_wire_line_sha256"],
            topology["worker_consumed_wire_line_sha256"],
        )
        body = score_one(
            public_case,
            truth,
            "E2-CONDITION-FORMATION",
            run,
        )["body"]
        self.assertTrue(
            body["bounded_reachability_witness"][
                "frozen_coordinate_observed"
            ]
        )

    def test_g3_envelope_passes_real_integration_preflight_field_scan(
        self,
    ) -> None:
        preflight_root = ROOT.parent / "integration-preflight"
        spec = importlib.util.spec_from_file_location(
            "ce001_preflight_for_g3",
            preflight_root / "preflight.py",
        )
        assert spec and spec.loader
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        envelope = json.loads(
            (preflight_root / "fixtures" / "qualified-e1.json").read_text(
                encoding="utf-8"
            )
        )
        envelope["components"]["G3"] = copy.deepcopy(self.report["body"])
        result = preflight.validate_envelope(envelope)
        codes = {item["code"] for item in result["rejections"]}
        self.assertNotIn("CONTRACT_FIELD_PASSTHROUGH", codes)
        self.assertNotIn("LINE_SCOPE_PASSTHROUGH", codes)
        self.assertEqual(result["preflight_status"], "QUALIFIED_COMPONENT_OUTPUTS")

    def test_g3_component_has_no_contract_verdict_or_synonym_labels(
        self,
    ) -> None:
        forbidden = {
            "authority",
            "effect",
            "acceptance",
            "settlement",
            "exact_task_success",
            "correct_resolution",
            "recovery_to_value",
            "task_succeeded",
            "goal_achieved",
            "value_delivered",
            "exact_value_obtained",
            "resolved_correctly",
            "valid_resolution",
            "recovered_value",
            "recovery_success",
            "restored_to_value",
            "authorized",
            "permission_valid",
            "delegation_authority",
            "effect_occurred",
            "physical_effect",
            "effect_exact",
            "accepted",
            "owner_accepted",
            "acceptance_valid",
            "settled",
            "finality_complete",
            "settlement_valid",
        }

        def normalize(value: str) -> str:
            return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

        observed: set[str] = set()

        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    observed.add(normalize(str(key)))
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, str):
                observed.add(normalize(value))

        walk(self.report["body"])
        self.assertEqual(observed.intersection(forbidden), set())


if __name__ == "__main__":
    unittest.main()
