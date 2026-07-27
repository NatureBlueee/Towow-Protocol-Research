from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class StabilityVector:
    technical_operational: bool
    authority_governance: bool
    epistemic_assurance: bool
    normative_legitimacy: bool
    economic_resource: bool

    def passed(self, required: tuple[str, ...] | None = None) -> bool:
        required = required or tuple(asdict(self).keys())
        values = asdict(self)
        return all(values[name] for name in required)

    def failures(self) -> list[str]:
        return [name for name, value in asdict(self).items() if not value]


@dataclass(frozen=True)
class EnactmentAssurance:
    observable: bool
    information_reaches_authority: bool
    authority_can_intervene: bool
    evidence_admissible: bool
    pause_rollback_escalation: bool
    capacity_and_incentive: bool

    def enacted(self) -> bool:
        return all(asdict(self).values())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value['enacted'] = self.enacted()
        return value
