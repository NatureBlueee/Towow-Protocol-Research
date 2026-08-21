#!/usr/bin/env python3
"""Lawful optimized strong-center implementation.

This executable owns its decision code.  It shares only the JSON observation
schema with the other implementations.
"""

import json
import sys


def decide(packet):
    o = packet["observations"]
    execution = o["execution"]["payload"]
    target = o["target"]["payload"]
    adoption_store = o["adoption"]["payload"]
    acceptance_store = o["acceptance"]["payload"]
    settlement_store = o["settlement"]["payload"]
    authority = o["authority"]["payload"]
    cut = o["cut"]["payload"]

    attempts = [a for a in execution.get("attempts", []) if a.get("crossed_boundary")]
    exact_object = target.get("exact_object")
    grants = authority.get("attempt_grants", [])
    authorized_attempt_ids = []
    for attempt in attempts:
        if any(
            attempt.get("actor") == grant.get("actor")
            and attempt.get("operation") in grant.get("operations", [])
            and attempt.get("object") in grant.get("objects", [])
            for grant in grants
        ):
            authorized_attempt_ids.append(attempt["id"])

    transitions = target.get("transitions", [])
    exact_transitions = [t for t in transitions if t.get("object") == exact_object]
    caused = [
        t
        for t in exact_transitions
        if t.get("operation_id") in {a["id"] for a in attempts}
    ]
    latest_head = target.get("known_latest_head", target.get("current_head"))
    target_observed_at = o["target"].get("observed_at", 0)
    read_fresh = (
        target.get("current_head") is not None
        and target.get("current_head") >= latest_head
        and target_observed_at <= target.get("expires_at", target_observed_at + 1)
    )
    intervals = cut.get("head_intervals", [])
    consistent = bool(intervals) and max(
        int(x["valid_from"]) for x in intervals
    ) <= min(int(x["valid_through"]) for x in intervals)
    counts_effects = [
        t
        for t in caused
        if t.get("operation_id") in authorized_attempt_ids and read_fresh and consistent
    ]
    current_attempt_ids = {a["id"] for a in attempts}
    recovery_effects = [
        t
        for t in transitions
        if t.get("operation_id") in current_attempt_ids
        and (
            t.get("object") != exact_object
            or t.get("operation_id") not in authorized_attempt_ids
            or not read_fresh
        )
    ]

    count_effect_ids = {t.get("occurrence") for t in counts_effects}
    adopted = [
        event
        for event in adoption_store.get("events", [])
        if event.get("object") == exact_object
        and event.get("source_effect") in count_effect_ids
    ]

    authority_principals = set(authority.get("acceptance_authorities", []))
    qualified_acceptance = [
        act
        for act in acceptance_store.get("acts", [])
        if act.get("principal") in authority_principals
        and act.get("object") == exact_object
        and act.get("criterion") == "criterion-v1"
    ]
    rejects = [act for act in qualified_acceptance if act.get("stance") == "REJECT"]
    accepts = [act for act in qualified_acceptance if act.get("stance") == "ACCEPT"]
    required = set(authority.get("required_acceptors", []))
    accepted_by = {act.get("principal") for act in accepts}
    if rejects:
        acceptance_status = "REJECTED"
    elif required and required.issubset(accepted_by):
        acceptance_status = "ACCEPTED"
    elif accepts:
        acceptance_status = "ACCEPTED_PARTIAL"
    else:
        acceptance_status = "NONE"

    phases = [item.get("phase") for item in settlement_store.get("transitions", [])]
    disputes = settlement_store.get("disputes", [])
    if "REVERSAL_OPEN" in phases or disputes:
        settlement_status = "REVERSAL_OPEN"
    elif (
        "BENEFICIARY_PAID_OUT" in phases
        and settlement_store.get("reversal_window") == "CLOSED"
    ):
        settlement_status = "FINAL"
    elif "BENEFICIARY_PAID_OUT" in phases:
        settlement_status = "PAID_OUT_REVERSIBLE"
    elif "PROVIDER_SETTLED" in phases:
        settlement_status = "PROVIDER_SETTLED_ONLY"
    else:
        settlement_status = "NOT_APPLICABLE"

    timed_out = any(a.get("transport") == "TIMEOUT" for a in attempts)
    if recovery_effects:
        control_action = "RECOVER_AND_BLOCK"
    elif not read_fresh or not consistent:
        control_action = "BOUNDED_UNKNOWN"
    elif timed_out and caused:
        control_action = "READBACK_NO_RETRY"
    elif timed_out:
        control_action = "RETRY_SAFE"
    elif rejects:
        control_action = "BLOCK_DISPUTED"
    else:
        control_action = "OBSERVE"

    occurrences = []
    role_assignments = []
    for attempt in attempts:
        occurrences.append(
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
                    if attempt["id"] in authorized_attempt_ids
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for transition in transitions:
        occurrences.append(
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
                    if transition in counts_effects
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for event in adoption_store.get("events", []):
        occurrences.append(
            {
                "occurrence_id": event["occurrence"],
                "native_kind": "OPERATIONAL_USE",
                "object": event["object"],
            }
        )
        role_assignments.append(
            {
                "subject_kind": "Occurrence",
                "subject_id": event["occurrence"],
                "episode": packet["world_token"],
                "role": "Adoption",
                "status": "QUALIFIES" if event in adopted else "DOES_NOT_QUALIFY",
            }
        )
    for act in acceptance_store.get("acts", []):
        occurrences.append(
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
                    if act in qualified_acceptance
                    else "DOES_NOT_QUALIFY"
                ),
            }
        )
    for index, transition in enumerate(settlement_store.get("transitions", [])):
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
        "implementation": "strong_center",
        "raw_occurrences": occurrences,
        "role_assignments": role_assignments,
        "episode_binding": {
            "exact_object": exact_object,
            "bound_effect_ids": [t["occurrence"] for t in caused],
        },
        "authority": {
            "stratum": authority.get("authority_stratum"),
            "authorized_attempt_ids": authorized_attempt_ids,
            "qualified_acceptance_ids": [a["occurrence"] for a in qualified_acceptance],
        },
        "counts_toward_q": {
            "effect_ids": [t["occurrence"] for t in counts_effects],
            "adoption_ids": [e["occurrence"] for e in adopted],
            "acceptance_status": acceptance_status,
            "settlement_status": settlement_status,
        },
        "recovery_relevance": {
            "required": bool(recovery_effects),
            "effect_ids": [t["occurrence"] for t in recovery_effects],
        },
        "causal_attribution": (
            "EXACT_ATTEMPT"
            if caused
            else (
                "EXACT_ATTEMPT_WRONG_TARGET"
                if any(t.get("operation_id") in current_attempt_ids for t in transitions)
                else ("PREEXISTING_OR_OTHER" if exact_transitions else "NO_EFFECT")
            )
        ),
        "consistent_cut": consistent,
        "read_fresh": read_fresh,
        "control_action": control_action,
        "graph_views": {
            "occurrence_provenance": [x["occurrence_id"] for x in occurrences],
            "authority_qualification": authorized_attempt_ids
            + [a["occurrence"] for a in qualified_acceptance],
            "obligation_control": phases,
        },
        "worker_cost": {"compute_units": 5, "hitl_calls": 0, "added_latency_ms": 1},
    }


if __name__ == "__main__":
    print(json.dumps(decide(json.load(sys.stdin)), ensure_ascii=False, sort_keys=True))
