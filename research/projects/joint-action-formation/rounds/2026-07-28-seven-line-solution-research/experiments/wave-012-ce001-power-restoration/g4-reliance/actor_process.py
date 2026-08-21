#!/usr/bin/env python3
"""Isolated local O_E/O_Q/O_V actor.

The private Ed25519 key exists only in this child process.  The controller pins
the public key emitted by the actual Popen child and can verify, but cannot
recompute, signed response bytes without asking that child to act.

This is a cooperative local-process trust boundary.  It is not protection
against a malicious same-user process that can replace or inspect executables.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def b64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def unb64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"), validate=True)


def read_message() -> tuple[dict[str, Any], bytes]:
    line = sys.stdin.buffer.readline()
    if not line:
        raise EOFError
    raw = line.rstrip(b"\n")
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("message must be an object")
    return value, raw


def send_message(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")
    sys.stdout.buffer.flush()


def signed_envelope(
    private_key: Ed25519PrivateKey,
    public_key_bytes: bytes,
    payload: dict[str, Any],
    corrupt_signature: bool = False,
) -> dict[str, Any]:
    payload_bytes = canonical_bytes(payload)
    signature = private_key.sign(payload_bytes)
    if corrupt_signature:
        signature = bytes([signature[0] ^ 1]) + signature[1:]
    return {
        "type": "SIGNED_TRANSMITTED_BYTES",
        "public_key_b64": b64(public_key_bytes),
        "payload_b64": b64(payload_bytes),
        "payload_sha256": sha256_bytes(payload_bytes),
        "signature_b64": b64(signature),
    }


def verify_signed_envelope(
    envelope: dict[str, Any], public_key_b64: str
) -> dict[str, Any]:
    if envelope.get("type") != "SIGNED_TRANSMITTED_BYTES":
        raise ValueError("wrong envelope type")
    if envelope.get("public_key_b64") != public_key_b64:
        raise ValueError("untrusted public key")
    payload_bytes = unb64(str(envelope["payload_b64"]))
    if sha256_bytes(payload_bytes) != envelope.get("payload_sha256"):
        raise ValueError("payload digest mismatch")
    public_key = Ed25519PublicKey.from_public_bytes(unb64(public_key_b64))
    try:
        public_key.verify(
            unb64(str(envelope["signature_b64"])), payload_bytes
        )
    except InvalidSignature as exc:
        raise ValueError("invalid signature") from exc
    value = json.loads(payload_bytes.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("signed payload must be an object")
    return value


def exact_bound(episode: dict[str, Any]) -> dict[str, str]:
    return {
        "episode_id": str(episode["episode_id"]),
        "Q_version": str(episode["Q_version"]),
        "object_id": str(episode["object_id"]),
        "operation_id": str(episode["operation_id"]),
    }


def validate_adapter(episode: dict[str, Any]) -> None:
    adapter = episode.get("object_adapter")
    if not isinstance(adapter, dict):
        raise ValueError("explicit object adapter missing")
    expected = {
        "adapter_id": "G4_LEGACY_TARGET_V1_TO_CE001_CANONICAL_V1",
        "adapter_version": "1",
        "source_object_id": "Venue-V/Circuit-C7",
        "canonical_object_id": "VenueV:CircuitC7",
    }
    if any(adapter.get(key) != value for key, value in expected.items()):
        raise ValueError("object adapter mismatch")
    if episode.get("native_object_id") != expected["source_object_id"]:
        raise ValueError("native object is not the adapter source")
    if episode.get("object_id") != expected["canonical_object_id"]:
        raise ValueError("canonical object is not the adapter target")
    expected_hash = sha256_bytes(
        canonical_bytes(
            {
                "adapter_id": expected["adapter_id"],
                "adapter_version": expected["adapter_version"],
                "source_object_id": expected["source_object_id"],
                "canonical_object_id": expected["canonical_object_id"],
            }
        )
    )
    if adapter.get("mapping_sha256") != expected_hash:
        raise ValueError("object adapter mapping digest mismatch")


def validate_target_envelope(
    envelope: dict[str, Any],
    oe_trust_binding: dict[str, Any],
    episode: dict[str, Any],
    request: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    try:
        record = verify_signed_envelope(
            envelope, str(oe_trust_binding["public_key_b64"])
        )
    except (KeyError, TypeError, ValueError):
        return {}, ["O_E_PROVENANCE_INVALID"]
    for field, expected in exact_bound(episode).items():
        if record.get(field) != expected:
            failures.append(f"TARGET_WRONG_{field.upper()}")
    if record.get("issuer") != "O_E":
        failures.append("TARGET_WRONG_ISSUER")
    for field in (
        "service_id",
        "state_source_id",
        "act_source_id",
        "process_instance_id",
    ):
        if record.get(field) != oe_trust_binding.get(field):
            failures.append(f"TARGET_WRONG_{field.upper()}")
    if record.get("reported_pid") != oe_trust_binding.get("actual_child_pid"):
        failures.append("TARGET_WRONG_ACTUAL_CHILD_PID")
    if record.get("state") != "SUCCEEDED":
        failures.append("TARGET_NOT_SUCCEEDED")
    if record.get("circuit_id") != "C7":
        failures.append("TARGET_WRONG_CIRCUIT")
    power = record.get("power_kw")
    if not isinstance(power, (int, float)) or not 2.85 <= float(power) <= 3.15:
        failures.append("TARGET_POWER_OUT_OF_RANGE")
    duration = record.get("continuous_minutes")
    if not isinstance(duration, (int, float)) or float(duration) < 45:
        failures.append("TARGET_DURATION_TOO_SHORT")
    if record.get("no_other_circuit") is not True:
        failures.append("TARGET_OTHER_CIRCUIT_FLAG")
    if record.get("other_circuits_energized") != []:
        failures.append("TARGET_OTHER_CIRCUIT_PRESENT")
    completed_tick = record.get("completed_tick")
    if (
        not isinstance(completed_tick, int)
        or completed_tick > int(episode["deadline_tick"])
    ):
        failures.append("TARGET_DEADLINE_MISSED")
    if request.get("reconciliation_state") != "SUCCEEDED":
        failures.append("RECONCILIATION_NOT_SUCCEEDED")
    if request.get("exact_reconciliation") is not True:
        failures.append("EXACT_RECONCILIATION_MISSING")
    if request.get("target_payload_sha256") != envelope.get("payload_sha256"):
        failures.append("RECONCILIATION_TARGET_MISMATCH")
    for field in ("effect_occurrence_id", "effect_revision"):
        if request.get(field) != record.get(field):
            failures.append(f"REQUEST_WRONG_{field.upper()}")
    return record, failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("O_E", "O_Q", "O_V"), required=True)
    args = parser.parse_args()

    init, init_raw = read_message()
    if init.get("type") != "INIT":
        raise ValueError("first message must be INIT")
    episode = init["episode"]
    if not isinstance(episode, dict):
        raise ValueError("episode missing")
    validate_adapter(episode)

    private_key = Ed25519PrivateKey.generate()
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_key_b64 = b64(public_key_bytes)
    process_instance_id = str(uuid.uuid4())
    service_id = f"local-actor-service/{args.role}"
    state_source_id = f"local-actor-state/{args.role}/{process_instance_id}"
    act_source_id = f"local-actor-act/{args.role}/{process_instance_id}"
    source_hash = sha256_bytes(Path(__file__).read_bytes())
    revision = 19 if args.role == "O_Q" else 23 if args.role == "O_V" else 1
    mutation = str(init.get("mutation", "NONE"))
    oe_trust_binding = init.get("oe_trust_binding", {})
    if not isinstance(oe_trust_binding, dict):
        oe_trust_binding = {}
    act_count = 0

    identity = {
        "role": args.role,
        "service_id": service_id,
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "reported_pid": os.getpid(),
        "process_instance_id": process_instance_id,
        "executable_sha256": source_hash,
        "init_transmitted_sha256": sha256_bytes(init_raw),
    }
    ready = {
        "kind": "LOCAL_ACTOR_READY",
        **identity,
        "current_revision": revision,
    }
    send_message(
        signed_envelope(private_key, public_key_bytes, ready)
    )

    while True:
        try:
            request, request_raw = read_message()
        except EOFError:
            break
        kind = request.get("type")
        if kind == "SHUTDOWN":
            send_message({"type": "SHUTDOWN_ACK"})
            break
        request_hash = sha256_bytes(request_raw)
        if kind == "ISSUE_TARGET_RECORD" and args.role == "O_E":
            bound = exact_bound(episode)
            if any(request.get(field) != value for field, value in bound.items()):
                send_message(
                    {
                        "type": "REJECTED",
                        "reason": "TARGET_REQUEST_BINDING_MISMATCH",
                    }
                )
                continue
            act_count += 1
            circuit_id = "C8" if mutation == "O_E_WRONG_CIRCUIT" else "C7"
            power_kw = 0.0 if mutation == "O_E_ZERO_POWER" else 3.0
            duration = 15 if mutation == "O_E_SHORT_DURATION" else 45
            other = ["C9"] if mutation == "O_E_OTHER_CIRCUIT" else []
            completed_tick = (
                int(episode["deadline_tick"]) + 1
                if mutation == "O_E_DEADLINE_MISS"
                else int(request["completed_tick"])
            )
            payload = {
                "kind": "TARGET_NATIVE_RECORD",
                **identity,
                **bound,
                "issuer": "O_E",
                "state": "SUCCEEDED",
                "effect_revision": 1,
                "effect_occurrence_id": (
                    f"target-occurrence/{episode['operation_id']}/1"
                ),
                "circuit_id": circuit_id,
                "power_kw": power_kw,
                "continuous_minutes": duration,
                "no_other_circuit": not other,
                "other_circuits_energized": other,
                "completed_tick": completed_tick,
                "deadline_tick": int(episode["deadline_tick"]),
                "target_native_object_id": episode["native_object_id"],
                "object_adapter_id": episode["object_adapter"]["adapter_id"],
                "request_transmitted_sha256": request_hash,
                "act_ordinal": act_count,
            }
            send_message(
                signed_envelope(
                    private_key,
                    public_key_bytes,
                    payload,
                    corrupt_signature=mutation == "O_E_BAD_SIGNATURE",
                )
            )
            continue
        if kind == "ISSUE_OWNER_ACT" and args.role in {"O_Q", "O_V"}:
            target_envelope = request.get("target_envelope")
            if not isinstance(target_envelope, dict):
                send_message(
                    {"type": "REJECTED", "reason": "TARGET_ENVELOPE_MISSING"}
                )
                continue
            record, gate_failures = validate_target_envelope(
                target_envelope, oe_trust_binding, episode, request
            )
            if gate_failures:
                send_message(
                    {
                        "type": "REJECTED",
                        "reason": "OWNER_PRE_ACT_GATE_REJECTED",
                        "failures": gate_failures,
                    }
                )
                continue
            act_count += 1
            issuer = "O_Q" if mutation == "O_V_DUPLICATE_ISSUER" else args.role
            decision = "REFUSE" if mutation == f"{args.role}_REFUSE" else "ACCEPT"
            bound = exact_bound(episode)
            if mutation == f"{args.role}_WRONG_EPISODE":
                bound["episode_id"] = "CE-001-WRONG-EPISODE"
            if mutation == f"{args.role}_WRONG_Q":
                bound["Q_version"] = "Q@wrong"
            occurrence_id = record["effect_occurrence_id"]
            if mutation == f"{args.role}_WRONG_EFFECT":
                occurrence_id = "target-occurrence/wrong"
            owner_revision = revision - 1 if mutation == f"{args.role}_STALE" else revision
            emitted_service_id = (
                "local-actor-service/O_Q"
                if mutation == "O_V_DUPLICATE_SERVICE"
                else service_id
            )
            payload = {
                "kind": "OWNER_ACT",
                **identity,
                "service_id": emitted_service_id,
                **bound,
                "issuer": issuer,
                "decision": decision,
                "owner_revision": owner_revision,
                "effect_occurrence_id": occurrence_id,
                "effect_revision": record["effect_revision"],
                "target_payload_sha256": target_envelope["payload_sha256"],
                "request_transmitted_sha256": request_hash,
                "act_ordinal": act_count,
            }
            send_message(
                signed_envelope(private_key, public_key_bytes, payload)
            )
            continue
        send_message({"type": "REJECTED", "reason": "UNSUPPORTED_REQUEST"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
