from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import numpy as np
from scipy.optimize import linprog

from .events import EventStore
from .models import Arrangement, Commitment, Delegation
from .oracles import SovereignBoundaryOracle


@dataclass
class CoordinationResult:
    feasible: bool
    vector: np.ndarray | None
    objective: float | None
    iterations: int
    disclosed_cuts: int
    trace: list[dict] = field(default_factory=list)


class PolyhedralBoundaryCoordinator:
    """A cutting-plane coordinator over sovereign local separation oracles.

    It never asks an oracle to reveal its complete private constraint set. The
    master proposes a shared vector; each local oracle returns either acceptance
    or one separating boundary. Exact convergence claims require linear/convex
    assumptions and sound exact oracles.
    """

    def __init__(
        self,
        dimension: int,
        objective: np.ndarray,
        oracles: Iterable[SovereignBoundaryOracle],
        bounds: list[tuple[float, float]] | None = None,
        event_store: EventStore | None = None,
    ) -> None:
        self.dimension = dimension
        self.objective = np.asarray(objective, dtype=float)
        if self.objective.shape != (dimension,):
            raise ValueError("objective dimension mismatch")
        self.oracles = list(oracles)
        self.bounds = bounds or [(0.0, 1.0)] * dimension
        self.events = event_store or EventStore()
        self.A: list[np.ndarray] = []
        self.b: list[float] = []

    def seed_cut(self, coefficients: np.ndarray, rhs: float) -> None:
        self.A.append(np.asarray(coefficients, dtype=float))
        self.b.append(float(rhs))

    def solve(self, max_iterations: int = 500) -> CoordinationResult:
        trace: list[dict] = []
        for iteration in range(1, max_iterations + 1):
            A_ub = np.vstack(self.A) if self.A else None
            b_ub = np.asarray(self.b) if self.b else None
            res = linprog(-self.objective, A_ub=A_ub, b_ub=b_ub, bounds=self.bounds, method="highs")
            if not res.success:
                return CoordinationResult(False, None, None, iteration, len(self.A), trace)
            y = np.asarray(res.x)
            rejected = []
            for oracle in self.oracles:
                assessment = oracle.assess(y)
                if not assessment.feasible and assessment.cut is not None:
                    a = np.asarray(assessment.cut.coefficients, dtype=float)
                    duplicate = any(np.allclose(a, old, atol=1e-10) and abs(assessment.cut.rhs-rhs) < 1e-10
                                    for old, rhs in zip(self.A, self.b))
                    if not duplicate:
                        self.A.append(a)
                        self.b.append(assessment.cut.rhs)
                    rejected.append({"principal": oracle.principal_id, "cut": assessment.cut.model_dump(mode="json")})
                    self.events.append(
                        "boundary.cut.returned", "master", oracle.principal_id,
                        {"iteration": iteration, "cut": assessment.cut.model_dump(mode="json")},
                    )
            trace.append({"iteration": iteration, "objective": float(self.objective @ y), "rejections": rejected})
            if not rejected:
                self.events.append("arrangement.feasible", "master", "coordinator", {"vector": y.tolist()})
                return CoordinationResult(True, y, float(self.objective @ y), iteration, len(self.A), trace)
        return CoordinationResult(False, None, None, max_iterations, len(self.A), trace)


class CommitmentCompiler:
    def __init__(self, event_store: EventStore | None = None) -> None:
        self.events = event_store or EventStore()

    def compile(
        self,
        arrangement: Arrangement,
        delegation: Delegation,
        debtor: str,
        creditor: str,
        performance: dict,
        evidence_rule: dict,
        deadline: datetime,
        jurisdiction: str | None = None,
    ) -> Commitment:
        if arrangement.status != "recognized":
            raise ValueError("only a recognized arrangement may be compiled")
        if delegation.issuer_principal_id != debtor:
            raise PermissionError("delegation issuer is not debtor")
        if not delegation.permits("commit", arrangement.id):
            raise PermissionError("delegation does not permit commitment")
        commitment = Commitment(
            debtor=debtor,
            creditor=creditor,
            performance=performance,
            evidence_rule=evidence_rule,
            deadline=deadline,
            jurisdiction=jurisdiction,
            arrangement_id=arrangement.id,
        )
        self.events.append(
            "commitment.proposed", commitment.id, delegation.delegate_execution_id,
            commitment.model_dump(mode="json"),
        )
        return commitment
