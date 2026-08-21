#!/usr/bin/env python3
"""Fail-closed independent evaluator for the Wave 025 prefix suite.

This module intentionally does not import the runner or the JavaScript
collector.  It reads a frozen batch only after reveal, recomputes the evidence
it can derive from raw bytes, and refuses to turn unresolved shared-interface
ambiguity into a positive qualification.

Only Python's standard library is used.  The statistical implementation and
its tie-breaking rules are therefore part of this source preimage.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import pathlib
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence


EVALUATION_SCHEMA = "WAVE025_INDEPENDENT_EVALUATION_V1"
PRECOMMIT_SCHEMA = "WAVE025_BATCH_PRECOMMIT_V1"
PUBLIC_PLAN_SCHEMA = "WAVE025_PUBLIC_PLAN_V1"
PRIVATE_STATE_SCHEMA = "WAVE025_RUNNER_PRIVATE_STATE_V1"
ANCHOR_SCHEMA = "WAVE025_ANCHOR_RECEIPT_V1"
HOST_LAUNCH_SCHEMA = "WAVE025_HOST_LAUNCH_V1"
SLOT_RECEIPT_SCHEMA = "WAVE025_SLOT_RECEIPT_V1"
CLOSED_SCHEMA = "WAVE025_BATCH_CLOSED_V1"
REVEAL_SCHEMA = "WAVE025_BATCH_REVEAL_V1"
COLLECTOR_SCHEMA = "WAVE025_LEAK_ONLY_FEATURES_V1"

CHALLENGES = (
    "D0-HOST-LEAK",
    "D1-OCI-CANARY",
    "T-OCI-ISOLATED",
)
ROLES = ("R", "S")
PARTITIONS = ("calibration", "holdout")
DOMAINS = (
    "PRIVATE_ASSIGNMENT_ORDER",
    "PUBLIC_ID",
    "MEASUREMENT_PADDING",
)

ASSIGNMENT_ALGORITHM = "HMAC_SHA256_BALANCED_FISHER_YATES_V1"
PUBLIC_ID_ALGORITHM = "HMAC_SHA256_OPAQUE_SLOT_V1"
PADDING_ALGORITHM = "HMAC_SHA256_UINT32_PADDING_V1"
MERKLE_ALGORITHM = "SHA256_SORTED_LEAVES_DUPLICATE_ODD_V1"

FORMAL_SAMPLE_PLAN = {
    "D0-HOST-LEAK": {"calibration": 100, "holdout": 100},
    "D1-OCI-CANARY": {"calibration": 100, "holdout": 100},
    "T-OCI-ISOLATED": {"calibration": 400, "holdout": 800},
}
FORMAL_SLOT_COUNT = 1600

FEATURE_SPEC = {
    "schema": "WAVE025_FEATURE_SPEC_V1",
    "collector_schema": COLLECTOR_SCHEMA,
    "included_roots": [
        "argv",
        "collection_window",
        "cwd",
        "directory_trees",
        "environment",
        "hostname",
        "identity",
        "input_contract",
        "process_view",
        "subject_input",
        "timing",
        "visible_canaries",
    ],
    "categorical_hash_dimensions": 128,
    "maximum_numeric_paths": 96,
    "numeric_minimum_coverage": 0.50,
    "numeric_decimal_strings": True,
    "normalization": "CALIBRATION_ZSCORE_THEN_ROW_L2_V1",
    "missing_value": "ZERO_PLUS_EXPLICIT_MISSING_BIT",
    "forbidden_predictors": [
        "opaque_slot_id",
        "container_id",
        "host_timestamps",
        "execution_order",
        "role",
        "block",
        "host_only_receipt",
    ],
}

SUPPORTED_CLASSIFIER_PLAN = {
    "schema": "WAVE025_CLASSIFIER_PLAN_V1",
    "feature_spec_schema": "WAVE025_FEATURE_SPEC_V1",
    "deterministic": {
        "minimum_value_support": 2,
        "unknown_value_prediction": "CALIBRATION_MAJORITY_THEN_R",
    },
    "logistic": {
        "epochs": 120,
        "learning_rate": 0.08,
        "l2": 1.0,
        "threshold": 0.5,
        "tie_prediction": "R",
    },
    "bounded_tree": {
        "maximum_depth": 2,
        "maximum_thresholds_per_feature": 9,
        "minimum_leaf": 10,
        "tie_prediction": "R",
    },
    "knn": {"k": 5, "metric": "EUCLIDEAN", "tie_prediction": "R"},
    "permutation": {
        "count": 199,
        "seed_derivation": "SHA256_PRECOMMIT_MODEL_LABEL_V1",
        "tail": "GREATER_OR_EQUAL",
    },
    "multiplicity": "HOLM_V1",
    "ci_method": "CLOPPER_PEARSON_BALANCED_TOTAL_ONE_SIDED_V1",
    # Each positive-control family is a dict with a stable name and one or
    # more flattened collector path prefixes.  The runner must freeze these
    # before seeing any slot output.  Exact family content is intentionally
    # not supplied by the shared contract.
    "positive_control_families": {
        "D0-HOST-LEAK": [],
        "D1-OCI-CANARY": [],
    },
}

SUPPORTED_THRESHOLDS = {
    "confidence": 0.95,
    "positive_control_holdout_ba_lower_min": 0.90,
    "t_holdout_ba_upper_max": 0.55,
    "deterministic_stable_recovery_ba": 1.0,
}

COLLECTOR_TOP_LEVEL_FIELDS = {
    "schema",
    "collector_version",
    "contract",
    "input_contract",
    "subject_input",
    "argv",
    "environment",
    "cwd",
    "hostname",
    "identity",
    "directory_trees",
    "process_view",
    "visible_canaries",
    "timing",
    "collection_window",
}

SLOT_RAW_FILES = (
    "host-launch.json",
    "docker-inspect-pre.json",
    "docker-inspect-post.json",
    "collector-stdout.bin",
    "collector-stderr.bin",
    "collector-out.bin",
    "collector-features.json",
)

# These are not filled in with convenient assumptions.  The evaluator can
# exercise a local, versioned profile, but a formal positive verdict remains
# blocked until the shared contract names the corresponding exact rules.
CONTRACT_AMBIGUITIES = [
    {
        "id": "AMB-EXACT-SCHEMAS",
        "blocking": True,
        "detail": (
            "The contract says every formal object has an exact field set, but "
            "uses 'at least' and does not freeze nested shapes for anchor, plan, "
            "private-state, host-launch, slot-receipt, closed, or reveal."
        ),
    },
    {
        "id": "AMB-RANDOM-MAPPING",
        "blocking": True,
        "detail": (
            "The three algorithm identifiers and commitment formula are required, "
            "but the byte encoding, deterministic stream, public-ID derivation, "
            "block assignment, execution-order derivation, and padding derivation "
            "are not standardized."
        ),
    },
    {
        "id": "AMB-MERKLE",
        "blocking": True,
        "detail": (
            "Leaf identity is stated, but internal-node domain separation, odd-leaf "
            "handling, and empty-tree behavior are not frozen."
        ),
    },
    {
        "id": "AMB-FEATURE-SPEC-LOCATION",
        "blocking": True,
        "detail": (
            "precommit binds feature_spec_sha256, but the batch layout contains no "
            "feature-spec bytes from which the evaluator can recompute that hash."
        ),
    },
    {
        "id": "AMB-POSITIVE-CONTROL-FAMILIES",
        "blocking": True,
        "detail": (
            "D0/D1 require every preregistered family to pass, but the shared "
            "contract does not freeze the family registry, feature path, or token "
            "commitment/reveal representation."
        ),
    },
    {
        "id": "AMB-ANCHOR-VERIFICATION",
        "blocking": False,
        "detail": (
            "The shared contract does not freeze anchor-receipt fields.  The local "
            "profile independently reads a Git blob with git cat-file and requires "
            "an exact Codex-commentary SHA/reference; commentary readback itself is "
            "not available to this standalone process."
        ),
    },
    {
        "id": "AMB-RAW-INSPECT-CANONICALITY",
        "blocking": False,
        "detail": (
            "The contract simultaneously calls docker-inspect files raw daemon bytes "
            "and states that all JSON is canonical; this evaluator preserves raw "
            "bytes and parses them without requiring canonical reserialization."
        ),
    },
    {
        "id": "AMB-HOST-MONOTONIC-RECEIPT",
        "blocking": True,
        "detail": (
            "The contract requires host monotonic nanoseconds to check ordering, "
            "but no exact field names or binding location are frozen in the listed "
            "host-launch/slot/closed objects."
        ),
    },
]


class EvaluationError(RuntimeError):
    """Evidence cannot support the requested qualification."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    try:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise EvaluationError("value is not canonical-JSON representable") from exc
    return rendered.encode("utf-8") + b"\n"


def sha256_canonical(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvaluationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _regular_file(path: pathlib.Path, *, maximum_bytes: int) -> bytes:
    try:
        info = path.lstat()
    except OSError as exc:
        raise EvaluationError(f"missing evidence file: {path}") from exc
    require(stat.S_ISREG(info.st_mode), f"evidence path is not a regular file: {path}")
    require(info.st_size <= maximum_bytes, f"evidence file exceeds size limit: {path}")
    return path.read_bytes()


def parse_json_bytes(raw: bytes, *, label: str) -> Any:
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_pairs)
    except EvaluationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvaluationError(f"invalid UTF-8 JSON: {label}") from exc


def load_json(
    path: pathlib.Path,
    *,
    schema: str | None = None,
    canonical: bool = True,
    allowed_fields: set[str] | None = None,
    maximum_bytes: int = 32 * 1024 * 1024,
) -> tuple[dict[str, Any], bytes]:
    raw = _regular_file(path, maximum_bytes=maximum_bytes)
    parsed = parse_json_bytes(raw, label=str(path))
    require(isinstance(parsed, dict), f"JSON object required: {path}")
    if canonical:
        require(raw == canonical_json_bytes(parsed), f"non-canonical JSON bytes: {path}")
    if schema is not None:
        require(parsed.get("schema") == schema, f"wrong schema in {path}")
    if allowed_fields is not None:
        unknown = sorted(set(parsed) - allowed_fields)
        require(not unknown, f"unknown fields in {path}: {unknown}")
    return parsed, raw


def _hex_bytes(value: Any, *, length: int, label: str) -> bytes:
    require(isinstance(value, str), f"{label} must be hex string")
    require(len(value) == length * 2, f"{label} must encode {length} bytes")
    require(re.fullmatch(r"[0-9a-f]+", value) is not None, f"{label} must be lowercase hex")
    return bytes.fromhex(value)


def commitment(domain: str, seed: bytes, nonce: bytes, public_plan_bytes: bytes) -> str:
    require(domain in DOMAINS, f"unsupported commitment domain: {domain}")
    require(len(seed) == 32 and len(nonce) == 32, "commitment seed/nonce must be 32 bytes")
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\x00"
        + seed
        + b"\x00"
        + nonce
        + b"\x00"
        + public_plan_bytes
    )


class HmacStream:
    """Small deterministic stream used only by the local evaluator profile."""

    def __init__(self, seed: bytes, label: str):
        self.seed = seed
        self.label = label.encode("utf-8")
        self.counter = 0

    def block(self) -> bytes:
        value = hmac.new(
            self.seed,
            self.label + b"\x00" + self.counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        self.counter += 1
        return value

    def randbelow(self, upper: int) -> int:
        require(upper > 0, "randbelow upper must be positive")
        limit = (1 << 256) - ((1 << 256) % upper)
        while True:
            candidate = int.from_bytes(self.block(), "big")
            if candidate < limit:
                return candidate % upper

    def shuffle(self, values: Sequence[Any]) -> list[Any]:
        result = list(values)
        for index in range(len(result) - 1, 0, -1):
            swap = self.randbelow(index + 1)
            result[index], result[swap] = result[swap], result[index]
        return result


def derive_public_ids(seed: bytes, count: int) -> list[str]:
    result = []
    for index in range(count):
        digest = hmac.new(
            seed,
            b"WAVE025_PUBLIC_ID_V1\x00" + index.to_bytes(8, "big"),
            hashlib.sha256,
        ).hexdigest()
        result.append(f"slot-{digest[:32]}")
    return result


def derive_padding(seed: bytes, slot_id: str) -> int:
    digest = hmac.new(
        seed,
        b"WAVE025_PADDING_V1\x00" + slot_id.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return int.from_bytes(digest[:4], "big")


def _validate_sample_plan(sample_plan: Any, mode: str) -> dict[str, dict[str, int]]:
    require(isinstance(sample_plan, dict), "sample_plan must be an object")
    require(set(sample_plan) == set(CHALLENGES), "sample_plan challenge set mismatch")
    normalized: dict[str, dict[str, int]] = {}
    for challenge in CHALLENGES:
        value = sample_plan[challenge]
        require(isinstance(value, dict), f"sample_plan[{challenge}] must be object")
        require(set(value) == set(PARTITIONS), f"sample_plan[{challenge}] split mismatch")
        normalized[challenge] = {}
        for partition in PARTITIONS:
            count = value[partition]
            require(isinstance(count, int) and not isinstance(count, bool) and count > 0, "sample counts must be positive integers")
            require(count % 2 == 0, "every split must be role-balanced")
            normalized[challenge][partition] = count
    if mode == "formal":
        require(normalized == FORMAL_SAMPLE_PLAN, "formal sample plan is not the frozen 1600-slot population")
    return normalized


def derive_mapping(
    public_plan: Mapping[str, Any],
    sample_plan: Mapping[str, Mapping[str, int]],
    block_plan: Mapping[str, Any],
    assignment_seed: bytes,
    padding_seed: bytes,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Derive the local-profile mapping, order, and padding."""

    require(block_plan == {"block_size": 20, "roles_per_block": {"R": 10, "S": 10}}, "unsupported block_plan")
    slots = public_plan.get("slots")
    require(isinstance(slots, list), "public-plan slots must be a list")
    by_challenge: dict[str, list[str]] = {challenge: [] for challenge in CHALLENGES}
    seen: set[str] = set()
    for item in slots:
        require(isinstance(item, dict) and set(item) == {"opaque_slot_id", "challenge"}, "invalid public slot entry")
        slot_id = item["opaque_slot_id"]
        challenge = item["challenge"]
        require(isinstance(slot_id, str) and re.fullmatch(r"slot-[0-9a-f]{32}", slot_id) is not None, "invalid opaque slot id")
        require(challenge in CHALLENGES, "unknown public slot challenge")
        require(slot_id not in seen, "duplicate opaque slot id")
        seen.add(slot_id)
        by_challenge[challenge].append(slot_id)

    mapping: list[dict[str, Any]] = []
    block_size = int(block_plan["block_size"])
    for challenge in CHALLENGES:
        expected = sum(sample_plan[challenge].values())
        require(len(by_challenge[challenge]) == expected, f"population mismatch for {challenge}")
        slot_stream = HmacStream(assignment_seed, f"ASSIGN-SLOTS:{challenge}")
        role_stream = HmacStream(assignment_seed, f"ASSIGN-ROLES:{challenge}")
        shuffled = slot_stream.shuffle(sorted(by_challenge[challenge]))
        offset = 0
        for partition in PARTITIONS:
            count = sample_plan[challenge][partition]
            require(count % block_size == 0, f"split not divisible by block size: {challenge}/{partition}")
            selected = shuffled[offset : offset + count]
            offset += count
            for block_index in range(count // block_size):
                chunk = selected[block_index * block_size : (block_index + 1) * block_size]
                roles = role_stream.shuffle(["R"] * (block_size // 2) + ["S"] * (block_size // 2))
                block_id = f"{challenge}:{partition}:{block_index:03d}"
                for slot_id, role in zip(chunk, roles):
                    mapping.append(
                        {
                            "opaque_slot_id": slot_id,
                            "challenge": challenge,
                            "role": role,
                            "block": block_id,
                            "partition": partition,
                            "padding_units": derive_padding(padding_seed, slot_id),
                        }
                    )
    order_stream = HmacStream(assignment_seed, "EXECUTION-ORDER")
    execution_order = order_stream.shuffle(sorted(seen))
    order_index = {slot_id: index for index, slot_id in enumerate(execution_order)}
    for item in mapping:
        item["execution_index"] = order_index[item["opaque_slot_id"]]
    mapping.sort(key=lambda item: item["opaque_slot_id"])
    return mapping, execution_order


def merkle_root(receipt_hashes: Sequence[str]) -> str:
    require(receipt_hashes, "Merkle tree cannot be empty")
    level = []
    for item in receipt_hashes:
        level.append(_hex_bytes(item, length=32, label="Merkle leaf"))
    while len(level) > 1:
        if len(level) % 2:
            level.append(level[-1])
        level = [
            hashlib.sha256(level[index] + level[index + 1]).digest()
            for index in range(0, len(level), 2)
        ]
    return level[0].hex()


def _binomial_cdf(k: int, n: int, probability: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if probability <= 0.0:
        return 1.0
    if probability >= 1.0:
        return 0.0
    # Direct log terms are stable for the n<=1600 scope and avoid recursive
    # underflow at either endpoint.
    logs = []
    for index in range(k + 1):
        logs.append(
            math.lgamma(n + 1)
            - math.lgamma(index + 1)
            - math.lgamma(n - index + 1)
            + index * math.log(probability)
            + (n - index) * math.log1p(-probability)
        )
    largest = max(logs)
    return min(1.0, math.exp(largest) * sum(math.exp(item - largest) for item in logs))


def clopper_pearson_one_sided(k: int, n: int, confidence: float) -> tuple[float, float]:
    require(0 <= k <= n and n > 0, "invalid binomial counts")
    require(0.5 < confidence < 1.0, "invalid confidence")
    alpha = 1.0 - confidence
    if k == 0:
        lower = 0.0
    else:
        low, high = 0.0, 1.0
        for _ in range(80):
            middle = (low + high) / 2.0
            survival = 1.0 - _binomial_cdf(k - 1, n, middle)
            if survival < alpha:
                low = middle
            else:
                high = middle
        lower = high
    if k == n:
        upper = 1.0
    else:
        low, high = 0.0, 1.0
        for _ in range(80):
            middle = (low + high) / 2.0
            cdf = _binomial_cdf(k, n, middle)
            if cdf > alpha:
                low = middle
            else:
                high = middle
        upper = high
    return lower, upper


def balanced_accuracy(labels: Sequence[int], predictions: Sequence[int]) -> dict[str, Any]:
    require(len(labels) == len(predictions) and labels, "labels/predictions length mismatch")
    counts = {0: {"n": 0, "correct": 0}, 1: {"n": 0, "correct": 0}}
    for label, prediction in zip(labels, predictions):
        require(label in (0, 1) and prediction in (0, 1), "binary labels required")
        counts[label]["n"] += 1
        counts[label]["correct"] += int(label == prediction)
    require(counts[0]["n"] == counts[1]["n"], "balanced accuracy exact CI requires equal class counts")
    tnr = counts[0]["correct"] / counts[0]["n"]
    tpr = counts[1]["correct"] / counts[1]["n"]
    return {
        "balanced_accuracy": (tnr + tpr) / 2.0,
        "specificity": tnr,
        "sensitivity": tpr,
        "correct": counts[0]["correct"] + counts[1]["correct"],
        "n": len(labels),
        "class_counts": {"R": counts[0]["n"], "S": counts[1]["n"]},
    }


def balanced_accuracy_with_ci(
    labels: Sequence[int], predictions: Sequence[int], confidence: float
) -> dict[str, Any]:
    result = balanced_accuracy(labels, predictions)
    lower, upper = clopper_pearson_one_sided(result["correct"], result["n"], confidence)
    result.update(
        {
            "one_sided_confidence": confidence,
            "lower": lower,
            "upper": upper,
            "ci_method": "CLOPPER_PEARSON_BALANCED_TOTAL_ONE_SIDED_V1",
        }
    )
    return result


def flatten_features(value: Any, prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            result.update(flatten_features(value[key], child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            result.update(flatten_features(item, f"{prefix}[{index}]"))
        result[f"{prefix}.__length__"] = len(value)
    elif value is None or isinstance(value, (str, int, float, bool)):
        result[prefix] = value
    else:
        raise EvaluationError(f"unsupported feature scalar at {prefix}")
    return result


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
        try:
            number = float(value)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _feature_priority(path: str) -> tuple[int, str]:
    order = {
        "timing": 0,
        "collection_window": 1,
        "hostname": 2,
        "identity": 3,
        "process_view": 4,
        "directory_trees": 5,
        "environment": 6,
        "argv": 7,
        "cwd": 8,
        "subject_input": 9,
        "input_contract": 10,
        "visible_canaries": 11,
    }
    root = path.split(".", 1)[0].split("[", 1)[0]
    return order.get(root, 99), path


@dataclass
class FeatureEncoder:
    numeric_paths: list[str]
    means: dict[str, float]
    scales: dict[str, float]
    categorical_dimensions: int

    @classmethod
    def fit(cls, rows: Sequence[Mapping[str, Any]]) -> "FeatureEncoder":
        minimum = float(FEATURE_SPEC["numeric_minimum_coverage"])
        paths: set[str] = set()
        for row in rows:
            paths.update(row)
        candidates: list[tuple[float, int, tuple[int, str], str]] = []
        for path in paths:
            numbers = [_numeric(row.get(path)) for row in rows]
            present = [item for item in numbers if item is not None]
            coverage = len(present) / len(rows)
            unique = len(set(present))
            if coverage >= minimum and unique >= 2:
                candidates.append((-coverage, -unique, _feature_priority(path), path))
        candidates.sort()
        numeric_paths = [item[-1] for item in candidates[: int(FEATURE_SPEC["maximum_numeric_paths"])]]
        means: dict[str, float] = {}
        scales: dict[str, float] = {}
        for path in numeric_paths:
            values = [_numeric(row.get(path)) for row in rows]
            present = [item for item in values if item is not None]
            mean = sum(present) / len(present)
            variance = sum((item - mean) ** 2 for item in present) / len(present)
            means[path] = mean
            scales[path] = math.sqrt(variance) if variance > 1e-24 else 1.0
        return cls(
            numeric_paths=numeric_paths,
            means=means,
            scales=scales,
            categorical_dimensions=int(FEATURE_SPEC["categorical_hash_dimensions"]),
        )

    def transform_one(self, row: Mapping[str, Any]) -> list[float]:
        vector: list[float] = []
        numeric_set = set(self.numeric_paths)
        for path in self.numeric_paths:
            value = _numeric(row.get(path))
            if value is None:
                vector.extend((0.0, 1.0))
            else:
                vector.extend(((value - self.means[path]) / self.scales[path], 0.0))
        hashed = [0.0] * self.categorical_dimensions
        for path in sorted(row):
            if path in numeric_set:
                continue
            token = f"{path}={json.dumps(row[path], ensure_ascii=False, sort_keys=True)}".encode("utf-8")
            digest = hashlib.sha256(token).digest()
            index = int.from_bytes(digest[:4], "big") % self.categorical_dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            hashed[index] += sign
        vector.extend(hashed)
        norm = math.sqrt(sum(item * item for item in vector))
        if norm > 0.0:
            vector = [item / norm for item in vector]
        return vector

    def transform(self, rows: Sequence[Mapping[str, Any]]) -> list[list[float]]:
        return [self.transform_one(row) for row in rows]


def _majority(labels: Sequence[int]) -> int:
    ones = sum(labels)
    zeros = len(labels) - ones
    return 1 if ones > zeros else 0


@dataclass
class DeterministicRule:
    path: str | None
    mapping: dict[str, int]
    fallback: int

    def predict(self, rows: Sequence[Mapping[str, Any]]) -> list[int]:
        if self.path is None:
            return [self.fallback] * len(rows)
        return [self.mapping.get(_stable_scalar(row.get(self.path)), self.fallback) for row in rows]


def _stable_scalar(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def fit_deterministic_rule(rows: Sequence[Mapping[str, Any]], labels: Sequence[int]) -> DeterministicRule:
    minimum_support = int(SUPPORTED_CLASSIFIER_PLAN["deterministic"]["minimum_value_support"])
    fallback = _majority(labels)
    paths = sorted(set().union(*(row.keys() for row in rows)))
    best: tuple[float, str, dict[str, int]] | None = None
    for path in paths:
        groups: dict[str, list[int]] = {}
        for row, label in zip(rows, labels):
            groups.setdefault(_stable_scalar(row.get(path)), []).append(label)
        mapping: dict[str, int] = {}
        covered = 0
        valid = True
        for value, group in groups.items():
            if len(group) < minimum_support or len(set(group)) != 1:
                valid = False
                break
            mapping[value] = group[0]
            covered += len(group)
        if valid and mapping:
            candidate = (covered / len(rows), path, mapping)
            if best is None or (candidate[0], candidate[1]) > (best[0], best[1]):
                best = candidate
    if best is None:
        return DeterministicRule(None, {}, fallback)
    return DeterministicRule(best[1], best[2], fallback)


@dataclass
class LogisticModel:
    weights: list[float]
    bias: float

    def predict(self, rows: Sequence[Sequence[float]]) -> list[int]:
        predictions = []
        for row in rows:
            score = self.bias + sum(weight * value for weight, value in zip(self.weights, row))
            predictions.append(1 if score > 0.0 else 0)
        return predictions


def fit_logistic(rows: Sequence[Sequence[float]], labels: Sequence[int]) -> LogisticModel:
    require(rows and len(rows) == len(labels), "logistic training data mismatch")
    dimension = len(rows[0])
    require(all(len(row) == dimension for row in rows), "logistic feature dimensions differ")
    plan = SUPPORTED_CLASSIFIER_PLAN["logistic"]
    epochs = int(plan["epochs"])
    learning_rate = float(plan["learning_rate"])
    l2 = float(plan["l2"])
    weights = [0.0] * dimension
    bias = 0.0
    for epoch in range(epochs):
        gradient = [0.0] * dimension
        bias_gradient = 0.0
        for row, label in zip(rows, labels):
            score = max(-35.0, min(35.0, bias + sum(weight * value for weight, value in zip(weights, row))))
            probability = 1.0 / (1.0 + math.exp(-score))
            error = probability - label
            bias_gradient += error
            for index, value in enumerate(row):
                gradient[index] += error * value
        step = learning_rate / math.sqrt(epoch + 1.0)
        count = float(len(rows))
        for index in range(dimension):
            weights[index] -= step * (gradient[index] / count + l2 * weights[index] / count)
        bias -= step * bias_gradient / count
    return LogisticModel(weights, bias)


@dataclass
class TreeNode:
    prediction: int
    feature: int | None = None
    threshold: float | None = None
    left: "TreeNode | None" = None
    right: "TreeNode | None" = None

    def predict_one(self, row: Sequence[float]) -> int:
        if self.feature is None or self.left is None or self.right is None:
            return self.prediction
        branch = self.left if row[self.feature] <= float(self.threshold) else self.right
        return branch.predict_one(row)

    def predict(self, rows: Sequence[Sequence[float]]) -> list[int]:
        return [self.predict_one(row) for row in rows]


def _gini(labels: Sequence[int]) -> float:
    if not labels:
        return 0.0
    probability = sum(labels) / len(labels)
    return 2.0 * probability * (1.0 - probability)


def fit_bounded_tree(rows: Sequence[Sequence[float]], labels: Sequence[int]) -> TreeNode:
    plan = SUPPORTED_CLASSIFIER_PLAN["bounded_tree"]
    maximum_depth = int(plan["maximum_depth"])
    maximum_thresholds = int(plan["maximum_thresholds_per_feature"])
    minimum_leaf = int(plan["minimum_leaf"])

    def build(indices: list[int], depth: int) -> TreeNode:
        local_labels = [labels[index] for index in indices]
        prediction = _majority(local_labels)
        node = TreeNode(prediction)
        if depth >= maximum_depth or len(set(local_labels)) == 1 or len(indices) < 2 * minimum_leaf:
            return node
        parent_impurity = _gini(local_labels)
        best: tuple[float, int, float, list[int], list[int]] | None = None
        for feature in range(len(rows[0])):
            unique = sorted(set(rows[index][feature] for index in indices))
            if len(unique) < 2:
                continue
            thresholds = []
            for rank in range(1, maximum_thresholds + 1):
                position = min(len(unique) - 1, max(1, round(rank * len(unique) / (maximum_thresholds + 1))))
                thresholds.append((unique[position - 1] + unique[position]) / 2.0)
            for threshold in sorted(set(thresholds)):
                left = [index for index in indices if rows[index][feature] <= threshold]
                right = [index for index in indices if rows[index][feature] > threshold]
                if len(left) < minimum_leaf or len(right) < minimum_leaf:
                    continue
                impurity = (len(left) * _gini([labels[index] for index in left]) + len(right) * _gini([labels[index] for index in right])) / len(indices)
                gain = parent_impurity - impurity
                candidate = (gain, -feature, -threshold, left, right)
                if best is None or candidate[:3] > best[:3]:
                    best = candidate
        if best is None or best[0] <= 0.0:
            return node
        node.feature = -best[1]
        node.threshold = -best[2]
        node.left = build(best[3], depth + 1)
        node.right = build(best[4], depth + 1)
        return node

    return build(list(range(len(rows))), 0)


@dataclass
class KnnModel:
    rows: list[list[float]]
    labels: list[int]
    k: int

    def predict(self, queries: Sequence[Sequence[float]]) -> list[int]:
        predictions = []
        for query in queries:
            distances = []
            for index, row in enumerate(self.rows):
                distance = sum((left - right) ** 2 for left, right in zip(query, row))
                distances.append((distance, index, self.labels[index]))
            distances.sort(key=lambda item: (item[0], item[1]))
            labels = [item[2] for item in distances[: self.k]]
            predictions.append(_majority(labels))
        return predictions


def fit_knn(rows: Sequence[Sequence[float]], labels: Sequence[int]) -> KnnModel:
    k = int(SUPPORTED_CLASSIFIER_PLAN["knn"]["k"])
    require(len(rows) >= k, "insufficient rows for kNN")
    return KnnModel([list(row) for row in rows], list(labels), k)


def _permutation(seed_material: bytes, count: int) -> list[int]:
    stream = HmacStream(hashlib.sha256(seed_material).digest(), "LABEL-PERMUTATION")
    return stream.shuffle(list(range(count)))


def permutation_p_value(
    labels: Sequence[int], predictions: Sequence[int], *, count: int, seed_material: bytes
) -> float:
    observed = balanced_accuracy(labels, predictions)["balanced_accuracy"]
    at_least = 0
    for index in range(count):
        order = _permutation(seed_material + index.to_bytes(8, "big"), len(labels))
        permuted = [labels[item] for item in order]
        value = balanced_accuracy(permuted, predictions)["balanced_accuracy"]
        at_least += int(value >= observed - 1e-15)
    return (at_least + 1.0) / (count + 1.0)


def holm_adjust(raw: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(raw.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    previous = 0.0
    total = len(ordered)
    for index, (name, value) in enumerate(ordered):
        current = min(1.0, (total - index) * value)
        current = max(previous, current)
        adjusted[name] = current
        previous = current
    return adjusted


def _restrict_rows(rows: Sequence[Mapping[str, Any]], prefixes: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            key: value
            for key, value in row.items()
            if any(key == prefix or key.startswith(prefix + ".") or key.startswith(prefix + "[") for prefix in prefixes)
        }
        for row in rows
    ]


def run_classifiers(
    calibration_rows: Sequence[Mapping[str, Any]],
    calibration_labels: Sequence[int],
    holdout_rows: Sequence[Mapping[str, Any]],
    holdout_labels: Sequence[int],
    *,
    confidence: float,
    permutation_seed: bytes,
) -> dict[str, Any]:
    require(calibration_rows and holdout_rows, "classifier split is empty")
    require(len(calibration_rows) == len(calibration_labels), "calibration mismatch")
    require(len(holdout_rows) == len(holdout_labels), "holdout mismatch")
    encoder = FeatureEncoder.fit(calibration_rows)
    train_matrix = encoder.transform(calibration_rows)
    holdout_matrix = encoder.transform(holdout_rows)

    deterministic = fit_deterministic_rule(calibration_rows, calibration_labels)
    models: dict[str, tuple[Any, list[int]]] = {
        "deterministic": (deterministic, deterministic.predict(holdout_rows)),
    }
    logistic = fit_logistic(train_matrix, calibration_labels)
    models["logistic"] = (logistic, logistic.predict(holdout_matrix))
    tree = fit_bounded_tree(train_matrix, calibration_labels)
    models["bounded_tree"] = (tree, tree.predict(holdout_matrix))
    knn = fit_knn(train_matrix, calibration_labels)
    models["knn"] = (knn, knn.predict(holdout_matrix))

    permutation_count = int(SUPPORTED_CLASSIFIER_PLAN["permutation"]["count"])
    results: dict[str, Any] = {}
    raw_p: dict[str, float] = {}
    for name, (_, predictions) in models.items():
        metric = balanced_accuracy_with_ci(holdout_labels, predictions, confidence)
        p_value = permutation_p_value(
            holdout_labels,
            predictions,
            count=permutation_count,
            seed_material=permutation_seed + name.encode("utf-8"),
        )
        metric["label_permutation_p"] = p_value
        if name == "deterministic":
            metric["selected_path"] = deterministic.path
        results[name] = metric
        raw_p[name] = p_value
    adjusted = holm_adjust(raw_p)
    for name, value in adjusted.items():
        results[name]["holm_adjusted_p"] = value
    return {
        "feature_encoding": {
            "schema": FEATURE_SPEC["schema"],
            "numeric_path_count": len(encoder.numeric_paths),
            "numeric_paths_sha256": sha256_canonical(encoder.numeric_paths),
            "categorical_hash_dimensions": encoder.categorical_dimensions,
            "vector_dimensions": len(train_matrix[0]),
        },
        "models": results,
        "multiplicity": "HOLM_V1",
        "permutation_count": permutation_count,
    }


def _role_labels(items: Sequence[Mapping[str, Any]]) -> list[int]:
    labels = []
    for item in items:
        role = item.get("role")
        require(role in ROLES, "invalid hidden role")
        labels.append(1 if role == "S" else 0)
    return labels


def _feature_rows(items: Sequence[Mapping[str, Any]], features: Mapping[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    allowed_roots = set(FEATURE_SPEC["included_roots"])
    for item in items:
        document = features[item["opaque_slot_id"]]
        projected = {key: document[key] for key in sorted(allowed_roots)}
        rows.append(flatten_features(projected))
    return rows


def _host_env(env_items: Any) -> list[dict[str, Any]]:
    require(isinstance(env_items, list), "Docker Config.Env must be list")
    result = []
    for item in env_items:
        require(isinstance(item, str) and "=" in item, "invalid Docker env entry")
        key, value = item.split("=", 1)
        result.append(
            {
                "key": key,
                "value_byte_length": len(value.encode("utf-8")),
                "value_sha256": sha256_bytes(value.encode("utf-8")),
            }
        )
    return sorted(result, key=lambda item: item["key"])


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    require(isinstance(value, list), "expected JSON list")
    return value


def normalize_inspect(raw: Any) -> dict[str, Any]:
    require(isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], dict), "docker inspect must be a one-container array")
    item = raw[0]
    config = item.get("Config")
    host = item.get("HostConfig")
    state = item.get("State")
    mounts = item.get("Mounts")
    require(isinstance(config, dict) and isinstance(host, dict) and isinstance(state, dict), "docker inspect lacks Config/HostConfig/State")
    require(isinstance(mounts, list), "docker inspect Mounts must be list")
    argv = [str(value) for value in _as_list(config.get("Entrypoint")) + _as_list(config.get("Cmd"))]
    normalized_mounts = []
    for mount in mounts:
        require(isinstance(mount, dict), "invalid Docker mount")
        source = str(mount.get("Source", ""))
        normalized_mounts.append(
            {
                "type": str(mount.get("Type", "")),
                "source_sha256": sha256_bytes(source.encode("utf-8")),
                "destination": str(mount.get("Destination", "")),
                "readonly": not bool(mount.get("RW", False)),
                "mode": str(mount.get("Mode", "")),
                "propagation": str(mount.get("Propagation", "")),
            }
        )
    normalized_mounts.sort(key=lambda value: (value["destination"], value["type"], value["source_sha256"]))
    return {
        "container_id": item.get("Id"),
        "container_name": item.get("Name"),
        "image_id": item.get("Image"),
        "argv": argv,
        "env": _host_env(config.get("Env", [])),
        "working_dir": config.get("WorkingDir", ""),
        "user": config.get("User", ""),
        "hostname": config.get("Hostname", ""),
        "network_mode": host.get("NetworkMode"),
        "readonly_rootfs": host.get("ReadonlyRootfs"),
        "cap_drop": sorted(str(value).upper() for value in _as_list(host.get("CapDrop"))),
        "security_opt": sorted(str(value).lower() for value in _as_list(host.get("SecurityOpt"))),
        "privileged": host.get("Privileged"),
        "pid_namespace_mode": host.get("PidMode", ""),
        "ipc_namespace_mode": host.get("IpcMode", ""),
        "uts_namespace_mode": host.get("UTSMode", ""),
        "user_namespace_mode": host.get("UsernsMode", ""),
        "pids_limit": host.get("PidsLimit"),
        "memory_limit_bytes": host.get("Memory"),
        "cpu_limit_nanos": host.get("NanoCpus"),
        "mounts": normalized_mounts,
        "created_at": item.get("Created"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
        "exit_code": state.get("ExitCode"),
        "oom_killed": state.get("OOMKilled"),
        "daemon_error": state.get("Error"),
    }


def validate_isolation(inspect: Mapping[str, Any], challenge: str) -> list[str]:
    if challenge not in ("D1-OCI-CANARY", "T-OCI-ISOLATED"):
        return []
    failures = []
    if inspect.get("network_mode") != "none":
        failures.append("network_mode is not none")
    if inspect.get("readonly_rootfs") is not True:
        failures.append("root filesystem is not read-only")
    if str(inspect.get("user")) not in {"65534", "65534:65534"}:
        failures.append("container user is not frozen non-root 65534:65534")
    if inspect.get("cap_drop") != ["ALL"]:
        failures.append("cap_drop is not exactly ALL")
    if not any(str(item).startswith("no-new-privileges") for item in inspect.get("security_opt", [])):
        failures.append("no-new-privileges missing")
    if inspect.get("privileged") is not False:
        failures.append("privileged is not false")
    if inspect.get("pid_namespace_mode") not in ("", None):
        failures.append("PID namespace is shared")
    if inspect.get("ipc_namespace_mode") not in ("", "private", None):
        failures.append("IPC namespace is shared")
    if inspect.get("uts_namespace_mode") not in ("", None):
        failures.append("UTS namespace is shared")
    for field in ("pids_limit", "memory_limit_bytes", "cpu_limit_nanos"):
        value = inspect.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            failures.append(f"{field} is not a positive limit")
    mounts = inspect.get("mounts", [])
    challenge_mount = [item for item in mounts if item.get("destination") == "/challenge"]
    out_mount = [item for item in mounts if item.get("destination") == "/out"]
    if len(challenge_mount) != 1 or challenge_mount[0].get("type") != "bind" or challenge_mount[0].get("readonly") is not True:
        failures.append("/challenge is not one read-only bind")
    if len(out_mount) != 1 or out_mount[0].get("type") != "tmpfs" or out_mount[0].get("readonly") is not False:
        failures.append("/out is not one writable tmpfs")
    if len(mounts) != 2:
        failures.append("unexpected additional mount")
    if any(item.get("destination") in {"/var/run/docker.sock", "/run/docker.sock"} for item in mounts):
        failures.append("Docker socket mounted")
    return failures


def _compare_host_launch(host_launch: Mapping[str, Any], normalized: Mapping[str, Any]) -> list[str]:
    failures = []
    for key, value in normalized.items():
        if host_launch.get(key) != value:
            failures.append(f"host-launch mismatch: {key}")
    return failures


def _stable_host_projection(host_launch: Mapping[str, Any]) -> dict[str, Any]:
    mounts = []
    for item in host_launch.get("mounts", []):
        mounts.append(
            {
                key: value
                for key, value in item.items()
                if key != "source_sha256"
            }
        )
    mounts.sort(key=lambda item: (item.get("destination"), item.get("type")))
    keys = (
        "image_id", "repo_digest_or_null", "base_repo_digest", "argv", "env",
        "working_dir", "user", "hostname", "network_mode", "readonly_rootfs",
        "cap_drop", "security_opt", "privileged", "pid_namespace_mode",
        "ipc_namespace_mode", "uts_namespace_mode", "user_namespace_mode",
        "pids_limit", "memory_limit_bytes", "cpu_limit_nanos",
    )
    return {**{key: host_launch.get(key) for key in keys}, "mounts": mounts}


def _allowed_collector_document(document: Mapping[str, Any]) -> None:
    require(set(document) == COLLECTOR_TOP_LEVEL_FIELDS, "collector feature top-level field set mismatch")
    require(document.get("schema") == COLLECTOR_SCHEMA, "collector feature schema mismatch")
    contract = document.get("contract")
    require(isinstance(contract, dict), "collector contract missing")
    require(contract.get("lawful_truth_api_calls") == 0, "collector reports lawful truth call")
    require(contract.get("network_calls") == 0, "collector reports network call")
    require(contract.get("does_not_rank_treatments") is True, "collector contract rank guard missing")
    require(contract.get("does_not_score_leakage") is True, "collector contract score guard missing")


def read_collector_channels(slot_dir: pathlib.Path) -> tuple[dict[str, Any], dict[str, str]]:
    """Read and compare raw stdout/stderr/out plus the frozen feature copy."""

    stdout = _regular_file(slot_dir / "collector-stdout.bin", maximum_bytes=32 * 1024 * 1024)
    stderr = _regular_file(slot_dir / "collector-stderr.bin", maximum_bytes=4 * 1024 * 1024)
    out_bytes = _regular_file(slot_dir / "collector-out.bin", maximum_bytes=32 * 1024 * 1024)
    feature_bytes = _regular_file(slot_dir / "collector-features.json", maximum_bytes=32 * 1024 * 1024)
    require(stderr == b"", "collector stderr is not empty")
    require(stdout == out_bytes == feature_bytes, "collector stdout/out/frozen feature bytes differ")
    feature_doc = parse_json_bytes(feature_bytes, label=f"{slot_dir.name}/collector-features")
    require(feature_bytes == canonical_json_bytes(feature_doc), f"collector features non-canonical: {slot_dir.name}")
    require(isinstance(feature_doc, dict), "collector features must be object")
    _allowed_collector_document(feature_doc)
    return feature_doc, {
        "collector-stdout.bin": sha256_bytes(stdout),
        "collector-stderr.bin": sha256_bytes(stderr),
        "collector-out.bin": sha256_bytes(out_bytes),
        "collector-features.json": sha256_bytes(feature_bytes),
    }


def _forbidden_output_keys(value: Any, path: str = "") -> list[str]:
    forbidden = {"winner", "ranking", "coverage", "pareto", "a1", "a2", "a3", "a4", "a5"}
    hits = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key.lower() in forbidden:
                hits.append(child)
            hits.extend(_forbidden_output_keys(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_forbidden_output_keys(item, f"{path}[{index}]"))
    return hits


def _claim(status: str, evidence: str) -> dict[str, str]:
    return {"status": status, "evidence": evidence}


def verify_external_anchor(anchor: Mapping[str, Any], precommit_raw: bytes) -> dict[str, Any]:
    """Verify the planned dual anchor without trusting the receipt's assertion.

    The Git object is read with ``git cat-file`` and compared byte-for-byte.
    Codex commentary is not queryable from this standalone evaluator, so its
    recorded digest is checked for consistency but never described as an
    independently read-back external fact.
    """

    expected_sha = sha256_bytes(precommit_raw)
    anchor_type = anchor.get("anchor_type")
    if anchor_type == "LOCAL_NONQUALIFYING_ANCHOR":
        return {
            "eligible": False,
            "anchor_type": anchor_type,
            "precommit_sha256_matches": anchor.get("precommit_sha256") == expected_sha,
            "git_object_verified": False,
            "commentary_readback_verified": False,
            "errors": ["local anchor is structurally useful but non-qualifying"],
        }
    errors = []
    git_object = anchor.get("git_object")
    git_verified = False
    object_type = None
    if not isinstance(git_object, dict):
        errors.append("dual anchor lacks git_object")
    else:
        if set(git_object) != {"repository", "object_id"}:
            errors.append("git_object field set differs from local anchor profile")
        repository = git_object.get("repository")
        object_id = git_object.get("object_id")
        if not isinstance(repository, str) or not pathlib.Path(repository).is_absolute():
            errors.append("git anchor repository must be an absolute path")
        elif not isinstance(object_id, str) or re.fullmatch(r"[0-9a-f]{40,64}", object_id) is None:
            errors.append("git anchor object_id is invalid")
        else:
            try:
                type_result = subprocess.run(
                    ["git", "-C", repository, "cat-file", "-t", object_id],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                object_type = type_result.stdout.decode("ascii", errors="strict").strip()
                require(object_type == "blob", "Git anchor object is not a blob")
                content_result = subprocess.run(
                    ["git", "-C", repository, "cat-file", "blob", object_id],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10,
                )
                require(content_result.stdout == precommit_raw, "Git anchor blob bytes differ from precommit")
                git_verified = True
            except (OSError, UnicodeDecodeError, subprocess.SubprocessError, EvaluationError) as exc:
                errors.append(f"Git object readback failed: {exc}")
    commentary = anchor.get("codex_commentary")
    commentary_digest_matches = (
        isinstance(commentary, dict)
        and set(commentary) == {"precommit_sha256", "message_reference"}
        and commentary.get("precommit_sha256") == expected_sha
        and isinstance(commentary.get("message_reference"), str)
        and bool(commentary.get("message_reference"))
    )
    if not commentary_digest_matches:
        errors.append("Codex commentary receipt does not record the exact precommit SHA/reference")
    if anchor.get("precommit_sha256") != expected_sha:
        errors.append("anchor receipt precommit SHA mismatch")
    return {
        "eligible": (
            anchor_type == "DUAL_CODEX_COMMENTARY_AND_GIT_BLOB"
            and git_verified
            and commentary_digest_matches
            and not errors
        ),
        "anchor_type": anchor_type,
        "precommit_sha256_matches": anchor.get("precommit_sha256") == expected_sha,
        "git_object_verified": git_verified,
        "git_object_type": object_type,
        "commentary_digest_matches": commentary_digest_matches,
        "commentary_readback_verified": False,
        "errors": errors,
    }


@dataclass
class BatchData:
    precommit: dict[str, Any]
    precommit_raw: bytes
    anchor: dict[str, Any]
    public_plan: dict[str, Any]
    public_plan_raw: bytes
    private_state: dict[str, Any]
    closed: dict[str, Any]
    closed_raw: bytes
    reveal: dict[str, Any]
    slot_features: dict[str, dict[str, Any]]
    host_documents: dict[str, dict[str, Any]]
    mapping: list[dict[str, Any]]
    host_failures: dict[str, list[str]]
    evidence_checks: dict[str, Any]


def _precommit_allowed() -> set[str]:
    return {
        "schema", "batch_id", "mode", "challenges", "created_at",
        "question_sha256", "qualification_contract_sha256", "batch_contract_sha256",
        "collector_source_sha256", "collector_dockerfile_sha256", "collector_image_id",
        "collector_image_repo_digest_or_null", "collector_base_repo_digest",
        "runner_source_sha256", "evaluator_source_sha256", "feature_spec_sha256",
        "sample_plan", "block_plan", "classifier_plan", "thresholds",
        "assignment_algorithm", "public_id_algorithm", "padding_algorithm",
        "assignment_commitment", "public_id_commitment", "padding_commitment", "diagnostics",
    }


ANCHOR_FIELDS = {
    "schema", "batch_id", "anchor_type", "anchored_at", "precommit_sha256",
    "git_object", "codex_commentary", "diagnostics",
}
PUBLIC_PLAN_FIELDS = {
    "schema", "batch_id", "mode", "challenges", "slot_count", "block_shape",
    "slots", "public_packet_sha256", "resource_envelope", "launch_templates", "diagnostics",
}
PRIVATE_STATE_FIELDS = {
    "schema", "batch_id", "domains", "mapping", "execution_order", "diagnostics",
}
CLOSED_FIELDS = {
    "schema", "batch_id", "status", "slots", "first_host_time", "last_host_time",
    "docker_daemon", "docker_version", "merkle_algorithm", "merkle_root", "diagnostics",
}
REVEAL_FIELDS = {
    "schema", "batch_id", "status", "closed_sha256", "domains", "mapping",
    "execution_order", "reconstruction", "diagnostics",
}
HOST_LAUNCH_FIELDS = {
    "schema", "opaque_slot_id", "container_id", "container_name", "image_id",
    "repo_digest_or_null", "base_repo_digest", "argv", "env", "working_dir", "user",
    "hostname", "network_mode", "readonly_rootfs", "cap_drop", "security_opt",
    "privileged", "pid_namespace_mode", "ipc_namespace_mode", "uts_namespace_mode",
    "user_namespace_mode", "pids_limit", "memory_limit_bytes", "cpu_limit_nanos",
    "mounts", "created_at", "started_at", "finished_at", "exit_code", "oom_killed",
    "daemon_error", "diagnostics",
}
SLOT_RECEIPT_FIELDS = {
    "schema", "opaque_slot_id", "challenge", "files", "execution_index", "exit_code",
    "infrastructure_classification", "attempts", "diagnostics",
}
CLOSED_SLOT_FIELDS = {
    "opaque_slot_id", "challenge", "attempt_count", "files", "missing", "duplicate", "failed",
}


def _public_forbidden_key_paths(value: Any, path: str = "") -> list[str]:
    forbidden = {"role", "seed", "nonce", "mapping", "execution_order", "expected", "token", "case", "private_hash"}
    hits = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            if key.lower() in forbidden:
                hits.append(child)
            hits.extend(_public_forbidden_key_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_public_forbidden_key_paths(item, f"{path}[{index}]"))
    return hits


def _verify_source_preimages(precommit: Mapping[str, Any]) -> list[str]:
    base = pathlib.Path(__file__).resolve().parent.parent
    paths = {
        "question_sha256": base / "QUESTION.md",
        "qualification_contract_sha256": base / "QUALIFICATION-CONTRACT.md",
        "batch_contract_sha256": base / "BATCH-EVIDENCE-CONTRACT.md",
        "collector_source_sha256": base / "attackers" / "leak-only-collector" / "collector.js",
        "collector_dockerfile_sha256": base / "attackers" / "leak-only-collector" / "Dockerfile",
        "evaluator_source_sha256": pathlib.Path(__file__).resolve(),
    }
    failures = []
    for field, path in paths.items():
        try:
            actual = sha256_file(path)
        except OSError:
            failures.append(f"source preimage unavailable: {field}")
            continue
        if precommit.get(field) != actual:
            failures.append(f"source preimage mismatch: {field}")
    if precommit.get("feature_spec_sha256") != sha256_canonical(FEATURE_SPEC):
        failures.append("feature_spec_sha256 does not match evaluator-local profile")
    return failures


def _validate_classifier_plan(value: Any) -> tuple[dict[str, Any], list[str]]:
    require(isinstance(value, dict), "classifier_plan must be object")
    expected = dict(SUPPORTED_CLASSIFIER_PLAN)
    families = value.get("positive_control_families")
    require(isinstance(families, dict) and set(families) == {"D0-HOST-LEAK", "D1-OCI-CANARY"}, "positive-control family registry missing")
    expected["positive_control_families"] = families
    require(value == expected, "classifier_plan differs from supported pure-Python profile")
    failures = []
    for challenge, entries in families.items():
        require(isinstance(entries, list) and entries, f"no preregistered families for {challenge}")
        seen = set()
        for entry in entries:
            require(isinstance(entry, dict) and set(entry) == {"name", "path_prefixes"}, "invalid positive-control family")
            require(isinstance(entry["name"], str) and entry["name"] and entry["name"] not in seen, "duplicate/empty family name")
            seen.add(entry["name"])
            prefixes = entry["path_prefixes"]
            require(isinstance(prefixes, list) and prefixes and all(isinstance(item, str) and item for item in prefixes), "invalid family prefixes")
            allowed = set(FEATURE_SPEC["included_roots"])
            if any(prefix.split(".", 1)[0].split("[", 1)[0] not in allowed for prefix in prefixes):
                failures.append(f"family uses non-allowlisted root: {challenge}/{entry['name']}")
    return value, failures


def _load_batch(batch_root: pathlib.Path) -> BatchData:
    require(batch_root.is_absolute(), "batch path must be absolute")
    require(batch_root.is_dir(), "batch path is not a directory")
    require(not batch_root.is_symlink(), "batch root cannot be a symlink")

    precommit, precommit_raw = load_json(
        batch_root / "precommit.json",
        schema=PRECOMMIT_SCHEMA,
        allowed_fields=_precommit_allowed(),
    )
    anchor, _ = load_json(
        batch_root / "anchor-receipt.json", schema=ANCHOR_SCHEMA, allowed_fields=ANCHOR_FIELDS
    )
    public_plan, public_plan_raw = load_json(
        batch_root / "public-plan.json", schema=PUBLIC_PLAN_SCHEMA, allowed_fields=PUBLIC_PLAN_FIELDS
    )
    private_state, _ = load_json(
        batch_root / "runner-private-state.json", schema=PRIVATE_STATE_SCHEMA, allowed_fields=PRIVATE_STATE_FIELDS
    )
    closed, closed_raw = load_json(
        batch_root / "closed.json", schema=CLOSED_SCHEMA, allowed_fields=CLOSED_FIELDS
    )
    reveal, _ = load_json(
        batch_root / "reveal.json", schema=REVEAL_SCHEMA, allowed_fields=REVEAL_FIELDS
    )

    require(precommit.get("batch_id") == public_plan.get("batch_id") == private_state.get("batch_id") == closed.get("batch_id") == reveal.get("batch_id"), "batch_id mismatch")
    require(anchor.get("batch_id") == precommit.get("batch_id"), "anchor batch_id mismatch")
    mode = precommit.get("mode")
    require(mode in {"smoke", "formal"}, "mode must be smoke or formal")
    require(precommit.get("challenges") == list(CHALLENGES), "precommit challenge suite mismatch")
    require(public_plan.get("challenges") == list(CHALLENGES), "public-plan challenge suite mismatch")
    require(public_plan.get("mode") == mode, "public-plan mode mismatch")
    require(closed.get("status") == "CLOSED", "batch is not CLOSED")
    require(reveal.get("status") == "REVEALED", "batch is not REVEALED")
    require(reveal.get("closed_sha256") == sha256_bytes(closed_raw), "reveal does not bind closed bytes")
    require(anchor.get("precommit_sha256") == sha256_bytes(precommit_raw), "anchor does not bind precommit bytes")
    require(public_plan.get("public_packet_sha256") == sha256_bytes(b'{"schema":"WAVE025_LEAK_ONLY_COLLECTOR_INPUT_V1"}\n'), "public packet hash mismatch")
    require(not _public_forbidden_key_paths(public_plan), "public plan contains a forbidden hidden-control key")
    require(not _public_forbidden_key_paths(precommit), "precommit contains seed/nonce/mapping/order/truth material")

    sample_plan = _validate_sample_plan(precommit.get("sample_plan"), mode)
    require(public_plan.get("slot_count") == sum(sum(value.values()) for value in sample_plan.values()), "public slot_count mismatch")
    require(precommit.get("assignment_algorithm") == ASSIGNMENT_ALGORITHM, "unsupported assignment algorithm")
    require(precommit.get("public_id_algorithm") == PUBLIC_ID_ALGORITHM, "unsupported public-id algorithm")
    require(precommit.get("padding_algorithm") == PADDING_ALGORITHM, "unsupported padding algorithm")
    _, classifier_failures = _validate_classifier_plan(precommit.get("classifier_plan"))
    require(precommit.get("thresholds") == SUPPORTED_THRESHOLDS, "thresholds differ from frozen evaluator profile")

    source_failures = _verify_source_preimages(precommit)
    domains = reveal.get("domains")
    require(isinstance(domains, dict) and set(domains) == set(DOMAINS), "reveal domain set mismatch")
    domain_bytes: dict[str, tuple[bytes, bytes]] = {}
    for domain in DOMAINS:
        item = domains[domain]
        require(isinstance(item, dict) and set(item) == {"seed_hex", "nonce_hex"}, f"invalid reveal domain {domain}")
        domain_bytes[domain] = (
            _hex_bytes(item["seed_hex"], length=32, label=f"{domain} seed"),
            _hex_bytes(item["nonce_hex"], length=32, label=f"{domain} nonce"),
        )
    all_secrets = [value for pair in domain_bytes.values() for value in pair]
    require(len(set(all_secrets)) == len(all_secrets), "RNG seed/nonce reuse across domains")
    commitment_fields = {
        "PRIVATE_ASSIGNMENT_ORDER": "assignment_commitment",
        "PUBLIC_ID": "public_id_commitment",
        "MEASUREMENT_PADDING": "padding_commitment",
    }
    commitment_failures = []
    for domain, field in commitment_fields.items():
        seed, nonce = domain_bytes[domain]
        actual = commitment(domain, seed, nonce, public_plan_raw)
        if precommit.get(field) != actual:
            commitment_failures.append(f"commitment mismatch: {domain}")

    public_slots = public_plan.get("slots")
    require(isinstance(public_slots, list), "public-plan slots missing")
    expected_ids = derive_public_ids(domain_bytes["PUBLIC_ID"][0], len(public_slots))
    actual_ids = [item.get("opaque_slot_id") if isinstance(item, dict) else None for item in public_slots]
    public_id_failures = [] if actual_ids == expected_ids else ["opaque slot IDs do not reconstruct"]
    expected_mapping, expected_order = derive_mapping(
        public_plan,
        sample_plan,
        precommit.get("block_plan"),
        domain_bytes["PRIVATE_ASSIGNMENT_ORDER"][0],
        domain_bytes["MEASUREMENT_PADDING"][0],
    )
    reveal_mapping = reveal.get("mapping")
    require(isinstance(reveal_mapping, list), "reveal mapping missing")
    mapping_failures = [] if reveal_mapping == expected_mapping else ["reveal mapping does not reconstruct"]
    if reveal.get("execution_order") != expected_order:
        mapping_failures.append("execution order does not reconstruct")
    if private_state.get("domains") != reveal.get("domains") or private_state.get("mapping") != reveal_mapping or private_state.get("execution_order") != reveal.get("execution_order"):
        mapping_failures.append("runner-private-state and reveal differ")

    planned_ids = set(actual_ids)
    slot_root = batch_root / "slots"
    require(slot_root.is_dir() and not slot_root.is_symlink(), "slots directory missing or symlinked")
    actual_dirs = {item.name for item in slot_root.iterdir() if item.is_dir() and not item.is_symlink()}
    require(actual_dirs == planned_ids, "slot directory population mismatch")
    require(all(item.name in planned_ids for item in slot_root.iterdir()), "unexpected non-slot entry")

    closed_entries = closed.get("slots")
    require(isinstance(closed_entries, list), "closed slots missing")
    require([item.get("opaque_slot_id") for item in closed_entries] == sorted(planned_ids), "closed slots not exact sorted population")
    closed_by_id = {item["opaque_slot_id"]: item for item in closed_entries}
    require(len(closed_by_id) == len(closed_entries), "duplicate closed slot")
    receipt_hashes = []
    slot_features: dict[str, dict[str, Any]] = {}
    host_documents: dict[str, dict[str, Any]] = {}
    host_failures: dict[str, list[str]] = {}
    raw_equality_failures: list[str] = []
    receipt_failures: list[str] = []
    mapping_by_id = {item["opaque_slot_id"]: item for item in reveal_mapping}
    require(set(mapping_by_id) == planned_ids, "reveal mapping population mismatch")

    for slot_id in sorted(planned_ids):
        slot_dir = slot_root / slot_id
        expected_names = set(SLOT_RAW_FILES) | {"slot-receipt.json"}
        names = {item.name for item in slot_dir.iterdir()}
        require(names == expected_names, f"slot file set mismatch: {slot_id}")
        require(all(not item.is_symlink() for item in slot_dir.iterdir()), f"slot contains symlink: {slot_id}")
        plan_item = next(item for item in public_slots if item["opaque_slot_id"] == slot_id)
        challenge = plan_item["challenge"]

        pre_raw = _regular_file(slot_dir / "docker-inspect-pre.json", maximum_bytes=16 * 1024 * 1024)
        post_raw = _regular_file(slot_dir / "docker-inspect-post.json", maximum_bytes=16 * 1024 * 1024)
        pre_inspect = normalize_inspect(parse_json_bytes(pre_raw, label=f"{slot_id}/inspect-pre"))
        post_inspect = normalize_inspect(parse_json_bytes(post_raw, label=f"{slot_id}/inspect-post"))
        immutable_keys = set(pre_inspect) - {"started_at", "finished_at", "exit_code", "oom_killed", "daemon_error"}
        local_host_failures = [f"inspect pre/post drift: {key}" for key in sorted(immutable_keys) if pre_inspect.get(key) != post_inspect.get(key)]
        local_host_failures.extend(validate_isolation(post_inspect, challenge))
        host_launch, host_raw = load_json(
            slot_dir / "host-launch.json",
            schema=HOST_LAUNCH_SCHEMA,
            allowed_fields=HOST_LAUNCH_FIELDS,
        )
        host_documents[slot_id] = host_launch
        local_host_failures.extend(_compare_host_launch(host_launch, post_inspect))
        if host_launch.get("opaque_slot_id") != slot_id:
            local_host_failures.append("host-launch slot id mismatch")
        if host_launch.get("image_id") != precommit.get("collector_image_id"):
            local_host_failures.append("actual final image ID differs from precommit")
        if host_launch.get("base_repo_digest") != precommit.get("collector_base_repo_digest"):
            local_host_failures.append("base repo digest differs from precommit")
        committed_repo = precommit.get("collector_image_repo_digest_or_null")
        if host_launch.get("repo_digest_or_null") != committed_repo:
            local_host_failures.append("final repo digest differs from precommit")
        if committed_repo is None:
            for field in ("collector_image_id", "collector_source_sha256", "collector_dockerfile_sha256", "collector_base_repo_digest"):
                if not isinstance(precommit.get(field), str) or not precommit[field]:
                    local_host_failures.append(f"null final RepoDigest lacks binding: {field}")
        if post_inspect.get("exit_code") != 0 or post_inspect.get("oom_killed") is not False or post_inspect.get("daemon_error") not in ("", None):
            local_host_failures.append("container exit state is not clean")
        host_failures[slot_id] = local_host_failures

        try:
            feature_doc, _ = read_collector_channels(slot_dir)
            slot_features[slot_id] = feature_doc
        except EvaluationError as exc:
            raw_equality_failures.append(f"{slot_id}: {exc}")
            # Preserve fail-closed behavior: malformed feature bytes are not
            # admitted to the feature matrix.
            raise

        receipt, receipt_raw = load_json(
            slot_dir / "slot-receipt.json",
            schema=SLOT_RECEIPT_SCHEMA,
            allowed_fields=SLOT_RECEIPT_FIELDS,
        )
        receipt_hashes.append(sha256_bytes(receipt_raw))
        if receipt.get("opaque_slot_id") != slot_id or receipt.get("challenge") != challenge:
            receipt_failures.append(f"slot receipt identity mismatch: {slot_id}")
        if receipt.get("execution_index") != mapping_by_id[slot_id]["execution_index"]:
            receipt_failures.append(f"slot receipt execution index mismatch: {slot_id}")
        if receipt.get("exit_code") != 0:
            receipt_failures.append(f"slot receipt exit code nonzero: {slot_id}")
        files = receipt.get("files")
        require(isinstance(files, dict) and set(files) == set(SLOT_RAW_FILES), f"slot receipt file set mismatch: {slot_id}")
        for filename in SLOT_RAW_FILES:
            actual = sha256_file(slot_dir / filename)
            if files.get(filename) != actual:
                receipt_failures.append(f"slot receipt hash mismatch: {slot_id}/{filename}")
        closed_entry = closed_by_id[slot_id]
        require(set(closed_entry) == CLOSED_SLOT_FIELDS, f"closed slot field set mismatch: {slot_id}")
        if closed_entry.get("challenge") != challenge or closed_entry.get("attempt_count") != 1:
            receipt_failures.append(f"closed slot identity/attempt mismatch: {slot_id}")
        if closed_entry.get("files") != files | {"slot-receipt.json": sha256_bytes(receipt_raw)}:
            receipt_failures.append(f"closed slot hashes mismatch: {slot_id}")
        if any(closed_entry.get(key) is not False for key in ("missing", "duplicate", "failed")):
            receipt_failures.append(f"closed slot is not complete: {slot_id}")

    isolated_ids = [
        item["opaque_slot_id"]
        for item in public_slots
        if item["challenge"] in ("D1-OCI-CANARY", "T-OCI-ISOLATED")
    ]
    if isolated_ids:
        reference_projection = _stable_host_projection(host_documents[isolated_ids[0]])
        for slot_id in isolated_ids[1:]:
            if _stable_host_projection(host_documents[slot_id]) != reference_projection:
                host_failures[slot_id].append("D1/T stable host projection drift")

    merkle_failures = []
    if closed.get("merkle_algorithm") != MERKLE_ALGORITHM:
        merkle_failures.append("unsupported Merkle algorithm")
    elif closed.get("merkle_root") != merkle_root(receipt_hashes):
        merkle_failures.append("Merkle root mismatch")

    checks = {
        "source_preimages": source_failures,
        "classifier_plan": classifier_failures,
        "commitments": commitment_failures,
        "public_ids": public_id_failures,
        "mapping_and_private_state": mapping_failures,
        "raw_stdout_out_equality": raw_equality_failures,
        "slot_receipts_and_close": receipt_failures,
        "merkle": merkle_failures,
    }
    return BatchData(
        precommit=precommit,
        precommit_raw=precommit_raw,
        anchor=anchor,
        public_plan=public_plan,
        public_plan_raw=public_plan_raw,
        private_state=private_state,
        closed=closed,
        closed_raw=closed_raw,
        reveal=reveal,
        slot_features=slot_features,
        host_documents=host_documents,
        mapping=reveal_mapping,
        host_failures=host_failures,
        evidence_checks=checks,
    )


def _split_items(mapping: Sequence[Mapping[str, Any]], challenge: str, partition: str) -> list[dict[str, Any]]:
    result = [dict(item) for item in mapping if item.get("challenge") == challenge and item.get("partition") == partition]
    result.sort(key=lambda item: item["opaque_slot_id"])
    require(result, f"empty split: {challenge}/{partition}")
    labels = _role_labels(result)
    require(labels.count(0) == labels.count(1), f"unbalanced split: {challenge}/{partition}")
    return result


def _evaluate_positive_controls(data: BatchData) -> tuple[dict[str, Any], bool]:
    confidence = float(data.precommit["thresholds"]["confidence"])
    minimum = float(data.precommit["thresholds"]["positive_control_holdout_ba_lower_min"])
    families = data.precommit["classifier_plan"]["positive_control_families"]
    result: dict[str, Any] = {}
    all_pass = True
    for challenge in ("D0-HOST-LEAK", "D1-OCI-CANARY"):
        calibration = _split_items(data.mapping, challenge, "calibration")
        holdout = _split_items(data.mapping, challenge, "holdout")
        calibration_rows = _feature_rows(calibration, data.slot_features)
        holdout_rows = _feature_rows(holdout, data.slot_features)
        calibration_labels = _role_labels(calibration)
        holdout_labels = _role_labels(holdout)
        family_results = {}
        for family in families[challenge]:
            train = _restrict_rows(calibration_rows, family["path_prefixes"])
            test = _restrict_rows(holdout_rows, family["path_prefixes"])
            classification = run_classifiers(
                train,
                calibration_labels,
                test,
                holdout_labels,
                confidence=confidence,
                permutation_seed=hashlib.sha256(data.precommit_raw + challenge.encode() + family["name"].encode()).digest(),
            )
            best_name, best_metric = max(
                classification["models"].items(),
                key=lambda item: (item[1]["lower"], item[1]["balanced_accuracy"], item[0]),
            )
            passed = best_metric["lower"] >= minimum
            all_pass = all_pass and passed
            family_results[family["name"]] = {
                "path_prefixes": family["path_prefixes"],
                "best_model": best_name,
                "best_metric": best_metric,
                "passed": passed,
                "classifiers": classification,
            }
        result[challenge] = {"families": family_results, "passed": all(item["passed"] for item in family_results.values())}
    return result, all_pass


def _evaluate_t(data: BatchData) -> tuple[dict[str, Any], bool]:
    calibration = _split_items(data.mapping, "T-OCI-ISOLATED", "calibration")
    holdout = _split_items(data.mapping, "T-OCI-ISOLATED", "holdout")
    classification = run_classifiers(
        _feature_rows(calibration, data.slot_features),
        _role_labels(calibration),
        _feature_rows(holdout, data.slot_features),
        _role_labels(holdout),
        confidence=float(data.precommit["thresholds"]["confidence"]),
        permutation_seed=hashlib.sha256(data.precommit_raw + b"T-OCI-ISOLATED").digest(),
    )
    upper_limit = float(data.precommit["thresholds"]["t_holdout_ba_upper_max"])
    deterministic_limit = float(data.precommit["thresholds"]["deterministic_stable_recovery_ba"])
    failures = []
    for name, metric in classification["models"].items():
        if name == "deterministic" and metric["balanced_accuracy"] >= deterministic_limit:
            failures.append("deterministic stable role recovery")
        if metric["upper"] > upper_limit:
            failures.append(f"{name} one-sided upper bound exceeds {upper_limit}")
    classification["equivalence_rule"] = {
        "required_upper_at_most": upper_limit,
        "ordinary_p_gt_0_05_is_not_equivalence": True,
        "passed": not failures,
    }
    classification["failures"] = failures
    return classification, not failures


def _order_association(mapping: Sequence[Mapping[str, Any]], precommit_raw: bytes) -> dict[str, Any]:
    # Execution order is host-only and excluded from predictors, but a direct
    # monotone role/order association is still audited.
    items = sorted(mapping, key=lambda item: item["execution_index"])
    labels = _role_labels(items)
    midpoint = len(items) // 2
    predictions = [0 if index < midpoint else 1 for index in range(len(items))]
    if labels.count(0) != labels.count(1):
        return {"status": "INVALID_UNBALANCED", "balanced_accuracy": None}
    metric = balanced_accuracy_with_ci(labels, predictions, 0.95)
    metric["permutation_p"] = permutation_p_value(
        labels,
        predictions,
        count=int(SUPPORTED_CLASSIFIER_PLAN["permutation"]["count"]),
        seed_material=hashlib.sha256(precommit_raw + b"ORDER-AUDIT").digest(),
    )
    metric["classifier_feature"] = False
    return metric


def _host_only_deterministic_audit(data: BatchData) -> dict[str, Any]:
    calibration = _split_items(data.mapping, "T-OCI-ISOLATED", "calibration")
    holdout = _split_items(data.mapping, "T-OCI-ISOLATED", "holdout")

    def rows(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for item in items:
            host = data.host_documents[item["opaque_slot_id"]]
            selected = {
                "opaque_slot_id": item["opaque_slot_id"],
                "execution_index": item["execution_index"],
                "container_id": host.get("container_id"),
                "container_name": host.get("container_name"),
                "created_at": host.get("created_at"),
                "started_at": host.get("started_at"),
                "finished_at": host.get("finished_at"),
                "mount_source_hashes": [
                    mount.get("source_sha256") for mount in host.get("mounts", [])
                ],
            }
            result.append(flatten_features(selected))
        return result

    rule = fit_deterministic_rule(rows(calibration), _role_labels(calibration))
    predictions = rule.predict(rows(holdout))
    metric = balanced_accuracy_with_ci(_role_labels(holdout), predictions, 0.95)
    metric.update(
        {
            "selected_path": rule.path,
            "classifier_feature": False,
            "purpose": "separate association audit only",
        }
    )
    return metric


def evaluate_batch(batch_root: pathlib.Path) -> dict[str, Any]:
    """Evaluate without writing or changing the supplied batch."""

    errors: list[str] = []
    try:
        data = _load_batch(batch_root.resolve())
        all_check_failures = [
            f"{group}: {failure}"
            for group, failures in data.evidence_checks.items()
            for failure in failures
        ]
        all_host_failures = [
            f"{slot_id}: {failure}"
            for slot_id, failures in data.host_failures.items()
            for failure in failures
        ]
        evidence_ok = not all_check_failures
        host_ok = not all_host_failures
        controls, controls_ok = _evaluate_positive_controls(data)
        t_result, t_ok = _evaluate_t(data)
        random_ok = not any(
            data.evidence_checks[name]
            for name in ("commitments", "public_ids", "mapping_and_private_state")
        )
        anchor_verification = verify_external_anchor(data.anchor, data.precommit_raw)
        external_anchor = bool(anchor_verification["eligible"])
        blocking_ambiguities = [item["id"] for item in CONTRACT_AMBIGUITIES if item["blocking"]]

        if not t_ok:
            final_status = "BLIND_QUALIFICATION_FAILED"
        elif not evidence_ok or not host_ok or not controls_ok or not random_ok:
            final_status = "NOT_QUALIFIED"
        elif data.precommit.get("mode") != "formal":
            final_status = "STRUCTURAL_PREFIX_ONLY"
        elif not external_anchor or blocking_ambiguities:
            final_status = "NOT_QUALIFIED"
        else:
            final_status = "PREFIX_QUALIFIED_SCOPED"

        claims = {
            "CL-025-LEAK-DETECTOR-SENSITIVITY": _claim(
                "SUPPORT_SCOPED" if controls_ok else "FAIL",
                "D0 predecessor/shared-state and D1 current-run canary families both pass the frozen holdout lower-bound gate."
                if controls_ok
                else "At least one preregistered D0/D1 positive-control family did not pass the holdout lower-bound gate.",
            ),
            "CL-025-OCI-PREFIX-ISOLATION": _claim(
                "SUPPORT_SCOPED" if t_ok and host_ok and evidence_ok else "FAIL",
                "T raw candidate-visible features stay within the preregistered upper-bound rule under a host-recomputed OCI profile."
                if t_ok and host_ok and evidence_ok
                else "T leakage statistics, raw evidence integrity, or host OCI reconstruction failed.",
            ),
            "CL-025-SECRET-RANDOMIZATION-CLOSURE": _claim(
                "SUPPORT_SCOPED" if random_ok else "FAIL",
                "Three domain commitments, public IDs, mapping, order, padding, and private-state/reveal equality recompute under the named local algorithm profile."
                if random_ok
                else "At least one commitment, public-ID, mapping, order, padding, or private-state relation failed.",
            ),
            "CL-025-HOST-OBSERVED-LAUNCH": _claim(
                "SUPPORT_SCOPED" if host_ok else "FAIL",
                "Raw pre/post Docker inspect bytes independently reconstruct the frozen D1/T launch boundary."
                if host_ok
                else "Raw Docker inspect reconstruction or D1/T isolation profile failed.",
            ),
            "CL-025-FULL-BLIND-COMPARISON-QUALIFICATION": _claim(
                "NOT_TESTED",
                "Wave 025 tests only the static pre-lawful-response prefix; it does not run or rank A1-A5 treatments.",
            ),
        }
        result = {
            "schema": EVALUATION_SCHEMA,
            "evaluator_profile": "WAVE025_PURE_PYTHON_INDEPENDENT_EVALUATOR_V1",
            "batch_path": str(batch_root.resolve()),
            "batch_id": data.precommit.get("batch_id"),
            "mode": data.precommit.get("mode"),
            "final_status": final_status,
            "evidence_integrity": {
                "status": "PASS" if evidence_ok else "FAIL",
                "checks": data.evidence_checks,
                "errors": all_check_failures,
                "raw_stdout_out_equality_recomputed": not data.evidence_checks["raw_stdout_out_equality"],
            },
            "detector_sensitivity": {
                "status": "PASS" if controls_ok else "DETECTOR_INADEQUATE",
                "positive_controls": controls,
            },
            "oci_prefix_isolation": {
                "status": "PASS" if t_ok and host_ok and evidence_ok else "FAIL",
                "t_classifiers": t_result,
            },
            "secret_randomization_closure": {
                "status": "PASS" if random_ok else "FAIL",
                "algorithm_profile": {
                    "assignment": ASSIGNMENT_ALGORITHM,
                    "public_id": PUBLIC_ID_ALGORITHM,
                    "padding": PADDING_ALGORITHM,
                },
                "failures": {
                    key: data.evidence_checks[key]
                    for key in ("commitments", "public_ids", "mapping_and_private_state")
                },
            },
            "host_observed_launch": {
                "status": "PASS" if host_ok else "FAIL",
                "raw_inspect_recomputed": True,
                "slot_failures": {key: value for key, value in data.host_failures.items() if value},
                "null_final_repo_digest_rule_checked": True,
            },
            "association_audits": {
                "execution_order": _order_association(data.mapping, data.precommit_raw),
                "host_only_deterministic": _host_only_deterministic_audit(data),
                "host_only_fields_excluded_from_classifier": list(FEATURE_SPEC["forbidden_predictors"]),
            },
            "claims": claims,
            "contract_ambiguities": CONTRACT_AMBIGUITIES,
            "formal_admission_blocked_by_ambiguity": bool(blocking_ambiguities),
            "external_anchor": anchor_verification,
            "full_blind_comparison_qualification": "NOT_TESTED",
            "non_claims": {
                "dynamic_lawful_divergence": "NOT_TESTED",
                "cross_run_provider_or_human_memory": "NOT_TESTED",
                "evaluator_truth_validity": "NOT_TESTED",
                "a1_a5_native_treatment_qualification": "NOT_RUN",
                "actual_comparative_runs": 0,
            },
        }
    except (EvaluationError, OSError, KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        errors.append(str(exc))
        result = {
            "schema": EVALUATION_SCHEMA,
            "evaluator_profile": "WAVE025_PURE_PYTHON_INDEPENDENT_EVALUATOR_V1",
            "batch_path": str(batch_root.resolve()),
            "final_status": "NOT_QUALIFIED",
            "evidence_integrity": {"status": "FAIL", "errors": errors},
            "detector_sensitivity": {"status": "NOT_EVALUATED"},
            "oci_prefix_isolation": {"status": "NOT_EVALUATED"},
            "secret_randomization_closure": {"status": "NOT_EVALUATED"},
            "host_observed_launch": {"status": "NOT_EVALUATED"},
            "claims": {
                "CL-025-LEAK-DETECTOR-SENSITIVITY": _claim("UNKNOWN", "Evidence package rejected before this claim could be evaluated."),
                "CL-025-OCI-PREFIX-ISOLATION": _claim("UNKNOWN", "Evidence package rejected before this claim could be evaluated."),
                "CL-025-SECRET-RANDOMIZATION-CLOSURE": _claim("UNKNOWN", "Evidence package rejected before this claim could be evaluated."),
                "CL-025-HOST-OBSERVED-LAUNCH": _claim("UNKNOWN", "Evidence package rejected before this claim could be evaluated."),
                "CL-025-FULL-BLIND-COMPARISON-QUALIFICATION": _claim("NOT_TESTED", "Outside Wave 025 static-prefix scope."),
            },
            "contract_ambiguities": CONTRACT_AMBIGUITIES,
            "formal_admission_blocked_by_ambiguity": True,
            "full_blind_comparison_qualification": "NOT_TESTED",
            "non_claims": {
                "dynamic_lawful_divergence": "NOT_TESTED",
                "cross_run_provider_or_human_memory": "NOT_TESTED",
                "evaluator_truth_validity": "NOT_TESTED",
                "a1_a5_native_treatment_qualification": "NOT_RUN",
                "actual_comparative_runs": 0,
            },
        }
    forbidden = _forbidden_output_keys(result)
    require(not forbidden, f"evaluator generated prohibited ranking fields: {forbidden}")
    return result


def write_evaluation_exclusive(batch_root: pathlib.Path, result: Mapping[str, Any]) -> pathlib.Path:
    output = batch_root.resolve() / "evaluation.json"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(output, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(canonical_json_bytes(result))
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            output.unlink()
        except OSError:
            pass
        raise
    return output


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_path", type=pathlib.Path)
    args = parser.parse_args(argv)
    result = evaluate_batch(args.batch_path)
    if not args.batch_path.is_dir():
        print(canonical_json_bytes(result).decode("utf-8"), end="")
        return 1
    try:
        write_evaluation_exclusive(args.batch_path, result)
    except FileExistsError:
        print("evaluation.json already exists; refusing to overwrite", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"cannot create evaluation.json: {exc}", file=sys.stderr)
        return 2
    print(canonical_json_bytes(result).decode("utf-8"), end="")
    return 0 if result["final_status"] in {"PREFIX_QUALIFIED_SCOPED", "STRUCTURAL_PREFIX_ONLY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
