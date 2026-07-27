from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .models import Commitment, CommitmentState, Evidence, VerificationResult


class TrustAdapter(ABC):
    """Interface object for external trust infrastructure.

    Implementations may use platform identity, electronic signature, escrow,
    insurance, a blockchain contract, or another jurisdiction-specific system.
    """

    @abstractmethod
    def identify(self, principal_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def reserve(self, commitment: Commitment, asset: str, amount: float) -> str: ...

    @abstractmethod
    def sign(self, commitment: Commitment, principal_id: str) -> str: ...

    @abstractmethod
    def activate(self, commitment: Commitment) -> Commitment: ...

    @abstractmethod
    def verify(self, commitment: Commitment, evidence: list[Evidence]) -> VerificationResult: ...

    @abstractmethod
    def settle(self, commitment: Commitment, verification: VerificationResult) -> Commitment: ...

    @abstractmethod
    def dispute(self, commitment: Commitment, reason: str) -> Commitment: ...


@dataclass
class InMemoryPlatformTrustAdapter(TrustAdapter):
    identities: dict[str, dict[str, Any]] = field(default_factory=dict)
    balances: dict[tuple[str, str], float] = field(default_factory=dict)
    reservations: dict[str, tuple[str, str, float]] = field(default_factory=dict)

    def identify(self, principal_id: str) -> dict[str, Any]:
        if principal_id not in self.identities:
            raise KeyError("principal not verified")
        return self.identities[principal_id]

    def reserve(self, commitment: Commitment, asset: str, amount: float) -> str:
        key = (commitment.debtor, asset)
        available = self.balances.get(key, 0.0)
        if amount <= 0 or available < amount:
            raise ValueError("insufficient reservable balance")
        reservation_id = f"res_{commitment.id}_{len(self.reservations)+1}"
        self.balances[key] = available - amount
        self.reservations[reservation_id] = (commitment.debtor, asset, amount)
        return reservation_id

    def sign(self, commitment: Commitment, principal_id: str) -> str:
        self.identify(principal_id)
        signature = f"sig:{principal_id}:{commitment.id}"
        if signature not in commitment.signatures:
            commitment.signatures.append(signature)
        return signature

    def activate(self, commitment: Commitment) -> Commitment:
        debtor_sig = f"sig:{commitment.debtor}:{commitment.id}"
        if debtor_sig not in commitment.signatures:
            raise PermissionError("debtor signature missing")
        commitment.state = CommitmentState.ACTIVE
        return commitment

    def verify(self, commitment: Commitment, evidence: list[Evidence]) -> VerificationResult:
        required_kind = commitment.evidence_rule.get("required_kind")
        passed = any(e.kind == required_kind for e in evidence) if required_kind else bool(evidence)
        return VerificationResult(
            commitment_id=commitment.id,
            passed=passed,
            criterion_version=str(commitment.evidence_rule.get("version", "1")),
            evidence_refs=[e.id for e in evidence],
            verifier="in-memory-platform",
            findings=[] if passed else ["required evidence missing"],
        )

    def settle(self, commitment: Commitment, verification: VerificationResult) -> Commitment:
        if commitment.state != CommitmentState.ACTIVE:
            raise ValueError("commitment is not active")
        if not verification.passed:
            raise ValueError("verification did not pass")
        commitment.state = CommitmentState.SATISFIED
        return commitment

    def dispute(self, commitment: Commitment, reason: str) -> Commitment:
        if not reason.strip():
            raise ValueError("dispute reason required")
        commitment.state = CommitmentState.DISPUTED
        return commitment
