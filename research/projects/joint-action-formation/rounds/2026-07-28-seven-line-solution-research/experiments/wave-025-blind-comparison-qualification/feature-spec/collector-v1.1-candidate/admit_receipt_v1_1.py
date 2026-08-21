#!/usr/bin/env python3
"""Executable candidate admission for Wave 025 collector V1 receipts.

This is deliberately independent of feature routing and predictor semantics.
It does not upgrade an admitted receipt to formal/scientific evidence.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from jsonschema import Draft202012Validator


HERE = Path(__file__).resolve().parent
OLD_SCHEMA = HERE.parent / "COLLECTOR-RECEIPT-V1.candidate.schema.json"
RECEIPT_SCHEMA = HERE / "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json"
BINDING_SCHEMA = HERE / "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json"
RAW_CHECKER = HERE / "raw-canonical-check.candidate.js"
PACKAGE_MANIFEST = HERE / "PACKAGE-MANIFEST.candidate.json"

MAX_RAW_RECEIPT_BYTES = 64 * 1024 * 1024
MAX_ENVIRONMENT_ROWS = 4096
MAX_TREE_ERRORS = 8192
MAX_VISIBLE_CANARIES = 65536
MAX_CANARY_NODES = 2048
MAX_CANARY_FILE_BYTES = 64 * 1024
MAX_TREE_DEPTH = 5
CANARY_RE = re.compile(r"WAVE025_CANARY_[A-Za-z0-9._-]{1,96}")
DECIMAL_RE = re.compile(r"^(0|[1-9][0-9]*)$")
ID_VECTOR_RE = re.compile(
    r"^(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)\t(0|[1-9][0-9]*)$"
)
PATH_RE = re.compile(r"^(?:\.|[^/]+(?:/[^/]+)*)$")


class AdmissionError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def reject(code: str, detail: str) -> None:
    raise AdmissionError(code, detail)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_package(expected_manifest_sha256: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_manifest_sha256 or ""):
        reject("PACKAGE_SEAL_REQUIRED", "exact controller-supplied manifest SHA-256 is required")
    if not PACKAGE_MANIFEST.is_file():
        reject("PACKAGE_MANIFEST_MISSING", str(PACKAGE_MANIFEST))
    raw, manifest = parse_json_raw(PACKAGE_MANIFEST, canonical=True, max_bytes=4 * 1024 * 1024)
    if sha256(raw) != expected_manifest_sha256:
        reject("PACKAGE_MANIFEST_SEAL_MISMATCH", sha256(raw))
    if not isinstance(manifest, dict) or manifest.get("schema") != "WAVE025_COLLECTOR_ADMISSION_PACKAGE_MANIFEST_V1_1_CANDIDATE":
        reject("PACKAGE_MANIFEST_SCHEMA", "wrong package manifest schema")
    required_files = {
        "ADMISSION-POLICY-V1.1.candidate.json",
        "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json",
        "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json",
        "admit_receipt_v1_1.py",
        "producer-v1.1.candidate.js",
        "raw-canonical-check.candidate.js",
    }
    required_historical = {
        "../../attackers/leak-only-collector/collector.js",
        "../COLLECTOR-RECEIPT-V1.candidate.schema.json",
    }
    if {row.get("path") for row in manifest.get("files", [])} != required_files:
        reject("PACKAGE_MANIFEST_FILE_SET", "runtime file set differs")
    if {row.get("path") for row in manifest.get("historical_inputs", [])} != required_historical:
        reject("PACKAGE_MANIFEST_HISTORICAL_SET", "historical input set differs")
    for group, base_dir in (("files", HERE), ("historical_inputs", HERE)):
        rows = manifest.get(group)
        if not isinstance(rows, list):
            reject("PACKAGE_MANIFEST_FIELDS", group)
        for row in rows:
            if set(row) != {"path", "byte_length", "sha256"}:
                reject("PACKAGE_MANIFEST_ENTRY", f"{group}:{row}")
            relative = PurePosixPath(row["path"])
            try:
                target = base_dir.joinpath(*relative.parts).resolve(strict=True)
            except (FileNotFoundError, PermissionError, OSError) as error:
                reject("PACKAGE_FILE_MISSING", f"{row['path']}:{getattr(error, 'errno', None)}")
            if target.stat().st_size != row["byte_length"] or sha256_file(target) != row["sha256"]:
                reject("PACKAGE_FILE_MISMATCH", row["path"])
    old = json.loads(OLD_SCHEMA.read_text(encoding="utf-8"))
    release = json.loads(RECEIPT_SCHEMA.read_text(encoding="utf-8"))
    for key in ("$id", "title", "description", "x-towow-profile", "x-towow-status"):
        old.pop(key, None)
        release.pop(key, None)
    if old != release:
        reject("RELEASE_SCHEMA_DIVERGES_FROM_FROZEN_V1", str(RECEIPT_SCHEMA))
    return manifest


def utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def canonical_bytes(value: Any) -> bytes:
    # All keys in candidate-owned documents are ASCII. Receipt byte canonicality
    # itself is checked by the JavaScript helper to preserve JSON.stringify rules.
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            reject("RAW_DUPLICATE_MEMBER", key)
        result[key] = value
    return result


def parse_json_raw(path: Path, *, canonical: bool, max_bytes: int) -> tuple[bytes, Any]:
    size = path.stat().st_size
    if size > max_bytes:
        reject("RAW_SIZE_CAP", f"{path}: {size} > {max_bytes}")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        reject("RAW_UTF8_BOM", str(path))
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        reject("RAW_UTF8_INVALID", f"{path}:{error.start}")
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda token: reject("RAW_NONFINITE_NUMBER", token),
        )
    except AdmissionError:
        raise
    except json.JSONDecodeError as error:
        reject("RAW_JSON_INVALID", f"{path}:{error.lineno}:{error.colno}")
    if canonical:
        try:
            completed = subprocess.run(
                ["node", str(RAW_CHECKER), str(path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as error:
            reject("RAW_CHECKER_UNAVAILABLE", str(error))
        if completed.returncode != 0:
            reject("RAW_NOT_CANONICAL", completed.stderr.strip() or str(path))
    return raw, parsed


def validate_schema(instance: Any, schema_path: Path, code: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    errors = sorted(Draft202012Validator(schema).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        error = errors[0]
        pointer = "/" + "/".join(str(part) for part in error.path)
        reject(code, f"{pointer}: {error.message}")


def ensure_sorted_unique(values: list[Any], identity, code: str, pointer: str) -> None:
    identities = [identity(value) for value in values]
    if len(set(identities)) != len(identities):
        reject(code, f"{pointer}: duplicate identity")
    if identities != sorted(identities):
        reject(code, f"{pointer}: not in required order")


def validate_relative_observation_path(value: str, pointer: str) -> None:
    if not PATH_RE.fullmatch(value):
        reject("TREE_PATH_GRAMMAR", f"{pointer}: {value!r}")
    parts = PurePosixPath(value).parts
    if value != "." and any(part in {"", ".", ".."} for part in parts):
        reject("TREE_PATH_GRAMMAR", f"{pointer}: {value!r}")
    if value.startswith("/") or "\x00" in value:
        reject("TREE_PATH_GRAMMAR", f"{pointer}: {value!r}")


def expected_visible_prefix(label: str) -> str:
    return {
        "challenge": "$CHALLENGE",
        "cwd": "$CWD",
        "out": "$OUT",
        "tmp": "$TMP",
        "self-fd": "$PROC/self/fd",
    }[label]


def validate_tree(label: str, tree: dict[str, Any]) -> None:
    if tree["truncated"]:
        reject("TREE_TRUNCATED", label)
    if len(tree["errors"]) > MAX_TREE_ERRORS:
        reject("TREE_ERROR_CAP", label)
    if not tree["available"]:
        return
    if not tree["entries"] and not tree["errors"]:
        reject("TREE_EMPTY_AVAILABLE", label)
    ensure_sorted_unique(
        tree["entries"], lambda row: utf8_key(row["path"]), "TREE_ENTRY_IDENTITY_ORDER", label
    )
    ensure_sorted_unique(
        tree["errors"], lambda row: utf8_key(row["path"]), "TREE_ERROR_IDENTITY_ORDER", label
    )
    entries = {row["path"]: row for row in tree["entries"]}
    errors = {row["path"]: row for row in tree["errors"]}
    for index, row in enumerate(tree["entries"]):
        validate_relative_observation_path(row["path"], f"{label}.entries[{index}].path")
        depth = 0 if row["path"] == "." else len(PurePosixPath(row["path"]).parts)
        if depth > MAX_TREE_DEPTH or (depth == MAX_TREE_DEPTH and row["type"] == "directory"):
            reject("TREE_DEPTH_UNREACHABLE", f"{label}:{row['path']}:{row['type']}")
        if row["path"] != ".":
            parent = str(PurePosixPath(row["path"]).parent)
            if parent == "":
                parent = "."
            if parent not in entries or entries[parent]["type"] != "directory":
                reject("TREE_PARENT_MISSING", f"{label}:{row['path']}")
    for index, row in enumerate(tree["errors"]):
        value = row["path"]
        validate_relative_observation_path(value, f"{label}.errors[{index}].path")
        error = row["error"]
        if value in entries:
            if entries[value]["type"] != "directory" or error["syscall"] != "scandir":
                reject("TREE_ENTRY_ERROR_CONTRADICTION", f"{label}:{value}")
        else:
            if error["syscall"] != "lstat":
                reject("TREE_ERROR_OPERATION_PROVENANCE", f"{label}:{value}:{error['syscall']}")
            if value != ".":
                parent = str(PurePosixPath(value).parent)
                if parent == "":
                    parent = "."
                if parent not in entries or entries[parent]["type"] != "directory":
                    reject("TREE_ERROR_PARENT_MISSING", f"{label}:{value}")
        error_path = error["path"]
        if error_path is not None:
            expected = expected_visible_prefix(label)
            if value != ".":
                expected = f"{expected}/{value}"
            if error_path != expected:
                reject("TREE_ERROR_PATH_PROVENANCE", f"{label}:{value}:{error_path}")
    if "." not in entries and "." not in errors:
        reject("TREE_ROOT_OBSERVATION_MISSING", label)


def validate_status(status: dict[str, str], pointer: str) -> None:
    for name in ("ppid", "threads"):
        if name in status and not DECIMAL_RE.fullmatch(status[name]):
            reject("STATUS_GRAMMAR", f"{pointer}.{name}")
    for name in ("uid", "gid"):
        if name in status and not ID_VECTOR_RE.fullmatch(status[name]):
            reject("STATUS_GRAMMAR", f"{pointer}.{name}")


def validate_process_view(view: dict[str, Any]) -> None:
    if view["truncated"]:
        reject("PROCESS_TRUNCATED", "process_view")
    if not view["available"]:
        return
    ensure_sorted_unique(
        view["processes"], lambda row: row["pid"], "PROCESS_IDENTITY_ORDER", "process_view"
    )
    for row in view["processes"]:
        pid = row["pid"]
        if "error" in row:
            error_path = row["error"]["path"]
            if error_path is not None and error_path not in {f"$PROC/{pid}/cmdline", f"$PROC/{pid}/status"}:
                reject("PROCESS_ERROR_PATH_PROVENANCE", f"pid={pid}:{error_path}")
        else:
            validate_status(row["status"], f"process[{pid}].status")
    for name in ("cgroup", "mountinfo", "status"):
        capture = view["self"][name]
        if "error" in capture:
            error_path = capture["error"]["path"]
            if error_path is not None and error_path != f"$PROC/self/{name}":
                reject("PROCESS_SELF_ERROR_PATH_PROVENANCE", f"{name}:{error_path}")


def validate_timing(receipt: dict[str, Any]) -> None:
    collection_start = int(receipt["collection_window"]["start"]["monotonic_ns"])
    timing_start = int(receipt["timing"]["monotonic_start_ns"])
    timing_end = int(receipt["timing"]["monotonic_end_ns"])
    collection_end = int(receipt["collection_window"]["end"]["monotonic_ns"])
    if not (collection_start <= timing_start <= timing_end <= collection_end):
        reject("MONOTONIC_NESTING", "collection.start <= timing.start <= timing.end <= collection.end")
    sample_sum = sum(
        int(value)
        for value in (
            receipt["timing"]["immediate_delta_ns"]
            + receipt["timing"]["input_stat_elapsed_ns"]
        )
    )
    if sample_sum > timing_end - timing_start:
        reject("TIMING_SAMPLE_SUM", f"{sample_sum} > {timing_end - timing_start}")
    expected = {
        "read-fixed-missing-file": ("$CHALLENGE/__collector_missing_probe__", {"open", "read"}),
        "stat-fixed-missing-proc": ("$PROC/0/__collector_missing_probe__", {"stat", "lstat"}),
        "read-challenge-directory-as-file": (None, {"read", "open"}),
    }
    for probe in receipt["timing"]["error_shape_probes"]:
        if probe["ok"]:
            continue
        path_value, syscalls = expected[probe["name"]]
        error = probe["error"]
        if probe["name"] == "read-challenge-directory-as-file":
            if error["path"] not in {None, "$CHALLENGE"}:
                reject("TIMING_PROBE_PROVENANCE", probe["name"])
        elif error["path"] != path_value:
            reject("TIMING_PROBE_PROVENANCE", probe["name"])
        if error["syscall"] not in syscalls:
            reject("TIMING_PROBE_PROVENANCE", probe["name"])


def validate_semantics(receipt: dict[str, Any]) -> None:
    if len(receipt["environment"]) > MAX_ENVIRONMENT_ROWS:
        reject("ENVIRONMENT_CAP", str(len(receipt["environment"])))
    ensure_sorted_unique(
        receipt["environment"], lambda row: utf8_key(row["key"]), "ENVIRONMENT_IDENTITY_ORDER", "environment"
    )
    for label, tree in receipt["directory_trees"].items():
        validate_tree(label, tree)
    validate_process_view(receipt["process_view"])
    groups = receipt["identity"]["groups"]
    if groups != sorted(set(groups)):
        reject("IDENTITY_GROUP_ORDER", "identity.groups")
    ensure_sorted_unique(
        receipt["visible_canaries"],
        lambda row: canonical_bytes(row),
        "VISIBLE_CANARY_IDENTITY_ORDER",
        "visible_canaries",
    )
    if len(receipt["visible_canaries"]) > MAX_VISIBLE_CANARIES:
        reject("VISIBLE_CANARY_CAP", str(len(receipt["visible_canaries"])))
    env_keys = {row["key"] for row in receipt["environment"]}
    for row in receipt["visible_canaries"]:
        if row["source"].startswith("environment-") and row["location"] not in env_keys:
            reject("VISIBLE_CANARY_ORPHAN_ENV", row["location"])
        if row["source"].startswith("challenge-"):
            validate_relative_observation_path(row["location"], "visible_canary.location")
    os_hostname = receipt["hostname"]["os_hostname"]
    if not os_hostname["ok"] and os_hostname["error"]["path"] is not None:
        reject("HOSTNAME_ERROR_PROVENANCE", "os.hostname error path must be null")
    etc_hostname = receipt["hostname"]["etc_hostname"]
    if isinstance(etc_hostname, dict) and etc_hostname["error"]["path"] != "/etc/hostname":
        reject("HOSTNAME_ERROR_PROVENANCE", "etc hostname error path must be /etc/hostname")
    validate_timing(receipt)


def validate_g_closed_branches(receipt: dict[str, Any]) -> None:
    if not receipt["hostname"]["os_hostname"]["ok"] or isinstance(receipt["hostname"]["etc_hostname"], dict):
        reject("G_UNVERIFIED_ERROR_BRANCH", "hostname")
    if "error" in receipt["identity"]["user_info"]:
        reject("G_UNVERIFIED_ERROR_BRANCH", "identity.user_info")
    for label, tree in receipt["directory_trees"].items():
        if not tree["available"] or tree["errors"]:
            reject("G_UNVERIFIED_ERROR_BRANCH", f"directory_trees.{label}")
    view = receipt["process_view"]
    if not view["available"]:
        reject("G_UNVERIFIED_ERROR_BRANCH", "process_view unavailable")
    if any("error" in row for row in view["processes"]):
        reject("G_UNVERIFIED_ERROR_BRANCH", "process row")
    if not view["processes"] or receipt["identity"]["pid"] not in {row["pid"] for row in view["processes"]}:
        reject("G_PROCESS_SELF_PID_MISSING", str(receipt["identity"]["pid"]))
    if any("error" in view["self"][name] for name in ("cgroup", "mountinfo", "status")):
        reject("G_UNVERIFIED_ERROR_BRANCH", "process self")
    for name in ("process_uptime_seconds", "os_uptime_seconds"):
        if not receipt["timing"][name]["ok"]:
            reject("G_UNVERIFIED_ERROR_BRANCH", f"timing.{name}")


def resolve_bound_file(material_root: Path, binding: dict[str, Any]) -> Path:
    relative = PurePosixPath(binding["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        reject("BINDING_PATH_ESCAPE", binding["relative_path"])
    candidate = material_root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            reject("BINDING_SYMLINK", binding["relative_path"])
    root_real = material_root.resolve()
    candidate_real = candidate.resolve(strict=True)
    try:
        candidate_real.relative_to(root_real)
    except ValueError:
        reject("BINDING_PATH_ESCAPE", binding["relative_path"])
    if not candidate_real.is_file():
        reject("BINDING_NOT_FILE", binding["relative_path"])
    if candidate_real.stat().st_size != binding["byte_length"] or sha256_file(candidate_real) != binding["sha256"]:
        reject("BINDING_FILE_MISMATCH", binding["relative_path"])
    return candidate_real


def tokens(value: str) -> list[str]:
    return sorted(set(CANARY_RE.findall(value)), key=utf8_key)


def snapshot_challenge(root: Path, *, reject_oversize: bool = False) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not root.exists() or not root.is_dir():
        reject("CHALLENGE_ROOT_INVALID", str(root))
    inventory: list[dict[str, Any]] = []
    canaries: list[dict[str, Any]] = []
    tree_entries: list[dict[str, Any]] = []
    seen_canaries: set[bytes] = set()
    nodes = 0

    def add_canary(token: str, source: str, location: str) -> None:
        raw = token.encode("utf-8")
        row = {
            "source": source,
            "location": location,
            "token_byte_length": len(raw),
            "token_sha256": sha256(raw),
        }
        identity = canonical_bytes(row)
        if identity in seen_canaries:
            return
        if len(canaries) >= MAX_VISIBLE_CANARIES:
            reject("VISIBLE_CANARY_CAP", str(root))
        seen_canaries.add(identity)
        canaries.append(row)

    def visit(path_value: Path, relative: str, depth: int) -> None:
        nonlocal nodes
        if nodes >= MAX_CANARY_NODES:
            reject("CANARY_SCAN_NODE_CAP", str(root))
        nodes += 1
        observed = os.lstat(path_value)
        name = path_value.name
        location = relative or "."
        for token in tokens(name):
            add_canary(token, "challenge-entry-name", location)
        if stat.S_ISDIR(observed.st_mode):
            kind = "directory"
        elif stat.S_ISREG(observed.st_mode):
            kind = "file"
        elif stat.S_ISLNK(observed.st_mode):
            kind = "symlink"
        elif stat.S_ISSOCK(observed.st_mode):
            kind = "socket"
        elif stat.S_ISFIFO(observed.st_mode):
            kind = "fifo"
        elif stat.S_ISCHR(observed.st_mode):
            kind = "character-device"
        elif stat.S_ISBLK(observed.st_mode):
            kind = "block-device"
        else:
            kind = "other"
        tree_entry = {
            "path": location,
            "type": kind,
            "mode_octal": f"0o{stat.S_IMODE(observed.st_mode):04o}",
            "uid": str(observed.st_uid),
            "gid": str(observed.st_gid),
            "size_bytes": str(observed.st_size),
            "inode": str(observed.st_ino),
            "device": str(observed.st_dev),
            "nlink": str(observed.st_nlink),
            "mtime_ns": str(observed.st_mtime_ns),
            "ctime_ns": str(observed.st_ctime_ns),
        }
        if stat.S_ISLNK(observed.st_mode):
            target = os.readlink(path_value)
            tree_entry["symlink_target"] = target
            tree_entries.append(tree_entry)
            inventory.append({"path": location, "type": "symlink", "target": target})
            for token in tokens(target):
                add_canary(token, "challenge-symlink-target", location)
            return
        if stat.S_ISREG(observed.st_mode):
            tree_entries.append(tree_entry)
            size = observed.st_size
            if reject_oversize and size > MAX_CANARY_FILE_BYTES:
                reject("G_CANARY_FILE_OVERSIZE", f"{location}:{size}")
            eligible = size <= MAX_CANARY_FILE_BYTES
            raw = path_value.read_bytes() if eligible else None
            inventory.append(
                {
                    "path": location,
                    "type": "file",
                    "byte_length": size,
                    "sha256": sha256(raw) if raw is not None else sha256_file(path_value),
                    "canary_scan_eligible": eligible,
                }
            )
            if eligible:
                assert raw is not None
                for token in tokens(raw.decode("utf-8", errors="replace")):
                    add_canary(token, "challenge-file-content", location)
            return
        if stat.S_ISDIR(observed.st_mode):
            tree_entries.append(tree_entry)
            inventory.append({"path": location, "type": "directory"})
            children = sorted(path_value.iterdir(), key=lambda item: utf8_key(item.name))
            if depth >= MAX_TREE_DEPTH and children:
                reject("CANARY_SCAN_DEPTH_CAP", location)
            for child in children:
                child_relative = f"{relative}/{child.name}" if relative else child.name
                visit(child, child_relative, depth + 1)
            return
        tree_entries.append(tree_entry)
        inventory.append({"path": location, "type": "other"})

    visit(root, "", 0)
    inventory.sort(key=lambda row: utf8_key(row["path"]))
    tree_entries.sort(key=lambda row: utf8_key(row["path"]))
    canaries.sort(key=canonical_bytes)
    return {
        "schema": "WAVE025_CHALLENGE_SNAPSHOT_V1_1_CANDIDATE",
        "entries": inventory,
        "directory_tree": {
            "available": True,
            "entries": tree_entries,
            "errors": [],
            "truncated": False,
        },
    }, canaries


def environment_rows(environment: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = []
    canaries = []
    seen = set()
    for key in sorted(environment, key=utf8_key):
        value = environment[key]
        if not isinstance(value, str):
            reject("ENVIRONMENT_VALUE_TYPE", key)
        raw = value.encode("utf-8")
        rows.append({"key": key, "value_byte_length": len(raw), "value_sha256": sha256(raw)})
        for token, source in [*((item, "environment-value") for item in tokens(value)), *((item, "environment-key") for item in tokens(key))]:
            token_raw = token.encode("utf-8")
            row = {
                "source": source,
                "location": key,
                "token_byte_length": len(token_raw),
                "token_sha256": sha256(token_raw),
            }
            identity = canonical_bytes(row)
            if identity not in seen:
                seen.add(identity)
                canaries.append(row)
    return rows, canaries


def parse_status(raw: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    allowed = {"Name", "State", "PPid", "Uid", "Gid", "Threads"}
    for line in raw.decode("utf-8", errors="replace").split("\n"):
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key in allowed:
            result[key.lower()] = value.strip()
    return result


def strict_b64(value: str, pointer: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception:
        reject("PROCESS_SNAPSHOT_BASE64", pointer)


def validate_process_snapshot(view: dict[str, Any], snapshot: Any, *, g_mode: bool) -> list[str]:
    unknown_codes: list[str] = []
    if snapshot is None:
        if view["available"]:
            if g_mode:
                reject("G_PROCESS_SNAPSHOT_REQUIRED", "process_view is available")
            unknown_codes.append("PROCESS_RAW_SNAPSHOT_MISSING")
        return unknown_codes
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "WAVE025_PROCESS_SNAPSHOT_V1_1_CANDIDATE":
        reject("PROCESS_SNAPSHOT_SCHEMA", "wrong process snapshot schema")
    expected_keys = {"schema", "numeric_pid_names", "processes", "self"}
    if set(snapshot) != expected_keys:
        reject("PROCESS_SNAPSHOT_FIELDS", str(sorted(set(snapshot) ^ expected_keys)))
    names = snapshot["numeric_pid_names"]
    if not isinstance(names, list) or any(not isinstance(name, str) or not DECIMAL_RE.fullmatch(name) for name in names):
        reject("PROCESS_SNAPSHOT_PID_NAMES", "not canonical decimal strings")
    numeric = [int(name) for name in names]
    if numeric != sorted(set(numeric)) or any(str(value) != name for value, name in zip(numeric, names)):
        reject("PROCESS_SNAPSHOT_PID_NAMES", "not unique numeric order")
    if len(numeric) > 256:
        reject("PROCESS_SNAPSHOT_TRUNCATED", str(len(numeric)))
    if not view["available"]:
        reject("PROCESS_SNAPSHOT_CONTRADICTION", "snapshot supplied for unavailable view")
    if [row["pid"] for row in view["processes"]] != numeric:
        reject("PROCESS_SNAPSHOT_POPULATION", "PID population mismatch")
    raw_rows = snapshot["processes"]
    if not isinstance(raw_rows, list) or [row.get("pid") for row in raw_rows] != numeric:
        reject("PROCESS_SNAPSHOT_ROWS", "raw row population/order mismatch")
    for public, raw_row in zip(view["processes"], raw_rows):
        if "error" in public:
            unknown_codes.append("PROCESS_ERROR_ORIGINAL_UNAVAILABLE")
            continue
        if set(raw_row) != {"pid", "cmdline_base64", "status_base64", "pid_namespace", "mount_namespace"}:
            reject("PROCESS_SNAPSHOT_ROW_FIELDS", str(public["pid"]))
        cmdline = strict_b64(raw_row["cmdline_base64"], f"process[{public['pid']}].cmdline")
        status_raw = strict_b64(raw_row["status_base64"], f"process[{public['pid']}].status")
        expected_cmdline = [item for item in cmdline.decode("utf-8", errors="replace").split("\0") if item]
        if (
            public["cmdline"] != expected_cmdline
            or public["cmdline_byte_length"] != len(cmdline)
            or public["cmdline_sha256"] != sha256(cmdline)
            or public["status"] != parse_status(status_raw)
            or public["pid_namespace"] != raw_row["pid_namespace"]
            or public["mount_namespace"] != raw_row["mount_namespace"]
        ):
            reject("PROCESS_SNAPSHOT_ROW_MISMATCH", str(public["pid"]))
    self_raw = snapshot["self"]
    if not isinstance(self_raw, dict) or set(self_raw) != {"cgroup", "mountinfo", "status", "pid_namespace", "mount_namespace"}:
        reject("PROCESS_SNAPSHOT_SELF_FIELDS", "self")
    for name in ("cgroup", "mountinfo", "status"):
        public = view["self"][name]
        raw_value = self_raw[name]
        if "error" in public:
            unknown_codes.append("PROCESS_SELF_ERROR_ORIGINAL_UNAVAILABLE")
            continue
        if not isinstance(raw_value, str):
            reject("PROCESS_SNAPSHOT_SELF_MISSING", name)
        raw = strict_b64(raw_value, f"self.{name}")
        if public != {"byte_length": len(raw), "sha256": sha256(raw)}:
            reject("PROCESS_SNAPSHOT_SELF_MISMATCH", name)
    for name in ("pid_namespace", "mount_namespace"):
        if view["self"][name] != self_raw[name]:
            reject("PROCESS_SNAPSHOT_SELF_MISMATCH", name)
    if g_mode and unknown_codes:
        reject("G_PROCESS_SNAPSHOT_INCOMPLETE", ",".join(sorted(set(unknown_codes))))
    return unknown_codes


def resolve_bound_dir(controller_root: Path, relative_value: str) -> Path:
    relative = PurePosixPath(relative_value)
    if relative.is_absolute() or ".." in relative.parts:
        reject("CONTROLLER_PATH_ESCAPE", relative_value)
    if controller_root.is_symlink():
        reject("CONTROLLER_ROOT_SYMLINK", str(controller_root))
    root_real = controller_root.resolve()
    unresolved = controller_root
    for part in relative.parts:
        unresolved = unresolved / part
        if unresolved.is_symlink():
            reject("CONTROLLER_PATH_SYMLINK", relative_value)
    target = unresolved.resolve(strict=True)
    try:
        target.relative_to(root_real)
    except ValueError:
        reject("CONTROLLER_PATH_ESCAPE", relative_value)
    if not target.is_dir():
        reject("CONTROLLER_PATH_NOT_DIRECTORY", relative_value)
    return target


def validate_controller_preimage(
    receipt_path: Path,
    receipt_raw: bytes,
    receipt: dict[str, Any],
    preimage_path: Path,
    preimage_sha256: str,
    controller_root: Path,
    package_manifest_sha256: str,
    *,
    g_mode: bool,
) -> list[str]:
    if not re.fullmatch(r"[0-9a-f]{64}", preimage_sha256 or ""):
        reject("CONTROLLER_SEAL_REQUIRED", "exact external preimage SHA-256 is required")
    root_real = controller_root.resolve(strict=True)
    preimage_real = preimage_path.resolve(strict=True)
    try:
        preimage_real.relative_to(root_real)
    except ValueError:
        reject("CONTROLLER_SEAL_OUTSIDE_DOMAIN", str(preimage_path))
    if preimage_path.is_symlink():
        reject("CONTROLLER_SEAL_SYMLINK", str(preimage_path))
    preimage_raw, binding = parse_json_raw(preimage_path, canonical=True, max_bytes=1024 * 1024)
    if sha256(preimage_raw) != preimage_sha256:
        reject("CONTROLLER_SEAL_MISMATCH", sha256(preimage_raw))
    validate_schema(binding, BINDING_SCHEMA, "CONTROLLER_PREIMAGE_SCHEMA_INVALID")
    expected_roles = {
        "collector_input": f"{binding['challenge_root_relative_path']}/collector-input.json",
        "subject_input": f"{binding['challenge_root_relative_path']}/input.bin",
    }
    for role, expected_path in expected_roles.items():
        if binding[role]["relative_path"] != expected_path:
            reject("CONTROLLER_ROLE_PATH_MISMATCH", f"{role}:{binding[role]['relative_path']} != {expected_path}")
    if binding["package_manifest"] != {
        "byte_length": PACKAGE_MANIFEST.stat().st_size,
        "sha256": package_manifest_sha256,
    }:
        reject("CONTROLLER_PACKAGE_BINDING_MISMATCH", str(PACKAGE_MANIFEST))
    resolved = {
        name: (resolve_bound_file(controller_root, value) if value is not None else None)
        for name, value in binding.items()
        if name in {"receipt", "collector_input", "subject_input", "launch_environment", "challenge_snapshot", "process_snapshot", "execution_evidence"}
    }
    if os.path.samestat(os.stat(resolved["collector_input"], follow_symlinks=False), os.stat(resolved["subject_input"], follow_symlinks=False)):
        reject("CONTROLLER_ROLE_FILE_ALIAS", "collector_input and subject_input resolve to the same inode")
    if resolved["receipt"].resolve() != receipt_path.resolve():
        reject("CONTROLLER_RECEIPT_TARGET", "CLI receipt differs from controller-bound receipt")
    if len(receipt_raw) != binding["receipt"]["byte_length"] or sha256(receipt_raw) != binding["receipt"]["sha256"]:
        reject("CONTROLLER_RECEIPT_MISMATCH", str(receipt_path))

    if receipt["input_contract"]["byte_length"] != binding["collector_input"]["byte_length"] or receipt["input_contract"]["sha256"] != binding["collector_input"]["sha256"]:
        reject("CONTROLLER_INPUT_DIGEST_MISMATCH", str(resolved["collector_input"]))
    _, input_document = parse_json_raw(resolved["collector_input"], canonical=False, max_bytes=1024 * 1024)
    if input_document != {"schema": "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"} or input_document != receipt["input_contract"]["parsed"]:
        reject("CONTROLLER_INPUT_PARSED_MISMATCH", str(resolved["collector_input"]))
    if receipt["subject_input"]["byte_length"] != binding["subject_input"]["byte_length"] or receipt["subject_input"]["sha256"] != binding["subject_input"]["sha256"]:
        reject("CONTROLLER_SUBJECT_MISMATCH", str(resolved["subject_input"]))

    _, environment_doc = parse_json_raw(resolved["launch_environment"], canonical=True, max_bytes=64 * 1024 * 1024)
    if not isinstance(environment_doc, dict) or set(environment_doc) != {"schema", "values"} or environment_doc["schema"] != "WAVE025_LAUNCH_ENVIRONMENT_V1_1_CANDIDATE" or not isinstance(environment_doc["values"], dict):
        reject("CONTROLLER_ENVIRONMENT_DOCUMENT", "closed launch environment document required")
    env_rows, env_canaries = environment_rows(environment_doc["values"])
    if receipt["environment"] != env_rows:
        reject("CONTROLLER_ENVIRONMENT_MISMATCH", "environment row digest/length/population differs")

    _, expected_challenge_snapshot = parse_json_raw(resolved["challenge_snapshot"], canonical=True, max_bytes=64 * 1024 * 1024)
    challenge_root = resolve_bound_dir(controller_root, binding["challenge_root_relative_path"])
    actual_challenge_snapshot, challenge_canaries = snapshot_challenge(challenge_root, reject_oversize=g_mode)
    if expected_challenge_snapshot != actual_challenge_snapshot:
        reject("CONTROLLER_CHALLENGE_SNAPSHOT_MISMATCH", str(challenge_root))
    if receipt["directory_trees"]["challenge"] != actual_challenge_snapshot["directory_tree"]:
        reject("CONTROLLER_CHALLENGE_TREE_MISMATCH", str(challenge_root))
    inventory = {row["path"]: row for row in actual_challenge_snapshot["entries"]}
    for role, leaf, contract in (
        ("collector_input", "collector-input.json", receipt["input_contract"]),
        ("subject_input", "input.bin", receipt["subject_input"]),
    ):
        row = inventory.get(leaf)
        if not row or row.get("type") != "file":
            reject("CONTROLLER_ROLE_NOT_REGULAR_FILE", f"{role}:{leaf}")
        if row.get("byte_length") != contract["byte_length"] or row.get("sha256") != contract["sha256"]:
            reject("CONTROLLER_ROLE_INVENTORY_MISMATCH", role)
    expected_canaries = sorted(env_canaries + challenge_canaries, key=canonical_bytes)
    deduped = []
    seen = set()
    for row in expected_canaries:
        identity = canonical_bytes(row)
        if identity not in seen:
            seen.add(identity)
            deduped.append(row)
    if receipt["visible_canaries"] != deduped:
        reject("CONTROLLER_VISIBLE_CANARY_COMPLETENESS", "receipt does not equal complete reconstructed scan")

    process_doc = None
    if resolved["process_snapshot"] is not None:
        _, process_doc = parse_json_raw(resolved["process_snapshot"], canonical=True, max_bytes=64 * 1024 * 1024)
    unknown_codes = validate_process_snapshot(receipt["process_view"], process_doc, g_mode=g_mode)

    _, execution = parse_json_raw(resolved["execution_evidence"], canonical=True, max_bytes=4 * 1024 * 1024)
    expected_execution_keys = {
        "schema", "receipt_sha256", "package_manifest_sha256", "challenge_read_only",
        "controller_domain_worker_writable", "network_isolation", "authority_channel_absent"
    }
    if not isinstance(execution, dict) or set(execution) != expected_execution_keys or execution.get("schema") != "WAVE025_RUNNER_EXECUTION_EVIDENCE_V1_1_CANDIDATE":
        reject("CONTROLLER_EXECUTION_EVIDENCE_SCHEMA", str(resolved["execution_evidence"]))
    if execution["receipt_sha256"] != sha256(receipt_raw) or execution["package_manifest_sha256"] != package_manifest_sha256:
        reject("CONTROLLER_EXECUTION_EVIDENCE_BINDING", str(resolved["execution_evidence"]))
    if g_mode and (
        execution["challenge_read_only"] is not True
        or execution["controller_domain_worker_writable"] is not False
        or execution["network_isolation"] != "RUNNER_ENFORCED"
        or execution["authority_channel_absent"] is not True
    ):
        reject("G_EXECUTION_EVIDENCE_INSUFFICIENT", str(resolved["execution_evidence"]))
    return unknown_codes


def admit(
    receipt_path: Path,
    *,
    package_manifest_sha256: str,
    controller_preimage: Path | None = None,
    controller_preimage_sha256: str | None = None,
    controller_root: Path | None = None,
    g_mode: bool = False,
) -> dict[str, Any]:
    verify_package(package_manifest_sha256)
    receipt_raw, receipt = parse_json_raw(receipt_path, canonical=True, max_bytes=MAX_RAW_RECEIPT_BYTES)
    validate_schema(receipt, RECEIPT_SCHEMA, "RECEIPT_SCHEMA_INVALID")
    validate_semantics(receipt)
    if g_mode:
        validate_g_closed_branches(receipt)
    unknown_codes = ["SAME_PERMISSION_MALICIOUS_PEER_OUT_OF_SCOPE"]
    if not g_mode:
        unknown_codes.append("ZERO_CALL_FIELDS_REQUIRE_INDEPENDENT_RUNTIME_EVIDENCE_INTERPRETATION")
    if controller_preimage is None:
        if g_mode:
            reject("G_CONTROLLER_SEAL_REQUIRED", "controller preimage is mandatory")
        unknown_codes.append("CONTROLLER_MATERIAL_PREIMAGE_MISSING")
        status = "CANDIDATE_NON_G_ADMISSION_PASS_WITH_UNVERIFIED_CODES"
    else:
        if controller_root is None or controller_preimage_sha256 is None:
            reject("CONTROLLER_SEAL_ARGUMENTS", "controller root and independent preimage SHA are required")
        unknown_codes.extend(
            validate_controller_preimage(
                receipt_path, receipt_raw, receipt, controller_preimage,
                controller_preimage_sha256, controller_root, package_manifest_sha256,
                g_mode=g_mode,
            )
        )
        if g_mode and any(code not in {
            "SAME_PERMISSION_MALICIOUS_PEER_OUT_OF_SCOPE",
        } for code in unknown_codes):
            reject("G_UNVERIFIED_MACHINE_CODES", ",".join(sorted(set(unknown_codes))))
        status = "CANDIDATE_G_INPUT_ADMISSION_PASS" if g_mode else "CANDIDATE_CONTROLLER_MATERIALS_BOUND"
    return {
        "schema": "WAVE025_COLLECTOR_ADMISSION_REPORT_V1_1_CANDIDATE",
        "status": status,
        "formal_admission": False,
        "g_mode": g_mode,
        "package_manifest_sha256": package_manifest_sha256,
        "receipt": {
            "byte_length": len(receipt_raw),
            "sha256": sha256(receipt_raw),
        },
        "verified": [
            "strict raw UTF-8/JSON/duplicate-member/canonical bytes",
            "self-contained V1.1 schema mechanically equal to frozen V1 structural core",
            "identity uniqueness and deterministic order",
            "tree/process truncation rejection and cross-field relations",
            "monotonic timing nesting and sample bound",
            "visible-canary source grammar",
        ] + (["controller-sealed input/environment/challenge/process/execution material preimage"] if controller_preimage else []),
        "remaining_unknown_codes": sorted(set(unknown_codes)),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    parser.add_argument("--controller-preimage", type=Path)
    parser.add_argument("--controller-preimage-sha256")
    parser.add_argument("--controller-root", type=Path)
    parser.add_argument("--g-mode", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = admit(
            args.receipt,
            package_manifest_sha256=args.package_manifest_sha256,
            controller_preimage=args.controller_preimage,
            controller_preimage_sha256=args.controller_preimage_sha256,
            controller_root=args.controller_root,
            g_mode=args.g_mode,
        )
        sys.stdout.buffer.write(canonical_bytes(report))
        return 0
    except AdmissionError as error:
        report = {
            "schema": "WAVE025_COLLECTOR_ADMISSION_REPORT_V1_1_CANDIDATE",
            "status": "REJECTED",
            "formal_admission": False,
            "error": {"code": error.code, "detail": error.detail},
        }
        sys.stdout.buffer.write(canonical_bytes(report))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
