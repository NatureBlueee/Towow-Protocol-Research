import hashlib
import json
import sys
import unittest
from copy import deepcopy
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import deterministic_math_duel as duel  # noqa: E402


EXTERNAL_TABLE_PIN = "0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5"


class RationalToBinary64Tests(unittest.TestCase):
    def test_midpoint_ties_even(self):
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(1) + Fraction(1, 1 << 53)),
            0x3FF0000000000000,
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(1) + Fraction(3, 1 << 53)),
            0x3FF0000000000002,
        )

    def test_normal_subnormal_underflow_boundaries(self):
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(1, 1 << 1022)),
            0x0010000000000000,
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction((1 << 52) - 1, 1 << 1074)),
            0x000FFFFFFFFFFFFF,
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(1, 1 << 1074)), 1
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(1, 1 << 1075)), 0
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(3, 1 << 1076)), 1
        )

    def test_max_finite_and_overflow_admission_boundary(self):
        maximum = duel.bits_to_fraction(duel.MAX_FINITE_BITS)
        self.assertEqual(duel.rational_to_binary64_bits(maximum), duel.MAX_FINITE_BITS)
        self.assertEqual(
            duel.rational_to_binary64_bits(maximum + Fraction(1 << 969)),
            duel.MAX_FINITE_BITS,
        )
        self.assertEqual(
            duel.rational_to_binary64_bits(maximum + Fraction(1 << 970)),
            duel.POS_INF_BITS,
        )

    def test_signed_decimal_zero_and_underflow_are_positive_zero(self):
        for lexeme in ("0", "-0", "-0.0e999"):
            self.assertEqual(
                duel.rational_to_binary64_bits(
                    duel.decimal_lexeme_to_fraction(lexeme)
                ),
                0,
            )
        self.assertEqual(
            duel.rational_to_binary64_bits(Fraction(-1, 1 << 1075)), 0
        )


class FrozenLog1pTableTests(unittest.TestCase):
    def test_table_is_frozen_canonical_and_exact_digest(self):
        raw = duel.TABLE_PATH.read_bytes()
        parsed = json.loads(raw)
        self.assertEqual(raw, duel.canonical_bytes(parsed))
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "0c91fac4170e278ff4e35b9c9ae026f749ffc326b9c94cc021c322d0993801d5",
        )
        self.assertEqual(len(parsed["entries"]), 256)

    def test_count_0_1_255_exact_kats(self):
        table, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        entries = table["entries"]
        self.assertEqual(entries[0]["bits_be_hex"], "0000000000000000")
        self.assertEqual(entries[1]["bits_be_hex"], "3fe62e42fefa39ef")
        self.assertEqual(entries[255]["bits_be_hex"], "40162e42fefa39ef")

    def test_all_256_match_stable_decimal_reference(self):
        table, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        for count, entry in enumerate(table["entries"]):
            expected = int(entry["bits_be_hex"], 16)
            references = {
                duel.decimal_log1p_bits(count, precision)
                for precision in (80, 160, 240)
            }
            self.assertEqual(references, {expected}, msg=f"count={count}")

    def _mutated_raw(self, mutate):
        value, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        value = deepcopy(value)
        mutate(value)
        return duel.canonical_bytes(value)

    def test_external_digest_is_a_loader_input_not_a_result_self_report(self):
        raw = bytearray(duel.TABLE_PATH.read_bytes())
        raw[0] ^= 1
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(bytes(raw), EXTERNAL_TABLE_PIN)
        self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_BINDING")

    def test_external_pin_wrong_types_are_total_failures(self):
        for pin in (None, 7, b"0" * 64):
            outcome = duel.lookup_count_log1p(1, pin)
            self.assertEqual(outcome["status"], "NOT_QUALIFIED")
            self.assertEqual(
                outcome["failure_code"], "NOT_QUALIFIED_TABLE_BINDING"
            )
            self.assertEqual(
                outcome["failure_stage"], "TABLE_EXPECTED_SHA_GRAMMAR"
            )

    def test_evil_str_subclass_cannot_override_digest_comparison(self):
        class EvilPin(str):
            def __eq__(self, other):
                return True

            def __ne__(self, other):
                return False

        current = duel.TABLE_PATH.read_bytes()
        one_ulp = current.replace(
            b'"bits_be_hex":"3fe62e42fefa39ef","count":"1"',
            b'"bits_be_hex":"3fe62e42fefa39ee","count":"1"',
            1,
        )
        self.assertEqual(len(one_ulp), len(current))
        self.assertNotEqual(hashlib.sha256(one_ulp).hexdigest(), EXTERNAL_TABLE_PIN)
        evil = EvilPin("0" * 64)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(one_ulp, evil)
        self.assertEqual(caught.exception.stage, "TABLE_EXPECTED_SHA_GRAMMAR")
        outcome = duel.lookup_count_log1p(1, evil)
        self.assertEqual(outcome["failure_stage"], "TABLE_EXPECTED_SHA_GRAMMAR")

        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(one_ulp, EXTERNAL_TABLE_PIN)
        self.assertEqual(caught.exception.stage, "TABLE_SHA256")
        wrong_current_pin = hashlib.sha256(one_ulp).hexdigest()
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(current, wrong_current_pin)
        self.assertEqual(caught.exception.stage, "TABLE_SHA256")

    def test_loader_rejects_non_builtin_raw_bytes_types(self):
        class BytesSubclass(bytes):
            pass

        for raw in (
            None,
            7,
            bytearray(duel.TABLE_PATH.read_bytes()),
            memoryview(duel.TABLE_PATH.read_bytes()),
            BytesSubclass(duel.TABLE_PATH.read_bytes()),
        ):
            with self.assertRaises(duel.StudyFailure) as caught:
                duel.load_table_bytes(raw, EXTERNAL_TABLE_PIN)
            self.assertEqual(caught.exception.stage, "TABLE_RAW_TYPE")

    def test_table_rejects_negative_noncanonical_or_wrong_width_bits(self):
        for replacement in (
            "-000000000000001",
            "ABCDEF0123456789",
            "7ff0000000000000",
        ):
            raw = self._mutated_raw(
                lambda value, replacement=replacement: value["entries"][1].__setitem__(
                    "bits_be_hex", replacement
                )
            )
            with self.assertRaises(duel.StudyFailure) as caught:
                duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
            self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_STRUCTURE")
        raw = self._mutated_raw(
            lambda value: value["entries"][1].__setitem__(
                "bits_be_hex", "10000000000000000"
            )
        )
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_STRUCTURE")

    def test_table_rejects_duplicate_index_and_extra_members(self):
        raw = self._mutated_raw(
            lambda value: value["entries"][2].__setitem__("count", "1")
        )
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.stage, "TABLE_DUPLICATE_COUNT")

        value, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        value = deepcopy(value)
        value["entries"][2]["count"], value["entries"][3]["count"] = "3", "2"
        raw = duel.canonical_bytes(value)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.stage, "TABLE_COUNT_INDEX")

        value, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        value = deepcopy(value)
        value["extraxx"] = value.pop("version")  # same key length keeps byte ceiling meaningful
        raw = duel.canonical_bytes(value)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_STRUCTURE")

        value, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        value = deepcopy(value)
        value["entries"][1]["extra"] = value["entries"][1].pop("count")
        raw = duel.canonical_bytes(value)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.stage, "TABLE_ENTRY_KEYS")

        with self.assertRaises(duel.StudyFailure) as caught:
            duel._strict_object([("same", 1), ("same", 2)])
        self.assertEqual(caught.exception.stage, "TABLE_DUPLICATE_KEY")

    def test_table_rejects_non_rfc_constants_and_metadata_drift(self):
        original, _ = duel.load_table(EXTERNAL_TABLE_PIN)
        for nonfinite in (float("nan"), float("inf"), float("-inf")):
            value = deepcopy(original)
            value["version"] = nonfinite
            raw = (
                json.dumps(
                    value,
                    allow_nan=True,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            delta = duel.EXPECTED_TABLE_BYTES - len(raw)
            source = value["construction_source"]
            value["construction_source"] = (
                source + ("x" * delta) if delta >= 0 else source[:delta]
            )
            raw = (
                json.dumps(
                    value,
                    allow_nan=True,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            self.assertEqual(len(raw), duel.EXPECTED_TABLE_BYTES)
            with self.assertRaises(duel.StudyFailure) as caught:
                duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
            self.assertEqual(caught.exception.stage, "TABLE_JSON_CONSTANT")

        value = deepcopy(original)
        value["version"] = "0.1.1"
        raw = duel.canonical_bytes(value)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.stage, "TABLE_METADATA")

    def _raw_with_version_token(self, token: bytes) -> bytes:
        raw = duel.TABLE_PATH.read_bytes().replace(
            b'"version":"0.1.0"', b'"version":' + token, 1
        )
        delta = duel.EXPECTED_TABLE_BYTES - len(raw)
        anchor = b'"construction_source":"'
        if delta >= 0:
            raw = raw.replace(anchor, anchor + (b"x" * delta), 1)
        else:
            removable = b"one-time Python math.log1p"
            shortened = removable[: len(removable) + delta]
            raw = raw.replace(removable, shortened, 1)
        self.assertEqual(len(raw), duel.EXPECTED_TABLE_BYTES)
        return raw

    def test_json_exponent_overflow_and_surrogate_are_stable_failures(self):
        overflow = self._raw_with_version_token(b"1e9999")
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(overflow, hashlib.sha256(overflow).hexdigest())
        self.assertEqual(caught.exception.stage, "TABLE_JSON_NUMBER")

        surrogate = self._raw_with_version_token(b'"\\ud800"')
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(surrogate, hashlib.sha256(surrogate).hexdigest())
        self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_STRUCTURE")
        self.assertIn(
            caught.exception.stage, ("TABLE_CANONICAL_ENCODER", "TABLE_JSON")
        )

    def test_deep_json_recursion_is_a_stable_failure(self):
        depth = 1100
        deep = ("[" * depth) + '"x"' + ("]" * depth)
        metadata = duel.EXPECTED_TABLE_METADATA

        def assemble(padding):
            return (
                "{"
                + '"candidate_status":'
                + json.dumps(metadata["candidate_status"])
                + ',"construction_source":'
                + json.dumps("x" * padding)
                + ',"entries":[]'
                + ',"runtime_rule":'
                + json.dumps(metadata["runtime_rule"])
                + ',"schema":'
                + json.dumps(metadata["schema"])
                + ',"serialization":'
                + json.dumps(metadata["serialization"])
                + ',"version":'
                + deep
                + "}\n"
            ).encode("utf-8")

        base = assemble(0)
        raw = assemble(duel.EXPECTED_TABLE_BYTES - len(base))
        self.assertEqual(len(raw), duel.EXPECTED_TABLE_BYTES)
        with self.assertRaises(duel.StudyFailure) as caught:
            duel.load_table_bytes(raw, hashlib.sha256(raw).hexdigest())
        self.assertEqual(caught.exception.code, "NOT_QUALIFIED_TABLE_STRUCTURE")
        self.assertIn(
            caught.exception.stage, ("TABLE_JSON", "TABLE_CANONICAL_ENCODER")
        )

    def test_count_clip_is_executable_and_total(self):
        self.assertEqual(
            duel.lookup_count_log1p(0, EXTERNAL_TABLE_PIN)["bits_be_hex"],
            "0000000000000000",
        )
        self.assertEqual(
            duel.lookup_count_log1p(1, EXTERNAL_TABLE_PIN)["bits_be_hex"],
            "3fe62e42fefa39ef",
        )
        self.assertEqual(
            duel.lookup_count_log1p(255, EXTERNAL_TABLE_PIN)["bits_be_hex"],
            "40162e42fefa39ef",
        )
        self.assertEqual(
            duel.lookup_count_log1p(256, EXTERNAL_TABLE_PIN)["bits_be_hex"],
            "40162e42fefa39ef",
        )
        self.assertEqual(
            duel.lookup_count_log1p(-1, EXTERNAL_TABLE_PIN)["failure_code"],
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
        )
        self.assertEqual(
            duel.lookup_count_log1p(1 << 64, EXTERNAL_TABLE_PIN)["failure_code"],
            "NOT_QUALIFIED_NUMERIC_BOUNDS",
        )


class PathDuelTests(unittest.TestCase):
    def test_signed_collision_has_real_order_sensitive_counterexample(self):
        first = [Fraction(1 << 53), Fraction(1), Fraction(-(1 << 53))]
        second = [Fraction(1 << 53), Fraction(-(1 << 53)), Fraction(1)]
        self.assertEqual(duel.path_a_accumulate(first)[0], 0)
        self.assertEqual(duel.path_a_accumulate(second)[0], 0x3FF0000000000000)
        self.assertEqual(duel.path_b_accumulate(first), 0x3FF0000000000000)
        self.assertEqual(duel.path_b_accumulate(second), 0x3FF0000000000000)

    def test_many_small_terms_are_not_recovered_by_fixed_order_binary64(self):
        terms = [Fraction(1)] + [Fraction(1, 1 << 60)] * 1024
        self.assertEqual(duel.path_a_accumulate(terms)[0], 0x3FF0000000000000)
        self.assertEqual(duel.path_b_accumulate(terms), 0x3FF0000000000004)

    def test_family_norm_exact_dyadic_path_retains_small_squares(self):
        components = [Fraction(1)] + [Fraction(1, 1 << 27)] * 5
        a_norm, a_sum, _ = duel.path_a_norm(components)
        b_norm, b_sum = duel.path_b_norm(components)
        self.assertEqual(a_sum, 0x3FF0000000000000)
        self.assertEqual(a_norm, 0x3FF0000000000000)
        self.assertEqual(b_sum, Fraction((1 << 54) + 5, 1 << 54))
        self.assertEqual(b_norm, 0x3FF0000000000001)

    def test_exact_integer_sqrt_oracle_handles_control_and_boundary(self):
        self.assertEqual(duel.exact_sqrt_to_binary64_bits(Fraction(25)), 0x4014000000000000)
        # The exact midpoint between 1.0 and its successor ties to 1.0.
        midpoint = (
            duel.bits_to_fraction(0x3FF0000000000000)
            + duel.bits_to_fraction(0x3FF0000000000001)
        ) / 2
        self.assertEqual(
            duel.exact_sqrt_to_binary64_bits(midpoint * midpoint),
            0x3FF0000000000000,
        )

    def test_large_offset_unit_shift_separates_pre_round_from_last_round(self):
        center = Fraction(1 << 53)
        value = center + 1
        self.assertEqual(duel.path_a_transform(value, center, Fraction(1)), 0)
        self.assertEqual(
            duel.path_b_transform(value, center, Fraction(1)),
            0x3FF0000000000000,
        )


class TotalEvaluatorRegressionTests(unittest.TestCase):
    def assert_failure(self, outcome, code, stage=None):
        self.assertEqual(outcome["status"], "NOT_QUALIFIED")
        self.assertEqual(outcome["failure_code"], code)
        if stage is not None:
            self.assertEqual(outcome["failure_stage"], stage)

    def test_every_leaf_is_admitted_before_b_exact_cancellation(self):
        outcome = duel.evaluate_accumulation(
            [Fraction(1 << 1024), Fraction(-(1 << 1024)), Fraction(1)],
            "B_EXACT_LAST_ROUND",
        )
        self.assert_failure(outcome, "NOT_QUALIFIED_NUMERIC_RANGE", "LEAF_RANGE")
        self.assertEqual(outcome["failure_provenance"], "term[0]/term-0000")

    def test_sum_norm_sqrt_and_scale_fail_with_stable_codes_not_exceptions(self):
        maximum = duel.bits_to_fraction(duel.MAX_FINITE_BITS)
        cases = [
            (
                duel.evaluate_accumulation(
                    [Fraction(1 << 1023), Fraction(1 << 1023)],
                    "A_FIXED_BINARY64",
                ),
                "NOT_QUALIFIED_NUMERIC_RANGE",
            ),
            (
                duel.evaluate_norm([maximum], "A_FIXED_BINARY64"),
                "NOT_QUALIFIED_NUMERIC_RANGE",
            ),
            (
                duel.evaluate_norm([maximum, maximum], "B_EXACT_LAST_ROUND"),
                "NOT_QUALIFIED_NUMERIC_RANGE",
            ),
            (
                duel.evaluate_standardize(
                    Fraction(1),
                    Fraction(0),
                    Fraction(1, 1 << 1075),
                    "A_FIXED_BINARY64",
                ),
                "NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW",
            ),
            (
                duel.evaluate_standardize(
                    Fraction(1),
                    Fraction(0),
                    Fraction(1, 1 << 1075),
                    "B_EXACT_LAST_ROUND",
                ),
                "NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW",
            ),
            (
                duel.evaluate_standardize(
                    Fraction(1), Fraction(0), Fraction(0), "A_FIXED_BINARY64"
                ),
                "NOT_QUALIFIED_NUMERIC_SCALE_ZERO",
            ),
            (
                duel.evaluate_standardize(
                    Fraction(1), Fraction(0), Fraction(0), "B_EXACT_LAST_ROUND"
                ),
                "NOT_QUALIFIED_NUMERIC_SCALE_ZERO",
            ),
            (
                duel.evaluate_sqrt(Fraction(-1), "negative"),
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
            ),
            (
                duel.evaluate_standardize(
                    Fraction(1), Fraction(0), Fraction(-1), "B_EXACT_LAST_ROUND"
                ),
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
            ),
            (
                duel.evaluate_accumulation([float("nan")], "B_EXACT_LAST_ROUND"),
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
            ),
            (
                duel.evaluate_accumulation([float("inf")], "A_FIXED_BINARY64"),
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
            ),
        ]
        for outcome, code in cases:
            self.assert_failure(outcome, code)

    def test_leaf_digit_term_and_intermediate_caps_are_executable(self):
        too_many_digits = Fraction(10**duel.MAX_CANONICAL_RATIONAL_DIGITS, 1)
        self.assert_failure(
            duel.evaluate_accumulation([too_many_digits], "B_EXACT_LAST_ROUND"),
            "NOT_QUALIFIED_NUMERIC_BOUNDS",
            "LEAF_DIGITS",
        )
        self.assert_failure(
            duel.evaluate_accumulation(
                [Fraction(1, 1 << (duel.STUDY_MAX_ABS_RATIONAL_BINARY_EXPONENT + 1))],
                "B_EXACT_LAST_ROUND",
            ),
            "NOT_QUALIFIED_NUMERIC_BOUNDS",
            "LEAF_EXPONENT",
        )
        self.assert_failure(
            duel.evaluate_accumulation(
                [Fraction(0)] * (duel.STUDY_MAX_TERMS + 1),
                "B_EXACT_LAST_ROUND",
            ),
            "NOT_QUALIFIED_NUMERIC_TERM_LIMIT",
            "COLUMN_TERM_COUNT",
        )
        denominator_a = (1 << 9000) - 1
        denominator_b = (1 << 9000) + 1
        self.assert_failure(
            duel.evaluate_accumulation(
                [Fraction(1, denominator_a), Fraction(1, denominator_b)],
                "B_EXACT_LAST_ROUND",
            ),
            "NOT_QUALIFIED_NUMERIC_BOUNDS",
            "COLUMN_EXACT_ADD",
        )

    def test_column_identity_order_duplicate_and_zero_are_closed(self):
        self.assert_failure(
            duel.evaluate_column_accumulation(
                [("b", Fraction(1)), ("a", Fraction(1))], "B_EXACT_LAST_ROUND"
            ),
            "NOT_QUALIFIED_NUMERIC_ORDER",
        )
        self.assert_failure(
            duel.evaluate_column_accumulation(
                [("a", Fraction(1)), ("a", Fraction(-1))], "B_EXACT_LAST_ROUND"
            ),
            "NOT_QUALIFIED_NUMERIC_DUPLICATE_TERM",
        )
        self.assert_failure(
            duel.evaluate_column_accumulation(
                [("\ud800", Fraction(1))], "B_EXACT_LAST_ROUND"
            ),
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
            "COLUMN_IDENTITY_UTF8",
        )
        for path in ("A_FIXED_BINARY64", "B_EXACT_LAST_ROUND"):
            result = duel.evaluate_column_accumulation(
                [("a", Fraction(7, 4)), ("b", Fraction(-7, 4))], path
            )
            self.assertEqual(result["bits_be_hex"], "0000000000000000")

    def test_clip_then_family_normalization_and_zero_norm_are_explicit(self):
        for path in ("A_FIXED_BINARY64", "B_EXACT_LAST_ROUND"):
            clipped = duel.evaluate_standardize(
                Fraction(100), Fraction(0), Fraction(1), path
            )
            self.assertEqual(clipped["bits_be_hex"], "4020000000000000")  # +8
            zero = duel.evaluate_family_normalization([Fraction(0), Fraction(0)], path)
            self.assertEqual(zero["norm_bits_be_hex"], "0000000000000000")
            self.assertEqual(
                zero["component_bits_be_hex"],
                ["0000000000000000", "0000000000000000"],
            )
            normalized = duel.evaluate_family_normalization(
                [Fraction(3), Fraction(4)], path
            )
            self.assertEqual(normalized["status"], "OK")
            self.assertEqual(normalized["norm_bits_be_hex"], "4014000000000000")
            for bits_hex in normalized["component_bits_be_hex"]:
                self.assertFalse(duel._is_nonfinite_bits(int(bits_hex, 16)))

    def test_family_normalization_executes_clipped_binary64_input_admission(self):
        for path in ("A_FIXED_BINARY64", "B_EXACT_LAST_ROUND"):
            self.assert_failure(
                duel.evaluate_family_normalization(
                    [Fraction(100), Fraction(0)], path
                ),
                "NOT_QUALIFIED_NUMERIC_RANGE",
                "FAMILY_INPUT_CLIP_BOUND",
            )
            self.assert_failure(
                duel.evaluate_family_normalization([Fraction(1, 3)], path),
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
                "FAMILY_INPUT_BINARY64_EXACT",
            )
            bounded = duel.evaluate_family_normalization(
                [Fraction(8), Fraction(-8)], path
            )
            self.assertEqual(bounded["status"], "OK")
            zero = duel.evaluate_family_normalization([Fraction(0)], path)
            self.assertEqual(zero["component_bits_be_hex"], ["0000000000000000"])

        minimum_subnormal = Fraction(1, 1 << 1074)
        path_a = duel.evaluate_family_normalization(
            [minimum_subnormal], "A_FIXED_BINARY64"
        )
        path_b = duel.evaluate_family_normalization(
            [minimum_subnormal], "B_EXACT_LAST_ROUND"
        )
        self.assertEqual(path_a["status"], "OK")
        self.assertEqual(path_b["status"], "OK")
        self.assertEqual(path_a["component_bits_be_hex"], ["0000000000000000"])
        self.assertEqual(path_b["component_bits_be_hex"], ["3ff0000000000000"])

    def test_family_normalization_freezes_exact_list_and_fraction_leaf_types(self):
        malformed_containers = [
            None,
            (Fraction(1),),
            (value for value in [Fraction(1)]),
            Fraction(1),
            "8",
        ]
        malformed_leaves = [["8"], [True], [8], [8.0]]
        for path in ("A_FIXED_BINARY64", "B_EXACT_LAST_ROUND"):
            for components in malformed_containers:
                self.assert_failure(
                    duel.evaluate_family_normalization(components, path),
                    "NOT_QUALIFIED_NUMERIC_DOMAIN",
                    "FAMILY_INPUT_CONTAINER_TYPE",
                )
            for components in malformed_leaves:
                self.assert_failure(
                    duel.evaluate_family_normalization(components, path),
                    "NOT_QUALIFIED_NUMERIC_DOMAIN",
                    "FAMILY_INPUT_LEAF_TYPE",
                )


class QuantileTests(unittest.TestCase):
    def test_type7_and_averaged_inverted_cdf_are_distinct(self):
        values = [Fraction(0), Fraction(10), Fraction(20), Fraction(30)]
        self.assertEqual(
            duel.exact_quantile(values, Fraction(1, 4), "type7"), Fraction(15, 2)
        )
        self.assertEqual(
            duel.exact_quantile(values, Fraction(3, 4), "type7"), Fraction(45, 2)
        )
        self.assertEqual(
            duel.exact_quantile(
                values, Fraction(1, 4), "averaged_inverted_cdf"
            ),
            Fraction(5),
        )
        self.assertEqual(
            duel.exact_quantile(
                values, Fraction(3, 4), "averaged_inverted_cdf"
            ),
            Fraction(25),
        )

    def test_zero_iqr_uses_scale_one_and_preserves_shift(self):
        center, iqr, scale = duel.robust_parameters([Fraction(7)] * 4, "type7")
        self.assertEqual((center, iqr, scale), (Fraction(7), Fraction(0), Fraction(1)))
        self.assertEqual(
            duel.path_b_transform(Fraction(8), center, scale), 0x3FF0000000000000
        )


class ArtifactTests(unittest.TestCase):
    def test_results_are_byte_rebuildable_and_have_no_formal_claim(self):
        raw = duel.RESULTS_PATH.read_bytes()
        self.assertEqual(
            raw, duel.canonical_bytes(duel.build_results(EXTERNAL_TABLE_PIN))
        )
        parsed = json.loads(raw)
        self.assertEqual(
            parsed["candidate_status"],
            "CANDIDATE_STUDY_NOT_CANON__NO_G__NO_FORMAL_3200",
        )
        self.assertFalse(parsed["dependency_boundary"]["depends_on_rejected_c01_v0"])
        self.assertFalse(parsed["dependency_boundary"]["g_executed"])
        self.assertFalse(parsed["decision"]["path_b_wholesale_deletable"])
        self.assertEqual(parsed["decision"]["minimal_sufficient_set"], "UNKNOWN_NOT_CLAIMED")
        self.assertEqual(parsed["decision"]["formal_reachability"], "UNKNOWN")
        self.assertEqual(
            parsed["log1p_table_a_vs_decimal_reference_b"]["correct_rounding_status"],
            "CORROBORATED_NOT_PROVEN",
        )
        self.assertGreaterEqual(
            len(parsed["path_duel"]["true_divergence_case_ids"]), 4
        )


if __name__ == "__main__":
    unittest.main()
