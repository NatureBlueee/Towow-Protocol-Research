#!/usr/bin/env python3
"""Uniform metered evidence API for every Wave-007-C strategy."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_EVIDENCE = BASE_DIR / "fixtures" / "evidence.json"


def load_json(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("JSON top level must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class EvidenceAPI:
    """Read-only evidence access plus independently metered verification."""

    def __init__(
        self,
        database: dict[str, Any],
        world_token: str,
        strategy_label: str,
    ) -> None:
        if world_token not in database["worlds"]:
            raise KeyError("unknown opaque world token")
        self._database = database
        self._world_token = world_token
        self._strategy_label = strategy_label
        self._log: list[dict[str, Any]] = []

    @property
    def operation_log(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._log)

    def _append(
        self,
        operation: str,
        *,
        evidence_type: str,
        record_id: str | None = None,
        byte_count: int = 0,
        latency_ms: float = 0.0,
        success: bool,
        retry: bool = False,
        disclosure_units: float = 0.0,
        observation: str | None = None,
    ) -> None:
        self._log.append({
            "sequence": len(self._log) + 1,
            "strategy_label": self._strategy_label,
            "operation": operation,
            "evidence_type": evidence_type,
            "record_id": record_id,
            "bytes": byte_count,
            "latency_ms": latency_ms,
            "success": success,
            "retry": retry,
            "disclosure_units": disclosure_units,
            "observation": observation,
        })

    def get_request_context(self) -> dict[str, Any]:
        value = copy.deepcopy(
            self._database["worlds"][self._world_token]["request"]
        )
        encoded = canonical_bytes(value)
        self._append(
            "READ_REQUEST_CONTEXT",
            evidence_type="request_context",
            byte_count=len(encoded),
            latency_ms=1.0 + len(encoded) / 2000.0,
            success=True,
            observation="PRESENT",
        )
        return value

    def read(
        self,
        evidence_type: str,
        *,
        retry: bool = False,
    ) -> dict[str, Any]:
        evidence = self._database["worlds"][self._world_token]["evidence"]
        response = copy.deepcopy(evidence.get(
            evidence_type,
            {"observation": "UNKNOWN"},
        ))
        encoded = canonical_bytes(response)
        records = []
        if isinstance(response.get("record"), dict):
            records.append(response["record"])
        if isinstance(response.get("records"), list):
            records.extend(
                row for row in response["records"] if isinstance(row, dict)
            )
        disclosure = sum(
            float(record.get("disclosure_units", 0.0))
            for record in records
        )
        observation = response.get("observation", "UNKNOWN")
        self._append(
            "READ_EVIDENCE",
            evidence_type=evidence_type,
            byte_count=len(encoded),
            latency_ms=2.0 + len(encoded) / 1500.0,
            success=observation != "UNKNOWN",
            retry=retry,
            disclosure_units=disclosure,
            observation=observation,
        )
        return response

    def verify_signature(self, record: dict[str, Any]) -> bool:
        signature_hex = record.get("signature_hex")
        issuer = record.get("issuer")
        unsigned = {
            key: value for key, value in record.items()
            if key != "signature_hex"
        }
        success = False
        try:
            public_hex = self._database["public_keys"][issuer]
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_hex)
            ).verify(
                bytes.fromhex(signature_hex),
                canonical_bytes(unsigned),
            )
            success = True
        except (
            KeyError,
            TypeError,
            ValueError,
            InvalidSignature,
        ):
            success = False
        self._append(
            "VERIFY_SIGNATURE",
            evidence_type=str(record.get("evidence_type", "unknown")),
            record_id=record.get("record_id"),
            byte_count=len(canonical_bytes(record)),
            latency_ms=1.5,
            success=success,
        )
        return success

    def validate_binding(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        payload = record.get("payload", {})
        fields = (
            "operation_id",
            "operation_family",
            "key_id",
            "environment",
            "command_hash",
            "semantic_hash",
            "purpose",
            "retention",
        )
        success = all(payload.get(field) == context.get(field) for field in fields)
        self._append(
            "VALIDATE_BINDING",
            evidence_type=str(record.get("evidence_type", "unknown")),
            record_id=record.get("record_id"),
            latency_ms=0.5,
            success=success,
        )
        return success

    def validate_observation_binding(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        payload = record.get("payload", {})
        fields = (
            "operation_id",
            "operation_family",
            "key_id",
            "environment",
            "command_hash",
            "semantic_hash",
            "purpose",
            "retention",
        )
        success = all(
            payload.get(field) == context.get(field) for field in fields
        )
        self._append(
            "VALIDATE_OBSERVATION_BINDING",
            evidence_type=str(record.get("evidence_type", "observation")),
            record_id=record.get("record_id"),
            latency_ms=0.25,
            success=success,
        )
        return success

    def validate_freshness(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
        *,
        max_age: int,
    ) -> bool:
        issued = record.get("payload", {}).get("issued_step")
        success = (
            isinstance(issued, int)
            and 0 <= context["decision_step"] - issued <= max_age
        )
        self._append(
            "VALIDATE_FRESHNESS",
            evidence_type=str(record.get("evidence_type", "unknown")),
            record_id=record.get("record_id"),
            latency_ms=0.25,
            success=success,
        )
        return success

    def validate_authority(
        self,
        record: dict[str, Any],
        authority_record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        payload = record.get("payload", {})
        authority = authority_record.get("payload", {})
        success = (
            authority.get("subject") == payload.get("authority_subject")
            and authority.get("status") == "ACTIVE"
            and authority.get("key_id") == context["key_id"]
        )
        self._append(
            "VALIDATE_AUTHORITY",
            evidence_type=str(record.get("evidence_type", "unknown")),
            record_id=record.get("record_id"),
            latency_ms=0.5,
            success=success,
            observation=authority.get("status"),
        )
        return success


def reconstruct_cost(
    operation_log: list[dict[str, Any]],
    cost_model: dict[str, float],
) -> dict[str, float]:
    operations = len(operation_log)
    byte_count = sum(row["bytes"] for row in operation_log)
    latency = sum(row["latency_ms"] for row in operation_log)
    disclosure = sum(row["disclosure_units"] for row in operation_log)
    retries = sum(bool(row["retry"]) for row in operation_log)
    total = (
        operations * cost_model["operation_cost"]
        + byte_count * cost_model["byte_cost"]
        + latency * cost_model["latency_ms_cost"]
        + disclosure * cost_model["disclosure_unit_cost"]
        + retries * cost_model["retry_cost"]
    )
    return {
        "api_operations": operations,
        "bytes": byte_count,
        "latency_ms": round(latency, 6),
        "disclosure_units": round(disclosure, 6),
        "retries": retries,
        "total_evidence_cost": round(total, 6),
    }
