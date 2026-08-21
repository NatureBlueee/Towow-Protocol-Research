#!/usr/bin/env python3
"""A2 evaluator with separate attempt, L3 and L4 state deltas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from protocol import normalize_request, sha256_value


V1_DIR = (
    Path(__file__).resolve().parents[1]
    / "wave-007-a-opaque-authority-harness"
)
_SPEC = importlib.util.spec_from_file_location(
    "wave007_a_v1_evaluator_for_a2",
    V1_DIR / "evaluator.py",
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("cannot load Wave 007-A evaluator dependency")
_BASE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _BASE
_SPEC.loader.exec_module(_BASE)

operational_expected_terminal = _BASE.operational_expected_terminal
recompute_cost = _BASE.recompute_cost


def _can_reach_l3(world: dict[str, Any]) -> bool:
    return (
        world["holder_seek"] == "ACTIVE"
        and world["holder_offer"] == "ACTIVE"
        and world["anchor"] == "HEALTHY"
        and world["recipient"] == "ACTIVE"
    )


def evaluate(
    *,
    public_request: dict[str, Any],
    world_truth: dict[str, Any],
    public_registry: dict[str, str],
    candidate_output: dict[str, Any],
    operation_log: list[dict[str, Any]],
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
) -> dict[str, Any]:
    result = _BASE.evaluate(
        public_request=public_request,
        world_truth=world_truth,
        public_registry=public_registry,
        candidate_output=candidate_output,
        operation_log=operation_log,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
    )
    request = normalize_request(public_request)
    request_sha = sha256_value(request)
    key = request["idempotency_key"]
    before_bindings = before_snapshot["attempt_bindings"]
    previous_binding = before_bindings.get(key)
    conflict = (
        previous_binding is not None
        and previous_binding != request_sha
    )

    actual_attempt_binding_delta = (
        after_snapshot["attempt_binding_count"]
        - before_snapshot["attempt_binding_count"]
    )
    expected_attempt_binding_delta = (
        1
        if previous_binding is None
        and world_truth["holder_seek"] == "ACTIVE"
        and world_truth["holder_offer"] == "ACTIVE"
        else 0
    )

    before_l3 = set(
        before_snapshot["domain_postcondition_sha256"]
    )
    actual_l3_delta = (
        after_snapshot["domain_postcondition_count"]
        - before_snapshot["domain_postcondition_count"]
    )
    expected_l3_delta = (
        1
        if not conflict
        and _can_reach_l3(world_truth)
        and request_sha not in before_l3
        else 0
    )

    # A v1's effect delta is specifically the L4 beneficiary ledger.  A2
    # retains that field for compatibility but names both levels explicitly.
    actual_l4_delta = result["actual_effect_delta"]
    expected_l4_delta = result["expected_effect_delta"]
    result.update(
        {
            "idempotency_binding_conflict": conflict,
            "actual_attempt_binding_delta": actual_attempt_binding_delta,
            "expected_attempt_binding_delta": expected_attempt_binding_delta,
            "attempt_binding_delta_match": (
                actual_attempt_binding_delta
                == expected_attempt_binding_delta
            ),
            "actual_l3_domain_postcondition_delta": actual_l3_delta,
            "expected_l3_domain_postcondition_delta": expected_l3_delta,
            "l3_domain_postcondition_delta_match": (
                actual_l3_delta == expected_l3_delta
            ),
            "actual_l4_beneficiary_acceptance_delta": actual_l4_delta,
            "expected_l4_beneficiary_acceptance_delta": expected_l4_delta,
            "l4_beneficiary_acceptance_delta_match": (
                actual_l4_delta == expected_l4_delta
            ),
            "all_level_deltas_match": (
                actual_attempt_binding_delta
                == expected_attempt_binding_delta
                and actual_l3_delta == expected_l3_delta
                and actual_l4_delta == expected_l4_delta
            ),
            "anchor_equivocation_evidence_scope": (
                "CENTRAL_HIDDEN_STATE_DETECTOR_FIXTURE_ONLY"
            ),
        }
    )
    return result
