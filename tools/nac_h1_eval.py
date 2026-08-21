#!/usr/bin/env python3
"""Validate and evaluate frozen E-H1′ precomputed-embedding inputs.

This tool deliberately does not call embedding models, train mappings, choose
anchors, or promote mechanism claims. It verifies a frozen manifest and computes
Recall@100 from already materialized vectors. A successful invocation proves
only that the declared input and metric contract was executable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Sequence, Set, Tuple

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - reported by the CLI
    Draft202012Validator = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "research" / "contracts" / "nac-h1-embedding-manifest.schema.json"

BUDGET_CEILING_FIELDS = {
    "corpus_items": "max_corpus_items",
    "encoder_calls": "max_encoder_calls",
    "training_compute_seconds": "max_training_compute_seconds",
    "training_seed_count": "max_training_seed_count",
    "onboarding_compute_seconds": "max_onboarding_compute_seconds",
    "query_encoding_compute_seconds": "max_query_encoding_compute_seconds",
    "candidate_encoding_compute_seconds": "max_candidate_encoding_compute_seconds",
    "retrieval_compute_seconds": "max_retrieval_compute_seconds",
    "storage_bytes": "max_storage_bytes",
    "transfer_bytes": "max_transfer_bytes",
    "adapter_count": "max_adapter_count",
    "mapping_count": "max_mapping_count",
    "version_recompute_compute_seconds": "max_version_recompute_compute_seconds",
    "dual_write_seconds": "max_dual_write_seconds",
    "downtime_seconds": "max_downtime_seconds",
}

ARM_INFORMATION_CONDITIONS = {
    "nac_relative": "public_anchor_texts",
    "vec2vec": "unpaired_corpora",
    "procrustes": "paired_correspondences",
    "shared_reference": "shared_reference_encoder",
    "stable_schema_sparse": "lexical_or_sparse_corpus",
}

INFORMATION_COUNT_FIELDS = {
    "anchor_text_count",
    "paired_correspondence_count",
    "unpaired_source_embedding_count",
    "unpaired_target_embedding_count",
    "shared_encoder_call_count",
    "lexical_corpus_item_count",
}


class ManifestError(RuntimeError):
    """A frozen-input or evaluation-contract violation."""


def reject_duplicate_json_keys(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
    value: Dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            path.read_text(encoding="utf-8-sig"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ManifestError(f"cannot read JSON {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ManifestError(f"cannot read artifact {path}: {exc}") from exc
    return digest.hexdigest()


def artifact_path(manifest_path: Path, artifact: Mapping[str, Any]) -> Path:
    path = Path(str(artifact["path"]))
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def validate_artifact(
    manifest_path: Path,
    artifact: Mapping[str, Any],
    verified: Dict[Tuple[Path, str], Path],
) -> Path:
    path = artifact_path(manifest_path, artifact)
    expected = str(artifact["sha256"])
    key = (path, expected)
    if key in verified:
        return verified[key]
    if not path.is_file():
        raise ManifestError(f"artifact is not a file: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ManifestError(
            f"artifact SHA-256 mismatch for {path}: expected {expected}, got {actual}"
        )
    verified[key] = path
    return path


def schema_errors(manifest: Mapping[str, Any]) -> List[str]:
    if Draft202012Validator is None:
        raise ManifestError("jsonschema is required to validate the E-H1′ manifest")
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    errors: List[str] = []
    for error in sorted(validator.iter_errors(manifest), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.path) or "<root>"
        errors.append(f"{location}: {error.message}")
    return errors


def evaluative_readiness_errors(
    manifest: Mapping[str, Any],
    manifest_path: Path,
) -> List[str]:
    """Return explicit E-H1′ readiness failures before deep schema evaluation.

    E0 packets may be internally well-formed evidence packages while still being
    non-evaluative. This gate names the missing experimental conditions instead
    of allowing such a packet to fail later as an ambiguous metric error.
    """
    errors: List[str] = []
    if manifest.get("input_evidence_class") != "EVALUATIVE_EH1":
        errors.append(
            "EH1_NOT_EVALUATIVE_CLASS: input_evidence_class must be EVALUATIVE_EH1"
        )

    dataset = manifest.get("dataset")
    if not isinstance(dataset, dict) or dataset.get("label_status") != "GOLD":
        errors.append(
            "EH1_GOLD_LABELS_REQUIRED: independently frozen gold labels are required"
        )

    candidate_count: int | None = None
    if isinstance(dataset, dict):
        labels_artifact = dataset.get("labels")
        if isinstance(labels_artifact, dict) and isinstance(
            labels_artifact.get("path"), str
        ):
            try:
                labels = load_json(artifact_path(manifest_path, labels_artifact))
                if isinstance(labels, dict) and isinstance(
                    labels.get("candidate_ids"), list
                ):
                    candidate_count = len(labels["candidate_ids"])
            except ManifestError:
                candidate_count = None
    if candidate_count is None or candidate_count <= 100:
        rendered_count = "unavailable" if candidate_count is None else str(candidate_count)
        errors.append(
            "EH1_CANDIDATE_POOL_TOO_SMALL: Recall@100 requires a frozen "
            f"candidate pool larger than 100; got {rendered_count}"
        )

    models = manifest.get("models")
    verified_receipts = 0
    if isinstance(models, list):
        for model in models:
            if not isinstance(model, dict) or model.get("receipt_status") != "VERIFIED":
                continue
            receipt = model.get("receipt")
            if (
                isinstance(receipt, dict)
                and isinstance(receipt.get("path"), str)
                and isinstance(receipt.get("sha256"), str)
                and len(receipt["sha256"]) == 64
            ):
                verified_receipts += 1
    if verified_receipts < 5:
        errors.append(
            "EH1_FIVE_MODEL_RECEIPTS_REQUIRED: at least five hash-bound verified "
            f"model receipts are required; got {verified_receipts}"
        )
    return errors


def require_unique(values: Iterable[str], label: str) -> List[str]:
    items = list(values)
    if len(items) != len(set(items)):
        raise ManifestError(f"{label} must be unique")
    return items


def load_labels(path: Path) -> Tuple[List[Dict[str, Any]], List[str]]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise ManifestError("labels artifact must be a JSON object")
    if set(value) != {"queries", "candidate_ids"}:
        raise ManifestError("labels artifact must contain only queries and candidate_ids")
    queries = value["queries"]
    candidates = value["candidate_ids"]
    if not isinstance(queries, list) or not queries:
        raise ManifestError("labels.queries must be a non-empty array")
    if not isinstance(candidates, list):
        raise ManifestError("labels.candidate_ids must be an array")
    candidate_ids = require_unique(
        (str(item) for item in candidates),
        "labels.candidate_ids",
    )
    candidate_set = set(candidate_ids)
    parsed_queries: List[Dict[str, Any]] = []
    query_ids: List[str] = []
    for index, item in enumerate(queries):
        if not isinstance(item, dict) or set(item) != {
            "id",
            "positive_candidate_ids",
            "slices",
        }:
            raise ManifestError(
                f"labels.queries[{index}] must contain only id, positive_candidate_ids, slices"
            )
        query_id = str(item["id"])
        positives = require_unique(
            (str(candidate) for candidate in item["positive_candidate_ids"]),
            f"positive candidates for query {query_id}",
        )
        slices = require_unique(
            (str(slice_id) for slice_id in item["slices"]),
            f"slices for query {query_id}",
        )
        if not positives:
            raise ManifestError(f"query {query_id} has no positive candidates")
        unknown = set(positives) - candidate_set
        if unknown:
            raise ManifestError(
                f"query {query_id} positives are absent from candidate_ids: {sorted(unknown)}"
            )
        query_ids.append(query_id)
        parsed_queries.append(
            {
                "id": query_id,
                "positive_candidate_ids": positives,
                "slices": slices,
            }
        )
    require_unique(query_ids, "labels query ids")
    return parsed_queries, candidate_ids


def validate_split(
    split_path: Path,
    query_ids: Set[str],
) -> None:
    split = load_json(split_path)
    expected_keys = {
        "evaluation_query_ids",
        "anchor_selection_query_ids",
        "alignment_training_query_ids",
    }
    if not isinstance(split, dict) or set(split) != expected_keys:
        raise ManifestError(
            "split manifest must contain only evaluation_query_ids, "
            "anchor_selection_query_ids, and alignment_training_query_ids"
        )
    evaluation = set(
        require_unique(
            (str(item) for item in split["evaluation_query_ids"]),
            "evaluation_query_ids",
        )
    )
    anchors = set(
        require_unique(
            (str(item) for item in split["anchor_selection_query_ids"]),
            "anchor_selection_query_ids",
        )
    )
    alignment = set(
        require_unique(
            (str(item) for item in split["alignment_training_query_ids"]),
            "alignment_training_query_ids",
        )
    )
    if evaluation != query_ids:
        raise ManifestError(
            "labels query ids must exactly match split_manifest.evaluation_query_ids"
        )
    leaked = evaluation & (anchors | alignment)
    if leaked:
        raise ManifestError(
            f"evaluation queries leak into anchor/alignment inputs: {sorted(leaked)}"
        )


def load_vectors(path: Path) -> Dict[str, Tuple[float, ...]]:
    value = load_json(path)
    if not isinstance(value, dict) or set(value) != {"vectors"}:
        raise ManifestError(f"embedding artifact {path} must contain only vectors")
    rows = value["vectors"]
    if not isinstance(rows, list) or not rows:
        raise ManifestError(f"embedding artifact {path} has no vectors")
    vectors: Dict[str, Tuple[float, ...]] = {}
    dimension: int | None = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {"id", "values"}:
            raise ManifestError(
                f"{path}: vectors[{index}] must contain only id and values"
            )
        item_id = str(row["id"])
        if item_id in vectors:
            raise ManifestError(f"{path}: duplicate vector id {item_id}")
        raw_values = row["values"]
        if not isinstance(raw_values, list) or not raw_values:
            raise ManifestError(f"{path}: vector {item_id} has no values")
        try:
            values = tuple(float(item) for item in raw_values)
        except (TypeError, ValueError) as exc:
            raise ManifestError(f"{path}: vector {item_id} is not numeric") from exc
        if any(not math.isfinite(item) for item in values):
            raise ManifestError(f"{path}: vector {item_id} contains a non-finite value")
        if math.sqrt(sum(item * item for item in values)) == 0:
            raise ManifestError(f"{path}: vector {item_id} has zero norm")
        if dimension is None:
            dimension = len(values)
        elif len(values) != dimension:
            raise ManifestError(f"{path}: embedding dimensions are inconsistent")
        vectors[item_id] = values
    return vectors


def validate_model_receipt(path: Path, model: Mapping[str, Any]) -> None:
    receipt = load_json(path)
    expected = {
        "model_id": model["id"],
        "provider": model["provider"],
        "backbone": model["backbone"],
        "version": model["version"],
        "embedding_dimension": model["embedding_dimension"],
    }
    if not isinstance(receipt, dict):
        raise ManifestError(f"model receipt {path} must be a JSON object")
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            raise ManifestError(
                f"model receipt {path} does not bind {key}={expected_value!r}"
            )


def validate_cost(
    evaluation_label: str,
    ceiling_id: str,
    cost: Mapping[str, Any],
    fair_budget: Mapping[str, Any],
) -> None:
    if ceiling_id != fair_budget["ceiling_id"]:
        raise ManifestError(
            f"{evaluation_label} uses budget ceiling {ceiling_id!r}, "
            f"expected {fair_budget['ceiling_id']!r}"
        )
    for cost_field, ceiling_field in BUDGET_CEILING_FIELDS.items():
        if cost[cost_field] > fair_budget[ceiling_field]:
            raise ManifestError(
                f"{evaluation_label} exceeds {ceiling_field}: "
                f"{cost[cost_field]} > {fair_budget[ceiling_field]}"
            )


def validate_information_condition(
    manifest_path: Path,
    arm: str,
    condition: Mapping[str, Any],
    verified: Dict[Tuple[Path, str], Path],
) -> None:
    expected_type = ARM_INFORMATION_CONDITIONS[arm]
    if condition["condition_type"] != expected_type:
        raise ManifestError(
            f"arm {arm} must declare its native information condition "
            f"{expected_type}, got {condition['condition_type']}"
        )
    positive_by_type = {
        "public_anchor_texts": {"anchor_text_count"},
        "paired_correspondences": {"paired_correspondence_count"},
        "unpaired_corpora": {
            "unpaired_source_embedding_count",
            "unpaired_target_embedding_count",
        },
        "shared_reference_encoder": {"shared_encoder_call_count"},
        "lexical_or_sparse_corpus": {"lexical_corpus_item_count"},
    }
    positive_fields = positive_by_type[expected_type]
    for field in INFORMATION_COUNT_FIELDS:
        value = int(condition[field])
        if field in positive_fields and value <= 0:
            raise ManifestError(
                f"arm {arm} information condition requires positive {field}"
            )
        if field not in positive_fields and value != 0:
            raise ManifestError(
                f"arm {arm} native information condition must set {field} to zero"
            )

    receipt_path = validate_artifact(manifest_path, condition["receipt"], verified)
    receipt = load_json(receipt_path)
    if not isinstance(receipt, dict):
        raise ManifestError(f"information-condition receipt {receipt_path} must be an object")
    expected_receipt = {
        "arm_id": arm,
        "condition_type": expected_type,
        **{field: condition[field] for field in sorted(INFORMATION_COUNT_FIELDS)},
    }
    for key, expected_value in expected_receipt.items():
        if receipt.get(key) != expected_value:
            raise ManifestError(
                f"information-condition receipt {receipt_path} "
                f"does not bind {key}={expected_value!r}"
            )


class EvaluationInputs(NamedTuple):
    manifest: Dict[str, Any]
    manifest_sha256: str
    queries: List[Dict[str, Any]]
    candidate_ids: List[str]
    baseline_vectors: Dict[str, Tuple[Dict[str, Tuple[float, ...]], Dict[str, Tuple[float, ...]]]]
    cross_vectors: Dict[
        Tuple[str, str, str],
        Tuple[Dict[str, Tuple[float, ...]], Dict[str, Tuple[float, ...]]],
    ]


def validate_vector_pair(
    label: str,
    query_vectors: Mapping[str, Tuple[float, ...]],
    candidate_vectors: Mapping[str, Tuple[float, ...]],
    query_ids: Set[str],
    candidate_ids: Set[str],
) -> None:
    if set(query_vectors) != query_ids:
        raise ManifestError(f"{label} query vector ids do not match frozen evaluation ids")
    if set(candidate_vectors) != candidate_ids:
        raise ManifestError(f"{label} candidate vector ids do not match frozen candidate ids")
    query_dimension = len(next(iter(query_vectors.values())))
    candidate_dimension = len(next(iter(candidate_vectors.values())))
    if query_dimension != candidate_dimension:
        raise ManifestError(
            f"{label} query/candidate dimensions differ: "
            f"{query_dimension} != {candidate_dimension}"
        )


def load_and_validate_manifest(manifest_path: Path) -> EvaluationInputs:
    raw = load_json(manifest_path)
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be a JSON object")
    errors = evaluative_readiness_errors(raw, manifest_path)
    errors.extend(f"SCHEMA: {error}" for error in schema_errors(raw))
    if errors:
        raise ManifestError(
            "manifest is not valid E-H1′ evaluative input:\n- "
            + "\n- ".join(errors)
        )

    manifest: Dict[str, Any] = raw
    verified: Dict[Tuple[Path, str], Path] = {}
    labels_path = validate_artifact(manifest_path, manifest["dataset"]["labels"], verified)
    split_path = validate_artifact(
        manifest_path,
        manifest["dataset"]["split_manifest"],
        verified,
    )
    queries, candidate_ids = load_labels(labels_path)
    query_ids = {item["id"] for item in queries}
    candidate_id_set = set(candidate_ids)
    k = int(manifest["recall_policy"]["k"])
    if len(candidate_ids) <= k:
        raise ManifestError(
            f"candidate pool must be larger than Recall@{k}; got {len(candidate_ids)}"
        )
    validate_split(split_path, query_ids)

    model_ids = require_unique(
        (str(model["id"]) for model in manifest["models"]),
        "model ids",
    )
    models = {str(model["id"]): model for model in manifest["models"]}
    if len({model["provider"] for model in manifest["models"]}) < 2:
        raise ManifestError("five-model panel must include at least two providers")
    if len({model["backbone"] for model in manifest["models"]}) < 2:
        raise ManifestError("five-model panel must include at least two backbones")
    if len({model["embedding_dimension"] for model in manifest["models"]}) < 2:
        raise ManifestError("five-model panel must include at least two embedding dimensions")
    if len({tuple(model["language_profile"]) for model in manifest["models"]}) < 2:
        raise ManifestError("five-model panel must include differing language profiles")
    for model in manifest["models"]:
        receipt_path = validate_artifact(manifest_path, model["receipt"], verified)
        validate_model_receipt(receipt_path, model)

    slice_ids = require_unique(
        (str(item["id"]) for item in manifest["critical_slices"]),
        "critical slice ids",
    )
    known_slices = {slice_id for query in queries for slice_id in query["slices"]}
    for slice_contract in manifest["critical_slices"]:
        slice_id = str(slice_contract["id"])
        count = sum(slice_id in query["slices"] for query in queries)
        if slice_id not in known_slices or count < slice_contract["minimum_queries"]:
            raise ManifestError(
                f"critical slice {slice_id!r} has {count} queries; "
                f"minimum is {slice_contract['minimum_queries']}"
            )

    fair_budget = manifest["fair_budget"]
    baseline_by_model: Dict[str, Mapping[str, Any]] = {}
    for baseline in manifest["same_model_baselines"]:
        model_id = str(baseline["model_id"])
        if model_id not in models:
            raise ManifestError(f"same-model baseline references unknown model {model_id}")
        if model_id in baseline_by_model:
            raise ManifestError(f"duplicate same-model baseline for {model_id}")
        baseline_by_model[model_id] = baseline
        validate_cost(
            f"same-model baseline {model_id}",
            str(baseline["budget_ceiling_id"]),
            baseline["cost"],
            fair_budget,
        )
    if set(baseline_by_model) != set(model_ids):
        missing = sorted(set(model_ids) - set(baseline_by_model))
        extra = sorted(set(baseline_by_model) - set(model_ids))
        raise ManifestError(
            f"same-model baseline coverage must exactly match models; "
            f"missing={missing}, extra={extra}"
        )

    required_pairs = {
        (source, target)
        for source in model_ids
        for target in model_ids
        if source != target
    }
    required_arms = set(manifest["required_cross_model_arms"])
    evaluations: Dict[Tuple[str, str, str], Mapping[str, Any]] = {}
    for evaluation in manifest["cross_model_evaluations"]:
        arm = str(evaluation["arm_id"])
        source = str(evaluation["source_model_id"])
        target = str(evaluation["target_model_id"])
        key = (arm, source, target)
        if arm not in required_arms:
            raise ManifestError(f"cross-model evaluation uses undeclared arm {arm}")
        if source not in models or target not in models:
            raise ManifestError(f"{key} references an unknown model")
        if source == target:
            raise ManifestError(f"{key} is not a cross-model ordered pair")
        if key in evaluations:
            raise ManifestError(f"duplicate cross-model evaluation {key}")
        evaluations[key] = evaluation
        validate_information_condition(
            manifest_path,
            arm,
            evaluation["information_condition"],
            verified,
        )
        validate_cost(
            f"cross-model evaluation {key}",
            str(evaluation["budget_ceiling_id"]),
            evaluation["cost"],
            fair_budget,
        )
    for arm in required_arms:
        actual_pairs = {
            (source, target)
            for candidate_arm, source, target in evaluations
            if candidate_arm == arm
        }
        if actual_pairs != required_pairs:
            missing = sorted(required_pairs - actual_pairs)
            extra = sorted(actual_pairs - required_pairs)
            raise ManifestError(
                f"arm {arm} must cover every ordered model pair; "
                f"missing={missing}, extra={extra}"
            )

    vector_cache: Dict[Tuple[Path, str], Dict[str, Tuple[float, ...]]] = {}

    def vectors_for(artifact: Mapping[str, Any]) -> Dict[str, Tuple[float, ...]]:
        path = validate_artifact(manifest_path, artifact, verified)
        key = (path, str(artifact["sha256"]))
        if key not in vector_cache:
            vector_cache[key] = load_vectors(path)
        return vector_cache[key]

    baseline_vectors: Dict[
        str,
        Tuple[Dict[str, Tuple[float, ...]], Dict[str, Tuple[float, ...]]],
    ] = {}
    for model_id, baseline in baseline_by_model.items():
        query_vectors = vectors_for(baseline["inputs"]["query_embeddings"])
        candidate_vectors = vectors_for(baseline["inputs"]["candidate_embeddings"])
        validate_vector_pair(
            f"same-model baseline {model_id}",
            query_vectors,
            candidate_vectors,
            query_ids,
            candidate_id_set,
        )
        expected_dimension = int(models[model_id]["embedding_dimension"])
        if len(next(iter(query_vectors.values()))) != expected_dimension:
            raise ManifestError(
                f"same-model baseline {model_id} dimension does not match its model receipt"
            )
        baseline_vectors[model_id] = (query_vectors, candidate_vectors)

    cross_vectors: Dict[
        Tuple[str, str, str],
        Tuple[Dict[str, Tuple[float, ...]], Dict[str, Tuple[float, ...]]],
    ] = {}
    for key, evaluation in evaluations.items():
        query_vectors = vectors_for(evaluation["inputs"]["query_embeddings"])
        candidate_vectors = vectors_for(evaluation["inputs"]["candidate_embeddings"])
        validate_vector_pair(
            f"cross-model evaluation {key}",
            query_vectors,
            candidate_vectors,
            query_ids,
            candidate_id_set,
        )
        cross_vectors[key] = (query_vectors, candidate_vectors)

    return EvaluationInputs(
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        queries=queries,
        candidate_ids=candidate_ids,
        baseline_vectors=baseline_vectors,
        cross_vectors=cross_vectors,
    )


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(item * item for item in left))
    right_norm = math.sqrt(sum(item * item for item in right))
    return numerator / (left_norm * right_norm)


def recall_at_k(
    queries: Sequence[Mapping[str, Any]],
    query_vectors: Mapping[str, Sequence[float]],
    candidate_vectors: Mapping[str, Sequence[float]],
    k: int,
    slice_id: str | None = None,
) -> float:
    selected = [
        query
        for query in queries
        if slice_id is None or slice_id in query["slices"]
    ]
    if not selected:
        raise ManifestError(f"cannot compute Recall@{k} for empty slice {slice_id!r}")
    recalls: List[float] = []
    for query in selected:
        query_id = str(query["id"])
        ranked = sorted(
            (
                (cosine(query_vectors[query_id], vector), candidate_id)
                for candidate_id, vector in candidate_vectors.items()
            ),
            key=lambda item: (-item[0], item[1]),
        )
        retrieved = {candidate_id for _, candidate_id in ranked[:k]}
        positives = set(query["positive_candidate_ids"])
        recalls.append(len(retrieved & positives) / len(positives))
    return sum(recalls) / len(recalls)


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def evaluate(inputs: EvaluationInputs) -> Dict[str, Any]:
    manifest = inputs.manifest
    evaluation_contracts = {
        (
            str(item["arm_id"]),
            str(item["source_model_id"]),
            str(item["target_model_id"]),
        ): item
        for item in manifest["cross_model_evaluations"]
    }
    k = int(manifest["recall_policy"]["k"])
    threshold = float(manifest["recall_policy"]["threshold_fraction"])
    slices: List[str | None] = [None] + [
        str(item["id"]) for item in manifest["critical_slices"]
    ]

    baselines: Dict[str, Dict[str, float]] = {}
    for model_id, (query_vectors, candidate_vectors) in sorted(
        inputs.baseline_vectors.items()
    ):
        baselines[model_id] = {
            "overall" if slice_id is None else slice_id: recall_at_k(
                inputs.queries,
                query_vectors,
                candidate_vectors,
                k,
                slice_id,
            )
            for slice_id in slices
        }

    results: List[Dict[str, Any]] = []
    all_gates_pass = True
    for (arm, source, target), (query_vectors, candidate_vectors) in sorted(
        inputs.cross_vectors.items()
    ):
        slice_results: Dict[str, Any] = {}
        for slice_id in slices:
            slice_key = "overall" if slice_id is None else slice_id
            cross_recall = recall_at_k(
                inputs.queries,
                query_vectors,
                candidate_vectors,
                k,
                slice_id,
            )
            source_recall = baselines[source][slice_key]
            target_recall = baselines[target][slice_key]
            source_ratio = safe_ratio(cross_recall, source_recall)
            target_ratio = safe_ratio(cross_recall, target_recall)
            symmetric_denominator = math.sqrt(source_recall * target_recall)
            symmetric_ratio = safe_ratio(cross_recall, symmetric_denominator)
            ratios = [source_ratio, target_ratio, symmetric_ratio]
            gate_pass = all(ratio is not None and ratio >= threshold for ratio in ratios)
            all_gates_pass = all_gates_pass and gate_pass
            slice_results[slice_key] = {
                f"recall_at_{k}": cross_recall,
                "source_same_model_recall": source_recall,
                "target_same_model_recall": target_recall,
                "ratio_R_AB_over_R_AA": source_ratio,
                "ratio_R_AB_over_R_BB": target_ratio,
                "ratio_R_AB_over_sqrt_R_AA_R_BB": symmetric_ratio,
                "threshold_fraction": threshold,
                "metric_gate_passed": gate_pass,
            }
        results.append(
            {
                "arm_id": arm,
                "source_model_id": source,
                "target_model_id": target,
                "information_condition": evaluation_contracts[
                    (arm, source, target)
                ]["information_condition"],
                "cost": evaluation_contracts[(arm, source, target)]["cost"],
                "slices": slice_results,
            }
        )

    return {
        "schema_version": "1.0",
        "kind": "NACH1MetricReport",
        "experiment_id": manifest["experiment_id"],
        "input_evidence_class": manifest["input_evidence_class"],
        "hypothesis_id": manifest["hypothesis_id"],
        "tested_claim_id": manifest["tested_claim_id"],
        "input_manifest_sha256": inputs.manifest_sha256,
        "input_contract_valid": True,
        "fairness_policy": manifest["fairness_policy"],
        "fair_budget": manifest["fair_budget"],
        "ordered_pair_and_slice_metric_gate_passed": all_gates_pass,
        "same_model_baselines": baselines,
        "cross_model_results": results,
        "interpretation_status": "REQUIRES_RESEARCH_REVIEW",
        "claim_boundary": "TOOL_VALIDATION_IS_NOT_MECHANISM_VALIDATION",
        "cannot_support": [
            "NAC or MC-NAC-ANCHOR is validated merely because this tool ran successfully",
            "ground-truth quality beyond the frozen provenance declarations",
            "real-world frequency, deployment value, authorization, Effect, Adoption, or Acceptance",
            "any claim outside E-H1-PRIME and MC-NAC-ANCHOR",
        ],
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or evaluate an E-H1′ manifest containing only precomputed embeddings."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "evaluate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("manifest", type=Path)
        if command == "evaluate":
            subparser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        inputs = load_and_validate_manifest(args.manifest.resolve())
        if args.command == "validate":
            print(
                json.dumps(
                    {
                        "valid": True,
                        "experiment_id": inputs.manifest["experiment_id"],
                        "input_manifest_sha256": inputs.manifest_sha256,
                        "model_count": len(inputs.manifest["models"]),
                        "required_arm_count": len(
                            inputs.manifest["required_cross_model_arms"]
                        ),
                        "cross_model_evaluation_count": len(inputs.cross_vectors),
                        "claim_boundary": (
                            "TOOL_VALIDATION_IS_NOT_MECHANISM_VALIDATION"
                        ),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 0

        report = evaluate(inputs)
        rendered = json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except ManifestError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
