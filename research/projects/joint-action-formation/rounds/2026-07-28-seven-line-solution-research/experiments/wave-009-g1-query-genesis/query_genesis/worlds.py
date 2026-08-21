"""Frozen parent-only semantic worlds.

The gateway consumes records and policies in these worlds.  It never consumes
the frozen L/D/H labels; those are checked by a separately implemented
evaluator.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from .authority_evidence import (
    SignedAuthorityEvidence,
    semantic_scope,
    sign_authority_evidence,
)

WORLD_MODEL_VERSION = "wave009-semantic-world-v3"


@dataclass(frozen=True)
class VagueValueSeedSpec:
    origin: str
    value: str
    version: int


@dataclass(frozen=True)
class PrincipalIntent:
    principal: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    query_head_version: int
    clarification_policy: str = "ALLOW"


@dataclass(frozen=True)
class SemanticResource:
    resource_id: str
    principal: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int = 1
    active: bool = True


@dataclass(frozen=True)
class IndexRecord:
    record_id: str
    principal: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int = 1
    current_head: int = 1
    status: str = "ACTIVE"
    qualification_revokes: bool = False


@dataclass(frozen=True)
class LocalAuthority:
    principal: str
    availability: str
    fact: Optional[SemanticResource] = None
    projection_allowed: bool = False
    timeout_evidence: Optional[SignedAuthorityEvidence] = None
    refusal: Optional[SignedAuthorityEvidence] = None
    completeness: Optional[SignedAuthorityEvidence] = None
    negative_attestation: Optional[SignedAuthorityEvidence] = None


@dataclass(frozen=True)
class PredicateRecord:
    predicate_id: str
    principal: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int = 1
    active: bool = True


@dataclass(frozen=True)
class ReciprocalResponse:
    kind: str
    principal: str
    evidence: SignedAuthorityEvidence
    version: int = 1


@dataclass(frozen=True)
class PlatformTask:
    task_id: str
    target_domain: str
    requested_effect: str
    mode: str
    version: int = 1


@dataclass(frozen=True)
class HiddenWorld:
    truth_id: str
    public_trial_id: str
    family: str
    public_value_seed: VagueValueSeedSpec
    principal_intent: PrincipalIntent
    public_initial_transcript: tuple[str, ...]
    latent_resources: tuple[SemanticResource, ...] = ()
    index_records: tuple[IndexRecord, ...] = ()
    local_authority: Optional[LocalAuthority] = None
    predicate_record: Optional[PredicateRecord] = None
    reciprocal_response: Optional[ReciprocalResponse] = None
    raw_fact: Optional[SemanticResource] = None
    raw_disclosure_allowed: bool = False
    local_oracle_allowed: bool = False
    platform_task: Optional[PlatformTask] = None
    goal_head_advances_after_qualification: bool = False
    latent_truth: bool = False
    d_actual_truth: bool = False
    handoff_truth: bool = False


def semantic_compatible(
    *,
    purpose: str,
    direction: str,
    constraints: tuple[str, ...],
    goal: PrincipalIntent,
) -> bool:
    return (
        purpose == goal.purpose
        and direction == goal.direction
        and set(goal.constraints).issubset(constraints)
    )


def _public_id(index: int, truth_id: str) -> str:
    digest = sha256(f"wave009-v2:{index}:{truth_id}".encode()).hexdigest()[:12]
    return f"trial-{index:02d}-{digest}"


PUBLIC_VALUE_SEED = VagueValueSeedSpec(
    origin="requester:A",
    value="timely confidential language help",
    version=1,
)
BASE_INTENT = PrincipalIntent(
    principal="principal:requester:A",
    purpose="discover_translation_partner",
    direction="provide_translation",
    constraints=("confidential", "within_24h"),
    query_head_version=1,
)
PUBLIC_TRANSCRIPT = (
    "requester:A expresses a vague value seed",
    "value: timely confidential language help",
)
QUERY_SCOPE = semantic_scope(
    BASE_INTENT.purpose,
    BASE_INTENT.direction,
    BASE_INTENT.constraints,
)


def _resource(name: str, *, direction: str = "provide_translation") -> SemanticResource:
    return SemanticResource(
        resource_id=f"hidden:{name}",
        principal=f"authority:{name}",
        purpose=BASE_INTENT.purpose,
        direction=direction,
        constraints=BASE_INTENT.constraints,
    )


def _record(
    name: str,
    *,
    direction: str = "provide_translation",
    status: str = "ACTIVE",
    qualification_revokes: bool = False,
) -> IndexRecord:
    return IndexRecord(
        record_id=f"index:{name}",
        principal=f"authority:{name}",
        purpose=BASE_INTENT.purpose,
        direction=direction,
        constraints=BASE_INTENT.constraints,
        status=status,
        qualification_revokes=qualification_revokes,
    )


def _local_online(name: str) -> LocalAuthority:
    return LocalAuthority(
        principal=f"authority:{name}",
        availability="ONLINE",
        fact=_resource(name),
        projection_allowed=True,
    )


def _world(
    index: int,
    truth_id: str,
    family: str,
    *,
    latent_resources: tuple[SemanticResource, ...] = (),
    index_records: tuple[IndexRecord, ...] = (),
    local_authority: Optional[LocalAuthority] = None,
    predicate_record: Optional[PredicateRecord] = None,
    reciprocal_response: Optional[ReciprocalResponse] = None,
    raw_fact: Optional[SemanticResource] = None,
    raw_disclosure_allowed: bool = False,
    local_oracle_allowed: bool = False,
    platform_task: Optional[PlatformTask] = None,
    clarification_policy: str = "ALLOW",
    goal_head_advances_after_qualification: bool = False,
    latent: bool,
    discoverable: bool,
) -> HiddenWorld:
    return HiddenWorld(
        truth_id=truth_id,
        public_trial_id=_public_id(index, truth_id),
        family=family,
        public_value_seed=PUBLIC_VALUE_SEED,
        principal_intent=PrincipalIntent(
            principal=BASE_INTENT.principal,
            purpose=BASE_INTENT.purpose,
            direction=BASE_INTENT.direction,
            constraints=BASE_INTENT.constraints,
            query_head_version=BASE_INTENT.query_head_version,
            clarification_policy=clarification_policy,
        ),
        public_initial_transcript=PUBLIC_TRANSCRIPT,
        latent_resources=latent_resources,
        index_records=index_records,
        local_authority=local_authority,
        predicate_record=predicate_record,
        reciprocal_response=reciprocal_response,
        raw_fact=raw_fact,
        raw_disclosure_allowed=raw_disclosure_allowed,
        local_oracle_allowed=local_oracle_allowed,
        platform_task=platform_task,
        goal_head_advances_after_qualification=(
            goal_head_advances_after_qualification
        ),
        latent_truth=latent,
        d_actual_truth=discoverable,
        handoff_truth=discoverable,
    )


def hidden_worlds() -> tuple[HiddenWorld, ...]:
    """Return the frozen semantic 22-world matrix."""

    e_indexed = _resource("e-indexed")
    e_unexpressed = _resource("e-unexpressed")
    u_compat = _resource("u-compat")
    s_active = _resource("s-active")
    s_revoked = _resource("s-revoked")
    n_new = _resource("n-new")
    q_unexpressed = _resource("q-unexpressed")
    q_unwilling = _resource("q-unwilling")
    z_exists = _resource("z-exists")
    r_mutual = _resource("r-mutual")
    r_one_sided = _resource("r-one-sided")
    p_shared = _resource("p-shared")
    c_allowed = _resource("c-allowed")
    c_forbidden = _resource("c-forbidden")

    definitions = (
        ("E-INDEXED", "E", dict(latent_resources=(e_indexed,), index_records=(_record("e-indexed"),), latent=True, discoverable=True)),
        ("E-UNEXPRESSED", "E", dict(latent_resources=(e_unexpressed,), local_authority=_local_online("e-unexpressed"), latent=True, discoverable=True)),
        ("U-COMPAT", "U", dict(latent_resources=(u_compat,), index_records=(_record("u-compat"),), latent=True, discoverable=True)),
        ("U-DIRECTION-DECOY", "U", dict(latent_resources=(_resource("u-decoy", direction="provide_finance"),), index_records=(_record("u-decoy", direction="provide_finance"),), latent=False, discoverable=False)),
        ("S-ACTIVE", "S", dict(latent_resources=(s_active,), index_records=(_record("s-active"),), latent=True, discoverable=True)),
        ("S-REVOKED", "S", dict(latent_resources=(s_revoked,), index_records=(_record("s-revoked", qualification_revokes=True),), goal_head_advances_after_qualification=True, latent=True, discoverable=False)),
        ("N-NEW-FACT", "N", dict(latent_resources=(n_new,), local_authority=_local_online("n-new"), latent=True, discoverable=True)),
        ("N-NO-FACT", "N", dict(local_authority=LocalAuthority("authority:n", "OFFLINE", timeout_evidence=sign_authority_evidence("AUTHORITY_TIMEOUT", "observer:runner", QUERY_SCOPE, nonce="n-timeout")), clarification_policy="AMBIGUOUS", latent=False, discoverable=False)),
        ("Q-UNEXPRESSED", "Q", dict(latent_resources=(q_unexpressed,), local_authority=_local_online("q-unexpressed"), latent=True, discoverable=True)),
        ("Q-UNKNOWN", "Q", dict(local_authority=LocalAuthority("authority:q", "OFFLINE", timeout_evidence=sign_authority_evidence("AUTHORITY_TIMEOUT", "observer:runner", QUERY_SCOPE, nonce="q-timeout")), latent=False, discoverable=False)),
        (
            "Q-UNWILLING",
            "Q",
            dict(
                latent_resources=(q_unwilling,),
                local_authority=LocalAuthority(
                    "authority:q-unwilling",
                    "SIGNED_REFUSAL",
                    fact=q_unwilling,
                    refusal=sign_authority_evidence(
                        "SIGNED_REFUSAL",
                        "authority:q-unwilling",
                        QUERY_SCOPE,
                        nonce="q-refusal",
                    ),
                ),
                latent=True,
                discoverable=False,
            ),
        ),
        (
            "Q-ABSENT",
            "Q",
            dict(
                local_authority=LocalAuthority(
                    "authority:q-closed",
                    "CLOSED",
                    completeness=sign_authority_evidence(
                        "POPULATION_COMPLETENESS",
                        "authority:q-closed",
                        QUERY_SCOPE,
                        nonce="q-completeness",
                    ),
                    negative_attestation=sign_authority_evidence(
                        "NEGATIVE_ATTESTATION",
                        "authority:q-closed",
                        QUERY_SCOPE,
                        nonce="q-negative",
                    ),
                ),
                latent=False,
                discoverable=False,
            ),
        ),
        ("Z-EXISTS", "Z", dict(latent_resources=(z_exists,), local_authority=LocalAuthority("authority:z", "POLICY_SILENT", fact=z_exists), clarification_policy="ZERO_DISCLOSURE", latent=True, discoverable=False)),
        ("Z-ABSENT", "Z", dict(local_authority=LocalAuthority("authority:z", "POLICY_SILENT"), clarification_policy="ZERO_DISCLOSURE", latent=False, discoverable=False)),
        ("R-MUTUAL", "R", dict(latent_resources=(r_mutual,), index_records=(_record("r-mutual", status="COARSE"),), reciprocal_response=ReciprocalResponse("ACCEPTED", "authority:r-mutual", sign_authority_evidence("RECIPROCAL_ACCEPTANCE", "authority:r-mutual", QUERY_SCOPE, nonce="r-mutual")), latent=True, discoverable=True)),
        ("R-ONE-SIDED", "R", dict(latent_resources=(r_one_sided,), index_records=(_record("r-one-sided", status="COARSE"),), reciprocal_response=ReciprocalResponse("SIGNED_REFUSAL", "authority:r-one-sided", sign_authority_evidence("SIGNED_REFUSAL", "authority:r-one-sided", QUERY_SCOPE, nonce="r-refusal")), latent=True, discoverable=False)),
        ("P-SHARED", "P", dict(latent_resources=(p_shared,), predicate_record=PredicateRecord("predicate:p-shared", "authority:p-shared", BASE_INTENT.purpose, BASE_INTENT.direction, BASE_INTENT.constraints), latent=True, discoverable=True)),
        ("P-NO-PREDICATE", "P", dict(clarification_policy="REFUSED", latent=False, discoverable=False)),
        ("C-RAW-ALLOWED", "C", dict(latent_resources=(c_allowed,), raw_fact=c_allowed, raw_disclosure_allowed=True, latent=True, discoverable=True)),
        ("C-RAW-FORBIDDEN", "C", dict(latent_resources=(c_forbidden,), raw_fact=c_forbidden, local_oracle_allowed=True, latent=True, discoverable=True)),
        ("T5-DIRECT", "T5", dict(platform_task=PlatformTask("task:t5-direct", "canonical_task_queue", "mark_completed", "DIRECT"), latent=False, discoverable=False)),
        ("T5-NO-MATCH", "T5", dict(platform_task=PlatformTask("task:t5-no-match", "canonical_task_queue", "mark_completed", "NO_MATCH"), latent=False, discoverable=False)),
    )
    return tuple(
        _world(index, truth_id, family, **values)
        for index, (truth_id, family, values) in enumerate(definitions, start=1)
    )


def derive_truth(world: HiddenWorld):
    """Compatibility entrypoint; the implementation lives in evaluator.py."""

    from .evaluator import evaluate_truth

    return evaluate_truth(world)
