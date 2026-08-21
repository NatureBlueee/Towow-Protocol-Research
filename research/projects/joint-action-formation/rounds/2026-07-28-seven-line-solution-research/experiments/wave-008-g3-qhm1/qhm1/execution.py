"""Holder-executed runtime plus independent old-task verifiers."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from typing import Iterable

from .authorities import (
    ActionRequest,
    EffectClaim,
    HolderRegistry,
    Receipt,
)
from .model import AbstractState, initial_state, transition
from .spec import (
    ACTION_BY_NAME,
    OLD_TASK,
    RESOURCE_ACCOUNT,
    authorization_payload,
    canonical_json,
    expected_action_payload,
    expected_holder,
    fingerprint,
    frozen_package,
)
from .worlds import HiddenWorld


@dataclass(frozen=True)
class PublicFacts:
    public_trial_id: str
    initial_message: str
    route: str
    authorization: str
    schema: str
    value_floor: str


@dataclass(frozen=True)
class LedgerEntry:
    index: int
    action: str
    actor: str
    cost: int
    privacy_cost: int
    success: bool
    response_hash: str | None = None


@dataclass(frozen=True)
class TraceEvent:
    index: int
    action: str
    actor: str
    success: bool
    receipt_id: str | None
    response_hash: str | None = None


@dataclass(frozen=True)
class TargetRecord:
    artifact_hash: str
    schema: str
    projector: str
    project_receipt_id: str


@dataclass(frozen=True)
class InspectionRecord:
    public_trial_id: str
    task_fingerprint: str
    facts: PublicFacts
    facts_hash: str
    obligations: tuple[str, ...]
    ledger_index: int


@dataclass(frozen=True)
class EffectRecord:
    effect_log_id: str
    receipt_id: str
    action: str
    holder_id: str
    before_state_digest: str
    after_state_digest: str
    success: bool


@dataclass(frozen=True)
class VerificationBundle:
    public_trial_id: str
    task_version: str
    package_fingerprint: str
    state: AbstractState
    trace: tuple[TraceEvent, ...]
    receipts: tuple[Receipt, ...]
    target_records: tuple[TargetRecord, ...]
    inspection_records: tuple[InspectionRecord, ...]
    ledger_entries: tuple[LedgerEntry, ...]
    ledger_intact: bool


@dataclass(frozen=True)
class TrustedEvidenceAnchor:
    bundle_fingerprint: str
    inspection_records: tuple[InspectionRecord, ...]
    effect_records: tuple[EffectRecord, ...]


@dataclass(frozen=True)
class Evaluation:
    qualified: bool
    reasons: tuple[str, ...]
    authority_valid: bool
    target_valid: bool
    acceptance_valid: bool
    cost_valid: bool
    information_valid: bool
    evidence_seal_valid: bool
    task_invariant: bool


class AuthoritativeCostLedger:
    def __init__(self):
        self._entries: list[LedgerEntry] = []
        self.intact = True

    @property
    def cost_used(self) -> int:
        return sum(entry.cost for entry in self._entries)

    @property
    def steps_used(self) -> int:
        return len(self._entries)

    @property
    def privacy_cost_used(self) -> int:
        return sum(entry.privacy_cost for entry in self._entries)

    def can_charge(self, cost: int, privacy_cost: int) -> bool:
        return (
            self.steps_used + 1 <= RESOURCE_ACCOUNT.horizon
            and self.cost_used + cost <= RESOURCE_ACCOUNT.max_cost
            and self.privacy_cost_used + privacy_cost
            <= RESOURCE_ACCOUNT.max_privacy_cost
        )

    def record(
        self,
        action: str,
        actor: str,
        cost: int,
        privacy_cost: int,
        success: bool,
        response_hash: str | None = None,
    ) -> None:
        self._entries.append(
            LedgerEntry(
                index=len(self._entries),
                action=action,
                actor=actor,
                cost=cost,
                privacy_cost=privacy_cost,
                success=success,
                response_hash=response_hash,
            )
        )

    def bind_response(self, index: int, response_hash: str) -> None:
        entry = self._entries[index]
        if entry.action != "INSPECT" or entry.response_hash is not None:
            raise RuntimeError("response binding is only valid once for INSPECT")
        self._entries[index] = replace(
            entry,
            response_hash=response_hash,
        )

    def snapshot(self) -> tuple[LedgerEntry, ...]:
        return tuple(self._entries)


class TargetStore:
    def __init__(self):
        self._records: list[TargetRecord] = []

    def project(self, holder_id: str, receipt_id: str) -> None:
        self._records.append(
            TargetRecord(
                artifact_hash=OLD_TASK.artifact_hash,
                schema=OLD_TASK.target_schema,
                projector=holder_id,
                project_receipt_id=receipt_id,
            )
        )

    def snapshot(self) -> tuple[TargetRecord, ...]:
        return tuple(self._records)


class TrialGateway:
    """Narrow public interface; the hidden world itself is not returned."""

    def __init__(self, runtime: "TrialRuntime"):
        self._runtime = runtime

    @property
    def public_trial_id(self) -> str:
        return self._runtime.world.public_trial_id

    @property
    def initial_message(self) -> str:
        return self._runtime.world.initial_message

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(ACTION_BY_NAME)

    def inspect(self) -> PublicFacts:
        return self._runtime.inspect()

    def perform(self, action: str) -> bool:
        return self._runtime.perform(action)


class TrialRuntime:
    def __init__(self, world: HiddenWorld):
        self.world = world
        self.package = frozen_package(world)
        self.state = initial_state(world)
        self.ledger = AuthoritativeCostLedger()
        self.target_store = TargetStore()
        self.trace: list[TraceEvent] = []
        self.receipts: list[Receipt] = []
        self.inspection_records: list[InspectionRecord] = []
        self.effect_records: list[EffectRecord] = []
        self.registry = HolderRegistry(
            self._holder_policy_allows,
            self._execute_holder_effect,
        )
        if world.authorization_policy == "PRESENT":
            request = ActionRequest(
                action="INITIAL_AUTHORIZATION",
                payload=authorization_payload(),
                task_fingerprint=fingerprint(OLD_TASK),
            )
            receipt = self.registry.dispatch(request)
            if receipt is None:
                raise RuntimeError("initial owner authorization failed")
            self.receipts.append(receipt)

    def gateway(self) -> TrialGateway:
        return TrialGateway(self)

    def _public_facts(self) -> PublicFacts:
        route = {
            "ALTERNATE_ACTIVE_UNADVERTISED": "READY_UNADVERTISED",
            "COMPATIBLE_DISABLED": "DISABLED_COMPATIBLE",
            "COMPATIBLE_ACTIVE": "READY_COMPATIBLE",
            "SCHEMA_BLOCKED": "BLOCKED_SCHEMA",
            "UNAVAILABLE": "UNAVAILABLE",
        }[self.world.route_state]
        return PublicFacts(
            public_trial_id=self.world.public_trial_id,
            initial_message=self.world.initial_message,
            route=route,
            authorization=self.world.authorization_policy,
            schema=self.world.schema_policy,
            value_floor="PASS" if self.world.value_floor_ok else "FAIL",
        )

    def inspect(self) -> PublicFacts:
        if not self.perform("INSPECT"):
            raise RuntimeError("inspection unavailable within budget")
        facts = self._public_facts()
        facts_hash = fingerprint(facts)
        index = len(self.trace) - 1
        self.trace[index] = replace(
            self.trace[index],
            response_hash=facts_hash,
        )
        self.ledger.bind_response(index, facts_hash)
        self.inspection_records.append(
            InspectionRecord(
                public_trial_id=self.world.public_trial_id,
                task_fingerprint=fingerprint(OLD_TASK),
                facts=facts,
                facts_hash=facts_hash,
                obligations=(
                    "task-bound use only",
                    "no authority inferred from disclosure",
                ),
                ledger_index=index,
            )
        )
        return facts

    def _payload(self, action: str) -> dict[str, str]:
        return expected_action_payload(action)

    def _allows(self, action: str) -> bool:
        return transition(self.world, self.state, action) is not None

    def _holder_policy_allows(self, request: ActionRequest) -> bool:
        if request.action == "INITIAL_AUTHORIZATION":
            return self.world.authorization_policy == "PRESENT"
        return self._allows(request.action)

    def _apply_effect(self, action: str) -> None:
        next_state = transition(self.world, self.state, action)
        if next_state is None:
            raise RuntimeError(f"holder invoked invalid transition: {action}")
        self.state = next_state

    def _execute_holder_effect(
        self,
        request: ActionRequest,
        receipt_id: str,
    ) -> EffectClaim:
        before = self.state.digest()
        if request.action != "INITIAL_AUTHORIZATION":
            self._apply_effect(request.action)
            if request.action == "PROJECT":
                self.target_store.project("T", receipt_id)
        after = self.state.digest()
        effect_log_id = (
            f"effect:{len(self.effect_records) + 1}:{receipt_id}"
        )
        record = EffectRecord(
            effect_log_id=effect_log_id,
            receipt_id=receipt_id,
            action=request.action,
            holder_id=expected_holder(request.action) or "",
            before_state_digest=before,
            after_state_digest=after,
            success=True,
        )
        self.effect_records.append(record)
        return EffectClaim(
            effect_log_id=effect_log_id,
            before_state_digest=before,
            after_state_digest=after,
            success=True,
        )

    def perform(self, action: str) -> bool:
        if action not in ACTION_BY_NAME:
            raise ValueError(f"action not in frozen capability set: {action}")
        spec = ACTION_BY_NAME[action]
        if not self.ledger.can_charge(spec.cost, spec.privacy_cost):
            return False

        actor = spec.holder if spec.holder is not None else "C"
        receipt: Receipt | None = None
        success = False
        if spec.holder is None:
            if self._allows(action):
                self._apply_effect(action)
                success = True
        else:
            request = ActionRequest(
                action=action,
                payload=self._payload(action),
                task_fingerprint=fingerprint(OLD_TASK),
            )
            receipt = self.registry.dispatch(request)
            success = receipt is not None
            if receipt is not None:
                self.receipts.append(receipt)

        self.ledger.record(
            action,
            actor,
            spec.cost,
            spec.privacy_cost,
            success,
        )
        self.trace.append(
            TraceEvent(
                index=len(self.trace),
                action=action,
                actor=actor,
                success=success,
                receipt_id=receipt.receipt_id if receipt else None,
                response_hash=None,
            )
        )
        return success

    def bundle(self) -> VerificationBundle:
        return VerificationBundle(
            public_trial_id=self.world.public_trial_id,
            task_version=OLD_TASK.task_version,
            package_fingerprint=self.package.package_fingerprint,
            state=self.state,
            trace=tuple(self.trace),
            receipts=tuple(self.receipts),
            target_records=self.target_store.snapshot(),
            inspection_records=tuple(self.inspection_records),
            ledger_entries=self.ledger.snapshot(),
            ledger_intact=self.ledger.intact,
        )

    def trusted_anchor(self) -> TrustedEvidenceAnchor:
        bundle = self.bundle()
        return TrustedEvidenceAnchor(
            bundle_fingerprint=fingerprint(bundle),
            inspection_records=tuple(self.inspection_records),
            effect_records=tuple(self.effect_records),
        )


class AuthorityVerifier:
    def __init__(
        self,
        trusted_registry: HolderRegistry,
        trusted_effect_records: tuple[EffectRecord, ...],
    ):
        self.trusted_registry = trusted_registry
        self.trusted_effect_records = trusted_effect_records

    def verify(self, bundle: VerificationBundle) -> bool:
        if len({receipt.receipt_id for receipt in bundle.receipts}) != len(
            bundle.receipts
        ):
            return False
        receipts = {receipt.receipt_id: receipt for receipt in bundle.receipts}
        effects = {
            record.effect_log_id: record
            for record in self.trusted_effect_records
        }
        for receipt in bundle.receipts:
            expected_payload_hash = hashlib.sha256(
                canonical_json(
                    expected_action_payload(receipt.action)
                ).encode("utf-8")
            ).hexdigest()
            if (
                receipt.holder_id == "C"
                or receipt.receipt_id
                != (
                    f"{receipt.holder_id}:{receipt.sequence}:"
                    f"{receipt.action}"
                )
                or expected_holder(receipt.action) != receipt.holder_id
                or receipt.task_fingerprint != fingerprint(OLD_TASK)
                or receipt.payload_hash != expected_payload_hash
                or not receipt.success
                or not self.trusted_registry.verify(receipt)
            ):
                return False
            effect = effects.get(receipt.effect_log_id)
            if (
                effect is None
                or effect.receipt_id != receipt.receipt_id
                or effect.action != receipt.action
                or effect.holder_id != receipt.holder_id
                or effect.before_state_digest
                != receipt.before_state_digest
                or effect.after_state_digest
                != receipt.after_state_digest
                or effect.success != receipt.success
            ):
                return False

        for event in bundle.trace:
            holder = expected_holder(event.action)
            if holder is None:
                if event.actor != "C" or event.receipt_id is not None:
                    return False
                continue
            if not event.success or event.receipt_id not in receipts:
                return False
            receipt = receipts[event.receipt_id]
            if event.actor != holder or receipt.action != event.action:
                return False

        authorization_receipts = [
            receipt
            for receipt in bundle.receipts
            if receipt.action in {"INITIAL_AUTHORIZATION", "ISSUE_AUTHORIZATION"}
        ]
        return any(
            receipt.holder_id == "O"
            and receipt.payload_hash
            == hashlib.sha256(
                canonical_json(authorization_payload()).encode("utf-8")
            ).hexdigest()
            and self.trusted_registry.verify(receipt)
            for receipt in authorization_receipts
        )


class TargetVerifier:
    def verify(self, bundle: VerificationBundle) -> bool:
        receipt_by_id = {
            receipt.receipt_id: receipt for receipt in bundle.receipts
        }
        project_events = [
            event
            for event in bundle.trace
            if event.action == "PROJECT" and event.success
        ]
        if len(project_events) != 1:
            return False
        project_receipt = receipt_by_id.get(
            project_events[0].receipt_id or ""
        )
        return (
            len(bundle.target_records) == 1
            and bundle.target_records[0].artifact_hash == OLD_TASK.artifact_hash
            and bundle.target_records[0].schema == OLD_TASK.target_schema
            and bundle.target_records[0].projector == "T"
            and project_receipt is not None
            and project_receipt.action == "PROJECT"
            and bundle.target_records[0].project_receipt_id
            == project_receipt.receipt_id
            and bundle.state.project_count == 1
            and bundle.state.readback
        )


class AcceptanceVerifier:
    def __init__(self, trusted_registry: HolderRegistry):
        self.trusted_registry = trusted_registry

    def verify(self, bundle: VerificationBundle) -> bool:
        receipt_by_id = {
            receipt.receipt_id: receipt for receipt in bundle.receipts
        }
        acceptance_events = [
            event
            for event in bundle.trace
            if event.action == "ACCEPT" and event.success
        ]
        if len(acceptance_events) != 1 or not bundle.state.accepted:
            return False
        receipt = receipt_by_id.get(acceptance_events[0].receipt_id or "")
        return bool(
            receipt
            and receipt.holder_id == "T"
            and receipt.action == "ACCEPT"
            and self.trusted_registry.verify(receipt)
        )


class CostVerifier:
    def verify(self, bundle: VerificationBundle) -> bool:
        if (
            not bundle.ledger_intact
            or len(bundle.ledger_entries) != len(bundle.trace)
            or len(bundle.ledger_entries) > RESOURCE_ACCOUNT.horizon
        ):
            return False
        for entry, event in zip(bundle.ledger_entries, bundle.trace):
            spec = ACTION_BY_NAME.get(event.action)
            if (
                spec is None
                or entry.index != event.index
                or entry.action != event.action
                or entry.actor != event.actor
                or entry.success != event.success
                or entry.response_hash != event.response_hash
                or entry.cost != spec.cost
                or entry.privacy_cost != spec.privacy_cost
            ):
                return False
        return (
            sum(entry.cost for entry in bundle.ledger_entries)
            <= RESOURCE_ACCOUNT.max_cost
            and sum(
                entry.privacy_cost for entry in bundle.ledger_entries
            )
            <= RESOURCE_ACCOUNT.max_privacy_cost
            and bundle.state.cost_used
            == sum(entry.cost for entry in bundle.ledger_entries)
            and bundle.state.privacy_cost_used
            == sum(
                entry.privacy_cost for entry in bundle.ledger_entries
            )
            and bundle.state.steps_used == len(bundle.ledger_entries)
            and sum(
                1
                for entry in bundle.ledger_entries
                if entry.success
                and expected_holder(entry.action) == "H"
            )
            == bundle.state.human_escalations_used
            and bundle.state.human_escalations_used
            <= RESOURCE_ACCOUNT.human_escalation_quota
        )


class InformationVerifier:
    def verify(
        self,
        bundle: VerificationBundle,
        observed_information_hash: str,
    ) -> bool:
        if len(bundle.inspection_records) != 1:
            return False
        record = bundle.inspection_records[0]
        if (
            record.public_trial_id != bundle.public_trial_id
            or record.task_fingerprint != fingerprint(OLD_TASK)
            or record.facts_hash != fingerprint(record.facts)
            or record.facts_hash != observed_information_hash
            or record.obligations
            != (
                "task-bound use only",
                "no authority inferred from disclosure",
            )
            or not bundle.state.inspected
            or not bundle.state.inspection_provenance_bound
            or not bundle.state.inspection_obligation_bound
        ):
            return False
        if not 0 <= record.ledger_index < len(bundle.ledger_entries):
            return False
        entry = bundle.ledger_entries[record.ledger_index]
        event = bundle.trace[record.ledger_index]
        return (
            entry.action == "INSPECT"
            and event.action == "INSPECT"
            and entry.success
            and event.success
            and entry.actor == "C"
            and event.actor == "C"
            and entry.response_hash == record.facts_hash
            and event.response_hash == record.facts_hash
            and entry.privacy_cost > 0
        )


class TaskEvaluator:
    """Immutable old-Q evaluator; candidate labels and claims are not inputs."""

    def __init__(
        self,
        expected_package_fingerprint: str,
        trusted_registry: HolderRegistry,
        trusted_anchor: TrustedEvidenceAnchor,
    ):
        self.expected_package_fingerprint = expected_package_fingerprint
        self.trusted_registry = trusted_registry
        self.trusted_anchor = trusted_anchor

    def evaluate(
        self,
        bundle: VerificationBundle,
        observed_information_hash: str,
    ) -> Evaluation:
        authority_valid = AuthorityVerifier(
            self.trusted_registry,
            self.trusted_anchor.effect_records,
        ).verify(bundle)
        target_valid = TargetVerifier().verify(bundle)
        acceptance_valid = AcceptanceVerifier(
            self.trusted_registry
        ).verify(bundle)
        cost_valid = CostVerifier().verify(bundle)
        information_valid = InformationVerifier().verify(
            bundle,
            observed_information_hash,
        ) and bundle.inspection_records == (
            self.trusted_anchor.inspection_records
        )
        evidence_seal_valid = (
            fingerprint(bundle)
            == self.trusted_anchor.bundle_fingerprint
        )
        task_invariant = (
            bundle.task_version == OLD_TASK.task_version
            and bundle.state.task_version == OLD_TASK.task_version
            and bundle.state.value_floor_ok
            and bundle.state.transfer_count == 1
            and bundle.package_fingerprint
            == self.expected_package_fingerprint
        )
        checks = {
            "AUTHORITY_INVALID": authority_valid,
            "TARGET_INVALID": target_valid,
            "ACCEPTANCE_INVALID": acceptance_valid,
            "COST_OR_HORIZON_INVALID": cost_valid,
            "INFORMATION_PROVENANCE_OR_OBLIGATION_INVALID":
                information_valid,
            "PARENT_EVIDENCE_SEAL_INVALID": evidence_seal_valid,
            "OLD_TASK_INVARIANT_FAILED": task_invariant,
        }
        reasons = tuple(reason for reason, passed in checks.items() if not passed)
        return Evaluation(
            qualified=not reasons,
            reasons=reasons,
            authority_valid=authority_valid,
            target_valid=target_valid,
            acceptance_valid=acceptance_valid,
            cost_valid=cost_valid,
            information_valid=information_valid,
            evidence_seal_valid=evidence_seal_valid,
            task_invariant=task_invariant,
        )
