from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .model import CandidateProposal, EvidenceEvent
from .session import DiscoverySession


@dataclass(frozen=True)
class EvidenceFirstDiscovery:
    """A generic evidence-seeking method, not an arm comparison.

    It has no fixture/oracle imports and receives no correct-path or final
    proposal field. Candidate identifiers arise only from discovery responses.
    """

    name: str = "EVIDENCE_FIRST_DISCOVERY"

    def run(
        self,
        session: DiscoverySession,
    ) -> None:
        interface = session.observe_interface()
        if interface["boundary"] != "IntentAtCoordinationInterface":
            session.trace.notes.append("wrong_intent_boundary")
            return

        by_candidate: dict[str, dict[str, list[EvidenceEvent]]] = defaultdict(
            lambda: defaultdict(list)
        )
        predicates: dict[str, Any] = {
            "q_version": interface["q_version"],
            "object_id": interface["object_id"],
            "deadline": interface["constraints"]["deadline"],
            "power_kw": interface["constraints"]["power_kw"],
            "exact_target_only": interface["constraints"]["exact_target_only"],
        }
        for kind in interface["discovery_api"]["query_kinds"]:
            for event in session.discover(kind, predicates):
                by_candidate[event.candidate_id][kind].append(event)

        complete_ids = sorted(
            candidate_id
            for candidate_id, evidence_by_kind in by_candidate.items()
            if all(evidence_by_kind.get(kind) for kind in ("candidate", "resource", "partner"))
        )
        if not complete_ids:
            session.trace.notes.append(
                "refused_or_unknown"
                if session.trace.refusals
                else "no_complete_candidate"
            )
            return

        candidate_id = complete_ids[0]
        evidence_by_kind = by_candidate[candidate_id]
        candidate_event = evidence_by_kind["candidate"][0]
        resource_event = evidence_by_kind["resource"][0]
        partner_event = evidence_by_kind["partner"][0]
        evidence = (candidate_event, resource_event, partner_event)
        session.submit(
            CandidateProposal.synthesize(
                episode_id=interface["episode_id"],
                q_version=interface["q_version"],
                object_id=interface["object_id"],
                operation_id=interface["operation_id"],
                candidate_id=candidate_event.candidate_id,
                resource_id=resource_event.subject_id,
                partner_id=partner_event.subject_id,
                owner_ids=tuple(sorted({item.issuer_id for item in evidence})),
                evidence_ids=tuple(item.evidence_id for item in evidence),
            )
        )
