"""Towow field research kit v0.7.

A dependency-free research instrument for authority-preserving relation
formation, extended with OPC operating-envelope and mechanism-routing views.
"""

__version__ = "0.7.0"

from .opc import CoordinationContext, CoordinationMode, OPCOperatingEnvelope
from .router import RouteDecision, RouteStep, route_coordination
from .stability import StabilityVector, EnactmentAssurance
from .reopen import affected_dependency_closure
from .frames import FrameScope, RelationFrameRef

__all__ = [
    'CoordinationContext','CoordinationMode','OPCOperatingEnvelope',
    'RouteDecision','RouteStep','route_coordination',
    'StabilityVector','EnactmentAssurance','affected_dependency_closure',
    'FrameScope','RelationFrameRef',
]
