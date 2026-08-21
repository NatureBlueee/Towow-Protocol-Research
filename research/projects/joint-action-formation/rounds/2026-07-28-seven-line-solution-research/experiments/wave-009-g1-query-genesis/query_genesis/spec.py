"""Frozen experiment constants shared by candidates and the parent runner."""

from __future__ import annotations

CAPABILITIES = (
    "observe_goal_seed",
    "request_principal_clarification",
    "form_query",
    "poll_local_trigger",
    "emit_projection",
    "search_index",
    "read_current_head",
    "private_match",
    "request_probe",
    "handoff",
    "platform_direct",
    "stop",
)

HANDOFF_STATUS = "CANDIDATE_NOT_COMMITMENT"
BROKER_MODEL_VERSION = "wave009-parent-broker-v3"
STRATEGY_REGISTRY_VERSION = "wave009-seven-arm-registry-v2"

DISCLOSURE_VECTOR_KEYS = (
    "origin_facts",
    "recipients",
    "sensitivity",
    "retention_units",
    "onward_hops",
    "depth",
    "cryptographic_leakage_bits",
    "policy_violations",
)
