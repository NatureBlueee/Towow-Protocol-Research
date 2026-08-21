"""Fail-closed arm visibility primitives for the Wave 015 runner.

This module deliberately does not accept a complete episode manifest or bundle.
``ArmViewFactory`` builds a new public object from an exact allowlist.
``BlindProcessLauncher`` starts a real multiprocessing ``spawn`` child and
returns what that child actually observed after its visibility boundary was
installed.

The boundary is cooperative local-process isolation.  It does not claim to
resist a hostile process with the same OS-user filesystem and process rights.
"""

from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import os
import pathlib
import re
import secrets
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


PUBLIC_INPUT_SCHEMA = "CE001_ARM_PUBLIC_INPUT_V1"
ARM_VIEW_SCHEMA = "CE001_ARM_VIEW_V1"
LAUNCH_RECEIPT_SCHEMA = "CE001_BLIND_LAUNCH_RECEIPT_V1"

PUBLIC_INPUT_FIELDS = frozenset({"schema", "task"})
PUBLIC_TASK_FIELDS = frozenset(
    {
        "q_version",
        "object_id",
        "target_id",
        "deadline_minute",
        "required_duration_minutes",
        "required_power_kw",
        "power_tolerance_percent",
    }
)
ARM_VIEW_FIELDS = frozenset(
    {
        "schema",
        "arm_id",
        "public_run_id",
        "episode_instance_id",
        "arm_binding_token",
        "q_version",
        "object_id",
        "target_id",
        "operation_id",
        "deadline_minute",
        "required_duration_minutes",
        "required_power_kw",
        "power_tolerance_percent",
        "broker_surface",
    }
)
BROKER_SURFACE_FIELDS = frozenset(
    {"endpoint_handle", "capabilities", "surface_version"}
)

DEFAULT_BROKER_CAPABILITIES = (
    "DISCOVER",
    "REQUEST",
    "STATUS",
)

_OPAQUE_PATTERNS = {
    "public_run_id": re.compile(r"run-[0-9a-f]{32}\Z"),
    "episode_instance_id": re.compile(r"episode-[0-9a-f]{32}\Z"),
    "arm_binding_token": re.compile(r"arm-bind-[0-9a-f]{64}\Z"),
    "operation_id": re.compile(r"operation-[0-9a-f]{32}\Z"),
}
_ARM_ID_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9_.-]{2,95}\Z")
_CAPABILITY_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9_.-]{2,95}\Z")
_SEMANTIC_CASE_PATTERN = re.compile(
    r"(?:\bE[0-9]+[A-Z]?-[A-Z0-9_-]+\b|"
    r"ACK[-_ ]LOST|IMPOSSIBLE[-_ ]REFUSAL|"
    r"REVOKE[-_ ]WITH[-_ ]ALTERNATIVE|MIGRATION[-_ ]REPLAY)",
    re.IGNORECASE,
)
_PRIVATE_FIELD_NAMES = frozenset(
    {
        "case",
        "case_id",
        "semantic_case",
        "expected",
        "expected_disposition",
        "world_root",
        "private_case",
        "private_case_receipt",
        "private_case_reveal",
        "private_truth",
        "private_truth_sha256",
        "private_hash",
        "manifest_sha256",
        "owner_registry",
        "owner_registry_sha256",
        "owner_topology",
        "target_registry",
        "target_registry_sha256",
        "alternative_oracle",
        "feasible_alternatives",
        "crash_schedule",
        "fault_schedule",
        "will_migrate",
        "drop_ack",
        "effect_occurred",
        "authority_stratum",
    }
)

_SPAWN_LOCK = threading.RLock()


class VisibilityViolation(ValueError):
    """Raised when private or unknown information could reach an arm."""


def canonical_bytes(value: Any) -> bytes:
    """Return the canonical JSON bytes used by receipts and leak scans."""

    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise VisibilityViolation(f"value is not canonical-JSON-safe: {exc}") from exc


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _material_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return canonical_bytes(value)


def _forbidden_needles(private_materials: Sequence[Any]) -> tuple[bytes, ...]:
    needles: set[bytes] = set()

    def add_raw(material: Any) -> None:
        raw = _material_bytes(material)
        if raw:
            needles.add(raw)
            needles.add(hashlib.sha256(raw).hexdigest().encode("ascii"))

    def add_material(material: Any) -> None:
        if isinstance(material, Mapping):
            add_raw(material)
            for nested in material.values():
                add_material(nested)
        elif isinstance(material, Sequence) and not isinstance(
            material, (str, bytes, bytearray)
        ):
            add_raw(material)
            for nested in material:
                add_material(nested)
        elif isinstance(material, str) and len(material.encode("utf-8")) >= 4:
            add_raw(material)
        elif isinstance(material, (bytes, bytearray)) and len(material) >= 4:
            add_raw(material)

    for material in private_materials:
        add_material(material)
    return tuple(sorted(needles))


def _assert_no_material(
    value: Any,
    private_materials: Sequence[Any],
    *,
    where: str,
) -> None:
    raw = canonical_bytes(value)
    for needle in _forbidden_needles(private_materials):
        if needle and needle in raw:
            raise VisibilityViolation(f"private material or candidate hash visible in {where}")


def _assert_exact_keys(
    value: Mapping[str, Any],
    expected: frozenset[str],
    *,
    where: str,
) -> None:
    actual = set(value)
    unknown = actual - expected
    missing = expected - actual
    if unknown:
        raise VisibilityViolation(f"unknown fields in {where}: {sorted(unknown)}")
    if missing:
        raise VisibilityViolation(f"missing fields in {where}: {sorted(missing)}")
    lowered = {key.lower() for key in actual}
    private = lowered & _PRIVATE_FIELD_NAMES
    if private:
        raise VisibilityViolation(f"private fields in {where}: {sorted(private)}")


def _assert_public_string(value: Any, *, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise VisibilityViolation(f"{where} must be a non-empty string")
    if _SEMANTIC_CASE_PATTERN.search(value):
        raise VisibilityViolation(f"semantic case value in {where}")
    return value


def _assert_number(value: Any, *, where: str, minimum: float) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise VisibilityViolation(f"{where} must be a number")
    if value < minimum:
        raise VisibilityViolation(f"{where} must be >= {minimum}")
    return value


def _validate_public_input(public_input: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(public_input, Mapping):
        raise VisibilityViolation("public input must be an object")
    _assert_exact_keys(public_input, PUBLIC_INPUT_FIELDS, where="public input")
    if public_input["schema"] != PUBLIC_INPUT_SCHEMA:
        raise VisibilityViolation(f"public input schema must be {PUBLIC_INPUT_SCHEMA}")
    task = public_input["task"]
    if not isinstance(task, Mapping):
        raise VisibilityViolation("public input task must be an object")
    _assert_exact_keys(task, PUBLIC_TASK_FIELDS, where="public input task")
    result = {
        "q_version": _assert_public_string(task["q_version"], where="task.q_version"),
        "object_id": _assert_public_string(task["object_id"], where="task.object_id"),
        "target_id": _assert_public_string(task["target_id"], where="task.target_id"),
        "deadline_minute": _assert_number(
            task["deadline_minute"], where="task.deadline_minute", minimum=1
        ),
        "required_duration_minutes": _assert_number(
            task["required_duration_minutes"],
            where="task.required_duration_minutes",
            minimum=1,
        ),
        "required_power_kw": _assert_number(
            task["required_power_kw"], where="task.required_power_kw", minimum=0.001
        ),
        "power_tolerance_percent": _assert_number(
            task["power_tolerance_percent"],
            where="task.power_tolerance_percent",
            minimum=0,
        ),
    }
    if result["required_duration_minutes"] > result["deadline_minute"]:
        raise VisibilityViolation("required duration exceeds deadline")
    return result


def validate_arm_view(view: Mapping[str, Any]) -> dict[str, Any]:
    """Validate an already-built arm view with no access to private state."""

    if not isinstance(view, Mapping):
        raise VisibilityViolation("arm view must be an object")
    _assert_exact_keys(view, ARM_VIEW_FIELDS, where="arm view")
    if view["schema"] != ARM_VIEW_SCHEMA:
        raise VisibilityViolation(f"arm view schema must be {ARM_VIEW_SCHEMA}")
    arm_id = _assert_public_string(view["arm_id"], where="arm_view.arm_id")
    if not _ARM_ID_PATTERN.fullmatch(arm_id):
        raise VisibilityViolation("arm_view.arm_id is not a public method identifier")
    for field, pattern in _OPAQUE_PATTERNS.items():
        value = _assert_public_string(view[field], where=f"arm_view.{field}")
        if not pattern.fullmatch(value):
            raise VisibilityViolation(f"arm_view.{field} is not independently opaque")
    _assert_public_string(view["q_version"], where="arm_view.q_version")
    _assert_public_string(view["object_id"], where="arm_view.object_id")
    _assert_public_string(view["target_id"], where="arm_view.target_id")
    _assert_number(view["deadline_minute"], where="arm_view.deadline_minute", minimum=1)
    _assert_number(
        view["required_duration_minutes"],
        where="arm_view.required_duration_minutes",
        minimum=1,
    )
    _assert_number(
        view["required_power_kw"], where="arm_view.required_power_kw", minimum=0.001
    )
    _assert_number(
        view["power_tolerance_percent"],
        where="arm_view.power_tolerance_percent",
        minimum=0,
    )
    if view["required_duration_minutes"] > view["deadline_minute"]:
        raise VisibilityViolation("arm view duration exceeds deadline")
    surface = view["broker_surface"]
    if not isinstance(surface, Mapping):
        raise VisibilityViolation("broker_surface must be an object")
    _assert_exact_keys(surface, BROKER_SURFACE_FIELDS, where="broker surface")
    endpoint_handle = surface["endpoint_handle"]
    if (
        not isinstance(endpoint_handle, str)
        or not re.fullmatch(r"[0-9a-f]{32}", endpoint_handle)
    ):
        raise VisibilityViolation(
            "broker_surface.endpoint_handle must be 32 lowercase hex characters"
        )
    if surface["surface_version"] != 1:
        raise VisibilityViolation("broker_surface.surface_version must be 1")
    capabilities = surface["capabilities"]
    if not isinstance(capabilities, list) or not capabilities:
        raise VisibilityViolation("broker surface capabilities must be a non-empty list")
    if capabilities != sorted(set(capabilities)):
        raise VisibilityViolation("broker surface capabilities must be sorted and unique")
    for capability in capabilities:
        if (
            not isinstance(capability, str)
            or not _CAPABILITY_PATTERN.fullmatch(capability)
            or _SEMANTIC_CASE_PATTERN.search(capability)
        ):
            raise VisibilityViolation("invalid broker capability")
    return copy.deepcopy(dict(view))


class ArmViewFactory:
    """Construct an arm view from an exact public-input allowlist."""

    def __init__(
        self,
        *,
        arm_id: str,
        broker_capabilities: Sequence[str] = DEFAULT_BROKER_CAPABILITIES,
    ) -> None:
        self._arm_id = _assert_public_string(arm_id, where="factory.arm_id")
        if not _ARM_ID_PATTERN.fullmatch(self._arm_id):
            raise VisibilityViolation("factory.arm_id is not a public method identifier")
        capabilities = sorted(set(broker_capabilities))
        if not capabilities:
            raise VisibilityViolation("factory broker capabilities cannot be empty")
        for capability in capabilities:
            if (
                not isinstance(capability, str)
                or not _CAPABILITY_PATTERN.fullmatch(capability)
                or _SEMANTIC_CASE_PATTERN.search(capability)
            ):
                raise VisibilityViolation("invalid factory broker capability")
        self._broker_capabilities = tuple(capabilities)

    def build(
        self,
        public_input: Mapping[str, Any],
        *,
        broker_surface: Mapping[str, Any] | None = None,
        private_materials: Sequence[Any] = (),
    ) -> dict[str, Any]:
        """Build a fresh view; unknown or private input fails closed."""

        task = _validate_public_input(public_input)
        _assert_no_material(public_input, private_materials, where="public input")
        selected_broker_surface = (
            {
                "endpoint_handle": secrets.token_hex(16),
                "capabilities": list(self._broker_capabilities),
                "surface_version": 1,
            }
            if broker_surface is None
            else copy.deepcopy(dict(broker_surface))
        )
        view: dict[str, Any] = {
            "schema": ARM_VIEW_SCHEMA,
            "arm_id": self._arm_id,
            "public_run_id": f"run-{secrets.token_hex(16)}",
            "episode_instance_id": f"episode-{secrets.token_hex(16)}",
            "arm_binding_token": f"arm-bind-{secrets.token_hex(32)}",
            "q_version": task["q_version"],
            "object_id": task["object_id"],
            "target_id": task["target_id"],
            "operation_id": f"operation-{secrets.token_hex(16)}",
            "deadline_minute": task["deadline_minute"],
            "required_duration_minutes": task["required_duration_minutes"],
            "required_power_kw": task["required_power_kw"],
            "power_tolerance_percent": task["power_tolerance_percent"],
            "broker_surface": selected_broker_surface,
        }
        validated = validate_arm_view(view)
        if validated["broker_surface"]["capabilities"] != list(
            self._broker_capabilities
        ):
            raise VisibilityViolation(
                "broker surface capabilities differ from the factory contract"
            )
        _assert_no_material(validated, private_materials, where="arm view")
        return validated

    @staticmethod
    def pair_projection(view: Mapping[str, Any]) -> dict[str, Any]:
        """Return the α-normal form used for paired-world visibility checks."""

        normalized = validate_arm_view(view)
        replacements = {
            "public_run_id": "run-" + ("0" * 32),
            "episode_instance_id": "episode-" + ("0" * 32),
            "arm_binding_token": "arm-bind-" + ("0" * 64),
            "operation_id": "operation-" + ("0" * 32),
        }
        normalized.update(replacements)
        normalized["broker_surface"]["endpoint_handle"] = "0" * 32
        return normalized

    @classmethod
    def assert_pair_compatible(
        cls,
        left: Mapping[str, Any],
        right: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Fail unless two views differ only by registered opaque identifiers."""

        left_valid = validate_arm_view(left)
        right_valid = validate_arm_view(right)
        left_raw = canonical_bytes(left_valid)
        right_raw = canonical_bytes(right_valid)
        left_projection = cls.pair_projection(left_valid)
        right_projection = cls.pair_projection(right_valid)
        if left_projection != right_projection:
            raise VisibilityViolation("paired views differ outside opaque identifiers")
        if len(left_raw) != len(right_raw):
            raise VisibilityViolation("paired views expose a canonical-length difference")
        return {
            "status": "PAIR_COMPATIBLE",
            "raw_length": len(left_raw),
            "alpha_projection_sha256": sha256_value(left_projection),
        }


@dataclass(frozen=True)
class LaunchReceipt:
    schema: str
    status: str
    process_start_method: str
    exit_code: int
    visible_surface: dict[str, Any]
    visible_surface_sha256: str
    worker_result: Any
    private_material_absent: bool
    isolation_boundary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "process_start_method": self.process_start_method,
            "exit_code": self.exit_code,
            "visible_surface": copy.deepcopy(self.visible_surface),
            "visible_surface_sha256": self.visible_surface_sha256,
            "worker_result": copy.deepcopy(self.worker_result),
            "private_material_absent": self.private_material_absent,
            "isolation_boundary": self.isolation_boundary,
        }


def _fd_inventory() -> list[str]:
    root = pathlib.Path("/dev/fd")
    if not root.exists():
        return []
    try:
        return sorted(entry.name for entry in root.iterdir())
    except OSError:
        return []


def _surface_only_worker(view: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": "SURFACE_RECORDED",
        "view_sha256": sha256_value(view),
    }


def _blind_child_entry(
    view: Mapping[str, Any],
    child_cwd: str,
    child_argv: tuple[str, ...],
    minimal_environment: Mapping[str, str],
    worker: Callable[[Mapping[str, Any]], Any],
    result_queue: Any,
) -> None:
    """Install the child boundary, record it, then call the public worker."""

    sys.argv[:] = list(child_argv)
    os.chdir(child_cwd)
    os.environ.clear()
    os.environ.update(dict(minimal_environment))
    validated_view = validate_arm_view(view)
    visible_surface = {
        "view": validated_view,
        "view_bytes": canonical_bytes(validated_view).decode("utf-8"),
        "argv": list(sys.argv),
        "cwd": os.getcwd(),
        "cwd_entries": sorted(path.name for path in pathlib.Path.cwd().iterdir()),
        "process_name": multiprocessing.current_process().name,
        "environment": dict(sorted(os.environ.items())),
        "inherited_file_descriptors": _fd_inventory(),
    }
    try:
        worker_result = worker(copy.deepcopy(validated_view))
    except BaseException as exc:  # fail closed without returning exception text
        result_queue.put(
            {
                "status": "WORKER_ERROR",
                "error_type": type(exc).__name__,
                "visible_surface": visible_surface,
            }
        )
        raise
    result_queue.put(
        {
            "status": "CHILD_OK",
            "visible_surface": visible_surface,
            "worker_result": worker_result,
        }
    )


class BlindProcessLauncher:
    """Launch a real spawn child with a fixed, recorded public surface."""

    def __init__(
        self,
        *,
        minimal_environment: Mapping[str, str] | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        environment = dict(
            minimal_environment
            or {
                "LANG": "C.UTF-8",
                "PATH": "/usr/bin:/bin",
                "PYTHONHASHSEED": "0",
            }
        )
        if not environment or any(
            not isinstance(key, str)
            or not key
            or not isinstance(value, str)
            for key, value in environment.items()
        ):
            raise VisibilityViolation("minimal environment must contain string pairs")
        self._minimal_environment = environment
        self._timeout_seconds = timeout_seconds

    def launch(
        self,
        view: Mapping[str, Any],
        *,
        private_materials: Sequence[Any] = (),
        worker: Callable[[Mapping[str, Any]], Any] = _surface_only_worker,
    ) -> LaunchReceipt:
        validated_view = validate_arm_view(view)
        _assert_no_material(validated_view, private_materials, where="launcher arm view")
        if not callable(worker):
            raise VisibilityViolation("worker must be callable")

        context = multiprocessing.get_context("spawn")
        result_queue = context.Queue()
        child_name = f"arm-worker-{secrets.token_hex(8)}"
        child_argv = ("wave015-blind-child", "--opaque")

        with tempfile.TemporaryDirectory(prefix="wave015-arm-") as child_cwd:
            process = context.Process(
                target=_blind_child_entry,
                name=child_name,
                args=(
                    validated_view,
                    child_cwd,
                    child_argv,
                    self._minimal_environment,
                    worker,
                    result_queue,
                ),
            )
            # multiprocessing spawn snapshots argv/cwd/env before the target
            # function starts.  Serialise this cooperative transition so the
            # child import path cannot inherit a semantic caller surface.
            with _SPAWN_LOCK:
                parent_argv = list(sys.argv)
                parent_cwd = os.getcwd()
                parent_environment = dict(os.environ)
                sys.argv[:] = list(child_argv)
                os.chdir(child_cwd)
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
                child_result = result_queue.get(timeout=self._timeout_seconds)
            except Exception:
                process.terminate()
                process.join(timeout=5)
                raise VisibilityViolation("blind child did not return a visibility receipt")
            process.join(timeout=self._timeout_seconds)
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                raise VisibilityViolation("blind child exceeded timeout")
            if process.exitcode != 0 or child_result.get("status") != "CHILD_OK":
                raise VisibilityViolation(
                    f"blind child failed closed with exit code {process.exitcode}"
                )

            visible_surface = child_result["visible_surface"]
            _assert_no_material(
                visible_surface,
                private_materials,
                where="child visible surface",
            )
            if visible_surface["argv"] != list(child_argv):
                raise VisibilityViolation("child argv was not sanitized")
            if pathlib.Path(visible_surface["cwd"]).resolve() != pathlib.Path(child_cwd).resolve():
                raise VisibilityViolation("child cwd was not sanitized")
            if visible_surface["process_name"] != child_name:
                raise VisibilityViolation("child process name was not sanitized")
            if visible_surface["environment"] != dict(sorted(self._minimal_environment.items())):
                raise VisibilityViolation("child environment was not sanitized")
            if visible_surface["cwd_entries"]:
                raise VisibilityViolation("child cwd was not empty")

            receipt = LaunchReceipt(
                schema=LAUNCH_RECEIPT_SCHEMA,
                status="CHILD_VISIBLE_SURFACE_RECORDED",
                process_start_method="spawn",
                exit_code=process.exitcode,
                visible_surface=visible_surface,
                visible_surface_sha256=sha256_value(visible_surface),
                worker_result=copy.deepcopy(child_result["worker_result"]),
                private_material_absent=True,
                isolation_boundary=(
                    "COOPERATIVE_SPAWN_VISIBILITY_BOUNDARY; "
                    "HOSTILE_SAME_OS_USER_AND_UNRELATED_CONCURRENT_SPAWN_NOT_COVERED"
                ),
            )
            return receipt
