from __future__ import annotations

from collections import defaultdict
from typing import Any

from .fixtures import World
from .model import (
    EvidenceEvent,
    SYNTHETIC_OWNER_SOURCE,
    Trace,
    digest,
    serialize,
)


T0_INTERVENTIONS = {"T0_REPLAY", "FAILURE_INJECTION"}
REQUIRED_KINDS = {"candidate", "resource", "partner"}
REQUIRED_AUTHORITIES = {"O_R", "O_V"}
LINE_ENVELOPE_FORBIDDEN_TERMS = {
    "relation",
    "authority",
    "effect",
    "acceptance",
    "settlement",
}
def _line_envelope_tokens(value: str) -> set[str]:
    return {
        token
        for token in value.casefold().replace("-", "_").split("_")
        if token
    }


def line_local_envelope_violations(
    value: Any,
    *,
    path: str = "$",
) -> list[str]:
    """Reject cross-line/contract claims from the exported G1 envelope.

    Identifiers such as the frozen E3A episode name remain opaque identifiers;
    exact forbidden claim values and claim-shaped keys are rejected.
    """

    violations: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            folded = str(key).casefold()
            tokens = _line_envelope_tokens(folded)
            if (
                "contract" in tokens
                or "success" in tokens
                or tokens & LINE_ENVELOPE_FORBIDDEN_TERMS
            ):
                violations.append(f"{path}.{key}:forbidden_key")
            violations.extend(
                line_local_envelope_violations(
                    nested,
                    path=f"{path}.{key}",
                )
            )
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            violations.extend(
                line_local_envelope_violations(
                    nested,
                    path=f"{path}[{index}]",
                )
            )
    elif isinstance(value, str):
        normalized = value.strip().casefold()
        tokens = _line_envelope_tokens(normalized)
        if (
            "contract" in tokens
            or "success" in tokens
            or tokens & LINE_ENVELOPE_FORBIDDEN_TERMS
        ):
            violations.append(f"{path}:forbidden_value")
    return sorted(set(violations))


def _invalidity_gate(world: World, trace: Trace) -> list[str]:
    failures: list[str] = []
    proposal = trace.proposal
    interface = world.interface
    if trace.intent_boundary != "IntentAtCoordinationInterface":
        failures.append("INTENT_BOUNDARY_VIOLATION")
    if (
        digest(world.prelude)
        != interface["clarification_prelude_receipt_hash"]
        or trace.prelude_receipt_hash
        != interface["clarification_prelude_receipt_hash"]
    ):
        failures.append("PRELUDE_LINEAGE_MISMATCH")
    expected_predicates = {
        "q_version": interface["q_version"],
        "object_id": interface["object_id"],
        "deadline": interface["constraints"]["deadline"],
        "power_kw": interface["constraints"]["power_kw"],
        "exact_target_only": interface["constraints"]["exact_target_only"],
    }
    discovery_api = interface["discovery_api"]
    if (
        len(trace.queries) > discovery_api["max_queries"]
        or any(
            query.get("kind") not in discovery_api["query_kinds"]
            or query.get("predicates") != expected_predicates
            for query in trace.queries
        )
    ):
        failures.append("ACTION_ENVELOPE_BREACH")
    if proposal is None:
        return sorted(set(failures))
    if proposal.status != "CANDIDATE_NOT_COMMITMENT":
        failures.append("G1_STATUS_OVERPROMOTION")
    for field in ("episode_id", "q_version", "object_id", "operation_id"):
        if getattr(proposal, field) != interface[field]:
            failures.append(f"{field.upper()}_DRIFT")
    observed = {event.evidence_id: event for event in trace.evidence}
    selected: list[EvidenceEvent] = []
    for evidence_id in proposal.evidence_ids:
        event = observed.get(evidence_id)
        expected = world.expected.get(evidence_id)
        if event is None or expected is None:
            failures.append("UNKNOWN_OR_UNOBSERVED_EVIDENCE")
            continue
        selected.append(event)
        if digest(event.hash_payload()) != event.evidence_hash:
            failures.append("EVIDENCE_HASH_MISMATCH")
        if event.episode_id != trace.episode_id:
            failures.append("TRUTH_TRANSPLANT")
        if event.issuer_id != expected["issuer_id"]:
            failures.append("WRONG_ISSUER")
        if event.candidate_id != expected["candidate_id"]:
            failures.append("EVIDENCE_CANDIDATE_MISMATCH")
        if event.subject_id != expected["subject_id"]:
            failures.append("EVIDENCE_SUBJECT_MISMATCH")
        expected_authority = world.authority_aliases.get(
            expected["authority_id"], expected["authority_id"]
        )
        actual_authority = world.authority_aliases.get(
            event.authority_id, event.authority_id
        )
        if actual_authority != expected_authority:
            failures.append("WRONG_AUTHORITY")
        expected_source = world.source_aliases.get(
            expected["source_id"], expected["source_id"]
        )
        actual_source = world.source_aliases.get(
            event.source_id, event.source_id
        )
        if actual_source != expected_source:
            failures.append("WRONG_SOURCE")
        if not event.disclosure_allowed or not expected["disclosure_allowed"]:
            failures.append("FORBIDDEN_DISCLOSURE")
        if (
            event.recipient_id != expected["recipient_id"]
            or event.purpose != interface["discovery_api"]["purpose"]
            or event.purpose != expected["purpose"]
            or event.scope_version != proposal.q_version
            or event.scope_version != expected["scope_version"]
        ):
            failures.append("DISCLOSURE_SCOPE_MISMATCH")
        if not event.current or not expected["current"]:
            failures.append("REVOKED_EVIDENCE")
        if trace.intervention in T0_INTERVENTIONS and (
            event.observed_at != "t0" or not event.existed_at_t0
        ):
            failures.append("POST_TREATMENT_EVIDENCE_IN_T0_REPLAY")
        if event.payload.get("q_version") != proposal.q_version:
            failures.append("EVIDENCE_Q_DRIFT")
        if event.payload.get("object_id") != proposal.object_id:
            failures.append("EVIDENCE_OBJECT_DRIFT")
        if event.candidate_id != proposal.candidate_id:
            failures.append("CANDIDATE_BINDING_MISMATCH")

    kinds = {event.kind for event in selected}
    if not REQUIRED_KINDS.issubset(kinds):
        failures.append("MISSING_EVIDENCE_KIND")
    subject_by_kind: dict[str, set[str]] = defaultdict(set)
    for event in selected:
        subject_by_kind[event.kind].add(event.subject_id)
    if proposal.resource_id not in subject_by_kind["resource"]:
        failures.append("RESOURCE_BINDING_MISMATCH")
    if proposal.partner_id not in subject_by_kind["partner"]:
        failures.append("PARTNER_BINDING_MISMATCH")

    authority_roots = {
        world.authority_aliases.get(event.authority_id, event.authority_id)
        for event in selected
    }
    if not REQUIRED_AUTHORITIES.issubset(authority_roots):
        failures.append("AUTHORITY_ROOT_COVERAGE")
    source_roots = {
        world.source_aliases.get(event.source_id, event.source_id)
        for event in selected
    }
    if len(source_roots) < world.min_unique_sources:
        failures.append("SAME_SOURCE_ALIAS")
    return sorted(set(failures))


def evaluate_trace(world: World, trace: Trace) -> dict[str, Any]:
    failures = _invalidity_gate(world, trace)
    selected_candidate = trace.proposal.candidate_id if trace.proposal else None
    in_frozen_population = bool(
        trace.proposal is not None
        and selected_candidate in world.l_benchmark
    )
    eligible = bool(
        trace.proposal is not None
        and not failures
        and in_frozen_population
        and (
            selected_candidate in world.d_actual
            or trace.intervention == "FULL_ACTUAL_TRACE"
        )
    )
    if failures:
        boundary = "INVALID"
    elif trace.proposal is not None and not in_frozen_population:
        boundary = "NOVEL_CANDIDATE_FOR_NEXT_VERSION"
    elif eligible:
        boundary = "QUALIFIED_CANDIDATE"
    elif trace.refusals:
        boundary = "REFUSED_OR_UNAVAILABLE"
    else:
        boundary = "UNKNOWN"

    operator_types = {event.operator_type for event in trace.operators}
    selected_evidence = (
        [
            event
            for event in trace.evidence
            if event.evidence_id in trace.proposal.evidence_ids
        ]
        if trace.proposal
        else []
    )
    qualification_source_roots = sorted(
        {
            world.source_aliases.get(event.source_id, event.source_id)
            for event in selected_evidence
        }
    )
    candidate_source_roots = sorted(
        {
            world.source_aliases.get(event.source_id, event.source_id)
            for event in selected_evidence
            if event.kind == "candidate"
        }
    )
    authority_roots = sorted(
        {
            world.authority_aliases.get(event.authority_id, event.authority_id)
            for event in selected_evidence
        }
    )
    event_vector = {
        "candidate_sources": candidate_source_roots,
        "qualification_sources": qualification_source_roots,
        "authority_roots": authority_roots,
        "fact_existed_at_t0": bool(world.l_benchmark),
        "legal_evidence_path_existed_at_t0": bool(world.d_actual),
        "qualification_created": bool(
            eligible
            and any(
                event.observed_at != "t0" or not event.existed_at_t0
                for event in selected_evidence
            )
        ),
        "partner_discovery_changed": "PARTNER_DISCLOSURE_FORMATION" in operator_types,
        "resource_discovery_changed": "RESOURCE_DISCOVERY" in operator_types,
        "authority_changed": "AUTHORITY_FORMATION" in operator_types,
        "capability_changed": "CAPABILITY_FORMATION" in operator_types,
        "understanding_changed": False,
        "terms_changed": False,
        "relation_state_changed": False,
        "claimability_changed": bool(operator_types),
    }
    raw_trace = serialize(trace)
    handoff = {
        "schema_version": "ce001-g1-handoff-v1",
        "line": "G1",
        "episode_id": trace.episode_id,
        "Q_version": world.interface["q_version"],
        "object_id": world.interface["object_id"],
        "operation_id": world.interface["operation_id"],
        "status": (
            "CANDIDATE_NOT_COMMITMENT"
            if boundary == "QUALIFIED_CANDIDATE"
            else boundary
        ),
        "owner_ids": list(trace.proposal.owner_ids) if trace.proposal else [],
        "candidate_id": selected_candidate,
        "resource_id": trace.proposal.resource_id if trace.proposal else None,
        "partner_id": trace.proposal.partner_id if trace.proposal else None,
        "evidence": [
            {
                "evidence_id": event.evidence_id,
                "evidence_hash": event.evidence_hash,
                "kind": event.kind,
                "subject_id": event.subject_id,
                "owner_id": event.issuer_id,
                "issuer_id": event.issuer_id,
                "source_id": event.source_id,
                "authority_id": event.authority_id,
                "recipient_id": event.recipient_id,
                "purpose": event.purpose,
                "scope_version": event.scope_version,
                "observed_at": event.observed_at,
                "owner_request_hash": event.request_hash,
                "owner_state_version": event.owner_state_version,
                "owner_service_pid": event.origin_process_id,
                "owner_source_type": event.owner_source_type,
                "owner_source_instance_id": event.owner_source_instance_id,
                "owner_state_instance_id": event.owner_state_instance_id,
                "owner_process_instance_id": event.owner_process_instance_id,
            }
            for event in selected_evidence
        ],
        "event_vector": event_vector,
        "invalidity_reasons": failures,
        "frozen_population": {
            "member": in_frozen_population,
            "disposition": (
                "IN_SCOPE"
                if in_frozen_population
                else "PRESERVE_AS_NEXT_VERSION_CANDIDATE"
            ),
        },
        "explicit_non_claims": [
            "RELATION",
            "COMMITMENT",
            "AUTHORITY",
            "EFFECT",
            "ACCEPTANCE",
            "SETTLEMENT",
        ],
        "raw_trace_sha256": digest(raw_trace),
    }
    handoff["output_hash"] = digest(handoff)
    line_envelope = {
        "schema_version": "towow-g1-provenance-line-envelope-v2",
        "g1_namespace": "G1_PROVENANCE",
        "g1_episode_ref_sha256": digest({"episode_id": trace.episode_id}),
        "g1_q_version": world.interface["q_version"],
        "g1_object_id": world.interface["object_id"],
        "g1_operation_id": world.interface["operation_id"],
        "g1_status": handoff["status"],
        "g1_candidate_id": selected_candidate,
        "g1_resource_id": trace.proposal.resource_id if trace.proposal else None,
        "g1_partner_id": trace.proposal.partner_id if trace.proposal else None,
        "g1_owner_fixture_class": SYNTHETIC_OWNER_SOURCE,
        "g1_real_owner_truth": "NOT_ESTABLISHED",
        "g1_real_owner_origin": "NOT_ESTABLISHED",
        "g1_evidence": [
            {
                "g1_evidence_id": event.evidence_id,
                "g1_evidence_hash": event.evidence_hash,
                "g1_kind": event.kind,
                "g1_subject_id": event.subject_id,
                "g1_owner_id": event.issuer_id,
                "g1_source_id": event.source_id,
                "g1_owner_request_hash": event.request_hash,
                "g1_owner_state_version": event.owner_state_version,
                "g1_owner_process_id": event.origin_process_id,
                "g1_owner_source_instance_id": (
                    event.owner_source_instance_id
                ),
                "g1_owner_state_instance_id": (
                    event.owner_state_instance_id
                ),
                "g1_owner_process_instance_id": (
                    event.owner_process_instance_id
                ),
            }
            for event in selected_evidence
        ],
        "g1_invalidity_count": len(failures),
        "g1_invalidity_digest": digest(failures),
        "g1_population_disposition": handoff["frozen_population"]["disposition"],
        "g1_raw_trace_sha256": digest(raw_trace),
        "g1_scope": "LINE_LOCAL_CANDIDATE_PROVENANCE_ONLY",
    }
    violations = line_local_envelope_violations(line_envelope)
    if violations:
        raise ValueError(f"G1 line envelope contains forbidden claims: {violations}")
    line_envelope["g1_output_hash"] = digest(line_envelope)
    return {
        "episode_id": trace.episode_id,
        "intervention": trace.intervention,
        "boundary": boundary,
        "eligible_positive": eligible,
        "in_frozen_population": in_frozen_population,
        "invalidity_first_gate": {
            "passed": not failures,
            "failures": failures,
        },
        "L_benchmark": list(world.l_benchmark),
        "D_actual": list(world.d_actual),
        "event_vector": event_vector,
        "g1_handoff": handoff,
        "g1_line_envelope": line_envelope,
        "raw_trace": raw_trace,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    l_denominator = sum(len(result["L_benchmark"]) for result in results)
    d_denominator = sum(len(result["D_actual"]) for result in results)
    qualified = {
        (result["episode_id"], result["g1_handoff"]["candidate_id"])
        for result in results
        if result["eligible_positive"]
    }
    l_hits = sum(
        (result["episode_id"], candidate_id) in qualified
        for result in results
        for candidate_id in result["L_benchmark"]
    )
    d_hits = sum(
        (result["episode_id"], candidate_id) in qualified
        for result in results
        for candidate_id in result["D_actual"]
    )
    return {
        "L_benchmark": {
            "denominator": l_denominator,
            "discovered": l_hits,
            "recall": l_hits / l_denominator if l_denominator else None,
        },
        "D_actual": {
            "denominator": d_denominator,
            "discovered": d_hits,
            "recall": d_hits / d_denominator if d_denominator else None,
        },
        "invalid": sum(result["boundary"] == "INVALID" for result in results),
        "qualified": sum(
            result["boundary"] == "QUALIFIED_CANDIDATE" for result in results
        ),
        "refused_or_unknown_not_actual_miss": sum(
            not result["D_actual"]
            and result["boundary"] in {"REFUSED_OR_UNAVAILABLE", "UNKNOWN"}
            for result in results
        ),
    }
