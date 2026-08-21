import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent
sys.path.insert(0, str(PACKAGE))
import c01_minisuite as suite  # noqa: E402


def load(name):
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def case_result(results, case_id):
    return next(item for item in results["case_results"] if item["case_id"] == case_id)


def family_result(results, case_id, family):
    return next(
        item for item in case_result(results, case_id)["family_results"] if item["family"] == family
    )


def make_join(labels_doc, rows, schema):
    mapping = suite.labels_for_rows(labels_doc, rows)
    return {
        "assignments": [
            {"class_id": mapping[row_id], "row_id": row_id} for row_id in sorted(mapping)
        ],
        "schema": schema,
    }


def freeze_one(case, labels_doc, contract):
    calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
    join = make_join(labels_doc, calibration, "WAVE025_C01_CALIBRATION_JOIN_V3")
    staged = {
        "calibration-join.json": suite.canonical_bytes(join),
        "case.json": suite.canonical_bytes(case),
        "contract.json": suite.canonical_bytes(contract),
    }
    expected = {
        "calibration_join_sha256": suite.sha256_json(join),
        "case_sha256": suite.sha256_json(case),
        "contract_sha256": suite.sha256_json(contract),
    }
    return suite.invoke_capability_phase(
        "freeze", staged, expected, "frozen-package.output.json"
    )


def score_one(package, labels_doc, contract, expected_frozen_sha=None):
    holdout_ids = {
        item["row_id"] for item in package["family_freezes"][0]["holdout_predictions"]
    }
    all_labels = {item["row_id"]: item["class_id"] for item in labels_doc["labels"]}
    join = {
        "assignments": [
            {"class_id": all_labels[row_id], "row_id": row_id}
            for row_id in sorted(holdout_ids)
        ],
        "schema": "WAVE025_C01_HOLDOUT_JOIN_V3",
    }
    staged = {
        "contract.json": suite.canonical_bytes(contract),
        "frozen-package.json": suite.canonical_bytes(package),
        "holdout-join.json": suite.canonical_bytes(join),
    }
    expected = {
        "contract_sha256": suite.sha256_json(contract),
        "frozen_package_sha256": expected_frozen_sha or suite.sha256_json(package),
        "holdout_join_sha256": suite.sha256_json(join),
    }
    return suite.invoke_capability_phase("score", staged, expected, "scored-case.output.json")


def test_all_six_artifacts_are_byte_exact_canonical_and_current():
    artifacts = suite.build_all()
    assert len(artifacts) == 6
    for path, value in artifacts.items():
        raw = path.read_bytes()
        assert raw == suite.canonical_bytes(value)
        assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")


def test_freeze_minimal_capability_root_excludes_and_cannot_read_full_labels():
    features, labels = suite.build_cases()
    package, receipt = freeze_one(features["cases"][0], labels, suite.build_contract())
    names = {item["name"] for item in receipt["capability_root_initial_inventory"]}
    assert names == {"worker.py", "contract.json", "case.json", "calibration-join.json"}
    child = receipt["child_capability_receipt"]
    assert child["full_labels_artifact_probe_blocked"] is True
    assert child["actual_capability_read_set"] == [
        "$CAP/calibration-join.json",
        "$CAP/case.json",
        "$CAP/contract.json",
    ]
    assert child["actual_capability_write_set"] == ["$CAP/frozen-package.output.json"]
    assert child["denied_external_read_events"] == [
        "$EXTERNAL_SHA256/" + receipt["forbidden_probe_path_sha256"]
    ]
    assert receipt["forbidden_full_labels_artifact_sha256"] == hashlib.sha256(
        (PACKAGE / "CASES-LABELS.candidate.json").read_bytes()
    ).hexdigest()
    assert package["holdout_labels_received"] is False


def test_recursive_freeze_schema_rejects_nested_holdout_labels_and_row_extras():
    features, labels = suite.build_cases()
    contract = suite.build_contract()
    bad_case = copy.deepcopy(features["cases"][0])
    bad_case["holdout_labels"] = {"nested": "forbidden"}
    with pytest.raises(RuntimeError, match="recursively closed|label-like"):
        freeze_one(bad_case, labels, contract)
    bad_row = copy.deepcopy(features["cases"][0])
    bad_row["rows"][0]["metadata"] = {"role": "forbidden"}
    with pytest.raises(RuntimeError, match="recursively closed|label-like"):
        freeze_one(bad_row, labels, contract)


def test_score_recursive_schema_rejects_feature_rows_even_with_matching_mutated_hash():
    features, labels = suite.build_cases()
    contract = suite.build_contract()
    package, _ = freeze_one(features["cases"][0], labels, contract)
    mutated = copy.deepcopy(package)
    mutated["feature_rows"] = features["cases"][0]["rows"]
    # The attack is allowed to recompute the mutated bytes' hash. Recursive closure,
    # not a self-reported hash, must still reject it.
    with pytest.raises(RuntimeError, match="recursively closed"):
        score_one(mutated, labels, contract, suite.sha256_json(mutated))


def test_score_rejects_deep_label_like_key_even_inside_dynamic_rule_mapping():
    features, labels = suite.build_cases()
    contract = suite.build_contract()
    package, _ = freeze_one(features["cases"][3], labels, contract)
    mutated = copy.deepcopy(package)
    f2 = next(item for item in mutated["family_freezes"] if item["family"] == suite.FAMILIES[1])
    f2["selected_rule"]["mapping"]["holdout_labels"] = "R"
    with pytest.raises(RuntimeError, match="label-like key rejected"):
        score_one(mutated, labels, contract, suite.sha256_json(mutated))


def test_external_frozen_seal_rejects_synchronized_payload_mutation():
    features, labels = suite.build_cases()
    contract = suite.build_contract()
    package, receipt = freeze_one(features["cases"][0], labels, contract)
    sealed = receipt["external_output_sha256"]
    mutated = copy.deepcopy(package)
    mutated["description"] += " changed"
    with pytest.raises(RuntimeError, match="exact-byte binding mismatch"):
        score_one(mutated, labels, contract, sealed)


def test_zero_and_wrong_freeze_source_bindings_all_fail_closed():
    features, labels = suite.build_cases()
    case = features["cases"][0]
    contract = suite.build_contract()
    calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
    join = make_join(labels, calibration, "WAVE025_C01_CALIBRATION_JOIN_V3")
    staged = {
        "calibration-join.json": suite.canonical_bytes(join),
        "case.json": suite.canonical_bytes(case),
        "contract.json": suite.canonical_bytes(contract),
    }
    normal = {
        "calibration_join_sha256": suite.sha256_json(join),
        "case_sha256": suite.sha256_json(case),
        "contract_sha256": suite.sha256_json(contract),
    }
    for key in normal:
        zero = {**normal, key: "0" * 64}
        with pytest.raises(ValueError, match="nonzero"):
            suite.invoke_capability_phase("freeze", staged, zero, "frozen-package.output.json")
        wrong = {**normal, key: "1" * 64}
        with pytest.raises(RuntimeError, match="exact-byte binding mismatch"):
            suite.invoke_capability_phase("freeze", staged, wrong, "frozen-package.output.json")


def test_legacy_640_of_640_slot_oracle_recovers_zero_membership_ids():
    membership = load("OPAQUE-MEMBERSHIP.candidate.json")
    actual = {
        row_id
        for case in membership["cases"]
        for ids in case["phases"].values()
        for row_id in ids
    }
    legacy = set()
    for case in membership["cases"]:
        for phase in ("calibration", "holdout"):
            for slot in range(40):
                raw = f"WAVE025_C01_OPAQUE_ROW_V2\0{case['case_id']}\0{phase}\0{slot}".encode()
                legacy.add("o_" + hashlib.sha256(raw).hexdigest()[:24])
    assert len(actual) == 640
    assert actual.isdisjoint(legacy)
    assert not hasattr(suite, "opaque_row_id")
    assert not hasattr(suite, "label_assignments")


def test_metadata_only_cannot_rescue_p3_or_p7_above_chance():
    features, labels = suite.build_cases()
    contract_hash = "1" * 64
    for case_id in ("P3_PER_SLOT_FRESH_TOKEN", "P7_CONTEXT_TOTAL_OOV"):
        case = copy.deepcopy(next(item for item in features["cases"] if item["case_id"] == case_id))
        for row in case["rows"]:
            row["categories"] = []
            row["numerics"] = []
        calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
        holdout = [row for row in case["rows"] if row["phase"] == "holdout"]
        cal_labels = suite.labels_for_rows(labels, calibration)
        package = suite.freeze_case_core(
            case,
            cal_labels,
            contract_hash,
            suite.sha256_json(case),
            suite.sha256_json({"metadata_only": case_id}),
        )
        scored = suite.score_case_core(package, suite.labels_for_rows(labels, holdout))
        for family in suite.FAMILIES[:3]:
            result = next(item for item in scored["family_results"] if item["family"] == family)
            assert result["selected_rule"] is None
            assert result["calibration"]["balanced_accuracy"]["decimal"] == 0.5
            assert result["holdout"]["balanced_accuracy"]["decimal"] == 0.5
            assert result["stable_recovery_calibration_and_holdout_exact_both_classes"] is False


def test_feature_fixture_has_independent_membership_binding_and_no_plaintext_classes():
    features = load("CASES-FEATURES.candidate.json")
    membership_raw = (PACKAGE / "OPAQUE-MEMBERSHIP.candidate.json").read_bytes()
    assert features["membership_sha256"] == hashlib.sha256(membership_raw).hexdigest()
    suite.validate_feature_document(features)
    raw = suite.canonical_bytes(features).lower()
    for forbidden in (b'"r"', b'"s"', b"role-r", b"role-s", b"-r-", b"-s-"):
        assert forbidden not in raw


def test_f4_remains_unavailable_and_xor_lookup_is_not_substituted():
    results = load("RESULTS.candidate.json")
    f4 = family_result(results, "P6_XOR_TWO_TOKEN", suite.FAMILIES[3])
    assert f4["availability"] == "REJECTED_UNDERDETERMINED_NOT_EXECUTED"
    assert f4["selected_rule"] is None and f4["candidate_count_generated"] == 0
    assert f4["failure_reason"] == "RULE_FAMILY_SPEC_UNDERDETERMINED_NO_EXECUTION"


def test_stable_requires_calibration_and_holdout_exact_recall():
    features, labels = suite.build_cases()
    case = copy.deepcopy(features["cases"][0])
    calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
    holdout = [row for row in case["rows"] if row["phase"] == "holdout"]
    cal_labels = suite.labels_for_rows(labels, calibration)
    r_id = next(key for key, value in cal_labels.items() if value == "R")
    s_id = next(key for key, value in cal_labels.items() if value == "S")
    cal_labels[r_id], cal_labels[s_id] = "S", "R"
    package = suite.freeze_case_core(
        case, cal_labels, "1" * 64, suite.sha256_json(case), "2" * 64
    )
    scored = suite.score_case_core(package, suite.labels_for_rows(labels, holdout))
    f1 = next(item for item in scored["family_results"] if item["family"] == suite.FAMILIES[0])
    assert f1["holdout"]["balanced_accuracy"]["decimal"] == 1.0
    assert f1["calibration"]["balanced_accuracy"]["decimal"] == 0.95
    assert f1["stable_recovery_calibration_and_holdout_exact_both_classes"] is False


def test_f1_oov_truth_table_is_still_unique():
    results = load("RESULTS.candidate.json")
    f1 = family_result(results, "P8_F1_OOV_SELECTOR_ABSENCE", suite.FAMILIES[0])
    assert f1["holdout_oov_row_count"] == 20
    assert f1["stable_recovery_calibration_and_holdout_exact_both_classes"] is True
    rule = f1["selected_rule"]
    unknown = {
        "categories": [{"context": "Z", "count": 1, "token": "unknown"}],
        "numerics": [],
        "phase": "holdout",
        "row_id": "o_000000000000000000000000",
    }
    known = copy.deepcopy(unknown)
    known["categories"].append({**rule["selector"], "count": 1})
    assert suite.predict(rule, suite.FAMILIES[0], unknown) == rule["absent_class"]
    assert suite.predict(rule, suite.FAMILIES[0], known) == rule["present_class"]


def test_p2_and_actual_status_boundaries_remain_unknown():
    results = load("RESULTS.candidate.json")
    p2 = case_result(results, "P2_D1_CONDITIONAL_STABLE_EXACT_ATOM")
    assert p2["source_premise_status"].startswith("UNKNOWN_CONDITIONAL")
    assert results["conclusion"]["actual_d0_status"].startswith("UNKNOWN_NOT_RUN")
    assert results["conclusion"]["actual_d1_status"].startswith("UNKNOWN_NOT_RUN")
    assert "NOT_MODEL_INPUT_CANON" in results["status"]
    assert results["status"].endswith("G_AND_3200_NOT_RUN")


def test_positive_and_negative_synthetic_discrimination_remains():
    results = load("RESULTS.candidate.json")
    stable_key = "stable_recovery_calibration_and_holdout_exact_both_classes"
    assert family_result(results, "P1_D0_STABLE_EXACT_ATOM", suite.FAMILIES[0])[stable_key]
    assert all(
        not family_result(results, "P3_PER_SLOT_FRESH_TOKEN", family)[stable_key]
        for family in suite.FAMILIES
    )
    assert family_result(results, "P4_CONTEXT_COUNT_ONLY", suite.FAMILIES[1])[stable_key]
    assert family_result(results, "P5_NUMERIC_EXACT_AND_MISSING", suite.FAMILIES[2])[stable_key]
    assert family_result(results, "P7_CONTEXT_TOTAL_OOV", suite.FAMILIES[1])["failure_reason"] == "HOLDOUT_OOV_USED_FROZEN_FALLBACK"


def test_all_result_bindings_are_nonzero_and_exact():
    results = load("RESULTS.candidate.json")
    targets = {
        "contract_sha256": "C01-MINISUITE-CONTRACT.candidate.json",
        "features_sha256": "CASES-FEATURES.candidate.json",
        "frozen_selections_sha256": "FROZEN-SELECTIONS.candidate.json",
        "labels_sha256": "CASES-LABELS.candidate.json",
        "membership_sha256": "OPAQUE-MEMBERSHIP.candidate.json",
    }
    for key, name in targets.items():
        expected = results["artifact_bindings"][key]
        suite.require_binding(expected, key)
        assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == expected
    implementation = results["implementation_bindings"]
    implementation_targets = {
        "generator_sha256": "c01_minisuite.py",
        "membership_initializer_sha256": "initialize_membership_sources.py",
        "readme_sha256": "README.md",
        "tests_sha256": "tests/test_c01_minisuite.py",
    }
    for key, name in implementation_targets.items():
        suite.require_binding(implementation[key], key)
        assert hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest() == implementation[key]
    root = PACKAGE.parent.parent
    external_targets = {
        "d0_control_design_candidate_sha256": root
        / "control-registries/D0-CONTROL-DESIGN.candidate.json",
        "public_control_family_registration_sha256": root
        / "control-registries/PUBLIC-CONTROL-FAMILY-REGISTRATION.preformal-candidate.json",
    }
    for key, path in external_targets.items():
        binding = results["external_public_source_bindings"][key]
        suite.require_binding(binding, key)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding
    assert results["external_public_source_bindings"]["private_control_registry_read"] is False
