from __future__ import annotations

from typing import Any


MAPPING_VERSION = "task-mapping-estuary-v1"

POSITIVE_NATIVE_OUTCOMES = {
    "PERMIT",
    "OPA_DEFINED_ALLOW",
    "CEDAR_ALLOW",
    "OPENFGA_ALLOWED_TRUE",
    "XACML_PERMIT",
}

NEGATIVE_NATIVE_OUTCOMES = {
    "FORBID",
    "CEDAR_DENY_EXPLICIT_FORBID",
    "XACML_DENY",
}

RESOLVABLE_NATIVE_OUTCOMES = {
    "NOT_APPLICABLE",
    "INDETERMINATE",
    "PENDING_EXTERNAL_APPROVAL",
    "ENGINE_ERROR",
    "OPA_UNDEFINED",
    "OPA_EVAL_ERROR",
    "CEDAR_ALLOW_WITH_EVALUATION_ERRORS",
    "CEDAR_DENY_NO_PERMIT",
    "OPENFGA_ALLOWED_FALSE",
    "OPENFGA_HTTP_400_UNDEFINED_RELATION",
    "XACML_NOT_APPLICABLE",
    "XACML_INDETERMINATE_P",
    "XACML_INDETERMINATE_D",
    "XACML_INDETERMINATE_DP",
}


def derive_business_outcome(native: dict[str, Any]) -> dict[str, Any]:
    """Derive a task outcome while preserving the complete native record."""

    outcome = native["native_outcome"]
    freshness = native["source_freshness"]
    resolver = native.get("resolver")

    if native.get("negative_authority_fact") or outcome in NEGATIVE_NATIVE_OUTCOMES:
        business = "REJECT"
        reason = "AUTHORITATIVE_NEGATIVE_FACT"
    elif freshness != "FRESH":
        business = "DEFER" if resolver else "UNKNOWN"
        reason = "STALE_SOURCE_REQUIRES_REFRESH"
    elif native.get("native_error") is not None:
        business = "DEFER" if resolver else "UNKNOWN"
        reason = "NATIVE_ERROR_REQUIRES_OWNER_MAPPING"
    elif (
        outcome in POSITIVE_NATIVE_OUTCOMES
        and native["input_complete"]
        and freshness == "FRESH"
    ):
        business = "ALLOW"
        reason = "FRESH_COMPLETE_NATIVE_PERMIT"
    elif outcome in RESOLVABLE_NATIVE_OUTCOMES:
        business = "DEFER" if resolver else "UNKNOWN"
        reason = "RESOLVER_AVAILABLE" if resolver else "NO_AUTHORITATIVE_RESOLVER"
    else:
        business = "UNMAPPED_NATIVE_OUTCOME"
        reason = "NO_OWNER_APPROVED_MAPPING"

    return {
        "schema": "mcb-g5-v2.task-mapped-decision.v1",
        "mapping_version": MAPPING_VERSION,
        "business_outcome": business,
        "reason": reason,
        "native_record": native,
    }
