"""Independent evaluator over allowed action/observation graphs."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict, deque

from .authority_evidence import semantic_scope, verify_authority_evidence
from .worlds import HiddenWorld, semantic_compatible


EVALUATOR_VERSION = "wave009-independent-action-graph-evaluator-v2"


@dataclass(frozen=True)
class EvaluatedTruth:
    latent: bool
    d_actual: bool
    handoff: bool
    reachable_paths: tuple[str, ...]


@dataclass(frozen=True)
class EvaluatorQuery:
    origin: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int
    provenance: str


def principal_accepts_query(world: HiddenWorld, query) -> bool:
    """Independent Principal acceptance predicate for a candidate draft/query."""

    intent = world.principal_intent
    return (
        intent.clarification_policy == "ALLOW"
        and getattr(query, "origin", None) == world.public_value_seed.origin
        and getattr(query, "purpose", None) == intent.purpose
        and getattr(query, "direction", None) == intent.direction
        and tuple(getattr(query, "constraints", ())) == intent.constraints
        and getattr(query, "version", None) == intent.query_head_version
        and getattr(query, "provenance", None)
        == "SYNTHETIC_PRINCIPAL_CLARIFICATION"
    )


def _matches_goal(item, world: HiddenWorld) -> bool:
    return semantic_compatible(
        purpose=item.purpose,
        direction=item.direction,
        constraints=item.constraints,
        goal=world.principal_intent,
    )


def evaluate_truth(world: HiddenWorld) -> EvaluatedTruth:
    """Build and traverse the permitted action/observation graph.

    Edge construction consumes semantic records and actual policies.  It does
    not call broker handlers or read the frozen result labels.
    """

    latent = any(
        resource.active and _matches_goal(resource, world)
        for resource in world.latent_resources
    )
    edges: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
    simulated_candidate_query = EvaluatorQuery(
        origin=world.public_value_seed.origin,
        purpose=world.principal_intent.purpose,
        direction=world.principal_intent.direction,
        constraints=world.principal_intent.constraints,
        version=world.principal_intent.query_head_version,
        provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
    )
    if principal_accepts_query(world, simulated_candidate_query):
        edges["START"].append(("PRINCIPAL_CLARIFICATION", None))
        edges["PRINCIPAL_CLARIFICATION"].append(("CANDIDATE_QUERY_DRAFT", None))
        edges["CANDIDATE_QUERY_DRAFT"].append(("SEMANTIC_QUERY", None))

    for record in world.index_records:
        if (
            record.status == "ACTIVE"
            and _matches_goal(record, world)
            and not record.qualification_revokes
        ):
            edges["SEMANTIC_QUERY"].append(("INDEX_MATCH", None))
            edges["INDEX_MATCH"].append(("CURRENT_HEAD", None))
            edges["CURRENT_HEAD"].append(
                ("QUALIFIED_CURRENT_INDEX", "CURRENT_INDEX")
            )
            edges["QUALIFIED_CURRENT_INDEX"].append(("HANDOFF", None))
        if (
            record.status == "COARSE"
            and _matches_goal(record, world)
            and world.reciprocal_response is not None
            and world.reciprocal_response.kind == "ACCEPTED"
            and verify_authority_evidence(
                world.reciprocal_response.evidence,
                allowed_kinds={"RECIPROCAL_ACCEPTANCE"},
                expected_scope=semantic_scope(
                    world.principal_intent.purpose,
                    world.principal_intent.direction,
                    world.principal_intent.constraints,
                ),
                expected_signer=world.reciprocal_response.principal,
            )
        ):
            edges["SEMANTIC_QUERY"].append(("COARSE_DIRECTION", None))
            edges["COARSE_DIRECTION"].append(("RECIPROCAL_PROBE", None))
            edges["RECIPROCAL_PROBE"].append(
                ("QUALIFIED_RECIPROCAL", "RECIPROCAL_PROBE")
            )
            edges["QUALIFIED_RECIPROCAL"].append(("HANDOFF", None))

    local = world.local_authority
    if (
        local is not None
        and local.availability == "ONLINE"
        and local.projection_allowed
        and local.fact is not None
        and local.fact.active
        and _matches_goal(local.fact, world)
    ):
        edges["SEMANTIC_QUERY"].append(("LOCAL_TRIGGER", None))
        edges["LOCAL_TRIGGER"].append(("SIGNED_PROJECTION", None))
        edges["SIGNED_PROJECTION"].append(
            ("QUALIFIED_LOCAL", "LOCAL_PERMITTED_PROJECTION")
        )
        edges["QUALIFIED_LOCAL"].append(("HANDOFF", None))

    predicate = world.predicate_record
    if (
        predicate is not None
        and predicate.active
        and _matches_goal(predicate, world)
    ):
        edges["SEMANTIC_QUERY"].append(("PRIVATE_MATCH", None))
        edges["PRIVATE_MATCH"].append(
            ("QUALIFIED_PRIVATE", "PRIVATE_PREDICATE")
        )
        edges["QUALIFIED_PRIVATE"].append(("HANDOFF", None))

    if (
        world.raw_fact is not None
        and world.raw_fact.active
        and _matches_goal(world.raw_fact, world)
    ):
        if world.raw_disclosure_allowed:
            edges["SEMANTIC_QUERY"].append(("RAW_POLICY_CHECK", None))
            edges["RAW_POLICY_CHECK"].append(
                ("QUALIFIED_RAW", "RAW_ALLOWED")
            )
            edges["QUALIFIED_RAW"].append(("HANDOFF", None))
        elif world.local_oracle_allowed:
            edges["SEMANTIC_QUERY"].append(("LOCAL_ORACLE", None))
            edges["LOCAL_ORACLE"].append(
                ("QUALIFIED_ORACLE", "LOCAL_AUTHORITATIVE_ORACLE")
            )
            edges["QUALIFIED_ORACLE"].append(("HANDOFF", None))

    visited = {"START"}
    queue = deque(["START"])
    path_labels: set[str] = set()
    while queue:
        node = queue.popleft()
        for target, label in edges.get(node, ()):
            if label is not None:
                path_labels.add(label)
            if target not in visited:
                visited.add(target)
                queue.append(target)
    reachable = tuple(sorted(path_labels)) if "HANDOFF" in visited else ()
    return EvaluatedTruth(
        latent=latent,
        d_actual="HANDOFF" in visited,
        handoff="HANDOFF" in visited,
        reachable_paths=reachable,
    )


def expected_q_state(world: HiddenWorld) -> str:
    """Construct expected state from authority evidence, never a Q label."""

    local = world.local_authority
    scope = semantic_scope(
        world.principal_intent.purpose,
        world.principal_intent.direction,
        world.principal_intent.constraints,
    )
    if local is None:
        return "UNKNOWN"
    if (
        local.availability == "ONLINE"
        and local.fact is not None
        and local.projection_allowed
        and _matches_goal(local.fact, world)
    ):
        return "UNEXPRESSED"
    if local.availability == "OFFLINE" and verify_authority_evidence(
        local.timeout_evidence,
        allowed_kinds={"AUTHORITY_TIMEOUT"},
        expected_scope=scope,
        expected_signer="observer:runner",
    ):
        return "UNKNOWN"
    if (
        local.availability == "SIGNED_REFUSAL"
        and verify_authority_evidence(
            local.refusal,
            allowed_kinds={"SIGNED_REFUSAL"},
            expected_scope=scope,
            expected_signer=local.principal,
        )
    ):
        return "UNWILLING_TO_DISCLOSE"
    if (
        local.availability == "CLOSED"
        and verify_authority_evidence(
            local.completeness,
            allowed_kinds={"POPULATION_COMPLETENESS"},
            expected_scope=scope,
            expected_signer=local.principal,
        )
        and verify_authority_evidence(
            local.negative_attestation,
            allowed_kinds={"NEGATIVE_ATTESTATION"},
            expected_scope=scope,
            expected_signer=local.principal,
        )
    ):
        return "ABSENT"
    return "UNKNOWN"


def q_evidence_constructor(world: HiddenWorld) -> str:
    state = expected_q_state(world)
    if state == "UNKNOWN":
        local = world.local_authority
        scope = semantic_scope(
            world.principal_intent.purpose,
            world.principal_intent.direction,
            world.principal_intent.constraints,
        )
        if (
            local is not None
            and local.availability == "OFFLINE"
            and verify_authority_evidence(
                local.timeout_evidence,
                allowed_kinds={"AUTHORITY_TIMEOUT"},
                expected_scope=scope,
                expected_signer="observer:runner",
            )
        ):
            return "AUTHORITY_TIMEOUT"
        return "INVALID_OR_UNRELATED_EVIDENCE"
    return {
        "UNEXPRESSED": "LOCAL_TRUTH_PERMITTED_PROJECTION",
        "UNWILLING_TO_DISCLOSE": "AUTHORITY_SIGNED_REFUSAL",
        "ABSENT": "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
    }[state]
