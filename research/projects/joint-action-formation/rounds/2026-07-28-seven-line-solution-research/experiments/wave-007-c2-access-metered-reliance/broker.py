#!/usr/bin/env python3
"""Parent-owned evidence broker and cost ledger for Wave-007-C2."""

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


class EvidenceBroker:
    """Lives only in the parent process; worker receives JSON/RPC responses."""

    ALLOWED_METHODS = {
        "get_request_context",
        "read",
        "verify_signature",
        "validate_binding",
        "validate_observation_binding",
        "validate_freshness",
        "validate_authority",
    }

    def __init__(
        self,
        database: dict[str, Any],
        world_token: str,
        registry_owner: str,
        display_label: str,
    ) -> None:
        if world_token not in database["worlds"]:
            raise KeyError("unknown opaque world token")
        self.__database = database
        self.__world_token = world_token
        self.__registry_owner = registry_owner
        self.__display_label = display_label
        self.__operation_log: list[dict[str, Any]] = []

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
        self.__operation_log.append({
            "sequence": len(self.__operation_log) + 1,
            "registry_owner": self.__registry_owner,
            "display_label": self.__display_label,
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

    def snapshot_operation_log(self) -> list[dict[str, Any]]:
        """Parent runner calls this after the worker exits."""
        return copy.deepcopy(self.__operation_log)

    def _trusted_request(self) -> dict[str, Any]:
        return self.__database["worlds"][
            self.__world_token
        ]["request"]

    def _context_matches_trusted(
        self, supplied: dict[str, Any]
    ) -> bool:
        return canonical_bytes(supplied) == canonical_bytes(
            self._trusted_request()
        )

    def handle(self, method: str, arguments: dict[str, Any]) -> Any:
        if method not in self.ALLOWED_METHODS:
            self._append(
                "DENIED_RPC",
                evidence_type="broker_control",
                byte_count=len(canonical_bytes({
                    "method": method,
                    "arguments": arguments,
                })),
                latency_ms=0.1,
                success=False,
                observation="REFUSE",
            )
            raise PermissionError(f"RPC method is not allowed: {method}")
        return getattr(self, method)(**arguments)

    def get_request_context(self) -> dict[str, Any]:
        value = copy.deepcopy(
            self.__database["worlds"][self.__world_token]["request"]
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
        retry: bool = False,
    ) -> dict[str, Any]:
        evidence = self.__database["worlds"][
            self.__world_token
        ]["evidence"]
        response = copy.deepcopy(evidence.get(
            evidence_type, {"observation": "UNKNOWN"}
        ))
        encoded = canonical_bytes(response)
        records: list[dict[str, Any]] = []
        if isinstance(response.get("record"), dict):
            records.append(response["record"])
        if isinstance(response.get("records"), list):
            records.extend(
                record for record in response["records"]
                if isinstance(record, dict)
            )
        observation = response.get("observation", "UNKNOWN")
        self._append(
            "READ_EVIDENCE",
            evidence_type=evidence_type,
            byte_count=len(encoded),
            latency_ms=2.0 + len(encoded) / 1500.0,
            success=observation != "UNKNOWN",
            retry=retry,
            disclosure_units=sum(
                float(record.get("disclosure_units", 0.0))
                for record in records
            ),
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
        try:
            public_hex = self.__database["public_keys"][issuer]
            Ed25519PublicKey.from_public_bytes(
                bytes.fromhex(public_hex)
            ).verify(
                bytes.fromhex(signature_hex),
                canonical_bytes(unsigned),
            )
            success = True
        except (KeyError, TypeError, ValueError, InvalidSignature):
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
        trusted = self._trusted_request()
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
        success = (
            self._context_matches_trusted(context)
            and all(
                payload.get(field) == trusted.get(field)
                for field in fields
            )
        )
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
        trusted = self._trusted_request()
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
        success = (
            self._context_matches_trusted(context)
            and all(
                payload.get(field) == trusted.get(field)
                for field in fields
            )
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
        max_age: int,
    ) -> bool:
        issued = record.get("payload", {}).get("issued_step")
        trusted = self._trusted_request()
        success = (
            self._context_matches_trusted(context)
            and
            isinstance(issued, int)
            and 0 <= trusted["decision_step"] - issued <= max_age
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
        trusted = self._trusted_request()
        trusted_fields = (
            "authority_head",
            "authority_epoch",
            "authority_contract_version",
        )
        success = (
            self._context_matches_trusted(context)
            and
            authority.get("subject") == payload.get("authority_subject")
            and authority.get("status") == "ACTIVE"
            and authority.get("key_id") == trusted["key_id"]
            and all(
                authority.get(field) == trusted.get(field)
                for field in trusted_fields
            )
        )
        self._append(
            "VALIDATE_AUTHORITY_HEAD",
            evidence_type=str(record.get("evidence_type", "unknown")),
            record_id=record.get("record_id"),
            latency_ms=0.75,
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
