#!/usr/bin/env python3
"""Reliance strategies that can access evidence only through EvidenceAPI."""

from __future__ import annotations

from typing import Any, Callable

from evidence_api import EvidenceAPI


def _epistemic_response(
    api: EvidenceAPI,
    response: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any] | None:
    observation = response.get("observation", "UNKNOWN")
    if observation == "PRESENT":
        return None
    record = response.get("record")
    if observation in {"REFUSE", "ABSENT"} and isinstance(record, dict):
        if (
            api.verify_signature(record)
            and api.validate_observation_binding(record, context)
            and api.validate_freshness(record, context, max_age=1)
        ):
            return {
                "rely": False,
                "decision_state": observation,
                "reason": f"signed_{observation.lower()}",
            }
    return {
        "rely": False,
        "decision_state": "UNKNOWN",
        "reason": "evidence_missing_or_invalid_observation",
    }


def _authority(
    api: EvidenceAPI,
    record: dict[str, Any],
    context: dict[str, Any],
) -> tuple[bool, str]:
    response = api.read("authority_status")
    epistemic = _epistemic_response(api, response, context)
    if epistemic:
        return False, epistemic["decision_state"]
    authority_record = response["record"]
    if not api.verify_signature(authority_record):
        return False, "UNKNOWN"
    if not api.validate_freshness(
        authority_record, context, max_age=1
    ):
        return False, "UNKNOWN"
    if not api.validate_authority(record, authority_record, context):
        status = authority_record.get("payload", {}).get("status")
        return False, "REFUSE" if status == "REVOKED" else "UNKNOWN"
    return True, "PRESENT"


def _validate(
    api: EvidenceAPI,
    record: dict[str, Any],
    context: dict[str, Any],
    *,
    max_age: int,
) -> tuple[bool, str]:
    if not api.verify_signature(record):
        return False, "UNKNOWN"
    if not api.validate_binding(record, context):
        return False, "UNKNOWN"
    if not api.validate_freshness(record, context, max_age=max_age):
        return False, "UNKNOWN"
    return _authority(api, record, context)


def declaration(api: EvidenceAPI) -> dict[str, Any]:
    implementation_id = "IMPL_DECLARATION"
    context = api.get_request_context()
    response = api.read("declaration")
    epistemic = _epistemic_response(api, response, context)
    if epistemic:
        return {**epistemic, "implementation_id": implementation_id}
    record = response["record"]
    valid, state = _validate(api, record, context, max_age=10)
    rely = bool(valid and record["payload"].get("result") == "SUCCESS")
    return {
        "implementation_id": implementation_id,
        "rely": rely,
        "decision_state": (
            "RELY" if rely
            else "OBSERVED_FAILURE" if valid
            else state
        ),
        "reason": "verified_current_declaration" if rely else "declaration_invalid",
    }


def latest_probe(api: EvidenceAPI) -> dict[str, Any]:
    implementation_id = "IMPL_LATEST_PROBE"
    context = api.get_request_context()
    response = api.read("probe")
    epistemic = _epistemic_response(api, response, context)
    if epistemic:
        return {**epistemic, "implementation_id": implementation_id}
    record = response["record"]
    valid, state = _validate(api, record, context, max_age=2)
    payload = record["payload"]
    rely = bool(
        valid
        and payload.get("result") == "SUCCESS"
        and payload.get("latency_ms", context["deadline_ms"] + 1)
        <= context["deadline_ms"]
    )
    return {
        "implementation_id": implementation_id,
        "rely": rely,
        "decision_state": (
            "RELY" if rely
            else "OBSERVED_FAILURE" if valid
            else state
        ),
        "reason": "verified_fresh_exact_probe" if rely else "probe_invalid",
    }


def receipt_window(api: EvidenceAPI) -> dict[str, Any]:
    implementation_id = "IMPL_RECEIPT_WINDOW"
    context = api.get_request_context()
    response = api.read("receipt_history")
    epistemic = _epistemic_response(api, response, context)
    if epistemic:
        return {**epistemic, "implementation_id": implementation_id}
    records = response.get("records", [])
    if len(records) != 3:
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": "UNKNOWN",
            "reason": "receipt_window_incomplete",
        }
    record_ids = [record.get("record_id") for record in records]
    if (
        any(not isinstance(record_id, str) for record_id in record_ids)
        or len(set(record_ids)) != len(record_ids)
    ):
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": "UNKNOWN",
            "reason": "receipt_window_not_unique",
        }
    for record in records:
        valid, state = _validate(api, record, context, max_age=5)
        payload = record.get("payload", {})
        if not (
            valid
            and payload.get("result") == "SUCCESS"
            and payload.get("recipient_ack") is True
            and payload.get("external_anchor") is True
            and payload.get("latency_ms", context["deadline_ms"] + 1)
            <= context["deadline_ms"]
        ):
            return {
                "implementation_id": implementation_id,
                "rely": False,
                "decision_state": (
                    "OBSERVED_FAILURE" if valid else state
                ),
                "reason": "receipt_window_invalid",
            }
    return {
        "implementation_id": implementation_id,
        "rely": True,
        "decision_state": "RELY",
        "reason": "three_verified_current_receipts",
    }


def sla_recovery(api: EvidenceAPI) -> dict[str, Any]:
    implementation_id = "IMPL_SLA_RECOVERY"
    context = api.get_request_context()
    sla_response = api.read("sla")
    epistemic = _epistemic_response(api, sla_response, context)
    if epistemic:
        return {**epistemic, "implementation_id": implementation_id}
    sla_record = sla_response["record"]
    valid, state = _validate(api, sla_record, context, max_age=5)
    if not valid:
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": state,
            "reason": "sla_invalid",
        }
    if sla_record["payload"].get("status") != "IN_FORCE":
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": "OBSERVED_CONSTRAINT",
            "reason": "sla_not_in_force",
        }
    health_response = api.read("health")
    epistemic = _epistemic_response(api, health_response, context)
    if epistemic:
        return {**epistemic, "implementation_id": implementation_id}
    health_record = health_response["record"]
    health_valid, health_state = _validate(
        api, health_record, context, max_age=2
    )
    if not health_valid:
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": health_state,
            "reason": "health_invalid",
        }
    health = health_record["payload"].get("health")
    if health == "RECOVERED":
        recovery_response = api.read("recovery_receipt")
        if recovery_response.get("observation") == "UNKNOWN":
            recovery_response = api.read("recovery_receipt", retry=True)
        epistemic = _epistemic_response(api, recovery_response, context)
        if epistemic:
            return {**epistemic, "implementation_id": implementation_id}
        recovery = recovery_response["record"]
        recovery_valid, recovery_state = _validate(
            api, recovery, context, max_age=1
        )
        if not (
            recovery_valid
            and recovery["payload"].get("recovered") is True
            and recovery["payload"].get("prior_revocation_bound") is True
        ):
            return {
                "implementation_id": implementation_id,
                "rely": False,
                "decision_state": recovery_state,
                "reason": "recovery_receipt_invalid",
            }
    elif health != "GREEN":
        return {
            "implementation_id": implementation_id,
            "rely": False,
            "decision_state": "OBSERVED_FAILURE",
            "reason": "health_not_green",
        }
    payload = sla_record["payload"]
    rely = bool(
        payload.get("status") == "IN_FORCE"
        and bool(payload.get("recovery_owner"))
        and payload.get("max_latency_ms", context["deadline_ms"] + 1)
        <= context["deadline_ms"]
    )
    return {
        "implementation_id": implementation_id,
        "rely": rely,
        "decision_state": "RELY" if rely else "UNKNOWN",
        "reason": "verified_sla_health_recovery" if rely else "sla_constraints_failed",
    }


STRATEGIES: dict[str, Callable[[EvidenceAPI], dict[str, Any]]] = {
    "DECLARATION": declaration,
    "LATEST_PROBE": latest_probe,
    "RECEIPT_WINDOW": receipt_window,
    "SLA_RECOVERY": sla_recovery,
}
