#!/usr/bin/env python3
"""Build a conservative T4 candidate from controller-mediated disclosures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--evaluator-hash", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = load_json(args.summary)

    successful: dict[tuple[str, str], dict[str, Any]] = {}
    for result in summary["results"]:
        if result["decision"] == "DISCLOSE":
            receipt = result["receipt"]
            successful[(receipt["authority_id"], receipt["request_type"])] = result

    def fact(authority: str, request_type: str) -> dict[str, Any]:
        return successful[(authority, request_type)]["disclosed_fields"]

    def receipt(authority: str, request_type: str) -> dict[str, Any]:
        return successful[(authority, request_type)]["receipt"]

    current = fact("CITY-PROCUREMENT", "REQUEST_CURRENT_TENDER_VERSION")
    budget = fact("CITY-PROCUREMENT", "REQUEST_BUDGET_RULE")
    prime_price = fact("PRIME-BID", "REQUEST_PRIME_PRICE_BOUND")
    field_price = fact("FIELD-COMMERCIAL", "REQUEST_FIELD_PRICE_BOUND")
    audit_price = fact("ASSURE-COMMERCIAL", "REQUEST_AUDIT_PRICE_BOUND")
    total_price = (
        prime_price["fixed_price"]
        + field_price["fixed_price"]
        + audit_price["fixed_price"]
    )
    probe = fact("PRIME-TECH", "RUN_INTEROP_PROBE")
    prime_sign = fact("PRIME-BID", "REQUEST_PRIME_SIGNING_STANCE")
    field_sign = fact(
        "FIELD-COMMERCIAL", "REQUEST_FIELD_SIGNING_STANCE"
    )
    audit_sign = fact(
        "ASSURE-COMMERCIAL", "REQUEST_AUDIT_SIGNING_STANCE"
    )
    target_readback = fact(
        "CITY-PROCUREMENT", "REQUEST_TARGET_READBACK_RULE"
    )
    outcome_rules = fact(
        "CITY-PROCUREMENT", "REQUEST_SUBMISSION_EVIDENCE_RULE"
    )
    adoption_acceptance = fact(
        "CITY-PROCUREMENT",
        "REQUEST_ADOPTION_ACCEPTANCE_SEPARATION",
    )
    reservations = [
        (
            "PRIME-BID",
            "RESERVE_PRIME_STAFF",
            fact("PRIME-BID", "RESERVE_PRIME_STAFF"),
        ),
        (
            "FIELD-COMMERCIAL",
            "RESERVE_FIELD_CAPACITY",
            fact("FIELD-COMMERCIAL", "RESERVE_FIELD_CAPACITY"),
        ),
        (
            "ASSURE-COMMERCIAL",
            "RESERVE_AUDIT_SLOT",
            fact("ASSURE-COMMERCIAL", "RESERVE_AUDIT_SLOT"),
        ),
    ]

    query_receipts = []
    for raw in summary["receipts"]:
        query_receipts.append(
            {
                key: raw[key]
                for key in (
                    "request_id",
                    "receipt_id",
                    "receipt_hash",
                    "authority_id",
                    "request_type",
                    "purpose",
                    "relation_version_ref",
                    "response_type",
                    "disclosed_fields",
                    "retention_scope",
                )
            }
        )

    submission = {
        "schema_version": "1.0",
        "task_id": summary["task_id"],
        "method_id": summary["method_id"],
        "run_id": summary["run_id"],
        "input_hash": summary["blind_input_hash"],
        "evaluator_hash": args.evaluator_hash,
        "controller_history_hash": summary["controller_history_hash"],
        "method_components": [
            "deterministic authority-interface discovery",
            "existing workflow/state-machine composition",
            "controller-mediated IAM/policy disclosure receipts",
            "bounded interoperability probe before commitment",
            "authoritative outcome readback plan",
        ],
        "queries_and_disclosures": query_receipts,
        "task_reconstruction": {
            "current_tender_version": current["current_tender_version"],
            "material_addendum_id": current["material_addendum_id"],
            "raw_data_boundary": current["raw_data_boundary"],
            "approved_external_projection": current[
                "approved_external_projection"
            ],
            "site_count": 12,
            "minimum_offline_capture_hours": 24,
            "deadline": budget["deadline"],
            "total_price_cny": total_price,
            "budget_ceiling_cny": budget["ceiling"],
            "within_budget": total_price <= budget["ceiling"],
            "principals": ["PRIME", "FIELD", "ASSURE"],
            "candidate_value": (
                "12-site offline capture, deferred synchronization and "
                "independent verification under the current city data boundary"
            ),
        },
        "relation_versions": [
            {
                "relation_version": summary["relation_version_ref"],
                "tender_version": current["current_tender_version"],
                "addendum": current["material_addendum_id"],
                "participants": ["PRIME", "FIELD", "ASSURE"],
                "state": "CANDIDATE_NOT_COMMITMENT",
                "current_assessment": (
                    "ALL_DISCLOSED_CONDITIONS_SATISFIED; FINAL_SIGNATURES "
                    "AND REAL_SUBMISSION_NOT_OCCURRED"
                ),
                "total_price_cny": total_price,
                "probe_receipt": receipt(
                    "PRIME-TECH", "RUN_INTEROP_PROBE"
                )["receipt_id"],
                "reservation_receipts": [
                    receipt(authority, request_type)["receipt_id"]
                    for authority, request_type, _ in reservations
                ],
            }
        ],
        "capability_qualifications": [
            {
                "operation": probe["operation_id"],
                "executor": "PRIME-TECH_WITH_FIELD_INTERFACE",
                "environment": probe["environment"],
                "version": {
                    "prime": probe["prime_version"],
                    "field": probe["field_version"],
                    "tender": current["current_tender_version"],
                },
                "permission": (
                    "CONTROLLER_AUTHORIZED_SYNTHETIC_BOUNDED_PROBE_ONLY"
                ),
                "resource": "12_SITE_OPERATION",
                "recovery": fact(
                    "PRIME-TECH", "REQUEST_FAILURE_RECOVERY"
                ),
                "status": (
                    "QUALIFIED_EXACT_SYNTHETIC_OPERATION_NOT_GENERAL_CAPABILITY"
                ),
                "evidence_available_at_claim_time": {
                    "receipt_id": receipt(
                        "PRIME-TECH", "RUN_INTEROP_PROBE"
                    )["receipt_id"],
                    "receipt_hash": receipt(
                        "PRIME-TECH", "RUN_INTEROP_PROBE"
                    )["receipt_hash"],
                    "observed": probe,
                },
                "asserted_before_commitment": True,
            }
        ],
        "authority_state": [
            {
                "authority": "CITY-PROCUREMENT",
                "scope": "tender, budget and outcome witness semantics",
                "current_tender": current,
                "budget": budget,
                "submission_evidence_rule": outcome_rules,
                "adoption_acceptance": adoption_acceptance,
                "target_readback": target_readback,
            },
            {
                "authority": "PRIME-BID",
                "stance": prime_sign,
                "price": prime_price,
                "liability": fact(
                    "PRIME-BID", "REQUEST_LIABILITY_BOUNDARY"
                ),
                "final_signature_occurred": False,
            },
            {
                "authority": "FIELD-COMMERCIAL",
                "stance": field_sign,
                "price": field_price,
                "risk": fact("FIELD-OPS", "REQUEST_DEPLOYMENT_RISK"),
                "final_signature_occurred": False,
            },
            {
                "authority": "ASSURE-COMMERCIAL",
                "stance": audit_sign,
                "price": audit_price,
                "independence": fact(
                    "ASSURE-AUDIT", "REQUEST_INDEPENDENCE_BOUNDARY"
                ),
                "final_signature_occurred": False,
            },
        ],
        "reservations": [
            {
                "authority": authority,
                "request_type": request_type,
                "status": "ACTIVE_SYNTHETIC_RESERVATION",
                "relation_version": summary["relation_version_ref"],
                "receipt_id": receipt(authority, request_type)["receipt_id"],
                **details,
            }
            for authority, request_type, details in reservations
        ],
        "workflow": {
            "method_family": (
                "authority-aware deterministic broker using existing "
                "workflow, policy and receipt primitives"
            ),
            "phase_order": [
                "bind current tender and value floor",
                "collect minimal price, capability, risk and authority bounds",
                "run exact scoped interoperability probe",
                "reserve scarce resources against one relation version",
                "verify budget and all conditional stances",
                "request final signatures",
                "submit exact frozen bytes",
                "separately wait for eligibility, adoption, acceptance and effect",
            ],
            "candidate_ready_to_request_final_signatures": True,
            "commitment_created": False,
            "real_submission_executed": False,
        },
        "outcomes": {
            "submission": {
                "state": "NOT_OCCURRED",
                "required_witness": outcome_rules[
                    "portal_receipt_proves"
                ],
            },
            "receipt_or_eligibility": {
                "state": "NOT_OCCURRED",
                "required_witness": outcome_rules[
                    "eligibility_receipt_proves"
                ],
            },
            "adoption": {
                "state": "NOT_OCCURRED",
                "required_witness": adoption_acceptance["adoption_witness"],
            },
            "acceptance": {
                "state": "NOT_OCCURRED",
                "required_witness": adoption_acceptance[
                    "acceptance_witness"
                ],
            },
            "action_attempt": {
                "state": "SYNTHETIC_INTEROP_PROBE_OCCURRED",
                "does_not_mean": [
                    "REAL_BID_SUBMISSION",
                    "PRODUCTION_EXECUTION",
                    "CITY_EFFECT",
                ],
            },
            "effect": {
                "state": "NOT_OCCURRED",
                "readback_authority": target_readback[
                    "readback_authority"
                ],
                "required_fields": target_readback["required_fields"],
            },
            "settlement": {
                "state": "NOT_OCCURRED",
                "required_witness": "SIGNED_SETTLEMENT_BY_RELEVANT_AUTHORITIES",
            },
        },
        "reopen_plan": {
            "rules": [
                {
                    "trigger": "tender or material addendum changes",
                    "invalidate": [
                        "task reconstruction",
                        "all conditional stances",
                        "probe if affected fields change",
                    ],
                    "preserve": ["historical receipts"],
                },
                {
                    "trigger": "PRIME or FIELD technical version changes",
                    "invalidate": ["interop qualification", "dependent stances"],
                    "preserve": [
                        "unaffected price bounds if still within validity"
                    ],
                },
                {
                    "trigger": "reservation revoked or TTL expires",
                    "invalidate": [
                        "that reservation",
                        "dependent signing readiness",
                    ],
                    "preserve": ["unaffected authority facts and probe"],
                },
                {
                    "trigger": "ASSURE conflict appears",
                    "invalidate": [
                        "independence stance",
                        "audit reservation",
                        "acceptance witness plan",
                    ],
                    "preserve": ["PRIME and FIELD evidence"],
                },
            ],
            "replay_rule": (
                "same query and same run reuses receipt; it does not create "
                "a second disclosure or reservation"
            ),
        },
        "migration_plan": {
            "invariants": [
                "discover authority interfaces from the current task",
                "qualify exact operation before commitment",
                "bind reservations to one version",
                "keep submission, adoption, acceptance and effect separate",
            ],
            "domain_specific_fields_to_rediscover": [
                "participants",
                "current target version",
                "operation",
                "environment",
                "price and capacity",
                "target-domain readback authority and fields",
            ],
            "hardcoded_current_entities_are_not_reused": True,
            "migration_claim": "PLAN_ONLY_NOT_RUN",
        },
        "unknowns": [
            "whether all three principals will issue final signatures",
            "whether exact bid bytes will be submitted before D+5",
            "whether the city will find the bid eligible, adopt or accept it",
            "whether production deployment will create the target-domain effect",
            "whether settlement will occur",
            "whether the method passes the hidden cross-industry migration run",
        ],
        "refusals": [],
        "cannot_support": [
            "A real bid was submitted.",
            "The city adopted or accepted the candidate.",
            "The synthetic probe proves general production capability.",
            "The target-domain effect occurred.",
            "Settlement occurred.",
            "This method is better than all strong-center or standards-only alternatives.",
        ],
    }
    write_json(args.output, submission)


if __name__ == "__main__":
    main()
