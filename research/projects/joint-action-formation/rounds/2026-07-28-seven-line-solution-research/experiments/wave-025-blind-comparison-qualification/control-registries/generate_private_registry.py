#!/usr/bin/env python3
"""Generate one preformal Wave 025 private control-registry candidate.

D0 tags are fresh 16-byte OS-CSPRNG values. D1 tokens are read from an already
revealed smoke batch; this deliberately makes the output preformal-only.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any


PUBLIC_SCHEMA = "WAVE025_PUBLIC_CONTROL_FAMILY_REGISTRATION_V1"
PRIVATE_SCHEMA = "WAVE025_PRIVATE_CONTROL_REGISTRY_V1"
PROFILE_ID = "WAVE025-EXECUTABLE-ATTACK-PROFILE-FULL-V1"
D0_FAMILY_ID = "D0_RESIDUE_OPAQUE_BASENAME_V1"
D1_FAMILY_ID = "D1_CURRENT_RUN_CANARY_V1"
D0_BASENAME_PREFIX = "d0-residue-v1-"
ROLE_LABELS = ("R", "S")


class RegistryGenerationError(ValueError):
    """Raised when an input cannot produce the frozen candidate shape."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(value)
    if actual != expected:
        raise RegistryGenerationError(
            f"{context} fields mismatch missing={sorted(expected - actual)} unknown={sorted(actual - expected)}"
        )


def validate_public_registration(value: Any) -> None:
    if not isinstance(value, dict):
        raise RegistryGenerationError("public registration must be an object")
    _require_exact_keys(
        value,
        {
            "schema",
            "version",
            "registry_id",
            "status",
            "binding_state",
            "profile_id",
            "feature_spec_sha256",
            "private_material_included",
            "families",
        },
        "public registration",
    )
    if value["schema"] != PUBLIC_SCHEMA:
        raise RegistryGenerationError("wrong public registration schema")
    if value["version"] != "1.0.0":
        raise RegistryGenerationError("wrong public registration version")
    if value["registry_id"] != "WAVE025-PUBLIC-CONTROL-FAMILIES-PREFORMAL-V1":
        raise RegistryGenerationError("wrong public registry_id")
    if value["status"] != "PREFORMAL_CANDIDATE_NOT_BOUND":
        raise RegistryGenerationError("public registration is not the preformal candidate")
    if value["binding_state"] != "NOT_BOUND_TO_PROFILE_OR_PRECOMMIT":
        raise RegistryGenerationError("public registration binding state is not candidate-only")
    if value["profile_id"] != PROFILE_ID:
        raise RegistryGenerationError("wrong profile_id")
    if value["feature_spec_sha256"] != "8398fb773dca1f7da1edd9a5dcef742f27db7ee954fc9f90de8de56713f1236a":
        raise RegistryGenerationError("wrong feature_spec_sha256")
    if value["private_material_included"] is not False:
        raise RegistryGenerationError("public registration cannot include private material")
    families = value["families"]
    if not isinstance(families, list) or len(families) != 2:
        raise RegistryGenerationError("public registration must contain exactly D0 and D1")
    expected = [
        (
            D0_FAMILY_ID,
            "D0-HOST-LEAK",
            "F04_DIRECTORY_AND_SHARED_STATE",
            "SACRIFICIAL_PREDECESSOR_CREATED_EXACT_BASENAME_IN_READONLY_SHARED_RESIDUE_CWD",
        ),
        (
            D1_FAMILY_ID,
            "D1-OCI-CANARY",
            "F07_VISIBLE_CANARY",
            "CURRENT_RUN_ROLE_CORRELATED_CANARY_IN_CHALLENGE_ENTRY_NAME_AND_FILE_CONTENT",
        ),
    ]
    family_keys = {
        "family_id",
        "challenge",
        "injection_surface",
        "expected_collector_feature_family",
        "primary_detector_id_from_C01_TO_C05",
        "calibration_population_by_role",
        "holdout_population_by_role",
    }
    for index, (family, expected_values) in enumerate(zip(families, expected)):
        if not isinstance(family, dict):
            raise RegistryGenerationError(f"public family[{index}] must be an object")
        _require_exact_keys(family, family_keys, f"public family[{index}]")
        actual_values = (
            family["family_id"],
            family["challenge"],
            family["expected_collector_feature_family"],
            family["injection_surface"],
        )
        if actual_values != expected_values:
            raise RegistryGenerationError(f"public family[{index}] identity mismatch")
        if family["primary_detector_id_from_C01_TO_C05"] != "C01_EXACT_CATEGORICAL_SCAN":
            raise RegistryGenerationError(f"public family[{index}] primary detector mismatch")
        if family["calibration_population_by_role"] != 50 or family["holdout_population_by_role"] != 50:
            raise RegistryGenerationError(f"public family[{index}] population mismatch")


def d1_mapping_from_reveal(reveal: Any) -> dict[str, str]:
    if not isinstance(reveal, dict) or not isinstance(reveal.get("mapping"), list):
        raise RegistryGenerationError("reveal mapping missing")
    values: dict[str, set[str]] = {role: set() for role in ROLE_LABELS}
    for row in reveal["mapping"]:
        if not isinstance(row, dict) or row.get("challenge") != "D1-OCI-CANARY":
            continue
        role = row.get("role")
        token = row.get("canary_token_or_null")
        if role not in values or not isinstance(token, str):
            raise RegistryGenerationError("D1 reveal row has invalid role or token")
        values[role].add(token)
    result: dict[str, str] = {}
    for role in ROLE_LABELS:
        if len(values[role]) != 1:
            raise RegistryGenerationError(f"D1 role {role} must have exactly one stable token")
        token = next(iter(values[role]))
        if len(token.encode("utf-8")) != 50 or not token.startswith("WAVE025_CANARY_D1_CURRENT_"):
            raise RegistryGenerationError(f"D1 role {role} token has wrong shape")
        result[role] = token
    if result["R"] == result["S"]:
        raise RegistryGenerationError("D1 tokens must be distinct")
    return result


def build_registry(
    public_raw: bytes,
    reveal_raw: bytes,
    generated_at: str,
    d0_tags: tuple[str, str] | None = None,
) -> dict[str, Any]:
    public = json.loads(public_raw)
    reveal = json.loads(reveal_raw)
    validate_public_registration(public)
    if public_raw != canonical_bytes(public):
        raise RegistryGenerationError("public registration must be canonical UTF-8 JSON with one LF")
    d1_tokens = d1_mapping_from_reveal(reveal)
    if d0_tags is None:
        d0_tags = (secrets.token_hex(16), secrets.token_hex(16))
        while d0_tags[0] == d0_tags[1]:
            d0_tags = (d0_tags[0], secrets.token_hex(16))
    if len(d0_tags) != 2 or any(len(tag) != 32 or any(ch not in "0123456789abcdef" for ch in tag) for tag in d0_tags):
        raise RegistryGenerationError("D0 tags must be two lowercase 16-byte hex values")
    if d0_tags[0] == d0_tags[1]:
        raise RegistryGenerationError("D0 tags must be distinct")

    d0_family = {
        "challenge": "D0-HOST-LEAK",
        "family_id": D0_FAMILY_ID,
        "mapping_stability": "ONE_VALUE_PER_ROLE_REUSED_ACROSS_CALIBRATION_AND_HOLDOUT",
        "private_value_kind": "TWO_DISTINCT_16_BYTE_CSPRNG_TAGS_HEX_ENCODED_IN_BASENAME",
        "role_mappings": [
            {
                "candidate_visible_basename": f"{D0_BASENAME_PREFIX}{tag}",
                "role_label": role,
                "tag_hex": tag,
            }
            for role, tag in zip(ROLE_LABELS, d0_tags)
        ],
    }
    d1_family = {
        "challenge": "D1-OCI-CANARY",
        "family_id": D1_FAMILY_ID,
        "mapping_stability": "ONE_VALUE_PER_ROLE_REUSED_ACROSS_CALIBRATION_AND_HOLDOUT",
        "private_value_kind": "CURRENT_WAVE025_CANARY_TOKEN_UTF8",
        "role_mappings": [
            {
                "candidate_visible_sources": ["challenge-entry-name", "challenge-file-content"],
                "role_label": role,
                "token_byte_length": len(d1_tokens[role].encode("utf-8")),
                "token_utf8": d1_tokens[role],
            }
            for role in ROLE_LABELS
        ],
    }
    return {
        "binding_state": "NOT_BOUND_TO_PROFILE_OR_PRECOMMIT",
        "families": [d0_family, d1_family],
        "generated_at": generated_at,
        "material_provenance": {
            "D0-HOST-LEAK": {
                "fresh_for_this_candidate": True,
                "generator": "PYTHON_SECRETS_TOKEN_HEX_16",
                "kind": "OS_CSPRNG",
            },
            "D1-OCI-CANARY": {
                "fresh_for_formal": False,
                "kind": "REUSED_FROM_ALREADY_REVEALED_SMOKE_PREFORMAL_ONLY",
                "source_batch_id": reveal.get("batch_id"),
                "source_reveal_sha256": sha256(reveal_raw),
            },
        },
        "per_family_canonical_sha256": {
            D0_FAMILY_ID: sha256(canonical_bytes(d0_family)),
            D1_FAMILY_ID: sha256(canonical_bytes(d1_family)),
        },
        "profile_id": PROFILE_ID,
        "public_registration_sha256": sha256(public_raw),
        "registry_id": "WAVE025-PRIVATE-CONTROL-REGISTRY-PREFORMAL-V1",
        "role_labels": list(ROLE_LABELS),
        "schema": PRIVATE_SCHEMA,
        "status": "PREFORMAL_CANDIDATE_NOT_BOUND_REUSES_REVEALED_D1",
        "version": "1.0.0",
    }


def write_exclusive_0600(path: Path, raw: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public_registration", type=Path)
    parser.add_argument("revealed_smoke", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--generated-at",
        default=None,
        help="Frozen RFC3339 UTC timestamp; defaults to current UTC.",
    )
    args = parser.parse_args()
    generated_at = args.generated_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    registry = build_registry(
        args.public_registration.read_bytes(),
        args.revealed_smoke.read_bytes(),
        generated_at,
    )
    write_exclusive_0600(args.output, canonical_bytes(registry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
