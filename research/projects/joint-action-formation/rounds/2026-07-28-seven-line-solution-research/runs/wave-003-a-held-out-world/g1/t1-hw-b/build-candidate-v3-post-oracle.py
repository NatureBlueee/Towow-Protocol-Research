#!/usr/bin/env python3
"""Post-oracle representation diagnosis; never a blind candidate.

V2 already contains only disclosures produced by the local controller.  This
script changes no route, fact, recipient, purpose, retention, event id, parent
link, decision, or handoff.  It only applies evaluator conventions that were
not present in the method-visible contract:

- disclosure depth is a one-unit-per-event budget, not a zero-based hop index;
- the OFFER side is serialized as reciprocal requester;
- the scorer's terminal label is RECIPROCAL_COMPLETE.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    candidate = load("candidate-submission-v2.json")
    candidate["method_id"] = (
        "controller-receipts-v3-post-oracle-representation-diagnosis"
    )

    for disclosure in candidate["disclosures"]:
        disclosure["depth"] = 1

    reciprocal = load(
        "candidate-controller/reciprocal-juniper-kite.json"
    )
    controller_outcome = reciprocal["controller_result"]["outcome"]
    disclosures = controller_outcome["disclosures"]
    offer = next(
        item
        for item in disclosures
        if item["projection"]["direction"] == "OFFER"
    )
    seek = next(
        item
        for item in disclosures
        if item["projection"]["direction"] == "SEEK"
    )
    exchange = controller_outcome["reciprocal_exchange"]
    candidate["probes"] = [
        {
            "probe_id": exchange["exchange_id"],
            "requester": offer["from"],
            "responder": seek["from"],
            "requested_fact": seek["projection"]["fact_id"],
            "offered_fact": offer["projection"]["fact_id"],
            "status": "RECIPROCAL_COMPLETE",
            "evidence_refs": ["W-HWB-RECIPROCAL-RECEIPT"],
        }
    ]

    output = ROOT / "candidate-submission-v3-post-oracle.json"
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
