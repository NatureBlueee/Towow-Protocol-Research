#!/usr/bin/env python3
"""Bounded synthetic duel for the underdetermined Wave025 C01/F4 semantics.

This program does not import or modify the current C01 minisuite.  It freezes
three explicit pair semantics, applies the same calibration selector to each,
freezes holdout predictions before scoring labels, and reports a fourth
responsibility allocation in which C01 has no F4 and C04 would own
interactions only after its own machine semantics are closed.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
FIXTURES_PATH = ROOT / "FIXTURES.json"
RESULTS_PATH = ROOT / "RESULTS.json"
FEATURE_SPEC_ROOT = ROOT.parent

CLASSES = ("R", "S")
FALLBACK_CLASS = "R"
FAMILIES = (
    "STRICT_POSITIVE_AND",
    "SIGNED_LITERAL_SINGLE_PATTERN",
    "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK",
)
FAMILY_COMPLEXITY = {
    "STRICT_POSITIVE_AND": 3,
    "SIGNED_LITERAL_SINGLE_PATTERN": 3,
    "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK": 6,
}
SOURCE_PATHS = {
    "feature_spec": FEATURE_SPEC_ROOT / "FEATURE-SPEC.json",
    "model_input_redteam": FEATURE_SPEC_ROOT / "MODEL-INPUT-V2S-PROPOSAL-A-REDTEAM.md",
    "c01_minisuite_redteam": FEATURE_SPEC_ROOT / "model-input-c01-minisuite/INDEPENDENT-REDTEAM.md",
    "c01_v3_contract": FEATURE_SPEC_ROOT / "model-input-c01-minisuite/C01-MINISUITE-CONTRACT.candidate.json",
    "c01_v3_results": FEATURE_SPEC_ROOT / "model-input-c01-minisuite/RESULTS.candidate.json",
    "public_control_registration": FEATURE_SPEC_ROOT.parent / "control-registries/PUBLIC-CONTROL-FAMILY-REGISTRATION.preformal-candidate.json",
    "d0_control_design": FEATURE_SPEC_ROOT.parent / "control-registries/D0-CONTROL-DESIGN.candidate.json",
}


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def pretty_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fraction_object(value: Fraction) -> dict[str, Any]:
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
        "decimal": float(value),
    }


def load_fixtures() -> dict[str, Any]:
    value = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "WAVE025_F4_SEMANTICS_DUEL_FIXTURES_V1":
        raise ValueError("unexpected fixture schema")
    if value.get("classes") != list(CLASSES):
        raise ValueError("fixture classes must be exactly R,S")
    ids = [case.get("case_id") for case in value.get("cases", [])]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("case_id values must be nonempty and unique")
    return value


def expand_phase(case_id: str, phase: str, groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    index = 0
    for group in groups:
        if set(group) != {"label", "count", "tokens"}:
            raise ValueError(f"{case_id}/{phase}: group keys are not closed")
        label = group["label"]
        count = group["count"]
        tokens = group["tokens"]
        if label not in CLASSES or not isinstance(count, int) or count <= 0:
            raise ValueError(f"{case_id}/{phase}: invalid label or count")
        if not isinstance(tokens, list) or any(not isinstance(x, str) or not x for x in tokens):
            raise ValueError(f"{case_id}/{phase}: invalid token")
        if len(tokens) != len(set(tokens)):
            raise ValueError(f"{case_id}/{phase}: duplicate token in row")
        frozen_tokens = tuple(sorted(tokens, key=lambda x: x.encode("utf-8")))
        for _ in range(count):
            rows.append(
                {
                    "row_id": f"{case_id}-{phase}-{index:03d}",
                    "tokens": frozen_tokens,
                    "label": label,
                }
            )
            index += 1
    if Counter(row["label"] for row in rows) != Counter({"R": 20, "S": 20}):
        raise ValueError(f"{case_id}/{phase}: duel requires exactly 20 rows per class")
    return rows


def freeze_universe(calibration_rows: list[dict[str, Any]], top_token_limit: int) -> dict[str, Any]:
    support: Counter[str] = Counter()
    for row in calibration_rows:
        support.update(set(row["tokens"]))
    top_tokens = sorted(support, key=lambda token: (-support[token], token.encode("utf-8")))[
        :top_token_limit
    ]
    pairs = [list(pair) for pair in itertools.combinations(top_tokens, 2)]
    return {
        "top_token_limit": top_token_limit,
        "top_tokens": top_tokens,
        "row_presence_support": {token: support[token] for token in top_tokens},
        "pairs": pairs,
    }


def pair_state(tokens: Iterable[str], pair: Iterable[str]) -> str:
    present = set(tokens)
    a, b = pair
    return ("1" if a in present else "0") + ("1" if b in present else "0")


def other_class(label: str) -> str:
    return "S" if label == "R" else "R"


def finalize_rule(rule: dict[str, Any]) -> dict[str, Any]:
    raw = canonical_bytes(rule)
    result = dict(rule)
    result["canonical_byte_length_without_binding"] = len(raw)
    result["canonical_sha256_without_binding"] = sha256_bytes(raw)
    return result


def semantic_rule_bytes(rule: dict[str, Any]) -> bytes:
    """Tie on semantic fields, not on derived hash/length metadata."""
    return canonical_bytes(
        {
            key: value
            for key, value in rule.items()
            if key not in {"canonical_byte_length_without_binding", "canonical_sha256_without_binding"}
        }
    )


def candidate_rules(
    family: str, universe: dict[str, Any], calibration_rows: list[dict[str, Any]]
) -> Iterable[dict[str, Any]]:
    for pair_list in universe["pairs"]:
        pair = tuple(pair_list)
        if family == "STRICT_POSITIVE_AND":
            for match_class in CLASSES:
                yield finalize_rule(
                    {
                        "schema": "WAVE025_F4_DUEL_RULE_V1",
                        "family": family,
                        "pair": list(pair),
                        "target_state": "11",
                        "match_class": match_class,
                        "nonmatch_class": other_class(match_class),
                        "complexity_units": FAMILY_COMPLEXITY[family],
                        "unseen_state_behavior": "TOTAL_MATCH_VS_NONMATCH_NO_SPECIAL_FALLBACK",
                    }
                )
        elif family == "SIGNED_LITERAL_SINGLE_PATTERN":
            for target_state in ("00", "01", "10", "11"):
                for match_class in CLASSES:
                    yield finalize_rule(
                        {
                            "schema": "WAVE025_F4_DUEL_RULE_V1",
                            "family": family,
                            "pair": list(pair),
                            "target_state": target_state,
                            "match_class": match_class,
                            "nonmatch_class": other_class(match_class),
                            "complexity_units": FAMILY_COMPLEXITY[family],
                            "unseen_state_behavior": "TOTAL_MATCH_VS_NONMATCH_NO_SPECIAL_FALLBACK",
                        }
                    )
        elif family == "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK":
            state_counts: dict[str, Counter[str]] = defaultdict(Counter)
            for row in calibration_rows:
                state_counts[pair_state(row["tokens"], pair)][row["label"]] += 1
            mapping = {
                state: ("S" if counts["S"] > counts["R"] else "R")
                for state, counts in sorted(state_counts.items())
            }
            yield finalize_rule(
                {
                    "schema": "WAVE025_F4_DUEL_RULE_V1",
                    "family": family,
                    "pair": list(pair),
                    "mapping": mapping,
                    "unseen_state_fallback_class": FALLBACK_CLASS,
                    "complexity_units": FAMILY_COMPLEXITY[family],
                    "unseen_state_behavior": "PREDICT_R_WITHOUT_RESELECTION",
                }
            )
        else:
            raise ValueError(f"unknown family {family}")


def predict_one(rule: dict[str, Any] | None, tokens: Iterable[str]) -> str:
    if rule is None:
        return FALLBACK_CLASS
    state = pair_state(tokens, rule["pair"])
    if rule["family"] in ("STRICT_POSITIVE_AND", "SIGNED_LITERAL_SINGLE_PATTERN"):
        return rule["match_class"] if state == rule["target_state"] else rule["nonmatch_class"]
    if rule["family"] == "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK":
        return rule["mapping"].get(state, rule["unseen_state_fallback_class"])
    raise ValueError("unknown rule family")


def predictions(rule: dict[str, Any] | None, rows: list[dict[str, Any]]) -> list[str]:
    return [predict_one(rule, row["tokens"]) for row in rows]


def metrics(rows: list[dict[str, Any]], predicted: list[str]) -> dict[str, Any]:
    if len(rows) != len(predicted):
        raise ValueError("row/prediction length mismatch")
    true_support = Counter(row["label"] for row in rows)
    predicted_support = Counter(predicted)
    recalls: dict[str, Fraction] = {}
    for label in CLASSES:
        correct = sum(
            row["label"] == label and guess == label for row, guess in zip(rows, predicted)
        )
        recalls[label] = Fraction(correct, true_support[label])
    balanced_accuracy = sum(recalls.values(), Fraction(0, 1)) / len(CLASSES)
    return {
        "balanced_accuracy": fraction_object(balanced_accuracy),
        "recall_by_class": {label: fraction_object(recalls[label]) for label in CLASSES},
        "true_class_support": {label: true_support[label] for label in CLASSES},
        "predicted_class_support": {label: predicted_support[label] for label in CLASSES},
    }


def metric_fraction(value: dict[str, Any]) -> Fraction:
    return Fraction(value["numerator"], value["denominator"])


def eligible(
    candidate_metrics: dict[str, Any], row_count: int, minimum_total: int, minimum_each: int
) -> bool:
    supports = candidate_metrics["predicted_class_support"]
    return row_count >= minimum_total and all(supports[label] >= minimum_each for label in CLASSES)


def state_support(rows: list[dict[str, Any]], pair: list[str]) -> dict[str, int]:
    counts = Counter(pair_state(row["tokens"], pair) for row in rows)
    return {state: counts[state] for state in ("00", "01", "10", "11")}


def select_rule(
    family: str,
    universe: dict[str, Any],
    calibration_rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> dict[str, Any]:
    generated = 0
    ranked: list[tuple[Fraction, int, bytes, dict[str, Any], dict[str, Any]]] = []
    for rule in candidate_rules(family, universe, calibration_rows):
        generated += 1
        candidate_metrics = metrics(calibration_rows, predictions(rule, calibration_rows))
        if not eligible(
            candidate_metrics,
            len(calibration_rows),
            selection["minimum_total_calibration_support"],
            selection["minimum_predicted_support_each_class"],
        ):
            continue
        score = metric_fraction(candidate_metrics["balanced_accuracy"])
        ranked.append(
            (
                score,
                rule["complexity_units"],
                semantic_rule_bytes(rule),
                rule,
                candidate_metrics,
            )
        )
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    if not ranked:
        return {
            "generated": generated,
            "eligible": 0,
            "selected_rule": None,
            "calibration_metrics": metrics(
                calibration_rows, [FALLBACK_CLASS] * len(calibration_rows)
            ),
            "score_complexity_tie_count": 0,
        }
    best = ranked[0]
    tie_count = sum(item[0] == best[0] and item[1] == best[1] for item in ranked)
    return {
        "generated": generated,
        "eligible": len(ranked),
        "selected_rule": best[3],
        "calibration_metrics": best[4],
        "score_complexity_tie_count": tie_count,
    }


def theoretical_rule_space(family: str, pair_count: int) -> int:
    per_pair = {
        "STRICT_POSITIVE_AND": 2,
        "SIGNED_LITERAL_SINGLE_PATTERN": 8,
        "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK": 16,
    }[family]
    return per_pair * pair_count


def pair_recovery(case: dict[str, Any], rule: dict[str, Any] | None) -> str:
    registered = case.get("registered_pair")
    if rule is None:
        return "NO_RULE"
    if registered is None:
        return "NO_REGISTERED_PAIR"
    if tuple(rule["pair"]) == tuple(sorted(registered, key=lambda x: x.encode("utf-8"))):
        return "MATCHED_REGISTERED_PAIR"
    return "WRONG_PAIR"


def coverage_diagnostics(
    universe: dict[str, Any], rule: dict[str, Any] | None, calibration: list[dict[str, Any]], holdout: list[dict[str, Any]]
) -> dict[str, Any]:
    known = set(universe["top_tokens"])
    total_token_occurrences = sum(len(row["tokens"]) for row in holdout)
    known_token_occurrences = sum(
        sum(token in known for token in row["tokens"]) for row in holdout
    )
    oov_rows = sum(bool(set(row["tokens"]) - known) for row in holdout)
    token_coverage = (
        Fraction(known_token_occurrences, total_token_occurrences)
        if total_token_occurrences
        else Fraction(1, 1)
    )
    if rule is None:
        return {
            "holdout_known_token_occurrence_coverage": fraction_object(token_coverage),
            "holdout_oov_row_count": oov_rows,
            "holdout_pair_state_seen_in_calibration": None,
            "holdout_unseen_pair_state_row_count": None,
            "calibration_selected_pair_state_support": None,
        }
    calibration_states = {
        pair_state(row["tokens"], rule["pair"]) for row in calibration
    }
    seen_count = sum(pair_state(row["tokens"], rule["pair"]) in calibration_states for row in holdout)
    return {
        "holdout_known_token_occurrence_coverage": fraction_object(token_coverage),
        "holdout_oov_row_count": oov_rows,
        "holdout_pair_state_seen_in_calibration": fraction_object(
            Fraction(seen_count, len(holdout))
        ),
        "holdout_unseen_pair_state_row_count": len(holdout) - seen_count,
        "calibration_selected_pair_state_support": state_support(calibration, rule["pair"]),
    }


def evaluate_case(case: dict[str, Any], fixtures: dict[str, Any]) -> dict[str, Any]:
    calibration = expand_phase(case["case_id"], "calibration", case["calibration"])
    holdout = expand_phase(case["case_id"], "holdout", case["holdout"])
    universe = freeze_universe(calibration, fixtures["top_token_limit"])
    family_results: list[dict[str, Any]] = []
    for family in FAMILIES:
        frozen = select_rule(family, universe, calibration, fixtures["selection"])
        rule = frozen["selected_rule"]
        # Holdout features are consumed here, before the labels are passed to metrics.
        frozen_holdout_predictions = predictions(rule, holdout)
        holdout_metrics = metrics(holdout, frozen_holdout_predictions)
        calibration_metrics = frozen["calibration_metrics"]
        stable = all(
            metric_fraction(phase_metrics["recall_by_class"][label]) == 1
            for phase_metrics in (calibration_metrics, holdout_metrics)
            for label in CLASSES
        )
        recovery = pair_recovery(case, rule)
        family_results.append(
            {
                "family": family,
                "generated_candidate_count": frozen["generated"],
                "eligible_candidate_count": frozen["eligible"],
                "conceptual_total_2bit_labeling_rule_space": theoretical_rule_space(
                    family, len(universe["pairs"])
                ),
                "selected_rule": rule,
                "selected_rule_sha256": sha256_bytes(semantic_rule_bytes(rule)) if rule else None,
                "score_complexity_tie_count_before_canonical_bytes": frozen[
                    "score_complexity_tie_count"
                ],
                "calibration": calibration_metrics,
                "holdout": holdout_metrics,
                "stable_recovery_calibration_and_holdout_exact_both_classes": stable,
                "pair_recovery": recovery,
                "misselected_registered_pair": recovery == "WRONG_PAIR",
                "selected_spurious_pattern": rule is not None
                and "spurious-pair" in case["tags"]
                and recovery in ("WRONG_PAIR", "NO_REGISTERED_PAIR"),
                "coverage": coverage_diagnostics(universe, rule, calibration, holdout),
            }
        )
    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "expected_relation": case["expected_relation"],
        "registered_pair": case.get("registered_pair"),
        "tags": case["tags"],
        "calibration_row_count": len(calibration),
        "holdout_row_count": len(holdout),
        "universe": universe,
        "family_results": family_results,
    }


def average_metric(results: list[dict[str, Any]], phase: str) -> Fraction:
    values = [metric_fraction(result[phase]["balanced_accuracy"]) for result in results]
    return sum(values, Fraction(0, 1)) / len(values)


def summarize_family(family: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    results = [
        next(item for item in case["family_results"] if item["family"] == family)
        for case in cases
    ]
    pair_counts = Counter(result["pair_recovery"] for result in results)
    role_null = next(
        result
        for case, result in zip(cases, results)
        if "role-null" in case["tags"]
    )
    return {
        "family": family,
        "case_count": len(results),
        "stable_recovery_case_ids": [
            case["case_id"]
            for case, result in zip(cases, results)
            if result["stable_recovery_calibration_and_holdout_exact_both_classes"]
        ],
        "holdout_exact_case_ids": [
            case["case_id"]
            for case, result in zip(cases, results)
            if metric_fraction(result["holdout"]["balanced_accuracy"]) == 1
        ],
        "mean_calibration_balanced_accuracy": fraction_object(
            average_metric(results, "calibration")
        ),
        "mean_holdout_balanced_accuracy": fraction_object(average_metric(results, "holdout")),
        "pair_recovery_counts": dict(sorted(pair_counts.items())),
        "misselection_case_ids": [
            case["case_id"]
            for case, result in zip(cases, results)
            if result["misselected_registered_pair"]
        ],
        "spurious_selection_case_ids": [
            case["case_id"]
            for case, result in zip(cases, results)
            if result["selected_spurious_pattern"]
        ],
        "role_null_holdout_balanced_accuracy": role_null["holdout"]["balanced_accuracy"],
        "role_null_false_recovery_at_ba_ge_0_90": metric_fraction(
            role_null["holdout"]["balanced_accuracy"]
        )
        >= Fraction(9, 10),
        "total_generated_candidates": sum(result["generated_candidate_count"] for result in results),
        "total_eligible_candidates": sum(result["eligible_candidate_count"] for result in results),
        "total_conceptual_rule_space": sum(
            result["conceptual_total_2bit_labeling_rule_space"] for result in results
        ),
        "total_holdout_oov_rows": sum(
            result["coverage"]["holdout_oov_row_count"] for result in results
        ),
        "total_holdout_unseen_pair_state_rows_where_rule_selected": sum(
            result["coverage"]["holdout_unseen_pair_state_row_count"] or 0
            for result in results
        ),
    }


def minimum_binary_tree_depth(truth_table: dict[str, str]) -> int:
    if set(truth_table) != {"00", "01", "10", "11"} or any(
        label not in CLASSES for label in truth_table.values()
    ):
        raise ValueError("truth table must map all four states to R or S")
    if len(set(truth_table.values())) == 1:
        return 0
    for bit in (0, 1):
        if all(
            len({truth_table[state] for state in truth_table if state[bit] == branch}) == 1
            for branch in ("0", "1")
        ):
            return 1
    return 2


def no_f4_allocation(
    fixtures: dict[str, Any], cases: list[dict[str, Any]], summaries: list[dict[str, Any]]
) -> dict[str, Any]:
    tree_tables = []
    fixture_by_id = {case["case_id"]: case for case in fixtures["cases"]}
    for case in cases:
        source = fixture_by_id[case["case_id"]]
        if "frozen_truth_table" not in source:
            continue
        depth = minimum_binary_tree_depth(source["frozen_truth_table"])
        tree_tables.append(
            {
                "case_id": case["case_id"],
                "minimum_binary_tree_depth": depth,
                "representable_within_registered_C04_maximum_depth_3": depth <= 3,
                "learned_or_holdout_validated_by_this_duel": false_value(),
            }
        )
    return {
        "allocation": "NO_F4_IN_C01__C04_OWNS_INTERACTIONS",
        "status": "RESPONSIBILITY_ALLOCATION_CANDIDATE_NOT_EXECUTED",
        "c01_f4_generated_candidates": 0,
        "c01_f4_conceptual_rule_space": 0,
        "current_holdout_predictions": None,
        "current_reason": "C04 machine semantics and its model-input bytes are not closed or executed by this duel",
        "candidate_surface_removed_relative_to_each_f4_semantics": {
            item["family"]: {
                "generated_candidates_removed_on_these_fixtures": item[
                    "total_generated_candidates"
                ],
                "conceptual_pair_labelings_removed_on_these_fixtures": item[
                    "total_conceptual_rule_space"
                ],
            }
            for item in summaries
        },
        "two_bit_representation_upper_bound_only": tree_tables,
        "would_miss_in_c01": [
            "positive AND interactions not reducible to F1/F2/F3",
            "negated signed patterns not reducible to F1/F2/F3",
            "XOR or other multi-state pair mappings",
        ],
        "could_reduce": [
            "C01 pair enumeration and canonical tie surface",
            "calibration-only pair misselection",
            "low-support pair admission",
            "duplicate interaction ownership between C01 and C04",
        ],
        "delegation_preconditions": [
            "C04 exact machine semantics, input matrix, support, tie, OOV and convergence/failure behavior are frozen",
            "the relevant interaction attack is pre-registered to C04 rather than silently rescued by a secondary detector",
            "holdout selection remains frozen and role-null plus spurious-pair attacks are retained",
            "SECURITY_REVIEW_REQUIRED for any real isolation, zero-ingress, capability or attack-surface claim",
        ],
        "d0_d1_primary_boundary": {
            "public_registration_currently_names_C01_for_D0_and_D1": True,
            "D0_design_candidate_rule": "single exact categorical token presence",
            "D0_dependency_on_F4": "NONE_IF_BOUND_DESIGN_PREMISES_HOLD__ACTUAL_D0_NOT_RUN",
            "D1_dependency_on_F4": "NONE_IF_ONE_ROLE_ATOM_IS_CROSS_PHASE_STABLE__THAT_PREMISE_IS_NOT_PUBLICLY_BOUND_AND_ACTUAL_D1_NOT_RUN",
            "secondary_detector_can_rescue_failed_primary": False,
        },
    }


def false_value() -> bool:
    """Avoid visually conflating an analytic upper bound with an executed result."""
    return False


def source_bindings() -> dict[str, Any]:
    bindings: dict[str, Any] = {}
    for name, path in SOURCE_PATHS.items():
        raw = path.read_bytes()
        bindings[name] = {
            "path_relative_to_wave025": str(path.relative_to(FEATURE_SPEC_ROOT.parent)),
            "byte_length": len(raw),
            "sha256": sha256_bytes(raw),
        }
    fixture_raw = FIXTURES_PATH.read_bytes()
    script_raw = Path(__file__).read_bytes()
    tests_path = ROOT / "tests/test_f4_semantics_duel.py"
    tests_raw = tests_path.read_bytes()
    bindings["duel_fixtures"] = {
        "path_relative_to_duel": FIXTURES_PATH.name,
        "byte_length": len(fixture_raw),
        "sha256": sha256_bytes(fixture_raw),
    }
    bindings["duel_implementation"] = {
        "path_relative_to_duel": Path(__file__).name,
        "byte_length": len(script_raw),
        "sha256": sha256_bytes(script_raw),
    }
    bindings["duel_tests"] = {
        "path_relative_to_duel": str(tests_path.relative_to(ROOT)),
        "byte_length": len(tests_raw),
        "sha256": sha256_bytes(tests_raw),
    }
    return bindings


def build_results() -> dict[str, Any]:
    fixtures = load_fixtures()
    cases = [evaluate_case(case, fixtures) for case in fixtures["cases"]]
    summaries = [summarize_family(family, cases) for family in FAMILIES]
    return {
        "schema": "WAVE025_F4_SEMANTICS_DUEL_RESULTS_V1",
        "status": "SYNTHETIC_SEMANTIC_DUEL_NOT_C01_CANON_NOT_ACTUAL_D0_D1_EVIDENCE",
        "question": "Which bounded meaning, if any, should the historical C01 F4 name denote?",
        "scope": {
            "evidence_kind": "deterministic local synthetic semantic discriminator",
            "security_boundary": "NO_NETWORK_CONTAINER_REAL_PERMISSION_OR_ISOLATION_BYPASS_WORK__EXTERNAL_SECURITY_DEPENDENCIES_ARE_SECURITY_REVIEW_REQUIRED",
            "selection_reads": ["calibration feature tokens", "calibration labels"],
            "holdout_prediction_reads": ["frozen selected rule", "holdout feature tokens"],
            "holdout_scoring_reads_after_prediction_freeze": ["holdout labels"],
            "not_claimed": [
                "MODEL-INPUT canon",
                "actual D0 or D1 sensitivity",
                "C04 execution",
                "G qualification",
                "formal 3200 population result",
                "real-world frequency of any truth table",
            ],
        },
        "semantics": [
            {
                "family": "STRICT_POSITIVE_AND",
                "meaning": "one positive A AND B predicate; match predicts one class and all other states the other",
                "rules_per_pair": 2,
                "unseen_state_behavior": "all states are defined by match versus nonmatch",
            },
            {
                "family": "SIGNED_LITERAL_SINGLE_PATTERN",
                "meaning": "one of 00,01,10,11 is a signed two-literal pattern; that state predicts one class and the other three the other",
                "rules_per_pair": 8,
                "unseen_state_behavior": "all states are defined by match versus nonmatch",
            },
            {
                "family": "FULL_2BIT_OBSERVED_MAPPING_R_FALLBACK",
                "meaning": "each observed state maps to its calibration majority class (tie R); an unobserved state freezes to R",
                "conceptual_labelings_per_pair_when_all_states_observed": 16,
                "generated_candidates_per_pair": 1,
                "unseen_state_behavior": "R without reselection",
            },
        ],
        "selection": fixtures["selection"],
        "case_results": cases,
        "family_summaries": summaries,
        "responsibility_allocation_comparison": no_f4_allocation(fixtures, cases, summaries),
        "source_bindings": source_bindings(),
        "conclusion_boundary": {
            "synthetic_coverage_order_is_not_a_canon_decision": True,
            "spurious_and_unseen_state_counterexamples_prevent_unconditional_winner_claim": True,
            "no_f4_allocation_remains_live": True,
            "actual_d0_d1_and_role_null_receipts_are_required_for_decision": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write deterministic RESULTS.json")
    parser.add_argument("--check", action="store_true", help="check RESULTS.json byte-for-byte")
    args = parser.parse_args()
    if not args.write and not args.check:
        parser.error("choose --write or --check")
    expected = pretty_bytes(build_results())
    if args.write:
        RESULTS_PATH.write_bytes(expected)
        print(f"wrote {RESULTS_PATH.name}: {len(expected)} bytes {sha256_bytes(expected)}")
    if args.check:
        actual = RESULTS_PATH.read_bytes()
        if actual != expected:
            raise SystemExit("RESULTS.json does not match current sources and implementation")
        print(f"byte-exact check passed: {len(actual)} bytes {sha256_bytes(actual)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
