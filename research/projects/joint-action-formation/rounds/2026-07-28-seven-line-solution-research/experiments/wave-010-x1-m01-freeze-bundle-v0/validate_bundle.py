#!/usr/bin/env python3
"""Recompute the M01 freeze-bundle candidate bindings.

This validates research-package integrity and declared pair equality only. It
does not run or score an X1 method and does not make the pair scoreable.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
OUTCOME_CONTRACT = ROOT.parent.parent / "WAVE-010-X1-OUTCOME-CONTRACT-v0.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    bundle = load(ROOT / "bundle.json")
    certificate = load(ROOT / "certificates" / "bearing-delta.json")
    common = load(ROOT / "public" / "common-coordinate.json")

    manifest_paths = {item["path"] for item in bundle["content_manifest"]}
    package_json_paths = {
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.json")
        if path.name != "bundle.json"
    }
    check(
        manifest_paths == package_json_paths,
        "content manifest does not bind every package JSON file exactly once",
    )
    for item in bundle["content_manifest"]:
        path = ROOT / item["path"]
        check(path.is_file(), f"missing manifest file: {item['path']}")
        check(
            raw_sha256(path) == item["raw_sha256"],
            f"raw hash mismatch: {item['path']}",
        )

    check(
        canonical_sha256(bundle["content_manifest"])
        == bundle["content_root"]["sha256"],
        "content-root mismatch",
    )
    check(
        raw_sha256(OUTCOME_CONTRACT)
        == bundle["outcome_contract"]["raw_sha256"],
        "outcome-contract raw hash mismatch",
    )
    outcome_contract = load(OUTCOME_CONTRACT)
    schema_preimage = {
        "$defs": outcome_contract["$defs"],
        "category_registry": outcome_contract["category_registry"],
        "outcome_schema": outcome_contract["outcome_schema"],
    }
    reason_preimage = {
        "reason_registry": outcome_contract["reason_registry"],
        "reason_registry_version": outcome_contract["reason_registry_version"],
    }
    check(
        canonical_sha256(schema_preimage)
        == bundle["outcome_contract"]["schema_preimage_sha256"],
        "outcome schema preimage mismatch",
    )
    check(
        canonical_sha256(reason_preimage)
        == bundle["outcome_contract"]["reason_registry_preimage_sha256"],
        "outcome reason-registry preimage mismatch",
    )

    common_bindings = certificate["common_coordinate_bindings"]
    check(
        raw_sha256(ROOT / "public" / "common-coordinate.json")
        == common_bindings["common_coordinate_raw_sha256"],
        "common-coordinate raw hash mismatch",
    )
    for json_key, binding_key in [
        ("intent_at_coordination_interface", "intent_subvalue_canonical_sha256"),
        ("V0", "V0_subvalue_canonical_sha256"),
        ("BE0", "BE0_subvalue_canonical_sha256"),
        ("Q_episode", "Q_episode_subvalue_canonical_sha256"),
        ("action_grammar", "action_grammar_subvalue_canonical_sha256"),
        ("transition_bound", "transition_bound_subvalue_canonical_sha256"),
    ]:
        check(
            canonical_sha256(common[json_key]) == common_bindings[binding_key],
            f"common subvalue mismatch: {json_key}",
        )

    public_packets = [
        load(ROOT / "public" / "episode-765f0698.json"),
        load(ROOT / "public" / "episode-d952741e.json"),
    ]
    normalized_packets = []
    for packet in public_packets:
        normalized = copy.deepcopy(packet)
        normalized.pop("episode_id")
        normalized_packets.append(normalized)
    check(
        normalized_packets[0] == normalized_packets[1],
        "public packets differ beyond opaque episode_id",
    )
    check(
        canonical_sha256(normalized_packets[0])
        == certificate["public_input_bindings"][
            "normalized_public_packet_sha256_after_removing_episode_id"
        ],
        "normalized public packet hash mismatch",
    )
    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "public").glob("*.json"))
    )
    for forbidden_value in [
        "INDEXED_CURRENT_PROJECTION",
        "LOCAL_UNEXPRESSED_NOT_INDEXED",
        "M01_INDEXED_VS_LOCAL_UNEXPRESSED",
        "M01_method_visible_equality_policy",
        "x1-m01",
        "AUTHORITY_VALID_FRONT_HALF_CANDIDATE",
    ]:
        check(
            forbidden_value not in public_text,
            f"instantiated private label leaked into public files: {forbidden_value}",
        )

    g1 = load(ROOT / "private" / "g1-fragment.json")
    g1_preimage = copy.deepcopy(g1)
    recorded_g1_root = g1_preimage["ledger"]["root_candidate"].pop("sha256")
    check(
        canonical_sha256(g1_preimage) == recorded_g1_root,
        "G1 ledger-root candidate mismatch",
    )
    g1_branches = list(g1["branches"].values())
    check(
        g1_branches[0]["D_actual"] == g1_branches[1]["D_actual"],
        "G1 D_actual differs across pair",
    )
    normalized_branch_local_projections = []
    for branch in g1_branches:
        projection = copy.deepcopy(branch["purpose_bound_local_projection"])
        projection.pop("exact_response_ref")
        normalized_branch_local_projections.append(projection)
    check(
        normalized_branch_local_projections[0]
        == normalized_branch_local_projections[1],
        "G1 local projection semantics differ across pair",
    )
    check(
        g1_branches[0]["local_expression_state"]
        == g1_branches[1]["local_expression_state"],
        "G1 local expression state differs across pair",
    )
    check(
        g1_branches[0]["directory_snapshot_presence"]
        != g1_branches[1]["directory_snapshot_presence"],
        "G1 directory snapshot does not carry the paired delta",
    )
    directory_responses = [
        load(ROOT / "private" / "g1-api" / "directory-response-765f0698.json"),
        load(ROOT / "private" / "g1-api" / "directory-response-d952741e.json"),
    ]
    directory_response_paths = [
        ROOT / "private" / "g1-api" / "directory-response-765f0698.json",
        ROOT / "private" / "g1-api" / "directory-response-d952741e.json",
    ]
    episode_ids = [
        "765f0698-edb8-459d-bba6-ceb0ae154e51",
        "d952741e-11f8-44db-a98d-7a34c12e6801",
    ]
    directory_request_paths = [
        ROOT / "private" / "g1-api" / "directory-request-765f0698.json",
        ROOT / "private" / "g1-api" / "directory-request-d952741e.json",
    ]
    local_request_paths = [
        ROOT / "private" / "g1-api" / "local-projection-request-765f0698.json",
        ROOT / "private" / "g1-api" / "local-projection-request-d952741e.json",
    ]
    local_response_paths = [
        ROOT / "private" / "g1-api" / "local-projection-response-765f0698.json",
        ROOT / "private" / "g1-api" / "local-projection-response-d952741e.json",
    ]
    directory_requests = [load(path) for path in directory_request_paths]
    local_requests = [load(path) for path in local_request_paths]
    local_responses = [load(path) for path in local_response_paths]
    for episode_id, directory_request, local_request in zip(
        episode_ids, directory_requests, local_requests
    ):
        for request in [directory_request, local_request]:
            check(
                request["episode_id"] == episode_id,
                "G1 exact request is not bound to its episode_id",
            )
            check(
                set(request)
                >= {
                    "episode_id",
                    "intent_id",
                    "purpose",
                    "recipient",
                    "request_version",
                    "current_head",
                },
                "G1 exact request omits a public-contract binding",
            )
    for requests in [directory_requests, local_requests]:
        normalized_requests = []
        for request in requests:
            normalized = copy.deepcopy(request)
            normalized.pop("episode_id")
            normalized_requests.append(normalized)
        check(
            normalized_requests[0] == normalized_requests[1],
            "G1 requests differ beyond opaque episode_id",
        )
    check(
        len(directory_response_paths[0].read_bytes())
        == len(directory_response_paths[1].read_bytes()),
        "directory response raw sizes differ",
    )
    allowed_directory_delta_fields = {
        "current_head",
        "status_code",
        "candidate_projection_ref",
        "payload_raw_sha256",
        "request_raw_sha256",
        "padding",
    }
    observed_directory_delta_fields = {
        key
        for key in directory_responses[0]
        if directory_responses[0][key] != directory_responses[1][key]
    }
    check(
        observed_directory_delta_fields == allowed_directory_delta_fields,
        "directory responses differ outside the frozen owner delta",
    )
    interface_contract = load(ROOT / "public" / "interface-contract.json")
    directory_statuses = set(
        interface_contract["endpoints"]["current-directory-query"]["response_status"]
    )
    local_statuses = set(
        interface_contract["endpoints"]["purpose-bound-local-projection"][
            "response_status"
        ]
    )
    for response, request_path in zip(
        directory_responses, directory_request_paths
    ):
        check(
            response["request_raw_sha256"] == raw_sha256(request_path),
            "directory response request binding mismatch",
        )
        check(
            response["status_code"] in directory_statuses,
            "directory response uses a non-contract semantic status",
        )
    check(
        directory_responses[0]["payload_raw_sha256"]
        == raw_sha256(ROOT / "private" / "g1-api" / "candidate-projection.json"),
        "directory MATCH payload binding mismatch",
    )
    check(
        len(local_response_paths[0].read_bytes())
        == len(local_response_paths[1].read_bytes()),
        "local projection response raw sizes differ",
    )
    normalized_local_responses = []
    for response, request_path in zip(local_responses, local_request_paths):
        check(
            response["request_raw_sha256"] == raw_sha256(request_path),
            "local projection request binding mismatch",
        )
        check(
            response["status_code"] in local_statuses,
            "local projection response uses a non-contract semantic status",
        )
        check(
            response["payload_raw_sha256"]
            == raw_sha256(ROOT / "private" / "g1-api" / "candidate-projection.json"),
            "local projection payload binding mismatch",
        )
        normalized = copy.deepcopy(response)
        normalized.pop("request_raw_sha256")
        normalized_local_responses.append(normalized)
    check(
        normalized_local_responses[0] == normalized_local_responses[1],
        "local projection responses differ semantically across episodes",
    )

    transition = load(ROOT / "certificates" / "t-g1-to-g2.json")
    transition_text = (ROOT / "certificates" / "t-g1-to-g2.json").read_text(
        encoding="utf-8"
    )
    transition_preimage = copy.deepcopy(transition)
    recorded_transition_root = transition_preimage["ledger"]["root_candidate"].pop(
        "sha256"
    )
    check(
        canonical_sha256(transition_preimage) == recorded_transition_root,
        "T_G1_TO_G2 ledger-root candidate mismatch",
    )
    check(
        {
            item["path"] for item in transition["source_boundary"]["read_inputs"]
        }
        == {"public/common-coordinate.json", "private/g1-fragment.json"},
        "T_G1_TO_G2 truth source boundary is not exactly common plus G1",
    )
    check(
        "g2_fragment_raw_sha256" not in transition_text,
        "T_G1_TO_G2 creates a raw-hash cycle back to G2",
    )
    check(
        "target_binding" not in transition
        and "truth_projection_canonical_sha256" not in transition_text,
        "T_G1_TO_G2 embeds downstream G2 truth",
    )
    passthrough = transition["typed_non_success_contract"][-1][
        "passthrough_envelope"
    ]
    check(
        passthrough["category_source_field"] == "G1_return.category"
        and passthrough["reason_code_source_field"] == "G1_return.reason_code"
        and passthrough["copy_rule"]
        == "COPY_THE_ACTUAL_RUNTIME_CATEGORY_AND_REASON_CODE_PAIR_BYTE_EXACT"
        and "must already be registered together"
        in passthrough["registry_membership_requirement"],
        "T_G1_TO_G2 does not define lossless registered-pair passthrough",
    )
    fail_closed_cases = passthrough["fail_closed_cases"]
    check(
        {
            (item["category"], item["reason_code"])
            for item in fail_closed_cases
        }
        == {
            ("INVALID", "INVALID_TRANSITION_BINDING"),
            ("UNRESOLVED_SCHEMA", "UNREGISTERED_CATEGORY_REASON_PAIR"),
        }
        and all(
            item["transition_status"] == "NOT_REACHED"
            and item["attempted_raw_return_sha256_required"]
            for item in fail_closed_cases
        )
        and "exactly one owner-signed typed transition receipt"
        in passthrough["totality_rule"],
        "T_G1_TO_G2 passthrough is not typed and total for failed bindings "
        "and unregistered upstream pairs",
    )
    check(
        transition["outcome_reason_registry_binding"]["contract_raw_sha256"]
        == raw_sha256(OUTCOME_CONTRACT)
        and transition["outcome_reason_registry_binding"][
            "reason_registry_preimage_sha256"
        ]
        == canonical_sha256(reason_preimage),
        "T_G1_TO_G2 outcome-registry binding mismatch",
    )
    check(
        "independent-estuary-validation-lab"
        in json.dumps(common["intent_at_coordination_interface"], ensure_ascii=False)
        and "independent-estuary-validation-lab" in transition_text,
        "fixed witness is not carried from Intent into T_G1_TO_G2",
    )
    check(
        "candidate-calibration-consortium-role-filler-0007" in transition_text,
        "G1 calibration candidate is not carried into T_G1_TO_G2",
    )
    g2_transition_hash = raw_sha256(ROOT / "certificates" / "t-g1-to-g2.json")

    g2 = load(ROOT / "private" / "g2-fragment.json")
    check(
        g2_transition_hash in json.dumps(g2, ensure_ascii=False),
        "G2 does not bind the finalized T_G1_TO_G2 contract",
    )
    g2_projections = [
        item["truth_projection"] for item in g2["branch_truth_projections"]
    ]
    check(g2_projections[0] == g2_projections[1], "G2 truth differs across pair")
    g2_projection_hash = canonical_sha256(g2_projections[0])

    g3 = load(ROOT / "private" / "g3-fragment.json")
    g3_projection_hash = canonical_sha256(g3["shared_g3_assessment_projection"])
    check(
        all(
            item["projection_canonical_sha256"] == g3_projection_hash
            for item in g3["episode_projection_bindings"]
        ),
        "G3 episode projection binding mismatch",
    )
    check(
        g3["shared_g3_assessment_projection"]["coordinate"]["V0_canonical_sha256"]
        == canonical_sha256(common["V0"]),
        "G3 V0 binding mismatch",
    )
    check(
        g3["shared_g3_assessment_projection"]["coordinate"][
            "Q_episode_canonical_sha256"
        ]
        == canonical_sha256(common["Q_episode"]),
        "G3 Q_episode binding mismatch",
    )

    g5 = load(ROOT / "private" / "g5-fragment.json")
    g5_projections = []
    for item in g5["branch_truth_projections"]:
        projection = copy.deepcopy(item)
        projection.pop("episode_key")
        g5_projections.append(projection)
    check(g5_projections[0] == g5_projections[1], "G5 truth differs across pair")
    g5_projection_hash = canonical_sha256(g5_projections[0])
    check(
        "private_truth"
        not in (ROOT / "private" / "g5-fragment.json").read_text(encoding="utf-8"),
        "G5 assembly still embeds authority-domain private truth",
    )
    domain_values = []
    authority_owner_keys = set()
    closure_lines = []
    for binding in g5["domain_truth_bindings"]:
        domain_path = ROOT / binding["path"]
        domain = load(domain_path)
        check(
            raw_sha256(domain_path) == binding["raw_bytes_sha256"],
            f"G5 domain raw hash mismatch: {binding['authority_domain_id']}",
        )
        check(
            domain["authority_domain_id"] == binding["authority_domain_id"],
            "G5 domain identity mismatch",
        )
        check(
            domain["truth_owner"]["owner_key_id"] == binding["owner_key_id"],
            "G5 domain owner-key mismatch",
        )
        owner_root_preimage = {
            key: domain[key]
            for key in [
                "authority_domain_id",
                "relation_coordinate",
                "truth_owner",
                "private_truth",
                "not_run_boundary",
            ]
        }
        check(
            canonical_sha256(owner_root_preimage)
            == domain["ledger_candidates"]["root_candidate_sha256"],
            f"G5 owner-root mismatch: {binding['authority_domain_id']}",
        )
        authority_owner_keys.add(binding["owner_key_id"])
        domain_values.append(domain)
        closure_lines.append(
            f"{binding['authority_domain_id']}={binding['raw_bytes_sha256']}\n"
        )
    check(len(authority_owner_keys) == 4, "G5 does not retain four owner keys")
    check(
        hashlib.sha256("".join(closure_lines).encode("utf-8")).hexdigest()
        == g5["domain_truth_closure"]["candidate_sha256"],
        "G5 four-domain closure mismatch",
    )
    delta_domain = next(
        item
        for item in domain_values
        if item["authority_domain_id"] == "delta-calibration-domain"
    )
    check(
        delta_domain["private_truth"]["s0"]["resource"]["resource_owner_principal_id"]
        == "delta-field-calibration-cooperative",
        "reservation authority is not held by the calibration resource owner",
    )
    check(
        set(g5["g5_gate_receipt_requirements"])
        >= {
            "relation",
            "program_coordinator",
            "delta_calibration",
            "independent_validation",
            "site_data_steward",
        },
        "G5 gate does not require every authority domain",
    )
    check(
        "resource-owner reservation"
        in g5["g5_gate_receipt_requirements"]["delta_calibration"][
            "required_current_owner_receipts"
        ],
        "G5 gate omits the delta resource-owner reservation receipt",
    )

    registered_reason_pairs = {
        (category, reason)
        for category, reasons in outcome_contract["reason_registry"].items()
        for reason in reasons
    }

    def collect_reason_pairs(value: Any) -> list[tuple[str, str]]:
        pairs = []
        if isinstance(value, dict):
            if set(value) >= {"category", "reason_code"}:
                pairs.append((value["category"], value["reason_code"]))
            for child in value.values():
                pairs.extend(collect_reason_pairs(child))
        elif isinstance(value, list):
            for child in value:
                pairs.extend(collect_reason_pairs(child))
        return pairs

    reason_scan_documents = [("bundle.json", bundle)] + [
        (item["path"], load(ROOT / item["path"]))
        for item in bundle["content_manifest"]
        if item["path"].endswith(".json")
    ]
    for document_path, document in reason_scan_documents:
        for reason_pair in collect_reason_pairs(document):
            check(
                reason_pair in registered_reason_pairs,
                f"unregistered category/reason pair in {document_path}: "
                f"{reason_pair}",
            )

    non_bearing = certificate["non_bearing_fragment_equality_proofs"]
    check(
        g2_projection_hash
        == non_bearing["G2"]["canonical_branch_truth_projection_sha256_both"],
        "G2 equality-proof hash mismatch",
    )
    check(
        g2_projection_hash not in transition_text,
        "T_G1_TO_G2 embeds the downstream G2 projection hash",
    )
    check(
        g3_projection_hash
        == non_bearing["G3"]["shared_projection_canonical_sha256_both"],
        "G3 equality-proof hash mismatch",
    )
    check(
        g5_projection_hash
        == non_bearing["G5"][
            "canonical_branch_projection_sha256_after_removing_episode_key_both"
        ],
        "G5 equality-proof hash mismatch",
    )
    for line, relative_path in {
        "G1": "private/g1-fragment.json",
        "G2": "private/g2-fragment.json",
        "G3": "private/g3-fragment.json",
        "G5": "private/g5-fragment.json",
    }.items():
        check(
            raw_sha256(ROOT / relative_path)
            == certificate["fragment_commitments"][f"{line}_raw_sha256"],
            f"{line} fragment commitment mismatch",
        )

    allowed_score_values = {
        "SCORE_DELTA",
        "SCORE_PROPAGATED",
        "SCORE_INVARIANCE",
        "MASK_NOT_COMPARABLE",
        "SPLIT_REQUIRED",
    }
    for episode_id, line_mask in certificate["scoring_mask"]["per_episode"].items():
        check(
            set(line_mask.values()) <= allowed_score_values,
            f"invalid score-mask value: {episode_id}",
        )
    check(
        certificate["scoring_mask"]["integration_denominator"]
        == "ALL_FINALIZED_EPISODE_ARM_OUTPUTS"
        and "never removes the episode"
        in certificate["scoring_mask"]["not_reached_rule"],
        "NOT_REACHED may shrink the frozen integration population",
    )

    check(
        bundle["status"] == "ASSEMBLED_CANDIDATE_AWAITING_INDEPENDENT_REVIEW",
        "bundle status overclaims acceptance",
    )
    check(
        bundle["current_truth"]["scoreable_episode_candidates"] == 0
        and bundle["current_truth"]["runs_completed"] == 0
        and not bundle["current_truth"]["runner_implemented"],
        "bundle status overclaims a run or scoreable population",
    )

    print(
        "PASS: package integrity, public normalization, common-coordinate "
        "bindings, G1 ledger, G2/G3/G5 equality, G5 owner separation, and "
        "candidate-only status"
    )


if __name__ == "__main__":
    main()
