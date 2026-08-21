#!/usr/bin/env python3
"""Deterministic scorer for T1-HW-B.

Candidate methods own their detection, probe, disclosure, and handoff IDs.
Only this scorer maps observable pair/claim signatures to latent truth. It
never generates, repairs, or runs a candidate method.
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
    "R7": "Avoid direction/version false wakeups and structural misses.",
    "R8": "Handoff discoveries to relation constitution without inventing commitment.",
}
ALLOWED_STATES = {
    "DISCOVERED",
    "INVALIDATED",
    "UNFINDABLE_UNDER_POLICY",
    "UNKNOWN",
    "REFUSE",
    "ABSENT",
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
    "relation_handoffs",
}
DECISION_PAIR_FIELDS = {
    "detection_id",
    "kind",
    "state",
    "seeker",
    "provider",
    "direction",
    "evidence_refs",
}
DECISION_CLAIM_FIELDS = {
    "detection_id",
    "kind",
    "state",
    "claim_key",
    "subject",
    "evidence_refs",
}
PROBE_FIELDS = {
    "probe_id",
    "requester",
    "responder",
    "requested_fact",
    "offered_fact",
    "status",
    "evidence_refs",
}
DISCLOSURE_REQUIRED_FIELDS = {
    "event_id",
    "origin_party",
    "sender",
    "recipient",
    "fact_id",
    "depth",
    "purpose",
    "retention",
}
DISCLOSURE_ALLOWED_FIELDS = DISCLOSURE_REQUIRED_FIELDS | {
    "derived_from_event_id"
}
UPDATE_FIELDS = {
    "party",
    "from_version",
    "to_version",
    "step",
    "evidence_ref",
}
HANDOFF_FIELDS = {
    "detection_id",
    "status",
    "commitment",
    "seeker",
    "provider",
    "evidence_refs",
    "open_questions",
}
SECRET_INTERFACE_FIELDS = {
    "item_id",
    "opportunity_id",
    "truth_id",
    "expected_state",
    "latent_id",
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


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def validate_submission_structure(submission: Any) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []

    def error(code: str, path: str, detail: str) -> None:
        errors.append({"code": code, "path": path, "detail": detail})

    def exact_fields(
        value: dict[str, Any],
        required: set[str],
        allowed: set[str],
        path: str,
    ) -> None:
        missing = sorted(required - set(value))
        extra = sorted(set(value) - allowed)
        if missing:
            error("FIELDS_MISSING", path, ", ".join(missing))
        if extra:
            error("FIELDS_FORBIDDEN", path, ", ".join(extra))

    if not isinstance(submission, dict):
        return [{
            "code": "SUBMISSION_NOT_OBJECT",
            "path": "$",
            "detail": "Submission must be a JSON object.",
        }]
    exact_fields(submission, TOP_LEVEL_FIELDS, TOP_LEVEL_FIELDS, "$")
    if submission.get("schema_version") != "1.1":
        error("SCHEMA_VERSION_INVALID", "$.schema_version", "Expected 1.1.")
    if not _nonempty_string(submission.get("method_id")):
        error("METHOD_ID_INVALID", "$.method_id", "Expected non-empty string.")
    if not isinstance(submission.get("evaluation_step"), int):
        error("EVALUATION_STEP_INVALID", "$.evaluation_step", "Expected integer.")
    for field in (
        "decisions",
        "probes",
        "disclosures",
        "projection_updates",
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
        fields = (
            DECISION_PAIR_FIELDS
            if decision.get("kind") == "PAIR"
            else DECISION_CLAIM_FIELDS
            if decision.get("kind") == "CLAIM"
            else {"detection_id", "kind", "state", "evidence_refs"}
        )
        exact_fields(decision, fields, fields, path)
        detection_id = decision.get("detection_id")
        if not _nonempty_string(detection_id):
            error("DETECTION_ID_INVALID", f"{path}.detection_id", "Expected ID.")
        elif detection_id in detection_ids:
            error("DUPLICATE_DETECTION_ID", f"{path}.detection_id", detection_id)
        else:
            detection_ids.add(detection_id)
        if decision.get("kind") not in {"PAIR", "CLAIM"}:
            error("DECISION_KIND_INVALID", f"{path}.kind", "Expected PAIR or CLAIM.")
        if decision.get("state") not in ALLOWED_STATES:
            error("STATE_INVALID", f"{path}.state", "Unknown state.")
        if not isinstance(decision.get("evidence_refs"), list):
            error("EVIDENCE_REFS_INVALID", f"{path}.evidence_refs", "Expected array.")
        if decision.get("kind") == "PAIR":
            for field in ("seeker", "provider"):
                if not _nonempty_string(decision.get(field)):
                    error("PAIR_FIELD_INVALID", f"{path}.{field}", "Expected string.")
            if decision.get("direction") != "SEEK_TO_OFFER":
                error(
                    "PAIR_DIRECTION_INVALID",
                    f"{path}.direction",
                    "Expected SEEK_TO_OFFER.",
                )
        if decision.get("kind") == "CLAIM":
            for field in ("claim_key", "subject"):
                if not _nonempty_string(decision.get(field)):
                    error("CLAIM_FIELD_INVALID", f"{path}.{field}", "Expected string.")

    for collection, required, allowed, prefix in (
        ("probes", PROBE_FIELDS, PROBE_FIELDS, "PROBE"),
        (
            "disclosures",
            DISCLOSURE_REQUIRED_FIELDS,
            DISCLOSURE_ALLOWED_FIELDS,
            "DISCLOSURE",
        ),
        ("projection_updates", UPDATE_FIELDS, UPDATE_FIELDS, "UPDATE"),
        ("relation_handoffs", HANDOFF_FIELDS, HANDOFF_FIELDS, "HANDOFF"),
    ):
        for index, value in enumerate(submission.get(collection, [])):
            path = f"$.{collection}[{index}]"
            if not isinstance(value, dict):
                error(f"{prefix}_NOT_OBJECT", path, "Expected object.")
                continue
            exact_fields(value, required, allowed, path)

    def scan(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if key in SECRET_INTERFACE_FIELDS:
                    error(
                        "ORACLE_INTERFACE_FIELD_FORBIDDEN",
                        child_path,
                        "Secret-side fields are forbidden.",
                    )
                scan(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                scan(child, f"{path}[{index}]")

    scan(submission, "$")
    return sorted(errors, key=lambda item: (item["code"], item["path"], item["detail"]))


def _truth_signature(item: dict[str, Any]) -> tuple[str, ...]:
    if "claim_key" in item:
        return ("CLAIM", item["claim_key"], item["subject"])
    return ("PAIR", item["seeker"], item["provider"], item["direction"])


def _decision_signature(decision: dict[str, Any]) -> tuple[str, ...] | None:
    if decision.get("kind") == "CLAIM":
        return (
            "CLAIM",
            decision.get("claim_key", ""),
            decision.get("subject", ""),
        )
    if decision.get("kind") == "PAIR":
        return (
            "PAIR",
            decision.get("seeker", ""),
            decision.get("provider", ""),
            decision.get("direction", ""),
        )
    return None


def _target_digest(item: dict[str, Any]) -> str:
    return canonical_sha256(_truth_signature(item))


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
        requirements: tuple[str, ...] = (),
    ) -> None:
        failures.append({
            "code": code,
            "target_signature_sha256": _target_digest(target) if target else None,
            "detection_id": detection_id,
            "detail": detail,
            "requirements": list(requirements),
        })

    for structural_error in validate_submission_structure(submission):
        fail(
            structural_error["code"],
            f"{structural_error['path']}: {structural_error['detail']}",
            requirements=tuple(REQUIREMENT_DESCRIPTIONS),
        )
    if submission.get("world_id") != oracle["world_id"]:
        fail(
            "WORLD_ID_MISMATCH",
            "Submission is not bound to this frozen world.",
            requirements=tuple(REQUIREMENT_DESCRIPTIONS),
        )
    if submission.get("evaluation_step") != oracle["freeze"]["S0"]["evaluation_step"]:
        fail(
            "EVALUATION_STEP_MISMATCH",
            "Submission did not evaluate the frozen step.",
            requirements=("R2",),
        )

    decisions = (
        submission.get("decisions", [])
        if isinstance(submission.get("decisions"), list)
        else []
    )
    valid_decisions = [item for item in decisions if isinstance(item, dict)]
    decision_by_id = {
        item["detection_id"]: item
        for item in valid_decisions
        if _nonempty_string(item.get("detection_id"))
    }
    expected_items = oracle["expected_items"]
    truth_by_signature = {
        _truth_signature(item): item for item in expected_items
    }
    witness_ids = {item["witness_id"] for item in oracle["witnesses"]}
    mapped: dict[str, dict[str, Any]] = {}
    truth_by_detection: dict[str, dict[str, Any]] = {}

    forbidden_pairs = {
        (item["seeker"], item["provider"]): item
        for item in oracle["forbidden_pairs"]
    }
    for decision in valid_decisions:
        detection_id = decision.get("detection_id")
        signature = _decision_signature(decision)
        expected = truth_by_signature.get(signature) if signature else None
        if expected is None:
            fail(
                "UNEXPECTED_DETECTION",
                "Observable signature is not a frozen target.",
                detection_id=detection_id,
                requirements=("R7",),
            )
            if decision.get("state") == "DISCOVERED":
                fail(
                    "FALSE_WAKEUP",
                    "An unmatched signature was marked DISCOVERED.",
                    detection_id=detection_id,
                    requirements=("R7",),
                )
                decoy = forbidden_pairs.get(
                    (decision.get("seeker"), decision.get("provider"))
                )
                if decoy:
                    fail(
                        decoy["failure_code"],
                        "A frozen direction/version decoy was awakened.",
                        detection_id=detection_id,
                        requirements=("R7",),
                    )
            continue
        item_id = expected["item_id"]
        if item_id in mapped:
            fail(
                "DUPLICATE_TRUTH_DETECTION",
                "Multiple detections map to one target.",
                target=expected,
                detection_id=detection_id,
                requirements=("R7",),
            )
            continue
        mapped[item_id] = decision
        if _nonempty_string(detection_id):
            truth_by_detection[detection_id] = expected

    discoverable = [
        item for item in expected_items if item["expected_state"] == "DISCOVERED"
    ]
    for expected in expected_items:
        requirements = tuple(expected["requirement_ids"])
        decision = mapped.get(expected["item_id"])
        if decision is None:
            fail(
                "RECALL_MISS",
                "No candidate-owned signature maps to this target.",
                target=expected,
                requirements=requirements,
            )
            continue
        detection_id = decision.get("detection_id")
        if decision.get("state") != expected["expected_state"]:
            fail(
                "STATE_MISMATCH",
                "Candidate state differs from frozen state.",
                target=expected,
                detection_id=detection_id,
                requirements=requirements,
            )
        refs = (
            decision.get("evidence_refs", [])
            if isinstance(decision.get("evidence_refs"), list)
            else []
        )
        missing = sorted(set(expected["required_evidence"]) - set(refs))
        if missing:
            fail(
                "REQUIRED_EVIDENCE_MISSING",
                "Required observable evidence is missing.",
                target=expected,
                detection_id=detection_id,
                requirements=requirements,
            )
        if set(refs) - witness_ids:
            fail(
                "UNKNOWN_EVIDENCE",
                "Decision references evidence outside the frozen witness set.",
                target=expected,
                detection_id=detection_id,
                requirements=requirements,
            )

    roles = oracle["party_roles_at_evaluation_step"]
    for decision in valid_decisions:
        if decision.get("kind") != "PAIR" or decision.get("state") != "DISCOVERED":
            continue
        if (
            decision.get("direction") != "SEEK_TO_OFFER"
            or roles.get(decision.get("seeker")) != "SEEK"
            or roles.get(decision.get("provider")) != "OFFER"
        ):
            fail(
                "DIRECTION_VIOLATION",
                "DISCOVERED pair is not current SEEK_TO_OFFER.",
                target=truth_by_detection.get(decision.get("detection_id")),
                detection_id=decision.get("detection_id"),
                requirements=("R7",),
            )

    for raw_ref in sorted(
        set(oracle["forbidden_fact_refs"]).intersection(_all_strings(submission))
    ):
        fail(
            "RAW_FACT_EXPOSED",
            "A forbidden raw local fact appears in the submission.",
            detection_id=raw_ref,
            requirements=("R3", "R4"),
        )

    updates = (
        submission.get("projection_updates", [])
        if isinstance(submission.get("projection_updates"), list)
        else []
    )
    for expected in expected_items:
        required_update = expected.get("required_projection_update")
        if not required_update:
            continue
        if not any(
            isinstance(update, dict)
            and all(update.get(key) == value for key, value in required_update.items())
            for update in updates
        ):
            fail(
                "DYNAMIC_UPDATE_MISSING",
                "Required version invalidation update is missing.",
                target=expected,
                requirements=("R2",),
            )

    policies = {item["fact_id"]: item for item in oracle["policies"]}
    disclosures = (
        submission.get("disclosures", [])
        if isinstance(submission.get("disclosures"), list)
        else []
    )
    disclosure_by_id: dict[str, dict[str, Any]] = {}
    for event in disclosures:
        if not isinstance(event, dict):
            fail(
                "DISCLOSURE_RECORD_INVALID",
                "Disclosure must be an object.",
                requirements=("R4",),
            )
            continue
        event_id = event.get("event_id")
        if not _nonempty_string(event_id):
            fail(
                "DISCLOSURE_EVENT_ID_INVALID",
                "Disclosure event ID is missing.",
                requirements=("R4",),
            )
            continue
        if event_id in disclosure_by_id:
            fail(
                "DUPLICATE_DISCLOSURE_EVENT",
                "Disclosure event IDs must be unique.",
                detection_id=event_id,
                requirements=("R4",),
            )
        else:
            disclosure_by_id[event_id] = event

    aggregate: dict[str, dict[str, Any]] = {}
    for event_id, event in sorted(disclosure_by_id.items()):
        fact_id = event.get("fact_id")
        policy = policies.get(fact_id)
        if policy is None:
            fail(
                "DISCLOSURE_POLICY_MISSING",
                "No policy authorizes the disclosed fact.",
                detection_id=event_id,
                requirements=("R4",),
            )
            continue
        parent_id = event.get("derived_from_event_id")
        if parent_id is None:
            if event.get("sender") != policy["origin_party"]:
                fail(
                    "DISCLOSURE_SENDER_UNAUTHORIZED",
                    "Direct disclosure must be sent by origin.",
                    detection_id=event_id,
                    requirements=("R4",),
                )
        else:
            parent = disclosure_by_id.get(parent_id)
            if parent is None:
                fail(
                    "DISCLOSURE_PARENT_MISSING",
                    "Derived disclosure parent is absent.",
                    detection_id=event_id,
                    requirements=("R4",),
                )
            else:
                if event.get("sender") != parent.get("recipient"):
                    fail(
                        "DISCLOSURE_CHAIN_BROKEN",
                        "Derived sender is not prior recipient.",
                        detection_id=event_id,
                        requirements=("R4",),
                    )
                if event.get("fact_id") != parent.get("fact_id"):
                    fail(
                        "DISCLOSURE_ORIGIN_CHANGED",
                        "Derived disclosure changed origin fact.",
                        detection_id=event_id,
                        requirements=("R4",),
                    )
            if not policy["onward_disclosure"]:
                fail(
                    "ONWARD_DISCLOSURE_FORBIDDEN",
                    "Policy forbids onward disclosure.",
                    detection_id=event_id,
                    requirements=("R4",),
                )
        checks = (
            (event.get("origin_party") == policy["origin_party"], "DISCLOSURE_ORIGIN_MISMATCH"),
            (event.get("recipient") in policy["allowed_recipients"], "DISCLOSURE_RECIPIENT_FORBIDDEN"),
            (event.get("purpose") == policy["allowed_purpose"], "DISCLOSURE_PURPOSE_MISMATCH"),
            (event.get("retention") == policy["retention"], "DISCLOSURE_RETENTION_MISMATCH"),
        )
        for valid, code in checks:
            if not valid:
                fail(
                    code,
                    "Disclosure differs from frozen policy.",
                    detection_id=event_id,
                    requirements=("R4",),
                )
        depth = event.get("depth")
        if (
            not isinstance(depth, int)
            or isinstance(depth, bool)
            or depth < 0
        ):
            fail(
                "DISCLOSURE_DEPTH_INVALID",
                "Depth must be a non-negative integer.",
                detection_id=event_id,
                requirements=("R4",),
            )
            depth = 0
        elif depth > policy["max_depth"]:
            fail(
                "DISCLOSURE_DEPTH_EXCEEDED",
                "Per-event depth exceeds policy.",
                detection_id=event_id,
                requirements=("R4",),
            )
        values = aggregate.setdefault(
            fact_id, {"recipients": set(), "cumulative_depth": 0}
        )
        values["recipients"].add(event.get("recipient"))
        values["cumulative_depth"] += depth

    for fact_id, values in sorted(aggregate.items()):
        policy = policies[fact_id]
        if len(values["recipients"]) > policy["max_unique_recipients"]:
            fail(
                "DISCLOSURE_RECIPIENT_BUDGET_EXCEEDED",
                "Unique-recipient budget exceeded.",
                detection_id=fact_id,
                requirements=("R4",),
            )
        if values["cumulative_depth"] > policy["max_cumulative_depth"]:
            fail(
                "DISCLOSURE_CUMULATIVE_DEPTH_EXCEEDED",
                "Cumulative depth budget exceeded.",
                detection_id=fact_id,
                requirements=("R4",),
            )

    for required_path in oracle["required_disclosure_paths"]:
        matched_event_ids: list[str] = []
        path_ok = True
        for index, required in enumerate(required_path["required_events"]):
            expected_fields = {
                key: value
                for key, value in required.items()
                if key not in {
                    "derived_from_event_id",
                    "derived_from_required_event_index",
                }
            }
            candidate = next(
                (
                    event
                    for event in disclosures
                    if isinstance(event, dict)
                    and all(event.get(key) == value for key, value in expected_fields.items())
                    and (
                        required.get("derived_from_event_id", "__UNSET__")
                        == "__UNSET__"
                        or event.get("derived_from_event_id")
                        == required.get("derived_from_event_id")
                    )
                    and (
                        "derived_from_required_event_index" not in required
                        or (
                            required["derived_from_required_event_index"]
                            < len(matched_event_ids)
                            and event.get("derived_from_event_id")
                            == matched_event_ids[
                                required["derived_from_required_event_index"]
                            ]
                        )
                    )
                ),
                None,
            )
            if candidate is None:
                path_ok = False
                break
            matched_event_ids.append(candidate["event_id"])
        if not path_ok:
            target = next(
                item
                for item in expected_items
                if item["item_id"] == required_path["truth_item_id"]
            )
            fail(
                "REQUIRED_DISCLOSURE_PATH_MISSING",
                "A required authorized projection route is incomplete.",
                target=target,
                requirements=("R1", "R3", "R4"),
            )

    expected_probe = oracle["required_reciprocal_probe"]
    probes = (
        submission.get("probes", [])
        if isinstance(submission.get("probes"), list)
        else []
    )
    probe = next(
        (
            item
            for item in probes
            if isinstance(item, dict)
            and all(
                item.get(key) == expected_probe[key]
                for key in (
                    "requester",
                    "responder",
                    "requested_fact",
                    "offered_fact",
                )
            )
        ),
        None,
    )
    reciprocal_target = next(
        item
        for item in expected_items
        if item["category"] == "EXPRESSIBLE_AFTER_TWO_SIDED_RECEIPT"
    )
    if probe is None:
        fail(
            "RECIPROCAL_PROBE_MISSING",
            "No two-sided probe maps to the frozen reciprocal contract.",
            target=reciprocal_target,
            requirements=("R4", "R7"),
        )
    else:
        if probe.get("status") != expected_probe["status"]:
            fail(
                "RECIPROCAL_PROBE_STATUS_INVALID",
                "Probe is not reciprocally complete.",
                target=reciprocal_target,
                detection_id=probe.get("probe_id"),
                requirements=("R4", "R7"),
            )
        if expected_probe["evidence_ref"] not in probe.get("evidence_refs", []):
            fail(
                "RECIPROCAL_PROBE_EVIDENCE_MISSING",
                "Two-sided completion witness is missing.",
                target=reciprocal_target,
                detection_id=probe.get("probe_id"),
                requirements=("R4", "R7"),
            )
    present_facts = {
        event.get("fact_id") for event in disclosures if isinstance(event, dict)
    }
    for fact_id in sorted(
        set(expected_probe["required_disclosure_facts"]) - present_facts
    ):
        fail(
            "RECIPROCAL_DISCLOSURE_MISSING",
            "One side of reciprocal disclosure is missing.",
            target=reciprocal_target,
            detection_id=fact_id,
            requirements=("R4", "R7"),
        )

    handoffs = (
        submission.get("relation_handoffs", [])
        if isinstance(submission.get("relation_handoffs"), list)
        else []
    )
    handoff_by_detection = {
        item.get("detection_id"): item
        for item in handoffs
        if isinstance(item, dict) and _nonempty_string(item.get("detection_id"))
    }
    for expected in expected_items:
        decision = mapped.get(expected["item_id"])
        detection_id = decision.get("detection_id") if decision else None
        handoff = handoff_by_detection.get(detection_id)
        if expected["requires_relation_handoff"]:
            if handoff is None:
                fail(
                    "RELATION_HANDOFF_MISSING",
                    "Discovered opportunity lacks relation handoff.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
                continue
            if handoff.get("status") != "CANDIDATE_NOT_COMMITMENT":
                fail(
                    "RELATION_HANDOFF_STATUS_INVALID",
                    "Handoff status overstates discovery.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
            if handoff.get("commitment") is not False:
                fail(
                    "COMMITMENT_INVENTED",
                    "Discovery cannot create commitment.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
            if (
                handoff.get("seeker") != expected.get("seeker")
                or handoff.get("provider") != expected.get("provider")
            ):
                fail(
                    "RELATION_HANDOFF_PARTIES_MISMATCH",
                    "Handoff parties differ from observed discovery.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
            if not handoff.get("open_questions"):
                fail(
                    "RELATION_HANDOFF_OPEN_QUESTIONS_MISSING",
                    "Handoff must retain unresolved questions.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
            if not set(expected["required_evidence"]).issubset(
                handoff.get("evidence_refs", [])
            ):
                fail(
                    "RELATION_HANDOFF_EVIDENCE_MISSING",
                    "Handoff omits discovery evidence.",
                    target=expected,
                    detection_id=detection_id,
                    requirements=("R8",),
                )
        elif handoff is not None:
            fail(
                "RELATION_HANDOFF_FORBIDDEN",
                "Non-discoverable item cannot be handed off.",
                target=expected,
                detection_id=detection_id,
                requirements=("R8",),
            )
    for detection_id in sorted(
        set(handoff_by_detection) - set(truth_by_detection)
    ):
        fail(
            "UNEXPECTED_RELATION_HANDOFF",
            "Handoff references an unmapped detection.",
            detection_id=detection_id,
            requirements=("R8",),
        )

    failures.sort(
        key=lambda item: (
            item["code"],
            item["target_signature_sha256"] or "",
            item["detection_id"] or "",
            item["detail"],
        )
    )
    requirement_results: dict[str, dict[str, Any]] = {}
    for requirement_id, description in REQUIREMENT_DESCRIPTIONS.items():
        failure_codes = sorted({
            failure["code"]
            for failure in failures
            if requirement_id in failure["requirements"]
        })
        requirement_results[requirement_id] = {
            "status": "FAIL" if failure_codes else "PASS",
            "failure_codes": failure_codes,
            "description": description,
        }
    passed = sum(
        1 for result in requirement_results.values() if result["status"] == "PASS"
    )
    correct_discovered = sum(
        1
        for item in discoverable
        if mapped.get(item["item_id"], {}).get("state") == "DISCOVERED"
    )
    return {
        "schema_version": "1.1",
        "world_id": oracle["world_id"],
        "submission_sha256": canonical_sha256(submission),
        "status": "PASS" if not failures else "FAIL",
        "critical_failures": failures,
        "requirement_results": requirement_results,
        "metrics": {
            "frozen_item_count": len(expected_items),
            "mapped_item_count": len(mapped),
            "discoverable_opportunity_count": len(discoverable),
            "correctly_discovered_count": correct_discovered,
            "opportunity_recall": (
                correct_discovered / len(discoverable) if discoverable else 1.0
            ),
            "false_wakeup_count": sum(
                1 for item in failures if item["code"] == "FALSE_WAKEUP"
            ),
            "disclosure_event_count": len(disclosure_by_id),
        },
        "coverage": {
            "requirements_passed": passed,
            "requirements_total": len(REQUIREMENT_DESCRIPTIONS),
            "ratio": passed / len(REQUIREMENT_DESCRIPTIONS),
        },
        "evidence_boundary": (
            "One synthetic held-out world only. A calibration fixture is not a "
            "candidate result and cannot establish real-world frequency or value."
        ),
    }


def apply_mutation(
    document: dict[str, Any],
    mutation: dict[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(document)
    for action in mutation.get("actions", []):
        name = action["action"]
        if name == "SET_DECISION_STATE":
            target = next(
                item
                for item in result["decisions"]
                if item["detection_id"] == action["detection_id"]
            )
            target["state"] = action["state"]
        elif name == "REMOVE_PROJECTION_UPDATE":
            result["projection_updates"] = [
                item
                for item in result["projection_updates"]
                if item.get("party") != action["party"]
            ]
        elif name == "APPEND_DECISION":
            result["decisions"].append(copy.deepcopy(action["value"]))
        elif name == "APPEND_DISCLOSURE":
            result["disclosures"].append(copy.deepcopy(action["value"]))
        elif name == "REMOVE_DISCLOSURE":
            result["disclosures"] = [
                item
                for item in result["disclosures"]
                if item.get("event_id") != action["event_id"]
            ]
        elif name == "REMOVE_RELATION_HANDOFF":
            result["relation_handoffs"] = [
                item
                for item in result["relation_handoffs"]
                if item.get("detection_id") != action["detection_id"]
            ]
        elif name == "SET_HANDOFF_FIELD":
            target = next(
                item
                for item in result["relation_handoffs"]
                if item["detection_id"] == action["detection_id"]
            )
            target[action["field"]] = action["value"]
        elif name == "SET_PROBE_FIELD":
            target = next(
                item
                for item in result["probes"]
                if item["probe_id"] == action["probe_id"]
            )
            target[action["field"]] = action["value"]
        else:
            raise ValueError(f"Unknown mutation action: {name}")
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
