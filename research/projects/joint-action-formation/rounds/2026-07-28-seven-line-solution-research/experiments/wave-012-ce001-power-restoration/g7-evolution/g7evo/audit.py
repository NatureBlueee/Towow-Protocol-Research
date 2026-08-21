"""Contract-oriented audit for the Agent B component.

The audit reads only produced records.  It does not use a private expected
label and does not select an implementation arm.
"""

from __future__ import annotations

from typing import Any, Mapping

from .model import AppendOnlyHistory


PUBLIC_FORBIDDEN_KEYS = {
    "exacttasksuccess",
    "correctresolution",
    "recoverytovalue",
    "unsafeeffect",
    "duplicateeffect",
    "wrongobjectreliance",
    "unreconciledeffect",
    "authority",
    "effect",
    "acceptance",
    "settlement",
    "contractscore",
    "contractsuccess",
    "completesolution",
}


def _normalized(key: Any) -> str:
    return "".join(character for character in str(key).lower() if character.isalnum())


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.append(_normalized(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def audit_line_local_results(results: Mapping[str, Any]) -> list[str]:
    """Audit only claims and facts owned by the public G7 output."""

    violations: list[str] = []
    leaked = sorted(set(_walk_keys(results)) & PUBLIC_FORBIDDEN_KEYS)
    if leaked:
        violations.append(f"public G7 output contains forbidden keys: {leaked}")
    evidence = results.get("evidence")
    if not isinstance(evidence, Mapping):
        return violations + ["public G7 evidence is missing"]
    owners = evidence.get("owner_sources")
    if not isinstance(owners, Mapping) or set(owners) != {"O_Q", "O_V", "O_P"}:
        violations.append("owner process evidence is incomplete")
    else:
        for field in ("process_id", "state_source_id", "act_source_id", "state_path"):
            values = [owners[owner].get(field) for owner in sorted(owners)]
            if any(value in (None, "") for value in values) or len(values) != len(
                set(values)
            ):
                violations.append(f"owner {field} boundary is not distinct")
    for attack_id, outcome in (evidence.get("owner_binding_attacks") or {}).items():
        if (
            outcome.get("accepted")
            or outcome.get("finalized")
            or outcome.get("state_act_count") != 0
            or outcome.get("worker_exit_code") != 0
        ):
            violations.append(f"owner attack was not fail closed: {attack_id}")
    for attack_id, outcome in (evidence.get("receipt_consumption_attacks") or {}).items():
        if outcome.get("committed") or outcome.get("target_transition_count") != 0:
            violations.append(f"receipt attack reached target transition: {attack_id}")
    receipt_issuers = evidence.get("receipt_issuer_sources")
    target_consumption = evidence.get("target_receipt_consumption") or {}
    if not isinstance(receipt_issuers, Mapping) or set(receipt_issuers) != {
        "O_R",
        "O_S",
    }:
        violations.append("receipt issuer process evidence is incomplete")
    else:
        issuer_pids = [
            receipt_issuers[owner].get("process_id") for owner in ("O_R", "O_S")
        ]
        if (
            len(set(issuer_pids)) != 2
            or target_consumption.get("target_process_id") in issuer_pids
        ):
            violations.append("receipt issuers and target process are not distinct")
        for field in ("state_source_id", "act_source_id", "state_path"):
            values = [
                receipt_issuers[owner].get(field) for owner in ("O_R", "O_S")
            ]
            if any(value in (None, "") for value in values) or len(set(values)) != 2:
                violations.append(f"receipt issuer {field} is not distinct")
    migration = evidence.get("migration")
    if not isinstance(migration, Mapping):
        violations.append("migration evidence is missing")
    else:
        source = migration.get("source_runtime") or {}
        target = migration.get("target_runtime") or {}
        restart = migration.get("old_runtime_restart") or {}
        if source.get("process_id") == target.get("process_id"):
            violations.append("source and target process are not distinct")
        if source.get("termination_observed") is not True:
            violations.append("source termination was not observed")
        if restart.get("fence_result") != "REJECTED_OLD_EPOCH":
            violations.append("old epoch was not explicitly rejected")
        lineage = migration.get("lineage_verification") or {}
        recovery = migration.get("recovery") or {}
        provenance = evidence.get("byte_provenance") or {}
        occurrence = provenance.get("effect_occurrence") or {}
        if lineage.get("effect_hash") != occurrence.get("bytes_hash"):
            violations.append("occurrence reference is not derived from actual bytes")
        if isinstance(owners, Mapping):
            expected_owner_refs = {
                owners[owner].get("response_bytes_hash")
                for owner in ("O_Q", "O_V")
                if owner in owners
            }
            if set(recovery.get("acceptance_hashes", [])) != expected_owner_refs:
                violations.append("owner response references are not actual frame hashes")
            if recovery.get("finality_hash") != owners.get("O_P", {}).get(
                "response_bytes_hash"
            ):
                violations.append("O_P response reference is not the actual frame hash")
    envelope = results.get("integration_envelope")
    if (
        not isinstance(envelope, Mapping)
        or envelope.get("namespace") != "G7"
        or envelope.get("qualification") != "QUALIFIED_COMPONENT_OUTPUT"
    ):
        violations.append("qualified G7 integration envelope is missing")
    return violations


def _history_chain_valid(records: list[Mapping[str, Any]]) -> bool:
    if not records:
        return False
    try:
        AppendOnlyHistory.import_verified(
            "result-audit", records, records[-1]["record_hash"]
        )
    except (KeyError, ValueError):
        return False
    return True


def audit_results(results: Mapping[str, Any]) -> list[str]:
    violations: list[str] = []
    aggregate = results["aggregate"]
    for metric in (
        "unsafe_effect",
        "duplicate_effect",
        "wrong_object_reliance",
        "unreconciled_effect",
        "history_rewrite",
    ):
        if aggregate[metric] != 0:
            violations.append(f"aggregate {metric} is nonzero")

    e4 = results["cases"]["E4"]
    events = [record["event"] for record in e4["history"]]
    if "DEFEATER_APPENDED" not in events:
        violations.append("E4 revocation defeater is not append-only history")
    if "ALTERNATIVE_COMMITMENT_FORMED" not in events:
        violations.append("E4 alternative commitment missing")
    if e4["final_action"] == "CONTINUE":
        violations.append("E4 continued the revoked primary path")
    if not e4["RecoveryToValue"]:
        violations.append("E4 did not recover to exact task value")
    e4_receipts = e4["acceptance"].get("owner_receipts", {})
    if set(e4_receipts) != {"O_Q", "O_V"} or any(
        receipt.get("decision") != "ACCEPTED"
        for receipt in e4_receipts.values()
    ):
        violations.append("E4 distinct requester/venue Acceptance is incomplete")
    if set(e4["settlement"].get("acceptance_evidence_hashes", ())) != {
        receipt.get("evidence_hash") for receipt in e4_receipts.values()
    }:
        violations.append("E4 Settlement is not bound to both Acceptance receipts")
    if not _history_chain_valid(e4["history"]):
        violations.append("E4 emitted history chain is invalid")

    e6 = results["cases"]["E6"]
    if e6["effect_count"] != 1:
        violations.append("E6 authoritative Effect count is not one")
    if e6["old_runtime_restart"]["outcome"] != "FENCED_OR_DENIED":
        violations.append("E6 old runtime restart was not fenced")
    if not e6["history_prefix_preserved"]:
        violations.append("E6 source history prefix was rewritten")
    if not _history_chain_valid(e6["history"]):
        violations.append("E6 emitted history chain is invalid")
    if not e6["reconciliation"]["complete"] or e6["reconciliation"]["after"]:
        violations.append("E6 Effect reconciliation is incomplete")
    if e6["acceptance"]["decision"] != "ACCEPTED":
        violations.append("E6 exact Acceptance was not restored")
    e6_receipts = e6["acceptance"].get("owner_receipts", {})
    if set(e6_receipts) != {"O_Q", "O_V"} or any(
        receipt.get("decision") != "ACCEPTED"
        for receipt in e6_receipts.values()
    ):
        violations.append("E6 distinct requester/venue Acceptance is incomplete")
    if set(e6["settlement"].get("acceptance_evidence_hashes", ())) != {
        receipt.get("evidence_hash") for receipt in e6_receipts.values()
    }:
        violations.append("E6 Settlement is not bound to both Acceptance receipts")
    if e6["settlement"]["status"] != "SETTLED":
        violations.append("E6 Settlement lineage was not restored")

    field_loss = results["interventions"]["DROP_MIGRATION_CAPSULE_FIELD"]
    if field_loss["migration_import"]["imported"]:
        violations.append("capsule field loss was imported")
    if field_loss["dispatch_after_import"]:
        violations.append("capsule field loss dispatched an Effect")
    if field_loss["final_action"] != "BOUNDED_UNKNOWN":
        violations.append("capsule field loss did not fail closed")
    return violations
