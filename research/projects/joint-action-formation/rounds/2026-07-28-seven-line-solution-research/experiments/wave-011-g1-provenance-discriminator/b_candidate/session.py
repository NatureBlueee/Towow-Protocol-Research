from __future__ import annotations

from copy import deepcopy
from typing import Any

from .model import EvidenceEvent, OperatorEvent, Proposal, Trace


class ActionSession:
    """The only view available to an arm.

    Private oracle truth remains in the runner. The session returns only
    observations reachable through the frozen action envelope.
    """

    def __init__(
        self,
        public_world: dict[str, Any],
        private_oracle: dict[str, Any],
        trace: Trace,
        *,
        allow_t0_queries: bool,
        allow_operators: bool,
        allow_raw: bool,
        removed_operator: str | None = None,
        reversed_operator: str | None = None,
    ) -> None:
        self._public = deepcopy(public_world)
        self._oracle = private_oracle
        self.trace = trace
        self._allow_t0_queries = allow_t0_queries
        self._allow_operators = allow_operators
        self._allow_raw = allow_raw
        self._removed_operator = removed_operator
        self._reversed_operator = reversed_operator

    def observe_public(self) -> dict[str, Any]:
        self.trace.cost.actions += 1
        return deepcopy(self._public)

    def ask(self, owner: str, claim: str) -> dict[str, Any]:
        self.trace.cost.actions += 1
        if not self._allow_t0_queries:
            return {"status": "BLOCKED_BY_INTERVENTION"}
        response = next(
            (
                item
                for item in self._oracle["t0_responses"]
                if item["owner"] == owner and claim in item["accepted_claims"]
            ),
            None,
        )
        if response is None:
            return {"status": "UNKNOWN"}
        if not response["allowed"]:
            refusal = {
                "owner": owner,
                "claim": claim,
                "status": "UNWILLING_TO_DISCLOSE",
            }
            self.trace.refusals.append(refusal)
            return deepcopy(refusal)
        event = EvidenceEvent(
            event_id=f"t0:{self.trace.world_id}:{len(self.trace.evidence)}",
            path_id=response["path_id"],
            source_id=response["source_id"],
            canonical_source=response["canonical_source"],
            authority_root=response["authority_root"],
            claim=claim,
            observed_at="t0",
            existed_at_t0=response["existed_at_t0"],
            legal_at_t0=True,
            recipient=self._public["action_envelope"]["recipient"],
            purpose=self._public["action_envelope"]["purpose"],
        )
        self.trace.evidence.append(event)
        self.trace.cost.disclosure_exposure += event.sensitivity
        return {
            "status": "WITNESS",
            "path_id": event.path_id,
            "authority_root": event.authority_root,
            "source_id": event.source_id,
        }

    def submit_proposal(self, proposal: Proposal, source: str) -> None:
        self.trace.cost.actions += 1
        self.trace.proposal = proposal
        if source not in self.trace.candidate_sources:
            self.trace.candidate_sources.append(source)

    def apply_operator(self, operator_id: str) -> dict[str, Any]:
        self.trace.cost.actions += 1
        if not self._allow_operators:
            return {"status": "BLOCKED_BY_INTERVENTION"}
        spec = next(
            (item for item in self._oracle["operators"] if item["id"] == operator_id),
            None,
        )
        if spec is None:
            return {"status": "UNKNOWN_OPERATOR"}
        if operator_id == self._removed_operator:
            self.trace.notes.append(f"removed:{operator_id}")
            return {"status": "REMOVED"}
        mode = "REVERSED" if operator_id == self._reversed_operator else "APPLIED"
        created: list[EvidenceEvent] = []
        evidence_spec = spec.get("creates_evidence")
        if evidence_spec is not None:
            created.append(
                EvidenceEvent(
                    event_id=f"t1:{self.trace.world_id}:{operator_id}",
                    path_id=self._oracle["canonical_proposal"]["path_id"],
                    source_id=evidence_spec["source_id"],
                    canonical_source=evidence_spec["canonical_source"],
                    authority_root=evidence_spec["authority_root"],
                    claim=evidence_spec["claim"],
                    observed_at="t1",
                    existed_at_t0=False,
                    legal_at_t0=False,
                    recipient=self._public["action_envelope"]["recipient"],
                    purpose=self._public["action_envelope"]["purpose"],
                )
            )
        event = OperatorEvent(
            operator_id=operator_id,
            operator_type=spec["type"],
            mode=mode,
            authority_root=spec["authority_root"],
            valid_authority=spec["valid_authority"],
            disclosure_legal=spec["disclosure_legal"],
            created_evidence=tuple(created),
        )
        self.trace.operators.append(event)
        self.trace.evidence.extend(created)
        if created:
            self.trace.cost.disclosure_exposure += sum(
                item.sensitivity for item in created
            )
        return {
            "status": mode,
            "operator_type": spec["type"],
            "path_id": (
                self._oracle["canonical_proposal"]["path_id"] if created else None
            ),
        }

    def raw_snapshot(self) -> dict[str, Any]:
        self.trace.cost.actions += 1
        if not self._allow_raw or not self._public["raw_centralization_allowed"]:
            return {"status": "RAW_ACCESS_NOT_AUTHORIZED"}
        self.trace.cost.raw_exposure += 10
        for response in self._oracle["t0_responses"]:
            if not response["allowed"]:
                continue
            event = EvidenceEvent(
                event_id=f"raw-t0:{self.trace.world_id}:{len(self.trace.evidence)}",
                path_id=response["path_id"],
                source_id=response["source_id"],
                canonical_source=response["canonical_source"],
                authority_root=response["authority_root"],
                claim="legal_raw_snapshot",
                observed_at="t0",
                existed_at_t0=response["existed_at_t0"],
                legal_at_t0=True,
                recipient=self._public["action_envelope"]["recipient"],
                purpose=self._public["action_envelope"]["purpose"],
                sensitivity=3,
            )
            self.trace.evidence.append(event)
            self.trace.cost.disclosure_exposure += event.sensitivity
        return {
            "status": "RAW",
            "path_id": self._oracle["canonical_proposal"]["path_id"]
            if self._oracle["fact_existed_at_t0"]
            else None,
        }

    @property
    def available_operator_ids(self) -> tuple[str, ...]:
        return tuple(self._public["available_operator_ids"])
