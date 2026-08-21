"""Parent-owned semantic broker, evidence ledger, and canonical effects."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import hmac
import importlib
import inspect
import json
from pathlib import Path
import secrets
from types import CodeType
from typing import Any, Callable, Optional

from .authority_evidence import (
    AUTHORITY_EVIDENCE_MODEL_VERSION,
    semantic_scope,
    verify_authority_evidence,
)
from .evaluator import (
    EVALUATOR_VERSION,
    evaluate_truth,
    expected_q_state,
    principal_accepts_query,
    q_evidence_constructor,
)
from .spec import (
    BROKER_MODEL_VERSION,
    HANDOFF_STATUS,
    STRATEGY_REGISTRY_VERSION,
)
from .worlds import WORLD_MODEL_VERSION, semantic_compatible


@dataclass(frozen=True)
class VagueValueSeed:
    origin: str
    value: str
    seed_version: int
    nonce: str
    signature: str


@dataclass(frozen=True)
class PrincipalClarification:
    facet: str
    value: Any
    principal: str
    seed_nonce: str
    query_head_version: int
    nonce: str
    signature: str


@dataclass(frozen=True)
class QueryDraft:
    origin: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int
    provenance: str


@dataclass(frozen=True)
class SemanticQuery:
    origin: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int
    provenance: str
    nonce: str
    signature: str


@dataclass(frozen=True)
class SemanticProjection:
    origin: str
    purpose: str
    direction: str
    constraints: tuple[str, ...]
    version: int
    provenance: str
    principal: str
    nonce: str
    signature: str


@dataclass(frozen=True)
class Response:
    status: str
    ref: Optional[str] = None
    seed: Optional[VagueValueSeed] = None
    clarification: Optional[PrincipalClarification] = None
    query: Optional[SemanticQuery] = None
    projection: Optional[SemanticProjection] = None
    candidate_ref: Optional[str] = None
    evidence_kind: Optional[str] = None
    version: Optional[int] = None


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: asdict(item) if hasattr(item, "__dataclass_fields__") else list(item),
    ).encode()


class CandidateGateway:
    """Logical request-only surface; not a hostile in-process sandbox."""

    __slots__ = ("__dispatch",)

    def __init__(self, dispatch: Callable[..., Response]) -> None:
        object.__setattr__(self, "_CandidateGateway__dispatch", dispatch)

    def observe_goal_seed(self) -> Response:
        return self.__dispatch("observe_goal_seed")

    def request_principal_clarification(
        self,
        seed: VagueValueSeed,
        facet: str,
    ) -> Response:
        return self.__dispatch("request_principal_clarification", seed, facet)

    def form_query(
        self,
        seed: VagueValueSeed,
        clarifications: tuple[PrincipalClarification, ...],
        draft: QueryDraft,
    ) -> Response:
        return self.__dispatch("form_query", seed, clarifications, draft)

    def poll_local_trigger(
        self,
        query: SemanticQuery,
        mode: str = "STANDARD",
    ) -> Response:
        return self.__dispatch("poll_local_trigger", query, mode)

    def emit_projection(self, trigger_ref: Optional[str]) -> Response:
        return self.__dispatch("emit_projection", trigger_ref)

    def search_index(self, query: Any) -> Response:
        return self.__dispatch("search_index", query)

    def read_current_head(self, candidate_ref: Optional[str]) -> Response:
        return self.__dispatch("read_current_head", candidate_ref)

    def private_match(self, query: Any) -> Response:
        return self.__dispatch("private_match", query)

    def request_probe(self, candidate_ref: Optional[str]) -> Response:
        return self.__dispatch("request_probe", candidate_ref)

    def handoff(self, refs: tuple[str, ...] | list[str]) -> Response:
        return self.__dispatch("handoff", tuple(refs))

    def platform_direct(self) -> Response:
        return self.__dispatch("platform_direct")

    def stop(self, boundary: str) -> Response:
        return self.__dispatch("stop", boundary)


class ParentRuntime:
    """Trusted controller for one world and one parent-selected strategy."""

    _COSTS = {
        "observe_goal_seed": (1.0, 1.0),
        "request_principal_clarification": (0.5, 0.5),
        "form_query": (1.0, 1.0),
        "poll_local_trigger": (1.5, 1.5),
        "emit_projection": (2.0, 2.0),
        "search_index": (2.0, 2.5),
        "read_current_head": (1.0, 1.0),
        "private_match": (2.5, 3.0),
        "request_probe": (3.0, 4.0),
        "handoff": (1.5, 1.5),
        "platform_direct": (0.5, 0.5),
        "stop": (0.1, 0.1),
    }
    _REGISTERED_TARGET_DOMAINS = ("canonical_task_queue",)

    def __init__(
        self,
        world: Any,
        *,
        canonical_strategy_id: str,
        strategy_code_identity: Optional[str] = None,
    ) -> None:
        self.__world = world
        self.__canonical_strategy_id = canonical_strategy_id
        self.__strategy_code_identity = (
            strategy_code_identity
            or sha256(canonical_strategy_id.encode()).hexdigest()
        )
        self.__key = secrets.token_bytes(32)
        self.__evidence: dict[str, dict[str, Any]] = {}
        self.__query_store: dict[str, dict[str, Any]] = {}
        self.__seed_store: dict[str, dict[str, Any]] = {}
        self.__clarification_store: dict[str, dict[str, Any]] = {}
        self.__events: list[dict[str, Any]] = []
        self.__disclosures: list[dict[str, Any]] = []
        self.__index_heads = {
            record.record_id: {
                **asdict(record),
            }
            for record in world.index_records
        }
        self.__cost = 0.0
        self.__latency = 0.0
        self.__counter = 0
        self.__clock = 0
        self.__probe_calls = 0
        self.__terminal = "NOT_STOPPED"
        self.__candidate_disposition = "NO_CANDIDATE_CLAIMS"
        self.__q_constructor_observed: Optional[str] = None
        self.__platform_runs: list[dict[str, Any]] = []
        self.__platform_domain: dict[str, str] = {}
        self.__query_head_version = world.principal_intent.query_head_version
        self.query_injection_rejected = False
        self.handoffs: list[dict[str, Any]] = []

    @property
    def strategy_id(self) -> str:
        return self.__canonical_strategy_id

    def gateway(self) -> CandidateGateway:
        return CandidateGateway(self.__dispatch)

    def note_candidate_claims(self, candidate_claims: Optional[dict[str, Any]]) -> None:
        if candidate_claims:
            self.__candidate_disposition = "IGNORED_UNTRUSTED_CANDIDATE_CLAIMS"

    def _sign(self, payload: Any) -> str:
        return hmac.new(self.__key, _json_bytes(payload), sha256).hexdigest()

    def _new_ref(self, kind: str, binding: dict[str, Any]) -> str:
        self.__counter += 1
        nonce = secrets.token_hex(16)
        ref = f"opaque:{self._sign({'kind': kind, 'counter': self.__counter, 'nonce': nonce})[:32]}"
        self.__evidence[ref] = {
            "kind": kind,
            "binding": {
                **binding,
                "expiry": self.__clock + 20,
                "nonce": nonce,
            },
            "consumed": False,
        }
        return ref

    def _record(self, operation: str, status: str) -> None:
        cost, latency = self._COSTS[operation]
        self.__clock += 1
        self.__cost += cost
        self.__latency += latency
        self.__events.append(
            {
                "sequence": self.__clock,
                "operation": operation,
                "status": status,
            }
        )

    def _disclose(
        self,
        *,
        origin: str,
        recipient: str,
        sensitivity: str,
        retention: int,
        hops: int,
        depth: int,
        bits: int,
    ) -> None:
        self.__disclosures.append(
            {
                "origin": origin,
                "recipient": recipient,
                "sensitivity": sensitivity,
                "retention": retention,
                "hops": hops,
                "depth": depth,
                "bits": bits,
                "violation": False,
            }
        )

    def __dispatch(self, operation: str, *args: Any) -> Response:
        return getattr(self, f"_request_{operation}")(*args)

    def _query_payload(self, query: SemanticQuery) -> dict[str, Any]:
        return {
            "origin": query.origin,
            "purpose": query.purpose,
            "direction": query.direction,
            "constraints": query.constraints,
            "version": query.version,
            "provenance": query.provenance,
            "nonce": query.nonce,
        }

    def _query_fingerprint(self, query: SemanticQuery) -> str:
        semantic = {
            key: value
            for key, value in self._query_payload(query).items()
            if key not in {"nonce"}
        }
        return sha256(_json_bytes(semantic)).hexdigest()

    def _valid_query(self, query: Any) -> bool:
        if not isinstance(query, SemanticQuery):
            return False
        payload = self._query_payload(query)
        if not hmac.compare_digest(self._sign(payload), query.signature):
            return False
        if query.version != self.__query_head_version:
            return False
        stored = self.__query_store.get(query.nonce)
        return stored == {
            "payload": payload,
            "fingerprint": self._query_fingerprint(query),
        }

    def _semantic_match(self, item: Any, query: SemanticQuery) -> bool:
        return (
            item.purpose == query.purpose
            and item.direction == query.direction
            and set(query.constraints).issubset(item.constraints)
        )

    def _seed_payload(self, seed: VagueValueSeed) -> dict[str, Any]:
        return {
            "origin": seed.origin,
            "value": seed.value,
            "seed_version": seed.seed_version,
            "nonce": seed.nonce,
        }

    def _valid_seed(self, seed: Any) -> bool:
        if not isinstance(seed, VagueValueSeed):
            return False
        payload = self._seed_payload(seed)
        return (
            hmac.compare_digest(self._sign(payload), seed.signature)
            and self.__seed_store.get(seed.nonce) == payload
        )

    def _clarification_payload(
        self,
        clarification: PrincipalClarification,
    ) -> dict[str, Any]:
        return {
            "facet": clarification.facet,
            "value": clarification.value,
            "principal": clarification.principal,
            "seed_nonce": clarification.seed_nonce,
            "query_head_version": clarification.query_head_version,
            "nonce": clarification.nonce,
        }

    def _valid_clarification(
        self,
        clarification: Any,
        *,
        seed_nonce: str,
    ) -> bool:
        if not isinstance(clarification, PrincipalClarification):
            return False
        payload = self._clarification_payload(clarification)
        return (
            clarification.seed_nonce == seed_nonce
            and clarification.query_head_version == self.__query_head_version
            and hmac.compare_digest(
                self._sign(payload),
                clarification.signature,
            )
            and self.__clarification_store.get(clarification.nonce) == payload
        )

    def _request_observe_goal_seed(self) -> Response:
        seed_spec = self.__world.public_value_seed
        nonce = secrets.token_hex(16)
        unsigned = {
            "origin": seed_spec.origin,
            "value": seed_spec.value,
            "seed_version": seed_spec.version,
            "nonce": nonce,
        }
        seed = VagueValueSeed(**unsigned, signature=self._sign(unsigned))
        self.__seed_store[nonce] = unsigned
        self._record("observe_goal_seed", "VAGUE_VALUE_SEED_ISSUED")
        return Response("VAGUE_VALUE_SEED_ISSUED", seed=seed)

    def _request_request_principal_clarification(
        self,
        seed: Any,
        facet: str,
    ) -> Response:
        if not self._valid_seed(seed):
            self._record(
                "request_principal_clarification",
                "INVALID_VALUE_SEED",
            )
            return Response("INVALID_VALUE_SEED")
        policy = self.__world.principal_intent.clarification_policy
        if policy == "AMBIGUOUS":
            self._record(
                "request_principal_clarification",
                "CLARIFICATION_AMBIGUOUS",
            )
            return Response("CLARIFICATION_AMBIGUOUS")
        if policy == "REFUSED":
            self._record(
                "request_principal_clarification",
                "PRINCIPAL_REFUSED_CLARIFICATION",
            )
            return Response("PRINCIPAL_REFUSED_CLARIFICATION")
        if policy == "ZERO_DISCLOSURE":
            self._record(
                "request_principal_clarification",
                "ZERO_DISCLOSURE",
            )
            return Response("ZERO_DISCLOSURE")
        intent = self.__world.principal_intent
        values = {
            "PURPOSE": intent.purpose,
            "DIRECTION": intent.direction,
            "CONSTRAINTS": intent.constraints,
            "VERSION": self.__query_head_version,
        }
        if facet not in values:
            self._record(
                "request_principal_clarification",
                "INVALID_CLARIFICATION_FACET",
            )
            return Response("INVALID_CLARIFICATION_FACET")
        nonce = secrets.token_hex(16)
        unsigned = {
            "facet": facet,
            "value": values[facet],
            "principal": intent.principal,
            "seed_nonce": seed.nonce,
            "query_head_version": self.__query_head_version,
            "nonce": nonce,
        }
        clarification = PrincipalClarification(
            **unsigned,
            signature=self._sign(unsigned),
        )
        self.__clarification_store[nonce] = unsigned
        self._record(
            "request_principal_clarification",
            "PRINCIPAL_DISCLOSURE_PERMITTED",
        )
        return Response(
            "PRINCIPAL_DISCLOSURE_PERMITTED",
            clarification=clarification,
        )

    def _request_form_query(
        self,
        seed: Any,
        clarifications: tuple[Any, ...],
        draft: Any,
    ) -> Response:
        if not self._valid_seed(seed) or not isinstance(draft, QueryDraft):
            self._record("form_query", "INVALID_QUERY_FORMATION_INPUT")
            return Response("INVALID_QUERY_FORMATION_INPUT")
        if len(clarifications) != 4:
            self._record("form_query", "INCOMPLETE_PRINCIPAL_DISCLOSURE")
            return Response("INCOMPLETE_PRINCIPAL_DISCLOSURE")
        if any(
            not self._valid_clarification(item, seed_nonce=seed.nonce)
            for item in clarifications
        ):
            self._record("form_query", "INVALID_PRINCIPAL_DISCLOSURE")
            return Response("INVALID_PRINCIPAL_DISCLOSURE")
        by_facet = {item.facet: item.value for item in clarifications}
        if set(by_facet) != {"PURPOSE", "DIRECTION", "CONSTRAINTS", "VERSION"}:
            self._record("form_query", "DUPLICATE_OR_MISSING_FACET")
            return Response("DUPLICATE_OR_MISSING_FACET")
        accepted = QueryDraft(
            origin=seed.origin,
            purpose=by_facet["PURPOSE"],
            direction=by_facet["DIRECTION"],
            constraints=tuple(by_facet["CONSTRAINTS"]),
            version=by_facet["VERSION"],
            provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
        )
        intent = self.__world.principal_intent
        principal_accepts = (
            draft == accepted
            and draft.purpose == intent.purpose
            and draft.direction == intent.direction
            and draft.constraints == intent.constraints
            and draft.version == self.__query_head_version
        )
        if not principal_accepts:
            self._record("form_query", "QUERY_REJECTED_BY_PRINCIPAL")
            return Response("QUERY_REJECTED_BY_PRINCIPAL")
        nonce = secrets.token_hex(16)
        unsigned = {
            "origin": draft.origin,
            "purpose": draft.purpose,
            "direction": draft.direction,
            "constraints": draft.constraints,
            "version": draft.version,
            "provenance": draft.provenance,
            "nonce": nonce,
        }
        query = SemanticQuery(**unsigned, signature=self._sign(unsigned))
        self.__query_store[nonce] = {
            "payload": unsigned,
            "fingerprint": self._query_fingerprint(query),
        }
        self._record("form_query", "QUERY_ACCEPTED_BY_PRINCIPAL")
        return Response("QUERY_ACCEPTED_BY_PRINCIPAL", query=query)

    def _request_search_index(self, query: Any) -> Response:
        if not self._valid_query(query):
            self.query_injection_rejected = True
            self._record("search_index", "INVALID_QUERY_PROVENANCE")
            return Response("INVALID_QUERY_PROVENANCE")

        compatible: Optional[dict[str, Any]] = None
        incompatible_seen = False
        for record in self.__index_heads.values():
            record_obj = type("RecordView", (), record)
            if self._semantic_match(record_obj, query):
                compatible = record
                break
            incompatible_seen = True
        if compatible is None:
            status = "DIRECTION_INCOMPATIBLE" if incompatible_seen else "NO_INDEX_MATCH"
            self._record("search_index", status)
            return Response(status)

        state = compatible["status"]
        candidate_ref = self._new_ref(
            "INDEX_CANDIDATE",
            {
                "semantic_scope": semantic_scope(
                    query.purpose,
                    query.direction,
                    query.constraints,
                ),
                "query_fingerprint": self._query_fingerprint(query),
                "query_nonce": query.nonce,
                "goal_head": self.__query_head_version,
                "source": "INDEX",
                "source_id": compatible["record_id"],
                "principal": compatible["principal"],
                "version": compatible["version"],
                "current_head": compatible["current_head"],
            },
        )
        status = "COARSE_CANDIDATE" if state == "COARSE" else "DIRECTION_FOUND"
        self._record("search_index", status)
        return Response(status, candidate_ref=candidate_ref)

    def _request_read_current_head(self, candidate_ref: Optional[str]) -> Response:
        item = self.__evidence.get(candidate_ref or "")
        if item is None or item["kind"] != "INDEX_CANDIDATE":
            self._record("read_current_head", "INVALID_CANDIDATE")
            return Response("INVALID_CANDIDATE")
        binding = item["binding"]
        head = self.__index_heads.get(binding["source_id"])
        if head is None:
            self._record("read_current_head", "MISSING_CURRENT_HEAD")
            return Response("MISSING_CURRENT_HEAD")
        if head["status"] == "COARSE":
            self._record("read_current_head", "CURRENT_COARSE")
            return Response(
                "CURRENT_COARSE",
                ref=candidate_ref,
                version=head["version"],
            )
        if head["status"] != "ACTIVE":
            self._record("read_current_head", "REVOKED")
            return Response("REVOKED", version=head["version"])

        qualified = self._new_ref(
            "QUALIFIED",
            {
                "semantic_scope": binding["semantic_scope"],
                "query_fingerprint": binding["query_fingerprint"],
                "query_nonce": binding["query_nonce"],
                "goal_head": binding["goal_head"],
                "source": "INDEX",
                "source_id": head["record_id"],
                "principal": head["principal"],
                "version": head["version"],
                "current_head": head["current_head"],
            },
        )
        version = head["version"]
        if head["qualification_revokes"]:
            head["status"] = "REVOKED"
            head["version"] += 1
            head["current_head"] += 1
        if self.__world.goal_head_advances_after_qualification:
            self.__query_head_version += 1
        self._record("read_current_head", "CURRENT_COMPAT")
        return Response("CURRENT_COMPAT", ref=qualified, version=version)

    def _authority_evidence(
        self,
        kind: str,
        *,
        query: SemanticQuery,
        principal: str,
        source_id: str,
        version: int,
        authority_signature: Optional[str] = None,
    ) -> str:
        return self._new_ref(
            kind,
            {
                "semantic_scope": semantic_scope(
                    query.purpose,
                    query.direction,
                    query.constraints,
                ),
                "query_fingerprint": self._query_fingerprint(query),
                "query_nonce": query.nonce,
                "goal_head": self.__query_head_version,
                "source": kind,
                "source_id": source_id,
                "principal": principal,
                "version": version,
                "current_head": version,
                "authority_signature": authority_signature,
            },
        )

    def _request_poll_local_trigger(
        self,
        query: Any,
        mode: str = "STANDARD",
    ) -> Response:
        if not self._valid_query(query):
            self._record("poll_local_trigger", "INVALID_QUERY_PROVENANCE")
            return Response("INVALID_QUERY_PROVENANCE")
        world = self.__world
        local = world.local_authority
        expected_scope = semantic_scope(
            query.purpose,
            query.direction,
            query.constraints,
        )
        if mode == "STANDARD":
            if (
                local is not None
                and local.availability == "ONLINE"
                and local.fact is not None
                and local.projection_allowed
                and self._semantic_match(local.fact, query)
            ):
                ref = self._authority_evidence(
                    "LOCAL_FACT_TRIGGER",
                    query=query,
                    principal=local.principal,
                    source_id=local.fact.resource_id,
                    version=local.fact.version,
                )
                self.__q_constructor_observed = "LOCAL_TRUTH_PERMITTED_PROJECTION"
                self._record("poll_local_trigger", "LOCAL_FACT_TRIGGER")
                return Response(
                    "LOCAL_FACT_TRIGGER",
                    ref=ref,
                    evidence_kind="LOCAL_FACT_TRIGGER",
                )
            if local is not None and local.availability == "OFFLINE":
                if not verify_authority_evidence(
                    local.timeout_evidence,
                    allowed_kinds={"AUTHORITY_TIMEOUT"},
                    expected_scope=expected_scope,
                    expected_signer="observer:runner",
                ):
                    self._record(
                        "poll_local_trigger",
                        "INVALID_AUTHORITY_EVIDENCE",
                    )
                    return Response("INVALID_AUTHORITY_EVIDENCE")
                ref = self._authority_evidence(
                    "AUTHORITY_TIMEOUT",
                    query=query,
                    principal=local.principal,
                    source_id=f"timeout:{local.principal}",
                    version=local.timeout_evidence.version,
                    authority_signature=local.timeout_evidence.signature,
                )
                self.__q_constructor_observed = "AUTHORITY_TIMEOUT"
                self._record("poll_local_trigger", "AUTHORITY_TIMEOUT")
                return Response(
                    "AUTHORITY_TIMEOUT",
                    ref=ref,
                    evidence_kind="AUTHORITY_TIMEOUT",
                )
            if (
                local is not None
                and local.availability == "SIGNED_REFUSAL"
            ):
                if not verify_authority_evidence(
                    local.refusal,
                    allowed_kinds={"SIGNED_REFUSAL"},
                    expected_scope=expected_scope,
                    expected_signer=local.principal,
                ):
                    self._record(
                        "poll_local_trigger",
                        "INVALID_AUTHORITY_EVIDENCE",
                    )
                    return Response("INVALID_AUTHORITY_EVIDENCE")
                ref = self._authority_evidence(
                    "AUTHORITY_SIGNED_REFUSAL",
                    query=query,
                    principal=local.principal,
                    source_id=local.refusal.scope,
                    version=local.refusal.version,
                    authority_signature=local.refusal.signature,
                )
                self.__q_constructor_observed = "AUTHORITY_SIGNED_REFUSAL"
                self._record("poll_local_trigger", "AUTHORITY_SIGNED_REFUSAL")
                return Response(
                    "AUTHORITY_SIGNED_REFUSAL",
                    ref=ref,
                    evidence_kind="AUTHORITY_SIGNED_REFUSAL",
                )
            if (
                local is not None
                and local.availability == "CLOSED"
            ):
                completeness_valid = verify_authority_evidence(
                    local.completeness,
                    allowed_kinds={"POPULATION_COMPLETENESS"},
                    expected_scope=expected_scope,
                    expected_signer=local.principal,
                )
                negative_valid = verify_authority_evidence(
                    local.negative_attestation,
                    allowed_kinds={"NEGATIVE_ATTESTATION"},
                    expected_scope=expected_scope,
                    expected_signer=local.principal,
                )
                if not (completeness_valid and negative_valid):
                    self._record(
                        "poll_local_trigger",
                        "INVALID_AUTHORITY_EVIDENCE",
                    )
                    return Response("INVALID_AUTHORITY_EVIDENCE")
                ref = self._authority_evidence(
                    "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
                    query=query,
                    principal=local.principal,
                    source_id=local.completeness.scope,
                    version=max(
                        local.completeness.version,
                        local.negative_attestation.version,
                    ),
                    authority_signature=sha256(
                        (
                            local.completeness.signature
                            + local.negative_attestation.signature
                        ).encode()
                    ).hexdigest(),
                )
                self.__q_constructor_observed = (
                    "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION"
                )
                self._record(
                    "poll_local_trigger",
                    "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
                )
                return Response(
                    "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
                    ref=ref,
                    evidence_kind="CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
                )
            self._record("poll_local_trigger", "NO_OBSERVABLE_LOCAL_EVIDENCE")
            return Response("NO_OBSERVABLE_LOCAL_EVIDENCE")

        if mode == "CENTER_RAW":
            if world.raw_fact is not None and world.raw_disclosure_allowed:
                ref = self._authority_evidence(
                    "RAW_FACT_TRIGGER",
                    query=query,
                    principal=world.raw_fact.principal,
                    source_id=world.raw_fact.resource_id,
                    version=world.raw_fact.version,
                )
                self._record("poll_local_trigger", "RAW_FACT_TRIGGER")
                return Response("RAW_FACT_TRIGGER", ref=ref, evidence_kind="RAW_FACT_TRIGGER")
            status = (
                "RAW_DISCLOSURE_DENIED"
                if world.raw_fact is not None
                else "NO_RAW_FACT"
            )
            self._record("poll_local_trigger", status)
            return Response(status)

        if mode == "LOCAL_ORACLE":
            if world.raw_fact is not None and world.local_oracle_allowed:
                ref = self._authority_evidence(
                    "ORACLE_FACT_TRIGGER",
                    query=query,
                    principal=world.raw_fact.principal,
                    source_id=world.raw_fact.resource_id,
                    version=world.raw_fact.version,
                )
                self._record("poll_local_trigger", "ORACLE_FACT_TRIGGER")
                return Response(
                    "ORACLE_FACT_TRIGGER",
                    ref=ref,
                    evidence_kind="ORACLE_FACT_TRIGGER",
                )
            self._record("poll_local_trigger", "NO_ORACLE_EVIDENCE")
            return Response("NO_ORACLE_EVIDENCE")

        self._record("poll_local_trigger", "INVALID_LOCAL_MODE")
        return Response("INVALID_LOCAL_MODE")

    def _request_emit_projection(self, trigger_ref: Optional[str]) -> Response:
        trigger = self.__evidence.get(trigger_ref or "")
        allowed_kinds = {
            "LOCAL_FACT_TRIGGER": "LOCAL",
            "RAW_FACT_TRIGGER": "RAW",
            "ORACLE_FACT_TRIGGER": "ORACLE",
        }
        if trigger is None or trigger["kind"] not in allowed_kinds:
            self._record("emit_projection", "INVALID_TRIGGER")
            return Response("INVALID_TRIGGER")
        binding = trigger["binding"]
        local_resource = next(
            (
                resource
                for resource in self.__world.latent_resources
                if resource.resource_id == binding["source_id"]
            ),
            self.__world.raw_fact
            if self.__world.raw_fact is not None
            and self.__world.raw_fact.resource_id == binding["source_id"]
            else None,
        )
        if local_resource is None:
            self._record("emit_projection", "MISSING_LOCAL_TRUTH")
            return Response("MISSING_LOCAL_TRUTH")
        nonce = secrets.token_hex(16)
        unsigned = {
            "origin": local_resource.principal,
            "purpose": local_resource.purpose,
            "direction": local_resource.direction,
            "constraints": local_resource.constraints,
            "version": local_resource.version,
            "provenance": "AUTHORITY_LOCAL_PROJECTION",
            "principal": local_resource.principal,
            "nonce": nonce,
        }
        projection = SemanticProjection(**unsigned, signature=self._sign(unsigned))
        projection_scope = semantic_scope(
            projection.purpose,
            projection.direction,
            projection.constraints,
        )
        if projection_scope != binding["semantic_scope"]:
            self._record("emit_projection", "UNRELATED_PROJECTION_SCOPE")
            return Response("UNRELATED_PROJECTION_SCOPE")
        qualified = self._new_ref(
            "QUALIFIED",
            {
                "semantic_scope": projection_scope,
                "query_fingerprint": binding["query_fingerprint"],
                "query_nonce": binding["query_nonce"],
                "goal_head": binding["goal_head"],
                "source": allowed_kinds[trigger["kind"]],
                "source_id": local_resource.resource_id,
                "principal": local_resource.principal,
                "version": local_resource.version,
                "current_head": local_resource.version,
            },
        )
        self._disclose(
            origin="authority_local_projection",
            recipient="runner_router",
            sensitivity="derived",
            retention=1,
            hops=0,
            depth=1,
            bits=64,
        )
        self._record("emit_projection", "SEMANTIC_PROJECTION_EMITTED")
        return Response(
            "SEMANTIC_PROJECTION_EMITTED",
            ref=qualified,
            projection=projection,
        )

    def _request_private_match(self, query: Any) -> Response:
        if not self._valid_query(query):
            self.query_injection_rejected = True
            self._record("private_match", "INVALID_QUERY_PROVENANCE")
            return Response("INVALID_QUERY_PROVENANCE")
        predicate = self.__world.predicate_record
        if predicate is None:
            self._record("private_match", "NO_SHARED_PREDICATE")
            return Response("NO_SHARED_PREDICATE")
        if not predicate.active or not self._semantic_match(predicate, query):
            self._record("private_match", "PRIVATE_NO_MATCH")
            return Response("PRIVATE_NO_MATCH")
        ref = self._new_ref(
            "QUALIFIED",
            {
                "semantic_scope": semantic_scope(
                    query.purpose,
                    query.direction,
                    query.constraints,
                ),
                "query_fingerprint": self._query_fingerprint(query),
                "query_nonce": query.nonce,
                "goal_head": self.__query_head_version,
                "source": "PRIVATE",
                "source_id": predicate.predicate_id,
                "principal": predicate.principal,
                "version": predicate.version,
                "current_head": predicate.version,
            },
        )
        self._disclose(
            origin="predicate_witness",
            recipient="predicate_provider",
            sensitivity="cryptographic",
            retention=1,
            hops=0,
            depth=1,
            bits=16,
        )
        self._record("private_match", "PRIVATE_MATCH")
        return Response("PRIVATE_MATCH", ref=ref)

    def _request_request_probe(self, candidate_ref: Optional[str]) -> Response:
        self.__probe_calls += 1
        candidate = self.__evidence.get(candidate_ref or "")
        if candidate is None or candidate["kind"] != "INDEX_CANDIDATE":
            self._record("request_probe", "INVALID_PROBE_TARGET")
            return Response("INVALID_PROBE_TARGET")
        response = self.__world.reciprocal_response
        if response is None:
            self._record("request_probe", "NO_RECIPROCAL_ROUTE")
            return Response("NO_RECIPROCAL_ROUTE")
        binding = candidate["binding"]
        if response.kind == "SIGNED_REFUSAL":
            if not verify_authority_evidence(
                response.evidence,
                allowed_kinds={"SIGNED_REFUSAL"},
                expected_scope=binding["semantic_scope"],
                expected_signer=response.principal,
            ):
                self._record("request_probe", "INVALID_AUTHORITY_EVIDENCE")
                return Response("INVALID_AUTHORITY_EVIDENCE")
            ref = self._new_ref(
                "RECIPROCAL_SIGNED_REFUSAL",
                {
                    **{
                        key: binding[key]
                        for key in (
                            "semantic_scope",
                            "query_fingerprint",
                            "query_nonce",
                            "goal_head",
                        )
                    },
                    "source": "RECIPROCAL_SIGNED_REFUSAL",
                    "source_id": binding["source_id"],
                    "principal": response.principal,
                    "version": response.version,
                    "current_head": response.version,
                    "authority_signature": response.evidence.signature,
                },
            )
            self._record("request_probe", "RECIPROCAL_SIGNED_REFUSAL")
            return Response(
                "RECIPROCAL_SIGNED_REFUSAL",
                ref=ref,
                evidence_kind="AUTHORITY_SIGNED_REFUSAL",
            )
        if response.kind != "ACCEPTED":
            self._record("request_probe", "RECIPROCAL_UNKNOWN")
            return Response("RECIPROCAL_UNKNOWN")
        if not verify_authority_evidence(
            response.evidence,
            allowed_kinds={"RECIPROCAL_ACCEPTANCE"},
            expected_scope=binding["semantic_scope"],
            expected_signer=response.principal,
        ):
            self._record("request_probe", "INVALID_AUTHORITY_EVIDENCE")
            return Response("INVALID_AUTHORITY_EVIDENCE")
        ref = self._new_ref(
            "QUALIFIED",
            {
                "semantic_scope": binding["semantic_scope"],
                "query_fingerprint": binding["query_fingerprint"],
                "query_nonce": binding["query_nonce"],
                "goal_head": binding["goal_head"],
                "source": "PROBE",
                "source_id": binding["source_id"],
                "principal": response.principal,
                "version": response.version,
                "current_head": response.version,
            },
        )
        self._disclose(
            origin="bilateral_probe",
            recipient="counterparty",
            sensitivity="directional",
            retention=1,
            hops=1,
            depth=1,
            bits=32,
        )
        self._record("request_probe", "RECIPROCAL_MATCH")
        return Response("RECIPROCAL_MATCH", ref=ref)

    def _recheck_qualified(self, evidence: dict[str, Any]) -> tuple[bool, str]:
        binding = evidence["binding"]
        if self.__clock > binding["expiry"]:
            return False, "EVIDENCE_EXPIRED"
        if binding.get("goal_head") != self.__query_head_version:
            return False, "GOAL_QUERY_HEAD_ADVANCED"
        query_item = self.__query_store.get(binding.get("query_nonce"))
        if query_item is None:
            return False, "QUERY_BINDING_MISSING"
        query_payload = query_item["payload"]
        if (
            binding.get("query_fingerprint") != query_item["fingerprint"]
            or binding.get("semantic_scope")
            != semantic_scope(
                query_payload["purpose"],
                query_payload["direction"],
                tuple(query_payload["constraints"]),
            )
        ):
            return False, "QUERY_SCOPE_BINDING_INVALID"
        source = binding["source"]
        if source == "INDEX":
            head = self.__index_heads.get(binding["source_id"])
            if (
                head is None
                or head["status"] != "ACTIVE"
                or head["version"] != binding["version"]
                or head["current_head"] != binding["current_head"]
            ):
                return False, "POST_QUALIFICATION_REVOKED"
        elif source == "LOCAL":
            local = self.__world.local_authority
            if (
                local is None
                or local.fact is None
                or not local.projection_allowed
                or local.availability != "ONLINE"
                or local.fact.resource_id != binding["source_id"]
                or local.fact.version != binding["version"]
            ):
                return False, "LOCAL_PROJECTION_NO_LONGER_CURRENT"
        elif source == "PRIVATE":
            predicate = self.__world.predicate_record
            if (
                predicate is None
                or not predicate.active
                or predicate.predicate_id != binding["source_id"]
                or predicate.version != binding["version"]
            ):
                return False, "PRIVATE_WITNESS_NO_LONGER_CURRENT"
        elif source == "PROBE":
            response = self.__world.reciprocal_response
            if (
                response is None
                or response.kind != "ACCEPTED"
                or response.version != binding["version"]
                or not verify_authority_evidence(
                    response.evidence,
                    allowed_kinds={"RECIPROCAL_ACCEPTANCE"},
                    expected_scope=binding["semantic_scope"],
                    expected_signer=response.principal,
                )
            ):
                return False, "RECIPROCITY_NO_LONGER_CURRENT"
        elif source == "RAW":
            if (
                self.__world.raw_fact is None
                or not self.__world.raw_disclosure_allowed
                or self.__world.raw_fact.version != binding["version"]
            ):
                return False, "RAW_POLICY_NO_LONGER_CURRENT"
        elif source == "ORACLE":
            if (
                self.__world.raw_fact is None
                or not self.__world.local_oracle_allowed
                or self.__world.raw_fact.version != binding["version"]
            ):
                return False, "ORACLE_NO_LONGER_CURRENT"
        else:
            return False, "UNRECOGNIZED_EVIDENCE_SOURCE"
        return True, "CURRENT"

    def _request_handoff(self, refs: tuple[str, ...]) -> Response:
        if not refs:
            self._record("handoff", "HANDOFF_REJECTED")
            return Response("HANDOFF_REJECTED")
        if len(set(refs)) != len(refs):
            self._record("handoff", "DUPLICATE_REFERENCE_IN_HANDOFF")
            return Response("DUPLICATE_REFERENCE_IN_HANDOFF")
        selected: list[dict[str, Any]] = []
        for ref in refs:
            evidence = self.__evidence.get(ref)
            if evidence is None or evidence["kind"] != "QUALIFIED":
                self._record("handoff", "HANDOFF_REJECTED")
                return Response("HANDOFF_REJECTED")
            if evidence["consumed"]:
                self._record("handoff", "EVIDENCE_ALREADY_CONSUMED")
                return Response("EVIDENCE_ALREADY_CONSUMED")
            current, status = self._recheck_qualified(evidence)
            if not current:
                self._record("handoff", status)
                return Response(status)
            selected.append(evidence)

        for evidence in selected:
            evidence["consumed"] = True
        receipt_binding = {
            "semantic_scopes": sorted(
                evidence["binding"]["semantic_scope"] for evidence in selected
            ),
            "query_fingerprints": sorted(
                evidence["binding"]["query_fingerprint"]
                for evidence in selected
            ),
            "goal_heads": sorted(
                evidence["binding"]["goal_head"] for evidence in selected
            ),
            "sources": sorted(
                evidence["binding"]["source"] for evidence in selected
            ),
            "principals": sorted(
                evidence["binding"]["principal"] for evidence in selected
            ),
            "versions": sorted(
                evidence["binding"]["version"] for evidence in selected
            ),
            "current_heads": sorted(
                evidence["binding"]["current_head"] for evidence in selected
            ),
            "expiry": min(
                evidence["binding"]["expiry"] for evidence in selected
            ),
        }
        receipt = self._new_ref("HANDOFF_RECEIPT", receipt_binding)
        summary = {
            "status": HANDOFF_STATUS,
            "commitment": False,
            "authority": False,
            "capability": False,
            "binding_fingerprint": sha256(_json_bytes(receipt_binding)).hexdigest(),
        }
        self.handoffs.append(summary)
        self._record("handoff", HANDOFF_STATUS)
        return Response(HANDOFF_STATUS, ref=receipt)

    def _request_platform_direct(self) -> Response:
        task = self.__world.platform_task
        if task is None:
            self._record("platform_direct", "PLATFORM_NOT_APPLICABLE")
            return Response("PLATFORM_NOT_APPLICABLE")

        if task.target_domain not in self._REGISTERED_TARGET_DOMAINS:
            run = {
                "canonical_parent_state_machine": True,
                "task_id": task.task_id,
                "target_domain": task.target_domain,
                "requested_effect": task.requested_effect,
                "transitions": ["IDLE", "REJECTED_UNREGISTERED_TARGET_DOMAIN"],
                "before": dict(self.__platform_domain),
                "after": dict(self.__platform_domain),
                "effect_applied": False,
                "readback_confirmed": False,
                "status": "UNREGISTERED_TARGET_DOMAIN",
                "domain_kind": "INTERNAL_SYNTHETIC",
            }
            self.__platform_runs.append(run)
            self.__terminal = "UNREGISTERED_TARGET_DOMAIN"
            self._record("platform_direct", "UNREGISTERED_TARGET_DOMAIN")
            return Response("UNREGISTERED_TARGET_DOMAIN")

        transitions = ["IDLE", "VALIDATED"]
        before = dict(self.__platform_domain)
        if task.mode == "DIRECT":
            self.__platform_domain[task.task_id] = task.requested_effect
            transitions.extend(["EXECUTED", "READBACK_CONFIRMED"])
            readback = (
                self.__platform_domain.get(task.task_id)
                == task.requested_effect
            )
            status = "PLATFORM_COMPLETED" if readback else "PLATFORM_EFFECT_MISMATCH"
        else:
            transitions.extend(["NO_MATCH", "READBACK_CONFIRMED"])
            readback = task.task_id not in self.__platform_domain
            status = "PLATFORM_NO_MATCH" if readback else "PLATFORM_EFFECT_MISMATCH"
        after = dict(self.__platform_domain)
        run = {
            "canonical_parent_state_machine": True,
            "task_id": task.task_id,
            "target_domain": task.target_domain,
            "requested_effect": task.requested_effect,
            "transitions": transitions,
            "before": before,
            "after": after,
            "effect_applied": task.mode == "DIRECT" and readback,
            "readback_confirmed": readback,
            "status": status,
            "domain_kind": "INTERNAL_SYNTHETIC",
        }
        self.__platform_runs.append(run)
        self.__terminal = status
        self._record("platform_direct", status)
        return Response(status)

    def _request_stop(self, boundary: str) -> Response:
        if self.__terminal not in {
            "PLATFORM_COMPLETED",
            "PLATFORM_NO_MATCH",
            "PLATFORM_EFFECT_MISMATCH",
        }:
            self.__terminal = boundary
        self._record("stop", self.__terminal)
        return Response(self.__terminal)

    def semantic_trace(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (event["operation"], event["status"]) for event in self.__events
        )

    def trusted_summary(self) -> dict[str, Any]:
        sensitivity: dict[str, int] = {}
        for item in self.__disclosures:
            sensitivity[item["sensitivity"]] = (
                sensitivity.get(item["sensitivity"], 0) + 1
            )
        vector = {
            "origin_facts": len({item["origin"] for item in self.__disclosures}),
            "recipients": len({item["recipient"] for item in self.__disclosures}),
            "sensitivity": sensitivity,
            "retention_units": sum(item["retention"] for item in self.__disclosures),
            "onward_hops": sum(item["hops"] for item in self.__disclosures),
            "depth": max((item["depth"] for item in self.__disclosures), default=0),
            "cryptographic_leakage_bits": sum(
                item["bits"] for item in self.__disclosures
            ),
            "policy_violations": sum(
                bool(item["violation"]) for item in self.__disclosures
            ),
        }
        return {
            "handoff": bool(self.handoffs),
            "terminal": self.__terminal,
            "operation_cost": round(self.__cost, 3),
            "latency_units": round(self.__latency, 3),
            "disclosure_events": len(self.__disclosures),
            "probe_calls": self.__probe_calls,
            "disclosure_vector": vector,
            "query_injection_rejected": self.query_injection_rejected,
            "semantic_trace": self.semantic_trace(),
            "q_evidence_constructor": self.__q_constructor_observed,
            "platform_runs": tuple(self.__platform_runs),
        }

    def _executable_preimage(self) -> str:
        package_dir = Path(__file__).resolve().parent
        files = tuple(
            path.name for path in sorted(package_dir.glob("*.py"))
        )
        file_hashes = {
            name: sha256((package_dir / name).read_bytes()).hexdigest()
            for name in files
        }

        def canonical_value(value: Any) -> Any:
            if isinstance(value, CodeType):
                return {"code": code_preimage(value)}
            if value is None or isinstance(value, (bool, int, str)):
                return {
                    "type": type(value).__name__,
                    "value": value,
                }
            if isinstance(value, float):
                return {"type": "float", "value": value.hex()}
            if isinstance(value, complex):
                return {
                    "type": "complex",
                    "real": value.real.hex(),
                    "imag": value.imag.hex(),
                }
            if isinstance(value, bytes):
                return {"type": "bytes", "value": value.hex()}
            if isinstance(value, tuple):
                return {
                    "type": "tuple",
                    "items": [canonical_value(item) for item in value],
                }
            if isinstance(value, list):
                return {
                    "type": "list",
                    "items": [canonical_value(item) for item in value],
                }
            if isinstance(value, (set, frozenset)):
                items = [canonical_value(item) for item in value]
                items.sort(
                    key=lambda item: json.dumps(
                        item,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                return {
                    "type": type(value).__name__,
                    "items": items,
                }
            if isinstance(value, dict):
                items = [
                    (canonical_value(key), canonical_value(item))
                    for key, item in value.items()
                ]
                items.sort(
                    key=lambda pair: json.dumps(
                        pair[0],
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                return {"type": "dict", "items": items}
            if value is Ellipsis:
                return {"type": "ellipsis"}
            if inspect.isclass(value):
                return {
                    "type": "class",
                    "module": getattr(value, "__module__", None),
                    "qualname": getattr(value, "__qualname__", None),
                }
            return {
                "type": (
                    f"{type(value).__module__}."
                    f"{type(value).__qualname__}"
                )
            }

        def code_preimage(code: CodeType) -> dict[str, Any]:
            return {
                "argcount": code.co_argcount,
                "posonlyargcount": getattr(code, "co_posonlyargcount", 0),
                "kwonlyargcount": code.co_kwonlyargcount,
                "flags": code.co_flags,
                "bytecode": code.co_code.hex(),
                "constants": [
                    canonical_value(item) for item in code.co_consts
                ],
                "names": code.co_names,
                "varnames": code.co_varnames,
                "freevars": code.co_freevars,
                "cellvars": code.co_cellvars,
            }

        def function_preimage(function: Any) -> Optional[dict[str, Any]]:
            if isinstance(function, (staticmethod, classmethod)):
                function = function.__func__
            if isinstance(function, property):
                parts = {}
                for name, accessor in (
                    ("get", function.fget),
                    ("set", function.fset),
                    ("delete", function.fdel),
                ):
                    if accessor is not None:
                        parts[name] = function_preimage(accessor)
                return {"property": parts}
            code = getattr(function, "__code__", None)
            if code is None:
                return None
            return {
                "code": code_preimage(code),
                "defaults": canonical_value(
                    getattr(function, "__defaults__", None)
                ),
                "kwdefaults": canonical_value(
                    getattr(function, "__kwdefaults__", None)
                ),
            }

        def class_preimage(class_type: type) -> dict[str, Any]:
            callables = {}
            for name, value in sorted(vars(class_type).items()):
                identity = function_preimage(value)
                if identity is not None:
                    callables[name] = identity
            return callables

        def code_objects(value: Any) -> list[CodeType]:
            if isinstance(value, (staticmethod, classmethod)):
                value = value.__func__
            if isinstance(value, property):
                result = []
                for accessor in (value.fget, value.fset, value.fdel):
                    if accessor is not None:
                        result.extend(code_objects(accessor))
                return result
            if inspect.isclass(value):
                result = []
                for item in vars(value).values():
                    result.extend(code_objects(item))
                return result
            code = getattr(value, "__code__", None)
            return [code] if isinstance(code, CodeType) else []

        def referenced_names(codes: list[CodeType]) -> set[str]:
            result: set[str] = set()
            pending = list(codes)
            while pending:
                code = pending.pop()
                result.update(code.co_names)
                pending.extend(
                    item
                    for item in code.co_consts
                    if isinstance(item, CodeType)
                )
            return result

        def imported_alias_preimage(value: Any) -> dict[str, Any]:
            if inspect.isfunction(value) or inspect.ismethod(value):
                return {
                    "kind": "python_function",
                    "module": getattr(value, "__module__", None),
                    "qualname": getattr(value, "__qualname__", None),
                    "identity": function_preimage(value),
                }
            if inspect.isclass(value):
                module = getattr(value, "__module__", None)
                identity = (
                    class_preimage(value)
                    if module is not None
                    and module.startswith("query_genesis")
                    else None
                )
                return {
                    "kind": "class",
                    "module": module,
                    "qualname": getattr(value, "__qualname__", None),
                    "identity": identity,
                }
            return {
                "kind": type(value).__qualname__,
                "module": getattr(value, "__module__", None),
                "qualname": getattr(value, "__qualname__", None),
            }

        module_names = tuple(
            f"query_genesis.{Path(name).stem}"
            for name in files
            if name not in {"__init__.py", "__main__.py"}
        )
        executable_objects: dict[str, Any] = {}
        for module_name in module_names:
            module = importlib.import_module(module_name)
            members = {}
            local_codes: list[CodeType] = []
            for name, value in sorted(vars(module).items()):
                if getattr(value, "__module__", None) != module_name:
                    continue
                if inspect.isclass(value):
                    members[name] = {"class": class_preimage(value)}
                    local_codes.extend(code_objects(value))
                elif inspect.isfunction(value):
                    members[name] = {"function": function_preimage(value)}
                    local_codes.extend(code_objects(value))
            aliases = {}
            for name in sorted(referenced_names(local_codes)):
                value = vars(module).get(name)
                if value is None or not callable(value):
                    continue
                if getattr(value, "__module__", None) == module_name:
                    continue
                aliases[name] = imported_alias_preimage(value)
            executable_objects[module_name] = {
                "defined_callables": members,
                "consumed_imported_callable_aliases": aliases,
            }
        return sha256(
            _json_bytes(
                {
                    "files": file_hashes,
                    "current_executable_objects": executable_objects,
                }
            )
        ).hexdigest()

    def _seal_anchors(self, summary: dict[str, Any]) -> dict[str, Any]:
        world_model = asdict(self.__world)
        current_heads = self.__index_heads
        semantic_queries = {
            "value_seeds": sorted(
                sha256(_json_bytes(item)).hexdigest()
                for item in self.__seed_store.values()
            ),
            "principal_clarifications": sorted(
                sha256(_json_bytes(item)).hexdigest()
                for item in self.__clarification_store.values()
            ),
            "accepted_queries": sorted(
                item["fingerprint"] for item in self.__query_store.values()
            ),
            "current_goal_query_head": self.__query_head_version,
        }
        model_manifest = {
            "broker": BROKER_MODEL_VERSION,
            "world": WORLD_MODEL_VERSION,
            "evaluator": EVALUATOR_VERSION,
            "strategy_registry": STRATEGY_REGISTRY_VERSION,
            "strategy_implementation": self.__strategy_code_identity,
            "authority_evidence_model": AUTHORITY_EVIDENCE_MODEL_VERSION,
            "evaluator_implementation": sha256(
                inspect.getsource(evaluate_truth).encode()
            ).hexdigest(),
        }
        return {
            "trial": self.__world.public_trial_id,
            "world_modes_and_policies": self._sign(world_model),
            "cost_table": sha256(_json_bytes(self._COSTS)).hexdigest(),
            "target_domain_registry": sha256(
                _json_bytes(self._REGISTERED_TARGET_DOMAINS)
            ).hexdigest(),
            "strategy_registry": STRATEGY_REGISTRY_VERSION,
            "strategy_implementation": self.__strategy_code_identity,
            "evaluator_version": EVALUATOR_VERSION,
            "world_model_version": WORLD_MODEL_VERSION,
            "broker_model_version": BROKER_MODEL_VERSION,
            "operation_log": sha256(_json_bytes(self.__events)).hexdigest(),
            "current_heads": self._sign(current_heads),
            "semantic_queries": self._sign(semantic_queries),
            "executable_preimage": self._executable_preimage(),
            "identity": self.__canonical_strategy_id,
            "cost": summary["operation_cost"],
            "model_manifest": sha256(_json_bytes(model_manifest)).hexdigest(),
        }

    def evidence_bundle(self) -> dict[str, Any]:
        summary = self.trusted_summary()
        canonical = {
            "strategy_id": self.__canonical_strategy_id,
            "summary": summary,
            "handoffs": self.handoffs,
            "anchors": self._seal_anchors(summary),
        }
        return {
            **canonical,
            "parent_seal": self._sign(canonical),
            "candidate_claims_disposition": self.__candidate_disposition,
        }

    def verify_bundle(self, bundle: dict[str, Any]) -> bool:
        canonical = {
            "strategy_id": bundle["strategy_id"],
            "summary": bundle["summary"],
            "handoffs": bundle["handoffs"],
            "anchors": bundle["anchors"],
        }
        return (
            bundle["anchors"].get("executable_preimage")
            == self._executable_preimage()
            and hmac.compare_digest(
                self._sign(canonical),
                bundle["parent_seal"],
            )
        )
