"""Five isolated synthetic truth-owner process implementations.

Each worker receives exactly one owner state shard.  The public RPC connection
cannot request snapshots; snapshots and shutdown use a separate admin pipe that
is never passed to ``OwnerClient`` or the G6 method.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from multiprocessing.connection import Connection, wait
from typing import Any

from model import (
    AcceptanceObservation,
    AdoptionObservation,
    AuthorityObservation,
    AuthorityStatus,
    Obligation,
    RawOccurrence,
    SchemePhase,
    TargetStateObservation,
    Truth,
    _jsonable,
    assess_settlement,
)
from wire import (
    GENESIS_HEAD,
    WireProtocolError,
    canonical_bytes,
    canonical_hash,
    decode_canonical,
    make_response,
    native_ledger_entry,
    read_request,
)


OWNER_IDS = ("O_S", "O_E", "O_Q", "O_V", "O_P")

OWNER_ENDPOINTS = {
    "O_S": {"authority"},
    "O_E": {
        "execute",
        "effects",
        "recover",
        "recovery_state",
        "target_state",
    },
    "O_Q": {"episode_status", "acceptance"},
    "O_V": {"adoption", "acceptance"},
    "O_P": {"open_settlement", "settlement_state"},
}


@dataclass
class AuthorityGrant:
    operation_id: str
    actor_id: str
    object_id: str
    q_version: str
    status: AuthorityStatus
    observed_at: int
    scope_ref: str


@dataclass
class SafetyOwnerState:
    grants: dict[str, AuthorityGrant]
    native_records: list[dict[str, Any]] = field(default_factory=list)
    fail_endpoints: set[str] = field(default_factory=set)
    response_overrides: dict[str, Any] = field(default_factory=dict)
    now: int = 100


@dataclass
class EffectOperation:
    operation_id: str
    attempted_at: int
    actual_target: str
    create_effect: bool
    ack_lost: bool = False
    damage: bool = False


@dataclass
class VersionedTarget:
    state: str = "UNPOWERED"
    version: int = 0
    observed_at: int = 0
    last_occurrence_id: str | None = None


@dataclass
class EffectOwnerState:
    case_id: str
    expected_target_id: str
    operations: dict[str, EffectOperation]
    occurrences: list[RawOccurrence] = field(default_factory=list)
    submissions: dict[str, str | None] = field(default_factory=dict)
    recoveries: list[RawOccurrence] = field(default_factory=list)
    targets: dict[str, VersionedTarget] = field(default_factory=dict)
    native_records: list[dict[str, Any]] = field(default_factory=list)
    fail_endpoints: set[str] = field(default_factory=set)
    response_overrides: dict[str, Any] = field(default_factory=dict)
    recovery_mode: str = "NORMAL"
    now: int = 100


@dataclass
class QueryOwnerState:
    episode_id: str
    q_version: str
    target_id: str
    acceptance_state: Truth = Truth.TRUE
    acts: dict[str, AcceptanceObservation] = field(default_factory=dict)
    native_records: list[dict[str, Any]] = field(default_factory=list)
    fail_endpoints: set[str] = field(default_factory=set)
    response_overrides: dict[str, Any] = field(default_factory=dict)
    now: int = 100


@dataclass
class VenueOwnerState:
    episode_id: str
    q_version: str
    target_id: str
    adoption_state: Truth = Truth.TRUE
    acceptance_state: Truth = Truth.TRUE
    acts: dict[str, AcceptanceObservation] = field(default_factory=dict)
    native_records: list[dict[str, Any]] = field(default_factory=list)
    fail_endpoints: set[str] = field(default_factory=set)
    response_overrides: dict[str, Any] = field(default_factory=dict)
    now: int = 100


@dataclass
class PaymentOwnerState:
    case_id: str
    episode_id: str
    q_version: str
    obligations: dict[str, Obligation] = field(default_factory=dict)
    phases: dict[str, list[SchemePhase]] = field(default_factory=dict)
    native_records: list[dict[str, Any]] = field(default_factory=list)
    reversal: bool = False
    force_obligation_effect_id: str | None = None
    force_finality: str | None = None
    fail_endpoints: set[str] = field(default_factory=set)
    response_overrides: dict[str, Any] = field(default_factory=dict)
    now: int = 100


def _effect_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    effect = payload.get("effect")
    if not isinstance(effect, dict):
        raise WireProtocolError("EFFECT_NOT_OBJECT")
    required = {
        "occurrence_id",
        "owner_id",
        "domain",
        "object_id",
        "occurred_at",
    }
    if not required.issubset(effect):
        raise WireProtocolError("EFFECT_FIELDS_MISSING")
    return effect


def _acceptance_act(
    *,
    owner_id: str,
    state: QueryOwnerState | VenueOwnerState,
    payload: dict[str, Any],
    process_id: int,
) -> AcceptanceObservation:
    effect = _effect_from_payload(payload)
    effect_id = str(effect["occurrence_id"])
    requested_episode = str(payload.get("episode_id", ""))
    requested_q = str(payload.get("q_version", ""))
    exact = all((
        effect.get("owner_id") == "O_E",
        effect.get("domain") == "TARGET_NATIVE",
        effect.get("object_id") == state.target_id,
        requested_episode == state.episode_id,
        requested_q == state.q_version,
    ))
    accepted = state.acceptance_state if exact else Truth.FALSE
    if effect_id not in state.acts:
        state.acts[effect_id] = AcceptanceObservation(
            owner_id=owner_id,
            effect_id=effect_id,
            episode_id=requested_episode,
            q_version=requested_q,
            accepted=accepted,
            observed_at=state.now + 4,
            act_id=f"act:{owner_id}:{process_id}:{effect_id}",
            process_id=process_id,
        )
    return state.acts[effect_id]


def _dispatch_safety(
    state: SafetyOwnerState,
    endpoint: str,
    payload: dict[str, Any],
    _process_id: int,
) -> Any:
    if endpoint == "authority":
        grant = state.grants[payload["operation_id"]]
        return AuthorityObservation(
            owner_id="O_S",
            operation_id=grant.operation_id,
            actor_id=grant.actor_id,
            object_id=grant.object_id,
            q_version=grant.q_version,
            status=grant.status,
            observed_at=grant.observed_at,
            scope_ref=grant.scope_ref,
        )
    raise KeyError(endpoint)


def _ensure_target(state: EffectOwnerState, object_id: str) -> VersionedTarget:
    if object_id not in state.targets:
        state.targets[object_id] = VersionedTarget()
    return state.targets[object_id]


def _dispatch_effect(
    state: EffectOwnerState,
    endpoint: str,
    payload: dict[str, Any],
    _process_id: int,
) -> Any:
    if endpoint == "execute":
        operation_id = payload["operation_id"]
        if operation_id in state.submissions:
            return {
                "ack": state.submissions[operation_id],
                "idempotency": "REPLAY_NO_NEW_EFFECT",
            }
        operation = state.operations[operation_id]
        occurrence_id: str | None = None
        if operation.create_effect:
            occurrence_id = f"occ:{state.case_id}:{operation_id}"
            target = _ensure_target(state, operation.actual_target)
            target.version += 1
            occurrence = RawOccurrence(
                occurrence_id=occurrence_id,
                owner_id="O_E",
                domain="TARGET_NATIVE",
                native_kind="POWER_STATE_TRANSITION",
                object_id=operation.actual_target,
                occurred_at=operation.attempted_at + 1,
                operation_id=operation_id,
                from_state=target.state,
                to_state="POWERED",
                power_kw=3.0,
                damage=operation.damage,
                state_version=target.version,
            )
            state.occurrences.append(occurrence)
            target.state = "POWERED"
            target.observed_at = occurrence.occurred_at
            target.last_occurrence_id = occurrence.occurrence_id
        ack = None if operation.ack_lost else occurrence_id or "NO_EFFECT"
        state.submissions[operation_id] = ack
        return {"ack": ack, "idempotency": "FIRST"}
    if endpoint == "effects":
        operation_id = payload["operation_id"]
        return [
            occurrence for occurrence in state.occurrences
            if occurrence.operation_id == operation_id
            or (
                occurrence.operation_id is None
                and occurrence.object_id == state.expected_target_id
            )
        ]
    if endpoint == "recover":
        occurrence_id = payload["occurrence_id"]
        original = next(
            item for item in state.occurrences
            if item.occurrence_id == occurrence_id
        )
        if not original.damage:
            return {"status": "DENIED_NOT_DAMAGED", "occurrence_id": occurrence_id}
        if state.recovery_mode == "BOGUS_TRANSPLANT":
            return RawOccurrence(
                "bogus-recovery",
                "O_R",
                "RESOURCE_ACCOUNTING",
                "POWER_STATE_RECOVERY",
                "Circuit-C99",
                state.now + 2,
                "unrelated-operation",
                "UNKNOWN",
                "POWERED",
                3.0,
            )
        target = _ensure_target(state, original.object_id)
        next_version = target.version + 1
        recovery = RawOccurrence(
            occurrence_id=f"recovery:{occurrence_id}",
            owner_id="O_E",
            domain="TARGET_NATIVE",
            native_kind="POWER_STATE_RECOVERY",
            object_id=original.object_id,
            occurred_at=max(state.now + 2, original.occurred_at + 1),
            operation_id=f"recover:{occurrence_id}",
            from_state=original.to_state,
            to_state=original.from_state,
            power_kw=0.0,
            damage=False,
            reverses_occurrence_id=occurrence_id,
            state_version=next_version,
        )
        state.recoveries.append(recovery)
        if state.recovery_mode != "FORGED_NO_MUTATION":
            target.state = original.from_state or "UNKNOWN"
            target.version = next_version
            target.observed_at = recovery.occurred_at
            target.last_occurrence_id = recovery.occurrence_id
        return recovery
    if endpoint == "recovery_state":
        return [
            recovery for recovery in state.recoveries
            if recovery.reverses_occurrence_id == payload["occurrence_id"]
        ]
    if endpoint == "target_state":
        object_id = payload["object_id"]
        target = _ensure_target(state, object_id)
        return TargetStateObservation(
            owner_id="O_E",
            domain="TARGET_NATIVE",
            object_id=object_id,
            state=target.state,
            observed_at=max(state.now + 3, target.observed_at),
            state_version=target.version,
            last_occurrence_id=target.last_occurrence_id,
        )
    raise KeyError(endpoint)


def _dispatch_query(
    state: QueryOwnerState,
    endpoint: str,
    payload: dict[str, Any],
    process_id: int,
) -> Any:
    if endpoint == "episode_status":
        return {
            "owner_id": "O_Q",
            "episode_id": payload["episode_id"],
            "q_version": payload["q_version"],
            "current": (
                payload["episode_id"] == state.episode_id
                and payload["q_version"] == state.q_version
            ),
        }
    if endpoint == "acceptance":
        return _acceptance_act(
            owner_id="O_Q",
            state=state,
            payload=payload,
            process_id=process_id,
        )
    raise KeyError(endpoint)


def _dispatch_venue(
    state: VenueOwnerState,
    endpoint: str,
    payload: dict[str, Any],
    process_id: int,
) -> Any:
    effect = _effect_from_payload(payload)
    if endpoint == "adoption":
        exact = all((
            effect.get("owner_id") == "O_E",
            effect.get("domain") == "TARGET_NATIVE",
            effect.get("object_id") == state.target_id,
            payload.get("episode_id") == state.episode_id,
        ))
        return AdoptionObservation(
            owner_id="O_V",
            effect_id=str(effect["occurrence_id"]),
            episode_id=str(payload.get("episode_id", "")),
            adopted=state.adoption_state if exact else Truth.FALSE,
            observed_at=state.now + 3,
        )
    if endpoint == "acceptance":
        return _acceptance_act(
            owner_id="O_V",
            state=state,
            payload=payload,
            process_id=process_id,
        )
    raise KeyError(endpoint)


def _valid_acceptances(
    acceptances: Any,
    *,
    effect_id: str,
    episode_id: str,
    q_version: str,
) -> bool:
    if not isinstance(acceptances, list) or len(acceptances) != 2:
        return False
    owners = {item.get("owner_id") for item in acceptances if isinstance(item, dict)}
    act_ids = {item.get("act_id") for item in acceptances if isinstance(item, dict)}
    process_ids = {
        item.get("process_id") for item in acceptances if isinstance(item, dict)
    }
    return (
        owners == {"O_Q", "O_V"}
        and len(act_ids) == 2
        and None not in act_ids
        and len(process_ids) == 2
        and all(isinstance(value, int) and value > 0 for value in process_ids)
        and all(
            isinstance(item, dict)
            and item.get("effect_id") == effect_id
            and item.get("episode_id") == episode_id
            and item.get("q_version") == q_version
            and item.get("accepted") == Truth.TRUE.value
            and bool(item.get("response_hash"))
            for item in acceptances
        )
    )


def _dispatch_payment(
    state: PaymentOwnerState,
    endpoint: str,
    payload: dict[str, Any],
    _process_id: int,
) -> Any:
    if endpoint == "open_settlement":
        effect = _effect_from_payload(payload)
        effect_id = str(effect["occurrence_id"])
        if not _valid_acceptances(
            payload.get("acceptances"),
            effect_id=effect_id,
            episode_id=state.episode_id,
            q_version=state.q_version,
        ):
            return {"status": "REJECTED_ACCEPTANCE_CLOSURE"}
        obligation_id = f"obl:{state.case_id}:{effect_id}"
        if obligation_id not in state.obligations:
            obligation = Obligation(
                obligation_id=obligation_id,
                owner_id="O_P",
                effect_id=state.force_obligation_effect_id or effect_id,
                scheme="CE_PAY_V1",
                debtor="requester",
                beneficiary="resource-provider",
                required_phases=(
                    "AUTHORIZATION",
                    "CAPTURE",
                    "PAYOUT",
                    "BENEFICIARY_RECEIPT",
                    "CONTRACTUAL_DISCHARGE",
                ),
                reversal_phases=("DISPUTE", "CHARGEBACK", "REVERSAL"),
                finality_horizon=state.now + 5,
            )
            state.obligations[obligation_id] = obligation
            records = [
                SchemePhase(
                    obligation_id=obligation_id,
                    scheme=obligation.scheme,
                    phase=phase,
                    state=Truth.TRUE,
                    observed_at=state.now + 5,
                    occurrence_id=f"phase:{obligation_id}:{phase}",
                )
                for phase in obligation.required_phases
            ]
            for phase in obligation.reversal_phases:
                phase_state = (
                    Truth.TRUE
                    if state.reversal and phase == "REVERSAL"
                    else Truth.FALSE
                )
                records.append(SchemePhase(
                    obligation_id=obligation_id,
                    scheme=obligation.scheme,
                    phase=phase,
                    state=phase_state,
                    observed_at=state.now + 5,
                    occurrence_id=f"phase:{obligation_id}:{phase}",
                    reverses_occurrence_id=(
                        f"phase:{obligation_id}:PAYOUT"
                        if phase_state == Truth.TRUE else None
                    ),
                ))
            state.phases[obligation_id] = records
        return state.obligations[obligation_id]
    if endpoint == "settlement_state":
        obligation_id = payload["obligation_id"]
        obligation = state.obligations[obligation_id]
        phases = state.phases[obligation_id]
        observed_at = state.now + 6
        assessment = assess_settlement(
            obligation,
            phases,
            observed_at,
            expected_effect_id=payload["effect_id"],
        )
        finality = state.force_finality or assessment.finality.value
        return {
            "obligation": obligation,
            "phases": phases,
            "observed_at": observed_at,
            "finality": finality,
        }
    raise KeyError(endpoint)


DISPATCHERS = {
    "O_S": _dispatch_safety,
    "O_E": _dispatch_effect,
    "O_Q": _dispatch_query,
    "O_V": _dispatch_venue,
    "O_P": _dispatch_payment,
}


def _native_state_head(state: Any) -> str:
    """Hash the actual owner shard after dispatch, never a response override."""
    projection = _jsonable(state)
    for control_key in (
        "fail_endpoints",
        "response_overrides",
        "recovery_mode",
        "force_obligation_effect_id",
        "force_finality",
    ):
        projection.pop(control_key, None)
    return canonical_hash(canonical_bytes(projection))


def _snapshot(
    owner_id: str,
    state: Any,
    native_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "owner_id": owner_id,
        "process_id": os.getpid(),
        "state": _jsonable(state),
        "native_ledger": native_ledger,
        "native_ledger_head": (
            native_ledger[-1]["ledger_head"]
            if native_ledger else GENESIS_HEAD
        ),
    }


def _append_native_record(
    *,
    owner_id: str,
    state: Any,
    endpoint: str,
    request: dict[str, Any],
    request_bytes: bytes,
    native_payload: Any,
    process_id: int,
    session_id: str,
) -> list[dict[str, Any]]:
    """Persist an endpoint-specific record in the actual owner shard."""
    payload = request["payload"]
    native_value = _jsonable(native_payload)
    bindings: dict[str, Any] = {}
    effect = payload.get("effect")
    if isinstance(effect, dict):
        bindings.update({
            "effect_id": effect.get("occurrence_id"),
            "effect_sha256": canonical_hash(canonical_bytes(effect)),
            "episode_id": payload.get("episode_id"),
            "q_version": payload.get("q_version"),
        })
    if owner_id == "O_E":
        bindings.update({
            "operation_id": payload.get("operation_id"),
            "occurrence_id": payload.get("occurrence_id"),
            "object_id": payload.get("object_id"),
        })
        if endpoint in {"effects", "recovery_state"} and isinstance(
            native_value, list
        ):
            bindings["native_occurrence_ids"] = [
                item.get("occurrence_id")
                for item in native_value if isinstance(item, dict)
            ]
        if endpoint == "target_state" and isinstance(native_value, dict):
            bindings["native_target_head"] = {
                key: native_value.get(key)
                for key in (
                    "object_id",
                    "state",
                    "state_version",
                    "last_occurrence_id",
                )
            }
    if endpoint == "acceptance" and isinstance(native_value, dict):
        bindings.update({
            "act_id": native_value.get("act_id"),
            "accepted": native_value.get("accepted"),
            "native_act_effect_id": native_value.get("effect_id"),
            "native_act_episode_id": native_value.get("episode_id"),
            "native_act_q_version": native_value.get("q_version"),
        })
    if owner_id == "O_P":
        acceptances = payload.get("acceptances")
        if isinstance(acceptances, list):
            exact_set = sorted(
                acceptances,
                key=lambda item: (
                    str(item.get("owner_id")),
                    str(item.get("act_id")),
                ),
            )
            bindings["exact_acceptance_set_sha256"] = canonical_hash(
                canonical_bytes(exact_set)
            )
            bindings["exact_acceptance_owners"] = [
                item.get("owner_id") for item in exact_set
            ]
        bindings["requested_effect_id"] = (
            effect.get("occurrence_id")
            if isinstance(effect, dict)
            else payload.get("effect_id")
        )
        bindings["requested_obligation_id"] = payload.get("obligation_id")
        if isinstance(native_value, dict):
            obligation = native_value.get("obligation", native_value)
            phases = native_value.get("phases", [])
            if isinstance(obligation, dict):
                bindings.update({
                    "native_obligation_id": obligation.get("obligation_id"),
                    "native_effect_id": obligation.get("effect_id"),
                    "native_scheme": obligation.get("scheme"),
                    "required_phases": obligation.get("required_phases"),
                    "reversal_phases": obligation.get("reversal_phases"),
                })
            bindings["native_phase_set_sha256"] = canonical_hash(
                canonical_bytes(phases)
            )
    record = {
        "kind": "OWNER_NATIVE_RECORD_V2",
        "owner_id": owner_id,
        "endpoint": endpoint,
        "owner_process_id": process_id,
        "session_id": session_id,
        "request_id": request["request_id"],
        "request_sha256": canonical_hash(request_bytes),
        "nonce": request["nonce"],
        "ordinal": request["ordinal"],
        "request_payload_sha256": canonical_hash(canonical_bytes(payload)),
        "native_payload_sha256": canonical_hash(canonical_bytes(native_value)),
        "bindings": bindings,
    }
    record_id = canonical_hash(canonical_bytes(record))
    stored = {"record_id": record_id, **record}
    state.native_records.append(stored)
    return [{
        "kind": stored["kind"],
        "record_id": record_id,
        "owner_id": owner_id,
        "endpoint": endpoint,
    }]


def owner_worker(
    owner_id: str,
    state: Any,
    rpc: Connection,
    admin: Connection,
    session_id: str,
) -> None:
    process_id = os.getpid()
    owner_instance_id = canonical_hash(canonical_bytes({
        "owner_id": owner_id,
        "session_id": session_id,
        "process_id": process_id,
    }))
    allowed = OWNER_ENDPOINTS[owner_id]
    dispatcher = DISPATCHERS[owner_id]
    native_ledger: list[dict[str, Any]] = []
    ledger_head = GENESIS_HEAD
    admin.send_bytes(canonical_bytes({
        "kind": "OWNER_READY_V2",
        "owner_id": owner_id,
        "process_id": process_id,
        "session_id": session_id,
    }))
    while True:
        ready = wait((rpc, admin))
        if admin in ready:
            command = decode_canonical(admin.recv_bytes())
            if command.get("command") == "SNAPSHOT":
                admin.send_bytes(canonical_bytes(
                    _snapshot(owner_id, state, native_ledger)
                ))
            elif command.get("command") == "SHUTDOWN":
                admin.send_bytes(canonical_bytes({
                    "kind": "OWNER_STOPPED_V2",
                    "owner_id": owner_id,
                    "process_id": process_id,
                    "session_id": session_id,
                }))
                return
            else:
                admin.send_bytes(canonical_bytes({"error": "UNKNOWN_ADMIN_COMMAND"}))
        if rpc in ready:
            request_bytes = rpc.recv_bytes()
            try:
                request = read_request(
                    request_bytes,
                    expected_owner=owner_id,
                    allowed_endpoints=allowed,
                    expected_session_id=session_id,
                )
                endpoint = request["endpoint"]
                state_head_before = _native_state_head(state)
                try:
                    if endpoint in state.fail_endpoints:
                        raise RuntimeError(
                            f"INJECTED_FAILURE:{owner_id}.{endpoint}"
                        )
                    native_payload = dispatcher(
                        state, endpoint, request["payload"], process_id
                    )
                except Exception as dispatch_exc:
                    native_payload = {
                        "error": type(dispatch_exc).__name__,
                        "detail": str(dispatch_exc),
                    }
                native_payload_sha256 = canonical_hash(
                    canonical_bytes(native_payload)
                )
                native_record_refs = _append_native_record(
                    owner_id=owner_id,
                    state=state,
                    endpoint=endpoint,
                    request=request,
                    request_bytes=request_bytes,
                    native_payload=native_payload,
                    process_id=process_id,
                    session_id=session_id,
                )
                state_head = _native_state_head(state)
                previous_ledger_head = ledger_head
                ledger_length = len(native_ledger) + 1
                entry = native_ledger_entry(
                    owner_id=owner_id,
                    endpoint=endpoint,
                    session_id=session_id,
                    process_id=process_id,
                    owner_instance_id=owner_instance_id,
                    client_pid=request["client_pid"],
                    request_id=request["request_id"],
                    request_sha256=canonical_hash(request_bytes),
                    request_nonce=request["nonce"],
                    request_ordinal=request["ordinal"],
                    previous_ledger_head=previous_ledger_head,
                    ledger_length=ledger_length,
                    state_head_before=state_head_before,
                    state_head=state_head,
                    native_payload_sha256=native_payload_sha256,
                    native_record_refs=native_record_refs,
                )
                ledger_head = canonical_hash(canonical_bytes(entry))
                native_record = {
                    **entry,
                    "ledger_head": ledger_head,
                }
                native_ledger.append(native_record)
                native_attestation = dict(native_record)

                # Failure injection may replace only the transmitted payload.
                # The independent native attestation always commits the actual
                # dispatcher output and post-dispatch owner shard.
                payload = state.response_overrides.get(
                    endpoint, native_payload
                )
                response = make_response(
                    owner_id=owner_id,
                    endpoint=endpoint,
                    request_bytes=request_bytes,
                    payload=payload,
                    observed_at=state.now,
                    process_id=process_id,
                    session_id=session_id,
                    request_id=request["request_id"],
                    request_nonce=request["nonce"],
                    request_ordinal=request["ordinal"],
                    native_attestation=native_attestation,
                    owner_instance_id=owner_instance_id,
                    client_pid=request["client_pid"],
                )
            except Exception as exc:
                decoded = (
                    decode_canonical(request_bytes)
                    if request_bytes else {}
                )
                endpoint = decoded.get("endpoint", "UNKNOWN")
                fallback_native = {
                    "owner_id": owner_id,
                    "endpoint": endpoint,
                    "session_id": session_id,
                    "process_id": process_id,
                    "owner_instance_id": owner_instance_id,
                    "client_pid": decoded.get("client_pid", -1),
                    "request_id": decoded.get("request_id", "INVALID"),
                    "request_sha256": canonical_hash(request_bytes),
                    "request_nonce": decoded.get("nonce", "INVALID"),
                    "request_ordinal": decoded.get("ordinal", -1),
                    "previous_ledger_head": ledger_head,
                    "ledger_length": len(native_ledger),
                    "state_head_before": _native_state_head(state),
                    "state_head": _native_state_head(state),
                    "native_payload_sha256": canonical_hash(canonical_bytes({
                        "error": type(exc).__name__,
                        "detail": str(exc),
                    })),
                    "native_record_refs": [],
                    "ledger_head": ledger_head,
                }
                response = make_response(
                    owner_id=owner_id,
                    endpoint=endpoint,
                    request_bytes=request_bytes,
                    payload={
                        "error": type(exc).__name__,
                        "detail": str(exc),
                    },
                    observed_at=-1,
                    process_id=process_id,
                    session_id=session_id,
                    request_id=decoded.get("request_id", "INVALID"),
                    request_nonce=decoded.get("nonce", "INVALID"),
                    request_ordinal=decoded.get("ordinal", -1),
                    native_attestation=fallback_native,
                    owner_instance_id=owner_instance_id,
                    client_pid=decoded.get("client_pid", -1),
                )
            rpc.send_bytes(response)
