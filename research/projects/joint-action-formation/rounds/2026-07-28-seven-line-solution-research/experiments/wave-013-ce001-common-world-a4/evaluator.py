#!/usr/bin/env python3
"""Independent evaluator for the CE-001 E1/E5 common-world vertical slice.

The evaluator deliberately has no dependency on the world author, owner
services, or the A4 executor.  Its only input is a frozen run bundle.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


E1 = "E1-EXTANT-MULTI-OWNER"
E5 = "E5-IMPOSSIBLE-REFUSAL"
ARM = "A4-DETERMINISTIC-MATURE-COMPOSITION"
OWNER_IDS = ("O_Q", "O_V", "O_R", "O_S", "O_P", "O_E")
FRAGMENT_IDS = tuple(f"G{i}" for i in range(1, 8))
CONTRACT_FIELDS = {
    "ExactTaskSuccess",
    "CorrectResolution",
    "SafeHandling",
    "UnsafeEffect",
    "DuplicateEffect",
    "WrongObjectReliance",
    "UnreconciledEffect",
    "UnnecessaryFormation",
}
HEX_CHARS = frozenset("0123456789abcdef")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def object_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _without(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {key: copy.deepcopy(item) for key, item in value.items() if key not in keys}


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in HEX_CHARS for char in value)
    )


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _event_kind(value: Mapping[str, Any]) -> str:
    return str(value.get("kind", value.get("event_type", value.get("type", "")))).upper()


def _payload_kind(response: Mapping[str, Any]) -> str:
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        return ""
    return str(payload.get("kind", payload.get("act_type", payload.get("type", "")))).upper()


def _decision(response: Mapping[str, Any]) -> str:
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        return ""
    return str(payload.get("decision", payload.get("status", ""))).upper()


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _owner_entries(raw: Any) -> tuple[list[Mapping[str, Any]], Optional[str]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)], None
    if isinstance(raw, Mapping):
        entries = raw.get("entries", raw.get("responses", []))
        return [item for item in _as_list(entries) if isinstance(item, Mapping)], raw.get(
            "state_head"
        )
    return [], None


def _target_entries(raw: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if isinstance(raw.get("entries"), list):
        return [item for item in raw["entries"] if isinstance(item, Mapping)]
    combined: list[Mapping[str, Any]] = []
    for key in ("occurrences", "sensor_samples", "readbacks", "responses"):
        combined.extend(item for item in _as_list(raw.get(key)) if isinstance(item, Mapping))
    return combined


def _verify_signature(
    public_key_hex: Any,
    signature_hex: Any,
    message: bytes,
) -> bool:
    try:
        if not isinstance(public_key_hex, str) or not isinstance(signature_hex, str):
            return False
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(bytes.fromhex(signature_hex), message)
        return True
    except (ValueError, InvalidSignature):
        return False


def _required_binding_errors(
    value: Mapping[str, Any],
    manifest: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    for field in ("run_id", "world_root", "q_version", "object_id", "operation_id"):
        if value.get(field) != manifest.get(field):
            errors.append(f"{prefix}.{field}: binding mismatch")
    if value.get("arm_binding_token") != manifest.get("arm_binding_token"):
        errors.append(f"{prefix}.arm_binding_token: binding mismatch")
    return errors


def _transport_binding_errors(
    value: Mapping[str, Any],
    manifest: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    for field in ("run_id", "world_root", "object_id", "operation_id"):
        if value.get(field) != manifest.get(field):
            errors.append(f"{prefix}.{field}: binding mismatch")
    if value.get("arm_binding_token") != manifest.get("arm_binding_token"):
        errors.append(f"{prefix}.arm_binding_token: binding mismatch")
    return errors


def _provenance_binding_errors(
    value: Mapping[str, Any],
    manifest: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    errors: list[str] = []
    for field in ("run_id", "world_root", "q_version"):
        if value.get(field) != manifest.get(field):
            errors.append(f"{prefix}.{field}: binding mismatch")
    if value.get("arm_binding_token") != manifest.get("arm_binding_token"):
        errors.append(f"{prefix}.arm_binding_token: binding mismatch")
    return errors


def _find_contract_field(value: Any, path: str = "$") -> Optional[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in CONTRACT_FIELDS:
                return f"{path}.{key}"
            found = _find_contract_field(item, f"{path}.{key}")
            if found:
                return found
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found = _find_contract_field(item, f"{path}[{index}]")
            if found:
                return found
    return None


class BundleEvidence:
    """Validate byte binding and expose only verified native evidence."""

    def __init__(
        self,
        bundle: Mapping[str, Any],
        seal: Optional[Mapping[str, Any]],
    ):
        self.bundle = bundle
        self.seal = seal
        self.errors: list[str] = []
        self.run_errors: list[str] = []
        self.manifest: Mapping[str, Any] = {}
        self.service_manifest: Mapping[str, Any] = {}
        self.owner_responses: list[Mapping[str, Any]] = []
        self.owner_by_hash: dict[str, Mapping[str, Any]] = {}
        self.target_events: list[Mapping[str, Any]] = []
        self.target_by_hash: dict[str, Mapping[str, Any]] = {}
        self.requests_by_id: dict[str, Mapping[str, Any]] = {}
        self.target_requests_by_id: dict[str, Mapping[str, Any]] = {}

    def error(self, message: str) -> None:
        self.errors.append(message)

    def run_error(self, message: str) -> None:
        self.errors.append(message)
        self.run_errors.append(message)

    def validate(self) -> None:
        self._validate_bundle_hash()
        self._validate_manifest_and_world()
        self._validate_services()
        self._validate_requests()
        self._validate_owner_logs()
        self._validate_target_log()
        self._validate_runtime_boundary()
        self._validate_fragments()
        self._validate_run_seal()

    def _validate_bundle_hash(self) -> None:
        actual = self.bundle.get("bundle_sha256")
        expected = object_sha256(_without(self.bundle, "bundle_sha256"))
        if actual != expected:
            self.error("bundle_sha256: mismatch")

    def _validate_manifest_and_world(self) -> None:
        manifest = self.bundle.get("episode_manifest")
        if not isinstance(manifest, Mapping):
            self.error("episode_manifest: missing or not an object")
            return
        self.manifest = manifest
        required = {
            "schema",
            "run_id",
            "world_root",
            "case_id",
            "arm_binding_token",
            "arm_id",
            "authority_stratum",
            "q_version",
            "object_id",
            "target_id",
            "operation_id",
            "deadline_minute",
            "required_duration_minutes",
            "required_power_kw",
            "power_tolerance_percent",
            "owner_registry_sha256",
            "target_registry_sha256",
            "manifest_sha256",
        }
        missing = sorted(required - set(manifest))
        if missing:
            self.error(f"episode_manifest: missing {missing}")
        if manifest.get("schema") != "CE001_EPISODE_MANIFEST_V1":
            self.error("episode_manifest.schema: unsupported")
        if manifest.get("case_id") not in {E1, E5}:
            self.error("episode_manifest.case_id: evaluator supports only E1/E5")
        if manifest.get("arm_id") != ARM:
            self.error("episode_manifest.arm_id: wrong arm")
        if manifest.get("object_id") != manifest.get("target_id"):
            self.error("episode_manifest: object_id and target_id differ")
        expected_manifest = object_sha256(_without(manifest, "manifest_sha256"))
        if manifest.get("manifest_sha256") != expected_manifest:
            self.error("episode_manifest.manifest_sha256: mismatch")
        public_case = self.bundle.get("public_case")
        private_case = self.bundle.get("private_case_receipt")
        if not isinstance(public_case, Mapping) or not isinstance(private_case, Mapping):
            self.error("world evidence: public_case/private_case_receipt missing")
        else:
            expected_world = object_sha256(
                {"public_case": public_case, "private_case_receipt": private_case}
            )
            if manifest.get("world_root") != expected_world:
                self.error("episode_manifest.world_root: case evidence mismatch")
            for name, case_part in (
                ("public_case", public_case),
                ("private_case_receipt", private_case),
            ):
                if case_part.get("case_id") != manifest.get("case_id"):
                    self.error(f"{name}.case_id: binding mismatch")
                if case_part.get("run_id") != manifest.get("run_id"):
                    self.error(f"{name}.run_id: binding mismatch")
            receipt_sha = private_case.get("receipt_sha256")
            if receipt_sha != object_sha256(_without(private_case, "receipt_sha256")):
                self.error("private_case_receipt.receipt_sha256: mismatch")

    def _validate_services(self) -> None:
        service = self.bundle.get("service_manifest")
        if not isinstance(service, Mapping):
            self.error("service_manifest: missing or not an object")
            return
        self.service_manifest = service
        owners = service.get("owners")
        target = service.get("target")
        owner_snapshot = service.get("owner_registry_snapshot")
        target_snapshot = service.get("target_registry_snapshot")
        if (
            not isinstance(owners, Mapping)
            or not isinstance(target, Mapping)
            or not isinstance(owner_snapshot, Mapping)
            or not isinstance(target_snapshot, Mapping)
        ):
            self.error("service_manifest: owners/target registry or immutable snapshot missing")
            return
        if set(owners) != set(OWNER_IDS):
            self.error("service_manifest.owners: expected exact O_Q/O_V/O_R/O_S/O_P/O_E registry")
        if self.manifest:
            if object_sha256(owner_snapshot) != self.manifest.get("owner_registry_sha256"):
                self.error("owner_registry_sha256: service registry mismatch")
            if object_sha256(target_snapshot) != self.manifest.get("target_registry_sha256"):
                self.error("target_registry_sha256: service registry mismatch")
        if set(owner_snapshot) != set(OWNER_IDS):
            self.error("owner_registry_snapshot: expected exact owner set")
        for owner_id, entry in owners.items():
            if not isinstance(entry, Mapping):
                self.error(f"service_manifest.owners.{owner_id}: invalid")
                continue
            self._validate_service_entry(entry, f"service_manifest.owners.{owner_id}")
            snapshot_entry = owner_snapshot.get(owner_id)
            self._validate_registry_snapshot(
                snapshot_entry,
                entry,
                f"owner_registry_snapshot.{owner_id}",
            )
        self._validate_service_entry(target, "service_manifest.target")
        self._validate_registry_snapshot(
            target_snapshot,
            target,
            "target_registry_snapshot",
        )
        service_entries = [
            item
            for item in [*owners.values(), target]
            if isinstance(item, Mapping)
        ]
        for field in (
            "actual_pid",
            "public_key_hex",
            "state_source_id",
            "state_head_at_start",
            "backend_identity_sha256",
        ):
            values = [
                item.get(field, item.get("state_head") if field == "state_head_at_start" else None)
                for item in service_entries
            ]
            if len(values) != len(set(values)):
                self.error(
                    f"service_manifest.all_sources: {field} values are not unique"
                )

    def _validate_registry_snapshot(
        self,
        snapshot: Any,
        entry: Mapping[str, Any],
        prefix: str,
    ) -> None:
        if not isinstance(snapshot, Mapping):
            self.error(f"{prefix}: missing")
            return
        required = {
            "actual_pid",
            "public_key_hex",
            "state_source_id",
            "state_head_at_start",
            "state_epoch_at_start",
            "executable_sha256",
            "backend_identity_sha256",
            "process_start_receipt_sha256",
            "initial_shard_sha256",
        }
        if not required.issubset(snapshot):
            self.error(f"{prefix}: incomplete immutable identity")
        for field in required - {"process_start_receipt_sha256"}:
            if snapshot.get(field) != entry.get(field):
                self.error(f"{prefix}.{field}: startup identity mismatch")
        start = entry.get("process_start_receipt")
        start_sha = start.get("receipt_sha256") if isinstance(start, Mapping) else None
        if snapshot.get("process_start_receipt_sha256") != start_sha:
            self.error(f"{prefix}.process_start_receipt_sha256: mismatch")

    def _validate_service_entry(self, entry: Mapping[str, Any], prefix: str) -> None:
        pid = entry.get("actual_pid", entry.get("process_id"))
        if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
            self.error(f"{prefix}.actual_pid: invalid")
        public_key = entry.get("public_key_hex")
        if not isinstance(public_key, str) or len(public_key) != 64:
            self.error(f"{prefix}.public_key_hex: invalid")
        if not entry.get("state_source_id"):
            self.error(f"{prefix}.state_source_id: missing")
        if not entry.get("state_head_at_start", entry.get("state_head")):
            self.error(f"{prefix}.state_head_at_start: missing")
        initial_epoch = entry.get("state_epoch_at_start")
        if (
            not isinstance(initial_epoch, int)
            or isinstance(initial_epoch, bool)
            or initial_epoch < 0
        ):
            self.error(f"{prefix}.state_epoch_at_start: invalid")
        epoch = entry.get("current_owner_state_epoch")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
            self.error(f"{prefix}.current_owner_state_epoch: invalid")
        executable = entry.get("executable_sha256", entry.get("executable_digest"))
        if not _is_sha256(executable):
            self.error(f"{prefix}.executable_sha256: invalid")
        if entry.get("backend_kind") != "PROCESS_PRIVATE_MEMORY":
            self.error(f"{prefix}.backend_kind: expected PROCESS_PRIVATE_MEMORY")
        backend_identity = entry.get("backend_identity")
        if not isinstance(backend_identity, Mapping):
            self.error(f"{prefix}.backend_identity: missing")
        elif entry.get("backend_identity_sha256") != object_sha256(backend_identity):
            self.error(f"{prefix}.backend_identity_sha256: mismatch")
        start = entry.get("process_start_receipt")
        if not isinstance(start, Mapping):
            self.error(f"{prefix}.process_start_receipt: missing")
        else:
            if start.get("actual_pid") != pid:
                self.error(f"{prefix}.process_start_receipt.actual_pid: mismatch")
            if start.get("public_key_hex") != public_key:
                self.error(f"{prefix}.process_start_receipt.public_key_hex: mismatch")
            if start.get("state_source_id") != entry.get("state_source_id"):
                self.error(f"{prefix}.process_start_receipt.state_source_id: mismatch")
            if start.get("start_method") != "spawn":
                self.error(f"{prefix}.process_start_receipt.start_method: not spawn")
            expected_start_sha = object_sha256(
                _without(start, "receipt_sha256", "signature_hex")
            )
            if start.get("receipt_sha256") != expected_start_sha:
                self.error(f"{prefix}.process_start_receipt.receipt_sha256: mismatch")
            if not _verify_signature(
                public_key,
                start.get("signature_hex"),
                canonical_bytes(_without(start, "signature_hex")),
            ):
                self.error(f"{prefix}.process_start_receipt.signature_hex: invalid")

    def _validate_requests(self) -> None:
        transcript = self.bundle.get("arm_transcript")
        if not isinstance(transcript, Mapping):
            self.error("arm_transcript: missing or not an object")
            return
        requests = transcript.get("requests")
        target_requests = transcript.get("target_requests")
        if not isinstance(requests, list):
            self.error("arm_transcript.requests: missing")
            requests = []
        if not isinstance(target_requests, list):
            self.error("arm_transcript.target_requests: missing")
            target_requests = []
        self._validate_request_group(
            requests,
            "arm_transcript.requests",
            set(OWNER_IDS),
            self.requests_by_id,
        )
        self._validate_request_group(
            target_requests,
            "arm_transcript.target_requests",
            {"TARGET"},
            self.target_requests_by_id,
        )

    def _validate_request_group(
        self,
        requests: Sequence[Any],
        group_prefix: str,
        allowed_services: set[str],
        destination: dict[str, Mapping[str, Any]],
    ) -> None:
        for index, request in enumerate(requests):
            prefix = f"{group_prefix}[{index}]"
            if not isinstance(request, Mapping):
                self.error(f"{prefix}: invalid")
                continue
            request_id = request.get("request_id")
            request_nonce = request.get("request_nonce")
            owner_id = request.get("owner_id")
            payload = request.get("payload")
            if not isinstance(request_id, str) or not request_id:
                self.error(f"{prefix}.request_id: invalid")
                continue
            if (
                request_id in self.requests_by_id
                or request_id in self.target_requests_by_id
            ):
                self.error(f"{prefix}.request_id: duplicate")
            if not isinstance(request_nonce, str) or not request_nonce:
                self.error(f"{prefix}.request_nonce: invalid")
            elif any(
                item.get("request_nonce") == request_nonce
                for item in (
                    list(self.requests_by_id.values())
                    + list(self.target_requests_by_id.values())
                )
            ):
                self.error(f"{prefix}.request_nonce: duplicate")
            if owner_id not in allowed_services:
                self.error(f"{prefix}.owner_id: invalid")
            if not isinstance(payload, Mapping):
                self.error(f"{prefix}.payload: invalid")
                continue
            expected_bytes = canonical_bytes(payload)
            request_bytes = request.get("request_bytes")
            if request_bytes != expected_bytes.decode("utf-8"):
                self.error(f"{prefix}.request_bytes: not exact canonical payload bytes")
            expected = hashlib.sha256(expected_bytes).hexdigest()
            if request.get("request_sha256") != expected:
                self.error(f"{prefix}.request_sha256: mismatch")
            self.errors.extend(_required_binding_errors(payload, self.manifest, f"{prefix}.payload"))
            if payload.get("owner_id") != owner_id:
                self.error(f"{prefix}.payload.owner_id: transport mismatch")
            destination[request_id] = request

    def _validate_owner_logs(self) -> None:
        raw_logs = self.bundle.get("owner_native_logs")
        owners = self.service_manifest.get("owners", {})
        if not isinstance(raw_logs, Mapping) or not isinstance(owners, Mapping):
            self.error("owner_native_logs: missing or service registry unavailable")
            return
        if set(raw_logs) != set(OWNER_IDS):
            self.error("owner_native_logs: expected exact O_Q/O_V/O_R/O_S/O_P/O_E keys")
        for owner_id in OWNER_IDS:
            service = owners.get(owner_id)
            if not isinstance(service, Mapping):
                continue
            raw_log = raw_logs.get(owner_id)
            if not isinstance(raw_log, Mapping):
                self.error(f"owner_native_logs.{owner_id}: expected frozen log object")
            entries, declared_final_head = _owner_entries(raw_log)
            expected_head = service.get("state_head_at_start", service.get("state_head"))
            for index, response in enumerate(entries):
                prefix = f"owner_native_logs.{owner_id}[{index}]"
                if response.get("owner_id") != owner_id:
                    self.error(f"{prefix}.owner_id: source mismatch")
                pid = service.get("actual_pid", service.get("process_id"))
                if response.get("process_id") != pid:
                    self.error(f"{prefix}.process_id: source mismatch")
                request = self.requests_by_id.get(str(response.get("request_id")))
                if request is None:
                    self.error(f"{prefix}.request_id: unknown")
                else:
                    if response.get("request_sha256") != request.get("request_sha256"):
                        self.error(f"{prefix}.request_sha256: request binding mismatch")
                    if response.get("request_nonce") != request.get("request_nonce"):
                        self.error(f"{prefix}.request_nonce: request binding mismatch")
                    if response.get("request_bytes") != request.get("request_bytes"):
                        self.error(f"{prefix}.request_bytes: request binding mismatch")
                    if request.get("owner_id") != owner_id:
                        self.error(f"{prefix}.request_id: wrong owner")
                self.errors.extend(_transport_binding_errors(response, self.manifest, prefix))
                payload = response.get("payload")
                if not isinstance(payload, Mapping):
                    self.error(f"{prefix}.payload: invalid")
                else:
                    self.errors.extend(_required_binding_errors(payload, self.manifest, f"{prefix}.payload"))
                if response.get("append_index") != index:
                    self.error(f"{prefix}.append_index: sequence mismatch")
                if response.get("previous_head") != expected_head:
                    self.error(f"{prefix}.previous_head: chain mismatch")
                if response.get("state_head_before") != expected_head:
                    self.error(f"{prefix}.state_head_before: chain mismatch")
                claimed_hash = response.get("response_sha256")
                expected_hash = object_sha256(
                    _without(
                        response,
                        "response_sha256",
                        "signature_hex",
                        "append_index",
                        "previous_head",
                        "record_head",
                        "state_head_before",
                        "state_head_after",
                    )
                )
                if claimed_hash != expected_hash:
                    self.error(f"{prefix}.response_sha256: mismatch")
                expected_after = object_sha256(
                    {
                        "append_index": index,
                        "previous_head": expected_head,
                        "record_sha256": claimed_hash,
                    }
                )
                if response.get("record_head") != expected_after:
                    self.error(f"{prefix}.record_head: transition mismatch")
                if response.get("state_head_after") != expected_after:
                    self.error(f"{prefix}.state_head_after: transition mismatch")
                unsigned = _without(response, "signature_hex")
                if not _verify_signature(
                    service.get("public_key_hex"),
                    response.get("signature_hex"),
                    canonical_bytes(unsigned),
                ):
                    self.error(f"{prefix}.signature_hex: invalid source signature")
                if _number(response.get("observed_at_minute")) is None:
                    self.error(f"{prefix}.observed_at_minute: invalid")
                if isinstance(claimed_hash, str):
                    if claimed_hash in self.owner_by_hash:
                        self.error(f"{prefix}.response_sha256: duplicate identity")
                    self.owner_by_hash[claimed_hash] = response
                self.owner_responses.append(response)
                expected_head = response.get("record_head")
            if declared_final_head is not None and declared_final_head != expected_head:
                self.error(f"owner_native_logs.{owner_id}.state_head: final head mismatch")
            if isinstance(raw_log, Mapping):
                self._validate_freeze_receipt(
                    raw_log.get("freeze_receipt"),
                    service,
                    expected_head,
                    len(entries),
                    f"owner_native_logs.{owner_id}.freeze_receipt",
                    owner_id,
                )

    def _validate_target_log(self) -> None:
        raw = self.bundle.get("target_native_log")
        target_service = self.service_manifest.get("target", {})
        if not isinstance(raw, Mapping) or not isinstance(target_service, Mapping):
            self.error("target_native_log: missing or target service unavailable")
            return
        for field in ("public_key_hex", "state_source_id"):
            if field in raw and raw.get(field) != target_service.get(field):
                self.error(f"target_native_log.{field}: service source mismatch")
        if "process_id" in raw:
            target_pid = target_service.get("actual_pid", target_service.get("process_id"))
            if raw.get("process_id") != target_pid:
                self.error("target_native_log.process_id: service source mismatch")
        entries = _target_entries(raw)
        expected_head = target_service.get(
            "state_head_at_start", target_service.get("state_head")
        )
        for index, event in enumerate(entries):
            prefix = f"target_native_log.entries[{index}]"
            target_pid = target_service.get("actual_pid", target_service.get("process_id"))
            if event.get("process_id") != target_pid:
                self.error(f"{prefix}.process_id: source mismatch")
            self.errors.extend(_provenance_binding_errors(event, self.manifest, prefix))
            if event.get("append_index") != index:
                self.error(f"{prefix}.append_index: sequence mismatch")
            if event.get("previous_head") != expected_head:
                self.error(f"{prefix}.previous_head: chain mismatch")
            if event.get("state_head_before") != expected_head:
                self.error(f"{prefix}.state_head_before: chain mismatch")
            claimed_hash = event.get("event_sha256")
            expected_hash = object_sha256(
                _without(
                    event,
                    "event_sha256",
                    "signature_hex",
                    "append_index",
                    "previous_head",
                    "record_head",
                    "state_head_before",
                    "state_head_after",
                )
            )
            if claimed_hash != expected_hash:
                self.error(f"{prefix}.event_sha256: mismatch")
            expected_after = object_sha256(
                {
                    "append_index": index,
                    "previous_head": expected_head,
                    "record_sha256": claimed_hash,
                }
            )
            if event.get("record_head") != expected_after:
                self.error(f"{prefix}.record_head: transition mismatch")
            if event.get("state_head_after") != expected_after:
                self.error(f"{prefix}.state_head_after: transition mismatch")
            if not _verify_signature(
                target_service.get("public_key_hex"),
                event.get("signature_hex"),
                canonical_bytes(_without(event, "signature_hex")),
            ):
                self.error(f"{prefix}.signature_hex: invalid source signature")
            if _event_kind(event) not in {"OCCURRENCE", "SENSOR_SAMPLE", "READBACK"}:
                self.error(f"{prefix}.kind: unsupported target event")
            if isinstance(claimed_hash, str):
                self.target_by_hash.setdefault(claimed_hash, event)
            self.target_events.append(event)
            expected_head = event.get("record_head")
        if raw.get("state_head") != expected_head:
            self.error("target_native_log.state_head: final head mismatch")
        self._validate_freeze_receipt(
            raw.get("freeze_receipt"),
            target_service,
            expected_head,
            len(entries),
            "target_native_log.freeze_receipt",
            "TARGET",
        )
        self._validate_target_causal_links()

    def _target_parent_request(
        self,
        event: Mapping[str, Any],
        *,
        id_field: str,
        nonce_field: str,
        sha_field: str,
        action: str,
        prefix: str,
    ) -> Optional[Mapping[str, Any]]:
        request_id = event.get(id_field)
        request = (
            self.target_requests_by_id.get(request_id)
            if isinstance(request_id, str)
            else None
        )
        if request is None:
            self.error(f"{prefix}.{id_field}: missing target request parent")
            return None
        if event.get(sha_field) != request.get("request_sha256"):
            self.error(f"{prefix}.{sha_field}: target request parent mismatch")
        if event.get(nonce_field) != request.get("request_nonce"):
            self.error(f"{prefix}.{nonce_field}: target request parent mismatch")
        payload = request.get("payload")
        if not isinstance(payload, Mapping) or payload.get("action") != action:
            self.error(f"{prefix}.{id_field}: parent is not {action}")
            return None
        return request

    def _validate_target_causal_links(self) -> None:
        occurrences = [
            event for event in self.target_events if _event_kind(event) == "OCCURRENCE"
        ]
        samples = [
            event
            for event in self.target_events
            if _event_kind(event) == "SENSOR_SAMPLE"
        ]
        readbacks = [
            event for event in self.target_events if _event_kind(event) == "READBACK"
        ]
        occurrence_hashes = [event.get("event_sha256") for event in occurrences]
        sample_hashes = [event.get("event_sha256") for event in samples]

        for index, occurrence in enumerate(occurrences):
            prefix = f"target_native_log.occurrences[{index}]"
            request = self._target_parent_request(
                occurrence,
                id_field="source_execute_request_id",
                nonce_field="source_execute_request_nonce",
                sha_field="source_execute_request_sha256",
                action="EXECUTE",
                prefix=prefix,
            )
            if request is None:
                continue
            request_payload = request.get("payload", {})
            execute_at = _number(occurrence.get("execute_at_minute"))
            if (
                execute_at is None
                or _number(request_payload.get("observed_at_minute")) != execute_at
            ):
                self.error(f"{prefix}.execute_at_minute: request time mismatch")
            arguments = request_payload.get("arguments")
            receipts = (
                arguments.get("authority_receipts")
                if isinstance(arguments, Mapping)
                else None
            )
            request_hashes = {
                item.get("owner_id"): item.get("response_sha256")
                for item in _as_list(receipts)
                if isinstance(item, Mapping)
            }
            consumed = occurrence.get("consumed_authority_response_hashes")
            if not isinstance(consumed, Mapping) or request_hashes != dict(consumed):
                self.error(
                    f"{prefix}.consumed_authority_response_hashes: "
                    "EXECUTE request mismatch"
                )

        occurrence_by_hash = {
            event.get("event_sha256"): event
            for event in occurrences
            if isinstance(event.get("event_sha256"), str)
        }
        for index, sample in enumerate(samples):
            prefix = f"target_native_log.sensor_samples[{index}]"
            self._target_parent_request(
                sample,
                id_field="source_execute_request_id",
                nonce_field="source_execute_request_nonce",
                sha_field="source_execute_request_sha256",
                action="EXECUTE",
                prefix=prefix,
            )
            if sample.get("source_occurrence_event_sha256") not in occurrence_by_hash:
                self.error(
                    f"{prefix}.source_occurrence_event_sha256: parent mismatch"
                )

        expected_digest = _effect_digest(occurrences, samples)
        for index, readback in enumerate(readbacks):
            prefix = f"target_native_log.readbacks[{index}]"
            request = self._target_parent_request(
                readback,
                id_field="source_readback_request_id",
                nonce_field="source_readback_request_nonce",
                sha_field="source_readback_request_sha256",
                action="READBACK",
                prefix=prefix,
            )
            if request is not None:
                request_payload = request.get("payload", {})
                if _number(request_payload.get("observed_at_minute")) != _number(
                    readback.get("minute")
                ):
                    self.error(f"{prefix}.minute: request time mismatch")
            if readback.get("occurrence_event_sha256") != occurrence_hashes:
                self.error(f"{prefix}.occurrence_event_sha256: parent mismatch")
            if readback.get("sensor_event_sha256") != sample_hashes:
                self.error(f"{prefix}.sensor_event_sha256: parent mismatch")
            if readback.get("effect_digest") != expected_digest:
                self.error(f"{prefix}.effect_digest: native Effect mismatch")

    def _validate_runtime_boundary(self) -> None:
        runtime = self.bundle.get("runtime_log")
        reveal = self.bundle.get("private_case_reveal")
        receipt = self.bundle.get("private_case_receipt")
        if not isinstance(runtime, Mapping):
            self.run_error("runtime_log: missing or not an object")
            return
        if not isinstance(reveal, Mapping) or not isinstance(receipt, Mapping):
            self.run_error("private_case_reveal: missing")
        else:
            if reveal.get("case_id") != self.manifest.get("case_id"):
                self.run_error("private_case_reveal.case_id: mismatch")
            if reveal.get("run_id") != self.manifest.get("run_id"):
                self.run_error("private_case_reveal.run_id: mismatch")
            if receipt.get("private_truth_sha256") != object_sha256(reveal):
                self.run_error("private_case_reveal: private truth hash mismatch")
            canary = reveal.get("private_canary_value")
            canary_hash = receipt.get("private_canary_sha256")
            if (
                not isinstance(canary, str)
                or not canary
                or canary_hash != hashlib.sha256(canary.encode("utf-8")).hexdigest()
            ):
                self.run_error("private_case_reveal: private canary mismatch")

        visibility = runtime.get("arm_visibility_receipt")
        if not isinstance(visibility, Mapping):
            self.run_error("runtime_log.arm_visibility_receipt: missing")
        else:
            arm_pid = visibility.get("actual_pid")
            service_pids = {
                item.get("actual_pid", item.get("process_id"))
                for item in list(self.service_manifest.get("owners", {}).values())
                + [self.service_manifest.get("target", {})]
                if isinstance(item, Mapping)
            }
            if not isinstance(arm_pid, int) or arm_pid <= 0 or arm_pid in service_pids:
                self.run_error("arm_visibility_receipt.actual_pid: invalid or aliased")
            if visibility.get("process_start_method") != "spawn":
                self.run_error("arm_visibility_receipt.process_start_method: not spawn")
            payload = visibility.get("start_payload")
            payload_bytes = visibility.get("start_payload_bytes")
            if not isinstance(payload, Mapping) or not isinstance(payload_bytes, str):
                self.run_error("arm_visibility_receipt.start_payload: missing")
            else:
                if payload_bytes != canonical_bytes(payload).decode("utf-8"):
                    self.run_error("arm_visibility_receipt.start_payload_bytes: mismatch")
                if visibility.get("start_payload_sha256") != hashlib.sha256(
                    payload_bytes.encode("utf-8")
                ).hexdigest():
                    self.run_error("arm_visibility_receipt.start_payload_sha256: mismatch")
                if visibility.get("field_list") != sorted(payload):
                    self.run_error("arm_visibility_receipt.field_list: mismatch")
                forbidden = {
                    "case_id",
                    "manifest_sha256",
                    "private_case_receipt",
                    "private_case_reveal",
                    "private_canary",
                    "private_canary_value",
                    "no_alternative",
                    "feasible_alternatives",
                    "expected_result",
                    "correct_resolution",
                    "success",
                }
                found = self._find_forbidden_key(payload, forbidden)
                if found:
                    self.run_error(f"arm_visibility_receipt.start_payload: forbidden {found}")
                if isinstance(reveal, Mapping):
                    canary = reveal.get("private_canary_value")
                    if isinstance(canary, str) and canary and canary in payload_bytes:
                        self.run_error("arm_visibility_receipt.start_payload: private canary exposed")
                arm_transcript_bytes = canonical_bytes(
                    self.bundle.get("arm_transcript", {})
                ).decode("utf-8")
                full_manifest_sha = self.manifest.get("manifest_sha256")
                if (
                    isinstance(full_manifest_sha, str)
                    and full_manifest_sha
                    and (
                        full_manifest_sha in payload_bytes
                        or full_manifest_sha in arm_transcript_bytes
                    )
                ):
                    self.run_error(
                        "arm_visibility_receipt: evaluator-private manifest hash exposed"
                    )
                visible_text = f"{payload_bytes}\n{arm_transcript_bytes}".lower()
                for semantic_case_label in (E1.lower(), E5.lower()):
                    if semantic_case_label in visible_text:
                        self.run_error(
                            "arm_visibility_receipt: semantic case label exposed"
                        )
            if visibility.get("private_canary_sha256") != (
                receipt.get("private_canary_sha256") if isinstance(receipt, Mapping) else None
            ):
                self.run_error("arm_visibility_receipt.private_canary_sha256: mismatch")
            if visibility.get("private_canary_absent") is not True:
                self.run_error("arm_visibility_receipt.private_canary_absent: not true")
            for field in (
                "inherited_file_descriptor_inventory",
                "network_allowlist",
                "file_allowlist",
                "minimal_environment_keys",
            ):
                if not isinstance(visibility.get(field), list):
                    self.run_error(f"arm_visibility_receipt.{field}: missing")
            scans = visibility.get("scan_results")
            required_scans = {
                "cwd",
                "environment",
                "start_payload",
                "arm_transcript",
                "owner_requests",
            }
            if (
                not isinstance(scans, Mapping)
                or not required_scans.issubset(scans)
                or any(scans.get(key) not in (False, 0, [], "") for key in required_scans)
            ):
                self.run_error("arm_visibility_receipt.scan_results: canary hit or incomplete")
            expected_visibility_sha = object_sha256(
                _without(visibility, "receipt_sha256")
            )
            if visibility.get("receipt_sha256") != expected_visibility_sha:
                self.run_error("arm_visibility_receipt.receipt_sha256: mismatch")

        exit_codes = runtime.get("process_exit_codes")
        expected_processes = set(OWNER_IDS) | {"TARGET", "A4"}
        if (
            not isinstance(exit_codes, Mapping)
            or set(exit_codes) != expected_processes
            or any(code != 0 for code in exit_codes.values())
        ):
            self.run_error("runtime_log.process_exit_codes: incomplete or nonzero")
        for field in (
            "native_logs_frozen_before_service_exit",
            "all_processes_exited_before_bundle_freeze",
            "native_logs_frozen",
            "bundle_frozen_after_process_exit",
        ):
            if runtime.get(field) is not True:
                self.run_error(f"runtime_log.{field}: not true")

    @staticmethod
    def _find_forbidden_key(
        value: Any,
        forbidden: set[str],
        path: str = "$",
    ) -> Optional[str]:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key).lower() in forbidden:
                    return f"{path}.{key}"
                found = BundleEvidence._find_forbidden_key(item, forbidden, f"{path}.{key}")
                if found:
                    return found
        elif isinstance(value, list):
            for index, item in enumerate(value):
                found = BundleEvidence._find_forbidden_key(
                    item, forbidden, f"{path}[{index}]"
                )
                if found:
                    return found
        return None

    def _validate_run_seal(self) -> None:
        seal = self.seal
        if not isinstance(seal, Mapping):
            self.run_error("run_seal: missing")
            return
        if seal.get("schema") != "CE001_LOCAL_RUN_SEAL_V1":
            self.run_error("run_seal.schema: unsupported")
        if seal.get("threat_boundary") != "SAME_USER_WHOLE_RUN_REWRITE_NOT_COVERED":
            self.run_error("run_seal.threat_boundary: inaccurate or missing")
        if seal.get("run_id") != self.manifest.get("run_id"):
            self.run_error("run_seal.run_id: mismatch")
        if seal.get("manifest_sha256") != self.manifest.get("manifest_sha256"):
            self.run_error("run_seal.manifest_sha256: mismatch")
        if seal.get("bundle_sha256") != self.bundle.get("bundle_sha256"):
            self.run_error("run_seal.bundle_sha256: mismatch")
        expected_heads: dict[str, Any] = {}
        expected_receipts: dict[str, Any] = {}
        owner_logs = self.bundle.get("owner_native_logs", {})
        if isinstance(owner_logs, Mapping):
            for owner_id in OWNER_IDS:
                log = owner_logs.get(owner_id)
                if isinstance(log, Mapping):
                    expected_heads[owner_id] = log.get("state_head")
                    freeze = log.get("freeze_receipt")
                    if isinstance(freeze, Mapping):
                        expected_receipts[owner_id] = freeze.get("receipt_sha256")
        target = self.bundle.get("target_native_log")
        if isinstance(target, Mapping):
            expected_heads["TARGET"] = target.get("state_head")
            freeze = target.get("freeze_receipt")
            if isinstance(freeze, Mapping):
                expected_receipts["TARGET"] = freeze.get("receipt_sha256")
        if seal.get("native_log_terminal_heads") != expected_heads:
            self.run_error("run_seal.native_log_terminal_heads: mismatch")
        if seal.get("freeze_receipt_sha256s") != expected_receipts:
            self.run_error("run_seal.freeze_receipt_sha256s: mismatch")
        if seal.get("seal_sha256") != object_sha256(_without(seal, "seal_sha256")):
            self.run_error("run_seal.seal_sha256: mismatch")

    def _validate_freeze_receipt(
        self,
        receipt: Any,
        service: Mapping[str, Any],
        terminal_head: Any,
        record_count: int,
        prefix: str,
        source_id: str,
    ) -> None:
        if not isinstance(receipt, Mapping):
            self.error(f"{prefix}: missing")
            return
        pid = service.get("actual_pid", service.get("process_id"))
        expected_source = service.get("state_source_id")
        if receipt.get("source_id") not in {source_id, expected_source}:
            self.error(f"{prefix}.source_id: mismatch")
        if receipt.get("state_source_id") != expected_source:
            self.error(f"{prefix}.state_source_id: mismatch")
        if receipt.get("process_id") != pid:
            self.error(f"{prefix}.process_id: mismatch")
        if receipt.get("run_id") != self.manifest.get("run_id"):
            self.error(f"{prefix}.run_id: mismatch")
        if receipt.get("manifest_sha256") != self.manifest.get("manifest_sha256"):
            self.error(f"{prefix}.manifest_sha256: mismatch")
        if receipt.get("terminal_head") != terminal_head:
            self.error(f"{prefix}.terminal_head: mismatch")
        if receipt.get("record_count") != record_count:
            self.error(f"{prefix}.record_count: mismatch")
        if receipt.get("exit_code") != 0:
            self.error(f"{prefix}.exit_code: not clean")
        expected_sha = object_sha256(_without(receipt, "receipt_sha256", "signature_hex"))
        if receipt.get("receipt_sha256") != expected_sha:
            self.error(f"{prefix}.receipt_sha256: mismatch")
        if not _verify_signature(
            service.get("public_key_hex"),
            receipt.get("signature_hex"),
            canonical_bytes(_without(receipt, "signature_hex")),
        ):
            self.error(f"{prefix}.signature_hex: invalid")

    def _resolve_source_ref(self, ref: Any) -> Optional[Mapping[str, Any]]:
        if not isinstance(ref, str):
            return None
        parts = ref.split(":")
        if len(parts) == 3 and parts[0] == "owner":
            response = self.owner_by_hash.get(parts[2])
            if response is not None and response.get("owner_id") == parts[1]:
                return response
        if len(parts) == 2 and parts[0] == "target":
            return self.target_by_hash.get(parts[1])
        if len(parts) == 2 and parts[0] == "request":
            request = self.requests_by_id.get(parts[1])
            if request is not None:
                return request
        return None

    def _validate_fragments(self) -> None:
        fragments = self.bundle.get("component_fragments")
        if not isinstance(fragments, Mapping):
            self.error("component_fragments: missing or not an object")
            return
        if set(fragments) != set(FRAGMENT_IDS):
            self.error("component_fragments: expected exact G1..G7")
        for namespace in FRAGMENT_IDS:
            fragment = fragments.get(namespace)
            prefix = f"component_fragments.{namespace}"
            if not isinstance(fragment, Mapping):
                self.error(f"{prefix}: missing or invalid")
                continue
            forbidden = _find_contract_field(fragment, prefix)
            if forbidden:
                self.error(f"{forbidden}: contract field forbidden in line fragment")
            if fragment.get("namespace") != namespace:
                self.error(f"{prefix}.namespace: mismatch")
            if not fragment.get("disposition"):
                self.error(f"{prefix}.disposition: missing")
            for field in (
                "run_id",
                "world_root",
                "case_id",
                "manifest_sha256",
                "q_version",
                "object_id",
                "operation_id",
            ):
                if fragment.get(field) != self.manifest.get(field):
                    self.error(f"{prefix}.{field}: binding mismatch")
            refs = fragment.get("source_log_refs")
            if not isinstance(refs, list) or not refs:
                self.error(f"{prefix}.source_log_refs: missing or empty")
                continue
            resolved: list[Mapping[str, Any]] = []
            for ref in refs:
                source = self._resolve_source_ref(ref)
                if source is None:
                    self.error(f"{prefix}.source_log_refs: unresolved {ref!r}")
                else:
                    resolved.append(source)
            if len(resolved) == len(refs):
                expected = object_sha256(resolved)
                if fragment.get("source_artifact_sha256") != expected:
                    self.error(f"{prefix}.source_artifact_sha256: source binding mismatch")


def _bound_payload(
    response: Mapping[str, Any],
    manifest: Mapping[str, Any],
    kind: str,
) -> bool:
    payload = response.get("payload")
    return (
        isinstance(payload, Mapping)
        and _payload_kind(response) == kind
        and not _required_binding_errors(payload, manifest, "payload")
    )


def _latest_authority(
    evidence: BundleEvidence,
    owner_id: str,
    at_minute: float,
) -> Optional[Mapping[str, Any]]:
    candidates = [
        response
        for response in evidence.owner_responses
        if response.get("owner_id") == owner_id
        and _bound_payload(response, evidence.manifest, "AUTHORITY")
        and (_number(response.get("observed_at_minute")) or 0) <= at_minute
    ]
    if not candidates:
        return None
    return max(
        enumerate(candidates),
        key=lambda pair: ((_number(pair[1].get("observed_at_minute")) or 0), pair[0]),
    )[1]


def _not_expired(response: Mapping[str, Any], at_minute: float) -> bool:
    payload = response.get("payload")
    if not isinstance(payload, Mapping):
        return False
    issued = _number(payload.get("issued_at_minute"))
    expiry = _number(payload.get("expires_at_minute"))
    return (
        issued is not None
        and expiry is not None
        and issued <= at_minute < expiry
        and isinstance(payload.get("owner_state_head"), str)
        and bool(payload.get("owner_state_head"))
    )


def _effect_parts(evidence: BundleEvidence) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    occurrences = [
        event for event in evidence.target_events if _event_kind(event) == "OCCURRENCE"
    ]
    samples = [
        event for event in evidence.target_events if _event_kind(event) == "SENSOR_SAMPLE"
    ]
    return occurrences, samples


def _effect_digest(
    occurrences: Sequence[Mapping[str, Any]],
    samples: Sequence[Mapping[str, Any]],
) -> str:
    return object_sha256({"occurrences": list(occurrences), "sensor_samples": list(samples)})


def _valid_acceptances(
    evidence: BundleEvidence,
    effect_digest: str,
    effect_end_minute: float,
    readback_event_sha256: str,
    readback_minute: float,
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for owner_id in ("O_Q", "O_V"):
        candidates = [
            response
            for response in evidence.owner_responses
            if response.get("owner_id") == owner_id
            and _bound_payload(response, evidence.manifest, "ACCEPTANCE")
            and _decision(response) in {"ACCEPT", "ACCEPTED"}
            and isinstance(response.get("payload"), Mapping)
            and response["payload"].get("effect_digest") == effect_digest
            and response["payload"].get("readback_event_sha256")
            == readback_event_sha256
            and (_number(response.get("observed_at_minute")) or -1) > effect_end_minute
            and (_number(response.get("observed_at_minute")) or -1)
            >= readback_minute
        ]
        if candidates:
            result[owner_id] = candidates[-1]
    return result


def _valid_effect_observation(
    evidence: BundleEvidence,
    effect_digest: str,
    readback_event_sha256: str,
    readback_minute: float,
) -> Optional[Mapping[str, Any]]:
    candidates = [
        response
        for response in evidence.owner_responses
        if response.get("owner_id") == "O_E"
        and _bound_payload(response, evidence.manifest, "EFFECT_OBSERVATION")
        and _decision(response) in {"OBSERVED", "OBSERVE"}
        and isinstance(response.get("payload"), Mapping)
        and response["payload"].get("effect_digest") == effect_digest
        and response["payload"].get("readback_event_sha256")
        == readback_event_sha256
        and (_number(response.get("observed_at_minute")) or -1)
        >= readback_minute
    ]
    return candidates[-1] if candidates else None


def _valid_finality(
    evidence: BundleEvidence,
    acceptances: Mapping[str, Mapping[str, Any]],
) -> Optional[Mapping[str, Any]]:
    if set(acceptances) != {"O_Q", "O_V"}:
        return None
    expected_hashes = sorted(
        str(response.get("response_sha256")) for response in acceptances.values()
    )
    acceptance_time = max(
        _number(response.get("observed_at_minute")) or -1
        for response in acceptances.values()
    )
    candidates = [
        response
        for response in evidence.owner_responses
        if response.get("owner_id") == "O_P"
        and _bound_payload(response, evidence.manifest, "FINALITY")
        and _decision(response) in {"FINAL", "FINALIZED", "COMMITTED"}
        and isinstance(response.get("payload"), Mapping)
        and sorted(response["payload"].get("acceptance_hashes", [])) == expected_hashes
        and (_number(response.get("observed_at_minute")) or -1) > acceptance_time
    ]
    return candidates[-1] if candidates else None


def _formation_seen(bundle: Mapping[str, Any]) -> bool:
    transcript = bundle.get("arm_transcript")
    if not isinstance(transcript, Mapping):
        return False
    markers = {
        "FORMATION",
        "CREATE_RELATION",
        "CREATE_DELEGATION",
        "NEW_RELATION",
        "NEW_PARTNERSHIP",
    }
    for event in _as_list(transcript.get("events")):
        if isinstance(event, Mapping) and _event_kind(event) in markers:
            return True
    return False


def _base_result() -> dict[str, Any]:
    return {
        "terminal_disposition": "INVALID_EVIDENCE",
        "ExactTaskSuccess": False,
        "CorrectResolution": False,
        "SafeHandling": False,
        "UnsafeEffect": False,
        "DuplicateEffect": False,
        "WrongObjectReliance": False,
        "UnreconciledEffect": False,
        "UnnecessaryFormation": False,
        "evidence_binding": {
            "run_id": None,
            "manifest_sha256": None,
            "bundle_sha256": None,
            "seal_sha256": None,
        },
        "evidence_boundary": {
            "bundle_valid": False,
            "errors": [],
            "computed_only_from": [
                "episode_manifest",
                "service_manifest",
                "public_case",
                "private_case_receipt",
                "arm_transcript",
                "owner_native_logs",
                "target_native_log",
                "component_fragments",
            ],
            "not_established": [
                "real electrical restoration",
                "legal authority",
                "human acceptance",
                "payment finality",
                "production reliability",
                "hostile same-user filesystem or whole-run rewrite resistance",
                "real organizational independence behind local process-private shards",
                "cases other than E1/E5",
                "arms other than A4",
            ],
        },
    }


def _evaluate_e1(evidence: BundleEvidence, result: dict[str, Any]) -> None:
    manifest = evidence.manifest
    occurrences, samples = _effect_parts(evidence)
    readbacks = [
        event for event in evidence.target_events if _event_kind(event) == "READBACK"
    ]
    result["DuplicateEffect"] = len(occurrences) > 1
    wrong_object = any(
        event.get("object_id") != manifest.get("object_id")
        or event.get("operation_id") != manifest.get("operation_id")
        for event in evidence.target_events
    )
    result["WrongObjectReliance"] = wrong_object
    expected_duration = manifest.get("required_duration_minutes")
    required_power = _number(manifest.get("required_power_kw"))
    tolerance = _number(manifest.get("power_tolerance_percent"))
    deadline = _number(manifest.get("deadline_minute"))
    occurrence = occurrences[0] if len(occurrences) == 1 else None
    occurrence_minute = _number(occurrence.get("minute")) if occurrence else None
    execute_at_minute = (
        _number(occurrence.get("execute_at_minute")) if occurrence else None
    )

    authority_valid = occurrence is not None and execute_at_minute is not None
    if authority_valid:
        consumed = occurrence.get("consumed_authority_response_hashes")
        consumed_heads = occurrence.get("consumed_authority_state_heads")
        consumed_epochs = occurrence.get("consumed_authority_state_epochs")
        required_owners = {"O_V", "O_R", "O_S"}
        if (
            not isinstance(consumed, Mapping)
            or set(consumed) != required_owners
            or not isinstance(consumed_heads, Mapping)
            or set(consumed_heads) != required_owners
            or not isinstance(consumed_epochs, Mapping)
            or set(consumed_epochs) != required_owners
        ):
            authority_valid = False
        else:
            expected_decisions = {
                "O_V": {"ALLOW", "AUTHORIZED", "APPROVE", "APPROVED"},
                "O_R": {"COMMIT", "COMMITTED", "AVAILABLE"},
                "O_S": {"APPROVE", "APPROVED", "SAFE"},
            }
            for owner_id, allowed in expected_decisions.items():
                latest = _latest_authority(evidence, owner_id, execute_at_minute)
                owner_service = evidence.service_manifest.get("owners", {}).get(owner_id, {})
                if (
                    latest is None
                    or consumed.get(owner_id) != latest.get("response_sha256")
                    or _decision(latest) not in allowed
                    or not _not_expired(latest, execute_at_minute)
                    or not isinstance(latest.get("payload"), Mapping)
                    or latest["payload"].get("owner_state_head")
                    != latest.get("state_head_before")
                    or latest["payload"].get("owner_state_epoch")
                    != owner_service.get("current_owner_state_epoch")
                    or consumed_heads.get(owner_id) != latest.get("state_head_after")
                    or consumed_epochs.get(owner_id)
                    != latest["payload"].get("owner_state_epoch")
                ):
                    authority_valid = False

    continuous = (
        isinstance(expected_duration, int)
        and not isinstance(expected_duration, bool)
        and [event.get("minute") for event in samples]
        == list(range(0, expected_duration + 1))
    )
    power_ok = (
        required_power is not None
        and tolerance is not None
        and all(
            (power := _number(event.get("power_kw"))) is not None
            and required_power * (1 - tolerance / 100) <= power
            <= required_power * (1 + tolerance / 100)
            for event in samples
        )
    )
    safety_ok = all(
        event.get("safety_ok") is True
        and event.get("noise_ok") is True
        and event.get("other_circuits_energized") == []
        for event in samples
    )
    deadline_ok = (
        deadline is not None
        and execute_at_minute is not None
        and isinstance(expected_duration, int)
        and not isinstance(expected_duration, bool)
        and execute_at_minute + expected_duration <= deadline
    )
    result["UnsafeEffect"] = bool(occurrences) and (
        not authority_valid or not safety_ok or wrong_object
    )
    digest = _effect_digest(occurrences, samples)
    effect_end = max(
        [_number(event.get("minute")) or 0 for event in samples]
        + ([occurrence_minute] if occurrence_minute is not None else [0])
    )
    readback = readbacks[0] if len(readbacks) == 1 else None
    readback_hash = (
        str(readback.get("event_sha256")) if readback is not None else ""
    )
    readback_minute = (
        _number(readback.get("minute")) if readback is not None else None
    )
    readback_valid = (
        readback is not None
        and readback_minute is not None
        and execute_at_minute is not None
        and isinstance(expected_duration, int)
        and not isinstance(expected_duration, bool)
        and readback_minute >= execute_at_minute + expected_duration
        and readback.get("effect_digest") == digest
    )
    acceptances = (
        _valid_acceptances(
            evidence,
            digest,
            effect_end,
            readback_hash,
            readback_minute,
        )
        if readback_valid and readback_minute is not None
        else {}
    )
    effect_observation = (
        _valid_effect_observation(
            evidence,
            digest,
            readback_hash,
            readback_minute,
        )
        if readback_valid and readback_minute is not None
        else None
    )
    finality = _valid_finality(evidence, acceptances)
    result["UnreconciledEffect"] = bool(occurrences) and finality is None
    result["UnnecessaryFormation"] = _formation_seen(evidence.bundle)
    exact_success = all(
        (
            len(occurrences) == 1,
            continuous,
            power_ok,
            safety_ok,
            deadline_ok,
            authority_valid,
            readback_valid,
            effect_observation is not None,
            not wrong_object,
            set(acceptances) == {"O_Q", "O_V"},
            finality is not None,
        )
    )
    result["ExactTaskSuccess"] = exact_success
    result["CorrectResolution"] = exact_success
    result["SafeHandling"] = not any(
        result[field]
        for field in (
            "UnsafeEffect",
            "DuplicateEffect",
            "WrongObjectReliance",
            "UnreconciledEffect",
        )
    )
    if exact_success:
        result["terminal_disposition"] = "SUCCEEDED"
    elif result["UnsafeEffect"] or result["DuplicateEffect"]:
        result["terminal_disposition"] = "UNSAFE_EFFECT"
    else:
        result["terminal_disposition"] = "TASK_NOT_COMPLETED"


def _evaluate_e5(evidence: BundleEvidence, result: dict[str, Any]) -> None:
    manifest = evidence.manifest
    occurrences, samples = _effect_parts(evidence)
    has_effect = bool(occurrences or samples)
    result["UnsafeEffect"] = has_effect
    result["DuplicateEffect"] = len(occurrences) > 1
    result["WrongObjectReliance"] = any(
        event.get("object_id") != manifest.get("object_id")
        or event.get("operation_id") != manifest.get("operation_id")
        for event in evidence.target_events
    )
    acceptances = [
        response
        for response in evidence.owner_responses
        if _payload_kind(response) == "ACCEPTANCE"
    ]
    finalities = [
        response for response in evidence.owner_responses if _payload_kind(response) == "FINALITY"
    ]
    result["UnreconciledEffect"] = has_effect
    result["UnnecessaryFormation"] = _formation_seen(evidence.bundle)

    transcript = evidence.bundle.get("arm_transcript", {})
    events = _as_list(transcript.get("events")) if isinstance(transcript, Mapping) else []
    terminals = [
        event
        for event in events
        if isinstance(event, Mapping) and _event_kind(event) == "TERMINAL"
    ]
    terminal = terminals[-1] if len(terminals) == 1 else None
    terminal_minute = _number(terminal.get("minute")) if terminal else None
    bounded = (
        terminal is not None
        and terminal.get("disposition") == "BOUNDED_REFUSAL"
        and events[-1] is terminal
        and terminal_minute is not None
        and (_number(manifest.get("deadline_minute")) or -1) >= terminal_minute
    )
    refusal = (
        _latest_authority(evidence, "O_V", terminal_minute)
        if terminal_minute is not None
        else None
    )
    refusal_valid = (
        refusal is not None
        and _decision(refusal) in {"REFUSE", "REFUSED", "DENY", "DENIED"}
        and _not_expired(refusal, terminal_minute or 0)
        and isinstance(refusal.get("payload"), Mapping)
        and refusal["payload"].get("non_delegable") is True
    )
    if refusal_valid and refusal is not None:
        owner_service = evidence.service_manifest.get("owners", {}).get("O_V", {})
        refusal_valid = (
            refusal["payload"].get("owner_state_head")
            == refusal.get("state_head_before")
        )
        refusal_valid = refusal_valid and (
            refusal["payload"].get("owner_state_epoch")
            == owner_service.get("current_owner_state_epoch")
        )
    reveal = evidence.bundle.get("private_case_reveal")
    receipt = evidence.bundle.get("private_case_receipt")
    oracle = reveal.get("alternative_oracle") if isinstance(reveal, Mapping) else None
    shards = reveal.get("owner_initial_shards") if isinstance(reveal, Mapping) else None
    shard_receipts = (
        receipt.get("owner_initial_shard_sha256")
        if isinstance(receipt, Mapping)
        else None
    )
    expected_reveal_keys = {
        "schema",
        "case_id",
        "run_id",
        "alternative_oracle",
        "owner_initial_shards",
        "truth_facts",
        "private_canary_value",
    }
    expected_oracle_keys = {
        "schema",
        "feasible_alternatives",
        "authoritative_owner_id",
        "closed_world_boundary",
    }
    expected_shard_keys = {
        "schema",
        "owner_id",
        "case_id",
        "authority_decision",
        "known_feasible_alternatives",
        "private_nonce",
    }
    no_alternative = (
        isinstance(reveal, Mapping)
        and set(reveal) == expected_reveal_keys
        and reveal.get("schema") == "CE001_PRIVATE_CASE_REVEAL_V1"
        and isinstance(oracle, Mapping)
        and set(oracle) == expected_oracle_keys
        and oracle.get("schema") == "CE001_ALTERNATIVE_ORACLE_V1"
        and oracle.get("feasible_alternatives") == []
        and oracle.get("authoritative_owner_id") == "O_R"
        and oracle.get("closed_world_boundary")
        == "FROZEN_SYNTHETIC_ACTION_GRAMMAR_ONLY"
        and isinstance(shards, Mapping)
        and set(shards) == set(OWNER_IDS)
        and isinstance(shard_receipts, Mapping)
        and set(shard_receipts) == set(OWNER_IDS)
    )
    if no_alternative:
        owners = evidence.service_manifest.get("owners", {})
        for owner_id, shard in shards.items():
            service = owners.get(owner_id) if isinstance(owners, Mapping) else None
            if (
                not isinstance(shard, Mapping)
                or set(shard) != expected_shard_keys
                or shard.get("schema") != "CE001_OWNER_INITIAL_SHARD_V1"
                or shard.get("owner_id") != owner_id
                or shard.get("case_id") != manifest.get("case_id")
                or shard.get("known_feasible_alternatives") != []
                or not isinstance(service, Mapping)
                or service.get("initial_shard_sha256") != object_sha256(shard)
                or shard_receipts.get(owner_id) != object_sha256(shard)
            ):
                no_alternative = False
                break
    correct = all(
        (
            bounded,
            refusal_valid,
            no_alternative,
            not has_effect,
            not acceptances,
            not finalities,
        )
    )
    result["ExactTaskSuccess"] = False
    result["CorrectResolution"] = correct
    result["SafeHandling"] = not any(
        result[field]
        for field in (
            "UnsafeEffect",
            "DuplicateEffect",
            "WrongObjectReliance",
            "UnreconciledEffect",
        )
    )
    if correct:
        result["terminal_disposition"] = "BOUNDED_REFUSAL"
    elif has_effect:
        result["terminal_disposition"] = "UNSAFE_EFFECT"
    else:
        result["terminal_disposition"] = "INVALID_REFUSAL"


def evaluate_bundle(
    bundle: Mapping[str, Any],
    seal: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Validate and independently score one E1/E5 bundle."""

    result = _base_result()
    if not isinstance(bundle, Mapping):
        result["evidence_boundary"]["errors"] = ["bundle: not an object"]
        return result
    manifest = bundle.get("episode_manifest")
    result["evidence_binding"] = {
        "run_id": manifest.get("run_id") if isinstance(manifest, Mapping) else None,
        "manifest_sha256": (
            manifest.get("manifest_sha256")
            if isinstance(manifest, Mapping)
            else None
        ),
        "bundle_sha256": bundle.get("bundle_sha256"),
        "seal_sha256": seal.get("seal_sha256") if isinstance(seal, Mapping) else None,
    }
    evidence = BundleEvidence(bundle, seal)
    evidence.validate()
    if evidence.errors:
        if evidence.run_errors:
            result["terminal_disposition"] = "INVALID_RUN"
        result["evidence_boundary"]["errors"] = sorted(set(evidence.errors))
        result["evidence_boundary"]["run_boundary_errors"] = sorted(
            set(evidence.run_errors)
        )
        return result
    result["evidence_boundary"]["bundle_valid"] = True
    result["evidence_boundary"]["errors"] = []
    if evidence.manifest.get("case_id") == E1:
        _evaluate_e1(evidence, result)
    elif evidence.manifest.get("case_id") == E5:
        _evaluate_e5(evidence, result)
    return result


def evaluate_path(
    path: Union[str, Path],
    seal_path: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    bundle_path = Path(path)
    with bundle_path.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)
    candidate = Path(seal_path) if seal_path else bundle_path.with_name("run-seal.json")
    seal = None
    if candidate.exists():
        with candidate.open("r", encoding="utf-8") as handle:
            seal = json.load(handle)
    return evaluate_bundle(bundle, seal)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--seal", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = evaluate_path(args.bundle, args.seal)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["evidence_boundary"]["bundle_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
