#!/usr/bin/env python3
"""One-time initializer for independent opaque membership and label sources.

The random seed is intentionally not stored.  Normal minisuite builds consume
the resulting canonical sources and never regenerate the row-id/label mapping.
"""

import argparse
import json
import secrets
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MEMBERSHIP = ROOT / "OPAQUE-MEMBERSHIP.candidate.json"
LABELS = ROOT / "CASES-LABELS.candidate.json"
CASE_IDS = (
    "P1_D0_STABLE_EXACT_ATOM",
    "P2_D1_CONDITIONAL_STABLE_EXACT_ATOM",
    "P3_PER_SLOT_FRESH_TOKEN",
    "P4_CONTEXT_COUNT_ONLY",
    "P5_NUMERIC_EXACT_AND_MISSING",
    "P6_XOR_TWO_TOKEN",
    "P7_CONTEXT_TOTAL_OOV",
    "P8_F1_OOV_SELECTOR_ABSENCE",
)


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if (MEMBERSHIP.exists() or LABELS.exists()) and not args.replace:
        parser.error("sources exist; explicit --replace is required")
    seen = set()
    cases = []
    labels = []
    rng = secrets.SystemRandom()
    for case_id in CASE_IDS:
        phases = {}
        for phase in ("calibration", "holdout"):
            row_ids = []
            while len(row_ids) < 40:
                row_id = "o_" + secrets.token_hex(12)
                if row_id not in seen:
                    seen.add(row_id)
                    row_ids.append(row_id)
            row_ids.sort()
            phase_labels = ["R"] * 20 + ["S"] * 20
            rng.shuffle(phase_labels)
            labels.extend(
                {"class_id": class_id, "row_id": row_id}
                for row_id, class_id in zip(row_ids, phase_labels)
            )
            phases[phase] = row_ids
        cases.append({"case_id": case_id, "phases": phases})
    membership = {
        "cases": cases,
        "generation": "ONE_TIME_OS_CSPRNG_IDS_SEED_DISCARDED_NO_SLOT_MAPPING_RETAINED",
        "schema": "WAVE025_C01_OPAQUE_MEMBERSHIP_V3",
    }
    label_doc = {
        "labels": sorted(labels, key=lambda item: item["row_id"]),
        "mapping_boundary": "SYNTHETIC_CONTROLLER_SOURCE_NOT_COPIED_TO_FREEZE_CAPABILITY_ROOT",
        "schema": "WAVE025_C01_SYNTHETIC_LABEL_MAP_V3",
    }
    MEMBERSHIP.write_bytes(canonical_bytes(membership))
    LABELS.write_bytes(canonical_bytes(label_doc))
    print(f"wrote {MEMBERSHIP.name} rows={len(seen)}")
    print(f"wrote {LABELS.name} labels={len(labels)}")


if __name__ == "__main__":
    main()
