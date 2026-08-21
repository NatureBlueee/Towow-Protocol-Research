"""Actual multi-process runtime for CT-001.

Each worker creates and retains its Ed25519 private key inside its spawned
process.  The controller receives signed start receipts and native records, but
never receives a private key.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import queue
import sys
import uuid
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


MODE_FORWARD = "FORWARD_A4"
MODE_EXTERNAL = "SUPPRESS_A4_HELPER"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_value(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def sign_mapping(
    private_key: Ed25519PrivateKey, value: Mapping[str, Any]
) -> dict[str, Any]:
    signed = dict(value)
    signed["signature_hex"] = private_key.sign(canonical_bytes(value)).hex()
    return signed


def verify_signed(value: Mapping[str, Any], public_hex: str) -> bool:
    signature = value.get("signature_hex")
    if not isinstance(signature, str):
        return False
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(
            bytes.fromhex(signature), canonical_bytes(unsigned)
        )
    except (ValueError, InvalidSignature):
        return False
    return True


def _identity(
    private_key: Ed25519PrivateKey, worker_id: str, state_source_id: str
) -> dict[str, Any]:
    executable = pathlib.Path(__file__).resolve()
    receipt = {
        "worker_id": worker_id,
        "actual_pid": os.getpid(),
        "public_key_hex": public_key_hex(private_key),
        "state_source_id": state_source_id,
        "start_method": "spawn",
        "executable": str(executable),
        "executable_sha256": sha256_bytes(executable.read_bytes()),
    }
    receipt["receipt_sha256"] = sha256_value(receipt)
    return sign_mapping(private_key, receipt)


def _request_envelope(
    private_key: Ed25519PrivateKey,
    *,
    actor_id: str,
    run_binding: str,
    object_id: str,
    operation_id: str,
) -> dict[str, Any]:
    body = {
        "kind": "EXACT_COMMIT",
        "actor_id": actor_id,
        "run_binding": run_binding,
        "request_id": f"r-{uuid.uuid4().hex}",
        "object_id": object_id,
        "operation_id": operation_id,
        "desired_state": {"energized": True},
    }
    envelope = {
        "body": body,
        "body_sha256": sha256_value(body),
        "actor_public_key_hex": public_key_hex(private_key),
    }
    return sign_mapping(private_key, envelope)


def verify_request_envelope(
    envelope: Mapping[str, Any],
    actor_registry: Mapping[str, str],
    *,
    run_binding: str,
) -> tuple[bool, str]:
    body = envelope.get("body")
    if not isinstance(body, Mapping):
        return False, "request body missing"
    actor_id = body.get("actor_id")
    if actor_id not in actor_registry:
        return False, "actor not registered"
    public_hex = actor_registry[actor_id]
    if envelope.get("actor_public_key_hex") != public_hex:
        return False, "actor public key mismatch"
    if envelope.get("body_sha256") != sha256_value(body):
        return False, "request body digest mismatch"
    if not verify_signed(envelope, public_hex):
        return False, "request signature invalid"
    if body.get("run_binding") != run_binding:
        return False, "run binding mismatch"
    if body.get("kind") != "EXACT_COMMIT":
        return False, "request kind mismatch"
    return True, ""


def _alpha_shape(value: Any) -> Any:
    """Return a value-blind shape that still preserves ordering and lengths."""
    if isinstance(value, Mapping):
        return {key: _alpha_shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_alpha_shape(item) for item in value]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if value is None:
        return "null"
    if isinstance(value, str):
        return f"str:{len(value)}"
    return type(value).__name__


def alpha_shape(value: Any) -> Any:
    return _alpha_shape(value)


def a4_worker(
    router_request_queue: Any,
    router_response_queue: Any,
    ready_queue: Any,
    bind_queue: Any,
    result_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    state_source_id = f"a-{uuid.uuid4().hex}"
    start_receipt = _identity(private_key, "A4", state_source_id)
    ready_queue.put({"worker_id": "A4", "start_receipt": start_receipt})
    manifest = bind_queue.get(timeout=15)

    events: list[dict[str, Any]] = [
        {
            "event": "START",
            "argv": list(sys.argv),
            "cwd": os.getcwd(),
            "process_name": __import__("multiprocessing").current_process().name,
        }
    ]
    envelope = _request_envelope(
        private_key,
        actor_id="A4",
        run_binding=manifest["run_binding"],
        object_id=manifest["object_id"],
        operation_id=manifest["operation_id"],
    )
    events.append({"event": "COMMIT_PREPARED", "envelope": envelope})
    events.append(
        {
            "event": "COMMIT_SENT",
            "request_sha256": envelope["body_sha256"],
        }
    )
    router_request_queue.put(envelope)
    neutral_response = router_response_queue.get(timeout=20)
    events.append({"event": "TARGET_OBSERVATION", "response": neutral_response})
    result_queue.put(
        {
            "worker_id": "A4",
            "start_receipt": start_receipt,
            "request_envelope": envelope,
            "transcript": {
                "process_id": os.getpid(),
                "events": events,
                "pre_decision_event_count": 3,
            },
        }
    )


def helper_worker(
    target_request_queue: Any,
    target_response_queue: Any,
    trigger_queue: Any,
    router_result_queue: Any,
    ready_queue: Any,
    bind_queue: Any,
    result_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    state_source_id = f"h-{uuid.uuid4().hex}"
    start_receipt = _identity(private_key, "HELPER", state_source_id)
    ready_queue.put({"worker_id": "HELPER", "start_receipt": start_receipt})
    binding = bind_queue.get(timeout=15)

    # The plan is frozen before A4 is released.  The later trigger contains only
    # the pre-registered window token, never A4's request or request digest.
    plan = {
        "plan_id": binding["plan_id"],
        "window_token": binding["window_token"],
        "run_binding": binding["run_binding"],
        "object_id": binding["object_id"],
        "operation_id": binding["operation_id"],
        "desired_state": {"energized": True},
    }
    plan_receipt = sign_mapping(
        private_key,
        {
            "kind": "HELPER_PLAN_FROZEN",
            "plan_sha256": sha256_value(plan),
            "window_token_sha256": sha256_value(binding["window_token"]),
            "frozen_before_a4_release": True,
        },
    )
    trigger = trigger_queue.get(timeout=20)
    envelope = None
    target_receipt = None
    action = "DORMANT"
    if (
        binding["mode"] == MODE_EXTERNAL
        and trigger.get("command") == "OPEN_WINDOW"
        and trigger.get("window_token") == binding["window_token"]
    ):
        action = "COMMITTED"
        envelope = _request_envelope(
            private_key,
            actor_id="HELPER",
            run_binding=plan["run_binding"],
            object_id=plan["object_id"],
            operation_id=plan["operation_id"],
        )
        target_request_queue.put(envelope)
        target_receipt = target_response_queue.get(timeout=20)
    helper_result = {
        "worker_id": "HELPER",
        "start_receipt": start_receipt,
        "mode": binding["mode"],
        "plan": plan,
        "plan_receipt": plan_receipt,
        "action": action,
        "request_envelope": envelope,
        "target_receipt": target_receipt,
    }
    router_result_queue.put(helper_result)
    result_queue.put(helper_result)


def router_worker(
    arm_request_queue: Any,
    arm_response_queue: Any,
    target_request_queue: Any,
    target_response_queue: Any,
    helper_trigger_queue: Any,
    helper_result_queue: Any,
    ready_queue: Any,
    bind_queue: Any,
    result_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    state_source_id = f"r-{uuid.uuid4().hex}"
    start_receipt = _identity(private_key, "ROUTER", state_source_id)
    ready_queue.put({"worker_id": "ROUTER", "start_receipt": start_receipt})
    binding = bind_queue.get(timeout=15)

    envelope = arm_request_queue.get(timeout=20)
    valid, error = verify_request_envelope(
        envelope,
        {"A4": binding["a4_public_key_hex"]},
        run_binding=binding["run_binding"],
    )
    if not valid:
        raise RuntimeError(f"A4 request rejected: {error}")

    if binding["mode"] == MODE_FORWARD:
        target_request_queue.put(envelope)
        target_receipt = target_response_queue.get(timeout=20)
        helper_trigger_queue.put(
            {"command": "NOOP", "window_token": binding["window_token"]}
        )
        actual_action = "DELIVERED_A4"
    else:
        helper_trigger_queue.put(
            {"command": "OPEN_WINDOW", "window_token": binding["window_token"]}
        )
        helper_preview = helper_result_queue.get(timeout=20)
        target_receipt = helper_preview["target_receipt"]
        actual_action = "SUPPRESSED_A4"

    # A deliberate attack fixture can make a correctly signed Router log lie.
    # The Target receipt remains the authoritative direct-actor evidence.
    claimed_action = (
        "DELIVERED_A4"
        if binding.get("signed_lie") and actual_action == "SUPPRESSED_A4"
        else actual_action
    )
    route_record = sign_mapping(
        private_key,
        {
            "kind": "ROUTE_DECISION",
            "run_binding": binding["run_binding"],
            "arm_request_id": envelope["body"]["request_id"],
            "arm_request_sha256": envelope["body_sha256"],
            "actual_action": actual_action,
            "claimed_action": claimed_action,
            "window_token_sha256": sha256_value(binding["window_token"]),
            "target_commit_id": target_receipt["commit"]["commit_id"],
        },
    )
    neutral_response = {
        "status": "TARGET_STATE_OBSERVED",
        "object_id": binding["object_id"],
        "operation_id": binding["operation_id"],
        "energized": target_receipt["commit"]["post_state"]["energized"],
        "version": target_receipt["commit"]["post_version"],
    }
    arm_response_queue.put(neutral_response)
    if binding["mode"] == MODE_FORWARD:
        helper_result_queue.get(timeout=20)
    result_queue.put(
        {
            "worker_id": "ROUTER",
            "start_receipt": start_receipt,
            "mode": binding["mode"],
            "route_record": route_record,
            "arm_request_envelope": envelope,
            "neutral_response": neutral_response,
        }
    )


def target_worker(
    router_request_queue: Any,
    router_response_queue: Any,
    helper_request_queue: Any,
    helper_response_queue: Any,
    ready_queue: Any,
    bind_queue: Any,
    result_queue: Any,
) -> None:
    private_key = Ed25519PrivateKey.generate()
    state_source_id = f"t-{uuid.uuid4().hex}"
    start_receipt = _identity(private_key, "TARGET", state_source_id)
    ready_queue.put({"worker_id": "TARGET", "start_receipt": start_receipt})
    binding = bind_queue.get(timeout=15)

    channels = (
        ("A4_ROUTED", router_request_queue, router_response_queue),
        ("HELPER_DIRECT", helper_request_queue, helper_response_queue),
    )
    envelope = None
    ingress_channel = None
    response_queue = None
    while envelope is None:
        for channel, request_queue, candidate_response_queue in channels:
            try:
                envelope = request_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            ingress_channel = channel
            response_queue = candidate_response_queue
            break

    actor_registry = binding["actor_registry"]
    valid, error = verify_request_envelope(
        envelope, actor_registry, run_binding=binding["run_binding"]
    )
    if not valid:
        raise RuntimeError(f"Target rejected request: {error}")

    body = envelope["body"]
    if body["object_id"] != binding["object_id"]:
        raise RuntimeError("Target object mismatch")
    if body["operation_id"] != binding["operation_id"]:
        raise RuntimeError("Target operation mismatch")
    pre_state = {"energized": False}
    post_state = dict(body["desired_state"])
    commit = {
        "kind": "TARGET_ATOMIC_COMMIT",
        "commit_id": f"c-{uuid.uuid4().hex}",
        "run_binding": binding["run_binding"],
        "object_id": binding["object_id"],
        "operation_id": binding["operation_id"],
        "actor_id": body["actor_id"],
        "actor_process_id": binding["actor_process_ids"][body["actor_id"]],
        "actor_public_key_sha256": sha256_value(
            envelope["actor_public_key_hex"]
        ),
        "origin_request_id": body["request_id"],
        "origin_request_sha256": envelope["body_sha256"],
        "origin_request_signature_hex": envelope["signature_hex"],
        "ingress_channel": ingress_channel,
        "pre_version": 0,
        "post_version": 1,
        "pre_state": pre_state,
        "post_state": post_state,
    }
    receipt = {
        "commit": commit,
        "commit_sha256": sha256_value(commit),
        "target_public_key_hex": public_key_hex(private_key),
    }
    receipt = sign_mapping(private_key, receipt)
    response_queue.put(receipt)
    projection = {
        "object_id": binding["object_id"],
        "operation_id": binding["operation_id"],
        "energized": post_state["energized"],
        "version": 1,
    }
    readback = {
        "object_id": binding["object_id"],
        "operation_id": binding["operation_id"],
        "state": post_state,
        "version": 1,
        "last_commit_id": commit["commit_id"],
    }
    readback_receipt = {
        "readback": readback,
        "readback_sha256": sha256_value(readback),
        "target_public_key_hex": public_key_hex(private_key),
    }
    readback_receipt = sign_mapping(private_key, readback_receipt)
    result_queue.put(
        {
            "worker_id": "TARGET",
            "start_receipt": start_receipt,
            "native_commit_receipt": receipt,
            "state_projection": projection,
            "state_projection_sha256": sha256_value(projection),
            "authoritative_readback_receipt": readback_receipt,
        }
    )
