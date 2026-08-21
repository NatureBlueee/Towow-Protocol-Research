#!/usr/bin/env python3
"""Build signed public evidence without exposing private keys to strategies."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT = BASE_DIR / "fixtures" / "evidence.json"
ISSUERS = [
    "CAPABILITY-PROVIDER",
    "PROBE-SERVICE",
    "SIM-RECIPIENT",
    "ANCHOR-W6",
    "SLA-OPERATOR",
    "HEALTH-SERVICE",
    "AUTHORITY-REGISTRY",
]


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def private_key(issuer: str) -> Ed25519PrivateKey:
    seed = hashlib.sha256(f"wave007c::{issuer}".encode("utf-8")).digest()
    return Ed25519PrivateKey.from_private_bytes(seed)


def public_key_hex(issuer: str) -> str:
    return private_key(issuer).public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


def signed_record(
    record_id: str,
    issuer: str,
    evidence_type: str,
    payload: dict[str, Any],
    disclosure_units: float,
) -> dict[str, Any]:
    envelope = {
        "record_id": record_id,
        "issuer": issuer,
        "evidence_type": evidence_type,
        "payload": payload,
        "disclosure_units": disclosure_units,
    }
    envelope["signature_hex"] = private_key(issuer).sign(
        canonical_bytes(envelope)
    ).hex()
    return envelope


def context(
    token: str,
    *,
    step: int = 7,
    key_id: str = "RECIPIENT-KEY-v1",
    environment: str = "SIM-ENV-A",
) -> dict[str, Any]:
    return {
        "world_token": token,
        "operation_id": "RUN-STERILE-ROUTE-SIM-v1",
        "operation_family": "sterile-route-simulation",
        "key_id": key_id,
        "environment": environment,
        "command_hash": "CMD-W7C-V1",
        "semantic_hash": "SEM-W7C-V1",
        "purpose": "sterile-route-simulation",
        "retention": "PT7M",
        "deadline_ms": 250,
        "decision_step": step,
    }


def bound_payload(
    ctx: dict[str, Any],
    *,
    issued_step: int,
    result: str = "SUCCESS",
    latency_ms: int = 100,
) -> dict[str, Any]:
    return {
        "operation_id": ctx["operation_id"],
        "operation_family": ctx["operation_family"],
        "key_id": ctx["key_id"],
        "environment": ctx["environment"],
        "command_hash": ctx["command_hash"],
        "semantic_hash": ctx["semantic_hash"],
        "purpose": ctx["purpose"],
        "retention": ctx["retention"],
        "authority_subject": "CAPABILITY-PROVIDER",
        "issued_step": issued_step,
        "result": result,
        "latency_ms": latency_ms,
    }


def present(record: dict[str, Any]) -> dict[str, Any]:
    return {"observation": "PRESENT", "record": record}


def opaque_observation(
    token: str,
    observation: str,
    *,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    record = signed_record(
        f"{token}-OBS-{observation}",
        "AUTHORITY-REGISTRY",
        "observation",
        {
            "observation": observation,
            "operation_id": ctx["operation_id"],
            "operation_family": ctx["operation_family"],
            "key_id": ctx["key_id"],
            "environment": ctx["environment"],
            "command_hash": ctx["command_hash"],
            "semantic_hash": ctx["semantic_hash"],
            "purpose": ctx["purpose"],
            "retention": ctx["retention"],
            "issued_step": ctx["decision_step"],
        },
        0.1,
    )
    return {"observation": observation, "record": record}


def valid_world(
    token: str,
    *,
    step: int = 7,
    key_id: str = "RECIPIENT-KEY-v1",
    request_environment: str = "SIM-ENV-A",
    evidence_environment: str | None = None,
    authority_status: str = "ACTIVE",
    health: str = "GREEN",
    include_recovery: bool = False,
    declaration_result: str = "SUCCESS",
    probe_result: str = "SUCCESS",
    receipt_result: str = "SUCCESS",
    receipt_count: int = 3,
    sla_status: str = "IN_FORCE",
) -> dict[str, Any]:
    ctx = context(
        token,
        step=step,
        key_id=key_id,
        environment=request_environment,
    )
    evidence_ctx = dict(ctx)
    evidence_ctx["environment"] = (
        evidence_environment
        if evidence_environment is not None
        else request_environment
    )
    evidence_step = step if step == 7 else step - 1
    declaration = signed_record(
        f"{token}-DECL",
        "CAPABILITY-PROVIDER",
        "declaration",
        bound_payload(
            evidence_ctx,
            issued_step=evidence_step,
            result=declaration_result,
        ),
        0.2,
    )
    probe = signed_record(
        f"{token}-PROBE",
        "PROBE-SERVICE",
        "probe",
        bound_payload(
            evidence_ctx,
            issued_step=evidence_step,
            result=probe_result,
            latency_ms=90,
        ),
        0.4,
    )
    receipts = [
        signed_record(
            f"{token}-RECEIPT-{index}",
            "SIM-RECIPIENT",
            "receipt",
            {
                **bound_payload(
                    evidence_ctx,
                    issued_step=max(0, evidence_step - (2 - index)),
                    latency_ms=100 + index * 5,
                ),
                "recipient_ack": True,
                "external_anchor": True,
            },
            0.35,
        )
        for index in range(receipt_count)
    ]
    sla = signed_record(
        f"{token}-SLA",
        "SLA-OPERATOR",
        "sla",
        {
            **bound_payload(evidence_ctx, issued_step=evidence_step),
            "status": sla_status,
            "max_latency_ms": 180,
            "recovery_owner": "SIM-RECIPIENT-OPS",
        },
        0.5,
    )
    health_record = signed_record(
        f"{token}-HEALTH",
        "HEALTH-SERVICE",
        "health",
        {
            **bound_payload(evidence_ctx, issued_step=evidence_step),
            "health": health,
        },
        0.25,
    )
    status_record = signed_record(
        f"{token}-AUTHORITY",
        "AUTHORITY-REGISTRY",
        "authority_status",
        {
            "subject": "CAPABILITY-PROVIDER",
            "status": authority_status,
            "key_id": key_id,
            "issued_step": step,
        },
        0.1,
    )
    evidence = {
        "declaration": present(declaration),
        "probe": present(probe),
        "receipt_history": {
            "observation": "PRESENT",
            "records": receipts,
        },
        "sla": present(sla),
        "health": present(health_record),
        "authority_status": present(status_record),
    }
    if include_recovery:
        evidence["recovery_receipt"] = present(signed_record(
            f"{token}-RECOVERY",
            "AUTHORITY-REGISTRY",
            "recovery_receipt",
            {
                **bound_payload(evidence_ctx, issued_step=step),
                "recovered": True,
                "prior_revocation_bound": True,
            },
            0.3,
        ))
    return {"request": ctx, "evidence": evidence}


def build() -> dict[str, Any]:
    worlds: dict[str, Any] = {}
    worlds["w7c-8f13a0"] = valid_world("w7c-8f13a0")

    absent_ctx = context("w7c-1bc492")
    worlds["w7c-1bc492"] = {
        "request": absent_ctx,
        "evidence": {
            evidence_type: opaque_observation(
                "w7c-1bc492", "ABSENT", ctx=absent_ctx
            )
            for evidence_type in (
                "declaration",
                "probe",
                "receipt_history",
                "sla",
                "health",
                "authority_status",
            )
        },
    }

    worlds["w7c-50de71"] = valid_world("w7c-50de71")
    worlds["w7c-a76e20"] = valid_world(
        "w7c-a76e20",
        step=8,
        authority_status="REVOKED",
        health="RED",
    )
    worlds["w7c-3d9b14"] = valid_world("w7c-3d9b14")
    worlds["w7c-e021f8"] = valid_world(
        "w7c-e021f8",
        request_environment="SIM-ENV-B",
        evidence_environment="SIM-ENV-A",
    )

    refusal_ctx = context("w7c-7aa935")
    worlds["w7c-7aa935"] = {
        "request": refusal_ctx,
        "evidence": {
            evidence_type: opaque_observation(
                "w7c-7aa935", "REFUSE", ctx=refusal_ctx
            )
            for evidence_type in (
                "declaration",
                "probe",
                "receipt_history",
                "sla",
                "health",
                "authority_status",
            )
        },
    }
    worlds["w7c-c6430e"] = valid_world("w7c-c6430e")
    worlds["w7c-926db1"] = valid_world(
        "w7c-926db1",
        step=9,
        key_id="RECIPIENT-KEY-v2",
        health="RECOVERED",
        include_recovery=True,
    )
    worlds["w7c-4ef270"] = valid_world(
        "w7c-4ef270",
        step=9,
        key_id="RECIPIENT-KEY-v2",
        health="RECOVERED",
        include_recovery=False,
    )
    worlds["w7c-f010aa"] = valid_world(
        "w7c-f010aa",
        probe_result="FAILURE",
        health="RED",
    )
    worlds["w7c-332faa"] = valid_world(
        "w7c-332faa",
        probe_result="FAILURE",
    )
    worlds["w7c-610cdd"] = valid_world(
        "w7c-610cdd",
        receipt_count=1,
    )
    worlds["w7c-d2049e"] = valid_world(
        "w7c-d2049e",
        sla_status="EXPIRED",
    )
    worlds["w7c-b1856c"] = {
        "request": context("w7c-b1856c"),
        "evidence": {},
    }
    return {
        "schema_version": "1.0",
        "shared_task_sha256": (
            "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
        ),
        "public_keys": {
            issuer: public_key_hex(issuer) for issuer in ISSUERS
        },
        "worlds": worlds,
    }


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
