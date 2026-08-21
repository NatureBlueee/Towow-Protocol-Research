"""CE-001 G1 provenance component."""

from .evaluator import evaluate_trace, summarize
from .fixtures import EPISODE_IDS, make_world
from .method import EvidenceFirstDiscovery
from .runner import build_report, run_episode

__all__ = [
    "EPISODE_IDS",
    "EvidenceFirstDiscovery",
    "build_report",
    "evaluate_trace",
    "make_world",
    "run_episode",
    "summarize",
]
