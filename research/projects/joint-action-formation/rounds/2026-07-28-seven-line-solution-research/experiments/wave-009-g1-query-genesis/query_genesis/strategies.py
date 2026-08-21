"""Seven capability-parity candidates over the semantic request gateway.

No hidden-world or evaluator module is imported here.
"""

from __future__ import annotations

from typing import Any

from .evidence import QueryDraft
from .spec import CAPABILITIES


def _state_from_authority_status(status: str) -> str:
    return {
        "AUTHORITY_TIMEOUT": "UNKNOWN",
        "AUTHORITY_SIGNED_REFUSAL": "UNWILLING_TO_DISCLOSE",
        "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION": "ABSENT",
    }.get(status, "UNKNOWN")


def _form_candidate_query(gateway: Any):
    seed_response = gateway.observe_goal_seed()
    seed = seed_response.seed
    clarifications = []
    for facet in ("PURPOSE", "DIRECTION", "CONSTRAINTS", "VERSION"):
        response = gateway.request_principal_clarification(seed, facet)
        if response.clarification is None:
            return None, response.status
        clarifications.append(response.clarification)
    values = {item.facet: item.value for item in clarifications}
    draft = QueryDraft(
        origin=seed.origin,
        purpose=values["PURPOSE"],
        direction=values["DIRECTION"],
        constraints=tuple(values["CONSTRAINTS"]),
        version=values["VERSION"],
        provenance="SYNTHETIC_PRINCIPAL_CLARIFICATION",
    )
    formed = gateway.form_query(seed, tuple(clarifications), draft)
    return formed.query, formed.status


class ExpressedIndexARD:
    strategy_id = "expressed_index_ard"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        direct = gateway.platform_direct()
        if direct.status != "PLATFORM_NOT_APPLICABLE":
            return {"terminal": direct.status, "method": "ard_platform_bypass"}
        query, genesis_status = _form_candidate_query(gateway)
        if query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "current_ard"}
        direction = gateway.search_index(query)
        if direction.candidate_ref:
            current = gateway.read_current_head(direction.candidate_ref)
            if current.status == "CURRENT_COMPAT" and current.ref:
                receipt = gateway.handoff((current.ref,))
                terminal = (
                    "EXPRESSED_INDEX_HANDOFF"
                    if receipt.status == "CANDIDATE_NOT_COMMITMENT"
                    else "REVOKED"
                )
                gateway.stop(terminal)
                return {"terminal": receipt.status, "method": "current_ard"}
            if current.status == "REVOKED":
                gateway.stop("REVOKED")
                return {"terminal": "REVOKED", "method": "current_ard"}
        gateway.stop("UNKNOWN")
        return {"terminal": "UNKNOWN", "method": "current_ard"}


class LocalProjection:
    strategy_id = "local_projection"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        platform = gateway.platform_direct()
        if platform.status in {"PLATFORM_COMPLETED", "PLATFORM_NO_MATCH"}:
            return {"terminal": platform.status, "method": "local_platform_bypass"}
        query, genesis_status = _form_candidate_query(gateway)
        if query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "authority_evidence"}
        observed = gateway.poll_local_trigger(query, "STANDARD")
        if observed.status == "LOCAL_FACT_TRIGGER":
            projection = gateway.emit_projection(observed.ref)
            receipt = gateway.handoff((projection.ref,))
            gateway.stop("UNEXPRESSED")
            return {"terminal": receipt.status, "method": "semantic_local_projection"}
        state = _state_from_authority_status(observed.status)
        gateway.stop(state)
        return {"terminal": state, "method": "authority_evidence"}


class StrongCenterLocalOracle:
    strategy_id = "strong_center_local_oracle"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        platform = gateway.platform_direct()
        if platform.status != "PLATFORM_NOT_APPLICABLE":
            return {"terminal": platform.status, "method": "optimized_center"}
        semantic_query, genesis_status = _form_candidate_query(gateway)
        if semantic_query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "optimized_center"}
        indexed = gateway.search_index(semantic_query)
        if indexed.candidate_ref:
            head = gateway.read_current_head(indexed.candidate_ref)
            if head.status == "CURRENT_COMPAT" and head.ref:
                handoff = gateway.handoff((head.ref,))
                boundary = (
                    "EXPRESSED_INDEX_HANDOFF"
                    if handoff.status == "CANDIDATE_NOT_COMMITMENT"
                    else "REVOKED"
                )
                gateway.stop(boundary)
                return {"terminal": handoff.status, "method": "optimized_center"}
            if head.status == "CURRENT_COARSE":
                probe = gateway.request_probe(indexed.candidate_ref)
                if probe.status == "RECIPROCAL_MATCH":
                    handoff = gateway.handoff((probe.ref,))
                    gateway.stop("RECIPROCAL_HANDOFF")
                    return {"terminal": handoff.status, "method": "optimized_center"}
                if probe.status == "RECIPROCAL_SIGNED_REFUSAL":
                    gateway.stop("UNWILLING_TO_DISCLOSE")
                    return {"terminal": probe.status, "method": "optimized_center"}
        local = gateway.poll_local_trigger(semantic_query, "STANDARD")
        if local.status == "LOCAL_FACT_TRIGGER":
            projection = gateway.emit_projection(local.ref)
            handoff = gateway.handoff((projection.ref,))
            gateway.stop("UNEXPRESSED")
            return {"terminal": handoff.status, "method": "optimized_center"}
        if local.status in {
            "AUTHORITY_TIMEOUT",
            "AUTHORITY_SIGNED_REFUSAL",
            "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
        }:
            boundary = _state_from_authority_status(local.status)
            gateway.stop(boundary)
            return {"terminal": boundary, "method": "optimized_center"}
        predicate = gateway.private_match(semantic_query)
        if predicate.status == "PRIVATE_MATCH":
            handoff = gateway.handoff((predicate.ref,))
            gateway.stop("PRIVATE_PREDICATE_HANDOFF")
            return {"terminal": handoff.status, "method": "optimized_center"}
        raw = gateway.poll_local_trigger(semantic_query, "CENTER_RAW")
        if raw.status == "RAW_FACT_TRIGGER":
            projection = gateway.emit_projection(raw.ref)
            handoff = gateway.handoff((projection.ref,))
            gateway.stop("RAW_CENTER_HANDOFF")
            return {"terminal": handoff.status, "method": "optimized_center"}
        oracle = gateway.poll_local_trigger(semantic_query, "LOCAL_ORACLE")
        if oracle.status == "ORACLE_FACT_TRIGGER":
            projection = gateway.emit_projection(oracle.ref)
            handoff = gateway.handoff((projection.ref,))
            gateway.stop("LOCAL_ORACLE_HANDOFF")
            return {"terminal": handoff.status, "method": "optimized_center"}
        gateway.stop("UNKNOWN")
        return {"terminal": "UNKNOWN", "method": "optimized_center"}


class PrivacyPredicateProvider:
    strategy_id = "privacy_predicate_provider"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        direct = gateway.platform_direct()
        if direct.status != "PLATFORM_NOT_APPLICABLE":
            return {"terminal": direct.status, "method": "predicate_platform_bypass"}
        semantic_query, genesis_status = _form_candidate_query(gateway)
        if semantic_query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "private_predicate"}
        witness = gateway.private_match(semantic_query)
        if witness.status == "PRIVATE_MATCH":
            receipt = gateway.handoff((witness.ref,))
            gateway.stop("PRIVATE_PREDICATE_HANDOFF")
            return {"terminal": receipt.status, "method": "private_predicate"}
        gateway.stop("UNKNOWN")
        return {"terminal": "UNKNOWN", "method": "private_predicate"}


class ReciprocalProbe:
    strategy_id = "reciprocal_probe"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        direct = gateway.platform_direct()
        if direct.status in {"PLATFORM_COMPLETED", "PLATFORM_NO_MATCH"}:
            return {"terminal": direct.status, "method": "probe_platform_bypass"}
        query, genesis_status = _form_candidate_query(gateway)
        if query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "reciprocal_probe"}
        candidate = gateway.search_index(query)
        if candidate.status == "COARSE_CANDIDATE" and candidate.candidate_ref:
            gateway.read_current_head(candidate.candidate_ref)
            response = gateway.request_probe(candidate.candidate_ref)
            if response.status == "RECIPROCAL_MATCH":
                receipt = gateway.handoff((response.ref,))
                gateway.stop("RECIPROCAL_HANDOFF")
                return {"terminal": receipt.status, "method": "reciprocal_probe"}
            if response.status == "RECIPROCAL_SIGNED_REFUSAL":
                gateway.stop("UNWILLING_TO_DISCLOSE")
                return {"terminal": response.status, "method": "reciprocal_probe"}
        gateway.stop("UNKNOWN")
        return {"terminal": "UNKNOWN", "method": "reciprocal_probe"}


class RouterComposition:
    strategy_id = "router_composition"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        direct_result = gateway.platform_direct()
        if direct_result.status != "PLATFORM_NOT_APPLICABLE":
            return {"terminal": direct_result.status, "method": "optimized_router"}
        task_query, genesis_status = _form_candidate_query(gateway)
        if task_query is None:
            gateway.stop("QUERY_NOT_FORMED")
            return {"terminal": genesis_status, "method": "optimized_router"}
        directory_result = gateway.search_index(task_query)
        if directory_result.candidate_ref:
            current_result = gateway.read_current_head(directory_result.candidate_ref)
            if current_result.status == "CURRENT_COMPAT" and current_result.ref:
                routed_result = gateway.handoff((current_result.ref,))
                stop_state = (
                    "EXPRESSED_INDEX_HANDOFF"
                    if routed_result.status == "CANDIDATE_NOT_COMMITMENT"
                    else "REVOKED"
                )
                gateway.stop(stop_state)
                return {"terminal": routed_result.status, "method": "optimized_router"}
            if current_result.status == "CURRENT_COARSE":
                reciprocal_result = gateway.request_probe(directory_result.candidate_ref)
                if reciprocal_result.status == "RECIPROCAL_MATCH":
                    routed_result = gateway.handoff((reciprocal_result.ref,))
                    gateway.stop("RECIPROCAL_HANDOFF")
                    return {"terminal": routed_result.status, "method": "optimized_router"}
                if reciprocal_result.status == "RECIPROCAL_SIGNED_REFUSAL":
                    gateway.stop("UNWILLING_TO_DISCLOSE")
                    return {"terminal": reciprocal_result.status, "method": "optimized_router"}
        local_result = gateway.poll_local_trigger(task_query, "STANDARD")
        if local_result.status == "LOCAL_FACT_TRIGGER":
            projection_result = gateway.emit_projection(local_result.ref)
            routed_result = gateway.handoff((projection_result.ref,))
            gateway.stop("UNEXPRESSED")
            return {"terminal": routed_result.status, "method": "optimized_router"}
        if local_result.status in {
            "AUTHORITY_TIMEOUT",
            "AUTHORITY_SIGNED_REFUSAL",
            "CLOSED_COMPLETENESS_PLUS_NEGATIVE_ATTESTATION",
        }:
            stop_state = _state_from_authority_status(local_result.status)
            gateway.stop(stop_state)
            return {"terminal": stop_state, "method": "optimized_router"}
        private_result = gateway.private_match(task_query)
        if private_result.status == "PRIVATE_MATCH":
            routed_result = gateway.handoff((private_result.ref,))
            gateway.stop("PRIVATE_PREDICATE_HANDOFF")
            return {"terminal": routed_result.status, "method": "optimized_router"}
        raw_result = gateway.poll_local_trigger(task_query, "CENTER_RAW")
        if raw_result.status == "RAW_FACT_TRIGGER":
            projection_result = gateway.emit_projection(raw_result.ref)
            routed_result = gateway.handoff((projection_result.ref,))
            gateway.stop("RAW_CENTER_HANDOFF")
            return {"terminal": routed_result.status, "method": "optimized_router"}
        oracle_result = gateway.poll_local_trigger(task_query, "LOCAL_ORACLE")
        if oracle_result.status == "ORACLE_FACT_TRIGGER":
            projection_result = gateway.emit_projection(oracle_result.ref)
            routed_result = gateway.handoff((projection_result.ref,))
            gateway.stop("LOCAL_ORACLE_HANDOFF")
            return {"terminal": routed_result.status, "method": "optimized_router"}
        gateway.stop("UNKNOWN")
        return {"terminal": "UNKNOWN", "method": "optimized_router"}


class PlatformDirectControl:
    strategy_id = "platform_direct_control"
    capabilities = CAPABILITIES

    @staticmethod
    def run(gateway: Any) -> dict[str, Any]:
        platform = gateway.platform_direct()
        if platform.status == "PLATFORM_COMPLETED":
            return {"terminal": platform.status, "method": "canonical_platform"}
        if platform.status == "PLATFORM_NO_MATCH":
            return {"terminal": platform.status, "method": "canonical_platform"}
        gateway.stop("NOT_APPLICABLE")
        return {"terminal": "NOT_APPLICABLE", "method": "canonical_platform"}
