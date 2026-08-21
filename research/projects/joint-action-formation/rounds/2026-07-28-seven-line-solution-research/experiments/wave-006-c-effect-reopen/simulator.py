#!/usr/bin/env python3
"""Frozen effect ladder and drift scenarios for Wave 006 G6/G7.

This module reuses the public Wave 005-B signature/receipt primitives.  It does
not read HW-C material and does not change the shared operation, truth, or
authority denominator.
"""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


KERNEL = (
    Path(__file__).resolve().parents[1]
    / "wave-005-b-cross-authority-receipts"
)
sys.path.insert(0, str(KERNEL))

from protocol import (  # noqa: E402
    envelope_hash,
    private_key_from_hex,
    sha256_value,
    sign_envelope,
)


SHARED_TASK_ID = "W6-STERILE-ROUTE-SIMULATION-001"
SHARED_TASK_SHA256 = (
    "0cde980b1cd9754d61e1cc2f9478a85c9f587ec5fb5b4e7c07ccb068fbc100a3"
)
WORLD_ID = "W6-STERILE-ROUTE-WORLD"
OPERATION = "RUN-STERILE-ROUTE-SIM-v1"
PURPOSE = "sterile-route-simulation"
RETENTION = "PT7M"
BASE_STEP = 7
TRUTH = {
    "route_status": "STERILE_ROUTE_FEASIBLE",
    "window": "E2-E5",
    "capacity_units": 2,
}
AUTHORITIES = [
    "LAB-SEEK",
    "LAB-OFFER",
    "CONTROLLER-W6",
    "SIM-RECIPIENT",
    "SIM-RECIPIENT-B",
    "SIMULATOR-W6",
    "BENEFICIARY-REVIEWER",
    "ANCHOR-W6",
]


def _seed(authority: str, version: str) -> str:
    return hashlib.sha256(
        f"towow-wave006-effect:{authority}:{version}".encode("utf-8")
    ).hexdigest()


def private_key(authority: str, version: str = "v1"):
    return private_key_from_hex(_seed(authority, version))


def public_key_hex(authority: str, version: str) -> str:
    return (
        private_key(authority, version)
        .public_key()
        .public_bytes(Encoding.Raw, PublicFormat.Raw)
        .hex()
    )


def build_contract(
    *,
    version: str = "v1",
    step: int = BASE_STEP,
    semantic_retention: str = RETENTION,
    environment_version: str = "sterile-sim-env-v1",
    recipient: str = "SIM-RECIPIENT",
    withdrawn: tuple[str, ...] = (),
    holders_revoked: bool = False,
) -> dict[str, Any]:
    key_version = "v1" if version == "v1" else "v2"
    return {
        "schema": "towow.effect-contract.v1",
        "contract_id": f"W6-EFFECT-CONTRACT-{version}",
        "contract_version": version,
        "shared_task_id": SHARED_TASK_ID,
        "shared_task_sha256": SHARED_TASK_SHA256,
        "world_id": WORLD_ID,
        "evaluation_step": step,
        "operation": OPERATION,
        "purpose": PURPOSE,
        "retention": semantic_retention,
        "environment_version": environment_version,
        "recipient": recipient,
        "anchor_genesis": None,
        "holders_revoked": holders_revoked,
        "withdrawn_authorities": list(withdrawn),
        "frozen_truth_sha256": sha256_value(TRUTH),
        "verification_keys": [
            {
                "issuer": authority,
                "key_id": key_version,
                "public_key_hex": public_key_hex(authority, key_version),
                "valid_from_step": 1 if key_version == "v1" else 8,
                "valid_through_step": 7 if key_version == "v1" else 30,
            }
            for authority in AUTHORITIES
        ],
    }


def _sign(
    contract: dict[str, Any],
    issuer: str,
    kind: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    key_id = "v1" if contract["contract_version"] == "v1" else "v2"
    return sign_envelope(
        private_key(issuer, key_id),
        kind=kind,
        issuer=issuer,
        key_id=key_id,
        body=body,
    )


def action_coordinates(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "shared_task_id": SHARED_TASK_ID,
        "world_id": WORLD_ID,
        "evaluation_step": contract["evaluation_step"],
        "operation": OPERATION,
        "purpose": PURPOSE,
        "retention": contract["retention"],
        "environment_version": contract["environment_version"],
        "contract_sha256": sha256_value(contract),
        "action_digest": sha256_value(
            {
                "world_id": WORLD_ID,
                "operation": OPERATION,
                "purpose": PURPOSE,
                "retention": contract["retention"],
                "environment_version": contract["environment_version"],
                "recipient": contract["recipient"],
                "projections": [
                    {
                        "origin": "LAB-SEEK",
                        "facet": "route-constraints",
                        "units": 1,
                    },
                    {
                        "origin": "LAB-OFFER",
                        "facet": "window-capacity",
                        "units": 1,
                    },
                ],
            }
        ),
        "idempotency_key": (
            f"W6-EFFECT-{contract['contract_version']}-"
            f"{contract['recipient']}-{contract['environment_version']}"
        ),
    }


def build_effect(
    contract: dict[str, Any],
    *,
    stop_level: int = 4,
    beneficiary_refusal: bool = False,
    single_side_delivery: bool = False,
) -> dict[str, Any]:
    coords = action_coordinates(contract)
    authorization_hashes = [
        sha256_value(
            {
                "holder": holder,
                "world_id": WORLD_ID,
                "operation": OPERATION,
                "purpose": PURPOSE,
                "retention": contract["retention"],
                "recipient": contract["recipient"],
                "authorized": not contract["holders_revoked"],
            }
        )
        for holder in ["LAB-SEEK", "LAB-OFFER"]
    ]
    attempt_body = {
        **coords,
        "status": "ATTEMPTED",
        "holder_authorization_sha256": authorization_hashes,
    }
    package: dict[str, Any] = {
        "schema": "towow.effect-evidence-package.v1",
        "contract_sha256": sha256_value(contract),
        "attempt": _sign(
            contract, "CONTROLLER-W6", "EFFECT_ATTEMPT", attempt_body
        ),
        "terminal_observations": {
            "unknown": "UNKNOWN",
            "explicit_refusal": "REFUSE",
            "closed_population_negative": "ABSENT",
        },
    }
    if stop_level < 1:
        return package

    deliveries = [
        {
            "origin": "LAB-SEEK",
            "recipient": contract["recipient"],
            "fact_id": "FACT-W6-ROUTE-CONSTRAINTS",
            "depth": 0,
            "purpose": PURPOSE,
            "retention": contract["retention"],
            "projection_sha256": sha256_value(
                {"facet": "route-constraints", "units": 1}
            ),
        },
        {
            "origin": "LAB-OFFER",
            "recipient": contract["recipient"],
            "fact_id": "FACT-W6-WINDOW-CAPACITY",
            "depth": 0,
            "purpose": PURPOSE,
            "retention": contract["retention"],
            "projection_sha256": sha256_value(
                {"facet": "window-capacity", "units": 1}
            ),
        },
    ]
    if single_side_delivery:
        deliveries = deliveries[:1]
    delivery_body = {
        **coords,
        "status": "DELIVERED",
        "attempt_sha256": envelope_hash(package["attempt"]),
        "deliveries": deliveries,
        "authoritative_state_root": sha256_value(deliveries),
    }
    delivery_receipt = _sign(
        contract,
        "CONTROLLER-W6",
        "DELIVERY_EXECUTION_RECEIPT",
        delivery_body,
    )
    anchor_event = {
        "event": "DELIVERY_COMMITTED",
        "action_digest": coords["action_digest"],
        "idempotency_key": coords["idempotency_key"],
        "delivery_receipt_sha256": envelope_hash(delivery_receipt),
        "state_root": delivery_body["authoritative_state_root"],
    }
    anchor_body = {
        **coords,
        "sequence": 1,
        "previous_head": contract["anchor_genesis"],
        "event": anchor_event,
        "new_head": sha256_value(
            {
                "sequence": 1,
                "previous_head": contract["anchor_genesis"],
                "event": anchor_event,
            }
        ),
    }
    package["delivery"] = {
        "receipt": delivery_receipt,
        "anchor": _sign(
            contract, "ANCHOR-W6", "EXTERNAL_ANCHOR_RECEIPT", anchor_body
        ),
    }
    if stop_level < 2:
        return package

    ack_body = {
        **coords,
        "status": "READ_BACK_ACKED",
        "delivery_receipt_sha256": envelope_hash(delivery_receipt),
        "anchor_receipt_sha256": envelope_hash(
            package["delivery"]["anchor"]
        ),
        "delivery_event_sha256": [
            sha256_value(item) for item in deliveries
        ],
        "recipient_store_root": sha256_value(
            {"recipient": contract["recipient"], "deliveries": deliveries}
        ),
    }
    package["recipient_ack"] = _sign(
        contract, contract["recipient"], "RECIPIENT_READBACK_ACK", ack_body
    )
    if stop_level < 3:
        return package

    output = {
        **TRUTH,
        "operation": OPERATION,
        "environment_version": contract["environment_version"],
        "input_delivery_sha256": ack_body["delivery_event_sha256"],
    }
    postcondition_body = {
        **coords,
        "status": "DOMAIN_POSTCONDITION_SATISFIED",
        "recipient_ack_sha256": envelope_hash(package["recipient_ack"]),
        "output": output,
        "output_sha256": sha256_value(output),
        "domain_state_root": sha256_value(
            {
                "environment_version": contract["environment_version"],
                "operation": OPERATION,
                "output": output,
            }
        ),
    }
    package["domain_postcondition"] = _sign(
        contract,
        "SIMULATOR-W6",
        "DOMAIN_POSTCONDITION",
        postcondition_body,
    )
    if stop_level < 4:
        if beneficiary_refusal:
            refusal_body = {
                **coords,
                "status": "REFUSE",
                "postcondition_sha256": envelope_hash(
                    package["domain_postcondition"]
                ),
                "reason": "beneficiary-declined-this-output",
            }
            package["beneficiary_refusal"] = _sign(
                contract,
                "BENEFICIARY-REVIEWER",
                "BENEFICIARY_REFUSAL",
                refusal_body,
            )
        return package

    if beneficiary_refusal:
        refusal_body = {
            **coords,
            "status": "REFUSE",
            "postcondition_sha256": envelope_hash(
                package["domain_postcondition"]
            ),
            "reason": "beneficiary-declined-this-output",
        }
        package["beneficiary_refusal"] = _sign(
            contract,
            "BENEFICIARY-REVIEWER",
            "BENEFICIARY_REFUSAL",
            refusal_body,
        )
        return package

    acceptance_body = {
        **coords,
        "status": "ACCEPTED",
        "postcondition_sha256": envelope_hash(
            package["domain_postcondition"]
        ),
        "accepted_output_sha256": package["domain_postcondition"]["body"][
            "output_sha256"
        ],
        "criteria_version": "sterile-route-acceptance-v1",
        "continuing_relation_claimed": False,
    }
    package["beneficiary_acceptance"] = _sign(
        contract,
        "BENEFICIARY-REVIEWER",
        "BENEFICIARY_ACCEPTANCE",
        acceptance_body,
    )
    return package


def schema_alias(package: dict[str, Any]) -> dict[str, Any]:
    aliased = copy.deepcopy(package)
    for old, new in [
        ("recipient_ack", "recipientAck"),
        ("domain_postcondition", "domainPostcondition"),
        ("beneficiary_acceptance", "beneficiaryAcceptance"),
        ("beneficiary_refusal", "beneficiaryRefusal"),
    ]:
        if old in aliased:
            aliased[new] = aliased.pop(old)
    aliased["schema"] = "towow.effect-evidence-package.alias-v1"
    return aliased


def anchor_fork(package: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    forked = copy.deepcopy(package)
    old = forked["delivery"]["anchor"]["body"]
    body = copy.deepcopy(old)
    body["previous_head"] = "forked-history-head"
    body["new_head"] = sha256_value(
        {
            "sequence": body["sequence"],
            "previous_head": body["previous_head"],
            "event": body["event"],
        }
    )
    forked["delivery"]["anchor"] = _sign(
        contract, "ANCHOR-W6", "EXTERNAL_ANCHOR_RECEIPT", body
    )
    return forked


def build_scenarios() -> dict[str, dict[str, Any]]:
    v1 = build_contract()
    v2 = build_contract(version="v2", step=8)
    semantic_v2 = build_contract(
        version="v2", step=8, semantic_retention="PT9M"
    )
    environment_v2 = build_contract(
        version="v2", step=8, environment_version="sterile-sim-env-v2"
    )
    alternate_v2 = build_contract(
        version="v2",
        step=8,
        recipient="SIM-RECIPIENT-B",
        withdrawn=("SIM-RECIPIENT",),
    )
    holder_revoked_v2 = build_contract(
        version="v2", step=8, holders_revoked=True
    )
    baseline = build_effect(v1)
    return {
        "exact_replay": {
            "input": baseline,
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": True,
        },
        "contract_change": {
            "input": baseline,
            "archived_contract": v1,
            "current_contract": semantic_v2,
            "valid_current_possible": True,
        },
        "key_rotation": {
            "input": baseline,
            "archived_contract": v1,
            "current_contract": v2,
            "valid_current_possible": True,
        },
        "recipient_withdrawal": {
            "input": baseline,
            "archived_contract": v1,
            "current_contract": alternate_v2,
            "valid_current_possible": True,
        },
        "anchor_fork": {
            "input": anchor_fork(baseline, v1),
            "archived_contract": v1,
            "current_contract": v2,
            "valid_current_possible": True,
        },
        "schema_alias": {
            "input": schema_alias(baseline),
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": True,
        },
        "partial_recovery": {
            "input": build_effect(v1, stop_level=2),
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": True,
        },
        "delayed_ack": {
            "input": build_effect(v1, stop_level=1),
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": True,
        },
        "single_side_partial": {
            "input": build_effect(
                v1, stop_level=1, single_side_delivery=True
            ),
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": True,
        },
        "holder_revocation": {
            "input": build_effect(v1, stop_level=0),
            "archived_contract": v1,
            "current_contract": holder_revoked_v2,
            "valid_current_possible": False,
        },
        "beneficiary_refusal": {
            "input": build_effect(
                v1, stop_level=3, beneficiary_refusal=True
            ),
            "archived_contract": v1,
            "current_contract": v1,
            "valid_current_possible": False,
        },
        "material_semantic_change": {
            "input": baseline,
            "archived_contract": v1,
            "current_contract": environment_v2,
            "valid_current_possible": True,
        },
    }

