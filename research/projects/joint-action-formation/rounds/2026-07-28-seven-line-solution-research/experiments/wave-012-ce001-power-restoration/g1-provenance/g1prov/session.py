from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Any

from .fixtures import World
from .model import (
    CandidateProposal,
    EvidenceEvent,
    OperatorEvent,
    Trace,
    digest,
)


class DiscoverySession:
    """Method-facing session.

    The worker receives this object, not the World. Private expected records,
    denominators, and operator truth stay controller-side.
    """

    def __init__(
        self,
        world: World,
        trace: Trace,
        *,
        allow_t0_queries: bool,
        allow_operators: bool,
        removed_operator: str | None = None,
        reversed_operator: str | None = None,
        failure_injection: str | None = None,
    ) -> None:
        self._world = world
        self._trace = trace
        self._allow_t0_queries = allow_t0_queries
        self._allow_operators = allow_operators
        self._removed_operator = removed_operator
        self._reversed_operator = reversed_operator
        self._failure_injection = failure_injection
        self._active_records = list(deepcopy(world.records))

    @property
    def trace(self) -> Trace:
        return self._trace

    def observe_interface(self) -> dict[str, Any]:
        self._trace.cost.interface_reads += 1
        interface = deepcopy(self._world.interface)
        self._trace.intent_boundary = interface["boundary"]
        self._trace.prelude_receipt_hash = interface[
            "clarification_prelude_receipt_hash"
        ]
        return interface

    def discover(
        self,
        kind: str,
        predicates: dict[str, Any],
    ) -> list[EvidenceEvent]:
        self._trace.cost.owner_queries += 1
        self._trace.queries.append(
            {"kind": kind, "predicates": deepcopy(predicates)}
        )
        api = self._world.interface["discovery_api"]
        if (
            kind not in api["query_kinds"]
            or len(self._trace.queries) > api["max_queries"]
        ):
            self._trace.notes.append(f"query_outside_envelope:{kind}")
            return []
        expected_predicates = {
            "q_version": self._world.interface["q_version"],
            "object_id": self._world.interface["object_id"],
            "deadline": self._world.interface["constraints"]["deadline"],
            "power_kw": self._world.interface["constraints"]["power_kw"],
            "exact_target_only": self._world.interface["constraints"][
                "exact_target_only"
            ],
        }
        if predicates != expected_predicates:
            self._trace.notes.append(f"query_scope_mismatch:{kind}")
            return []
        if not self._allow_t0_queries:
            self._trace.notes.append(f"query_blocked:{kind}")
            return []
        records = [
            record
            for record in self._active_records
            if record["kind"] == kind
            and record["payload"].get("q_version") == predicates["q_version"]
            and record["payload"].get("object_id") == predicates["object_id"]
        ]
        events: list[EvidenceEvent] = []
        for record in records:
            if record["response"] == "REFUSED" or not record["disclosure_allowed"]:
                self._trace.refusals.append(
                    {
                        "kind": kind,
                        "issuer_id": record["issuer_id"],
                        "status": (
                            "REFUSED"
                            if record["response"] == "REFUSED"
                            else "DISCLOSURE_NOT_ALLOWED"
                        ),
                    }
                )
                continue
            event = self._issue(record)
            events.append(event)
            self._trace.evidence.append(event)
        self._trace.cost.evidence_items += len(events)
        self._trace.cost.disclosure_units += len(events)
        return deepcopy(events)

    def _issue(self, record: dict[str, Any]) -> EvidenceEvent:
        fields = {
            key: deepcopy(record[key])
            for key in (
                "evidence_id",
                "episode_id",
                "kind",
                "subject_id",
                "candidate_id",
                "issuer_id",
                "authority_id",
                "source_id",
                "recipient_id",
                "purpose",
                "scope_version",
                "observed_at",
                "existed_at_t0",
                "disclosure_allowed",
                "current",
                "payload",
                "via_operator",
            )
        }
        event = EvidenceEvent.issue(**fields)
        injection = self._failure_injection
        if injection == "WRONG_AUTHORITY" and event.kind == "partner":
            changed = event.hash_payload()
            changed["authority_id"] = "controller-admin"
            event = EvidenceEvent.issue(**changed)
        elif injection == "SOURCE_ALIAS" and event.kind == "partner":
            alias_id = "alias-of-resource-ledger"
            original_resource = next(
                (
                    item
                    for item in self._active_records
                    if item["kind"] == "resource"
                    and item["candidate_id"] == event.candidate_id
                ),
                None,
            )
            if original_resource is not None:
                self._world.source_aliases[alias_id] = original_resource["source_id"]
                changed = event.hash_payload()
                changed["source_id"] = alias_id
                event = EvidenceEvent.issue(**changed)
        elif injection == "TAMPER_PAYLOAD" and event.kind == "resource":
            payload = dict(event.payload)
            payload["object_id"] = "Venue-V:Circuit-C8"
            event = replace(event, payload=payload)
        elif injection == "TRUTH_TRANSPLANT" and event.kind == "candidate":
            changed = event.hash_payload()
            changed["episode_id"] = "E0-PLATFORM-DIRECT"
            event = EvidenceEvent.issue(**changed)
        return event

    def apply_operator(self, operator_id: str) -> dict[str, Any]:
        if not self._allow_operators:
            self._trace.notes.append(f"operator_blocked:{operator_id}")
            return {"status": "BLOCKED"}
        spec = next(
            (
                operator
                for operator in self._world.operators
                if operator["operator_id"] == operator_id
            ),
            None,
        )
        if spec is None:
            return {"status": "UNKNOWN_OPERATOR"}
        if operator_id == self._removed_operator:
            self._trace.notes.append(f"operator_removed:{operator_id}")
            return {"status": "REMOVED"}
        mode = "REVERSED" if operator_id == self._reversed_operator else "APPLIED"
        created = deepcopy(spec["created_record"])
        if mode == "REVERSED":
            created["current"] = False
            created["evidence_id"] += "-REVERSED"
            self._world.expected[created["evidence_id"]] = deepcopy(created)
            self._world.source_aliases[created["source_id"]] = created["source_id"]
        self._active_records.append(created)
        self._trace.operators.append(
            OperatorEvent(
                operator_id=operator_id,
                operator_type=spec["operator_type"],
                mode=mode,
                owner_id=spec["owner_id"],
                authority_id=spec["authority_id"],
                created_evidence_ids=(created["evidence_id"],),
            )
        )
        return {"status": mode}

    def submit(self, proposal: CandidateProposal) -> None:
        self._trace.proposal = deepcopy(proposal)

    @property
    def controller_operator_ids(self) -> tuple[str, ...]:
        return tuple(
            operator["operator_id"] for operator in self._world.operators
        )

    def visible_snapshot_digest(self) -> str:
        """Receipt over exactly what observe_interface may reveal."""
        return digest(self._world.interface)
