from __future__ import annotations

import copy
import unittest

from audit import (
    EXPECTED_LINES,
    assess_binding_records,
    audit_current_artifacts,
)


def coherent_records():
    shared = {
        "persisted_output": True,
        "selected_case_id": "E1-EXTANT-MULTI-OWNER",
        "episode_manifest_sha256": "manifest-hash",
        "run_root": "run-root",
        "q_version": "Q@v1",
        "canonical_object_id": "VenueV:CircuitC7",
        "operation_id": "operation-001",
        "owner_registry_sha256": "owner-registry-hash",
        "target_registry_sha256": "target-registry-hash",
        "cross_refs": {},
    }
    records = []
    for line in EXPECTED_LINES:
        record = copy.deepcopy(shared)
        record["line"] = line
        record["source_artifact_sha256"] = f"{line}-artifact-hash"
        records.append(record)
    by_line = {record["line"]: record for record in records}
    by_line["G6"]["cross_refs"]["g5_source_artifact_sha256"] = by_line["G5"][
        "source_artifact_sha256"
    ]
    by_line["G7"]["cross_refs"]["g6_source_artifact_sha256"] = by_line["G6"][
        "source_artifact_sha256"
    ]
    return records


class BindingAuditTests(unittest.TestCase):
    def test_coherent_single_episode_records_are_joinable(self) -> None:
        report = assess_binding_records(coherent_records())
        self.assertEqual(report["status"], "JOINABLE_SINGLE_EPISODE")
        self.assertEqual(report["failures"], [])
        self.assertEqual(report["contract_score_status"], "NOT_COMPUTED")

    def test_cross_line_source_links_are_required(self) -> None:
        records = coherent_records()
        by_line = {record["line"]: record for record in records}
        by_line["G6"]["cross_refs"] = {}
        report = assess_binding_records(records)
        codes = {failure["code"] for failure in report["failures"]}
        self.assertEqual(report["status"], "NOT_JOINABLE_CURRENT_ARTIFACTS")
        self.assertIn("G5_TO_G6_SOURCE_LINK_MISSING", codes)

    def test_case_or_operation_transplant_is_rejected(self) -> None:
        records = coherent_records()
        records[2]["selected_case_id"] = "E6-MIGRATION-REPLAY"
        records[3]["operation_id"] = "foreign-operation"
        report = assess_binding_records(records)
        mismatches = {
            failure["detail"]["field"]
            for failure in report["failures"]
            if failure["code"] == "COMMON_BINDING_MISMATCH"
        }
        self.assertEqual(report["status"], "NOT_JOINABLE_CURRENT_ARTIFACTS")
        self.assertEqual(mismatches, {"selected_case_id", "operation_id"})

    def test_current_artifacts_are_not_joinable(self) -> None:
        report = audit_current_artifacts()
        codes = {failure["code"] for failure in report["failures"]}
        self.assertEqual(report["status"], "NOT_JOINABLE_CURRENT_ARTIFACTS")
        self.assertEqual(report["contract_score_status"], "NOT_COMPUTED")
        self.assertIn("PERSISTED_OUTPUT_MISSING", codes)
        self.assertIn("COMMON_BINDING_MISSING", codes)
        self.assertIn("G5_TO_G6_SOURCE_LINK_MISSING", codes)
        self.assertIn("G6_TO_G7_SOURCE_LINK_MISSING", codes)

        g7_matches = report["observations"][
            "g7_recovery_refs_present_in_g6_report"
        ]
        self.assertTrue(g7_matches)
        self.assertTrue(all(value is False for value in g7_matches.values()))


if __name__ == "__main__":
    unittest.main()
