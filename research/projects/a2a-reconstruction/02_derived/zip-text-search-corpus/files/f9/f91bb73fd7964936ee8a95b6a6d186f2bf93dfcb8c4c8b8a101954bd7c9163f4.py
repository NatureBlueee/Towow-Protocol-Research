from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any


class FrameScope(str, Enum):
    PERSONAL = "PERSONAL"
    ORGANIZATIONAL = "ORGANIZATIONAL"
    PLATFORM = "PLATFORM"
    INDUSTRY = "INDUSTRY"
    LEGAL = "LEGAL"
    RELATION = "RELATION"


@dataclass(frozen=True)
class RelationFrameRef:
    """A relation's reference to inherited institutional frames.

    This is metadata on a RelationVersion, not a new aggregate root. `overrides`
    names the dimensions or rules intentionally changed by the relation-specific
    version; unresolved conflicts block compilation.
    """

    frame_id: str
    frame_scope: FrameScope
    frame_version: str
    inherits_from: tuple[str, ...] = ()
    overrides: tuple[str, ...] = ()
    unresolved_conflicts: tuple[str, ...] = ()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.frame_id:
            errors.append("frame_id is required")
        if not self.frame_version:
            errors.append("frame_version is required")
        if self.frame_id in self.inherits_from:
            errors.append("a frame cannot inherit from itself")
        if len(set(self.inherits_from)) != len(self.inherits_from):
            errors.append("inherits_from contains duplicates")
        if len(set(self.overrides)) != len(self.overrides):
            errors.append("overrides contains duplicates")
        return errors

    def compile_ready(self) -> bool:
        return not self.validate() and not self.unresolved_conflicts

    def to_dict(self) -> dict[str, Any]:
        value=asdict(self)
        value['frame_scope']=self.frame_scope.value
        value['compile_ready']=self.compile_ready()
        return value
