#!/usr/bin/env python3
"""Deterministic scorer for the T1 hidden-world discovery fixture.

Candidate methods invent their own detection_id values and submit observable
pair or claim signatures. Only this scorer maps those signatures to latent
oracle truth. This module does not implement a discovery method.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_ORACLE = BASE_DIR / "oracle_truth.json"

REQUIREMENT_DESCRIPTIONS = {
    "R1": "Recover an unexpressed opportunity without requiring a prebuilt public card.",
    "R2": "Invalidate stale discovery after the dynamic state flip.",
    "R3": "Use task-relative projections rather than raw or full-world disclosure.",
    "R4": "Respect receiver, purpose, retention, depth, onward, and cumulative disclosure limits.",
    "R5": "Keep UNKNOWN, REFUSE, and ABSENT distinct.",
    "R6": "Report a real but policy-unfindable opportunity honestly.",
    "R7": "Avoid SEEK/SEEK false wakeups and structural misses.",
    "R8": "Handoff discoveries to relation constitution without inventing commitment."
}

ALLOWED_STATES = {
    "DISCOVERED",
    "INVALIDATED",
    "UNFINDABLE_UNDER_POLICY",
    "UNKNOWN",
    "REFUSE",
    "ABSENT"
}

TOP_LEVEL_FIELDS = {
    "schema_version",
    "world_id",
    "evaluation_step",
    "method_id",
    "decisions",
    "probes",
    "disclosures",
    "projection_updates",
    "relation_handoffs"
}

DISCLOSURE_FIELDS = {
    "event_id",
    "origin_party",
    "sender",
    "recipient",
    "fact_id",
    "depth",
    "purpose",
    "retention"
}


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_all_strings(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(_all_strings(item))
        return result
    return []


def validate_submission_structure(submission: Any) -> list[dict[str, str]]:
    """Validate the method-visible contract without consulting oracle truth."""

    errors: list[dict[str, str]] = []

    def error(code: str, path: str, detail: str) -> None:
        errors.append({"code": code, "path": path, "detail": detail})

    if not isinstance(submission, dict):
        return [
            {
                "code": "SUBMISSION_NOT_OBJECT",
                "path": "$",
                "detail": "Submission must be a JSON object."
            }
        ]
    missing = sorted(TOP_LEVEL_FIELDS - set(submission))
    if missing:
        error("TOP_LEVEL_FIELDS_MISSING", "$", ", ".join(missing))
    unexpected_top = sorted(set(submission) - TOP_LEVEL_FIELDS)
    if unexpected_top:
        error("TOP_LEVEL_FIELDS_FORBIDDEN", "$", ", ".join(unexpected_top))
    if submission.get("schema_version") != "1.1":
        error("SCHEMA_VERSION_INVALID", "$.schema_version", "Expected 1.1.")
    if not isinstance(submission.get("method_id"), str) or not submission.get("method_id"):
        error("METHOD_ID_INVALID", "$.method_id", "method_id must be non-empty.")
    if not isinstance(submission.get("evaluation_step"), int):
        error(
            "EVALUATION_STEP_INVALID",
            "$.evaluation_step",
            "evaluation_step must be an integer."
        )
    for field in (
        "decisions",
        "probes",
        "disclosures",
        "projection_updates",
        "relation_handoffs"
    ):
        if not isinstance(submission.get(field), list):
            error("ARRAY_FIELD_INVALID", f"$.{field}", f"{field} must be a list.")

    seen_detection_ids: set[str] = set()
    decisions = submission.get("decisions", [])
    if isinstance(decisions, list):
        for index, decision in enumerate(decisions):
            path = f"$.decisions[{index}]"
            if not isinstance(decision, dict):
                error("DECISION_NOT_OBJECT", path, "Decision must be an object.")
                continue
            detection_id = decision.get("detection_id")
            if not isinstance(detection_id, str) or not detection_id:
                error(
                    "DETECTION_ID_INVALID",
                    f"{path}.detection_id",
                    "detection_id must be a non-empty candidate-owned string."
                )
            elif detection_id in seen_detection_ids:
                error(
                    "DUPLICATE_DETECTION_ID",
                    f"{path}.detection_id",
                    "detection_id must be unique."
                )
            else:
                seen_detection_ids.add(detection_id)
            if decision.get("state") not in ALLOWED_STATES:
                error(
                    "STATE_INVALID",
                    f"{path}.state",
                    "state is outside the method-visible enum."
                )
            if not isinstance(decision.get("evidence_refs"), list):
                error(
                    "EVIDENCE_REFS_INVALID",
                    f"{path}.evidence_refs",
                    "evidence_refs must be a list."
                )
            kind = decision.get("kind")
            if kind == "PAIR":
                allowed_fields = {
                    "detection_id",
                    "kind",
                    "state",
                    "seeker",
                    "provider",
                    "direction",
                    "evidence_refs"
                }
                for field in ("seeker", "provider"):
                    if not isinstance(decision.get(field), str) or not decision.get(field):
                        error(
                            "PAIR_FIELD_INVALID",
                            f"{path}.{field}",
                            f"{field} must be non-empty."
                        )
                if decision.get("direction") != "SEEK_TO_OFFER":
                    error(
                        "PAIR_DIRECTION_INVALID",
                        f"{path}.direction",
                        "PAIR direction must be SEEK_TO_OFFER."
                    )
            elif kind == "CLAIM":
                allowed_fields = {
                    "detection_id",
                    "kind",
                    "state",
                    "claim_key",
                    "subject",
                    "evidence_refs"
                }
                for field in ("claim_key", "subject"):
                    if not isinstance(decision.get(field), str) or not decision.get(field):
                        error(
                            "CLAIM_FIELD_INVALID",
                            f"{path}.{field}",
                            f"{field} must be non-empty."
                        )
            else:
                allowed_fields = {
                    "detection_id",
                    "kind",
                    "state",
                    "evidence_refs"
                }
                error(
                    "DECISION_KIND_INVALID",
                    f"{path}.kind",
                    "kind must be PAIR or CLAIM."
                )
            unexpected_fields = sorted(set(decision) - allowed_fields)
            if unexpected_fields:
                error(
                    "DECISION_FIELDS_FORBIDDEN",
                    path,
                    "Forbidden fields: " + ", ".join(unexpected_fields)
                )

    def scan_for_secret_interface_fields(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in {
                    "item_id",
                    "opportunity_id",
                    "truth_id",
                    "expected_state"
                }:
                    error(
                        "ORACLE_INTERFACE_FIELD_FORBIDDEN",
                        child_path,
                        "Oracle-side identifiers or expected labels are forbidden."
                    )
                scan_for_secret_interface_fields(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan_for_secret_interface_fields(child, f"{path}[{index}]")

    scan_for_secret_interface_fields(submission, "$")

    errors.sort(key=lambda item: (item["code"], item["path"], item["detail"]))
    return errors


def _truth_signature(item: dict[str, Any]) -> tuple[str, ...]:
    if "claim_key" in item:
        return ("CLAIM", item["claim_key"], item["subject"])
    return (
        "PAIR",
        item["seeker"],
        item["provider"],
        item["direction"]
    )


def _decision_signature(decision: dict[str, Any]) -> tuple[str, ...] | None:
    if decision.get("kind") == "CLAIM":
        return (
            "CLAIM",
            decision.get("claim_key", ""),
            decision.get("subject", "")
        )
    if decision.get("kind") == "PAIR":
        return (
            "PAIR",
            decision.get("seeker", ""),
            decision.get("provider", ""),
            decision.get("direction", "")
        )
    return None


def evaluate(
    submission: dict[str, Any], oracle: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Evaluate a candidate-owned receipt against hidden truth."""

    oracle = copy.deepcopy(oracle if oracle is not None else load_json(DEFAULT_ORACLE))
    submission = copy.deepcopy(submission)
    failures: list[dict[str, Any]] = []

    def fail(
        code: str,
        detail: str,
        truth_id: str | None = None,
        detection_id: str | None = None,
        requirements: tuple[str, ...] = ()
    ) -> None:
        failures.append(
            {
                "code": code,
                "truth_id": truth_id,
                "detection_id": detection_id,
                "detail": detail,
                "requirements": list(requirements)
            }
        )

    for structural_error in validate_submission_structure(submission):
        fail(
            structural_error["code"],
            f"{structural_error['path']}: {structural_error['detail']}",
            requirements=tuple(REQUIREMENT_DESCRIPTIONS)
        )

    if submission.get("world_id") != oracle["world_id"]:
        fail(
            "WORLD_ID_MISMATCH",
            "Submission is not bound to the frozen world.",
            requirements=tuple(REQUIREMENT_DESCRIPTIONS)
        )
    if submission.get("evaluation_step") != oracle["freeze"]["S0"]["evaluation_step"]:
        fail(
            "EVALUATION_STEP_MISMATCH",
            "Submission did not evaluate the frozen timeline step.",
            requirements=("R2",)
        )

    decisions = submission.get("decisions", [])
    if not isinstance(decisions, list):
        decisions = []
    valid_decisions = [item for item in decisions if isinstance(item, dict)]
    decision_by_detection_id = {
        item["detection_id"]: item
        for item in valid_decisions
        if isinstance(item.get("detection_id"), str) and item.get("detection_id")
    }

    expected_by_id = {
        item["item_id"]: item for item in oracle["expected_items"]
    }
    truth_by_signature = {
        _truth_signature(item): item for item in oracle["expected_items"]
    }
    witness_ids = {witness["witness_id"] for witness in oracle["witnesses"]}
    mapped_by_truth_id: dict[str, dict[str, Any]] = {}
    truth_id_by_detection_id: dict[str, str] = {}

    for decision in valid_decisions:
        detection_id = decision.get("detection_id")
        signature = _decision_signature(decision)
        expected = truth_by_signature.get(signature) if signature else None
        if expected is None:
            fail(
                "UNEXPECTED_DETECTION",
                "Observable signature does not map to any frozen latent target.",
                detection_id=detection_id,
                requirements=("R7",)
            )
            if decision.get("state") == "DISCOVERED":
                fail(
                    "FALSE_WAKEUP",
                    "An unmatched observable signature was marked DISCOVERED.",
                    detection_id=detection_id,
                    requirements=("R7",)
                )
        else:
            truth_id = expected["item_id"]
            if truth_id in mapped_by_truth_id:
                fail(
                    "DUPLICATE_TRUTH_DETECTION",
                    "Multiple candidate detections map to one latent target.",
                    truth_id,
                    detection_id,
                    ("R7",)
                )
            else:
                mapped_by_truth_id[truth_id] = decision
                if isinstance(detection_id, str):
                    truth_id_by_detection_id[detection_id] = truth_id

    epistemic_ids = {"CLAIM-UNKNOWN", "CLAIM-REFUSE", "CLAIM-ABSENT"}
    discoverable_ids = {
        item["item_id"]
        for item in oracle["expected_items"]
        if item["expected_state"] == "DISCOVERED"
    }
    for expected in oracle["expected_items"]:
        truth_id = expected["item_id"]
        decision = mapped_by_truth_id.get(truth_id)
        if truth_id == "OPP-UNEXPRESSED":
            reqs = ("R1", "R3", "R7")
        elif truth_id == "OPP-DYNAMIC":
            reqs = ("R2", "R7")
        elif truth_id in epistemic_ids:
            reqs = ("R5",)
        elif truth_id == "OPP-POLICY":
            reqs = ("R6",)
        elif truth_id in discoverable_ids:
            reqs = ("R7",)
        else:
            reqs = ()
        if decision is None:
            fail(
                "RECALL_MISS",
                "No candidate-owned detection maps to this latent target.",
                truth_id,
                requirements=reqs
            )
            continue
        detection_id = decision.get("detection_id")
        if decision.get("state") != expected["expected_state"]:
            fail(
                "STATE_MISMATCH",
                (
                    f"Expected {expected['expected_state']}, "
                    f"received {decision.get('state')}."
                ),
                truth_id,
                detection_id,
                reqs
            )
        evidence_refs = decision.get("evidence_refs", [])
        if not isinstance(evidence_refs, list):
            evidence_refs = []
        missing_evidence = sorted(
            set(expected["required_evidence"]) - set(evidence_refs)
        )
        if missing_evidence:
            fail(
                "REQUIRED_EVIDENCE_MISSING",
                f"Missing evidence: {', '.join(missing_evidence)}.",
                truth_id,
                detection_id,
                reqs
            )
        unknown_evidence = sorted(set(evidence_refs) - witness_ids)
        if unknown_evidence:
            fail(
                "UNKNOWN_EVIDENCE",
                f"Unknown evidence: {', '.join(unknown_evidence)}.",
                truth_id,
                detection_id,
                reqs
            )

    party_roles = oracle["party_roles"]
    for decision in valid_decisions:
        if decision.get("state") != "DISCOVERED" or decision.get("kind") != "PAIR":
            continue
        detection_id = decision.get("detection_id")
        seeker = decision.get("seeker")
        provider = decision.get("provider")
        if (
            decision.get("direction") != "SEEK_TO_OFFER"
            or party_roles.get(seeker) != "SEEK"
            or party_roles.get(provider) != "OFFER"
        ):
            fail(
                "DIRECTION_VIOLATION",
                f"DISCOVERED pair {seeker!r}/{provider!r} is not SEEK_TO_OFFER.",
                truth_id_by_detection_id.get(detection_id),
                detection_id,
                ("R7",)
            )

    forbidden_refs = set(oracle["forbidden_fact_refs"])
    for fact_id in sorted(forbidden_refs.intersection(_all_strings(submission))):
        fail(
            "RAW_FACT_EXPOSED",
            f"Forbidden raw fact {fact_id} appears in the submission.",
            detection_id=fact_id,
            requirements=("R3", "R4")
        )

    updates = submission.get("projection_updates", [])
    if not isinstance(updates, list):
        updates = []
    required_update = expected_by_id["OPP-DYNAMIC"]["required_projection_update"]
    if not any(
        isinstance(update, dict)
        and all(update.get(key) == value for key, value in required_update.items())
        for update in updates
    ):
        fail(
            "DYNAMIC_UPDATE_MISSING",
            "The step-1 revocation and version transition are not recorded.",
            "OPP-DYNAMIC",
            requirements=("R2",)
        )

    policies_by_fact = {policy["fact_id"]: policy for policy in oracle["policies"]}
    disclosures = submission.get("disclosures", [])
    if not isinstance(disclosures, list):
        disclosures = []
    disclosure_by_id: dict[str, dict[str, Any]] = {}
    for event in disclosures:
        if not isinstance(event, dict):
            fail(
                "DISCLOSURE_RECORD_INVALID",
                "Each disclosure must be an object.",
                requirements=("R4",)
            )
            continue
        missing_fields = sorted(DISCLOSURE_FIELDS - set(event))
        if missing_fields:
            fail(
                "DISCLOSURE_FIELDS_MISSING",
                f"Missing disclosure fields: {', '.join(missing_fields)}.",
                detection_id=event.get("event_id"),
                requirements=("R4",)
            )
        event_id = event.get("event_id")
        if not event_id:
            continue
        if event_id in disclosure_by_id:
            fail(
                "DUPLICATE_DISCLOSURE_EVENT",
                "Disclosure event IDs must be unique.",
                detection_id=event_id,
                requirements=("R4",)
            )
        else:
            disclosure_by_id[event_id] = event

    aggregate: dict[str, dict[str, Any]] = {}
    for event_id, event in sorted(disclosure_by_id.items()):
        fact_id = event.get("fact_id")
        policy = policies_by_fact.get(fact_id)
        if policy is None:
            fail(
                "DISCLOSURE_POLICY_MISSING",
                f"No frozen policy authorizes fact {fact_id!r}.",
                detection_id=event_id,
                requirements=("R4",)
            )
            continue
        derived_from = event.get("derived_from_event_id")
        if derived_from is None:
            if event.get("sender") != policy["origin_party"]:
                fail(
                    "DISCLOSURE_SENDER_UNAUTHORIZED",
                    "A direct disclosure must be sent by the origin party.",
                    detection_id=event_id,
                    requirements=("R4",)
                )
        else:
            parent = disclosure_by_id.get(derived_from)
            if parent is None:
                fail(
                    "DISCLOSURE_PARENT_MISSING",
                    f"Derived event references missing parent {derived_from}.",
                    detection_id=event_id,
                    requirements=("R4",)
                )
            else:
                if event.get("sender") != parent.get("recipient"):
                    fail(
                        "DISCLOSURE_CHAIN_BROKEN",
                        "Derived disclosure sender must be the parent recipient.",
                        detection_id=event_id,
                        requirements=("R4",)
                    )
                if parent.get("fact_id") != fact_id:
                    fail(
                        "DISCLOSURE_ORIGIN_CHANGED",
                        "A derived disclosure cannot change its origin fact.",
                        detection_id=event_id,
                        requirements=("R4",)
                    )
            if not policy["onward_disclosure"]:
                fail(
                    "ONWARD_DISCLOSURE_FORBIDDEN",
                    f"Policy {policy['policy_id']} forbids onward disclosure.",
                    detection_id=event_id,
                    requirements=("R4",)
                )
        checks = (
            (
                event.get("origin_party") == policy["origin_party"],
                "DISCLOSURE_ORIGIN_MISMATCH",
                "origin_party does not own the disclosed fact."
            ),
            (
                event.get("recipient") in policy["allowed_recipients"],
                "DISCLOSURE_RECIPIENT_FORBIDDEN",
                f"Recipient is not allowed by {policy['policy_id']}."
            ),
            (
                event.get("purpose") == policy["allowed_purpose"],
                "DISCLOSURE_PURPOSE_MISMATCH",
                f"Purpose is not allowed by {policy['policy_id']}."
            ),
            (
                event.get("retention") == policy["retention"],
                "DISCLOSURE_RETENTION_MISMATCH",
                f"Retention is not allowed by {policy['policy_id']}."
            )
        )
        for valid, code, detail in checks:
            if not valid:
                fail(code, detail, detection_id=event_id, requirements=("R4",))
        depth = event.get("depth")
        if not isinstance(depth, int) or isinstance(depth, bool) or depth < 0:
            fail(
                "DISCLOSURE_DEPTH_INVALID",
                "Disclosure depth must be a non-negative integer.",
                detection_id=event_id,
                requirements=("R4",)
            )
            depth = 0
        elif depth > policy["max_depth"]:
            fail(
                "DISCLOSURE_DEPTH_EXCEEDED",
                f"Depth exceeds {policy['policy_id']}.",
                detection_id=event_id,
                requirements=("R4",)
            )
        values = aggregate.setdefault(
            fact_id, {"recipients": set(), "cumulative_depth": 0}
        )
        if event.get("recipient") is not None:
            values["recipients"].add(event["recipient"])
        values["cumulative_depth"] += depth

    for fact_id, values in sorted(aggregate.items()):
        policy = policies_by_fact[fact_id]
        if len(values["recipients"]) > policy["max_unique_recipients"]:
            fail(
                "DISCLOSURE_RECIPIENT_BUDGET_EXCEEDED",
                f"{fact_id} exceeds its unique-recipient budget.",
                detection_id=fact_id,
                requirements=("R4",)
            )
        if values["cumulative_depth"] > policy["max_cumulative_depth"]:
            fail(
                "DISCLOSURE_CUMULATIVE_DEPTH_EXCEEDED",
                f"{fact_id} exceeds its cumulative-depth budget.",
                detection_id=fact_id,
                requirements=("R4",)
            )

    present_facts = {
        event.get("fact_id") for event in disclosures if isinstance(event, dict)
    }
    for fact_id in sorted(
        {
            "F-UNEXP-SEEK-PROJECTION",
            "F-UNEXP-OFFER-PROJECTION"
        }
        - present_facts
    ):
        fail(
            "TASK_PROJECTION_DISCLOSURE_MISSING",
            f"Required task-relative projection {fact_id} is missing.",
            "OPP-UNEXPRESSED",
            requirements=("R1", "R3", "R4")
        )

    probe_expected = oracle["required_reciprocal_probe"]
    probes = submission.get("probes", [])
    if not isinstance(probes, list):
        probes = []
    probe = next(
        (
            item
            for item in probes
            if isinstance(item, dict) and item.get("probe_id") == probe_expected["probe_id"]
        ),
        None
    )
    if probe is None:
        fail(
            "RECIPROCAL_PROBE_MISSING",
            "Required reciprocal probe receipt is missing.",
            "OPP-RECIPROCAL",
            requirements=("R4", "R7")
        )
    else:
        for key in (
            "requester",
            "responder",
            "requested_fact",
            "offered_fact",
            "status"
        ):
            if probe.get(key) != probe_expected[key]:
                fail(
                    "RECIPROCAL_PROBE_MISMATCH",
                    f"Probe field {key} must be {probe_expected[key]}.",
                    "OPP-RECIPROCAL",
                    requirements=("R4", "R7")
                )
        if probe_expected["evidence_ref"] not in probe.get("evidence_refs", []):
            fail(
                "RECIPROCAL_PROBE_EVIDENCE_MISSING",
                "Reciprocal probe completion witness is missing.",
                "OPP-RECIPROCAL",
                requirements=("R4", "R7")
            )
    reciprocal_facts = set(probe_expected["required_disclosure_facts"])
    for fact_id in sorted(reciprocal_facts - present_facts):
        fail(
            "RECIPROCAL_DISCLOSURE_MISSING",
            f"Reciprocal disclosure {fact_id} is missing.",
            "OPP-RECIPROCAL",
            requirements=("R4", "R7")
        )

    handoffs = submission.get("relation_handoffs", [])
    if not isinstance(handoffs, list):
        handoffs = []
    handoff_by_detection_id = {
        item.get("detection_id"): item
        for item in handoffs
        if isinstance(item, dict) and item.get("detection_id")
    }
    for expected in oracle["expected_items"]:
        truth_id = expected["item_id"]
        decision = mapped_by_truth_id.get(truth_id)
        detection_id = decision.get("detection_id") if decision else None
        handoff = handoff_by_detection_id.get(detection_id)
        if expected["requires_relation_handoff"]:
            if handoff is None:
                fail(
                    "RELATION_HANDOFF_MISSING",
                    "Discovered opportunity did not enter relation constitution.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
                continue
            if handoff.get("status") != "CANDIDATE_NOT_COMMITMENT":
                fail(
                    "RELATION_HANDOFF_STATUS_INVALID",
                    "Handoff must remain a non-commitment candidate.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
            if handoff.get("commitment") is True:
                fail(
                    "COMMITMENT_INVENTED",
                    "Discovery cannot create commitment.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
            if (
                handoff.get("seeker") != expected.get("seeker")
                or handoff.get("provider") != expected.get("provider")
            ):
                fail(
                    "RELATION_HANDOFF_PARTIES_MISMATCH",
                    "Handoff parties differ from latent truth.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
            if not handoff.get("open_questions"):
                fail(
                    "RELATION_HANDOFF_OPEN_QUESTIONS_MISSING",
                    "Candidate handoff must preserve unresolved relation questions.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
            if not set(expected["required_evidence"]).issubset(
                handoff.get("evidence_refs", [])
            ):
                fail(
                    "RELATION_HANDOFF_EVIDENCE_MISSING",
                    "Handoff omits required discovery evidence.",
                    truth_id,
                    detection_id,
                    ("R8",)
                )
        elif handoff is not None:
            fail(
                "RELATION_HANDOFF_FORBIDDEN",
                "A non-discoverable item cannot enter relation constitution.",
                truth_id,
                detection_id,
                ("R8",)
            )
    for detection_id in sorted(
        set(handoff_by_detection_id) - set(truth_id_by_detection_id)
    ):
        fail(
            "UNEXPECTED_RELATION_HANDOFF",
            "Handoff references an unmapped detection.",
            detection_id=detection_id,
            requirements=("R8",)
        )

    failures.sort(
        key=lambda item: (
            item["code"],
            item["truth_id"] or "",
            item["detection_id"] or "",
            item["detail"]
        )
    )
    requirement_results: dict[str, dict[str, Any]] = {}
    for requirement_id, description in REQUIREMENT_DESCRIPTIONS.items():
        failure_codes = sorted(
            {
                failure["code"]
                for failure in failures
                if requirement_id in failure["requirements"]
            }
        )
        requirement_results[requirement_id] = {
            "status": "FAIL" if failure_codes else "PASS",
            "failure_codes": failure_codes,
            "description": description
        }

    correct_discovered = sum(
        1
        for truth_id in discoverable_ids
        if mapped_by_truth_id.get(truth_id, {}).get("state") == "DISCOVERED"
    )
    exact_decisions = sum(
        1
        for truth_id, expected in expected_by_id.items()
        if mapped_by_truth_id.get(truth_id, {}).get("state")
        == expected["expected_state"]
    )
    passed_requirements = sum(
        1 for value in requirement_results.values() if value["status"] == "PASS"
    )
    return {
        "schema_version": "1.1",
        "world_id": oracle["world_id"],
        "submission_sha256": canonical_sha256(submission),
        "status": "PASS" if not failures else "FAIL",
        "critical_failures": failures,
        "requirement_results": requirement_results,
        "metrics": {
            "frozen_items": len(expected_by_id),
            "mapped_latent_items": len(mapped_by_truth_id),
            "exact_state_decisions": exact_decisions,
            "discoverable_opportunities": len(discoverable_ids),
            "correctly_discovered_opportunities": correct_discovered,
            "opportunity_recall": (
                correct_discovered / len(discoverable_ids)
                if discoverable_ids
                else 1.0
            ),
            "false_wakeup_count": sum(
                1 for failure in failures if failure["code"] == "FALSE_WAKEUP"
            ),
            "disclosure_event_count": len(disclosure_by_id),
            "unique_recipients_by_origin_fact": {
                fact_id: sorted(values["recipients"])
                for fact_id, values in sorted(aggregate.items())
            }
        },
        "coverage": {
            "requirements_passed": passed_requirements,
            "requirements_total": len(REQUIREMENT_DESCRIPTIONS),
            "ratio": passed_requirements / len(REQUIREMENT_DESCRIPTIONS)
        },
        "evidence_boundary": (
            "This score validates one local synthetic receipt against hidden frozen "
            "truth. The calibration fixture is not a candidate result."
        )
    }


def apply_mutation(
    document: dict[str, Any], mutation: dict[str, Any]
) -> dict[str, Any]:
    """Apply one named scorer mutation; never generates candidate detections."""

    result = copy.deepcopy(document)
    for action in mutation.get("actions", []):
        action_name = action["action"]
        if action_name == "SET_DECISION_STATE":
            target = next(
                decision
                for decision in result["decisions"]
                if decision["detection_id"] == action["detection_id"]
            )
            target["state"] = action["state"]
        elif action_name == "REMOVE_PROJECTION_UPDATE":
            result["projection_updates"] = [
                update
                for update in result.get("projection_updates", [])
                if update.get("party") != action["party"]
            ]
        elif action_name == "APPEND_DECISION":
            result.setdefault("decisions", []).append(copy.deepcopy(action["value"]))
        elif action_name == "APPEND_DISCLOSURE":
            result.setdefault("disclosures", []).append(copy.deepcopy(action["value"]))
        elif action_name == "REMOVE_RELATION_HANDOFF":
            result["relation_handoffs"] = [
                handoff
                for handoff in result.get("relation_handoffs", [])
                if handoff.get("detection_id") != action["detection_id"]
            ]
        else:
            raise ValueError(f"Unknown mutation action: {action_name}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", required=True, type=Path)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(load_json(args.submission), load_json(args.oracle))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
