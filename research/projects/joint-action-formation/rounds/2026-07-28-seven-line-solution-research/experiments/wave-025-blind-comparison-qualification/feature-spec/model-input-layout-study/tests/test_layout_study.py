from __future__ import annotations

import importlib.util
import copy
import json
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SPEC = importlib.util.spec_from_file_location("layout_study", STUDY / "layout_study.py")
assert SPEC and SPEC.loader
layout_study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout_study)


class LayoutStudyV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = layout_study.build_result()
        routing, receipt_schema, _coverage = layout_study.routing_lib.verify_candidate_bytes(
            layout_study.ROUTING_PATH.read_bytes(),
            layout_study.ROUTING_SCHEMA_PATH.read_bytes(),
            layout_study.RECEIPT_SCHEMA_PATH.read_bytes(),
            layout_study.PRIMITIVES_PATH.read_bytes(),
        )
        cls.shapes = [
            layout_study.receipt_shape(routing, receipt_schema, path)
            for path in sorted(layout_study.SMOKE_SLOTS.glob("*/collector-features.json"))
        ]
        cls.disk_slots = [
            path.name for path in layout_study.SMOKE_SLOTS.iterdir() if path.is_dir()
        ]

    def test_public_plan_closed_and_disk_lineage_is_bound(self) -> None:
        lineage = self.result["public_f_lineage"]
        self.assertEqual(
            lineage["status"], "OBSERVED_PUBLIC_LINEAGE_PASS__NOT_V1_1_ADMISSION"
        )
        self.assertTrue(lineage["slot_sets_plan_closed_disk_receipts_equal"])
        self.assertTrue(lineage["raw_plan_rows_unique"])
        self.assertTrue(lineage["raw_closed_rows_unique"])
        self.assertTrue(lineage["collector_hashes_match_closed"])
        self.assertEqual(self.result["bound_inputs"]["receipt_count"], 12)

    def test_lineage_rejects_duplicate_append_before_deduplication(self) -> None:
        plan = json.loads(layout_study.PUBLIC_PLAN_PATH.read_bytes())
        closed = json.loads(layout_study.CLOSED_PATH.read_bytes())
        plan["slots"].append(copy.deepcopy(plan["slots"][0]))
        closed["slots"].append(copy.deepcopy(closed["slots"][0]))
        plan_raw = layout_study.canonical_bytes(plan)
        closed_raw = layout_study.canonical_bytes(closed)
        with self.assertRaisesRegex(ValueError, "raw slot row count mismatch"):
            layout_study.verify_f_lineage_documents(
                plan_raw=plan_raw,
                closed_raw=closed_raw,
                shapes=self.shapes,
                disk_slot_names=self.disk_slots,
                unexpected_disk_entries=[],
                expected_plan_sha256=layout_study.sha256(plan_raw),
                expected_closed_sha256=layout_study.sha256(closed_raw),
            )

    def test_lineage_rejects_duplicate_slot_id_even_with_recomputed_expected_hash(self) -> None:
        plan = json.loads(layout_study.PUBLIC_PLAN_PATH.read_bytes())
        plan["slots"][-1]["opaque_slot_id"] = plan["slots"][0]["opaque_slot_id"]
        plan_raw = layout_study.canonical_bytes(plan)
        with self.assertRaisesRegex(ValueError, "duplicate public plan slot id"):
            layout_study.verify_f_lineage_documents(
                plan_raw=plan_raw,
                closed_raw=layout_study.CLOSED_PATH.read_bytes(),
                shapes=self.shapes,
                disk_slot_names=self.disk_slots,
                unexpected_disk_entries=[],
                expected_plan_sha256=layout_study.sha256(plan_raw),
                expected_closed_sha256=layout_study.EXPECTED_CLOSED_SHA256,
            )

    def test_local_expected_sha_rejects_plan_closed_common_rewrite(self) -> None:
        plan = json.loads(layout_study.PUBLIC_PLAN_PATH.read_bytes())
        closed = json.loads(layout_study.CLOSED_PATH.read_bytes())
        target = plan["slots"][0]["opaque_slot_id"]
        for row in plan["slots"]:
            if row["opaque_slot_id"] == target:
                row["challenge"] = "COEDITED-PUBLIC-TREATMENT"
        for row in closed["slots"]:
            if row["opaque_slot_id"] == target:
                row["challenge"] = "COEDITED-PUBLIC-TREATMENT"
        with self.assertRaisesRegex(ValueError, "expected SHA"):
            layout_study.verify_f_lineage_documents(
                plan_raw=layout_study.canonical_bytes(plan),
                closed_raw=layout_study.canonical_bytes(closed),
                shapes=self.shapes,
                disk_slot_names=self.disk_slots,
                unexpected_disk_entries=[],
                expected_plan_sha256=layout_study.EXPECTED_PUBLIC_PLAN_SHA256,
                expected_closed_sha256=layout_study.EXPECTED_CLOSED_SHA256,
            )

    def test_routing_mixed_keys_are_not_predictor_templates(self) -> None:
        static = self.result["routing_static_shape"]
        primitive = static["primitives_emittable_representative_templates_index_zero"]
        self.assertEqual(static["routing_rows"], 109)
        self.assertEqual(static["route_channel_stat_matrix_entries"], 641)
        self.assertEqual(static["routing_mixed_representative_keys_index_zero"], 2715)
        self.assertEqual(primitive["numeric_context_stat"], 2312)
        self.assertEqual(primitive["category_context_channel_before_value"], 213)
        self.assertEqual(primitive["direct_ngram_family"], 6)
        self.assertEqual(primitive["total"], 2531)
        self.assertFalse(static["closed_final_predictor_universe_proven"])

    def test_wildcards_distinguish_ordered_bag_and_container(self) -> None:
        wildcard = self.result["routing_static_shape"]["wildcard_path_rows"]
        self.assertEqual(wildcard["total"], 47)
        self.assertEqual(wildcard["classes"]["ORDERED_CONTEXT_RETAINED"], 11)
        self.assertEqual(wildcard["classes"]["BAG_ITEM_CAPTURE_DROPPED"], 35)
        self.assertEqual(wildcard["classes"]["CONTAINER_ITEM_CAPTURE_DROPPED"], 1)

    def test_category_domain_is_grammar_based_and_unknown_is_preserved(self) -> None:
        domain = self.result["routing_static_shape"]["category_route_channel_domain_status"]
        self.assertEqual(domain["counts"]["CLOSED_JSON_BOOL"], 2)
        self.assertEqual(domain["counts"]["NONENUMERABLE_SHA256_GRAMMAR"], 6)
        self.assertEqual(domain["counts"]["UNKNOWN_NEEDS_SCHEMA_DOMAIN_PROOF"], 31)
        self.assertIn("transform names are not used", domain["method"])

    def test_only_six_ngram_family_blocks_are_allocated(self) -> None:
        observed = self.result["actual_f_shape"][
            "observed_union_snapshot_not_a_frozen_model_layout"
        ]
        self.assertEqual(len(observed["reachable_ngram_families"]), 6)
        self.assertEqual(observed["fixed_direct_ngram_columns"], 24576)
        self.assertEqual(observed["snapshot_logical_columns"], 26766)
        self.assertEqual(observed["snapshot_dense_float64_bytes"], 2569536)
        expected_csr = 12 * observed["snapshot_total_nnz"] + 4 * 13
        self.assertEqual(observed["snapshot_csr_float64_u32_bytes"], expected_csr)

    def test_novelty_is_stratified_singleton_heavy_and_insufficient(self) -> None:
        split = self.result["selection_firewall"]["probe_split"]
        for counts in split["strata"].values():
            self.assertEqual(counts, {"reference": 2, "probe": 2})
        novelty = self.result["actual_f_shape"]["novelty_exploration_current_12"]
        self.assertEqual(novelty["all_category_singletons"], 408)
        self.assertEqual(novelty["probe_only_category_columns"], 204)
        self.assertEqual(novelty["probe_only_singletons"], 204)
        self.assertEqual(
            novelty["verdict"], "CURRENT_12_INSUFFICIENT_FOR_NOVELTY_OR_HASH_VALUE_DECISION"
        )

    def test_dictionary_is_reference_frozen_and_layouts_are_distinct(self) -> None:
        study = self.result["calibration_frozen_layout_comparison"][0]
        self.assertEqual(study["dictionary_phase"], "REFERENCE_ONLY_BEFORE_PROBE")
        self.assertEqual(study["reference_exact_columns"], 382)
        self.assertEqual(study["probe_application"]["exact_oov_columns"], 204)
        self.assertTrue(study["probe_application"]["probe_does_not_expand_dictionary"])
        self.assertEqual(
            study["logical_columns"],
            {
                "exact_only": 26562,
                "exact_plus_other": 26668,
                "hash_only": 54852,
                "hybrid_exact_plus_oov_hash": 55234,
            },
        )
        self.assertEqual(study["total_nnz"]["exact_only_nnz"], 62047)
        self.assertEqual(study["total_nnz"]["exact_plus_other_nnz"], 62107)
        self.assertEqual(study["total_nnz"]["hybrid_oov_presence_nnz"], 62250)

    def test_e1_to_e4_removal_counterexamples_remain_scoped(self) -> None:
        fixtures = self.result["fixtures"]
        self.assertTrue(fixtures[0]["observed"]["exact_distinguishes"])
        self.assertFalse(fixtures[0]["observed"]["static_route_only_distinguishes"])
        self.assertEqual(fixtures[1]["observed"]["signed_sum"], 0)
        self.assertEqual(fixtures[1]["observed"]["presence_or"], 1)
        self.assertTrue(fixtures[2]["observed"]["value_plus_missing_distinguishes"])
        self.assertTrue(fixtures[3]["observed"]["normalization_removes_family_volume_on_single_axis"])

    def test_e5_correctly_changes_zero_compressed_nnz(self) -> None:
        observed = self.result["fixtures"][4]["observed"]
        self.assertTrue(observed["logical_width_equal"])
        self.assertEqual(observed["raw_nonzero_values"], 3)
        self.assertEqual(observed["robust_nonzero_values"], 4)
        self.assertFalse(observed["zero_compressed_sparsity_equal"])

    def test_signed_hash_diagnostic_rejects_bare_boolean_assertions(self) -> None:
        current = self.result["mechanism_compatibility"]["signed_hash"][
            "deletion_authorization_diagnostic"
        ]
        self.assertEqual(current["decision"], "UNKNOWN_DO_NOT_DELETE")
        self.assertFalse(current["study_can_authorize_deletion"])
        all_true = {
            name: True for name in layout_study.DELETION_REQUIREMENT_SCOPES
        }
        self.assertEqual(
            layout_study.signed_hash_receipt_diagnostic(all_true, {})["decision"],
            "UNKNOWN_DO_NOT_DELETE",
        )
        self.assertIn(
            "BUNDLE_NOT_CLOSED_SCHEMA",
            layout_study.signed_hash_receipt_diagnostic(all_true, {})["validation_errors"],
        )

    def test_signed_hash_diagnostic_checks_unique_ids_sha_and_exact_scope(self) -> None:
        descriptors = []
        for requirement, scope in layout_study.DELETION_REQUIREMENT_SCOPES.items():
            descriptors.append(
                {
                    "requirement_id": requirement,
                    "evidence_receipt_id": "duplicate-id",
                    "evidence_receipt_sha256": "",
                    "scope": scope + "-WRONG",
                    "status": "SATISFIED",
                }
            )
        result = layout_study.signed_hash_receipt_diagnostic(
            {
                "schema": "wave025-signed-hash-deletion-evidence-bundle-v1",
                "receipts": descriptors,
            },
            {},
        )
        self.assertEqual(result["decision"], "UNKNOWN_DO_NOT_DELETE")
        self.assertTrue(any(error.endswith("SCOPE_MISMATCH") for error in result["validation_errors"]))
        self.assertTrue(any(error.endswith("RECEIPT_SHA_INVALID") for error in result["validation_errors"]))
        self.assertIn("DUPLICATE_EVIDENCE_RECEIPT_ID", result["validation_errors"])

    def test_signed_hash_diagnostic_malformed_descriptor_fails_closed_without_exception(self) -> None:
        descriptors = []
        for requirement, scope in layout_study.DELETION_REQUIREMENT_SCOPES.items():
            descriptors.append(
                {
                    "requirement_id": requirement,
                    "evidence_receipt_id": f"receipt-{len(descriptors)}",
                    "evidence_receipt_sha256": "0" * 64,
                    "scope": scope,
                    "status": "SATISFIED",
                }
            )
        descriptors[0]["requirement_id"] = []
        result = layout_study.signed_hash_receipt_diagnostic(
            {
                "schema": "wave025-signed-hash-deletion-evidence-bundle-v1",
                "receipts": descriptors,
            },
            {},
        )
        self.assertEqual(result["decision"], "UNKNOWN_DO_NOT_DELETE")
        self.assertIn("receipt[0]:REQUIREMENT_ID_INVALID", result["validation_errors"])

    def test_caller_made_eight_receipts_never_authorize_deletion(self) -> None:
        descriptors = []
        documents = {}
        for index, (requirement, scope) in enumerate(
            layout_study.DELETION_REQUIREMENT_SCOPES.items()
        ):
            receipt_id = f"caller-made-{index}"
            document = {
                "schema": "wave025-signed-hash-deletion-evidence-receipt-v1",
                "requirement_id": requirement,
                "evidence_receipt_id": receipt_id,
                "scope": scope,
                "status": "SATISFIED",
                "subject_sha256": "0" * 64,
            }
            raw = layout_study.canonical_bytes(document)
            documents[receipt_id] = raw
            descriptors.append(
                {
                    "requirement_id": requirement,
                    "evidence_receipt_id": receipt_id,
                    "evidence_receipt_sha256": layout_study.sha256(raw),
                    "scope": scope,
                    "status": "SATISFIED",
                }
            )
        result = layout_study.signed_hash_receipt_diagnostic(
            {
                "schema": "wave025-signed-hash-deletion-evidence-bundle-v1",
                "receipts": descriptors,
            },
            documents,
        )
        self.assertEqual(result["validation_errors"], [])
        self.assertTrue(result["local_bundle_well_formed"])
        self.assertFalse(result["study_can_authorize_deletion"])
        self.assertFalse(result["issuer_authority_verified"])
        self.assertFalse(result["subject_preimage_authority_verified"])
        self.assertFalse(result["requirement_specific_proof_verified"])
        self.assertEqual(result["decision"], "EXTERNAL_AUTHORITY_REQUIRED")

    def test_scientific_state_remains_unknown_and_not_run(self) -> None:
        boundary = self.result["scientific_boundary"]
        self.assertEqual(boundary["power"], "UNKNOWN")
        self.assertTrue(boundary["no_classifier_fit"])
        self.assertEqual(boundary["c01_phase_boundary"], "EXTERNAL_UNRESOLVED_DEPENDENCY")
        self.assertFalse(boundary["rejected_c01_minisuite_used_as_ground_truth"])
        self.assertFalse(boundary["g_started"])
        self.assertFalse(boundary["formal_3200_started"])

    def test_checked_result_is_byte_rebuildable(self) -> None:
        frozen = STUDY / "RESULTS.candidate.json"
        self.assertEqual(frozen.read_bytes(), layout_study.canonical_bytes(self.result))
        parsed = json.loads(frozen.read_bytes())
        self.assertEqual(
            parsed["status"],
            "CANDIDATE_STUDY_V4__SCOPED_RETROSPECTIVE_SHAPE_ONLY__POWER_UNKNOWN__NO_G__NO_3200",
        )


if __name__ == "__main__":
    unittest.main()
