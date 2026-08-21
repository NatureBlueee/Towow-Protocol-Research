from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .canonical import canonical_bytes, sha256


def object_id(task: dict[str, Any]) -> str:
    target = task["target"]
    return f'{target["venue_id"]}:{target["circuit_id"]}'


def request_bytes(request: dict[str, Any]) -> bytes:
    return canonical_bytes(request)


def response_bytes(response: dict[str, Any]) -> bytes:
    return canonical_bytes(response)


def make_owner_response(
    *,
    request: dict[str, Any],
    payload: dict[str, Any],
    owner_identity: str,
    state_version: str,
    policy_version: str,
    policy_head: str,
    episode_handle: str,
    task: dict[str, Any],
    issued_at: str,
    proposal_sha256: str | None,
    operation_id: str | None,
    signing_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    issued_at = f'T0+{request["sent_at_ms"] + 1:03d}ms'
    body = {
        "schema_version": "ce001-owner-response-v2",
        "owner_identity": owner_identity,
        "owner_state_version": state_version,
        "owner_policy_version": policy_version,
        "owner_policy_head": policy_head,
        "episode_handle": episode_handle,
        "q_version": task["q_version"],
        "object_id": object_id(task),
        "operation_id": operation_id,
        "request_sha256": sha256(request),
        "request_nonce": request["request_nonce"],
        "response_nonce": sha256(
            {
                "request_nonce": request["request_nonce"],
                "owner_identity": owner_identity,
                "issued_at": issued_at,
            }
        )[:32],
        "proposal_sha256": proposal_sha256,
        "issued_at": issued_at,
        "issued_at_ms": request["sent_at_ms"] + 1,
        "payload": copy.deepcopy(payload),
    }
    return authorize_owner_response(body, signing_key)


def authorize_owner_response(
    response: dict[str, Any], signing_key: Ed25519PrivateKey
) -> dict[str, Any]:
    body = copy.deepcopy(response)
    body.pop("response_sha256", None)
    body.pop("owner_authenticator", None)
    body["response_nonce"] = sha256(
        {
            "request_nonce": body["request_nonce"],
            "owner_identity": body["owner_identity"],
            "issued_at": body["issued_at"],
        }
    )[:32]
    body["response_sha256"] = sha256(body)
    body["owner_authenticator"] = signing_key.sign(
        canonical_bytes(body)
    ).hex()
    return body


def verify_owner_response(
    *,
    response: dict[str, Any],
    request: dict[str, Any],
    public_case: dict[str, Any],
    expected_owner: str,
    expected_state_version: str,
    expected_policy_version: str,
    expected_policy_head: str,
    expected_proposal_sha256: str | None,
    expected_operation_id: str | None,
) -> dict[str, Any]:
    body = copy.deepcopy(response)
    authenticator = body.pop("owner_authenticator", None)
    try:
        key = Ed25519PublicKey.from_public_bytes(
            bytes.fromhex(public_case["owner_endpoint_verification_key"])
        )
        key.verify(bytes.fromhex(authenticator or ""), canonical_bytes(body))
    except (InvalidSignature, ValueError, TypeError):
        raise ValueError("OWNER_RESPONSE_AUTHENTICATOR_INVALID") from None
    claimed = body.pop("response_sha256", None)
    if claimed != sha256(body):
        raise ValueError("OWNER_RESPONSE_TAMPER")
    task = public_case["task"]
    checks = {
        "OWNER_IDENTITY_MISMATCH": response.get("owner_identity") == expected_owner,
        "OWNER_STATE_VERSION_STALE": (
            response.get("owner_state_version") == expected_state_version
        ),
        "OWNER_POLICY_VERSION_STALE": (
            response.get("owner_policy_version") == expected_policy_version
        ),
        "OWNER_POLICY_HEAD_STALE": (
            response.get("owner_policy_head") == expected_policy_head
        ),
        "OWNER_EPISODE_TRANSPLANT": (
            response.get("episode_handle") == public_case["episode_handle"]
        ),
        "OWNER_Q_TRANSPLANT": response.get("q_version") == task["q_version"],
        "OWNER_WRONG_TARGET": response.get("object_id") == object_id(task),
        "OWNER_REQUEST_TRANSPLANT": (
            response.get("request_sha256") == sha256(request)
        ),
        "OWNER_REQUEST_NONCE_TRANSPLANT": (
            response.get("request_nonce") == request.get("request_nonce")
        ),
        "OWNER_RESPONSE_NONCE_INVALID": (
            response.get("response_nonce")
            == sha256(
                {
                    "request_nonce": request.get("request_nonce"),
                    "owner_identity": response.get("owner_identity"),
                    "issued_at": response.get("issued_at"),
                }
            )[:32]
        ),
        "OWNER_PROPOSAL_TRANSPLANT": (
            response.get("proposal_sha256") == expected_proposal_sha256
        ),
        "OWNER_OPERATION_TRANSPLANT": (
            response.get("operation_id")
            == (
                response.get("payload", {}).get("operation_id")
                if expected_operation_id == "__PAYLOAD__"
                else expected_operation_id
            )
        ),
        "OWNER_ISSUED_AT_INVALID": bool(
            re.fullmatch(r"T0\+\d{3}ms", str(response.get("issued_at", "")))
        ),
        "OWNER_ISSUED_AT_BINDING_INVALID": (
            isinstance(response.get("issued_at_ms"), int)
            and response.get("issued_at")
            == f'T0+{response["issued_at_ms"]:03d}ms'
        ),
        "OWNER_RESPONSE_STALE": (
            isinstance(response.get("issued_at_ms"), int)
            and request.get("sent_at_ms")
            <= response["issued_at_ms"]
            <= request.get("response_deadline_ms")
        ),
    }
    for code, valid in checks.items():
        if not valid:
            raise ValueError(code)
    payload = response.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("OWNER_RESPONSE_PAYLOAD_INVALID")
    return copy.deepcopy(payload)


def write_message(stream: Any, value: dict[str, Any]) -> None:
    stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    stream.flush()


def write_raw_message(stream: Any, raw_line: str) -> None:
    if not raw_line.endswith("\n"):
        raise ValueError("raw protocol message must include newline")
    stream.write(raw_line)
    stream.flush()


def raw_line_sha256(raw_line: str) -> str:
    return hashlib.sha256(raw_line.encode("utf-8")).hexdigest()


def read_raw_message(stream: Any) -> tuple[str, dict[str, Any]]:
    line = stream.readline()
    if not line:
        raise EOFError("protocol peer closed")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("protocol message must be an object")
    return line, value


def read_message(stream: Any) -> dict[str, Any]:
    return read_raw_message(stream)[1]
