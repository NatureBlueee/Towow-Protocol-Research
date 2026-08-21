#!/usr/bin/env python3
"""Deterministic hidden-world scorer for T1-HW-C.

This evaluator never generates or repairs a candidate. Output identifies
candidate-owned detections and hashed truth signatures, not oracle item IDs.
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

REQUIREMENTS = {
    "R1": "Recover unexpressed task-relative opportunities.",
    "R2": "Invalidate stale candidates after dynamic change.",
    "R3": "Respect projections, route, purpose, retention, and depth.",
    "R4": "Bind execution to controller receipt, all ACKs, and external anchor.",
    "R5": "Keep UNKNOWN, REFUSE, and ABSENT distinct.",
    "R6": "Represent a real policy-unfindable opportunity honestly.",
    "R7": "Reject compatibility, direction, version, and reciprocal decoys.",
    "R8": "Handoff without inventing commitment or authority.",
}
ALLOWED_STATES = {
    "DISCOVERED",
    "INVALIDATED",
    "UNFINDABLE_UNDER_POLICY",
    "UNKNOWN",
    "REFUSE",
    "ABSENT",
}
TOP_FIELDS = {
    "schema_version",
    "world_id",
    "evaluation_step",
    "method_id",
    "decisions",
    "projection_updates",
    "execution_proofs",
    "relation_handoffs",
}
PAIR_FIELDS = {
    "detection_id",
    "kind",
    "state",
    "seeker",
    "provider",
    "direction",
    "evidence_refs",
}
CLAIM_FIELDS = {
    "detection_id",
    "kind",
    "state",
    "claim_key",
    "subject",
    "evidence_refs",
}
UPDATE_FIELDS = {
    "party",
    "invalidated_signature",
    "from_version",
    "to_version",
    "step",
    "current_direction",
    "evidence_ref",
}
PROOF_FIELDS = {
    "action_id",
    "detection_id",
    "action_kind",
    "status",
    "action_digest",
    "idempotency_key",
    "delivery_events",
    "controller_receipt_ref",
    "recipient_ack_refs",
    "external_anchor_ref",
}
DELIVERY_FIELDS = {
    "event_ref",
    "origin_party",
    "sender",
    "recipient",
    "fact_id",
    "depth",
    "purpose",
    "retention",
}
HANDOFF_FIELDS = {
    "detection_id",
    "status",
    "commitment",
    "authority_inferred",
    "evidence_refs",
    "open_questions",
}
FORBIDDEN_INTERFACE_FIELDS = {
    "item_id",
    "truth_id",
    "expected_state",
    "target_item_id",
    "oracle_id",
}


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON top level must be an object")
    return value


def canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(_nonempty(item) for item in value)
        and len(set(value)) == len(value)
    )


def _signature(value: dict[str, Any]) -> tuple[str, ...]:
    if value.get("kind") == "CLAIM" or "claim_key" in value:
        return (
            "CLAIM",
            str(value.get("claim_key", "")),
            str(value.get("subject", "")),
        )
    return (
        "PAIR",
        str(value.get("seeker", "")),
        str(value.get("provider", "")),
        str(value.get("direction", "")),
    )


def _target_digest(item: dict[str, Any]) -> str:
    return canonical_sha256(_signature(item))


def validate_submission_structure(submission: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    def error(code: str, path: str, detail: str) -> None:
        errors.append({"code": code, "path": path, "detail": detail})

    def exact(
        value: dict[str, Any],
        expected: set[str],
        path: str,
    ) -> None:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        if missing:
            error("FIELDS_MISSING", path, ", ".join(missing))
        if extra:
            error("FIELDS_FORBIDDEN", path, ", ".join(extra))

    if not isinstance(submission, dict):
        return [{
            "code": "SUBMISSION_NOT_OBJECT",
            "path": "$",
            "detail": "Submission must be an object.",
        }]
    exact(submission, TOP_FIELDS, "$")
    if submission.get("schema_version") != "2.0":
        error("SCHEMA_VERSION_INVALID", "$.schema_version", "Expected 2.0.")
    if not _nonempty(submission.get("world_id")):
        error("WORLD_ID_INVALID", "$.world_id", "Expected non-empty string.")
    if not isinstance(submission.get("evaluation_step"), int):
        error("EVALUATION_STEP_INVALID", "$.evaluation_step", "Expected integer.")
    if not _nonempty(submission.get("method_id")):
        error("METHOD_ID_INVALID", "$.method_id", "Expected non-empty string.")
    for field in (
        "decisions",
        "projection_updates",
        "execution_proofs",
        "relation_handoffs",
    ):
        if not isinstance(submission.get(field), list):
            error("ARRAY_FIELD_INVALID", f"$.{field}", "Expected array.")

    detection_ids: set[str] = set()
    for index, decision in enumerate(submission.get("decisions", [])):
        path = f"$.decisions[{index}]"
        if not isinstance(decision, dict):
            error("DECISION_NOT_OBJECT", path, "Expected object.")
            continue
        fields = PAIR_FIELDS if decision.get("kind") == "PAIR" else CLAIM_FIELDS
        exact(decision, fields, path)
        detection_id = decision.get("detection_id")
        if not _nonempty(detection_id):
            error("DETECTION_ID_INVALID", f"{path}.detection_id", "Expected ID.")
        elif detection_id in detection_ids:
            error("DUPLICATE_DETECTION_ID", f"{path}.detection_id", detection_id)
        else:
            detection_ids.add(detection_id)
        if decision.get("kind") not in {"PAIR", "CLAIM"}:
            error("DECISION_KIND_INVALID", f"{path}.kind", "Expected PAIR or CLAIM.")
        if decision.get("state") not in ALLOWED_STATES:
            error("STATE_INVALID", f"{path}.state", "Unknown state.")
        if not _string_list(decision.get("evidence_refs")):
            error("EVIDENCE_REFS_INVALID", f"{path}.evidence_refs", "Expected unique strings.")
        if decision.get("kind") == "PAIR":
            if decision.get("direction") != "SEEK_TO_OFFER":
                error("PAIR_DIRECTION_INVALID", f"{path}.direction", "Expected SEEK_TO_OFFER.")
            for field in ("seeker", "provider"):
                if not _nonempty(decision.get(field)):
                    error("PAIR_FIELD_INVALID", f"{path}.{field}", "Expected string.")
        else:
            for field in ("claim_key", "subject"):
                if not _nonempty(decision.get(field)):
                    error("CLAIM_FIELD_INVALID", f"{path}.{field}", "Expected string.")

    for index, update in enumerate(submission.get("projection_updates", [])):
        path = f"$.projection_updates[{index}]"
        if not isinstance(update, dict):
            error("UPDATE_NOT_OBJECT", path, "Expected object.")
            continue
        exact(update, UPDATE_FIELDS, path)
        if update.get("current_direction") not in {"SEEK", "OFFER"}:
            error("UPDATE_DIRECTION_INVALID", f"{path}.current_direction", "Invalid direction.")

    action_ids: set[str] = set()
    for index, proof in enumerate(submission.get("execution_proofs", [])):
        path = f"$.execution_proofs[{index}]"
        if not isinstance(proof, dict):
            error("EXECUTION_PROOF_NOT_OBJECT", path, "Expected object.")
            continue
        exact(proof, PROOF_FIELDS, path)
        action_id = proof.get("action_id")
        if not _nonempty(action_id):
            error("ACTION_ID_INVALID", f"{path}.action_id", "Expected ID.")
        elif action_id in action_ids:
            error("DUPLICATE_ACTION_ID", f"{path}.action_id", action_id)
        else:
            action_ids.add(action_id)
        if proof.get("action_kind") not in {"DERIVED_ONWARD", "RECIPROCAL_EXCHANGE"}:
            error("ACTION_KIND_INVALID", f"{path}.action_kind", "Invalid action kind.")
        if proof.get("status") not in {
            "EXECUTED_VERIFIED",
            "EXECUTION_REJECTED",
            "EXECUTION_NOT_REQUESTED",
        }:
            error("EXECUTION_STATUS_INVALID", f"{path}.status", "Invalid status.")
        digest = proof.get("action_digest")
        if not (
            isinstance(digest, str)
            and len(digest) == 64
            and all(char in "0123456789abcdef" for char in digest)
        ):
            error("ACTION_DIGEST_INVALID", f"{path}.action_digest", "Expected SHA-256 hex.")
        if not _string_list(proof.get("recipient_ack_refs")):
            error("ACK_REFS_INVALID", f"{path}.recipient_ack_refs", "Expected unique strings.")
        deliveries = proof.get("delivery_events")
        if not isinstance(deliveries, list) or not deliveries:
            error("DELIVERY_EVENTS_INVALID", f"{path}.delivery_events", "Expected non-empty array.")
            continue
        event_refs: set[str] = set()
        for event_index, event in enumerate(deliveries):
            event_path = f"{path}.delivery_events[{event_index}]"
            if not isinstance(event, dict):
                error("DELIVERY_EVENT_NOT_OBJECT", event_path, "Expected object.")
                continue
            exact(event, DELIVERY_FIELDS, event_path)
            event_ref = event.get("event_ref")
            if not _nonempty(event_ref):
                error("DELIVERY_EVENT_REF_INVALID", f"{event_path}.event_ref", "Expected ID.")
            elif event_ref in event_refs:
                error("DUPLICATE_DELIVERY_EVENT", f"{event_path}.event_ref", event_ref)
            else:
                event_refs.add(event_ref)
            if not isinstance(event.get("depth"), int) or event.get("depth", -1) < 0:
                error("DISCLOSURE_DEPTH_INVALID", f"{event_path}.depth", "Expected nonnegative integer.")

    for index, handoff in enumerate(submission.get("relation_handoffs", [])):
        path = f"$.relation_handoffs[{index}]"
        if not isinstance(handoff, dict):
            error("HANDOFF_NOT_OBJECT", path, "Expected object.")
            continue
        exact(handoff, HANDOFF_FIELDS, path)
        if handoff.get("status") != "CANDIDATE_NOT_COMMITMENT":
            error("HANDOFF_STATUS_INVALID", f"{path}.status", "Invalid status.")
        if handoff.get("commitment") is not False:
            error("COMMITMENT_INVENTED", f"{path}.commitment", "Must be false.")
        if handoff.get("authority_inferred") is not False:
            error("AUTHORITY_INVENTED", f"{path}.authority_inferred", "Must be false.")
        if not _string_list(handoff.get("evidence_refs")):
            error("EVIDENCE_REFS_INVALID", f"{path}.evidence_refs", "Expected unique strings.")
        if not _string_list(handoff.get("open_questions")):
            error("OPEN_QUESTIONS_INVALID", f"{path}.open_questions", "Expected non-empty unique strings.")

    def scan(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in FORBIDDEN_INTERFACE_FIELDS:
                    error(
                        "ORACLE_INTERFACE_FIELD_FORBIDDEN",
                        child_path,
                        "Secret-side field is forbidden.",
                    )
                scan(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")
        elif isinstance(value, str) and value.startswith("RAW-HWC-"):
            error("RAW_FACT_EXPOSED", path, "Raw local facts are forbidden.")

    scan(submission, "$")
    return sorted(errors, key=lambda row: (row["code"], row["path"], row["detail"]))


def _sorted_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(copy.deepcopy(events), key=lambda row: str(row.get("event_ref", "")))


def evaluate(
    submission: dict[str, Any],
    oracle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    oracle = copy.deepcopy(oracle if oracle is not None else load_json(DEFAULT_ORACLE))
    submission = copy.deepcopy(submission)
    failures: list[dict[str, Any]] = []

    def fail(
        code: str,
        detail: str,
        *,
        target: dict[str, Any] | None = None,
        detection_id: str | None = None,
        requirements: tuple[str, ...] | list[str] = (),
    ) -> None:
        failures.append({
            "code": code,
            "target_signature_sha256": _target_digest(target) if target else None,
            "detection_id": detection_id,
            "detail": detail,
            "requirements": sorted(set(requirements)),
        })

    for structural in validate_submission_structure(submission):
        mapped_requirements = tuple(REQUIREMENTS)
        if structural["code"] in {"DISCLOSURE_DEPTH_INVALID", "RAW_FACT_EXPOSED"}:
            mapped_requirements = ("R3",)
        elif structural["code"] in {
            "COMMITMENT_INVENTED",
            "AUTHORITY_INVENTED",
            "HANDOFF_STATUS_INVALID",
        }:
            mapped_requirements = ("R8",)
        fail(
            structural["code"],
            f"{structural['path']}: {structural['detail']}",
            requirements=mapped_requirements,
        )

    if submission.get("world_id") != oracle["world_id"]:
        fail("WORLD_ID_MISMATCH", "Submission is not bound to the frozen world.", requirements=tuple(REQUIREMENTS))
    if submission.get("evaluation_step") != oracle["freeze"]["evaluation_step"]:
        fail("EVALUATION_STEP_MISMATCH", "Submission did not evaluate the frozen step.", requirements=("R2", "R4", "R7"))

    decisions = [
        row for row in submission.get("decisions", []) if isinstance(row, dict)
    ]
    decision_by_id = {
        row["detection_id"]: row
        for row in decisions
        if _nonempty(row.get("detection_id"))
    }
    truth_by_signature = {
        _signature(item): item for item in oracle["expected_items"]
    }
    mapped: dict[str, dict[str, Any]] = {}
    truth_by_detection: dict[str, dict[str, Any]] = {}

    forbidden = {
        (
            "PAIR",
            row["seeker"],
            row["provider"],
            row["direction"],
        ): row
        for row in oracle["forbidden_pairs"]
    }
    false_wakeup_count = 0
    for decision in decisions:
        signature = _signature(decision)
        truth = truth_by_signature.get(signature)
        detection_id = decision.get("detection_id")
        if truth is None:
            fail(
                "UNEXPECTED_DETECTION",
                "Candidate signature is not an expected truth signature.",
                detection_id=detection_id,
                requirements=("R7",),
            )
            if decision.get("state") == "DISCOVERED":
                false_wakeup_count += 1
                fail(
                    "FALSE_WAKEUP",
                    "Unexpected signature was promoted to DISCOVERED.",
                    detection_id=detection_id,
                    requirements=("R7",),
                )
            if signature in forbidden:
                reason = forbidden[signature]["reason"]
                code = (
                    "VERSION_DECOY_WAKEUP"
                    if "version" in reason
                    else "ORIENTATION_VIOLATION"
                )
                fail(code, reason, detection_id=detection_id, requirements=("R7",))
            continue
        item_id = truth["item_id"]
        if item_id in mapped:
            fail(
                "DUPLICATE_TRUTH_MAPPING",
                "Multiple detections map to the same truth signature.",
                target=truth,
                detection_id=detection_id,
                requirements=truth["requirements"],
            )
            continue
        mapped[item_id] = decision
        if _nonempty(detection_id):
            truth_by_detection[detection_id] = truth
        if decision.get("state") != truth["expected_state"]:
            fail(
                "STATE_MISMATCH",
                f"Expected {truth['expected_state']}; received {decision.get('state')}.",
                target=truth,
                detection_id=detection_id,
                requirements=truth["requirements"],
            )
        evidence = set(decision.get("evidence_refs", []))
        missing_evidence = sorted(set(truth["required_evidence_refs"]) - evidence)
        if missing_evidence:
            fail(
                "EVIDENCE_MISSING",
                f"Missing {len(missing_evidence)} required method-visible witness(es).",
                target=truth,
                detection_id=detection_id,
                requirements=truth["requirements"],
            )

    for truth in oracle["expected_items"]:
        if truth["item_id"] not in mapped:
            fail(
                "MISSING_DETECTION",
                "No candidate decision maps to this truth signature.",
                target=truth,
                requirements=truth["requirements"],
            )

    updates = [
        row for row in submission.get("projection_updates", []) if isinstance(row, dict)
    ]
    if oracle["expected_update"] not in updates:
        dynamic_truth = next(
            row for row in oracle["expected_items"] if row["item_id"] == "HWC-O-02"
        )
        fail(
            "DYNAMIC_UPDATE_MISSING",
            "Frozen version/direction invalidation was not carried into the submission.",
            target=dynamic_truth,
            detection_id=mapped.get("HWC-O-02", {}).get("detection_id"),
            requirements=("R2", "R7"),
        )

    expected_actions = {
        row["action_id"]: row for row in oracle["execution_actions"]
    }
    proofs = [
        row for row in submission.get("execution_proofs", []) if isinstance(row, dict)
    ]
    proof_by_action = {
        row["action_id"]: row
        for row in proofs
        if _nonempty(row.get("action_id"))
    }
    trusted = oracle["trusted_execution_evidence"]
    seen_keys: dict[str, str] = {}

    for proof in proofs:
        key = proof.get("idempotency_key")
        action_id = proof.get("action_id")
        if _nonempty(key):
            previous = seen_keys.get(key)
            if previous is not None and previous != action_id:
                fail(
                    "IDEMPOTENCY_REPLAY_CONFLICT",
                    "One idempotency key was reused for a different action.",
                    detection_id=proof.get("detection_id"),
                    requirements=("R4",),
                )
            seen_keys[key] = str(action_id)
        expected = expected_actions.get(str(action_id))
        if expected is None:
            fail(
                "UNEXPECTED_EXECUTION_PROOF",
                "Execution proof does not name a frozen expected action.",
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
            continue
        truth = next(
            row
            for row in oracle["expected_items"]
            if row["item_id"] == expected["target_item_id"]
        )
        decision = mapped.get(truth["item_id"])
        if decision is None or proof.get("detection_id") != decision.get("detection_id"):
            fail(
                "EXECUTION_DETECTION_LINK_MISMATCH",
                "Execution proof is not linked to the mapped candidate detection.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
        if proof.get("status") != "EXECUTED_VERIFIED":
            fail(
                "EXECUTION_STATUS_INVALID",
                "Frozen successful action must be EXECUTED_VERIFIED.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
        for field in ("action_kind", "action_digest", "idempotency_key"):
            if proof.get(field) != expected[field]:
                fail(
                    "EXECUTION_BINDING_MISMATCH",
                    f"Execution {field} is not bound to the frozen action.",
                    target=truth,
                    detection_id=proof.get("detection_id"),
                    requirements=("R3", "R4"),
                )
        if _sorted_events(proof.get("delivery_events", [])) != _sorted_events(expected["delivery_events"]):
            fail(
                "DELIVERY_PATH_MISMATCH",
                "Delivery route, depth, purpose, retention, or event binding differs.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R3", "R4"),
            )

        receipt_ref = proof.get("controller_receipt_ref")
        receipt = trusted["controller_receipts"].get(receipt_ref)
        if receipt_ref != expected["controller_receipt_ref"] or receipt is None:
            fail(
                "EXECUTION_RECEIPT_UNTRUSTED",
                "Controller receipt is absent from the frozen trusted registry.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
        elif (
            receipt.get("world_id") != oracle["world_id"]
            or receipt.get("evaluation_step") != oracle["freeze"]["evaluation_step"]
            or receipt.get("action_digest") != proof.get("action_digest")
            or receipt.get("idempotency_key") != proof.get("idempotency_key")
            or receipt.get("outcome") != "EXECUTED"
        ):
            fail(
                "EXECUTION_RECEIPT_BINDING_INVALID",
                "Trusted receipt is not bound to world, step, action, key, and EXECUTED outcome.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )

        actual_ack_refs = set(proof.get("recipient_ack_refs", []))
        expected_ack_refs = set(expected["recipient_ack_refs"])
        if actual_ack_refs != expected_ack_refs:
            fail(
                "RECIPIENT_ACK_SET_MISMATCH",
                "Recipient ACK set is incomplete or contains a non-required ACK.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
        for ack_ref in actual_ack_refs:
            ack = trusted["recipient_acks"].get(ack_ref)
            if ack is None:
                fail(
                    "RECIPIENT_ACK_UNTRUSTED",
                    "ACK is absent from the frozen recipient registry.",
                    target=truth,
                    detection_id=proof.get("detection_id"),
                    requirements=("R4",),
                )
            elif (
                ack.get("action_digest") != proof.get("action_digest")
                or ack.get("idempotency_key") != proof.get("idempotency_key")
            ):
                fail(
                    "RECIPIENT_ACK_BINDING_INVALID",
                    "ACK is not bound to the same action and key.",
                    target=truth,
                    detection_id=proof.get("detection_id"),
                    requirements=("R4",),
                )

        anchor_ref = proof.get("external_anchor_ref")
        anchor = trusted["external_anchors"].get(anchor_ref)
        if anchor_ref != expected["external_anchor_ref"] or anchor is None:
            fail(
                "EXTERNAL_ANCHOR_MISMATCH",
                "External anchor is not the frozen append-only entry for this action.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )
        elif (
            anchor.get("action_digest") != proof.get("action_digest")
            or anchor.get("idempotency_key") != proof.get("idempotency_key")
            or anchor.get("controller_receipt_ref") != receipt_ref
            or set(anchor.get("recipient_ack_refs", [])) != actual_ack_refs
            or anchor.get("issuer") == receipt.get("issuer", "") if receipt else True
        ):
            fail(
                "EXTERNAL_ANCHOR_BINDING_INVALID",
                "Anchor does not bind the action, receipt, ACK set, or independent domain.",
                target=truth,
                detection_id=proof.get("detection_id"),
                requirements=("R4",),
            )

    for action_id, expected in expected_actions.items():
        if action_id not in proof_by_action:
            truth = next(
                row
                for row in oracle["expected_items"]
                if row["item_id"] == expected["target_item_id"]
            )
            fail(
                "EXECUTION_PROOF_MISSING",
                "Required three-domain execution proof is missing.",
                target=truth,
                detection_id=mapped.get(truth["item_id"], {}).get("detection_id"),
                requirements=("R4",),
            )

    handoffs = [
        row for row in submission.get("relation_handoffs", []) if isinstance(row, dict)
    ]
    handoff_by_detection = {
        row.get("detection_id"): row
        for row in handoffs
        if _nonempty(row.get("detection_id"))
    }
    for truth in oracle["expected_items"]:
        if truth["expected_state"] != "DISCOVERED":
            continue
        decision = mapped.get(truth["item_id"])
        if decision is None:
            continue
        detection_id = decision.get("detection_id")
        handoff = handoff_by_detection.get(detection_id)
        if handoff is None:
            fail(
                "RELATION_HANDOFF_MISSING",
                "Discovered opportunity has no relation candidate handoff.",
                target=truth,
                detection_id=detection_id,
                requirements=("R8",),
            )
            continue
        if handoff.get("commitment") is not False:
            fail(
                "COMMITMENT_INVENTED",
                "Discovery was promoted into commitment.",
                target=truth,
                detection_id=detection_id,
                requirements=("R8",),
            )
        if handoff.get("authority_inferred") is not False:
            fail(
                "AUTHORITY_INVENTED",
                "Discovery was promoted into inferred authority.",
                target=truth,
                detection_id=detection_id,
                requirements=("R8",),
            )

    failures = sorted(
        failures,
        key=lambda row: (
            row["code"],
            row["target_signature_sha256"] or "",
            row["detection_id"] or "",
            row["detail"],
        ),
    )
    requirement_results: dict[str, dict[str, Any]] = {}
    for requirement_id, description in REQUIREMENTS.items():
        related = [
            row["code"]
            for row in failures
            if requirement_id in row["requirements"]
        ]
        requirement_results[requirement_id] = {
            "status": "PASS" if not related else "FAIL",
            "description": description,
            "failure_codes": sorted(set(related)),
        }
    passed = sum(
        row["status"] == "PASS" for row in requirement_results.values()
    )
    correctly_discovered = sum(
        truth["expected_state"] == "DISCOVERED"
        and truth["item_id"] in mapped
        and mapped[truth["item_id"]].get("state") == "DISCOVERED"
        for truth in oracle["expected_items"]
    )
    return {
        "schema_version": "2.0",
        "world_id": oracle["world_id"],
        "submission_sha256": canonical_sha256(submission),
        "status": "PASS" if not failures else "FAIL",
        "coverage": {
            "requirements_passed": passed,
            "requirements_total": len(REQUIREMENTS),
            "ratio": passed / len(REQUIREMENTS),
        },
        "metrics": {
            "expected_item_count": len(oracle["expected_items"]),
            "mapped_item_count": len(mapped),
            "correctly_discovered_count": correctly_discovered,
            "false_wakeup_count": false_wakeup_count,
        },
        "requirement_results": requirement_results,
        "critical_failures": failures,
    }


def apply_mutation(
    fixture: dict[str, Any],
    mutation: dict[str, Any],
) -> dict[str, Any]:
    value = copy.deepcopy(fixture)
    for action in mutation["actions"]:
        operation = action["action"]
        if operation == "SET_DECISION_STATE":
            decision = next(
                row for row in value["decisions"]
                if row["detection_id"] == action["detection_id"]
            )
            decision["state"] = action["state"]
        elif operation == "SET_DECISION_FIELD":
            decision = next(
                row for row in value["decisions"]
                if row["detection_id"] == action["detection_id"]
            )
            decision[action["field"]] = action["value"]
        elif operation == "APPEND_DECISION":
            value["decisions"].append(copy.deepcopy(action["value"]))
        elif operation == "REMOVE_UPDATE":
            value["projection_updates"] = [
                row for row in value["projection_updates"]
                if row["party"] != action["party"]
            ]
        elif operation == "SET_PROOF_FIELD":
            proof = next(
                row for row in value["execution_proofs"]
                if row["action_id"] == action["action_id"]
            )
            proof[action["field"]] = copy.deepcopy(action["value"])
        elif operation == "REMOVE_ACK":
            proof = next(
                row for row in value["execution_proofs"]
                if row["action_id"] == action["action_id"]
            )
            proof["recipient_ack_refs"] = [
                ref for ref in proof["recipient_ack_refs"]
                if ref != action["ack_ref"]
            ]
        elif operation == "SET_DELIVERY_FIELD":
            proof = next(
                row for row in value["execution_proofs"]
                if row["action_id"] == action["action_id"]
            )
            event = next(
                row for row in proof["delivery_events"]
                if row["event_ref"] == action["event_ref"]
            )
            event[action["field"]] = action["value"]
        elif operation == "APPEND_PROOF":
            value["execution_proofs"].append(copy.deepcopy(action["value"]))
        elif operation == "REMOVE_HANDOFF":
            value["relation_handoffs"] = [
                row for row in value["relation_handoffs"]
                if row["detection_id"] != action["detection_id"]
            ]
        elif operation == "SET_HANDOFF_FIELD":
            handoff = next(
                row for row in value["relation_handoffs"]
                if row["detection_id"] == action["detection_id"]
            )
            handoff[action["field"]] = copy.deepcopy(action["value"])
        else:
            raise ValueError(f"unknown mutation action: {operation}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path)
    parser.add_argument("--oracle", type=Path, default=DEFAULT_ORACLE)
    args = parser.parse_args()
    result = evaluate(load_json(args.submission), load_json(args.oracle))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
