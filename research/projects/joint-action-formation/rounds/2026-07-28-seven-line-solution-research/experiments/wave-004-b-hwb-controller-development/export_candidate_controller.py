#!/usr/bin/env python3
"""Export coordinator-visible HW-B records only from verified controller output."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import adapter


HERE = Path(__file__).resolve().parent
TARGET = adapter.HWB_ROOT / "candidate-controller"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_result(
    result: dict[str, Any],
    *,
    route_type: str,
    expected_routes: list[tuple[str, str, int]],
) -> dict[str, Any]:
    if result.get("replay") != "FIRST_ATTEMPT":
        raise RuntimeError("CONTROLLER_OUTPUT_NOT_FIRST_ATTEMPT")
    outcome = result.get("outcome", {})
    receipt = result.get("execution_receipt", {})
    if (
        outcome.get("status") != "EXECUTED"
        or outcome.get("route_type") != route_type
        or receipt.get("decision") != "EXECUTED"
        or receipt.get("output_sha256") != adapter.EXECUTOR.sha256_value(outcome)
    ):
        raise RuntimeError("CONTROLLER_EXECUTION_BINDING_INVALID")
    receipt_body = {
        key: value for key, value in receipt.items() if key != "receipt_sha256"
    }
    if adapter.EXECUTOR.sha256_value(receipt_body) != receipt.get(
        "receipt_sha256"
    ):
        raise RuntimeError("CONTROLLER_RECEIPT_HASH_INVALID")
    readback = outcome.get("authority_evidence", {}).get("readback", {})
    if (
        readback.get("all_postconditions_observed") is not True
        or readback.get("delivery_count") != len(expected_routes)
    ):
        raise RuntimeError("CONTROLLER_READBACK_INCOMPLETE")
    disclosures = outcome.get("disclosures", [])
    actual_routes = [
        (item.get("from"), item.get("to"), item.get("depth"))
        for item in disclosures
    ]
    if actual_routes != expected_routes:
        raise RuntimeError(
            f"CONTROLLER_ROUTE_MISMATCH:{actual_routes!r}!={expected_routes!r}"
        )
    observed = {
        (item["recipient"], item["delivery_event_id"])
        for item in readback.get("recipient_store_observations", [])
    }
    required = {(item["to"], item["event_id"]) for item in disclosures}
    if observed != required:
        raise RuntimeError("RECIPIENT_STORE_READBACK_ROUTE_MISMATCH")
    return outcome


def _coordinator_disclosure(
    item: dict[str, Any],
    *,
    origin_party: str,
    derived_from_event_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "event_id": item["event_id"],
        "origin_party": origin_party,
        "sender": item["from"],
        "recipient": item["to"],
        "fact_id": item["projection"]["fact_id"],
        "depth": item["depth"],
        "purpose": item["purpose"],
        "retention": item["retention"],
    }
    if derived_from_event_id is not None:
        record["derived_from_event_id"] = derived_from_event_id
    return record


def _export_record(
    *,
    source_path: Path,
    result: dict[str, Any],
    coordinator_visible: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "towow.hwb-controller-export.v1",
        "development_label": "DEVELOPMENT_POST_FEEDBACK_NOT_BLIND",
        "generated_from": {
            "path": str(source_path.relative_to(adapter.ROUND_ROOT)),
            "source_file_sha256": file_sha256(source_path),
            "controller_execution_receipt_sha256": result[
                "execution_receipt"
            ]["receipt_sha256"],
            "controller_output_sha256": adapter.EXECUTOR.sha256_value(result),
        },
        "controller_result": result,
        "coordinator_visible": coordinator_visible,
        "claim_boundary": {
            "relation_status": result["outcome"]["relation_status"],
            "commitment_status": result["outcome"]["commitment_status"],
            "authority_status": result["outcome"]["authority_status"],
            "real_world_effect": "NOT_CLAIMED",
        },
    }


def build_exports() -> dict[str, dict[str, Any]]:
    direct_path = HERE / "outputs" / "helios-direct.json"
    derived_path = HERE / "outputs" / "ion-derived.json"
    reciprocal_path = HERE / "outputs" / "reciprocal-juniper-kite.json"
    direct = load(direct_path)
    derived = load(derived_path)
    reciprocal_wrapper = load(reciprocal_path)
    reciprocal = reciprocal_wrapper["controller_result"]

    direct_outcome = _validate_result(
        direct,
        route_type="DIRECT_PROJECTION",
        expected_routes=[("HELIOS-44", "NODE-COPPER-ROUTER", 0)],
    )
    derived_outcome = _validate_result(
        derived,
        route_type="DERIVED_ONWARD",
        expected_routes=[
            ("ION-06", "NODE-SILVER-RELAY", 0),
            ("NODE-SILVER-RELAY", "NODE-COPPER-ROUTER", 1),
        ],
    )
    reciprocal_outcome = _validate_result(
        reciprocal,
        route_type="RECIPROCAL_EXCHANGE",
        expected_routes=[
            ("JUNIPER-28", "KITE-15", 0),
            ("KITE-15", "JUNIPER-28", 0),
        ],
    )
    exchange = reciprocal_outcome["reciprocal_exchange"]
    if (
        exchange.get("status") != "PERFORMED"
        or exchange.get("delivery_mode") != "COUNTERPARTY_EXCHANGE"
        or exchange.get("scope")
        != "RECIPROCAL_COUNTERPARTY_PROJECTION_EXCHANGE"
    ):
        raise RuntimeError("RECIPROCAL_EXCHANGE_NOT_COUNTERPARTY_COMPLETE")

    direct_disclosures = [
        _coordinator_disclosure(
            direct_outcome["disclosures"][0], origin_party="HELIOS-44"
        )
    ]
    derived_disclosures = [
        _coordinator_disclosure(
            derived_outcome["disclosures"][0], origin_party="ION-06"
        ),
        _coordinator_disclosure(
            derived_outcome["disclosures"][1],
            origin_party="ION-06",
            derived_from_event_id=derived_outcome["disclosures"][0]["event_id"],
        ),
    ]
    reciprocal_disclosures = [
        _coordinator_disclosure(item, origin_party=item["from"])
        for item in reciprocal_outcome["disclosures"]
    ]
    by_direction = {
        item["projection"]["direction"]: item
        for item in reciprocal_outcome["disclosures"]
    }
    seek = by_direction["SEEK"]
    offer = by_direction["OFFER"]
    probe = {
        "probe_id": exchange["exchange_id"],
        "requester": seek["from"],
        "responder": offer["from"],
        "requested_fact": offer["projection"]["fact_id"],
        "offered_fact": seek["projection"]["fact_id"],
        "status": "COMPLETED_RECIPROCAL_RECEIPT",
    }

    return {
        "route-helios-direct.json": _export_record(
            source_path=direct_path,
            result=direct,
            coordinator_visible={"disclosures": direct_disclosures},
        ),
        "route-ion-relay.json": _export_record(
            source_path=derived_path,
            result=derived,
            coordinator_visible={"disclosures": derived_disclosures},
        ),
        "reciprocal-juniper-kite.json": _export_record(
            source_path=reciprocal_path,
            result=reciprocal,
            coordinator_visible={
                "probe": probe,
                "disclosures": reciprocal_disclosures,
            },
        ),
    }


def export() -> None:
    exports = build_exports()
    TARGET.mkdir(parents=True, exist_ok=True)
    for name, value in exports.items():
        adapter.write_json(TARGET / name, value)


if __name__ == "__main__":
    export()
