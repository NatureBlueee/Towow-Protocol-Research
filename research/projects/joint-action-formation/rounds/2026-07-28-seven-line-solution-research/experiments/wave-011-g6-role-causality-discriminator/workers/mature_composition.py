#!/usr/bin/env python3
"""Independent transaction/outbox/workflow/readback composition."""

import json
import sys


def authority_gate(attempts, policy):
    permits = []
    for attempt in attempts:
        for grant in policy.get("attempt_grants", []):
            same_subject = grant.get("actor") == attempt.get("actor")
            operation_ok = attempt.get("operation") in grant.get("operations", [])
            object_ok = attempt.get("object") in grant.get("objects", [])
            if same_subject and operation_ok and object_ok:
                permits.append(attempt["id"])
                break
    return permits


def reconcile_target(attempts, target, target_observed_at, permitted, cut):
    exact = target.get("exact_object")
    attempt_ids = {x["id"] for x in attempts}
    all_events = list(target.get("transitions", []))
    caused = [
        event
        for event in all_events
        if event.get("operation_id") in attempt_ids and event.get("object") == exact
    ]
    latest_head = target.get("known_latest_head", target.get("current_head"))
    fresh = (
        target.get("current_head") is not None
        and target.get("current_head") >= latest_head
        and target_observed_at <= target.get("expires_at", target_observed_at + 1)
    )
    intervals = cut.get("head_intervals", [])
    consistent = bool(intervals) and max(
        int(x["valid_from"]) for x in intervals
    ) <= min(int(x["valid_through"]) for x in intervals)
    eligible = [
        event
        for event in caused
        if event.get("operation_id") in permitted
        and fresh
        and consistent
    ]
    residual = [
        event
        for event in all_events
        if event.get("operation_id") in attempt_ids
        and (
            event.get("object") != exact
            or event.get("operation_id") not in permitted
            or not fresh
        )
    ]
    return exact, all_events, caused, eligible, residual, fresh, consistent


def classify_acceptance(acts, exact, policy):
    permitted_principals = set(policy.get("acceptance_authorities", []))
    qualified = []
    for act in acts:
        if (
            act.get("principal") in permitted_principals
            and act.get("object") == exact
            and act.get("criterion") == "criterion-v1"
        ):
            qualified.append(act)
    if any(x.get("stance") == "REJECT" for x in qualified):
        status = "REJECTED"
    else:
        acceptors = {x.get("principal") for x in qualified if x.get("stance") == "ACCEPT"}
        required = set(policy.get("required_acceptors", []))
        if required and required <= acceptors:
            status = "ACCEPTED"
        elif acceptors:
            status = "ACCEPTED_PARTIAL"
        else:
            status = "NONE"
    return qualified, status


def obligation_projection(store):
    phases = [event.get("phase") for event in store.get("transitions", [])]
    if store.get("disputes") or "REVERSAL_OPEN" in phases:
        return phases, "REVERSAL_OPEN"
    if "BENEFICIARY_PAID_OUT" in phases:
        if store.get("reversal_window") == "CLOSED":
            return phases, "FINAL"
        return phases, "PAID_OUT_REVERSIBLE"
    if "PROVIDER_SETTLED" in phases:
        return phases, "PROVIDER_SETTLED_ONLY"
    return phases, "NOT_APPLICABLE"


def run(packet):
    views = packet["observations"]
    attempt_rows = [
        x
        for x in views["execution"]["payload"].get("attempts", [])
        if x.get("crossed_boundary") is True
    ]
    policy = views["authority"]["payload"]
    permitted = authority_gate(attempt_rows, policy)
    cut = views["cut"]["payload"]
    target = views["target"]["payload"]
    exact, raw_effects, causal_effects, counted_effects, residuals, is_fresh, is_consistent = reconcile_target(
        attempt_rows, target, views["target"].get("observed_at", 0), permitted, cut
    )
    effect_ids = {x.get("occurrence") for x in counted_effects}
    adoption_rows = []
    for use_event in views["adoption"]["payload"].get("events", []):
        if (
            use_event.get("object") == exact
            and use_event.get("source_effect") in effect_ids
        ):
            adoption_rows.append(use_event)
    qualified_acts, acceptance_state = classify_acceptance(
        views["acceptance"]["payload"].get("acts", []), exact, policy
    )
    settlement_phases, settlement_state = obligation_projection(
        views["settlement"]["payload"]
    )

    has_timeout = any(x.get("transport") == "TIMEOUT" for x in attempt_rows)
    if residuals:
        workflow_directive = "RECOVER_AND_BLOCK"
    elif not (is_fresh and is_consistent):
        workflow_directive = "BOUNDED_UNKNOWN"
    elif has_timeout and causal_effects:
        workflow_directive = "READBACK_NO_RETRY"
    elif has_timeout:
        workflow_directive = "RETRY_SAFE"
    elif acceptance_state == "REJECTED":
        workflow_directive = "BLOCK_DISPUTED"
    else:
        workflow_directive = "OBSERVE"

    occurrence_nodes = []
    role_assignments = []
    for attempt in attempt_rows:
        occurrence_nodes.append(
            {
                "occurrence_id": attempt["id"],
                "native_kind": "ACTION_ATTEMPT",
                "object": attempt["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": attempt["id"],
                "episode": packet["world_token"],
                "role": "Attempt",
                "status": (
                    "QUALIFIES"
                    if attempt["id"] in permitted
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for event in raw_effects:
        occurrence_nodes.append(
            {
                "occurrence_id": event["occurrence"],
                "native_kind": "TARGET_TRANSITION",
                "object": event["object"],
            }
        )
        role_assignments.append(
            {
                "occurrence_id": event["occurrence"],
                "subject_kind": "Occurrence",
                "subject_id": event["occurrence"],
                "episode": packet["world_token"],
                "role": "Effect",
                "status": (
                    "QUALIFIES"
                    if event in counted_effects
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for use_event in views["adoption"]["payload"].get("events", []):
        occurrence_nodes.append(
            {
                "occurrence_id": use_event["occurrence"],
                "native_kind": "OPERATIONAL_USE",
                "object": use_event["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": use_event["occurrence"],
                "episode": packet["world_token"],
                "role": "Adoption",
                "status": (
                    "QUALIFIES"
                    if use_event in adoption_rows
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for act in views["acceptance"]["payload"].get("acts", []):
        occurrence_nodes.append(
            {
                "occurrence_id": act["occurrence"],
                "native_kind": "INSTITUTIONAL_ACT",
                "object": act["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": act["occurrence"],
                "episode": packet["world_token"],
                "role": "Acceptance",
                "status": (
                    "QUALIFIES"
                    if act in qualified_acts
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for index, transition in enumerate(
        views["settlement"]["payload"].get("transitions", [])
    ):
        role_assignments.append(
            {
                "subject_kind": "Claim",
                "subject_id": f"settlement-{index}-{transition.get('obligation')}",
                "episode": packet["world_token"],
                "role": "Settlement",
                "status": (
                    "DOES_NOT_QUALIFY"
                    if transition.get("phase") == "REVERSAL_OPEN"
                    else "QUALIFIES"
                ),
            }
        )

    return {
        "implementation": "mature_composition",
        "raw_occurrences": occurrence_nodes,
        "role_assignments": role_assignments,
        "episode_binding": {
            "exact_object": exact,
            "bound_effect_ids": [x["occurrence"] for x in causal_effects],
        },
        "authority": {
            "stratum": policy.get("authority_stratum"),
            "authorized_attempt_ids": permitted,
            "qualified_acceptance_ids": [x["occurrence"] for x in qualified_acts],
        },
        "counts_toward_q": {
            "effect_ids": [x["occurrence"] for x in counted_effects],
            "adoption_ids": [x["occurrence"] for x in adoption_rows],
            "acceptance_status": acceptance_state,
            "settlement_status": settlement_state,
        },
        "recovery_relevance": {
            "required": bool(residuals),
            "effect_ids": [x["occurrence"] for x in residuals],
        },
        "causal_attribution": (
            "EXACT_ATTEMPT"
            if causal_effects
            else (
                "EXACT_ATTEMPT_WRONG_TARGET"
                if any(
                    x.get("operation_id") in {a["id"] for a in attempt_rows}
                    for x in raw_effects
                )
                else ("PREEXISTING_OR_OTHER" if raw_effects else "NO_EFFECT")
            )
        ),
        "consistent_cut": is_consistent,
        "read_fresh": is_fresh,
        "control_action": workflow_directive,
        "graph_views": {
            "occurrence_provenance": [x["occurrence_id"] for x in occurrence_nodes],
            "authority_qualification": permitted
            + [x["occurrence"] for x in qualified_acts],
            "obligation_control": settlement_phases,
        },
        "worker_cost": {"compute_units": 8, "hitl_calls": 0, "added_latency_ms": 4},
    }


if __name__ == "__main__":
    print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
