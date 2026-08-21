#!/usr/bin/env python3
"""Deterministically build the three canonical candidate release JSON files."""

from __future__ import annotations

import copy
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OLD_SCHEMA = HERE.parent / "COLLECTOR-RECEIPT-V1.candidate.schema.json"


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode()


def write(name: str, value) -> None:
    (HERE / name).write_bytes(canonical(value))


old = json.loads(OLD_SCHEMA.read_text(encoding="utf-8"))
receipt = copy.deepcopy(old)
receipt["$id"] = "https://towow.invalid/schemas/wave025/collector-receipt-v1.1-admission.candidate.schema.json"
receipt["title"] = "Wave 025 collector V1.1 candidate admission shape"
receipt["description"] = (
    "Self-contained candidate schema mechanically derived from the hash-bound V1 schema. "
    "Raw canonical bytes, producer reachability, cross-field semantics and controller seals "
    "remain executable admission layers."
)
receipt["x-towow-profile"] = "WAVE025_COLLECTOR_ADMISSION_V1_1_CANDIDATE"
receipt["x-towow-status"] = "CANDIDATE_NOT_ADOPTED"

sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
digest_binding = {
    "type": "object",
    "additionalProperties": False,
    "required": ["byte_length", "sha256"],
    "properties": {
        "byte_length": {"type": "integer", "minimum": 0, "maximum": 1073741824},
        "sha256": {"$ref": "#/$defs/sha256"},
    },
}
file_binding = copy.deepcopy(digest_binding)
file_binding["required"] = ["relative_path", "byte_length", "sha256"]
file_binding["properties"]["relative_path"] = {
    "type": "string",
    "minLength": 1,
    "maxLength": 512,
    "pattern": r"^(?!/)(?!.*(?:^|/)\.\.(?:/|$))(?!.*\u0000).+$",
}
binding = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://towow.invalid/schemas/wave025/controller-material-preimage-v1.1.candidate.schema.json",
    "title": "Wave 025 controller-sealed material preimage V1.1 candidate",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema", "seal_id", "run_id", "role", "slot_id", "controller_domain",
        "package_manifest", "receipt", "collector_input", "subject_input",
        "launch_environment", "challenge_snapshot", "challenge_root_relative_path",
        "process_snapshot", "execution_evidence"
    ],
    "properties": {
        "schema": {"const": "WAVE025_CONTROLLER_MATERIAL_PREIMAGE_V1_1_CANDIDATE"},
        "seal_id": {"type": "string", "minLength": 1, "maxLength": 256},
        "run_id": {"type": "string", "minLength": 1, "maxLength": 256},
        "role": {"enum": ["D0", "D1", "T"]},
        "slot_id": {"type": "string", "pattern": "^[A-Za-z0-9._-]{1,256}$"},
        "controller_domain": {"const": "EXTERNAL_READ_ONLY_TO_WORKER"},
        "package_manifest": {"$ref": "#/$defs/digestBinding"},
        "receipt": {"$ref": "#/$defs/fileBinding"},
        "collector_input": {"$ref": "#/$defs/collectorInputBinding"},
        "subject_input": {"$ref": "#/$defs/subjectInputBinding"},
        "launch_environment": {"$ref": "#/$defs/fileBinding"},
        "challenge_snapshot": {"$ref": "#/$defs/fileBinding"},
        "challenge_root_relative_path": {"const": "challenge"},
        "process_snapshot": {"oneOf": [{"$ref": "#/$defs/fileBinding"}, {"type": "null"}]},
        "execution_evidence": {"$ref": "#/$defs/fileBinding"},
    },
    "$defs": {
        "sha256": sha,
        "digestBinding": digest_binding,
        "fileBinding": file_binding,
        "collectorInputBinding": {
            "allOf": [
                {"$ref": "#/$defs/fileBinding"},
                {"type": "object", "properties": {"relative_path": {"const": "challenge/collector-input.json"}}},
            ]
        },
        "subjectInputBinding": {
            "allOf": [
                {"$ref": "#/$defs/fileBinding"},
                {"type": "object", "properties": {"relative_path": {"const": "challenge/input.bin"}}},
            ]
        },
    },
}

policy = {
    "schema": "WAVE025_COLLECTOR_ADMISSION_POLICY_V1_1_CANDIDATE",
    "status": "CANDIDATE_NOT_ADOPTED",
    "public_receipt_schema": "WAVE025_LEAK_ONLY_FEATURES_V1",
    "producer_adapter_version": "1.1.0-candidate",
    "g_mode": {
        "external_controller_seal_required": True,
        "process_snapshot_required_when_process_available": True,
        "all_process_tree_hostname_identity_uptime_error_branches": "REJECT",
        "challenge_file_over_65536_bytes": "REJECT",
        "challenge_role_paths": {
            "collector_input": "challenge/collector-input.json",
            "subject_input": "challenge/input.bin"
        },
        "tree_truncation_or_depth_boundary": "REJECT",
        "preallocation_preflight_and_postcollection_stability": "REQUIRED",
        "unverified_machine_codes": "REJECT",
    },
    "raw_admission_order": [
        "runtime_package_manifest_and_historical_hash_verification",
        "bounded_file_read", "strict_utf8", "duplicate_member_rejection",
        "strict_json_number_parse", "recursive_key_sorted_compact_json_plus_one_lf",
        "self_contained_v1_1_schema", "semantic_cross_field_validation",
        "controller_seal_hash", "controller_material_reconstruction"
    ],
    "caps": {
        "environment_rows": 4096, "tree_entries_per_root": 2048,
        "tree_errors": 0, "process_rows": 256, "visible_canary_rows": 65536,
        "visible_canary_scanned_nodes": 2048, "visible_canary_file_bytes": 65536,
        "subject_bytes": 1073741824, "generic_string_code_points": 1048576,
        "proc_directory_entries": 4096, "proc_directory_name_bytes": 1048576,
    },
    "claims_not_closed_by_candidate_alone": [
        "controller seal origin and worker write exclusion",
        "same-permission malicious peer resistance",
        "zero network or lawful API syscalls without independent runtime evidence interpretation",
    ],
}

write("COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json", receipt)
write("EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json", binding)
write("ADMISSION-POLICY-V1.1.candidate.json", policy)
