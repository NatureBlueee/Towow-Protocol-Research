#!/usr/bin/env python3
"""Blocked design sketch for a future HW-B controller-executed revision.

V1 incorrectly promoted holder authorization into execution. V2 copies the
actual disclosure/probe objects returned by the controller and limits
decision/handoff evidence to frozen witness references.

The current workspace has no authoritative controller executor or receipt
issuer, so the referenced candidate-controller files must not be handwritten.
This script intentionally remains non-runnable until such receipts exist.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    required_receipts = [
        ROOT / "candidate-controller/route-helios-direct.json",
        ROOT / "candidate-controller/route-ion-relay.json",
        ROOT / "candidate-controller/reciprocal-juniper-kite.json",
    ]
    if not all(path.exists() for path in required_receipts):
        raise SystemExit(
            "BLOCKED_BY_MISSING_CONTROLLER: authoritative execution "
            "receipts do not exist"
        )
    candidate = load("candidate-submission-v1.json")
    helios = load("candidate-controller/route-helios-direct.json")
    ion = load("candidate-controller/route-ion-relay.json")
    reciprocal = load("candidate-controller/reciprocal-juniper-kite.json")

    candidate["method_id"] = (
        "local-projection-routing-controller-receipts-v2"
    )
    allowed_evidence = {
        "DET-HWB-PUBLIC-COLD-AURORA-BASALT": [
            "W-HWB-COLD-SEEK-V2",
            "W-HWB-COLD-OFFER-V5",
        ],
        "DET-HWB-HIDDEN-GRID-HELIOS-ION": [
            "W-HWB-HELIOS-PROJECTION",
            "W-HWB-ION-PROJECTION",
        ],
        "DET-HWB-RECIP-JUNIPER-KITE": [
            "W-HWB-RECIPROCAL-RECEIPT",
        ],
        "DET-HWB-MOBILE-ECHO-DELTA": [
            "W-HWB-MOBILE-VERSION-FLIP",
        ],
        "DET-HWB-POLICY-FJORD-GLASS": [
            "W-HWB-POLICY-REFUSAL",
        ],
        "DET-HWB-CLAIM-LUMEN-QUIET-NODE": [
            "W-HWB-NO-RESPONSE",
        ],
        "DET-HWB-CLAIM-MESA-SEALED-NODE": [
            "W-HWB-EXPLICIT-REFUSAL",
        ],
        "DET-HWB-CLAIM-CLOSED-ORBITAL-COHORT": [
            "W-HWB-CLOSED-COHORT-V4",
            "W-HWB-CLOSED-NOVA-NEG",
            "W-HWB-CLOSED-ONYX-NEG",
            "W-HWB-CLOSED-PULSE-NEG",
            "W-HWB-CLOSED-QUARTZ-NEG",
        ],
    }
    for decision in candidate["decisions"]:
        decision["evidence_refs"] = allowed_evidence[
            decision["detection_id"]
        ]

    candidate["probes"] = [
        reciprocal["coordinator_visible"]["probe"]
    ]
    candidate["probes"][0]["evidence_refs"] = [
        "W-HWB-RECIPROCAL-RECEIPT"
    ]
    candidate["disclosures"] = (
        helios["coordinator_visible"]["disclosures"]
        + ion["coordinator_visible"]["disclosures"]
        + reciprocal["coordinator_visible"]["disclosures"]
    )

    for handoff in candidate["relation_handoffs"]:
        handoff["evidence_refs"] = allowed_evidence[
            handoff["detection_id"]
        ]

    output = ROOT / "candidate-submission-v2.json"
    output.write_text(
        json.dumps(
            candidate,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
