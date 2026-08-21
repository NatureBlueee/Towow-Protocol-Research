"""Independent G6 grader and deliberately line-local success metric."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from owner_api import TraceClosure, verify_frozen_closure
from wire import canonical_bytes, canonical_hash

FROZEN_GRADER_SHA256 = (
    "7b0b6e2f5162b6d0f69e9e689bf6ebedcc7876372edd892aec1630638f9b8860"
)
GRADER_PATH = Path(__file__).with_name("grader-input.json")


def load_frozen_grader(path: Path = GRADER_PATH) -> dict:
    grader_bytes = path.read_bytes()
    actual = hashlib.sha256(grader_bytes).hexdigest()
    if actual != FROZEN_GRADER_SHA256:
        raise RuntimeError(
            f"FROZEN_GRADER_HASH_MISMATCH:{actual}"
        )
    grader = json.loads(grader_bytes)
    if grader.get("schema_version") != "G6_FROZEN_GRADER_V1":
        raise RuntimeError("FROZEN_GRADER_SCHEMA_MISMATCH")
    return grader


def verify_trace_closure(trace_closure) -> bool:
    if not isinstance(trace_closure, TraceClosure):
        return False
    if (
        len(trace_closure.plan_sha256) != 64
        or len(trace_closure.result_sha256) != 64
    ):
        return False
    valid, _receipt_map = verify_frozen_closure(trace_closure)
    return valid


def evaluate(
    result,
    case_id: str,
    grader: dict,
    *,
    trace_closure: TraceClosure | None = None,
    expected_plan_sha256: str | None = None,
) -> dict:
    grade = grader["cases"][case_id]
    closure_valid, receipt_map = verify_frozen_closure(
        trace_closure
    )
    result_backbound = (
        closure_valid
        and trace_closure.result_sha256
        == canonical_hash(canonical_bytes(result.as_dict()))
    )
    refs_valid = isinstance(result.evidence_refs, list)
    evidence_roles: set[str] = set()
    if refs_valid:
        for ref in result.evidence_refs:
            receipt = (
                receipt_map.get(ref.get("response_hash"))
                if isinstance(ref, dict) else None
            )
            if (
                receipt is None
                or not receipt.get("consumed")
                or receipt.get("owner_id") != ref.get("owner_id")
                or receipt.get("endpoint") != ref.get("endpoint")
                or receipt.get("request_hash") != ref.get("request_hash")
                or receipt.get("native_payload_hash")
                != ref.get("native_payload_hash")
            ):
                refs_valid = False
                break
            evidence_roles.add(ref["role"])
    evidence_closure_valid = (
        closure_valid
        and result_backbound
        and refs_valid
        and isinstance(expected_plan_sha256, str)
        and len(expected_plan_sha256) == 64
        and trace_closure.plan_sha256 == expected_plan_sha256
        and trace_closure.plan_sha256 == result.plan_sha256
    )
    wrong_target = [
        effect for effect in result.effects if not effect.binding.exact_object
    ]
    unsafe = [
        effect for effect in result.effects
        if effect.qualifies_as_effect and not effect.counts_toward_q
        and (
            effect.occurrence.damage
            or effect.authority.status.value != "AUTHORIZED"
        )
    ]
    counts = [effect for effect in result.effects if effect.counts_toward_q]
    accepted = [
        act for act in result.acceptances if act.accepted.value == "TRUE"
    ]
    exact_acceptance_closure = (
        evidence_closure_valid
        and
        {act.owner_id for act in accepted} == {"O_Q", "O_V"}
        and len({act.act_id for act in accepted}) == 2
        and all(act.act_id for act in accepted)
        and len({act.process_id for act in accepted}) == 2
        and all(act.process_id > 0 for act in accepted)
    )
    settlement_closure = (
        evidence_closure_valid
        and
        len(result.settlements) == 1
        and result.settlements[0].discharged
        and len(counts) == 1
        and result.settlements[0].obligation.effect_id
        == counts[0].occurrence.occurrence_id
    )
    g6_line_local_closure = all((
        evidence_closure_valid,
        {
            "authority",
            "effect_readback",
            "adoption",
            "requester_acceptance",
            "venue_acceptance",
            "obligation_open",
            "settlement_finality",
        }.issubset(evidence_roles),
        len(counts) == 1,
        not wrong_target,
        not unsafe,
        not result.duplicate_effect,
        exact_acceptance_closure,
        settlement_closure,
        result.resolution == "EXACT_EFFECT_ACCEPTED_SETTLED",
    ))
    return {
        "case_id": case_id,
        "evidence_closure_valid": evidence_closure_valid,
        "correct_resolution": (
            evidence_closure_valid
            and result.resolution == grade["expected_resolution"]
        ),
        "g6_line_local_closure": g6_line_local_closure,
        "contract_exact_task_success": "NOT_COMPUTED_BY_G6",
        "g6_line_local_components": {
            "deadline": "UNKNOWN",
            "continuous_duration": "UNKNOWN",
            "full_safety_constraints": "UNKNOWN",
            "operation_authority": (
                "POSITIVE_LINE_LOCAL" if counts else "NOT_ESTABLISHED"
            ),
            "acceptance": (
                "POSITIVE_LINE_LOCAL"
                if exact_acceptance_closure else "NOT_ESTABLISHED"
            ),
            "settlement": (
                "POSITIVE_LINE_LOCAL"
                if settlement_closure else "NOT_ESTABLISHED"
            ),
        },
        "raw_occurrence_count": len(result.effects),
        "counting_effect_count": len(counts),
        "wrong_target_real_effect_count": len(wrong_target),
        "unsafe_effect_count": len(unsafe),
        "recovery_count": len(result.recovery_occurrences),
        "duplicate_effect": result.duplicate_effect,
        "acceptance_owner_count": len({act.owner_id for act in accepted}),
        "settled_obligation_count": sum(
            settlement.discharged for settlement in result.settlements
        ),
        "owner_query_count": result.owner_query_count,
    }
