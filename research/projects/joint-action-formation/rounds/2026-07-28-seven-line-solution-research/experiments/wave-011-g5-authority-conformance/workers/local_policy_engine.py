#!/usr/bin/env python3
"""Executable local reference policy engine.

It emits only native engine data. It never reads the business-outcome oracle
and does not know the ALLOW/REJECT/UNKNOWN/DEFER expected label.

This is a real local subprocess engine used by the harness, but it is not OPA,
Cedar, OpenFGA, or XACML and is not evidence about those products.
"""

from __future__ import annotations

import json
import sys
from typing import Any


def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    request = case["request"]
    policy = case["policy"]
    attributes = request.get("attributes", {})
    missing = [name for name in policy.get("requires", []) if name not in attributes]
    if missing:
        outcome = "INDETERMINATE"
        error = {
            "code": "MISSING_ATTRIBUTE",
            "attributes": missing,
            "recoverable": True,
        }
    else:
        outcome = policy["effect"]
        error = None
        if outcome == "ENGINE_ERROR":
            error = {
                "code": "REFERENCE_ENGINE_FAILURE",
                "recoverable": True,
            }
    return {
        "schema": "mcb-g5-v2.local-reference-native-result.v1",
        "case_id": case["case_id"],
        "native_engine": "LOCAL_REFERENCE_POLICY_ENGINE",
        "native_outcome": outcome,
        "native_error": error,
        "policy_version": policy["version"],
        "input_complete": not missing,
        "source_freshness": case["source_freshness"],
        "negative_authority_fact": outcome == "FORBID",
        "resolver": case.get("resolvable_by"),
    }


def main() -> int:
    case = json.load(sys.stdin)
    json.dump(evaluate(case), sys.stdout, ensure_ascii=False, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
