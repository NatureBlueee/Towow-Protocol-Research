#!/usr/bin/env python3
"""Wave 025 host-side prefix qualification runner.

This program creates evidence; it never classifies leakage and never emits a
qualification verdict.  The batch root is host-only and is never mounted into
a candidate container.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_INPUT = "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"
SCHEMA_FEATURES = "WAVE025_LEAK_ONLY_FEATURES_V1"
SCHEMA_PRECOMMIT = "WAVE025_BATCH_PRECOMMIT_V1_4"
SCHEMA_PUBLIC_PLAN = "WAVE025_PUBLIC_PLAN_V1"
SCHEMA_PRIVATE_STATE = "WAVE025_RUNNER_PRIVATE_STATE_V1"
SCHEMA_ANCHOR = "WAVE025_ANCHOR_RECEIPT_V1"
SCHEMA_HOST_LAUNCH = "WAVE025_HOST_LAUNCH_V1"
SCHEMA_SLOT_RECEIPT = "WAVE025_SLOT_RECEIPT_V1"
SCHEMA_CLOSED = "WAVE025_BATCH_CLOSED_V1"
SCHEMA_REVEAL = "WAVE025_BATCH_REVEAL_V1"
SCHEMA_COMMAND = "WAVE025_HOST_COMMAND_RECEIPT_V1"
SCHEMA_FROZEN_INPUT_REGISTRY = "WAVE025_FROZEN_INPUT_REGISTRY_V1_4"
SCHEMA_PRIVATE_CONTROL_REGISTRY = "WAVE025_PRIVATE_CONTROL_REGISTRY_V1"
SCHEMA_PRIVATE_CONTROL_REGISTRY_COMMITMENT = (
    "WAVE025_PRIVATE_CONTROL_REGISTRY_COMMITMENT_V1"
)
SCHEMA_D0_PRIVATE_PROVENANCE = "WAVE025_D0_PRIVATE_PREDECESSOR_PROVENANCE_V1"
SCHEMA_D0_PRIVATE_PROVENANCE_COMMITMENT = (
    "WAVE025_D0_PRIVATE_PREDECESSOR_PROVENANCE_COMMITMENT_V1"
)

FROZEN_INPUT_SPECS = (
    {
        "name": "feature_spec",
        "argument": "feature_spec_path",
        "filename": "feature-spec.json",
        "schema": "WAVE025_FEATURE_CLASSIFIER_SPEC_V1",
    },
    {
        "name": "executable_attack_profile",
        "argument": "executable_attack_profile_path",
        "filename": "executable-attack-profile.json",
        "schema": "WAVE025_EXECUTABLE_ATTACK_PROFILE_FULL_V1",
    },
    {
        "name": "shared_evidence_profile",
        "argument": "shared_evidence_profile_path",
        "filename": "shared-evidence-profile.json",
        "schema": "WAVE025_SHARED_EVIDENCE_PROFILE_CANDIDATE_V1",
    },
    {
        "name": "control_family_registration",
        "argument": "control_family_registration_path",
        "filename": "control-family-registration.json",
        "schema": "WAVE025_PUBLIC_CONTROL_FAMILY_REGISTRATION_V1",
    },
    {
        "name": "host_only_inventory",
        "argument": "host_only_inventory_path",
        "filename": "host-only-inventory.json",
        "schema": "WAVE025_HOST_ONLY_INVENTORY_V1",
    },
    {
        "name": "independent_evaluator_source_manifest",
        "argument": "independent_evaluator_source_manifest_path",
        "filename": "independent-evaluator-source-manifest.json",
        "schema": "WAVE025_INDEPENDENT_EVALUATOR_SOURCE_MANIFEST_V1",
    },
)

CHALLENGES = ["D0-HOST-LEAK", "D1-OCI-CANARY", "T-OCI-ISOLATED"]
DOMAINS = ["PRIVATE_ASSIGNMENT_ORDER", "PUBLIC_ID", "MEASUREMENT_PADDING"]
HEX_256 = re.compile(r"^[0-9a-f]{64}$")
BATCH_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$")
OPAQUE_ID = re.compile(r"^s_[0-9a-f]{32}$")
D0_MARKER_BASENAME = re.compile(r"^d0-residue-v1-[0-9a-f]{32}$")
D1_CANARY_TOKEN = re.compile(r"^WAVE025_CANARY_D1_CURRENT_[0-9a-f]{24}$")
CONTROL_CHALLENGES = ("D0-HOST-LEAK", "D1-OCI-CANARY")

HERE = Path(__file__).resolve().parent
WAVE_ROOT = HERE.parent
QUESTION = WAVE_ROOT / "QUESTION.md"
QUALIFICATION_CONTRACT = WAVE_ROOT / "QUALIFICATION-CONTRACT.md"
BATCH_CONTRACT = WAVE_ROOT / "BATCH-EVIDENCE-CONTRACT.md"
COLLECTOR_ROOT = WAVE_ROOT / "attackers" / "leak-only-collector"
COLLECTOR_SOURCE = COLLECTOR_ROOT / "collector.js"
COLLECTOR_DOCKERFILE = COLLECTOR_ROOT / "Dockerfile"

PUBLIC_PACKET = canonical_packet = {"schema": SCHEMA_INPUT}
PUBLIC_PACKET_BYTES = b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n'
FIXED_INPUT_BYTES = bytes(32)
SUPERVISOR_READY_FRAME = b"WAVE025_SUPERVISOR_READY_V1\n"
SUPERVISOR_SCRIPT = """collector_rc=0
node /app/collector.js > /out/collector-stdout 2> /out/collector-stderr || collector_rc=$?
printf '%s\\n' "$collector_rc" > /out/collector-exit-code
printf 'READY\\n' > /out/collector-ready
printf 'WAVE025_SUPERVISOR_READY_V1\\n'
trap 'exit "$collector_rc"' TERM INT
while :; do sleep 1; done
"""
SUPERVISOR_SCRIPT_SHA256 = hashlib.sha256(SUPERVISOR_SCRIPT.encode("utf-8")).hexdigest()
EXTRACTION_READS = [
    {
        "ordinal": 1,
        "out_path": "/out/collector-ready",
        "evidence_file": "collector-ready.bin",
    },
    {
        "ordinal": 2,
        "out_path": "/out/collector-exit-code",
        "evidence_file": "collector-exit-code.bin",
    },
    {
        "ordinal": 3,
        "out_path": "/out/collector-stdout",
        "evidence_file": "collector-stdout.bin",
    },
    {
        "ordinal": 4,
        "out_path": "/out/collector-stderr",
        "evidence_file": "collector-stderr.bin",
    },
    {
        "ordinal": 5,
        "out_path": "/out/leak-features.json",
        "evidence_file": "collector-out.bin",
    },
]
EVIDENCE_EXTRACTION_PROFILE = {
    "schema": "WAVE025_POST_OBSERVATION_EXTRACTION_PROFILE_V1",
    "ready_frame_utf8": SUPERVISOR_READY_FRAME.decode("ascii"),
    "ready_frame_sha256": hashlib.sha256(SUPERVISOR_READY_FRAME).hexdigest(),
    "pre_ready_host_observers": ["docker logs", "docker inspect"],
    "exec_command_template": [
        "docker",
        "exec",
        "--user",
        "65534:65534",
        "<exact-container-name>",
        "/bin/cat",
        "<exact-allowlisted-out-path>",
    ],
    "exec_user": "65534:65534",
    "exec_binary": "/bin/cat",
    "ordered_reads": EXTRACTION_READS,
    "termination_command_template": [
        "docker",
        "kill",
        "--signal",
        "TERM",
        "<exact-container-name>",
    ],
    "daemon_event_profile": {
        "filter_identity": "exact-container-id",
        "capture_window": "container-created-through-post-inspect-host-time-plus-250ms",
        "until_format": "UTC-RFC3339-microseconds",
        "required_lifecycle_actions": ["create", "start", "kill", "die"],
        "required_exec_actions_per_read": ["exec_create", "exec_start", "exec_die"],
        "extra_exec_policy": "fail-closed",
        "trust_boundary": "trusted-docker-daemon-event-history",
    },
    "threat_boundary": (
        "post-cut read-only extraction trusts host, Docker daemon, kernel, and frozen image /bin/cat; "
        "daemon events detect ordinary pipeline drift but cannot prove a malicious daemon did not hide behavior"
    ),
}


class RunnerError(RuntimeError):
    """Fail-closed runner error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonicalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not (value == value and abs(value) != float("inf")):
            raise RunnerError("canonical JSON rejects non-finite float")
        return value
    if isinstance(value, list):
        return [canonicalize(item) for item in value]
    if isinstance(value, dict):
        if not all(isinstance(key, str) for key in value):
            raise RunnerError("canonical JSON object keys must be strings")
        return {key: canonicalize(value[key]) for key in sorted(value)}
    raise RunnerError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(canonicalize(value), ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RunnerError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json_bytes(raw: bytes, source: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerError(f"invalid JSON in {source}: {error}") from error


def read_json(path: Path, expected_schema: str | None = None) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    value = parse_json_bytes(raw, str(path))
    if canonical_bytes(value) != raw:
        raise RunnerError(f"JSON is not canonical bytes: {path}")
    if expected_schema is not None:
        if not isinstance(value, dict) or value.get("schema") != expected_schema:
            raise RunnerError(f"wrong schema in {path}; expected {expected_schema}")
    return value, raw


def ensure_sha256(value: str, label: str) -> str:
    normalized = value.lower()
    if not HEX_256.fullmatch(normalized):
        raise RunnerError(f"{label} must be a lowercase SHA-256 hex digest")
    return normalized


def exclusive_write(path: Path, raw: bytes, mode: int = 0o644) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, mode)
    try:
        offset = 0
        while offset < len(raw):
            offset += os.write(descriptor, raw[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def exclusive_json(path: Path, value: Any, mode: int = 0o644) -> bytes:
    raw = canonical_bytes(value)
    exclusive_write(path, raw, mode)
    return raw


def mkdir_exclusive(path: Path, mode: int = 0o755) -> None:
    os.mkdir(path, mode)


def assert_regular_file(path: Path, mode: int | None = None) -> None:
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or path.is_symlink():
        raise RunnerError(f"expected regular non-symlink file: {path}")
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise RunnerError(
            f"wrong mode for {path}: {oct(stat.S_IMODE(info.st_mode))}, expected {oct(mode)}"
        )


def load_frozen_input_sources(args: argparse.Namespace) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    resolved_paths: set[Path] = set()
    for spec in FROZEN_INPUT_SPECS:
        raw_argument = getattr(args, spec["argument"], None)
        if not isinstance(raw_argument, str) or not raw_argument:
            raise RunnerError(f"missing exact JSON path --{spec['argument'].replace('_', '-')}")
        source_path = Path(raw_argument).expanduser().absolute()
        assert_regular_file(source_path)
        resolved = source_path.resolve(strict=True)
        if resolved in resolved_paths:
            raise RunnerError(f"duplicate frozen input source path: {resolved}")
        resolved_paths.add(resolved)
        value, raw = read_json(source_path, spec["schema"])
        if not isinstance(value, dict) or set(value).isdisjoint({"schema"}):
            raise RunnerError(f"frozen input must be a JSON object with schema: {source_path}")
        sources.append(
            {
                "spec": spec,
                "source_path": source_path,
                "value": value,
                "raw": raw,
                "entry": {
                    "name": spec["name"],
                    "relative_path": f"frozen-inputs/{spec['filename']}",
                    "schema": spec["schema"],
                    "sha256": sha256_bytes(raw),
                    "byte_length": len(raw),
                },
            }
        )
    return sources


def frozen_input_registry(sources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": SCHEMA_FROZEN_INPUT_REGISTRY,
        "directory": "frozen-inputs",
        "entries": [source["entry"] for source in sources],
    }


def freeze_input_sources(batch_root: Path, sources: list[dict[str, Any]]) -> None:
    frozen_root = batch_root / "frozen-inputs"
    mkdir_exclusive(frozen_root, 0o700)
    for source in sources:
        destination = batch_root / source["entry"]["relative_path"]
        exclusive_write(destination, source["raw"], 0o444)
    os.chmod(frozen_root, 0o500)


def validate_frozen_input_registry(
    batch_root: Path, precommit: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    registry = precommit.get("frozen_inputs")
    if not isinstance(registry, dict) or set(registry) != {"schema", "directory", "entries"}:
        raise RunnerError("precommit frozen_inputs registry has unknown or missing fields")
    if registry["schema"] != SCHEMA_FROZEN_INPUT_REGISTRY:
        raise RunnerError("precommit frozen_inputs registry has wrong schema")
    if registry["directory"] != "frozen-inputs":
        raise RunnerError("precommit frozen_inputs registry has wrong directory")
    entries = registry["entries"]
    if not isinstance(entries, list) or len(entries) != len(FROZEN_INPUT_SPECS):
        raise RunnerError("precommit frozen_inputs registry has unknown or missing inputs")
    expected_names = [spec["name"] for spec in FROZEN_INPUT_SPECS]
    names = [entry.get("name") if isinstance(entry, dict) else None for entry in entries]
    if names != expected_names or len(names) != len(set(names)):
        raise RunnerError("precommit frozen_inputs registry has unknown, duplicate, or reordered inputs")
    frozen_root = batch_root / "frozen-inputs"
    if not frozen_root.is_dir() or frozen_root.is_symlink():
        raise RunnerError("frozen-inputs is not a real directory")
    if stat.S_IMODE(frozen_root.stat().st_mode) != 0o500:
        raise RunnerError("frozen-inputs directory mode changed after precommit")
    expected_files = {spec["filename"] for spec in FROZEN_INPUT_SPECS}
    actual_files = {path.name for path in frozen_root.iterdir()}
    if actual_files != expected_files:
        raise RunnerError("frozen-inputs contains unknown, missing, or duplicate entries")
    by_name: dict[str, dict[str, Any]] = {}
    validated: dict[str, dict[str, Any]] = {}
    exact_entry_fields = {"name", "relative_path", "schema", "sha256", "byte_length"}
    for spec, entry in zip(FROZEN_INPUT_SPECS, entries):
        if not isinstance(entry, dict) or set(entry) != exact_entry_fields:
            raise RunnerError(f"frozen input entry {spec['name']} has unknown or missing fields")
        if entry["name"] != spec["name"]:
            raise RunnerError("frozen input name mismatch")
        expected_relative = f"frozen-inputs/{spec['filename']}"
        if entry["relative_path"] != expected_relative:
            raise RunnerError(f"frozen input path mismatch for {spec['name']}")
        if entry["schema"] != spec["schema"]:
            raise RunnerError(f"frozen input schema mismatch for {spec['name']}")
        ensure_sha256(entry["sha256"], f"frozen input {spec['name']} digest")
        if not isinstance(entry["byte_length"], int) or entry["byte_length"] <= 0:
            raise RunnerError(f"frozen input {spec['name']} byte length is invalid")
        path = batch_root / expected_relative
        assert_regular_file(path, 0o444)
        value, raw = read_json(path, spec["schema"])
        if len(raw) != entry["byte_length"] or sha256_bytes(raw) != entry["sha256"]:
            raise RunnerError(f"frozen input bytes changed after precommit: {spec['name']}")
        by_name[spec["name"]] = entry
        validated[spec["name"]] = {"value": value, "raw": raw, "entry": entry}
    if precommit.get("feature_spec_sha256") != by_name["feature_spec"]["sha256"]:
        raise RunnerError("feature_spec_sha256 does not bind frozen feature spec bytes")
    if precommit.get("evaluator_source_manifest_sha256") != by_name[
        "independent_evaluator_source_manifest"
    ]["sha256"]:
        raise RunnerError("evaluator_source_manifest_sha256 does not bind frozen manifest bytes")
    return validated


def load_private_control_registry(
    args: argparse.Namespace, frozen_sources: list[dict[str, Any]]
) -> tuple[dict[str, Any], bytes]:
    raw_argument = getattr(args, "private_control_registry_path", None)
    if not isinstance(raw_argument, str) or not raw_argument:
        raise RunnerError("missing exact JSON path --private-control-registry-path")
    path = Path(raw_argument).expanduser().absolute()
    assert_regular_file(path, 0o600)
    resolved = path.resolve(strict=True)
    if resolved in {source["source_path"].resolve(strict=True) for source in frozen_sources}:
        raise RunnerError("private control registry duplicates a public frozen input path")
    value, raw = read_json(path, SCHEMA_PRIVATE_CONTROL_REGISTRY)
    if not isinstance(value, dict):
        raise RunnerError("private control registry must be a JSON object")
    return value, raw


def validate_control_registries(
    public_registration: Any,
    public_raw: bytes,
    private_registry: Any,
    mode: str,
    sample_plan: dict[str, Any],
    feature_spec_entry: dict[str, Any],
    executable_profile: Any,
) -> dict[str, dict[str, str]]:
    public_fields = {
        "schema", "version", "registry_id", "status", "binding_state",
        "profile_id", "feature_spec_sha256", "private_material_included", "families",
    }
    private_fields = {
        "schema", "version", "registry_id", "status", "binding_state", "profile_id",
        "public_registration_sha256", "generated_at", "role_labels",
        "material_provenance", "families", "per_family_canonical_sha256",
    }
    public_family_fields = {
        "family_id", "challenge", "injection_surface",
        "expected_collector_feature_family", "primary_detector_id_from_C01_TO_C05",
        "calibration_population_by_role", "holdout_population_by_role",
    }
    private_family_fields = {
        "family_id", "challenge", "private_value_kind", "mapping_stability",
        "role_mappings",
    }
    if not isinstance(public_registration, dict) or set(public_registration) != public_fields:
        raise RunnerError("public control family registration has unknown or missing fields")
    if public_registration["schema"] != "WAVE025_PUBLIC_CONTROL_FAMILY_REGISTRATION_V1":
        raise RunnerError("public control family registration schema mismatch")
    if public_registration["version"] != "1.0.0":
        raise RunnerError("public control family registration version mismatch")
    if public_registration["registry_id"] != "WAVE025-PUBLIC-CONTROL-FAMILIES-PREFORMAL-V1":
        raise RunnerError("public control family registration id mismatch")
    if public_registration["status"] != "PREFORMAL_CANDIDATE_NOT_BOUND":
        raise RunnerError("public control family registration status mismatch")
    if public_registration["binding_state"] != "NOT_BOUND_TO_PROFILE_OR_PRECOMMIT":
        raise RunnerError("public control family registration binding state mismatch")
    if public_registration["private_material_included"] is not False:
        raise RunnerError("public control registration contains private material")
    if public_registration["feature_spec_sha256"] != feature_spec_entry["sha256"]:
        raise RunnerError("public control registration does not bind frozen feature spec bytes")
    if not isinstance(private_registry, dict) or set(private_registry) != private_fields:
        raise RunnerError("private control registry has unknown or missing fields")
    if private_registry["schema"] != SCHEMA_PRIVATE_CONTROL_REGISTRY:
        raise RunnerError("private control registry schema mismatch")
    if private_registry["version"] != "1.0.0":
        raise RunnerError("private control registry version mismatch")
    if private_registry["registry_id"] != "WAVE025-PRIVATE-CONTROL-REGISTRY-PREFORMAL-V1":
        raise RunnerError("private control registry id mismatch")
    try:
        rfc3339_epoch_ns(private_registry["generated_at"], "private registry generated_at")
    except (KeyError, TypeError):
        raise RunnerError("private control registry generated_at mismatch") from None
    if private_registry["public_registration_sha256"] != sha256_bytes(public_raw):
        raise RunnerError("private registry public_registration_sha256 mismatch")
    profile_id = public_registration["profile_id"]
    if profile_id != "WAVE025-EXECUTABLE-ATTACK-PROFILE-FULL-V1":
        raise RunnerError("public control registration profile_id is invalid")
    if private_registry["profile_id"] != profile_id:
        raise RunnerError("private/public control profile_id mismatch")
    if not isinstance(executable_profile, dict) or executable_profile.get("profile_id") != profile_id:
        raise RunnerError("frozen executable profile_id does not match control registries")
    feature_binding = executable_profile.get("feature_spec_binding")
    if not isinstance(feature_binding, dict):
        raise RunnerError("frozen executable profile lacks feature_spec_binding")
    if feature_binding.get("raw_bytes_sha256") != feature_spec_entry["sha256"]:
        raise RunnerError("frozen executable profile feature hash mismatch")
    if feature_binding.get("raw_byte_length") != feature_spec_entry["byte_length"]:
        raise RunnerError("frozen executable profile feature byte length mismatch")
    if feature_binding.get("expected_schema") != feature_spec_entry["schema"]:
        raise RunnerError("frozen executable profile feature schema mismatch")
    if private_registry["role_labels"] != ["R", "S"]:
        raise RunnerError("private control registry role_labels must be exactly R,S")

    public_families = public_registration["families"]
    private_families = private_registry["families"]
    if not isinstance(public_families, list) or not isinstance(private_families, list):
        raise RunnerError("control registry families must be arrays")
    if len(public_families) != 2 or len(private_families) != 2:
        raise RunnerError("control registries must contain exactly D0 and D1 families")
    if [family.get("challenge") if isinstance(family, dict) else None for family in public_families] != list(CONTROL_CHALLENGES):
        raise RunnerError("public control families must be ordered D0 then D1")
    if [family.get("challenge") if isinstance(family, dict) else None for family in private_families] != list(CONTROL_CHALLENGES):
        raise RunnerError("private control families must be ordered D0 then D1")
    public_by_challenge: dict[str, dict[str, Any]] = {}
    private_by_challenge: dict[str, dict[str, Any]] = {}
    for family in public_families:
        if not isinstance(family, dict) or set(family) != public_family_fields:
            raise RunnerError("public control family has unknown or missing fields")
        challenge = family["challenge"]
        if challenge not in CONTROL_CHALLENGES or challenge in public_by_challenge:
            raise RunnerError("public control family challenge is unknown or duplicate")
        if family["primary_detector_id_from_C01_TO_C05"] != "C01_EXACT_CATEGORICAL_SCAN":
            raise RunnerError("public control family primary detector mismatch")
        public_by_challenge[challenge] = family
    for family in private_families:
        if not isinstance(family, dict) or set(family) != private_family_fields:
            raise RunnerError("private control family has unknown or missing fields")
        challenge = family["challenge"]
        if challenge not in CONTROL_CHALLENGES or challenge in private_by_challenge:
            raise RunnerError("private control family challenge is unknown or duplicate")
        private_by_challenge[challenge] = family
    if set(public_by_challenge) != set(CONTROL_CHALLENGES):
        raise RunnerError("public control family challenges are incomplete")
    if set(private_by_challenge) != set(CONTROL_CHALLENGES):
        raise RunnerError("private control family challenges are incomplete")

    expected_public_family = {
        "D0-HOST-LEAK": {
            "family_id": "D0_RESIDUE_OPAQUE_BASENAME_V1",
            "injection_surface": "SACRIFICIAL_PREDECESSOR_CREATED_EXACT_BASENAME_IN_READONLY_SHARED_RESIDUE_CWD",
            "expected_collector_feature_family": "F04_DIRECTORY_AND_SHARED_STATE",
        },
        "D1-OCI-CANARY": {
            "family_id": "D1_CURRENT_RUN_CANARY_V1",
            "injection_surface": "CURRENT_RUN_ROLE_CORRELATED_CANARY_IN_CHALLENGE_ENTRY_NAME_AND_FILE_CONTENT",
            "expected_collector_feature_family": "F07_VISIBLE_CANARY",
        },
    }
    for challenge, expected_fields in expected_public_family.items():
        if any(public_by_challenge[challenge].get(key) != expected for key, expected in expected_fields.items()):
            raise RunnerError(f"public control family canonical fields mismatch for {challenge}")

    instances: dict[str, dict[str, str]] = {}
    family_ids: set[str] = set()
    for challenge in CONTROL_CHALLENGES:
        public_family = public_by_challenge[challenge]
        private_family = private_by_challenge[challenge]
        if private_family["family_id"] != public_family["family_id"]:
            raise RunnerError(f"private/public control family mismatch for {challenge}")
        family_id = public_family["family_id"]
        if not isinstance(family_id, str) or not family_id or family_id in family_ids:
            raise RunnerError("control family_id is invalid or duplicate")
        family_ids.add(family_id)
        for phase, field in (
            ("calibration", "calibration_population_by_role"),
            ("holdout", "holdout_population_by_role"),
        ):
            population = public_family[field]
            if population != 50:
                raise RunnerError(f"canonical control family population must be 50 for {challenge}")
            if mode == "formal" and sample_plan[challenge][phase] != population * 2:
                raise RunnerError(f"control family population does not match batch for {challenge}")
        mappings = private_family["role_mappings"]
        if not isinstance(mappings, list) or len(mappings) != 2:
            raise RunnerError(f"control role_mappings mismatch for {challenge}")
        if [item.get("role_label") if isinstance(item, dict) else None for item in mappings] != ["R", "S"]:
            raise RunnerError(f"control role mapping labels mismatch for {challenge}")
        if private_family["mapping_stability"] != "ONE_VALUE_PER_ROLE_REUSED_ACROSS_CALIBRATION_AND_HOLDOUT":
            raise RunnerError(f"control mapping stability mismatch for {challenge}")
        role_instances: dict[str, str] = {}
        if challenge == "D0-HOST-LEAK":
            if private_family["private_value_kind"] != "TWO_DISTINCT_16_BYTE_CSPRNG_TAGS_HEX_ENCODED_IN_BASENAME":
                raise RunnerError("D0 private value kind mismatch")
            for mapping in mappings:
                if set(mapping) != {"role_label", "tag_hex", "candidate_visible_basename"}:
                    raise RunnerError("D0 role mapping has unknown or missing fields")
                basename, tag = mapping["candidate_visible_basename"], mapping["tag_hex"]
                if not isinstance(tag, str) or basename != f"d0-residue-v1-{tag}":
                    raise RunnerError("D0 tag/basename binding mismatch")
                if not D0_MARKER_BASENAME.fullmatch(basename):
                    raise RunnerError("D0 registry instances must be opaque marker basenames")
                role_instances[mapping["role_label"]] = basename
        else:
            if private_family["private_value_kind"] != "CURRENT_WAVE025_CANARY_TOKEN_UTF8":
                raise RunnerError("D1 private value kind mismatch")
            for mapping in mappings:
                if set(mapping) != {
                    "role_label", "token_utf8", "token_byte_length", "candidate_visible_sources"
                }:
                    raise RunnerError("D1 role mapping has unknown or missing fields")
                token = mapping["token_utf8"]
                if not isinstance(token, str) or not D1_CANARY_TOKEN.fullmatch(token):
                    raise RunnerError("D1 registry instances must be canary tokens")
                if mapping["token_byte_length"] != len(token.encode("utf-8")):
                    raise RunnerError("D1 token byte length mismatch")
                if mapping["candidate_visible_sources"] != [
                    "challenge-entry-name", "challenge-file-content"
                ]:
                    raise RunnerError("D1 visible sources mismatch")
                role_instances[mapping["role_label"]] = token
        if role_instances["R"] == role_instances["S"]:
            raise RunnerError(f"control role instances must be distinct for {challenge}")
        instances[challenge] = role_instances

    expected_hashes = {
        family["family_id"]: sha256_bytes(canonical_bytes(family))
        for family in private_families
    }
    if private_registry["per_family_canonical_sha256"] != expected_hashes:
        raise RunnerError("private control per-family canonical hash mismatch")
    provenance = private_registry["material_provenance"]
    if not isinstance(provenance, dict) or set(provenance) != set(CONTROL_CHALLENGES):
        raise RunnerError("private control material provenance mismatch")
    if provenance["D0-HOST-LEAK"] != {
        "kind": "OS_CSPRNG", "generator": "PYTHON_SECRETS_TOKEN_HEX_16",
        "fresh_for_this_candidate": True,
    }:
        raise RunnerError("D0 private provenance is not fresh CSPRNG material")
    d1_provenance = provenance["D1-OCI-CANARY"]
    if (
        not isinstance(d1_provenance, dict)
        or set(d1_provenance) != {
            "kind", "source_batch_id", "source_reveal_sha256", "fresh_for_formal"
        }
        or d1_provenance.get("kind") != "REUSED_FROM_ALREADY_REVEALED_SMOKE_PREFORMAL_ONLY"
        or d1_provenance.get("fresh_for_formal") is not False
        or d1_provenance.get("source_batch_id") != "w025-smoke-v13-20260801-f"
        or d1_provenance.get("source_reveal_sha256")
        != "7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287"
    ):
        raise RunnerError("D1 private provenance is not explicit preformal-only reuse")
    if private_registry["status"] != "PREFORMAL_CANDIDATE_NOT_BOUND_REUSES_REVEALED_D1":
        raise RunnerError("private control registry status is not the canonical preformal status")
    if private_registry["binding_state"] != "NOT_BOUND_TO_PROFILE_OR_PRECOMMIT":
        raise RunnerError("private control registry binding state mismatch")
    if mode == "formal":
        raise RunnerError("formal batch refuses preformal/revealed D1 control material")
    return instances


def private_control_registry_commitment(
    registry: dict[str, Any], raw: bytes
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_PRIVATE_CONTROL_REGISTRY_COMMITMENT,
        "registry_schema": SCHEMA_PRIVATE_CONTROL_REGISTRY,
        "registry_sha256": sha256_bytes(raw),
        "registry_byte_length": len(raw),
        "public_registration_sha256": registry["public_registration_sha256"],
        "profile_id": registry["profile_id"],
        "registry_id": registry["registry_id"],
        "status": registry["status"],
        "binding_state": registry["binding_state"],
        "role_labels": registry["role_labels"],
        "family_hashes": [
            {
                "family_id": family["family_id"],
                "challenge": family["challenge"],
                "sha256": registry["per_family_canonical_sha256"][family["family_id"]],
            }
            for family in registry["families"]
        ],
    }


def control_instances_from_private_registry(
    registry: dict[str, Any]
) -> dict[str, dict[str, str]]:
    return {
        family["challenge"]: {
            mapping["role_label"]: (
                mapping["candidate_visible_basename"]
                if family["challenge"] == "D0-HOST-LEAK"
                else mapping["token_utf8"]
            )
            for mapping in family["role_mappings"]
        }
        for family in registry["families"]
    }


def validate_batch_root(path: Path, must_exist: bool) -> Path:
    resolved_parent = path.expanduser().absolute().parent.resolve()
    candidate = resolved_parent / path.name
    if candidate.name in {"", ".", ".."}:
        raise RunnerError("batch directory must be an explicit child path")
    if must_exist:
        if not candidate.is_dir() or candidate.is_symlink():
            raise RunnerError(f"batch directory is not a real directory: {candidate}")
    elif candidate.exists() or candidate.is_symlink():
        raise RunnerError(f"batch directory already exists: {candidate}")
    return candidate


class HmacStream:
    def __init__(self, key: bytes, label: bytes):
        self.key = key
        self.label = label
        self.counter = 0
        self.buffer = b""

    def read(self, size: int) -> bytes:
        while len(self.buffer) < size:
            block = hmac.new(
                self.key,
                self.label + b"\x00" + self.counter.to_bytes(8, "big"),
                hashlib.sha256,
            ).digest()
            self.counter += 1
            self.buffer += block
        result, self.buffer = self.buffer[:size], self.buffer[size:]
        return result

    def randbelow(self, upper: int) -> int:
        if upper <= 0:
            raise RunnerError("randbelow upper bound must be positive")
        width = max(1, ((upper - 1).bit_length() + 7) // 8)
        ceiling = 1 << (8 * width)
        limit = ceiling - (ceiling % upper)
        while True:
            value = int.from_bytes(self.read(width), "big")
            if value < limit:
                return value % upper


def shuffled(items: Iterable[Any], seed: bytes, label: str) -> list[Any]:
    result = list(items)
    stream = HmacStream(seed, label.encode("utf-8"))
    for index in range(len(result) - 1, 0, -1):
        selected = stream.randbelow(index + 1)
        result[index], result[selected] = result[selected], result[index]
    return result


def commitment(domain: str, seed: bytes, nonce: bytes, public_plan_bytes: bytes) -> str:
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\x00"
        + seed
        + b"\x00"
        + nonce
        + b"\x00"
        + public_plan_bytes
    )


def opaque_slot_id(seed: bytes, index: int) -> str:
    payload = hmac.new(
        seed, b"W025-PUBLIC-ID-V1\x00" + index.to_bytes(8, "big"), hashlib.sha256
    ).hexdigest()
    return f"s_{payload[:32]}"


def padding_value(seed: bytes, slot_id: str) -> int:
    stream = HmacStream(seed, f"W025-PADDING-V1\x00{slot_id}".encode())
    return stream.randbelow(257)


def sample_layout(mode: str, smoke_per_split: int) -> list[dict[str, Any]]:
    if mode == "formal":
        specifications = [
            ("D0-HOST-LEAK", "calibration", 5, 20),
            ("D0-HOST-LEAK", "holdout", 5, 20),
            ("D1-OCI-CANARY", "calibration", 5, 20),
            ("D1-OCI-CANARY", "holdout", 5, 20),
            ("T-OCI-ISOLATED", "calibration", 20, 20),
            ("T-OCI-ISOLATED", "holdout", 120, 20),
        ]
    else:
        if smoke_per_split < 2 or smoke_per_split % 2:
            raise RunnerError("--smoke-per-split must be an even integer >= 2")
        specifications = [
            (challenge, phase, 1, smoke_per_split)
            for challenge in CHALLENGES
            for phase in ("calibration", "holdout")
        ]
    layout: list[dict[str, Any]] = []
    for challenge, phase, blocks, block_size in specifications:
        if block_size % 2:
            raise RunnerError("every block must have even size for strict balance")
        for block_index in range(blocks):
            for within_block in range(block_size):
                layout.append(
                    {
                        "challenge": challenge,
                        "phase": phase,
                        "block": f"{challenge}:{phase}:{block_index:03d}",
                        "within_block": within_block,
                    }
                )
    return layout


def assign_population(
    layout: list[dict[str, Any]],
    assignment_seed: bytes,
    public_seed: bytes,
    padding_seed: bytes,
    control_instances: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_block: dict[str, list[int]] = {}
    for index, item in enumerate(layout):
        by_block.setdefault(item["block"], []).append(index)
    roles: dict[int, str] = {}
    for block, indexes in sorted(by_block.items()):
        role_values = ["S"] * (len(indexes) // 2) + ["R"] * (len(indexes) // 2)
        role_values = shuffled(role_values, assignment_seed, f"roles\x00{block}")
        roles.update(zip(indexes, role_values))

    mapping: list[dict[str, Any]] = []
    for index, item in enumerate(layout):
        slot_id = opaque_slot_id(public_seed, index)
        challenge = item["challenge"]
        role = roles[index]
        token = (
            control_instances[challenge][role]
            if challenge in CONTROL_CHALLENGES
            else None
        )
        mapping.append(
            {
                "opaque_slot_id": slot_id,
                "challenge": challenge,
                "phase": item["phase"],
                "block": item["block"],
                "role": role,
                "private_canary_token_or_null": token,
                "measurement_padding_bytes": padding_value(padding_seed, slot_id),
            }
        )
    order = shuffled(
        [item["opaque_slot_id"] for item in mapping], assignment_seed, "execution-order"
    )
    return mapping, order


def summarize_plans(mapping: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    sample: dict[str, dict[str, int]] = {challenge: {} for challenge in CHALLENGES}
    block_sizes: dict[str, int] = {}
    for item in mapping:
        challenge, phase, block = item["challenge"], item["phase"], item["block"]
        sample[challenge][phase] = sample[challenge].get(phase, 0) + 1
        block_sizes[block] = block_sizes.get(block, 0) + 1
    block_plan = {
        "count": len(block_sizes),
        "blocks": [
            {"block": block, "size": size, "roles": {"R": size // 2, "S": size // 2}}
            for block, size in sorted(block_sizes.items())
        ],
    }
    return sample, block_plan


@dataclass
class CommandReceipt:
    command: list[str]
    started_at: str
    finished_at: str
    monotonic_start_ns: int
    monotonic_finish_ns: int
    returncode: int
    stdout: bytes
    stderr: bytes

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA_COMMAND,
            "command": self.command,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "monotonic_start_ns": self.monotonic_start_ns,
            "monotonic_finish_ns": self.monotonic_finish_ns,
            "returncode": self.returncode,
            "stdout_base64": base64.b64encode(self.stdout).decode("ascii"),
            "stderr_base64": base64.b64encode(self.stderr).decode("ascii"),
        }


class DockerClient:
    def __init__(self, binary: str = "docker"):
        self.binary = binary

    def call(self, arguments: Sequence[str], timeout: int = 120) -> CommandReceipt:
        command = [self.binary, *arguments]
        started_at = utc_now()
        start_ns = time.monotonic_ns()
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout,
            )
            returncode, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            returncode = 124
            stdout = error.stdout or b""
            stderr = (error.stderr or b"") + b"\nWAVE025_RUNNER_TIMEOUT\n"
        return CommandReceipt(
            command=command,
            started_at=started_at,
            finished_at=utc_now(),
            monotonic_start_ns=start_ns,
            monotonic_finish_ns=time.monotonic_ns(),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
        )

    def require(self, arguments: Sequence[str], label: str, timeout: int = 120) -> CommandReceipt:
        receipt = self.call(arguments, timeout)
        if receipt.returncode != 0:
            detail = receipt.stderr.decode("utf-8", "replace")[-1000:]
            raise RunnerError(f"docker {label} failed ({receipt.returncode}): {detail}")
        return receipt


def parse_docker_json(raw: bytes, label: str) -> Any:
    value = parse_json_bytes(raw, label)
    return value


def inspect_image(client: DockerClient, reference: str) -> tuple[dict[str, Any], CommandReceipt]:
    receipt = client.require(["image", "inspect", reference], f"image inspect {reference}")
    value = parse_docker_json(receipt.stdout, f"docker image inspect {reference}")
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise RunnerError(f"docker image inspect returned unexpected shape for {reference}")
    return value[0], receipt


def select_repo_digest(image: dict[str, Any], required: bool) -> str | None:
    digests = image.get("RepoDigests") or []
    if not isinstance(digests, list) or not all(isinstance(item, str) for item in digests):
        raise RunnerError("image RepoDigests is malformed")
    selected = sorted(digests)[0] if digests else None
    if required and selected is None:
        raise RunnerError("base image has no resolved RepoDigest; mutable base tag is insufficient")
    return selected


def build_public_plan(
    batch_id: str,
    mode: str,
    mapping: list[dict[str, Any]],
    block_plan: dict[str, Any],
) -> dict[str, Any]:
    slots = sorted(
        [
            {"opaque_slot_id": item["opaque_slot_id"], "challenge": item["challenge"]}
            for item in mapping
        ],
        key=lambda item: item["opaque_slot_id"],
    )
    return {
        "schema": SCHEMA_PUBLIC_PLAN,
        "batch_id": batch_id,
        "mode": mode,
        "challenges": CHALLENGES,
        "slot_count": len(slots),
        "block_shape": {
            "count": block_plan["count"],
            "blocks": [
                {"block": item["block"], "size": item["size"]}
                for item in block_plan["blocks"]
            ],
        },
        "slots": slots,
        "public_packet_sha256": sha256_bytes(PUBLIC_PACKET_BYTES),
        "resource_envelope": {
            "cpu_limit": "1.0",
            "memory_bytes": 268435456,
            "pids_limit": 64,
            "network": "none",
            "readonly_rootfs": True,
            "candidate_uid_gid": "65534:65534",
            "measurement_padding_surface": "host-private-capture-only",
        },
        "startup_templates": {
            "D0-HOST-LEAK": {
                "candidate_profile": "WEAK_OCI_SHARED_RESIDUE_V1",
                "sacrificial_predecessor": True,
                "shared_residue_surface": "/shared-residue as cwd",
                "cleanup_boundary": "exact generated predecessor and candidate containers only",
                "supervisor_argv": ["/bin/sh", "-c", SUPERVISOR_SCRIPT],
                "supervisor_script_sha256": SUPERVISOR_SCRIPT_SHA256,
            },
            "D1-OCI-CANARY": {
                "candidate_profile": "OCI_PREFIX_CELL_V1",
                "canary_surface_family": "challenge-readonly-file",
                "supervisor_argv": ["/bin/sh", "-c", SUPERVISOR_SCRIPT],
                "supervisor_script_sha256": SUPERVISOR_SCRIPT_SHA256,
            },
            "T-OCI-ISOLATED": {
                "candidate_profile": "OCI_PREFIX_CELL_V1",
                "canary_surface_family": None,
                "shared_residue_surface": None,
                "supervisor_argv": ["/bin/sh", "-c", SUPERVISOR_SCRIPT],
                "supervisor_script_sha256": SUPERVISOR_SCRIPT_SHA256,
            },
        },
    }


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    batch_root = validate_batch_root(Path(args.batch_dir), must_exist=False)
    batch_id = args.batch_id or (
        f"w025-{args.mode}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{secrets.token_hex(6)}"
    )
    if not BATCH_ID.fullmatch(batch_id):
        raise RunnerError("batch id has invalid shape")
    frozen_sources = load_frozen_input_sources(args)
    frozen_registry = frozen_input_registry(frozen_sources)
    frozen_by_name = {source["entry"]["name"]: source["entry"] for source in frozen_sources}
    private_control_registry, private_control_raw = load_private_control_registry(
        args, frozen_sources
    )
    layout = sample_layout(args.mode, args.smoke_per_split)
    sample_plan, block_plan = summarize_plans(layout)
    public_control_source = next(
        source for source in frozen_sources if source["entry"]["name"] == "control_family_registration"
    )
    feature_spec_source = next(
        source for source in frozen_sources if source["entry"]["name"] == "feature_spec"
    )
    executable_profile_source = next(
        source for source in frozen_sources
        if source["entry"]["name"] == "executable_attack_profile"
    )
    control_instances = validate_control_registries(
        public_control_source["value"],
        public_control_source["raw"],
        private_control_registry,
        args.mode,
        sample_plan,
        feature_spec_source["entry"],
        executable_profile_source["value"],
    )
    private_control_commitment = private_control_registry_commitment(
        private_control_registry, private_control_raw
    )

    docker = DockerClient(args.docker_bin)
    final_image, final_receipt = inspect_image(docker, args.image_ref)
    base_image, base_receipt = inspect_image(docker, args.base_image_ref)
    image_id = final_image.get("Id")
    if not isinstance(image_id, str) or not image_id.startswith("sha256:"):
        raise RunnerError("collector final image lacks content-addressed image Id")
    final_repo_digest = select_repo_digest(final_image, required=False)
    base_repo_digest = select_repo_digest(base_image, required=True)

    seeds = {domain: secrets.token_bytes(32) for domain in DOMAINS}
    nonces = {domain: secrets.token_bytes(32) for domain in DOMAINS}
    mapping, execution_order = assign_population(
        layout,
        seeds["PRIVATE_ASSIGNMENT_ORDER"],
        seeds["PUBLIC_ID"],
        seeds["MEASUREMENT_PADDING"],
        control_instances,
    )
    public_plan = build_public_plan(batch_id, args.mode, mapping, block_plan)
    public_raw = canonical_bytes(public_plan)

    classifier_plan = {
        "version": "WAVE025_CLASSIFIER_PLAN_V1",
        "families": [
            "deterministic-exact-categorical",
            "regularized-logistic-linear",
            "bounded-decision-stumps-tree",
            "knn-frozen-normalized-encoding",
        ],
        "holdout_feedback": "none-before-batch-freeze",
        "multiplicity": "Holm",
        "tie_breaking": "frozen-evaluator-source",
    }
    thresholds = {
        "confidence": 0.95,
        "D0_holdout_balanced_accuracy_lower_bound_min": 0.90,
        "D1_holdout_balanced_accuracy_lower_bound_min": 0.90,
        "T_holdout_balanced_accuracy_upper_bound_max": 0.55,
    }
    commitments = {
        domain: commitment(domain, seeds[domain], nonces[domain], public_raw)
        for domain in DOMAINS
    }
    created_at = utc_now()
    precommit = {
        "schema": SCHEMA_PRECOMMIT,
        "batch_id": batch_id,
        "mode": args.mode,
        "challenges": CHALLENGES,
        "created_at": created_at,
        "question_sha256": sha256_file(QUESTION),
        "qualification_contract_sha256": sha256_file(QUALIFICATION_CONTRACT),
        "batch_contract_sha256": sha256_file(BATCH_CONTRACT),
        "collector_source_sha256": sha256_file(COLLECTOR_SOURCE),
        "collector_dockerfile_sha256": sha256_file(COLLECTOR_DOCKERFILE),
        "collector_image_id": image_id,
        "collector_image_repo_digest_or_null": final_repo_digest,
        "collector_base_repo_digest": base_repo_digest,
        "supervisor_script_sha256": SUPERVISOR_SCRIPT_SHA256,
        "evidence_extraction_profile": EVIDENCE_EXTRACTION_PROFILE,
        "runner_source_sha256": sha256_file(Path(__file__)),
        "evaluator_source_manifest_sha256": frozen_by_name[
            "independent_evaluator_source_manifest"
        ]["sha256"],
        "feature_spec_sha256": frozen_by_name["feature_spec"]["sha256"],
        "frozen_inputs": frozen_registry,
        "private_control_registry_commitment": private_control_commitment,
        "sample_plan": sample_plan,
        "block_plan": block_plan,
        "classifier_plan": classifier_plan,
        "thresholds": thresholds,
        "assignment_algorithm": "HMAC-SHA256/FISHER-YATES-REJECTION/W025-V1",
        "public_id_algorithm": "HMAC-SHA256-TRUNC128/W025-V1",
        "padding_algorithm": "HMAC-SHA256-REJECTION-0-256/HOST-PRIVATE/W025-V1",
        "assignment_commitment": commitments["PRIVATE_ASSIGNMENT_ORDER"],
        "public_id_commitment": commitments["PUBLIC_ID"],
        "padding_commitment": commitments["MEASUREMENT_PADDING"],
        "diagnostics": {
            "schema": "WAVE025_RUNNER_DIAGNOSTICS_V1",
            "docker_command_receipt_schema": SCHEMA_COMMAND,
            "raw_slot_channels": [
                "docker-inspect-pre.json",
                "docker-inspect-post.json",
                "docker-events.jsonl",
                "collector-stdout.bin",
                "collector-stderr.bin",
                "collector-out.bin",
                "collector-ready.bin",
                "collector-exit-code.bin",
                "supervisor-control-stdout.bin",
                "supervisor-control-stderr.bin",
            ],
        },
    }
    precommit_raw = canonical_bytes(precommit)
    private_state = {
        "schema": SCHEMA_PRIVATE_STATE,
        "batch_id": batch_id,
        "created_at": created_at,
        "public_plan_sha256": sha256_bytes(public_raw),
        "precommit_sha256": sha256_bytes(precommit_raw),
        "domains": {
            domain: {"seed_hex": seeds[domain].hex(), "nonce_hex": nonces[domain].hex()}
            for domain in DOMAINS
        },
        "mapping": mapping,
        "execution_order": execution_order,
        "image_reference_used_for_prepare": args.image_ref,
        "base_image_reference_used_for_prepare": args.base_image_ref,
        "final_image_inspect_receipt": final_receipt.as_json(),
        "base_image_inspect_receipt": base_receipt.as_json(),
        "private_control_registry": private_control_registry,
    }

    mkdir_exclusive(batch_root, 0o700)
    slots_root = batch_root / "slots"
    mkdir_exclusive(slots_root, 0o700)
    freeze_input_sources(batch_root, frozen_sources)
    # Frozen inputs, private state and the public plan exist before precommit.
    # Once the precommit bytes are written this command performs no further batch write.
    exclusive_json(batch_root / "runner-private-state.json", private_state, 0o600)
    exclusive_write(batch_root / "public-plan.json", public_raw, 0o644)
    exclusive_write(batch_root / "precommit.json", precommit_raw, 0o644)
    return {
        "command": "prepare",
        "state": "PREPARED",
        "batch_id": batch_id,
        "batch_dir": str(batch_root),
        "precommit_sha256": sha256_bytes(precommit_raw),
        "next": "anchor externally, then record receipts with the anchor command",
    }


def validate_frozen_inputs(batch_root: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    precommit, precommit_raw = read_json(batch_root / "precommit.json", SCHEMA_PRECOMMIT)
    public_plan, public_raw = read_json(batch_root / "public-plan.json", SCHEMA_PUBLIC_PLAN)
    private_state, _ = read_json(
        batch_root / "runner-private-state.json", SCHEMA_PRIVATE_STATE
    )
    assert_regular_file(batch_root / "runner-private-state.json", 0o600)
    if precommit["batch_id"] != public_plan["batch_id"] or precommit["batch_id"] != private_state["batch_id"]:
        raise RunnerError("batch id mismatch across frozen objects")
    if sha256_bytes(public_raw) != private_state["public_plan_sha256"]:
        raise RunnerError("public plan hash no longer matches private state")
    if sha256_bytes(precommit_raw) != private_state["precommit_sha256"]:
        raise RunnerError("precommit hash no longer matches private state")
    frozen = validate_frozen_input_registry(batch_root, precommit)
    private_control_registry = private_state.get("private_control_registry")
    private_control_raw = canonical_bytes(private_control_registry)
    validate_control_registries(
        frozen["control_family_registration"]["value"],
        frozen["control_family_registration"]["raw"],
        private_control_registry,
        precommit["mode"],
        precommit["sample_plan"],
        frozen["feature_spec"]["entry"],
        frozen["executable_attack_profile"]["value"],
    )
    rebuilt_control_commitment = private_control_registry_commitment(
        private_control_registry, private_control_raw
    )
    if precommit.get("private_control_registry_commitment") != rebuilt_control_commitment:
        raise RunnerError("private control registry no longer matches precommit commitment")
    if precommit["runner_source_sha256"] != sha256_file(Path(__file__)):
        raise RunnerError("runner source changed after precommit")
    if precommit["question_sha256"] != sha256_file(QUESTION):
        raise RunnerError("question changed after precommit")
    if precommit["qualification_contract_sha256"] != sha256_file(QUALIFICATION_CONTRACT):
        raise RunnerError("qualification contract changed after precommit")
    if precommit["batch_contract_sha256"] != sha256_file(BATCH_CONTRACT):
        raise RunnerError("batch evidence contract changed after precommit")
    if precommit["collector_source_sha256"] != sha256_file(COLLECTOR_SOURCE):
        raise RunnerError("collector source changed after precommit")
    if precommit["collector_dockerfile_sha256"] != sha256_file(COLLECTOR_DOCKERFILE):
        raise RunnerError("collector Dockerfile changed after precommit")
    if precommit.get("supervisor_script_sha256") != SUPERVISOR_SCRIPT_SHA256:
        raise RunnerError("supervisor script changed after precommit")
    if precommit.get("evidence_extraction_profile") != EVIDENCE_EXTRACTION_PROFILE:
        raise RunnerError("evidence extraction profile changed after precommit")
    return precommit, public_plan, private_state


def parse_anchor_receipts(args: argparse.Namespace, precommit_sha: str) -> list[dict[str, str]]:
    raw_receipts: list[Any] = []
    for value in args.receipt_json or []:
        raw_receipts.append(parse_json_bytes(value.encode("utf-8"), "--receipt-json"))
    for filename in args.receipt_file or []:
        raw_receipts.append(parse_json_bytes(Path(filename).read_bytes(), filename))
    if not raw_receipts:
        raise RunnerError("anchor requires at least one already-created root receipt")
    normalized: list[dict[str, str]] = []
    required = {"kind", "reference", "anchored_at", "precommit_sha256"}
    for index, value in enumerate(raw_receipts):
        if not isinstance(value, dict) or set(value) != required:
            raise RunnerError(f"anchor receipt {index} fields must be exactly {sorted(required)}")
        if value["precommit_sha256"] != precommit_sha:
            raise RunnerError(f"anchor receipt {index} binds the wrong precommit")
        if not all(isinstance(value[key], str) and value[key] for key in required):
            raise RunnerError(f"anchor receipt {index} fields must be non-empty strings")
        normalized.append({key: value[key] for key in sorted(required)})
    references = [item["reference"] for item in normalized]
    if len(references) != len(set(references)):
        raise RunnerError("duplicate anchor reference")
    return normalized


def anchor(args: argparse.Namespace) -> dict[str, Any]:
    batch_root = validate_batch_root(Path(args.batch_dir), must_exist=True)
    precommit, _, _ = validate_frozen_inputs(batch_root)
    if (batch_root / "anchor-receipt.json").exists():
        raise RunnerError("anchor receipt already exists and will not be overwritten")
    precommit_sha = sha256_file(batch_root / "precommit.json")
    receipts = parse_anchor_receipts(args, precommit_sha)
    qualifying = any(item["kind"] != "LOCAL_NONQUALIFYING_ANCHOR" for item in receipts)
    if precommit["mode"] == "formal" and not qualifying:
        raise RunnerError("formal batch requires at least one external root receipt")
    document = {
        "schema": SCHEMA_ANCHOR,
        "batch_id": precommit["batch_id"],
        "recorded_at": utc_now(),
        "precommit_sha256": precommit_sha,
        "root_receipts": receipts,
        "qualifying_external_anchor_present": qualifying,
    }
    raw = exclusive_json(batch_root / "anchor-receipt.json", document, 0o644)
    return {
        "command": "anchor",
        "state": "EXTERNALLY_ANCHORED" if qualifying else "LOCALLY_ANCHORED_NONQUALIFYING",
        "batch_id": precommit["batch_id"],
        "anchor_receipt_sha256": sha256_bytes(raw),
        "root_receipt_count": len(receipts),
    }


def record_command(
    client: DockerClient,
    arguments: Sequence[str],
    journal_dir: Path,
    sequence: int,
    label: str,
    timeout: int = 120,
) -> CommandReceipt:
    receipt = client.call(arguments, timeout)
    exclusive_json(journal_dir / f"{sequence:02d}-{label}.json", receipt.as_json(), 0o600)
    return receipt


def one_inspect(raw: bytes, label: str) -> dict[str, Any]:
    value = parse_docker_json(raw, label)
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise RunnerError(f"{label} must be a one-element Docker inspect array")
    return value[0]


def role_free_container_name(batch_id: str, slot_id: str, suffix: str) -> str:
    batch_token = sha256_bytes(batch_id.encode("utf-8"))[:10]
    return f"w025-{batch_token}-{slot_id[2:18]}-{suffix}-a001"


def docker_mount(source: Path, destination: str, readonly: bool) -> str:
    raw_source = str(source.resolve())
    if "," in raw_source:
        raise RunnerError("Docker --mount source cannot contain comma in this runner")
    value = f"type=bind,src={raw_source},dst={destination}"
    return value + (",readonly" if readonly else "")


def make_template(path: Path, canary_token: str | None = None, d0: bool = False) -> None:
    mkdir_exclusive(path, 0o755)
    exclusive_write(path / "collector-input.json", PUBLIC_PACKET_BYTES, 0o444)
    exclusive_write(path / "input.bin", FIXED_INPUT_BYTES, 0o444)
    if canary_token is not None and not d0:
        exclusive_write(
            path / f"{canary_token}.txt",
            (canary_token + "\n").encode("utf-8"),
            0o444,
        )
    for child in path.iterdir():
        os.utime(child, ns=(0, 0), follow_symlinks=False)
    os.utime(path, ns=(0, 0), follow_symlinks=False)


def expected_template_files(
    challenge: str, private_instance: str | None
) -> dict[str, bytes]:
    expected = {
        "collector-input.json": PUBLIC_PACKET_BYTES,
        "input.bin": FIXED_INPUT_BYTES,
    }
    if challenge == "D1-OCI-CANARY":
        if private_instance is None or not D1_CANARY_TOKEN.fullmatch(private_instance):
            raise RunnerError("D1 runtime template lacks a registered token")
        expected[f"{private_instance}.txt"] = (private_instance + "\n").encode("utf-8")
    elif challenge == "D0-HOST-LEAK":
        if private_instance is None or not D0_MARKER_BASENAME.fullmatch(private_instance):
            raise RunnerError("D0 runtime template lacks a registered marker")
    elif challenge == "T-OCI-ISOLATED":
        if private_instance is not None:
            raise RunnerError("T runtime template received a private control instance")
    else:
        raise RunnerError(f"unknown runtime template challenge: {challenge}")
    return expected


def validate_runtime_template(
    path: Path, challenge: str, private_instance: str | None
) -> None:
    if not path.is_dir() or path.is_symlink():
        raise RunnerError(f"runtime template is not a real directory: {path}")
    if stat.S_IMODE(path.lstat().st_mode) != 0o755:
        raise RunnerError(f"runtime template directory mode mismatch: {path}")
    expected = expected_template_files(challenge, private_instance)
    children = list(path.iterdir())
    names = {child.name for child in children}
    if len(children) != len(names) or names != set(expected):
        raise RunnerError(f"runtime template closed inventory mismatch: {path}")
    for name, exact_bytes in expected.items():
        child = path / name
        assert_regular_file(child, 0o444)
        if child.read_bytes() != exact_bytes:
            raise RunnerError(f"runtime template exact bytes mismatch: {path / name}")


def prepare_runtime_templates(
    batch_root: Path, private_state: dict[str, Any]
) -> tuple[Path, dict[str, Path]]:
    runtime_root = Path(str(batch_root) + ".runtime")
    if runtime_root.exists():
        if not runtime_root.is_dir() or runtime_root.is_symlink():
            raise RunnerError("runtime root is not a safe directory")
    else:
        mkdir_exclusive(runtime_root, 0o700)
    if stat.S_IMODE(runtime_root.lstat().st_mode) != 0o700:
        raise RunnerError("runtime root mode must be exactly 0700")
    templates = runtime_root / "templates"
    if not templates.exists():
        mkdir_exclusive(templates, 0o700)
    if not templates.is_dir() or templates.is_symlink():
        raise RunnerError("runtime templates root is not a real directory")
    if stat.S_IMODE(templates.lstat().st_mode) != 0o700:
        raise RunnerError("runtime templates root mode must be exactly 0700")
    t_template = templates / "t-isolated"
    if not t_template.exists():
        make_template(t_template)

    result: dict[str, Path] = {}
    for item in private_state["mapping"]:
        slot_id, challenge = item["opaque_slot_id"], item["challenge"]
        if challenge == "T-OCI-ISOLATED":
            result[slot_id] = t_template
            continue
        slot_template = templates / slot_id
        if not slot_template.exists():
            make_template(
                slot_template,
                item["private_canary_token_or_null"],
                d0=(challenge == "D0-HOST-LEAK"),
            )
        result[slot_id] = slot_template
    expected_template_names = {
        "t-isolated",
        *(
            item["opaque_slot_id"]
            for item in private_state["mapping"]
            if item["challenge"] != "T-OCI-ISOLATED"
        ),
    }
    actual_template_entries = list(templates.iterdir())
    actual_template_names = {item.name for item in actual_template_entries}
    if (
        len(actual_template_entries) != len(actual_template_names)
        or actual_template_names != expected_template_names
    ):
        raise RunnerError("runtime templates root closed inventory mismatch")
    for item in private_state["mapping"]:
        validate_runtime_template(
            result[item["opaque_slot_id"]],
            item["challenge"],
            item["private_canary_token_or_null"],
        )
    return runtime_root, result


def baseline_create_arguments(
    name: str,
    batch_id: str,
    slot_id: str,
    image_id: str,
    challenge_root: Path,
    hostname: str,
    challenge: str,
    residue_root: Path | None,
) -> list[str]:
    arguments = [
        "create",
        "--name",
        name,
        "--label",
        f"org.towow.wave025.batch={batch_id}",
        "--label",
        f"org.towow.wave025.slot={slot_id}",
        "--label",
        "org.towow.wave025.owner=runner-v1",
        "--network",
        "none",
        "--read-only",
        "--user",
        "65534:65534",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--pids-limit",
        "64",
        "--memory",
        "268435456",
        "--cpus",
        "1.0",
        "--ipc",
        "private",
        "--hostname",
        hostname,
        "--mount",
        docker_mount(challenge_root, "/challenge", True),
        "--tmpfs",
        "/out:rw,noexec,nosuid,nodev,uid=65534,gid=65534,mode=0700",
    ]
    if challenge == "D0-HOST-LEAK":
        if residue_root is None:
            raise RunnerError("D0 requires a shared residue root")
        arguments += [
            "--mount",
            docker_mount(residue_root, "/shared-residue", True),
            "--workdir",
            "/shared-residue",
        ]
    else:
        arguments += ["--workdir", "/app"]
    arguments += ["--entrypoint", "/bin/sh", image_id, "-c", SUPERVISOR_SCRIPT]
    return arguments


def predecessor_arguments(
    name: str,
    batch_id: str,
    slot_id: str,
    image_id: str,
    residue_root: Path,
    marker_basename: str,
) -> list[str]:
    return [
        "create",
        "--name",
        name,
        "--label",
        f"org.towow.wave025.batch={batch_id}",
        "--label",
        f"org.towow.wave025.slot={slot_id}",
        "--label",
        "org.towow.wave025.owner=runner-v1-predecessor",
        "--network",
        "none",
        "--read-only",
        "--user",
        "65534:65534",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--pids-limit",
        "16",
        "--memory",
        "67108864",
        "--cpus",
        "0.25",
        "--mount",
        docker_mount(residue_root, "/shared-residue", False),
        "--entrypoint",
        "/bin/sh",
        image_id,
        "-c",
        'set -eu; umask 077; : > "/shared-residue/$1"; chmod 0400 "/shared-residue/$1"; sync',
        "wave025-predecessor",
        marker_basename,
    ]


def validate_d0_residue_before_predecessor(residue_root: Path) -> None:
    if not residue_root.is_dir() or residue_root.is_symlink():
        raise RunnerError("D0 residue root is not a real directory")
    if list(residue_root.iterdir()):
        raise RunnerError("D0 residue root is not empty before predecessor")


def validate_d0_residue_after_predecessor(
    residue_root: Path, marker_basename: str
) -> None:
    if not D0_MARKER_BASENAME.fullmatch(marker_basename):
        raise RunnerError("D0 registry selected an invalid marker basename")
    entries = list(residue_root.iterdir())
    if len(entries) != 1 or entries[0].name != marker_basename:
        raise RunnerError("D0 predecessor must create exactly the registered marker")
    marker = entries[0]
    info = marker.lstat()
    if marker.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise RunnerError("D0 marker must be a regular non-symlink file")
    if info.st_size != 0:
        raise RunnerError("D0 marker content must be empty")
    if stat.S_IMODE(info.st_mode) != 0o400:
        raise RunnerError("D0 marker mode must be exactly 0400")


def d0_residue_snapshot(residue_root: Path) -> dict[str, Any]:
    if not residue_root.is_dir() or residue_root.is_symlink():
        raise RunnerError("D0 residue root is not a real directory")
    root_info = residue_root.lstat()
    entries: list[dict[str, Any]] = []
    for child in sorted(residue_root.iterdir(), key=lambda item: item.name):
        info = child.lstat()
        entry_type = (
            "symlink" if child.is_symlink()
            else "file" if stat.S_ISREG(info.st_mode)
            else "directory" if stat.S_ISDIR(info.st_mode)
            else "other"
        )
        entries.append(
            {
                "basename": child.name,
                "type": entry_type,
                "size_bytes": info.st_size,
                "mode_octal": f"0o{stat.S_IMODE(info.st_mode):04o}",
                "content_sha256_or_null": (
                    sha256_file(child) if entry_type == "file" else None
                ),
            }
        )
    return {
        "directory_mode_octal": f"0o{stat.S_IMODE(root_info.st_mode):04o}",
        "entry_count": len(entries),
        "entries": entries,
    }


def ensure_owned_stopped(
    inspect_value: dict[str, Any], expected_name: str, batch_id: str, slot_id: str
) -> None:
    actual_name = str(inspect_value.get("Name", "")).lstrip("/")
    labels = (inspect_value.get("Config") or {}).get("Labels") or {}
    running = bool((inspect_value.get("State") or {}).get("Running"))
    if actual_name != expected_name:
        raise RunnerError("refusing cleanup: container name mismatch")
    if labels.get("org.towow.wave025.batch") != batch_id:
        raise RunnerError("refusing cleanup: batch ownership label mismatch")
    if labels.get("org.towow.wave025.slot") != slot_id:
        raise RunnerError("refusing cleanup: slot ownership label mismatch")
    if running:
        raise RunnerError("refusing cleanup: owned container is still running")


def clean_exact_container(
    client: DockerClient,
    name: str,
    batch_id: str,
    slot_id: str,
    journal_dir: Path,
    sequence: int,
) -> tuple[int, list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    inspect_receipt = record_command(
        client, ["inspect", name], journal_dir, sequence, "cleanup-inspect"
    )
    diagnostics.append(inspect_receipt.as_json())
    sequence += 1
    if inspect_receipt.returncode != 0:
        return sequence, diagnostics
    value = one_inspect(inspect_receipt.stdout, f"cleanup inspect {name}")
    ensure_owned_stopped(value, name, batch_id, slot_id)
    remove_receipt = record_command(client, ["rm", name], journal_dir, sequence, "cleanup-rm")
    diagnostics.append(remove_receipt.as_json())
    sequence += 1
    if remove_receipt.returncode != 0:
        raise RunnerError(f"failed to remove exact stopped owned container {name}")
    return sequence, diagnostics


def env_hashes(environment: Any) -> list[dict[str, str]]:
    if environment is None:
        return []
    if not isinstance(environment, list) or not all(isinstance(item, str) for item in environment):
        raise RunnerError("Docker inspect Config.Env is malformed")
    result = []
    for item in environment:
        key, separator, value = item.partition("=")
        if not separator:
            value = ""
        result.append(
            {
                "key": key,
                "value_sha256": sha256_bytes(value.encode("utf-8")),
                "value_byte_length": str(len(value.encode("utf-8"))),
            }
        )
    return sorted(result, key=lambda item: item["key"])


def normalized_mounts(inspect_value: dict[str, Any]) -> list[dict[str, Any]]:
    mounts: list[dict[str, Any]] = []
    for mount in inspect_value.get("Mounts") or []:
        source = mount.get("Source")
        mounts.append(
            {
                "type": mount.get("Type"),
                "source_or_source_hash": (
                    f"sha256:{sha256_bytes(str(source).encode('utf-8'))}" if source else None
                ),
                "destination": mount.get("Destination"),
                "readonly": not bool(mount.get("RW")),
                "options": {
                    "mode": mount.get("Mode") or "",
                    "propagation": mount.get("Propagation") or "",
                },
            }
        )
    host_config = inspect_value.get("HostConfig") or {}
    for destination, options in sorted((host_config.get("Tmpfs") or {}).items()):
        mounts.append(
            {
                "type": "tmpfs",
                "source_or_source_hash": None,
                "destination": destination,
                "readonly": False,
                "options": {"raw": options},
            }
        )
    return sorted(mounts, key=lambda item: (str(item["destination"]), str(item["type"])))


def derive_host_launch(
    slot_id: str,
    challenge: str,
    pre: dict[str, Any],
    post: dict[str, Any],
    precommit: dict[str, Any],
    docker_version_receipt: CommandReceipt,
    command_receipts: list[dict[str, Any]],
    extraction_audit: dict[str, Any],
    control_audit: dict[str, Any],
    private_predecessor_commitment: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    config = pre.get("Config") or {}
    host = pre.get("HostConfig") or {}
    state = post.get("State") or {}
    entrypoint = config.get("Entrypoint") or []
    command = config.get("Cmd") or []
    if isinstance(entrypoint, str):
        entrypoint = [entrypoint]
    if isinstance(command, str):
        command = [command]
    mounts = normalized_mounts(pre)
    checks: list[tuple[str, bool]] = [
        ("image_id", pre.get("Image") == precommit["collector_image_id"]),
        (
            "frozen_supervisor_argv",
            [*entrypoint, *command] == ["/bin/sh", "-c", SUPERVISOR_SCRIPT],
        ),
        ("network_none", host.get("NetworkMode") == "none"),
        ("readonly_rootfs", host.get("ReadonlyRootfs") is True),
        ("non_root", str(config.get("User") or "") not in {"", "0", "0:0", "root"}),
        ("cap_drop_all", "ALL" in [str(item).upper() for item in (host.get("CapDrop") or [])]),
        (
            "no_new_privileges",
            any("no-new-privileges" in str(item) for item in (host.get("SecurityOpt") or [])),
        ),
        ("pid_private", (host.get("PidMode") or "private") != "host"),
        ("ipc_private", (host.get("IpcMode") or "private") != "host"),
        ("uts_private", (host.get("UTSMode") or "private") != "host"),
        ("pids_limited", isinstance(host.get("PidsLimit"), int) and host.get("PidsLimit") > 0),
        ("memory_limited", isinstance(host.get("Memory"), int) and host.get("Memory") > 0),
        ("cpu_limited", isinstance(host.get("NanoCpus"), int) and host.get("NanoCpus") > 0),
        (
            "challenge_readonly_bind",
            sum(
                1
                for item in mounts
                if item["destination"] == "/challenge"
                and item["type"] == "bind"
                and item["readonly"] is True
            )
            == 1,
        ),
        (
            "out_exclusive_tmpfs",
            sum(
                1
                for item in mounts
                if item["destination"] == "/out" and item["type"] == "tmpfs"
            )
            == 1,
        ),
        (
            "no_docker_socket",
            not any("docker.sock" in str(item.get("destination")) for item in mounts),
        ),
    ]
    bind_destinations = sorted(
        item["destination"] for item in mounts if item["type"] == "bind"
    )
    if challenge == "T-OCI-ISOLATED":
        checks += [
            ("T_only_challenge_bind", bind_destinations == ["/challenge"]),
            ("T_fixed_workdir", config.get("WorkingDir") == "/app"),
            (
                "T_role_free_container_name",
                re.fullmatch(r"/?w025-[0-9a-f]{10}-[0-9a-f]{16}-c-a001", str(pre.get("Name", "")))
                is not None,
            ),
        ]
    elif challenge == "D1-OCI-CANARY":
        checks += [
            ("D1_only_challenge_bind", bind_destinations == ["/challenge"]),
            ("D1_fixed_workdir", config.get("WorkingDir") == "/app"),
        ]
    else:
        checks += [
            ("D0_shared_residue_bind", "/shared-residue" in bind_destinations),
            ("D0_shared_residue_cwd", config.get("WorkingDir") == "/shared-residue"),
        ]
    failures = [name for name, passed in checks if not passed]
    document = {
        "schema": SCHEMA_HOST_LAUNCH,
        "opaque_slot_id": slot_id,
        "container_id": pre.get("Id"),
        "container_name": str(pre.get("Name") or "").lstrip("/"),
        "image_id": pre.get("Image"),
        "repo_digest_or_null": precommit["collector_image_repo_digest_or_null"],
        "base_repo_digest": precommit["collector_base_repo_digest"],
        "argv": [*entrypoint, *command],
        "env_key_value_hashes": env_hashes(config.get("Env")),
        "working_dir": config.get("WorkingDir"),
        "user": config.get("User"),
        "network_mode": host.get("NetworkMode") or "default",
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "cap_drop": host.get("CapDrop") or [],
        "security_opt": host.get("SecurityOpt") or [],
        "pid_namespace_mode": host.get("PidMode") or "private",
        "ipc_namespace_mode": host.get("IpcMode") or "private",
        "uts_namespace_mode": host.get("UTSMode") or "private",
        "user_namespace_mode": host.get("UsernsMode") or "daemon-default",
        "pids_limit": host.get("PidsLimit"),
        "memory_limit_bytes": host.get("Memory"),
        "nano_cpus": host.get("NanoCpus"),
        "mounts": mounts,
        "created_at": pre.get("Created"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "exit_code": state.get("ExitCode"),
        "oom_killed": state.get("OOMKilled"),
        "daemon_error": state.get("Error") or None,
        "diagnostics": {
            "schema": "WAVE025_RUNNER_DIAGNOSTICS_V1",
            "actual_configuration_checks": [
                {"check": name, "passed": passed} for name, passed in checks
            ],
            "docker_version_command": docker_version_receipt.as_json(),
            "host_command_receipts": command_receipts,
            "post_observation_extraction": extraction_audit,
            "registered_control_integrity": control_audit,
            "private_predecessor_provenance_commitment_or_null": (
                private_predecessor_commitment
            ),
        },
    }
    return document, failures


def validate_anchor(batch_root: Path, precommit: dict[str, Any]) -> dict[str, Any]:
    anchor_document, _ = read_json(batch_root / "anchor-receipt.json", SCHEMA_ANCHOR)
    if anchor_document["batch_id"] != precommit["batch_id"]:
        raise RunnerError("anchor batch id mismatch")
    if anchor_document["precommit_sha256"] != sha256_file(batch_root / "precommit.json"):
        raise RunnerError("anchor no longer binds exact precommit bytes")
    receipts = anchor_document.get("root_receipts")
    if not isinstance(receipts, list) or not receipts:
        raise RunnerError("anchor contains no root receipts")
    if precommit["mode"] == "formal" and not anchor_document.get(
        "qualifying_external_anchor_present"
    ):
        raise RunnerError("formal batch has no qualifying external anchor")
    return anchor_document


def collector_bytes_are_valid(stdout: bytes, stderr: bytes, out: bytes, exit_code: Any) -> bool:
    if exit_code != 0 or stderr != b"" or stdout != out:
        return False
    try:
        parsed = parse_json_bytes(out, "collector output")
    except RunnerError:
        return False
    return (
        isinstance(parsed, dict)
        and parsed.get("schema") == SCHEMA_FEATURES
        and canonical_bytes(parsed) == out
    )


def all_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from all_string_values(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from all_string_values(item)


def registered_private_derivatives(
    control_instances: dict[str, dict[str, str]]
) -> set[str]:
    derivatives: set[str] = set()
    for challenge, by_role in control_instances.items():
        for instance in by_role.values():
            derivatives.add(instance)
            derivatives.add(sha256_bytes(instance.encode("utf-8")))
            if challenge == "D0-HOST-LEAK":
                tag = instance.removeprefix("d0-residue-v1-")
                derivatives.add(tag)
                derivatives.add(sha256_bytes(tag.encode("utf-8")))
            elif challenge == "D1-OCI-CANARY":
                filename = f"{instance}.txt"
                content = (instance + "\n").encode("utf-8")
                derivatives.update(
                    {
                        filename,
                        sha256_bytes(filename.encode("utf-8")),
                        sha256_bytes(content),
                    }
                )
    return derivatives


def audit_registered_control_receipt(
    challenge: str,
    expected_instance: str | None,
    collector_out: bytes,
    inspect_pre: dict[str, Any],
    residue_root: Path | None,
    precommit: dict[str, Any],
    control_instances: dict[str, dict[str, str]],
) -> dict[str, Any]:
    failures: list[str] = []
    parsed: Any = None
    try:
        parsed = parse_json_bytes(collector_out, "registered control collector receipt")
    except RunnerError:
        failures.append("collector_receipt_invalid_json")
    if not isinstance(parsed, dict) or parsed.get("schema") != SCHEMA_FEATURES:
        failures.append("collector_receipt_wrong_schema")
        parsed = {}
    family_id = None
    for family in precommit["private_control_registry_commitment"]["family_hashes"]:
        if family["challenge"] == challenge:
            family_id = family["family_id"]
            break
    mounts = inspect_pre.get("Mounts") or []
    shared_mounts = [
        item for item in mounts
        if isinstance(item, dict) and item.get("Destination") == "/shared-residue"
    ]
    if challenge == "D0-HOST-LEAK":
        if expected_instance is None or not D0_MARKER_BASENAME.fullmatch(expected_instance):
            failures.append("d0_expected_marker_invalid")
        if len(shared_mounts) != 1 or shared_mounts[0].get("RW") is not False:
            failures.append("d0_shared_residue_mount_not_exact_readonly")
        elif residue_root is None or Path(str(shared_mounts[0].get("Source"))).resolve() != residue_root.resolve():
            failures.append("d0_shared_residue_mount_source_mismatch")
        if (inspect_pre.get("Config") or {}).get("WorkingDir") != "/shared-residue":
            failures.append("d0_candidate_cwd_mismatch")
        tree = ((parsed.get("directory_trees") or {}).get("cwd") or {})
        if tree.get("available") is not True or tree.get("truncated") is not False:
            failures.append("d0_cwd_tree_unavailable_or_truncated")
        if tree.get("errors") != []:
            failures.append("d0_cwd_tree_has_errors")
        entries = tree.get("entries")
        entries = entries if isinstance(entries, list) else []
        marker_entries = [
            item for item in entries
            if isinstance(item, dict) and item.get("path") == expected_instance
        ]
        non_dot_entries = [
            item for item in entries
            if isinstance(item, dict) and item.get("path") != "."
        ]
        if len(marker_entries) != 1 or len(non_dot_entries) != 1:
            failures.append("d0_collector_marker_count_or_basename_mismatch")
        elif (
            marker_entries[0].get("type") != "file"
            or str(marker_entries[0].get("size_bytes")) != "0"
            or marker_entries[0].get("mode_octal") != "0o0400"
        ):
            failures.append("d0_collector_marker_shape_mismatch")
        try:
            if residue_root is None:
                raise RunnerError("missing D0 residue root")
            validate_d0_residue_after_predecessor(residue_root, expected_instance or "")
            if stat.S_IMODE(residue_root.stat().st_mode) != 0o555:
                raise RunnerError("D0 residue root mode is not 0555 after candidate")
        except RunnerError:
            failures.append("d0_host_marker_post_candidate_mismatch")
    elif challenge == "D1-OCI-CANARY":
        if expected_instance is None or not D1_CANARY_TOKEN.fullmatch(expected_instance):
            failures.append("d1_expected_canary_invalid")
        if shared_mounts:
            failures.append("d1_has_unexpected_shared_residue_mount")
        visible = parsed.get("visible_canaries")
        visible = visible if isinstance(visible, list) else []
        locations = [
            item.get("location") for item in visible if isinstance(item, dict)
        ]
        expected_location = f"{expected_instance}.txt"
        if locations.count(expected_location) != 2:
            failures.append("d1_registered_canary_not_observed_twice")
        sources = {
            item.get("source") for item in visible
            if isinstance(item, dict) and item.get("location") == expected_location
        }
        if sources != {"challenge-entry-name", "challenge-file-content"}:
            failures.append("d1_registered_canary_sources_mismatch")
    elif challenge == "T-OCI-ISOLATED":
        if expected_instance is not None:
            failures.append("t_has_private_control_instance")
        if shared_mounts:
            failures.append("t_has_shared_residue_mount")
        if (inspect_pre.get("Config") or {}).get("WorkingDir") == "/shared-residue":
            failures.append("t_has_shared_residue_cwd")
        visible = parsed.get("visible_canaries")
        if visible != []:
            failures.append("t_visible_canaries_not_empty")
        tree = ((parsed.get("directory_trees") or {}).get("challenge") or {})
        if tree.get("available") is not True or tree.get("truncated") is not False:
            failures.append("t_challenge_tree_unavailable_or_truncated")
        if tree.get("errors") != []:
            failures.append("t_challenge_tree_has_errors")
        entries = tree.get("entries")
        entries = entries if isinstance(entries, list) else []
        expected_paths = {".", "collector-input.json", "input.bin"}
        paths = [
            item.get("path") if isinstance(item, dict) else None for item in entries
        ]
        if len(paths) != 3 or len(set(paths)) != 3 or set(paths) != expected_paths:
            failures.append("t_challenge_tree_closed_inventory_mismatch")
        else:
            by_path = {item["path"]: item for item in entries}
            expected_shapes = {
                ".": ("directory", "0o0755", None),
                "collector-input.json": ("file", "0o0444", len(PUBLIC_PACKET_BYTES)),
                "input.bin": ("file", "0o0444", len(FIXED_INPUT_BYTES)),
            }
            for path, (entry_type, mode_octal, size_bytes) in expected_shapes.items():
                entry = by_path[path]
                if entry.get("type") != entry_type or entry.get("mode_octal") != mode_octal:
                    failures.append("t_challenge_tree_entry_shape_mismatch")
                    break
                if size_bytes is not None and str(entry.get("size_bytes")) != str(size_bytes):
                    failures.append("t_challenge_tree_entry_shape_mismatch")
                    break
        private_derivatives = registered_private_derivatives(control_instances)
        receipt_strings = list(all_string_values(parsed))
        inspect_strings = list(all_string_values(inspect_pre))
        if any(
            derivative in value
            for derivative in private_derivatives
            for value in receipt_strings
        ):
            failures.append("t_collector_receipt_contains_registered_private_derivative")
        if any(
            derivative in value
            for derivative in private_derivatives
            for value in inspect_strings
        ):
            failures.append("t_container_configuration_contains_registered_private_derivative")
    else:
        failures.append("unknown_control_challenge")
    return {
        "schema": "WAVE025_REGISTERED_CONTROL_INTEGRITY_AUDIT_V1",
        "challenge": challenge,
        "family_id_or_null": family_id,
        "valid": not failures,
        "failures": sorted(set(failures)),
        "private_instance_disclosed": False,
    }


def rfc3339_epoch_ns(value: str, label: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as error:
        raise RunnerError(f"invalid RFC3339 timestamp for {label}: {value!r}") from error
    if parsed.tzinfo is None:
        raise RunnerError(f"RFC3339 timestamp lacks timezone for {label}")
    utc_value = parsed.astimezone(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = utc_value - epoch
    return (
        (delta.days * 86_400 + delta.seconds) * 1_000_000_000
        + delta.microseconds * 1_000
    )


def audit_docker_events(
    raw: bytes,
    container_id: str,
    container_name: str,
    ready_receipt: CommandReceipt,
    extraction_receipts: list[CommandReceipt],
    supervisor_exit_code: Any,
) -> dict[str, Any]:
    failures: list[str] = []
    expected_logs_command = [
        ready_receipt.command[0] if ready_receipt.command else "docker",
        "logs",
        container_name,
    ]
    if ready_receipt.command != expected_logs_command:
        failures.append("ready_observer_command_mismatch")
    if ready_receipt.returncode != 0:
        failures.append("ready_observer_nonzero")
    if ready_receipt.stdout != SUPERVISOR_READY_FRAME:
        failures.append("ready_frame_mismatch")
    if ready_receipt.stderr != b"":
        failures.append("ready_observer_stderr_nonempty")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        try:
            value = parse_json_bytes(line, f"docker events line {line_number}")
        except RunnerError:
            failures.append(f"event_{line_number}_invalid_json")
            continue
        if not isinstance(value, dict):
            failures.append(f"event_{line_number}_not_object")
            continue
        events.append(value)

    expected_actions = ["create", "start"]
    for item in EXTRACTION_READS:
        command = f"/bin/cat {item['out_path']}"
        expected_actions.extend(
            [f"exec_create: {command}", f"exec_start: {command}", "exec_die"]
        )
    expected_actions.extend(["kill", "die"])
    actions = [event.get("Action") for event in events]
    if actions != expected_actions:
        failures.append("event_action_sequence_mismatch")

    event_times: list[int] = []
    for index, event in enumerate(events):
        actor = event.get("Actor") or {}
        attributes = actor.get("Attributes") or {}
        if event.get("Type") != "container":
            failures.append(f"event_{index + 1}_wrong_type")
        if actor.get("ID") != container_id:
            failures.append(f"event_{index + 1}_wrong_container_id")
        if attributes.get("name") != container_name:
            failures.append(f"event_{index + 1}_wrong_container_name")
        event_time = event.get("timeNano")
        if not isinstance(event_time, int):
            failures.append(f"event_{index + 1}_missing_time_nano")
        else:
            event_times.append(event_time)
    if len(event_times) == len(events) and event_times != sorted(event_times):
        failures.append("event_time_order_mismatch")

    if len(extraction_receipts) != len(EXTRACTION_READS):
        failures.append("registered_exec_receipt_count_mismatch")
    previous_finish = ready_receipt.monotonic_finish_ns
    ready_wall_ns = rfc3339_epoch_ns(ready_receipt.finished_at, "ready receipt finish")
    exec_groups: list[dict[str, Any]] = []
    for offset, item in enumerate(EXTRACTION_READS):
        event_index = 2 + (offset * 3)
        receipt = extraction_receipts[offset] if offset < len(extraction_receipts) else None
        expected_command = [
            receipt.command[0] if receipt is not None and receipt.command else "docker",
            "exec",
            "--user",
            "65534:65534",
            container_name,
            "/bin/cat",
            item["out_path"],
        ]
        if receipt is None:
            failures.append(f"exec_{offset + 1}_missing_command_receipt")
        else:
            if receipt.command != expected_command:
                failures.append(f"exec_{offset + 1}_command_mismatch")
            if receipt.monotonic_start_ns < previous_finish:
                failures.append(f"exec_{offset + 1}_host_order_mismatch")
            previous_finish = receipt.monotonic_finish_ns
            if receipt.returncode != 0:
                failures.append(f"exec_{offset + 1}_nonzero")
            if receipt.stderr != b"":
                failures.append(f"exec_{offset + 1}_stderr_nonempty")

        group_events = events[event_index : event_index + 3]
        event_ids: list[str | None] = []
        for event in group_events:
            actor = event.get("Actor") or {}
            attributes = actor.get("Attributes") or {}
            event_ids.append(attributes.get("execID"))
        event_id = event_ids[0] if len(event_ids) == 3 else None
        if (
            len(event_ids) != 3
            or not isinstance(event_id, str)
            or not event_id
            or event_ids != [event_id, event_id, event_id]
        ):
            failures.append(f"exec_{offset + 1}_event_id_mismatch")
        if len(group_events) == 3:
            first_time = group_events[0].get("timeNano")
            if isinstance(first_time, int) and first_time < ready_wall_ns:
                failures.append(f"exec_{offset + 1}_event_before_ready_observation")
            die_attributes = ((group_events[2].get("Actor") or {}).get("Attributes") or {})
            if die_attributes.get("exitCode") != "0":
                failures.append(f"exec_{offset + 1}_event_nonzero")
        exec_groups.append(
            {
                "ordinal": item["ordinal"],
                "out_path": item["out_path"],
                "evidence_file": item["evidence_file"],
                "exec_id": event_id,
            }
        )

    if len(events) >= 2:
        kill_attributes = ((events[-2].get("Actor") or {}).get("Attributes") or {})
        die_attributes = ((events[-1].get("Actor") or {}).get("Attributes") or {})
        if kill_attributes.get("signal") != "15":
            failures.append("termination_event_not_sigterm")
        if die_attributes.get("exitCode") != str(supervisor_exit_code):
            failures.append("container_die_exit_code_mismatch")

    return {
        "schema": "WAVE025_POST_OBSERVATION_EXTRACTION_AUDIT_V1",
        "valid": not failures,
        "failures": sorted(set(failures)),
        "ready_frame_sha256": sha256_bytes(ready_receipt.stdout),
        "ready_observed_at": ready_receipt.finished_at,
        "ready_observed_monotonic_ns": ready_receipt.monotonic_finish_ns,
        "registered_exec_count": len(extraction_receipts),
        "daemon_event_count": len(events),
        "daemon_event_actions": actions,
        "exec_groups": exec_groups,
    }


def create_d0_predecessor(
    client: DockerClient,
    batch_id: str,
    slot: dict[str, Any],
    image_id: str,
    residue_root: Path,
    journal_dir: Path,
) -> list[dict[str, Any]]:
    name = role_free_container_name(batch_id, slot["opaque_slot_id"], "p")
    marker_basename = slot["private_canary_token_or_null"]
    validate_d0_residue_before_predecessor(residue_root)
    receipts: list[dict[str, Any]] = []
    sequence = 1
    create_receipt = record_command(
        client,
        predecessor_arguments(
            name,
            batch_id,
            slot["opaque_slot_id"],
            image_id,
            residue_root,
            marker_basename,
        ),
        journal_dir,
        sequence,
        "predecessor-create",
    )
    receipts.append(create_receipt.as_json())
    if create_receipt.returncode != 0:
        raise RunnerError("D0 predecessor docker create failed")
    sequence += 1
    pre_inspect = record_command(
        client, ["inspect", name], journal_dir, sequence, "predecessor-inspect-pre"
    )
    receipts.append(pre_inspect.as_json())
    if pre_inspect.returncode != 0:
        raise RunnerError("D0 predecessor pre-inspect failed")
    sequence += 1
    start_receipt = record_command(
        client, ["start", "-a", name], journal_dir, sequence, "predecessor-start"
    )
    receipts.append(start_receipt.as_json())
    sequence += 1
    post_inspect = record_command(
        client, ["inspect", name], journal_dir, sequence, "predecessor-inspect-post"
    )
    receipts.append(post_inspect.as_json())
    if post_inspect.returncode != 0:
        raise RunnerError("D0 predecessor post-inspect failed")
    post_value = one_inspect(post_inspect.stdout, "D0 predecessor inspect post")
    if start_receipt.returncode != 0 or (post_value.get("State") or {}).get("ExitCode") != 0:
        raise RunnerError("D0 predecessor did not complete successfully")
    validate_d0_residue_after_predecessor(residue_root, marker_basename)
    sequence += 1
    sequence, cleanup = clean_exact_container(
        client,
        name,
        batch_id,
        slot["opaque_slot_id"],
        journal_dir,
        sequence,
    )
    receipts.extend(cleanup)
    return receipts


def run_slot(
    client: DockerClient,
    batch_root: Path,
    runtime_root: Path,
    challenge_root: Path,
    slot: dict[str, Any],
    execution_index: int,
    precommit: dict[str, Any],
    docker_version_receipt: CommandReceipt,
    control_instances: dict[str, dict[str, str]],
) -> dict[str, Any]:
    slot_id, challenge = slot["opaque_slot_id"], slot["challenge"]
    if not OPAQUE_ID.fullmatch(slot_id):
        raise RunnerError(f"invalid opaque slot id: {slot_id}")
    slot_dir = batch_root / "slots" / slot_id
    if slot_dir.exists():
        raise RunnerError(f"slot directory already exists; no overwrite/retry: {slot_id}")
    mkdir_exclusive(slot_dir, 0o700)
    attempt_root = runtime_root / "attempts"
    if not attempt_root.exists():
        mkdir_exclusive(attempt_root, 0o700)
    journal_dir = attempt_root / slot_id
    mkdir_exclusive(journal_dir, 0o700)

    residue_root: Path | None = None
    predecessor_receipts: list[dict[str, Any]] = []
    d0_before: dict[str, Any] | None = None
    d0_after_predecessor: dict[str, Any] | None = None
    if challenge == "D0-HOST-LEAK":
        residues = runtime_root / "d0-residues"
        if not residues.exists():
            mkdir_exclusive(residues, 0o700)
        residue_root = residues / slot_id
        mkdir_exclusive(residue_root, 0o777)
        os.chmod(residue_root, 0o777)
        d0_before = d0_residue_snapshot(residue_root)
        predecessor_journal = journal_dir / "predecessor"
        mkdir_exclusive(predecessor_journal, 0o700)
        predecessor_receipts = create_d0_predecessor(
            client,
            precommit["batch_id"],
            slot,
            precommit["collector_image_id"],
            residue_root,
            predecessor_journal,
        )
        os.chmod(residue_root, 0o555)
        d0_after_predecessor = d0_residue_snapshot(residue_root)

    name = role_free_container_name(precommit["batch_id"], slot_id, "c")
    hostname = f"w025-{slot_id[2:18]}"
    command_receipts: list[dict[str, Any]] = []
    sequence = 1
    create_receipt = record_command(
        client,
        baseline_create_arguments(
            name,
            precommit["batch_id"],
            slot_id,
            precommit["collector_image_id"],
            challenge_root,
            hostname,
            challenge,
            residue_root,
        ),
        journal_dir,
        sequence,
        "candidate-create",
    )
    command_receipts.append(create_receipt.as_json())
    if create_receipt.returncode != 0:
        raise RunnerError(f"candidate docker create failed for {slot_id}")
    sequence += 1

    inspect_pre_receipt = record_command(
        client, ["inspect", name], journal_dir, sequence, "candidate-inspect-pre"
    )
    command_receipts.append(inspect_pre_receipt.as_json())
    if inspect_pre_receipt.returncode != 0:
        raise RunnerError(f"candidate pre-inspect failed for {slot_id}")
    exclusive_write(slot_dir / "docker-inspect-pre.json", inspect_pre_receipt.stdout, 0o600)
    inspect_pre = one_inspect(inspect_pre_receipt.stdout, "docker inspect pre")
    if inspect_pre.get("Image") != precommit["collector_image_id"]:
        raise RunnerError("actual candidate image differs from precommit before start")
    sequence += 1

    start_receipt = record_command(
        client, ["start", name], journal_dir, sequence, "candidate-start-detached", timeout=30
    )
    command_receipts.append(start_receipt.as_json())
    if start_receipt.returncode != 0:
        raise RunnerError(f"candidate start failed for {slot_id}")
    sequence += 1

    control_receipt: CommandReceipt | None = None
    for poll in range(1, 61):
        control_receipt = record_command(
            client,
            ["logs", name],
            journal_dir,
            sequence,
            f"candidate-control-logs-{poll:03d}",
            timeout=10,
        )
        command_receipts.append(control_receipt.as_json())
        sequence += 1
        if (
            control_receipt.returncode == 0
            and control_receipt.stdout == SUPERVISOR_READY_FRAME
            and control_receipt.stderr == b""
        ):
            break
        time.sleep(0.05)
    if control_receipt is None:
        raise RunnerError("internal error: ready polling produced no command receipt")
    control_stdout = control_receipt.stdout
    control_stderr = control_receipt.stderr
    ready_frame_observed = (
        control_receipt.returncode == 0
        and control_stdout == SUPERVISOR_READY_FRAME
        and control_stderr == b""
    )

    running_inspect_receipt = record_command(
        client, ["inspect", name], journal_dir, sequence, "candidate-inspect-ready-running"
    )
    command_receipts.append(running_inspect_receipt.as_json())
    sequence += 1
    running_at_ready = False
    if running_inspect_receipt.returncode == 0:
        running_value = one_inspect(running_inspect_receipt.stdout, "docker inspect at ready")
        running_at_ready = bool((running_value.get("State") or {}).get("Running"))

    extracted_bytes = {item["evidence_file"]: b"" for item in EXTRACTION_READS}
    extraction_receipts: list[CommandReceipt] = []
    if ready_frame_observed and running_at_ready:
        for item in EXTRACTION_READS:
            extraction_receipt = record_command(
                client,
                [
                    "exec",
                    "--user",
                    "65534:65534",
                    name,
                    "/bin/cat",
                    item["out_path"],
                ],
                journal_dir,
                sequence,
                f"candidate-extract-{item['ordinal']:02d}",
                timeout=30,
            )
            extraction_receipts.append(extraction_receipt)
            command_receipts.append(extraction_receipt.as_json())
            extracted_bytes[item["evidence_file"]] = extraction_receipt.stdout
            sequence += 1

    term_receipt = record_command(
        client,
        ["kill", "--signal", "TERM", name],
        journal_dir,
        sequence,
        "candidate-term",
        timeout=30,
    )
    command_receipts.append(term_receipt.as_json())
    sequence += 1
    wait_receipt = record_command(
        client, ["wait", name], journal_dir, sequence, "candidate-wait", timeout=30
    )
    command_receipts.append(wait_receipt.as_json())
    sequence += 1

    inspect_post_receipt = record_command(
        client, ["inspect", name], journal_dir, sequence, "candidate-inspect-post"
    )
    command_receipts.append(inspect_post_receipt.as_json())
    if inspect_post_receipt.returncode != 0:
        raise RunnerError(f"candidate post-inspect failed for {slot_id}")
    exclusive_write(slot_dir / "docker-inspect-post.json", inspect_post_receipt.stdout, 0o600)
    inspect_post = one_inspect(inspect_post_receipt.stdout, "docker inspect post")
    sequence += 1

    container_id = inspect_pre.get("Id")
    if not isinstance(container_id, str) or not container_id:
        raise RunnerError("candidate pre-inspect lacks container Id")
    created_at = inspect_pre.get("Created")
    if not isinstance(created_at, str) or not created_at:
        raise RunnerError("candidate pre-inspect lacks Created timestamp")
    events_until = (
        datetime.now(timezone.utc) + timedelta(milliseconds=250)
    ).isoformat(timespec="microseconds").replace("+00:00", "Z")
    events_receipt = record_command(
        client,
        [
            "events",
            "--since",
            created_at,
            "--until",
            events_until,
            "--filter",
            f"container={container_id}",
            "--format",
            "{{json .}}",
        ],
        journal_dir,
        sequence,
        "candidate-events",
        timeout=30,
    )
    command_receipts.append(events_receipt.as_json())
    sequence += 1

    collector_stdout = extracted_bytes["collector-stdout.bin"]
    collector_stderr = extracted_bytes["collector-stderr.bin"]
    out_bytes = extracted_bytes["collector-out.bin"]
    ready_bytes = extracted_bytes["collector-ready.bin"]
    collector_exit_bytes = extracted_bytes["collector-exit-code.bin"]
    exclusive_write(slot_dir / "collector-stdout.bin", collector_stdout, 0o600)
    exclusive_write(slot_dir / "collector-stderr.bin", collector_stderr, 0o600)
    exclusive_write(slot_dir / "collector-out.bin", out_bytes, 0o600)
    exclusive_write(slot_dir / "collector-ready.bin", ready_bytes, 0o600)
    exclusive_write(slot_dir / "collector-exit-code.bin", collector_exit_bytes, 0o600)
    exclusive_write(slot_dir / "supervisor-control-stdout.bin", control_stdout, 0o600)
    exclusive_write(slot_dir / "supervisor-control-stderr.bin", control_stderr, 0o600)
    exclusive_write(slot_dir / "docker-events.jsonl", events_receipt.stdout, 0o600)

    supervisor_exit_code = (inspect_post.get("State") or {}).get("ExitCode")
    extraction_audit = audit_docker_events(
        events_receipt.stdout,
        container_id,
        name,
        control_receipt,
        extraction_receipts,
        supervisor_exit_code,
    )
    if events_receipt.returncode != 0:
        extraction_audit["valid"] = False
        extraction_audit["failures"] = sorted(
            set([*extraction_audit["failures"], "docker_events_command_nonzero"])
        )
    if events_receipt.stderr != b"":
        extraction_audit["valid"] = False
        extraction_audit["failures"] = sorted(
            set([*extraction_audit["failures"], "docker_events_command_stderr_nonempty"])
        )

    control_audit = audit_registered_control_receipt(
        challenge,
        slot["private_canary_token_or_null"],
        out_bytes,
        inspect_pre,
        residue_root,
        precommit,
        control_instances,
    )
    private_predecessor_commitment: dict[str, Any] | None = None
    if challenge == "D0-HOST-LEAK":
        if d0_before is None or d0_after_predecessor is None or residue_root is None:
            raise RunnerError("D0 private provenance snapshots are incomplete")
        d0_after_candidate = d0_residue_snapshot(residue_root)
        private_provenance = {
            "schema": SCHEMA_D0_PRIVATE_PROVENANCE,
            "opaque_slot_id": slot_id,
            "family_id": control_audit["family_id_or_null"],
            "registered_marker_basename": slot["private_canary_token_or_null"],
            "before_predecessor": d0_before,
            "predecessor_exact_command_receipts": predecessor_receipts,
            "after_predecessor_before_candidate": d0_after_predecessor,
            "after_candidate": d0_after_candidate,
        }
        private_provenance_raw = exclusive_json(
            journal_dir / "d0-private-provenance.json", private_provenance, 0o600
        )
        private_predecessor_commitment = {
            "schema": SCHEMA_D0_PRIVATE_PROVENANCE_COMMITMENT,
            "opaque_slot_id": slot_id,
            "private_provenance_sha256": sha256_bytes(private_provenance_raw),
            "private_provenance_byte_length": len(private_provenance_raw),
            "predecessor_command_receipt_count": len(predecessor_receipts),
            "before_entry_count": d0_before["entry_count"],
            "after_predecessor_entry_count": d0_after_predecessor["entry_count"],
            "after_candidate_entry_count": d0_after_candidate["entry_count"],
            "private_instance_disclosed": False,
        }

    host_launch, configuration_failures = derive_host_launch(
        slot_id,
        challenge,
        inspect_pre,
        inspect_post,
        precommit,
        docker_version_receipt,
        command_receipts,
        extraction_audit,
        control_audit,
        private_predecessor_commitment,
    )
    host_raw = exclusive_json(slot_dir / "host-launch.json", host_launch, 0o600)
    collector_exit_code: int | None = None
    if re.fullmatch(rb"[0-9]{1,3}\n", collector_exit_bytes):
        collector_exit_code = int(collector_exit_bytes.strip())
    supervisor_protocol_valid = (
        ready_frame_observed
        and ready_bytes == b"READY\n"
        and running_at_ready
        and collector_exit_code is not None
        and len(extraction_receipts) == len(EXTRACTION_READS)
        and all(item.returncode == 0 and item.stderr == b"" for item in extraction_receipts)
        and extraction_audit["valid"]
        and term_receipt.returncode == 0
        and wait_receipt.returncode == 0
        and supervisor_exit_code == collector_exit_code
    )
    valid_collector = collector_bytes_are_valid(
        collector_stdout, collector_stderr, out_bytes, collector_exit_code
    )
    feature_raw: bytes | None = None
    if valid_collector:
        exclusive_write(slot_dir / "collector-features.json", out_bytes, 0o600)
        feature_raw = out_bytes

    if configuration_failures:
        classification = "HOST_CONFIGURATION_MISMATCH"
    elif not extraction_audit["valid"]:
        classification = "POST_OBSERVATION_EVENT_AUDIT_MISMATCH"
    elif not control_audit["valid"]:
        classification = "CONTROL_INTEGRITY_MISMATCH"
    elif not supervisor_protocol_valid:
        classification = "SUPERVISOR_PROTOCOL_MISMATCH"
    elif collector_exit_code != 0:
        classification = "COLLECTOR_FAILURE"
    elif not valid_collector:
        classification = "COLLECTOR_CHANNEL_OR_SCHEMA_MISMATCH"
    else:
        classification = "COMPLETE"
    files = {
        "host-launch.json": sha256_bytes(host_raw),
        "docker-inspect-pre.json": sha256_bytes(inspect_pre_receipt.stdout),
        "docker-inspect-post.json": sha256_bytes(inspect_post_receipt.stdout),
        "docker-events.jsonl": sha256_bytes(events_receipt.stdout),
        "collector-stdout.bin": sha256_bytes(collector_stdout),
        "collector-stderr.bin": sha256_bytes(collector_stderr),
        "collector-out.bin": sha256_bytes(out_bytes),
        "collector-ready.bin": sha256_bytes(ready_bytes),
        "collector-exit-code.bin": sha256_bytes(collector_exit_bytes),
        "supervisor-control-stdout.bin": sha256_bytes(control_stdout),
        "supervisor-control-stderr.bin": sha256_bytes(control_stderr),
        "collector-features.json": sha256_bytes(feature_raw) if feature_raw is not None else None,
    }
    receipt = {
        "schema": SCHEMA_SLOT_RECEIPT,
        "opaque_slot_id": slot_id,
        "challenge": challenge,
        "attempt_count": 1,
        "execution_index": execution_index,
        "exit_code": supervisor_exit_code,
        "collector_exit_code": collector_exit_code,
        "infrastructure_classification": classification,
        "files": files,
        "host_started_at": start_receipt.started_at,
        "host_finished_at": inspect_post_receipt.finished_at,
        "host_monotonic_start_ns": start_receipt.monotonic_start_ns,
        "host_monotonic_finish_ns": inspect_post_receipt.monotonic_finish_ns,
    }
    sequence += 1
    sequence, cleanup_receipts = clean_exact_container(
        client,
        name,
        precommit["batch_id"],
        slot_id,
        journal_dir,
        sequence,
    )
    # A slot is not terminal evidence until its exact owned, stopped container
    # has been removed.  Cleanup failure therefore leaves raw evidence but no
    # slot receipt, forcing close to ABORT rather than claiming completion.
    slot_receipt_raw = exclusive_json(slot_dir / "slot-receipt.json", receipt, 0o600)
    # Cleanup receipts remain in the host-only attempt journal.  The immutable
    # host-launch preimage intentionally ends at stopped-container observation.
    return {
        "opaque_slot_id": slot_id,
        "challenge": challenge,
        "execution_index": execution_index,
        "infrastructure_classification": classification,
        "slot_receipt_sha256": sha256_bytes(slot_receipt_raw),
        "cleanup_command_count": len(cleanup_receipts),
    }


def run_batch(args: argparse.Namespace) -> dict[str, Any]:
    batch_root = validate_batch_root(Path(args.batch_dir), must_exist=True)
    precommit, public_plan, private_state = validate_frozen_inputs(batch_root)
    validate_anchor(batch_root, precommit)
    for forbidden in ("closed.json", "reveal.json", "evaluation.json"):
        if (batch_root / forbidden).exists():
            raise RunnerError(f"cannot run after {forbidden} exists")
    if precommit["mode"] == "formal" and public_plan["slot_count"] != 3200:
        raise RunnerError("formal default must contain exactly 3200 slots")

    mapping = {item["opaque_slot_id"]: item for item in private_state["mapping"]}
    control_instances = control_instances_from_private_registry(
        private_state["private_control_registry"]
    )
    public_slots = {item["opaque_slot_id"]: item["challenge"] for item in public_plan["slots"]}
    if set(mapping) != set(public_slots):
        raise RunnerError("private/public slot population mismatch")
    for slot_id, item in mapping.items():
        if public_slots[slot_id] != item["challenge"]:
            raise RunnerError("private/public challenge mismatch")

    runtime_root, templates = prepare_runtime_templates(batch_root, private_state)
    docker = DockerClient(args.docker_bin)
    image, _ = inspect_image(docker, precommit["collector_image_id"])
    if image.get("Id") != precommit["collector_image_id"]:
        raise RunnerError("resolved collector image changed before run")
    version_receipt = docker.require(["version", "--format", "{{json .}}"], "version")

    completed: list[dict[str, Any]] = []
    seen_missing = False
    for execution_index, slot_id in enumerate(private_state["execution_order"], 1):
        receipt_path = batch_root / "slots" / slot_id / "slot-receipt.json"
        if receipt_path.exists():
            if seen_missing:
                raise RunnerError("existing slot receipts are not an execution-order prefix")
            receipt, _ = read_json(receipt_path, SCHEMA_SLOT_RECEIPT)
            if receipt["execution_index"] != execution_index:
                raise RunnerError("existing execution index differs from sealed order")
            completed.append(
                {
                    "opaque_slot_id": slot_id,
                    "challenge": receipt["challenge"],
                    "execution_index": execution_index,
                    "infrastructure_classification": receipt["infrastructure_classification"],
                    "slot_receipt_sha256": sha256_file(receipt_path),
                    "resumed_existing": True,
                }
            )
            continue
        seen_missing = True
        validate_runtime_template(
            templates[slot_id],
            mapping[slot_id]["challenge"],
            mapping[slot_id]["private_canary_token_or_null"],
        )
        completed.append(
            run_slot(
                docker,
                batch_root,
                runtime_root,
                templates[slot_id],
                mapping[slot_id],
                execution_index,
                precommit,
                version_receipt,
                control_instances,
            )
        )
    return {
        "command": "run",
        "state": "RUNNING_COMPLETE_NOT_CLOSED",
        "batch_id": precommit["batch_id"],
        "slot_count": len(completed),
        "infrastructure_counts": count_values(
            item["infrastructure_classification"] for item in completed
        ),
        "next": "close",
    }


def count_values(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return {key: result[key] for key in sorted(result)}


SLOT_FILES = [
    "host-launch.json",
    "docker-inspect-pre.json",
    "docker-inspect-post.json",
    "docker-events.jsonl",
    "collector-stdout.bin",
    "collector-stderr.bin",
    "collector-out.bin",
    "collector-ready.bin",
    "collector-exit-code.bin",
    "supervisor-control-stdout.bin",
    "supervisor-control-stderr.bin",
    "collector-features.json",
]


def merkle_root_hex(leaves: list[str]) -> str | None:
    if not leaves:
        return None
    level = [bytes.fromhex(ensure_sha256(item, "Merkle leaf")) for item in leaves]
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


def docker_daemon_document(client: DockerClient) -> tuple[dict[str, Any], bool]:
    receipt = client.call(["version", "--format", "{{json .}}"])
    parsed: Any = None
    if receipt.returncode == 0:
        try:
            parsed = parse_json_bytes(receipt.stdout, "docker version")
        except RunnerError:
            parsed = None
    server = parsed.get("Server") if isinstance(parsed, dict) else None
    client_value = parsed.get("Client") if isinstance(parsed, dict) else None
    document = {
        "available": receipt.returncode == 0 and isinstance(server, dict),
        "client_version": (client_value or {}).get("Version") if isinstance(client_value, dict) else None,
        "server_version": (server or {}).get("Version") if isinstance(server, dict) else None,
        "api_version": (server or {}).get("ApiVersion") if isinstance(server, dict) else None,
        "os": (server or {}).get("Os") if isinstance(server, dict) else None,
        "arch": (server or {}).get("Arch") if isinstance(server, dict) else None,
        "raw_stdout_sha256": sha256_bytes(receipt.stdout),
        "raw_stderr_sha256": sha256_bytes(receipt.stderr),
        "returncode": receipt.returncode,
        "diagnostics": {"schema": "WAVE025_RUNNER_DIAGNOSTICS_V1", "command": receipt.as_json()},
    }
    return document, bool(document["available"])


def decode_exact_command_receipt(
    value: Any, label: str
) -> tuple[list[str], bytes, bytes, int, int]:
    fields = {
        "schema", "command", "started_at", "finished_at", "monotonic_start_ns",
        "monotonic_finish_ns", "returncode", "stdout_base64", "stderr_base64",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise RunnerError(f"{label} command receipt fields mismatch")
    if value["schema"] != SCHEMA_COMMAND:
        raise RunnerError(f"{label} command receipt schema mismatch")
    command = value["command"]
    if not isinstance(command, list) or not command or not all(
        isinstance(item, str) for item in command
    ):
        raise RunnerError(f"{label} command receipt argv mismatch")
    if type(value["returncode"]) is not int:
        raise RunnerError(f"{label} command receipt returncode mismatch")
    start_ns = value["monotonic_start_ns"]
    finish_ns = value["monotonic_finish_ns"]
    if (
        type(start_ns) is not int
        or type(finish_ns) is not int
        or start_ns < 0
        or finish_ns < start_ns
    ):
        raise RunnerError(f"{label} command receipt monotonic interval mismatch")
    if not isinstance(value["started_at"], str) or not isinstance(value["finished_at"], str):
        raise RunnerError(f"{label} command receipt timestamp type mismatch")
    if rfc3339_epoch_ns(value["finished_at"], f"{label} finished_at") < rfc3339_epoch_ns(
        value["started_at"], f"{label} started_at"
    ):
        raise RunnerError(f"{label} command receipt wall interval mismatch")
    if not isinstance(value["stdout_base64"], str) or not isinstance(
        value["stderr_base64"], str
    ):
        raise RunnerError(f"{label} command receipt base64 type mismatch")
    try:
        stdout = base64.b64decode(value["stdout_base64"], validate=True)
        stderr = base64.b64decode(value["stderr_base64"], validate=True)
    except (TypeError, ValueError) as error:
        raise RunnerError(f"{label} command receipt base64 mismatch") from error
    return command, stdout, stderr, start_ns, finish_ns


def validate_predecessor_inspect(
    raw: bytes,
    label: str,
    expected_name: str,
    expected_batch_id: str,
    expected_slot_id: str,
    expected_image_id: str,
    expected_residue_root: Path,
    expected_marker: str,
    completed: bool,
) -> str:
    inspect_value = one_inspect(raw, label)
    if str(inspect_value.get("Name") or "").lstrip("/") != expected_name:
        raise RunnerError(f"{label} predecessor name mismatch")
    labels = (inspect_value.get("Config") or {}).get("Labels") or {}
    if labels != {
        "org.towow.wave025.batch": expected_batch_id,
        "org.towow.wave025.slot": expected_slot_id,
        "org.towow.wave025.owner": "runner-v1-predecessor",
    }:
        raise RunnerError(f"{label} predecessor ownership labels mismatch")
    if inspect_value.get("Image") != expected_image_id:
        raise RunnerError(f"{label} predecessor image mismatch")
    config = inspect_value.get("Config") or {}
    if config.get("Entrypoint") != ["/bin/sh"]:
        raise RunnerError(f"{label} predecessor entrypoint mismatch")
    if config.get("Cmd") != [
        "-c",
        'set -eu; umask 077; : > "/shared-residue/$1"; chmod 0400 "/shared-residue/$1"; sync',
        "wave025-predecessor",
        expected_marker,
    ]:
        raise RunnerError(f"{label} predecessor command mismatch")
    if config.get("User") != "65534:65534":
        raise RunnerError(f"{label} predecessor user mismatch")
    mounts = inspect_value.get("Mounts") or []
    if len(mounts) != 1:
        raise RunnerError(f"{label} predecessor mount count mismatch")
    mount = mounts[0]
    if (
        mount.get("Type") != "bind"
        or Path(str(mount.get("Source"))).resolve() != expected_residue_root.resolve()
        or mount.get("Destination") != "/shared-residue"
        or mount.get("RW") is not True
    ):
        raise RunnerError(f"{label} predecessor residue mount mismatch")
    host = inspect_value.get("HostConfig") or {}
    if (
        host.get("NetworkMode") != "none"
        or host.get("ReadonlyRootfs") is not True
        or "ALL" not in [str(item).upper() for item in (host.get("CapDrop") or [])]
        or not any("no-new-privileges" in str(item) for item in (host.get("SecurityOpt") or []))
        or host.get("PidsLimit") != 16
        or host.get("Memory") != 67108864
        or host.get("NanoCpus") != 250000000
    ):
        raise RunnerError(f"{label} predecessor host isolation mismatch")
    state = inspect_value.get("State") or {}
    if (
        state.get("Running") is not False
        or state.get("ExitCode") != 0
        or state.get("OOMKilled") is not False
        or state.get("Error") not in {None, ""}
    ):
        raise RunnerError(f"{label} predecessor state mismatch")
    if completed:
        if state.get("StartedAt") in {None, "", "0001-01-01T00:00:00Z"}:
            raise RunnerError(f"{label} predecessor never started")
        if state.get("FinishedAt") in {None, "", "0001-01-01T00:00:00Z"}:
            raise RunnerError(f"{label} predecessor never finished")
    elif (
        state.get("StartedAt") not in {None, "", "0001-01-01T00:00:00Z"}
        or state.get("FinishedAt") not in {None, "", "0001-01-01T00:00:00Z"}
    ):
        raise RunnerError(f"{label} predecessor pre-inspect is not pre-start")
    container_id = inspect_value.get("Id")
    if not isinstance(container_id, str) or not container_id:
        raise RunnerError(f"{label} predecessor container id missing")
    return container_id


def validate_d0_private_provenance(
    value: dict[str, Any],
    slot: dict[str, Any],
    precommit: dict[str, Any],
    batch_root: Path,
) -> None:
    marker = slot["private_canary_token_or_null"]
    family_id = next(
        (
            family["family_id"]
            for family in precommit["private_control_registry_commitment"]["family_hashes"]
            if family["challenge"] == "D0-HOST-LEAK"
        ),
        None,
    )
    if value.get("opaque_slot_id") != slot["opaque_slot_id"]:
        raise RunnerError("D0 private provenance slot mismatch")
    if value.get("family_id") != family_id:
        raise RunnerError("D0 private provenance family mismatch")
    if value.get("registered_marker_basename") != marker:
        raise RunnerError("D0 private provenance marker mismatch")
    before = value.get("before_predecessor")
    after_predecessor = value.get("after_predecessor_before_candidate")
    after_candidate = value.get("after_candidate")
    if (
        not isinstance(before, dict)
        or before.get("directory_mode_octal") != "0o0777"
        or before.get("entry_count") != 0
        or before.get("entries") != []
    ):
        raise RunnerError("D0 private provenance does not prove an empty pre-state")
    expected_entry = {
        "basename": marker,
        "type": "file",
        "size_bytes": 0,
        "mode_octal": "0o0400",
        "content_sha256_or_null": sha256_bytes(b""),
    }
    for label, snapshot in (
        ("after predecessor", after_predecessor),
        ("after candidate", after_candidate),
    ):
        if (
            not isinstance(snapshot, dict)
            or snapshot.get("directory_mode_octal") != "0o0555"
            or snapshot.get("entry_count") != 1
            or snapshot.get("entries") != [expected_entry]
        ):
            raise RunnerError(f"D0 private provenance {label} snapshot mismatch")
    receipts = value.get("predecessor_exact_command_receipts")
    if not isinstance(receipts, list) or len(receipts) != 6:
        raise RunnerError("D0 private provenance requires exactly six predecessor receipts")
    decoded = [
        decode_exact_command_receipt(receipt, f"D0 predecessor receipt {index}")
        for index, receipt in enumerate(receipts, 1)
    ]
    if any(receipt[2] != b"" or receipts[index]["returncode"] != 0 for index, receipt in enumerate(decoded)):
        raise RunnerError("D0 predecessor command failed or wrote stderr")
    for left, right in zip(decoded, decoded[1:]):
        if left[4] > right[3]:
            raise RunnerError("D0 predecessor receipt order/monotonic intervals overlap")
    slot_id = slot["opaque_slot_id"]
    name = role_free_container_name(precommit["batch_id"], slot_id, "p")
    residue_root = Path(str(batch_root) + ".runtime") / "d0-residues" / slot_id
    docker_binary = decoded[0][0][0]
    expected_commands = [
        [docker_binary, *predecessor_arguments(
            name, precommit["batch_id"], slot_id, precommit["collector_image_id"],
            residue_root, marker,
        )],
        [docker_binary, "inspect", name],
        [docker_binary, "start", "-a", name],
        [docker_binary, "inspect", name],
        [docker_binary, "inspect", name],
        [docker_binary, "rm", name],
    ]
    if [item[0] for item in decoded] != expected_commands:
        raise RunnerError("D0 predecessor exact command sequence mismatch")
    create_stdout = decoded[0][1]
    pre_id = validate_predecessor_inspect(
        decoded[1][1], "D0 predecessor pre-inspect", name, precommit["batch_id"],
        slot_id, precommit["collector_image_id"], residue_root, marker, False,
    )
    post_id = validate_predecessor_inspect(
        decoded[3][1], "D0 predecessor post-inspect", name, precommit["batch_id"],
        slot_id, precommit["collector_image_id"], residue_root, marker, True,
    )
    cleanup_id = validate_predecessor_inspect(
        decoded[4][1], "D0 predecessor cleanup-inspect", name, precommit["batch_id"],
        slot_id, precommit["collector_image_id"], residue_root, marker, True,
    )
    if pre_id != post_id or pre_id != cleanup_id:
        raise RunnerError("D0 predecessor inspect container identity changed")
    if create_stdout != (pre_id + "\n").encode("utf-8"):
        raise RunnerError("D0 predecessor create stdout does not bind inspect id")
    if decoded[2][1] != b"":
        raise RunnerError("D0 predecessor start emitted unexpected stdout")
    if decoded[5][1] != (name + "\n").encode("utf-8"):
        raise RunnerError("D0 predecessor rm stdout mismatch")
    if after_predecessor != after_candidate:
        raise RunnerError("D0 residue snapshot changed during candidate execution")


def load_d0_private_provenance(
    batch_root: Path,
    private_state: dict[str, Any],
    precommit: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    runtime_root = Path(str(batch_root) + ".runtime")
    documents: list[dict[str, Any]] = []
    commitments: list[dict[str, Any]] = []
    d0_slots = sorted(
        (
            item for item in private_state["mapping"]
            if item["challenge"] == "D0-HOST-LEAK"
        ),
        key=lambda item: item["opaque_slot_id"],
    )
    for slot in d0_slots:
        path = (
            runtime_root / "attempts" / slot["opaque_slot_id"]
            / "d0-private-provenance.json"
        )
        if not path.is_file() or path.is_symlink():
            raise RunnerError(f"missing D0 private provenance for {slot['opaque_slot_id']}")
        value, raw = read_json(path, SCHEMA_D0_PRIVATE_PROVENANCE)
        assert_regular_file(path, 0o600)
        validate_d0_private_provenance(value, slot, precommit, batch_root)
        host_launch, _ = read_json(
            batch_root / "slots" / slot["opaque_slot_id"] / "host-launch.json",
            SCHEMA_HOST_LAUNCH,
        )
        commitment = {
            "schema": SCHEMA_D0_PRIVATE_PROVENANCE_COMMITMENT,
            "opaque_slot_id": slot["opaque_slot_id"],
            "private_provenance_sha256": sha256_bytes(raw),
            "private_provenance_byte_length": len(raw),
            "predecessor_command_receipt_count": len(
                value["predecessor_exact_command_receipts"]
            ),
            "before_entry_count": value["before_predecessor"]["entry_count"],
            "after_predecessor_entry_count": value[
                "after_predecessor_before_candidate"
            ]["entry_count"],
            "after_candidate_entry_count": value["after_candidate"]["entry_count"],
            "private_instance_disclosed": False,
        }
        host_commitment = ((host_launch.get("diagnostics") or {}).get(
            "private_predecessor_provenance_commitment_or_null"
        ))
        if host_commitment != commitment:
            raise RunnerError("D0 host-launch/private provenance commitment mismatch")
        documents.append(value)
        commitments.append(commitment)
    aggregate = {
        "schema": "WAVE025_D0_PRIVATE_PROVENANCE_SET_COMMITMENT_V1",
        "expected_d0_slot_count": len(d0_slots),
        "entries": commitments,
        "merkle_root": merkle_root_hex(
            [item["private_provenance_sha256"] for item in commitments]
        ),
    }
    return documents, aggregate


def close_batch(args: argparse.Namespace) -> dict[str, Any]:
    batch_root = validate_batch_root(Path(args.batch_dir), must_exist=True)
    precommit, public_plan, private_state = validate_frozen_inputs(batch_root)
    validate_anchor(batch_root, precommit)
    if (batch_root / "closed.json").exists():
        raise RunnerError("closed.json already exists and will not be overwritten")
    if (batch_root / "reveal.json").exists() or (batch_root / "evaluation.json").exists():
        raise RunnerError("reveal/evaluation exists before close")

    expected = {item["opaque_slot_id"]: item["challenge"] for item in public_plan["slots"]}
    slots_root = batch_root / "slots"
    actual_entries = sorted(item.name for item in slots_root.iterdir())
    unexpected = [name for name in actual_entries if name not in expected]
    summaries: list[dict[str, Any]] = []
    receipt_leaves: list[str] = []
    complete = not unexpected and len(actual_entries) == len(expected)
    first_time: str | None = None
    last_time: str | None = None

    for slot_id, challenge in sorted(expected.items()):
        slot_dir = slots_root / slot_id
        summary: dict[str, Any] = {
            "opaque_slot_id": slot_id,
            "challenge": challenge,
            "attempt_count": 0,
            "status": "MISSING_SLOT_DIRECTORY",
            "files": {name: None for name in [*SLOT_FILES, "slot-receipt.json"]},
        }
        if not slot_dir.is_dir() or slot_dir.is_symlink():
            complete = False
            summaries.append(summary)
            continue
        names = sorted(item.name for item in slot_dir.iterdir())
        allowed_names = set(SLOT_FILES) | {"slot-receipt.json"}
        if any(name not in allowed_names for name in names):
            summary["status"] = "UNEXPECTED_SLOT_FILE"
            complete = False
            summaries.append(summary)
            continue
        receipt_path = slot_dir / "slot-receipt.json"
        if not receipt_path.is_file():
            summary["status"] = "MISSING_SLOT_RECEIPT"
            complete = False
            summaries.append(summary)
            continue
        try:
            receipt, receipt_raw = read_json(receipt_path, SCHEMA_SLOT_RECEIPT)
        except RunnerError:
            summary["status"] = "INVALID_SLOT_RECEIPT"
            complete = False
            summaries.append(summary)
            continue
        if "role" in canonical_bytes(receipt).decode("utf-8"):
            summary["status"] = "FORBIDDEN_ROLE_TEXT_IN_SLOT_RECEIPT"
            complete = False
            summaries.append(summary)
            continue
        hashes: dict[str, str | None] = {}
        for filename in SLOT_FILES:
            path = slot_dir / filename
            hashes[filename] = sha256_file(path) if path.is_file() and not path.is_symlink() else None
        hashes["slot-receipt.json"] = sha256_bytes(receipt_raw)
        receipt_hashes = receipt.get("files")
        valid_hashes = isinstance(receipt_hashes, dict) and all(
            receipt_hashes.get(filename) == hashes[filename] for filename in SLOT_FILES
        )
        status = "COMPLETE"
        if receipt.get("opaque_slot_id") != slot_id or receipt.get("challenge") != challenge:
            status = "SLOT_BINDING_MISMATCH"
        elif not valid_hashes:
            status = "SLOT_FILE_HASH_MISMATCH"
        elif any(hashes[name] is None for name in SLOT_FILES):
            status = "MISSING_SLOT_FILE"
        elif receipt.get("infrastructure_classification") != "COMPLETE":
            status = str(receipt.get("infrastructure_classification") or "UNKNOWN_FAILURE")
        if status != "COMPLETE":
            complete = False
        else:
            receipt_leaves.append(sha256_bytes(receipt_raw))
        summary = {
            "opaque_slot_id": slot_id,
            "challenge": challenge,
            "attempt_count": receipt.get("attempt_count"),
            "execution_index": receipt.get("execution_index"),
            "status": status,
            "files": hashes,
        }
        started, finished = receipt.get("host_started_at"), receipt.get("host_finished_at")
        if isinstance(started, str):
            first_time = started if first_time is None or started < first_time else first_time
        if isinstance(finished, str):
            last_time = finished if last_time is None or finished > last_time else last_time
        summaries.append(summary)

    daemon, daemon_ok = docker_daemon_document(DockerClient(args.docker_bin))
    if not daemon_ok:
        complete = False
    try:
        _, private_provenance_commitment = load_d0_private_provenance(
            batch_root, private_state, precommit
        )
    except RunnerError as error:
        complete = False
        private_provenance_commitment = {
            "schema": "WAVE025_D0_PRIVATE_PROVENANCE_SET_COMMITMENT_V1",
            "expected_d0_slot_count": sum(
                item["challenge"] == "D0-HOST-LEAK"
                for item in private_state["mapping"]
            ),
            "entries": [],
            "merkle_root": None,
            "valid": False,
            "failure": str(error),
        }
    if len(receipt_leaves) != len(expected):
        complete = False
    status = "CLOSED" if complete else "ABORTED"
    document = {
        "schema": SCHEMA_CLOSED,
        "batch_id": precommit["batch_id"],
        "status": status,
        "closed_at": utc_now(),
        "expected_slot_count": len(expected),
        "actual_slot_directory_count": len(actual_entries),
        "unexpected_slot_entries": unexpected,
        "slots": summaries,
        "first_host_time": first_time,
        "last_host_time": last_time,
        "docker_daemon": daemon,
        "merkle_algorithm": "SHA256-PAIR-CONCAT-DUPLICATE-LAST-W025-V1",
        "batch_merkle_root": merkle_root_hex(receipt_leaves) if complete else None,
        "private_d0_provenance_commitment": private_provenance_commitment,
        "precommit_sha256": sha256_file(batch_root / "precommit.json"),
        "anchor_receipt_sha256": sha256_file(batch_root / "anchor-receipt.json"),
    }
    raw = exclusive_json(batch_root / "closed.json", document, 0o644)
    return {
        "command": "close",
        "state": status,
        "batch_id": precommit["batch_id"],
        "closed_sha256": sha256_bytes(raw),
        "expected_slots": len(expected),
        "complete_slots": len(receipt_leaves),
        "next": "reveal" if complete else "terminal ABORTED; do not reveal or rerun",
    }


def decode_domains(private_state: dict[str, Any]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    domains = private_state.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(DOMAINS):
        raise RunnerError("private domain set mismatch")
    seeds: dict[str, bytes] = {}
    nonces: dict[str, bytes] = {}
    for domain in DOMAINS:
        value = domains[domain]
        try:
            seeds[domain] = bytes.fromhex(value["seed_hex"])
            nonces[domain] = bytes.fromhex(value["nonce_hex"])
        except (KeyError, TypeError, ValueError) as error:
            raise RunnerError(f"invalid private bytes for {domain}") from error
        if len(seeds[domain]) != 32 or len(nonces[domain]) != 32:
            raise RunnerError(f"private seed/nonce for {domain} is not 32 bytes")
    return seeds, nonces


def strict_balance(mapping: list[dict[str, Any]]) -> bool:
    blocks: dict[str, list[str]] = {}
    for item in mapping:
        blocks.setdefault(item["block"], []).append(item["role"])
    return all(
        len(roles) % 2 == 0
        and roles.count("S") == len(roles) // 2
        and roles.count("R") == len(roles) // 2
        for roles in blocks.values()
    )


def reveal_batch(args: argparse.Namespace) -> dict[str, Any]:
    batch_root = validate_batch_root(Path(args.batch_dir), must_exist=True)
    precommit, public_plan, private_state = validate_frozen_inputs(batch_root)
    validate_anchor(batch_root, precommit)
    if (batch_root / "reveal.json").exists():
        raise RunnerError("reveal.json already exists and will not be overwritten")
    if (batch_root / "evaluation.json").exists():
        raise RunnerError("evaluation exists before reveal")
    closed, closed_raw = read_json(batch_root / "closed.json", SCHEMA_CLOSED)
    if closed.get("status") != "CLOSED":
        raise RunnerError("ABORTED/incomplete batch is terminal and cannot reveal")
    private_d0_provenance, private_d0_provenance_commitment = (
        load_d0_private_provenance(batch_root, private_state, precommit)
    )
    if closed.get("private_d0_provenance_commitment") != private_d0_provenance_commitment:
        raise RunnerError("closed D0 private provenance commitment no longer matches preimages")

    seeds, nonces = decode_domains(private_state)
    public_raw = (batch_root / "public-plan.json").read_bytes()
    commitment_checks = {
        "assignment": commitment(
            "PRIVATE_ASSIGNMENT_ORDER",
            seeds["PRIVATE_ASSIGNMENT_ORDER"],
            nonces["PRIVATE_ASSIGNMENT_ORDER"],
            public_raw,
        )
        == precommit["assignment_commitment"],
        "public_id": commitment(
            "PUBLIC_ID", seeds["PUBLIC_ID"], nonces["PUBLIC_ID"], public_raw
        )
        == precommit["public_id_commitment"],
        "padding": commitment(
            "MEASUREMENT_PADDING",
            seeds["MEASUREMENT_PADDING"],
            nonces["MEASUREMENT_PADDING"],
            public_raw,
        )
        == precommit["padding_commitment"],
    }
    if precommit["mode"] == "formal":
        regenerated_layout = sample_layout("formal", 2)
    else:
        smoke_per_split = precommit["sample_plan"]["D0-HOST-LEAK"]["calibration"]
        regenerated_layout = sample_layout("smoke", smoke_per_split)
    regenerated_mapping, regenerated_order = assign_population(
        regenerated_layout,
        seeds["PRIVATE_ASSIGNMENT_ORDER"],
        seeds["PUBLIC_ID"],
        seeds["MEASUREMENT_PADDING"],
        control_instances_from_private_registry(
            private_state["private_control_registry"]
        ),
    )
    stored_mapping = private_state["mapping"]
    public_pairs = sorted(
        (item["opaque_slot_id"], item["challenge"]) for item in public_plan["slots"]
    )
    regenerated_pairs = sorted(
        (item["opaque_slot_id"], item["challenge"]) for item in regenerated_mapping
    )
    revealed_control_registry = private_state["private_control_registry"]
    rebuilt_control_commitment = private_control_registry_commitment(
        revealed_control_registry, canonical_bytes(revealed_control_registry)
    )
    reconstruction = {
        "commitments": commitment_checks,
        "strict_block_balance": strict_balance(regenerated_mapping),
        "opaque_ids_unique_and_rebuilt": (
            len(regenerated_pairs) == len(set(slot_id for slot_id, _ in regenerated_pairs))
            and regenerated_pairs == public_pairs
        ),
        "mapping_exactly_rebuilt": canonical_bytes(regenerated_mapping) == canonical_bytes(stored_mapping),
        "execution_order_exactly_rebuilt": regenerated_order == private_state["execution_order"],
        "padding_exactly_rebuilt": all(
            left["measurement_padding_bytes"] == right["measurement_padding_bytes"]
            for left, right in zip(regenerated_mapping, stored_mapping)
        ),
        "private_control_registry_exactly_rebuilt": (
            rebuilt_control_commitment
            == precommit["private_control_registry_commitment"]
        ),
        "private_d0_provenance_exactly_rebuilt": (
            private_d0_provenance_commitment
            == closed["private_d0_provenance_commitment"]
        ),
    }
    all_rebuilt = (
        all(commitment_checks.values())
        and all(value for key, value in reconstruction.items() if key != "commitments")
    )
    reveal_mapping = [
        {
            "opaque_slot_id": item["opaque_slot_id"],
            "challenge": item["challenge"],
            "phase": item["phase"],
            "block": item["block"],
            "role": item["role"],
            "canary_token_or_null": item["private_canary_token_or_null"],
            "measurement_padding_bytes": item["measurement_padding_bytes"],
        }
        for item in stored_mapping
    ]
    document = {
        "schema": SCHEMA_REVEAL,
        "batch_id": precommit["batch_id"],
        "revealed_at": utc_now(),
        "closed_sha256": sha256_bytes(closed_raw),
        "domains": {
            domain: {
                "seed_hex": seeds[domain].hex(),
                "nonce_hex": nonces[domain].hex(),
            }
            for domain in DOMAINS
        },
        "mapping": reveal_mapping,
        "execution_order": private_state["execution_order"],
        "private_control_registry": revealed_control_registry,
        "private_control_registry_reconstruction": rebuilt_control_commitment,
        "private_d0_provenance": private_d0_provenance,
        "private_d0_provenance_commitment": private_d0_provenance_commitment,
        "reconstruction": reconstruction,
        "reconstruction_complete": all_rebuilt,
    }
    raw = exclusive_json(batch_root / "reveal.json", document, 0o644)
    return {
        "command": "reveal",
        "state": "REVEALED",
        "batch_id": precommit["batch_id"],
        "reveal_sha256": sha256_bytes(raw),
        "reconstruction_complete": all_rebuilt,
        "next": "independent evaluator (runner does not import or invoke it)",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Wave 025 host runner: evidence only, no verdict/classifier"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="freeze a batch, write precommit, stop")
    prepare_parser.add_argument("--batch-dir", required=True)
    prepare_parser.add_argument("--mode", choices=("smoke", "formal"), required=True)
    prepare_parser.add_argument("--batch-id")
    prepare_parser.add_argument("--image-ref", default="wave025-leak-collector:local")
    prepare_parser.add_argument("--base-image-ref", default="node:20-slim")
    prepare_parser.add_argument("--feature-spec-path", required=True)
    prepare_parser.add_argument("--executable-attack-profile-path", required=True)
    prepare_parser.add_argument("--shared-evidence-profile-path", required=True)
    prepare_parser.add_argument("--control-family-registration-path", required=True)
    prepare_parser.add_argument("--host-only-inventory-path", required=True)
    prepare_parser.add_argument("--independent-evaluator-source-manifest-path", required=True)
    prepare_parser.add_argument("--private-control-registry-path", required=True)
    prepare_parser.add_argument("--smoke-per-split", type=int, default=2)
    prepare_parser.add_argument("--docker-bin", default="docker")
    prepare_parser.set_defaults(handler=prepare)

    anchor_parser = subparsers.add_parser(
        "anchor", help="record already-created external/local anchor receipts"
    )
    anchor_parser.add_argument("--batch-dir", required=True)
    anchor_parser.add_argument("--receipt-json", action="append")
    anchor_parser.add_argument("--receipt-file", action="append")
    anchor_parser.set_defaults(handler=anchor)

    run_parser = subparsers.add_parser("run", help="execute the sealed Docker slot order")
    run_parser.add_argument("--batch-dir", required=True)
    run_parser.add_argument("--docker-bin", default="docker")
    run_parser.set_defaults(handler=run_batch)

    close_parser = subparsers.add_parser("close", help="freeze a complete or aborted batch")
    close_parser.add_argument("--batch-dir", required=True)
    close_parser.add_argument("--docker-bin", default="docker")
    close_parser.set_defaults(handler=close_batch)

    reveal_parser = subparsers.add_parser("reveal", help="reveal secrets after successful close")
    reveal_parser.add_argument("--batch-dir", required=True)
    reveal_parser.set_defaults(handler=reveal_batch)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    try:
        result = arguments.handler(arguments)
    except (RunnerError, FileExistsError, FileNotFoundError, PermissionError) as error:
        failure = {
            "schema": "WAVE025_RUNNER_COMMAND_FAILURE_V1",
            "command": arguments.command,
            "status": "FAILED_CLOSED",
            "error_type": type(error).__name__,
            "error": str(error),
        }
        sys.stderr.buffer.write(canonical_bytes(failure))
        return 2
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
