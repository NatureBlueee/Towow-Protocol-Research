from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ClaimStatus(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    BOTH = "both"
    UNKNOWN = "unknown"


class CommitmentState(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class Principal(BaseModel):
    id: str = Field(default_factory=lambda: f"prn_{uuid4().hex}")
    display_name: str
    jurisdiction: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentExecution(BaseModel):
    id: str = Field(default_factory=lambda: f"exe_{uuid4().hex}")
    agent_instance_id: str
    principal_id: str
    model_id: str | None = None
    started_at: datetime = Field(default_factory=utcnow)
    ended_at: datetime | None = None


class Delegation(BaseModel):
    id: str = Field(default_factory=lambda: f"del_{uuid4().hex}")
    issuer_principal_id: str
    delegate_execution_id: str
    actions: set[str]
    objects: set[str] = Field(default_factory=set)
    constraints: dict[str, Any] = Field(default_factory=dict)
    expires_at: datetime
    nonce: str = Field(default_factory=lambda: uuid4().hex)
    revoked: bool = False

    def permits(self, action: str, object_id: str | None = None, now: datetime | None = None) -> bool:
        now = now or utcnow()
        if self.revoked or now >= self.expires_at or action not in self.actions:
            return False
        return not self.objects or object_id is None or object_id in self.objects


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: f"ev_{uuid4().hex}")
    kind: str
    uri: str | None = None
    digest: str | None = None
    issuer: str | None = None
    observed_at: datetime = Field(default_factory=utcnow)
    payload: dict[str, Any] = Field(default_factory=dict)


class Claim(BaseModel):
    id: str = Field(default_factory=lambda: f"clm_{uuid4().hex}")
    predicate: str
    subject: str
    object: Any
    status: ClaimStatus = ClaimStatus.UNKNOWN
    probability: float | None = Field(default=None, ge=0.0, le=1.0)
    provenance: list[str] = Field(default_factory=list)
    purpose: str | None = None
    audience: set[str] = Field(default_factory=set)
    expires_at: datetime | None = None


class CoordinationSchema(BaseModel):
    """Versioned variable and relation vocabulary for an arrangement family."""

    id: str = Field(default_factory=lambda: f"sch_{uuid4().hex}")
    name: str
    version: int = 1
    role_types: set[str] = Field(default_factory=set)
    task_types: set[str] = Field(default_factory=set)
    resource_types: set[str] = Field(default_factory=set)
    outcome_types: set[str] = Field(default_factory=set)
    constraint_types: set[str] = Field(default_factory=set)
    supersedes: str | None = None


class Arrangement(BaseModel):
    """Materialized candidate view of a deeper coordination program."""

    id: str = Field(default_factory=lambda: f"arr_{uuid4().hex}")
    schema_id: str
    version: int = 1
    parent_version: int | None = None
    participants: dict[str, str] = Field(default_factory=dict)  # role -> principal
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    unknowns: list[dict[str, Any]] = Field(default_factory=list)
    stances: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provenance: list[str] = Field(default_factory=list)
    status: Literal["draft", "candidate", "recognized", "compiled", "rejected"] = "draft"


class ArrangementPatch(BaseModel):
    id: str = Field(default_factory=lambda: f"pat_{uuid4().hex}")
    arrangement_id: str
    expected_version: int
    author_execution_id: str
    operations: list[dict[str, Any]]
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)


class ConstraintCut(BaseModel):
    """A machine-readable counterexample or boundary constraint."""

    id: str = Field(default_factory=lambda: f"cut_{uuid4().hex}")
    principal_id: str
    coefficients: list[float]
    rhs: float
    relation: Literal["<=", ">="] = "<="
    scope: str = "arrangement"
    rationale: str | None = None
    witness: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class Commitment(BaseModel):
    id: str = Field(default_factory=lambda: f"com_{uuid4().hex}")
    debtor: str
    creditor: str
    performance: dict[str, Any]
    preconditions: list[dict[str, Any]] = Field(default_factory=list)
    evidence_rule: dict[str, Any]
    deadline: datetime
    remedy: dict[str, Any] = Field(default_factory=dict)
    jurisdiction: str | None = None
    signatures: list[str] = Field(default_factory=list)
    state: CommitmentState = CommitmentState.PROPOSED
    arrangement_id: str | None = None

    @model_validator(mode="after")
    def check_parties(self) -> "Commitment":
        if self.debtor == self.creditor:
            raise ValueError("debtor and creditor must differ")
        return self


class VerificationResult(BaseModel):
    id: str = Field(default_factory=lambda: f"ver_{uuid4().hex}")
    commitment_id: str
    passed: bool
    criterion_version: str
    evidence_refs: list[str]
    findings: list[str] = Field(default_factory=list)
    verifier: str
    verified_at: datetime = Field(default_factory=utcnow)
