"""Lossless G6 semantics for the Wave 011 role/causality discriminator.

This module is deliberately a model, not an oracle or a decision policy.  It
contains no fixture loader and no expected-output table.  A runner must obtain
occurrences, owner claims, authority acts, and scheme states from their native
sources, then place them in these separate structures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


class SemanticError(ValueError):
    """Raised when an input would collapse or cross semantic boundaries."""


class TruthValue(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"


class SubjectType(str, Enum):
    OCCURRENCE = "OCCURRENCE"
    CLAIM = "CLAIM"


class Role(str, Enum):
    ATTEMPT = "ATTEMPT"
    EFFECT = "EFFECT"
    ADOPTION = "ADOPTION"
    ACCEPTANCE = "ACCEPTANCE"
    SETTLEMENT = "SETTLEMENT"


class QualificationStatus(str, Enum):
    QUALIFIES = "QUALIFIES"
    DOES_NOT_QUALIFY = "DOES_NOT_QUALIFY"
    UNKNOWN = "UNKNOWN"
    DISPUTED = "DISPUTED"


class AuthorityStatus(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class AuthorityStratum(str, Enum):
    S1_UNIFIED_AUTHORITY = "S1_UNIFIED_AUTHORITY"
    S2_INDEPENDENT_OWNERS = "S2_INDEPENDENT_OWNERS"
    S3_LAWFULLY_DELEGATED = "S3_LAWFULLY_DELEGATED"


class RecoveryRelevance(str, Enum):
    REQUIRED = "REQUIRED"
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"


class ProvenanceEdgeKind(str, Enum):
    CAUSES = "CAUSES"
    OBSERVES = "OBSERVES"
    CORRELATES = "CORRELATES"
    REVERSES = "REVERSES"
    COMPENSATES = "COMPENSATES"
    SUPERSEDES = "SUPERSEDES"


class QualificationEdgeKind(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    BINDS = "BINDS"
    AUTHORIZES = "AUTHORIZES"
    REVOKES = "REVOKES"
    COUNTS = "COUNTS"
    DISPUTES = "DISPUTES"
    SUPERSEDES = "SUPERSEDES"


class ControlEdgeKind(str, Enum):
    REQUIRES = "REQUIRES"
    ENABLES = "ENABLES"
    BLOCKS = "BLOCKS"
    ADVANCES = "ADVANCES"
    DISCHARGES = "DISCHARGES"
    REOPENS = "REOPENS"
    REVERSES = "REVERSES"


class SettlementPhase(str, Enum):
    AUTHORIZATION = "AUTHORIZATION"
    CAPTURE = "CAPTURE"
    SCHEME_SETTLEMENT = "SCHEME_SETTLEMENT"
    PROVIDER_BALANCE_CREDIT = "PROVIDER_BALANCE_CREDIT"
    PAYOUT = "PAYOUT"
    BENEFICIARY_RECEIPT = "BENEFICIARY_RECEIPT"
    CONTRACTUAL_DISCHARGE = "CONTRACTUAL_DISCHARGE"
    DISPUTE = "DISPUTE"
    CHARGEBACK = "CHARGEBACK"
    REVERSAL = "REVERSAL"


@dataclass(frozen=True)
class ObjectRef:
    authority_domain: str
    namespace: str
    local_id: str
    revision: str
    schema_version: str
    policy_version: str

    def identity(self) -> Tuple[str, str, str, str, str, str]:
        return (
            self.authority_domain,
            self.namespace,
            self.local_id,
            self.revision,
            self.schema_version,
            self.policy_version,
        )


@dataclass(frozen=True)
class Episode:
    episode_id: str
    q_version: str
    control_policy_version: str
    object_refs: Tuple[ObjectRef, ...] = ()


@dataclass(frozen=True)
class Occurrence:
    """A raw world or institutional occurrence, before episode qualification."""

    occurrence_id: str
    domain: str
    native_kind: str
    actor_id: str
    object_ref: ObjectRef
    occurred_at_event: int
    source_refs: Tuple[str, ...] = ()
    transition_from: Optional[str] = None
    transition_to: Optional[str] = None


@dataclass(frozen=True)
class Claim:
    """An owner assertion/current-head candidate, not reality itself."""

    claim_id: str
    ledger_id: str
    issuer_id: str
    authority_scope: str
    subject_id: str
    predicate: str
    value: TruthValue
    object_ref: Optional[ObjectRef]
    observed_at_event: int
    effective_from_event: int
    effective_until_event: Optional[int]
    head_sequence: int
    evidence_refs: Tuple[str, ...] = ()
    supersedes_claim_id: Optional[str] = None

    def is_effective(self, event_index: int) -> bool:
        return self.effective_from_event <= event_index and (
            self.effective_until_event is None
            or event_index < self.effective_until_event
        )


@dataclass
class OwnerLedger:
    """Carries only owner claims and their temporal current head.

    It intentionally has no occurrence, sensor, actuator, or grader field.
    Native owner services must create claims from their own store/sensor/act.
    """

    ledger_id: str
    owner_id: str
    _claims: Dict[str, Claim] = field(default_factory=dict, init=False, repr=False)

    def append_claim(self, claim: Claim) -> None:
        if claim.ledger_id != self.ledger_id:
            raise SemanticError("claim ledger_id does not match owner ledger")
        if claim.issuer_id != self.owner_id:
            raise SemanticError("only the ledger owner may append its claim")
        if claim.claim_id in self._claims:
            raise SemanticError("duplicate claim_id")
        if any(
            existing.head_sequence == claim.head_sequence
            for existing in self._claims.values()
        ):
            raise SemanticError("head_sequence must be unique within a ledger")
        if claim.supersedes_claim_id is not None:
            prior = self._claims.get(claim.supersedes_claim_id)
            if prior is None:
                raise SemanticError("superseded claim is absent from owner ledger")
            if prior.head_sequence >= claim.head_sequence:
                raise SemanticError("a superseding claim must advance head_sequence")
        self._claims[claim.claim_id] = claim

    @property
    def claims(self) -> Tuple[Claim, ...]:
        return tuple(sorted(self._claims.values(), key=lambda item: item.head_sequence))

    def claim(self, claim_id: str) -> Claim:
        try:
            return self._claims[claim_id]
        except KeyError as exc:
            raise SemanticError("unknown claim_id") from exc

    def current_head(self, event_index: int) -> Optional[Claim]:
        candidates = [
            claim for claim in self._claims.values() if claim.is_effective(event_index)
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.head_sequence)


@dataclass(frozen=True)
class EpisodeBinding:
    """Whether a subject binds this episode; it does not decide authority."""

    binding_id: str
    episode_id: str
    subject_id: str
    episode_object_ref: ObjectRef
    observed_object_ref: ObjectRef
    exact_binding: TruthValue
    current_version: TruthValue
    valid_time: TruthValue
    rule_version: str


@dataclass(frozen=True)
class AuthorityAssessment:
    """A separately sourced normative assessment."""

    authority_id: str
    episode_id: str
    assignment_id: str
    principal_id: str
    acting_subject_id: str
    authority_locus: str
    scope_role: Role
    object_ref: ObjectRef
    status: AuthorityStatus
    decided_at_event: int
    stratum: AuthorityStratum = AuthorityStratum.S2_INDEPENDENT_OWNERS
    delegation_chain: Tuple[str, ...] = ()
    delegation_scope_ref: Optional[str] = None
    revocable: bool = True
    expires_at_event: Optional[int] = None

    def status_at(self, event_index: int) -> AuthorityStatus:
        if (
            self.status == AuthorityStatus.AUTHORIZED
            and self.expires_at_event is not None
            and event_index >= self.expires_at_event
        ):
            return AuthorityStatus.EXPIRED
        return self.status


@dataclass(frozen=True)
class RoleAssignment:
    """Many-to-many mapping from one occurrence/claim to episode-relative roles."""

    assignment_id: str
    subject_type: SubjectType
    subject_id: str
    episode_id: str
    role: Role
    subtype: str
    qualification_rule_version: str
    binding_id: str
    qualification_id: str
    authority_id: Optional[str] = None
    counts_id: Optional[str] = None
    recovery_id: Optional[str] = None
    obligation_id: Optional[str] = None


@dataclass(frozen=True)
class QualificationAssessment:
    """Role fit only; authority and episode-success counting remain orthogonal."""

    qualification_id: str
    assignment_id: str
    episode_id: str
    status: QualificationStatus
    reason: str
    source_refs: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CountsTowardQ:
    counts_id: str
    assignment_id: str
    episode_id: str
    counts: TruthValue
    q_version: str
    reason: str


@dataclass(frozen=True)
class RecoveryAssessment:
    recovery_id: str
    assignment_id: str
    episode_id: str
    occurrence_id: str
    relevance: RecoveryRelevance
    affected_objects: Tuple[ObjectRef, ...]
    reason: str


@dataclass(frozen=True)
class ProvenanceEdge:
    edge_id: str
    source_occurrence_id: str
    target_occurrence_id: str
    kind: ProvenanceEdgeKind
    asserted_by: str
    status: TruthValue


@dataclass(frozen=True)
class QualificationEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    kind: QualificationEdgeKind


@dataclass(frozen=True)
class ControlNode:
    node_id: str
    episode_id: str
    node_type: str
    label: str


@dataclass(frozen=True)
class ControlEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    kind: ControlEdgeKind
    rule_version: str


@dataclass(frozen=True)
class Obligation:
    obligation_id: str
    episode_id: str
    scheme_id: str
    debtor_id: str
    beneficiary_id: str
    amount_minor: int
    currency: str
    required_phases: Tuple[SettlementPhase, ...]
    blocking_phases: Tuple[SettlementPhase, ...]
    finality_not_before_event: Optional[int] = None


@dataclass(frozen=True)
class SchemePhaseRecord:
    phase_record_id: str
    obligation_id: str
    scheme_id: str
    phase: SettlementPhase
    value: TruthValue
    owner_id: str
    claim_id: str
    effective_from_event: int
    effective_until_event: Optional[int]
    head_sequence: int
    supersedes_record_id: Optional[str] = None

    def is_effective(self, event_index: int) -> bool:
        return self.effective_from_event <= event_index and (
            self.effective_until_event is None
            or event_index < self.effective_until_event
        )


@dataclass(frozen=True)
class AssignmentEvaluation:
    assignment: RoleAssignment
    binding: EpisodeBinding
    qualification: QualificationAssessment
    authority: Optional[AuthorityAssessment]
    counts_toward_q: Optional[CountsTowardQ]
    recovery: Optional[RecoveryAssessment]


@dataclass(frozen=True)
class HeadVectorAssessment:
    consistent: bool
    cut_event: Optional[int]
    claim_ids: Tuple[str, ...]
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class SettlementAssessment:
    obligation_id: str
    status: QualificationStatus
    phase_heads: Tuple[Tuple[SettlementPhase, TruthValue], ...]
    reasons: Tuple[str, ...]


@dataclass(frozen=True)
class GraphSnapshot:
    node_ids: Tuple[str, ...]
    edge_ids: Tuple[str, ...]


class SemanticModel:
    """Container enforcing separation of G6 facts, judgments, and control."""

    def __init__(self) -> None:
        self.episodes: Dict[str, Episode] = {}
        self.occurrences: Dict[str, Occurrence] = {}
        self.ledgers: Dict[str, OwnerLedger] = {}
        self.claims: Dict[str, Claim] = {}
        self.bindings: Dict[str, EpisodeBinding] = {}
        self.authorities: Dict[str, AuthorityAssessment] = {}
        self.assignments: Dict[str, RoleAssignment] = {}
        self.qualifications: Dict[str, QualificationAssessment] = {}
        self.q_counts: Dict[str, CountsTowardQ] = {}
        self.recoveries: Dict[str, RecoveryAssessment] = {}
        self.provenance_edges: Dict[str, ProvenanceEdge] = {}
        self.qualification_edges: Dict[str, QualificationEdge] = {}
        self.control_nodes: Dict[str, ControlNode] = {}
        self.control_edges: Dict[str, ControlEdge] = {}
        self.obligations: Dict[str, Obligation] = {}
        self.scheme_phase_records: Dict[str, SchemePhaseRecord] = {}

    @staticmethod
    def _put(store: Dict[str, object], key: str, value: object) -> None:
        if key in store:
            raise SemanticError("duplicate semantic identifier: {}".format(key))
        store[key] = value

    def add_episode(self, episode: Episode) -> None:
        self._put(self.episodes, episode.episode_id, episode)

    def add_occurrence(self, occurrence: Occurrence) -> None:
        if occurrence.occurrence_id in self.claims:
            raise SemanticError("occurrence and claim identifiers must not collide")
        self._put(self.occurrences, occurrence.occurrence_id, occurrence)

    def add_ledger(self, ledger: OwnerLedger) -> None:
        self._put(self.ledgers, ledger.ledger_id, ledger)

    def append_claim(self, claim: Claim) -> None:
        if claim.claim_id in self.occurrences:
            raise SemanticError("claim and occurrence identifiers must not collide")
        try:
            ledger = self.ledgers[claim.ledger_id]
        except KeyError as exc:
            raise SemanticError("claim references unknown owner ledger") from exc
        ledger.append_claim(claim)
        self._put(self.claims, claim.claim_id, claim)

    def add_binding(self, binding: EpisodeBinding) -> None:
        self._require_episode_and_subject(
            binding.episode_id, binding.subject_id, allow_claim=True
        )
        self._put(self.bindings, binding.binding_id, binding)

    def add_authority(self, authority: AuthorityAssessment) -> None:
        if authority.episode_id not in self.episodes:
            raise SemanticError("authority references unknown episode")
        if (
            authority.status == AuthorityStatus.AUTHORIZED
            and authority.stratum == AuthorityStratum.S3_LAWFULLY_DELEGATED
            and (
                not authority.delegation_chain
                or authority.delegation_scope_ref is None
            )
        ):
            raise SemanticError(
                "lawful delegation requires chain and exact scope reference"
            )
        self._put(self.authorities, authority.authority_id, authority)

    def add_qualification(self, qualification: QualificationAssessment) -> None:
        if qualification.episode_id not in self.episodes:
            raise SemanticError("qualification references unknown episode")
        self._put(
            self.qualifications, qualification.qualification_id, qualification
        )

    def add_counts_toward_q(self, counts: CountsTowardQ) -> None:
        if counts.episode_id not in self.episodes:
            raise SemanticError("Q count references unknown episode")
        self._put(self.q_counts, counts.counts_id, counts)

    def add_recovery(self, recovery: RecoveryAssessment) -> None:
        if recovery.episode_id not in self.episodes:
            raise SemanticError("recovery references unknown episode")
        if recovery.occurrence_id not in self.occurrences:
            raise SemanticError("recovery must reference a raw occurrence")
        self._put(self.recoveries, recovery.recovery_id, recovery)

    def add_assignment(self, assignment: RoleAssignment) -> None:
        self._require_episode_and_subject(
            assignment.episode_id,
            assignment.subject_id,
            allow_claim=assignment.subject_type == SubjectType.CLAIM,
            require_claim=assignment.subject_type == SubjectType.CLAIM,
        )
        binding = self.bindings.get(assignment.binding_id)
        qualification = self.qualifications.get(assignment.qualification_id)
        if binding is None or qualification is None:
            raise SemanticError("role assignment lacks binding or qualification")
        if (
            binding.episode_id != assignment.episode_id
            or binding.subject_id != assignment.subject_id
            or qualification.episode_id != assignment.episode_id
            or qualification.assignment_id != assignment.assignment_id
        ):
            raise SemanticError("role assignment references cross-episode assessment")
        if assignment.authority_id is not None:
            authority = self.authorities.get(assignment.authority_id)
            if authority is None:
                raise SemanticError("role assignment references unknown authority")
            if (
                authority.episode_id != assignment.episode_id
                or authority.assignment_id != assignment.assignment_id
                or authority.scope_role != assignment.role
            ):
                raise SemanticError("authority does not scope this role assignment")
        if assignment.counts_id is not None:
            counts = self.q_counts.get(assignment.counts_id)
            if (
                counts is None
                or counts.assignment_id != assignment.assignment_id
                or counts.episode_id != assignment.episode_id
            ):
                raise SemanticError("CountsTowardQ does not scope this assignment")
        if assignment.recovery_id is not None:
            recovery = self.recoveries.get(assignment.recovery_id)
            if (
                recovery is None
                or recovery.assignment_id != assignment.assignment_id
                or recovery.episode_id != assignment.episode_id
            ):
                raise SemanticError("recovery assessment does not scope this assignment")
        if assignment.role == Role.SETTLEMENT and assignment.obligation_id is None:
            raise SemanticError("Settlement role requires an exact obligation")
        if assignment.obligation_id is not None:
            obligation = self.obligations.get(assignment.obligation_id)
            if (
                obligation is None
                or obligation.episode_id != assignment.episode_id
            ):
                raise SemanticError("settlement role references wrong obligation")
        self._put(self.assignments, assignment.assignment_id, assignment)

    def evaluate_assignment(self, assignment_id: str) -> AssignmentEvaluation:
        try:
            assignment = self.assignments[assignment_id]
        except KeyError as exc:
            raise SemanticError("unknown role assignment") from exc
        return AssignmentEvaluation(
            assignment=assignment,
            binding=self.bindings[assignment.binding_id],
            qualification=self.qualifications[assignment.qualification_id],
            authority=(
                self.authorities[assignment.authority_id]
                if assignment.authority_id is not None
                else None
            ),
            counts_toward_q=(
                self.q_counts[assignment.counts_id]
                if assignment.counts_id is not None
                else None
            ),
            recovery=(
                self.recoveries[assignment.recovery_id]
                if assignment.recovery_id is not None
                else None
            ),
        )

    def assignments_for_subject(self, subject_id: str) -> Tuple[RoleAssignment, ...]:
        return tuple(
            assignment
            for assignment in self.assignments.values()
            if assignment.subject_id == subject_id
        )

    def add_provenance_edge(self, edge: ProvenanceEdge) -> None:
        if (
            edge.source_occurrence_id not in self.occurrences
            or edge.target_occurrence_id not in self.occurrences
        ):
            raise SemanticError("provenance edges may join raw occurrences only")
        self._put(self.provenance_edges, edge.edge_id, edge)

    def add_qualification_edge(self, edge: QualificationEdge) -> None:
        nodes = self._qualification_node_ids()
        if edge.source_node_id not in nodes or edge.target_node_id not in nodes:
            raise SemanticError(
                "qualification edges may join qualification-layer nodes only"
            )
        self._put(self.qualification_edges, edge.edge_id, edge)

    def add_control_node(self, node: ControlNode) -> None:
        if node.episode_id not in self.episodes:
            raise SemanticError("control node references unknown episode")
        self._put(self.control_nodes, node.node_id, node)

    def add_control_edge(self, edge: ControlEdge) -> None:
        nodes = self._control_node_ids()
        if edge.source_node_id not in nodes or edge.target_node_id not in nodes:
            raise SemanticError(
                "control edges may join obligation/control nodes only"
            )
        self._put(self.control_edges, edge.edge_id, edge)

    def add_obligation(self, obligation: Obligation) -> None:
        if obligation.episode_id not in self.episodes:
            raise SemanticError("obligation references unknown episode")
        if not obligation.required_phases:
            raise SemanticError("obligation must freeze at least one required phase")
        if obligation.amount_minor < 0:
            raise SemanticError("obligation amount cannot be negative")
        self._put(self.obligations, obligation.obligation_id, obligation)

    def add_scheme_phase_record(self, record: SchemePhaseRecord) -> None:
        obligation = self.obligations.get(record.obligation_id)
        if obligation is None:
            raise SemanticError("scheme phase references unknown obligation")
        if record.scheme_id != obligation.scheme_id:
            raise SemanticError("scheme phase uses the wrong settlement scheme")
        claim = self.claims.get(record.claim_id)
        if claim is None:
            raise SemanticError("scheme phase must reference an owner claim")
        if claim.issuer_id != record.owner_id or claim.value != record.value:
            raise SemanticError("scheme phase does not preserve its owner claim")
        if record.supersedes_record_id is not None:
            prior = self.scheme_phase_records.get(record.supersedes_record_id)
            if prior is None:
                raise SemanticError("superseded scheme record is absent")
            if (
                prior.obligation_id != record.obligation_id
                or prior.phase != record.phase
                or prior.head_sequence >= record.head_sequence
            ):
                raise SemanticError("invalid scheme-phase supersession")
        self._put(
            self.scheme_phase_records, record.phase_record_id, record
        )

    def settlement_status(
        self, obligation_id: str, event_index: int
    ) -> SettlementAssessment:
        try:
            obligation = self.obligations[obligation_id]
        except KeyError as exc:
            raise SemanticError("unknown obligation") from exc

        heads: Dict[SettlementPhase, SchemePhaseRecord] = {}
        for record in self.scheme_phase_records.values():
            if (
                record.obligation_id == obligation_id
                and record.is_effective(event_index)
            ):
                current = heads.get(record.phase)
                if current is None or record.head_sequence > current.head_sequence:
                    heads[record.phase] = record

        reasons = []
        if (
            obligation.finality_not_before_event is not None
            and event_index < obligation.finality_not_before_event
        ):
            reasons.append("finality horizon remains open")

        for phase in obligation.blocking_phases:
            record = heads.get(phase)
            if record is None or record.value == TruthValue.UNKNOWN:
                reasons.append("{} status unavailable".format(phase.value))
            elif record.value in (
                TruthValue.TRUE,
                TruthValue.DISPUTED,
            ):
                reasons.append("{} is open".format(phase.value))

        missing_required = []
        explicitly_failed = []
        for phase in obligation.required_phases:
            record = heads.get(phase)
            if record is None or record.value in (
                TruthValue.UNKNOWN,
                TruthValue.DISPUTED,
            ):
                missing_required.append(phase.value)
            elif record.value != TruthValue.TRUE:
                explicitly_failed.append(phase.value)

        phase_heads = tuple(
            sorted(
                ((phase, record.value) for phase, record in heads.items()),
                key=lambda item: item[0].value,
            )
        )
        if any(" is open" in reason for reason in reasons):
            status = QualificationStatus.DISPUTED
        elif explicitly_failed:
            reasons.append(
                "required phase false: {}".format(",".join(explicitly_failed))
            )
            status = QualificationStatus.DOES_NOT_QUALIFY
        elif missing_required or reasons:
            if missing_required:
                reasons.append(
                    "required phase absent or unknown: {}".format(
                        ",".join(missing_required)
                    )
                )
            status = QualificationStatus.UNKNOWN
        else:
            status = QualificationStatus.QUALIFIES
        return SettlementAssessment(
            obligation_id=obligation_id,
            status=status,
            phase_heads=phase_heads,
            reasons=tuple(reasons),
        )

    def assess_head_vector(
        self, ledger_claim_ids: Mapping[str, str]
    ) -> HeadVectorAssessment:
        """Find a cut on which every supplied claim is the current owner head."""

        if not ledger_claim_ids:
            return HeadVectorAssessment(False, None, (), ("empty head vector",))
        claims = []
        reasons = []
        for ledger_id, claim_id in ledger_claim_ids.items():
            ledger = self.ledgers.get(ledger_id)
            if ledger is None:
                reasons.append("unknown ledger {}".format(ledger_id))
                continue
            try:
                claim = ledger.claim(claim_id)
            except SemanticError:
                reasons.append(
                    "{} is not a claim in {}".format(claim_id, ledger_id)
                )
                continue
            claims.append(claim)
        if reasons:
            return HeadVectorAssessment(
                False,
                None,
                tuple(claim.claim_id for claim in claims),
                tuple(reasons),
            )

        lower = max(claim.effective_from_event for claim in claims)
        finite_uppers = [
            claim.effective_until_event
            for claim in claims
            if claim.effective_until_event is not None
        ]
        upper = min(finite_uppers) if finite_uppers else None
        if upper is not None and lower >= upper:
            return HeadVectorAssessment(
                False,
                None,
                tuple(claim.claim_id for claim in claims),
                ("claims have no common validity window",),
            )

        candidate_events = {lower}
        for claim in claims:
            candidate_events.add(claim.effective_from_event)
        search_events = sorted(
            event
            for event in candidate_events
            if upper is None or event < upper
        )
        for event_index in search_events:
            if all(
                self.ledgers[claim.ledger_id].current_head(event_index) == claim
                for claim in claims
            ):
                return HeadVectorAssessment(
                    True,
                    event_index,
                    tuple(claim.claim_id for claim in claims),
                    (),
                )
        return HeadVectorAssessment(
            False,
            None,
            tuple(claim.claim_id for claim in claims),
            ("claims never form a simultaneous current-head cut",),
        )

    @property
    def occurrence_graph(self) -> GraphSnapshot:
        return GraphSnapshot(
            node_ids=tuple(self.occurrences),
            edge_ids=tuple(self.provenance_edges),
        )

    @property
    def qualification_graph(self) -> GraphSnapshot:
        return GraphSnapshot(
            node_ids=tuple(sorted(self._qualification_node_ids())),
            edge_ids=tuple(self.qualification_edges),
        )

    @property
    def obligation_control_graph(self) -> GraphSnapshot:
        return GraphSnapshot(
            node_ids=tuple(sorted(self._control_node_ids())),
            edge_ids=tuple(self.control_edges),
        )

    def validate_graph_separation(self) -> None:
        graph_sets = (
            set(self.occurrence_graph.node_ids),
            set(self.qualification_graph.node_ids),
            set(self.obligation_control_graph.node_ids),
        )
        if graph_sets[0] & graph_sets[1]:
            raise SemanticError("occurrence and qualification graph nodes collide")
        if graph_sets[0] & graph_sets[2]:
            raise SemanticError("occurrence and control graph nodes collide")
        if graph_sets[1] & graph_sets[2]:
            raise SemanticError("qualification and control graph nodes collide")

    def _require_episode_and_subject(
        self,
        episode_id: str,
        subject_id: str,
        allow_claim: bool,
        require_claim: bool = False,
    ) -> None:
        if episode_id not in self.episodes:
            raise SemanticError("unknown episode")
        occurrence_exists = subject_id in self.occurrences
        claim_exists = subject_id in self.claims
        if require_claim and not claim_exists:
            raise SemanticError("role assignment requires a claim subject")
        if not occurrence_exists and not (allow_claim and claim_exists):
            raise SemanticError("unknown or disallowed semantic subject")

    def _qualification_node_ids(self) -> set:
        return (
            set(self.claims)
            | set(self.bindings)
            | set(self.authorities)
            | set(self.assignments)
            | set(self.qualifications)
            | set(self.q_counts)
            | set(self.recoveries)
        )

    def _control_node_ids(self) -> set:
        return (
            set(self.control_nodes)
            | set(self.obligations)
            | set(self.scheme_phase_records)
        )
