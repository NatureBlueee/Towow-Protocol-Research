from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .canonical import sha256
from .owner_service import OwnerService
from .protocol import (
    authorize_owner_response,
    make_owner_response,
    read_message,
    write_message,
    write_raw_message,
)


PHASE_OWNER = {
    "read": "O_R",
    "rediscover": "O_S",
    "sign": "O_V",
    "reserve": "O_R",
    "execute": "O_E",
    "target_readback": "O_E",
}


class EndpointSession:
    def __init__(
        self,
        private_document: dict[str, Any],
        case_handle: str,
        intervention: str,
        response_fault: str | None,
        signing_seed: str,
    ) -> None:
        case_id = private_document["manifest"][case_handle]
        self.truth = copy.deepcopy(private_document["cases"][case_id])
        self.owner = OwnerService(self.truth, intervention)
        self.anchors = self.owner.frozen_anchors()
        self.response_fault = response_fault
        self.signing_key = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(signing_seed)
        )
        self.counter = 0

    def respond(self, request: dict[str, Any]) -> dict[str, Any]:
        self.counter += 1
        operation = request["operation"]
        public_case = request["public_case"]
        task = public_case["task"]
        proposal = request.get("proposal")
        proposal_hash = sha256(proposal) if proposal is not None else None
        operation_id = request.get("operation_id")

        if operation == "freeze_snapshot":
            routing: dict[str, str] = {}
            for phase, phase_truth in self.truth["owner_events"].items():
                if isinstance(phase_truth, dict) and phase_truth.get("owner_id"):
                    routing[phase] = phase_truth["owner_id"]
                elif isinstance(phase_truth, dict):
                    for resource_id, value in phase_truth.items():
                        if isinstance(value, dict) and value.get("owner_id"):
                            routing[f"{phase}:{resource_id}"] = value["owner_id"]
            payload = {
                "initial_state": self.owner.initial_state(),
                "initial_kernel": self.owner.initial_kernel(),
                "operator_registry": self.owner.operator_registry(),
                "anchors": self.anchors,
                "owner_routing": routing,
            }
            owner_id = "O_R"
        elif operation == "owner_event":
            phase = request["phase"]
            payload = self.owner.owner_event(
                phase,
                request.get("resource_id"),
                proposal,
            )
            owner_id = payload.get("owner_id", PHASE_OWNER[phase])
            operation_id = payload.get("operation_id", operation_id)
        elif operation == "target_readback":
            payload = self.owner.target_readback(
                request["resource_id"],
                operation_id,
                request["attempt"],
            )
            owner_id = "O_E"
        elif operation == "outcome_observation":
            owner_id = request["owner_id"]
            payload = self.owner.accept_effect(
                owner_id,
                request["task_sha256"],
                request["readback_sha256"],
                operation_id,
            )
        else:
            raise ValueError(f"unsupported operation: {operation}")

        response = make_owner_response(
            request=request,
            payload=payload,
            owner_identity=owner_id,
            state_version=self.anchors["owner_state_versions"][owner_id],
            policy_version=self.anchors["owner_policy_versions"][owner_id],
            policy_head=self.anchors["owner_policy_heads"][owner_id],
            episode_handle=public_case["episode_handle"],
            task=task,
            issued_at=f"T0+{self.counter:03d}ms",
            proposal_sha256=proposal_hash,
            operation_id=operation_id,
            signing_key=self.signing_key,
        )
        return self._inject_fault(response, operation)

    def _inject_fault(
        self, response: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        fault = self.response_fault
        if operation != "owner_event" or response["payload"].get("phase") != "sign":
            return response
        body = copy.deepcopy(response)
        if fault == "STALE":
            body["issued_at_ms"] = 999
            body["issued_at"] = "T0+999ms"
        elif fault == "WRONG_OWNER":
            body["owner_identity"] = "CONTROLLER"
        elif fault == "STALE_STATE":
            body["owner_state_version"] = "STATE-O_V-v0"
        elif fault == "STALE_POLICY_VERSION":
            body["owner_policy_version"] = "POLICY-O_V-v0"
        elif fault == "STALE_POLICY_HEAD":
            body["owner_policy_head"] = "HEAD-O_V-stale"
        elif fault == "TRANSPLANT":
            body["episode_handle"] = "P999"
        elif fault == "WRONG_Q":
            body["q_version"] = "CE-001-Q@wrong"
        elif fault == "WRONG_TARGET":
            body["object_id"] = "Venue-V:C8"
        elif fault == "WRONG_OPERATION":
            body["operation_id"] = "OP-WRONG"
        elif fault == "WRONG_REQUEST":
            body["request_sha256"] = "f" * 64
        elif fault == "WRONG_REQUEST_NONCE":
            body["request_nonce"] = "d" * 32
        elif fault == "WRONG_PROPOSAL":
            body["proposal_sha256"] = "e" * 64
        else:
            return response
        return authorize_owner_response(body, self.signing_key)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", required=True)
    args = parser.parse_args()
    private_document = json.loads(
        Path(args.private).read_text(encoding="utf-8")
    )
    init = read_message(sys.stdin)
    session = EndpointSession(
        private_document,
        init["case_handle"],
        init["intervention"],
        init.get("response_fault"),
        private_document["owner_endpoint_signing_seed"],
    )
    write_message(
        sys.stdout,
        {
            "type": "OWNER_ENDPOINT_READY",
            "pid": __import__("os").getpid(),
            "case_handle": init["case_handle"],
        },
    )
    while True:
        try:
            request = read_message(sys.stdin)
        except EOFError:
            break
        if request.get("type") == "STOP":
            break
        response_message = {
            "type": "OWNER_RESPONSE",
            "response": session.respond(request["request"]),
        }
        if init.get("response_fault") == "WIRE_VARIANT":
            write_raw_message(
                sys.stdout,
                json.dumps(
                    response_message,
                    ensure_ascii=False,
                    sort_keys=False,
                    separators=(", ", " : "),
                )
                + "\n",
            )
        else:
            write_message(sys.stdout, response_message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
