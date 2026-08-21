#!/usr/bin/env python3
"""Build the canonical non-self-referential runtime package manifest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNTIME_FILES = [
    "ADMISSION-POLICY-V1.1.candidate.json",
    "COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json",
    "EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json",
    "admit_receipt_v1_1.py",
    "producer-v1.1.candidate.js",
    "raw-canonical-check.candidate.js",
]
HISTORICAL_FILES = [
    "../../attackers/leak-only-collector/collector.js",
    "../COLLECTOR-RECEIPT-V1.candidate.schema.json",
]


def row(relative: str) -> dict:
    raw = (HERE / relative).resolve().read_bytes()
    return {"path": relative, "byte_length": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


value = {
    "schema": "WAVE025_COLLECTOR_ADMISSION_PACKAGE_MANIFEST_V1_1_CANDIDATE",
    "status": "CANDIDATE_NOT_ADOPTED",
    "files": [row(name) for name in RUNTIME_FILES],
    "historical_inputs": [row(name) for name in HISTORICAL_FILES],
}
(HERE / "PACKAGE-MANIFEST.candidate.json").write_bytes(
    (json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n").encode()
)
