"""Runner for matched D/A/F worlds and attack arms."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict

from .candidates import (
    ActivationRunnerPolicy,
    FormationPolicy,
    ProducerOnlyPolicy,
    RemoveOperatorPolicy,
    ReverseOperatorPolicy,
    SameInformationStrongCenterHitlPolicy,
    StaticSearchPolicy,
    WrongAuthorityPolicy,
)
from .contract import (
    ActionKind,
    CandidatePolicy,
    EpisodeContract,
    PublicObservation,
    ResourceBudget,
)
from .truth import (
    EvaluationReport,
    HiddenWorld,
    OutcomeStatus,
    TruthSession,
    WorldKind,
)


def frozen_contract() -> EpisodeContract:
    return EpisodeContract(
        contract_id="G3-MATCHED-Q-V0-001",
        q=(
            "A joint path is executable by all necessary principals, remains "
            "above V0, is authorized at the declared locus, and is confirmed "
            "by the target-authoritative witness."
        ),
        v0=(
            "no necessary principal omitted",
            "no authority envelope expansion",
            "no target or acceptance substitution",
        ),
        necessary_principals=(
            "principal:requester",
            "principal:provider",
            "principal:joint-authority-holder",
        ),
        authority_locus="principal:joint-authority-holder",
        target_witness="target://joint-path/readback",
        resource_budget=ResourceBudget(max_actions=4, max_cost_units=4),
    )


def matched_worlds() -> tuple[HiddenWorld, ...]:
    contract = frozen_contract()
    return (
        HiddenWorld(
            world_id="D",
            kind=WorldKind.DISCOVERY,
            contract=contract,
            s0_path_exists=True,
            inactive_existing_resource=False,
            authorized_formation_available=False,
        ),
        HiddenWorld(
            world_id="A",
            kind=WorldKind.ACTIVATION,
            contract=contract,
            s0_path_exists=False,
            inactive_existing_resource=True,
            authorized_formation_available=False,
        ),
        HiddenWorld(
            world_id="F",
            kind=WorldKind.FORMATION,
            contract=contract,
            s0_path_exists=False,
            inactive_existing_resource=False,
            authorized_formation_available=True,
        ),
    )


def run_policy(world: HiddenWorld, policy: CandidatePolicy) -> EvaluationReport:
    session = TruthSession(world)
    decision_limit = world.contract.resource_budget.max_actions + 1
    for _ in range(decision_limit):
        observation = PublicObservation(
            contract=world.contract,
            events=tuple(session.events),
            actions_used=session.actions_used,
            cost_units_used=session.cost_units_used,
        )
        action = policy.decide(observation)
        if action.kind is ActionKind.STOP:
            break
        session.apply(action)
    return session.evaluate(policy.name)


def run_main_matrix() -> tuple[EvaluationReport, ...]:
    policies = (
        StaticSearchPolicy(),
        ActivationRunnerPolicy(),
        FormationPolicy(),
        SameInformationStrongCenterHitlPolicy(),
    )
    return tuple(
        run_policy(world, policy)
        for world in matched_worlds()
        for policy in policies
    )


def run_attack_matrix() -> tuple[EvaluationReport, ...]:
    world_f = next(
        world for world in matched_worlds() if world.kind is WorldKind.FORMATION
    )
    attacks = (
        WrongAuthorityPolicy(),
        ProducerOnlyPolicy(),
        RemoveOperatorPolicy(),
        ReverseOperatorPolicy(),
    )
    return tuple(run_policy(world_f, policy) for policy in attacks)


def _json_report(report: EvaluationReport) -> dict:
    payload = asdict(report)
    payload["status"] = report.status.value
    payload["reachability_kind"] = (
        report.reachability_kind.value if report.reachability_kind else None
    )
    return payload


def build_summary() -> dict:
    main = run_main_matrix()
    attacks = run_attack_matrix()
    all_reports = main + attacks
    fingerprints = {report.contract_fingerprint for report in all_reports}
    status_counts = Counter(report.status.value for report in all_reports)
    central = tuple(
        report
        for report in main
        if report.policy == "same_information_strong_center_hitl"
    )
    central_complete = (
        len(central) == 3
        and all(report.status is OutcomeStatus.SUCCESS for report in central)
    )

    return {
        "schema_version": "1.0",
        "experiment": "wave-008-g3-discriminator",
        "external_model_calls": 0,
        "matched_contract": {
            "fingerprints": sorted(fingerprints),
            "all_equal": len(fingerprints) == 1,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "comparative_result": {
            "same_policy_central_topology_constructive_success": central_complete,
            "independent_existing_solution_baseline_implemented": False,
            "existing_solution_value": "NOT_TESTED",
            "pfe_a2a_unique_increment": "NOT_ESTABLISHED",
            "novelty_scoring_used": False,
        },
        "main": [_json_report(report) for report in main],
        "attacks": [_json_report(report) for report in attacks],
    }
