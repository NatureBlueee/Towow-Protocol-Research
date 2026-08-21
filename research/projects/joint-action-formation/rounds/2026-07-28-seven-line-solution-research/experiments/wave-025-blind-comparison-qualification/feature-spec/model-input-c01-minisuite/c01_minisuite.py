#!/usr/bin/env python3
"""Deterministic C01 compatibility minisuite, revision 2.

The normal build invokes selection-freeze and holdout-scoring as separate Python
processes.  The freeze process receives calibration labels but no holdout labels;
the score process receives frozen predictions and holdout labels but no features.
This remains a synthetic research tool, not MODEL-INPUT canon.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent
MEMBERSHIP_PATH = ROOT / "OPAQUE-MEMBERSHIP.candidate.json"
FEATURES_PATH = ROOT / "CASES-FEATURES.candidate.json"
LABELS_PATH = ROOT / "CASES-LABELS.candidate.json"
CONTRACT_PATH = ROOT / "C01-MINISUITE-CONTRACT.candidate.json"
FROZEN_PATH = ROOT / "FROZEN-SELECTIONS.candidate.json"
RESULTS_PATH = ROOT / "RESULTS.candidate.json"
TEST_PATH = ROOT / "tests/test_c01_minisuite.py"
README_PATH = ROOT / "README.md"
INITIALIZER_PATH = ROOT / "initialize_membership_sources.py"

CLASS_IDS = ("R", "S")
FALLBACK_CLASS = "R"
MIN_TOTAL_SUPPORT = 10
MIN_PREDICTED_CLASS_SUPPORT = 5
TOP_TOKEN_LIMIT = 256

FAMILIES = (
    "F1_SINGLE_EXACT_CATEGORY_PRESENCE",
    "F2_SINGLE_CONTEXT_TOTAL_MAPPING",
    "F3_SINGLE_NUMERIC_EXACT_WITH_MISSING",
    "F4_TWO_TOKEN_CONJUNCTION_FROM_TOP256_SUPPORT",
)
F4_UNAVAILABLE_REASON = (
    "REGISTERED_NAME_DOES_NOT_UNIQUELY_DEFINE_POSITIVE_VS_NEGATED_LITERALS_"
    "ORIENTATION_FALLBACK_OR_SINGLE_RULE_VS_RULE_SET"
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def ratio(value: Fraction) -> dict[str, Any]:
    return {
        "decimal": float(value),
        "denominator": value.denominator,
        "numerator": value.numerator,
    }


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def require_binding(value: Any, path: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value) or value == "0" * 64:
        raise ValueError(f"{path} must be a nonzero lowercase SHA-256")
    return value


def require_exact_keys(value: Any, keys: set[str], path: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        actual = sorted(value) if isinstance(value, dict) else type(value).__name__
        raise ValueError(f"{path} is not recursively closed expected={sorted(keys)} actual={actual}")


def read_exact_canonical(path: Path, expected_sha256: str, logical_name: str) -> tuple[Any, bytes]:
    require_binding(expected_sha256, logical_name + ".expected_sha256")
    raw = path.read_bytes()
    if sha256_bytes(raw) != expected_sha256:
        raise ValueError(f"{logical_name} exact-byte binding mismatch")
    value = json.loads(raw)
    if raw != canonical_bytes(value):
        raise ValueError(f"{logical_name} is not canonical JSON")
    return value, raw


def category_identity(context: str, token: str) -> dict[str, str]:
    return {"context": context, "token": token}


def category_key(identity: dict[str, str]) -> bytes:
    return canonical_bytes(identity)


def row_category_identities(row: dict[str, Any]) -> set[bytes]:
    return {
        category_key(category_identity(item["context"], item["token"]))
        for item in row["categories"]
    }


def context_total_state(row: dict[str, Any], context: str) -> str:
    matches = [item for item in row["categories"] if item["context"] == context]
    if not matches:
        return "MISSING"
    return f"COUNT:{sum(item['count'] for item in matches)}"


def numeric_state(row: dict[str, Any], identity: str) -> str:
    matches = [item for item in row["numerics"] if item["identity"] == identity]
    if not matches:
        return "MISSING"
    if len(matches) != 1:
        raise ValueError(f"duplicate numeric identity {identity!r} in {row['row_id']}")
    value = matches[0]["value"]
    exact = Fraction(value["numerator"], value["denominator"])
    return f"VALUE:{exact.numerator}/{exact.denominator}"


def freeze_universe(calibration_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Construct membership without a labels parameter or labels input channel."""
    category_by_key: dict[bytes, dict[str, str]] = {}
    context_set: set[str] = set()
    numeric_set: set[str] = set()
    token_support: Counter[bytes] = Counter()
    for row in calibration_rows:
        present = row_category_identities(row)
        token_support.update(present)
        for item in row["categories"]:
            identity = category_identity(item["context"], item["token"])
            category_by_key[category_key(identity)] = identity
            context_set.add(item["context"])
        for item in row["numerics"]:
            numeric_set.add(item["identity"])
    top_keys = sorted(token_support, key=lambda key: (-token_support[key], key))[
        :TOP_TOKEN_LIMIT
    ]
    universe = {
        "exact_categories": [category_by_key[key] for key in sorted(category_by_key)],
        "numeric_identities": sorted(numeric_set),
        "schema": "WAVE025_C01_MINISUITE_LABEL_BLIND_UNIVERSE_V2",
        "single_contexts": sorted(context_set),
        "top_token_limit": TOP_TOKEN_LIMIT,
        "top_tokens": [category_by_key[key] for key in top_keys],
        "two_token_pairs": [
            [category_by_key[left], category_by_key[right]]
            for left, right in itertools.combinations(top_keys, 2)
        ],
    }
    universe["canonical_sha256_without_binding"] = sha256_json(universe)
    return universe


def join_labels(
    rows: list[dict[str, Any]], labels: dict[str, str]
) -> list[tuple[dict[str, Any], str]]:
    expected = {row["row_id"] for row in rows}
    supplied = set(labels)
    if supplied != expected:
        raise ValueError(
            f"label join mismatch missing={sorted(expected-supplied)} extra={sorted(supplied-expected)}"
        )
    joined = []
    for row in rows:
        label = labels[row["row_id"]]
        if label not in CLASS_IDS:
            raise ValueError(f"invalid label {label!r}")
        joined.append((row, label))
    return joined


def majority_mapping(states_and_labels: Iterable[tuple[str, str]]) -> dict[str, str]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for state, label in states_and_labels:
        counts[state][label] += 1
    mapping: dict[str, str] = {}
    for state in sorted(counts):
        mapping[state] = "S" if counts[state]["S"] > counts[state]["R"] else FALLBACK_CLASS
    return mapping


def predict(rule: dict[str, Any] | None, family: str, row: dict[str, Any]) -> str:
    if rule is None:
        return FALLBACK_CLASS
    if family == FAMILIES[0]:
        # Unknown exact tokens do not trigger row-level fallback.  They are ignored;
        # only the frozen selector's presence controls this rule.
        present = category_key(rule["selector"]) in row_category_identities(row)
        return rule["present_class"] if present else rule["absent_class"]
    if family == FAMILIES[1]:
        state = context_total_state(row, rule["context"])
        return rule["mapping"].get(state, rule["oov_fallback_class"])
    if family == FAMILIES[2]:
        state = numeric_state(row, rule["numeric_identity"])
        return rule["mapping"].get(state, rule["oov_fallback_class"])
    if family == FAMILIES[3]:
        raise ValueError("F4 conjunction semantics are underdetermined and not executable")
    raise ValueError(f"unknown family {family}")


def prediction_metrics(
    prediction_records: list[dict[str, str]], labels: dict[str, str]
) -> dict[str, Any]:
    expected = {item["row_id"] for item in prediction_records}
    if set(labels) != expected:
        raise ValueError("prediction/label population mismatch")
    totals: Counter[str] = Counter()
    correct: Counter[str] = Counter()
    predicted: Counter[str] = Counter()
    for item in prediction_records:
        label = labels[item["row_id"]]
        result = item["prediction"]
        if label not in CLASS_IDS or result not in CLASS_IDS:
            raise ValueError("invalid class in score input")
        totals[label] += 1
        predicted[result] += 1
        if result == label:
            correct[label] += 1
    recalls = {
        label: Fraction(correct[label], totals[label]) if totals[label] else Fraction(0)
        for label in CLASS_IDS
    }
    return {
        "balanced_accuracy": ratio(sum(recalls.values(), Fraction(0)) / 2),
        "predicted_class_support": {label: predicted[label] for label in CLASS_IDS},
        "recall_by_class": {label: ratio(recalls[label]) for label in CLASS_IDS},
        "true_class_support": {label: totals[label] for label in CLASS_IDS},
    }


def metrics(
    joined: list[tuple[dict[str, Any], str]], family: str, rule: dict[str, Any] | None
) -> dict[str, Any]:
    predictions = [
        {"prediction": predict(rule, family, row), "row_id": row["row_id"]}
        for row, _ in joined
    ]
    labels = {row["row_id"]: label for row, label in joined}
    return prediction_metrics(predictions, labels)


def eligible_by_support(candidate_metrics: dict[str, Any], total: int) -> bool:
    predicted = candidate_metrics["predicted_class_support"]
    return (
        total >= MIN_TOTAL_SUPPORT
        and predicted["R"] >= MIN_PREDICTED_CLASS_SUPPORT
        and predicted["S"] >= MIN_PREDICTED_CLASS_SUPPORT
    )


def finalize_rule(rule: dict[str, Any], complexity_units: int) -> dict[str, Any]:
    frozen = {
        **rule,
        "complexity_units": complexity_units,
        "fallback_class": FALLBACK_CLASS,
        "schema": "WAVE025_C01_MINISUITE_FROZEN_RULE_V2",
    }
    raw = canonical_bytes(frozen)
    frozen["canonical_byte_length_without_binding"] = len(raw)
    frozen["canonical_sha256_without_binding"] = sha256_bytes(raw)
    return frozen


def candidate_rules(
    family: str,
    universe: dict[str, Any],
    joined: list[tuple[dict[str, Any], str]],
) -> Iterable[dict[str, Any]]:
    if family == FAMILIES[0]:
        for identity in universe["exact_categories"]:
            for present_class in CLASS_IDS:
                yield finalize_rule(
                    {
                        "absent_class": "S" if present_class == "R" else "R",
                        "family": family,
                        "oov_semantics": "IGNORE_UNKNOWN_TOKENS_APPLY_SELECTOR_ABSENCE_BRANCH",
                        "present_class": present_class,
                        "selector": identity,
                    },
                    1,
                )
        return
    if family == FAMILIES[1]:
        for context in universe["single_contexts"]:
            mapping = majority_mapping(
                (context_total_state(row, context), label) for row, label in joined
            )
            mapping.setdefault("MISSING", FALLBACK_CLASS)
            yield finalize_rule(
                {
                    "context": context,
                    "family": family,
                    "mapping": mapping,
                    "missing_state": "MISSING",
                    "oov_fallback_class": FALLBACK_CLASS,
                },
                1 + len(mapping),
            )
        return
    if family == FAMILIES[2]:
        for identity in universe["numeric_identities"]:
            mapping = majority_mapping(
                (numeric_state(row, identity), label) for row, label in joined
            )
            mapping.setdefault("MISSING", FALLBACK_CLASS)
            yield finalize_rule(
                {
                    "family": family,
                    "mapping": mapping,
                    "missing_state": "MISSING",
                    "numeric_identity": identity,
                    "oov_fallback_class": FALLBACK_CLASS,
                },
                1 + len(mapping),
            )
        return
    if family == FAMILIES[3]:
        # The registered string names a conjunction but leaves essential semantics
        # open.  Generating a full 2-bit lookup would silently replace that family.
        return
    raise ValueError(f"unknown family {family}")


def select_rule(
    family: str,
    universe: dict[str, Any],
    joined: list[tuple[dict[str, Any], str]],
) -> tuple[dict[str, Any] | None, dict[str, Any], int, int]:
    if family == FAMILIES[3]:
        fallback_predictions = [
            {"prediction": FALLBACK_CLASS, "row_id": row["row_id"]}
            for row, _ in joined
        ]
        return (
            None,
            prediction_metrics(
                fallback_predictions, {row["row_id"]: label for row, label in joined}
            ),
            0,
            0,
        )
    eligible: list[tuple[Fraction, int, bytes, dict[str, Any], dict[str, Any]]] = []
    generated = 0
    for rule in candidate_rules(family, universe, joined):
        generated += 1
        candidate_metrics = metrics(joined, family, rule)
        if not eligible_by_support(candidate_metrics, len(joined)):
            continue
        score = Fraction(
            candidate_metrics["balanced_accuracy"]["numerator"],
            candidate_metrics["balanced_accuracy"]["denominator"],
        )
        rule_raw = canonical_bytes(rule)
        eligible.append(
            (-score, rule["complexity_units"], rule_raw, rule, candidate_metrics)
        )
    if not eligible:
        return None, metrics(joined, family, None), generated, 0
    _, _, _, selected, selected_metrics = min(eligible)
    return selected, selected_metrics, generated, len(eligible)


def oov_count(
    family: str,
    rule: dict[str, Any] | None,
    universe: dict[str, Any],
    rows: list[dict[str, Any]],
) -> int:
    exact_keys = {category_key(item) for item in universe["exact_categories"]}
    if family == FAMILIES[0]:
        return sum(bool(row_category_identities(row) - exact_keys) for row in rows)
    if rule is None:
        return 0
    if family == FAMILIES[1]:
        known = set(rule["mapping"])
        return sum(context_total_state(row, rule["context"]) not in known for row in rows)
    if family == FAMILIES[2]:
        known = set(rule["mapping"])
        return sum(numeric_state(row, rule["numeric_identity"]) not in known for row in rows)
    if family == FAMILIES[3]:
        return 0
    raise ValueError(f"unknown family {family}")


def make_predictions(
    rows: list[dict[str, Any]], family: str, rule: dict[str, Any] | None
) -> list[dict[str, str]]:
    if family == FAMILIES[3]:
        return [
            {"prediction": FALLBACK_CLASS, "row_id": row["row_id"]}
            for row in sorted(rows, key=lambda item: item["row_id"])
        ]
    return [
        {"prediction": predict(rule, family, row), "row_id": row["row_id"]}
        for row in sorted(rows, key=lambda item: item["row_id"])
    ]


def freeze_case_core(
    case: dict[str, Any],
    calibration_labels: dict[str, str],
    contract_sha256: str,
    case_sha256: str,
    calibration_join_sha256: str,
) -> dict[str, Any]:
    require_binding(contract_sha256, "freeze.contract_sha256")
    require_binding(case_sha256, "freeze.case_sha256")
    require_binding(calibration_join_sha256, "freeze.calibration_join_sha256")
    calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
    holdout = [row for row in case["rows"] if row["phase"] == "holdout"]
    universe = freeze_universe(calibration)
    joined_calibration = join_labels(calibration, calibration_labels)
    family_freezes = []
    for family in FAMILIES:
        rule, calibration_metrics, generated, eligible = select_rule(
            family, universe, joined_calibration
        )
        calibration_predictions = make_predictions(calibration, family, rule)
        holdout_predictions = make_predictions(holdout, family, rule)
        availability = (
            "REJECTED_UNDERDETERMINED_NOT_EXECUTED"
            if family == FAMILIES[3]
            else "EXECUTABLE_MINISUITE_CANDIDATE"
        )
        family_freezes.append(
            {
                "availability": availability,
                "calibration": calibration_metrics,
                "calibration_predictions": calibration_predictions,
                "calibration_predictions_sha256": sha256_json(calibration_predictions),
                "candidate_count_eligible": eligible,
                "candidate_count_generated": generated,
                "family": family,
                "holdout_oov_row_count": oov_count(family, rule, universe, holdout),
                "holdout_predictions": holdout_predictions,
                "holdout_predictions_sha256": sha256_json(holdout_predictions),
                "selected_rule": rule,
                "selected_rule_sha256": sha256_json(rule) if rule is not None else None,
                "unavailable_reason": F4_UNAVAILABLE_REASON if family == FAMILIES[3] else None,
            }
        )
    return {
        "calibration_labels_sha256": sha256_json(
            [{"label": calibration_labels[key], "row_id": key} for key in sorted(calibration_labels)]
        ),
        "case_feature_sha256": sha256_json(case),
        "case_id": case["case_id"],
        "description": case["description"],
        "family_freezes": family_freezes,
        "holdout_labels_received": False,
        "phase": "SELECTION_AND_PREDICTION_FREEZE",
        "registered_control_analogue": case["registered_control_analogue"],
        "schema": "WAVE025_C01_MINISUITE_FROZEN_CASE_V3",
        "source_bindings": {
            "calibration_join_sha256": calibration_join_sha256,
            "case_sha256": case_sha256,
            "contract_sha256": contract_sha256,
        },
        "source_premise_status": case["source_premise_status"],
        "universe": universe,
        "universe_sha256_after_calibration_label_join": sha256_json(universe),
        "universe_sha256_before_calibration_label_join": sha256_json(universe),
    }


def exact_recall_one(metrics_doc: dict[str, Any]) -> bool:
    return all(
        metrics_doc["recall_by_class"][label]["numerator"]
        == metrics_doc["recall_by_class"][label]["denominator"]
        for label in CLASS_IDS
    )


def score_case_core(
    frozen_package: dict[str, Any], holdout_labels: dict[str, str]
) -> dict[str, Any]:
    family_results = []
    for frozen in frozen_package["family_freezes"]:
        holdout_metrics = prediction_metrics(frozen["holdout_predictions"], holdout_labels)
        family = frozen["family"]
        stable = (
            frozen["selected_rule"] is not None
            and exact_recall_one(frozen["calibration"])
            and exact_recall_one(holdout_metrics)
        )
        if frozen["availability"] != "EXECUTABLE_MINISUITE_CANDIDATE":
            failure_reason = "RULE_FAMILY_SPEC_UNDERDETERMINED_NO_EXECUTION"
        elif frozen["selected_rule"] is None:
            failure_reason = "NO_ELIGIBLE_RULE_FALLBACK_R"
        elif stable:
            failure_reason = None
        elif frozen["holdout_oov_row_count"] and family != FAMILIES[0]:
            failure_reason = "HOLDOUT_OOV_USED_FROZEN_FALLBACK"
        elif frozen["holdout_oov_row_count"] and family == FAMILIES[0]:
            failure_reason = "F1_UNKNOWN_TOKENS_IGNORED_SELECTOR_BRANCH_NOT_STABLE"
        elif not exact_recall_one(frozen["calibration"]):
            failure_reason = "CALIBRATION_RECALL_NOT_EXACT_BOTH_CLASSES"
        else:
            failure_reason = "FROZEN_RULE_DOES_NOT_SEPARATE_HOLDOUT"
        family_results.append(
            {
                "availability": frozen["availability"],
                "calibration": frozen["calibration"],
                "candidate_count_eligible": frozen["candidate_count_eligible"],
                "candidate_count_generated": frozen["candidate_count_generated"],
                "failure_reason": failure_reason,
                "family": family,
                "holdout": holdout_metrics,
                "holdout_oov_row_count": frozen["holdout_oov_row_count"],
                "holdout_scoring_consumed_feature_rows": False,
                "selected_rule": frozen["selected_rule"],
                "selected_rule_sha256_frozen": frozen["selected_rule_sha256"],
                "stable_recovery_calibration_and_holdout_exact_both_classes": stable,
                "unavailable_reason": frozen["unavailable_reason"],
            }
        )
    return {
        "case_id": frozen_package["case_id"],
        "description": frozen_package["description"],
        "family_results": family_results,
        "holdout_labels_received_only_after_frozen_package": True,
        "phase": "HOLDOUT_LABEL_JOIN_AND_SCORE_ONLY",
        "registered_control_analogue": frozen_package["registered_control_analogue"],
        "schema": "WAVE025_C01_MINISUITE_SCORED_CASE_V3",
        "source_premise_status": frozen_package["source_premise_status"],
    }


def reject_label_like_keys(value: Any, path: str = "$", allow: set[str] | None = None) -> None:
    allow = allow or set()
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = key.lower()
            if key not in allow and ("label" in lowered or lowered in {"role", "roles"}):
                raise ValueError(f"label-like key rejected at {path}.{key}")
            reject_label_like_keys(nested, path + "." + key, allow)
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            reject_label_like_keys(nested, f"{path}[{index}]", allow)


def validate_case_document(case: dict[str, Any]) -> None:
    require_exact_keys(
        case,
        {"case_id", "description", "registered_control_analogue", "rows", "source_premise_status"},
        "case",
    )
    reject_label_like_keys(case)
    if not isinstance(case["rows"], list) or len(case["rows"]) != 80:
        raise ValueError("case.rows must contain exactly 80 rows")
    seen = set()
    for index, row in enumerate(case["rows"]):
        require_exact_keys(row, {"categories", "numerics", "phase", "row_id"}, f"case.rows[{index}]")
        if not re.fullmatch(r"o_[0-9a-f]{24}", row["row_id"]):
            raise ValueError("nonopaque row_id")
        if row["row_id"] in seen:
            raise ValueError("duplicate row_id")
        seen.add(row["row_id"])
        if row["phase"] not in {"calibration", "holdout"}:
            raise ValueError("invalid phase")
        if not isinstance(row["categories"], list) or not isinstance(row["numerics"], list):
            raise ValueError("row channels must be lists")
        for cat_index, item in enumerate(row["categories"]):
            require_exact_keys(item, {"context", "count", "token"}, f"row.categories[{cat_index}]")
            if not isinstance(item["count"], int) or item["count"] < 1:
                raise ValueError("invalid count")
        for num_index, item in enumerate(row["numerics"]):
            require_exact_keys(item, {"identity", "value"}, f"row.numerics[{num_index}]")
            require_exact_keys(item["value"], {"denominator", "numerator"}, "numeric.value")
            if not isinstance(item["value"]["denominator"], int) or item["value"]["denominator"] <= 0:
                raise ValueError("invalid numeric denominator")


def validate_join_document(doc: dict[str, Any], schema: str, expected_ids: set[str]) -> dict[str, str]:
    require_exact_keys(doc, {"assignments", "schema"}, "join")
    if doc["schema"] != schema or not isinstance(doc["assignments"], list):
        raise ValueError("join schema mismatch")
    mapping = {}
    for index, item in enumerate(doc["assignments"]):
        require_exact_keys(item, {"class_id", "row_id"}, f"join.assignments[{index}]")
        if item["class_id"] not in CLASS_IDS or item["row_id"] in mapping:
            raise ValueError("invalid join assignment")
        mapping[item["row_id"]] = item["class_id"]
    if set(mapping) != expected_ids:
        raise ValueError("join membership mismatch")
    return mapping


def validate_ratio_document(value: dict[str, Any], path: str) -> None:
    require_exact_keys(value, {"decimal", "denominator", "numerator"}, path)
    if not isinstance(value["numerator"], int) or not isinstance(value["denominator"], int):
        raise ValueError(path + " invalid rational")


def validate_metrics_document(value: dict[str, Any], path: str) -> None:
    require_exact_keys(
        value,
        {"balanced_accuracy", "predicted_class_support", "recall_by_class", "true_class_support"},
        path,
    )
    validate_ratio_document(value["balanced_accuracy"], path + ".balanced_accuracy")
    for name in ("predicted_class_support", "true_class_support"):
        require_exact_keys(value[name], set(CLASS_IDS), path + "." + name)
    require_exact_keys(value["recall_by_class"], set(CLASS_IDS), path + ".recall_by_class")
    for class_id in CLASS_IDS:
        validate_ratio_document(value["recall_by_class"][class_id], path + ".recall")


def validate_predictions(value: Any, path: str) -> None:
    if not isinstance(value, list):
        raise ValueError(path + " must be list")
    seen = set()
    for index, item in enumerate(value):
        require_exact_keys(item, {"prediction", "row_id"}, f"{path}[{index}]")
        if item["prediction"] not in CLASS_IDS or not re.fullmatch(r"o_[0-9a-f]{24}", item["row_id"]):
            raise ValueError(path + " invalid prediction")
        if item["row_id"] in seen:
            raise ValueError(path + " duplicate row")
        seen.add(item["row_id"])


def validate_rule_document(rule: Any, family: str, path: str) -> None:
    if rule is None:
        return
    common = {
        "canonical_byte_length_without_binding",
        "canonical_sha256_without_binding",
        "complexity_units",
        "fallback_class",
        "family",
        "schema",
    }
    additions = {
        FAMILIES[0]: {"absent_class", "oov_semantics", "present_class", "selector"},
        FAMILIES[1]: {"context", "mapping", "missing_state", "oov_fallback_class"},
        FAMILIES[2]: {"mapping", "missing_state", "numeric_identity", "oov_fallback_class"},
    }
    if family not in additions:
        raise ValueError("unavailable family cannot carry rule")
    require_exact_keys(rule, common | additions[family], path)
    if rule["family"] != family or rule["fallback_class"] not in CLASS_IDS:
        raise ValueError(path + " family/fallback mismatch")
    require_binding(rule["canonical_sha256_without_binding"], path + ".canonical_sha256_without_binding")
    without = dict(rule)
    expected_length = without.pop("canonical_byte_length_without_binding")
    expected_sha = without.pop("canonical_sha256_without_binding")
    raw = canonical_bytes(without)
    if len(raw) != expected_length or sha256_bytes(raw) != expected_sha:
        raise ValueError(path + " internal rule binding mismatch")
    if family == FAMILIES[0]:
        require_exact_keys(rule["selector"], {"context", "token"}, path + ".selector")
    else:
        if not isinstance(rule["mapping"], dict) or any(v not in CLASS_IDS for v in rule["mapping"].values()):
            raise ValueError(path + " invalid mapping")


def validate_universe_document(value: dict[str, Any]) -> None:
    require_exact_keys(
        value,
        {
            "canonical_sha256_without_binding",
            "exact_categories",
            "numeric_identities",
            "schema",
            "single_contexts",
            "top_token_limit",
            "top_tokens",
            "two_token_pairs",
        },
        "universe",
    )
    expected = require_binding(value["canonical_sha256_without_binding"], "universe.binding")
    without = dict(value)
    without.pop("canonical_sha256_without_binding")
    if sha256_json(without) != expected:
        raise ValueError("universe internal binding mismatch")
    for identity in value["exact_categories"] + value["top_tokens"]:
        require_exact_keys(identity, {"context", "token"}, "universe.category")
    for pair in value["two_token_pairs"]:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("universe pair invalid")
        for identity in pair:
            require_exact_keys(identity, {"context", "token"}, "universe.pair.category")


def validate_frozen_package(package: dict[str, Any]) -> None:
    reject_label_like_keys(
        package,
        allow={
            "calibration_labels_sha256",
            "holdout_labels_received",
            "universe_sha256_after_calibration_label_join",
            "universe_sha256_before_calibration_label_join",
        },
    )
    require_exact_keys(
        package,
        {
            "calibration_labels_sha256",
            "case_feature_sha256",
            "case_id",
            "description",
            "family_freezes",
            "holdout_labels_received",
            "phase",
            "registered_control_analogue",
            "schema",
            "source_bindings",
            "source_premise_status",
            "universe",
            "universe_sha256_after_calibration_label_join",
            "universe_sha256_before_calibration_label_join",
        },
        "frozen_package",
    )
    require_binding(package["calibration_labels_sha256"], "frozen.calibration_labels_sha256")
    require_binding(package["case_feature_sha256"], "frozen.case_feature_sha256")
    if package["schema"] != "WAVE025_C01_MINISUITE_FROZEN_CASE_V3":
        raise ValueError("frozen package schema mismatch")
    if package["phase"] != "SELECTION_AND_PREDICTION_FREEZE" or package["holdout_labels_received"] is not False:
        raise ValueError("frozen package phase boundary mismatch")
    require_exact_keys(
        package["source_bindings"],
        {"calibration_join_sha256", "case_sha256", "contract_sha256"},
        "frozen.source_bindings",
    )
    for key, binding in package["source_bindings"].items():
        require_binding(binding, "frozen.source_bindings." + key)
    if package["case_feature_sha256"] != package["source_bindings"]["case_sha256"]:
        raise ValueError("frozen case source binding mismatch")
    validate_universe_document(package["universe"])
    universe_sha = sha256_json(package["universe"])
    if (
        package["universe_sha256_before_calibration_label_join"] != universe_sha
        or package["universe_sha256_after_calibration_label_join"] != universe_sha
    ):
        raise ValueError("frozen universe binding mismatch")
    if not isinstance(package["family_freezes"], list) or len(package["family_freezes"]) != 4:
        raise ValueError("frozen family population mismatch")
    for index, frozen in enumerate(package["family_freezes"]):
        require_exact_keys(
            frozen,
            {
                "availability",
                "calibration",
                "calibration_predictions",
                "calibration_predictions_sha256",
                "candidate_count_eligible",
                "candidate_count_generated",
                "family",
                "holdout_oov_row_count",
                "holdout_predictions",
                "holdout_predictions_sha256",
                "selected_rule",
                "selected_rule_sha256",
                "unavailable_reason",
            },
            f"frozen.family_freezes[{index}]",
        )
        family = frozen["family"]
        if family != FAMILIES[index]:
            raise ValueError("frozen family order mismatch")
        expected_availability = (
            "REJECTED_UNDERDETERMINED_NOT_EXECUTED"
            if family == FAMILIES[3]
            else "EXECUTABLE_MINISUITE_CANDIDATE"
        )
        if frozen["availability"] != expected_availability:
            raise ValueError("frozen family availability mismatch")
        if not isinstance(frozen["candidate_count_eligible"], int) or not isinstance(
            frozen["candidate_count_generated"], int
        ):
            raise ValueError("frozen candidate count invalid")
        validate_metrics_document(frozen["calibration"], "frozen.calibration")
        validate_predictions(frozen["calibration_predictions"], "frozen.calibration_predictions")
        validate_predictions(frozen["holdout_predictions"], "frozen.holdout_predictions")
        if sha256_json(frozen["calibration_predictions"]) != require_binding(
            frozen["calibration_predictions_sha256"], "frozen.calibration_predictions_sha256"
        ):
            raise ValueError("calibration prediction binding mismatch")
        if sha256_json(frozen["holdout_predictions"]) != require_binding(
            frozen["holdout_predictions_sha256"], "frozen.holdout_predictions_sha256"
        ):
            raise ValueError("holdout prediction binding mismatch")
        validate_rule_document(frozen["selected_rule"], family, "frozen.selected_rule")
        if frozen["selected_rule"] is None:
            if frozen["selected_rule_sha256"] is not None:
                raise ValueError("null rule cannot have hash")
        elif sha256_json(frozen["selected_rule"]) != require_binding(
            frozen["selected_rule_sha256"], "frozen.selected_rule_sha256"
        ):
            raise ValueError("selected rule binding mismatch")


def install_capability_guard(capability_root: Path, forbidden_probe: Path) -> dict[str, Any]:
    root = capability_root.resolve()
    state: dict[str, Any] = {"denied": [], "reads": set(), "writes": set()}
    system_prefixes = tuple(
        Path(path).resolve()
        for path in (
            "/System",
            "/usr/lib",
            "/Library/Developer/CommandLineTools/usr",
            "/Library/Frameworks",
            "/dev",
        )
        if Path(path).exists()
    )

    def normalize(path: Path) -> str:
        try:
            return "$CAP/" + str(path.relative_to(root))
        except ValueError:
            return "$EXTERNAL_SHA256/" + sha256_bytes(str(path).encode())

    def audit(event: str, args: tuple[Any, ...]) -> None:
        if event not in {"open", "os.listdir", "os.scandir"} or not args:
            return
        target = args[0]
        if isinstance(target, int):
            return
        try:
            path = Path(os.fspath(target))
        except TypeError:
            return
        if not path.is_absolute():
            path = Path.cwd() / path
        path = path.resolve(strict=False)
        in_root = path == root or root in path.parents
        in_system = any(path == prefix or prefix in path.parents for prefix in system_prefixes)
        if not in_root and not in_system:
            state["denied"].append(normalize(path))
            raise PermissionError(f"capability read denied: {normalize(path)}")
        if in_root:
            write = False
            if event == "open" and len(args) > 1:
                mode = args[1]
                if isinstance(mode, str):
                    write = any(marker in mode for marker in "wax+")
                elif isinstance(mode, int):
                    write = bool(mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
                if len(args) > 2 and isinstance(args[2], int):
                    flags = args[2]
                    write = write or bool(
                        flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                    )
            state["writes" if write else "reads"].add(normalize(path))

    sys.addaudithook(audit)
    try:
        forbidden_probe.read_bytes()
    except PermissionError:
        probe_blocked = True
    else:
        probe_blocked = False
        raise RuntimeError("forbidden label artifact probe unexpectedly readable")
    state["probe_blocked"] = probe_blocked
    return state


def capability_receipt(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "actual_capability_read_set": sorted(state["reads"]),
        "actual_capability_write_set": sorted(state["writes"]),
        "denied_external_read_events": sorted(state["denied"]),
        "full_labels_artifact_probe_blocked": state["probe_blocked"],
        "guard": "PYTHON_AUDIT_HOOK_DENY_NON_SYSTEM_READS_OUTSIDE_MINIMAL_CAPABILITY_ROOT",
    }


def stage_capability_file(root: Path, name: str, raw: bytes, mode: int = 0o400) -> None:
    path = root / name
    path.write_bytes(raw)
    path.chmod(mode)


def invoke_capability_phase(
    phase: str,
    staged_files: dict[str, bytes],
    expected_bindings: dict[str, str],
    expected_output_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for key, value in expected_bindings.items():
        require_binding(value, "outer_expected." + key)
    with tempfile.TemporaryDirectory(prefix="wave025-c01-cap-") as temp_name:
        cap_root = Path(temp_name)
        cap_root.chmod(0o700)
        worker_raw = Path(__file__).read_bytes()
        stage_capability_file(cap_root, "worker.py", worker_raw, 0o500)
        for name, raw in staged_files.items():
            stage_capability_file(cap_root, name, raw)
        inventory = []
        for path in sorted(cap_root.iterdir(), key=lambda item: item.name):
            inventory.append(
                {
                    "byte_length": path.stat().st_size,
                    "mode_octal": oct(path.stat().st_mode & 0o777),
                    "name": path.name,
                    "sha256": sha256_bytes(path.read_bytes()),
                }
            )
        if any("LABELS" in item["name"].upper() or item["name"] == LABELS_PATH.name for item in inventory):
            raise ValueError("full labels artifact entered capability root")
        env = {
            "C01_CAPABILITY_ROOT": str(cap_root),
            "C01_FORBIDDEN_PROBE": str(LABELS_PATH.resolve()),
            "PATH": "/usr/bin:/bin",
        }
        env.update({"C01_EXPECTED_" + key.upper(): value for key, value in expected_bindings.items()})
        completed = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(cap_root / "worker.py"), "--cap-" + phase],
            cwd=cap_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"capability phase {phase} failed rc={completed.returncode}: "
                + completed.stderr.decode("utf-8", errors="replace")
            )
        child_receipt = json.loads(completed.stdout)
        if completed.stdout != canonical_bytes(child_receipt):
            raise ValueError("capability worker receipt noncanonical")
        output_path = cap_root / expected_output_name
        output_raw = output_path.read_bytes()
        output = json.loads(output_raw)
        if output_raw != canonical_bytes(output):
            raise ValueError("capability output noncanonical")
        receipt = {
            "capability_root_initial_inventory": inventory,
            "child_capability_receipt": child_receipt,
            "external_output_byte_length": len(output_raw),
            "external_output_sha256": sha256_bytes(output_raw),
            "full_labels_artifact_present_in_capability_root": False,
            "forbidden_full_labels_artifact_sha256": sha256_bytes(LABELS_PATH.read_bytes()),
            "forbidden_probe_path_sha256": sha256_bytes(str(LABELS_PATH.resolve()).encode()),
            "phase": phase,
            "wrapper": "OUTER_EXACT_BYTE_SEAL_NOT_SUPPLIED_INSIDE_PAYLOAD",
        }
        return output, receipt


def _cat(context: str, token: str, count: int = 1) -> dict[str, Any]:
    return {"context": context, "count": count, "token": token}


def _num(identity: str, numerator: int, denominator: int = 1) -> dict[str, Any]:
    return {
        "identity": identity,
        "value": {"denominator": denominator, "numerator": numerator},
    }


def opaque_feature_token(domain: str, row_id: str) -> str:
    raw = f"WAVE025_C01_FEATURE_TOKEN_V3\0{domain}\0{row_id}".encode()
    return "x_" + hashlib.sha256(raw).hexdigest()[:24]


def _row(
    row_id: str,
    phase: str,
    categories: list[dict[str, Any]] | None = None,
    numerics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "categories": categories or [],
        "numerics": numerics or [],
        "phase": phase,
        "row_id": row_id,
    }


def build_cases() -> tuple[dict[str, Any], dict[str, Any]]:
    membership_raw = MEMBERSHIP_PATH.read_bytes()
    labels_raw = LABELS_PATH.read_bytes()
    membership = json.loads(membership_raw)
    labels_doc = json.loads(labels_raw)
    if membership_raw != canonical_bytes(membership) or labels_raw != canonical_bytes(labels_doc):
        raise ValueError("membership and labels sources must be canonical")
    validate_membership_document(membership)
    validate_label_document(labels_doc)
    label_map = {item["row_id"]: item["class_id"] for item in labels_doc["labels"]}
    cases: list[dict[str, Any]] = []

    def add_case(
        case_id: str,
        description: str,
        registered_control_analogue: str | None,
        source_premise_status: str,
        row_builder: Any,
    ) -> None:
        member = next(item for item in membership["cases"] if item["case_id"] == case_id)
        rows: list[dict[str, Any]] = []
        for phase in ("calibration", "holdout"):
            within_class = Counter()
            for row_id in member["phases"][phase]:
                label = label_map[row_id]
                index = within_class[label]
                within_class[label] += 1
                row = row_builder(phase, label, index, row_id)
                rows.append(row)
        cases.append(
            {
                "case_id": case_id,
                "description": description,
                "registered_control_analogue": registered_control_analogue,
                "rows": sorted(rows, key=lambda item: item["row_id"]),
                "source_premise_status": source_premise_status,
            }
        )

    add_case(
        "P1_D0_STABLE_EXACT_ATOM",
        "Synthetic public-D0 mechanism analogue: one latent-class exact basename atom repeats across phases; no actual registry value is used.",
        "D0_RESIDUE_OPAQUE_BASENAME_V1",
        "PUBLIC_D0_DESIGN_EXPRESSES_ONE_ATOM_PER_CLASS_CROSS_PHASE_BUT_ACTUAL_D0_NOT_RUN",
        lambda phase, label, index, row_id: _row(
            row_id,
            phase,
            [_cat("F04:CWD_PATH", "opaque-atom-17" if label == "R" else "opaque-atom-83")],
        ),
    )
    add_case(
        "P2_D1_CONDITIONAL_STABLE_EXACT_ATOM",
        "Conditional synthetic mechanism only: if one opaque canary atom per latent class repeats across phases, test exact-presence compatibility.",
        "D1_CURRENT_RUN_CANARY_V1",
        "UNKNOWN_CONDITIONAL_CROSS_PHASE_STABILITY_NOT_EXPRESSED_BY_BOUND_PUBLIC_REGISTRATION",
        lambda phase, label, index, row_id: _row(
            row_id,
            phase,
            [_cat("F07:VISIBLE_CANARY", "opaque-atom-29" if label == "R" else "opaque-atom-71")],
        ),
    )
    add_case(
        "P3_PER_SLOT_FRESH_TOKEN",
        "Every row receives a fresh opaque categorical token; calibration identities never recur in holdout.",
        None,
        "SYNTHETIC_COUNTEREXAMPLE",
        lambda phase, label, index, row_id: _row(
            row_id,
            phase,
            [_cat("F07:FRESH", opaque_feature_token("P3_FRESH", row_id))],
        ),
    )
    add_case(
        "P4_CONTEXT_COUNT_ONLY",
        "Both latent classes contain the same exact category; only context total differs as count 1 versus 2.",
        None,
        "SYNTHETIC_COUNTEREXAMPLE",
        lambda phase, label, index, row_id: _row(
            row_id,
            phase,
            [_cat("F04:COUNT", "opaque-atom-41", 1 if label == "R" else 2)],
        ),
    )
    add_case(
        "P5_NUMERIC_EXACT_AND_MISSING",
        "One latent class has exact numeric 7; the other has exact 8 or explicit missing induced by absence.",
        None,
        "SYNTHETIC_COUNTEREXAMPLE",
        lambda phase, label, index, row_id: _row(
            row_id,
            phase,
            numerics=(
                [_num("F05:UID", 7)]
                if label == "R"
                else ([_num("F05:UID", 8)] if index < 10 else [])
            ),
        ),
    )

    def xor_builder(phase: str, label: str, index: int, row_id: str) -> dict[str, Any]:
        if label == "R":
            categories = (
                [_cat("F04:PAIR_A", "opaque-atom-11"), _cat("F07:PAIR_B", "opaque-atom-97")]
                if index < 10
                else []
            )
        else:
            categories = (
                [_cat("F04:PAIR_A", "opaque-atom-11")]
                if index < 10
                else [_cat("F07:PAIR_B", "opaque-atom-97")]
            )
        return _row(row_id, phase, categories)

    add_case(
        "P6_XOR_TWO_TOKEN",
        "Two opaque tokens in distinct contexts encode XOR; this distinguishes strict conjunction from a forbidden full Boolean lookup substitution.",
        None,
        "SYNTHETIC_SEMANTIC_DISCRIMINATOR_F4_REMAINS_UNDERDETERMINED",
        xor_builder,
    )

    def context_oov_builder(phase: str, label: str, index: int, row_id: str) -> dict[str, Any]:
        categories = []
        if label == "S":
            count = 2 if phase == "calibration" else 3
            categories = [_cat("F04:CONTEXT_OOV", opaque_feature_token("P7_CTX", row_id), count)]
        return _row(row_id, phase, categories)

    add_case(
        "P7_CONTEXT_TOTAL_OOV",
        "Calibration maps context absence versus total 2; holdout changes the second state to unseen total 3 with fresh atoms.",
        None,
        "SYNTHETIC_OOV_COUNTEREXAMPLE",
        context_oov_builder,
    )

    def f1_oov_builder(phase: str, label: str, index: int, row_id: str) -> dict[str, Any]:
        if label == "R":
            categories = [_cat("F04:F1_OOV", "opaque-atom-53")]
        elif phase == "holdout":
            categories = [_cat("F04:F1_OOV", opaque_feature_token("P8_F1OOV", row_id))]
        else:
            categories = []
        return _row(row_id, phase, categories)

    add_case(
        "P8_F1_OOV_SELECTOR_ABSENCE",
        "An OOV-only holdout row lacks the frozen selector; F1 ignores unknown atoms and uses the selector absence branch rather than row-level fallback.",
        None,
        "SYNTHETIC_F1_OOV_TRUTH_TABLE",
        f1_oov_builder,
    )

    features = {
        "cases": cases,
        "contains_labels": False,
        "membership_sha256": sha256_bytes(membership_raw),
        "schema": "WAVE025_C01_MINISUITE_FEATURE_CASES_V3",
    }
    return features, labels_doc


def build_contract() -> dict[str, Any]:
    return {
        "candidate_status": "MINISUITE_ONLY_NOT_MODEL_INPUT_CANON",
        "classes": list(CLASS_IDS),
        "fallback": {
            "F1_unknown_exact_tokens": "IGNORE_UNKNOWN_TOKENS_AND_APPLY_FROZEN_SELECTOR_PRESENCE_OR_ABSENCE_BRANCH",
            "mapping_family_unseen_state": "PREDICT_R_WITHOUT_RESELECTION",
            "no_eligible_rule": "PREDICT_R_FOR_EVERY_ROW",
        },
        "families": [
            {
                "availability": "EXECUTABLE_MINISUITE_CANDIDATE",
                "family": FAMILIES[0],
                "semantics": "one calibration-universe context+token selector; presence predicts one class and absence the other; unknown tokens are ignored",
            },
            {
                "availability": "EXECUTABLE_MINISUITE_CANDIDATE",
                "family": FAMILIES[1],
                "semantics": "one context; exact sum(count) or explicit MISSING maps to class; unseen total uses frozen R fallback",
            },
            {
                "availability": "EXECUTABLE_MINISUITE_CANDIDATE",
                "family": FAMILIES[2],
                "semantics": "one numeric identity; normalized exact rational or explicit MISSING maps to class; unseen value uses frozen R fallback",
            },
            {
                "ambiguities": [
                    "positive literals only versus negated literals",
                    "class orientation and fallback",
                    "one predicate versus a rule set",
                    "whether 00/01/10/11 is a forbidden full lookup",
                ],
                "availability": "REJECTED_UNDERDETERMINED_NOT_EXECUTED",
                "family": FAMILIES[3],
                "reason": F4_UNAVAILABLE_REASON,
            },
        ],
        "label_blind_freeze": {
            "calibration_universe_before_calibration_label_join": True,
            "feature_fixture_forbids_plaintext_class_in_row_id_token_context": True,
            "pair_prefilter": "descending calibration row support then canonical UTF-8 identity bytes; first 256",
            "universe_inputs": ["calibration feature rows"],
            "universe_prohibited_inputs": ["calibration labels", "holdout labels", "private control registry", "holdout rows"],
        },
        "phase_boundary": {
            "capability_guard": "deny non-system reads outside a 0700 temporary minimal root using an in-process Python audit hook",
            "freeze_process_inputs": ["canonical contract", "canonical feature case", "calibration-only join"],
            "freeze_process_outputs": ["universe", "selected rules", "calibration metrics", "calibration predictions", "holdout predictions"],
            "full_labels_artifact_in_capability_root": False,
            "holdout_labels_available_to_freeze_process": False,
            "outer_wrapper_seal": "hash exact output bytes outside worker and supply expected frozen hash to score through environment, never inside mutable payload",
            "score_process_inputs": ["canonical contract", "externally sealed frozen package", "holdout-only join"],
            "score_process_receives_feature_rows": False,
            "worker_input_schemas": "recursively closed",
        },
        "selection": {
            "balanced_accuracy": "mean of exact per-class recalls",
            "minimum_predicted_support_each_class": MIN_PREDICTED_CLASS_SUPPORT,
            "minimum_total_calibration_support": MIN_TOTAL_SUPPORT,
            "order": [
                "maximum calibration balanced accuracy",
                "minimum rule complexity units",
                "lexicographically minimum canonical UTF-8 JSON rule bytes",
            ],
        },
        "stable_recovery": "one selected frozen rule has exact recall 1 for R and S in calibration and holdout",
        "schema": "WAVE025_C01_MINISUITE_CONTRACT_V3",
        "serialization": "UTF-8; JSON sort_keys=true; separators comma/colon; ensure_ascii=false; one LF",
        "top_token_limit": TOP_TOKEN_LIMIT,
        "version": "0.3.0",
    }


def validate_membership_document(membership: dict[str, Any]) -> None:
    require_exact_keys(membership, {"cases", "generation", "schema"}, "membership")
    if membership["schema"] != "WAVE025_C01_OPAQUE_MEMBERSHIP_V3":
        raise ValueError("membership schema mismatch")
    all_ids = []
    for index, case in enumerate(membership["cases"]):
        require_exact_keys(case, {"case_id", "phases"}, f"membership.cases[{index}]")
        require_exact_keys(case["phases"], {"calibration", "holdout"}, "membership.phases")
        for phase in ("calibration", "holdout"):
            ids = case["phases"][phase]
            if len(ids) != 40 or ids != sorted(ids):
                raise ValueError("membership phase must contain 40 sorted ids")
            if any(not re.fullmatch(r"o_[0-9a-f]{24}", row_id) for row_id in ids):
                raise ValueError("membership id invalid")
            all_ids.extend(ids)
    if len(all_ids) != 640 or len(set(all_ids)) != 640:
        raise ValueError("membership population must be 640 unique ids")


def validate_label_document(labels_doc: dict[str, Any]) -> None:
    require_exact_keys(labels_doc, {"labels", "mapping_boundary", "schema"}, "labels")
    if labels_doc["schema"] != "WAVE025_C01_SYNTHETIC_LABEL_MAP_V3":
        raise ValueError("label source schema mismatch")
    seen = set()
    for index, item in enumerate(labels_doc["labels"]):
        require_exact_keys(item, {"class_id", "row_id"}, f"labels[{index}]")
        if item["class_id"] not in CLASS_IDS or item["row_id"] in seen:
            raise ValueError("invalid label source")
        seen.add(item["row_id"])
    if len(seen) != 640:
        raise ValueError("label source population must be 640")


def validate_feature_document(features: dict[str, Any]) -> None:
    require_exact_keys(features, {"cases", "contains_labels", "membership_sha256", "schema"}, "features")
    require_binding(features["membership_sha256"], "features.membership_sha256")
    if MEMBERSHIP_PATH.exists() and sha256_bytes(MEMBERSHIP_PATH.read_bytes()) != features["membership_sha256"]:
        raise ValueError("feature membership binding mismatch")
    if features.get("contains_labels") is not False:
        raise ValueError("feature fixture must explicitly contain no labels")
    raw_lower = canonical_bytes(features).lower()
    for forbidden in (b'"r"', b'"s"', b"role-r", b"role-s", b"-r-", b"-s-"):
        if forbidden in raw_lower:
            raise ValueError(f"plaintext class marker in feature bytes: {forbidden!r}")
    row_ids = []
    for case in features["cases"]:
        for row in case["rows"]:
            row_ids.append(row["row_id"])
            if len(row["row_id"]) != 26 or not row["row_id"].startswith("o_"):
                raise ValueError("row_id is not opaque fixed-width hex")
            int(row["row_id"][2:], 16)
            if set(row) != {"categories", "numerics", "phase", "row_id"}:
                raise ValueError(f"open row shape {row['row_id']}")
            for item in row["categories"]:
                if set(item) != {"context", "count", "token"}:
                    raise ValueError(f"invalid category {row['row_id']}")
                if not isinstance(item["count"], int) or item["count"] < 1:
                    raise ValueError(f"invalid category count {row['row_id']}")
            for item in row["numerics"]:
                if set(item) != {"identity", "value"} or item["value"]["denominator"] <= 0:
                    raise ValueError(f"invalid numeric {row['row_id']}")
    if len(row_ids) != len(set(row_ids)):
        raise ValueError("duplicate row ids")


def validate_inputs(features: dict[str, Any], labels_doc: dict[str, Any]) -> None:
    validate_feature_document(features)
    validate_label_document(labels_doc)
    row_ids = {row["row_id"] for case in features["cases"] for row in case["rows"]}
    labels = {item["row_id"]: item["class_id"] for item in labels_doc["labels"]}
    if set(labels) != row_ids or len(labels) != len(labels_doc["labels"]):
        raise ValueError("label population mismatch")
    for case in features["cases"]:
        counts: Counter[tuple[str, str]] = Counter()
        for row in case["rows"]:
            counts[(row["phase"], labels[row["row_id"]])] += 1
        if any(
            counts[(phase, label)] != 20
            for phase in ("calibration", "holdout")
            for label in CLASS_IDS
        ):
            raise ValueError(f"unbalanced case {case['case_id']}")


def labels_for_rows(labels_doc: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, str]:
    all_labels = {item["row_id"]: item["class_id"] for item in labels_doc["labels"]}
    return {row["row_id"]: all_labels[row["row_id"]] for row in rows}


def build_frozen_selections(
    features: dict[str, Any], labels_doc: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    validate_inputs(features, labels_doc)
    entries = []
    for case in features["cases"]:
        calibration = [row for row in case["rows"] if row["phase"] == "calibration"]
        calibration_map = labels_for_rows(labels_doc, calibration)
        join_doc = {
            "assignments": [
                {"class_id": calibration_map[row_id], "row_id": row_id}
                for row_id in sorted(calibration_map)
            ],
            "schema": "WAVE025_C01_CALIBRATION_JOIN_V3",
        }
        staged = {
            "calibration-join.json": canonical_bytes(join_doc),
            "case.json": canonical_bytes(case),
            "contract.json": canonical_bytes(contract),
        }
        expected = {
            "calibration_join_sha256": sha256_json(join_doc),
            "case_sha256": sha256_json(case),
            "contract_sha256": sha256_json(contract),
        }
        package, receipt = invoke_capability_phase(
            "freeze", staged, expected, "frozen-package.output.json"
        )
        validate_frozen_package(package)
        if receipt["external_output_sha256"] != sha256_json(package):
            raise ValueError("outer frozen package seal mismatch")
        entries.append(
            {
                "case_id": case["case_id"],
                "frozen_package": package,
                "frozen_package_byte_length": len(canonical_bytes(package)),
                "frozen_package_sha256": sha256_json(package),
                "phase_receipt": receipt,
            }
        )
    return {
        "cases": entries,
        "contract_sha256": sha256_json(contract),
        "schema": "WAVE025_C01_MINISUITE_FROZEN_SELECTIONS_V3",
        "selection_capability_root_contained_full_labels_artifact": False,
    }


def build_results(
    features: dict[str, Any],
    labels_doc: dict[str, Any],
    contract: dict[str, Any],
    frozen_doc: dict[str, Any],
) -> dict[str, Any]:
    validate_inputs(features, labels_doc)
    case_by_id = {case["case_id"]: case for case in features["cases"]}
    case_results = []
    scoring_receipts = []
    for entry in frozen_doc["cases"]:
        package = entry["frozen_package"]
        case = case_by_id[entry["case_id"]]
        holdout = [row for row in case["rows"] if row["phase"] == "holdout"]
        holdout_map = labels_for_rows(labels_doc, holdout)
        join_doc = {
            "assignments": [
                {"class_id": holdout_map[row_id], "row_id": row_id}
                for row_id in sorted(holdout_map)
            ],
            "schema": "WAVE025_C01_HOLDOUT_JOIN_V3",
        }
        staged = {
            "contract.json": canonical_bytes(contract),
            "frozen-package.json": canonical_bytes(package),
            "holdout-join.json": canonical_bytes(join_doc),
        }
        expected = {
            "contract_sha256": sha256_json(contract),
            "frozen_package_sha256": entry["frozen_package_sha256"],
            "holdout_join_sha256": sha256_json(join_doc),
        }
        scored, receipt = invoke_capability_phase(
            "score", staged, expected, "scored-case.output.json"
        )
        case_results.append(scored)
        scoring_receipts.append({"case_id": entry["case_id"], **receipt})
    stable_by_family = {
        family: [
            result["case_id"]
            for result in case_results
            if next(item for item in result["family_results"] if item["family"] == family)[
                "stable_recovery_calibration_and_holdout_exact_both_classes"
            ]
        ]
        for family in FAMILIES
    }
    return {
        "artifact_bindings": {
            "contract_sha256": sha256_json(contract),
            "features_sha256": sha256_json(features),
            "frozen_selections_sha256": sha256_json(frozen_doc),
            "labels_sha256": sha256_json(labels_doc),
            "membership_sha256": sha256_bytes(MEMBERSHIP_PATH.read_bytes()),
        },
        "case_results": case_results,
        "conclusion": {
            "actual_d0_status": "UNKNOWN_NOT_RUN_SYNTHETIC_MECHANISM_COMPATIBILITY_ONLY",
            "actual_d1_status": "UNKNOWN_NOT_RUN_AND_CROSS_PHASE_STABILITY_PREMISE_NOT_PUBLICLY_BOUND",
            "d0_public_design_simplest_compatible_tested_family": FAMILIES[0],
            "d1_conditional_if_cross_phase_stable_atom_then_compatible_family": FAMILIES[0],
            "f4_status": "REJECTED_UNDERDETERMINED_NOT_REPLACED_BY_BOOLEAN_LOOKUP",
            "families_with_distinct_synthetic_capability": {
                FAMILIES[1]: ["P4 context-total/count"],
                FAMILIES[2]: ["P5 numeric exact/missing"],
            },
            "no_claim_all_four_needed_or_not_needed": True,
            "synthetic_results_not_external_validity": True,
        },
        "external_public_source_bindings": {
            "d0_control_design_candidate_sha256": "36df6dca526eac8e8d23871b00ad6abefa3ccfe286448943586c7e95e969758d",
            "private_control_registry_read": False,
            "public_control_family_registration_sha256": "aafe698ef0a70097e74a81d41e8fbe64d7e9a581766719f2cb2360da1ba1a21a",
        },
        "families": list(FAMILIES),
        "implementation_bindings": {
            "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
            "membership_initializer_sha256": sha256_bytes(INITIALIZER_PATH.read_bytes()),
            "readme_sha256": sha256_bytes(README_PATH.read_bytes()),
            "tests_sha256": sha256_bytes(TEST_PATH.read_bytes()),
        },
        "phase_boundary": {
            "freeze_actual_read_sets_recorded": True,
            "freeze_capability_roots_excluded_full_labels_artifact": True,
            "frozen_hash_externally_sealed_and_supplied_out_of_payload": True,
            "score_process_received_feature_rows": False,
            "scoring_receipts": scoring_receipts,
        },
        "schema": "WAVE025_C01_MINISUITE_RESULTS_V3",
        "stable_cases_by_family": stable_by_family,
        "status": "SYNTHETIC_MINISUITE_NOT_MODEL_INPUT_CANON_ACTUAL_D0_D1_UNKNOWN_G_AND_3200_NOT_RUN",
        "version": "0.3.0",
    }


def build_all() -> dict[Path, Any]:
    features, labels_doc = build_cases()
    membership = json.loads(MEMBERSHIP_PATH.read_bytes())
    contract = build_contract()
    frozen_doc = build_frozen_selections(features, labels_doc, contract)
    results = build_results(features, labels_doc, contract, frozen_doc)
    return {
        MEMBERSHIP_PATH: membership,
        FEATURES_PATH: features,
        LABELS_PATH: labels_doc,
        CONTRACT_PATH: contract,
        FROZEN_PATH: frozen_doc,
        RESULTS_PATH: results,
    }


def write_or_check(check: bool) -> int:
    artifacts = build_all()
    if check:
        failures = [
            path.name
            for path, value in artifacts.items()
            if not path.exists() or path.read_bytes() != canonical_bytes(value)
        ]
        if failures:
            print("non-canonical or stale: " + ", ".join(failures), file=sys.stderr)
            return 1
        print(f"byte-exact canonical check passed: {len(artifacts)} artifacts")
        return 0
    for path, value in artifacts.items():
        path.write_bytes(canonical_bytes(value))
        print(f"wrote {path.name} sha256={sha256_json(value)}")
    return 0


def capability_environment() -> tuple[Path, Path]:
    root_value = os.environ.get("C01_CAPABILITY_ROOT")
    probe_value = os.environ.get("C01_FORBIDDEN_PROBE")
    if not root_value or not probe_value:
        raise ValueError("capability environment missing")
    root = Path(root_value).resolve()
    if Path.cwd().resolve() != root or Path(__file__).resolve().parent != root:
        raise ValueError("worker must execute from copied minimal capability root")
    return root, Path(probe_value)


def expected_environment_binding(name: str) -> str:
    return require_binding(os.environ.get("C01_EXPECTED_" + name.upper()), "env." + name)


def run_capability_freeze() -> int:
    root, probe = capability_environment()
    guard = install_capability_guard(root, probe)
    expected_contract = expected_environment_binding("contract_sha256")
    expected_case = expected_environment_binding("case_sha256")
    expected_join = expected_environment_binding("calibration_join_sha256")
    contract, _ = read_exact_canonical(root / "contract.json", expected_contract, "contract")
    case, _ = read_exact_canonical(root / "case.json", expected_case, "case")
    join_doc, _ = read_exact_canonical(
        root / "calibration-join.json", expected_join, "calibration_join"
    )
    if contract != build_contract():
        raise ValueError("contract content does not equal worker implementation contract")
    validate_case_document(case)
    calibration_ids = {row["row_id"] for row in case["rows"] if row["phase"] == "calibration"}
    calibration_labels = validate_join_document(
        join_doc, "WAVE025_C01_CALIBRATION_JOIN_V3", calibration_ids
    )
    package = freeze_case_core(
        case,
        calibration_labels,
        expected_contract,
        expected_case,
        expected_join,
    )
    validate_frozen_package(package)
    output_path = root / "frozen-package.output.json"
    output_path.write_bytes(canonical_bytes(package))
    sys.stdout.buffer.write(canonical_bytes(capability_receipt(guard)))
    return 0


def run_capability_score() -> int:
    root, probe = capability_environment()
    guard = install_capability_guard(root, probe)
    expected_contract = expected_environment_binding("contract_sha256")
    expected_frozen = expected_environment_binding("frozen_package_sha256")
    expected_join = expected_environment_binding("holdout_join_sha256")
    contract, _ = read_exact_canonical(root / "contract.json", expected_contract, "contract")
    package, _ = read_exact_canonical(
        root / "frozen-package.json", expected_frozen, "frozen_package"
    )
    join_doc, _ = read_exact_canonical(root / "holdout-join.json", expected_join, "holdout_join")
    if contract != build_contract():
        raise ValueError("contract content does not equal worker implementation contract")
    validate_frozen_package(package)
    if package["source_bindings"]["contract_sha256"] != expected_contract:
        raise ValueError("frozen package contract binding mismatch")
    holdout_ids = {
        item["row_id"]
        for item in package["family_freezes"][0]["holdout_predictions"]
    }
    holdout_labels = validate_join_document(
        join_doc, "WAVE025_C01_HOLDOUT_JOIN_V3", holdout_ids
    )
    scored = score_case_core(package, holdout_labels)
    output_path = root / "scored-case.output.json"
    output_path.write_bytes(canonical_bytes(scored))
    sys.stdout.buffer.write(canonical_bytes(capability_receipt(guard)))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--write", action="store_true")
    group.add_argument("--cap-freeze", action="store_true")
    group.add_argument("--cap-score", action="store_true")
    args = parser.parse_args()
    if args.cap_freeze:
        return run_capability_freeze()
    if args.cap_score:
        return run_capability_score()
    return write_or_check(check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
