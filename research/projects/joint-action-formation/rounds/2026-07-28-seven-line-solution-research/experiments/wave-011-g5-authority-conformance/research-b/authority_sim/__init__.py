"""Small, standard-library-only G5 race/fence discriminator."""

from .simulator import (
    FENCE_MODES,
    OWNER_NAMES,
    STRATEGIES,
    RacePlan,
    SimulationConfig,
    SimulationHarness,
    run_fence_probe,
)

__all__ = [
    "FENCE_MODES",
    "OWNER_NAMES",
    "STRATEGIES",
    "RacePlan",
    "SimulationConfig",
    "SimulationHarness",
    "run_fence_probe",
]
