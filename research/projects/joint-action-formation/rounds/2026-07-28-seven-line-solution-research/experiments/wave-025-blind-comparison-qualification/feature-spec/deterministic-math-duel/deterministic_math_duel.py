#!/usr/bin/env python3
"""Wave025 deterministic-math candidate duel.

This is deliberately a study, not the DETERMINISTIC-MATH canon.  It compares
two reproducible numerical semantics using only the Python standard library:

* A: round every declared binary64 operation, in a frozen order, and use a
  frozen count/log1p table.
* B: accumulate exact rationals/dyadics and round once; use an integer proof
  procedure for sqrt and a high-precision Decimal stability reference for
  log1p table construction.

No model, G run, or formal population is read by this program.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Optional, Sequence


HERE = Path(__file__).resolve().parent
TABLE_PATH = HERE / "COUNT-LOG1P-BINARY64.candidate.json"
RESULTS_PATH = HERE / "RESULTS.candidate.json"
REDTEAM_PATH = HERE / "INDEPENDENT-REDTEAM.md"
FINAL_REVIEW_PATH = HERE / "FINAL-INDEPENDENT-ACCEPTANCE.md"
THIRD_REVIEW_PATH = HERE / "FINAL-THIRD-FIX-INDEPENDENT-ACCEPTANCE.md"

MAX_FINITE_BITS = 0x7FEFFFFFFFFFFFFF
POS_INF_BITS = 0x7FF0000000000000
SIGN_BIT = 1 << 63
EXPECTED_TABLE_BYTES = 12870
TABLE_HEX_RE = re.compile(r"^[0-9a-f]{16}$")
EXPECTED_TABLE_METADATA = {
    "candidate_status": "FROZEN_STUDY_TABLE_NOT_CANON",
    "construction_source": (
        "one-time Python math.log1p on the study host; independently checked "
        "against Decimal ln at 80/160/240 digits; this is not an MPFR claim"
    ),
    "runtime_rule": "lookup only for saturated count=min(exact_count,255); no runtime libm",
    "schema": "WAVE025_COUNT_LOG1P_BINARY64_STUDY_V1",
    "serialization": "canonical compact UTF-8 JSON plus one LF",
    "version": "0.1.0",
}

# These are executable study guards, not proposed formal limits.  The leaf
# digit ceiling reuses the V2S primitives bound.  The other caps make this duel
# a total, bounded experiment while formal reachability/cost remains UNKNOWN.
MAX_CANONICAL_RATIONAL_DIGITS = 4864
UPSTREAM_MAX_ABS_DECIMAL_EXPONENT = 4096
STUDY_MAX_ABS_RATIONAL_BINARY_EXPONENT = 14000
STUDY_MAX_TERMS = 4096
STUDY_MAX_INTERMEDIATE_BITS = 16384
STUDY_MAX_QUANTILE_SAMPLES = 4096
STUDY_MAX_TABLE_BYTES = 16384
CLIP_ABS = Fraction(8)

FAILURE_CODES = (
    "NOT_QUALIFIED_NUMERIC_BOUNDS",
    "NOT_QUALIFIED_NUMERIC_DOMAIN",
    "NOT_QUALIFIED_NUMERIC_DUPLICATE_TERM",
    "NOT_QUALIFIED_NUMERIC_ORDER",
    "NOT_QUALIFIED_NUMERIC_RANGE",
    "NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW",
    "NOT_QUALIFIED_NUMERIC_SCALE_ZERO",
    "NOT_QUALIFIED_NUMERIC_TERM_LIMIT",
    "NOT_QUALIFIED_TABLE_BINDING",
    "NOT_QUALIFIED_TABLE_STRUCTURE",
)
DECIMAL_RE = re.compile(
    r"^(?P<sign>-?)(?P<int>0|[1-9][0-9]*)(?:\.(?P<frac>[0-9]+))?(?:[eE](?P<exp>[+-]?[0-9]+))?$"
)


class StudyFailure(ValueError):
    """Stable failure used at every V2 study admission/operator boundary."""

    def __init__(self, code: str, stage: str, provenance: str):
        if code not in FAILURE_CODES:
            raise AssertionError(f"unregistered failure code: {code}")
        super().__init__(f"{code}:{stage}:{provenance}")
        self.code = code
        self.stage = stage
        self.provenance = provenance


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bit_hex(bits: int) -> str:
    return f"{bits:016x}"


def bits_to_float(bits: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def float_to_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def bits_to_fraction(bits: int) -> Fraction:
    """Return the exact value of a finite binary64 bit pattern."""
    sign = -1 if bits & SIGN_BIT else 1
    exponent = (bits >> 52) & 0x7FF
    fraction = bits & ((1 << 52) - 1)
    if exponent == 0x7FF:
        raise ValueError("nonfinite binary64 has no Fraction value")
    if exponent == 0:
        if fraction == 0:
            return Fraction(0)
        value = Fraction(fraction, 1 << 1074)
    else:
        significand = (1 << 52) | fraction
        shift = exponent - 1023 - 52
        value = (
            Fraction(significand << shift, 1)
            if shift >= 0
            else Fraction(significand, 1 << (-shift))
        )
    return sign * value


def _floor_log2_fraction(value: Fraction) -> int:
    if value <= 0:
        raise ValueError("log2 domain")
    numerator = value.numerator
    denominator = value.denominator
    exponent = numerator.bit_length() - denominator.bit_length()
    if exponent >= 0:
        if numerator < (denominator << exponent):
            exponent -= 1
    elif (numerator << (-exponent)) < denominator:
        exponent -= 1
    return exponent


def _round_positive_ratio_ties_even(numerator: int, denominator: int) -> int:
    quotient, remainder = divmod(numerator, denominator)
    comparison = 2 * remainder - denominator
    if comparison > 0 or (comparison == 0 and quotient & 1):
        quotient += 1
    return quotient


def rational_to_binary64_bits(value: Fraction) -> int:
    """Canonical RN-ties-even binary64 conversion with zero canonicalized +0.

    The returned infinity bit pattern is only a mathematical conversion result.
    The candidate model policy treats it as NOT_QUALIFIED_NUMERIC_RANGE rather
    than emitting a nonfinite matrix value.
    """
    value = Fraction(value)
    if value == 0:
        return 0
    sign = SIGN_BIT if value < 0 else 0
    value = abs(value)
    exponent = _floor_log2_fraction(value)

    if exponent >= -1022:
        shift = 52 - exponent
        if shift >= 0:
            significand = _round_positive_ratio_ties_even(
                value.numerator << shift, value.denominator
            )
        else:
            significand = _round_positive_ratio_ties_even(
                value.numerator, value.denominator << (-shift)
            )
        if significand == (1 << 53):
            exponent += 1
            significand = 1 << 52
        if exponent > 1023:
            return sign | POS_INF_BITS
        return sign | ((exponent + 1023) << 52) | (significand - (1 << 52))

    subnormal = _round_positive_ratio_ties_even(
        value.numerator << 1074, value.denominator
    )
    if subnormal == 0:
        return 0  # project-wide matrix canonicalization erases negative zero
    if subnormal >= (1 << 52):
        return sign | (1 << 52)
    return sign | subnormal


def _is_nonfinite_bits(bits: int) -> bool:
    return bits & 0x7FF0000000000000 == 0x7FF0000000000000


def canonicalize_zero_bits(bits: int) -> int:
    return 0 if bits & 0x7FFFFFFFFFFFFFFF == 0 else bits


def _decimal_digits(value: int) -> int:
    return 1 if value == 0 else len(str(abs(value)))


def _resource_shape(value: Fraction) -> dict[str, int]:
    return {
        "denominator_bits": value.denominator.bit_length(),
        "denominator_digits": _decimal_digits(value.denominator),
        "numerator_bits": abs(value.numerator).bit_length(),
        "numerator_digits": _decimal_digits(value.numerator),
    }


def _check_intermediate(value: Fraction, stage: str, provenance: str) -> dict[str, int]:
    shape = _resource_shape(value)
    if (
        shape["numerator_bits"] > STUDY_MAX_INTERMEDIATE_BITS
        or shape["denominator_bits"] > STUDY_MAX_INTERMEDIATE_BITS
    ):
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_BOUNDS", stage, provenance)
    return shape


def admit_rational_leaf(value: Fraction, provenance: str) -> tuple[Fraction, int, dict[str, int]]:
    """Independently admit one post-parser rational leaf before any combining.

    Feature-vector rational leaves have already lost their source number lexeme,
    so this layer can re-check canonical numerator/denominator digits and model
    range but cannot reconstruct upstream lexeme/significand/exponent lengths.
    That upstream admission remains a separately named dependency.
    """
    try:
        value = Fraction(value)
    except (TypeError, ValueError, ZeroDivisionError, OverflowError):
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "LEAF_PARSE", provenance)
    shape = _resource_shape(value)
    if (
        shape["numerator_digits"] > MAX_CANONICAL_RATIONAL_DIGITS
        or shape["denominator_digits"] > MAX_CANONICAL_RATIONAL_DIGITS
    ):
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_BOUNDS", "LEAF_DIGITS", provenance)
    if value != 0:
        binary_exponent = _floor_log2_fraction(abs(value))
        shape["binary_exponent"] = binary_exponent
        if abs(binary_exponent) > STUDY_MAX_ABS_RATIONAL_BINARY_EXPONENT:
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_BOUNDS", "LEAF_EXPONENT", provenance)
    bits = canonicalize_zero_bits(rational_to_binary64_bits(value))
    if _is_nonfinite_bits(bits):
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_RANGE", "LEAF_RANGE", provenance)
    return value, bits, shape


def _failure_outcome(failure: StudyFailure, metrics: Optional[dict[str, object]] = None) -> dict[str, object]:
    return {
        "failure_code": failure.code,
        "failure_provenance": failure.provenance,
        "failure_stage": failure.stage,
        "metrics": metrics or {},
        "status": "NOT_QUALIFIED",
    }


def _success_outcome(
    bits: int,
    metrics: Optional[dict[str, object]] = None,
    **extra: object,
) -> dict[str, object]:
    bits = canonicalize_zero_bits(bits)
    if _is_nonfinite_bits(bits):
        raise AssertionError("success outcome cannot contain nonfinite bits")
    return {
        "bits_be_hex": bit_hex(bits),
        "metrics": metrics or {},
        "status": "OK",
        **extra,
    }


def _checked_output_bits(value: Fraction, stage: str, provenance: str) -> int:
    bits = canonicalize_zero_bits(rational_to_binary64_bits(value))
    if _is_nonfinite_bits(bits):
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_RANGE", stage, provenance)
    return bits


def decimal_lexeme_to_fraction(lexeme: str) -> Fraction:
    """Parse a finite JSON-style decimal lexeme without a binary float."""
    match = DECIMAL_RE.fullmatch(lexeme)
    if not match:
        raise ValueError(f"invalid finite decimal lexeme: {lexeme!r}")
    integer = match.group("int") or "0"
    fractional = match.group("frac") or ""
    digits = int(integer + fractional)
    if match.group("sign"):
        digits = -digits
    exponent = int(match.group("exp") or "0") - len(fractional)
    if exponent >= 0:
        return Fraction(digits * (10**exponent), 1)
    return Fraction(digits, 10 ** (-exponent))


def exact_sqrt_to_binary64_bits(value: Fraction) -> int:
    """Correctly round sqrt(value) using integer/rational comparisons only.

    A monotone binary search finds the adjacent finite binary64 values.  The
    exact rational input is then compared with the square of their midpoint;
    exact midpoint ties use the even low bit.  This is an independent integer
    oracle, not MPFR/Arb and not a claim about Decimal sqrt.
    """
    value = Fraction(value)
    if value < 0:
        raise ValueError("sqrt domain")
    if value == 0:
        return 0

    maximum = bits_to_fraction(MAX_FINITE_BITS)
    overflow_midpoint = maximum + Fraction(1 << 970, 1)
    if value >= overflow_midpoint * overflow_midpoint:
        return POS_INF_BITS

    low = 0
    high = MAX_FINITE_BITS
    while low < high:
        middle = (low + high + 1) // 2
        candidate = bits_to_fraction(middle)
        if candidate * candidate <= value:
            low = middle
        else:
            high = middle - 1
    if low == MAX_FINITE_BITS:
        return low
    upper = low + 1
    lower_value = bits_to_fraction(low)
    upper_value = bits_to_fraction(upper)
    midpoint = (lower_value + upper_value) / 2
    midpoint_square = midpoint * midpoint
    if value < midpoint_square:
        return low
    if value > midpoint_square:
        return upper
    return low if low & 1 == 0 else upper


def _b64_binary_op(left_bits: int, right_bits: int, operator: str) -> int:
    left = bits_to_fraction(left_bits)
    right = bits_to_fraction(right_bits)
    if operator == "add":
        exact = left + right
    elif operator == "subtract":
        exact = left - right
    elif operator == "multiply":
        exact = left * right
    elif operator == "divide":
        if right == 0:
            raise ZeroDivisionError
        exact = left / right
    else:
        raise ValueError(operator)
    return rational_to_binary64_bits(exact)


def path_a_accumulate(terms: Sequence[Fraction]) -> tuple[int, list[str]]:
    accumulator = 0
    trace: list[str] = []
    for term in terms:
        term_bits = rational_to_binary64_bits(term)
        accumulator = _b64_binary_op(accumulator, term_bits, "add")
        trace.append(bit_hex(accumulator))
    return accumulator, trace


def path_b_accumulate(terms: Sequence[Fraction]) -> int:
    return rational_to_binary64_bits(sum((Fraction(term) for term in terms), Fraction(0)))


def path_a_transform(value: Fraction, center: Fraction, scale: Fraction) -> int:
    value_bits = rational_to_binary64_bits(value)
    center_bits = rational_to_binary64_bits(center)
    scale_bits = rational_to_binary64_bits(scale)
    difference = _b64_binary_op(value_bits, center_bits, "subtract")
    return _b64_binary_op(difference, scale_bits, "divide")


def path_b_transform(value: Fraction, center: Fraction, scale: Fraction) -> int:
    if scale == 0:
        raise ZeroDivisionError
    return rational_to_binary64_bits((value - center) / scale)


def path_a_norm(components: Sequence[Fraction]) -> tuple[int, int, list[str]]:
    accumulator = 0
    trace: list[str] = []
    for component in components:
        component_bits = rational_to_binary64_bits(component)
        squared = _b64_binary_op(component_bits, component_bits, "multiply")
        accumulator = _b64_binary_op(accumulator, squared, "add")
        trace.append(bit_hex(accumulator))
    return exact_sqrt_to_binary64_bits(bits_to_fraction(accumulator)), accumulator, trace


def path_b_norm(components: Sequence[Fraction]) -> tuple[int, Fraction]:
    # Matrix components are binary64; B sums their exact dyadic squares.
    dyadics = [bits_to_fraction(rational_to_binary64_bits(item)) for item in components]
    squared_sum = sum((item * item for item in dyadics), Fraction(0))
    return exact_sqrt_to_binary64_bits(squared_sum), squared_sum


def evaluate_column_accumulation(
    terms: Sequence[tuple[str, Fraction]], path: str
) -> dict[str, object]:
    """Total V2 column fold with independent leaf admission and resource caps."""
    metrics: dict[str, object] = {
        "max_intermediate_denominator_bits": 0,
        "max_intermediate_numerator_bits": 0,
        "term_count": len(terms),
    }
    try:
        if len(terms) > STUDY_MAX_TERMS:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_TERM_LIMIT", "COLUMN_TERM_COUNT", "column"
            )
        admitted: list[tuple[str, Fraction, int]] = []
        previous: Optional[bytes] = None
        for index, term in enumerate(terms):
            if not isinstance(term, tuple) or len(term) != 2 or not isinstance(term[0], str):
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_DOMAIN", "COLUMN_TERM_SHAPE", f"term[{index}]"
                )
            identity, value = term
            try:
                identity_bytes = identity.encode("utf-8")
            except UnicodeEncodeError:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_DOMAIN", "COLUMN_IDENTITY_UTF8", f"term[{index}]"
                )
            if previous is not None and identity_bytes == previous:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_DUPLICATE_TERM",
                    "COLUMN_IDENTITY",
                    f"term[{index}]",
                )
            if previous is not None and identity_bytes < previous:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_ORDER",
                    "COLUMN_IDENTITY",
                    f"term[{index}]",
                )
            previous = identity_bytes
            admitted_value, admitted_bits, shape = admit_rational_leaf(
                value, f"term[{index}]/{identity}"
            )
            metrics["max_leaf_denominator_digits"] = max(
                int(metrics.get("max_leaf_denominator_digits", 0)),
                shape["denominator_digits"],
            )
            metrics["max_leaf_numerator_digits"] = max(
                int(metrics.get("max_leaf_numerator_digits", 0)),
                shape["numerator_digits"],
            )
            admitted.append((identity, admitted_value, admitted_bits))

        if path == "A_FIXED_BINARY64":
            accumulator_bits = 0
            trace: list[str] = []
            for index, (_, _, leaf_bits) in enumerate(admitted):
                accumulator_bits = _b64_binary_op(accumulator_bits, leaf_bits, "add")
                if _is_nonfinite_bits(accumulator_bits):
                    raise StudyFailure(
                        "NOT_QUALIFIED_NUMERIC_RANGE", "COLUMN_ADD", f"term[{index}]"
                    )
                accumulator_bits = canonicalize_zero_bits(accumulator_bits)
                trace.append(bit_hex(accumulator_bits))
            metrics["fixed_binary64_operations"] = len(admitted)
            return _success_outcome(
                accumulator_bits,
                metrics,
                operation_order="strict raw UTF-8 identity ascending; round after every add",
                trace_bits_be_hex=(
                    trace if len(trace) <= 8 else trace[:2] + ["..."] + trace[-2:]
                ),
            )
        if path != "B_EXACT_LAST_ROUND":
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "PATH", path)

        accumulator = Fraction(0)
        for index, (_, value, _) in enumerate(admitted):
            accumulator += value
            shape = _check_intermediate(accumulator, "COLUMN_EXACT_ADD", f"term[{index}]")
            metrics["max_intermediate_denominator_bits"] = max(
                int(metrics["max_intermediate_denominator_bits"]), shape["denominator_bits"]
            )
            metrics["max_intermediate_numerator_bits"] = max(
                int(metrics["max_intermediate_numerator_bits"]), shape["numerator_bits"]
            )
        output_bits = _checked_output_bits(accumulator, "COLUMN_OUTPUT_ROUND", "column")
        metrics["exact_additions"] = len(admitted)
        return _success_outcome(
            output_bits,
            metrics,
            exact_sum=_fraction_record(accumulator),
            operation_order="all leaves admitted first; exact identity-order additions; one output round",
        )
    except StudyFailure as failure:
        return _failure_outcome(failure, metrics)


def evaluate_accumulation(terms: Sequence[Fraction], path: str) -> dict[str, object]:
    width = max(4, len(str(max(0, len(terms) - 1))))
    identified = [(f"term-{index:0{width}d}", value) for index, value in enumerate(terms)]
    return evaluate_column_accumulation(identified, path)


def evaluate_sqrt(value: Fraction, provenance: str = "sqrt") -> dict[str, object]:
    metrics: dict[str, object] = {}
    try:
        admitted, _, shape = admit_rational_leaf(value, provenance)
        metrics["operand_shape"] = shape
        if admitted < 0:
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "SQRT_DOMAIN", provenance)
        _check_intermediate(admitted, "SQRT_OPERAND", provenance)
        bits = exact_sqrt_to_binary64_bits(admitted)
        if _is_nonfinite_bits(bits):
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_RANGE", "SQRT_OUTPUT", provenance)
        return _success_outcome(bits, metrics)
    except StudyFailure as failure:
        return _failure_outcome(failure, metrics)


def evaluate_norm(components: Sequence[Fraction], path: str) -> dict[str, object]:
    metrics: dict[str, object] = {
        "component_count": len(components),
        "max_intermediate_denominator_bits": 0,
        "max_intermediate_numerator_bits": 0,
    }
    try:
        if len(components) > STUDY_MAX_TERMS:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_TERM_LIMIT", "NORM_TERM_COUNT", "family"
            )
        admitted: list[tuple[Fraction, int]] = []
        # Admission is a complete first pass.  No exact square/cancellation can
        # make an individually illegal leaf acceptable.
        for index, component in enumerate(components):
            value, bits, shape = admit_rational_leaf(component, f"component[{index}]")
            metrics["max_leaf_denominator_digits"] = max(
                int(metrics.get("max_leaf_denominator_digits", 0)),
                shape["denominator_digits"],
            )
            metrics["max_leaf_numerator_digits"] = max(
                int(metrics.get("max_leaf_numerator_digits", 0)),
                shape["numerator_digits"],
            )
            admitted.append((value, bits))

        if path == "A_FIXED_BINARY64":
            squared_sum_bits = 0
            trace: list[str] = []
            for index, (_, component_bits) in enumerate(admitted):
                squared_bits = _b64_binary_op(component_bits, component_bits, "multiply")
                if _is_nonfinite_bits(squared_bits):
                    raise StudyFailure(
                        "NOT_QUALIFIED_NUMERIC_RANGE", "NORM_SQUARE", f"component[{index}]"
                    )
                squared_sum_bits = _b64_binary_op(squared_sum_bits, squared_bits, "add")
                if _is_nonfinite_bits(squared_sum_bits):
                    raise StudyFailure(
                        "NOT_QUALIFIED_NUMERIC_RANGE", "NORM_ADD", f"component[{index}]"
                    )
                squared_sum_bits = canonicalize_zero_bits(squared_sum_bits)
                trace.append(bit_hex(squared_sum_bits))
            norm_bits = exact_sqrt_to_binary64_bits(bits_to_fraction(squared_sum_bits))
            if _is_nonfinite_bits(norm_bits):
                raise StudyFailure("NOT_QUALIFIED_NUMERIC_RANGE", "NORM_SQRT", "family")
            metrics["fixed_binary64_operations"] = 2 * len(admitted) + 1
            return _success_outcome(
                norm_bits,
                metrics,
                squared_sum_bits_be_hex=bit_hex(squared_sum_bits),
                squared_sum_exact=_fraction_record(bits_to_fraction(squared_sum_bits)),
                squared_sum_trace_bits_be_hex=trace,
            )
        if path != "B_EXACT_LAST_ROUND":
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "PATH", path)

        squared_sum = Fraction(0)
        for index, (_, component_bits) in enumerate(admitted):
            # Norm inputs are matrix binary64 components, hence exact dyadics.
            dyadic = bits_to_fraction(component_bits)
            squared = dyadic * dyadic
            shape = _check_intermediate(squared, "NORM_EXACT_SQUARE", f"component[{index}]")
            metrics["max_intermediate_denominator_bits"] = max(
                int(metrics["max_intermediate_denominator_bits"]), shape["denominator_bits"]
            )
            metrics["max_intermediate_numerator_bits"] = max(
                int(metrics["max_intermediate_numerator_bits"]), shape["numerator_bits"]
            )
            squared_sum += squared
            shape = _check_intermediate(squared_sum, "NORM_EXACT_ADD", f"component[{index}]")
            metrics["max_intermediate_denominator_bits"] = max(
                int(metrics["max_intermediate_denominator_bits"]), shape["denominator_bits"]
            )
            metrics["max_intermediate_numerator_bits"] = max(
                int(metrics["max_intermediate_numerator_bits"]), shape["numerator_bits"]
            )
        norm_bits = exact_sqrt_to_binary64_bits(squared_sum)
        if _is_nonfinite_bits(norm_bits):
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_RANGE", "NORM_SQRT", "family")
        metrics["exact_squares"] = len(admitted)
        metrics["exact_additions"] = len(admitted)
        return _success_outcome(
            norm_bits,
            metrics,
            squared_sum_exact=_fraction_record(squared_sum),
        )
    except StudyFailure as failure:
        return _failure_outcome(failure, metrics)


def evaluate_standardize(
    value: Fraction,
    center: Fraction,
    scale: Fraction,
    path: str,
    clip_abs: Fraction = CLIP_ABS,
) -> dict[str, object]:
    """Total numeric lifecycle: admit -> subtract -> divide -> clip -> output."""
    metrics: dict[str, object] = {}
    try:
        admitted_value, value_bits, _ = admit_rational_leaf(value, "value")
        admitted_center, center_bits, _ = admit_rational_leaf(center, "center")
        admitted_scale, scale_bits, _ = admit_rational_leaf(scale, "scale")
        admitted_clip, clip_bits, _ = admit_rational_leaf(clip_abs, "clip_abs")
        if admitted_clip <= 0:
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "CLIP_DOMAIN", "clip_abs")
        if admitted_scale == 0:
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_SCALE_ZERO", "SCALE", "scale")
        if admitted_scale < 0:
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "SCALE", "scale")
        if scale_bits == 0:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW", "SCALE_ROUND", "scale"
            )

        if path == "A_FIXED_BINARY64":
            difference_bits = _b64_binary_op(value_bits, center_bits, "subtract")
            if _is_nonfinite_bits(difference_bits):
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_RANGE", "STANDARDIZE_SUBTRACT", "value-center"
                )
            quotient_bits = _b64_binary_op(difference_bits, scale_bits, "divide")
            if _is_nonfinite_bits(quotient_bits):
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_RANGE", "STANDARDIZE_DIVIDE", "difference/scale"
                )
            quotient = bits_to_fraction(quotient_bits)
            clip_value = bits_to_fraction(clip_bits)
            clipped = max(-clip_value, min(clip_value, quotient))
            output_bits = _checked_output_bits(clipped, "STANDARDIZE_OUTPUT", "value")
            metrics["fixed_binary64_operations"] = 2
            return _success_outcome(
                output_bits,
                metrics,
                lifecycle="admit leaves; round leaves; subtract+round; divide+round; clip[-8,8]; canonicalize +0",
                unclipped_bits_be_hex=bit_hex(canonicalize_zero_bits(quotient_bits)),
            )
        if path != "B_EXACT_LAST_ROUND":
            raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "PATH", path)

        difference = admitted_value - admitted_center
        shape = _check_intermediate(difference, "STANDARDIZE_EXACT_SUBTRACT", "value-center")
        metrics["max_intermediate_denominator_bits"] = shape["denominator_bits"]
        metrics["max_intermediate_numerator_bits"] = shape["numerator_bits"]
        quotient = difference / admitted_scale
        shape = _check_intermediate(quotient, "STANDARDIZE_EXACT_DIVIDE", "difference/scale")
        metrics["max_intermediate_denominator_bits"] = max(
            int(metrics["max_intermediate_denominator_bits"]), shape["denominator_bits"]
        )
        metrics["max_intermediate_numerator_bits"] = max(
            int(metrics["max_intermediate_numerator_bits"]), shape["numerator_bits"]
        )
        clipped = max(-admitted_clip, min(admitted_clip, quotient))
        output_bits = _checked_output_bits(clipped, "STANDARDIZE_OUTPUT", "value")
        metrics["exact_operations"] = 2
        return _success_outcome(
            output_bits,
            metrics,
            lifecycle="admit leaves; exact subtract; exact divide; exact clip[-8,8]; one output round; canonicalize +0",
            unclipped_exact=_fraction_record(quotient),
        )
    except StudyFailure as failure:
        return _failure_outcome(failure, metrics)


def evaluate_family_normalization(
    components: object, path: str
) -> dict[str, object]:
    """Normalize one family from an exact list of post-parser Fraction leaves."""
    metrics: dict[str, object] = {}
    try:
        if type(components) is not list:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_DOMAIN",
                "FAMILY_INPUT_CONTAINER_TYPE",
                "components",
            )
        metrics["component_count"] = len(components)
        admitted_values: list[Fraction] = []
        admitted_bits: list[int] = []
        for index, value in enumerate(components):
            if type(value) is not Fraction:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_DOMAIN",
                    "FAMILY_INPUT_LEAF_TYPE",
                    f"component[{index}]",
                )
            admitted, bits, _ = admit_rational_leaf(value, f"component[{index}]")
            if abs(admitted) > CLIP_ABS:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_RANGE",
                    "FAMILY_INPUT_CLIP_BOUND",
                    f"component[{index}]",
                )
            if bits_to_fraction(bits) != admitted:
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_DOMAIN",
                    "FAMILY_INPUT_BINARY64_EXACT",
                    f"component[{index}]",
                )
            admitted_values.append(admitted)
            admitted_bits.append(bits)

        norm = evaluate_norm(admitted_values, path)
        if norm["status"] != "OK":
            return norm
        norm_bits = int(str(norm["bits_be_hex"]), 16)
        metrics["norm_metrics"] = norm["metrics"]
        if norm_bits == 0:
            return {
                "component_bits_be_hex": ["0000000000000000"] * len(components),
                "metrics": metrics,
                "norm_bits_be_hex": "0000000000000000",
                "status": "OK",
                "zero_norm_rule": "do not divide; emit canonical +0 for every component",
            }
        normalized: list[str] = []
        norm_exact = bits_to_fraction(norm_bits)
        for index, component_bits in enumerate(admitted_bits):
            if path == "A_FIXED_BINARY64":
                output_bits = _b64_binary_op(component_bits, norm_bits, "divide")
            elif path == "B_EXACT_LAST_ROUND":
                quotient = bits_to_fraction(component_bits) / norm_exact
                _check_intermediate(
                    quotient, "FAMILY_NORMALIZATION_EXACT_DIVIDE", f"component[{index}]"
                )
                output_bits = _checked_output_bits(
                    quotient, "FAMILY_NORMALIZATION_OUTPUT", f"component[{index}]"
                )
            else:
                raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "PATH", path)
            if _is_nonfinite_bits(output_bits):
                raise StudyFailure(
                    "NOT_QUALIFIED_NUMERIC_RANGE",
                    "FAMILY_NORMALIZATION_OUTPUT",
                    f"component[{index}]",
                )
            normalized.append(bit_hex(canonicalize_zero_bits(output_bits)))
        return {
            "component_bits_be_hex": normalized,
                "lifecycle": "require exact list container and exact Fraction leaves; admit exact finite binary64 components; enforce abs<=8; family norm; divide each by rounded norm; output round; canonicalize +0",
            "metrics": metrics,
            "norm_bits_be_hex": bit_hex(norm_bits),
            "status": "OK",
        }
    except StudyFailure as failure:
        return _failure_outcome(failure, metrics)


def exact_quantile(values: Sequence[Fraction], probability: Fraction, method: str) -> Fraction:
    ordered = sorted(Fraction(value) for value in values)
    count = len(ordered)
    if not count:
        raise ValueError("quantile of empty input")
    if not 0 <= probability <= 1:
        raise ValueError("probability outside [0,1]")
    if count == 1:
        return ordered[0]
    if method == "type7":
        location = (count - 1) * probability
        lower = location.numerator // location.denominator
        fraction = location - lower
        if lower == count - 1:
            return ordered[-1]
        return ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])
    if method == "averaged_inverted_cdf":
        scaled = count * probability
        if scaled <= 0:
            return ordered[0]
        if scaled >= count:
            return ordered[-1]
        lower = scaled.numerator // scaled.denominator
        if scaled.denominator == 1:
            return (ordered[lower - 1] + ordered[lower]) / 2
        ceiling = lower + 1
        return ordered[ceiling - 1]
    raise ValueError(method)


def robust_parameters(values: Sequence[Fraction], method: str) -> tuple[Fraction, Fraction, Fraction]:
    if not values:
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "QUANTILE_EMPTY", "calibration")
    if len(values) > STUDY_MAX_QUANTILE_SAMPLES:
        raise StudyFailure(
            "NOT_QUALIFIED_NUMERIC_TERM_LIMIT", "QUANTILE_SAMPLE_COUNT", "calibration"
        )
    admitted = [
        admit_rational_leaf(value, f"calibration[{index}]")[0]
        for index, value in enumerate(values)
    ]
    try:
        center = exact_quantile(admitted, Fraction(1, 2), method)
        q1 = exact_quantile(admitted, Fraction(1, 4), method)
        q3 = exact_quantile(admitted, Fraction(3, 4), method)
    except ValueError:
        raise StudyFailure("NOT_QUALIFIED_NUMERIC_DOMAIN", "QUANTILE_METHOD", method)
    iqr = q3 - q1
    # Preserve the existing candidate's explicit 1.349 divisor.  It is a
    # decimal rational, not a binary float.  Only zero IQR falls back to one.
    scale = Fraction(1) if iqr == 0 else iqr / Fraction(1349, 1000)
    for name, result in (("center", center), ("q1", q1), ("q3", q3), ("iqr", iqr), ("scale", scale)):
        _check_intermediate(result, "QUANTILE_DERIVED", name)
    return center, iqr, scale


def decimal_log1p_bits(count: int, precision: int) -> int:
    if not 0 <= count <= 255:
        raise ValueError("count outside frozen table")
    with localcontext() as context:
        context.prec = precision
        value = (Decimal(1) + Decimal(count)).ln()
    return rational_to_binary64_bits(Fraction(value))


def build_initial_table() -> dict[str, object]:
    entries = []
    for count in range(256):
        # One-time local source.  Runtime consumers never call libm.
        bits = float_to_bits(math.log1p(count))
        entries.append({"bits_be_hex": bit_hex(bits), "count": str(count)})
    return {
        "candidate_status": EXPECTED_TABLE_METADATA["candidate_status"],
        "construction_source": EXPECTED_TABLE_METADATA["construction_source"],
        "entries": entries,
        "runtime_rule": EXPECTED_TABLE_METADATA["runtime_rule"],
        "schema": EXPECTED_TABLE_METADATA["schema"],
        "serialization": EXPECTED_TABLE_METADATA["serialization"],
        "version": EXPECTED_TABLE_METADATA["version"],
    }


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_DUPLICATE_KEY", key
            )
        output[key] = value
    return output


def _reject_json_constant(token: str) -> object:
    raise StudyFailure(
        "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_JSON_CONSTANT", token
    )


def _reject_json_number(token: str) -> object:
    # The frozen table grammar contains strings, arrays and objects only.  Any
    # JSON number, including exponent overflow such as 1e9999, is out of domain.
    raise StudyFailure(
        "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_JSON_NUMBER", token[:80]
    )


def load_table_bytes(
    raw: bytes, expected_sha256: str
) -> tuple[dict[str, object], bytes]:
    if type(raw) is not bytes:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_RAW_TYPE", "count_log1p_table"
        )
    if len(raw) > STUDY_MAX_TABLE_BYTES or len(raw) != EXPECTED_TABLE_BYTES:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_BYTE_LENGTH", "count_log1p_table"
        )
    if type(expected_sha256) is not str or not re.fullmatch(
        r"[0-9a-f]{64}", expected_sha256
    ):
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_BINDING", "TABLE_EXPECTED_SHA_GRAMMAR", "controller_pin"
        )
    if sha256_bytes(raw) != expected_sha256:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_BINDING", "TABLE_SHA256", "controller_pin"
        )
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_json_constant,
            parse_float=_reject_json_number,
            parse_int=_reject_json_number,
        )
    except StudyFailure:
        raise
    except (
        UnicodeDecodeError,
        UnicodeEncodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
        RecursionError,
        OverflowError,
    ):
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_JSON", "count_log1p_table"
        )
    try:
        canonical = canonical_bytes(value)
    except StudyFailure:
        raise
    except (
        UnicodeEncodeError,
        ValueError,
        TypeError,
        RecursionError,
        OverflowError,
    ):
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_CANONICAL_ENCODER", "count_log1p_table"
        )
    if not isinstance(value, dict) or raw != canonical:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_CANONICAL_BYTES", "count_log1p_table"
        )
    expected_top_keys = {
        "candidate_status",
        "construction_source",
        "entries",
        "runtime_rule",
        "schema",
        "serialization",
        "version",
    }
    if set(value) != expected_top_keys:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_TOP_LEVEL_KEYS", "count_log1p_table"
        )
    metadata = {key: value[key] for key in EXPECTED_TABLE_METADATA}
    if metadata != EXPECTED_TABLE_METADATA:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_METADATA", "count_log1p_table"
        )
    entries = value.get("entries")
    if not isinstance(entries, list) or len(entries) != 256:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_ENTRY_COUNT", "entries"
        )
    seen_counts: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"bits_be_hex", "count"}:
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_ENTRY_KEYS", f"entries[{index}]"
            )
        count = entry["count"]
        bits_hex = entry["bits_be_hex"]
        if not isinstance(count, str) or not re.fullmatch(r"0|[1-9][0-9]*", count):
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_COUNT_GRAMMAR", f"entries[{index}]"
            )
        if count in seen_counts:
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_DUPLICATE_COUNT", f"entries[{index}]"
            )
        seen_counts.add(count)
        if count != str(index):
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_COUNT_INDEX", f"entries[{index}]"
            )
        if not isinstance(bits_hex, str) or not TABLE_HEX_RE.fullmatch(bits_hex):
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_BITS_GRAMMAR", f"entries[{index}]"
            )
        bits = int(bits_hex, 16)
        if _is_nonfinite_bits(bits) or bits & SIGN_BIT:
            raise StudyFailure(
                "NOT_QUALIFIED_TABLE_STRUCTURE", "TABLE_BITS_RANGE", f"entries[{index}]"
            )
    return value, raw


def load_table(expected_sha256: str) -> tuple[dict[str, object], bytes]:
    try:
        raw = TABLE_PATH.read_bytes()
    except OSError:
        raise StudyFailure(
            "NOT_QUALIFIED_TABLE_BINDING", "TABLE_READ", "count_log1p_table"
        )
    return load_table_bytes(raw, expected_sha256)


def lookup_count_log1p(count: int, expected_table_sha256: str) -> dict[str, object]:
    try:
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_DOMAIN", "COUNT_CLIP", "exact_count"
            )
        if count > (1 << 64) - 1:
            raise StudyFailure(
                "NOT_QUALIFIED_NUMERIC_BOUNDS", "COUNT_U64", "exact_count"
            )
        table, _ = load_table(expected_table_sha256)
        saturated = min(count, 255)
        bits = int(table["entries"][saturated]["bits_be_hex"], 16)
        return _success_outcome(
            bits,
            {"exact_count": str(count), "saturated_count": str(saturated)},
            lifecycle="admit exact u64 count; saturate min(count,255); frozen lookup; canonicalize +0",
        )
    except StudyFailure as failure:
        return _failure_outcome(failure)


def _fraction_record(value: Fraction) -> dict[str, str]:
    return {"denominator": str(value.denominator), "numerator": str(value.numerator)}


def _conversion_cases() -> list[dict[str, object]]:
    maximum = bits_to_fraction(MAX_FINITE_BITS)
    cases: list[tuple[str, Fraction, str]] = [
        ("midpoint_tie_to_even_lower", Fraction(1) + Fraction(1, 1 << 53), "FINITE"),
        ("midpoint_tie_to_even_upper", Fraction(1) + Fraction(3, 1 << 53), "FINITE"),
        ("maximum_finite_exact", maximum, "FINITE"),
        ("below_overflow_midpoint", maximum + Fraction(1 << 969), "FINITE"),
        ("overflow_midpoint", maximum + Fraction(1 << 970), "NOT_QUALIFIED_NUMERIC_RANGE"),
        ("minimum_normal", Fraction(1, 1 << 1022), "FINITE"),
        ("largest_subnormal", Fraction((1 << 52) - 1, 1 << 1074), "FINITE"),
        ("minimum_subnormal", Fraction(1, 1 << 1074), "FINITE"),
        ("underflow_midpoint_tie_to_even_zero", Fraction(1, 1 << 1075), "FINITE"),
        ("above_underflow_midpoint", Fraction(3, 1 << 1076), "FINITE"),
        ("negative_underflow_to_canonical_positive_zero", Fraction(-1, 1 << 1075), "FINITE"),
    ]
    output = []
    for case_id, rational, admission in cases:
        bits = rational_to_binary64_bits(rational)
        output.append(
            {
                "admission": admission,
                "case_id": case_id,
                "conversion_bits_be_hex": bit_hex(bits),
                "emitted_bits_be_hex": None if bits & 0x7FF0000000000000 == POS_INF_BITS else bit_hex(bits),
                "input": _fraction_record(rational),
            }
        )
    for lexeme in ["0", "-0", "-0.0e999"]:
        rational = decimal_lexeme_to_fraction(lexeme)
        output.append(
            {
                "admission": "FINITE",
                "case_id": f"decimal_lexeme_{lexeme}",
                "conversion_bits_be_hex": bit_hex(rational_to_binary64_bits(rational)),
                "emitted_bits_be_hex": "0000000000000000",
                "input_lexeme": lexeme,
                "normalized_rational": _fraction_record(rational),
            }
        )
    return output


def _accumulation_cases() -> list[dict[str, object]]:
    raw_cases = [
        (
            "signed_collision_large_small_cancel",
            [Fraction(1 << 53), Fraction(1), Fraction(-(1 << 53))],
            "same exact multiset; fixed identity order places +1 between large cancellation terms",
        ),
        (
            "signed_collision_cancel_then_small",
            [Fraction(1 << 53), Fraction(-(1 << 53)), Fraction(1)],
            "same exact multiset in another frozen identity order",
        ),
        (
            "large_then_1024_small_terms",
            [Fraction(1)] + [Fraction(1, 1 << 60)] * 1024,
            "a large first identity followed by many individually sub-half-ULP terms",
        ),
        (
            "exact_pair_cancellation",
            [Fraction(7, 4), Fraction(-7, 4)],
            "control case; both paths produce canonical +0",
        ),
    ]
    output = []
    for case_id, terms, note in raw_cases:
        path_a = evaluate_accumulation(terms, "A_FIXED_BINARY64")
        path_b = evaluate_accumulation(terms, "B_EXACT_LAST_ROUND")
        if path_a["status"] != "OK" or path_b["status"] != "OK":
            raise AssertionError(f"registered positive accumulation case failed: {case_id}")
        output.append(
            {
                "case_id": case_id,
                "diverges": path_a["bits_be_hex"] != path_b["bits_be_hex"],
                "exact_sum": _fraction_record(sum(terms, Fraction(0))),
                "formal_reachability": "UNKNOWN",
                "note": note,
                "path_a": path_a,
                "path_a_bits_be_hex": path_a["bits_be_hex"],
                "path_b": path_b,
                "path_b_bits_be_hex": path_b["bits_be_hex"],
                "task_impact": "UNKNOWN",
                "term_count": len(terms),
            }
        )
    return output


def _norm_cases() -> list[dict[str, object]]:
    raw_cases = [
        ("zero_family", [Fraction(0), Fraction(0)]),
        ("three_four_five", [Fraction(3), Fraction(4)]),
        ("large_plus_five_quarter_ulp_squares", [Fraction(1)] + [Fraction(1, 1 << 27)] * 5),
    ]
    output = []
    for case_id, components in raw_cases:
        path_a = evaluate_norm(components, "A_FIXED_BINARY64")
        path_b = evaluate_norm(components, "B_EXACT_LAST_ROUND")
        if path_a["status"] != "OK" or path_b["status"] != "OK":
            raise AssertionError(f"registered positive norm case failed: {case_id}")
        output.append(
            {
                "case_id": case_id,
                "component_count": len(components),
                "diverges": (
                    path_a["bits_be_hex"] != path_b["bits_be_hex"]
                    or path_a["squared_sum_exact"] != path_b["squared_sum_exact"]
                ),
                "formal_reachability": "UNKNOWN",
                "path_a": path_a,
                "path_a_norm_bits_be_hex": path_a["bits_be_hex"],
                "path_b": path_b,
                "path_b_norm_bits_be_hex": path_b["bits_be_hex"],
                "task_impact": "UNKNOWN",
            }
        )
    return output


def _quantile_cases() -> list[dict[str, object]]:
    comparison_values = [Fraction(0), Fraction(10), Fraction(20), Fraction(30)]
    target = Fraction(30)
    methods = []
    for method in ["type7", "averaged_inverted_cdf"]:
        center, iqr, scale = robust_parameters(comparison_values, method)
        path_a = evaluate_standardize(target, center, scale, "A_FIXED_BINARY64")
        path_b = evaluate_standardize(target, center, scale, "B_EXACT_LAST_ROUND")
        if path_a["status"] != "OK" or path_b["status"] != "OK":
            raise AssertionError(f"registered quantile case failed: {method}")
        methods.append(
            {
                "center": _fraction_record(center),
                "iqr": _fraction_record(iqr),
                "method": method,
                "path_a": path_a,
                "path_a_transformed_bits_be_hex": path_a["bits_be_hex"],
                "path_b": path_b,
                "path_b_transformed_bits_be_hex": path_b["bits_be_hex"],
                "paths_diverge": path_a["bits_be_hex"] != path_b["bits_be_hex"],
                "scale_iqr_div_1_349": _fraction_record(scale),
            }
        )
    raw_a = evaluate_standardize(target, Fraction(0), Fraction(1), "A_FIXED_BINARY64")
    raw_b = evaluate_standardize(target, Fraction(0), Fraction(1), "B_EXACT_LAST_ROUND")
    methods.append(
        {
            "method": "no_centering_no_scaling_then_common_clip_baseline",
            "path_a": raw_a,
            "path_a_transformed_bits_be_hex": raw_a["bits_be_hex"],
            "path_b": raw_b,
            "path_b_transformed_bits_be_hex": raw_b["bits_be_hex"],
            "paths_diverge": raw_a["bits_be_hex"] != raw_b["bits_be_hex"],
        }
    )

    zero_values = [Fraction(7)] * 4
    zero_center, zero_iqr, zero_scale = robust_parameters(zero_values, "type7")
    zero_a = evaluate_standardize(
        Fraction(8), zero_center, zero_scale, "A_FIXED_BINARY64"
    )
    zero_b = evaluate_standardize(
        Fraction(8), zero_center, zero_scale, "B_EXACT_LAST_ROUND"
    )

    large_center = Fraction(1 << 53)
    large_value = large_center + 1
    large_a = evaluate_standardize(
        large_value, large_center, Fraction(1), "A_FIXED_BINARY64"
    )
    large_b = evaluate_standardize(
        large_value, large_center, Fraction(1), "B_EXACT_LAST_ROUND"
    )
    return [
        {
            "case_id": "estimator_difference_0_10_20_30_target_30",
            "methods": methods,
            "values": [str(value) for value in comparison_values],
        },
        {
            "case_id": "zero_iqr_fallback_preserves_holdout_shift",
            "center": _fraction_record(zero_center),
            "formal_reachability": "UNKNOWN",
            "iqr": _fraction_record(zero_iqr),
            "path_a": zero_a,
            "path_a_bits_be_hex": zero_a["bits_be_hex"],
            "path_b": zero_b,
            "path_b_bits_be_hex": zero_b["bits_be_hex"],
            "paths_diverge": zero_a["bits_be_hex"] != zero_b["bits_be_hex"],
            "scale_fallback": _fraction_record(zero_scale),
            "task_impact": "UNKNOWN",
            "target": "8",
        },
        {
            "case_id": "large_offset_unit_shift",
            "center": str(1 << 53),
            "formal_reachability": "UNKNOWN",
            "path_a": large_a,
            "path_a_bits_be_hex": large_a["bits_be_hex"],
            "path_b": large_b,
            "path_b_bits_be_hex": large_b["bits_be_hex"],
            "paths_diverge": large_a["bits_be_hex"] != large_b["bits_be_hex"],
            "scale": "1",
            "task_impact": "UNKNOWN",
            "target": str((1 << 53) + 1),
        },
    ]


def _failure_regressions() -> list[dict[str, object]]:
    maximum = bits_to_fraction(MAX_FINITE_BITS)
    cases = [
        (
            "a_sum_overflow_is_stable_failure",
            evaluate_accumulation([Fraction(1 << 1023), Fraction(1 << 1023)], "A_FIXED_BINARY64"),
            "NOT_QUALIFIED_NUMERIC_RANGE",
        ),
        (
            "a_norm_square_overflow_is_stable_failure",
            evaluate_norm([maximum], "A_FIXED_BINARY64"),
            "NOT_QUALIFIED_NUMERIC_RANGE",
        ),
        (
            "b_norm_output_overflow_is_stable_failure",
            evaluate_norm([maximum, maximum], "B_EXACT_LAST_ROUND"),
            "NOT_QUALIFIED_NUMERIC_RANGE",
        ),
        (
            "a_nonzero_scale_underflow_is_stable_failure",
            evaluate_standardize(
                Fraction(1), Fraction(0), Fraction(1, 1 << 1075), "A_FIXED_BINARY64"
            ),
            "NOT_QUALIFIED_NUMERIC_SCALE_UNDERFLOW",
        ),
        (
            "b_exact_zero_scale_is_stable_failure",
            evaluate_standardize(Fraction(1), Fraction(0), Fraction(0), "B_EXACT_LAST_ROUND"),
            "NOT_QUALIFIED_NUMERIC_SCALE_ZERO",
        ),
        (
            "b_illegal_leaf_cannot_cancel_before_admission",
            evaluate_accumulation(
                [Fraction(1 << 1024), Fraction(-(1 << 1024)), Fraction(1)],
                "B_EXACT_LAST_ROUND",
            ),
            "NOT_QUALIFIED_NUMERIC_RANGE",
        ),
        (
            "negative_sqrt_is_stable_failure",
            evaluate_sqrt(Fraction(-1), "negative_fixture"),
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
        ),
        (
            "b_term_cap_is_stable_failure",
            evaluate_accumulation(
                [Fraction(0)] * (STUDY_MAX_TERMS + 1), "B_EXACT_LAST_ROUND"
            ),
            "NOT_QUALIFIED_NUMERIC_TERM_LIMIT",
        ),
        (
            "external_pin_none_is_stable_failure",
            lookup_count_log1p(1, None),
            "NOT_QUALIFIED_TABLE_BINDING",
        ),
        (
            "family_rejects_unclipped_component",
            evaluate_family_normalization(
                [Fraction(100), Fraction(0)], "B_EXACT_LAST_ROUND"
            ),
            "NOT_QUALIFIED_NUMERIC_RANGE",
        ),
        (
            "family_rejects_non_binary64_exact_component",
            evaluate_family_normalization([Fraction(1, 3)], "A_FIXED_BINARY64"),
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
        ),
        (
            "family_rejects_nonlist_container",
            evaluate_family_normalization((Fraction(1),), "A_FIXED_BINARY64"),
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
        ),
        (
            "family_rejects_nonfraction_leaf",
            evaluate_family_normalization(["8"], "B_EXACT_LAST_ROUND"),
            "NOT_QUALIFIED_NUMERIC_DOMAIN",
        ),
    ]
    output = []
    for case_id, outcome, expected in cases:
        if outcome.get("failure_code") != expected:
            raise AssertionError(f"failure regression mismatch: {case_id}: {outcome}")
        output.append(
            {
                "case_id": case_id,
                "expected_failure_code": expected,
                "outcome": outcome,
            }
        )
    return output


def build_results(expected_table_sha256: str) -> dict[str, object]:
    table, table_raw = load_table(expected_table_sha256)
    table_entries = table["entries"]
    disagreements = []
    unstable = []
    for count, entry in enumerate(table_entries):
        frozen = int(entry["bits_be_hex"], 16)
        references = [decimal_log1p_bits(count, precision) for precision in (80, 160, 240)]
        if len(set(references)) != 1:
            unstable.append(
                {"bits": [bit_hex(item) for item in references], "count": str(count)}
            )
        if frozen != references[-1]:
            disagreements.append(
                {
                    "count": str(count),
                    "decimal_240_bits_be_hex": bit_hex(references[-1]),
                    "frozen_bits_be_hex": bit_hex(frozen),
                }
            )

    accumulation = _accumulation_cases()
    norms = _norm_cases()
    quantiles = _quantile_cases()
    failure_regressions = _failure_regressions()
    true_divergences = [
        item["case_id"]
        for item in accumulation + norms + quantiles
        if item.get("diverges") or item.get("paths_diverge")
    ]
    for quantile_case in quantiles:
        for method in quantile_case.get("methods", []):
            if method.get("paths_diverge"):
                true_divergences.append(
                    f"{quantile_case['case_id']}::{method['method']}"
                )
    source_raw = Path(__file__).read_bytes()
    redteam_raw = REDTEAM_PATH.read_bytes()
    final_review_raw = FINAL_REVIEW_PATH.read_bytes()
    third_review_raw = THIRD_REVIEW_PATH.read_bytes()
    return {
        "bindings": {
            "count_log1p_table": {
                "byte_length": len(table_raw),
                "filename": TABLE_PATH.name,
                "sha256": sha256_bytes(table_raw),
            },
            "independent_redteam": {
                "byte_length": len(redteam_raw),
                "filename": REDTEAM_PATH.name,
                "sha256": sha256_bytes(redteam_raw),
            },
            "v2_final_independent_review": {
                "byte_length": len(final_review_raw),
                "filename": FINAL_REVIEW_PATH.name,
                "sha256": sha256_bytes(final_review_raw),
                "verdict": "PARTIAL_ACCEPT_SCOPED_WITH_BLOCKERS",
            },
            "v3_final_independent_review": {
                "byte_length": len(third_review_raw),
                "filename": THIRD_REVIEW_PATH.name,
                "sha256": sha256_bytes(third_review_raw),
                "verdict": "REJECT_WITH_RETAINED_NUMERIC_SUBSCOPES",
            },
            "study_source": {
                "byte_length": len(source_raw),
                "filename": Path(__file__).name,
                "sha256": sha256_bytes(source_raw),
            },
        },
        "candidate_status": "CANDIDATE_STUDY_NOT_CANON__NO_G__NO_FORMAL_3200",
        "conversion_kats": _conversion_cases(),
        "cost_and_portability": {
            "measurement_status": {
                "executed_case_operation_counts_and_peak_fraction_bits": "MEASURED_IN_EACH_OUTCOME",
                "formal_3200_cost": "NOT_RUN",
                "formal_reachable_term_digit_distribution": "UNKNOWN",
                "wall_clock_cpu_peak_rss": "UNKNOWN",
            },
            "path_a": {
                "dependencies": ["IEEE-754 binary64 semantics", "frozen 256-entry lookup table"],
                "portability_boundary": (
                    "portable only when RN-ties-even, every-operation rounding, operation order, "
                    "no unregistered FMA/contraction, and exact KAT bytes are enforced"
                ),
                "runtime": "O(n) fixed-width operations; constant-width accumulator",
            },
            "path_b": {
                "dependencies": [
                    "bounded arbitrary-precision integer/rational arithmetic",
                    "integer midpoint sqrt oracle",
                ],
                "portability_boundary": (
                    "byte-rebuildable across languages if rational reduction, resource ceilings, "
                    "and final RN-ties-even conversion are identical"
                ),
                "runtime": (
                    "O(n) exact operations with data-dependent big-integer cost; numerator and "
                    "denominator ceilings are enforced by study caps but are not formal limits"
                ),
            },
            "study_only_reference": {
                "decimal_log1p": (
                    "Python Decimal ln at 80/160/240 digits; stability plus exact binary64 "
                    "conversion is strong cross-check evidence, not a formal correct-rounding proof"
                ),
                "external_dependencies_installed": False,
                "mpfr_or_arb_used": False,
            },
        },
        "decision": {
            "divergence_case_count": len(true_divergences),
            "divergence_case_interpretation": (
                "five recorded cases across three broad semantic axes, not five independent mechanisms"
            ),
            "formal_reachability": "UNKNOWN",
            "minimal_sufficient_set": "UNKNOWN_NOT_CLAIMED",
            "path_b_wholesale_deletable": False,
            "reason": (
                "The suites contain byte-level counterexamples: per-operation binary64 loses a "
                "unit shift at a large offset, changes signed collision sums, and changes an L2 "
                "norm after small squared terms. They refute universal byte equivalence only."
            ),
            "scoped_design_directions_not_adopted": [
                "exact rational-to-binary64 converter remains a supported kernel, not a complete admission wrapper",
                "exact dyadic collision/norm accumulation remains a candidate when multiset semantics are chosen",
                "fixed binary64 remains a candidate when order-defined fold semantics are chosen",
                "frozen count table can remove runtime transcendental only after external pin and release review",
            ],
            "task_impact": "UNKNOWN",
            "unresolved_before_canon": [
                "choose type7, averaged_inverted_cdf, or raw/no-centering by task ablation rather than numerical determinism alone",
                "decide whether signed collision is a mathematical multiset sum or an order-defined fold",
                "replace study-only resource caps with formal reachable input and cost limits",
                "compare mature fixed-width superaccumulator or integer-scaled alternatives under the same task and cost constraints",
                "obtain two independent provider byte rebuilds and secret holdback KATs",
            ],
        },
        "dependency_boundary": {
            "depends_on_rejected_c01_v0": False,
            "formal_population_read": False,
            "g_executed": False,
            "network_or_package_install": False,
        },
        "failure_contract": {
            "codes": list(FAILURE_CODES),
            "raw_exception_allowed_from_total_evaluators": False,
            "regressions": failure_regressions,
            "result_shape": "OK with finite bits or NOT_QUALIFIED with code, stage and provenance",
        },
        "independent_kernel_evidence": {
            "exact_sqrt_kernel": {
                "independent_exact_cell_checks": 3436,
                "status": "SCOPED_ACCEPT_KERNEL_ONLY",
            },
            "rational_to_binary64_kernel": {
                "independent_exact_neighbor_checks": 8882,
                "status": "SCOPED_ACCEPT_KERNEL_ONLY",
            },
            "source": "bound INDEPENDENT-REDTEAM.md; does not promote wrappers or G readiness",
        },
        "lifecycle_closure": {
            "column_accumulation": (
                "strict unique raw UTF-8 identity order; all rational leaves independently admitted; "
                "A rounds each add, B exact-adds under caps then rounds once; nonfinite fails"
            ),
            "count_transform": (
                "admit exact u64; min(count,255); externally pinned frozen lookup; +0 canonicalization"
            ),
            "family_normalization": (
                "require exact built-in list container and exact Fraction leaves; independently admit exact finite binary64 rationals and abs<=8; compute bounded norm; "
                "zero norm emits +0; otherwise divide by rounded norm, output-round and canonicalize +0"
            ),
            "numeric_standardization": {
                "A": "admit; leaf-round; subtract-round; divide-round; reject nonfinite; clip[-8,8]; +0",
                "B": "admit; exact subtract/divide under caps; exact clip[-8,8]; one output round; +0",
            },
        },
        "log1p_table_a_vs_decimal_reference_b": {
            "correct_rounding_status": "CORROBORATED_NOT_PROVEN",
            "decimal_precision_digits": [80, 160, 240],
            "disagreement_count": len(disagreements),
            "disagreements": disagreements,
            "entry_count": 256,
            "kats": [table_entries[index] for index in (0, 1, 255)],
            "stability_failure_count": len(unstable),
            "stability_failures": unstable,
            "heterogeneous_bc_corroboration": {
                "agreement_count": 256,
                "precision_decimal_digits": [100, 220],
                "source": "bound INDEPENDENT-REDTEAM.md",
                "status": "CORROBORATED_NOT_PROVEN",
            },
            "release_binding": {
                "expected_byte_length": EXPECTED_TABLE_BYTES,
                "expected_sha256_external_input": expected_table_sha256,
                "expected_sha256_type": "exact built-in str; subclasses rejected before regex/comparison",
                "metadata_exact_constants": EXPECTED_TABLE_METADATA,
                "raw_type": "exact built-in bytes; subclasses and bytes-like alternatives rejected",
                "rfc_json_nonfinite_constants_allowed": False,
                "rfc_json_numeric_tokens_allowed": False,
                "self_reported_digest_authoritative": False,
            },
        },
        "path_duel": {
            "accumulation": accumulation,
            "family_squared_norm_sqrt": norms,
            "quantile_and_centering": quantiles,
            "true_divergence_case_ids": true_divergences,
        },
        "resource_caps": {
            "absolute_post_parser_rational_binary_exponent": STUDY_MAX_ABS_RATIONAL_BINARY_EXPONENT,
            "canonical_numerator_or_denominator_decimal_digits": MAX_CANONICAL_RATIONAL_DIGITS,
            "formal_status": "STUDY_ONLY_NOT_CANON",
            "intermediate_numerator_or_denominator_bits": STUDY_MAX_INTERMEDIATE_BITS,
            "quantile_sample_count": STUDY_MAX_QUANTILE_SAMPLES,
            "table_bytes": STUDY_MAX_TABLE_BYTES,
            "terms_per_sum_or_norm": STUDY_MAX_TERMS,
            "upstream_absolute_decimal_exponent": UPSTREAM_MAX_ABS_DECIMAL_EXPONENT,
            "upstream_lexeme_significand_exponent_admission": "REQUIRED_BY_V2S_BUT_NOT_RECONSTRUCTABLE_FROM_POST_PARSER_RATIONAL; this study additionally enforces the post-parser binary-exponent guard",
        },
        "schema": "WAVE025_DETERMINISTIC_MATH_DUEL_RESULTS_V4",
        "serialization": "canonical compact UTF-8 JSON plus one LF",
        "version": "0.4.0",
    }


def write_canonical(path: Path, value: object) -> None:
    path.write_bytes(canonical_bytes(value))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--initialize-table",
        action="store_true",
        help="one-time construction only; refuses to replace an existing frozen table",
    )
    parser.add_argument("--write-results", action="store_true")
    parser.add_argument("--check", type=Path)
    parser.add_argument(
        "--expected-table-sha256",
        help="controller/reviewer supplied pin; never inferred from the table or result",
    )
    arguments = parser.parse_args()

    if arguments.initialize_table:
        if TABLE_PATH.exists():
            raise SystemExit(f"refusing to replace existing {TABLE_PATH.name}")
        write_canonical(TABLE_PATH, build_initial_table())
    if arguments.write_results:
        if not arguments.expected_table_sha256:
            parser.error("--write-results requires --expected-table-sha256")
        write_canonical(RESULTS_PATH, build_results(arguments.expected_table_sha256))
    if arguments.check:
        if not arguments.expected_table_sha256:
            parser.error("--check requires --expected-table-sha256")
        expected = canonical_bytes(build_results(arguments.expected_table_sha256))
        actual = arguments.check.read_bytes()
        if actual != expected:
            raise SystemExit(f"byte mismatch: {arguments.check}")
        print(
            f"PASS {arguments.check.name} bytes={len(actual)} sha256={sha256_bytes(actual)}"
        )
    if not (arguments.initialize_table or arguments.write_results or arguments.check):
        parser.error("choose --initialize-table, --write-results, or --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
