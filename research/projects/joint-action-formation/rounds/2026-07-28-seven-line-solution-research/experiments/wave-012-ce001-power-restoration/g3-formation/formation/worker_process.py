from __future__ import annotations

import copy
import os
import sys
from typing import Any

from .canonical import sha256
from .execution_service import FormationExecutionService
from .models import RunRecord
from .protocol import (
    raw_line_sha256,
    read_message,
    read_raw_message,
    verify_owner_response,
    write_message,
)


class BrokerOwnerClient:
    """Worker-side client that can consume only public bytes and endpoint bytes."""

    def __init__(self, public_case: dict[str, Any]) -> None:
        self.public_case = copy.deepcopy(public_case)
        self.anchors: dict[str, Any] | None = None
        self.owner_routing: dict[str, str] = {}
        self.received_response_sha256: list[str] = []
        self.request_counter = 0

    def _call(
        self,
        request: dict[str, Any],
        expected_owner: str,
        proposal_sha256: str | None = None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        self.request_counter += 1
        request = {
            **request,
            "public_case": copy.deepcopy(self.public_case),
            "request_nonce": sha256(
                {
                    "case_handle": self.public_case["case_handle"],
                    "counter": self.request_counter,
                    "operation": request["operation"],
                }
            )[:32],
            "sent_at_ms": self.request_counter * 10,
            "response_deadline_ms": self.request_counter * 10 + 5,
        }
        write_message(
            sys.stdout,
            {"type": "OWNER_REQUEST", "request": request},
        )
        raw_line, message = read_raw_message(sys.stdin)
        if message.get("type") != "OWNER_RESPONSE":
            raise ValueError("OWNER_PROTOCOL_RESPONSE_MISSING")
        response = message["response"]
        if self.anchors is None:
            payload = response.get("payload", {})
            candidate = payload.get("anchors")
            if not isinstance(candidate, dict):
                raise ValueError("OWNER_FREEZE_ANCHORS_MISSING")
            anchors = candidate
        else:
            anchors = self.anchors
        payload = verify_owner_response(
            response=response,
            request=request,
            public_case=self.public_case,
            expected_owner=expected_owner,
            expected_state_version=anchors["owner_state_versions"][
                expected_owner
            ],
            expected_policy_version=anchors["owner_policy_versions"][
                expected_owner
            ],
            expected_policy_head=anchors["owner_policy_heads"][expected_owner],
            expected_proposal_sha256=proposal_sha256,
            expected_operation_id=operation_id,
        )
        self.received_response_sha256.append(raw_line_sha256(raw_line))
        return payload

    def freeze_snapshot(self, public_case: dict[str, Any]) -> dict[str, Any]:
        payload = self._call(
            {"operation": "freeze_snapshot"},
            "O_R",
        )
        self.anchors = copy.deepcopy(payload["anchors"])
        self.owner_routing = copy.deepcopy(payload["owner_routing"])
        return payload

    def owner_event(
        self,
        phase: str,
        resource_id: str | None = None,
        proposal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        expected_owner = self.owner_routing.get(
            f"{phase}:{resource_id}",
            self.owner_routing.get(phase),
        )
        if expected_owner is None:
            raise ValueError("OWNER_ROUTE_NOT_FROZEN")
        return self._call(
            {
                "operation": "owner_event",
                "phase": phase,
                "resource_id": resource_id,
                "proposal": proposal,
            },
            expected_owner,
            sha256(proposal) if proposal is not None else None,
            "__PAYLOAD__" if phase == "execute" else None,
        )

    def target_readback(
        self, resource_id: str, operation_id: str, attempt: int
    ) -> dict[str, Any]:
        return self._call(
            {
                "operation": "target_readback",
                "resource_id": resource_id,
                "operation_id": operation_id,
                "attempt": attempt,
            },
            "O_E",
            operation_id=operation_id,
        )

    def observe_outcome(
        self,
        owner_id: str,
        task_sha256: str,
        readback_sha256: str,
        operation_id: str,
    ) -> dict[str, Any]:
        return self._call(
            {
                "operation": "outcome_observation",
                "owner_id": owner_id,
                "task_sha256": task_sha256,
                "readback_sha256": readback_sha256,
                "operation_id": operation_id,
            },
            owner_id,
            operation_id=operation_id,
        )


def main() -> int:
    start = read_message(sys.stdin)
    if start.get("type") != "START":
        raise ValueError("worker requires START")
    public_case = start["public_case"]
    client = BrokerOwnerClient(public_case)
    record = FormationExecutionService(client).execute(
        public_case, start["intervention"]
    )
    record.append(
        {
            "type": "PROCESS_BOUNDARY_OBSERVATION",
            "worker_pid": os.getpid(),
            "owner_response_count": len(client.received_response_sha256),
            "owner_response_stream_sha256": sha256(
                client.received_response_sha256
            ),
            "owner_response_wire_line_sha256": (
                client.received_response_sha256
            ),
            "worker_input_classes": [
                "PUBLIC_PACKET_BYTES",
                "OWNER_ENDPOINT_RESPONSE_BYTES",
            ],
        }
    )
    write_message(
        sys.stdout,
        {"type": "WORKER_RESULT", "record": record.body()},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
