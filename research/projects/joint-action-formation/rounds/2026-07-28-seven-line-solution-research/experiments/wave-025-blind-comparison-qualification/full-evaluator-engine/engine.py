#!/usr/bin/env python3
"""Independent full-leaf Wave025 evaluator engine.

This module intentionally consumes only raw collector receipts plus the frozen
FEATURE-SPEC/profile.  It is not wired to the batch runner and never emits a
qualification verdict or a treatment ranking.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import pathlib
import platform
import re
import sys
import warnings
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple


_THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
}
_NUMPY_PRELOADED = "numpy" in sys.modules
_PREIMPORT_ENV_MISMATCH = {
    key: os.environ.get(key)
    for key, value in _THREAD_ENV.items()
    if os.environ.get(key) not in (None, value)
}
for _key, _value in _THREAD_ENV.items():
    os.environ[_key] = _value

import numpy as np  # noqa: E402  (provider environment must be bound first)


FAMILIES = (
    "F01_PUBLIC_INPUT_BYTES",
    "F02_ARGV_ENV_CWD",
    "F03_HOSTNAME_IDENTITY",
    "F04_DIRECTORY_AND_SHARED_STATE",
    "F05_PROCESS_NAMESPACE_FD",
    "F06_TIMING_AND_ERRORS",
    "F07_VISIBLE_CANARY",
)
CLASSIFIERS = (
    "C01_EXACT_CATEGORICAL_SCAN",
    "C02_L2_LOGISTIC",
    "C03_DECISION_STUMP",
    "C04_BOUNDED_TREE",
    "C05_KNN_11",
)
EXPECTED_TOP_LEVEL = {
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
NUMERIC_NAMES = {
    "byte_length", "value_byte_length", "token_byte_length", "size_bytes",
    "inode", "device", "nlink", "mtime_ns", "ctime_ns", "pid", "ppid",
    "uid", "euid", "gid", "egid", "threads", "elapsed_ns", "wall_clock_ms",
    "monotonic_ns", "wall_clock_start_ms", "wall_clock_end_ms",
    "monotonic_start_ns", "monotonic_end_ns", "process_uptime_seconds",
    "os_uptime_seconds", "cmdline_byte_length",
}
SHAPE_NAMES = (
    "byte_length", "codepoint_length", "ascii_alpha", "ascii_digit", "slash",
    "dot", "dash", "underscore", "colon", "whitespace", "non_ascii",
)
RESIDUE_MODULI = (2, 4, 8, 16, 256)
CAT_BUCKETS = 16384
NGRAM_BUCKETS = 4096


class EngineError(RuntimeError):
    """Base fail-closed engine exception."""


class SpecMismatch(EngineError):
    pass


class ReceiptSchemaError(EngineError):
    pass


class ProviderMismatch(EngineError):
    pass


class NonFiniteFeature(EngineError):
    pass


class ReplayMismatch(EngineError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def _escape_pointer(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def scalar_leaves(value: Any, path: str = "") -> Iterable[Tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value):
            yield from scalar_leaves(value[key], f"{path}/{_escape_pointer(str(key))}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from scalar_leaves(item, f"{path}/{index}")
    else:
        yield path or "/", value


def _keys(value: Any, required: Iterable[str], optional: Iterable[str] = (), where: str = "") -> None:
    if not isinstance(value, dict):
        raise ReceiptSchemaError(f"{where or '/'} must be an object")
    required_set, optional_set = set(required), set(optional)
    actual = set(value)
    missing = sorted(required_set - actual)
    unknown = sorted(actual - required_set - optional_set)
    if missing or unknown:
        raise ReceiptSchemaError(f"{where or '/'} keys mismatch missing={missing} unknown={unknown}")


def _array(value: Any, where: str) -> list:
    if not isinstance(value, list):
        raise ReceiptSchemaError(f"{where} must be an array")
    return value


def _validate_error(value: Any, where: str) -> None:
    if value is None:
        return
    _keys(value, {"name", "code", "errno", "syscall", "path", "message"}, where=where)


def _validate_capture(value: Any, where: str) -> None:
    _keys(value, {"ok", "value", "error"}, where=where)
    _validate_error(value["error"], f"{where}/error")


def _validate_tree(value: Any, where: str) -> None:
    _keys(value, {"available", "entries", "errors", "truncated"}, where=where)
    for index, entry in enumerate(_array(value["entries"], f"{where}/entries")):
        _keys(
            entry,
            {"path", "type", "mode_octal", "uid", "gid", "size_bytes", "inode",
             "device", "nlink", "mtime_ns", "ctime_ns"},
            {"symlink_target"},
            f"{where}/entries/{index}",
        )
    for index, item in enumerate(_array(value["errors"], f"{where}/errors")):
        _keys(item, {"path", "error"}, where=f"{where}/errors/{index}")
        _validate_error(item["error"], f"{where}/errors/{index}/error")


def validate_receipt(receipt: Any) -> None:
    _keys(receipt, EXPECTED_TOP_LEVEL, where="/")
    if receipt["schema"] != "WAVE025_LEAK_ONLY_FEATURES_V1":
        raise ReceiptSchemaError("wrong collector receipt schema")
    _keys(
        receipt["contract"],
        {"mode", "lawful_truth_api_calls", "network_calls", "accepted_input_fields",
         "prohibited_control_fields", "does_not_score_leakage", "does_not_rank_treatments"},
        where="/contract",
    )
    _keys(receipt["input_contract"], {"parsed", "byte_length", "sha256"}, where="/input_contract")
    _keys(receipt["input_contract"]["parsed"], {"schema"}, where="/input_contract/parsed")
    _keys(receipt["subject_input"], {"path", "byte_length", "sha256"}, where="/subject_input")
    for index, item in enumerate(_array(receipt["environment"], "/environment")):
        _keys(item, {"key", "value_byte_length", "value_sha256"}, where=f"/environment/{index}")
    _array(receipt["argv"], "/argv")
    _keys(receipt["hostname"], {"os_hostname", "etc_hostname"}, where="/hostname")
    _validate_capture(receipt["hostname"]["os_hostname"], "/hostname/os_hostname")
    if isinstance(receipt["hostname"]["etc_hostname"], dict):
        _keys(receipt["hostname"]["etc_hostname"], {"error"}, where="/hostname/etc_hostname")
        _validate_error(receipt["hostname"]["etc_hostname"]["error"], "/hostname/etc_hostname/error")
    _keys(receipt["identity"], {"pid", "ppid", "uid", "euid", "gid", "egid", "groups", "user_info"}, where="/identity")
    _array(receipt["identity"]["groups"], "/identity/groups")
    user_info = receipt["identity"]["user_info"]
    if isinstance(user_info, dict) and "error" in user_info:
        _keys(user_info, {"error"}, where="/identity/user_info")
        _validate_error(user_info["error"], "/identity/user_info/error")
    else:
        _keys(user_info, {"username", "uid", "gid", "homedir", "shell"}, where="/identity/user_info")
    _keys(receipt["directory_trees"], {"challenge", "cwd", "out", "tmp", "self-fd"}, where="/directory_trees")
    for name, tree in receipt["directory_trees"].items():
        _validate_tree(tree, f"/directory_trees/{name}")
    process = receipt["process_view"]
    _keys(process, {"available", "processes", "self", "truncated"}, {"error"}, "/process_view")
    if "error" in process:
        _validate_error(process["error"], "/process_view/error")
    for index, item in enumerate(_array(process["processes"], "/process_view/processes")):
        if "error" in item:
            _keys(item, {"pid", "error"}, where=f"/process_view/processes/{index}")
            _validate_error(item["error"], f"/process_view/processes/{index}/error")
        else:
            _keys(item, {"pid", "cmdline", "cmdline_byte_length", "cmdline_sha256", "status",
                         "pid_namespace", "mount_namespace"}, where=f"/process_view/processes/{index}")
            _array(item["cmdline"], f"/process_view/processes/{index}/cmdline")
            _keys(item["status"], set(), {"name", "state", "ppid", "uid", "gid", "threads"},
                  f"/process_view/processes/{index}/status")
    if process["self"] is not None:
        _keys(process["self"], {"cgroup", "mountinfo", "status", "pid_namespace", "mount_namespace"}, where="/process_view/self")
        for name in ("cgroup", "mountinfo", "status"):
            item = process["self"][name]
            if "error" in item:
                _keys(item, {"error"}, where=f"/process_view/self/{name}")
                _validate_error(item["error"], f"/process_view/self/{name}/error")
            else:
                _keys(item, {"byte_length", "sha256"}, where=f"/process_view/self/{name}")
    timing = receipt["timing"]
    _keys(timing, {"wall_clock_start_ms", "wall_clock_end_ms", "monotonic_start_ns",
                   "monotonic_end_ns", "process_uptime_seconds", "os_uptime_seconds",
                   "immediate_delta_ns", "input_stat_elapsed_ns", "error_shape_probes"}, where="/timing")
    _validate_capture(timing["process_uptime_seconds"], "/timing/process_uptime_seconds")
    _validate_capture(timing["os_uptime_seconds"], "/timing/os_uptime_seconds")
    _array(timing["immediate_delta_ns"], "/timing/immediate_delta_ns")
    _array(timing["input_stat_elapsed_ns"], "/timing/input_stat_elapsed_ns")
    for index, item in enumerate(_array(timing["error_shape_probes"], "/timing/error_shape_probes")):
        _keys(item, {"name", "ok", "elapsed_ns", "error"}, where=f"/timing/error_shape_probes/{index}")
        _validate_error(item["error"], f"/timing/error_shape_probes/{index}/error")
    _keys(receipt["collection_window"], {"start", "end"}, where="/collection_window")
    for name in ("start", "end"):
        _keys(receipt["collection_window"][name], {"wall_clock_ms", "monotonic_ns"}, where=f"/collection_window/{name}")
    for index, item in enumerate(_array(receipt["visible_canaries"], "/visible_canaries")):
        _keys(item, {"source", "location", "token_byte_length", "token_sha256"}, where=f"/visible_canaries/{index}")


def classify_leaf(path: str) -> Tuple[str, str]:
    if path in ("/schema", "/collector_version", "/input_contract/parsed/schema", "/subject_input/path"):
        return "EXCLUDED", "FROZEN_TRANSPORT_OR_PATH_CONSTANT"
    if path.startswith("/contract/"):
        return "EXCLUDED", "COLLECTOR_SELF_DESCRIPTION_CONSTANT"
    if path.startswith("/directory_trees/self-fd/"):
        return "INCLUDED", "F05_PROCESS_NAMESPACE_FD"
    roots = (
        (("/input_contract/byte_length", "/input_contract/sha256", "/subject_input/byte_length", "/subject_input/sha256"), "F01_PUBLIC_INPUT_BYTES"),
        (("/argv/", "/environment/", "/cwd"), "F02_ARGV_ENV_CWD"),
        (("/hostname/", "/identity/"), "F03_HOSTNAME_IDENTITY"),
        (("/directory_trees/",), "F04_DIRECTORY_AND_SHARED_STATE"),
        (("/process_view/",), "F05_PROCESS_NAMESPACE_FD"),
        (("/timing/", "/collection_window/"), "F06_TIMING_AND_ERRORS"),
        (("/visible_canaries/",), "F07_VISIBLE_CANARY"),
    )
    for prefixes, family in roots:
        if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes):
            return "INCLUDED", family
    return "UNCLASSIFIED", "NO_FROZEN_PARTITION_RULE"


def _context(path: str) -> str:
    return re.sub(r"/\d+(?=/|$)", "/[]", path)


def _scalar_repr(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _domain_hash(domain: str, value: bytes) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + value).hexdigest()


def _string_shape(value: str) -> Dict[str, float]:
    raw = value.encode("utf-8")
    return {
        "byte_length": float(len(raw)),
        "codepoint_length": float(len(value)),
        "ascii_alpha": float(sum(ch.isascii() and ch.isalpha() for ch in value)),
        "ascii_digit": float(sum(ch.isascii() and ch.isdigit() for ch in value)),
        "slash": float(value.count("/")), "dot": float(value.count(".")),
        "dash": float(value.count("-")), "underscore": float(value.count("_")),
        "colon": float(value.count(":")), "whitespace": float(sum(ch.isspace() for ch in value)),
        "non_ascii": float(sum(not ch.isascii() for ch in value)),
    }


def _ngram_bytes(value: str) -> Tuple[bytes, bool]:
    raw = value.encode("utf-8")
    if len(raw) <= 4096:
        return raw, False
    return raw[:2048] + raw[-2048:], True


def _numeric_value(path: str, value: Any) -> Optional[float]:
    name = path.rsplit("/", 1)[-1]
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str) and (name in NUMERIC_NAMES or name.endswith(("_ns", "_ms", "_bytes", "_seconds"))) and re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value):
        result = float(value)
    else:
        return None
    if not math.isfinite(result):
        raise NonFiniteFeature(path)
    return result


def _series(values: Sequence[float]) -> Dict[str, float]:
    ordered = list(values)
    sorted_values = sorted(ordered)
    n = len(ordered)
    if not n:
        return {}
    deltas = [abs(ordered[i] - ordered[i - 1]) for i in range(1, n)]
    steps = [ordered[i] - ordered[i - 1] for i in range(1, n)]
    return {
        "count": float(n), "sum": float(sum(ordered)), "min": float(min(ordered)),
        "max": float(max(ordered)), "first": ordered[0], "last": ordered[-1],
        "lower_middle": sorted_values[(n - 1) // 2], "upper_middle": sorted_values[n // 2],
        "adjacent_absolute_delta_sum": float(sum(deltas)),
        "adjacent_absolute_delta_max": float(max(deltas, default=0.0)),
        "positive_step_count": float(sum(step > 0 for step in steps)),
        "negative_step_count": float(sum(step < 0 for step in steps)),
        "zero_step_count": float(sum(step == 0 for step in steps)),
    }


@dataclass(frozen=True)
class FeatureVector:
    numeric: Mapping[str, float]
    categorical: Mapping[str, int]
    audit: Mapping[str, Any]

    def predictors_json(self) -> Dict[str, Any]:
        return {
            "schema": "WAVE025_FULL_ENGINE_FEATURE_VECTOR_V1",
            "features": {
                "numeric": {key: self.numeric[key] for key in sorted(self.numeric)},
                "categorical": {key: self.categorical[key] for key in sorted(self.categorical)},
            },
        }


class RawReceiptFeatureProvider:
    provider_id = "WAVE025_RAW_FULL_LEAF_PROVIDER_V1"

    def extract(self, receipt: Mapping[str, Any]) -> FeatureVector:
        validate_receipt(receipt)
        numeric_values: MutableMapping[Tuple[str, str], List[float]] = defaultdict(list)
        shape_values: MutableMapping[Tuple[str, str, str], float] = defaultdict(float)
        categories: Counter[str] = Counter()
        included: List[str] = []
        excluded: List[Dict[str, str]] = []
        unclassified: List[str] = []
        for path, value in scalar_leaves(receipt):
            disposition, reason = classify_leaf(path)
            if disposition == "EXCLUDED":
                excluded.append({"path": path, "reason": reason})
                continue
            if disposition != "INCLUDED":
                unclassified.append(path)
                continue
            family = reason
            included.append(path)
            context = _context(path)
            if isinstance(value, float) and not math.isfinite(value):
                raise NonFiniteFeature(path)
            rendered = _scalar_repr(value).encode("utf-8")
            categories[f"{family}|exact|{context}|{_domain_hash(family + ':EXACT', rendered)}"] += 1
            number = _numeric_value(path, value)
            if number is not None:
                numeric_values[(family, context)].append(number)
                integer = int(number)
                if float(integer) == number:
                    for modulus in RESIDUE_MODULI:
                        categories[f"{family}|residue|{context}|m{modulus}|{integer % modulus}"] += 1
            if isinstance(value, str) and not path.endswith("sha256"):
                for name, count in _string_shape(value).items():
                    shape_values[(family, context, name)] += count
                scan, truncated = _ngram_bytes(value)
                categories[f"{family}|string-truncated|{context}|{int(truncated)}"] += 1
                for n in (1, 2, 3, 4):
                    for offset in range(max(0, len(scan) - n + 1)):
                        digest = hashlib.sha256(b"WAVE025_UTF8_NGRAM_V1\x00" + scan[offset:offset + n]).digest()
                        bucket = int.from_bytes(digest, "big") % NGRAM_BUCKETS
                        categories[f"{family}|ngram|{bucket:04d}"] += 1
        if unclassified:
            raise ReceiptSchemaError(f"unclassified scalar leaves: {sorted(unclassified)}")
        numeric: Dict[str, float] = {}
        for (family, context), values in sorted(numeric_values.items()):
            for name, result in _series(values).items():
                numeric[f"{family}|numeric|{context}|{name}"] = result
        for (family, context, name), result in sorted(shape_values.items()):
            numeric[f"{family}|shape|{context}|{name}"] = float(result)
        # Record-bag categories preserve exact composite rows without exposing strings.
        def add_records(node: Any, path: str = "") -> None:
            if isinstance(node, list):
                disposition, family = classify_leaf(f"{path}/0/_record_probe" if node else f"{path}/0")
                for item in node:
                    if isinstance(item, dict) and disposition == "INCLUDED":
                        digest = _domain_hash(family + ":RECORD", canonical_bytes(item))
                        categories[f"{family}|record|{_context(path)}|{digest}"] += 1
                    add_records(item, f"{path}/0")
            elif isinstance(node, dict):
                for key in sorted(node):
                    add_records(node[key], f"{path}/{_escape_pointer(str(key))}")
        add_records(receipt)
        audit = {
            "raw_leaf_count": len(included) + len(excluded),
            "included_leaf_count": len(included),
            "excluded_leaf_count": len(excluded),
            "included_paths_sha256": canonical_sha256(sorted(included)),
            "excluded_fields_with_path_and_reason": excluded,
            "unclassified_paths_empty": True,
            "families_present": sorted({key.split("|", 1)[0] for key in list(numeric) + list(categories)}),
        }
        return FeatureVector(numeric=numeric, categorical=dict(categories), audit=audit)


def load_bound_spec(profile_path: pathlib.Path) -> Tuple[Dict[str, Any], Dict[str, Any], pathlib.Path]:
    profile_bytes = profile_path.read_bytes()
    profile = json.loads(profile_bytes)
    binding = profile["feature_spec_binding"]
    spec_path = profile_path.parent / binding["path_from_profile"]
    spec_bytes = spec_path.read_bytes()
    if len(spec_bytes) != binding["raw_byte_length"] or sha256_bytes(spec_bytes) != binding["raw_bytes_sha256"]:
        raise SpecMismatch("FEATURE-SPEC exact byte binding mismatch")
    spec = json.loads(spec_bytes)
    if spec.get("schema") != binding["expected_schema"] or spec.get("spec_version") != binding["expected_spec_version"]:
        raise SpecMismatch("FEATURE-SPEC schema/version mismatch")
    for section in binding["resolved_sections"]:
        pointer = section["json_pointer"]
        value: Any = spec
        for part in pointer.split("/")[1:]:
            value = value[part.replace("~1", "/").replace("~0", "~")]
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if sha256_bytes(payload) != section["canonical_json_sha256"]:
            raise SpecMismatch(f"bound section mismatch: {pointer}")
    return profile, spec, spec_path


def verify_execution_provider(profile: Mapping[str, Any]) -> Dict[str, Any]:
    expected = profile["execution_provider"]
    problems: List[str] = []
    if _NUMPY_PRELOADED and (_PREIMPORT_ENV_MISMATCH or any(os.environ.get(k) != v for k, v in _THREAD_ENV.items())):
        problems.append("numpy was imported before the required single-thread provider binding")
    if sys.implementation.name != "cpython" or platform.python_version() != expected["python"]["version"]:
        problems.append("Python implementation/version mismatch")
    executable_hash = sha256_bytes(pathlib.Path(sys.executable).read_bytes())
    if executable_hash != expected["python"]["executable_sha256"]:
        problems.append("Python executable hash mismatch")
    if np.__version__ != expected["numpy"]["version"]:
        problems.append("NumPy version mismatch")
    distribution = importlib.metadata.distribution("numpy")
    record_path = pathlib.Path(distribution.locate_file(f"numpy-{np.__version__}.dist-info/RECORD"))
    if not record_path.is_file() or sha256_bytes(record_path.read_bytes()) != expected["numpy"]["distribution_record_sha256"]:
        problems.append("NumPy distribution RECORD mismatch")
    if platform.mac_ver()[0] != expected["platform"]["os"].removeprefix("macOS-"):
        problems.append("OS version mismatch")
    if platform.machine() != expected["platform"]["machine"] or sys.byteorder != expected["platform"]["byte_order"]:
        problems.append("machine or byte order mismatch")
    for key, value in expected["single_thread_environment"].items():
        if os.environ.get(key) != value:
            problems.append(f"environment mismatch: {key}")
    if problems:
        raise ProviderMismatch("; ".join(problems))
    return {
        "provider_id": expected["provider_id"],
        "python_executable_sha256": executable_hash,
        "numpy_version": np.__version__,
        "numpy_record_sha256": sha256_bytes(record_path.read_bytes()),
        "dtype": "float64",
        "einsum_optimize": False,
    }


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * fraction
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return float(ordered[lower])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _cat_hash(token: str) -> Tuple[int, float]:
    digest = hashlib.sha256(b"WAVE025_CATEGORICAL_MODEL_HASH_V1\x00" + token.encode("utf-8")).digest()
    bucket = int.from_bytes(digest, "big") % CAT_BUCKETS
    sign = 1.0 if digest[0] & 1 else -1.0
    return bucket, sign


@dataclass
class VectorSpace:
    numeric_ids: List[str]
    medians: Dict[str, float]
    scales: Dict[str, float]
    numeric_positions: Dict[str, Tuple[int, int]]
    family_cat_offsets: Dict[str, int]
    family_norm_positions: Dict[str, int]
    dimension: int

    @classmethod
    def fit(cls, vectors: Sequence[FeatureVector]) -> "VectorSpace":
        numeric_ids = sorted({key for vector in vectors for key in vector.numeric})
        medians: Dict[str, float] = {}
        scales: Dict[str, float] = {}
        positions: Dict[str, Tuple[int, int]] = {}
        cursor = 0
        for key in numeric_ids:
            values = [float(vector.numeric[key]) for vector in vectors if key in vector.numeric]
            if not all(math.isfinite(value) for value in values):
                raise NonFiniteFeature(key)
            medians[key] = _percentile(values, 0.5) if values else 0.0
            iqr_scaled = (_percentile(values, 0.75) - _percentile(values, 0.25)) / 1.349 if values else 0.0
            scales[key] = max(iqr_scaled, 1.0) if iqr_scaled == 0.0 else iqr_scaled
            positions[key] = (cursor, cursor + 1)
            cursor += 2
        family_offsets: Dict[str, int] = {}
        for family in FAMILIES:
            family_offsets[family] = cursor
            cursor += CAT_BUCKETS
        norm_positions = {}
        for family in FAMILIES:
            norm_positions[family] = cursor
            cursor += 1
        return cls(numeric_ids, medians, scales, positions, family_offsets, norm_positions, cursor)

    def normalized(self, vector: FeatureVector, *, clip_numeric: bool) -> Dict[int, float]:
        by_family: Dict[str, Dict[int, float]] = {family: {} for family in FAMILIES}
        for key in self.numeric_ids:
            family = key.split("|", 1)[0]
            value_position, missing_position = self.numeric_positions[key]
            if key in vector.numeric:
                value = (float(vector.numeric[key]) - self.medians[key]) / self.scales[key]
                if clip_numeric:
                    value = min(8.0, max(-8.0, value))
                by_family[family][value_position] = value
                by_family[family][missing_position] = 0.0
            else:
                by_family[family][value_position] = 0.0
                by_family[family][missing_position] = 1.0
        for token, count in vector.categorical.items():
            family = token.split("|", 1)[0]
            if family not in by_family:
                raise ReceiptSchemaError(f"unknown feature family in token: {family}")
            bucket, sign = _cat_hash(token)
            position = self.family_cat_offsets[family] + bucket
            transformed = sign * math.log1p(min(int(count), 255))
            by_family[family][position] = by_family[family].get(position, 0.0) + transformed
        result: Dict[int, float] = {}
        for family in FAMILIES:
            block = by_family[family]
            values = np.asarray([block[index] for index in sorted(block)], dtype=np.float64)
            norm = math.sqrt(float(np.einsum("i,i->", values, values, optimize=False))) if len(values) else 0.0
            if not math.isfinite(norm):
                raise NonFiniteFeature(f"family norm {family}")
            if norm > 0.0:
                for index, value in block.items():
                    scaled = value / norm
                    if scaled:
                        result[index] = scaled
            result[self.family_norm_positions[family]] = math.log1p(norm)
        if not all(math.isfinite(value) for value in result.values()):
            raise NonFiniteFeature("normalized vector")
        return result

    def tree_vector(self, vector: FeatureVector) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for key in self.numeric_ids:
            if key in vector.numeric:
                result[f"N|{key}"] = float(vector.numeric[key])
                result[f"M|{key}"] = 0.0
            else:
                result[f"N|{key}"] = self.medians[key]
                result[f"M|{key}"] = 1.0
        for token in vector.categorical:
            family = token.split("|", 1)[0]
            bucket, _sign = _cat_hash(token)
            result[f"B|{family}|{bucket:05d}"] = 1.0
        return result


def sparse_dot(weights: np.ndarray, row: Mapping[int, float]) -> float:
    if not row:
        return 0.0
    indices = np.fromiter(sorted(row), dtype=np.int64)
    values = np.asarray([row[int(index)] for index in indices], dtype=np.float64)
    result = float(np.einsum("i,i->", weights[indices], values, optimize=False))
    if not math.isfinite(result):
        raise NonFiniteFeature("sparse dot")
    return result


def sparse_inner(left: Mapping[int, float], right: Mapping[int, float]) -> float:
    common = sorted(set(left).intersection(right))
    if not common:
        return 0.0
    a = np.asarray([left[index] for index in common], dtype=np.float64)
    b = np.asarray([right[index] for index in common], dtype=np.float64)
    result = float(np.einsum("i,i->", a, b, optimize=False))
    if not math.isfinite(result):
        raise NonFiniteFeature("sparse inner product")
    return result


def balanced_accuracy(labels: Sequence[int], predictions: Sequence[int]) -> float:
    recalls = []
    for label in (0, 1):
        indices = [index for index, actual in enumerate(labels) if actual == label]
        if not indices:
            raise EngineError(f"balanced accuracy missing class {label}")
        recalls.append(sum(predictions[index] == label for index in indices) / len(indices))
    return 0.5 * (recalls[0] + recalls[1])


def _candidate_key(score: float, complexity: int, serial: str) -> Tuple[float, int, bytes]:
    # max score, then lower complexity, then UTF-8 serialization.
    return (-score, complexity, serial.encode("utf-8"))


@dataclass
class ExactRuleModel:
    rule: Dict[str, Any]
    calibration_balanced_accuracy: float

    def predict_one(self, vector: FeatureVector) -> int:
        kind = self.rule["kind"]
        if kind == "constant":
            return int(self.rule["class"])
        if kind == "token_presence":
            present = self.rule["token"] in vector.categorical
            return int(self.rule["present_class"] if present else 1 - self.rule["present_class"])
        if kind == "conjunction":
            present = all(token in vector.categorical for token in self.rule["tokens"])
            return int(self.rule["present_class"] if present else 1 - self.rule["present_class"])
        if kind == "categorical_mapping":
            prefix = self.rule["prefix"]
            present = sorted(token for token in vector.categorical if token.startswith(prefix))
            value = present[0] if len(present) == 1 else "__MISSING_OR_MULTI__"
            return int(self.rule["mapping"].get(value, self.rule["default_class"]))
        if kind == "numeric_mapping":
            key = self.rule["feature"]
            value = "__MISSING__" if key not in vector.numeric else _scalar_repr(float(vector.numeric[key]))
            return int(self.rule["mapping"].get(value, self.rule["default_class"]))
        raise EngineError(f"unknown C01 rule: {kind}")

    def predict(self, vectors: Sequence[FeatureVector]) -> List[int]:
        return [self.predict_one(vector) for vector in vectors]

    def artifact(self) -> Dict[str, Any]:
        return {"rule": self.rule, "calibration_balanced_accuracy": self.calibration_balanced_accuracy}


def _majority(labels: Sequence[int]) -> int:
    ones = sum(labels)
    zeros = len(labels) - ones
    return 1 if ones > zeros else 0


def fit_exact_rule(vectors: Sequence[FeatureVector], labels: Sequence[int]) -> ExactRuleModel:
    if len(vectors) != len(labels) or not vectors:
        raise EngineError("C01 requires nonempty aligned calibration data")
    candidates: List[Tuple[Tuple[float, int, bytes], Dict[str, Any], float]] = []

    def add(rule: Dict[str, Any], predictions: List[int], complexity: int) -> None:
        predicted_support = Counter(predictions)
        if predicted_support[0] < 5 or predicted_support[1] < 5:
            return
        score = balanced_accuracy(labels, predictions)
        serial = json.dumps(rule, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        candidates.append((_candidate_key(score, complexity, serial), rule, score))

    support = Counter(token for vector in vectors for token in vector.categorical)
    tokens = sorted(token for token, count in support.items() if count >= 10)
    for token in tokens:
        for present_class in (0, 1):
            predictions = [present_class if token in vector.categorical else 1 - present_class for vector in vectors]
            add({"kind": "token_presence", "token": token, "present_class": present_class}, predictions, 1)
    prefixes = sorted({token.rsplit("|", 1)[0] + "|" for token in tokens})
    for prefix in prefixes:
        values = []
        for vector in vectors:
            present = sorted(token for token in vector.categorical if token.startswith(prefix))
            values.append(present[0] if len(present) == 1 else "__MISSING_OR_MULTI__")
        grouped: Dict[str, List[int]] = defaultdict(list)
        for value, label in zip(values, labels):
            grouped[value].append(label)
        mapping = {value: _majority(group) for value, group in sorted(grouped.items())}
        default = _majority(labels)
        predictions = [mapping.get(value, default) for value in values]
        add({"kind": "categorical_mapping", "prefix": prefix, "mapping": mapping, "default_class": default}, predictions, 1)
    numeric_ids = sorted({key for vector in vectors for key in vector.numeric})
    for key in numeric_ids:
        values = ["__MISSING__" if key not in vector.numeric else _scalar_repr(float(vector.numeric[key])) for vector in vectors]
        grouped = defaultdict(list)
        for value, label in zip(values, labels):
            grouped[value].append(label)
        mapping = {value: _majority(group) for value, group in sorted(grouped.items())}
        default = _majority(labels)
        predictions = [mapping.get(value, default) for value in values]
        add({"kind": "numeric_mapping", "feature": key, "mapping": mapping, "default_class": default}, predictions, 1)
    top256 = sorted(support, key=lambda token: (-support[token], token.encode("utf-8")))[:256]
    for left, right in combinations(top256, 2):
        conjunction_support = sum(left in vector.categorical and right in vector.categorical for vector in vectors)
        if conjunction_support < 10:
            continue
        for present_class in (0, 1):
            predictions = [present_class if left in vector.categorical and right in vector.categorical else 1 - present_class for vector in vectors]
            add({"kind": "conjunction", "tokens": [left, right], "present_class": present_class}, predictions, 2)
    if not candidates:
        majority = _majority(labels)
        return ExactRuleModel({"kind": "constant", "class": majority}, balanced_accuracy(labels, [majority] * len(labels)))
    candidates.sort(key=lambda item: item[0])
    _key, rule, score = candidates[0]
    return ExactRuleModel(rule, score)


@dataclass
class LogisticModel:
    weights: np.ndarray
    intercept: float
    iterations: int
    converged: bool
    gradient_linf: float

    def predict(self, rows: Sequence[Mapping[int, float]]) -> List[int]:
        result = []
        for row in rows:
            score = self.intercept + sparse_dot(self.weights, row)
            probability = 1.0 / (1.0 + math.exp(-score)) if score >= 0 else math.exp(score) / (1.0 + math.exp(score))
            result.append(1 if probability > 0.5 else 0)
        return result

    def artifact(self) -> Dict[str, Any]:
        return {
            "weights_float64_sha256": sha256_bytes(np.ascontiguousarray(self.weights, dtype=np.float64).tobytes()),
            "dimension": int(len(self.weights)), "intercept": self.intercept,
            "iterations": self.iterations, "converged": self.converged,
            "gradient_linf": self.gradient_linf,
        }


def fit_logistic(rows: Sequence[Mapping[int, float]], labels: Sequence[int], dimension: int,
                 *, maximum_iterations: int = 2000, tolerance: float = 1e-10,
                 l2: float = 0.01) -> LogisticModel:
    if not rows or len(rows) != len(labels):
        raise EngineError("C02 requires nonempty aligned calibration data")
    matrix = np.zeros((len(rows), dimension), dtype=np.float64, order="C")
    for row_index, row in enumerate(rows):
        if any(index < 0 or index >= dimension for index in row):
            raise EngineError("C02 sparse feature index outside frozen dimension")
        if row:
            indices = np.fromiter(sorted(row), dtype=np.int64)
            matrix[row_index, indices] = np.asarray([row[int(index)] for index in indices], dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise NonFiniteFeature("logistic design matrix")
    label_array = np.asarray(labels, dtype=np.float64)
    weights = np.zeros(dimension, dtype=np.float64, order="C")
    intercept = 0.0
    n = float(len(rows))

    def objective(candidate_weights: np.ndarray, candidate_intercept: float) -> float:
        scores = np.einsum("ij,j->i", matrix, candidate_weights, optimize=False) + candidate_intercept
        total = float(np.sum(np.logaddexp(0.0, scores) - label_array * scores, dtype=np.float64))
        penalty = 0.5 * l2 * float(np.einsum("i,i->", candidate_weights, candidate_weights, optimize=False))
        value = total / n + penalty
        if not math.isfinite(value):
            raise NonFiniteFeature("logistic objective")
        return value

    def gradient(candidate_weights: np.ndarray, candidate_intercept: float) -> Tuple[np.ndarray, float]:
        scores = np.einsum("ij,j->i", matrix, candidate_weights, optimize=False) + candidate_intercept
        probabilities = np.empty_like(scores)
        nonnegative = scores >= 0.0
        probabilities[nonnegative] = 1.0 / (1.0 + np.exp(-scores[nonnegative]))
        exp_scores = np.exp(scores[~nonnegative])
        probabilities[~nonnegative] = exp_scores / (1.0 + exp_scores)
        delta = probabilities - label_array
        grad = np.einsum("ij,i->j", matrix, delta, optimize=False) / n + l2 * candidate_weights
        grad_intercept = float(np.sum(delta, dtype=np.float64) / n)
        if not np.isfinite(grad).all() or not math.isfinite(grad_intercept):
            raise NonFiniteFeature("logistic gradient")
        return grad, grad_intercept

    last_linf = math.inf
    for iteration in range(maximum_iterations + 1):
        grad, grad_intercept = gradient(weights, intercept)
        last_linf = max(float(np.max(np.abs(grad))) if dimension else 0.0, abs(grad_intercept))
        if last_linf <= tolerance:
            return LogisticModel(weights, intercept, iteration, True, last_linf)
        if iteration == maximum_iterations:
            break
        base = objective(weights, intercept)
        squared_norm = float(np.einsum("i,i->", grad, grad, optimize=False)) + grad_intercept * grad_intercept
        step = 1.0
        accepted = False
        for _ in range(80):
            candidate_weights = weights - step * grad
            candidate_intercept = intercept - step * grad_intercept
            if objective(candidate_weights, candidate_intercept) <= base - 0.0001 * step * squared_norm:
                weights, intercept = candidate_weights, candidate_intercept
                accepted = True
                break
            step *= 0.5
        if not accepted:
            return LogisticModel(weights, intercept, iteration, False, last_linf)
    return LogisticModel(weights, intercept, maximum_iterations, False, last_linf)


def _gini(labels: Sequence[int]) -> float:
    if not labels:
        return 0.0
    p = sum(labels) / len(labels)
    return 1.0 - p * p - (1.0 - p) * (1.0 - p)


@dataclass
class TreeNode:
    prediction: int
    feature: Optional[str] = None
    threshold: Optional[float] = None
    left: Optional["TreeNode"] = None
    right: Optional["TreeNode"] = None

    def predict_one(self, row: Mapping[str, float]) -> int:
        if self.feature is None:
            return self.prediction
        branch = self.left if row.get(self.feature, 0.0) <= float(self.threshold) else self.right
        if branch is None:
            raise EngineError("malformed tree")
        return branch.predict_one(row)

    def artifact(self) -> Dict[str, Any]:
        if self.feature is None:
            return {"prediction": self.prediction}
        return {
            "prediction": self.prediction, "feature": self.feature, "threshold": self.threshold,
            "left": self.left.artifact() if self.left else None,
            "right": self.right.artifact() if self.right else None,
        }


@dataclass
class TreeModel:
    root: TreeNode
    maximum_depth: int

    def predict(self, rows: Sequence[Mapping[str, float]]) -> List[int]:
        return [self.root.predict_one(row) for row in rows]

    def artifact(self) -> Dict[str, Any]:
        return {"maximum_depth": self.maximum_depth, "tree": self.root.artifact()}


def fit_tree(rows: Sequence[Mapping[str, float]], labels: Sequence[int], *, maximum_depth: int,
             minimum_leaf: int = 10, minimum_gain: float = 0.0) -> TreeModel:
    if not rows or len(rows) != len(labels):
        raise EngineError("tree requires nonempty aligned calibration data")
    feature_ids = sorted({feature for row in rows for feature in row}, key=lambda item: item.encode("utf-8"))

    def build(indices: List[int], depth: int) -> TreeNode:
        local_labels = [labels[index] for index in indices]
        prediction = _majority(local_labels)
        if depth >= maximum_depth or len(set(local_labels)) == 1:
            return TreeNode(prediction)
        parent_impurity = _gini(local_labels)
        best: Optional[Tuple[float, bytes, float, str, List[int], List[int]]] = None
        for feature in feature_ids:
            values = sorted({float(rows[index].get(feature, 0.0)) for index in indices})
            if len(values) < 2:
                continue
            thresholds = [0.5] if feature.startswith("B|") else [0.5 * (left + right) for left, right in zip(values, values[1:])]
            for threshold in thresholds:
                left_indices = [index for index in indices if float(rows[index].get(feature, 0.0)) <= threshold]
                right_indices = [index for index in indices if float(rows[index].get(feature, 0.0)) > threshold]
                if len(left_indices) < minimum_leaf or len(right_indices) < minimum_leaf:
                    continue
                gain = parent_impurity - (
                    len(left_indices) * _gini([labels[index] for index in left_indices])
                    + len(right_indices) * _gini([labels[index] for index in right_indices])
                ) / len(indices)
                candidate = (-gain, feature.encode("utf-8"), threshold, feature, left_indices, right_indices)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        if best is None or -best[0] <= minimum_gain:
            return TreeNode(prediction)
        _negative_gain, _feature_bytes, threshold, feature, left_indices, right_indices = best
        return TreeNode(
            prediction=prediction, feature=feature, threshold=threshold,
            left=build(left_indices, depth + 1), right=build(right_indices, depth + 1),
        )

    return TreeModel(build(list(range(len(rows))), 0), maximum_depth)


@dataclass
class KNNModel:
    rows: Sequence[Mapping[int, float]]
    labels: Sequence[int]
    k: int = 11

    @staticmethod
    def distance_squared(left: Mapping[int, float], right: Mapping[int, float]) -> float:
        left_values = np.asarray(list(left.values()), dtype=np.float64)
        right_values = np.asarray(list(right.values()), dtype=np.float64)
        left_norm = float(np.einsum("i,i->", left_values, left_values, optimize=False)) if len(left_values) else 0.0
        right_norm = float(np.einsum("i,i->", right_values, right_values, optimize=False)) if len(right_values) else 0.0
        distance = left_norm + right_norm - 2.0 * sparse_inner(left, right)
        if not math.isfinite(distance):
            raise NonFiniteFeature("KNN distance")
        return max(0.0, distance)

    def predict_one(self, row: Mapping[int, float]) -> int:
        if len(self.rows) < self.k:
            raise EngineError(f"C05 requires at least {self.k} calibration rows")
        distances = sorted((self.distance_squared(row, candidate), index) for index, candidate in enumerate(self.rows))
        boundary = distances[self.k - 1][0]
        neighbours = [index for distance, index in distances if distance <= boundary + 1e-15]
        votes = Counter(self.labels[index] for index in neighbours)
        return 1 if votes[1] > votes[0] else 0

    def predict(self, rows: Sequence[Mapping[int, float]]) -> List[int]:
        return [self.predict_one(row) for row in rows]

    def artifact(self) -> Dict[str, Any]:
        vector_manifest = [
            {"row": [[index, row[index]] for index in sorted(row)], "label": int(label)}
            for row, label in zip(self.rows, self.labels)
        ]
        return {"k": self.k, "boundary_ties": "INCLUDE_ALL", "training_manifest_sha256": canonical_sha256(vector_manifest)}


def _binomial_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    mode = min(n, max(0, int(math.floor((n + 1) * p))))
    relative = [0.0] * (n + 1)
    relative[mode] = 1.0
    for x in range(mode, 0, -1):
        relative[x - 1] = relative[x] * x / (n - x + 1) * (1.0 - p) / p
    for x in range(mode, n):
        relative[x + 1] = relative[x] * (n - x) / (x + 1) * p / (1.0 - p)
    total = math.fsum(relative)
    return math.fsum(relative[:k + 1]) / total


def clopper_pearson(k: int, n: int, alpha: float = 0.025) -> Tuple[float, float]:
    if n <= 0 or k < 0 or k > n:
        raise EngineError("invalid binomial count")
    if k == 0:
        lower = 0.0
    else:
        low, high = 0.0, 1.0
        for _ in range(80):
            mid = 0.5 * (low + high)
            tail = 1.0 - _binomial_cdf(k - 1, n, mid)
            if tail < alpha:
                low = mid
            else:
                high = mid
        lower = 0.5 * (low + high)
    if k == n:
        upper = 1.0
    else:
        low, high = 0.0, 1.0
        for _ in range(80):
            mid = 0.5 * (low + high)
            cdf = _binomial_cdf(k, n, mid)
            if cdf > alpha:
                low = mid
            else:
                high = mid
        upper = 0.5 * (low + high)
    return lower, upper


def classwise_balanced_interval(labels: Sequence[int], predictions: Sequence[int]) -> Dict[str, Any]:
    counts = {}
    lowers, uppers, recalls = [], [], []
    for label in (0, 1):
        total = sum(actual == label for actual in labels)
        correct = sum(actual == label and predicted == label for actual, predicted in zip(labels, predictions))
        lower, upper = clopper_pearson(correct, total, 0.025)
        recall = correct / total
        counts[str(label)] = {"correct": correct, "total": total, "recall": recall, "lower": lower, "upper": upper}
        lowers.append(lower)
        uppers.append(upper)
        recalls.append(recall)
    return {
        "classwise": counts,
        "balanced_accuracy": 0.5 * sum(recalls),
        "lower_balanced_accuracy": 0.5 * sum(lowers),
        "upper_balanced_accuracy": 0.5 * sum(uppers),
        "method": "CLASSWISE_ONE_SIDED_CLOPPER_PEARSON_BONFERRONI",
    }


def permutation_seed(precommit_sha256: str, feature_spec_sha256: str) -> bytes:
    """Resolve the spec formula using lowercase ASCII hex, not raw digest bytes.

    FEATURE-SPEC names SHA256 values but does not say whether the concatenated
    values are 32 raw bytes or 64 hexadecimal characters.  This engine freezes
    the latter convention and reports it; formal anchoring must adopt or replace
    this resolution explicitly.
    """
    return hashlib.sha256(
        b"WAVE025_PERMUTATION_SEED_V1\x00" + precommit_sha256.encode("ascii")
        + b"\x00" + feature_spec_sha256.encode("ascii")
    ).digest()


def t_host_holdout_indices(records: Sequence[Mapping[str, Any]]) -> List[int]:
    """Host-only family is scoped only to T fresh holdout, never D0 or D1."""
    return [
        index for index, record in enumerate(records)
        if record.get("challenge") == "T-OCI-ISOLATED" and record.get("phase") == "fresh_holdout"
    ]


def _permuted_labels(labels: Sequence[int], metadata: Sequence[Mapping[str, Any]], seed: bytes,
                     replicate: int) -> List[int]:
    result = list(labels)
    groups: Dict[Tuple[str, str, str], List[int]] = defaultdict(list)
    for index, row in enumerate(metadata):
        groups[(str(row["challenge"]), str(row["phase"]), str(row["block"]))].append(index)
    for indices in groups.values():
        source = sorted(indices, key=lambda index: str(metadata[index]["opaque_slot_id"]).encode("utf-8"))
        target = sorted(
            indices,
            key=lambda index: hashlib.sha256(
                seed + b"\x00" + str(replicate).encode("ascii") + b"\x00"
                + str(metadata[index]["opaque_slot_id"]).encode("utf-8")
            ).digest(),
        )
        source_labels = [labels[index] for index in source]
        for target_index, label in zip(target, source_labels):
            result[target_index] = label
    return result


def frozen_prediction_permutation(labels: Sequence[int], predictions: Sequence[int],
                                  metadata: Sequence[Mapping[str, Any]], seed: bytes,
                                  replicates: int = 9999) -> Dict[str, Any]:
    observed = balanced_accuracy(labels, predictions)
    exceed = 0
    for replicate in range(replicates):
        permuted = _permuted_labels(labels, metadata, seed, replicate)
        if balanced_accuracy(permuted, predictions) >= observed - 1e-15:
            exceed += 1
    return {
        "observed_balanced_accuracy": observed,
        "replicates": replicates,
        "count_permuted_ge_observed": exceed,
        "p_value": (1 + exceed) / (1 + replicates),
        "population": "FRESH_HOLDOUT_ONLY",
        "predictions": "FROZEN_BEFORE_LABEL_JOIN",
        "retrained_per_replicate": False,
    }


def holm_step_down(p_values: Mapping[str, float], alpha: float = 0.05) -> Dict[str, Any]:
    ordered = sorted(p_values.items(), key=lambda item: (item[1], item[0].encode("utf-8")))
    rejected: Dict[str, bool] = {test_id: False for test_id in p_values}
    stopped = False
    steps = []
    m = len(ordered)
    for index, (test_id, p_value) in enumerate(ordered):
        threshold = alpha / (m - index)
        decision = (not stopped) and p_value <= threshold
        if not decision:
            stopped = True
        rejected[test_id] = decision
        steps.append({"test_id": test_id, "p_value": p_value, "threshold": threshold, "rejected": decision})
    return {"method": "HOLM_STEP_DOWN", "familywise_alpha": alpha, "steps": steps, "rejected": rejected}


def _host_statistic(kind: str, values: Sequence[Any], labels: Sequence[int]) -> float:
    if kind == "numeric":
        groups = [[float(value) for value, label in zip(values, labels) if label == target] for target in (0, 1)]
        means = [sum(group) / len(group) for group in groups]
        variances = [sum((value - mean) ** 2 for value in group) / max(1, len(group) - 1) for group, mean in zip(groups, means)]
        pooled = math.sqrt(0.5 * (variances[0] + variances[1]))
        if pooled == 0.0:
            return 0.0 if means[0] == means[1] else math.inf
        return abs(means[1] - means[0]) / pooled
    if kind == "categorical":
        categories = sorted({"__MISSING__" if value is None else _scalar_repr(value) for value in values})
        table = [[0, 0] for _ in categories]
        lookup = {category: index for index, category in enumerate(categories)}
        for value, label in zip(values, labels):
            table[lookup["__MISSING__" if value is None else _scalar_repr(value)]][label] += 1
        n = len(values)
        col = [sum(row[label] for row in table) for label in (0, 1)]
        chi2 = 0.0
        for row in table:
            row_total = sum(row)
            for label in (0, 1):
                expected = row_total * col[label] / n
                if expected:
                    chi2 += (row[label] - expected) ** 2 / expected
        denominator = max(1, min(len(categories) - 1, 1))
        return math.sqrt(chi2 / (n * denominator))
    if kind == "set_or_path":
        normalized = [set(value or []) for value in values]
        categories = sorted({item for group in normalized for item in group}, key=lambda item: str(item).encode("utf-8"))
        best = 0.0
        for category in categories:
            support = sum(category in group for group in normalized)
            if support < 10:
                continue
            rates = [
                sum(category in group for group, label in zip(normalized, labels) if label == target)
                / sum(label == target for label in labels)
                for target in (0, 1)
            ]
            best = max(best, abs(rates[1] - rates[0]))
        return best
    raise EngineError(f"unknown host statistic kind: {kind}")


def evaluate_host_only(inventory: Sequence[Mapping[str, str]], host_rows: Sequence[Mapping[str, Any]],
                       labels: Sequence[int], metadata: Sequence[Mapping[str, Any]], seed: bytes,
                       replicates: int = 9999) -> Dict[str, Any]:
    tests: Dict[str, Any] = {}
    p_values: Dict[str, float] = {}
    for item in sorted(inventory, key=lambda value: value["test_id"].encode("utf-8")):
        test_id, kind, field = item["test_id"], item["kind"], item["field"]
        values = [row.get(field) for row in host_rows]
        observed = _host_statistic(kind, values, labels)
        exceed = 0
        for replicate in range(replicates):
            permuted = _permuted_labels(labels, metadata, seed, replicate)
            if _host_statistic(kind, values, permuted) >= observed:
                exceed += 1
        p_value = (1 + exceed) / (1 + replicates)
        p_values[test_id] = p_value
        rendered_statistic: Any = "INFINITY" if math.isinf(observed) else observed
        tests[test_id] = {"kind": kind, "field": field, "statistic": rendered_statistic,
                          "replicates": replicates, "p_value": p_value}
    return {"tests": tests, "holm": holm_step_down(p_values), "predictor_matrix_imported": False}


def _model_and_predictions(classifier_id: str, calibration: Sequence[FeatureVector],
                           calibration_labels: Sequence[int], holdout: Sequence[FeatureVector],
                           space: VectorSpace) -> Tuple[Any, List[int]]:
    if classifier_id == "C01_EXACT_CATEGORICAL_SCAN":
        model = fit_exact_rule(calibration, calibration_labels)
        return model, model.predict(holdout)
    if classifier_id == "C02_L2_LOGISTIC":
        train = [space.normalized(vector, clip_numeric=False) for vector in calibration]
        test = [space.normalized(vector, clip_numeric=False) for vector in holdout]
        model = fit_logistic(train, calibration_labels, space.dimension)
        if not model.converged:
            raise EngineError(f"C02 nonconvergence after {model.iterations} iterations gradient_linf={model.gradient_linf}")
        return model, model.predict(test)
    if classifier_id == "C03_DECISION_STUMP":
        train = [space.tree_vector(vector) for vector in calibration]
        test = [space.tree_vector(vector) for vector in holdout]
        model = fit_tree(train, calibration_labels, maximum_depth=1, minimum_leaf=10, minimum_gain=0.0)
        return model, model.predict(test)
    if classifier_id == "C04_BOUNDED_TREE":
        train = [space.tree_vector(vector) for vector in calibration]
        test = [space.tree_vector(vector) for vector in holdout]
        model = fit_tree(train, calibration_labels, maximum_depth=3, minimum_leaf=10, minimum_gain=1e-12)
        return model, model.predict(test)
    if classifier_id == "C05_KNN_11":
        train = [space.normalized(vector, clip_numeric=True) for vector in calibration]
        test = [space.normalized(vector, clip_numeric=True) for vector in holdout]
        model = KNNModel(train, list(calibration_labels), 11)
        return model, model.predict(test)
    raise EngineError(f"unknown classifier: {classifier_id}")


def _artifact(model: Any) -> Dict[str, Any]:
    value = model.artifact()
    canonical_bytes(value)  # reject non-finite or non-JSON artifacts
    return value


class FullEvaluatorEngine:
    """Run the frozen full-leaf attack engine with two-run replay checks."""

    def __init__(self, profile_path: Optional[pathlib.Path] = None,
                 feature_provider: Optional[Any] = None) -> None:
        if profile_path is None:
            profile_path = pathlib.Path(__file__).resolve().parent.parent / "EXECUTABLE-ATTACK-PROFILE.json"
        self.profile_path = pathlib.Path(profile_path)
        self.profile, self.spec, self.spec_path = load_bound_spec(self.profile_path)
        self.feature_provider = feature_provider or RawReceiptFeatureProvider()
        if self.profile["inherited_attack_surface"]["candidate_visible_leaf_cap"] != "NONE":
            raise SpecMismatch("candidate-visible leaf cap is forbidden")
        if self.profile["inherited_attack_surface"]["numeric_path_cap"] != "NONE":
            raise SpecMismatch("numeric path cap is forbidden")
        if tuple(self.profile["inherited_attack_surface"]["feature_family_ids"]) != FAMILIES:
            raise SpecMismatch("F01-F07 binding mismatch")
        if tuple(self.profile["inherited_attack_surface"]["classifier_ids"]) != CLASSIFIERS:
            raise SpecMismatch("C01-C05 binding mismatch")
        if self.profile["permutation_override"]["replicates"] != 9999:
            raise SpecMismatch("frozen-prediction permutation must use 9999 replicates")
        deferred = self.profile["deferred_challenge"]
        if deferred["id"] != "MODEL-SELECTION-RANDOMIZATION" or deferred["status"] != "NOT_TESTED":
            raise SpecMismatch("MODEL-SELECTION-RANDOMIZATION must remain NOT_TESTED")

    @staticmethod
    def _ordered_records(records: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
        required = {"receipt", "challenge", "phase", "block", "opaque_slot_id", "role"}
        optional = {"private_family", "host_only"}
        seen = set()
        ordered = []
        for index, record in enumerate(records):
            _keys(record, required, optional, f"records/{index}")
            if record["phase"] not in ("calibration", "fresh_holdout"):
                raise EngineError(f"invalid phase: {record['phase']}")
            slot = str(record["opaque_slot_id"])
            if slot in seen:
                raise EngineError(f"duplicate opaque_slot_id: {slot}")
            seen.add(slot)
            ordered.append(record)
        return sorted(
            ordered,
            key=lambda row: (str(row["challenge"]).encode("utf-8"), str(row["phase"]).encode("utf-8"),
                             str(row["block"]).encode("utf-8"), str(row["opaque_slot_id"]).encode("utf-8")),
        )

    def _run_once(self, records: Sequence[Mapping[str, Any]], precommit_sha256: str,
                  host_inventory: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
        provider_receipt = verify_execution_provider(self.profile)
        ordered = self._ordered_records(records)
        if not re.fullmatch(r"[0-9a-f]{64}", precommit_sha256):
            raise EngineError("precommit_sha256 must be lowercase SHA-256 hex")
        # The provider receives the raw receipt only. Labels and stratum metadata
        # are joined after predictor vectors and leaf audits have been frozen.
        vectors = [self.feature_provider.extract(record["receipt"]) for record in ordered]
        raw_manifest = [
            {"opaque_slot_id": str(record["opaque_slot_id"]), "receipt_sha256": canonical_sha256(record["receipt"])}
            for record in ordered
        ]
        audits = [vector.audit for vector in vectors]
        numeric_matrix = [
            {"opaque_slot_id": str(record["opaque_slot_id"]), "numeric": dict(sorted(vector.numeric.items()))}
            for record, vector in zip(ordered, vectors)
        ]
        categorical_matrix = [
            {"opaque_slot_id": str(record["opaque_slot_id"]), "categorical": dict(sorted(vector.categorical.items()))}
            for record, vector in zip(ordered, vectors)
        ]
        frozen_predictor_hash = canonical_sha256({"numeric": numeric_matrix, "categorical": categorical_matrix})

        roles = sorted({str(record["role"]) for record in ordered}, key=lambda value: value.encode("utf-8"))
        if len(roles) != 2:
            raise EngineError(f"exactly two revealed roles required, got {roles}")
        label_lookup = {roles[0]: 0, roles[1]: 1}
        labels = [label_lookup[str(record["role"])] for record in ordered]
        feature_spec_sha = self.profile["feature_spec_binding"]["raw_bytes_sha256"]
        seed = permutation_seed(precommit_sha256, feature_spec_sha)

        group_indices: Dict[Tuple[str, str], List[int]] = defaultdict(list)
        for index, record in enumerate(ordered):
            group_indices[(str(record["challenge"]), str(record.get("private_family", "")))].append(index)
        groups: Dict[str, Any] = {}
        model_artifacts: Dict[str, Any] = {}
        frozen_predictions: Dict[str, Any] = {}
        ci_statistics: Dict[str, Any] = {}
        permutation_statistics: Dict[str, Any] = {}
        for (challenge, private_family), indices in sorted(group_indices.items()):
            group_id = challenge if not private_family else f"{challenge}::{private_family}"
            calibration_indices = [index for index in indices if ordered[index]["phase"] == "calibration"]
            holdout_indices = [index for index in indices if ordered[index]["phase"] == "fresh_holdout"]
            if not calibration_indices or not holdout_indices:
                raise EngineError(f"group {group_id} missing calibration or fresh holdout")
            calibration = [vectors[index] for index in calibration_indices]
            holdout = [vectors[index] for index in holdout_indices]
            calibration_labels = [labels[index] for index in calibration_indices]
            holdout_labels = [labels[index] for index in holdout_indices]
            if set(calibration_labels) != {0, 1} or set(holdout_labels) != {0, 1}:
                raise EngineError(f"group {group_id} is missing a class")
            space = VectorSpace.fit(calibration)
            holdout_meta = [
                {"challenge": ordered[index]["challenge"], "phase": ordered[index]["phase"],
                 "block": ordered[index]["block"], "opaque_slot_id": ordered[index]["opaque_slot_id"]}
                for index in holdout_indices
            ]
            classifier_results: Dict[str, Any] = {}
            p_values: Dict[str, float] = {}
            for classifier_id in CLASSIFIERS:
                test_id = f"{group_id}::{classifier_id}"
                try:
                    model, predictions = _model_and_predictions(
                        classifier_id, calibration, calibration_labels, holdout, space,
                    )
                    artifact = _artifact(model)
                    interval = classwise_balanced_interval(holdout_labels, predictions)
                    permutation = frozen_prediction_permutation(
                        holdout_labels, predictions, holdout_meta, seed,
                        self.profile["permutation_override"]["replicates"],
                    )
                    if classifier_id == "C01_EXACT_CATEGORICAL_SCAN":
                        calibration_predictions = model.predict(calibration)
                        stable_recovery = (
                            balanced_accuracy(calibration_labels, calibration_predictions) == 1.0
                            and interval["balanced_accuracy"] == 1.0
                        )
                    else:
                        stable_recovery = None
                    classifier_results[classifier_id] = {
                        "status": "EXECUTED", "interval": interval, "permutation": permutation,
                        "stable_recovery": stable_recovery,
                    }
                    model_artifacts[test_id] = artifact
                    frozen_predictions[test_id] = predictions
                    ci_statistics[test_id] = interval
                    permutation_statistics[test_id] = permutation
                    p_values[test_id] = permutation["p_value"]
                except (EngineError, FloatingPointError, OverflowError, ValueError) as error:
                    classifier_results[classifier_id] = {
                        "status": "CLASSIFIER_ABNORMAL", "error_type": type(error).__name__,
                        "error": str(error), "chance_interpretation": "FORBIDDEN",
                    }
                    model_artifacts[test_id] = classifier_results[classifier_id]
            groups[group_id] = {
                "challenge": challenge, "private_family": private_family or None,
                "calibration_rows": len(calibration), "fresh_holdout_rows": len(holdout),
                "classifiers": classifier_results,
                "predictive_holm": holm_step_down(p_values),
            }

        holdout_indices = t_host_holdout_indices(ordered)
        if host_inventory:
            if not holdout_indices:
                raise EngineError("host-only inventory supplied but T fresh holdout is empty")
            if any("host_only" not in ordered[index] for index in holdout_indices):
                raise EngineError("host-only inventory supplied but a holdout row lacks host_only data")
            host_result = evaluate_host_only(
                host_inventory,
                [ordered[index]["host_only"] for index in holdout_indices],
                [labels[index] for index in holdout_indices],
                [{"challenge": ordered[index]["challenge"], "phase": ordered[index]["phase"],
                  "block": ordered[index]["block"], "opaque_slot_id": ordered[index]["opaque_slot_id"]}
                 for index in holdout_indices],
                seed,
                self.profile["host_only_holm"]["replicates"],
            )
        else:
            host_result = {"tests": {}, "holm": holm_step_down({}), "predictor_matrix_imported": False,
                           "state": "NO_FROZEN_HOST_ONLY_INVENTORY_SUPPLIED"}
        host_result["family_id"] = self.profile["host_only_holm"]["family_id"]
        host_result["population"] = "T-OCI-ISOLATED::FRESH_HOLDOUT_ONLY"
        evaluation = {
            "schema": "WAVE025_FULL_LEAF_EVALUATOR_RESULT_V1",
            "profile_id": self.profile["profile_id"],
            "feature_spec_sha256": feature_spec_sha,
            "provider": provider_receipt,
            "feature_provider_id": str(getattr(self.feature_provider, "provider_id", type(self.feature_provider).__name__)),
            "row_count": len(ordered), "role_labels_utf8_sorted": roles,
            "predictors_frozen_before_label_join_sha256": frozen_predictor_hash,
            "permutation_seed_encoding_resolution": "LOWERCASE_ASCII_HEX_SHA256_VALUES_NOT_RAW_32_BYTE_DIGESTS",
            "groups": groups,
            "host_only": host_result,
            "MODEL-SELECTION-RANDOMIZATION": "NOT_TESTED",
            "qualification_verdict_produced": False,
            "treatment_score_or_ranking_produced": False,
            "formal_use_claimed": False,
        }
        hash_manifest = {
            "RAW_RECEIPT_MANIFEST": canonical_sha256(raw_manifest),
            "INCLUDED_EXCLUDED_LEAF_AUDIT": canonical_sha256(audits),
            "NUMERIC_FEATURE_MATRIX": canonical_sha256(numeric_matrix),
            "CATEGORICAL_FEATURE_MATRIX": canonical_sha256(categorical_matrix),
            "CALIBRATION_MODEL_ARTIFACTS_C01_TO_C05": canonical_sha256(model_artifacts),
            "FROZEN_HOLDOUT_PREDICTIONS_C01_TO_C05": canonical_sha256(frozen_predictions),
            "CLASSWISE_CI_STATISTICS": canonical_sha256(ci_statistics),
            "BLOCK_PERMUTATION_STATISTICS": canonical_sha256(permutation_statistics),
            "HOST_ONLY_HOLM_STATISTICS": canonical_sha256(host_result),
            "EVALUATION_OUTPUT_BYTES": canonical_sha256(evaluation),
        }
        required = self.profile["deterministic_replay"]["required_hash_classes"]
        if sorted(hash_manifest) != sorted(required):
            raise SpecMismatch("deterministic replay hash-class coverage mismatch")
        return {"evaluation": evaluation, "hash_manifest": hash_manifest}

    def evaluate(self, records: Sequence[Mapping[str, Any]], precommit_sha256: str,
                 host_inventory: Sequence[Mapping[str, str]] = ()) -> Dict[str, Any]:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            first = self._run_once(records, precommit_sha256, host_inventory)
            second = self._run_once(records, precommit_sha256, host_inventory)
        enforce_replay_identity(
            first, second, self.profile["deterministic_replay"]["required_hash_classes"],
        )
        return {
            "schema": "WAVE025_FULL_LEAF_EVALUATOR_REPLAY_ENVELOPE_V1",
            "evaluation": first["evaluation"],
            "hash_manifest": first["hash_manifest"],
            "deterministic_replay": {
                "independent_runs": 2,
                "allowed_byte_differences": 0,
                "observed_hash_differences": 0,
                "status": "REPLAY_IDENTICAL",
            },
        }


def enforce_replay_identity(first: Mapping[str, Any], second: Mapping[str, Any],
                            required_hash_classes: Sequence[str]) -> None:
    mismatches = [
        key for key in required_hash_classes
        if first["hash_manifest"].get(key) != second["hash_manifest"].get(key)
    ]
    if canonical_bytes(first) != canonical_bytes(second):
        mismatches.append("FULL_RUN_ENVELOPE_BYTES")
    if mismatches:
        raise ReplayMismatch(f"deterministic replay mismatch: {sorted(set(mismatches))}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Wave025 full-leaf evaluator engine (not batch parser)")
    parser.add_argument("records_json", type=pathlib.Path)
    parser.add_argument("--profile", type=pathlib.Path, default=None)
    parser.add_argument("--precommit-sha256", required=True)
    parser.add_argument("--host-inventory", type=pathlib.Path)
    args = parser.parse_args(argv)
    records = json.loads(args.records_json.read_text(encoding="utf-8"))
    inventory = json.loads(args.host_inventory.read_text(encoding="utf-8")) if args.host_inventory else []
    output = FullEvaluatorEngine(args.profile).evaluate(records, args.precommit_sha256, inventory)
    sys.stdout.buffer.write(canonical_bytes(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
