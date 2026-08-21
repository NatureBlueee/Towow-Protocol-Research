from __future__ import annotations

"""Standalone owner service for the CE-001 G1 process-boundary run.

This file deliberately has no package imports.  It is launched with an
isolated Python interpreter and owns only owner records/operator state.  It
never receives evaluator expected records or either benchmark denominator.
"""

from copy import deepcopy
import hashlib
import json
import os
import sys
from typing import Any


SYNTHETIC_OWNER_SOURCE = "CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_message() -> dict[str, Any] | None:
    raw = sys.stdin.buffer.readline()
    if not raw:
        return None
    return json.loads(raw)


def write_message(value: dict[str, Any]) -> None:
    sys.stdout.buffer.write(canonical_bytes(value) + b"\n")
    sys.stdout.buffer.flush()


def issue(
    record: dict[str, Any],
    failure_injection: str | None,
    *,
    request_hash: str,
    owner_state_version: int,
    launch_binding: dict[str, str],
) -> dict[str, Any]:
    fields = {
        key: deepcopy(record[key])
        for key in (
            "evidence_id",
            "episode_id",
            "kind",
            "subject_id",
            "candidate_id",
            "issuer_id",
            "authority_id",
            "source_id",
            "recipient_id",
            "purpose",
            "scope_version",
            "observed_at",
            "existed_at_t0",
            "disclosure_allowed",
            "current",
            "payload",
            "via_operator",
        )
    }
    fields["request_hash"] = request_hash
    fields["owner_state_version"] = owner_state_version
    fields["origin_process_id"] = os.getpid()
    fields["owner_source_type"] = launch_binding["source_type"]
    fields["owner_source_instance_id"] = launch_binding["source_instance_id"]
    fields["owner_state_instance_id"] = launch_binding["state_instance_id"]
    fields["owner_process_instance_id"] = launch_binding["process_instance_id"]
    if failure_injection == "WRONG_AUTHORITY" and fields["kind"] == "partner":
        fields["authority_id"] = "controller-admin"
    elif failure_injection == "SOURCE_ALIAS" and fields["kind"] == "partner":
        fields["source_id"] = "alias-of-resource-ledger"
    elif failure_injection == "TRUTH_TRANSPLANT" and fields["kind"] == "candidate":
        fields["episode_id"] = "E0-PLATFORM-DIRECT"
    evidence_hash = digest(fields)
    event = {**fields, "evidence_hash": evidence_hash}
    if failure_injection == "TAMPER_PAYLOAD" and fields["kind"] == "resource":
        event["payload"] = {
            **event["payload"],
            "object_id": "Venue-V:Circuit-C8",
        }
    return event


def main() -> None:
    init = read_message()
    if init is None or init.get("type") != "OWNER_INIT":
        raise SystemExit("OWNER_INIT required")
    interface = deepcopy(init["interface"])
    active_records = list(deepcopy(init["records"]))
    operators = tuple(deepcopy(init["operators"]))
    allow_t0_queries = bool(init["allow_t0_queries"])
    allow_operators = bool(init["allow_operators"])
    removed_operator = init.get("removed_operator")
    reversed_operator = init.get("reversed_operator")
    failure_injection = init.get("failure_injection")
    launch_binding = deepcopy(init["controller_assigned_launch_binding"])
    if launch_binding["source_type"] != SYNTHETIC_OWNER_SOURCE:
        raise SystemExit("synthetic owner source type required")
    query_count = 0
    owner_state_version = 1
    ready_pid = 424242 if failure_injection == "OWNER_PID_MISMATCH" else os.getpid()
    write_message(
        {
            "type": "OWNER_READY",
            "pid": ready_pid,
            "source_type": launch_binding["source_type"],
            "source_instance_id": launch_binding["source_instance_id"],
            "state_instance_id": launch_binding["state_instance_id"],
            "process_instance_id": launch_binding["process_instance_id"],
            "state_contract": "OWNER_RECORDS_ONLY_NO_EVALUATOR_OR_DENOMINATORS",
        }
    )

    while True:
        request = read_message()
        if request is None:
            return
        request_type = request.get("type")
        if request_type == "STOP":
            write_message(
                {
                    "type": "OWNER_STOPPED",
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                }
            )
            return
        if request_type == "APPLY_OPERATOR":
            operator_id = request.get("operator_id")
            if not allow_operators:
                write_message(
                    {
                        "type": "OPERATOR_RESPONSE",
                        "status": "BLOCKED",
                        "operator_id": operator_id,
                        "origin_attestation": {
                            "pid": os.getpid(),
                            **launch_binding,
                            "owner_state_version": owner_state_version,
                        },
                    }
                )
                continue
            spec = next(
                (
                    operator
                    for operator in operators
                    if operator["operator_id"] == operator_id
                ),
                None,
            )
            if spec is None:
                write_message(
                    {
                        "type": "OPERATOR_RESPONSE",
                        "status": "UNKNOWN_OPERATOR",
                        "operator_id": operator_id,
                        "origin_attestation": {
                            "pid": os.getpid(),
                            **launch_binding,
                            "owner_state_version": owner_state_version,
                        },
                    }
                )
                continue
            if operator_id == removed_operator:
                write_message(
                    {
                        "type": "OPERATOR_RESPONSE",
                        "status": "REMOVED",
                        "operator_id": operator_id,
                        "origin_attestation": {
                            "pid": os.getpid(),
                            **launch_binding,
                            "owner_state_version": owner_state_version,
                        },
                    }
                )
                continue
            mode = "REVERSED" if operator_id == reversed_operator else "APPLIED"
            created = deepcopy(spec["created_record"])
            if mode == "REVERSED":
                created["current"] = False
                created["evidence_id"] += "-REVERSED"
            active_records.append(created)
            owner_state_version += 1
            write_message(
                {
                    "type": "OPERATOR_RESPONSE",
                    "status": mode,
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                    "operator_event": {
                        "operator_id": operator_id,
                        "operator_type": spec["operator_type"],
                        "mode": mode,
                        "owner_id": spec["owner_id"],
                        "authority_id": spec["authority_id"],
                        "created_evidence_ids": [created["evidence_id"]],
                    },
                }
            )
            continue
        if request_type != "DISCOVER":
            write_message(
                {
                    "type": "DISCOVERY_RESPONSE",
                    "status": "INVALID_REQUEST",
                    "events": [],
                    "refusals": [],
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                }
            )
            continue

        query_count += 1
        owner_state_version += 1
        kind = request.get("kind")
        predicates = request.get("predicates")
        api = interface["discovery_api"]
        expected_predicates = {
            "q_version": interface["q_version"],
            "object_id": interface["object_id"],
            "deadline": interface["constraints"]["deadline"],
            "power_kw": interface["constraints"]["power_kw"],
            "exact_target_only": interface["constraints"]["exact_target_only"],
        }
        if kind not in api["query_kinds"] or query_count > api["max_queries"]:
            write_message(
                {
                    "type": "DISCOVERY_RESPONSE",
                    "status": "OUTSIDE_ENVELOPE",
                    "events": [],
                    "refusals": [],
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                }
            )
            continue
        if predicates != expected_predicates:
            write_message(
                {
                    "type": "DISCOVERY_RESPONSE",
                    "status": "SCOPE_MISMATCH",
                    "events": [],
                    "refusals": [],
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                }
            )
            continue
        if not allow_t0_queries:
            write_message(
                {
                    "type": "DISCOVERY_RESPONSE",
                    "status": "QUERY_BLOCKED",
                    "events": [],
                    "refusals": [],
                    "origin_attestation": {
                        "pid": os.getpid(),
                        **launch_binding,
                        "owner_state_version": owner_state_version,
                    },
                }
            )
            continue

        records = [
            record
            for record in active_records
            if record["kind"] == kind
            and record["payload"].get("q_version") == predicates["q_version"]
            and record["payload"].get("object_id") == predicates["object_id"]
        ]
        events: list[dict[str, Any]] = []
        refusals: list[dict[str, Any]] = []
        for record in records:
            if record["response"] == "REFUSED" or not record["disclosure_allowed"]:
                refusals.append(
                    {
                        "kind": kind,
                        "issuer_id": record["issuer_id"],
                        "status": (
                            "REFUSED"
                            if record["response"] == "REFUSED"
                            else "DISCLOSURE_NOT_ALLOWED"
                        ),
                    }
                )
                continue
            request_hash = hashlib.sha256(
                canonical_bytes(request) + b"\n"
            ).hexdigest()
            event = issue(
                record,
                failure_injection,
                request_hash=request_hash,
                owner_state_version=owner_state_version,
                launch_binding=launch_binding,
            )
            if (
                failure_injection == "ORIGIN_SELF_REPORT_INCONSISTENCY"
                and not events
            ):
                unsigned = {
                    key: value
                    for key, value in event.items()
                    if key != "evidence_hash"
                }
                unsigned["origin_process_id"] = 424242
                event = {**unsigned, "evidence_hash": digest(unsigned)}
            if failure_injection == "WRONG_SOURCE_INSTANCE" and not events:
                unsigned = {
                    key: value
                    for key, value in event.items()
                    if key != "evidence_hash"
                }
                unsigned["owner_source_instance_id"] = "WRONG_SOURCE_INSTANCE"
                event = {**unsigned, "evidence_hash": digest(unsigned)}
            events.append(event)
        origin_attestation = {
            "pid": os.getpid(),
            **launch_binding,
            "owner_state_version": owner_state_version,
        }
        write_message(
            {
                "type": "DISCOVERY_RESPONSE",
                "status": "OK",
                "events": events,
                "refusals": refusals,
                "origin_attestation": origin_attestation,
            }
        )


if __name__ == "__main__":
    main()
