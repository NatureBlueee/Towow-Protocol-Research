from __future__ import annotations

import importlib.util
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("f4_semantics_duel", ROOT / "f4_semantics_duel.py")
assert SPEC and SPEC.loader
duel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(duel)


def built():
    return duel.build_results()


def case(result, case_id):
    return next(item for item in result["case_results"] if item["case_id"] == case_id)


def family(case_result, family_id):
    return next(item for item in case_result["family_results"] if item["family"] == family_id)


def ba(family_result, phase="holdout"):
    value = family_result[phase]["balanced_accuracy"]
    return Fraction(value["numerator"], value["denominator"])


def test_current_results_are_byte_exact_rebuild():
    assert duel.RESULTS_PATH.read_bytes() == duel.pretty_bytes(built())


def test_and_negated_and_xor_separate_the_three_semantics():
    result = built()
    and_case = case(result, "D01_AND")
    negated_case = case(result, "D02_NEGATED_SIGNED_PATTERN")
    xor_case = case(result, "D03_XOR")

    assert [ba(item) for item in and_case["family_results"]] == [1, 1, 1]
    assert [ba(item) for item in negated_case["family_results"]] == [
        Fraction(13, 20),
        1,
        1,
    ]
    assert [ba(item) for item in xor_case["family_results"]] == [
        Fraction(3, 4),
        Fraction(3, 4),
        1,
    ]


def test_spurious_pair_wins_calibration_tie_then_fails_holdout():
    result = built()
    attacked = case(result, "D04_SPURIOUS_PAIR_TIE")
    for item in attacked["family_results"]:
        assert item["selected_rule"]["pair"] == ["a-spur-a", "a-spur-b"]
        assert item["misselected_registered_pair"] is True
        assert item["score_complexity_tie_count_before_canonical_bytes"] > 1
        assert ba(item, "calibration") == 1
        assert ba(item, "holdout") == Fraction(1, 2)


def test_support_four_rejects_but_five_admits_spurious_pattern():
    result = built()
    below = case(result, "D05_LOW_SUPPORT_BELOW_5")
    edge = case(result, "D06_LOW_SUPPORT_EDGE_SPURIOUS")
    for item in below["family_results"]:
        assert item["eligible_candidate_count"] == 0
        assert item["selected_rule"] is None
    for item in edge["family_results"]:
        assert item["eligible_candidate_count"] > 0
        assert item["selected_spurious_pattern"] is True
        assert ba(item, "calibration") == Fraction(5, 8)
        assert ba(item, "holdout") == Fraction(1, 2)


def test_identical_calibration_cannot_determine_unseen_state_class():
    fixtures = duel.load_fixtures()
    r_case = next(item for item in fixtures["cases"] if item["case_id"] == "D07_HOLDOUT_UNSEEN_STATE_IS_R")
    s_case = next(item for item in fixtures["cases"] if item["case_id"] == "D08_HOLDOUT_UNSEEN_STATE_IS_S")
    assert duel.canonical_bytes(r_case["calibration"]) == duel.canonical_bytes(s_case["calibration"])

    result = built()
    r_full = family(case(result, r_case["case_id"]), "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK")
    s_full = family(case(result, s_case["case_id"]), "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK")
    assert r_full["selected_rule_sha256"] == s_full["selected_rule_sha256"]
    assert ba(r_full) == 1
    assert ba(s_full) == Fraction(1, 2)
    assert r_full["coverage"]["holdout_unseen_pair_state_row_count"] == 20
    assert s_full["coverage"]["holdout_unseen_pair_state_row_count"] == 20


def test_oov_is_distinct_from_unseen_pair_state():
    result = built()
    attacked = case(result, "D09_HOLDOUT_OOV_TOKENS")
    for item in attacked["family_results"]:
        assert item["coverage"]["holdout_oov_row_count"] == 40
        assert item["coverage"]["holdout_unseen_pair_state_row_count"] == 0
        assert ba(item) == Fraction(1, 2)


def test_role_null_does_not_false_recover():
    result = built()
    placebo = case(result, "D10_ROLE_NULL_TRANSFER")
    for item in placebo["family_results"]:
        assert ba(item, "calibration") == 1
        assert ba(item, "holdout") == Fraction(1, 2)
        assert item["stable_recovery_calibration_and_holdout_exact_both_classes"] is False
    for summary in result["family_summaries"]:
        assert summary["role_null_false_recovery_at_ba_ge_0_90"] is False


def test_no_f4_allocation_is_zero_surface_not_an_executed_c04_result():
    allocation = built()["responsibility_allocation_comparison"]
    assert allocation["c01_f4_generated_candidates"] == 0
    assert allocation["c01_f4_conceptual_rule_space"] == 0
    assert allocation["current_holdout_predictions"] is None
    assert allocation["status"] == "RESPONSIBILITY_ALLOCATION_CANDIDATE_NOT_EXECUTED"
    assert {
        item["case_id"]: item["minimum_binary_tree_depth"]
        for item in allocation["two_bit_representation_upper_bound_only"]
    } == {"D01_AND": 2, "D02_NEGATED_SIGNED_PATTERN": 2, "D03_XOR": 2}
    assert all(
        item["representable_within_registered_C04_maximum_depth_3"]
        and not item["learned_or_holdout_validated_by_this_duel"]
        for item in allocation["two_bit_representation_upper_bound_only"]
    )
