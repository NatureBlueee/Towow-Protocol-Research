#!/usr/bin/env python3
"""Classify what a synthetic bounded-probe result may change."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def classify(result: dict[str, Any]) -> dict[str, Any]:
    attempt = result["action_attempt"]
    witness = result["buyer_domain_witness"]
    idempotency = result["idempotency"]

    complete_attempt = (
        attempt["status"] == "COMPLETED"
        and attempt["new_execution"] is True
        and len(attempt["executed_query_ids"]) == 3
    )
    matching_witness = (
        witness["status"] == "PRESENT"
        and witness["new_witness"] is True
        and witness["observed_attempt_id"] == attempt["attempt_id"]
        and witness["observed_query_ids"] == attempt["executed_query_ids"]
        and witness["query_output_hashes"]
        == attempt["producer_evidence"]["query_output_hashes"]
        and witness["raw_row_export_count"] == 0
    )

    if attempt["status"] == "BLOCKED_PRE_EXECUTION":
        operation_state = "BLOCKED_BEFORE_OPERATION"
        relation_next_action = "SCOPED_REOPEN_ENVIRONMENT_BINDING"
    elif attempt["status"] == "DEDUPLICATED_REPLAY":
        operation_state = "NO_NEW_EVIDENCE_PRIOR_RECEIPT_ONLY"
        relation_next_action = "READ_AND_REVALIDATE_PRIOR_RECEIPT"
    elif attempt["status"] == "ABORTED_CREDENTIAL_REVOKED":
        operation_state = "NOT_QUALIFIED_CREDENTIAL_REVOKED"
        relation_next_action = "STOP_AND_REQUEST_NEW_DATA_AUTHORIZATION"
    elif complete_attempt and not matching_witness:
        operation_state = "PRODUCER_COMPLETED_BUYER_WITNESS_MISSING"
        relation_next_action = "REPAIR_AUDIT_WITHOUT_REPLAYING_EFFECTS"
    elif complete_attempt and matching_witness:
        operation_state = "QUALIFIED_FOR_FROZEN_SYNTHETIC_PROBE_ONLY"
        relation_next_action = "REQUEST_POST_PROBE_STANCES_ON_EXACT_VERSION"
    else:
        operation_state = "UNKNOWN_INCOMPLETE_EVIDENCE"
        relation_next_action = "STOP_AND_DIAGNOSE"

    qualifies_exact_probe = (
        operation_state == "QUALIFIED_FOR_FROZEN_SYNTHETIC_PROBE_ONLY"
    )
    return {
        "schema_version": "1.0",
        "kind": "SYNTHETIC_PROBE_EVIDENCE_CLASSIFICATION",
        "probe_id": result["probe_id"],
        "scenario_id": result["scenario_id"],
        "operation_qualification": {
            "state": operation_state,
            "qualifies_exact_frozen_probe": qualifies_exact_probe,
            "qualifies_formal_pilot": False,
            "qualifies_other_environment_or_version": False
        },
        "relation_transition": {
            "may_request_post_probe_stances": qualifies_exact_probe,
            "commitment_created": False,
            "formal_data_authorization_created": False,
            "next_action": relation_next_action
        },
        "outcomes": {
            "action_attempt": attempt["status"],
            "effect": "NOT_ESTABLISHED",
            "adoption": "NOT_ESTABLISHED",
            "acceptance": "NOT_ESTABLISHED",
            "settlement": "NOT_ESTABLISHED"
        },
        "effect_gap": [
            "The buyer audit witness establishes bounded query execution and zero raw-row export only.",
            "No buyer-domain evidence shows that at least three conclusions are backlog-worthy.",
            "No buyer work-system state change, business acceptance, or settlement is present."
        ],
        "evidence_boundary": {
            "synthetic_only": True,
            "real_capability": False,
            "real_effect": False,
            "strict_formation": "UNKNOWN"
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    classified = classify(result)
    rendered = json.dumps(
        classified, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
