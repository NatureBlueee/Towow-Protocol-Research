"""Canonical-byte capability API to five isolated synthetic owner processes."""

from __future__ import annotations

import multiprocessing
import os
import secrets
from dataclasses import dataclass
from multiprocessing.connection import Connection
from typing import Any

from owner_process import OWNER_IDS, owner_worker
from wire import (
    GENESIS_HEAD,
    WireProtocolError,
    canonical_bytes,
    canonical_hash,
    decode_canonical,
    make_request,
    native_ledger_entry,
    read_response,
)


class OwnerUnavailable(RuntimeError):
    pass


@dataclass
class ApiReceipt:
    sequence: int
    session_id: str
    request_id: str
    request_nonce: str
    request_ordinal: int
    owner_id: str
    owner_process_id: int
    endpoint: str
    request: dict[str, Any]
    response: Any
    request_bytes: str
    response_bytes: str
    request_hash: str
    response_hash: str
    previous_ledger_head: str
    native_ledger_head: str
    native_ledger_length: int
    native_state_head: str
    native_payload_hash: str
    consumed: bool = False
    verified: bool = True
    rejection_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "request_nonce": self.request_nonce,
            "request_ordinal": self.request_ordinal,
            "owner_id": self.owner_id,
            "owner_process_id": self.owner_process_id,
            "endpoint": self.endpoint,
            "request": self.request,
            "response": self.response,
            "request_bytes": self.request_bytes,
            "response_bytes": self.response_bytes,
            "request_hash": self.request_hash,
            "response_hash": self.response_hash,
            "previous_ledger_head": self.previous_ledger_head,
            "native_ledger_head": self.native_ledger_head,
            "native_ledger_length": self.native_ledger_length,
            "native_state_head": self.native_state_head,
            "native_payload_hash": self.native_payload_hash,
            "consumed": self.consumed,
            "verified": self.verified,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True)
class VerifiedOwnerResponse:
    payload: Any
    receipt: ApiReceipt


@dataclass(frozen=True)
class FrozenApiReceipt:
    sequence: int
    session_id: str
    request_id: str
    nonce: str
    ordinal: int
    owner_id: str
    owner_process_id: int
    endpoint: str
    request: dict[str, Any]
    response: Any
    request_bytes: str
    response_bytes: str
    raw_request_bytes: bytes
    raw_response_bytes: bytes
    request_hash: str
    response_hash: str
    previous_ledger_head: str
    native_ledger_head: str
    native_ledger_length: int
    native_state_head: str
    native_payload_hash: str
    consumed: bool
    verified: bool
    rejection_reason: str | None


@dataclass(frozen=True)
class TraceClosure:
    schema_version: str
    session_id: str
    plan_sha256: str
    result_sha256: str
    owner_process_ids: dict[str, int]
    receipts: tuple[FrozenApiReceipt, ...]
    receipt_count: int
    trace_head: str
    native_ledger_heads: dict[str, str]
    native_ledger_lengths: dict[str, int]


class OwnerClient:
    """Method-visible RPC surface.

    The client holds only five public RPC connections and their operating-system
    process IDs.  It has no callable, scenario/world reference, owner state, or
    admin/snapshot connection.
    """

    __slots__ = (
        "_channels",
        "_process_ids",
        "_session_id",
        "_sequence",
        "_trace",
        "_registered",
        "_last_ledger_heads",
        "_ledger_lengths",
        "_owner_instance_ids",
        "_client_pid",
    )

    def __init__(
        self,
        channels: dict[str, Connection],
        process_ids: dict[str, int],
        session_id: str | None = None,
    ) -> None:
        if set(channels) != set(OWNER_IDS):
            raise ValueError("EXACT_FIVE_OWNER_CHANNELS_REQUIRED")
        if len(set(process_ids.values())) != len(OWNER_IDS):
            raise ValueError("OWNER_PROCESSES_NOT_DISTINCT")
        self._channels = dict(channels)
        self._process_ids = dict(process_ids)
        self._session_id = session_id or secrets.token_hex(16)
        self._sequence = 0
        self._trace: list[ApiReceipt] = []
        self._registered: dict[str, ApiReceipt] = {}
        self._client_pid = os.getpid()
        self._owner_instance_ids = {
            owner_id: canonical_hash(canonical_bytes({
                "owner_id": owner_id,
                "session_id": self._session_id,
                "process_id": process_ids[owner_id],
            }))
            for owner_id in OWNER_IDS
        }
        self._last_ledger_heads = {
            owner_id: GENESIS_HEAD for owner_id in OWNER_IDS
        }
        self._ledger_lengths = {owner_id: 0 for owner_id in OWNER_IDS}

    def _assert_current_process(self) -> None:
        if os.getpid() != self._client_pid:
            raise WireProtocolError("OWNER_CLIENT_PROCESS_DRIFT")

    def _invoke(self, owner: str, endpoint: str, **payload: Any) -> bytes:
        self._assert_current_process()
        self._sequence += 1
        nonce = secrets.token_hex(16)
        request_id = f"{self._session_id}:{self._sequence}"
        request = make_request(
            owner,
            endpoint,
            payload,
            request_id=request_id,
            session_id=self._session_id,
            nonce=nonce,
            ordinal=self._sequence,
            client_pid=self._client_pid,
        )
        channel = self._channels[owner]
        response = b""
        envelope: dict[str, Any] | None = None
        native: dict[str, Any] | None = None
        native_chain_valid = False
        expected_previous = self._last_ledger_heads[owner]
        expected_length = self._ledger_lengths[owner] + 1
        expected_ledger_head = GENESIS_HEAD
        declared_native_payload_hash = ""
        try:
            channel.send_bytes(request)
            response = channel.recv_bytes()
            envelope = read_response(
                response,
                expected_owner=owner,
                expected_endpoint=endpoint,
                expected_request_hash=canonical_hash(request),
                expected_process_id=self._process_ids[owner],
                expected_session_id=self._session_id,
                expected_request_id=request_id,
                expected_nonce=nonce,
                expected_ordinal=self._sequence,
                expected_owner_instance_id=self._owner_instance_ids[owner],
                expected_client_pid=self._client_pid,
            )
            native = envelope["native_attestation"]
            if native.get("previous_ledger_head") != expected_previous:
                raise WireProtocolError("NATIVE_LEDGER_PREVIOUS_HEAD_MISMATCH")
            if native.get("ledger_length") != expected_length:
                raise WireProtocolError("NATIVE_LEDGER_LENGTH_MISMATCH")
            expected_native_fields = {
                "owner_id": owner,
                "endpoint": endpoint,
                "session_id": self._session_id,
                "process_id": self._process_ids[owner],
                "request_id": request_id,
                "request_sha256": canonical_hash(request),
                "request_nonce": nonce,
                "request_ordinal": self._sequence,
            }
            if any(
                native.get(key) != expected
                for key, expected in expected_native_fields.items()
            ):
                raise WireProtocolError("NATIVE_ATTESTATION_CONTEXT_MISMATCH")
            declared_native_payload_hash = native.get(
                "native_payload_sha256", ""
            )
            entry = native_ledger_entry(
                owner_id=owner,
                endpoint=endpoint,
                session_id=self._session_id,
                process_id=self._process_ids[owner],
                owner_instance_id=self._owner_instance_ids[owner],
                client_pid=self._client_pid,
                request_id=request_id,
                request_sha256=canonical_hash(request),
                request_nonce=nonce,
                request_ordinal=self._sequence,
                previous_ledger_head=expected_previous,
                ledger_length=expected_length,
                state_head_before=native.get("state_head_before"),
                state_head=native.get("state_head"),
                native_payload_sha256=declared_native_payload_hash,
                native_record_refs=native.get("native_record_refs", []),
            )
            expected_ledger_head = canonical_hash(canonical_bytes(entry))
            if native.get("ledger_head") != expected_ledger_head:
                raise WireProtocolError("NATIVE_LEDGER_HEAD_MISMATCH")
            native_chain_valid = True
            payload_hash = canonical_hash(canonical_bytes(
                envelope.get("payload")
            ))
            if declared_native_payload_hash != payload_hash:
                raise WireProtocolError(
                    "RESPONSE_PAYLOAD_NOT_NATIVE_DISPATCH_OUTPUT"
                )
        except WireProtocolError as exc:
            if native_chain_valid and envelope is not None and native is not None:
                rejected = ApiReceipt(
                    sequence=self._sequence,
                    session_id=self._session_id,
                    request_id=request_id,
                    request_nonce=nonce,
                    request_ordinal=self._sequence,
                    owner_id=owner,
                    owner_process_id=self._process_ids[owner],
                    endpoint=endpoint,
                    request=decode_canonical(request)["payload"],
                    response=envelope.get("payload"),
                    request_bytes=request.decode("utf-8"),
                    response_bytes=response.decode("utf-8"),
                    request_hash=canonical_hash(request),
                    response_hash=canonical_hash(response),
                    previous_ledger_head=expected_previous,
                    native_ledger_head=expected_ledger_head,
                    native_ledger_length=expected_length,
                    native_state_head=native["state_head"],
                    native_payload_hash=declared_native_payload_hash,
                    consumed=False,
                    verified=False,
                    rejection_reason=str(exc),
                )
                self._last_ledger_heads[owner] = expected_ledger_head
                self._ledger_lengths[owner] = expected_length
                self._trace.append(rejected)
            raise
        except (EOFError, BrokenPipeError, OSError) as exc:
            raise OwnerUnavailable(f"{owner}.{endpoint}:{type(exc).__name__}") from exc

        receipt = ApiReceipt(
            sequence=self._sequence,
            session_id=self._session_id,
            request_id=request_id,
            request_nonce=nonce,
            request_ordinal=self._sequence,
            owner_id=owner,
            owner_process_id=self._process_ids[owner],
            endpoint=endpoint,
            request=decode_canonical(request)["payload"],
            response=envelope.get("payload"),
            request_bytes=request.decode("utf-8"),
            response_bytes=response.decode("utf-8"),
            request_hash=canonical_hash(request),
            response_hash=canonical_hash(response),
            previous_ledger_head=expected_previous,
            native_ledger_head=expected_ledger_head,
            native_ledger_length=expected_length,
            native_state_head=native["state_head"],
            native_payload_hash=declared_native_payload_hash,
        )
        self._last_ledger_heads[owner] = expected_ledger_head
        self._ledger_lengths[owner] = expected_length
        self._trace.append(receipt)
        self._registered[receipt.response_hash] = receipt
        payload_value = envelope.get("payload")
        if isinstance(payload_value, dict) and "error" in payload_value:
            raise OwnerUnavailable(
                f"{owner}.{endpoint}:{payload_value['error']}"
            )
        return response

    def consume_response(
        self,
        value: bytes,
        *,
        owner_id: str,
        endpoint: str,
        min_sequence: int = 0,
    ) -> VerifiedOwnerResponse:
        """Consume a response registered by this exact current client.

        Merely having canonical owner-shaped bytes is insufficient.  The bytes
        must have passed ``_invoke`` in this session, for this endpoint, and may
        be consumed only once by the method.
        """
        if not isinstance(self, OwnerClient):
            raise WireProtocolError("CURRENT_OWNER_CLIENT_REQUIRED")
        self._assert_current_process()
        response_hash = canonical_hash(value)
        receipt = self._registered.get(response_hash)
        if receipt is None:
            raise WireProtocolError("DETACHED_OR_CROSS_SESSION_RESPONSE")
        if receipt.response_bytes.encode("utf-8") != value:
            raise WireProtocolError("REGISTERED_RESPONSE_BYTES_MISMATCH")
        if receipt.owner_id != owner_id or receipt.endpoint != endpoint:
            raise WireProtocolError("REGISTERED_RESPONSE_CONTEXT_MISMATCH")
        if receipt.sequence <= min_sequence:
            raise WireProtocolError("STALE_RESPONSE_BEFORE_CURRENT_RUN")
        if receipt.consumed:
            raise WireProtocolError("RESPONSE_ALREADY_CONSUMED")
        envelope = read_response(
            value,
            expected_owner=owner_id,
            expected_endpoint=endpoint,
            expected_request_hash=receipt.request_hash,
            expected_process_id=receipt.owner_process_id,
            expected_session_id=self._session_id,
            expected_request_id=receipt.request_id,
            expected_nonce=receipt.request_nonce,
            expected_ordinal=receipt.request_ordinal,
            expected_owner_instance_id=self._owner_instance_ids[owner_id],
            expected_client_pid=self._client_pid,
        )
        receipt.consumed = True
        return VerifiedOwnerResponse(envelope["payload"], receipt)

    def freeze_closure(self) -> dict[str, Any]:
        self._assert_current_process()
        receipts = [receipt.as_dict() for receipt in self._trace]
        trace_head = GENESIS_HEAD
        for receipt in receipts:
            trace_receipt = {
                key: value for key, value in receipt.items()
                if key not in {"raw_request_bytes", "raw_response_bytes"}
            }
            trace_head = canonical_hash(canonical_bytes({
                "previous_trace_head": trace_head,
                "receipt": trace_receipt,
            }))
        return {
            "schema_version": "G6_FROZEN_RECEIPT_CLOSURE_V2",
            "session_id": self._session_id,
            "owner_process_ids": dict(self._process_ids),
            "receipt_count": len(receipts),
            "receipts": receipts,
            "trace_head": trace_head,
            "native_ledger_heads": dict(self._last_ledger_heads),
            "native_ledger_lengths": dict(self._ledger_lengths),
        }

    def freeze_trace_closure(
        self,
        plan_sha256: str,
        result_sha256: str,
    ) -> TraceClosure:
        closure = self.freeze_closure()
        frozen_receipts = tuple(
            FrozenApiReceipt(
                sequence=receipt.sequence,
                session_id=receipt.session_id,
                request_id=receipt.request_id,
                nonce=receipt.request_nonce,
                ordinal=receipt.request_ordinal,
                owner_id=receipt.owner_id,
                owner_process_id=receipt.owner_process_id,
                endpoint=receipt.endpoint,
                request=receipt.request,
                response=receipt.response,
                request_bytes=receipt.request_bytes,
                response_bytes=receipt.response_bytes,
                raw_request_bytes=receipt.request_bytes.encode("utf-8"),
                raw_response_bytes=receipt.response_bytes.encode("utf-8"),
                request_hash=receipt.request_hash,
                response_hash=receipt.response_hash,
                previous_ledger_head=receipt.previous_ledger_head,
                native_ledger_head=receipt.native_ledger_head,
                native_ledger_length=receipt.native_ledger_length,
                native_state_head=receipt.native_state_head,
                native_payload_hash=receipt.native_payload_hash,
                consumed=receipt.consumed,
                verified=receipt.verified,
                rejection_reason=receipt.rejection_reason,
            )
            for receipt in self._trace
        )
        return TraceClosure(
            schema_version="G6_FROZEN_TRACE_CLOSURE_V2",
            session_id=self._session_id,
            plan_sha256=plan_sha256,
            result_sha256=result_sha256,
            owner_process_ids=dict(self._process_ids),
            receipts=frozen_receipts,
            receipt_count=len(frozen_receipts),
            trace_head=closure["trace_head"],
            native_ledger_heads=closure["native_ledger_heads"],
            native_ledger_lengths=closure["native_ledger_lengths"],
        )

    def authority(self, operation_id: str) -> bytes:
        return self._invoke("O_S", "authority", operation_id=operation_id)

    def execute(self, operation_id: str) -> bytes:
        return self._invoke("O_E", "execute", operation_id=operation_id)

    def effects(self, operation_id: str) -> bytes:
        return self._invoke("O_E", "effects", operation_id=operation_id)

    def recover(self, occurrence_id: str) -> bytes:
        return self._invoke("O_E", "recover", occurrence_id=occurrence_id)

    def recovery_state(self, occurrence_id: str) -> bytes:
        return self._invoke(
            "O_E", "recovery_state", occurrence_id=occurrence_id
        )

    def target_state(self, object_id: str) -> bytes:
        return self._invoke("O_E", "target_state", object_id=object_id)

    def adoption(
        self,
        effect: dict[str, Any],
        episode_id: str,
    ) -> bytes:
        return self._invoke(
            "O_V", "adoption", effect=effect, episode_id=episode_id
        )

    def acceptance(
        self,
        effect: dict[str, Any],
        owner_id: str,
        episode_id: str,
        q_version: str,
    ) -> bytes:
        return self._invoke(
            owner_id,
            "acceptance",
            effect=effect,
            episode_id=episode_id,
            q_version=q_version,
        )

    def open_settlement(
        self,
        effect: dict[str, Any],
        acceptances: list[dict[str, Any]],
    ) -> bytes:
        return self._invoke(
            "O_P",
            "open_settlement",
            effect=effect,
            acceptances=acceptances,
        )

    def settlement_state(
        self,
        obligation_id: str,
        effect_id: str,
    ) -> bytes:
        return self._invoke(
            "O_P",
            "settlement_state",
            obligation_id=obligation_id,
            effect_id=effect_id,
        )

    def episode_status(self, episode_id: str, q_version: str) -> bytes:
        return self._invoke(
            "O_Q",
            "episode_status",
            episode_id=episode_id,
            q_version=q_version,
        )

    @property
    def trace(self) -> tuple[ApiReceipt, ...]:
        return tuple(self._trace)

    @property
    def owner_process_ids(self) -> dict[str, int]:
        return dict(self._process_ids)

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def sequence(self) -> int:
        return self._sequence


class OwnerSession:
    """Runner-side lifecycle and admin surface, never passed to the method."""

    def __init__(self, scenario) -> None:
        self._scenario = scenario
        self._processes: dict[str, multiprocessing.Process] = {}
        self._admins: dict[str, Connection] = {}
        self.client: OwnerClient | None = None
        self._closed = False
        self._session_id = secrets.token_hex(16)

    def __enter__(self) -> "OwnerSession":
        context = multiprocessing.get_context("spawn")
        rpc_channels: dict[str, Connection] = {}
        process_ids: dict[str, int] = {}
        for owner_id, state in self._scenario.owner_states().items():
            rpc_parent, rpc_child = context.Pipe(duplex=True)
            admin_parent, admin_child = context.Pipe(duplex=True)
            process = context.Process(
                target=owner_worker,
                args=(
                    owner_id,
                    state,
                    rpc_child,
                    admin_child,
                    self._session_id,
                ),
                name=f"g6-{owner_id}",
            )
            process.start()
            rpc_child.close()
            admin_child.close()
            self._processes[owner_id] = process
            self._admins[owner_id] = admin_parent
            rpc_channels[owner_id] = rpc_parent
        for owner_id, process in self._processes.items():
            admin_parent = self._admins[owner_id]
            ready = decode_canonical(admin_parent.recv_bytes())
            if (
                ready.get("kind") != "OWNER_READY_V2"
                or ready.get("owner_id") != owner_id
                or ready.get("process_id") != process.pid
                or ready.get("session_id") != self._session_id
            ):
                raise RuntimeError(f"OWNER_START_FAILED:{owner_id}")
            process_ids[owner_id] = process.pid
        self.client = OwnerClient(
            rpc_channels, process_ids, session_id=self._session_id
        )
        return self

    def snapshots(self) -> dict[str, dict[str, Any]]:
        values = {}
        for owner_id, admin in self._admins.items():
            admin.send_bytes(canonical_bytes({"command": "SNAPSHOT"}))
            values[owner_id] = decode_canonical(admin.recv_bytes())
        return values

    def freeze_closure(
        self,
        plan_sha256: str,
        result_sha256: str,
    ) -> TraceClosure:
        if self.client is None:
            raise RuntimeError("OWNER_SESSION_NOT_STARTED")
        return self.client.freeze_trace_closure(
            plan_sha256, result_sha256
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for admin in self._admins.values():
            try:
                admin.send_bytes(canonical_bytes({"command": "SHUTDOWN"}))
            except (BrokenPipeError, OSError):
                pass
        for admin in self._admins.values():
            try:
                admin.recv_bytes()
            except (EOFError, OSError):
                pass
        for process in self._processes.values():
            process.join(timeout=2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
        if self.client is not None:
            for channel in self.client._channels.values():
                channel.close()
        for admin in self._admins.values():
            admin.close()

    def __exit__(self, _exc_type, _exc, _tb) -> None:
        self.close()


def start_owner_session(scenario) -> OwnerSession:
    return OwnerSession(scenario)


def response_payload(
    value: bytes,
    *,
    owner_id: str,
    endpoint: str,
) -> Any:
    """Detached payload decoding is intentionally not an evidence API."""
    raise WireProtocolError("CURRENT_OWNER_CLIENT_REQUIRED")


def verified_acceptance_payload(
    value: bytes,
    *,
    owner_id: str,
) -> tuple[dict[str, Any], int]:
    """Detached Acceptance decoding is intentionally not an evidence API."""
    raise WireProtocolError("CURRENT_OWNER_CLIENT_REQUIRED")


def verify_frozen_closure(
    closure: Any,
) -> tuple[bool, dict[str, dict[str, Any]]]:
    """Recompute a frozen receipt/native-ledger closure from raw bytes."""
    if isinstance(closure, TraceClosure):
        closure = {
            "schema_version": "G6_FROZEN_RECEIPT_CLOSURE_V2",
            "session_id": closure.session_id,
            "owner_process_ids": closure.owner_process_ids,
            "receipt_count": closure.receipt_count,
            "receipts": [
                {
                    "sequence": item.sequence,
                    "session_id": item.session_id,
                    "request_id": item.request_id,
                    "request_nonce": item.nonce,
                    "request_ordinal": item.ordinal,
                    "owner_id": item.owner_id,
                    "owner_process_id": item.owner_process_id,
                    "endpoint": item.endpoint,
                    "request": item.request,
                    "response": item.response,
                    "request_bytes": item.request_bytes,
                    "response_bytes": item.response_bytes,
                    "raw_request_bytes": item.raw_request_bytes,
                    "raw_response_bytes": item.raw_response_bytes,
                    "request_hash": item.request_hash,
                    "response_hash": item.response_hash,
                    "previous_ledger_head": item.previous_ledger_head,
                    "native_ledger_head": item.native_ledger_head,
                    "native_ledger_length": item.native_ledger_length,
                    "native_state_head": item.native_state_head,
                    "native_payload_hash": item.native_payload_hash,
                    "consumed": item.consumed,
                    "verified": item.verified,
                    "rejection_reason": item.rejection_reason,
                }
                for item in closure.receipts
            ],
            "trace_head": closure.trace_head,
            "native_ledger_heads": closure.native_ledger_heads,
            "native_ledger_lengths": closure.native_ledger_lengths,
        }
    global _LAST_CLOSURE_ERROR
    _LAST_CLOSURE_ERROR = ""
    if not isinstance(closure, dict):
        _LAST_CLOSURE_ERROR = "CLOSURE_NOT_OBJECT"
        return False, {}
    if closure.get("schema_version") != "G6_FROZEN_RECEIPT_CLOSURE_V2":
        _LAST_CLOSURE_ERROR = "CLOSURE_SCHEMA_MISMATCH"
        return False, {}
    session_id = closure.get("session_id")
    process_ids = closure.get("owner_process_ids")
    receipts = closure.get("receipts")
    if (
        not isinstance(session_id, str)
        or not session_id
        or not isinstance(process_ids, dict)
        or set(process_ids) != set(OWNER_IDS)
        or len(set(process_ids.values())) != len(OWNER_IDS)
        or not all(isinstance(value, int) and value > 0 for value in process_ids.values())
        or not isinstance(receipts, list)
        or closure.get("receipt_count") != len(receipts)
    ):
        _LAST_CLOSURE_ERROR = "CLOSURE_HEADER_INVALID"
        return False, {}

    ledger_heads = {owner: GENESIS_HEAD for owner in OWNER_IDS}
    ledger_lengths = {owner: 0 for owner in OWNER_IDS}
    receipt_map: dict[str, dict[str, Any]] = {}
    trace_head = GENESIS_HEAD
    try:
        for sequence, receipt in enumerate(receipts, 1):
            if not isinstance(receipt, dict) or receipt.get("sequence") != sequence:
                raise WireProtocolError("RECEIPT_SEQUENCE_MISMATCH")
            owner = receipt["owner_id"]
            endpoint = receipt["endpoint"]
            raw_request = receipt.get("raw_request_bytes")
            raw_response = receipt.get("raw_response_bytes")
            request_bytes = (
                raw_request
                if isinstance(raw_request, bytes)
                else receipt["request_bytes"].encode("utf-8")
            )
            response_bytes = (
                raw_response
                if isinstance(raw_response, bytes)
                else receipt["response_bytes"].encode("utf-8")
            )
            if (
                request_bytes != receipt["request_bytes"].encode("utf-8")
                or response_bytes != receipt["response_bytes"].encode("utf-8")
            ):
                raise WireProtocolError("FROZEN_RAW_BYTES_MISMATCH")
            if canonical_hash(request_bytes) != receipt["request_hash"]:
                raise WireProtocolError("FROZEN_REQUEST_HASH_MISMATCH")
            if canonical_hash(response_bytes) != receipt["response_hash"]:
                raise WireProtocolError("FROZEN_RESPONSE_HASH_MISMATCH")
            request = decode_canonical(request_bytes)
            if (
                request.get("kind") != "OWNER_REQUEST_V2"
                or request.get("owner_id") != owner
                or request.get("endpoint") != endpoint
                or request.get("session_id") != session_id
                or request.get("request_id") != receipt["request_id"]
                or request.get("nonce") != receipt["request_nonce"]
                or request.get("ordinal") != receipt["request_ordinal"]
                or request.get("payload") != receipt["request"]
            ):
                raise WireProtocolError("FROZEN_REQUEST_CONTEXT_MISMATCH")
            response = read_response(
                response_bytes,
                expected_owner=owner,
                expected_endpoint=endpoint,
                expected_request_hash=receipt["request_hash"],
                expected_process_id=process_ids[owner],
                expected_session_id=session_id,
                expected_request_id=receipt["request_id"],
                expected_nonce=receipt["request_nonce"],
                expected_ordinal=receipt["request_ordinal"],
                expected_owner_instance_id=canonical_hash(canonical_bytes({
                    "owner_id": owner,
                    "session_id": session_id,
                    "process_id": process_ids[owner],
                })),
                expected_client_pid=request["client_pid"],
            )
            if response.get("payload") != receipt.get("response"):
                raise WireProtocolError("FROZEN_RESPONSE_PAYLOAD_MISMATCH")
            native = response["native_attestation"]
            expected_length = ledger_lengths[owner] + 1
            expected_previous = ledger_heads[owner]
            payload_hash = canonical_hash(canonical_bytes(response["payload"]))
            entry = native_ledger_entry(
                owner_id=owner,
                endpoint=endpoint,
                session_id=session_id,
                process_id=process_ids[owner],
                owner_instance_id=response["owner_instance_id"],
                client_pid=request["client_pid"],
                request_id=receipt["request_id"],
                request_sha256=receipt["request_hash"],
                request_nonce=receipt["request_nonce"],
                request_ordinal=receipt["request_ordinal"],
                previous_ledger_head=expected_previous,
                ledger_length=expected_length,
                state_head_before=native.get("state_head_before"),
                state_head=native.get("state_head"),
                native_payload_sha256=payload_hash,
                native_record_refs=native.get("native_record_refs", []),
            )
            ledger_head = canonical_hash(canonical_bytes(entry))
            if any((
                native.get("previous_ledger_head") != expected_previous,
                native.get("ledger_length") != expected_length,
                native.get("native_payload_sha256") != payload_hash,
                native.get("ledger_head") != ledger_head,
                receipt.get("previous_ledger_head") != expected_previous,
                receipt.get("native_ledger_head") != ledger_head,
                receipt.get("native_ledger_length") != expected_length,
                receipt.get("native_state_head") != native.get("state_head"),
                receipt.get("native_payload_hash") != payload_hash,
            )):
                raise WireProtocolError("FROZEN_NATIVE_LEDGER_MISMATCH")
            ledger_heads[owner] = ledger_head
            ledger_lengths[owner] = expected_length
            if receipt["response_hash"] in receipt_map:
                raise WireProtocolError("DUPLICATE_FROZEN_RESPONSE")
            receipt_map[receipt["response_hash"]] = receipt
            trace_receipt = {
                key: value for key, value in receipt.items()
                if key not in {"raw_request_bytes", "raw_response_bytes"}
            }
            trace_head = canonical_hash(canonical_bytes({
                "previous_trace_head": trace_head,
                "receipt": trace_receipt,
            }))
    except (KeyError, TypeError, ValueError, WireProtocolError) as exc:
        _LAST_CLOSURE_ERROR = f"{type(exc).__name__}:{exc}"
        return False, {}

    if (
        trace_head != closure.get("trace_head")
        or ledger_heads != closure.get("native_ledger_heads")
        or ledger_lengths != closure.get("native_ledger_lengths")
    ):
        mismatches = []
        if trace_head != closure.get("trace_head"):
            mismatches.append("TRACE_HEAD")
        if ledger_heads != closure.get("native_ledger_heads"):
            mismatches.append("NATIVE_LEDGER_HEADS")
        if ledger_lengths != closure.get("native_ledger_lengths"):
            mismatches.append("NATIVE_LEDGER_LENGTHS")
        _LAST_CLOSURE_ERROR = (
            "CLOSURE_FINAL_HEAD_MISMATCH:" + ",".join(mismatches)
        )
        return False, {}
    return True, receipt_map


_LAST_CLOSURE_ERROR = ""


def last_closure_error() -> str:
    return _LAST_CLOSURE_ERROR
