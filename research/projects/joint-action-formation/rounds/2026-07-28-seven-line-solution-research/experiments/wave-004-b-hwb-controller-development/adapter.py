#!/usr/bin/env python3
"""Hash-bound adapter from four HW-B holder receipts to Wave-004-A inputs.

The adapter is intentionally explicit. It does not infer that authorization is
execution, and it preserves the source receipt byte hash inside every normalized
holder payload. Reciprocal counterparties remain per-side and use the executor's
COUNTERPARTY_EXCHANGE mode.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROUND_ROOT = HERE.parents[1]
HWB_ROOT = (
    ROUND_ROOT
    / "runs"
    / "wave-003-a-held-out-world"
    / "g1"
    / "t1-hw-b"
)
CONTROLLER_ROOT = HERE.parent / "wave-004-a-controller-executor"

SOURCE_FILES = {
    "HELIOS-44": HWB_ROOT / "candidate-local" / "HELIOS-44.json",
    "ION-06": HWB_ROOT / "candidate-local" / "ION-06.json",
    "JUNIPER-28": HWB_ROOT / "candidate-local" / "JUNIPER-28.json",
    "KITE-15": HWB_ROOT / "candidate-local" / "KITE-15.json",
}

FROZEN_SOURCE_SHA256 = {
    "HELIOS-44": "283be89a5de49c9e023318f4ffdfe32e553409498fde8f28c7fe0ea603d08941",
    "ION-06": "7d21eb56c0724dd22b03981a6daab032a4905b539ae36dbc8febd0cd7e50ef39",
    "JUNIPER-28": "d53836004fd003320fba6bb0f28c83e95a66594d122845ff38f3eaad26884083",
    "KITE-15": "c31ea346b59a5372e0c4295f5dc65da694faa4ae9ace32702e0280e5871f87d1",
}


def load_executor_module():
    spec = importlib.util.spec_from_file_location(
        "wave004a_executor", CONTROLLER_ROOT / "executor.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Wave-004-A executor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXECUTOR = load_executor_module()


def read_source(party: str) -> tuple[dict[str, Any], str]:
    path = SOURCE_FILES[party]
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    expected = FROZEN_SOURCE_SHA256[party]
    if actual != expected:
        raise RuntimeError(
            f"SOURCE_HASH_MISMATCH:{party}:expected={expected}:actual={actual}"
        )
    return json.loads(raw), actual


def _source_binding(party: str, source_hash: str) -> dict[str, Any]:
    return {
        "party": party,
        "relative_path": str(SOURCE_FILES[party].relative_to(ROUND_ROOT)),
        "source_file_sha256": source_hash,
        "binding_type": "EXACT_SOURCE_BYTES",
    }


def _projection_payload(
    *,
    receipt_id: str,
    issuer: str,
    source_hash: str,
    projection: dict[str, Any],
    policy: dict[str, Any],
    source_semantics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "towow.holder-authorization.v1",
        "receipt_id": receipt_id,
        "issuer": issuer,
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "valid_from_step": 2,
        "valid_through_step": 2,
        "status": "AUTHORIZED",
        "revoked": False,
        "authorization_type": "PROJECTION_ROUTE",
        "source_file_sha256": source_hash,
        "source_semantics": source_semantics,
        "projection": projection,
        "policy": policy,
    }


def normalize_direct() -> tuple[dict[str, Any], dict[str, Any]]:
    source, source_hash = read_source("HELIOS-44")
    auth = source["authorized_projection"]
    payload = _projection_payload(
        receipt_id="HWB-AUTH-HELIOS-44",
        issuer="HELIOS-44",
        source_hash=source_hash,
        projection={
            "fact_id": auth["fact_id"],
            "direction": auth["direction"],
            "facet": auth["facet"],
            "compatibility_key": auth["compatibility_key"],
        },
        policy={
            "recipient": auth["recipient"],
            "purpose": auth["purpose"],
            "retention": auth["retention"],
            "max_depth": auth["max_depth"],
            "onward_allowed": auth["onward_disclosure"],
            "budget_units": 1,
        },
        source_semantics={
            "receipt_type": source["receipt_type"],
            "witness_ref": auth["witness_ref"],
            "authorization_is_not_execution": True,
        },
    )
    request = {
        "schema": "towow.controller-request.v1",
        "request_id": "HWB-REQ-HELIOS-DIRECT",
        "idempotency_key": "hwb:2:helios-direct",
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "route_type": "DIRECT_PROJECTION",
        "authorizations": [
            {
                "declared_sha256": EXECUTOR.sha256_value(payload),
                "payload": payload,
            }
        ],
        "route": {
            "projection": {
                "fact_id": auth["fact_id"],
                "direction": auth["direction"],
                "facet": auth["facet"],
                "compatibility_key": auth["compatibility_key"],
            },
            "recipient": auth["recipient"],
            "purpose": auth["purpose"],
            "retention": auth["retention"],
            "depth": 0,
            "budget_units": 1,
        },
    }
    return payload, request


def normalize_derived() -> tuple[dict[str, Any], dict[str, Any]]:
    source, source_hash = read_source("ION-06")
    auth = source["authorized_projection"]
    onward = source["authorized_onward_route"]
    if (
        onward["status"]
        != "AUTHORIZED_DERIVED_RECEIPT_REQUIRED_NOT_FORWARDED"
        or onward["derived_receipt_required"] is not True
    ):
        raise RuntimeError("ION_ONWARD_SOURCE_NOT_AUTHORIZED_AS_EXPECTED")
    payload = _projection_payload(
        receipt_id="HWB-AUTH-ION-06",
        issuer="ION-06",
        source_hash=source_hash,
        projection={
            "fact_id": auth["fact_id"],
            "direction": auth["direction"],
            "facet": auth["facet"],
            "compatibility_key": auth["compatibility_key"],
        },
        policy={
            "recipient": auth["recipient"],
            "purpose": auth["purpose"],
            "retention": auth["retention"],
            "max_depth": auth["max_depth"],
            "onward_allowed": True,
            "budget_units": 1,
            "onward_policy": {
                "source_recipient": onward["sender"],
                "recipient": onward["recipient"],
                "purpose": onward["purpose"],
                "retention": onward["retention"],
                "max_depth": onward["max_depth"],
                "budget_units": 1,
            },
        },
        source_semantics={
            "receipt_type": source["receipt_type"],
            "witness_ref": auth["witness_ref"],
            "derived_receipt_required": True,
            "source_execution_status": "NOT_FORWARDED",
            "authorization_is_not_execution": True,
        },
    )
    projection = {
        "fact_id": auth["fact_id"],
        "direction": auth["direction"],
        "facet": auth["facet"],
        "compatibility_key": auth["compatibility_key"],
    }
    request = {
        "schema": "towow.controller-request.v1",
        "request_id": "HWB-REQ-ION-DERIVED",
        "idempotency_key": "hwb:2:ion-derived",
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "route_type": "DERIVED_ONWARD",
        "authorizations": [
            {
                "declared_sha256": EXECUTOR.sha256_value(payload),
                "payload": payload,
            }
        ],
        "route": {
            "projection": projection,
            "hops": [
                {
                    "recipient": auth["recipient"],
                    "purpose": auth["purpose"],
                    "retention": auth["retention"],
                    "depth": 0,
                    "budget_units": 1,
                },
                {
                    "recipient": onward["recipient"],
                    "purpose": onward["purpose"],
                    "retention": onward["retention"],
                    "depth": 1,
                    "budget_units": 1,
                },
            ],
        },
    }
    return payload, request


def _reciprocal_source(party: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    source, source_hash = read_source(party)
    if party == "JUNIPER-28":
        return source, source["authorization"], source_hash
    return source, source["probe_offer"], source_hash


def normalize_reciprocal() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized = []
    sides = []
    for party, facet in (
        ("JUNIPER-28", "reciprocal-detail-demand"),
        ("KITE-15", "reciprocal-detail-supply"),
    ):
        source, offer, source_hash = _reciprocal_source(party)
        payload = {
            "schema": "towow.holder-authorization.v1",
            "receipt_id": f"HWB-AUTH-{party}",
            "issuer": party,
            "world_id": "T1-HW-20260728-B",
            "evaluation_step": 2,
            "valid_from_step": 2,
            "valid_through_step": 2,
            "status": "AUTHORIZED",
            "revoked": False,
            "authorization_type": "RECIPROCAL_OFFER",
            "source_file_sha256": source_hash,
            "source_semantics": {
                "receipt_type": source["receipt_type"],
                "requested_counterfact_id": offer["requested_counterfact_id"],
                "witness_ref": offer["completion_witness_ref"],
                "source_exchange_status": (
                    source.get("exchange_status")
                    or source.get("status")
                ),
                "authorization_is_not_execution": True,
            },
            "projection": {
                "fact_id": (
                    "F-HWB-JUNIPER-RECIP-DETAIL"
                    if party == "JUNIPER-28"
                    else "F-HWB-KITE-RECIP-DETAIL"
                ),
                "direction": offer["direction"],
                "facet": facet,
                "compatibility_key": offer["compatibility_key"],
            },
            "counterparty_contract": {
                "allowed_counterparties": [offer["counterparty"]],
            },
            "policy": {
                "recipient": offer["counterparty"],
                "purpose": offer["purpose"],
                "retention": offer["retention"],
                "max_depth": 0,
                "onward_allowed": offer["onward_disclosure"],
                "budget_units": 1,
            },
        }
        normalized.append(payload)
        sides.append(
            {
                "receipt_id": payload["receipt_id"],
                "direction": payload["projection"]["direction"],
                "facet": payload["projection"]["facet"],
                "compatibility_key": payload["projection"]["compatibility_key"],
                "counterparty": offer["counterparty"],
            }
        )
    for side, payload in zip(sides, normalized):
        side["delivery"] = {
            "recipient": payload["policy"]["recipient"],
            "purpose": payload["policy"]["purpose"],
            "retention": payload["policy"]["retention"],
            "depth": 0,
        }
    request = {
        "schema": "towow.controller-request.v1",
        "request_id": "HWB-REQ-JUNIPER-KITE-RECIPROCAL",
        "idempotency_key": "hwb:2:juniper-kite-reciprocal",
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "route_type": "RECIPROCAL_EXCHANGE",
        "authorizations": [
            {
                "declared_sha256": EXECUTOR.sha256_value(payload),
                "payload": payload,
            }
            for payload in normalized
        ],
        "route": {
            "delivery_mode": "COUNTERPARTY_EXCHANGE",
            "purpose": "two-sided-route-probe",
            "retention": "PT7M",
            "depth": 0,
            "budget_units_each": 1,
            "sides": sides,
        }
    }
    return normalized, request


def build_contract() -> tuple[dict[str, Any], dict[str, Any]]:
    direct_payload, direct_request = normalize_direct()
    derived_payload, derived_request = normalize_derived()
    reciprocal_payloads, reciprocal_request = normalize_reciprocal()
    payloads = [direct_payload, derived_payload, *reciprocal_payloads]
    contract = {
        "schema": "towow.controller-contract.v1",
        "contract_id": "W4B-HWB-DEVELOPMENT-CONTRACT-001",
        "controller_id": "LOCAL-CONTROLLER-W4A",
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "max_disclosure_units": 10,
        "compatible_facet_pairs": [
            ["reciprocal-detail-demand", "reciprocal-detail-supply"],
        ],
        "trusted_holder_receipts": [
            {
                "receipt_id": payload["receipt_id"],
                "issuer": payload["issuer"],
                "sha256": EXECUTOR.sha256_value(payload),
                "source_file_sha256": payload["source_file_sha256"],
            }
            for payload in payloads
        ],
        "source_authentication": {
            "mode": "FROZEN_TRUSTED_CONTRACT_REGISTRY_SIMULATION",
            "claim": (
                "Normalized payload hashes are frozen and every payload embeds "
                "the exact source file byte hash."
            ),
            "not_claimed": [
                "holder cryptographic signature",
                "recipient-side independent acknowledgement",
                "malicious same-directory process resistance",
                "blind evaluation",
            ],
        },
        "derived_onward_execution_authority": {
            "mode": "TRUSTED_CONTROLLER_DELEGATION_SIMULATION",
            "scope": (
                "The controller may perform the ION-authorized second hop on "
                "behalf of NODE-SILVER-RELAY after binding it to the first hop."
            ),
            "not_claimed": [
                "NODE-SILVER-RELAY independent action",
                "NODE-SILVER-RELAY signed delegation",
                "recipient independent acknowledgement",
            ],
        },
    }
    return contract, {
        "direct": direct_request,
        "derived": derived_request,
        "reciprocal": reciprocal_request,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def materialize() -> None:
    contract, requests = build_contract()
    write_json(HERE / "normalized" / "contract.json", contract)
    for label, request in requests.items():
        write_json(HERE / "normalized" / "inputs" / f"{label}.json", request)
    bindings = {
        "schema": "towow.hwb-source-bindings.v1",
        "world_id": "T1-HW-20260728-B",
        "evaluation_step": 2,
        "bindings": [
            _source_binding(party, FROZEN_SOURCE_SHA256[party])
            for party in SOURCE_FILES
        ],
    }
    write_json(HERE / "source-bindings.json", bindings)


if __name__ == "__main__":
    materialize()
