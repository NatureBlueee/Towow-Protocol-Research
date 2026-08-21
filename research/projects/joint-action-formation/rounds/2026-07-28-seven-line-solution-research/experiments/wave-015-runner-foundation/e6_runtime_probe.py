"""Actual-process E6 runtime probe for the Wave 015 runner foundation.

The probe launches source, migrated, and old-runtime-restart processes through
one asynchronous extension of ``BlindProcessLauncher``.  It tests runtime
visibility, exact controller triggering, capsule binding, and an in-memory
controller epoch fence.  It does not implement or claim the full E6 scenario.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import os
import pathlib
import queue
import secrets
import sys
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from hidden_world import HiddenScenarioController
from visibility import (
    ARM_VIEW_SCHEMA,
    LAUNCH_RECEIPT_SCHEMA,
    PUBLIC_INPUT_SCHEMA,
    ArmViewFactory,
    BlindProcessLauncher,
    VisibilityViolation,
    _SPAWN_LOCK,
    _assert_no_material,
    _fd_inventory,
    canonical_bytes,
    sha256_value,
    validate_arm_view,
)


RUNTIME_VIEW_SCHEMA = ARM_VIEW_SCHEMA
RUNTIME_IDS = ("source", "migrated", "old_runtime_restart")
SCENARIO_LABEL = "E6-MIGRATION-REPLAY"


def _public_key_hex(private_key: Ed25519PrivateKey) -> str:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def _signed(
    private_key: Ed25519PrivateKey, value: Mapping[str, Any]
) -> Dict[str, Any]:
    result = dict(value)
    result["signature_hex"] = private_key.sign(canonical_bytes(value)).hex()
    return result


def verify_signed(value: Mapping[str, Any], public_key_hex: str) -> bool:
    signature_hex = value.get("signature_hex")
    if not isinstance(signature_hex, str):
        return False
    unsigned = dict(value)
    unsigned.pop("signature_hex", None)
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex)).verify(
            bytes.fromhex(signature_hex), canonical_bytes(unsigned)
        )
    except (ValueError, InvalidSignature):
        return False
    return True


def verify_capsule(
    capsule: Mapping[str, Any],
    *,
    expected_source_public_key_hex: str,
    expected_episode_instance_id: str,
    expected_operation_id: str,
    expected_public_view_sha256: str,
) -> bool:
    if capsule.get("schema") != "E6_RECOVERY_CAPSULE_V1":
        return False
    if capsule.get("source_public_key_hex") != expected_source_public_key_hex:
        return False
    if capsule.get("episode_instance_id") != expected_episode_instance_id:
        return False
    if capsule.get("operation_id") != expected_operation_id:
        return False
    if capsule.get("public_view_sha256") != expected_public_view_sha256:
        return False
    return verify_signed(capsule, expected_source_public_key_hex)


def _runtime_child_entry(
    arm_view: Mapping[str, Any],
    child_cwd: str,
    minimal_environment: Mapping[str, str],
    command_queue: Any,
    event_queue: Any,
) -> None:
    """One generic runtime loop used for all three lifecycle positions."""

    sys.argv[:] = ["wave015-blind-child", "--opaque"]
    os.chdir(child_cwd)
    os.environ.clear()
    os.environ.update(dict(minimal_environment))
    view = validate_arm_view(arm_view)
    private_key = Ed25519PrivateKey.generate()
    runtime_instance_id = uuid.uuid4().hex
    public_key_hex = _public_key_hex(private_key)
    identity = _signed(
        private_key,
        {
            "schema": "E6_RUNTIME_IDENTITY_V1",
            "runtime_instance_id": runtime_instance_id,
            "process_id": os.getpid(),
            "public_key_hex": public_key_hex,
            "public_view_sha256": sha256_value(view),
            "start_method": multiprocessing.get_start_method(),
        },
    )
    visible_surface = {
        "view": view,
        "view_bytes": canonical_bytes(view).decode("utf-8"),
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "cwd_entries": sorted(path.name for path in pathlib.Path.cwd().iterdir()),
        "process_name": multiprocessing.current_process().name,
        "environment": dict(sorted(os.environ.items())),
        "inherited_file_descriptors": _fd_inventory(),
    }
    event_queue.put(
        {
            "kind": "RUNTIME_READY",
            "visible_surface": visible_surface,
            "identity": identity,
        }
    )

    last_native_event_sha256: Optional[str] = None
    while True:
        command = command_queue.get()
        kind = command.get("kind")
        if kind == "EMIT_NATIVE_EVENT":
            body = copy.deepcopy(command["event_body"])
            body_sha256 = sha256_value(body)
            record = _signed(
                private_key,
                {
                    "schema": "E6_RUNTIME_NATIVE_EVENT_V1",
                    "runtime_instance_id": runtime_instance_id,
                    "process_id": os.getpid(),
                    "runtime_public_key_hex": public_key_hex,
                    "body": body,
                    "body_sha256": body_sha256,
                },
            )
            last_native_event_sha256 = body_sha256
            event_queue.put({"kind": "NATIVE_EVENT", "record": record})
        elif kind == "EXPORT_CAPSULE":
            if command["native_event_sha256"] != last_native_event_sha256:
                event_queue.put(
                    {"kind": "CAPSULE_REJECTED", "reason": "NATIVE_EVENT_MISMATCH"}
                )
                continue
            capsule = _signed(
                private_key,
                {
                    "schema": "E6_RECOVERY_CAPSULE_V1",
                    "capsule_id": uuid.uuid4().hex,
                    "source_runtime_instance_id": runtime_instance_id,
                    "source_process_id": os.getpid(),
                    "source_public_key_hex": public_key_hex,
                    "episode_instance_id": view["episode_instance_id"],
                    "operation_id": view["operation_id"],
                    "public_view_sha256": sha256_value(view),
                    "source_epoch": command["source_epoch"],
                    "native_event_sha256": last_native_event_sha256,
                    "history_head": command["history_head"],
                    "pending_obligations": list(command["pending_obligations"]),
                },
            )
            event_queue.put({"kind": "CAPSULE_EXPORTED", "capsule": capsule})
        elif kind == "ATTEMPT_ACTION":
            capsule = command.get("capsule")
            if capsule is not None and not verify_capsule(
                capsule,
                expected_source_public_key_hex=command[
                    "expected_source_public_key_hex"
                ],
                expected_episode_instance_id=view["episode_instance_id"],
                expected_operation_id=view["operation_id"],
                expected_public_view_sha256=sha256_value(view),
            ):
                event_queue.put(
                    {
                        "kind": "ACTION_RESULT",
                        "status": "CAPSULE_REJECTED",
                        "executed": False,
                    }
                )
                continue
            request = _signed(
                private_key,
                {
                    "schema": "E6_FENCE_REQUEST_V1",
                    "request_id": uuid.uuid4().hex,
                    "runtime_instance_id": runtime_instance_id,
                    "runtime_process_id": os.getpid(),
                    "runtime_public_key_hex": public_key_hex,
                    "episode_instance_id": view["episode_instance_id"],
                    "operation_id": view["operation_id"],
                    "requested_epoch": command["requested_epoch"],
                    "action": command["action"],
                    "capsule_sha256": (
                        sha256_value(capsule) if capsule is not None else None
                    ),
                },
            )
            event_queue.put({"kind": "FENCE_REQUEST", "request": request})
            decision = command_queue.get()
            if decision.get("kind") != "FENCE_DECISION":
                event_queue.put(
                    {
                        "kind": "ACTION_RESULT",
                        "status": "INVALID_CONTROLLER_RESPONSE",
                        "executed": False,
                    }
                )
                continue
            receipt = decision["receipt"]
            accepted = (
                receipt.get("decision") == "ACCEPTED"
                and receipt.get("request_sha256") == sha256_value(request)
            )
            event_queue.put(
                {
                    "kind": "ACTION_RESULT",
                    "status": receipt.get("decision"),
                    "executed": accepted,
                    "request": request,
                    "fence_receipt": receipt,
                }
            )
        elif kind == "STOP":
            event_queue.put({"kind": "RUNTIME_STOPPED"})
            return
        else:
            event_queue.put({"kind": "UNKNOWN_COMMAND", "executed": False})


@dataclass
class RunningRuntime:
    process: multiprocessing.Process
    command_queue: Any
    event_queue: Any
    temporary_directory: tempfile.TemporaryDirectory
    launch_receipt: Dict[str, Any]


class E6BlindProcessLauncher(BlindProcessLauncher):
    """Minimal asynchronous extension; foundation launcher remains unchanged."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.launcher_instance_id = uuid.uuid4().hex
        self.worker_code_sha256 = hashlib.sha256(
            _runtime_child_entry.__code__.co_code
        ).hexdigest()

    def start_runtime(
        self,
        arm_view: Mapping[str, Any],
        *,
        private_materials: Sequence[Any] = (),
    ) -> RunningRuntime:
        view = validate_arm_view(arm_view)
        _assert_no_material(view, private_materials, where="E6 runtime arm view")
        context = multiprocessing.get_context("spawn")
        command_queue = context.Queue()
        event_queue = context.Queue()
        child_name = "arm-worker-%s" % secrets.token_hex(8)
        temporary_directory = tempfile.TemporaryDirectory(prefix="wave015-arm-")
        process = context.Process(
            target=_runtime_child_entry,
            name=child_name,
            args=(
                view,
                temporary_directory.name,
                self._minimal_environment,
                command_queue,
                event_queue,
            ),
        )
        with _SPAWN_LOCK:
            parent_argv = list(sys.argv)
            parent_cwd = os.getcwd()
            parent_environment = dict(os.environ)
            sys.argv[:] = ["wave015-blind-child", "--opaque"]
            os.chdir(temporary_directory.name)
            os.environ.clear()
            os.environ.update(self._minimal_environment)
            try:
                process.start()
            finally:
                sys.argv[:] = parent_argv
                os.chdir(parent_cwd)
                os.environ.clear()
                os.environ.update(parent_environment)
        try:
            ready = event_queue.get(timeout=self._timeout_seconds)
        except queue.Empty as exc:
            process.terminate()
            process.join(timeout=5)
            temporary_directory.cleanup()
            raise VisibilityViolation("E6 blind runtime did not become ready") from exc
        if ready.get("kind") != "RUNTIME_READY":
            process.terminate()
            process.join(timeout=5)
            temporary_directory.cleanup()
            raise VisibilityViolation("E6 blind runtime failed before ready")
        surface = ready["visible_surface"]
        _assert_no_material(
            surface, private_materials, where="E6 child visible surface"
        )
        if surface["view"] != view:
            raise VisibilityViolation("E6 child received a different arm view")
        if surface["argv"] != ["wave015-blind-child", "--opaque"]:
            raise VisibilityViolation("E6 child argv was not sanitized")
        if surface["process_name"] != child_name:
            raise VisibilityViolation("E6 child process name was not sanitized")
        if surface["cwd_entries"]:
            raise VisibilityViolation("E6 child cwd was not empty")
        if surface["environment"] != dict(sorted(self._minimal_environment.items())):
            raise VisibilityViolation("E6 child environment was not sanitized")
        identity = ready["identity"]
        if not verify_signed(identity, identity.get("public_key_hex", "")):
            raise VisibilityViolation("E6 runtime identity signature invalid")
        receipt = {
            "schema": LAUNCH_RECEIPT_SCHEMA,
            "status": "CHILD_RUNTIME_READY",
            "process_start_method": "spawn",
            "launcher_instance_id": self.launcher_instance_id,
            "worker_code_sha256": self.worker_code_sha256,
            "exit_code_at_ready": None,
            "visible_surface": surface,
            "visible_surface_sha256": sha256_value(surface),
            "runtime_identity": identity,
            "private_material_absent": True,
            "isolation_boundary": (
                "COOPERATIVE_SPAWN_VISIBILITY_BOUNDARY; "
                "ASYNC_EXTENSION_LOCAL_TO_E6_PROBE"
            ),
        }
        return RunningRuntime(
            process=process,
            command_queue=command_queue,
            event_queue=event_queue,
            temporary_directory=temporary_directory,
            launch_receipt=receipt,
        )

    def recv(self, runtime: RunningRuntime, expected_kind: str) -> Dict[str, Any]:
        try:
            event = runtime.event_queue.get(timeout=self._timeout_seconds)
        except queue.Empty as exc:
            raise VisibilityViolation(
                "E6 runtime did not emit %s" % expected_kind
            ) from exc
        if event.get("kind") != expected_kind:
            raise VisibilityViolation(
                "expected %s, received %s"
                % (expected_kind, event.get("kind"))
            )
        return event

    def stop(self, runtime: RunningRuntime) -> int:
        if runtime.process.is_alive():
            runtime.command_queue.put({"kind": "STOP"})
            self.recv(runtime, "RUNTIME_STOPPED")
        runtime.process.join(timeout=self._timeout_seconds)
        if runtime.process.is_alive():
            runtime.process.terminate()
            runtime.process.join(timeout=5)
        exit_code = runtime.process.exitcode
        runtime.temporary_directory.cleanup()
        return exit_code

    def terminate_after_trigger(self, runtime: RunningRuntime) -> int:
        runtime.process.terminate()
        runtime.process.join(timeout=self._timeout_seconds)
        if runtime.process.is_alive():
            runtime.process.kill()
            runtime.process.join(timeout=5)
        exit_code = runtime.process.exitcode
        runtime.temporary_directory.cleanup()
        return exit_code


class ControllerEpochFence:
    """Controller-lifetime epoch register with signed decisions."""

    def __init__(self, *, episode_instance_id: str, operation_id: str) -> None:
        self._private_key = Ed25519PrivateKey.generate()
        self.public_key_hex = _public_key_hex(self._private_key)
        self.fence_instance_id = uuid.uuid4().hex
        self.episode_instance_id = episode_instance_id
        self.operation_id = operation_id
        self.current_epoch = 1
        self._runtime_registry: Dict[str, Dict[str, Any]] = {}
        self._seen_request_ids: set = set()

    def register_runtime(self, identity: Mapping[str, Any]) -> None:
        if not verify_signed(identity, identity.get("public_key_hex", "")):
            raise ValueError("runtime identity invalid")
        self._runtime_registry[identity["runtime_instance_id"]] = {
            "process_id": identity["process_id"],
            "public_key_hex": identity["public_key_hex"],
        }

    def advance(
        self,
        *,
        target_epoch: int,
        trigger_receipt_id: str,
        capsule_sha256: str,
    ) -> Dict[str, Any]:
        if target_epoch <= self.current_epoch:
            raise ValueError("target epoch must advance")
        previous_epoch = self.current_epoch
        self.current_epoch = target_epoch
        return _signed(
            self._private_key,
            {
                "schema": "E6_FENCE_ADVANCE_V1",
                "fence_instance_id": self.fence_instance_id,
                "episode_instance_id": self.episode_instance_id,
                "operation_id": self.operation_id,
                "previous_epoch": previous_epoch,
                "current_epoch": self.current_epoch,
                "trigger_receipt_id": trigger_receipt_id,
                "capsule_sha256": capsule_sha256,
            },
        )

    def authorize(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        runtime = self._runtime_registry.get(request.get("runtime_instance_id"))
        request_valid = (
            runtime is not None
            and runtime["process_id"] == request.get("runtime_process_id")
            and runtime["public_key_hex"] == request.get("runtime_public_key_hex")
            and verify_signed(request, runtime["public_key_hex"])
            and request.get("episode_instance_id") == self.episode_instance_id
            and request.get("operation_id") == self.operation_id
        )
        if not request_valid:
            decision = "REJECTED_INVALID_RUNTIME"
        elif request["request_id"] in self._seen_request_ids:
            decision = "REJECTED_REPLAY"
        elif request.get("requested_epoch") != self.current_epoch:
            decision = "REJECTED_STALE_EPOCH"
        else:
            decision = "ACCEPTED"
        if request_valid:
            self._seen_request_ids.add(request["request_id"])
        return _signed(
            self._private_key,
            {
                "schema": "E6_FENCE_DECISION_V1",
                "fence_instance_id": self.fence_instance_id,
                "episode_instance_id": self.episode_instance_id,
                "operation_id": self.operation_id,
                "request_sha256": sha256_value(request),
                "requested_epoch": request.get("requested_epoch"),
                "current_epoch": self.current_epoch,
                "action": request.get("action"),
                "decision": decision,
            },
        )

    def verify_receipt(self, receipt: Mapping[str, Any]) -> bool:
        return verify_fence_receipt(receipt, self.identity())

    def identity(self) -> Dict[str, Any]:
        return {
            "fence_instance_id": self.fence_instance_id,
            "episode_instance_id": self.episode_instance_id,
            "operation_id": self.operation_id,
            "public_key_hex": self.public_key_hex,
        }


def verify_fence_receipt(
    receipt: Mapping[str, Any], fence_identity: Mapping[str, Any]
) -> bool:
    return (
        receipt.get("fence_instance_id")
        == fence_identity.get("fence_instance_id")
        and receipt.get("episode_instance_id")
        == fence_identity.get("episode_instance_id")
        and receipt.get("operation_id") == fence_identity.get("operation_id")
        and verify_signed(receipt, fence_identity.get("public_key_hex", ""))
    )


def evaluate_action_result(
    result: Mapping[str, Any], fence_identity: Mapping[str, Any]
) -> Dict[str, Any]:
    receipt = result.get("fence_receipt")
    request = result.get("request")
    if not isinstance(receipt, Mapping) or not isinstance(request, Mapping):
        return {"valid": False, "authorized_execution": False}
    valid = (
        verify_fence_receipt(receipt, fence_identity)
        and receipt.get("request_sha256") == sha256_value(request)
        and result.get("status") == receipt.get("decision")
        and result.get("executed") == (receipt.get("decision") == "ACCEPTED")
    )
    return {
        "valid": valid,
        "authorized_execution": valid and receipt.get("decision") == "ACCEPTED",
        "decision": receipt.get("decision"),
    }


def _public_input() -> Dict[str, Any]:
    return {
        "schema": PUBLIC_INPUT_SCHEMA,
        "task": {
            "q_version": "Q@v1",
            "object_id": "VenueV:CircuitC7",
            "target_id": "VenueV:CircuitC7",
            "deadline_minute": 90,
            "required_duration_minutes": 45,
            "required_power_kw": 3.0,
            "power_tolerance_percent": 5,
        },
    }


def _do_fenced_action(
    launcher: E6BlindProcessLauncher,
    runtime: RunningRuntime,
    fence: ControllerEpochFence,
    *,
    requested_epoch: int,
    action: str,
    capsule: Optional[Mapping[str, Any]],
    source_public_key_hex: Optional[str],
) -> Dict[str, Any]:
    runtime.command_queue.put(
        {
            "kind": "ATTEMPT_ACTION",
            "requested_epoch": requested_epoch,
            "action": action,
            "capsule": copy.deepcopy(capsule),
            "expected_source_public_key_hex": source_public_key_hex,
        }
    )
    request_event = launcher.recv(runtime, "FENCE_REQUEST")
    receipt = fence.authorize(request_event["request"])
    runtime.command_queue.put({"kind": "FENCE_DECISION", "receipt": receipt})
    return launcher.recv(runtime, "ACTION_RESULT")


def run_e6_runtime_probe() -> Dict[str, Any]:
    factory = ArmViewFactory(arm_id="A4-DETERMINISTIC-MATURE-COMPOSITION")
    event_body_seed = {
        "kind": "TARGET_READBACK_OBSERVED",
        "logical_minute": 46,
        "readback_status": "EXACT_EFFECT_PRESENT",
        "history_head": "h-" + ("4" * 64),
    }
    trigger_event_sha256 = sha256_value(event_body_seed)
    schedule = {
        "trigger_event_sha256": trigger_event_sha256,
        "trigger_logical_minute": 46,
        "crash_cut": "AFTER_TARGET_READBACK_BEFORE_ACCEPTANCE",
        "target_epoch": 2,
        "old_runtime_restart_minute": 49,
    }
    private_materials = (
        SCENARIO_LABEL,
        schedule,
        schedule["crash_cut"],
        trigger_event_sha256,
    )
    arm_view = factory.build(
        _public_input(), private_materials=private_materials
    )
    episode_binding = arm_view["episode_instance_id"]
    controller = HiddenScenarioController()
    frozen = controller.freeze_e6(
        episode_binding=episode_binding,
        base_arm_view=arm_view,
        schedule=schedule,
    )
    launcher = E6BlindProcessLauncher(timeout_seconds=10)
    fence = ControllerEpochFence(
        episode_instance_id=arm_view["episode_instance_id"],
        operation_id=arm_view["operation_id"],
    )
    handles: Dict[str, RunningRuntime] = {}
    launch_receipts: Dict[str, Dict[str, Any]] = {}
    exit_codes: Dict[str, int] = {}
    try:
        source = launcher.start_runtime(
            arm_view, private_materials=private_materials
        )
        handles["source"] = source
        launch_receipts["source"] = source.launch_receipt
        fence.register_runtime(source.launch_receipt["runtime_identity"])
        source.command_queue.put(
            {"kind": "EMIT_NATIVE_EVENT", "event_body": event_body_seed}
        )
        source_event = launcher.recv(source, "NATIVE_EVENT")["record"]
        if source_event["body_sha256"] != trigger_event_sha256:
            raise RuntimeError("source emitted unexpected native event")
        source_identity = source.launch_receipt["runtime_identity"]
        if not verify_signed(source_event, source_identity["public_key_hex"]):
            raise RuntimeError("source native event signature invalid")
        trigger_packet = controller.maybe_fire_e6(
            frozen,
            episode_binding=episode_binding,
            native_event_sha256=source_event["body_sha256"],
            logical_minute=source_event["body"]["logical_minute"],
        )
        if trigger_packet is None:
            raise RuntimeError("controller did not fire exact E6 schedule")
        source.command_queue.put(
            {
                "kind": "EXPORT_CAPSULE",
                "native_event_sha256": source_event["body_sha256"],
                "source_epoch": 1,
                "history_head": source_event["body"]["history_head"],
                "pending_obligations": [
                    "OWNER_ACCEPTANCE",
                    "VENUE_ACCEPTANCE",
                    "FINALITY",
                ],
            }
        )
        capsule = launcher.recv(source, "CAPSULE_EXPORTED")["capsule"]
        if not verify_capsule(
            capsule,
            expected_source_public_key_hex=source_identity["public_key_hex"],
            expected_episode_instance_id=arm_view["episode_instance_id"],
            expected_operation_id=arm_view["operation_id"],
            expected_public_view_sha256=sha256_value(arm_view),
        ):
            raise RuntimeError("source capsule invalid")
        exit_codes["source"] = launcher.terminate_after_trigger(source)
        handles.pop("source")
        fence_advance = fence.advance(
            target_epoch=2,
            trigger_receipt_id=trigger_packet["receipt"]["receipt_id"],
            capsule_sha256=sha256_value(capsule),
        )

        migrated = launcher.start_runtime(
            arm_view, private_materials=private_materials
        )
        handles["migrated"] = migrated
        launch_receipts["migrated"] = migrated.launch_receipt
        fence.register_runtime(migrated.launch_receipt["runtime_identity"])
        migrated_result = _do_fenced_action(
            launcher,
            migrated,
            fence,
            requested_epoch=2,
            action="RECOVER_POSTCONDITIONS_NO_EXECUTE",
            capsule=capsule,
            source_public_key_hex=source_identity["public_key_hex"],
        )
        exit_codes["migrated"] = launcher.stop(migrated)
        handles.pop("migrated")

        old_runtime = launcher.start_runtime(
            arm_view, private_materials=private_materials
        )
        handles["old_runtime_restart"] = old_runtime
        launch_receipts["old_runtime_restart"] = old_runtime.launch_receipt
        fence.register_runtime(old_runtime.launch_receipt["runtime_identity"])
        old_result = _do_fenced_action(
            launcher,
            old_runtime,
            fence,
            requested_epoch=1,
            action="REPLAY_EXECUTE",
            capsule=None,
            source_public_key_hex=None,
        )
        exit_codes["old_runtime_restart"] = launcher.stop(old_runtime)
        handles.pop("old_runtime_restart")
    finally:
        for runtime in handles.values():
            if runtime.process.is_alive():
                runtime.process.terminate()
                runtime.process.join(timeout=5)
            runtime.temporary_directory.cleanup()

    view_hashes = {
        runtime_id: receipt["runtime_identity"]["public_view_sha256"]
        for runtime_id, receipt in launch_receipts.items()
    }
    return {
        "probe_id": "E6_RUNTIME_PROBE",
        "arm_view_schema": RUNTIME_VIEW_SCHEMA,
        "arm_view": arm_view,
        "private_schedule_packet": frozen["private_packet"],
        "controller_identity": {
            "controller_instance_id": controller.controller_instance_id,
            "controller_public_key_hex": controller.public_key_hex,
        },
        "source_native_event": source_event,
        "trigger_packet": trigger_packet,
        "capsule": capsule,
        "fence_public_key_hex": fence.public_key_hex,
        "fence_identity": fence.identity(),
        "fence_advance_receipt": fence_advance,
        "launch_receipts": launch_receipts,
        "exit_codes": exit_codes,
        "migrated_action_result": migrated_result,
        "old_runtime_action_result": old_result,
        "lifecycle_trace": [
            {
                "step": 1,
                "event": "SOURCE_NATIVE_EVENT",
                "native_event_sha256": source_event["body_sha256"],
            },
            {
                "step": 2,
                "event": "EXACT_SCHEDULE_TRIGGERED",
                "trigger_receipt_id": trigger_packet["receipt"]["receipt_id"],
            },
            {
                "step": 3,
                "event": "SOURCE_CAPSULE_EXPORTED",
                "capsule_sha256": sha256_value(capsule),
            },
            {
                "step": 4,
                "event": "SOURCE_EXTERNALLY_TERMINATED",
                "exit_code": exit_codes["source"],
            },
            {
                "step": 5,
                "event": "FENCE_ADVANCED",
                "current_epoch": fence_advance["current_epoch"],
            },
            {
                "step": 6,
                "event": "MIGRATED_EPOCH_DECIDED",
                "decision": migrated_result["fence_receipt"]["decision"],
            },
            {
                "step": 7,
                "event": "OLD_RUNTIME_EPOCH_DECIDED",
                "decision": old_result["fence_receipt"]["decision"],
            },
        ],
        "same_arm_view_schema": all(
            receipt["visible_surface"]["view"]["schema"] == RUNTIME_VIEW_SCHEMA
            for receipt in launch_receipts.values()
        ),
        "same_arm_view_hash": len(set(view_hashes.values())) == 1,
        "migrated_action_evaluation": evaluate_action_result(
            migrated_result, fence.identity()
        ),
        "old_runtime_action_evaluation": evaluate_action_result(
            old_result, fence.identity()
        ),
        "evidence_boundary": (
            "ACTUAL_LOCAL_SPAWN_LIFECYCLE_PROBE; "
            "NO_TARGET_EFFECT_OR_FULL_E6_COMPLETION"
        ),
    }
