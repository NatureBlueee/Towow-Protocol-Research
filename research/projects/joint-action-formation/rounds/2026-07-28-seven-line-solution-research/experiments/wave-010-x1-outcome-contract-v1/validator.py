#!/usr/bin/env python3
"""Build and validate the Wave010 X1 outcome-contract v1 candidate.

This module validates a contract candidate and synthetic conformance fixtures
only. It does not run X1, score a method, or authorize X2.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROUND_ROOT = HERE.parent.parent
V0_PATH = ROUND_ROOT / "WAVE-010-X1-OUTCOME-CONTRACT-v0.json"
V1_PATH = ROUND_ROOT / "WAVE-010-X1-OUTCOME-CONTRACT-v1.json"
SHA256_PATTERN_LENGTH = 64


class ValidationError(ValueError):
    """Raised when a contract or instance violates a v1 invariant."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _enum(values: list[str]) -> dict[str, Any]:
    return {"enum": values}


def _g3_defs() -> dict[str, Any]:
    tri_state = ["TRUE", "FALSE", "UNKNOWN"]
    completeness = ["COMPLETE", "INCOMPLETE", "UNKNOWN"]
    counterfactual_result = ["SAT", "UNSAT", "UNKNOWN", "NOT_APPLICABLE"]
    return {
        "g3_receipt": {
            "type": "object",
            "additionalProperties": False,
            "required": ["receipt_ref", "body_sha256", "body"],
            "properties": {
                "receipt_ref": {"$ref": "#/$defs/receipt_ref"},
                "body_sha256": {"$ref": "#/$defs/sha256"},
                "body": {"$ref": "#/$defs/g3_receipt_body"},
            },
        },
        "g3_receipt_body": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "C",
                "N",
                "E",
                "T",
                "V",
                "R",
                "inventory_completeness",
                "counterfactual",
                "task_diff",
            ],
            "properties": {
                "C": _enum(["SAT", "UNSAT", "UNKNOWN"]),
                "N": _enum(
                    ["NONE", "EXTANT_ACTIVATED", "NEW_TOKEN", "UNKNOWN"]
                ),
                "E": _enum(["SAME", "CHANGED", "UNKNOWN"]),
                "T": _enum(
                    [
                        "INVARIANT",
                        "OWNER_AUTHORIZED_NEW_EPISODE",
                        "CONTROLLER_SUBSTITUTION",
                        "UNKNOWN",
                    ]
                ),
                "V": _enum(
                    ["VALID", "INVALID", "UNKNOWN", "NO_QUALIFIED_EFFECT"]
                ),
                "R": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "R_physical_exists",
                        "R_measurable_exists",
                        "R_actual",
                        "R_effect_robust",
                        "R_safe_robust",
                        "R_terminal_robust",
                    ],
                    "properties": {
                        key: _enum(tri_state)
                        for key in [
                            "R_physical_exists",
                            "R_measurable_exists",
                            "R_actual",
                            "R_effect_robust",
                            "R_safe_robust",
                            "R_terminal_robust",
                        ]
                    },
                },
                "inventory_completeness": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "action_inventory",
                        "response_family",
                        "observation_kernel",
                        "transition_semantics",
                        "search_bound_frozen",
                        "horizon",
                        "unresolved_items",
                        "evidence_sha256",
                    ],
                    "properties": {
                        "action_inventory": _enum(completeness),
                        "response_family": _enum(completeness),
                        "observation_kernel": _enum(completeness),
                        "transition_semantics": _enum(completeness),
                        "search_bound_frozen": {"type": "boolean"},
                        "horizon": {"type": "integer", "minimum": 0},
                        "unresolved_items": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                        "evidence_sha256": {"$ref": "#/$defs/sha256"},
                    },
                },
                "counterfactual": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "status",
                        "operator_ids",
                        "remove_result",
                        "reverse_result",
                        "block_result",
                        "evidence_sha256",
                    ],
                    "properties": {
                        "status": _enum(
                            ["APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"]
                        ),
                        "operator_ids": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                        "remove_result": _enum(counterfactual_result),
                        "reverse_result": _enum(counterfactual_result),
                        "block_result": _enum(counterfactual_result),
                        "evidence_sha256": {"$ref": "#/$defs/sha256"},
                    },
                },
                "task_diff": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "classification",
                        "original_task_sha256",
                        "result_task_sha256",
                        "material_fields",
                        "changes",
                        "owner_authorization_receipts",
                        "controller_claim_refs",
                    ],
                    "properties": {
                        "classification": _enum(
                            [
                                "UNCHANGED",
                                "OWNER_AUTHORIZED_NEW_EPISODE",
                                "CONTROLLER_SUBSTITUTION",
                                "UNKNOWN",
                            ]
                        ),
                        "original_task_sha256": {"$ref": "#/$defs/sha256"},
                        "result_task_sha256": {"$ref": "#/$defs/sha256"},
                        "material_fields": {
                            "type": "array",
                            "items": {"type": "string", "minLength": 1},
                        },
                        "changes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "path",
                                    "before_value",
                                    "after_value",
                                ],
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "minLength": 1,
                                    },
                                    "before_value": {},
                                    "after_value": {},
                                },
                            },
                        },
                        "owner_authorization_receipts": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/receipt_ref"},
                        },
                        "controller_claim_refs": {
                            "type": "array",
                            "items": {"$ref": "#/$defs/receipt_ref"},
                        },
                    },
                },
            },
        },
    }


def build_v1_contract(v0: dict[str, Any]) -> dict[str, Any]:
    """Create the v1 candidate as a lossless, reproducible v0 migration."""

    contract = copy.deepcopy(v0)
    contract["contract_version"] = "1"
    contract["status"] = "CANDIDATE_NOT_RUN"
    contract["purpose"] = (
        "Lossless, fail-closed X1 to X2 outcome handoff with embedded G3 "
        "evidence. This contract does not create an X1 result or authorize "
        "an X2 attempt."
    )
    contract["base_contract"] = {
        "path": "WAVE-010-X1-OUTCOME-CONTRACT-v0.json",
        "raw_sha256": raw_sha256(V0_PATH),
        "migration": "ADDITIVE_EXCEPT_FOR_THREE_INTENTIONAL_G3_SEMANTIC_BREAKS",
    }

    categories = contract["category_registry"]
    insertion_point = categories.index("BOUNDED_UNREACHABLE")
    for category in [
        "ACTUAL_POLICY_MISS",
        "AUTHORIZED_NEW_EPISODE",
        "INVALID_SUBSTITUTION",
    ]:
        categories.insert(insertion_point, category)
        insertion_point += 1

    registry = contract["reason_registry"]
    registry["BOUNDED_UNREACHABLE"] = ["G3_BOUNDED_UNREACHABLE"]
    registry["INVALID"].remove("G3_INVALID_SUBSTITUTION")
    registry["ACTUAL_POLICY_MISS"] = [
        "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS"
    ]
    registry["AUTHORIZED_NEW_EPISODE"] = [
        "G3_OWNER_AUTHORIZED_MATERIAL_GOAL_CHANGE"
    ]
    registry["INVALID_SUBSTITUTION"] = [
        "G3_CONTROLLER_INVALID_SUBSTITUTION"
    ]
    contract["reason_registry_version"] = "x1-reason-registry-v2"

    schema = contract["outcome_schema"]
    schema["required"].append("g3_receipt")
    schema["properties"]["schema_version"]["const"] = "1"
    schema["properties"]["reason_registry_version"][
        "const"
    ] = "x1-reason-registry-v2"
    schema["properties"]["category"]["enum"] = categories
    schema["properties"]["g3_receipt"] = {"$ref": "#/$defs/g3_receipt"}
    contract["$defs"].update(_g3_defs())

    contract["compatibility"] = {
        "v0_unchanged": True,
        "v0_instances_accepted_when": (
            "They are re-finalized under v1 with a complete g3_receipt and "
            "do not use a retired category/reason pair."
        ),
        "intentional_breaks": [
            {
                "v0": "BOUNDED_UNREACHABLE/G3_NO_ACTUAL_POLICY_PATH",
                "v1": (
                    "ACTUAL_POLICY_MISS/"
                    "G3_MEASURABLE_PATH_EXISTS_ACTUAL_POLICY_MISS when "
                    "R_measurable_exists=TRUE and R_actual=FALSE"
                ),
            },
            {
                "v0": "INVALID/G3_INVALID_SUBSTITUTION",
                "v1": (
                    "AUTHORIZED_NEW_EPISODE/"
                    "G3_OWNER_AUTHORIZED_MATERIAL_GOAL_CHANGE or "
                    "INVALID_SUBSTITUTION/G3_CONTROLLER_INVALID_SUBSTITUTION"
                ),
            },
            {
                "v0": "G3 line receipt ref/hash only",
                "v1": (
                    "mandatory hash-bound G3 body with C/N/E/T/V, all R "
                    "coordinates, inventory completeness, counterfactual, "
                    "and task diff"
                ),
            },
        ],
        "no_status_promotion": True,
    }

    contract["validation_rules"].extend(
        [
            "g3_receipt.receipt_ref MUST equal line_receipt_refs.G3 byte-for-byte",
            "g3_receipt.body_sha256 MUST equal SHA-256 of canonical g3_receipt.body bytes",
            "the G3 body MUST preserve C/N/E/T/V, all six R coordinates, inventory completeness, counterfactual, and task diff; a ref/hash-only G3 receipt is invalid under v1",
            "ACTUAL_POLICY_MISS requires R_measurable_exists=TRUE and R_actual=FALSE and MUST NOT be normalized to BOUNDED_UNREACHABLE",
            "BOUNDED_UNREACHABLE requires C=UNSAT, R_measurable_exists=FALSE, a frozen search bound, and COMPLETE action inventory, response family, observation kernel, and transition semantics",
            "AUTHORIZED_NEW_EPISODE requires an owner-authorized material task diff, distinct original/result task hashes, and at least one owner receipt; it is not success on the original episode",
            "INVALID_SUBSTITUTION requires a controller-substitution task diff, distinct original/result task hashes, and MUST NOT carry owner authorization receipts",
            "contract status remains CANDIDATE_NOT_RUN; schema validation or conformance tests do not create a run, score, or formal evidence status",
        ]
    )

    schema_preimage = {
        "$defs": contract["$defs"],
        "category_registry": contract["category_registry"],
        "outcome_schema": contract["outcome_schema"],
    }
    reason_preimage = {
        "reason_registry": contract["reason_registry"],
        "reason_registry_version": contract["reason_registry_version"],
    }
    contract["hash_binding_rules"]["schema_sha256"][
        "current_preimage_sha256"
    ] = canonical_sha256(schema_preimage)
    contract["hash_binding_rules"]["reason_registry_sha256"][
        "current_preimage_sha256"
    ] = canonical_sha256(reason_preimage)
    return contract


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == SHA256_PATTERN_LENGTH
        and all(char in "0123456789abcdef" for char in value)
    )


def _validate_receipt_ref(value: Any, label: str) -> None:
    _require(isinstance(value, dict), f"{label} must be an object")
    expected = {
        "ref",
        "raw_bytes_sha256",
        "owner_key_id",
        "receipt_version",
        "status",
    }
    _require(set(value) == expected, f"{label} fields mismatch")
    _require(bool(value["ref"]), f"{label}.ref must be non-empty")
    _require(
        _is_sha256(value["raw_bytes_sha256"]),
        f"{label}.raw_bytes_sha256 invalid",
    )
    for key in ["owner_key_id", "receipt_version", "status"]:
        _require(bool(value[key]), f"{label}.{key} must be non-empty")


def validate_contract(contract: dict[str, Any]) -> None:
    _require(contract["contract_version"] == "1", "not contract v1")
    _require(contract["status"] == "CANDIDATE_NOT_RUN", "status promoted")
    _require(contract["base_contract"]["raw_sha256"] == raw_sha256(V0_PATH), "v0 base drift")
    _require(
        "G3_NO_ACTUAL_POLICY_PATH"
        not in contract["reason_registry"]["BOUNDED_UNREACHABLE"],
        "retired G3_NO_ACTUAL_POLICY_PATH still bounded-unreachable",
    )
    _require(
        "G3_INVALID_SUBSTITUTION" not in contract["reason_registry"]["INVALID"],
        "old merged invalid-substitution reason still accepted",
    )
    _require(
        "g3_receipt" in contract["outcome_schema"]["required"],
        "G3 embedded receipt is not mandatory",
    )
    for category in [
        "ACTUAL_POLICY_MISS",
        "AUTHORIZED_NEW_EPISODE",
        "INVALID_SUBSTITUTION",
    ]:
        _require(category in contract["category_registry"], f"missing {category}")
        _require(category in contract["reason_registry"], f"missing reasons for {category}")
    schema_preimage = {
        "$defs": contract["$defs"],
        "category_registry": contract["category_registry"],
        "outcome_schema": contract["outcome_schema"],
    }
    reason_preimage = {
        "reason_registry": contract["reason_registry"],
        "reason_registry_version": contract["reason_registry_version"],
    }
    _require(
        canonical_sha256(schema_preimage)
        == contract["hash_binding_rules"]["schema_sha256"][
            "current_preimage_sha256"
        ],
        "schema preimage hash mismatch",
    )
    _require(
        canonical_sha256(reason_preimage)
        == contract["hash_binding_rules"]["reason_registry_sha256"][
            "current_preimage_sha256"
        ],
        "reason registry preimage hash mismatch",
    )


def _validate_required_object(
    value: Any,
    *,
    label: str,
    required: set[str],
) -> dict[str, Any]:
    _require(isinstance(value, dict), f"{label} must be an object")
    _require(set(value) == required, f"{label} fields mismatch")
    return value


def validate_instance(contract: dict[str, Any], instance: dict[str, Any]) -> None:
    """Validate the three v1 semantic repairs plus lossless G3 embedding."""

    validate_contract(contract)
    required_top = set(contract["outcome_schema"]["required"])
    _require(set(instance) == required_top, "top-level fields mismatch")
    _require(instance["schema_version"] == "1", "wrong schema_version")
    _require(
        instance["reason_registry_version"] == "x1-reason-registry-v2",
        "wrong reason_registry_version",
    )
    _require(
        instance["schema_sha256"]
        == contract["hash_binding_rules"]["schema_sha256"][
            "current_preimage_sha256"
        ],
        "instance schema hash mismatch",
    )
    _require(
        instance["reason_registry_sha256"]
        == contract["hash_binding_rules"]["reason_registry_sha256"][
            "current_preimage_sha256"
        ],
        "instance reason registry hash mismatch",
    )
    _require(
        _is_sha256(instance["raw_method_return_bytes_sha256"]),
        "raw method-return hash invalid",
    )
    for key in ["x1_run_id", "x1_world_id", "x1_arm_id"]:
        _require(bool(instance[key]), f"{key} must be non-empty")

    category = instance["category"]
    reason = instance["reason_code"]
    _require(category in contract["category_registry"], "unregistered category")
    _require(
        reason in contract["reason_registry"].get(category, []),
        "unregistered category/reason pair",
    )

    line_refs = _validate_required_object(
        instance["line_receipt_refs"],
        label="line_receipt_refs",
        required={"G1", "G2", "G3", "G5"},
    )
    transition_refs = _validate_required_object(
        instance["transition_receipt_refs"],
        label="transition_receipt_refs",
        required={"T_G1_TO_G2", "T_G2_TO_G3", "T_G3_TO_G5", "T_G5_TO_X2"},
    )
    for key, value in line_refs.items():
        _validate_receipt_ref(value, f"line_receipt_refs.{key}")
    for key, value in transition_refs.items():
        _validate_receipt_ref(value, f"transition_receipt_refs.{key}")

    g3 = _validate_required_object(
        instance["g3_receipt"],
        label="g3_receipt",
        required={"receipt_ref", "body_sha256", "body"},
    )
    _validate_receipt_ref(g3["receipt_ref"], "g3_receipt.receipt_ref")
    _require(
        g3["receipt_ref"] == line_refs["G3"],
        "embedded G3 receipt ref differs from line_receipt_refs.G3",
    )
    _require(_is_sha256(g3["body_sha256"]), "invalid G3 body hash")
    _require(
        canonical_sha256(g3["body"]) == g3["body_sha256"],
        "G3 body hash mismatch",
    )

    body = _validate_required_object(
        g3["body"],
        label="g3_receipt.body",
        required={
            "C",
            "N",
            "E",
            "T",
            "V",
            "R",
            "inventory_completeness",
            "counterfactual",
            "task_diff",
        },
    )
    allowed_vectors = {
        "C": {"SAT", "UNSAT", "UNKNOWN"},
        "N": {"NONE", "EXTANT_ACTIVATED", "NEW_TOKEN", "UNKNOWN"},
        "E": {"SAME", "CHANGED", "UNKNOWN"},
        "T": {
            "INVARIANT",
            "OWNER_AUTHORIZED_NEW_EPISODE",
            "CONTROLLER_SUBSTITUTION",
            "UNKNOWN",
        },
        "V": {"VALID", "INVALID", "UNKNOWN", "NO_QUALIFIED_EFFECT"},
    }
    for key, allowed in allowed_vectors.items():
        _require(body[key] in allowed, f"invalid G3 {key}")

    r_coordinates = _validate_required_object(
        body["R"],
        label="g3_receipt.body.R",
        required={
            "R_physical_exists",
            "R_measurable_exists",
            "R_actual",
            "R_effect_robust",
            "R_safe_robust",
            "R_terminal_robust",
        },
    )
    for key, value in r_coordinates.items():
        _require(value in {"TRUE", "FALSE", "UNKNOWN"}, f"invalid {key}")

    inventory = _validate_required_object(
        body["inventory_completeness"],
        label="g3_receipt.body.inventory_completeness",
        required={
            "action_inventory",
            "response_family",
            "observation_kernel",
            "transition_semantics",
            "search_bound_frozen",
            "horizon",
            "unresolved_items",
            "evidence_sha256",
        },
    )
    for key in [
        "action_inventory",
        "response_family",
        "observation_kernel",
        "transition_semantics",
    ]:
        _require(
            inventory[key] in {"COMPLETE", "INCOMPLETE", "UNKNOWN"},
            f"invalid inventory {key}",
        )
    _require(
        isinstance(inventory["search_bound_frozen"], bool),
        "search_bound_frozen must be boolean",
    )
    _require(
        isinstance(inventory["horizon"], int) and inventory["horizon"] >= 0,
        "invalid inventory horizon",
    )
    _require(
        isinstance(inventory["unresolved_items"], list)
        and all(isinstance(item, str) and item for item in inventory["unresolved_items"]),
        "invalid inventory unresolved_items",
    )
    _require(_is_sha256(inventory["evidence_sha256"]), "invalid inventory evidence hash")

    counterfactual = _validate_required_object(
        body["counterfactual"],
        label="g3_receipt.body.counterfactual",
        required={
            "status",
            "operator_ids",
            "remove_result",
            "reverse_result",
            "block_result",
            "evidence_sha256",
        },
    )
    _require(
        counterfactual["status"] in {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"},
        "invalid counterfactual status",
    )
    _require(
        isinstance(counterfactual["operator_ids"], list)
        and all(
            isinstance(item, str) and item
            for item in counterfactual["operator_ids"]
        ),
        "invalid counterfactual operator ids",
    )
    for key in ["remove_result", "reverse_result", "block_result"]:
        _require(
            counterfactual[key]
            in {"SAT", "UNSAT", "UNKNOWN", "NOT_APPLICABLE"},
            f"invalid counterfactual {key}",
        )
    _require(
        _is_sha256(counterfactual["evidence_sha256"]),
        "invalid counterfactual evidence hash",
    )

    task_diff = _validate_required_object(
        body["task_diff"],
        label="g3_receipt.body.task_diff",
        required={
            "classification",
            "original_task_sha256",
            "result_task_sha256",
            "material_fields",
            "changes",
            "owner_authorization_receipts",
            "controller_claim_refs",
        },
    )
    _require(
        task_diff["classification"]
        in {
            "UNCHANGED",
            "OWNER_AUTHORIZED_NEW_EPISODE",
            "CONTROLLER_SUBSTITUTION",
            "UNKNOWN",
        },
        "invalid task-diff classification",
    )
    for key in ["original_task_sha256", "result_task_sha256"]:
        _require(_is_sha256(task_diff[key]), f"invalid task diff {key}")
    _require(
        isinstance(task_diff["material_fields"], list)
        and all(
            isinstance(item, str) and item for item in task_diff["material_fields"]
        ),
        "invalid task-diff material_fields",
    )
    _require(isinstance(task_diff["changes"], list), "task-diff changes must be a list")
    change_paths: list[str] = []
    for index, change in enumerate(task_diff["changes"]):
        _require(
            isinstance(change, dict)
            and set(change) == {"path", "before_value", "after_value"},
            f"task_diff.changes[{index}] fields mismatch",
        )
        _require(
            isinstance(change["path"], str) and bool(change["path"]),
            f"task_diff.changes[{index}].path invalid",
        )
        _require(
            change["before_value"] != change["after_value"],
            f"task_diff.changes[{index}] is not a change",
        )
        change_paths.append(change["path"])
    _require(
        change_paths == task_diff["material_fields"],
        "task-diff material_fields must exactly match ordered change paths",
    )
    for list_key in ["owner_authorization_receipts", "controller_claim_refs"]:
        _require(isinstance(task_diff[list_key], list), f"{list_key} must be a list")
        for index, value in enumerate(task_diff[list_key]):
            _validate_receipt_ref(value, f"task_diff.{list_key}[{index}]")

    if category == "ACTUAL_POLICY_MISS":
        _require(
            body["C"] == "SAT"
            and r_coordinates["R_physical_exists"] == "TRUE"
            and r_coordinates["R_measurable_exists"] == "TRUE"
            and r_coordinates["R_actual"] == "FALSE",
            "actual-policy miss requires C=SAT, physical/measurable TRUE, and actual FALSE",
        )
    if category == "BOUNDED_UNREACHABLE":
        _require(body["C"] == "UNSAT", "bounded unreachable requires C=UNSAT")
        _require(
            r_coordinates["R_physical_exists"] == "FALSE"
            and r_coordinates["R_measurable_exists"] == "FALSE",
            "bounded unreachable requires physical/measurable FALSE",
        )
        _require(
            inventory["search_bound_frozen"],
            "bounded unreachable requires frozen search bound",
        )
        for key in [
            "action_inventory",
            "response_family",
            "observation_kernel",
            "transition_semantics",
        ]:
            _require(
                inventory[key] == "COMPLETE",
                f"bounded unreachable requires COMPLETE {key}",
            )
    if category == "AUTHORIZED_NEW_EPISODE":
        _require(
            body["T"] == "OWNER_AUTHORIZED_NEW_EPISODE"
            and task_diff["classification"] == "OWNER_AUTHORIZED_NEW_EPISODE",
            "authorized new episode requires matching T and task diff",
        )
        _require(
            task_diff["original_task_sha256"]
            != task_diff["result_task_sha256"],
            "authorized new episode requires material task change",
        )
        _require(
            bool(task_diff["material_fields"])
            and bool(task_diff["changes"])
            and bool(task_diff["owner_authorization_receipts"]),
            "authorized new episode requires exact changes and owner receipt",
        )
    if category == "INVALID_SUBSTITUTION":
        _require(
            body["T"] == "CONTROLLER_SUBSTITUTION"
            and task_diff["classification"] == "CONTROLLER_SUBSTITUTION",
            "invalid substitution requires matching T and task diff",
        )
        _require(
            task_diff["original_task_sha256"]
            != task_diff["result_task_sha256"],
            "invalid substitution requires material task change",
        )
        _require(
            not task_diff["owner_authorization_receipts"]
            and bool(task_diff["changes"])
            and bool(task_diff["controller_claim_refs"]),
            "invalid substitution must preserve exact changes, lack owner authorization, and retain controller claim",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-contract",
        action="store_true",
        help="write the reproducible v1 candidate beside v0",
    )
    parser.add_argument(
        "--validate-instance",
        type=Path,
        help="validate one candidate instance",
    )
    args = parser.parse_args()

    built = build_v1_contract(load_json(V0_PATH))
    if args.write_contract:
        V1_PATH.write_text(
            json.dumps(built, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    contract = load_json(V1_PATH) if V1_PATH.exists() else built
    validate_contract(contract)
    if args.validate_instance:
        validate_instance(contract, load_json(args.validate_instance))
    print("PASS: X1 outcome-contract v1 candidate validation")
    print("status=CANDIDATE_NOT_RUN")


if __name__ == "__main__":
    main()
