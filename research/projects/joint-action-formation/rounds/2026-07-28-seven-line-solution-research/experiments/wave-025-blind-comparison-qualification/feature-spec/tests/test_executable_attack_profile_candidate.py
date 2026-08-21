from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "EXECUTABLE-ATTACK-PROFILE.candidate.json"
SCHEMA_PATH = ROOT / "EXECUTABLE-ATTACK-PROFILE.candidate.schema.json"


class SchemaValidationError(ValueError):
    pass


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_ref(root_schema: dict[str, Any], reference: str) -> dict[str, Any]:
    if not reference.startswith("#/"):
        raise SchemaValidationError(f"external ref is forbidden: {reference}")
    value: Any = root_schema
    for part in reference[2:].split("/"):
        value = value[part.replace("~1", "/").replace("~0", "~")]
    if not isinstance(value, dict):
        raise SchemaValidationError(f"ref does not resolve to a schema object: {reference}")
    return value


def validate(instance: Any, schema: dict[str, Any], root_schema: dict[str, Any], path: str = "$") -> None:
    if "$ref" in schema:
        validate(instance, resolve_ref(root_schema, schema["$ref"]), root_schema, path)
        return
    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{path}: expected const {schema['const']!r}, got {instance!r}")
    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value is not in enum")

    kind = schema.get("type")
    if kind == "object":
        if not isinstance(instance, dict):
            raise SchemaValidationError(f"{path}: expected object")
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        missing = sorted(required - set(instance))
        if missing:
            raise SchemaValidationError(f"{path}: missing {missing}")
        extra = sorted(set(instance) - set(properties))
        if extra and schema.get("additionalProperties") is False:
            raise SchemaValidationError(f"{path}: unexpected {extra}")
        for key, value in instance.items():
            if key in properties:
                validate(value, properties[key], root_schema, f"{path}.{key}")
        return
    if kind == "array":
        if not isinstance(instance, list):
            raise SchemaValidationError(f"{path}: expected array")
        if len(instance) < schema.get("minItems", 0):
            raise SchemaValidationError(f"{path}: too few items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            raise SchemaValidationError(f"{path}: too many items")
        if schema.get("uniqueItems"):
            rendered = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in instance]
            if len(rendered) != len(set(rendered)):
                raise SchemaValidationError(f"{path}: duplicate array items")
        prefix = schema.get("prefixItems", [])
        for index, item_schema in enumerate(prefix):
            if index < len(instance):
                validate(instance[index], item_schema, root_schema, f"{path}[{index}]")
        item_schema = schema.get("items")
        if item_schema is False and len(instance) > len(prefix):
            raise SchemaValidationError(f"{path}: items beyond closed prefix")
        if isinstance(item_schema, dict):
            start = len(prefix) if prefix else 0
            for index in range(start, len(instance)):
                validate(instance[index], item_schema, root_schema, f"{path}[{index}]")
        return
    if kind == "string":
        if not isinstance(instance, str):
            raise SchemaValidationError(f"{path}: expected string")
        if len(instance) < schema.get("minLength", 0):
            raise SchemaValidationError(f"{path}: string too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            raise SchemaValidationError(f"{path}: pattern mismatch")
    elif kind == "integer":
        if isinstance(instance, bool) or not isinstance(instance, int):
            raise SchemaValidationError(f"{path}: expected integer")
    elif kind == "number":
        if isinstance(instance, bool) or not isinstance(instance, (int, float)) or not math.isfinite(instance):
            raise SchemaValidationError(f"{path}: expected finite number")
    elif kind == "boolean":
        if not isinstance(instance, bool):
            raise SchemaValidationError(f"{path}: expected boolean")
    elif kind == "null":
        if instance is not None:
            raise SchemaValidationError(f"{path}: expected null")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            raise SchemaValidationError(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            raise SchemaValidationError(f"{path}: above maximum")


def iter_schema_nodes(value: Any, path: str = "$"):
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from iter_schema_nodes(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_schema_nodes(child, f"{path}[{index}]")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def permutation_replicates(profile: dict[str, Any], family_size: int) -> int:
    permutation = profile["statistics"]["permutation"]
    alpha = profile["statistics"]["holm"]["familywise_alpha"]
    raw_minimum = math.ceil(family_size / alpha) - 1
    target = max(permutation["base_replicates"], raw_minimum)
    return math.ceil((target + 1) / 1000) * 1000 - 1


class ExecutableAttackProfileCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_json(PROFILE_PATH)
        cls.schema = load_json(SCHEMA_PATH)

    def test_candidate_validates_against_dependency_free_schema_subset(self) -> None:
        validate(self.profile, self.schema, self.schema)

    def test_every_object_schema_is_closed_and_exact(self) -> None:
        for path, node in iter_schema_nodes(self.schema):
            if node.get("type") != "object":
                continue
            self.assertIs(node.get("additionalProperties"), False, path)
            self.assertEqual(set(node.get("required", [])), set(node.get("properties", {})), path)

    def test_unknown_and_missing_nested_fields_fail_closed(self) -> None:
        extra = copy.deepcopy(self.profile)
        extra["learned_matrix"]["numeric"]["role"] = "S"
        with self.assertRaises(SchemaValidationError):
            validate(extra, self.schema, self.schema)
        missing = copy.deepcopy(self.profile)
        del missing["statistics"]["confidence_intervals"]["class_tail_alpha"]
        with self.assertRaises(SchemaValidationError):
            validate(missing, self.schema, self.schema)

    def test_derivation_hashes_bind_existing_full_spec_and_redteam(self) -> None:
        derivation = self.profile["derivation"]
        self.assertEqual(
            derivation["full_feature_spec_sha256"],
            file_sha256(ROOT / "FEATURE-SPEC.json"),
        )
        self.assertEqual(
            derivation["redteam_sha256"],
            file_sha256(ROOT / "EXECUTABLE-PROFILE-REDTEAM.md"),
        )

    def test_formal_population_is_balanced_and_totals_3200(self) -> None:
        population = self.profile["formal_population"]
        slot_total = 0
        block_total = 0
        for challenge in ("D0-HOST-LEAK", "D1-OCI-CANARY", "T-OCI-ISOLATED"):
            stratum = population[challenge]
            self.assertEqual(stratum["calibration"], 2 * stratum["calibration_per_role"])
            self.assertEqual(stratum["holdout"], 2 * stratum["holdout_per_role"])
            self.assertEqual(stratum["calibration"], stratum["block_size"] * stratum["calibration_blocks"])
            self.assertEqual(stratum["holdout"], stratum["block_size"] * stratum["holdout_blocks"])
            slot_total += stratum["calibration"] + stratum["holdout"]
            block_total += stratum["calibration_blocks"] + stratum["holdout_blocks"]
        self.assertEqual(slot_total, population["total_slots"])
        self.assertEqual(block_total, population["total_blocks"])
        self.assertEqual(population["total_slots"], 3200)
        self.assertEqual(population["T-OCI-ISOLATED"]["calibration"], 400)
        self.assertEqual(population["T-OCI-ISOLATED"]["holdout"], 2400)
        self.assertEqual(population["T-OCI-ISOLATED"]["holdout_per_role"], 1200)

    def test_seven_families_are_distinct_and_all_direct_scanned(self) -> None:
        families = self.profile["feature_families"]
        expected_ids = [
            "F01_PUBLIC_INPUT_BYTES",
            "F02_ARGV_ENV_CWD",
            "F03_HOSTNAME_IDENTITY",
            "F04_DIRECTORY_AND_SHARED_STATE",
            "F05_PROCESS_NAMESPACE_FD",
            "F06_TIMING_AND_ERRORS",
            "F07_VISIBLE_CANARY",
        ]
        self.assertEqual([family["id"] for family in families], expected_ids)
        self.assertTrue(all(family["direct_scan_required"] for family in families))
        self.assertTrue(all(family["mandatory_feature_groups"] for family in families))
        self.assertEqual(len({root for family in families for root in family["candidate_visible_roots"]}), 16)

    def test_leaf_partition_and_direct_scan_are_not_subject_to_learned_quota(self) -> None:
        audit = self.profile["leaf_audit"]
        self.assertEqual(audit["unclassified_paths_required_value"], [])
        self.assertFalse(audit["audit_members_are_predictors"])
        self.assertEqual(len(audit["excluded_fields_exact"]), 5)
        excluded_paths = {item["path_pattern"] for item in audit["excluded_fields_exact"]}
        self.assertEqual(
            excluded_paths,
            {"/schema", "/collector_version", "/contract/**", "/input_contract/parsed/schema", "/subject_input/path"},
        )
        direct = self.profile["raw_direct_scan"]
        self.assertFalse(direct["learned_matrix_quota_applies"])
        self.assertEqual(direct["minimum_total_calibration_support"], 10)
        self.assertEqual(direct["minimum_per_predicted_class_support"], 5)

    def test_learned_width_closes_exactly_to_5831(self) -> None:
        matrix = self.profile["learned_matrix"]
        family_count = matrix["family_count"]
        numeric = matrix["numeric"]
        categorical = matrix["categorical"]
        lexical = matrix["lexical"]
        norms = matrix["family_norms"]
        quota_sum = sum(item["learned_numeric_quota"] for item in self.profile["feature_families"])
        self.assertEqual(quota_sum, family_count * numeric["paths_per_family"])
        self.assertEqual(numeric["maximum_selected_paths"], quota_sum)
        expected_numeric_width = quota_sum * (1 + numeric["missing_bit_per_path"])
        self.assertEqual(numeric["maximum_width_including_missing"], expected_numeric_width)
        expected_categorical = family_count * categorical["banks_per_family"] * categorical["dimensions_per_bank"]
        self.assertEqual(categorical["total_width"], expected_categorical)
        self.assertEqual(len(categorical["bank_domains"]), categorical["banks_per_family"])
        expected_lexical = family_count * lexical["dimensions_per_family"]
        self.assertEqual(lexical["total_width"], expected_lexical)
        self.assertEqual(norms["total_width"], family_count)
        expected_total = expected_numeric_width + expected_categorical + expected_lexical + norms["total_width"]
        self.assertEqual(matrix["maximum_total_width"], expected_total)
        self.assertEqual(expected_total, 5831)
        self.assertEqual(
            self.profile["cost_and_replay_ceiling"]["maximum_learned_width"],
            expected_total,
        )

    def test_attack_set_and_load_bearing_parameters_are_exact(self) -> None:
        attacks = {attack["id"]: attack for attack in self.profile["attacks"]}
        expected = {"A-DIRECT", "A-LOGISTIC", "A-STUMP", "A-TREE3", "A-KNN5", "A-KNN11"}
        self.assertEqual(set(attacks), expected)
        self.assertEqual(attacks["A-TREE3"]["maximum_depth"], 3)
        self.assertEqual(attacks["A-STUMP"]["maximum_depth"], 1)
        self.assertEqual(attacks["A-KNN5"]["k"], 5)
        self.assertEqual(attacks["A-KNN11"]["k"], 11)
        self.assertEqual(
            attacks["A-KNN5"]["neighbour_order_reuse_group"],
            attacks["A-KNN11"]["neighbour_order_reuse_group"],
        )
        logistic = attacks["A-LOGISTIC"]
        self.assertEqual(logistic["l2"], 0.01)
        self.assertEqual(logistic["maximum_iterations"], 500)
        self.assertEqual(logistic["nonconvergence"], "PROFILE_ABNORMAL_NO_CHANCE_SCORE")

    def test_classwise_cp_and_thresholds_are_frozen_without_p_value_equivalence(self) -> None:
        statistics = self.profile["statistics"]
        intervals = statistics["confidence_intervals"]
        self.assertEqual(
            intervals["decision_method"],
            "CLASS_WISE_CLOPPER_PEARSON_ONE_SIDED_BONFERRONI_THEN_AVERAGE",
        )
        self.assertAlmostEqual(intervals["class_tail_alpha"], (1 - intervals["confidence"]) / 2)
        self.assertEqual(intervals["balanced_total_cp_role"], "DIAGNOSTIC_ONLY")
        self.assertFalse(statistics["thresholds"]["ordinary_p_gt_0_05_is_equivalence"])
        self.assertFalse(statistics["holm"]["nonrejection_is_equivalence"])

    def test_permutation_B_formula_has_holm_resolution(self) -> None:
        self.assertEqual(permutation_replicates(self.profile, 5), 999)
        self.assertEqual(permutation_replicates(self.profile, 50), 999)
        self.assertEqual(permutation_replicates(self.profile, 51), 1999)
        self.assertEqual(permutation_replicates(self.profile, 100), 1999)
        alpha = self.profile["statistics"]["holm"]["familywise_alpha"]
        for family_size in (1, 5, 50, 51, 100, 137):
            replicates = permutation_replicates(self.profile, family_size)
            self.assertLessEqual(1 / (replicates + 1), alpha / family_size)
            self.assertEqual(replicates % 1000, 999)
        permutation = self.profile["statistics"]["permutation"]
        self.assertFalse(permutation["retrain_models_per_permutation"])
        self.assertTrue(permutation["preserve_role_balance"])

    def test_D0_D1_controls_are_separate_preanchor_primary_gates(self) -> None:
        controls = self.profile["positive_controls"]
        self.assertFalse(controls["pool_D0_and_D1"])
        self.assertEqual(controls["registry_freeze"], "BEFORE_EXTERNAL_ANCHOR")
        attack_ids = {attack["id"] for attack in self.profile["attacks"]}
        self.assertEqual(set(controls["allowed_primary_detector_ids"]), attack_ids)
        for challenge in ("D0-HOST-LEAK", "D1-OCI-CANARY"):
            self.assertFalse(controls[challenge]["registered_family_selector_is_predictor"])
            self.assertFalse(controls[challenge]["secondary_can_rescue_primary"])

    def test_host_only_fields_are_excluded_and_audited_separately(self) -> None:
        host = self.profile["host_only_audit"]
        forbidden = set(self.profile["receipt_contract"]["forbidden_predictor_sources"])
        self.assertTrue(set(host["excluded_from_predictor_exact"]).issubset(forbidden))
        self.assertTrue(host["association_audit_required"])
        self.assertFalse(host["may_copy_association_fields_into_learned_matrix"])
        self.assertIn(host["permutation_family"], self.profile["statistics"]["holm"]["families"])

    def test_abnormal_conditions_cost_and_replay_are_fail_closed(self) -> None:
        abnormal = self.profile["abnormal_fail_closed"]
        codes = {item["code"] for item in abnormal["conditions"]}
        required = {
            "UNKNOWN_OR_MISSING_SCHEMA_FIELD",
            "UNCLASSIFIED_RAW_LEAF",
            "REQUIRED_FEATURE_FAMILY_MISSING",
            "MANDATORY_PATH_OR_CONTROL_REGISTRY_MISSING",
            "FEATURE_CAP_OVERFLOW",
            "CLASSIFIER_NONCONVERGENCE_OR_EXCEPTION",
            "HOLDOUT_ADAPTATION",
            "PERMUTATION_RESOLUTION_INADEQUATE",
            "PROFILE_COST_CEILING_EXCEEDED",
            "DETERMINISTIC_REPLAY_DRIFT",
        }
        self.assertTrue(required.issubset(codes))
        self.assertFalse(abnormal["may_translate_abnormal_to_chance"])
        self.assertFalse(abnormal["may_reduce_profile_after_formal_data"])
        ceiling = self.profile["cost_and_replay_ceiling"]
        self.assertEqual(
            ceiling["feature_extraction_wall_seconds"] + ceiling["model_and_statistics_wall_seconds"],
            ceiling["attack_phase_total_wall_seconds"],
        )
        self.assertEqual(set(ceiling["deterministic_replay"].values()), {0})
        self.assertTrue(ceiling["preformal_benchmark"]["required"])
        self.assertEqual(ceiling["maximum_holdout_rows_per_challenge"], 2400)
        self.assertEqual(ceiling["preformal_benchmark"]["receipt_population"], 3200)
        self.assertFalse(ceiling["preformal_benchmark"]["ceiling_pass_is_formal_qualification"])
        self.assertEqual(ceiling["current_evidence_state"], "CEILINGS_NOT_YET_BENCHMARKED")

    def test_candidate_has_no_result_or_automatic_promotion_and_explicit_not_tested(self) -> None:
        self.assertEqual(self.profile["scope"]["result_state"], "NO_RESULT")
        self.assertEqual(self.profile["scope"]["actual_comparative_runs"], 0)
        self.assertFalse(self.profile["authority"]["may_produce_qualification_verdict"])
        self.assertFalse(self.profile["authority"]["may_rank_treatments"])
        self.assertFalse(self.profile["adoption_gate"]["automatic_promotion"])
        self.assertEqual(self.profile["adoption_gate"]["formal_use_before_adoption"], "FORBIDDEN")
        not_tested = set(self.profile["not_tested"])
        expected = {
            "DYNAMIC_FIXED_BROKER_AND_EARLIEST_LAWFUL_DIVERGENCE",
            "CROSS_RUN_PROVIDER_OR_HUMAN_MEMORY",
            "EVALUATOR_TRUTH_VALIDITY",
            "NATIVE_TREATMENT_QUALIFICATION_OR_COMPARISON",
            "MICROARCHITECTURAL_OR_PHYSICAL_SIDE_CHANNELS",
            "ARBITRARY_FRESH_UNIQUE_CODEBOOK",
            "HIGHER_THAN_THREE_WAY_INTERACTION_OR_PRIVATE_DECODER",
            "9999_PERMUTATION_RESOLUTION",
        }
        self.assertTrue(expected.issubset(not_tested))


if __name__ == "__main__":
    unittest.main()
