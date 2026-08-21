"""Three capability-parity systems.

This module intentionally does not import hidden worlds or truth labels.
"""

from __future__ import annotations

from dataclasses import dataclass

from .execution import PublicFacts, TrialGateway
from .spec import ACTION_SPECS


@dataclass(frozen=True)
class PolicyRun:
    system: str
    requested_terminal: str
    mechanism_disposition: str
    completed_actions: tuple[str, ...]
    public_facts: PublicFacts


class BaseSystem:
    name = "base"

    @property
    def capabilities(self) -> tuple[str, ...]:
        return tuple(spec.name for spec in ACTION_SPECS)

    def _disposition(self, facts: PublicFacts) -> str:
        raise NotImplementedError

    def plan(self, facts: PublicFacts) -> tuple[str, ...] | None:
        """Return a policy-specific action plan or a correct-stop decision."""
        raise NotImplementedError

    def run(self, gateway: TrialGateway) -> PolicyRun:
        completed = ["INSPECT"]
        facts = gateway.inspect()
        plan = self.plan(facts)
        if plan is None:
            return PolicyRun(
                system=self.name,
                requested_terminal="NO_QUALIFIED_POLICY_FOUND",
                mechanism_disposition="Unknown",
                completed_actions=tuple(completed),
                public_facts=facts,
            )

        for action in plan:
            if not gateway.perform(action):
                return PolicyRun(
                    system=self.name,
                    requested_terminal="ACTION_REFUSED_OR_BOUNDED",
                    mechanism_disposition="Unknown",
                    completed_actions=tuple(completed),
                    public_facts=facts,
                )
            completed.append(action)
        return PolicyRun(
            system=self.name,
            requested_terminal="REQUESTED_SUCCESS",
            mechanism_disposition=self._disposition(facts),
            completed_actions=tuple(completed),
            public_facts=facts,
        )


class StrongCenterHitl(BaseSystem):
    name = "same_information_strong_center_hitl"

    def plan(self, facts: PublicFacts) -> tuple[str, ...] | None:
        """Backward-chain from qualified readback through public blockers."""
        if facts.value_floor != "PASS":
            return None
        if facts.authorization == "REFUSE" or facts.route == "UNAVAILABLE":
            return None

        requirements: list[tuple[str, tuple[str, ...]]] = [
            ("authorization", ("SIGN_COMMITMENT", "ISSUE_AUTHORIZATION")),
            ("route", ("ENABLE_ENDPOINT",)),
            (
                "known-schema",
                ("BUILD_KNOWN_ADAPTER", "INSTALL_KNOWN_ADAPTER"),
            ),
            (
                "novel-schema",
                ("PROPOSE_NEW_OPERATOR", "REGISTER_NEW_OPERATOR"),
            ),
        ]
        active = {
            "authorization": facts.authorization == "CONDITIONAL_COMMITMENT",
            "route": facts.route == "DISABLED_COMPATIBLE",
            "known-schema": facts.schema == "KNOWN_ADAPTER",
            "novel-schema": facts.schema == "NOVEL_OPERATOR",
        }
        preparation = tuple(
            action
            for requirement, actions in requirements
            if active[requirement]
            for action in actions
        )
        return preparation + ("TRANSFER", "PROJECT", "ACCEPT", "READBACK")

    def _disposition(self, facts: PublicFacts) -> str:
        if facts.route == "READY_UNADVERTISED":
            return "none-needed"
        if facts.authorization == "CONDITIONAL_COMMITMENT":
            return "human"
        if facts.schema == "KNOWN_ADAPTER":
            return "adapter"
        if facts.schema == "NOVEL_OPERATOR":
            return "combined"
        return "central"


class MatureWorkflowComposition(BaseSystem):
    name = "mature_workflow_composition"

    _RULES = (
        (
            lambda facts: facts.route == "DISABLED_COMPATIBLE",
            ("ENABLE_ENDPOINT",),
        ),
        (
            lambda facts: facts.schema == "KNOWN_ADAPTER",
            ("BUILD_KNOWN_ADAPTER", "INSTALL_KNOWN_ADAPTER"),
        ),
        (
            lambda facts: facts.schema == "NOVEL_OPERATOR",
            ("PROPOSE_NEW_OPERATOR", "REGISTER_NEW_OPERATOR"),
        ),
        (
            lambda facts: facts.authorization == "CONDITIONAL_COMMITMENT",
            ("SIGN_COMMITMENT", "ISSUE_AUTHORIZATION"),
        ),
    )

    def plan(self, facts: PublicFacts) -> tuple[str, ...] | None:
        """Execute a fixed exception-routing rule graph."""
        terminal_rule = (
            facts.value_floor != "PASS"
            or facts.authorization == "REFUSE"
            or facts.route == "UNAVAILABLE"
        )
        if terminal_rule:
            return None
        routed: list[str] = []
        for predicate, actions in self._RULES:
            if predicate(facts):
                routed.extend(actions)
        routed.extend(("TRANSFER", "PROJECT", "ACCEPT", "READBACK"))
        return tuple(routed)

    def _disposition(self, facts: PublicFacts) -> str:
        if facts.route == "READY_UNADVERTISED":
            return "none-needed"
        if facts.authorization == "CONDITIONAL_COMMITMENT":
            return "human"
        if facts.schema == "KNOWN_ADAPTER":
            return "adapter"
        return "combined"


class FormationCandidate(BaseSystem):
    name = "formation_candidate"

    def plan(self, facts: PublicFacts) -> tuple[str, ...] | None:
        """Construct an intervention set, then append direct execution."""
        if any(
            (
                facts.value_floor != "PASS",
                facts.authorization == "REFUSE",
                facts.route == "UNAVAILABLE",
            )
        ):
            return None

        blockers = {
            "authorization": facts.authorization,
            "route": facts.route,
            "schema": facts.schema,
        }
        interventions: list[str] = []
        while blockers:
            kind, value = blockers.popitem()
            if kind == "authorization" and value == "CONDITIONAL_COMMITMENT":
                interventions[0:0] = [
                    "SIGN_COMMITMENT",
                    "ISSUE_AUTHORIZATION",
                ]
            elif kind == "route" and value == "DISABLED_COMPATIBLE":
                interventions.append("ENABLE_ENDPOINT")
            elif kind == "schema" and value == "KNOWN_ADAPTER":
                interventions.extend(
                    ("BUILD_KNOWN_ADAPTER", "INSTALL_KNOWN_ADAPTER")
                )
            elif kind == "schema" and value == "NOVEL_OPERATOR":
                interventions.extend(
                    ("PROPOSE_NEW_OPERATOR", "REGISTER_NEW_OPERATOR")
                )
        return tuple(interventions) + (
            "TRANSFER",
            "PROJECT",
            "ACCEPT",
            "READBACK",
        )

    def _disposition(self, facts: PublicFacts) -> str:
        if facts.route == "READY_UNADVERTISED":
            return "none-needed"
        if facts.authorization == "CONDITIONAL_COMMITMENT":
            return "human"
        if facts.schema == "KNOWN_ADAPTER":
            return "adapter"
        if facts.schema == "NOVEL_OPERATOR":
            return "new"
        return "central"
