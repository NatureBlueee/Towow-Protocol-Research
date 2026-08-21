"""Candidate-process public coordinates and JSON-RPC gateway.

The gateway contains only an RPC client connected to the parent broker.  It
never receives the broker object, private world state, keys, or audit log.
"""

from __future__ import annotations

from typing import Any, Protocol


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


class RpcClient(Protocol):
    def call(
        self, method: str, params: dict[str, Any]
    ) -> dict[str, Any]: ...


class JsonRpcEvidenceGateway:
    """Method-only proxy; no parent-process callable is transferred."""

    __slots__ = ("opaque_handle", "_client")

    def __init__(self, opaque_handle: str, client: RpcClient):
        self.opaque_handle = opaque_handle
        self._client = client

    def read_evidence(self, name: str) -> dict[str, Any]:
        return self._client.call("read_evidence", {"name": name})

    def verify_evidence(
        self, evidence: dict[str, Any]
    ) -> dict[str, Any]:
        return self._client.call(
            "verify_evidence", {"evidence": evidence}
        )

    def record_relation_decision(
        self, state: str, evidence_refs: list[str]
    ) -> None:
        self._client.call(
            "record_relation_decision",
            {"state": state, "evidence_refs": evidence_refs},
        )

    def request_reuse(
        self, authorizations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return self._client.call(
            "request_reuse", {"authorizations": authorizations}
        )

    def poll_withdrawal(self) -> dict[str, Any]:
        return self._client.call("poll_withdrawal", {})
