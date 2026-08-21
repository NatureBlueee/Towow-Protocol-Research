#!/usr/bin/env python3
"""Effect-ladder verifier and safe-reopen strategy comparison."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from simulator import (
    OPERATION,
    PURPOSE,
    SHARED_TASK_ID,
    TRUTH,
    WORLD_ID,
    _sign,
    action_coordinates,
    build_effect,
    build_scenarios,
    envelope_hash,
    private_key,
    sha256_value,
    sign_envelope,
)

from protocol import ProtocolError, verify_envelope


LEVEL_NAMES = [
    "ATTEMPT",
    "DELIVERY",
    "RECIPIENT_ACK",
    "DOMAIN_POSTCONDITION",
    "BENEFICIARY_ACCEPTANCE",
]
STRATEGIES = [
    "IMMUTABLE_REPLAY",
    "MIGRATION_ADAPTER",
    "REAUTHORIZE",
]


def _verify(
    envelope: dict[str, Any],
    contract: dict[str, Any],
    kind: str,
    issuer: str,
) -> dict[str, Any]:
    return verify_envelope(
        envelope,
        contract,
        expected_kind=kind,
        expected_issuer=issuer,
        step=contract["evaluation_step"],
    )


def _coordinates_match(
    body: dict[str, Any], contract: dict[str, Any]
) -> None:
    expected = action_coordinates(contract)
    for field in [
        "shared_task_id",
        "world_id",
        "evaluation_step",
        "operation",
        "purpose",
        "retention",
        "environment_version",
        "contract_sha256",
        "action_digest",
        "idempotency_key",
    ]:
        if body.get(field) != expected[field]:
            raise ProtocolError(
                "EFFECT_COORDINATE_MISMATCH",
                f"Effect evidence field {field} changed.",
            )


def evaluate(
    package: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    result = {
        "highest_level": -1,
        "highest_name": "NONE",
        "current_accepted": False,
        "terminal_state": "UNKNOWN",
        "errors": [],
        "levels_valid": [],
    }

    if package.get("contract_sha256") != sha256_value(contract):
        result["errors"].append("CONTRACT_HASH_MISMATCH")
        return result

    try:
        attempt = _verify(
            package["attempt"],
            contract,
            "EFFECT_ATTEMPT",
            "CONTROLLER-W6",
        )
        _coordinates_match(attempt, contract)
        if attempt["status"] != "ATTEMPTED":
            raise ProtocolError("ATTEMPT_STATUS_INVALID", "Not attempted.")
        result["highest_level"] = 0
        result["highest_name"] = LEVEL_NAMES[0]
        result["levels_valid"].append(LEVEL_NAMES[0])
    except (KeyError, ProtocolError) as error:
        result["errors"].append(getattr(error, "code", "ATTEMPT_MISSING"))
        return result

    try:
        delivery = package["delivery"]
        receipt = _verify(
            delivery["receipt"],
            contract,
            "DELIVERY_EXECUTION_RECEIPT",
            "CONTROLLER-W6",
        )
        anchor = _verify(
            delivery["anchor"],
            contract,
            "EXTERNAL_ANCHOR_RECEIPT",
            "ANCHOR-W6",
        )
        _coordinates_match(receipt, contract)
        _coordinates_match(anchor, contract)
        if receipt["attempt_sha256"] != envelope_hash(package["attempt"]):
            raise ProtocolError(
                "DELIVERY_ATTEMPT_LINK_INVALID", "Wrong attempt link."
            )
        if len(receipt["deliveries"]) != 2:
            raise ProtocolError(
                "DELIVERY_SET_INCOMPLETE",
                "Both shared-task projections must be delivered.",
            )
        if {
            item["origin"] for item in receipt["deliveries"]
        } != {"LAB-SEEK", "LAB-OFFER"}:
            raise ProtocolError(
                "DELIVERY_ORIGIN_SET_INVALID", "Wrong projection origins."
            )
        if any(
            item["recipient"] != contract["recipient"]
            or item["purpose"] != PURPOSE
            or item["retention"] != contract["retention"]
            or item["depth"] != 0
            for item in receipt["deliveries"]
        ):
            raise ProtocolError(
                "DELIVERY_POLICY_INVALID", "Delivery policy drifted."
            )
        if anchor["previous_head"] != contract["anchor_genesis"]:
            raise ProtocolError("ANCHOR_FORK", "Anchor did not extend genesis.")
        if anchor["event"]["delivery_receipt_sha256"] != envelope_hash(
            delivery["receipt"]
        ):
            raise ProtocolError(
                "ANCHOR_DELIVERY_LINK_INVALID", "Anchor links another delivery."
            )
        expected_head = sha256_value(
            {
                "sequence": anchor["sequence"],
                "previous_head": anchor["previous_head"],
                "event": anchor["event"],
            }
        )
        if anchor["sequence"] != 1 or anchor["new_head"] != expected_head:
            raise ProtocolError(
                "ANCHOR_CHAIN_INVALID", "Anchor sequence/head invalid."
            )
        result["highest_level"] = 1
        result["highest_name"] = LEVEL_NAMES[1]
        result["levels_valid"].append(LEVEL_NAMES[1])
    except (KeyError, ProtocolError) as error:
        result["errors"].append(getattr(error, "code", "DELIVERY_MISSING"))
        return result

    try:
        ack = _verify(
            package["recipient_ack"],
            contract,
            "RECIPIENT_READBACK_ACK",
            contract["recipient"],
        )
        _coordinates_match(ack, contract)
        if ack["delivery_receipt_sha256"] != envelope_hash(
            package["delivery"]["receipt"]
        ) or ack["anchor_receipt_sha256"] != envelope_hash(
            package["delivery"]["anchor"]
        ):
            raise ProtocolError(
                "ACK_DELIVERY_LINK_INVALID", "ACK links another delivery."
            )
        expected_events = [
            sha256_value(item)
            for item in package["delivery"]["receipt"]["body"]["deliveries"]
        ]
        if ack["delivery_event_sha256"] != expected_events:
            raise ProtocolError(
                "ACK_READBACK_SET_INVALID", "ACK did not read both events."
            )
        result["highest_level"] = 2
        result["highest_name"] = LEVEL_NAMES[2]
        result["levels_valid"].append(LEVEL_NAMES[2])
    except (KeyError, ProtocolError) as error:
        result["errors"].append(getattr(error, "code", "ACK_MISSING"))
        return result

    try:
        postcondition = _verify(
            package["domain_postcondition"],
            contract,
            "DOMAIN_POSTCONDITION",
            "SIMULATOR-W6",
        )
        _coordinates_match(postcondition, contract)
        if postcondition["recipient_ack_sha256"] != envelope_hash(
            package["recipient_ack"]
        ):
            raise ProtocolError(
                "POSTCONDITION_ACK_LINK_INVALID",
                "Postcondition links another ACK.",
            )
        output = postcondition["output"]
        for field, value in TRUTH.items():
            if output.get(field) != value:
                raise ProtocolError(
                    "FROZEN_TRUTH_MISMATCH", "Simulator output changed truth."
                )
        if (
            output["operation"] != OPERATION
            or output["environment_version"]
            != contract["environment_version"]
            or postcondition["output_sha256"] != sha256_value(output)
        ):
            raise ProtocolError(
                "DOMAIN_POSTCONDITION_INVALID",
                "Output bytes/environment are not frozen.",
            )
        result["highest_level"] = 3
        result["highest_name"] = LEVEL_NAMES[3]
        result["levels_valid"].append(LEVEL_NAMES[3])
    except (KeyError, ProtocolError) as error:
        result["errors"].append(
            getattr(error, "code", "POSTCONDITION_MISSING")
        )
        return result

    if "beneficiary_refusal" in package:
        try:
            refusal = _verify(
                package["beneficiary_refusal"],
                contract,
                "BENEFICIARY_REFUSAL",
                "BENEFICIARY-REVIEWER",
            )
            _coordinates_match(refusal, contract)
            if (
                refusal["status"] != "REFUSE"
                or refusal["postcondition_sha256"]
                != envelope_hash(package["domain_postcondition"])
            ):
                raise ProtocolError(
                    "BENEFICIARY_REFUSAL_INVALID", "Refusal binding invalid."
                )
            result["terminal_state"] = "REFUSE"
            result["errors"].append("BENEFICIARY_REFUSED")
            return result
        except ProtocolError as error:
            result["errors"].append(error.code)
            return result

    try:
        acceptance = _verify(
            package["beneficiary_acceptance"],
            contract,
            "BENEFICIARY_ACCEPTANCE",
            "BENEFICIARY-REVIEWER",
        )
        _coordinates_match(acceptance, contract)
        if (
            acceptance["status"] != "ACCEPTED"
            or acceptance["postcondition_sha256"]
            != envelope_hash(package["domain_postcondition"])
            or acceptance["accepted_output_sha256"]
            != package["domain_postcondition"]["body"]["output_sha256"]
        ):
            raise ProtocolError(
                "BENEFICIARY_ACCEPTANCE_INVALID",
                "Acceptance does not bind exact output.",
            )
        result["highest_level"] = 4
        result["highest_name"] = LEVEL_NAMES[4]
        result["levels_valid"].append(LEVEL_NAMES[4])
        result["current_accepted"] = True
        result["terminal_state"] = "ACCEPTED"
        return result
    except (KeyError, ProtocolError) as error:
        result["errors"].append(
            getattr(error, "code", "BENEFICIARY_ACCEPTANCE_MISSING")
        )
        return result


def normalize_schema_alias(package: dict[str, Any]) -> dict[str, Any]:
    if package.get("schema") != "towow.effect-evidence-package.alias-v1":
        return copy.deepcopy(package)
    normalized = copy.deepcopy(package)
    mapping = {
        "recipientAck": "recipient_ack",
        "domainPostcondition": "domain_postcondition",
        "beneficiaryAcceptance": "beneficiary_acceptance",
        "beneficiaryRefusal": "beneficiary_refusal",
    }
    for alias, canonical in mapping.items():
        if alias in normalized:
            if canonical in normalized:
                raise ProtocolError(
                    "SCHEMA_ALIAS_CONFLICT",
                    "Alias and canonical field both supplied.",
                )
            normalized[canonical] = normalized.pop(alias)
    normalized["schema"] = "towow.effect-evidence-package.v1"
    return normalized


def complete_from_partial(
    package: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    completed = build_effect(contract)
    for field in ["attempt", "delivery", "recipient_ack"]:
        if field in package:
            completed[field] = copy.deepcopy(package[field])
    completed["contract_sha256"] = package["contract_sha256"]
    return completed


def apply_strategy(
    strategy: str,
    case_id: str,
    scenario: dict[str, Any],
) -> tuple[dict[str, Any], int, int, int]:
    package = copy.deepcopy(scenario["input"])
    current = scenario["current_contract"]
    input_contract_hash = package.get("contract_sha256")
    same_contract = input_contract_hash == sha256_value(current)

    if strategy == "IMMUTABLE_REPLAY":
        if same_contract and case_id in {"partial_recovery", "delayed_ack"}:
            before = evaluate(package, current)["highest_level"]
            completed = complete_from_partial(package, current)
            cost = 4 - before
            return completed, cost, 0, cost
        return package, 0, 0, 0

    if strategy == "MIGRATION_ADAPTER":
        try:
            package = normalize_schema_alias(package)
        except ProtocolError:
            return scenario["input"], 1, 0, 1
        same_contract = package.get("contract_sha256") == sha256_value(current)
        if same_contract and case_id in {"partial_recovery", "delayed_ack"}:
            before = evaluate(package, current)["highest_level"]
            completed = complete_from_partial(package, current)
            cost = 1 + (4 - before)
            return completed, cost, 0, cost
        return package, 1, 0, 1

    if strategy != "REAUTHORIZE":
        raise ValueError(strategy)
    if case_id in {"holder_revocation", "beneficiary_refusal"}:
        return package, 1, 0, 1
    return build_effect(current), 5, 2, 5


def compare_strategies() -> dict[str, Any]:
    scenarios = build_scenarios()
    cases: dict[str, Any] = {}
    for case_id, scenario in scenarios.items():
        historical = evaluate(
            normalize_schema_alias(scenario["input"]),
            scenario["archived_contract"],
        )
        strategy_results = {}
        for strategy in STRATEGIES:
            candidate, cost, disclosure, coordination = apply_strategy(
                strategy, case_id, scenario
            )
            current = evaluate(candidate, scenario["current_contract"])
            stale_reuse = int(
                current["current_accepted"]
                and candidate.get("contract_sha256")
                != sha256_value(scenario["current_contract"])
            )
            lost = int(
                scenario["valid_current_possible"]
                and not current["current_accepted"]
            )
            accepted_value = 100 if current["current_accepted"] else 0
            net_value = (
                accepted_value
                - disclosure * 2
                - coordination
                - cost * 3
                - stale_reuse * 100
            )
            strategy_results[strategy] = {
                "current_highest_level": current["highest_level"],
                "current_terminal_state": current["terminal_state"],
                "current_accepted": current["current_accepted"],
                "errors": current["errors"],
                "historical_highest_level": historical["highest_level"],
                "false_promotion": 0,
                "false_positive": 0,
                "lost_valid_effect": lost,
                "false_negative": lost,
                "stale_reuse": stale_reuse,
                "recovery_time_steps": cost,
                "disclosure_units": disclosure,
                "evidence_coordination_operations": coordination,
                "residual_state_after_withdrawal": (
                    "OLD_EVIDENCE_ARCHIVED_NEW_EFFECT_ISOLATED"
                    if case_id == "recipient_withdrawal"
                    and current["current_accepted"]
                    else (
                        "HISTORICAL_ONLY_NO_CURRENT_EFFECT"
                        if case_id == "recipient_withdrawal"
                        else (
                            "ATTEMPT_ONLY"
                            if case_id == "holder_revocation"
                            else "NONE"
                        )
                    )
                ),
                "accepted_task_value": accepted_value,
                "net_task_value": net_value,
            }
        safe_accepted = [
            (name, value)
            for name, value in strategy_results.items()
            if value["current_accepted"] and not value["stale_reuse"]
        ]
        if safe_accepted:
            best = max(
                safe_accepted,
                key=lambda item: (
                    item[1]["net_task_value"],
                    -STRATEGIES.index(item[0]),
                ),
            )[0]
        else:
            best = "SAFE_REJECTION"
        cases[case_id] = {
            "historical_evidence": historical,
            "strategies": strategy_results,
            "best_strategy": best,
        }
    return {
        "schema": "towow.effect-reopen-comparison.v1",
        "shared_task_id": SHARED_TASK_ID,
        "cases": cases,
        "terminal_states_preserved": ["UNKNOWN", "REFUSE", "ABSENT"],
    }


def forgery_mutations() -> list[dict[str, Any]]:
    contract = build_scenarios()["exact_replay"]["current_contract"]
    full = build_effect(contract)
    mutations = []
    for predecessor_level in range(4):
        package = build_effect(contract, stop_level=predecessor_level)
        if predecessor_level == 0:
            package["delivery"] = copy.deepcopy(full["delivery"])
            anchor_body = full["delivery"]["anchor"]["body"]
            package["delivery"]["anchor"] = sign_envelope(
                private_key("CONTROLLER-W6", "v1"),
                kind="EXTERNAL_ANCHOR_RECEIPT",
                issuer="ANCHOR-W6",
                key_id="v1",
                body=anchor_body,
            )
        elif predecessor_level == 1:
            package["recipient_ack"] = sign_envelope(
                private_key("CONTROLLER-W6", "v1"),
                kind="RECIPIENT_READBACK_ACK",
                issuer=contract["recipient"],
                key_id="v1",
                body=full["recipient_ack"]["body"],
            )
        elif predecessor_level == 2:
            package["domain_postcondition"] = sign_envelope(
                private_key(contract["recipient"], "v1"),
                kind="DOMAIN_POSTCONDITION",
                issuer="SIMULATOR-W6",
                key_id="v1",
                body=full["domain_postcondition"]["body"],
            )
        else:
            package["beneficiary_acceptance"] = sign_envelope(
                private_key("SIMULATOR-W6", "v1"),
                kind="BENEFICIARY_ACCEPTANCE",
                issuer="BENEFICIARY-REVIEWER",
                key_id="v1",
                body=full["beneficiary_acceptance"]["body"],
            )
        outcome = evaluate(package, contract)
        mutations.append(
            {
                "mutation_id": f"PREDECESSOR_SELF_PROMOTION-{predecessor_level}-TO-{predecessor_level + 1}",
                "predecessor_level": predecessor_level,
                "attempted_level": predecessor_level + 1,
                "accepted_level": outcome["highest_level"],
                "false_promotion": int(
                    outcome["highest_level"] > predecessor_level
                ),
                "errors": outcome["errors"],
            }
        )
    return mutations


def full_report() -> dict[str, Any]:
    mutations = forgery_mutations()
    comparison = compare_strategies()
    return {
        **comparison,
        "promotion_mutations": mutations,
        "summary": {
            "false_promotions": sum(
                item["false_promotion"] for item in mutations
            ),
            "mutation_count": len(mutations),
            "stale_reuse_total": sum(
                strategy["stale_reuse"]
                for case in comparison["cases"].values()
                for strategy in case["strategies"].values()
            ),
            "solution_class": "EXISTING_COMPOSED_WORKFLOW_EVENT_SOURCING_AND_STRONG_CENTRAL_COORDINATION",
            "novel_protocol_required_in_frozen_scope": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = full_report()
    encoded = json.dumps(
        report, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
