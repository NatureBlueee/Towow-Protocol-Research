from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from .model import Proposal
from .session import ActionSession


class Worker(Protocol):
    name: str

    def run(self, session: ActionSession) -> None: ...


def proposal_from(public: dict, path_id: str) -> Proposal:
    return Proposal(
        path_id=path_id,
        target=public["target"],
        quality_floor=public["quality_floor"],
        necessary_principals=tuple(public["necessary_principals"]),
    )


@dataclass(frozen=True)
class PublicIndexWorker:
    name: str = "PUBLIC_INDEX"

    def run(self, session: ActionSession) -> None:
        public = session.observe_public()
        if not public["public_index"]:
            session.trace.notes.append("no_public_index_candidate")
            return
        item = public["public_index"][0]
        session.submit_proposal(
            Proposal(
                path_id=item["path_id"],
                target=item["target"],
                quality_floor=item["quality_floor"],
                necessary_principals=tuple(item["necessary_principals"]),
            ),
            "PUBLIC_INDEX",
        )


@dataclass(frozen=True)
class EqualAccessCenterWorker:
    """Central planner constrained to the common owner action envelope."""

    name: str = "C_EQUAL_ACCESS"

    def run(self, session: ActionSession) -> None:
        public = session.observe_public()
        if public["public_index"]:
            session.submit_proposal(
                proposal_from(public, public["public_index"][0]["path_id"]),
                "PUBLIC_INDEX",
            )
            return
        paths: list[str] = []
        claim = f"complement_for:{public['intent']['objective']}"
        for owner in public["owners"]:
            reply = session.ask(owner, claim)
            if reply.get("status") == "WITNESS":
                paths.append(reply["path_id"])
        if paths:
            path_id, _ = Counter(paths).most_common(1)[0]
            session.trace.cost.model_calls += 1
            session.submit_proposal(
                proposal_from(public, path_id), "ACTIVE_REVELATION"
            )


@dataclass(frozen=True)
class MatureCompositionWorker:
    """Evidence-first composition that can apply auditable owner operators."""

    name: str = "MATURE_COMPOSITION"

    def run(self, session: ActionSession) -> None:
        public = session.observe_public()
        path_ids: list[str] = []
        if public["public_index"]:
            path_ids.append(public["public_index"][0]["path_id"])
        claim = f"complement_for:{public['intent']['objective']}"
        for owner in public["owners"]:
            reply = session.ask(owner, claim)
            if reply.get("status") == "WITNESS":
                path_ids.append(reply["path_id"])
        for operator_id in session.available_operator_ids:
            reply = session.apply_operator(operator_id)
            if reply.get("path_id"):
                path_ids.append(reply["path_id"])
        if path_ids:
            path_id, _ = Counter(path_ids).most_common(1)[0]
            session.trace.cost.model_calls += 1
            session.submit_proposal(
                proposal_from(public, path_id), "MATURE_COMPOSITION"
            )


@dataclass(frozen=True)
class HumanEnvelopeWorker:
    """Scripted human-broker proxy using the same owners/actions/deadline."""

    name: str = "H_EQUAL_ENVELOPE"

    def run(self, session: ActionSession) -> None:
        public = session.observe_public()
        path_ids: list[str] = []
        broad_claim = f"what_path_supports:{public['intent']['objective']}"
        for owner in public["owners"]:
            session.trace.cost.human_minutes += 4
            reply = session.ask(owner, broad_claim)
            if reply.get("status") == "WITNESS":
                path_ids.append(reply["path_id"])
        for operator_id in session.available_operator_ids:
            session.trace.cost.human_minutes += 3
            reply = session.apply_operator(operator_id)
            if reply.get("path_id"):
                path_ids.append(reply["path_id"])
        if path_ids:
            session.submit_proposal(
                proposal_from(public, Counter(path_ids).most_common(1)[0][0]),
                "HUMAN_HYPOTHESIS",
            )


@dataclass(frozen=True)
class RawUpperWorker:
    """Legal raw-information upper bound, not a fair equal-access arm."""

    name: str = "C_RAW_UPPER"

    def run(self, session: ActionSession) -> None:
        public = session.observe_public()
        raw = session.raw_snapshot()
        if raw.get("status") != "RAW" or raw.get("path_id") is None:
            session.trace.notes.append(raw.get("status", "RAW_UNKNOWN"))
            return
        session.submit_proposal(
            proposal_from(public, raw["path_id"]), "RAW_TRUTH_UPPER_BOUND"
        )


WORKERS: tuple[Worker, ...] = (
    PublicIndexWorker(),
    EqualAccessCenterWorker(),
    MatureCompositionWorker(),
    HumanEnvelopeWorker(),
    RawUpperWorker(),
)

WORKER_BY_NAME = {worker.name: worker for worker in WORKERS}

