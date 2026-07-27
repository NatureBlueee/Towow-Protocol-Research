from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .opc import CoordinationContext, CoordinationMode


@dataclass(frozen=True)
class RouteStep:
    mode: CoordinationMode
    purpose: str
    mandatory_controls: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteDecision:
    steps: tuple[RouteStep, ...]
    collapse_safe: bool
    open_formation_required: bool
    reasons: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [
                {"mode": s.mode.value, "purpose": s.purpose, "mandatory_controls": list(s.mandatory_controls)}
                for s in self.steps
            ],
            "collapse_safe": self.collapse_safe,
            "open_formation_required": self.open_formation_required,
            "reasons": list(self.reasons),
            "unresolved": list(self.unresolved),
        }


def _collapse_safe(c: CoordinationContext) -> bool:
    """Whether the *whole relation* can be delegated to an existing frame.

    This is deliberately stricter than whether a particular computation can be
    centralized. Multiple authority loci may safely share a scheduler while
    retaining local commitment gates; that is handled by `_computation_safe`.
    """
    irreversibility_controlled = (
        c.irreversibility < 0.50
        or (
            c.deterministic_interface_available
            and c.schema_completeness >= 0.95
            and c.evidence_burden >= 0.70
        )
    )
    return (
        c.platform_frame_sufficient
        and c.schema_completeness >= 0.80
        and c.standardization >= 0.70
        and c.centralizable_within_grants
        and c.authority_plurality <= 1
        and c.externality_risk < 0.35
        and irreversibility_controlled
        and not c.dispute_active
        and not c.human_acceptance_required
    )


def _computation_safe(c: CoordinationContext) -> bool:
    """Whether candidate computation can be centralized without authority collapse."""
    return (
        c.optimization_problem
        and c.platform_frame_sufficient
        and c.schema_completeness >= 0.80
        and c.standardization >= 0.65
        and c.centralizable_within_grants
        and c.externality_risk < 0.35
        and c.irreversibility < 0.50
        and not c.dispute_active
        and not c.human_acceptance_required
    )


def route_coordination(c: CoordinationContext) -> RouteDecision:
    errors = c.validate()
    if errors:
        raise ValueError("; ".join(errors))

    reasons: list[str] = []
    unresolved: list[str] = []
    steps: list[RouteStep] = []
    collapse_safe = _collapse_safe(c)

    # Dispute handling is not ordinary optimization. It protects the historical
    # relation, separates performed effects from acceptance, and opens a scoped
    # human/legal remedy path without disclosing more private context than needed.
    if c.dispute_active:
        steps.append(RouteStep(
            CoordinationMode.HUMAN_ADJUDICATION,
            "resolve a contested authority, evidence, acceptance, or recourse question",
            (
                "preserve prior versions",
                "versioned relation schema",
                "scoped mandate",
                "minimal disclosure / local oracle",
                "freeze irreversible operations",
                "provisional remedy / staged evidence review",
                "effect/acceptance separation",
                "record standing and remedy scope",
            ),
        ))
        reasons.append("an active dispute cannot be settled by model confidence")
        return RouteDecision(tuple(steps), False, True, tuple(reasons))

    # One accountability root may contain several models, tools, and roles. That
    # is not automatically a cross-entity relation, but it still needs a local
    # operation specification, a mandate, resource bounds, and an effect witness.
    if c.self_executable and c.participants == 1 and c.authority_plurality == 1:
        steps.append(RouteStep(
            CoordinationMode.SELF_EXECUTION,
            "execute inside the OPC mandate without creating a cross-entity relation",
            (
                "versioned operation specification",
                "mandate scope",
                "resource reservation",
                "effect witness",
            ),
        ))
        reasons.append("the action remains inside one accountability and authority boundary")
        return RouteDecision(tuple(steps), True, False, tuple(reasons))

    # A computation may be centralized even when the relation as a whole cannot
    # be collapsed. The optimizer returns candidates; local authority loci retain
    # commitment and effect gates.
    if _computation_safe(c) and not collapse_safe:
        controls = [
            "scoped credentials",
            "do not mutate local authority",
            "return ranked candidates with evidence",
            "effect/acceptance separation",
            "reopen trigger",
        ]
        if c.participants > 2 or c.capacity_pressure >= 0.65:
            controls.append("resource reservation")
        steps.append(RouteStep(
            CoordinationMode.CENTRAL_OPTIMIZER,
            "compute candidates over a specified shared problem while keeping commitment authority local",
            tuple(controls),
        ))
        reasons.append("candidate computation is centralizable even though authority remains distributed")
        return RouteDecision(tuple(steps), False, False, tuple(reasons))

    # Standardized paths should be used when they preserve all relevant facts.
    if collapse_safe:
        if c.deterministic_interface_available:
            mode = CoordinationMode.DETERMINISTIC_SERVICE
            purpose = "run a stable relation through a scoped API or workflow"
        elif c.marketplace_available:
            mode = CoordinationMode.PLATFORM_MARKET
            purpose = "use an existing market frame for discovery, contracting, and settlement"
        elif c.optimization_problem:
            mode = CoordinationMode.CENTRAL_OPTIMIZER
            purpose = "solve an already specified allocation or scheduling problem"
        else:
            mode = CoordinationMode.DETERMINISTIC_SERVICE
            purpose = "compile the stable relation into a deterministic procedure"
        controls = ["scoped credentials", "effect/acceptance separation", "reopen trigger"]
        if c.participants > 2 or c.capacity_pressure >= 0.65:
            controls.append("resource reservation")
        if c.irreversibility >= 0.50:
            controls.append("pre-effect validation")
        steps.append(RouteStep(mode, purpose, tuple(controls)))
        reasons.append("the institutional frame and task schema are sufficient for lossless collapse")
        return RouteDecision(tuple(steps), True, False, tuple(reasons))

    # Authority plurality alone does not force open formation. It does so only
    # when the proposed mechanism would need to mutate or substitute those local
    # authority decisions. The `_computation_safe` branch above captures the
    # important counterexample of centralized triage/scheduling with local gates.
    formation_required = (
        c.schema_completeness < 0.80
        or not c.centralizable_within_grants
        or c.private_context_intensity >= 0.50
        or c.externality_risk >= 0.35
        or c.human_acceptance_required
        or (c.authority_plurality > 1 and not c.optimization_problem)
    )

    # A broker is useful when attention is scarce or the shared schema is very
    # incomplete. It never inherits final authority by default.
    if c.broker_available and (c.capacity_pressure >= 0.65 or c.schema_completeness < 0.45):
        steps.append(RouteStep(
            CoordinationMode.HUMAN_BROKER,
            "surface candidates, translate worlds, and reduce attention cost",
            ("no silent authority transfer", "source attribution", "record rejected candidates"),
        ))
        reasons.append("a boundary-spanning intermediary can reduce OPC attention load")

    if formation_required:
        if c.participants <= 2:
            mode = CoordinationMode.BILATERAL_FORMATION
            purpose = "form a versioned relation while preserving each party's mandate and private world"
        else:
            mode = CoordinationMode.TEMPORARY_COALITION
            purpose = "form a temporary multi-party operating constitution and resource commitments"
        controls = [
            "versioned relation schema", "scoped mandate", "countercondition and refusal",
            "resource reservation", "target-world effect witness", "acceptance gate", "local reopen",
        ]
        if c.externality_risk >= 0.35:
            controls.append("affected-party standing and recourse")
        if c.private_context_intensity >= 0.50:
            controls.append("minimal disclosure / local oracle")
        if c.irreversibility >= 0.50:
            controls.append("staged probe before irreversible effect")
        steps.append(RouteStep(mode, purpose, tuple(controls)))
        reasons.append("at least one material part of the relation cannot be safely collapsed into a fixed platform or global state")
    else:
        # This branch is deliberately conservative: if no safe standard path and
        # no formation operator is justified, the router returns an unresolved
        # result rather than silently choosing a mechanism.
        unresolved.append("no safe existing mechanism and no clear formation operator")

    # Once a relation repeats and drift is bounded, add a deterministic compiled stage.
    if c.repeated_relation and steps:
        steps.append(RouteStep(
            CoordinationMode.DETERMINISTIC_SERVICE,
            "compile the stable subgraph for repeated operation",
            ("minimum privilege", "version pinning", "defeater-triggered local reopen"),
        ))
        reasons.append("repeated stable work should not pay open-formation cost on every run")

    return RouteDecision(tuple(steps), collapse_safe, formation_required, tuple(reasons), tuple(unresolved))
