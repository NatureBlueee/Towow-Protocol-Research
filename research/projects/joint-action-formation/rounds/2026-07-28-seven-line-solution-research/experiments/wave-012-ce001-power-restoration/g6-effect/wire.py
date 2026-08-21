"""Canonical byte protocol shared by owner processes and the method client.

V2 makes response currentness part of the wire contract.  A response is not
just an owner-shaped payload: it is bound to the exact canonical request,
session, process, nonce, ordinal, and the worker's post-dispatch native ledger
entry.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from model import _jsonable


class WireProtocolError(ValueError):
    pass


GENESIS_HEAD = "0" * 64


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def canonical_hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def decode_canonical(value: bytes) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WireProtocolError("INVALID_JSON_BYTES") from exc
    if not isinstance(decoded, dict):
        raise WireProtocolError("WIRE_ROOT_NOT_OBJECT")
    if canonical_bytes(decoded) != value:
        raise WireProtocolError("NON_CANONICAL_JSON")
    return decoded


def make_request(
    owner_id: str,
    endpoint: str,
    payload: dict[str, Any],
    request_id: str,
    *,
    session_id: str,
    nonce: str,
    ordinal: int,
    client_pid: int,
) -> bytes:
    return canonical_bytes({
        "kind": "OWNER_REQUEST_V2",
        "owner_id": owner_id,
        "endpoint": endpoint,
        "request_id": request_id,
        "session_id": session_id,
        "nonce": nonce,
        "ordinal": ordinal,
        "client_pid": client_pid,
        "payload": payload,
    })


def read_request(
    value: bytes,
    *,
    expected_owner: str,
    allowed_endpoints: set[str],
    expected_session_id: str,
) -> dict[str, Any]:
    request = decode_canonical(value)
    if request.get("kind") != "OWNER_REQUEST_V2":
        raise WireProtocolError("WRONG_REQUEST_KIND")
    if request.get("owner_id") != expected_owner:
        raise WireProtocolError("WRONG_REQUEST_OWNER")
    if request.get("endpoint") not in allowed_endpoints:
        raise WireProtocolError("ENDPOINT_NOT_ALLOWED")
    if request.get("session_id") != expected_session_id:
        raise WireProtocolError("WRONG_REQUEST_SESSION")
    if not isinstance(request.get("request_id"), str):
        raise WireProtocolError("REQUEST_ID_MISSING")
    if not isinstance(request.get("nonce"), str) or not request["nonce"]:
        raise WireProtocolError("REQUEST_NONCE_MISSING")
    if not isinstance(request.get("ordinal"), int) or request["ordinal"] <= 0:
        raise WireProtocolError("REQUEST_ORDINAL_INVALID")
    if not isinstance(request.get("client_pid"), int) or request["client_pid"] <= 0:
        raise WireProtocolError("REQUEST_CLIENT_PID_INVALID")
    if not isinstance(request.get("payload"), dict):
        raise WireProtocolError("REQUEST_PAYLOAD_NOT_OBJECT")
    return request


def native_ledger_entry(
    *,
    owner_id: str,
    endpoint: str,
    session_id: str,
    process_id: int,
    owner_instance_id: str,
    client_pid: int,
    request_id: str,
    request_sha256: str,
    request_nonce: str,
    request_ordinal: int,
    previous_ledger_head: str,
    ledger_length: int,
    state_head_before: str,
    state_head: str,
    native_payload_sha256: str,
    native_record_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    """Canonical material committed by a worker's native ledger head."""
    return {
        "owner_id": owner_id,
        "endpoint": endpoint,
        "session_id": session_id,
        "process_id": process_id,
        "owner_instance_id": owner_instance_id,
        "client_pid": client_pid,
        "request_id": request_id,
        "request_sha256": request_sha256,
        "request_nonce": request_nonce,
        "request_ordinal": request_ordinal,
        "previous_ledger_head": previous_ledger_head,
        "ledger_length": ledger_length,
        "state_head_before": state_head_before,
        "state_head": state_head,
        "native_payload_sha256": native_payload_sha256,
        "native_record_refs": native_record_refs,
    }


def make_response(
    *,
    owner_id: str,
    endpoint: str,
    request_bytes: bytes,
    payload: Any,
    observed_at: int,
    process_id: int,
    session_id: str,
    request_id: str,
    request_nonce: str,
    request_ordinal: int,
    native_attestation: dict[str, Any],
    owner_instance_id: str,
    client_pid: int,
) -> bytes:
    native_record_refs = native_attestation["native_record_refs"]
    return canonical_bytes({
        "kind": "OWNER_RESPONSE_V2",
        "owner_id": owner_id,
        "endpoint": endpoint,
        "request_sha256": canonical_hash(request_bytes),
        "request_id": request_id,
        "session_id": session_id,
        "request_nonce": request_nonce,
        "request_ordinal": request_ordinal,
        "nonce": request_nonce,
        "ordinal": request_ordinal,
        "payload": payload,
        "observed_at": observed_at,
        "process_id": process_id,
        "owner_process_id": process_id,
        "owner_instance_id": owner_instance_id,
        "client_pid": client_pid,
        "pre_state_head": native_attestation["state_head_before"],
        "post_state_head": native_attestation["state_head"],
        "pre_ledger_head": native_attestation["previous_ledger_head"],
        "post_ledger_head": native_attestation["ledger_head"],
        "native_record_refs": native_record_refs,
        "native_attestation": native_attestation,
    })


def read_response(
    value: bytes,
    *,
    expected_owner: str,
    expected_endpoint: str,
    expected_request_hash: str | None = None,
    expected_process_id: int | None = None,
    expected_session_id: str | None = None,
    expected_request_id: str | None = None,
    expected_nonce: str | None = None,
    expected_ordinal: int | None = None,
    expected_owner_instance_id: str | None = None,
    expected_client_pid: int | None = None,
) -> dict[str, Any]:
    response = decode_canonical(value)
    if response.get("kind") != "OWNER_RESPONSE_V2":
        raise WireProtocolError("WRONG_RESPONSE_KIND")
    if response.get("owner_id") != expected_owner:
        raise WireProtocolError("WRONG_RESPONSE_OWNER")
    if response.get("endpoint") != expected_endpoint:
        raise WireProtocolError("WRONG_RESPONSE_ENDPOINT")
    if (
        expected_request_hash is not None
        and response.get("request_sha256") != expected_request_hash
    ):
        raise WireProtocolError("RESPONSE_TRANSPLANT_OR_REPLAY")
    if (
        expected_process_id is not None
        and response.get("process_id") != expected_process_id
    ):
        raise WireProtocolError("WRONG_OWNER_PROCESS")
    if (
        expected_session_id is not None
        and response.get("session_id") != expected_session_id
    ):
        raise WireProtocolError("RESPONSE_SESSION_REPLAY")
    if (
        expected_request_id is not None
        and response.get("request_id") != expected_request_id
    ):
        raise WireProtocolError("RESPONSE_REQUEST_ID_MISMATCH")
    if (
        expected_nonce is not None
        and response.get("request_nonce") != expected_nonce
    ):
        raise WireProtocolError("RESPONSE_NONCE_MISMATCH")
    if (
        expected_ordinal is not None
        and (
            response.get("request_ordinal") != expected_ordinal
            or response.get("ordinal") != expected_ordinal
        )
    ):
        raise WireProtocolError("RESPONSE_ORDINAL_MISMATCH")
    if (
        expected_nonce is not None
        and response.get("nonce") != expected_nonce
    ):
        raise WireProtocolError("RESPONSE_NONCE_ALIAS_MISMATCH")
    if (
        expected_process_id is not None
        and response.get("owner_process_id") != expected_process_id
    ):
        raise WireProtocolError("WRONG_OWNER_PROCESS_ALIAS")
    if (
        expected_owner_instance_id is not None
        and response.get("owner_instance_id") != expected_owner_instance_id
    ):
        raise WireProtocolError("WRONG_OWNER_INSTANCE")
    if (
        expected_client_pid is not None
        and response.get("client_pid") != expected_client_pid
    ):
        raise WireProtocolError("WRONG_CLIENT_PROCESS")
    if not isinstance(response.get("native_attestation"), dict):
        raise WireProtocolError("NATIVE_ATTESTATION_MISSING")
    native = response["native_attestation"]
    aliases = {
        "pre_state_head": native.get("state_head_before"),
        "post_state_head": native.get("state_head"),
        "pre_ledger_head": native.get("previous_ledger_head"),
        "post_ledger_head": native.get("ledger_head"),
        "native_record_refs": native.get("native_record_refs"),
    }
    if any(response.get(key) != expected for key, expected in aliases.items()):
        raise WireProtocolError("RESPONSE_NATIVE_ALIAS_MISMATCH")
    return response
