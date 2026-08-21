#!/usr/bin/env python3
"""Independent standard-library power audit for Wave 025 POWER-NOTE V3.

The implementation does not import the runner, evaluator, feature extractor,
or executable profile.  It reconstructs one-sided class-wise
Clopper-Pearson bounds and the two-Binomial pass probability directly.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any


CLASS_TAIL_ALPHA = 0.025
CLASS_CONFIDENCE = 0.975
AVERAGE_UPPER_THRESHOLD = 0.55
FLOAT_BISECTION_ITERATIONS = 80
DECIMAL_PRECISION = 80


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def binomial_cdf_float(k: int, n: int, p: float) -> float:
    """Return P[X <= k] for X~Binomial(n,p), stable in the CP root region."""
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if not 0.0 <= p <= 1.0:
        raise ValueError("p must satisfy 0 <= p <= 1")
    if k == n or p == 0.0:
        return 1.0
    if p == 1.0:
        return 0.0
    q = 1.0 - p
    log_term = (
        math.lgamma(n + 1)
        - math.lgamma(k + 1)
        - math.lgamma(n - k + 1)
        + k * math.log(p)
        + (n - k) * math.log1p(-p)
    )
    term = math.exp(log_term)
    terms = [term]
    max_term = term
    # At a one-sided CP upper root, p > k/n.  Starting at k and walking
    # downward therefore decreases the terms and avoids a large-tail
    # subtraction from one.
    for j in range(k, 0, -1):
        term *= (j / (n - j + 1)) * (q / p)
        terms.append(term)
        max_term = max(max_term, term)
        if term <= math.ulp(1.0) * max_term:
            break
    value = math.fsum(terms)
    return min(1.0, max(0.0, value))


def clopper_pearson_upper_float(
    k: int,
    n: int,
    tail_alpha: float = CLASS_TAIL_ALPHA,
    iterations: int = FLOAT_BISECTION_ITERATIONS,
) -> float:
    """Conservative one-sided CP upper endpoint.

    For k<n it solves P_p[X<=k]=tail_alpha.  The returned endpoint is the
    high side of the final bracket, so floating uncertainty cannot turn a
    numerically marginal failure into a pass.
    """
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if not 0.0 < tail_alpha < 1.0:
        raise ValueError("tail_alpha must satisfy 0 < alpha < 1")
    if k == n:
        return 1.0
    low = k / n if n else 0.0
    high = 1.0
    for _ in range(iterations):
        midpoint = (low + high) / 2.0
        cdf = binomial_cdf_float(k, n, midpoint)
        if cdf > tail_alpha:
            low = midpoint
        else:
            high = midpoint
    return high


def binomial_cdf_decimal(k: int, n: int, p: Decimal) -> Decimal:
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if not Decimal(0) <= p <= Decimal(1):
        raise ValueError("p must satisfy 0 <= p <= 1")
    if k == n or p == 0:
        return Decimal(1)
    if p == 1:
        return Decimal(0)
    q = Decimal(1) - p
    term = Decimal(math.comb(n, k)) * (p**k) * (q ** (n - k))
    total = term
    for j in range(k, 0, -1):
        term *= (Decimal(j) / Decimal(n - j + 1)) * (q / p)
        total += term
    return total


def clopper_pearson_upper_decimal(
    k: int,
    n: int,
    tail_alpha: Decimal = Decimal("0.025"),
    precision: int = DECIMAL_PRECISION,
) -> Decimal:
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if not Decimal(0) < tail_alpha < Decimal(1):
        raise ValueError("tail_alpha must satisfy 0 < alpha < 1")
    if k == n:
        return Decimal(1)
    with localcontext() as context:
        context.prec = precision
        low = Decimal(k) / Decimal(n) if n else Decimal(0)
        high = Decimal(1)
        # 280 halvings are substantially tighter than 80 decimal digits.
        for _ in range(280):
            midpoint = (low + high) / Decimal(2)
            if binomial_cdf_decimal(k, n, midpoint) > tail_alpha:
                low = midpoint
            else:
                high = midpoint
        return +high


def cp_upper_table(n: int, tail_alpha: float = CLASS_TAIL_ALPHA) -> list[float]:
    values = [clopper_pearson_upper_float(k, n, tail_alpha) for k in range(n + 1)]
    if any(values[index] > values[index + 1] for index in range(n)):
        raise ArithmeticError("CP upper table is not monotone")
    return values


def literal_double_binomial_probability(n: int, upper: list[float], threshold: float) -> Fraction:
    """Literal O(n^2) reference, intended for small-n tests."""
    numerator = 0
    weights = [math.comb(n, k) for k in range(n + 1)]
    for k_s, weight_s in enumerate(weights):
        for k_r, weight_r in enumerate(weights):
            if (upper[k_s] + upper[k_r]) / 2.0 <= threshold:
                numerator += weight_s * weight_r
    return Fraction(numerator, 1 << (2 * n))


def double_binomial_pass_probability(
    n: int,
    threshold: float = AVERAGE_UPPER_THRESHOLD,
    tail_alpha: float = CLASS_TAIL_ALPHA,
) -> dict[str, Any]:
    """Exact enumeration weight with monotone O(n log n) lattice lookup."""
    upper = cp_upper_table(n, tail_alpha)
    weights = [math.comb(n, k) for k in range(n + 1)]
    cumulative = []
    running = 0
    for weight in weights:
        running += weight
        cumulative.append(running)

    sum_limit = 2.0 * threshold
    numerator = 0
    max_pass_sum = -math.inf
    min_fail_sum = math.inf
    boundary_pairs: list[tuple[int, int]] = []
    for k_s, (upper_s, weight_s) in enumerate(zip(upper, weights)):
        k_r_max = bisect.bisect_right(upper, sum_limit - upper_s) - 1
        if k_r_max >= 0:
            numerator += weight_s * cumulative[k_r_max]
            pair_sum = upper_s + upper[k_r_max]
            max_pass_sum = max(max_pass_sum, pair_sum)
            boundary_pairs.append((k_s, k_r_max))
        if k_r_max + 1 <= n:
            min_fail_sum = min(min_fail_sum, upper_s + upper[k_r_max + 1])

    denominator = 1 << (2 * n)
    probability = Fraction(numerator, denominator)
    central = clopper_pearson_upper_float(n // 2, n, tail_alpha)
    return {
        "n_per_class": n,
        "holdout_total": 2 * n,
        "central_k": n // 2,
        "central_cp_upper": central,
        "pass_probability_fraction": probability,
        "pass_probability": float(probability),
        "max_pass_upper_sum": max_pass_sum,
        "min_fail_upper_sum": min_fail_sum,
        "pass_boundary_margin": sum_limit - max_pass_sum,
        "fail_boundary_margin": min_fail_sum - sum_limit,
        "boundary_pair_count": len(boundary_pairs),
        "cp_table": upper,
    }


def block_balance_audit() -> dict[str, Any]:
    strata = {
        "D0-HOST-LEAK": {"calibration": 100, "holdout": 100},
        "D1-OCI-CANARY": {"calibration": 100, "holdout": 100},
        "T-OCI-ISOLATED": {"calibration": 400, "holdout": 2400},
    }
    block_size = 20
    per_role_per_block = 10
    details = {}
    total_slots = 0
    total_blocks = 0
    for challenge, phases in strata.items():
        details[challenge] = {}
        for phase, slots in phases.items():
            if slots % block_size:
                raise ArithmeticError(f"{challenge}/{phase} is not block divisible")
            blocks = slots // block_size
            per_role = blocks * per_role_per_block
            if 2 * per_role != slots:
                raise ArithmeticError(f"{challenge}/{phase} is not exactly role balanced")
            details[challenge][phase] = {
                "slots": slots,
                "blocks": blocks,
                "per_role": per_role,
            }
            total_slots += slots
            total_blocks += blocks
    return {
        "block_size": block_size,
        "per_role_per_block": per_role_per_block,
        "strata": details,
        "total_slots": total_slots,
        "total_blocks": total_blocks,
        "T_holdout_n_per_class": details["T-OCI-ISOLATED"]["holdout"]["per_role"],
    }


def audit() -> dict[str, Any]:
    results = {n: double_binomial_pass_probability(n) for n in (400, 800, 1200)}
    decimal_cross_checks = {}
    for n in (400, 800, 1200):
        k = n // 2
        decimal_value = clopper_pearson_upper_decimal(k, n)
        float_value = results[n]["central_cp_upper"]
        decimal_cross_checks[str(n)] = {
            "k": k,
            "float": float_value,
            "decimal": format(decimal_value, ".16f"),
            "absolute_difference": abs(float_value - float(decimal_value)),
            "float_cdf_residual": abs(binomial_cdf_float(k, n, float_value) - CLASS_TAIL_ALPHA),
        }

    single = results[1200]["pass_probability_fraction"]
    five_lower = Fraction(1, 1) - 5 * (Fraction(1, 1) - single)
    six_lower = Fraction(1, 1) - 6 * (Fraction(1, 1) - single)
    serializable_results = {}
    for n, result in results.items():
        serializable_results[str(n)] = {
            key: value
            for key, value in result.items()
            if key not in {"cp_table", "pass_probability_fraction"}
        }
        serializable_results[str(n)]["pass_probability_decimal"] = format(
            Decimal(result["pass_probability_fraction"].numerator)
            / Decimal(result["pass_probability_fraction"].denominator),
            ".12f",
        )
        serializable_results[str(n)]["exact_probability_numerator_sha256"] = hashlib.sha256(
            str(result["pass_probability_fraction"].numerator).encode("ascii")
        ).hexdigest()
        serializable_results[str(n)]["exact_probability_denominator_power_of_two"] = 2 * n

    return {
        "schema": "WAVE025_POWER_AUDIT_V1",
        "method": {
            "cp_upper": "FLOAT_BISECTION_BINOMIAL_CDF_WITH_DECIMAL_CROSS_CHECK",
            "class_tail_alpha": CLASS_TAIL_ALPHA,
            "class_confidence": CLASS_CONFIDENCE,
            "average_upper_threshold": AVERAGE_UPPER_THRESHOLD,
            "pass_probability": "EXACT_TWO_BINOMIAL_INTEGER_WEIGHT_ENUMERATION_WITH_MONOTONE_BOUNDARY_LOOKUP",
            "episode_model": "K_S_AND_K_R_INDEPENDENT_BINOMIAL_N_0_5",
        },
        "single_attack": serializable_results,
        "decimal_cross_checks": decimal_cross_checks,
        "n1200_union_bounds": {
            "five_attacks": float(five_lower),
            "five_attacks_decimal": format(
                Decimal(five_lower.numerator) / Decimal(five_lower.denominator), ".12f"
            ),
            "six_attacks": float(six_lower),
            "six_attacks_decimal": format(
                Decimal(six_lower.numerator) / Decimal(six_lower.denominator), ".12f"
            ),
            "attack_independence_required": False,
            "within_attack_episode_and_class_count_model_required": True,
        },
        "block_balance": block_balance_audit(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recompute Wave025 POWER-NOTE V3")
    parser.parse_args(argv)
    print(canonical_bytes(audit()).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
