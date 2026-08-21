"""G6 method consuming only canonical owner-response bytes and a public plan."""

from __future__ import annotations

from dataclasses import asdict

from model import (
    AcceptanceObservation,
    AdoptionObservation,
    Attempt,
    AuthorityObservation,
    AuthorityStatus,
    Finality,
    MethodResult,
    Obligation,
    RawOccurrence,
    Recovery,
    SchemePhase,
    TargetStateObservation,
    Truth,
    _jsonable,
    assess_effect,
    assess_settlement,
)
from owner_api import (
    OwnerClient,
    OwnerUnavailable,
)
from wire import WireProtocolError, canonical_bytes, canonical_hash


def _current_owner_client(client) -> OwnerClient:
    if isinstance(client, OwnerClient):
        return client
    inner = getattr(client, "inner", None)
    if isinstance(inner, OwnerClient):
        return inner
    raise WireProtocolError("CURRENT_OWNER_CLIENT_REQUIRED")


def _consume(
    result: MethodResult,
    client: OwnerClient,
    value: bytes,
    *,
    owner_id: str,
    endpoint: str,
    role: str,
    subject_id: str,
):
    """Consume only bytes registered by the exact current OwnerClient."""
    current_client = _current_owner_client(client)
    verified = OwnerClient.consume_response(
        current_client,
        value,
        owner_id=owner_id,
        endpoint=endpoint,
        min_sequence=result.evidence_start_sequence,
    )
    receipt = verified.receipt
    result.evidence_refs.append({
        "role": role,
        "subject_id": subject_id,
        "owner_id": owner_id,
        "endpoint": endpoint,
        "response_hash": receipt.response_hash,
        "request_hash": receipt.request_hash,
        "native_payload_hash": receipt.native_payload_hash,
    })
    return verified


def _finish(result: MethodResult, client) -> MethodResult:
    result.owner_query_count = len(getattr(client, "trace", ()))
    try:
        current_client = _current_owner_client(client)
    except WireProtocolError:
        result.evidence_closure = {}
        return result
    closure = current_client.freeze_closure()
    closure["result_sha256"] = canonical_hash(canonical_bytes(
        result.evidence_payload()
    ))
    result.evidence_closure = closure
    return result


def _authority(value: dict) -> AuthorityObservation:
    return AuthorityObservation(
        owner_id=value["owner_id"],
        operation_id=value["operation_id"],
        actor_id=value["actor_id"],
        object_id=value["object_id"],
        q_version=value["q_version"],
        status=AuthorityStatus(value["status"]),
        observed_at=value["observed_at"],
        scope_ref=value["scope_ref"],
    )


def _occurrence(value: dict) -> RawOccurrence:
    return RawOccurrence(
        occurrence_id=value["occurrence_id"],
        owner_id=value["owner_id"],
        domain=value["domain"],
        native_kind=value["native_kind"],
        object_id=value["object_id"],
        occurred_at=value["occurred_at"],
        operation_id=value.get("operation_id"),
        from_state=value.get("from_state"),
        to_state=value.get("to_state"),
        power_kw=value.get("power_kw"),
        damage=value.get("damage", False),
        reverses_occurrence_id=value.get("reverses_occurrence_id"),
        state_version=value.get("state_version"),
    )


def _adoption(value: dict) -> AdoptionObservation:
    return AdoptionObservation(
        owner_id=value["owner_id"],
        effect_id=value["effect_id"],
        episode_id=value["episode_id"],
        adopted=Truth(value["adopted"]),
        observed_at=value["observed_at"],
    )


def _acceptance(
    value: dict,
    response_bytes: bytes,
    transport_process_id: int,
) -> AcceptanceObservation:
    if value.get("process_id") != transport_process_id:
        raise WireProtocolError("ACCEPTANCE_PROCESS_PROVENANCE_MISMATCH")
    return AcceptanceObservation(
        owner_id=value["owner_id"],
        effect_id=value["effect_id"],
        episode_id=value["episode_id"],
        q_version=value["q_version"],
        accepted=Truth(value["accepted"]),
        observed_at=value["observed_at"],
        act_id=value.get("act_id", ""),
        process_id=transport_process_id,
        response_hash=canonical_hash(response_bytes),
    )


def _obligation(value: dict) -> Obligation:
    return Obligation(
        obligation_id=value["obligation_id"],
        owner_id=value["owner_id"],
        effect_id=value["effect_id"],
        scheme=value["scheme"],
        debtor=value["debtor"],
        beneficiary=value["beneficiary"],
        required_phases=tuple(value["required_phases"]),
        reversal_phases=tuple(value["reversal_phases"]),
        finality_horizon=value["finality_horizon"],
    )


def _phase(value: dict) -> SchemePhase:
    return SchemePhase(
        obligation_id=value["obligation_id"],
        scheme=value["scheme"],
        phase=value["phase"],
        state=Truth(value["state"]),
        observed_at=value["observed_at"],
        occurrence_id=value["occurrence_id"],
        reverses_occurrence_id=value.get("reverses_occurrence_id"),
    )


def _target_state(value: dict) -> TargetStateObservation:
    return TargetStateObservation(
        owner_id=value["owner_id"],
        domain=value["domain"],
        object_id=value["object_id"],
        state=value["state"],
        observed_at=value["observed_at"],
        state_version=value.get("state_version", 0),
        last_occurrence_id=value.get("last_occurrence_id"),
    )


class G6Method:
    def run(self, plan, client: OwnerClient) -> MethodResult:
        result = MethodResult(
            case_id=plan.case_id,
            resolution="BOUNDED_UNKNOWN",
            plan_sha256=canonical_hash(canonical_bytes(plan)),
        )
        try:
            result.evidence_start_sequence = _current_owner_client(
                client
            ).sequence
        except WireProtocolError:
            return _finish(result, client)
        ordered = list(plan.attempts)
        if not ordered:
            try:
                status_bytes = client.episode_status(
                    plan.episode.episode_id, plan.episode.q_version
                )
                _consume(
                    result,
                    client,
                    status_bytes,
                    owner_id="O_Q",
                    endpoint="episode_status",
                    role="episode_currentness",
                    subject_id=plan.episode.episode_id,
                )
            except (OwnerUnavailable, WireProtocolError):
                pass
            return _finish(result, client)

        explicit_denial_seen = False
        unknown_authority_seen = False
        recovered_wrong_target = False
        for item in ordered:
            attempt = Attempt(
                attempt_id=item.attempt_id,
                operation_id=item.operation_id,
                actor_id=item.actor_id,
                target_id=item.target_id,
                episode_id=plan.episode.episode_id,
                q_version=plan.episode.q_version,
                attempted_at=item.attempted_at,
            )
            observation_stage = "authority"
            try:
                authority_bytes = client.authority(item.operation_id)
                authority_verified = _consume(
                    result,
                    client,
                    authority_bytes,
                    owner_id="O_S",
                    endpoint="authority",
                    role="authority",
                    subject_id=item.operation_id,
                )
                authority = _authority(authority_verified.payload)
                authority_identity_exact = (
                    authority.owner_id == "O_S"
                    and authority.operation_id == item.operation_id
                    and authority.actor_id == item.actor_id
                    and authority.object_id == item.target_id
                    and authority.q_version == plan.episode.q_version
                    and authority.observed_at <= item.attempted_at
                )
                if not authority_identity_exact:
                    unknown_authority_seen = True
                    continue
                if authority.status != AuthorityStatus.AUTHORIZED:
                    if authority.status in {
                        AuthorityStatus.UNAUTHORIZED,
                        AuthorityStatus.REVOKED,
                        AuthorityStatus.EXPIRED,
                    }:
                        explicit_denial_seen = True
                    else:
                        unknown_authority_seen = True
                    continue
                if plan.resume_operation_id != item.operation_id:
                    observation_stage = "execute"
                    execute_bytes = client.execute(item.operation_id)
                    _consume(
                        result,
                        client,
                        execute_bytes,
                        owner_id="O_E",
                        endpoint="execute",
                        role="effect_execute",
                        subject_id=item.operation_id,
                    )
                observation_stage = "effects"
                occurrence_bytes = client.effects(item.operation_id)
                occurrence_verified = _consume(
                    result,
                    client,
                    occurrence_bytes,
                    owner_id="O_E",
                    endpoint="effects",
                    role="effect_readback",
                    subject_id=item.operation_id,
                )
                occurrence_payload = occurrence_verified.payload
                occurrences = [_occurrence(value) for value in occurrence_payload]
            except WireProtocolError:
                if observation_stage == "authority":
                    unknown_authority_seen = True
                    continue
                result.resolution = "BOUNDED_UNKNOWN_OWNER_UNAVAILABLE"
                break
            except (OwnerUnavailable, KeyError, TypeError, ValueError):
                result.resolution = "BOUNDED_UNKNOWN_OWNER_UNAVAILABLE"
                break

            exact_effect = None
            for occurrence in occurrences:
                assessment = assess_effect(
                    plan.episode, attempt, occurrence, authority
                )
                result.effects.append(assessment)
                if assessment.recovery == Recovery.REQUIRED:
                    try:
                        recover_bytes = client.recover(
                            occurrence.occurrence_id
                        )
                        _consume(
                            result,
                            client,
                            recover_bytes,
                            owner_id="O_E",
                            endpoint="recover",
                            role="recovery_command",
                            subject_id=occurrence.occurrence_id,
                        )
                        recovery_bytes = client.recovery_state(
                            occurrence.occurrence_id
                        )
                        target_bytes = client.target_state(
                            occurrence.object_id
                        )
                        recovery_verified = _consume(
                            result,
                            client,
                            recovery_bytes,
                            owner_id="O_E",
                            endpoint="recovery_state",
                            role="recovery_readback",
                            subject_id=occurrence.occurrence_id,
                        )
                        target_verified = _consume(
                            result,
                            client,
                            target_bytes,
                            owner_id="O_E",
                            endpoint="target_state",
                            role="target_state_readback",
                            subject_id=occurrence.object_id,
                        )
                        recovery_readback = [
                            _occurrence(value)
                            for value in recovery_verified.payload
                        ]
                        target_readback = _target_state(
                            target_verified.payload
                        )
                    except (
                        OwnerUnavailable,
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        result.resolution = "RECOVERY_UNKNOWN"
                        return _finish(result, client)
                    valid_recovery = [
                        recovery for recovery in recovery_readback
                        if occurrence.damage
                        and recovery.owner_id == "O_E"
                        and recovery.domain == "TARGET_NATIVE"
                        and recovery.native_kind == "POWER_STATE_RECOVERY"
                        and recovery.object_id == occurrence.object_id
                        and recovery.reverses_occurrence_id
                        == occurrence.occurrence_id
                        and recovery.from_state == occurrence.to_state
                        and recovery.to_state == occurrence.from_state
                        and occurrence.state_version is not None
                        and recovery.state_version is not None
                        and recovery.state_version > occurrence.state_version
                    ]
                    if not valid_recovery:
                        result.resolution = "RECOVERY_UNKNOWN"
                        return _finish(result, client)
                    latest_recovery = max(
                        valid_recovery,
                        key=lambda value: (
                            value.state_version or -1,
                            value.occurred_at,
                        ),
                    )
                    target_restored = (
                        target_readback.owner_id == "O_E"
                        and target_readback.domain == "TARGET_NATIVE"
                        and target_readback.object_id == occurrence.object_id
                        and target_readback.state == occurrence.from_state
                        and target_readback.state_version
                        == latest_recovery.state_version
                        and target_readback.last_occurrence_id
                        == latest_recovery.occurrence_id
                        and target_readback.observed_at
                        >= latest_recovery.occurred_at
                    )
                    if not target_restored:
                        result.resolution = "RECOVERY_UNKNOWN"
                        return _finish(result, client)
                    result.recovery_occurrences.extend(valid_recovery)
                    if not assessment.binding.exact_object:
                        recovered_wrong_target = True
                if assessment.counts_toward_q:
                    exact_effect = assessment

            counting_for_operation = [
                effect for effect in result.effects
                if effect.counts_toward_q
                and effect.occurrence.operation_id == item.operation_id
            ]
            if len(counting_for_operation) > 1:
                result.duplicate_effect = True
                result.resolution = "DUPLICATE_EFFECT"
                return _finish(result, client)

            if exact_effect is None:
                continue

            effect = _jsonable(asdict(exact_effect.occurrence))
            effect_id = exact_effect.occurrence.occurrence_id
            try:
                adoption_bytes = client.adoption(
                    effect, plan.episode.episode_id
                )
                adoption_verified = _consume(
                    result,
                    client,
                    adoption_bytes,
                    owner_id="O_V",
                    endpoint="adoption",
                    role="adoption",
                    subject_id=effect_id,
                )
                adoption = _adoption(adoption_verified.payload)
                requester_bytes = client.acceptance(
                    effect,
                    "O_Q",
                    plan.episode.episode_id,
                    plan.episode.q_version,
                )
                venue_bytes = client.acceptance(
                    effect,
                    "O_V",
                    plan.episode.episode_id,
                    plan.episode.q_version,
                )
                requester_verified = _consume(
                    result,
                    client,
                    requester_bytes,
                    owner_id="O_Q",
                    endpoint="acceptance",
                    role="requester_acceptance",
                    subject_id=effect_id,
                )
                venue_verified = _consume(
                    result,
                    client,
                    venue_bytes,
                    owner_id="O_V",
                    endpoint="acceptance",
                    role="venue_acceptance",
                    subject_id=effect_id,
                )
                requester_acceptance = _acceptance(
                    requester_verified.payload,
                    requester_bytes,
                    requester_verified.receipt.owner_process_id,
                )
                venue_acceptance = _acceptance(
                    venue_verified.payload,
                    venue_bytes,
                    venue_verified.receipt.owner_process_id,
                )
            except WireProtocolError:
                result.resolution = "EFFECT_WITHOUT_ACCEPTANCE"
                break
            except (
                OwnerUnavailable,
                KeyError,
                TypeError,
                ValueError,
            ):
                result.resolution = "BOUNDED_UNKNOWN_OWNER_UNAVAILABLE"
                break
            result.adoptions.append(adoption)
            result.acceptances.extend(
                [requester_acceptance, venue_acceptance]
            )
            acceptance_acts = (requester_acceptance, venue_acceptance)
            both_accepted = (
                {act.owner_id for act in acceptance_acts} == {"O_Q", "O_V"}
                and len({act.act_id for act in acceptance_acts}) == 2
                and all(act.act_id for act in acceptance_acts)
                and len({act.process_id for act in acceptance_acts}) == 2
                and all(
                    act.accepted == Truth.TRUE
                    and act.effect_id == effect_id
                    and act.episode_id == plan.episode.episode_id
                    and act.q_version == plan.episode.q_version
                    and act.observed_at >= exact_effect.occurrence.occurred_at
                    for act in acceptance_acts
                )
            )
            adoption_exact = (
                adoption.owner_id == "O_V"
                and adoption.effect_id == effect_id
                and adoption.episode_id == plan.episode.episode_id
                and adoption.adopted == Truth.TRUE
                and adoption.observed_at >= exact_effect.occurrence.occurred_at
            )
            if not adoption_exact:
                result.resolution = "EFFECT_WITHOUT_ADOPTION"
                break
            if not both_accepted:
                result.resolution = "EFFECT_WITHOUT_ACCEPTANCE"
                break

            acts_payload = [
                _jsonable(asdict(act)) for act in acceptance_acts
            ]
            try:
                obligation_bytes = client.open_settlement(
                    effect, acts_payload
                )
                obligation_verified = _consume(
                    result,
                    client,
                    obligation_bytes,
                    owner_id="O_P",
                    endpoint="open_settlement",
                    role="obligation_open",
                    subject_id=effect_id,
                )
                obligation = _obligation(obligation_verified.payload)
                state_bytes = client.settlement_state(
                    obligation.obligation_id,
                    effect_id,
                )
                state_verified = _consume(
                    result,
                    client,
                    state_bytes,
                    owner_id="O_P",
                    endpoint="settlement_state",
                    role="settlement_finality",
                    subject_id=obligation.obligation_id,
                )
                state_payload = state_verified.payload
                observed_obligation = _obligation(
                    state_payload["obligation"]
                )
                phases = [
                    _phase(value) for value in state_payload["phases"]
                ]
                settlement = assess_settlement(
                    observed_obligation,
                    phases,
                    observed_at=state_payload["observed_at"],
                    expected_effect_id=effect_id,
                )
                owner_finality_matches = (
                    state_payload["finality"] == settlement.finality.value
                    and observed_obligation == obligation
                )
            except (
                OwnerUnavailable,
                KeyError,
                TypeError,
                ValueError,
            ):
                result.resolution = "ACCEPTED_SETTLEMENT_UNKNOWN"
                break
            result.settlements.append(settlement)
            if not owner_finality_matches:
                result.resolution = "ACCEPTED_SETTLEMENT_UNKNOWN"
            elif settlement.discharged and recovered_wrong_target:
                result.resolution = (
                    "RECOVERED_WRONG_TARGET_THEN_EXACT_EFFECT_ACCEPTED_SETTLED"
                )
            elif settlement.discharged:
                result.resolution = "EXACT_EFFECT_ACCEPTED_SETTLED"
            else:
                result.resolution = "ACCEPTED_SETTLEMENT_OPEN"
            break

        if not result.effects and result.resolution == "BOUNDED_UNKNOWN":
            if explicit_denial_seen and not unknown_authority_seen:
                result.resolution = "BOUNDED_REFUSAL_NO_EFFECT"

        counting_effects = [
            assessment for assessment in result.effects
            if assessment.counts_toward_q
        ]
        effect_ids = [
            assessment.occurrence.occurrence_id
            for assessment in counting_effects
        ]
        operation_ids = [
            assessment.occurrence.operation_id
            for assessment in counting_effects
        ]
        result.duplicate_effect = (
            len(effect_ids) != len(set(effect_ids))
            or len(operation_ids) != len(set(operation_ids))
        )
        return _finish(result, client)
