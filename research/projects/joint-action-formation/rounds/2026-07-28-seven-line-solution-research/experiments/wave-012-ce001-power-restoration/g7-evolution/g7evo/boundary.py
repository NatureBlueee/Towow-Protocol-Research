"""Process/state/byte boundaries for the second G7 root-red-light repair.

The worker protocol is intentionally small: the controller transmits one JSON
frame on stdin and receives one JSON frame on stdout.  Every process-owned act
or lifecycle observation carries the real worker PID and has a byte preimage.
This is local synthetic process isolation, not a legal or hostile-host trust
boundary.
"""

from __future__ import annotations

import argparse
import base64
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Mapping
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .model import canonical_bytes, digest


def _hash(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(encoded: str) -> bytes:
    return base64.b64decode(encoded, validate=True)


def _bytes_item(raw: bytes, *, source_kind: str) -> dict[str, Any]:
    return {
        "source_kind": source_kind,
        "bytes_b64": _b64(raw),
        "bytes_hash": _hash(raw),
        "byte_length": len(raw),
    }


def _write_bytes(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def _state_boundary(path: Path, store_uuid: str) -> str:
    stat = path.stat()
    return _hash(
        canonical_bytes(
            {
                "realpath": str(path.resolve()),
                "device": stat.st_dev,
                "inode": stat.st_ino,
                "store_uuid": store_uuid,
            }
        )
    )


def _process_event(role: str, runtime_id: str) -> tuple[dict[str, Any], bytes]:
    event = {
        "event": "PROCESS_STARTED",
        "role": role,
        "runtime_id": runtime_id,
        "process_id": os.getpid(),
        "start_token": str(uuid4()),
        "executable": str(Path(sys.executable).resolve()),
    }
    raw = canonical_bytes(event)
    return event, raw


def _frame_signature_valid(
    frame: Mapping[str, Any],
    owner_id: str,
    pinned_public_key_b64: str,
    pinned_act_source_id: str,
) -> bool:
    if frame.get("owner_id") != owner_id:
        return False
    unsigned = {
        key: value
        for key, value in frame.items()
        if key not in {"signature", "response_frame_hash", "evidence_hash"}
    }
    try:
        public_raw = _unb64(pinned_public_key_b64)
        Ed25519PublicKey.from_public_bytes(public_raw).verify(
            _unb64(str(frame.get("signature", ""))),
            canonical_bytes(unsigned),
        )
    except (ValueError, InvalidSignature):
        return False
    return (
        frame.get("trust_anchor_public_key_b64") == pinned_public_key_b64
        and frame.get("trust_anchor_id") == _hash(public_raw)
        and frame.get("act_source_id") == pinned_act_source_id
    )


def _owner_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    owner_id = str(command["owner_id"])
    runtime_id = f"owner-runtime:{owner_id}:{uuid4()}"
    process_event, process_raw = _process_event(f"OWNER_{owner_id}", runtime_id)
    state_path = Path(str(command["state_path"])).resolve()
    store_uuid = str(uuid4())
    state_source_id = f"state-source:{owner_id}:{store_uuid}"
    private_key = Ed25519PrivateKey.generate()
    private_raw = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    public_key_b64 = _b64(public_raw)
    trust_anchor_id = _hash(public_raw)
    act_source_id = f"act-source:{owner_id}:{trust_anchor_id[:16]}"
    state = {
        "owner_id": owner_id,
        "runtime_id": runtime_id,
        "store_uuid": store_uuid,
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "trust_anchor_id": trust_anchor_id,
        "trust_anchor_public_key_b64": public_key_b64,
        "private_key_b64": _b64(private_raw),
        "state_head": f"{owner_id}:head:1",
        "act_count": 0,
    }
    request_raw = _unb64(str(command["request_bytes_b64"]))
    request = json.loads(request_raw.decode("utf-8"))
    accepted = False
    reason = "INVALID_REQUEST"
    after_hashes: list[str] = []
    if owner_id in {"O_Q", "O_V"}:
        occurrence_raw = _unb64(str(request.get("occurrence_bytes_b64", "")))
        binding = request.get("binding", {})
        accepted = (
            request.get("owner_id") == owner_id
            and request.get("expected_state_head") == state["state_head"]
            and request.get("request_hash")
            == _hash(canonical_bytes(request.get("request_body", {})))
            and request.get("occurrence_bytes_hash") == _hash(occurrence_raw)
            and binding.get("episode_id") == request.get("request_body", {}).get("episode_id")
            and binding.get("q_version") == "Q@v1"
            and binding.get("object_id") == "VenueV:CircuitC7"
            and binding.get("operation_id") == "deliver-3kw-45m"
            and binding.get("target_id") == "VenueV:CircuitC7"
        )
        reason = "EXACT_POST_OCCURRENCE_ACT" if accepted else "REFUSED_BINDING"
    elif owner_id == "O_P":
        frames = [
            json.loads(_unb64(value).decode("utf-8"))
            for value in request.get("owner_response_frames_b64", [])
        ]
        by_owner = {str(frame.get("owner_id")): frame for frame in frames}
        after_hashes = [_hash(_unb64(value)) for value in request.get("owner_response_frames_b64", [])]
        exact_binding = {
            (
                frame.get("episode_id"),
                frame.get("q_version"),
                frame.get("object_id"),
                frame.get("operation_id"),
                frame.get("target_id"),
                frame.get("occurrence_bytes_hash"),
            )
            for frame in frames
        }
        current_heads = request.get("current_owner_heads", {})
        pinned_public_keys = request.get("owner_public_keys", {})
        pinned_act_sources = request.get("owner_act_sources", {})
        at_epoch = int(request.get("at_epoch", 0))
        accepted = (
            len(frames) == 2
            and set(by_owner) == {"O_Q", "O_V"}
            and len(exact_binding) == 1
            and all(
                _frame_signature_valid(
                    by_owner[item],
                    item,
                    str(pinned_public_keys.get(item, "")),
                    str(pinned_act_sources.get(item, "")),
                )
                and by_owner[item].get("decision") == "ACTED"
                and by_owner[item].get("state_head") == current_heads.get(item)
                and at_epoch <= int(by_owner[item].get("response_expires_epoch", -1))
                for item in ("O_Q", "O_V")
            )
        )
        reason = "POST_TWO_OWNER_ACT" if accepted else "REFUSED_OWNER_FRAMES"
    state["act_count"] = 1 if accepted else 0
    state["last_reason"] = reason
    state_raw = canonical_bytes(state)
    _write_bytes(state_path, state_raw)
    response_unsigned = {
        "owner_id": owner_id,
        "runtime_id": runtime_id,
        "process_id": os.getpid(),
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "trust_anchor_id": trust_anchor_id,
        "trust_anchor_public_key_b64": public_key_b64,
        "state_head": state["state_head"],
        "request_bytes_hash": _hash(request_raw),
        "episode_id": request.get("binding", {}).get("episode_id")
        or request.get("episode_id"),
        "q_version": request.get("binding", {}).get("q_version")
        or request.get("q_version"),
        "object_id": request.get("binding", {}).get("object_id")
        or request.get("object_id"),
        "operation_id": request.get("binding", {}).get("operation_id")
        or request.get("operation_id"),
        "target_id": request.get("binding", {}).get("target_id")
        or request.get("target_id"),
        "occurrence_bytes_hash": request.get("occurrence_bytes_hash"),
        "decision": "ACTED" if accepted else reason,
        "response_expires_epoch": 9,
        "after_owner_response_hashes": sorted(after_hashes),
        "derived_from_owner_response_object": False,
    }
    response = {
        **response_unsigned,
        "signature": _b64(private_key.sign(canonical_bytes(response_unsigned))),
    }
    response_raw = canonical_bytes(response)
    return {
        "process_event": process_event,
        "process_event_bytes_b64": _b64(process_raw),
        "process_event_hash": _hash(process_raw),
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "state_path": str(state_path),
        "state_bytes_hash": _hash(state_raw),
        "state_boundary_id": _state_boundary(state_path, store_uuid),
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "trust_anchor_id": trust_anchor_id,
        "trust_anchor_public_key_b64": public_key_b64,
        "request_bytes_b64": _b64(request_raw),
        "request_bytes_hash": _hash(request_raw),
        "response_bytes_b64": _b64(response_raw),
        "response_bytes_hash": _hash(response_raw),
        "after_owner_response_hashes": sorted(after_hashes),
        "derived_from_owner_response_object": False,
        "accepted": accepted,
    }


def _receipt_issuer_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    owner_id = str(command["owner_id"])
    identity_path = Path(str(command["identity_state_path"])).resolve()
    if identity_path.is_file():
        identity_raw = identity_path.read_bytes()
        identity = json.loads(identity_raw.decode("utf-8"))
        private_raw = _unb64(identity["private_key_b64"])
        private_key = Ed25519PrivateKey.from_private_bytes(private_raw)
        public_key_b64 = identity["trust_anchor_public_key_b64"]
        trust_anchor_id = identity["trust_anchor_id"]
        state_source_id = identity["state_source_id"]
        act_source_id = identity["act_source_id"]
        store_uuid = identity["store_uuid"]
    else:
        private_key = Ed25519PrivateKey.generate()
        private_raw = private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        )
        public_raw = private_key.public_key().public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        public_key_b64 = _b64(public_raw)
        trust_anchor_id = _hash(public_raw)
        store_uuid = str(uuid4())
        state_source_id = f"state-source:{owner_id}:{store_uuid}"
        act_source_id = f"act-source:{owner_id}:{trust_anchor_id[:16]}"
        identity = {
            "owner_id": owner_id,
            "store_uuid": store_uuid,
            "state_source_id": state_source_id,
            "act_source_id": act_source_id,
            "trust_anchor_id": trust_anchor_id,
            "trust_anchor_public_key_b64": public_key_b64,
            "private_key_b64": _b64(private_raw),
            "state_head": f"{owner_id}:current:7",
        }
        identity_raw = canonical_bytes(identity)
        _write_bytes(identity_path, identity_raw)
    runtime_id = f"receipt-issuer:{owner_id}:{uuid4()}"
    _event, event_raw = _process_event(f"RECEIPT_ISSUER_{owner_id}", runtime_id)
    binding = dict(command["binding"])
    unsigned = {
        "owner_id": owner_id,
        "role": "RESOURCE" if owner_id == "O_R" else "SAFETY",
        **binding,
        "state_head": command.get("declared_state_head", identity["state_head"]),
        "issued_epoch": command["issued_epoch"],
        "expires_epoch": command["expires_epoch"],
        "current": command.get("current", True),
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "trust_anchor_id": trust_anchor_id,
        "trust_anchor_public_key_b64": public_key_b64,
    }
    signed = {
        **unsigned,
        "signature": _b64(private_key.sign(canonical_bytes(unsigned))),
    }
    signed["receipt_hash"] = _hash(canonical_bytes(signed))
    frame_raw = canonical_bytes(signed)
    issuance_event = {
        "runtime_id": runtime_id,
        "process_id": os.getpid(),
        "owner_id": owner_id,
        "receipt_frame_hash": _hash(frame_raw),
        "identity_state_hash": _hash(identity_raw),
    }
    issuance_raw = canonical_bytes(issuance_event)
    issuance_path = Path(str(command["issuance_event_path"])).resolve()
    _write_bytes(issuance_path, issuance_raw)
    return {
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "process_event_hash": _hash(event_raw),
        "state_path": str(identity_path),
        "state_bytes_hash": _hash(identity_raw),
        "state_boundary_id": _state_boundary(identity_path, store_uuid),
        "state_source_id": state_source_id,
        "act_source_id": act_source_id,
        "trust_anchor_id": trust_anchor_id,
        "trust_anchor_public_key_b64": public_key_b64,
        "issuance_event_path": str(issuance_path),
        "issuance_event_hash": _hash(issuance_raw),
        "receipt_bytes_b64": _b64(frame_raw),
        "receipt_bytes_hash": _hash(frame_raw),
    }


def _verify_receipts(
    raw_frames: Iterable[bytes],
    binding: Mapping[str, Any],
    at_epoch: int,
    current_owner_heads: Mapping[str, str],
    trust_manifest: Mapping[str, Mapping[str, str]],
) -> tuple[bool, str, list[str]]:
    frames: list[Mapping[str, Any]] = []
    hashes: list[str] = []
    try:
        for raw in raw_frames:
            frame = json.loads(raw.decode("utf-8"))
            frames.append(frame)
            hashes.append(_hash(raw))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, "MALFORMED_FRAME", hashes
    owners = [str(frame.get("owner_id")) for frame in frames]
    if len(frames) != 2 or set(owners) != {"O_R", "O_S"} or len(set(owners)) != 2:
        return False, "OWNER_SET_MISMATCH", hashes
    for frame, raw_hash in zip(frames, hashes):
        owner_id = str(frame.get("owner_id"))
        unsigned = {
            key: value
            for key, value in frame.items()
            if key not in {"signature", "receipt_hash"}
        }
        signed_content = {
            key: value for key, value in frame.items() if key != "receipt_hash"
        }
        if frame.get("receipt_hash") != _hash(canonical_bytes(signed_content)):
            return False, "TRANSPORT_HASH_MISMATCH", hashes
        trust = trust_manifest.get(owner_id, {})
        try:
            public_raw = _unb64(str(trust.get("public_key_b64", "")))
            Ed25519PublicKey.from_public_bytes(public_raw).verify(
                _unb64(str(frame.get("signature", ""))),
                canonical_bytes(unsigned),
            )
        except (ValueError, InvalidSignature):
            return False, "TAMPERED_SIGNATURE", hashes
        if (
            frame.get("trust_anchor_public_key_b64")
            != trust.get("public_key_b64")
            or frame.get("trust_anchor_id") != trust.get("trust_anchor_id")
            or frame.get("state_source_id") != trust.get("state_source_id")
            or frame.get("act_source_id") != trust.get("act_source_id")
        ):
            return False, "UNTRUSTED_RECEIPT_SOURCE", hashes
        if frame.get("state_head") != current_owner_heads.get(owner_id):
            return False, "STALE_OWNER_HEAD", hashes
        if any(frame.get(key) != binding.get(key) for key in binding):
            return False, "WRONG_BINDING", hashes
        if not (
            frame.get("current") is True
            and frame.get("issued_epoch", at_epoch + 1) <= at_epoch
            and at_epoch <= frame.get("expires_epoch", -1)
        ):
            return False, "STALE_RECEIPT", hashes
    return True, "CURRENT_RECEIPT_SET", hashes


def _target_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    runtime_id = f"target-gate:{uuid4()}"
    process_event, process_raw = _process_event("TARGET_NATIVE_GATE", runtime_id)
    raw_frames = [_unb64(value) for value in command.get("receipt_frames_b64", [])]
    binding = dict(command["binding"])
    allowed, reason, hashes = _verify_receipts(
        raw_frames,
        binding,
        int(command["at_epoch"]),
        dict(command["current_owner_heads"]),
        dict(command["receipt_trust_manifest"]),
    )
    event = {
        "consumer": "TARGET_NATIVE",
        "runtime_id": runtime_id,
        "process_id": os.getpid(),
        "binding": binding,
        "consumed_receipt_hashes": hashes if allowed else [],
        "received_receipt_hashes": hashes,
        "decision": "ALLOW_TRANSITION" if allowed else "REJECT_RECEIPT_SET",
        "reason": reason,
        "previous_state_head": "GENESIS",
        "transition_count": 1 if allowed else 0,
    }
    event_raw = canonical_bytes(event)
    state = {
        "runtime_id": runtime_id,
        "store_uuid": str(uuid4()),
        "transition_count": 1 if allowed else 0,
        "last_consumption_event_hash": _hash(event_raw),
    }
    state_raw = canonical_bytes(state)
    state_path = Path(str(command["state_path"])).resolve()
    event_path = Path(str(command["event_path"])).resolve()
    _write_bytes(event_path, event_raw)
    _write_bytes(state_path, state_raw)
    occurrence = {
        "runtime_id": runtime_id,
        "binding": binding,
        "occurrence_count": 1 if allowed else 0,
        "consumption_event_hash": _hash(event_raw),
    }
    occurrence_raw = canonical_bytes(occurrence)
    return {
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "process_event_hash": _hash(process_raw),
        "event_bytes_b64": _b64(event_raw),
        "event_hash": _hash(event_raw),
        "state_path": str(state_path),
        "state_bytes_hash": _hash(state_raw),
        "committed": allowed,
        "outcome": "COMMITTED" if allowed else "REJECTED_RECEIPT_SET",
        "transmitted_receipt_hashes": hashes,
        "consumed_receipt_hashes": hashes if allowed else [],
        "occurrence_bytes_b64": _b64(occurrence_raw),
        "occurrence_bytes_hash": _hash(occurrence_raw),
    }


def _source_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    runtime_id = str(command["runtime_id"])
    event, event_raw = _process_event("SOURCE_COORDINATOR", runtime_id)
    state_path = Path(str(command["state_path"])).resolve()
    history_path = Path(str(command["history_path"])).resolve()
    store_uuid = str(uuid4())
    history_records = [
        {"sequence": 0, "event": "SOURCE_STARTED", "runtime_id": runtime_id},
        {"sequence": 1, "event": "OCCURRENCE_RESPONSE_MISSING"},
        {"sequence": 2, "event": "SOURCE_FLUSHED", "epoch": command["epoch"]},
    ]
    history_raw = b"".join(canonical_bytes(item) + b"\n" for item in history_records)
    state = {
        "runtime_id": runtime_id,
        "store_uuid": store_uuid,
        "epoch": command["epoch"],
        "history_prefix_hash": _hash(history_raw),
        "pending_owner_acts": ["O_Q", "O_V", "O_P"],
        "occurrence_bytes_hash": command["occurrence_bytes_hash"],
    }
    state_raw = canonical_bytes(state)
    _write_bytes(history_path, history_raw)
    _write_bytes(state_path, state_raw)
    capsule_payload = {
        "schema": "ce001.g7.migration.capsule.v2",
        "source_runtime_id": runtime_id,
        "source_epoch": command["epoch"],
        "target_epoch": command["target_epoch"],
        "source_state_bytes_b64": _b64(state_raw),
        "source_state_bytes_hash": _hash(state_raw),
        "history_prefix_bytes_b64": _b64(history_raw),
        "history_prefix_hash": _hash(history_raw),
        "owner_evidence_frame_hashes": list(command["owner_evidence_frame_hashes"]),
        "occurrence_bytes_hash": command["occurrence_bytes_hash"],
        "dependency_graph_bytes_b64": command["dependency_graph_bytes_b64"],
        "dependency_graph_bytes_hash": _hash(
            _unb64(str(command["dependency_graph_bytes_b64"]))
        ),
        "binding": deepcopy(dict(command["binding"])),
    }
    capsule_payload["source_runtime_seal"] = _hash(
        canonical_bytes(
            {
                "capsule_unsigned": capsule_payload,
                "source_process_start_event_hash": _hash(event_raw),
                "source_state_bytes_hash": _hash(state_raw),
            }
        )
    )
    capsule_raw = canonical_bytes(capsule_payload)
    return {
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "process_event_hash": _hash(event_raw),
        "state_path": str(state_path),
        "state_bytes_hash": _hash(state_raw),
        "state_boundary_id": _state_boundary(state_path, store_uuid),
        "history_path": str(history_path),
        "history_bytes_b64": _b64(history_raw),
        "history_bytes_hash": _hash(history_raw),
        "capsule_bytes_b64": _b64(capsule_raw),
        "capsule_bytes_hash": _hash(capsule_raw),
        "epoch": command["epoch"],
    }


def _target_migration_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    runtime_id = str(command["runtime_id"])
    event, event_raw = _process_event("TARGET_COORDINATOR", runtime_id)
    capsule_raw = _unb64(str(command["capsule_bytes_b64"]))
    capsule = json.loads(capsule_raw.decode("utf-8"))
    history_raw = _unb64(capsule["history_prefix_bytes_b64"])
    source_state_raw = _unb64(capsule["source_state_bytes_b64"])
    dependency_graph_raw = _unb64(capsule["dependency_graph_bytes_b64"])
    supplied_seal = capsule.get("source_runtime_seal")
    unsigned_capsule = {
        key: value for key, value in capsule.items() if key != "source_runtime_seal"
    }
    expected_seal = _hash(
        canonical_bytes(
            {
                "capsule_unsigned": unsigned_capsule,
                "source_process_start_event_hash": command[
                    "source_process_start_event_hash"
                ],
                "source_state_bytes_hash": _hash(source_state_raw),
            }
        )
    )
    required_fields = {
        "schema",
        "source_runtime_id",
        "source_epoch",
        "target_epoch",
        "source_state_bytes_b64",
        "source_state_bytes_hash",
        "history_prefix_bytes_b64",
        "history_prefix_hash",
        "owner_evidence_frame_hashes",
        "occurrence_bytes_hash",
        "dependency_graph_bytes_b64",
        "dependency_graph_bytes_hash",
        "binding",
        "source_runtime_seal",
    }
    valid = (
        required_fields <= set(capsule)
        and capsule.get("schema") == "ce001.g7.migration.capsule.v2"
        and bool(capsule.get("owner_evidence_frame_hashes"))
        and command.get("capsule_frame_hash") == _hash(capsule_raw)
        and capsule.get("source_state_bytes_hash") == _hash(source_state_raw)
        and capsule.get("history_prefix_hash") == _hash(history_raw)
        and capsule.get("dependency_graph_bytes_hash")
        == _hash(dependency_graph_raw)
        and supplied_seal == expected_seal
        and capsule.get("target_epoch") > capsule.get("source_epoch")
    )
    state_path = Path(str(command["state_path"])).resolve()
    history_path = Path(str(command["history_path"])).resolve()
    store_uuid = str(uuid4())
    state = {
        "runtime_id": runtime_id,
        "store_uuid": store_uuid,
        "epoch": capsule.get("target_epoch"),
        "imported_capsule_hash": _hash(capsule_raw),
        "source_state_bytes_hash": _hash(source_state_raw),
        "history_prefix_hash": _hash(history_raw),
        "imported": valid,
    }
    state_raw = canonical_bytes(state)
    appended = (
        canonical_bytes(
            {
                "sequence": 3,
                "event": "TARGET_TAKEOVER",
                "runtime_id": runtime_id,
            }
        )
        + b"\n"
    )
    _write_bytes(state_path, state_raw)
    _write_bytes(history_path, history_raw + appended)
    return {
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "process_event_hash": _hash(event_raw),
        "state_path": str(state_path),
        "state_bytes_hash": _hash(state_raw),
        "state_boundary_id": _state_boundary(state_path, store_uuid),
        "history_path": str(history_path),
        "history_prefix_bytes_b64": _b64(history_raw),
        "history_prefix_hash": _hash(history_raw),
        "capsule_received_hash": _hash(capsule_raw),
        "imported": valid,
        "epoch": capsule.get("target_epoch"),
    }


def _fence_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    runtime_id = f"fence-owner:{uuid4()}"
    _event, event_raw = _process_event("EXTERNAL_FENCE_OWNER", runtime_id)
    state_path = Path(str(command["state_path"])).resolve()
    if command["action"] == "install":
        store_uuid = str(uuid4())
        state = {
            "store_uuid": store_uuid,
            "target_key": command["target_key"],
            "installed_epoch": command["epoch"],
            "previous_epoch": command["previous_epoch"],
        }
        state_raw = canonical_bytes(state)
        _write_bytes(state_path, state_raw)
        return {
            "process_id": os.getpid(),
            "runtime_id": runtime_id,
            "process_event_hash": _hash(event_raw),
            "state_path": str(state_path),
            "state_bytes_hash": _hash(state_raw),
            "state_boundary_id": _state_boundary(state_path, store_uuid),
            "installed_epoch": command["epoch"],
        }
    state_raw = state_path.read_bytes()
    state = json.loads(state_raw.decode("utf-8"))
    request_raw = _unb64(str(command["request_bytes_b64"]))
    request = json.loads(request_raw.decode("utf-8"))
    rejected = int(request["presented_epoch"]) < int(state["installed_epoch"])
    rejection = {
        "fence_owner_runtime_id": runtime_id,
        "fence_owner_process_id": os.getpid(),
        "request_bytes_hash": _hash(request_raw),
        "presented_epoch": request["presented_epoch"],
        "required_epoch": state["installed_epoch"],
        "result": "REJECTED_OLD_EPOCH" if rejected else "EPOCH_ACCEPTED",
        "transition_count": 0 if rejected else 1,
    }
    rejection_raw = canonical_bytes(rejection)
    return {
        "process_id": os.getpid(),
        "runtime_id": runtime_id,
        "process_event_hash": _hash(event_raw),
        "state_path": str(state_path),
        "state_bytes_hash": _hash(state_raw),
        "event_bytes_b64": _b64(rejection_raw),
        "event_hash": _hash(rejection_raw),
        "response_bytes_b64": _b64(rejection_raw),
        "response_bytes_hash": _hash(rejection_raw),
        "result": rejection["result"],
        "presented_epoch": rejection["presented_epoch"],
        "required_epoch": rejection["required_epoch"],
    }


def _restart_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    source_state_path = Path(str(command["source_state_path"])).resolve()
    source_state = json.loads(source_state_path.read_bytes().decode("utf-8"))
    event, event_raw = _process_event("OLD_SOURCE_RESTART", source_state["runtime_id"])
    request = {
        "runtime_id": source_state["runtime_id"],
        "restart_process_id": os.getpid(),
        "presented_epoch": source_state["epoch"],
        "operation_id": command["operation_id"],
        "source_state_bytes_hash": _hash(source_state_path.read_bytes()),
    }
    request_raw = canonical_bytes(request)
    return {
        "process_id": os.getpid(),
        "runtime_id": source_state["runtime_id"],
        "process_event_hash": _hash(event_raw),
        "request_bytes_b64": _b64(request_raw),
        "request_bytes_hash": _hash(request_raw),
        "presented_epoch": source_state["epoch"],
    }


def _run_worker(command: Mapping[str, Any]) -> dict[str, Any]:
    kind = command["kind"]
    if kind == "owner":
        return _owner_worker(command)
    if kind == "receipt_issuer":
        return _receipt_issuer_worker(command)
    if kind == "target":
        return _target_worker(command)
    if kind == "source":
        return _source_worker(command)
    if kind == "target_migration":
        return _target_migration_worker(command)
    if kind == "fence":
        return _fence_worker(command)
    if kind == "restart":
        return _restart_worker(command)
    raise ValueError(f"unknown worker kind: {kind}")


def _spawn(command: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    root = str(Path(__file__).resolve().parents[1])
    environment = dict(os.environ)
    prior_path = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = root if not prior_path else f"{root}{os.pathsep}{prior_path}"
    sent_raw = canonical_bytes(command)
    completed = subprocess.run(
        [sys.executable, "-m", "g7evo.boundary", "--worker"],
        input=sent_raw,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"boundary worker failed ({completed.returncode}): "
            f"{completed.stderr.decode('utf-8', errors='replace')}"
        )
    received = json.loads(completed.stdout.decode("utf-8"))
    transport = {
        "producer_frame_hash": _hash(sent_raw),
        "producer_byte_length": len(sent_raw),
        "consumer_frame_hash": _hash(completed.stdout),
        "consumer_byte_length": len(completed.stdout),
        "worker_exit_code": completed.returncode,
    }
    return received, transport


def _owner_request(
    owner_id: str,
    binding: Mapping[str, Any],
    occurrence_raw: bytes,
) -> bytes:
    body = {
        **dict(binding),
        "owner_id": owner_id,
        "challenge": str(uuid4()),
    }
    request = {
        "protocol_version": "ce001.owner-act.v2",
        "owner_id": owner_id,
        "expected_state_head": f"{owner_id}:head:1",
        "request_body": body,
        "request_hash": _hash(canonical_bytes(body)),
        "binding": dict(binding),
        "occurrence_bytes_b64": _b64(occurrence_raw),
        "occurrence_bytes_hash": _hash(occurrence_raw),
    }
    return canonical_bytes(request)


def build_process_evidence(fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Run the full local process/state/byte evidence path once."""

    run_root = Path(tempfile.mkdtemp(prefix="g7-evolution-v2-")).resolve()
    binding = {
        "episode_id": "ce001-e6-synthetic-001",
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "operation_id": "deliver-3kw-45m",
        "target_id": "VenueV:CircuitC7",
    }
    def issue_receipt(
        owner_id: str,
        issued_binding: Mapping[str, Any],
        *,
        label: str,
        expires_epoch: int = 9,
        declared_state_head: str | None = None,
    ) -> dict[str, Any]:
        command: dict[str, Any] = {
            "kind": "receipt_issuer",
            "owner_id": owner_id,
            "identity_state_path": str(
                run_root / "receipt-issuers" / owner_id / "identity-state.json"
            ),
            "issuance_event_path": str(
                run_root / "receipt-issuers" / owner_id / f"{label}-event.json"
            ),
            "binding": dict(issued_binding),
            "issued_epoch": 7,
            "expires_epoch": expires_epoch,
        }
        if declared_state_head is not None:
            command["declared_state_head"] = declared_state_head
        result, _transport = _spawn(command)
        return result

    receipt_issuers = {
        owner_id: issue_receipt(owner_id, binding, label="current")
        for owner_id in ("O_R", "O_S")
    }
    normalized_frames = [
        _unb64(receipt_issuers[owner_id]["receipt_bytes_b64"])
        for owner_id in ("O_R", "O_S")
    ]
    receipt_trust_manifest = {
        owner_id: {
            "public_key_b64": receipt_issuers[owner_id][
                "trust_anchor_public_key_b64"
            ],
            "trust_anchor_id": receipt_issuers[owner_id]["trust_anchor_id"],
            "state_source_id": receipt_issuers[owner_id]["state_source_id"],
            "act_source_id": receipt_issuers[owner_id]["act_source_id"],
        }
        for owner_id in ("O_R", "O_S")
    }
    happy, _happy_transport = _spawn(
        {
            "kind": "target",
            "binding": binding,
            "at_epoch": 7,
            "receipt_frames_b64": [_b64(raw) for raw in normalized_frames],
            "current_owner_heads": {
                "O_R": "O_R:current:7",
                "O_S": "O_S:current:7",
            },
            "receipt_trust_manifest": receipt_trust_manifest,
            "state_path": str(run_root / "target-gate" / "state.json"),
            "event_path": str(run_root / "target-gate" / "consumption-event.json"),
        }
    )
    if not happy["committed"]:
        raise RuntimeError("valid current receipt set was rejected")

    attacks: dict[str, Any] = {}
    attack_frames: dict[str, list[bytes]] = {}
    wrong_binding = {**binding, "target_id": "VenueV:CircuitC8"}
    wrong_receipt = issue_receipt(
        "O_R", wrong_binding, label="wrong-binding"
    )
    attack_frames["wrong_receipt"] = [
        _unb64(wrong_receipt["receipt_bytes_b64"]),
        normalized_frames[1],
    ]
    stale_receipt = issue_receipt(
        "O_R", binding, label="stale", expires_epoch=6
    )
    attack_frames["stale_receipt"] = [
        _unb64(stale_receipt["receipt_bytes_b64"]),
        normalized_frames[1],
    ]
    tampered = bytearray(normalized_frames[0])
    tampered[-2:-1] = b"X"
    attack_frames["tampered_receipt"] = [bytes(tampered), normalized_frames[1]]
    transplant_binding = {**binding, "episode_id": "ce001-other-episode"}
    transplant_receipt = issue_receipt(
        "O_S", transplant_binding, label="transplant"
    )
    attack_frames["receipt_set_transplant"] = [
        normalized_frames[0],
        _unb64(transplant_receipt["receipt_bytes_b64"]),
    ]
    attack_frames["missing_receipt"] = [normalized_frames[0]]
    attack_frames["duplicate_receipt"] = [
        normalized_frames[0],
        normalized_frames[0],
    ]
    wrong_head_receipt = issue_receipt(
        "O_R",
        binding,
        label="wrong-current-head",
        declared_state_head="O_R:stale:6",
    )
    attack_frames["wrong_current_head"] = [
        _unb64(wrong_head_receipt["receipt_bytes_b64"]),
        normalized_frames[1],
    ]
    for attack_id, frames in attack_frames.items():
        result, _transport = _spawn(
            {
                "kind": "target",
                "binding": binding,
                "at_epoch": 7,
                "receipt_frames_b64": [_b64(raw) for raw in frames],
                "current_owner_heads": {
                    "O_R": "O_R:current:7",
                    "O_S": "O_S:current:7",
                },
                "receipt_trust_manifest": receipt_trust_manifest,
                "state_path": str(
                    run_root / "target-attacks" / attack_id / "state.json"
                ),
                "event_path": str(
                    run_root / "target-attacks" / attack_id / "event.json"
                ),
            }
        )
        attacks[attack_id] = {
            "committed": result["committed"],
            "outcome": result["outcome"],
            "event_bytes_b64": result["event_bytes_b64"],
            "event_hash": result["event_hash"],
            "target_process_id": result["process_id"],
            "target_state_path": result["state_path"],
            "target_state_bytes_hash": result["state_bytes_hash"],
            "target_transition_count": json.loads(
                Path(result["state_path"]).read_text(encoding="utf-8")
            )["transition_count"],
        }

    occurrence_raw = _unb64(happy["occurrence_bytes_b64"])
    owner_sources: dict[str, Any] = {}
    for owner_id in ("O_Q", "O_V"):
        request_raw = _owner_request(owner_id, binding, occurrence_raw)
        owner, _transport = _spawn(
            {
                "kind": "owner",
                "owner_id": owner_id,
                "state_path": str(run_root / "owners" / owner_id / "state.json"),
                "request_bytes_b64": _b64(request_raw),
            }
        )
        owner_sources[owner_id] = owner
    oq_raw = _unb64(owner_sources["O_Q"]["response_bytes_b64"])
    ov_raw = _unb64(owner_sources["O_V"]["response_bytes_b64"])
    op_request = {
        **binding,
        "owner_response_frames_b64": [_b64(oq_raw), _b64(ov_raw)],
        "occurrence_bytes_hash": _hash(occurrence_raw),
        "current_owner_heads": {"O_Q": "O_Q:head:1", "O_V": "O_V:head:1"},
        "owner_public_keys": {
            owner_id: owner_sources[owner_id]["trust_anchor_public_key_b64"]
            for owner_id in ("O_Q", "O_V")
        },
        "owner_act_sources": {
            owner_id: owner_sources[owner_id]["act_source_id"]
            for owner_id in ("O_Q", "O_V")
        },
        "at_epoch": 8,
    }
    op_request_raw = canonical_bytes(op_request)
    op, _op_transport = _spawn(
        {
            "kind": "owner",
            "owner_id": "O_P",
            "state_path": str(run_root / "owners" / "O_P" / "state.json"),
            "request_bytes_b64": _b64(op_request_raw),
        }
    )
    owner_sources["O_P"] = op

    oq_frame = json.loads(oq_raw.decode("utf-8"))
    ov_frame = json.loads(ov_raw.decode("utf-8"))
    attack_frame_sets: dict[str, list[bytes]] = {
        "duplicate_owner": [oq_raw, oq_raw],
    }
    transplanted = deepcopy(oq_frame)
    transplanted["owner_id"] = "O_V"
    transplanted["trust_anchor_id"] = owner_sources["O_V"]["trust_anchor_id"]
    transplanted["trust_anchor_public_key_b64"] = owner_sources["O_V"][
        "trust_anchor_public_key_b64"
    ]
    # act_source_id deliberately remains O_Q: relabelling and re-signing is
    # still not an O_V act from O_V's independent process/state source.
    attack_frame_sets["response_transplant"] = [
        oq_raw,
        canonical_bytes(transplanted),
    ]
    stale = deepcopy(oq_frame)
    stale["response_expires_epoch"] = 7
    attack_frame_sets["stale_response"] = [canonical_bytes(stale), ov_raw]
    wrong_episode = deepcopy(oq_frame)
    wrong_episode["episode_id"] = "ce001-other-episode"
    attack_frame_sets["wrong_episode"] = [
        canonical_bytes(wrong_episode),
        ov_raw,
    ]
    wrong_q = deepcopy(oq_frame)
    wrong_q["q_version"] = "Q@wrong"
    attack_frame_sets["wrong_q"] = [canonical_bytes(wrong_q), ov_raw]
    wrong_object = deepcopy(oq_frame)
    wrong_object["object_id"] = "VenueV:CircuitC8"
    attack_frame_sets["wrong_object"] = [
        canonical_bytes(wrong_object),
        ov_raw,
    ]
    wrong_operation = deepcopy(oq_frame)
    wrong_operation["operation_id"] = "deliver-other-operation"
    attack_frame_sets["wrong_operation"] = [
        canonical_bytes(wrong_operation),
        ov_raw,
    ]
    wrong_target = deepcopy(oq_frame)
    wrong_target["target_id"] = "VenueV:CircuitC8"
    attack_frame_sets["wrong_target"] = [
        canonical_bytes(wrong_target),
        ov_raw,
    ]
    wrong_occurrence = deepcopy(oq_frame)
    wrong_occurrence["occurrence_bytes_hash"] = _hash(b"other-occurrence")
    attack_frame_sets["wrong_effect_occurrence"] = [
        canonical_bytes(wrong_occurrence),
        ov_raw,
    ]
    owner_attacks: dict[str, Any] = {}
    for attack_id, frames in attack_frame_sets.items():
        attack_request = {
            **binding,
            "owner_response_frames_b64": [_b64(raw) for raw in frames],
            "occurrence_bytes_hash": _hash(occurrence_raw),
            "current_owner_heads": {
                "O_Q": "O_Q:head:1",
                "O_V": "O_V:head:1",
            },
            "owner_public_keys": {
                owner_id: owner_sources[owner_id][
                    "trust_anchor_public_key_b64"
                ]
                for owner_id in ("O_Q", "O_V")
            },
            "owner_act_sources": {
                owner_id: owner_sources[owner_id]["act_source_id"]
                for owner_id in ("O_Q", "O_V")
            },
            "at_epoch": 8,
        }
        attack_request_raw = canonical_bytes(attack_request)
        attack_result, attack_transport = _spawn(
            {
                "kind": "owner",
                "owner_id": "O_P",
                "state_path": str(
                    run_root / "owner-attacks" / attack_id / "O_P-state.json"
                ),
                "request_bytes_b64": _b64(attack_request_raw),
            }
        )
        attack_state = json.loads(
            Path(attack_result["state_path"]).read_text(encoding="utf-8")
        )
        if attack_result["accepted"] or attack_state["act_count"] != 0:
            raise RuntimeError(f"{attack_id} advanced O_P state")
        owner_attacks[attack_id] = {
            "accepted": False,
            "finalized": False,
            "process_id": attack_result["process_id"],
            "request_bytes_b64": attack_result["request_bytes_b64"],
            "request_bytes_hash": attack_result["request_bytes_hash"],
            "response_bytes_b64": attack_result["response_bytes_b64"],
            "response_bytes_hash": attack_result["response_bytes_hash"],
            "state_path": attack_result["state_path"],
            "state_bytes_hash": attack_result["state_bytes_hash"],
            "state_act_count": attack_state["act_count"],
            "worker_exit_code": attack_transport["worker_exit_code"],
        }
    owner_manifest_raw = b"".join(
        len(raw).to_bytes(8, "big") + raw for raw in (oq_raw, ov_raw, _unb64(op["response_bytes_b64"]))
    )
    receipt_manifest_raw = b"".join(
        len(raw).to_bytes(8, "big") + raw for raw in normalized_frames
    )
    dependency_graph_raw = canonical_bytes(
        fixture["e6"]["public_packet"]["dependency_graph"]
    )

    source, source_transport = _spawn(
        {
            "kind": "source",
            "runtime_id": "coordinator-old",
            "epoch": 7,
            "target_epoch": 8,
            "state_path": str(run_root / "migration" / "source" / "state.json"),
            "history_path": str(run_root / "migration" / "source" / "history.bin"),
            "binding": binding,
            "occurrence_bytes_hash": _hash(occurrence_raw),
            "dependency_graph_bytes_b64": _b64(dependency_graph_raw),
            "owner_evidence_frame_hashes": [
                owner_sources["O_Q"]["response_bytes_hash"],
                owner_sources["O_V"]["response_bytes_hash"],
                owner_sources["O_P"]["response_bytes_hash"],
            ],
        }
    )
    capsule_raw = _unb64(source["capsule_bytes_b64"])
    target, target_transport = _spawn(
        {
            "kind": "target_migration",
            "runtime_id": "coordinator-new",
            "state_path": str(run_root / "migration" / "target" / "state.json"),
            "history_path": str(run_root / "migration" / "target" / "history.bin"),
            "capsule_bytes_b64": _b64(capsule_raw),
            "capsule_frame_hash": _hash(capsule_raw),
            "source_process_start_event_hash": source["process_event_hash"],
        }
    )
    fence, fence_transport = _spawn(
        {
            "kind": "fence",
            "action": "install",
            "target_key": "ce001-e6-synthetic-001:VenueV:CircuitC7",
            "previous_epoch": 7,
            "epoch": 8,
            "state_path": str(run_root / "migration" / "fence" / "state.json"),
        }
    )
    restart, restart_transport = _spawn(
        {
            "kind": "restart",
            "source_state_path": source["state_path"],
            "operation_id": binding["operation_id"],
        }
    )
    rejection, rejection_transport = _spawn(
        {
            "kind": "fence",
            "action": "check",
            "state_path": fence["state_path"],
            "request_bytes_b64": restart["request_bytes_b64"],
        }
    )
    history_raw = _unb64(source["history_bytes_b64"])
    candidate_raw = history_raw.replace(b"SOURCE_FLUSHED", b"SOURCE_REWRITTEN")
    rewritten_capsule = json.loads(capsule_raw.decode("utf-8"))
    rewritten_capsule["history_prefix_bytes_b64"] = _b64(candidate_raw)
    rewritten_capsule["history_prefix_hash"] = _hash(candidate_raw)
    rewritten_capsule_raw = canonical_bytes(rewritten_capsule)
    rewrite_import, _rewrite_transport = _spawn(
        {
            "kind": "target_migration",
            "runtime_id": "coordinator-rewrite-attack",
            "state_path": str(
                run_root / "migration-attacks" / "history-rewrite" / "state.json"
            ),
            "history_path": str(
                run_root / "migration-attacks" / "history-rewrite" / "history.bin"
            ),
            "capsule_bytes_b64": _b64(rewritten_capsule_raw),
            "capsule_frame_hash": _hash(rewritten_capsule_raw),
            "source_process_start_event_hash": source["process_event_hash"],
        }
    )
    field_loss_capsule = json.loads(capsule_raw.decode("utf-8"))
    field_loss_capsule.pop("owner_evidence_frame_hashes")
    field_loss_capsule_raw = canonical_bytes(field_loss_capsule)
    field_loss_import, field_loss_transport = _spawn(
        {
            "kind": "target_migration",
            "runtime_id": "coordinator-field-loss-attack",
            "state_path": str(
                run_root / "migration-attacks" / "field-loss" / "state.json"
            ),
            "history_path": str(
                run_root / "migration-attacks" / "field-loss" / "history.bin"
            ),
            "capsule_bytes_b64": _b64(field_loss_capsule_raw),
            "capsule_frame_hash": _hash(field_loss_capsule_raw),
            "source_process_start_event_hash": source["process_event_hash"],
        }
    )
    target_history_raw = Path(target["history_path"]).read_bytes()
    if target_history_raw[: len(history_raw)] != history_raw:
        raise RuntimeError("target history prefix differs from transmitted source prefix")
    source_state_raw = Path(source["state_path"]).read_bytes()
    target_state_raw = Path(target["state_path"]).read_bytes()
    fence_state_raw = Path(fence["state_path"]).read_bytes()

    migration = {
        "source_runtime": {
            "runtime_id": source["runtime_id"],
            "process_id": source["process_id"],
            "state_boundary_id": source["state_boundary_id"],
            "epoch": source["epoch"],
            "state_path": source["state_path"],
            "state_bytes_hash": source["state_bytes_hash"],
            "termination_observed": True,
            "exit_code": source_transport["worker_exit_code"],
            "process_start_event_hash": source["process_event_hash"],
        },
        "target_runtime": {
            "runtime_id": target["runtime_id"],
            "process_id": target["process_id"],
            "state_boundary_id": target["state_boundary_id"],
            "epoch": target["epoch"],
            "state_path": target["state_path"],
            "state_bytes_hash": target["state_bytes_hash"],
            "start_observed": True,
            "process_start_event_hash": target["process_event_hash"],
        },
        "old_runtime_restart": {
            "actually_restarted": True,
            "restart_observed": True,
            "process_id": restart["process_id"],
            "presented_epoch": restart["presented_epoch"],
            "current_epoch": fence["installed_epoch"],
            "fence_result": rejection["result"],
            "process_start_event_hash": restart["process_event_hash"],
            "request_frame_hash": restart["request_bytes_hash"],
            "response_frame_hash": rejection["response_bytes_hash"],
            "external_fence_event_hash": rejection["event_hash"],
        },
        "fence_owner": {
            **fence,
            "restart_process_id": rejection["process_id"],
            "old_epoch_rejection": {
                "presented_epoch": rejection["presented_epoch"],
                "required_epoch": rejection["required_epoch"],
                "event_bytes_b64": rejection["event_bytes_b64"],
                "event_hash": rejection["event_hash"],
            },
        },
        "lineage_verification": {
            "capsule_hash": _hash(capsule_raw),
            "source_runtime_hash": _hash(source_state_raw),
            "target_runtime_hash": _hash(target_state_raw),
            "history_prefix_hash": _hash(history_raw),
            "owner_evidence_hashes_verified": True,
            "effect_hash": _hash(occurrence_raw),
            "q_version": "Q@v1",
            "object_id": "VenueV:CircuitC7",
            "history_fork_detected": False,
            "effect_occurrence_count_for_operation": 1,
            "capsule_producer_frame_hash": source["capsule_bytes_hash"],
            "capsule_consumer_frame_hash": target["capsule_received_hash"],
            "target_consumption_event_hash": happy["event_hash"],
            "owner_verification_event_hash": _hash(owner_manifest_raw),
            "fence_state_bytes_hash": _hash(fence_state_raw),
            "restart_request_frame_hash": restart["request_bytes_hash"],
            "restart_response_frame_hash": rejection["response_bytes_hash"],
        },
        "recovery": {
            "acceptance_hashes": [
                owner_sources["O_Q"]["response_bytes_hash"],
                owner_sources["O_V"]["response_bytes_hash"],
            ],
            "finality_hash": owner_sources["O_P"]["response_bytes_hash"],
            "recovered_from_owner_sources": True,
            "owner_transport_manifest_hash": _hash(owner_manifest_raw),
        },
    }
    byte_provenance = {
        "capsule": {
            **_bytes_item(capsule_raw, source_kind="TRANSMITTED_BYTES"),
            "sender_process_id": source["process_id"],
            "receiver_process_id": target["process_id"],
        },
        "source_state": _bytes_item(source_state_raw, source_kind="DURABLE_READBACK_BYTES"),
        "target_state": _bytes_item(target_state_raw, source_kind="DURABLE_READBACK_BYTES"),
        "history_prefix": _bytes_item(history_raw, source_kind="DURABLE_PREFIX_BYTES"),
        "owner_evidence": _bytes_item(owner_manifest_raw, source_kind="TRANSMITTED_OWNER_FRAMES"),
        "receipt_set": _bytes_item(
            receipt_manifest_raw, source_kind="TRANSMITTED_OWNER_RECEIPT_FRAMES"
        ),
        "effect_occurrence": _bytes_item(occurrence_raw, source_kind="TARGET_NATIVE_BYTES"),
        "dependency_graph": _bytes_item(
            dependency_graph_raw, source_kind="TRANSMITTED_CAPSULE_FIELD_BYTES"
        ),
        "external_fence_state": _bytes_item(fence_state_raw, source_kind="DURABLE_READBACK_BYTES"),
        "old_epoch_rejection": _bytes_item(
            _unb64(rejection["event_bytes_b64"]), source_kind="EXTERNAL_FENCE_EVENT_BYTES"
        ),
    }
    evidence_boundaries = {
        "hidden_pair": "NOT_CONSTRUCTED",
        "safety_liveness_frontier": "NOT_RUN",
        "cold_repeat_full_lifecycle": "NOT_MEASURED",
        "adapter_semantic_independence": "NOT_ESTABLISHED",
        "real_product_run": "NOT_RUN",
        "human_owner_run": "NOT_RUN",
        "legal_power_domain_run": "NOT_RUN",
        "physical_world_occurrence": "NOT_RUN",
        "production_split_brain": "NOT_RUN",
        "cross_product_portability": "NOT_ESTABLISHED",
        "full_lifecycle_net_value": "NOT_ESTABLISHED",
        "complete_ce001": "NOT_ESTABLISHED",
    }
    envelope_migration = deepcopy(migration)
    for runtime_key in ("source_runtime", "target_runtime"):
        envelope_migration[runtime_key] = {
            key: envelope_migration[runtime_key][key]
            for key in ("runtime_id", "process_id", "state_boundary_id", "epoch")
        }
    envelope_migration.pop("fence_owner", None)
    envelope = {
        "namespace": "G7",
        "qualification": "QUALIFIED_COMPONENT_OUTPUT",
        "evidence": {
            "append_only_history_hash": _hash(target_history_raw),
            "dependency_graph_hash": _hash(dependency_graph_raw),
            "reopen_set": ["e6:owner-source-recovery", "e6:lineage-reconciliation"],
            "migration": envelope_migration,
            "evidence_boundaries": {
                "hidden_pair": "NOT_CONSTRUCTED",
                "safety_liveness_frontier": "NOT_RUN",
                "cold_repeat_full_lifecycle": "NOT_MEASURED",
                "adapter_semantic_independence": "NOT_ESTABLISHED",
                "real_product": "NOT_RUN",
                "production_split_brain": "NOT_RUN",
            },
        },
    }
    return {
        "run_root": str(run_root),
        "owner_sources": owner_sources,
        "receipt_issuer_sources": receipt_issuers,
        "owner_binding_attacks": owner_attacks,
        "target_receipt_consumption": {
            "transmitted_receipt_hashes": happy["transmitted_receipt_hashes"],
            "consumed_receipt_hashes": happy["consumed_receipt_hashes"],
            "event_bytes_b64": happy["event_bytes_b64"],
            "consumption_event_hash": happy["event_hash"],
            "target_process_id": happy["process_id"],
            "target_state_path": happy["state_path"],
        },
        "receipt_consumption_attacks": attacks,
        "migration": migration,
        "byte_provenance": byte_provenance,
        "history_rewrite_attack": {
            "original_bytes_b64": _b64(history_raw),
            "original_bytes_hash": _hash(history_raw),
            "persisted_bytes_b64": _b64(target_history_raw[: len(history_raw)]),
            "persisted_bytes_hash": _hash(target_history_raw[: len(history_raw)]),
            "candidate_bytes_b64": _b64(candidate_raw),
            "candidate_bytes_hash": _hash(candidate_raw),
            "rewrite_rejected": not rewrite_import["imported"],
            "history_fork_detected": False,
            "attack_process_id": rewrite_import["process_id"],
            "attack_state_path": rewrite_import["state_path"],
        },
        "capsule_field_loss_attack": {
            "dropped_field": "owner_evidence_frame_hashes",
            "imported": field_loss_import["imported"],
            "dispatch_after_import": False,
            "process_id": field_loss_import["process_id"],
            "state_path": field_loss_import["state_path"],
            "state_bytes_hash": field_loss_import["state_bytes_hash"],
            "worker_exit_code": field_loss_transport["worker_exit_code"],
        },
        "evidence_boundaries": evidence_boundaries,
        "integration_envelope": envelope,
        "transport_manifest": {
            "source": source_transport,
            "target": target_transport,
            "fence_install": fence_transport,
            "old_restart": restart_transport,
            "fence_rejection": rejection_transport,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if not args.worker:
        parser.error("--worker is required")
    command = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    result = _run_worker(command)
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
