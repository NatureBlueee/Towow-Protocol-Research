from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .models import ConstraintCut


@dataclass(frozen=True)
class OracleAssessment:
    feasible: bool
    cut: ConstraintCut | None = None
    utility_interval: tuple[float, float] | None = None
    confidence: float = 1.0
    explanation: str | None = None


class SovereignBoundaryOracle(Protocol):
    principal_id: str

    def assess(self, shared_vector: np.ndarray) -> OracleAssessment:
        """Evaluate a candidate without revealing the full private feasible set."""
        ...


class PolytopeOracle:
    """Exact local oracle for A x <= b; reveals only a violated boundary when needed."""

    def __init__(self, principal_id: str, A: np.ndarray, b: np.ndarray, utility: np.ndarray | None = None):
        if A.ndim != 2 or b.ndim != 1 or A.shape[0] != b.shape[0]:
            raise ValueError("invalid polytope dimensions")
        self.principal_id = principal_id
        self.A = np.asarray(A, dtype=float)
        self.b = np.asarray(b, dtype=float)
        self.utility = None if utility is None else np.asarray(utility, dtype=float)

    def assess(self, shared_vector: np.ndarray) -> OracleAssessment:
        y = np.asarray(shared_vector, dtype=float)
        violation = self.A @ y - self.b
        idx = int(np.argmax(violation))
        if violation[idx] <= 1e-8:
            value = float(self.utility @ y) if self.utility is not None else 0.0
            return OracleAssessment(True, utility_interval=(value, value))
        cut = ConstraintCut(
            principal_id=self.principal_id,
            coefficients=self.A[idx].tolist(),
            rhs=float(self.b[idx]),
            rationale=f"private boundary violated by {float(violation[idx]):.6g}",
            witness={"violation": float(violation[idx])},
        )
        return OracleAssessment(False, cut=cut, explanation=cut.rationale)
