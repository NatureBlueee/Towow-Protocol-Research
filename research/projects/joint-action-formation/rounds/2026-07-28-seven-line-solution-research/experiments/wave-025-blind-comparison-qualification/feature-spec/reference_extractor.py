#!/usr/bin/env python3
"""Dependency-free reference extractor for Wave 025 candidate-visible receipts.

This module deliberately knows nothing about batch paths, slot identifiers,
roles, execution order, host receipts, or qualification decisions.  It accepts
one successful collector receipt and returns only a frozen numeric/categorical
feature vector plus a leaf-level inclusion/exclusion audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


INPUT_SCHEMA = "WAVE025_LEAK_ONLY_FEATURES_V1"
OUTPUT_SCHEMA = "WAVE025_REFERENCE_FEATURE_VECTOR_V1"
EXTRACTOR_VERSION = "1.0.0"
EXPECTED_COLLECTOR_VERSION = "1.0.0"
MAX_STRING_BYTES = 4096
NGRAM_BUCKETS = 4096
NGRAM_SIZES = (1, 2, 3, 4)
INTEGER_RESIDUES = (2, 4, 8, 16, 256)

ROOT_FIELDS = {
    "argv",
    "collection_window",
    "collector_version",
    "contract",
    "cwd",
    "directory_trees",
    "environment",
    "hostname",
    "identity",
    "input_contract",
    "process_view",
    "schema",
    "subject_input",
    "timing",
    "visible_canaries",
}

FORBIDDEN_STRUCTURAL_FIELDS = {
    "block",
    "calibration_or_holdout",
    "challenge",
    "container_id",
    "execution_order",
    "expected",
    "expected_result",
    "host_launch",
    "opaque_slot_id",
    "order",
    "phase",
    "private_canary_token",
    "role",
    "seed",
}

NUMERIC_FIELD_NAMES = {
    "byte_length",
    "cmdline_byte_length",
    "ctime_ns",
    "device",
    "elapsed_ns",
    "egid",
    "errno",
    "euid",
    "gid",
    "inode",
    "mtime_ns",
    "nlink",
    "pid",
    "ppid",
    "size_bytes",
    "threads",
    "token_byte_length",
    "uid",
    "value_byte_length",
    "wall_clock_end_ms",
    "wall_clock_ms",
    "wall_clock_start_ms",
}

SHA_FIELD_NAMES = {
    "cmdline_sha256",
    "sha256",
    "token_sha256",
    "value_sha256",
}

EXCLUDED_REASONS = {
    "/schema": "validated transport discriminator",
    "/collector_version": "validated frozen artifact version",
    "/input_contract/parsed/schema": "validated fixed public schema constant",
    "/subject_input/path": "validated fixed literal path",
}


class FeatureSpecError(ValueError):
    """Fail-closed input or extraction error."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _path_join(path: str, member: str | int) -> str:
    return f"{path}/{_pointer_part(str(member))}"


def _expect_mapping(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FeatureSpecError(f"{path or '/'} must be an object")
    return value


def _expect_list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise FeatureSpecError(f"{path} must be an array")
    return value


def _keys_exact(
    value: Any,
    path: str,
    required: Iterable[str],
    optional: Iterable[str] = (),
) -> dict[str, Any]:
    obj = _expect_mapping(value, path)
    required_set = set(required)
    allowed = required_set | set(optional)
    actual = set(obj)
    missing = sorted(required_set - actual)
    extra = sorted(actual - allowed)
    # A word such as ``challenge`` is legitimate only where the frozen
    # collector schema explicitly declares it (directory-tree label).  At all
    # other locations it is already an unknown field and is additionally
    # reported as forbidden.
    forbidden = sorted((actual & FORBIDDEN_STRUCTURAL_FIELDS) - allowed)
    if missing or extra or forbidden:
        raise FeatureSpecError(
            f"{path or '/'} field mismatch missing={missing} extra={extra} forbidden={forbidden}"
        )
    return obj


def _validate_error(value: Any, path: str) -> None:
    obj = _keys_exact(value, path, {"name", "code", "errno", "syscall", "path", "message"})
    for key in ("name", "code", "errno", "syscall", "path", "message"):
        if obj[key] is not None and not isinstance(obj[key], str):
            raise FeatureSpecError(f"{path}/{key} must be string or null")


def _validate_capture(value: Any, path: str) -> None:
    obj = _keys_exact(value, path, {"ok", "value", "error"})
    if not isinstance(obj["ok"], bool):
        raise FeatureSpecError(f"{path}/ok must be boolean")
    if obj["error"] is not None:
        _validate_error(obj["error"], f"{path}/error")


def _validate_tree(value: Any, path: str) -> None:
    obj = _keys_exact(value, path, {"available", "entries", "errors", "truncated"})
    if not isinstance(obj["available"], bool) or not isinstance(obj["truncated"], bool):
        raise FeatureSpecError(f"{path} availability/truncation must be boolean")
    for index, entry in enumerate(_expect_list(obj["entries"], f"{path}/entries")):
        item_path = f"{path}/entries/{index}"
        _keys_exact(
            entry,
            item_path,
            {"path", "type", "mode_octal", "uid", "gid", "size_bytes", "inode", "device", "nlink", "mtime_ns", "ctime_ns"},
            {"symlink_target"},
        )
    for index, error in enumerate(_expect_list(obj["errors"], f"{path}/errors")):
        item_path = f"{path}/errors/{index}"
        item = _keys_exact(error, item_path, {"path", "error"})
        _validate_error(item["error"], f"{item_path}/error")


def _validate_process_view(value: Any, path: str) -> None:
    obj = _keys_exact(value, path, {"available", "processes", "self", "truncated"}, {"error"})
    if "error" in obj:
        _validate_error(obj["error"], f"{path}/error")
    for index, process in enumerate(_expect_list(obj["processes"], f"{path}/processes")):
        item_path = f"{path}/processes/{index}"
        item = _expect_mapping(process, item_path)
        if "error" in item:
            _keys_exact(item, item_path, {"pid", "error"})
            _validate_error(item["error"], f"{item_path}/error")
        else:
            _keys_exact(
                item,
                item_path,
                {"pid", "cmdline", "cmdline_byte_length", "cmdline_sha256", "status", "pid_namespace", "mount_namespace"},
            )
            _expect_list(item["cmdline"], f"{item_path}/cmdline")
            _keys_exact(item["status"], f"{item_path}/status", set(), {"name", "state", "ppid", "uid", "gid", "threads"})
    if obj["self"] is not None:
        self_obj = _keys_exact(
            obj["self"],
            f"{path}/self",
            {"cgroup", "mountinfo", "status", "pid_namespace", "mount_namespace"},
        )
        for key in ("cgroup", "mountinfo", "status"):
            item_path = f"{path}/self/{key}"
            item = _expect_mapping(self_obj[key], item_path)
            if "error" in item:
                _keys_exact(item, item_path, {"error"})
                _validate_error(item["error"], f"{item_path}/error")
            else:
                _keys_exact(item, item_path, {"byte_length", "sha256"})


def validate_receipt(receipt: Any) -> dict[str, Any]:
    root = _keys_exact(receipt, "", ROOT_FIELDS)
    if root["schema"] != INPUT_SCHEMA:
        raise FeatureSpecError(f"wrong receipt schema: {root['schema']!r}")
    if root["collector_version"] != EXPECTED_COLLECTOR_VERSION:
        raise FeatureSpecError(f"unexpected collector version: {root['collector_version']!r}")

    contract = _keys_exact(
        root["contract"],
        "/contract",
        {"mode", "lawful_truth_api_calls", "network_calls", "accepted_input_fields", "prohibited_control_fields", "does_not_score_leakage", "does_not_rank_treatments"},
    )
    expected_contract = {
        "mode": "LEAK_ONLY_FEATURE_COLLECTION",
        "lawful_truth_api_calls": 0,
        "network_calls": 0,
        "accepted_input_fields": ["schema"],
        "prohibited_control_fields": ["expected", "order", "role", "seed"],
        "does_not_score_leakage": True,
        "does_not_rank_treatments": True,
    }
    if contract != expected_contract:
        raise FeatureSpecError("/contract differs from the frozen collector contract")

    input_contract = _keys_exact(root["input_contract"], "/input_contract", {"parsed", "byte_length", "sha256"})
    parsed = _keys_exact(input_contract["parsed"], "/input_contract/parsed", {"schema"})
    if parsed["schema"] != "WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1":
        raise FeatureSpecError("wrong /input_contract/parsed/schema")
    subject = _keys_exact(root["subject_input"], "/subject_input", {"path", "byte_length", "sha256"})
    if subject["path"] != "$CHALLENGE/input.bin":
        raise FeatureSpecError("wrong fixed /subject_input/path")

    for index, value in enumerate(_expect_list(root["argv"], "/argv")):
        if not isinstance(value, str):
            raise FeatureSpecError(f"/argv/{index} must be string")
    for index, value in enumerate(_expect_list(root["environment"], "/environment")):
        _keys_exact(value, f"/environment/{index}", {"key", "value_byte_length", "value_sha256"})
    if not isinstance(root["cwd"], str):
        raise FeatureSpecError("/cwd must be string")

    hostname = _keys_exact(root["hostname"], "/hostname", {"os_hostname", "etc_hostname"})
    _validate_capture(hostname["os_hostname"], "/hostname/os_hostname")
    if isinstance(hostname["etc_hostname"], dict):
        error_wrapper = _keys_exact(hostname["etc_hostname"], "/hostname/etc_hostname", {"error"})
        _validate_error(error_wrapper["error"], "/hostname/etc_hostname/error")
    elif not isinstance(hostname["etc_hostname"], str):
        raise FeatureSpecError("/hostname/etc_hostname must be string or error object")

    identity = _keys_exact(root["identity"], "/identity", {"pid", "ppid", "uid", "euid", "gid", "egid", "groups", "user_info"})
    _expect_list(identity["groups"], "/identity/groups")
    user_info = _expect_mapping(identity["user_info"], "/identity/user_info")
    if "error" in user_info:
        _keys_exact(user_info, "/identity/user_info", {"error"})
        _validate_error(user_info["error"], "/identity/user_info/error")
    else:
        _keys_exact(user_info, "/identity/user_info", {"username", "uid", "gid", "homedir", "shell"})

    trees = _keys_exact(root["directory_trees"], "/directory_trees", {"challenge", "cwd", "out", "tmp", "self-fd"})
    for tree_name in sorted(trees):
        _validate_tree(trees[tree_name], f"/directory_trees/{tree_name}")
    _validate_process_view(root["process_view"], "/process_view")

    for index, canary in enumerate(_expect_list(root["visible_canaries"], "/visible_canaries")):
        _keys_exact(canary, f"/visible_canaries/{index}", {"source", "location", "token_byte_length", "token_sha256"})

    timing = _keys_exact(
        root["timing"],
        "/timing",
        {"wall_clock_start_ms", "wall_clock_end_ms", "monotonic_start_ns", "monotonic_end_ns", "process_uptime_seconds", "os_uptime_seconds", "immediate_delta_ns", "input_stat_elapsed_ns", "error_shape_probes"},
    )
    _validate_capture(timing["process_uptime_seconds"], "/timing/process_uptime_seconds")
    _validate_capture(timing["os_uptime_seconds"], "/timing/os_uptime_seconds")
    _expect_list(timing["immediate_delta_ns"], "/timing/immediate_delta_ns")
    _expect_list(timing["input_stat_elapsed_ns"], "/timing/input_stat_elapsed_ns")
    for index, probe in enumerate(_expect_list(timing["error_shape_probes"], "/timing/error_shape_probes")):
        item_path = f"/timing/error_shape_probes/{index}"
        item = _keys_exact(probe, item_path, {"name", "ok", "elapsed_ns", "error"})
        if item["error"] is not None:
            _validate_error(item["error"], f"{item_path}/error")

    window = _keys_exact(root["collection_window"], "/collection_window", {"start", "end"})
    for side in ("start", "end"):
        _keys_exact(window[side], f"/collection_window/{side}", {"wall_clock_ms", "monotonic_ns"})
    return root


def _flatten_leaves(value: Any, path: str = "") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        result: list[tuple[str, Any]] = []
        for key in sorted(value):
            result.extend(_flatten_leaves(value[key], _path_join(path, key)))
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            result.extend(_flatten_leaves(item, _path_join(path, index)))
        return result
    return [(path or "/", value)]


def _excluded_reason(path: str) -> str | None:
    if path.startswith("/contract/"):
        return "validated collector self-description constant"
    return EXCLUDED_REASONS.get(path)


def _family_for(path: str) -> str:
    if path.startswith("/input_contract/") or path.startswith("/subject_input/"):
        return "F01_PUBLIC_INPUT_BYTES"
    if path.startswith("/argv/") or path.startswith("/environment/") or path == "/cwd":
        return "F02_ARGV_ENV_CWD"
    if path.startswith("/hostname/") or path.startswith("/identity/"):
        return "F03_HOSTNAME_IDENTITY"
    if path.startswith("/directory_trees/self-fd/") or path.startswith("/process_view/"):
        return "F05_PROCESS_NAMESPACE_FD"
    if path.startswith("/directory_trees/"):
        return "F04_DIRECTORY_AND_SHARED_STATE"
    if path.startswith("/timing/") or path.startswith("/collection_window/"):
        return "F06_TIMING_AND_ERRORS"
    if path.startswith("/visible_canaries/"):
        return "F07_VISIBLE_CANARY"
    raise FeatureSpecError(f"no frozen feature family for included leaf {path}")


def _normalized_context(path: str) -> str:
    parts = path.split("/")
    normalized = []
    for index, part in enumerate(parts):
        if part.isdigit():
            parent = parts[index - 1] if index else ""
            if parent in {"argv", "groups", "cmdline", "immediate_delta_ns", "input_stat_elapsed_ns", "error_shape_probes"}:
                normalized.append(f"@{int(part):04d}")
            else:
                normalized.append("*")
        else:
            normalized.append(part)
    return "/".join(normalized)


def _is_sha_leaf(path: str) -> bool:
    return _leaf_field_name(path) in SHA_FIELD_NAMES


def _leaf_field_name(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if not parts:
        return ""
    if parts[-1].isdigit() and len(parts) > 1:
        return parts[-2]
    return parts[-1]


def _is_numeric_string(path: str, value: str) -> bool:
    name = _leaf_field_name(path)
    return bool(re.fullmatch(r"-?[0-9]+", value)) and (
        name in NUMERIC_FIELD_NAMES
        or name.endswith("_ns")
        or name.endswith("_ms")
        or name.endswith("_bytes")
        or name.endswith("_seconds")
    )


class FeatureBuilder:
    def __init__(self) -> None:
        self.numeric_samples: dict[str, list[int | float]] = defaultdict(list)
        self.numeric_direct: Counter[str] = Counter()
        self.categories: Counter[tuple[str, str, str]] = Counter()

    def add_category(self, family: str, context: str, value: Any) -> None:
        domain = f"WAVE025_CATEGORY_V1\x00{family}\x00{context}\x00".encode("utf-8")
        digest = sha256(domain + canonical_bytes(value)[:-1])
        self.categories[(family, context, digest)] += 1

    def add_numeric(self, family: str, context: str, value: int | float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FeatureSpecError(f"non-numeric value at {context}")
        if isinstance(value, float) and not math.isfinite(value):
            raise FeatureSpecError(f"non-finite numeric value at {context}")
        self.numeric_samples[f"{family}|{context}"].append(value)

    def increment(self, family: str, context: str, count: int = 1) -> None:
        self.numeric_direct[f"{family}|{context}"] += count

    def add_string(self, family: str, context: str, value: str, *, sha_leaf: bool = False) -> None:
        self.add_category(family, context, value)
        encoded = value.encode("utf-8")
        self.add_numeric(family, f"{context}|shape.byte_length", len(encoded))
        self.add_numeric(family, f"{context}|shape.codepoint_length", len(value))
        if sha_leaf:
            return
        counts = {
            "ascii_alpha": sum(byte < 128 and chr(byte).isalpha() for byte in encoded),
            "ascii_digit": sum(48 <= byte <= 57 for byte in encoded),
            "slash": encoded.count(b"/"),
            "dot": encoded.count(b"."),
            "dash": encoded.count(b"-"),
            "underscore": encoded.count(b"_"),
            "colon": encoded.count(b":"),
            "whitespace": sum(byte < 128 and chr(byte).isspace() for byte in encoded),
            "non_ascii": sum(byte >= 128 for byte in encoded),
        }
        for name, count in counts.items():
            self.add_numeric(family, f"{context}|shape.{name}", count)
        if len(encoded) > MAX_STRING_BYTES:
            scanned = encoded[: MAX_STRING_BYTES // 2] + encoded[-MAX_STRING_BYTES // 2 :]
            self.increment(family, f"lexical|string_truncated", 1)
        else:
            scanned = encoded
        for n in NGRAM_SIZES:
            if len(scanned) < n:
                continue
            for offset in range(len(scanned) - n + 1):
                gram = scanned[offset : offset + n]
                digest = hashlib.sha256(b"WAVE025_UTF8_NGRAM_V1\x00" + bytes([n]) + gram).digest()
                bucket = int.from_bytes(digest[:4], "big") % NGRAM_BUCKETS
                # N is already domain-separated into the bucket hash.  Sharing
                # one bounded block across n=1..4 keeps the 1600-slot formal
                # suite tractable without erasing the n-gram distinction.
                self.increment(family, f"lexical|b{bucket:04d}", 1)

    def add_scalar(self, family: str, context: str, path: str, value: Any) -> None:
        if value is None or isinstance(value, bool):
            self.add_category(family, context, value)
            return
        if isinstance(value, (int, float)):
            self.add_numeric(family, context, value)
            self.add_category(family, f"{context}|exact_numeric", value)
            if isinstance(value, int):
                for modulus in INTEGER_RESIDUES:
                    self.add_category(family, f"{context}|mod_{modulus}", value % modulus)
            return
        if isinstance(value, str):
            if _is_numeric_string(path, value):
                number = int(value, 10)
                self.add_numeric(family, context, number)
                self.add_category(family, f"{context}|exact_numeric", value)
                for modulus in INTEGER_RESIDUES:
                    self.add_category(family, f"{context}|mod_{modulus}", number % modulus)
                return
            self.add_string(family, context, value, sha_leaf=_is_sha_leaf(path))
            return
        raise FeatureSpecError(f"unsupported scalar type at {path}: {type(value).__name__}")

    def finish_numeric(self) -> dict[str, int | float]:
        result: dict[str, int | float] = dict(self.numeric_direct)
        for key in sorted(self.numeric_samples):
            values = self.numeric_samples[key]
            if len(values) == 1:
                result[f"{key}|value"] = values[0]
                continue
            sorted_values = sorted(values)
            count = len(values)
            result[f"{key}|count"] = count
            result[f"{key}|sum"] = math.fsum(values) if any(isinstance(v, float) for v in values) else sum(values)
            result[f"{key}|min"] = sorted_values[0]
            result[f"{key}|max"] = sorted_values[-1]
            result[f"{key}|first"] = values[0]
            result[f"{key}|last"] = values[-1]
            result[f"{key}|lower_middle"] = sorted_values[(count - 1) // 2]
            result[f"{key}|upper_middle"] = sorted_values[count // 2]
            if count > 1:
                deltas = [values[index] - values[index - 1] for index in range(1, count)]
                absolute = [abs(delta) for delta in deltas]
                result[f"{key}|adjacent_absolute_delta_sum"] = (
                    math.fsum(absolute) if any(isinstance(v, float) for v in absolute) else sum(absolute)
                )
                result[f"{key}|adjacent_absolute_delta_max"] = max(absolute)
                result[f"{key}|positive_step_count"] = sum(delta > 0 for delta in deltas)
                result[f"{key}|negative_step_count"] = sum(delta < 0 for delta in deltas)
                result[f"{key}|zero_step_count"] = sum(delta == 0 for delta in deltas)
        return {key: result[key] for key in sorted(result)}

    def finish_categories(self) -> list[dict[str, Any]]:
        return [
            {"family": family, "context": context, "value_sha256": digest, "count": self.categories[(family, context, digest)]}
            for family, context, digest in sorted(self.categories)
        ]


def _walk_features(value: Any, path: str, builder: FeatureBuilder) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            child_path = _path_join(path, key)
            if _excluded_reason(child_path) is None and not child_path.startswith("/contract/"):
                _walk_features(value[key], child_path, builder)
        return
    if isinstance(value, list):
        family = _family_for(path + "/0")
        context = _normalized_context(path)
        builder.add_numeric(family, f"{context}|list_length", len(value))
        for index, item in enumerate(value):
            item_path = _path_join(path, index)
            builder.add_category(family, f"{context}|record_bag", item)
            _walk_features(item, item_path, builder)
            # Preserve each ordered position above, and additionally expose a
            # role-sensitive series summary for numeric scalar arrays such as
            # timing jitter, stat latency, and supplementary groups.
            if (
                isinstance(item, (int, float))
                and not isinstance(item, bool)
            ) or (isinstance(item, str) and _is_numeric_string(item_path, item)):
                number = int(item, 10) if isinstance(item, str) else item
                builder.add_numeric(family, f"{context}/*", number)
        return
    family = _family_for(path)
    builder.add_scalar(family, _normalized_context(path), path, value)


def extract_receipt(receipt: Any, source_bytes: bytes | None = None) -> dict[str, Any]:
    root = validate_receipt(receipt)
    leaves = _flatten_leaves(root)
    included: list[str] = []
    excluded: list[dict[str, str]] = []
    for path, value in leaves:
        reason = _excluded_reason(path)
        if reason is None:
            _family_for(path)
            included.append(path)
        else:
            excluded.append(
                {
                    "path": path,
                    "reason": reason,
                    "value_sha256": sha256(canonical_bytes(value)[:-1]),
                }
            )
    if len(included) + len(excluded) != len(leaves):
        raise FeatureSpecError("raw leaf audit is not a complete partition")

    builder = FeatureBuilder()
    for key in sorted(root):
        top_path = _path_join("", key)
        if _excluded_reason(top_path) is not None or top_path == "/contract":
            continue
        _walk_features(root[key], top_path, builder)

    if source_bytes is None:
        source_bytes = canonical_bytes(root)
    result = {
        "schema": OUTPUT_SCHEMA,
        "extractor_version": EXTRACTOR_VERSION,
        "source": {
            "receipt_schema": INPUT_SCHEMA,
            "receipt_bytes_sha256": sha256(source_bytes),
            "receipt_hash_is_predictor": False,
        },
        "features": {
            "numeric": builder.finish_numeric(),
            "categorical": builder.finish_categories(),
        },
        "audit": {
            "raw_leaf_count": len(leaves),
            "included_leaf_count": len(included),
            "excluded_leaf_count": len(excluded),
            "included_paths_sha256": sha256(canonical_bytes(sorted(included))),
            "excluded_fields": sorted(excluded, key=lambda item: item["path"]),
            "unclassified_paths": [],
            "only_features_members_are_predictors": True,
        },
    }
    return result


def load_and_extract(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FeatureSpecError(f"invalid UTF-8 JSON receipt: {error}") from error
    return extract_receipt(value, raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract Wave025 candidate-visible features")
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        result = load_and_extract(args.receipt)
    except (OSError, FeatureSpecError) as error:
        print(f"feature extraction failed: {error}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
