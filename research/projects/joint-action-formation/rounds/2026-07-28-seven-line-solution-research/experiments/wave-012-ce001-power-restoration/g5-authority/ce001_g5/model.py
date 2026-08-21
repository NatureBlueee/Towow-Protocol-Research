from __future__ import annotations

from copy import deepcopy
from typing import Any

from .common import sha256


AUTHORITY_STRATA = {
    "U": {
        "name": "LAWFULLY_UNIFIED",
        "owners": ["O_UNIFIED"],
        "authority_mode": "UNIFIED_PRINCIPAL_ACT",
        "delegatee": "C_COORDINATOR",
        "role_owners": {
            "Q": "O_UNIFIED",
            "VENUE": "O_UNIFIED",
            "RESOURCE": "O_UNIFIED",
            "SAFETY": "O_UNIFIED",
        },
    },
    "D": {
        "name": "EXACT_DELEGATION",
        "owners": ["O_Q", "O_V", "O_R", "O_S"],
        "authority_mode": "EXACT_DELEGATED_ACT",
        "delegatee": "C_COORDINATOR",
        "role_owners": {
            "Q": "O_Q",
            "VENUE": "O_V",
            "RESOURCE": "O_R",
            "SAFETY": "O_S",
        },
    },
    "P": {
        "name": "PLURAL_INDEPENDENT",
        "owners": ["O_Q", "O_V", "O_R", "O_S"],
        "authority_mode": "DIRECT_OWNER_ACT",
        "delegatee": None,
        "role_owners": {
            "Q": "O_Q",
            "VENUE": "O_V",
            "RESOURCE": "O_R",
            "SAFETY": "O_S",
        },
    },
}

REVOKE_BOUNDARIES = ("read", "sign", "reserve", "execute")

MATERIAL_SCOPE_FIELDS = (
    "target",
    "power_kw",
    "tolerance_percent",
    "minimum_minutes",
    "forbid_other_circuits",
    "noise_limit_dba",
    "safety_policy_version",
    "compensation",
)


def build_operation(stratum: str = "P") -> dict[str, Any]:
    if stratum not in AUTHORITY_STRATA:
        raise ValueError(f"unknown Authority stratum: {stratum}")
    authority = AUTHORITY_STRATA[stratum]
    operation = {
        "episode_id": "CE-001",
        "operation_id": f"CE-001-C7-ENERGIZE-{stratum}",
        "q_id": "CE-001-Q",
        "q_version": "Q@v1",
        "object_id": "Venue-V/Circuit-C7",
        "object_revision": "C7@rev5",
        "scope": {
            "target": "Venue-V/Circuit-C7",
            "power_kw": 3.0,
            "tolerance_percent": 5,
            "minimum_minutes": 45,
            "forbid_other_circuits": True,
            "noise_limit_dba": 55,
            "safety_policy_version": "O_S/policy@17",
            "compensation": "DEENERGIZE_ON_AUTHORITY_LOSS",
        },
        "expiry": 1_900_000_000,
        "authority": {
            "stratum": stratum,
            "stratum_name": authority["name"],
            "mode": authority["authority_mode"],
            "delegatee": authority["delegatee"],
            "required_owners": authority["owners"],
        },
        "resource": {
            "resource_id": "BATTERY-R17",
            "resource_version": "R17@4",
            "reservation_slot": "CE-001/T0..T0+90m",
        },
        "standing": {
            "snapshot_id": "STANDING-CE001@3",
            "status": "ADJUDICATED_CURRENT",
            "jurisdiction": "Venue-V",
        },
        "materiality_rule_version": "CE001-MATERIALITY@1",
    }
    operation["material_closure_sha256"] = material_operation_closure(operation)
    return operation


def build_topology(stratum: str) -> dict[str, Any]:
    """Build the target trust anchor; the operation label is not the proof.

    U, D, and P use different closure semantics even though the same worker
    implementation verifies their receipts.
    """
    authority = AUTHORITY_STRATA[stratum]
    topology = {
        "schema": "ce001.g5.authority-topology.v2",
        "topology_id": f"CE001-AUTHORITY-{stratum}@1",
        "derived_stratum": stratum,
        "closure_kind": authority["authority_mode"],
        "required_owners": authority["owners"],
        "role_owners": authority["role_owners"],
        "delegatee": authority["delegatee"],
    }
    topology["topology_closure_sha256"] = sha256(topology)
    return topology


def resource_owner_for_topology(topology: dict[str, Any]) -> str:
    return str(topology["role_owners"]["RESOURCE"])


def material_projection(operation: dict[str, Any]) -> dict[str, Any]:
    scope = operation["scope"]
    missing = [name for name in MATERIAL_SCOPE_FIELDS if name not in scope]
    if missing:
        raise ValueError(f"missing material scope fields: {','.join(missing)}")
    if not operation.get("materiality_rule_version"):
        raise ValueError("missing materiality_rule_version")
    return {
        "episode_id": operation["episode_id"],
        "q_id": operation["q_id"],
        "q_version": operation["q_version"],
        "object_id": operation["object_id"],
        "object_revision": operation["object_revision"],
        "operation_id": operation["operation_id"],
        "scope": {name: scope[name] for name in MATERIAL_SCOPE_FIELDS},
        "expiry": operation["expiry"],
        "authority": operation["authority"],
        "resource": operation["resource"],
        "standing": operation["standing"],
        "materiality_rule_version": operation["materiality_rule_version"],
    }


def material_operation_closure(operation: dict[str, Any]) -> str:
    return sha256(material_projection(operation))


def validate_embedded_closure(operation: dict[str, Any]) -> tuple[bool, str]:
    computed = material_operation_closure(operation)
    return computed == operation.get("material_closure_sha256"), computed


def frozen_operation_violation(operation: dict[str, Any]) -> str | None:
    """Enforce the frozen CE-001 Q rather than trusting controller-built config.

    An O_Q material change requires a separately frozen owner act and a new run;
    it cannot silently redefine this run's owner/target truth.
    """
    try:
        stratum = operation["authority"]["stratum"]
        frozen = build_operation(stratum)
        if material_projection(operation) != material_projection(frozen):
            return "SUBSTITUTION_INVALID_FROZEN_Q"
        if operation.get("material_closure_sha256") != frozen[
            "material_closure_sha256"
        ]:
            return "SUBSTITUTION_INVALID_FROZEN_Q"
    except (KeyError, TypeError, ValueError):
        return "SUBSTITUTION_INVALID_FROZEN_Q"
    return None


def build_materiality_cases() -> list[dict[str, Any]]:
    base = build_operation("P")
    cases: list[dict[str, Any]] = []

    cosmetic = deepcopy(base)
    cosmetic["controller_note"] = "non-material display copy"
    cases.append(_materiality_row("COSMETIC_METADATA", base, cosmetic))

    safety_change = deepcopy(base)
    safety_change["scope"]["safety_policy_version"] = "O_S/policy@18"
    cases.append(_materiality_row("SAFETY_SIDECAR_CHANGE", base, safety_change))

    resource_change = deepcopy(base)
    resource_change["resource"]["resource_version"] = "R17@5"
    cases.append(_materiality_row("RESOURCE_DEPENDENCY_CHANGE", base, resource_change))

    q_change = deepcopy(base)
    q_change["q_version"] = "Q@v2"
    cases.append(_materiality_row("MATERIAL_Q_CHANGE", base, q_change))
    return cases


def _materiality_row(
    case_id: str, base: dict[str, Any], changed: dict[str, Any]
) -> dict[str, Any]:
    base_hash = material_operation_closure(base)
    changed_hash = material_operation_closure(changed)
    return {
        "case_id": case_id,
        "base_closure_sha256": base_hash,
        "changed_closure_sha256": changed_hash,
        "same_operation_closure": base_hash == changed_hash,
    }


def evaluate_standing(record: dict[str, Any], *, effect_occurred: bool) -> str:
    status = record["status"]
    if status == "ADJUDICATED_CURRENT":
        return "EXECUTION_ELIGIBLE"
    if status == "ADJUDICATED_SUSPENSIVE":
        return "SUSPEND_EXECUTION"
    if status == "LATE_ADJUDICATED":
        return "COMPENSATE_AND_REOPEN" if effect_occurred else "REOPEN_BEFORE_EFFECT"
    if status == "CHALLENGE_REJECTED":
        return "CONTINUE_WITH_AUDIT"
    if status in {"JURISDICTION_CONFLICT", "UNRESOLVED"}:
        return "UNKNOWN"
    return "UNKNOWN"


def build_standing_cases() -> list[dict[str, Any]]:
    cases = [
        ({"status": "ADJUDICATED_CURRENT"}, False),
        ({"status": "ADJUDICATED_SUSPENSIVE"}, False),
        ({"status": "LATE_ADJUDICATED"}, False),
        ({"status": "LATE_ADJUDICATED"}, True),
        ({"status": "CHALLENGE_REJECTED"}, False),
        ({"status": "JURISDICTION_CONFLICT"}, False),
    ]
    return [
        {
            "record": record,
            "effect_occurred": effect,
            "native_resolution": evaluate_standing(record, effect_occurred=effect),
        }
        for record, effect in cases
    ]
