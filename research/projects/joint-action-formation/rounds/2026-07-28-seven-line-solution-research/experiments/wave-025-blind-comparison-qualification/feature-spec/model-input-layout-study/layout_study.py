#!/usr/bin/env python3
"""Private-role/outcome-blind, public-treatment-aware layout study.

This script measures structural shape only.  It deliberately reads the accepted
routing candidate and the twelve public collector feature receipts, but never a
private registry, reveal, private role assignment, or outcome assignment.  It
does read public-plan challenge treatments for stratification.  It does not fit
a classifier and cannot establish detection power.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional


HERE = Path(__file__).resolve().parent
FEATURE_SPEC = HERE.parent
WAVE = FEATURE_SPEC.parent
ROUTING_PATH = FEATURE_SPEC / "FEATURE-ROUTING-V2S.candidate.json"
ROUTING_SCHEMA_PATH = FEATURE_SPEC / "FEATURE-ROUTING-V2S.candidate.schema.json"
RECEIPT_SCHEMA_PATH = FEATURE_SPEC / "COLLECTOR-RECEIPT-V1.candidate.schema.json"
PRIMITIVES_PATH = FEATURE_SPEC / "V2S-PRIMITIVES.candidate.json"
SMOKE_SLOTS = WAVE / "runs" / "smoke-v13-20260801-f" / "slots"
PUBLIC_PLAN_PATH = WAVE / "runs" / "smoke-v13-20260801-f" / "public-plan.json"
CLOSED_PATH = WAVE / "runs" / "smoke-v13-20260801-f" / "closed.json"
EXPECTED_PUBLIC_PLAN_SHA256 = "09a8fc8a57906bc3d4182af7f3b1f08cccf5c36b2a6c6a07c2ccf1a9033acf72"
EXPECTED_CLOSED_SHA256 = "26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e"

sys.path.insert(0, str(FEATURE_SPEC))
import routing_v2s_coverage as routing_lib  # noqa: E402


FAMILIES = (
    "F01_PUBLIC_INPUT_BYTES",
    "F02_ARGV_ENV_CWD",
    "F03_HOSTNAME_IDENTITY",
    "F04_DIRECTORY_AND_SHARED_STATE",
    "F05_PROCESS_NAMESPACE_FD",
    "F06_TIMING_AND_ERRORS",
    "F07_VISIBLE_CANARY",
)
HASH_WIDTHS = (4096, 8192, 16384)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")

DELETION_REQUIREMENT_SCOPES = {
    "split_precommitted_before_receipts": "W025_MODEL_LAYOUT_SPLIT_PRECOMMIT",
    "independent_probe_not_used_for_dictionary": "W025_MODEL_LAYOUT_PROBE_DICTIONARY_ISOLATION",
    "c01_phase_boundary_closed": "W025_C01_PHASE_BOUNDARY",
    "resource_ceiling_bound_and_passed": "W025_MODEL_LAYOUT_RESOURCE_CEILING",
    "structural_drift_zero": "W025_MODEL_LAYOUT_STRUCTURAL_DRIFT",
    "closed_domain_or_validated_novelty_alternative": "W025_CATEGORY_DOMAIN_OR_NOVELTY_CLOSURE",
    "frozen_removal_fixture_set_passed_on_independent_probe": "W025_SIGNED_HASH_REMOVAL_FIXTURES",
    "exact_or_other_lost_pair_count_zero": "W025_EXACT_OTHER_LOST_PAIR_AUDIT",
}


def frame32(value: bytes) -> bytes:
    return len(value).to_bytes(4, "big") + value


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def typed_value_bytes(value: Any) -> bytes:
    """The bounded JSON subset needed by the twelve already-admitted receipts."""
    if value is _MISSING:
        return b"\x07"
    if value is None:
        return b"\x00"
    if value is False:
        return b"\x01"
    if value is True:
        return b"\x02"
    if isinstance(value, int):
        return b"\x03" + frame32(str(value).encode("ascii")) + frame32(b"1")
    if isinstance(value, float):
        rational = Fraction(str(value))
        return (
            b"\x03"
            + frame32(str(rational.numerator).encode("ascii"))
            + frame32(str(rational.denominator).encode("ascii"))
        )
    if isinstance(value, str):
        return b"\x04" + frame32(value.encode("utf-8"))
    if isinstance(value, list):
        return b"\x05" + len(value).to_bytes(4, "big") + b"".join(
            frame32(typed_value_bytes(item)) for item in value
        )
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: item[0].encode("utf-8"))
        return b"\x06" + len(items).to_bytes(4, "big") + b"".join(
            frame32(key.encode("utf-8")) + frame32(typed_value_bytes(item))
            for key, item in items
        )
    raise TypeError(type(value))


_MISSING = object()


def channel_identity(channel: str, expected_channel: str = "NONE") -> bytes:
    return (
        frame32(b"WAVE025_CHANNEL_V2S")
        + frame32(channel.encode("ascii"))
        + frame32(expected_channel.encode("ascii"))
    )


def category_row_preimage(
    family: str,
    context: bytes,
    channel: str,
    value: Any,
    expected_channel: str = "NONE",
) -> bytes:
    atom = typed_value_bytes(value)
    value_digest = hashlib.sha256(
        frame32(b"WAVE025_TYPED_VALUE_V2S") + frame32(atom)
    ).digest()
    return (
        frame32(b"WAVE025_CATEGORY_ROW_V2S")
        + frame32(family.encode("utf-8"))
        + frame32(context)
        + frame32(channel_identity(channel, expected_channel))
        + frame32(value_digest)
    )


def category_bucket(row_preimage: bytes, width: int) -> tuple[int, int]:
    digest = hashlib.sha256(
        frame32(b"WAVE025_MODEL_CATEGORY_HASH_V2S") + frame32(row_preimage)
    ).digest()
    return int.from_bytes(digest[:4], "big") % width, 1 if digest[4] & 1 == 0 else -1


def ngram_buckets(family: str, context: bytes, value: str) -> Counter[int]:
    raw = value.encode("utf-8")
    spans = [raw] if len(raw) <= 4096 else [raw[:2048], raw[-2048:]]
    channel = channel_identity("LEXICAL_NGRAM", "NONE")
    result: Counter[int] = Counter()
    for span in spans:
        for n in (1, 2, 3, 4):
            for offset in range(max(0, len(span) - n + 1)):
                gram = span[offset : offset + n]
                preimage = (
                    frame32(b"WAVE025_UTF8_NGRAM_V2S")
                    + frame32(family.encode("utf-8"))
                    + frame32(context)
                    + frame32(channel)
                    + frame32(bytes([n]))
                    + frame32(gram)
                )
                bucket = int.from_bytes(hashlib.sha256(preimage).digest()[:4], "big") % 4096
                result[bucket] += 1
    return result


def category_domain(row: Mapping[str, Any], channel: str) -> str:
    """Conservative domain status from primitive/routing grammar, never a name heuristic."""
    if channel == "MISSING":
        return "CLOSED_RESERVED_MISSING2"
    if channel == "BRANCH" or row["event_kind"] == "UNION_BRANCH":
        return "CLOSED_ROUTING_VARIANTS"
    atom = row["input_atom"]
    if atom == "JSON_BOOL":
        return "CLOSED_JSON_BOOL"
    if atom == "JSON_NULL":
        return "CLOSED_JSON_NULL"
    if atom == "SHA256_HEX":
        return "NONENUMERABLE_SHA256_GRAMMAR"
    # UTF8_STRING may be a schema enum, pattern, or unconstrained text.  Closed
    # records may also contain a mixture.  This study does not pretend to have
    # proved those per-route schema domains.
    return "UNKNOWN_NEEDS_SCHEMA_DOMAIN_PROOF"


def domain_is_open(status: str) -> bool:
    return status.startswith("NONENUMERABLE_") or status.startswith("OPEN_")


def get_event_value(root: Any, path: str, event_kind: str, active_variant: Any) -> Any:
    if event_kind == "ABSENCE":
        return _MISSING
    if event_kind == "UNION_BRANCH":
        return active_variant
    return routing_lib.get_pointer(root, path)


def add_event(
    *,
    routing: Mapping[str, Any],
    row: Mapping[str, Any],
    path: str,
    value: Any,
    captures: Mapping[str, str],
    numeric: set[tuple[str, ...]],
    categories: Counter[bytes],
    category_templates: dict[bytes, tuple[str, ...]],
    category_domains: dict[bytes, str],
    direct_ngrams: Counter[tuple[str, int]],
    route_only: set[tuple[str, ...]],
) -> int:
    opportunities = 0
    registry = routing["channel_stat_registry"]
    for spec in row["channels"]:
        channel = spec["channel"]
        expected = spec.get("expected_channel", "NONE")
        context = routing_lib.resolve_context(row, captures, spec["context"])
        if channel == "MISSING":
            stats = [("NONE", expected, expected_stat) for expected_stat in spec["expected_stats"]]
        else:
            stats = [(stat, "NONE", "NONE") for stat in registry[channel]["stats"]]
        opportunities += len(stats)
        kind = registry[channel]["kind"]
        for stat, expected_channel, expected_stat in stats:
            route_only.add((row["family"], row["id"], channel, stat, expected_channel, expected_stat))
            if kind == "NUMERIC":
                numeric.add(
                    (
                        row["family"],
                        context.hex(),
                        channel,
                        stat,
                        expected_channel,
                        expected_stat,
                    )
                )
            elif kind in {"CATEGORICAL", "CATEGORICAL_MISSING"}:
                category_value = _MISSING if channel == "MISSING" else value
                preimage = category_row_preimage(
                    row["family"], context, channel, category_value, expected
                )
                categories[preimage] += 1
                category_templates[preimage] = (
                    row["family"], context.hex(), channel, expected
                )
                category_domains[preimage] = category_domain(row, channel)
            elif kind == "NGRAM_DIRECT":
                if not isinstance(value, str):
                    raise TypeError(f"ngram route {row['id']} received {type(value)!r}")
                direct_ngrams.update(
                    (row["family"], bucket)
                    for bucket in ngram_buckets(row["family"], context, value)
                )
            else:
                raise ValueError(kind)
    return opportunities


def receipt_shape(
    routing: Mapping[str, Any], receipt_schema: Mapping[str, Any], path: Path
) -> dict[str, Any]:
    receipt = load_json(path)
    classified = routing_lib.classify_receipt(routing, receipt_schema, receipt)
    if classified["status"] != "ZERO_UNCLASSIFIED":
        raise ValueError(f"receipt did not route cleanly: {path}")
    row_by_id = {row["id"]: row for row in routing["rows"]}
    numeric: set[tuple[str, ...]] = set()
    categories: Counter[bytes] = Counter()
    category_templates: dict[bytes, tuple[str, ...]] = {}
    category_domains: dict[bytes, str] = {}
    direct_ngrams: Counter[tuple[str, int]] = Counter()
    route_only: set[tuple[str, ...]] = set()
    opportunities = 0
    for item in classified["classified"]:
        row = row_by_id[item["row"]]
        value = routing_lib.get_pointer(receipt, item["path"])
        captures = routing_lib.match_pattern(row["path_pattern"], item["path"]) or {}
        opportunities += add_event(
            routing=routing,
            row=row,
            path=item["path"],
            value=value,
            captures=captures,
            numeric=numeric,
            categories=categories,
            category_templates=category_templates,
            category_domains=category_domains,
            direct_ngrams=direct_ngrams,
            route_only=route_only,
        )
    for item in classified["pseudo_events"]:
        row = row_by_id[item["route_id"]]
        captures = routing_lib.match_pattern(row["path_pattern"], item["path"]) or {}
        value = get_event_value(
            receipt, item["path"], item["event_kind"], item["active_variant"]
        )
        opportunities += add_event(
            routing=routing,
            row=row,
            path=item["path"],
            value=value,
            captures=captures,
            numeric=numeric,
            categories=categories,
            category_templates=category_templates,
            category_domains=category_domains,
            direct_ngrams=direct_ngrams,
            route_only=route_only,
        )
    category_ids = {sha256(preimage) for preimage in categories}
    domain_by_id = {sha256(preimage): status for preimage, status in category_domains.items()}
    template_by_id = {
        sha256(preimage): template for preimage, template in category_templates.items()
    }
    open_ids = {identity for identity, status in domain_by_id.items() if domain_is_open(status)}
    unknown_ids = {
        identity
        for identity, status in domain_by_id.items()
        if status == "UNKNOWN_NEEDS_SCHEMA_DOMAIN_PROOF"
    }
    category_counts = {sha256(preimage): count for preimage, count in categories.items()}
    category_preimages = {sha256(preimage): preimage for preimage in categories}
    receipt_digest = sha256(path.read_bytes())
    return {
        "slot_id": path.parent.name,
        "source_name_sha256": sha256(path.parent.name.encode("utf-8")),
        "receipt_sha256": receipt_digest,
        "scalar_leaf_count": classified["scalar_leaf_count"],
        "pseudo_event_count": classified["pseudo_event_count"],
        "emission_opportunities_before_aggregation": opportunities,
        "numeric_structural_occupied": len(numeric),
        "exact_category_occupied": len(category_ids),
        "grammar_open_category_occupied": len(open_ids),
        "unknown_domain_category_occupied": len(unknown_ids),
        "ngram_direct_buckets_occupied": len(direct_ngrams),
        "static_route_only_occupied": len(route_only),
        "numeric_ids": numeric,
        "category_ids": category_ids,
        "open_ids": open_ids,
        "unknown_ids": unknown_ids,
        "domain_by_id": domain_by_id,
        "template_by_id": template_by_id,
        "category_counts": category_counts,
        "category_preimages": category_preimages,
        "ngram_ids": set(direct_ngrams),
        "route_only_ids": route_only,
    }


def csr_bytes(row_count: int, nnz: int) -> int:
    # Standard CSR layout: float64 data + uint32 indices + uint32 indptr.
    return nnz * 8 + nnz * 4 + (row_count + 1) * 4


def hashed_cells(
    shape: Mapping[str, Any], identities: Iterable[str], width: int
) -> tuple[int, int, int]:
    """Return signed nnz, presence nnz, and exact->bucket collapses."""
    signed: Counter[tuple[str, int]] = Counter()
    presence: set[tuple[str, int]] = set()
    selected = set(identities)
    for identity in selected:
        preimage = shape["category_preimages"][identity]
        family = shape["template_by_id"][identity][0]
        bucket, sign = category_bucket(preimage, width)
        signed[(family, bucket)] += sign * shape["category_counts"][identity]
        presence.add((family, bucket))
    return (
        sum(value != 0 for value in signed.values()),
        len(presence),
        len(selected) - len(presence),
    )


def calibration_frozen_layouts(
    reference: list[dict[str, Any]],
    probe: list[dict[str, Any]],
    ngram_families: set[str],
    width: int,
) -> dict[str, Any]:
    """Apply dictionaries frozen from reference only; never expand from probe."""
    reference_numeric = set().union(*(shape["numeric_ids"] for shape in reference))
    reference_exact = set().union(*(shape["category_ids"] for shape in reference))
    reference_templates = set().union(
        *(set(shape["template_by_id"].values()) for shape in reference)
    )
    ngram_width = len(ngram_families) * 4096
    base_width = len(reference_numeric) + ngram_width
    totals = Counter()
    probe_oov = set()
    probe_numeric_drift = set()
    probe_template_drift = set()
    row_reports = []
    for phase, population in (("reference", reference), ("probe", probe)):
        for shape in population:
            numeric_known = shape["numeric_ids"] & reference_numeric
            numeric_drift = shape["numeric_ids"] - reference_numeric
            exact_known = shape["category_ids"] & reference_exact
            oov = shape["category_ids"] - reference_exact
            other_cells = {
                shape["template_by_id"][identity]
                for identity in oov
                if shape["template_by_id"][identity] in reference_templates
            }
            template_drift = {
                shape["template_by_id"][identity]
                for identity in oov
                if shape["template_by_id"][identity] not in reference_templates
            }
            hash_all_signed, hash_all_presence, hash_all_collapses = hashed_cells(
                shape, shape["category_ids"], width
            )
            oov_signed, oov_presence, oov_collapses = hashed_cells(shape, oov, width)
            base_nnz = len(numeric_known) + len(shape["ngram_ids"])
            row = {
                "phase": phase,
                "receipt_sha256": shape["receipt_sha256"],
                "numeric_structural_drift": len(numeric_drift),
                "category_template_drift": len(template_drift),
                "exact_oov": len(oov),
                "exact_only_nnz": base_nnz + len(exact_known),
                "exact_plus_other_nnz": base_nnz + len(exact_known) + len(other_cells),
                "hash_only_signed_nnz": base_nnz + hash_all_signed,
                "hash_only_presence_nnz": base_nnz + hash_all_presence,
                "hybrid_oov_signed_nnz": base_nnz + len(exact_known) + oov_signed,
                "hybrid_oov_presence_nnz": base_nnz + len(exact_known) + oov_presence,
                "hash_all_exact_to_bucket_collapses": hash_all_collapses,
                "oov_exact_to_bucket_collapses": oov_collapses,
            }
            row_reports.append(row)
            for key, value in row.items():
                if key.endswith("_nnz"):
                    totals[key] += value
            if phase == "probe":
                probe_oov.update(oov)
                probe_numeric_drift.update(numeric_drift)
                probe_template_drift.update(template_drift)
    row_count = len(reference) + len(probe)
    widths = {
        "exact_only": base_width + len(reference_exact),
        "exact_plus_other": base_width + len(reference_exact) + len(reference_templates),
        "hash_only": base_width + len(FAMILIES) * width,
        "hybrid_exact_plus_oov_hash": base_width + len(reference_exact) + len(FAMILIES) * width,
    }
    return {
        "hash_width_per_family": width,
        "dictionary_phase": "REFERENCE_ONLY_BEFORE_PROBE",
        "reference_numeric_columns": len(reference_numeric),
        "reference_exact_columns": len(reference_exact),
        "reference_other_template_columns": len(reference_templates),
        "fixed_reachable_ngram_columns": ngram_width,
        "logical_columns": widths,
        "total_nnz": dict(sorted(totals.items())),
        "csr_float64_u32_bytes": {
            key.removesuffix("_nnz"): csr_bytes(row_count, value)
            for key, value in sorted(totals.items())
        },
        "dense_float64_bytes": {
            key: row_count * value * 8 for key, value in widths.items()
        },
        "probe_application": {
            "exact_oov_columns": len(probe_oov),
            "numeric_structural_drift_columns": len(probe_numeric_drift),
            "category_template_drift_columns": len(probe_template_drift),
            "probe_does_not_expand_dictionary": True,
        },
        "rows": row_reports,
    }


def signed_hash_receipt_diagnostic(
    bundle: Optional[Mapping[str, Any]],
    receipt_bytes_by_id: Optional[Mapping[str, bytes]] = None,
) -> dict[str, Any]:
    """Parse receipt bytes diagnostically; this study cannot authorize deletion."""
    errors = []
    documents = {} if receipt_bytes_by_id is None else dict(receipt_bytes_by_id)
    if not isinstance(bundle, Mapping):
        errors.append("MISSING_EVIDENCE_BUNDLE")
    elif set(bundle) != {"schema", "receipts"}:
        errors.append("BUNDLE_NOT_CLOSED_SCHEMA")
    elif bundle.get("schema") != "wave025-signed-hash-deletion-evidence-bundle-v1":
        errors.append("BUNDLE_SCHEMA_MISMATCH")
    elif not isinstance(bundle.get("receipts"), list):
        errors.append("BUNDLE_RECEIPTS_NOT_LIST")
    else:
        descriptors = bundle["receipts"]
        expected_requirements = set(DELETION_REQUIREMENT_SCOPES)
        seen_requirements = []
        seen_receipt_ids = []
        descriptor_fields = {
            "requirement_id",
            "evidence_receipt_id",
            "evidence_receipt_sha256",
            "scope",
            "status",
        }
        # The bundle descriptor binds the SHA of the external receipt bytes.
        # The receipt cannot contain that digest itself without a self-hash
        # fixed-point problem, so its closed schema deliberately omits it.
        receipt_fields = (
            descriptor_fields - {"evidence_receipt_sha256"}
        ) | {"schema", "subject_sha256"}
        if len(descriptors) != len(expected_requirements):
            errors.append("RECEIPT_COUNT_MISMATCH")
        for index, descriptor in enumerate(descriptors):
            prefix = f"receipt[{index}]"
            if not isinstance(descriptor, Mapping) or set(descriptor) != descriptor_fields:
                errors.append(f"{prefix}:DESCRIPTOR_NOT_CLOSED_SCHEMA")
                continue
            requirement = descriptor["requirement_id"]
            receipt_id = descriptor["evidence_receipt_id"]
            receipt_sha = descriptor["evidence_receipt_sha256"]
            if not isinstance(requirement, str) or not requirement:
                errors.append(f"{prefix}:REQUIREMENT_ID_INVALID")
                continue
            seen_requirements.append(requirement)
            if requirement not in DELETION_REQUIREMENT_SCOPES:
                errors.append(f"{prefix}:UNKNOWN_REQUIREMENT")
                continue
            if descriptor["scope"] != DELETION_REQUIREMENT_SCOPES[requirement]:
                errors.append(f"{prefix}:SCOPE_MISMATCH")
            if not isinstance(descriptor["status"], str) or descriptor["status"] not in {
                "SATISFIED",
                "FAILED",
                "UNKNOWN",
            }:
                errors.append(f"{prefix}:STATUS_INVALID")
            if not isinstance(receipt_id, str) or not receipt_id.strip():
                errors.append(f"{prefix}:EMPTY_RECEIPT_ID")
                continue
            seen_receipt_ids.append(receipt_id)
            if not isinstance(receipt_sha, str) or not SHA256_RE.fullmatch(receipt_sha):
                errors.append(f"{prefix}:RECEIPT_SHA_INVALID")
                continue
            raw = documents.get(receipt_id)
            if raw is None:
                errors.append(f"{prefix}:RECEIPT_BYTES_MISSING")
                continue
            if not isinstance(raw, bytes):
                errors.append(f"{prefix}:RECEIPT_BYTES_NOT_BYTES")
                continue
            if sha256(raw) != receipt_sha:
                errors.append(f"{prefix}:RECEIPT_SHA_MISMATCH")
                continue
            try:
                document = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                errors.append(f"{prefix}:RECEIPT_JSON_INVALID")
                continue
            if not isinstance(document, Mapping) or set(document) != receipt_fields:
                errors.append(f"{prefix}:RECEIPT_NOT_CLOSED_SCHEMA")
                continue
            if document["schema"] != "wave025-signed-hash-deletion-evidence-receipt-v1":
                errors.append(f"{prefix}:RECEIPT_SCHEMA_MISMATCH")
            for field in descriptor_fields:
                if field == "evidence_receipt_sha256":
                    continue
                if document[field] != descriptor[field]:
                    errors.append(f"{prefix}:RECEIPT_DESCRIPTOR_MISMATCH:{field}")
            subject_sha = document["subject_sha256"]
            if not isinstance(subject_sha, str) or not SHA256_RE.fullmatch(subject_sha):
                errors.append(f"{prefix}:SUBJECT_SHA_INVALID")
        if len(seen_requirements) != len(set(seen_requirements)):
            errors.append("DUPLICATE_REQUIREMENT_ID")
        if set(seen_requirements) != expected_requirements:
            errors.append("REQUIREMENT_SET_MISMATCH")
        if len(seen_receipt_ids) != len(set(seen_receipt_ids)):
            errors.append("DUPLICATE_EVIDENCE_RECEIPT_ID")
        if set(documents) != set(seen_receipt_ids):
            errors.append("UNEXPECTED_OR_MISSING_RECEIPT_DOCUMENT")
        if not errors and any(item["status"] != "SATISFIED" for item in descriptors):
            errors.append("ONE_OR_MORE_REQUIREMENTS_NOT_SATISFIED")
    local_bundle_well_formed = not errors
    return {
        "schema": "wave025-signed-hash-deletion-diagnostic-result-v2",
        "required_receipt_scopes": dict(sorted(DELETION_REQUIREMENT_SCOPES.items())),
        "study_issues_receipts": False,
        "study_can_authorize_deletion": False,
        "local_bundle_well_formed": local_bundle_well_formed,
        "issuer_authority_verified": False,
        "subject_preimage_authority_verified": False,
        "requirement_specific_proof_verified": False,
        "authorization_boundary": "Receipt parsing here is diagnostic only. Any hash/family deletion requires an external controller or explicit user decision that binds trusted issuer authority, the exact frozen subject preimage, and requirement-specific proof. No local bundle can grant that authority to this study.",
        "validation_errors": errors,
        "decision": (
            "EXTERNAL_AUTHORITY_REQUIRED"
            if local_bundle_well_formed
            else "UNKNOWN_DO_NOT_DELETE"
        ),
    }


def quantile_type7(values: Iterable[Fraction], p: Fraction) -> Fraction:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("empty quantile")
    if len(ordered) == 1:
        return ordered[0]
    h = Fraction(len(ordered) - 1) * p
    lower = h.numerator // h.denominator
    fraction = h - lower
    return ordered[lower] + fraction * (ordered[lower + 1] - ordered[lower])


def fixture_study() -> list[dict[str, Any]]:
    family = FAMILIES[1]
    context = frame32(b"WAVE025_CONTEXT_V2S") + (0).to_bytes(4, "big")
    channel = "EXACT_CATEGORY"

    a = category_row_preimage(family, context, channel, "alpha")
    b = category_row_preimage(family, context, channel, "beta")
    e1 = {
        "id": "E1_EXACT_VALUE_STATIC_ROUTE_COLLAPSE",
        "comparison": "exact sparse one-hot vs static route-only",
        "observed": {
            "exact_identities": 2,
            "static_route_identities": 1,
            "exact_distinguishes": sha256(a) != sha256(b),
            "static_route_only_distinguishes": False,
        },
        "removal_counterexample": "Two values on one legal open category route become identical if value identity is removed.",
    }

    seen: dict[tuple[int, int], bytes] = {}
    collision: tuple[bytes, bytes, int] | None = None
    for index in range(1, 100000):
        candidate = category_row_preimage(family, context, channel, f"collision-{index}")
        bucket, sign = category_bucket(candidate, 4096)
        opposite = seen.get((bucket, -sign))
        if opposite is not None:
            collision = (opposite, candidate, bucket)
            break
        seen[(bucket, sign)] = candidate
    if collision is None:
        raise AssertionError("deterministic collision search exhausted")
    left, right, bucket = collision
    left_sign = category_bucket(left, 4096)[1]
    right_sign = category_bucket(right, 4096)[1]
    e2 = {
        "id": "E2_SIGNED_HASH_CANCELLATION",
        "comparison": "continuous signed-sum vs independent presence OR",
        "observed": {
            "bucket_4096": bucket,
            "exact_identities": 2,
            "signed_sum": left_sign + right_sign,
            "presence_or": 1,
            "collision_search_candidates_examined": len(seen) + 1,
        },
        "removal_counterexample": "Deriving presence from signed sum erases a real occupied bucket when opposite signs collide.",
    }

    e3 = {
        "id": "E3_NUMERIC_CENTER_EQUALS_MISSING",
        "comparison": "numeric value alone vs numeric value plus independent missing bit",
        "observed": {
            "present_at_center": {"value": 0.0, "missing": 0.0},
            "absent": {"value": 0.0, "missing": 1.0},
            "value_only_distinguishes": False,
            "value_plus_missing_distinguishes": True,
        },
        "removal_counterexample": "Zero imputation without a missing column collapses absence and an observed value equal to the frozen center.",
    }

    e4 = {
        "id": "E4_FAMILY_NORM_VOLUME_REMOVAL",
        "comparison": "family norm off vs on",
        "observed": {
            "unnormalized_single_axis": [1.0, 10.0],
            "l2_family_normalized_single_axis": [1.0, 1.0],
            "normalization_changes_sparsity": False,
            "normalization_removes_family_volume_on_single_axis": True,
        },
        "removal_counterexample": "If the only signal is total activity in one family/direction, per-row L2 family normalization removes it.",
    }

    calibration = [Fraction(0), Fraction(1), Fraction(2), Fraction(1000)]
    center = quantile_type7(calibration, Fraction(1, 2))
    q1 = quantile_type7(calibration, Fraction(1, 4))
    q3 = quantile_type7(calibration, Fraction(3, 4))
    scale = q3 - q1 or Fraction(1)
    transformed = [(value - center) / scale for value in calibration]
    e5 = {
        "id": "E5_ROBUST_AFFINE_VS_RAW",
        "comparison": "frozen robust center/IQR vs no centering",
        "observed": {
            "calibration": [str(value) for value in calibration],
            "center": str(center),
            "q1": str(q1),
            "q3": str(q3),
            "scale": str(scale),
            "robust_transformed": [str(value) for value in transformed],
            "no_centering": [str(value) for value in calibration],
            "logical_width_equal": True,
            "raw_nonzero_values": sum(value != 0 for value in calibration),
            "robust_nonzero_values": sum(value != 0 for value in transformed),
            "zero_compressed_sparsity_equal": (
                sum(value != 0 for value in calibration)
                == sum(value != 0 for value in transformed)
            ),
            "frozen_nonzero_affine_transform_is_invertible_before_binary64_rounding": True,
        },
        "removal_counterexample": "The frozen exact-rational map is invertible, but it changes zero-compressed nnz (3 raw versus 4 transformed) and may interact with rounding, intercepts, regularization, or thresholds; recomputing on holdout remains forbidden.",
    }
    return [e1, e2, e3, e4, e5]


def static_routing_study(routing: Mapping[str, Any]) -> dict[str, Any]:
    registry = routing["channel_stat_registry"]
    mixed_representatives = set()
    numeric_templates = set()
    category_templates = set()
    ngram_families = set()
    wildcard_classes = Counter()
    domain_pairs = set()
    for row in routing["rows"]:
        star_captures = []
        for segment in row["path_pattern"].split("/"):
            match = routing_lib.CAPTURE_SEGMENT_RE.fullmatch(segment)
            if match and match.group(2) == "*":
                star_captures.append(match.group(1))
        if star_captures:
            ordered = any(
                f"ORDERED:{{{name}}}" in row["context_segments"] for name in star_captures
            )
            if ordered:
                wildcard_classes["ORDERED_CONTEXT_RETAINED"] += 1
            elif row["cardinality"] == "BAG_MULTISET":
                wildcard_classes["BAG_ITEM_CAPTURE_DROPPED"] += 1
            elif row["cardinality"] == "CONTAINER_COUNT":
                wildcard_classes["CONTAINER_ITEM_CAPTURE_DROPPED"] += 1
            else:
                wildcard_classes["OTHER"] += 1
        for _path, captures in routing_lib.expand_finite_pattern(row["path_pattern"]):
            for spec in row["channels"]:
                context = routing_lib.resolve_context(row, captures, spec["context"]).hex()
                channel = spec["channel"]
                kind = registry[channel]["kind"]
                if channel == "MISSING":
                    stats = [
                        ("NONE", spec["expected_channel"], expected_stat)
                        for expected_stat in spec["expected_stats"]
                    ]
                else:
                    stats = [(stat, "NONE", "NONE") for stat in registry[channel]["stats"]]
                for stat, expected, expected_stat in stats:
                    mixed_representatives.add(
                        (row["family"], context, channel, stat, expected, expected_stat)
                    )
                    if kind == "NUMERIC":
                        numeric_templates.add(
                            (row["family"], context, channel, stat, expected, expected_stat)
                        )
                if kind in {"CATEGORICAL", "CATEGORICAL_MISSING"}:
                    expected = spec.get("expected_channel", "NONE")
                    category_templates.add((row["family"], context, channel, expected))
                    domain_pairs.add((row["id"], channel, category_domain(row, channel)))
                elif kind == "NGRAM_DIRECT":
                    ngram_families.add(row["family"])
    matrix = routing_lib.derive_channel_stat_matrix(routing)
    matrix_kinds = Counter(registry[entry["channel"]]["kind"] for entry in matrix)
    domain_counts = Counter(status for _row, _channel, status in domain_pairs)
    primitives_total = len(numeric_templates) + len(category_templates) + len(ngram_families)
    return {
        "routing_rows": len(routing["rows"]),
        "route_channel_stat_matrix_entries": len(matrix),
        "route_channel_stat_matrix_entries_by_kind": dict(sorted(matrix_kinds.items())),
        "routing_mixed_representative_keys_index_zero": len(mixed_representatives),
        "routing_mixed_representative_semantics": "Keeps expected_stat-separated MISSING and route-aware ngram contexts; it is not a predictor column universe.",
        "primitives_emittable_representative_templates_index_zero": {
            "numeric_context_stat": len(numeric_templates),
            "category_context_channel_before_value": len(category_templates),
            "direct_ngram_family": len(ngram_families),
            "total": primitives_total,
            "semantics": "MISSING collapses by primitive category identity without expected_stat; direct ngram collapses to family/bucket. Category values and nonzero ordered indices are not expanded.",
        },
        "wildcard_path_rows": {
            "total": sum(wildcard_classes.values()),
            "classes": dict(sorted(wildcard_classes.items())),
            "domain_statement": "Routing '*' patterns are not fully expanded here. Only ORDERED_CONTEXT_RETAINED preserves index in CTX2; BAG/container captures are intentionally dropped. Receipt schema bounds and u32 context bounds are separate constraints, so this study does not call all 47 unbounded or ordered.",
        },
        "category_route_channel_domain_status": {
            "counts": dict(sorted(domain_counts.items())),
            "method": "Primitive/routing input atom and event grammar only; transform names are not used. UTF8 and closed-record routes remain UNKNOWN until per-route schema domain proof exists.",
        },
        "closed_final_predictor_universe_proven": False,
    }


def verify_f_lineage_documents(
    *,
    plan_raw: bytes,
    closed_raw: bytes,
    shapes: list[dict[str, Any]],
    disk_slot_names: list[str],
    unexpected_disk_entries: list[str],
    expected_plan_sha256: str,
    expected_closed_sha256: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    if sha256(plan_raw) != expected_plan_sha256:
        raise ValueError("public plan differs from exploratory expected SHA")
    if sha256(closed_raw) != expected_closed_sha256:
        raise ValueError("closed manifest differs from exploratory expected SHA")
    plan = json.loads(plan_raw)
    closed = json.loads(closed_raw)
    plan_rows = plan.get("slots")
    closed_rows = closed.get("slots")
    if not isinstance(plan_rows, list) or not isinstance(closed_rows, list):
        raise ValueError("plan/closed slots must be lists")
    # Multiplicity checks precede every dict/set projection, so duplicate ids or
    # exact duplicate rows cannot disappear through last-write or de-duplication.
    if len(plan_rows) != 12 or len(closed_rows) != 12:
        raise ValueError("plan/closed raw slot row count mismatch")
    if any(not isinstance(item, Mapping) for item in plan_rows + closed_rows):
        raise ValueError("plan/closed slot row must be an object")
    if len({canonical_bytes(item) for item in plan_rows}) != len(plan_rows):
        raise ValueError("duplicate public plan row")
    if len({canonical_bytes(item) for item in closed_rows}) != len(closed_rows):
        raise ValueError("duplicate closed row")
    plan_ids = [item.get("opaque_slot_id") for item in plan_rows]
    closed_ids = [item.get("opaque_slot_id") for item in closed_rows]
    shape_ids = [shape["slot_id"] for shape in shapes]
    if any(not isinstance(slot_id, str) or not slot_id for slot_id in plan_ids + closed_ids):
        raise ValueError("empty or invalid slot id")
    if len(plan_ids) != len(set(plan_ids)):
        raise ValueError("duplicate public plan slot id")
    if len(closed_ids) != len(set(closed_ids)):
        raise ValueError("duplicate closed slot id")
    if len(shape_ids) != len(set(shape_ids)) or len(shape_ids) != 12:
        raise ValueError("duplicate or missing routed receipt row")
    if len(disk_slot_names) != len(set(disk_slot_names)) or len(disk_slot_names) != 12:
        raise ValueError("duplicate or missing disk slot directory")
    if unexpected_disk_entries:
        raise ValueError("unexpected non-directory entry in slots root")
    if (
        plan.get("slot_count") != len(plan_rows)
        or closed.get("expected_slot_count") != len(closed_rows)
        or closed.get("actual_slot_directory_count") != len(disk_slot_names)
    ):
        raise ValueError("declared/list/disk multiplicity mismatch")
    if closed.get("status") != "CLOSED" or closed.get("unexpected_slot_entries") != []:
        raise ValueError("public closed receipt is incomplete or unexpected")
    plan_set = set(plan_ids)
    closed_set = set(closed_ids)
    disk_set = set(disk_slot_names)
    receipt_set = set(shape_ids)
    if not (plan_set == closed_set == disk_set == receipt_set):
        raise ValueError("unexpected or missing slot across plan/closed/disk/receipts")
    plan_slots = {
        item["opaque_slot_id"]: item["challenge"] for item in plan_rows
    }
    closed_slots = {item["opaque_slot_id"]: item for item in closed_rows}
    shape_by_slot = {shape["slot_id"]: shape for shape in shapes}
    for slot_id, challenge in plan_slots.items():
        item = closed_slots[slot_id]
        if item["challenge"] != challenge or item["status"] != "COMPLETE":
            raise ValueError(f"public lineage mismatch for {slot_id}")
        if item["files"]["collector-features.json"] != shape_by_slot[slot_id]["receipt_sha256"]:
            raise ValueError(f"collector hash mismatch for {slot_id}")
    if plan["batch_id"] != closed["batch_id"]:
        raise ValueError("batch id mismatch")
    return plan_slots, {
        "status": "OBSERVED_PUBLIC_LINEAGE_PASS__NOT_V1_1_ADMISSION",
        "batch_id": plan["batch_id"],
        "public_plan_sha256": sha256(plan_raw),
        "closed_sha256": sha256(closed_raw),
        "exploratory_expected_public_plan_sha256": expected_plan_sha256,
        "exploratory_expected_closed_sha256": expected_closed_sha256,
        "closed_merkle_root": closed["batch_merkle_root"],
        "slot_set_sha256": sha256(canonical_bytes(sorted(plan_slots))),
        "raw_plan_rows_unique": True,
        "raw_closed_rows_unique": True,
        "collector_hashes_match_closed": True,
        "slot_sets_plan_closed_disk_receipts_equal": True,
        "authority_boundary": "Expected plan/closed SHA constants are an exploratory local anchor. A writer that can also modify this study can co-rewrite them; formal admission requires an external controller or permission-domain expected preimage.",
    }


def verify_f_lineage(shapes: list[dict[str, Any]]) -> tuple[dict[str, str], dict[str, Any]]:
    disk_children = list(SMOKE_SLOTS.iterdir())
    disk_slots = [path.name for path in disk_children if path.is_dir()]
    unexpected = [path.name for path in disk_children if not path.is_dir()]
    return verify_f_lineage_documents(
        plan_raw=PUBLIC_PLAN_PATH.read_bytes(),
        closed_raw=CLOSED_PATH.read_bytes(),
        shapes=shapes,
        disk_slot_names=disk_slots,
        unexpected_disk_entries=unexpected,
        expected_plan_sha256=EXPECTED_PUBLIC_PLAN_SHA256,
        expected_closed_sha256=EXPECTED_CLOSED_SHA256,
    )


def stratified_public_split(
    shapes: list[dict[str, Any]], challenge_by_slot: Mapping[str, str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_challenge: dict[str, list[dict[str, Any]]] = {}
    for shape in shapes:
        by_challenge.setdefault(challenge_by_slot[shape["slot_id"]], []).append(shape)
    reference = []
    probe = []
    strata = {}
    for challenge, members in sorted(by_challenge.items()):
        if len(members) != 4:
            raise ValueError(f"expected four public slots in {challenge}")
        ranked = sorted(
            members,
            key=lambda shape: sha256(
                b"W025_LAYOUT_V2_PUBLIC_STRATIFIED_SPLIT\x00"
                + shape["slot_id"].encode("utf-8")
            ),
        )
        reference.extend(ranked[:2])
        probe.extend(ranked[2:])
        strata[challenge] = {"reference": 2, "probe": 2}
    return reference, probe, {
        "rule": "Within each public-plan challenge, rank opaque slot id by SHA256(domain||0x00||slot_id); first two reference, last two probe.",
        "domain": "W025_LAYOUT_V2_PUBLIC_STRATIFIED_SPLIT",
        "strata": strata,
        "precommitted_before_F_receipts": False,
        "fitness": "EXPLORATORY_ONLY_CURRENT_12_INSUFFICIENT_FOR_NOVELTY_DECISION",
    }


def build_result() -> dict[str, Any]:
    routing, receipt_schema, coverage = routing_lib.verify_candidate_bytes(
        ROUTING_PATH.read_bytes(),
        ROUTING_SCHEMA_PATH.read_bytes(),
        RECEIPT_SCHEMA_PATH.read_bytes(),
        PRIMITIVES_PATH.read_bytes(),
    )
    receipt_paths = sorted(SMOKE_SLOTS.glob("*/collector-features.json"))
    if len(receipt_paths) != 12:
        raise ValueError(f"expected 12 receipts, found {len(receipt_paths)}")
    shapes = [receipt_shape(routing, receipt_schema, path) for path in receipt_paths]
    challenge_by_slot, lineage = verify_f_lineage(shapes)
    reference, probe, split_manifest = stratified_public_split(shapes, challenge_by_slot)
    static = static_routing_study(routing)
    ngram_families = {
        row["family"]
        for row in routing["rows"]
        for spec in row["channels"]
        if routing["channel_stat_registry"][spec["channel"]]["kind"] == "NGRAM_DIRECT"
    }
    fixed_ngram_width = len(ngram_families) * 4096
    all_numeric = set().union(*(shape["numeric_ids"] for shape in shapes))
    all_category = set().union(*(shape["category_ids"] for shape in shapes))
    all_open = set().union(*(shape["open_ids"] for shape in shapes))
    all_unknown = set().union(*(shape["unknown_ids"] for shape in shapes))
    all_ngram = set().union(*(shape["ngram_ids"] for shape in shapes))
    all_route_only = set().union(*(shape["route_only_ids"] for shape in shapes))
    snapshot_width = len(all_numeric) + len(all_category) + fixed_ngram_width
    snapshot_nnz = sum(
        len(shape["numeric_ids"]) + len(shape["category_ids"]) + len(shape["ngram_ids"])
        for shape in shapes
    )
    route_only_nnz = sum(len(shape["route_only_ids"]) for shape in shapes)
    category_frequency = Counter()
    open_frequency = Counter()
    unknown_frequency = Counter()
    domain_by_identity = {}
    template_by_identity = {}
    for shape in shapes:
        category_frequency.update(shape["category_ids"])
        open_frequency.update(shape["open_ids"])
        unknown_frequency.update(shape["unknown_ids"])
        domain_by_identity.update(shape["domain_by_id"])
        template_by_identity.update(shape["template_by_id"])
    reference_category = set().union(*(shape["category_ids"] for shape in reference))
    probe_category = set().union(*(shape["category_ids"] for shape in probe))
    probe_only = probe_category - reference_category
    probe_only_singletons = {identity for identity in probe_only if category_frequency[identity] == 1}
    probe_only_by_family = Counter(template_by_identity[identity][0] for identity in probe_only)
    identity_domain_counts = Counter(domain_by_identity.values())
    layout_comparisons = [
        calibration_frozen_layouts(reference, probe, ngram_families, width)
        for width in HASH_WIDTHS
    ]
    public_shapes = []
    for shape in shapes:
        nnz = len(shape["numeric_ids"]) + len(shape["category_ids"]) + len(shape["ngram_ids"])
        public_shapes.append(
            {
                key: value
                for key, value in shape.items()
                if key
                in {
                    "source_name_sha256",
                    "receipt_sha256",
                    "scalar_leaf_count",
                    "pseudo_event_count",
                    "emission_opportunities_before_aggregation",
                    "numeric_structural_occupied",
                    "exact_category_occupied",
                    "grammar_open_category_occupied",
                    "unknown_domain_category_occupied",
                    "ngram_direct_buckets_occupied",
                    "static_route_only_occupied",
                }
            }
        )
        public_shapes[-1]["observed_union_snapshot_nnz"] = nnz
        public_shapes[-1]["observed_union_snapshot_density"] = nnz / snapshot_width
    exact_manifest = canonical_bytes(sorted(all_category))
    result = {
        "schema": "wave025-model-input-layout-study-result-v4",
        "status": "CANDIDATE_STUDY_V4__SCOPED_RETROSPECTIVE_SHAPE_ONLY__POWER_UNKNOWN__NO_G__NO_3200",
        "bound_inputs": {
            "routing_sha256": sha256(ROUTING_PATH.read_bytes()),
            "routing_schema_sha256": sha256(ROUTING_SCHEMA_PATH.read_bytes()),
            "receipt_schema_sha256": sha256(RECEIPT_SCHEMA_PATH.read_bytes()),
            "primitives_sha256": sha256(PRIMITIVES_PATH.read_bytes()),
            "public_plan_sha256": sha256(PUBLIC_PLAN_PATH.read_bytes()),
            "closed_sha256": sha256(CLOSED_PATH.read_bytes()),
            "exploratory_expected_public_plan_sha256": EXPECTED_PUBLIC_PLAN_SHA256,
            "exploratory_expected_closed_sha256": EXPECTED_CLOSED_SHA256,
            "receipt_count": len(receipt_paths),
            "receipt_set_sha256": sha256(
                canonical_bytes(sorted(sha256(path.read_bytes()) for path in receipt_paths))
            ),
        },
        "selection_firewall": {
            "awareness": "PRIVATE_ROLE_AND_OUTCOME_BLIND__PUBLIC_TREATMENT_AWARE",
            "public_treatment_used": "Public plan challenge assignment is used only to stratify D0-HOST-LEAK, D1-OCI-CANARY, and T-OCI-ISOLATED.",
            "read_inputs": [
                "FEATURE-ROUTING-V2S.candidate.json",
                "FEATURE-ROUTING-V2S.candidate.schema.json",
                "COLLECTOR-RECEIPT-V1.candidate.schema.json",
                "V2S-PRIMITIVES.candidate.json",
                "public-plan.json",
                "closed.json",
                "12 public collector-features.json receipts",
            ],
            "forbidden_and_not_read": [
                "runner-private-state.json",
                "reveal.json",
                "private registries",
                "role labels",
                "outcome labels",
            ],
            "probe_split": split_manifest,
        },
        "public_f_lineage": lineage,
        "routing_static_shape": static,
        "actual_f_shape": {
            "routing_status": coverage["structural_ownership"],
            "receipts": public_shapes,
            "observed_union_snapshot_not_a_frozen_model_layout": {
                "numeric_contextual_columns": len(all_numeric),
                "exact_category_columns": len(all_category),
                "grammar_open_category_columns": len(all_open),
                "unknown_domain_category_columns": len(all_unknown),
                "category_identity_domain_counts": dict(sorted(identity_domain_counts.items())),
                "occupied_direct_ngram_columns": len(all_ngram),
                "reachable_ngram_families": sorted(ngram_families),
                "fixed_direct_ngram_columns": fixed_ngram_width,
                "static_route_only_columns": len(all_route_only),
                "snapshot_logical_columns": snapshot_width,
                "snapshot_total_nnz": snapshot_nnz,
                "snapshot_csr_float64_u32_bytes": csr_bytes(12, snapshot_nnz),
                "snapshot_dense_float64_bytes": 12 * snapshot_width * 8,
                "exact_category_manifest_bytes": len(exact_manifest),
                "static_route_only_total_nnz": route_only_nnz,
                "static_route_only_csr_float64_u32_bytes": csr_bytes(12, route_only_nnz),
                "warning": "Uses all twelve receipts after observation; valid for retrospective shape arithmetic only, never for calibration-frozen model allocation.",
            },
            "novelty_exploration_current_12": {
                "reference_receipts": len(reference),
                "probe_receipts": len(probe),
                "all_category_columns": len(category_frequency),
                "all_category_singletons": sum(count == 1 for count in category_frequency.values()),
                "grammar_open_columns": len(open_frequency),
                "grammar_open_singletons": sum(count == 1 for count in open_frequency.values()),
                "unknown_domain_columns": len(unknown_frequency),
                "unknown_domain_singletons": sum(count == 1 for count in unknown_frequency.values()),
                "probe_category_columns": len(probe_category),
                "probe_only_category_columns": len(probe_only),
                "probe_only_singletons": len(probe_only_singletons),
                "probe_only_by_family": dict(sorted(probe_only_by_family.items())),
                "verdict": "CURRENT_12_INSUFFICIENT_FOR_NOVELTY_OR_HASH_VALUE_DECISION",
                "reason": "Two reference/two probe receipts per public mechanism stratum, no precommit, and singleton-heavy novelty cannot distinguish transferable OOV from per-run identity noise.",
            },
        },
        "calibration_frozen_layout_comparison": layout_comparisons,
        "transform_layout_estimates": {
            "family_norm_off": {
                "logical_columns_snapshot": snapshot_width,
                "structural_nnz_upper_bound_snapshot": snapshot_nnz,
                "csr_float64_u32_bytes_upper_bound_snapshot": csr_bytes(12, snapshot_nnz),
            },
            "family_norm_in_place": {
                "logical_columns_snapshot": snapshot_width,
                "structural_nnz_upper_bound_snapshot": snapshot_nnz,
                "csr_float64_u32_bytes_upper_bound_snapshot": csr_bytes(12, snapshot_nnz),
                "qualification": "Same allocation only when normalization is in-place and does not turn a nonzero family block into all-zero.",
            },
            "family_norm_plus_retained_norm_columns": {
                "logical_columns_snapshot": snapshot_width + len(FAMILIES),
                "structural_nnz_upper_bound_snapshot": snapshot_nnz + len(shapes) * len(FAMILIES),
                "csr_float64_u32_bytes_upper_bound_snapshot": csr_bytes(
                    12, snapshot_nnz + len(shapes) * len(FAMILIES)
                ),
                "qualification": "Upper bound assumes all seven family norms are emitted for every receipt.",
            },
            "robust_center_iqr_vs_no_centering": {
                "logical_columns_snapshot_both": snapshot_width,
                "structural_presence_upper_bound_snapshot_both": snapshot_nnz,
                "exact_zero_compressed_nnz_relation": "MAY_DIFFER; E5 changes 3 raw nonzeros to 4 centered/scaled nonzeros.",
                "semantic_provider_required_for_actual_receipt_nnz": True,
            },
        },
        "fixtures": fixture_study(),
        "mechanism_compatibility": {
            "exact_sparse_one_hot": {
                "compatible_with": "Calibration-frozen exact identities and E1 discrimination.",
                "does_not_solve": "Unseen category identity; exact-only drops it and exact+OTHER merges it by known structural template.",
            },
            "static_route_only": {
                "compatible_with": "Finite route/channel/stat membership checks and a low-width diagnostic baseline.",
                "does_not_solve": "Open category value identity; E1 is a direct removal counterexample.",
            },
            "signed_hash": {
                "compatible_with": "Bounded columns for probe-novel open categories.",
                "does_not_solve": "Collision-free identity; signed-sum is not presence; E2 proves an exact cancellation.",
                "deletion_authorization_diagnostic": signed_hash_receipt_diagnostic(None, {}),
                "evidence_receipts_supplied": 0,
                "current_decision": "UNKNOWN_DO_NOT_DELETE",
            },
            "independent_presence_or": {
                "compatible_with": "Bucket occupancy under signed cancellation.",
                "does_not_solve": "Exact value identity or multiplicity.",
            },
            "family_norm": {
                "compatible_with": "Optional conditioning against family volume dominance.",
                "does_not_solve": "It can erase family-volume signal; E4 forbids making it the only view without an ablation.",
            },
            "robust_center_iqr": {
                "compatible_with": "Frozen label-blind affine conditioning with an explicit missing column.",
                "does_not_solve": "Power; E5 only establishes transform behavior. It must never be recomputed on probe/holdout.",
            },
        },
        "scientific_boundary": {
            "actual_shape_is_not_signal": "The twelve F receipts constrain retrospective dimensions and sparse arithmetic only; the current sample is insufficient to establish novelty value.",
            "d0_fact_from_separate_audit": "F's registered collector surface did not expose the D0 token/content signal; layout differences cannot convert absent registered information into detector power.",
            "no_power_claim": True,
            "power": "UNKNOWN",
            "no_classifier_fit": True,
            "c01_phase_boundary": "EXTERNAL_UNRESOLVED_DEPENDENCY",
            "rejected_c01_minisuite_used_as_ground_truth": False,
            "g_started": False,
            "formal_3200_started": False,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    raw = canonical_bytes(build_result())
    if args.check:
        if args.check.read_bytes() != raw:
            print("RESULT_MISMATCH", file=sys.stderr)
            return 1
        print("RESULT_MATCH")
        return 0
    sys.stdout.buffer.write(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
