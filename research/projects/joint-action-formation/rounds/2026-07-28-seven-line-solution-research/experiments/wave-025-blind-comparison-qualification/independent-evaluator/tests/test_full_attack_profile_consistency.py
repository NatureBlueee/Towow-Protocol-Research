#!/usr/bin/env python3
"""Independent consistency checks for the selected full attack profile.

This test deliberately does not import evaluator or runner code.  The final
FEATURE-SPEC bytes are the semantic authority; the profile may only bind
those bytes and declare its two explicit overrides.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import pathlib
import platform
import sys
import unittest
import warnings

import jsonschema


EVALUATOR_DIR = pathlib.Path(__file__).resolve().parents[1]
WAVE_ROOT = EVALUATOR_DIR.parent
PROFILE_PATH = WAVE_ROOT / "EXECUTABLE-ATTACK-PROFILE.json"
SCHEMA_PATH = WAVE_ROOT / "EXECUTABLE-ATTACK-PROFILE.schema.json"
FEATURE_SPEC_PATH = WAVE_ROOT / "feature-spec" / "FEATURE-SPEC.json"

EXPECTED_SECTION_POINTERS = {
    "/scope",
    "/input_boundary",
    "/predictor_output",
    "/feature_families",
    "/excluded_candidate_receipt_fields",
    "/string_transform",
    "/numeric_transform",
    "/model_preprocessing",
    "/classifier_plan",
    "/control_evaluation",
    "/confidence_intervals",
    "/permutation_plan",
    "/multiplicity",
    "/deterministic_tie_and_failure_rules",
    "/excluded_field_audit",
    "/false_green_risks",
    "/false_fail_risks",
    "/not_tested",
}

EXPECTED_FEATURE_IDS = [
    "F01_PUBLIC_INPUT_BYTES",
    "F02_ARGV_ENV_CWD",
    "F03_HOSTNAME_IDENTITY",
    "F04_DIRECTORY_AND_SHARED_STATE",
    "F05_PROCESS_NAMESPACE_FD",
    "F06_TIMING_AND_ERRORS",
    "F07_VISIBLE_CANARY",
]

EXPECTED_CLASSIFIER_IDS = [
    "C01_EXACT_CATEGORICAL_SCAN",
    "C02_L2_LOGISTIC",
    "C03_DECISION_STUMP",
    "C04_BOUNDED_TREE",
    "C05_KNN_11",
]

EXPECTED_EXTERNAL_BINDINGS = {
    "profile_adoption_receipt_sha256",
    "external_profile_anchor_receipt_sha256",
    "independent_full_evaluator_source_manifest_sha256",
    "D0_private_family_registry_sha256",
    "D1_private_family_registry_sha256",
    "formal_3200_slot_manifest_sha256",
    "precommit_sha256",
    "host_only_test_inventory_sha256",
    "frozen_prediction_applicability_audit_sha256",
    "preformal_3200_cost_rehearsal_receipt_sha256",
    "deterministic_replay_hash_manifest_sha256",
}

EXPECTED_BLOCKER_IDS = {
    "B01_PROFILE_ADOPTION_UNBOUND",
    "B02_EXTERNAL_PROFILE_BYTES_ANCHOR_UNBOUND",
    "B03_FULL_EVALUATOR_IMPLEMENTATION_UNBOUND",
    "B04_D0_PRIVATE_FAMILY_REGISTRY_UNBOUND",
    "B05_D1_PRIVATE_FAMILY_REGISTRY_UNBOUND",
    "B06_FORMAL_3200_SLOT_MANIFEST_UNBOUND",
    "B07_PRECOMMIT_AND_PERMUTATION_SEED_UNBOUND",
    "B08_HOST_ONLY_TEST_INVENTORY_UNBOUND",
    "B09_FROZEN_PREDICTION_APPLICABILITY_AUDIT_UNBOUND",
    "B10_PREFORMAL_3200_COST_REHEARSAL_UNRUN",
    "B11_DETERMINISTIC_REPLAY_HASH_MANIFEST_UNBOUND",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def resolve_json_pointer(document: object, pointer: str) -> object:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise AssertionError(f"not an absolute JSON Pointer: {pointer!r}")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        elif isinstance(current, dict):
            current = current[token]
        else:
            raise AssertionError(f"pointer traverses scalar at {raw_token!r}")
    return current


class FullAttackProfileConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile_raw = PROFILE_PATH.read_bytes()
        cls.schema_raw = SCHEMA_PATH.read_bytes()
        cls.feature_spec_raw = FEATURE_SPEC_PATH.read_bytes()
        cls.profile = json.loads(cls.profile_raw)
        cls.schema = json.loads(cls.schema_raw)
        cls.feature_spec = json.loads(cls.feature_spec_raw)

    def test_json_schema_is_valid_and_profile_conforms(self) -> None:
        jsonschema.Draft202012Validator.check_schema(self.schema)
        jsonschema.Draft202012Validator(self.schema).validate(self.profile)

    def test_feature_spec_raw_bytes_and_every_bound_subtree_match(self) -> None:
        binding = self.profile["feature_spec_binding"]
        resolved_path = (PROFILE_PATH.parent / binding["path_from_profile"]).resolve()
        self.assertEqual(resolved_path, FEATURE_SPEC_PATH.resolve())
        self.assertEqual(binding["raw_byte_length"], len(self.feature_spec_raw))
        self.assertEqual(binding["raw_bytes_sha256"], sha256_bytes(self.feature_spec_raw))
        self.assertEqual(binding["expected_schema"], self.feature_spec["schema"])
        self.assertEqual(binding["expected_spec_version"], self.feature_spec["spec_version"])

        sections = binding["resolved_sections"]
        pointers = [section["json_pointer"] for section in sections]
        ids = [section["id"] for section in sections]
        self.assertEqual(set(pointers), EXPECTED_SECTION_POINTERS)
        self.assertEqual(len(pointers), len(set(pointers)))
        self.assertEqual(len(ids), len(set(ids)))
        for section in sections:
            subtree = resolve_json_pointer(self.feature_spec, section["json_pointer"])
            self.assertEqual(
                section["canonical_json_sha256"],
                sha256_bytes(canonical_json_bytes(subtree)),
                section["json_pointer"],
            )

    def test_profile_does_not_copy_parent_semantic_sections(self) -> None:
        forbidden_top_level_copies = {
            "scope",
            "input_boundary",
            "predictor_output",
            "feature_families",
            "excluded_candidate_receipt_fields",
            "string_transform",
            "numeric_transform",
            "model_preprocessing",
            "classifier_plan",
            "control_evaluation",
            "confidence_intervals",
            "permutation_plan",
            "multiplicity",
            "deterministic_tie_and_failure_rules",
            "excluded_field_audit",
            "false_green_risks",
            "false_fail_risks",
            "not_tested",
        }
        self.assertTrue(forbidden_top_level_copies.isdisjoint(self.profile))
        self.assertEqual(
            self.profile["feature_spec_binding"]["override_pointer_allowlist"],
            ["/formal_population", "/permutation_plan/label_permutation"],
        )

    def test_formal_population_is_exactly_3200_and_power_basis_is_frozen(self) -> None:
        population = self.profile["formal_population_override"]
        expected = {
            "D0-HOST-LEAK": (100, 100, 50, 50, 5, 5, 200),
            "D1-OCI-CANARY": (100, 100, 50, 50, 5, 5, 200),
            "T-OCI-ISOLATED": (400, 2400, 200, 1200, 20, 120, 2800),
        }
        slot_sum = 0
        block_sum = 0
        for challenge, values in expected.items():
            item = population[challenge]
            self.assertEqual(
                (
                    item["calibration"],
                    item["fresh_holdout"],
                    item["calibration_per_role"],
                    item["holdout_per_role"],
                    item["calibration_blocks"],
                    item["holdout_blocks"],
                    item["total"],
                ),
                values,
            )
            self.assertEqual(item["calibration"], 2 * item["calibration_per_role"])
            self.assertEqual(item["fresh_holdout"], 2 * item["holdout_per_role"])
            self.assertEqual(item["calibration"], item["block_size"] * item["calibration_blocks"])
            self.assertEqual(item["fresh_holdout"], item["block_size"] * item["holdout_blocks"])
            self.assertEqual(item["total"], item["calibration"] + item["fresh_holdout"])
            slot_sum += item["total"]
            block_sum += item["calibration_blocks"] + item["holdout_blocks"]
        self.assertEqual(slot_sum, 3200)
        self.assertEqual(block_sum, 160)
        self.assertEqual(population["total_slots"], slot_sum)
        self.assertEqual(population["total_blocks"], block_sum)

        power = population["power_basis"]
        self.assertEqual(power["T_holdout_per_role"], 1200)
        self.assertEqual(power["attack_count"], 5)
        self.assertEqual(power["single_attack_pass_probability_lower_bound"], 0.982255)
        self.assertEqual(power["five_attack_union_bound_pass_probability_lower_bound"], 0.911276)
        rounded_union_bound = 1.0 - 5.0 * (
            1.0 - power["single_attack_pass_probability_lower_bound"]
        )
        self.assertLessEqual(
            abs(power["five_attack_union_bound_pass_probability_lower_bound"] - rounded_union_bound),
            0.000002,
        )

    def test_full_leaf_and_f01_to_f07_semantics_are_inherited_without_caps(self) -> None:
        surface = self.profile["inherited_attack_surface"]
        spec_feature_ids = [item["id"] for item in self.feature_spec["feature_families"]]
        self.assertEqual(spec_feature_ids, EXPECTED_FEATURE_IDS)
        self.assertEqual(surface["feature_family_ids"], EXPECTED_FEATURE_IDS)
        self.assertEqual(surface["candidate_visible_leaf_cap"], "NONE")
        self.assertEqual(surface["numeric_path_cap"], "NONE")
        self.assertEqual(surface["categorical_bucket_reduction"], "FORBIDDEN")
        self.assertEqual(surface["ngram_bucket_reduction"], "FORBIDDEN")
        self.assertTrue(surface["extract_from_raw_receipts_independently"])
        self.assertFalse(surface["runner_supplied_vectors_are_authoritative"])

        audit = self.feature_spec["excluded_field_audit"]
        self.assertEqual(audit["partition"], "EVERY_SCALAR_LEAF_EXACTLY_ONE_OF_INCLUDED_OR_EXCLUDED")
        self.assertIn("unclassified_paths_empty", audit["required_outputs"])
        self.assertEqual(self.feature_spec["input_boundary"]["unknown_field_policy"], "FAIL_CLOSED")
        self.assertEqual(self.feature_spec["input_boundary"]["missing_field_policy"], "FAIL_CLOSED")
        self.assertEqual(self.feature_spec["string_transform"]["ngram_n"], [1, 2, 3, 4])
        self.assertEqual(self.feature_spec["string_transform"]["ngram_bucket_count"], 4096)
        self.assertEqual(
            self.feature_spec["model_preprocessing"]["categorical"]["bucket_count"],
            16384,
        )

    def test_c01_to_c05_are_the_original_bound_parameters(self) -> None:
        classifiers = {item["id"]: item for item in self.feature_spec["classifier_plan"]}
        self.assertEqual(list(classifiers), EXPECTED_CLASSIFIER_IDS)
        self.assertEqual(self.profile["inherited_attack_surface"]["classifier_ids"], EXPECTED_CLASSIFIER_IDS)

        c01 = classifiers["C01_EXACT_CATEGORICAL_SCAN"]
        self.assertEqual(c01["minimum_total_calibration_support"], 10)
        self.assertEqual(c01["minimum_per_predicted_class_support"], 5)
        self.assertIn(
            "two_token_conjunction_from_TOP256_CALIBRATION_SUPPORT_TOKENS",
            c01["calibration_candidates"],
        )

        c02 = classifiers["C02_L2_LOGISTIC"]
        self.assertEqual(
            c02["optimizer"],
            "DETERMINISTIC_FULL_BATCH_GRADIENT_DESCENT_BACKTRACKING_ARMIJO",
        )
        self.assertIn("0_01", c02["objective"])
        self.assertEqual(c02["maximum_iterations"], 2000)
        self.assertEqual(c02["initial_step"], 1.0)
        self.assertEqual(c02["backtracking_factor"], 0.5)
        self.assertEqual(c02["armijo_c"], 0.0001)
        self.assertEqual(c02["gradient_linf_stop"], 1e-10)

        c03 = classifiers["C03_DECISION_STUMP"]
        self.assertEqual(c03["maximum_depth"], 1)
        self.assertEqual(c03["minimum_leaf"], 10)

        c04 = classifiers["C04_BOUNDED_TREE"]
        self.assertEqual(c04["maximum_depth"], 3)
        self.assertEqual(c04["minimum_leaf"], 10)
        self.assertEqual(c04["minimum_gain"], 1e-12)

        c05 = classifiers["C05_KNN_11"]
        self.assertEqual(c05["k"], 11)
        self.assertEqual(c05["boundary_distance_tie"], "INCLUDE_ALL_NEIGHBOURS_AT_KTH_DISTANCE")

    def test_classwise_ci_control_mapping_and_no_secondary_rescue(self) -> None:
        ci = self.feature_spec["confidence_intervals"]
        self.assertEqual(
            ci["method"],
            "CONSERVATIVE_EXACT_ONE_SIDED_CLOPPER_PEARSON_PER_CLASS_WITH_BONFERRONI_ALPHA_OVER_TWO_THEN_AVERAGE_CLASS_BOUNDS",
        )
        self.assertEqual(ci["class_tail_alpha"], 0.025)
        self.assertEqual(ci["control_threshold"], "LOWER_BALANCED_ACCURACY_GE_0_90")
        self.assertEqual(
            ci["T_equivalence_threshold"],
            "EVERY_PREDECLARED_CLASSIFIER_UPPER_BALANCED_ACCURACY_LE_0_55",
        )
        self.assertFalse(ci["ordinary_nonsignificant_p_value_is_equivalence"])

        mapping = self.profile["control_primary_mapping"]
        self.assertFalse(mapping["pool_D0_and_D1"])
        self.assertEqual(
            mapping["D0-HOST-LEAK"],
            {
                "expected_feature_family_id": "F04_DIRECTORY_AND_SHARED_STATE",
                "primary_classifier_id": "C01_EXACT_CATEGORICAL_SCAN",
                "secondary_detector_can_rescue_failed_primary": False,
            },
        )
        self.assertEqual(
            mapping["D1-OCI-CANARY"],
            {
                "expected_feature_family_id": "F07_VISIBLE_CANARY",
                "primary_classifier_id": "C01_EXACT_CATEGORICAL_SCAN",
                "secondary_detector_can_rescue_failed_primary": False,
            },
        )
        self.assertFalse(self.feature_spec["control_evaluation"]["secondary_detector_can_rescue_failed_primary"])

    def test_9999_block_preserving_frozen_prediction_override_and_host_holm(self) -> None:
        base = self.feature_spec["permutation_plan"]
        override = self.profile["permutation_override"]
        self.assertEqual(base["replicates"], 9999)
        self.assertEqual(override["replicates"], 9999)
        self.assertEqual(override["block_keys"], ["challenge", "phase", "block"])
        self.assertEqual(override["population"], "FRESH_HOLDOUT_ONLY")
        self.assertEqual(override["predictions"], "FROZEN_BEFORE_HOLDOUT_LABEL_JOIN")
        self.assertFalse(override["retrain_or_reselect_per_replicate"])
        self.assertEqual(override["seed_rule_json_pointer"], "/permutation_plan/seed")
        self.assertEqual(override["permutation_order_json_pointer"], "/permutation_plan/permutation_order")
        self.assertEqual(override["p_value_json_pointer"], "/permutation_plan/p_value")
        self.assertFalse(override["nonrejection_is_equivalence"])
        self.assertIn("RETRAIN_AND_RESCORE", base["label_permutation"])

        host = self.profile["host_only_holm"]
        multiplicity = self.feature_spec["multiplicity"]
        self.assertEqual(host["replicates"], 9999)
        self.assertEqual(host["predictor_matrix_import"], "FORBIDDEN")
        self.assertEqual(multiplicity["method"], "HOLM_STEP_DOWN")
        self.assertEqual(multiplicity["familywise_alpha"], 0.05)
        self.assertIn(host["family_id"], multiplicity["separate_families"])
        self.assertEqual(
            resolve_json_pointer(self.feature_spec, host["host_statistics_json_pointer"]),
            base["host_only_association_statistics"],
        )

    def test_numpy_float64_single_thread_einsum_provider_matches_current_machine(self) -> None:
        provider = self.profile["execution_provider"]
        thread_environment = provider["single_thread_environment"]
        self.assertEqual(
            set(thread_environment),
            {
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "VECLIB_MAXIMUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            },
        )
        self.assertEqual(set(thread_environment.values()), {"1"})
        for name, value in thread_environment.items():
            os.environ[name] = value

        import numpy as np

        self.assertEqual(platform.python_implementation(), provider["python"]["implementation"])
        self.assertEqual(platform.python_version(), provider["python"]["version"])
        self.assertEqual(sha256_bytes(pathlib.Path(sys.executable).resolve().read_bytes()), provider["python"]["executable_sha256"])
        self.assertEqual(np.__version__, provider["numpy"]["version"])
        self.assertEqual(platform.machine(), provider["platform"]["machine"])
        self.assertEqual(sys.byteorder, provider["platform"]["byte_order"])
        self.assertEqual(f"macOS-{platform.mac_ver()[0]}", provider["platform"]["os"])

        distribution = importlib.metadata.distribution(provider["numpy"]["distribution"])
        record_path = pathlib.Path(
            distribution.locate_file(f"numpy-{provider['numpy']['version']}.dist-info/RECORD")
        )
        self.assertEqual(
            sha256_bytes(record_path.read_bytes()),
            provider["numpy"]["distribution_record_sha256"],
        )
        config = np.__config__.CONFIG
        self.assertEqual(config["Build Dependencies"]["blas"]["name"], "accelerate")
        self.assertEqual(config["Build Dependencies"]["lapack"]["name"], "accelerate")
        self.assertEqual(
            config["SIMD Extensions"]["baseline"],
            provider["numpy"]["baseline_simd"],
        )

        semantics = provider["numeric_semantics"]
        self.assertEqual(semantics["dtype"], "float64")
        self.assertFalse(semantics["einsum_optimize"])
        x = np.arange(24, dtype=np.float64).reshape(6, 4)
        y = np.linspace(-1.0, 1.0, 4, dtype=np.float64)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            first = np.einsum("ij,j->i", x, y, optimize=False)
            second = np.einsum("ij,j->i", x, y, optimize=False)
        self.assertEqual(first.dtype, np.dtype("float64"))
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertTrue(np.isfinite(first).all())

    def test_replay_and_cost_ceilings_are_exact_and_cannot_reduce_leaf_coverage(self) -> None:
        replay = self.profile["deterministic_replay"]
        self.assertEqual(replay["independent_runs"], 2)
        self.assertEqual(replay["hash_algorithm"], "SHA256")
        self.assertEqual(replay["allowed_byte_differences"], 0)
        self.assertEqual(replay["allowed_prediction_differences"], 0)
        self.assertEqual(replay["allowed_statistic_differences"], 0)
        self.assertEqual(replay["warning_count_required"], 0)
        self.assertEqual(replay["nonfinite_count_required"], 0)
        self.assertEqual(len(replay["required_hash_classes"]), 10)
        self.assertEqual(len(set(replay["required_hash_classes"])), 10)

        cost = self.profile["cost_ceiling"]
        self.assertEqual(cost["preformal_rehearsal_population"], 3200)
        self.assertEqual(cost["candidate_visible_leaf_cap"], "NONE")
        self.assertEqual(
            cost["ceiling_exceeded_action"],
            "NOT_QUALIFIED_NO_AUTOMATIC_PROFILE_REDUCTION",
        )
        self.assertGreaterEqual(cost["maximum_resident_memory_bytes"], 4 * 1024**3)
        self.assertGreaterEqual(cost["maximum_temporary_derived_cache_bytes"], 2 * 1024**3)
        self.assertLessEqual(
            cost["maximum_feature_extraction_wall_seconds"]
            + cost["maximum_model_ci_and_permutation_wall_seconds"],
            cost["maximum_total_attack_phase_wall_seconds"],
        )
        self.assertFalse(cost["ceiling_pass_is_qualification_evidence"])

    def test_deferred_retraining_challenge_is_not_silently_claimed(self) -> None:
        deferred = self.profile["deferred_challenge"]
        self.assertEqual(deferred["id"], "MODEL-SELECTION-RANDOMIZATION")
        self.assertEqual(deferred["status"], "NOT_TESTED")
        self.assertIn("9999", deferred["omitted_operation"])
        self.assertIn("C01_TO_C05", deferred["omitted_operation"])
        self.assertEqual(len(deferred["applicability_preconditions"]), 7)
        self.assertEqual(
            {item["required_state"] for item in deferred["applicability_preconditions"]},
            {"MACHINE_VERIFIED_BEFORE_FORMAL_USE"},
        )
        self.assertEqual(
            deferred["precondition_failure_action"],
            "NOT_QUALIFIED_DO_NOT_USE_FROZEN_PREDICTION_SHORTCUT",
        )
        self.assertFalse(deferred["later_challenge_may_reuse_formal_holdout"])

    def test_every_unbound_machine_field_is_one_to_one_with_a_blocker(self) -> None:
        external = self.profile["external_bindings"]
        blockers = self.profile["blocking"]
        self.assertEqual(set(external), EXPECTED_EXTERNAL_BINDINGS)
        self.assertEqual({item["id"] for item in blockers}, EXPECTED_BLOCKER_IDS)
        self.assertEqual(len(blockers), len({item["id"] for item in blockers}))
        self.assertEqual(
            {item["external_binding"] for item in blockers},
            EXPECTED_EXTERNAL_BINDINGS,
        )
        for binding_id, value in external.items():
            self.assertEqual(value, {"state": "BLOCKING_UNBOUND", "sha256": None}, binding_id)
        self.assertEqual(self.profile["authority"]["formal_use_while_blocking_nonempty"], "FORBIDDEN")

    def test_all_scientific_results_are_not_tested_and_outputs_are_prohibited(self) -> None:
        states = self.profile["evidence_states"]
        non_result_keys = {
            "profile_adoption",
            "inherited_not_tested_json_pointer",
            "state_rule",
        }
        for key, value in states.items():
            if key not in non_result_keys:
                self.assertEqual(value, "NOT_TESTED", key)
        self.assertEqual(
            states["profile_adoption"],
            "ROOT_SELECTED_PREFORMAL_EXTERNAL_ANCHOR_PENDING",
        )
        inherited_not_tested = resolve_json_pointer(
            self.feature_spec,
            states["inherited_not_tested_json_pointer"],
        )
        self.assertTrue(inherited_not_tested)
        self.assertTrue(all(isinstance(item, str) and item for item in inherited_not_tested))
        self.assertEqual(self.profile["deferred_challenge"]["status"], "NOT_TESTED")
        self.assertEqual(self.profile["output_prohibitions"]["qualification_verdict"], "PROHIBITED")
        self.assertEqual(self.profile["output_prohibitions"]["treatment_score_or_ranking"], "PROHIBITED")
        self.assertIn(
            "NOT_TESTED",
            self.profile["output_prohibitions"]["claim_full_feature_spec_permutation_compatibility"],
        )


if __name__ == "__main__":
    unittest.main()
