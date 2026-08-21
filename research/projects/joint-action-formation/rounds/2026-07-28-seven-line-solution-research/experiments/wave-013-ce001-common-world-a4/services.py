"""Process-private owner and target services for the CE-001 common world.

This module is runtime infrastructure, not a protocol definition.  Every
service owns its signing key and mutable state inside its child process.  The
controller receives only signed receipts and frozen native logs.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import queue
import uuid
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


OWNER_IDS = ("O_Q", "O_V", "O_R", "O_S", "O_P", "O_E")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def sign_object(private_key: Ed25519PrivateKey, value: Mapping[str, Any]) -> str:
    return private_key.sign(canonical_bytes(value)).hex()


def verify_signed(value: Mapping[str, Any], public_hex: str) -> bool:
    signature_hex = value.get("signature_hex")
    if not isinstance(signature_hex, str):
        return False
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
            bytes.fromhex(signature_hex), canonical_bytes(unsigned)
        )
    except (ValueError, InvalidSignature):
        return False
    return True


def make_request(
    *,
    owner_id: str,
    action: str,
    manifest: Mapping[str, Any],
    observed_at_minute: int,
    arguments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "action": action,
        "owner_id": owner_id,
        "run_id": manifest["run_id"],
        "world_root": manifest["world_root"],
        "arm_binding_token": manifest["arm_binding_token"],
        "q_version": manifest["q_version"],
        "object_id": manifest["object_id"],
        "operation_id": manifest["operation_id"],
        "observed_at_minute": observed_at_minute,
        "arguments": dict(arguments or {}),
    }
    raw = canonical_bytes(payload)
    return {
        "request_id": f"req-{uuid.uuid4().hex}",
        "request_nonce": uuid.uuid4().hex,
        "request_bytes": raw.decode("utf-8"),
        "request_sha256": sha256_bytes(raw),
        "payload": payload,
    }


def rpc(endpoint: Mapping[str, Any], request: Mapping[str, Any], timeout: int = 10) -> dict[str, Any]:
    endpoint["request_queue"].put(dict(request))
    response = endpoint["response_queue"].get(timeout=timeout)
    if response.get("request_id") != request.get("request_id"):
        raise RuntimeError("IPC response/request id mismatch")
    return response


def _record_hash_payload(record: Mapping[str, Any], sha_field: str) -> dict[str, Any]:
    result = dict(record)
    for key in (
        sha_field,
        "signature_hex",
        "append_index",
        "previous_head",
        "record_head",
        "state_head_before",
        "state_head_after",
    ):
        result.pop(key, None)
    return result


def _append_signed_record(
    *,
    private_key: Ed25519PrivateKey,
    base: Mapping[str, Any],
    entries: list[dict[str, Any]],
    previous_head: str,
    sha_field: str,
) -> tuple[dict[str, Any], str]:
    record = dict(base)
    record_sha = sha256_value(_record_hash_payload(record, sha_field))
    index = len(entries)
    record_head = sha256_value(
        {
            "append_index": index,
            "previous_head": previous_head,
            "record_sha256": record_sha,
        }
    )
    record.update(
        {
            sha_field: record_sha,
            "append_index": index,
            "previous_head": previous_head,
            "record_head": record_head,
            "state_head_before": previous_head,
            "state_head_after": record_head,
        }
    )
    record["signature_hex"] = sign_object(private_key, record)
    entries.append(record)
    return record, record_head


def _start_receipt(
    *,
    private_key: Ed25519PrivateKey,
    service_id: str,
    source_id: str,
    initial_head: str,
    backend_identity: Mapping[str, Any],
) -> dict[str, Any]:
    executable = pathlib.Path(__file__).resolve()
    base = {
        "service_id": service_id,
        "actual_pid": os.getpid(),
        "public_key_hex": public_key_hex(private_key),
        "state_source_id": source_id,
        "initial_state_head": initial_head,
        "start_method": "spawn",
        "executable": str(executable),
        "executable_sha256": sha256_bytes(executable.read_bytes()),
        "backend_kind": "PROCESS_PRIVATE_MEMORY",
        "backend_identity_sha256": sha256_value(backend_identity),
    }
    base["receipt_sha256"] = sha256_value(base)
    base["signature_hex"] = sign_object(private_key, base)
    return base


def _freeze_receipt(
    *,
    private_key: Ed25519PrivateKey,
    service_id: str,
    source_id: str,
    manifest: Mapping[str, Any],
    terminal_head: str,
    record_count: int,
) -> dict[str, Any]:
    receipt = {
        "service_id": service_id,
        "source_id": source_id,
        "state_source_id": source_id,
        "process_id": os.getpid(),
        "run_id": manifest["run_id"],
        "manifest_sha256": manifest["manifest_sha256"],
        "terminal_head": terminal_head,
        "record_count": record_count,
        "exit_code": 0,
    }
    receipt["receipt_sha256"] = sha256_value(receipt)
    receipt["signature_hex"] = sign_object(private_key, receipt)
    return receipt


def _validate_request(request: Mapping[str, Any], manifest: Mapping[str, Any], service_id: str) -> None:
    raw = request.get("request_bytes")
    payload = request.get("payload")
    if not isinstance(raw, str) or not isinstance(payload, Mapping):
        raise ValueError("request bytes/payload missing")
    raw_bytes = raw.encode("utf-8")
    if raw_bytes != canonical_bytes(payload):
        raise ValueError("request bytes are not exact payload bytes")
    if sha256_bytes(raw_bytes) != request.get("request_sha256"):
        raise ValueError("request digest mismatch")
    expected = {
        "owner_id": service_id,
        "run_id": manifest["run_id"],
        "world_root": manifest["world_root"],
        "arm_binding_token": manifest["arm_binding_token"],
        "q_version": manifest["q_version"],
        "object_id": manifest["object_id"],
        "operation_id": manifest["operation_id"],
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise ValueError(f"request binding mismatch: {key}")
    if not request.get("request_nonce") or not request.get("request_id"):
        raise ValueError("request identity missing")


def _owner_payload(
    owner_id: str,
    action: str,
    manifest: Mapping[str, Any],
    case_config: Mapping[str, Any],
    minute: int,
    arguments: Mapping[str, Any],
    next_state_head: str | None = None,
    epoch: int = 1,
) -> dict[str, Any]:
    binding = {
        "run_id": manifest["run_id"],
        "world_root": manifest["world_root"],
        "arm_binding_token": manifest["arm_binding_token"],
        "q_version": manifest["q_version"],
        "object_id": manifest["object_id"],
        "operation_id": manifest["operation_id"],
    }
    if action == "DISCOVER":
        return {
            **binding,
            "kind": "DISCOVERY",
            "decision": "FOUND",
            "resource_owner_id": "O_R",
            "resource_kind": "MOBILE_3KW_GENERATOR",
            "available_power_kw": 3.0,
            "issued_at_minute": minute,
            "expires_at_minute": 10,
        }
    if action == "AUTHORITY":
        configured = case_config.get("authority_decision", "GRANTED")
        decision = (
            configured
            if configured == "REFUSED"
            else {
                "O_V": "APPROVED",
                "O_R": "COMMITTED",
                "O_S": "SAFE",
            }.get(owner_id, "APPROVED")
        )
        payload = {
            **binding,
            "kind": "AUTHORITY",
            "decision": decision,
            "issued_at_minute": minute,
            "expires_at_minute": (
                manifest["deadline_minute"]
            ),
            "owner_state_head": next_state_head,
            "owner_state_epoch": epoch,
            "delegable": decision != "REFUSED",
            "authority_scope": {
                "target_id": manifest["target_id"],
                "power_kw": manifest["required_power_kw"],
                "duration_minutes": manifest["required_duration_minutes"],
            },
        }
        if decision == "REFUSED":
            payload.update(
                {
                    "refusal_code": "NON_DELEGABLE_OWNER_REFUSAL",
                    "delegable": False,
                    "non_delegable": True,
                }
            )
        return payload
    if action == "ACCEPT":
        return {
            **binding,
            "kind": "ACCEPTANCE",
            "decision": "ACCEPTED",
            "effect_digest": arguments["effect_digest"],
            "readback_event_sha256": arguments["readback_event_sha256"],
            "accepted_at_minute": minute,
        }
    if action == "FINALIZE":
        return {
            **binding,
            "kind": "FINALITY",
            "decision": "FINAL",
            "acceptance_hashes": list(arguments["acceptance_hashes"]),
            "finalized_at_minute": minute,
        }
    if action == "OBSERVE_EFFECT":
        return {
            **binding,
            "kind": "EFFECT_OBSERVATION",
            "decision": "OBSERVED",
            "effect_digest": arguments["effect_digest"],
            "readback_event_sha256": arguments["readback_event_sha256"],
            "observed_effect_at_minute": minute,
        }
    raise ValueError(f"unsupported owner action: {action}")


def owner_worker(
    owner_id: str,
    case_config: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
    control_queue: Any,
    control_response_queue: Any,
    head_update_queue: Any,
    ready_queue: Any,
) -> None:
    """Entrypoint for one process-private owner shard."""
    private_key = Ed25519PrivateKey.generate()
    source_id = f"{owner_id}-state-{uuid.uuid4().hex}"
    backend_identity = {
        "kind": "PROCESS_PRIVATE_MEMORY",
        "owner_id": owner_id,
        "pid": os.getpid(),
        "nonce": uuid.uuid4().hex,
    }
    initial_head = sha256_value(
        {"source_id": source_id, "owner_id": owner_id, "genesis": uuid.uuid4().hex}
    )
    state_head = initial_head
    epoch = 1
    entries: list[dict[str, Any]] = []
    manifest: Mapping[str, Any] | None = None
    start = _start_receipt(
        private_key=private_key,
        service_id=owner_id,
        source_id=source_id,
        initial_head=initial_head,
        backend_identity=backend_identity,
    )
    ready_queue.put(
        {
            "service_id": owner_id,
            "actual_pid": os.getpid(),
            "public_key_hex": public_key_hex(private_key),
            "state_source_id": source_id,
            "state_head_at_start": initial_head,
            "current_owner_state_epoch": epoch,
            "state_epoch_at_start": epoch,
            "backend_kind": "PROCESS_PRIVATE_MEMORY",
            "backend_identity": backend_identity,
            "backend_identity_sha256": sha256_value(backend_identity),
            "process_start_receipt": start,
            "executable_sha256": start["executable_sha256"],
            "initial_shard_sha256": sha256_value(case_config),
        }
    )
    while True:
        try:
            control = control_queue.get_nowait()
        except queue.Empty:
            control = None
        if control:
            if control["command"] == "BIND":
                manifest = control["manifest"]
                control_response_queue.put({"status": "BOUND", "service_id": owner_id})
                continue
            if control["command"] == "FREEZE":
                if manifest is None:
                    raise RuntimeError("owner frozen before manifest binding")
                freeze = _freeze_receipt(
                    private_key=private_key,
                    service_id=owner_id,
                    source_id=source_id,
                    manifest=manifest,
                    terminal_head=state_head,
                    record_count=len(entries),
                )
                control_response_queue.put(
                    {
                        "entries": entries,
                        "state_head": state_head,
                        "current_owner_state_epoch": epoch,
                        "freeze_receipt": freeze,
                    }
                )
                break
        try:
            request = request_queue.get(timeout=0.05)
        except queue.Empty:
            continue
        if manifest is None:
            raise RuntimeError("owner request before manifest binding")
        _validate_request(request, manifest, owner_id)
        payload = request["payload"]
        minute = int(payload["observed_at_minute"])
        action = str(payload["action"])
        # The response payload binds the state head produced by this append.
        provisional = _owner_payload(
            owner_id,
            action,
            manifest,
            case_config,
            minute,
            payload.get("arguments", {}),
            next_state_head=None,
            epoch=epoch,
        )
        base = {
            "owner_id": owner_id,
            "process_id": os.getpid(),
            "request_id": request["request_id"],
            "request_nonce": request["request_nonce"],
            "run_id": manifest["run_id"],
            "world_root": manifest["world_root"],
            "arm_binding_token": manifest["arm_binding_token"],
            "object_id": manifest["object_id"],
            "operation_id": manifest["operation_id"],
            "request_bytes": request["request_bytes"],
            "request_sha256": request["request_sha256"],
            "observed_at_minute": minute,
            "payload": provisional,
        }
        # Calculate the future head, then place it in Authority payload and
        # rebuild.  The chain hash intentionally excludes state/chain fields.
        response_sha = sha256_value(_record_hash_payload(base, "response_sha256"))
        future_head = sha256_value(
            {
                "append_index": len(entries),
                "previous_head": state_head,
                "record_sha256": response_sha,
            }
        )
        if action == "AUTHORITY":
            base["payload"]["owner_state_head"] = future_head
            response_sha = sha256_value(
                _record_hash_payload(base, "response_sha256")
            )
            future_head = sha256_value(
                {
                    "append_index": len(entries),
                    "previous_head": state_head,
                    "record_sha256": response_sha,
                }
            )
            # Fixpoint is impossible if owner_state_head participates in its
            # own digest.  owner_state_head therefore denotes the pre-append
            # authoritative head, and current receipt identity is carried by
            # the signed top-level state_head_after/epoch.
            base["payload"]["owner_state_head"] = state_head
        response, state_head = _append_signed_record(
            private_key=private_key,
            base=base,
            entries=entries,
            previous_head=state_head,
            sha_field="response_sha256",
        )
        # Target receives an independent process-to-process stream of the
        # latest signed owner record.  The arm cannot write this queue.
        head_update_queue.put(response)
        response_queue.put(response)


def _verify_record_digest(record: Mapping[str, Any], sha_field: str) -> bool:
    return sha256_value(_record_hash_payload(record, sha_field)) == record.get(sha_field)


def _target_event_base(
    *,
    kind: str,
    manifest: Mapping[str, Any],
    minute: int,
    extra: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "kind": kind,
        "process_id": os.getpid(),
        "minute": minute,
        "run_id": manifest["run_id"],
        "world_root": manifest["world_root"],
        "arm_binding_token": manifest["arm_binding_token"],
        "q_version": manifest["q_version"],
        "object_id": manifest["object_id"],
        "target_id": manifest["target_id"],
        "operation_id": manifest["operation_id"],
        **dict(extra),
    }


def target_worker(
    owner_registry: Mapping[str, Mapping[str, Any]],
    owner_head_update_queues: Mapping[str, Any],
    request_queue: Any,
    response_queue: Any,
    control_queue: Any,
    control_response_queue: Any,
    ready_queue: Any,
) -> None:
    """Entrypoint for the only native Target ledger."""
    private_key = Ed25519PrivateKey.generate()
    source_id = f"TARGET-state-{uuid.uuid4().hex}"
    backend_identity = {
        "kind": "PROCESS_PRIVATE_MEMORY",
        "target_id": "VenueV:CircuitC7",
        "pid": os.getpid(),
        "nonce": uuid.uuid4().hex,
    }
    initial_head = sha256_value(
        {"source_id": source_id, "target": "VenueV:CircuitC7", "genesis": uuid.uuid4().hex}
    )
    state_head = initial_head
    entries: list[dict[str, Any]] = []
    occurrences: list[dict[str, Any]] = []
    samples: list[dict[str, Any]] = []
    manifest: Mapping[str, Any] | None = None
    latest_owner_records: dict[str, Mapping[str, Any]] = {}
    start = _start_receipt(
        private_key=private_key,
        service_id="TARGET",
        source_id=source_id,
        initial_head=initial_head,
        backend_identity=backend_identity,
    )
    ready_queue.put(
        {
            "service_id": "TARGET",
            "actual_pid": os.getpid(),
            "public_key_hex": public_key_hex(private_key),
            "state_source_id": source_id,
            "state_head_at_start": initial_head,
            "state_epoch_at_start": 1,
            "current_owner_state_epoch": 1,
            "backend_kind": "PROCESS_PRIVATE_MEMORY",
            "backend_identity": backend_identity,
            "backend_identity_sha256": sha256_value(backend_identity),
            "process_start_receipt": start,
            "executable_sha256": start["executable_sha256"],
            "initial_shard_sha256": sha256_value(
                {"target_id": "VenueV:CircuitC7"}
            ),
        }
    )
    while True:
        try:
            control = control_queue.get_nowait()
        except queue.Empty:
            control = None
        if control:
            if control["command"] == "BIND":
                manifest = control["manifest"]
                control_response_queue.put({"status": "BOUND", "service_id": "TARGET"})
                continue
            if control["command"] == "FREEZE":
                if manifest is None:
                    raise RuntimeError("target frozen before manifest binding")
                freeze = _freeze_receipt(
                    private_key=private_key,
                    service_id="TARGET",
                    source_id=source_id,
                    manifest=manifest,
                    terminal_head=state_head,
                    record_count=len(entries),
                )
                control_response_queue.put(
                    {
                        "entries": entries,
                        "occurrences": occurrences,
                        "sensor_samples": samples,
                        "state_head": state_head,
                        "freeze_receipt": freeze,
                    }
                )
                break
        try:
            request = request_queue.get(timeout=0.05)
        except queue.Empty:
            continue
        if manifest is None:
            raise RuntimeError("target request before manifest binding")
        _validate_request(request, manifest, "TARGET")
        payload = request["payload"]
        action = payload["action"]
        arguments = payload.get("arguments", {})
        if action == "EXECUTE":
            if occurrences:
                original = occurrences[0]
                result = {
                    "kind": "TARGET_EXECUTION_RECEIPT",
                    "decision": "IDEMPOTENT_REPLAY",
                    "occurrence_event_sha256": original["event_sha256"],
                    "sensor_event_sha256": [
                        sample["event_sha256"] for sample in samples
                    ],
                    "original_execute_request_id": original[
                        "source_execute_request_id"
                    ],
                    "original_execute_request_sha256": original[
                        "source_execute_request_sha256"
                    ],
                }
                response_queue.put(
                    {
                        "request_id": request["request_id"],
                        "request_nonce": request["request_nonce"],
                        "request_sha256": request["request_sha256"],
                        "process_id": os.getpid(),
                        "payload": result,
                    }
                )
                continue
            receipts = arguments.get("authority_receipts", [])
            by_owner = {receipt.get("owner_id"): receipt for receipt in receipts}
            required = {"O_V", "O_R", "O_S"}
            if set(by_owner) != required:
                raise ValueError("target requires exact O_V/O_R/O_S authority set")
            # Drain the private owner->Target freshness streams at execute time.
            for owner_id, update_queue in owner_head_update_queues.items():
                while True:
                    try:
                        latest_owner_records[owner_id] = update_queue.get_nowait()
                    except queue.Empty:
                        break
            execute_minute = int(payload["observed_at_minute"])
            for owner_id in sorted(required):
                receipt = by_owner[owner_id]
                registry = owner_registry[owner_id]
                if not verify_signed(receipt, registry["public_key_hex"]):
                    raise ValueError("authority signature invalid")
                if not _verify_record_digest(receipt, "response_sha256"):
                    raise ValueError("authority digest invalid")
                owner_payload = receipt.get("payload", {})
                allowed_decisions = {
                    "O_V": {"ALLOW", "AUTHORIZED", "APPROVE", "APPROVED"},
                    "O_R": {"COMMIT", "COMMITTED", "AVAILABLE"},
                    "O_S": {"APPROVE", "APPROVED", "SAFE"},
                }
                if (
                    owner_payload.get("kind") != "AUTHORITY"
                    or owner_payload.get("decision")
                    not in allowed_decisions[owner_id]
                ):
                    raise ValueError("authority not granted")
                for key in (
                    "run_id",
                    "world_root",
                    "arm_binding_token",
                    "q_version",
                    "object_id",
                    "operation_id",
                ):
                    if owner_payload.get(key) != manifest.get(key):
                        raise ValueError(f"authority binding mismatch: {key}")
                if not (
                    int(owner_payload["issued_at_minute"])
                    <= execute_minute
                    < int(owner_payload["expires_at_minute"])
                ):
                    raise ValueError("authority not current at execution")
                latest = latest_owner_records.get(owner_id)
                if latest is None or latest.get("response_sha256") != receipt.get("response_sha256"):
                    raise ValueError("authority receipt is not current owner record")
                if latest.get("state_head_after") != receipt.get("state_head_after"):
                    raise ValueError("authority state head stale")
                if owner_payload.get("owner_state_epoch") != registry.get("current_owner_state_epoch"):
                    raise ValueError("authority state epoch stale")
            consumed = {
                owner_id: by_owner[owner_id]["response_sha256"]
                for owner_id in sorted(required)
            }
            consumed_heads = {
                owner_id: by_owner[owner_id]["state_head_after"]
                for owner_id in sorted(required)
            }
            consumed_epochs = {
                owner_id: by_owner[owner_id]["payload"]["owner_state_epoch"]
                for owner_id in sorted(required)
            }
            occurrence, state_head = _append_signed_record(
                private_key=private_key,
                base=_target_event_base(
                    kind="OCCURRENCE",
                    manifest=manifest,
                    minute=0,
                    extra={
                        "occurrence_id": f"occ-{manifest['operation_id']}",
                        "consumed_authority_response_hashes": consumed,
                        "consumed_authority_state_heads": consumed_heads,
                        "consumed_authority_state_epochs": consumed_epochs,
                        "source_execute_request_id": request["request_id"],
                        "source_execute_request_nonce": request["request_nonce"],
                        "source_execute_request_sha256": request["request_sha256"],
                        "execute_at_minute": execute_minute,
                    },
                ),
                entries=entries,
                previous_head=state_head,
                sha_field="event_sha256",
            )
            occurrences.append(occurrence)
            for minute in range(46):
                sample, state_head = _append_signed_record(
                    private_key=private_key,
                    base=_target_event_base(
                        kind="SENSOR_SAMPLE",
                        manifest=manifest,
                        minute=minute,
                        extra={
                            "power_kw": 3.0,
                            "safety_ok": True,
                            "noise_ok": True,
                            "other_circuits_energized": [],
                            "source_execute_request_id": request["request_id"],
                            "source_execute_request_nonce": request["request_nonce"],
                            "source_execute_request_sha256": request["request_sha256"],
                            "source_occurrence_event_sha256": occurrence["event_sha256"],
                        },
                    ),
                    entries=entries,
                    previous_head=state_head,
                    sha_field="event_sha256",
                )
                samples.append(sample)
            result = {
                "kind": "TARGET_EXECUTION_RECEIPT",
                "decision": "EXECUTED",
                "occurrence_event_sha256": occurrence["event_sha256"],
                "sensor_event_sha256": [sample["event_sha256"] for sample in samples],
            }
        elif action == "READBACK":
            effect_digest = sha256_value(
                {"occurrences": occurrences, "sensor_samples": samples}
            )
            readback, state_head = _append_signed_record(
                private_key=private_key,
                base=_target_event_base(
                    kind="READBACK",
                    manifest=manifest,
                    minute=int(payload["observed_at_minute"]),
                    extra={
                        "source_readback_request_id": request["request_id"],
                        "source_readback_request_nonce": request["request_nonce"],
                        "source_readback_request_sha256": request["request_sha256"],
                        "effect_digest": effect_digest,
                        "occurrence_event_sha256": [
                            event["event_sha256"] for event in occurrences
                        ],
                        "sensor_event_sha256": [
                            event["event_sha256"] for event in samples
                        ],
                    },
                ),
                entries=entries,
                previous_head=state_head,
                sha_field="event_sha256",
            )
            result = {
                "kind": "TARGET_READBACK",
                "decision": "READ",
                "occurrence_count": len(occurrences),
                "sensor_sample_count": len(samples),
                "effect_digest": effect_digest,
                "readback_event_sha256": readback["event_sha256"],
            }
        else:
            raise ValueError(f"unsupported target action: {action}")
        response_queue.put(
            {
                "request_id": request["request_id"],
                "request_nonce": request["request_nonce"],
                "request_sha256": request["request_sha256"],
                "process_id": os.getpid(),
                "payload": result,
            }
        )
