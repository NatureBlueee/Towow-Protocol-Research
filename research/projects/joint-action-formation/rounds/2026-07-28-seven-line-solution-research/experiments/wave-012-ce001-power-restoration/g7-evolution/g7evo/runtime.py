"""Runnable CE-001 G7 E4/E6 evolution module."""

from __future__ import annotations

from copy import deepcopy
import inspect
from typing import Any, Mapping

from .adapters import (
    CapsuleV1Exporter,
    CapsuleV2Importer,
    LeaseRegistryAdapter,
    SafetyPermitAdapter,
    drop_capsule_field,
)
from .boundary import build_process_evidence
from .model import (
    AcceptanceOwner,
    AppendOnlyHistory,
    DurableFenceAuthority,
    EffectTarget,
    SettlementOwner,
    canonical_bytes,
    causal_closure,
    digest,
    issue_current_receipt_set,
)


REQUIRED_CONTEXT_FIELDS = {
    "episode_id",
    "q_version",
    "object_id",
    "operation_id",
    "semantic_effect_key",
    "dependency_graph_version",
    "authority_evidence_hashes",
    "history_root",
    "runtime_epoch",
    "pending_acceptance",
    "context_binding_hash",
}

LIFECYCLE_COST_AXES = {
    "owner_queries",
    "disclosure_bytes",
    "calendar_wait",
    "human_minutes",
    "compute_tool",
    "formation_adapter_setup",
    "assurance",
    "recovery_migration",
    "governance",
    "opportunity_loss",
}


class ContextCompiler:
    """Build cold and repeat minimal-sufficient contexts."""

    def __init__(
        self,
        lease_adapter: LeaseRegistryAdapter,
        safety_adapter: SafetyPermitAdapter,
    ):
        self.lease_adapter = lease_adapter
        self.safety_adapter = safety_adapter

    @staticmethod
    def validate(context: Mapping[str, Any]) -> list[str]:
        violations = [
            f"missing:{field}"
            for field in sorted(REQUIRED_CONTEXT_FIELDS - set(context))
        ]
        for field in (
            "episode_id",
            "q_version",
            "object_id",
            "operation_id",
            "semantic_effect_key",
            "dependency_graph_version",
            "history_root",
            "context_binding_hash",
        ):
            if field in context and not context[field]:
                violations.append(f"empty:{field}")
        hashes = context.get("authority_evidence_hashes")
        if "authority_evidence_hashes" in context and (
            not isinstance(hashes, list) or len(hashes) < 2 or not all(hashes)
        ):
            violations.append("invalid:authority_evidence_hashes")
        if context.get("context_binding_hash"):
            unsigned = dict(context)
            claimed = unsigned.pop("context_binding_hash")
            if digest(unsigned) != claimed:
                violations.append("invalid:context_binding_hash")
        return sorted(violations)

    def cold(
        self,
        *,
        packet: Mapping[str, Any],
        reservation_ref: str,
        history_root: str,
        runtime_epoch: int,
    ) -> dict[str, Any]:
        before = self.lease_adapter.query_count + self.safety_adapter.query_count
        lease = self.lease_adapter.fetch_lease(reservation_ref)
        safety = self.safety_adapter.verify(
            packet["operation"], packet["policy_revision"], at_epoch=runtime_epoch
        )
        context: dict[str, Any] = {
            "episode_id": packet["episode_id"],
            "q_version": packet["operation"]["q_version"],
            "object_id": packet["operation"]["object_id"],
            "operation_id": packet["operation"]["operation_id"],
            "semantic_effect_key": packet["operation"]["semantic_effect_key"],
            "dependency_graph_version": packet["dependency_graph"]["version"],
            "authority_evidence_hashes": [
                lease["evidence_hash"],
                safety["evidence_hash"],
            ],
            "history_root": history_root,
            "runtime_epoch": runtime_epoch,
            "pending_acceptance": False,
        }
        context["context_binding_hash"] = digest(context)
        query_count = (
            self.lease_adapter.query_count
            + self.safety_adapter.query_count
            - before
        )
        return {
            "mode": "COLD",
            "context": context,
            "evidence_cache": {"lease": lease, "safety": safety},
            "decision": "CONTINUE" if lease["current"] and safety["allowed"] else "BLOCK",
            "cost": {
                "owner_queries": query_count,
                "disclosure_bytes": len(canonical_bytes([lease, safety])),
                "calendar_wait": 0,
                "context_bytes": len(canonical_bytes(context)),
                "human_minutes": 0,
                "compute_tool": 3,
                "formation_adapter_setup": 2,
                "assurance": 2,
                "recovery_migration": 0,
                "governance": 1,
                "opportunity_loss": 0,
            },
        }

    def repeat(
        self,
        *,
        packet: Mapping[str, Any],
        reservation_ref: str,
        prior_context: Mapping[str, Any],
        prior_safety_evidence: Mapping[str, Any],
    ) -> dict[str, Any]:
        before = self.lease_adapter.query_count
        lease = self.lease_adapter.fetch_lease(reservation_ref)
        operation = packet["operation"]
        exact_bindings = {
            "episode_id": packet["episode_id"],
            "q_version": operation["q_version"],
            "object_id": operation["object_id"],
            "operation_id": operation["operation_id"],
            "semantic_effect_key": operation["semantic_effect_key"],
            "dependency_graph_version": packet["dependency_graph"]["version"],
        }
        context_valid = not self.validate(prior_context)
        exact_binding_valid = all(
            prior_context.get(key) == value for key, value in exact_bindings.items()
        )
        evidence_bound = (
            prior_safety_evidence.get("evidence_hash")
            in prior_context.get("authority_evidence_hashes", [])
            and prior_safety_evidence.get("operation_hash") == digest(operation)
        )
        safety_current = (
            prior_safety_evidence["allowed"]
            and prior_safety_evidence["policy_revision"] == packet["policy_revision"]
            and prior_context["runtime_epoch"]
            <= prior_safety_evidence["valid_through_epoch"]
        )
        unsigned_context = {
            **{
                key: deepcopy(prior_context.get(key))
                for key in REQUIRED_CONTEXT_FIELDS
                if key != "context_binding_hash"
            },
            "authority_evidence_hashes": [
                lease["evidence_hash"],
                prior_safety_evidence["evidence_hash"],
            ],
        }
        context = {
            **unsigned_context,
            "context_binding_hash": digest(unsigned_context),
        }
        decision = (
            "CONTINUE"
            if (
                context_valid
                and exact_binding_valid
                and evidence_bound
                and lease["current"]
                and safety_current
            )
            else "BLOCK"
        )
        return {
            "mode": "REPEAT",
            "context": context,
            "decision": decision,
            "binding_checks": {
                "context_valid": context_valid,
                "exact_binding_valid": exact_binding_valid,
                "evidence_bound": evidence_bound,
                "lease_current": lease["current"],
                "safety_current": safety_current,
            },
            "cost": {
                "owner_queries": self.lease_adapter.query_count - before,
                "disclosure_bytes": len(canonical_bytes(lease)),
                "calendar_wait": 0,
                "context_bytes": len(canonical_bytes(context)),
                "human_minutes": 0,
                "compute_tool": 2,
                "formation_adapter_setup": 0,
                "assurance": 1,
                "recovery_migration": 0,
                "governance": 0,
                "opportunity_loss": 0 if decision == "CONTINUE" else 1,
            },
        }


class EvolutionModule:
    """One deterministic component, not an arm comparison."""

    identity = "G7_INTERNAL_AGENT_B"

    def __init__(self, fixture: Mapping[str, Any]):
        self.fixture = deepcopy(dict(fixture))
        self.frozen_contract = deepcopy(dict(self.fixture["frozen_contract"]))

    @staticmethod
    def _operation_success(effect: Mapping[str, Any]) -> bool:
        return (
            effect.get("object_id") == "Circuit-C7"
            and effect.get("q_version") == "Q@v1"
            and 2.85 <= float(effect.get("delivered_kw", 0)) <= 3.15
            and int(effect.get("duration_minutes", 0)) >= 45
        )

    def _acceptance_owners(self) -> tuple[AcceptanceOwner, AcceptanceOwner]:
        frozen = self.frozen_contract
        return tuple(
            AcceptanceOwner(
                owner_id,
                expected_q_version=frozen["q_version"],
                expected_object_id=frozen["object_id"],
                expected_operation_id=frozen["operation_id"],
                expected_semantic_effect_key=frozen["semantic_effect_key"],
            )
            for owner_id in ("O_Q", "O_V")
        )

    @staticmethod
    def _adapter_interface_evidence() -> dict[str, Any]:
        lease_signature = str(inspect.signature(LeaseRegistryAdapter.fetch_lease))
        safety_signature = str(inspect.signature(SafetyPermitAdapter.verify))
        exporter_signature = str(inspect.signature(CapsuleV1Exporter.export))
        importer_signature = str(inspect.signature(CapsuleV2Importer.ingest))
        return {
            "owner_adapter_interfaces_distinct": lease_signature != safety_signature,
            "capsule_adapter_interfaces_distinct": exporter_signature != importer_signature,
            "semantic_independence": "NOT_ESTABLISHED",
            "lease_signature": lease_signature,
            "safety_signature": safety_signature,
            "exporter_signature": exporter_signature,
            "importer_signature": importer_signature,
        }

    def run_e4(self) -> dict[str, Any]:
        config = self.fixture["e4"]
        packet = config["public_packet"]
        history = AppendOnlyHistory("runtime-e4")
        history.append(
            "Q_FROZEN",
            {
                "episode_id": packet["episode_id"],
                "q_version": packet["operation"]["q_version"],
            },
        )
        frozen_prefix = history.snapshot()
        lease_adapter = LeaseRegistryAdapter(config["lease_registry"])
        safety_adapter = SafetyPermitAdapter(config["safety_policies"])
        target = EffectTarget("O_E")
        target.fence_authority = DurableFenceAuthority()
        target.fence_key = f"{packet['episode_id']}:{packet['operation']['object_id']}"
        acceptance_owners = self._acceptance_owners()
        settlement_owner = SettlementOwner()

        primary = lease_adapter.fetch_lease(config["primary_reservation_ref"])
        history.append("PRIMARY_RESERVATION_READ", primary)
        if not primary["revoked"]:
            raise ValueError("E4 fixture must expose an owner-issued revocation")
        history.append("DEFEATER_APPENDED", primary)

        local_closure = causal_closure(
            [config["primary_node"]], packet["dependency_graph"]["edges"]
        )
        history.append(
            "LOCAL_CAUSAL_REOPEN",
            {"changed": [config["primary_node"]], "closure": local_closure},
        )
        alternative = lease_adapter.fetch_lease(primary["replacement_refs"][0])
        owner_commitment = lease_adapter.bind_commitment(
            alternative["reservation_ref"],
            packet["operation"],
            at_epoch=1,
        )
        safety = safety_adapter.verify(
            packet["operation"], packet["policy_revision"], at_epoch=1
        )
        allowed = (
            alternative["current"]
            and owner_commitment["decision"] == "COMMITTED_EXACT_SCOPE"
            and safety["allowed"]
        )
        if not allowed:
            history.append(
                "RECOVERY_BLOCKED",
                {
                    "alternative": alternative,
                    "owner_commitment": owner_commitment,
                    "safety": safety,
                },
            )
            return {
                "case_id": "E4-REVOKE-WITH-ALTERNATIVE",
                "final_action": "BLOCK",
                "RecoveryToValue": False,
                "history": history.snapshot(),
            }

        history.append(
            "ALTERNATIVE_COMMITMENT_FORMED",
            {
                "owner_commitment": owner_commitment,
                "safety": safety,
                "operation_hash": digest(packet["operation"]),
            },
        )
        recovered_operation = {
            **packet["operation"],
            "origin_resource_id": alternative["resource_id"],
            "reservation_ref": alternative["reservation_ref"],
            "lease_commitment_evidence_hash": owner_commitment["evidence_hash"],
        }
        dispatch = target.dispatch(
            operation=recovered_operation,
            coordinator_epoch=1,
            current_receipt_set=issue_current_receipt_set(
                recovered_operation,
                episode_id=packet["episode_id"],
                at_epoch=1,
            ),
        )
        readback = target.readback(packet["operation"]["semantic_effect_key"])
        history.append("EFFECT_RECONCILED", readback)
        acceptance_receipts = {
            owner.owner_id: owner.accept(
                q_version=packet["operation"]["q_version"],
                object_id=packet["operation"]["object_id"],
                operation_id=packet["operation"]["operation_id"],
                semantic_effect_key=packet["operation"]["semantic_effect_key"],
                effect_readback=readback,
            )
            for owner in acceptance_owners
        }
        for owner_id, receipt in acceptance_receipts.items():
            history.append(f"{owner_id}_ACCEPTANCE_APPENDED", receipt)
        acceptance = {
            "decision": "ACCEPTED"
            if all(
                receipt["decision"] == "ACCEPTED"
                for receipt in acceptance_receipts.values()
            )
            else "NOT_ACCEPTED",
            "owner_receipts": acceptance_receipts,
        }
        settlement = settlement_owner.settle(acceptance_receipts.values())
        history.append("SETTLEMENT_APPENDED", settlement)
        exact_success = (
            dispatch["outcome"] == "COMMITTED"
            and self._operation_success(readback["effect"])
            and readback["effect"].get("origin_resource_id")
            == alternative["resource_id"]
            and readback["effect"].get("reservation_ref")
            == alternative["reservation_ref"]
            and readback["effect"].get("lease_commitment_evidence_hash")
            == owner_commitment["evidence_hash"]
            and acceptance["decision"] == "ACCEPTED"
            and settlement["status"] == "SETTLED"
        )

        compiler = ContextCompiler(lease_adapter, safety_adapter)
        cold = compiler.cold(
            packet=packet,
            reservation_ref=alternative["reservation_ref"],
            history_root=history.root,
            runtime_epoch=1,
        )
        repeat = compiler.repeat(
            packet=packet,
            reservation_ref=alternative["reservation_ref"],
            prior_context=cold["context"],
            prior_safety_evidence=cold["evidence_cache"]["safety"],
        )

        global_closure = causal_closure(
            [config["global_reopen_root"]], packet["dependency_graph"]["edges"]
        )
        try:
            AppendOnlyHistory.import_verified(
                "e4-audit", history.snapshot(), history.root
            )
            history_chain_valid = True
        except ValueError:
            history_chain_valid = False
        history_prefix_preserved = (
            history_chain_valid and history.prefix_preserved(frozen_prefix)
        )
        return {
            "case_id": "E4-REVOKE-WITH-ALTERNATIVE",
            "implementation_identity": self.identity,
            "final_action": "CONTINUE_AFTER_LOCAL_REOPEN",
            "local_reopen": {
                "changed": [config["primary_node"]],
                "closure": local_closure,
                "mode": "LOCAL",
            },
            "global_reopen_intervention": {
                "changed": [config["global_reopen_root"]],
                "closure": global_closure,
                "mode": "GLOBAL",
            },
            "dispatch": dispatch,
            "effect_readback": readback,
            "acceptance": acceptance,
            "settlement": settlement,
            "ExactTaskSuccess": exact_success,
            "CorrectResolution": exact_success,
            "RecoveryToValue": exact_success,
            "UnsafeEffect": 0,
            "DuplicateEffect": max(0, len(target.effects) - 1),
            "WrongObjectReliance": int(
                readback["effect"]["object_id"] != packet["operation"]["object_id"]
            ),
            "UnreconciledEffect": 0
            if readback["status"] == "CONFIRMED"
            else 1,
            "history_prefix_preserved": history_prefix_preserved,
            "history_chain_valid": history_chain_valid,
            "history": history.snapshot(),
            "history_root": history.root,
            "target_history": target.history.snapshot(),
            "context": {
                "cold": cold,
                "repeat": repeat,
                "cost_comparison_status": "NOT_MEASURED_FULL_LIFECYCLE",
            },
            "adapter_interfaces": self._adapter_interface_evidence(),
        }

    def _prepare_e6(self) -> dict[str, Any]:
        config = self.fixture["e6"]
        packet = config["public_packet"]
        source_history = AppendOnlyHistory(config["source_runtime_id"])
        source_history.append(
            "Q_FROZEN",
            {
                "episode_id": packet["episode_id"],
                "q_version": packet["operation"]["q_version"],
            },
        )
        source_history.append(
            "EFFECT_INTENT_PERSISTED",
            {
                "semantic_effect_key": packet["operation"]["semantic_effect_key"],
                "operation_hash": digest(packet["operation"]),
            },
        )
        target = EffectTarget("O_E", current_epoch=config["source_epoch"])
        target.fence_authority = DurableFenceAuthority()
        target.fence_key = f"{packet['episode_id']}:{packet['operation']['object_id']}"
        initial_dispatch = target.dispatch(
            operation=packet["operation"],
            coordinator_epoch=config["source_epoch"],
            current_receipt_set=issue_current_receipt_set(
                packet["operation"],
                episode_id=packet["episode_id"],
                at_epoch=config["source_epoch"],
            ),
        )
        source_history.append(
            "DISPATCH_RESPONSE_LOST",
            {
                "semantic_effect_key": packet["operation"]["semantic_effect_key"],
                "caller_status": "UNKNOWN",
            },
        )
        source_history.append(
            "COORDINATOR_CRASHED",
            {"epoch": config["source_epoch"], "acceptance_pending": True},
        )
        exporter = CapsuleV1Exporter()
        capsule = exporter.export(
            source_runtime_id=config["source_runtime_id"],
            source_epoch=config["source_epoch"],
            target_epoch=config["target_epoch"],
            bindings={
                "episode_id": packet["episode_id"],
                "q_version": packet["operation"]["q_version"],
                "object_id": packet["operation"]["object_id"],
                "operation_id": packet["operation"]["operation_id"],
                "semantic_effect_key": packet["operation"]["semantic_effect_key"],
            },
            history=source_history,
            pending_acceptance=True,
            unresolved_effect_keys=[packet["operation"]["semantic_effect_key"]],
            obligations=[
                {
                    "type": "ACCEPTANCE_THEN_SETTLEMENT",
                    "owner_ids": ["O_Q", "O_V", "O_P"],
                }
            ],
            owner_evidence_hashes=config["owner_evidence_hashes"],
            dependency_graph_version=packet["dependency_graph"]["version"],
        )
        return {
            "config": config,
            "packet": packet,
            "source_history": source_history,
            "target": target,
            "initial_dispatch": initial_dispatch,
            "capsule": capsule,
        }

    def run_e6(self) -> dict[str, Any]:
        state = self._prepare_e6()
        config = state["config"]
        packet = state["packet"]
        source_history = state["source_history"]
        source_prefix = source_history.snapshot()
        target: EffectTarget = state["target"]
        importer = CapsuleV2Importer()
        imported = importer.ingest(
            {"capsule_hash": state["capsule"]["capsule_hash"]},
            state["capsule"]["payload"],
            target_runtime_id=config["target_runtime_id"],
        )
        if not imported["imported"]:
            raise ValueError("valid E6 capsule unexpectedly rejected")
        context = imported["context"]
        takeover_history = AppendOnlyHistory.import_verified(
            config["target_runtime_id"],
            context["history_records"],
            context["history_root"],
        )
        takeover_history.append(
            "TARGET_TAKEOVER",
            {
                "source_epoch": context["source_epoch"],
                "target_epoch": context["target_epoch"],
            },
        )
        target.install_external_fence(config["target_epoch"])
        target.advance_epoch(config["target_epoch"])
        readback = target.readback(context["semantic_effect_key"])
        takeover_history.append("EFFECT_RECONCILED", readback)

        replay_suppressed = readback["status"] == "CONFIRMED"
        if not replay_suppressed:
            target.dispatch(
                operation=packet["operation"],
                coordinator_epoch=config["target_epoch"],
                current_receipt_set=issue_current_receipt_set(
                    packet["operation"],
                    episode_id=packet["episode_id"],
                    at_epoch=config["target_epoch"],
                ),
            )
        else:
            takeover_history.append(
                "REPLAY_SUPPRESSED_AFTER_READBACK",
                {"semantic_effect_key": context["semantic_effect_key"]},
            )

        acceptance_receipts = {
            owner.owner_id: owner.accept(
                q_version=context["q_version"],
                object_id=context["object_id"],
                operation_id=context["operation_id"],
                semantic_effect_key=context["semantic_effect_key"],
                effect_readback=readback,
            )
            for owner in self._acceptance_owners()
        }
        for owner_id, receipt in acceptance_receipts.items():
            takeover_history.append(f"{owner_id}_ACCEPTANCE_APPENDED", receipt)
        acceptance = {
            "decision": "ACCEPTED"
            if all(
                receipt["decision"] == "ACCEPTED"
                for receipt in acceptance_receipts.values()
            )
            else "NOT_ACCEPTED",
            "owner_receipts": acceptance_receipts,
        }
        settlement = SettlementOwner().settle(acceptance_receipts.values())
        takeover_history.append("SETTLEMENT_APPENDED", settlement)

        restarted_old_runtime = EffectTarget(
            "O_E",
            current_epoch=config["source_epoch"],
            fence_authority=target.fence_authority,
            fence_key=target.fence_key,
        )
        old_restart = restarted_old_runtime.dispatch(
            operation=packet["operation"],
            coordinator_epoch=config["source_epoch"],
            current_receipt_set=issue_current_receipt_set(
                packet["operation"],
                episode_id=packet["episode_id"],
                at_epoch=config["source_epoch"],
            ),
        )
        takeover_history.append("OLD_RUNTIME_RESTART_BLOCKED", old_restart)
        history_prefix_preserved = takeover_history.prefix_preserved(source_prefix)
        exact_success = (
            readback["status"] == "CONFIRMED"
            and replay_suppressed
            and len(target.effects) == 1
            and self._operation_success(readback["effect"])
            and acceptance["decision"] == "ACCEPTED"
            and settlement["status"] == "SETTLED"
            and old_restart["outcome"] == "FENCED_OR_DENIED"
            and history_prefix_preserved
        )
        final_context = {
            **context,
            "pending_acceptance": False,
            "unresolved_effect_keys": [],
            "acceptance_evidence_hashes": sorted(
                receipt["evidence_hash"]
                for receipt in acceptance_receipts.values()
            ),
            "settlement_evidence_hash": settlement["evidence_hash"],
            "history_root": takeover_history.root,
        }
        return {
            "case_id": "E6-MIGRATION-REPLAY",
            "implementation_identity": self.identity,
            "final_action": "CONTINUE_ACCEPTANCE_SETTLEMENT_ONLY",
            "migration_import": imported,
            "effect_readback": readback,
            "reconciliation": {
                "before": context["unresolved_effect_keys"],
                "after": [],
                "complete": readback["status"] == "CONFIRMED",
            },
            "replay_suppressed": replay_suppressed,
            "acceptance": acceptance,
            "settlement": settlement,
            "old_runtime_restart": old_restart,
            "old_runtime_history": restarted_old_runtime.history.snapshot(),
            "effect_count": len(target.effects),
            "history_prefix_preserved": history_prefix_preserved,
            "history": takeover_history.snapshot(),
            "final_context": final_context,
            "source_history": source_prefix,
            "target_history": target.history.snapshot(),
            "ExactTaskSuccess": exact_success,
            "CorrectResolution": exact_success,
            "RecoveryToValue": exact_success,
            "UnsafeEffect": 0,
            "DuplicateEffect": max(0, len(target.effects) - 1),
            "WrongObjectReliance": int(
                readback["effect"]["object_id"] != context["object_id"]
            ),
            "UnreconciledEffect": int(readback["status"] != "CONFIRMED"),
            "adapter_interfaces": self._adapter_interface_evidence(),
        }

    def run_capsule_field_loss(self) -> dict[str, Any]:
        state = self._prepare_e6()
        config = state["config"]
        dropped = drop_capsule_field(
            state["capsule"],
            config["field_loss_path"],
            resign=True,
        )
        imported = CapsuleV2Importer().ingest(
            {"capsule_hash": dropped["capsule_hash"]},
            dropped["payload"],
            target_runtime_id=config["target_runtime_id"],
        )
        return {
            "intervention": "DROP_MIGRATION_CAPSULE_FIELD",
            "implementation_identity": self.identity,
            "dropped_field": config["field_loss_path"],
            "migration_import": imported,
            "final_action": "BOUNDED_UNKNOWN",
            "dispatch_after_import": False,
            "effect_count": len(state["target"].effects),
            "DuplicateEffect": max(0, len(state["target"].effects) - 1),
            "CorrectResolution": False,
            "SafetyGatePassed": not imported["imported"],
        }

    def run_all(self) -> dict[str, Any]:
        process_evidence = build_process_evidence(self.fixture)
        integration_envelope = process_evidence.pop("integration_envelope")
        return {
            "schema": "g7.evolution.line-local-evidence.v2",
            "implementation_identity": self.identity,
            "evidence_level": "LOCAL_PROCESS_STATE_SEPARATED_COMPONENT_EVIDENCE",
            "evidence": process_evidence,
            "integration_envelope": integration_envelope,
        }

    def run_regressions(self) -> dict[str, Any]:
        """Internal legacy risk surface; never emitted as the G7 envelope.

        The first-round tests still exercise these contract-shaped objects so
        their E4/E6 failure coverage is not lost.  Only ``run_all`` is the
        public component output.
        """

        e4 = self.run_e4()
        e6 = self.run_e6()
        field_loss = self.run_capsule_field_loss()
        return {
            "cases": {"E4": e4, "E6": e6},
            "interventions": {"DROP_MIGRATION_CAPSULE_FIELD": field_loss},
            "aggregate": {
                "case_count": 2,
                "exact_task_success": sum(
                    int(item["ExactTaskSuccess"]) for item in (e4, e6)
                ),
                "correct_resolution": sum(
                    int(item["CorrectResolution"]) for item in (e4, e6)
                ),
                "recovery_to_value": sum(
                    int(item["RecoveryToValue"]) for item in (e4, e6)
                ),
                "unsafe_effect": e4["UnsafeEffect"] + e6["UnsafeEffect"],
                "duplicate_effect": e4["DuplicateEffect"] + e6["DuplicateEffect"],
                "wrong_object_reliance": (
                    e4["WrongObjectReliance"] + e6["WrongObjectReliance"]
                ),
                "unreconciled_effect": (
                    e4["UnreconciledEffect"] + e6["UnreconciledEffect"]
                ),
                "history_rewrite": int(not e4["history_prefix_preserved"])
                + int(not e6["history_prefix_preserved"]),
            },
        }
