from __future__ import annotations

from copy import deepcopy


PRINCIPALS = ["requester", "provider"]
INTENT = {
    "kind": "IntentAtCoordinationInterface",
    "principal": "requester",
    "objective": "obtain_version_safe_translation_support",
    "normative_status": "CONDITIONALLY_SEEKING",
    "upstream_vague_goal_generation": "EXCLUDED_FROM_EXPERIMENT",
}


def public_world(
    world_id: str,
    *,
    index: list[dict] | None = None,
    owners: list[str] | None = None,
    raw_allowed: bool = False,
    operators: list[str] | None = None,
    skin: str = "repo-release",
) -> dict:
    return {
        "id": world_id,
        "skin": skin,
        "intent": deepcopy(INTENT),
        "target": "ship_patch_without_lowering_security",
        "quality_floor": "signed_tests_and_rollback",
        "necessary_principals": list(PRINCIPALS),
        "public_index": deepcopy(index or []),
        "owners": list(owners or ["provider"]),
        "available_operator_ids": list(operators or []),
        "raw_centralization_allowed": raw_allowed,
        "action_envelope": {
            "allowed": [
                "observe_public",
                "ask",
                "submit_proposal",
                "apply_operator",
                "stop",
            ],
            "max_actions": 8,
            "recipient": "coordinator",
            "purpose": "g1_candidate_qualification",
        },
    }


PUBLIC_WORLDS = [
    public_world(
        "W01_PUBLIC_INDEX",
        index=[
            {
                "path_id": "P01",
                "target": "ship_patch_without_lowering_security",
                "quality_floor": "signed_tests_and_rollback",
                "necessary_principals": PRINCIPALS,
                "source_id": "registry-v4",
            }
        ],
        raw_allowed=True,
    ),
    public_world(
        "W02_T0_LEGAL_PATH",
        owners=["provider", "release"],
        raw_allowed=True,
    ),
    public_world("W03_FINAL_PROPOSAL_ONLY", owners=[]),
    public_world(
        "W04_EXPLANATION_OPERATOR", owners=["provider"], operators=["OP04"]
    ),
    public_world(
        "W05_TERM_CHANGE_OPERATOR", owners=["provider"], operators=["OP05"]
    ),
    public_world(
        "W06_POST_TREATMENT_AUTHORITY", owners=["security"], operators=["OP06"]
    ),
    public_world(
        "W07_CAPABILITY_ADAPTER", owners=["provider"], operators=["OP07"]
    ),
    public_world(
        "W08_WRONG_AUTHORITY",
        owners=["security-delegate"],
        operators=["OP08"],
    ),
    public_world(
        "W09_FORBIDDEN_DISCLOSURE", owners=["provider"], operators=["OP09"]
    ),
    public_world("W10_SAME_SOURCE_ALIAS", owners=["provider-a", "provider-a-alias"]),
    public_world("W11_ZERO_DISCLOSURE_EXISTS", owners=["provider"]),
    public_world("W12_ZERO_DISCLOSURE_ABSENT", owners=["provider"]),
]


def response(
    owner: str,
    path_id: str,
    source: str,
    authority: str,
    *,
    aliases: list[str] | None = None,
    allowed: bool = True,
) -> dict:
    return {
        "owner": owner,
        "accepted_claims": aliases
        or [
            "complement_for:obtain_version_safe_translation_support",
            "what_path_supports:obtain_version_safe_translation_support",
        ],
        "path_id": path_id,
        "source_id": f"{source}:{owner}",
        "canonical_source": source,
        "authority_root": authority,
        "allowed": allowed,
        "existed_at_t0": True,
    }


def oracle(
    world_id: str,
    path_id: str,
    *,
    fact: bool = True,
    required_roots: list[str] | None = None,
    required_distinct_sources: int = 1,
    t0_responses: list[dict] | None = None,
    initial: dict | None = None,
    operators: list[dict] | None = None,
    expected_boundary: str = "QUALIFIED_CANDIDATE",
) -> dict:
    return {
        "world_id": world_id,
        "canonical_proposal": {
            "path_id": path_id,
            "target": "ship_patch_without_lowering_security",
            "quality_floor": "signed_tests_and_rollback",
            "necessary_principals": PRINCIPALS,
        },
        "fact_existed_at_t0": fact,
        "required_authority_roots": required_roots or [],
        "required_distinct_sources": required_distinct_sources,
        "t0_responses": t0_responses or [],
        "initial": {
            "qualified": False,
            "understood": True,
            "terms_compatible": True,
            "authority_valid": True,
            "capability_present": True,
            "claimable": True,
            **(initial or {}),
        },
        "operators": operators or [],
        "expected_boundary": expected_boundary,
    }


PRIVATE_ORACLES = [
    oracle(
        "W01_PUBLIC_INDEX",
        "P01",
        initial={"qualified": True},
    ),
    oracle(
        "W02_T0_LEGAL_PATH",
        "P02",
        required_roots=["provider-fact", "release-fact"],
        required_distinct_sources=2,
        t0_responses=[
            response("provider", "P02", "provider-ledger", "provider-fact"),
            response("release", "P02", "release-ledger", "release-fact"),
        ],
    ),
    oracle(
        "W03_FINAL_PROPOSAL_ONLY",
        "P03",
        initial={"qualified": True},
    ),
    oracle(
        "W04_EXPLANATION_OPERATOR",
        "P04",
        required_roots=["provider-fact"],
        t0_responses=[response("provider", "P04", "provider-ledger", "provider-fact")],
        initial={"understood": False, "claimable": False},
        operators=[
            {
                "id": "OP04",
                "type": "EXPLANATION",
                "authority_root": "requester-understanding",
                "valid_authority": True,
                "disclosure_legal": True,
                "effects": {"understood": True, "claimable": True},
            }
        ],
    ),
    oracle(
        "W05_TERM_CHANGE_OPERATOR",
        "P05",
        required_roots=["provider-fact"],
        t0_responses=[response("provider", "P05", "provider-ledger", "provider-fact")],
        initial={"terms_compatible": False, "claimable": False},
        operators=[
            {
                "id": "OP05",
                "type": "TERM_CHANGE",
                "authority_root": "provider-negotiation",
                "valid_authority": True,
                "disclosure_legal": True,
                "effects": {"terms_compatible": True, "claimable": True},
            }
        ],
    ),
    oracle(
        "W06_POST_TREATMENT_AUTHORITY",
        "P06",
        required_roots=["security-authority"],
        initial={"authority_valid": False, "qualified": False, "claimable": False},
        operators=[
            {
                "id": "OP06",
                "type": "AUTHORITY_GRANT",
                "authority_root": "security-authority",
                "valid_authority": True,
                "disclosure_legal": True,
                "effects": {"authority_valid": True, "qualified": True, "claimable": True},
                "creates_evidence": {
                    "source_id": "security-receipt-t1",
                    "canonical_source": "security-receipt-t1",
                    "authority_root": "security-authority",
                    "claim": "grant:P06",
                },
            }
        ],
    ),
    oracle(
        "W07_CAPABILITY_ADAPTER",
        "P07",
        required_roots=["provider-fact"],
        t0_responses=[response("provider", "P07", "provider-ledger", "provider-fact")],
        initial={"capability_present": False, "qualified": False, "claimable": False},
        operators=[
            {
                "id": "OP07",
                "type": "CAPABILITY_CREATE",
                "authority_root": "provider-execution",
                "valid_authority": True,
                "disclosure_legal": True,
                "effects": {"capability_present": True, "qualified": True, "claimable": True},
                "creates_evidence": {
                    "source_id": "adapter-test-t1",
                    "canonical_source": "adapter-test-t1",
                    "authority_root": "provider-fact",
                    "claim": "adapter_verified:P07",
                },
            }
        ],
    ),
    oracle(
        "W08_WRONG_AUTHORITY",
        "P08",
        required_roots=["security-authority"],
        initial={"authority_valid": False, "qualified": False, "claimable": False},
        operators=[
            {
                "id": "OP08",
                "type": "AUTHORITY_GRANT",
                "authority_root": "coordinator",
                "valid_authority": False,
                "disclosure_legal": True,
                "effects": {"authority_valid": True, "qualified": True, "claimable": True},
                "creates_evidence": {
                    "source_id": "coordinator-self-grant",
                    "canonical_source": "coordinator-self-grant",
                    "authority_root": "coordinator",
                    "claim": "grant:P08",
                },
            }
        ],
        expected_boundary="INVALID",
    ),
    oracle(
        "W09_FORBIDDEN_DISCLOSURE",
        "P09",
        required_roots=["provider-fact"],
        initial={"qualified": False},
        operators=[
            {
                "id": "OP09",
                "type": "QUALIFICATION_CREATE",
                "authority_root": "provider-fact",
                "valid_authority": True,
                "disclosure_legal": False,
                "effects": {"qualified": True},
                "creates_evidence": {
                    "source_id": "forbidden-private-record",
                    "canonical_source": "provider-private-record",
                    "authority_root": "provider-fact",
                    "claim": "private_compatibility:P09",
                },
            }
        ],
        expected_boundary="INVALID",
    ),
    oracle(
        "W10_SAME_SOURCE_ALIAS",
        "P10",
        required_roots=["provider-fact", "independent-release-fact"],
        required_distinct_sources=2,
        t0_responses=[
            response("provider-a", "P10", "shared-ledger", "provider-fact"),
            response("provider-a-alias", "P10", "shared-ledger", "provider-fact"),
        ],
        expected_boundary="INVALID",
    ),
    oracle(
        "W11_ZERO_DISCLOSURE_EXISTS",
        "P11",
        fact=True,
        required_roots=["provider-fact"],
        t0_responses=[
            response(
                "provider",
                "P11",
                "provider-private",
                "provider-fact",
                allowed=False,
            )
        ],
        expected_boundary="UNWILLING_TO_DISCLOSE",
    ),
    oracle(
        "W12_ZERO_DISCLOSURE_ABSENT",
        "P12",
        fact=False,
        required_roots=["provider-fact"],
        t0_responses=[
            response(
                "provider",
                "P12",
                "provider-private",
                "provider-fact",
                allowed=False,
            )
        ],
        expected_boundary="UNWILLING_TO_DISCLOSE",
    ),
]


PUBLIC_BY_ID = {world["id"]: world for world in PUBLIC_WORLDS}
ORACLE_BY_ID = {world["world_id"]: world for world in PRIVATE_ORACLES}
