"""Frozen E1/E5 worlds for the CE-001 A4 common-world vertical slice."""

from __future__ import annotations

import copy
import hashlib
import uuid
from typing import Any, Mapping

from services import OWNER_IDS, sha256_value


CASE_IDS = ("E1-EXTANT-MULTI-OWNER", "E5-IMPOSSIBLE-REFUSAL")


def case_definition(
    case_id: str,
    run_id: str,
    *,
    feasible_alternatives_override: list[str] | None = None,
) -> dict[str, Any]:
    if case_id not in CASE_IDS:
        raise ValueError(f"unsupported vertical-slice case: {case_id}")
    public_case = {
        "schema": "CE001_PUBLIC_CASE_V1",
        "case_id": case_id,
        "run_id": run_id,
        "task": {
            "q_version": "Q@v1",
            "object_id": "VenueV:CircuitC7",
            "target_id": "VenueV:CircuitC7",
            "required_power_kw": 3.0,
            "required_duration_minutes": 45,
            "deadline_minute": 90,
            "power_tolerance_percent": 5,
        },
        "available_interfaces": ["O_V", "O_R", "O_S", "O_Q", "O_P", "O_E", "TARGET"],
    }
    canary_value = f"private-canary-{uuid.uuid4().hex}"
    feasible_alternatives = (
        list(feasible_alternatives_override)
        if feasible_alternatives_override is not None
        else ([] if case_id == "E5-IMPOSSIBLE-REFUSAL" else ["A4"])
    )
    owner_shards = {
        owner_id: {
            "schema": "CE001_OWNER_INITIAL_SHARD_V1",
            "owner_id": owner_id,
            "case_id": case_id,
            "authority_decision": (
                "REFUSED" if case_id == "E5-IMPOSSIBLE-REFUSAL" and owner_id == "O_V" else "GRANTED"
            ),
            "known_feasible_alternatives": (
                list(feasible_alternatives) if owner_id == "O_R" else []
            ),
            "private_nonce": uuid.uuid4().hex,
        }
        for owner_id in OWNER_IDS
    }
    reveal = {
        "schema": "CE001_PRIVATE_CASE_REVEAL_V1",
        "case_id": case_id,
        "run_id": run_id,
        "alternative_oracle": {
            "schema": "CE001_ALTERNATIVE_ORACLE_V1",
            "feasible_alternatives": feasible_alternatives,
            "authoritative_owner_id": "O_R",
            "closed_world_boundary": (
                "FROZEN_SYNTHETIC_ACTION_GRAMMAR_ONLY"
            ),
        },
        "owner_initial_shards": copy.deepcopy(owner_shards),
        "truth_facts": {
            "venue_owner_non_delegable_refusal": case_id == "E5-IMPOSSIBLE-REFUSAL",
            "required_authority_owners": (
                ["O_V"] if case_id == "E5-IMPOSSIBLE-REFUSAL" else ["O_V", "O_R", "O_S"]
            ),
        },
        "private_canary_value": canary_value,
    }
    truth_sha = sha256_value(reveal)
    receipt = {
        "schema": "CE001_PRIVATE_CASE_RECEIPT_V1",
        "case_id": case_id,
        "run_id": run_id,
        "private_truth_sha256": truth_sha,
        "private_canary_sha256": hashlib.sha256(canary_value.encode("utf-8")).hexdigest(),
        "owner_initial_shard_sha256": {
            owner_id: sha256_value(shard) for owner_id, shard in owner_shards.items()
        },
    }
    receipt["receipt_sha256"] = sha256_value(receipt)
    world_root = sha256_value(
        {"public_case": public_case, "private_case_receipt": receipt}
    )
    return {
        "public_case": public_case,
        "private_case_receipt": receipt,
        "private_case_reveal": reveal,
        "owner_shards": owner_shards,
        "private_canary": canary_value,
        "world_root": world_root,
    }


def make_episode_manifest(
    *,
    case_id: str,
    run_id: str,
    world_root: str,
    owner_registry_sha256: str,
    target_registry_sha256: str,
) -> dict[str, Any]:
    manifest = {
        "schema": "CE001_EPISODE_MANIFEST_V1",
        "run_id": run_id,
        "world_root": world_root,
        "case_id": case_id,
        # Independent public binding for the arm-facing view.  It is not a
        # digest of case_id or of the evaluator-private manifest, so a two-case
        # dictionary cannot recover the hidden label.
        "arm_binding_token": f"arm-bind-{uuid.uuid4().hex}{uuid.uuid4().hex}",
        "arm_id": "A4-DETERMINISTIC-MATURE-COMPOSITION",
        "authority_stratum": "P",
        "q_version": "Q@v1",
        "object_id": "VenueV:CircuitC7",
        "target_id": "VenueV:CircuitC7",
        "operation_id": f"operation-{run_id}",
        "deadline_minute": 90,
        "required_duration_minutes": 45,
        "required_power_kw": 3.0,
        "power_tolerance_percent": 5,
        "owner_registry_sha256": owner_registry_sha256,
        "target_registry_sha256": target_registry_sha256,
    }
    manifest["manifest_sha256"] = sha256_value(manifest)
    return manifest


def registry_projection(service_entry: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable start-time projection used by the manifest."""
    keys = (
        "service_id",
        "actual_pid",
        "public_key_hex",
        "state_source_id",
        "state_head_at_start",
        "state_epoch_at_start",
        "backend_kind",
        "backend_identity_sha256",
        "executable_sha256",
        "initial_shard_sha256",
        "process_start_receipt_sha256",
    )
    projection = {key: service_entry[key] for key in keys if key in service_entry}
    projection["process_start_receipt_sha256"] = service_entry[
        "process_start_receipt"
    ]["receipt_sha256"]
    return projection
