#!/usr/bin/env python3
"""Independent human/institutional procedure implementation."""

import json
import sys


def institutional_review(packet):
    records = packet["observations"]
    attempts = [
        x
        for x in records["execution"]["payload"].get("attempts", [])
        if x.get("crossed_boundary")
    ]
    authority = records["authority"]["payload"]

    authorized = []
    for attempt in attempts:
        matching_grants = [
            grant
            for grant in authority.get("attempt_grants", [])
            if grant.get("actor") == attempt.get("actor")
        ]
        approved = False
        for grant in matching_grants:
            if (
                attempt.get("operation") in grant.get("operations", [])
                and attempt.get("object") in grant.get("objects", [])
            ):
                approved = True
        if approved:
            authorized.append(attempt["id"])

    target = records["target"]["payload"]
    exact_object = target.get("exact_object")
    transitions = target.get("transitions", [])
    attempt_ids = {x["id"] for x in attempts}
    episode_effects = [
        x
        for x in transitions
        if x.get("object") == exact_object and x.get("operation_id") in attempt_ids
    ]
    intervals = records["cut"]["payload"].get("head_intervals", [])
    cut_ok = bool(intervals) and max(
        int(x["valid_from"]) for x in intervals
    ) <= min(int(x["valid_through"]) for x in intervals)
    target_observed_at = records["target"].get("observed_at", 0)
    known_latest = target.get("known_latest_head", target.get("current_head"))
    freshness_ok = (
        target.get("current_head") is not None
        and target.get("current_head") >= known_latest
        and target_observed_at <= target.get("expires_at", target_observed_at + 1)
    )
    counted = [
        x
        for x in episode_effects
        if x.get("operation_id") in authorized and cut_ok and freshness_ok
    ]
    residuals = [
        x
        for x in transitions
        if x.get("operation_id") in attempt_ids
        and (
            x.get("object") != exact_object
            or x.get("operation_id") not in authorized
            or not freshness_ok
        )
    ]

    counted_ids = {x["occurrence"] for x in counted}
    use_records = records["adoption"]["payload"].get("events", [])
    adopted = [
        x
        for x in use_records
        if x.get("object") == exact_object and x.get("source_effect") in counted_ids
    ]

    valid_principals = set(authority.get("acceptance_authorities", []))
    accepted_acts = []
    rejected_acts = []
    for act in records["acceptance"]["payload"].get("acts", []):
        in_scope = (
            act.get("principal") in valid_principals
            and act.get("object") == exact_object
            and act.get("criterion") == "criterion-v1"
        )
        if not in_scope:
            continue
        if act.get("stance") == "ACCEPT":
            accepted_acts.append(act)
        if act.get("stance") == "REJECT":
            rejected_acts.append(act)
    required = set(authority.get("required_acceptors", []))
    observed_acceptors = {x.get("principal") for x in accepted_acts}
    if rejected_acts:
        acceptance_state = "REJECTED"
    elif required and required.issubset(observed_acceptors):
        acceptance_state = "ACCEPTED"
    elif accepted_acts:
        acceptance_state = "ACCEPTED_PARTIAL"
    else:
        acceptance_state = "NONE"

    settlement = records["settlement"]["payload"]
    phase_history = [x.get("phase") for x in settlement.get("transitions", [])]
    if settlement.get("disputes") or "REVERSAL_OPEN" in phase_history:
        settlement_state = "REVERSAL_OPEN"
    elif "BENEFICIARY_PAID_OUT" in phase_history:
        settlement_state = (
            "FINAL"
            if settlement.get("reversal_window") == "CLOSED"
            else "PAID_OUT_REVERSIBLE"
        )
    elif "PROVIDER_SETTLED" in phase_history:
        settlement_state = "PROVIDER_SETTLED_ONLY"
    else:
        settlement_state = "NOT_APPLICABLE"

    timeout = any(x.get("transport") == "TIMEOUT" for x in attempts)
    if residuals:
        directive = "RECOVER_AND_BLOCK"
    elif not freshness_ok or not cut_ok:
        directive = "BOUNDED_UNKNOWN"
    elif timeout and episode_effects:
        directive = "READBACK_NO_RETRY"
    elif timeout:
        directive = "RETRY_SAFE"
    elif rejected_acts:
        directive = "BLOCK_DISPUTED"
    else:
        directive = "OBSERVE"

    raw = []
    role_assignments = []
    for attempt in attempts:
        raw.append(
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
                    if attempt["id"] in authorized
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for transition in transitions:
        raw.append(
            {
                "occurrence_id": transition["occurrence"],
                "native_kind": "TARGET_TRANSITION",
                "object": transition["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": transition["occurrence"],
                "episode": packet["world_token"],
                "role": "Effect",
                "status": (
                    "QUALIFIES"
                    if transition in counted
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for use in use_records:
        raw.append(
            {
                "occurrence_id": use["occurrence"],
                "native_kind": "OPERATIONAL_USE",
                "object": use["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": use["occurrence"],
                "episode": packet["world_token"],
                "role": "Adoption",
                "status": "QUALIFIES" if use in adopted else "DOES_NOT_QUALIFY",
            }
        )
    for act in records["acceptance"]["payload"].get("acts", []):
        raw.append(
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
                    if act in accepted_acts + rejected_acts
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for index, transition in enumerate(settlement.get("transitions", [])):
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
        "implementation": "human_institution",
        "raw_occurrences": raw,
        "role_assignments": role_assignments,
        "episode_binding": {
            "exact_object": exact_object,
            "bound_effect_ids": [x["occurrence"] for x in episode_effects],
        },
        "authority": {
            "stratum": authority.get("authority_stratum"),
            "authorized_attempt_ids": authorized,
            "qualified_acceptance_ids": [
                x["occurrence"] for x in accepted_acts + rejected_acts
            ],
        },
        "counts_toward_q": {
            "effect_ids": [x["occurrence"] for x in counted],
            "adoption_ids": [x["occurrence"] for x in adopted],
            "acceptance_status": acceptance_state,
            "settlement_status": settlement_state,
        },
        "recovery_relevance": {
            "required": bool(residuals),
            "effect_ids": [x["occurrence"] for x in residuals],
        },
        "causal_attribution": (
            "EXACT_ATTEMPT"
            if episode_effects
            else (
                "EXACT_ATTEMPT_WRONG_TARGET"
                if any(
                    x.get("operation_id") in {a["id"] for a in attempts}
                    for x in transitions
                )
                else ("PREEXISTING_OR_OTHER" if transitions else "NO_EFFECT")
            )
        ),
        "consistent_cut": cut_ok,
        "read_fresh": freshness_ok,
        "control_action": directive,
        "graph_views": {
            "occurrence_provenance": [x["occurrence_id"] for x in raw],
            "authority_qualification": authorized
            + [x["occurrence"] for x in accepted_acts + rejected_acts],
            "obligation_control": phase_history,
        },
        "worker_cost": {"compute_units": 3, "hitl_calls": 1, "added_latency_ms": 25},
    }


if __name__ == "__main__":
    print(
        json.dumps(
            institutional_review(json.load(sys.stdin)),
            ensure_ascii=False,
            sort_keys=True,
        )
    )
