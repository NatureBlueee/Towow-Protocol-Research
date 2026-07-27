---
derived_view: true
source_path: Towow_Complete_Research_Archive_v1.2_2026-07-27/02_WORKSPACE_SNAPSHOT/Towow_Unified_Paper_v1.0_formal/通爻_主权智能主体共同现实形成_正式论文_v1.0.md
source_sha256: 7f92cd950ddb796f193509529268f22b12ab1de3a6139ee71ffa13d0ecc1a65e
source_line_start: 3097
source_line_end: 3268
source_heading: "附录 B　最小对象 Schema"
---

> 本文件是导航用派生视图。原始文本未改动；引用研究证据时应回到上列源文件与行号。

# 附录 B　最小对象 Schema

以下为规范性摘要，不替代可执行 JSON Schema。

## B.1 Entity

```yaml
Entity:
  entity_id: URI
  entity_type: person | legal_entity | organization | composite_agent
  responsibility_roots: [AuthorityRootRef]
  authority_loci: [AuthorityLocusRef]
  endpoints: [Endpoint]
  public_discovery_profile: optional
  provenance: Provenance
  status: active | suspended | retired
```

## B.2 AuthorityLocus

```yaml
AuthorityLocus:
  locus_id: URI
  root_ref: AuthorityRootRef
  role: string
  powers:
    propose: Scope
    recognize: Scope
    delegate: Scope
    commit: Scope
    execute: Scope
    witness: Scope
    adopt: Scope
    accept: Scope
    challenge: Scope
  representation: optional RepresentationRef
  validity: TimeInterval
  revocation: RevocationPolicy
```

AuthorityLocus 不必单独成为 canonical root；它可以作为 Entity 下的版本化权威记录，但其变更必须可追溯。

## B.3 Mandate

```yaml
Mandate:
  mandate_id: URI
  version: string
  issuer_locus: AuthorityLocusRef
  delegate: EntityOrExecutionRef
  principal_objective: ObjectiveVersionRef
  permitted_actions: [ActionPattern]
  permitted_objects: [ResourcePattern]
  monetary_bounds: optional Range
  time_bounds: TimeInterval
  risk_bounds: RiskPolicy
  data_rights:
    read: Scope
    compute: Scope
    retain: Scope
    derive: Scope
    train: Scope
    redisclose: Scope
  evidence_requirements: [WitnessPolicyRef]
  escalation_rules: [EscalationRule]
  revocation_policy: RevocationPolicy
  status: proposed | active | narrowed | revoked | expired
```

## B.4 RelationVersion

```yaml
RelationVersion:
  relation_id: URI
  version_id: content_hash
  frame_scope: string
  inherits_from: [RelationOrFrameRef]
  overrides: [SchemaPatch]
  schema:
    roles: R
    vocabulary: V
    transitions: T
    authority: A
    evidence: E
    data_rights: D
    outcomes: O
  participants: [RoleBinding]
  parameters: object
  unknowns: [Unknown]
  dependencies: [Dependency]
  materiality_summary: DifferenceReport
  status: draft | proposed | recognized | commit_ready | active | reopened | superseded
```

## B.5 Assertion

```yaml
Assertion:
  assertion_id: URI
  subject: ObjectRef
  predicate: URI
  value: any
  issuer: AuthorityOrModelRef
  epistemic_status: fact | inference | hypothesis | prediction | refusal
  confidence: optional number
  evidence_refs: [EvidenceRef]
  validity: TimeInterval
  defeaters: [DefeaterRef]
  supersedes: optional AssertionRef
```

模型 Assertion 与 Authority Assertion 使用相同外壳，但 `issuer` 和 `epistemic_status` 防止二者混淆。

## B.6 Commitment

```yaml
Commitment:
  commitment_id: URI
  version: string
  debtor: EntityOrLocusRef
  creditor: EntityOrLocusRef
  antecedent: Condition
  consequent: Obligation
  relation_version: RelationVersionRef
  mandate_refs: [MandateRef]
  resource_reservations: [ReservationRef]
  evidence_requirements: [WitnessPolicyRef]
  deadline: optional datetime
  remedy: RemedyPolicy
  exit: ExitPolicy
  status: proposed | recognized | reserved | active | fulfilled | breached | withdrawn | disputed | settled
```

## B.7 Operation

```yaml
Operation:
  operation_id: URI
  logical_action_key: string
  relation_version: RelationVersionRef
  commitment_refs: [CommitmentRef]
  mandate_ref: MandateRef
  action: URI
  target_domain: EntityOrSystemRef
  inputs: [ArtifactRef]
  preconditions: [Condition]
  idempotency_key: string
  witness_policy: WitnessPolicy
  retry_policy: RetryPolicy
  compensation: optional OperationRef
  irreversibility: reversible | partially_reversible | irreversible
  status: specified | authorized | attempted | effect_confirmed | failed | compensated
```

## B.8 EventEnvelope

```yaml
EventEnvelope:
  event_id: UUID
  type: EventType
  actor_entity: EntityRef
  authority_locus: optional AuthorityLocusRef
  mandate_ref: optional MandateRef
  relation_version: optional RelationVersionRef
  subject_ref: ObjectRef
  payload: object
  evidence_refs: [EvidenceRef]
  previous_event_hash: optional Hash
  timestamp: datetime
  attestation: SignatureOrAttestation
```

