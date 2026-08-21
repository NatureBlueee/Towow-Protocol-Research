"""Candidate-visible constants and callable-only evidence gateway.

This module deliberately contains no world truth, private key material,
signing helper, evidence inventory, or evaluator result.
"""

from __future__ import annotations

from typing import Any, Callable


SHARED_TASK_ID = "W6-STERILE-ROUTE-SIMULATION-001"
SHARED_TASK_SHA256 = (
    "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
)
WORLD_ID = "W6-STERILE-ROUTE-WORLD"
STEP = 7
OPERATION = "RUN-STERILE-ROUTE-SIM-v1"
REUSE_OPERATION = "RUN-STERILE-ROUTE-SIM-v1.1"
PURPOSE = "sterile-route-simulation"
RETENTION = "PT7M"


class EvidenceGateway:
    """Candidate-visible API with no authority-service or audit handle."""

    __slots__ = (
        "opaque_handle",
        "read_evidence",
        "verify_evidence",
        "record_relation_decision",
        "request_reuse",
        "poll_withdrawal",
    )

    def __init__(
        self,
        *,
        opaque_handle: str,
        read_evidence: Callable[[str], dict[str, Any]],
        verify_evidence: Callable[[dict[str, Any]], dict[str, Any]],
        record_relation_decision: Callable[
            [str, list[str]], None
        ],
        request_reuse: Callable[
            [list[dict[str, Any]]], dict[str, Any]
        ],
        poll_withdrawal: Callable[[], dict[str, Any]],
    ):
        self.opaque_handle = opaque_handle
        self.read_evidence = read_evidence
        self.verify_evidence = verify_evidence
        self.record_relation_decision = record_relation_decision
        self.request_reuse = request_reuse
        self.poll_withdrawal = poll_withdrawal
