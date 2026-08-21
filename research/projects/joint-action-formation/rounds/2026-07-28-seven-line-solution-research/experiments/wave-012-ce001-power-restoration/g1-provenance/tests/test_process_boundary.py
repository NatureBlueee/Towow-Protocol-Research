from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g1prov.runner import (
    build_report,
    run_episode,
    run_process_identity_injection,
    verify_frozen_manifest,
)


class G1ProcessBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.episode = run_episode("E1-EXTANT-MULTI-OWNER")

    def test_worker_owner_controller_are_distinct_and_bytes_are_exact(self) -> None:
        receipt = self.episode["process_boundary_receipt"]
        self.assertTrue(receipt["distinct_processes"])
        self.assertTrue(
            receipt["controller_raw_forwarding"]["all_exact_bytes_equal"]
        )
        self.assertTrue(
            receipt["worker_inbound_scan"]["worker_report_matches_controller"]
        )
        self.assertTrue(
            receipt["owner_event_origin"][
                "all_owner_generated_and_request_bound"
            ]
        )
        self.assertEqual(
            receipt["owner_pid"],
            receipt["process_identity_binding"]["controller_observed"][
                "owner_popen_pid"
            ],
        )
        self.assertEqual(
            receipt["worker_pid"],
            receipt["process_identity_binding"]["controller_observed"][
                "worker_popen_pid"
            ],
        )
        self.assertTrue(
            receipt["process_identity_binding"]["owner_ready_bound"]
        )
        self.assertTrue(
            receipt["process_identity_binding"]["worker_ready_bound"]
        )
        self.assertTrue(
            receipt["process_identity_binding"]["worker_result_bound"]
        )
        self.assertTrue(
            receipt["controller_evaluator_private_input"][
                "canary_present_in_private_input"
            ]
        )
        self.assertTrue(
            receipt["worker_inbound_scan"]["private_canary_absent"]
        )
        self.assertEqual(
            [],
            receipt["worker_inbound_scan"]["forbidden_marker_hits"],
        )
        self.assertEqual(
            [],
            receipt["worker_inbound_scan"][
                "worker_source_forbidden_marker_hits"
            ],
        )

    def test_reflection_closure_import_and_bounded_path_surfaces_are_clean(self) -> None:
        attestation = self.episode["process_boundary_receipt"][
            "worker_runtime_attestation"
        ]
        self.assertEqual(1, attestation["isolated_flag"])
        self.assertEqual(1, attestation["no_site_flag"])
        self.assertEqual(["worker_process.py"], attestation["bounded_cwd_path_scan"])
        self.assertEqual({"__main__"}, set(attestation["frame_module_names"]))
        loaded = set(attestation["loaded_module_names"])
        self.assertFalse(
            {
                "g1prov.fixtures",
                "g1prov.evaluator",
                "g1prov.runner",
                "g1prov.session",
            }
            & loaded
        )
        attack = self.episode["process_boundary_receipt"][
            "malicious_worker_scan"
        ]
        self.assertTrue(
            attack["private_canary_hash_absent_from_reachable_strings"]
        )
        self.assertEqual([], attack["private_field_name_hits"])
        self.assertEqual([], attack["controller_fixture_module_hits"])

    def test_handoff_is_only_candidate_and_owner_origin_is_exposed(self) -> None:
        handoff = self.episode["g1_handoff"]
        self.assertEqual("CANDIDATE_NOT_COMMITMENT", handoff["status"])
        self.assertEqual(
            {
                "RELATION",
                "COMMITMENT",
                "AUTHORITY",
                "EFFECT",
                "ACCEPTANCE",
                "SETTLEMENT",
            },
            set(handoff["explicit_non_claims"]),
        )
        owner_pid = self.episode["process_boundary_receipt"]["owner_pid"]
        owner_boundary = self.episode["process_boundary_receipt"][
            "owner_source_boundary"
        ]
        self.assertEqual(
            "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE",
            owner_boundary["source_type"],
        )
        self.assertEqual(
            "NOT_ESTABLISHED",
            owner_boundary["independent_owner_truth"],
        )
        self.assertEqual(
            "NOT_ESTABLISHED",
            owner_boundary["independent_owner_origin"],
        )
        self.assertTrue(
            all(
                item["owner_service_pid"] == owner_pid
                and item["owner_state_version"] > 0
                and item["owner_request_hash"]
                and item["owner_source_type"]
                == "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE"
                and item["owner_source_instance_id"]
                == owner_boundary["controller_assigned_launch_binding"][
                    "source_instance_id"
                ]
                and item["owner_state_instance_id"]
                == owner_boundary["controller_assigned_launch_binding"][
                    "state_instance_id"
                ]
                and item["owner_process_instance_id"]
                == owner_boundary["controller_assigned_launch_binding"][
                    "process_instance_id"
                ]
                for item in handoff["evidence"]
            )
        )

    def _assert_identity_injection(
        self,
        injection: str,
        reason: str,
    ) -> dict:
        result = run_process_identity_injection(injection)
        self.assertEqual("FAIL_CLOSED", result["status"])
        self.assertEqual(reason, result["reason"])
        receipt = result["receipt"]
        self.assertEqual("FAIL_CLOSED", receipt["status"])
        self.assertTrue(receipt["raw_boundary_trace"])
        self.assertTrue(receipt["raw_boundary_trace_sha256"])
        self.assertNotEqual(
            receipt["controller_observed"]["worker_popen_pid"],
            receipt["controller_observed"]["owner_popen_pid"],
        )
        self.assertEqual(
            "RED_NOT_ISOLATED",
            receipt["same_user_hostile_os_isolation"],
        )
        return receipt

    def test_owner_ready_pid_424242_fails_closed_against_popen_pid(self) -> None:
        receipt = self._assert_identity_injection(
            "OWNER_PID_MISMATCH",
            "OWNER_READY_PID_MISMATCH",
        )
        self.assertEqual(424242, receipt["claimed"])
        self.assertEqual(
            receipt["controller_observed"]["owner_popen_pid"],
            receipt["expected"],
        )

    def test_worker_ready_pid_424242_fails_closed_against_popen_pid(self) -> None:
        receipt = self._assert_identity_injection(
            "WORKER_PID_MISMATCH",
            "WORKER_READY_PID_MISMATCH",
        )
        self.assertEqual(424242, receipt["claimed"])
        self.assertEqual(
            receipt["controller_observed"]["worker_popen_pid"],
            receipt["expected"],
        )

    def test_event_origin_self_report_inconsistency_fails_closed(self) -> None:
        receipt = self._assert_identity_injection(
            "ORIGIN_SELF_REPORT_INCONSISTENCY",
            "OWNER_EVENT_ORIGIN_PID_MISMATCH",
        )
        self.assertEqual(424242, receipt["claimed"]["value"])
        self.assertEqual(
            receipt["controller_observed"]["owner_popen_pid"],
            receipt["expected"],
        )

    def test_wrong_controller_assigned_source_instance_fails_closed(self) -> None:
        receipt = self._assert_identity_injection(
            "WRONG_SOURCE_INSTANCE",
            "OWNER_EVENT_SOURCE_INSTANCE_MISMATCH",
        )
        self.assertEqual("WRONG_SOURCE_INSTANCE", receipt["claimed"]["value"])
        self.assertEqual(
            receipt["controller_assigned"]["owner_launch_binding"][
                "source_instance_id"
            ],
            receipt["expected"],
        )

    def test_frozen_manifest_binds_all_four_artifact_classes(self) -> None:
        report = build_report()
        self.assertTrue(verify_frozen_manifest(report)["valid"])
        self.assertEqual(
            4,
            len(report["process_identity_injections"]),
        )
        self.assertTrue(
            all(
                injection["status"] == "FAIL_CLOSED"
                for injection in report["process_identity_injections"]
            )
        )
        manifest = report["frozen_manifest"]
        self.assertTrue(manifest["source_tree"])
        self.assertTrue(manifest["input_receipts"]["public_input_bytes"])
        self.assertTrue(
            manifest["input_receipts"]["private_evaluator_input_bytes"]
        )
        self.assertTrue(manifest["raw_boundary_traces"])
        self.assertTrue(manifest["raw_result_traces"])
        self.assertEqual(4, len(manifest["process_identity_failure_traces"]))
        self.assertEqual(
            "RED_NOT_ISOLATED",
            report["isolation_attacks"]["same_user_absolute_path_scan"][
                "status"
            ],
        )

        mutated_trace = deepcopy(report)
        mutated_trace["baseline"][0]["raw_trace"]["notes"].append("tamper")
        verification = verify_frozen_manifest(mutated_trace)
        self.assertFalse(verification["valid"])
        self.assertIn("raw_result_traces_sha256", verification["mismatches"])
        self.assertIn("result_bytes_sha256", verification["mismatches"])

        mutated_source_receipt = deepcopy(report)
        mutated_source_receipt["frozen_manifest"]["source_tree"][0][
            "sha256"
        ] = "0" * 64
        verification = verify_frozen_manifest(mutated_source_receipt)
        self.assertFalse(verification["valid"])
        self.assertIn("source_tree", verification["mismatches"])

        mutated_input_receipt = deepcopy(report)
        mutated_input_receipt["frozen_manifest"]["input_receipts"][
            "private_evaluator_input_bytes"
        ][0]["byte_length"] += 1
        verification = verify_frozen_manifest(mutated_input_receipt)
        self.assertFalse(verification["valid"])
        self.assertIn("input_receipts", verification["mismatches"])

        mutated_transport = deepcopy(report)
        mutated_transport["baseline"][0]["process_boundary_receipt"][
            "raw_boundary_trace"
        ][0]["wire_b64"] += "AA=="
        verification = verify_frozen_manifest(mutated_transport)
        self.assertFalse(verification["valid"])
        self.assertIn(
            "raw_boundary_traces_sha256",
            verification["mismatches"],
        )

        mutated_result = deepcopy(report)
        mutated_result["baseline"][0]["boundary"] = "TAMPERED"
        verification = verify_frozen_manifest(mutated_result)
        self.assertFalse(verification["valid"])
        self.assertIn("result_bytes_sha256", verification["mismatches"])

        mutated_identity_failure = deepcopy(report)
        mutated_identity_failure["process_identity_injections"][0]["receipt"][
            "raw_boundary_trace"
        ][0]["wire_b64"] += "AA=="
        verification = verify_frozen_manifest(mutated_identity_failure)
        self.assertFalse(verification["valid"])
        self.assertIn(
            "process_identity_failure_traces_sha256",
            verification["mismatches"],
        )
        self.assertIn("result_bytes_sha256", verification["mismatches"])


if __name__ == "__main__":
    unittest.main()
