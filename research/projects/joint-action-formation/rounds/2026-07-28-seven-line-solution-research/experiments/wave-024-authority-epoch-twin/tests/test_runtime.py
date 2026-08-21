from __future__ import annotations

import copy
import json
import pathlib
import sys

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


WAVE_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WAVE_DIR))

import twin_runtime as runtime  # noqa: E402


def _fixture(tmp_path: pathlib.Path) -> dict[str, object]:
    authority_key = Ed25519PrivateKey.generate()
    lab_root_key = Ed25519PrivateKey.generate()
    target_key = Ed25519PrivateKey.generate()
    q_sha256 = runtime.sha256_value(runtime.exact_task())
    delegation = runtime.sign_record(
        {
            "schema": "AUTHORITY_DELEGATION_V1",
            "delegation_id": "delegation-test",
            "principal_id": "Principal:VenueV",
            "actor_id": runtime.ACTOR_ID,
            "q_sha256": q_sha256,
            "object_id": runtime.OBJECT_ID,
            "target_id": runtime.TARGET_ID,
            "operation": runtime.OPERATION,
            "epoch": 1,
            "status": "CURRENT",
            "valid_from_logical_minute": 0,
            "valid_until_logical_minute": 90,
            "prev_authority_head_sha256": runtime.GENESIS,
            "issuer_process_id": 101,
        },
        key=authority_key,
        digest_field="authority_head_sha256",
    )
    target_certificate = runtime.sign_record(
        {
            "schema": "LAB_SYNTHETIC_TARGET_CERTIFICATE_V1",
            "target_id": runtime.TARGET_ID,
            "q_sha256": q_sha256,
            "target_public_key_hex": runtime.public_key_hex(target_key),
            "certificate_scope": "LOCAL_SYNTHETIC_TARGET_ONLY",
            "registry_process_id": 102,
        },
        key=lab_root_key,
        digest_field="certificate_sha256",
    )
    db_path = tmp_path / "target.sqlite3"
    runtime._initialize_target_db(
        db_path,
        target_certificate=target_certificate,
        initial_authority=delegation,
    )
    request = {
        "schema": "EXACT_EFFECT_REQUEST_V1",
        "request_id": "request-test",
        "q_sha256": q_sha256,
        "object_id": runtime.OBJECT_ID,
        "target_id": runtime.TARGET_ID,
        "operation": runtime.OPERATION,
        "actor_id": runtime.ACTOR_ID,
        "presented_epoch": 1,
        "commit_logical_minute": 10,
        "delegation": delegation,
        "desired_state": runtime.exact_target_state(),
    }
    return {
        "authority_key": authority_key,
        "authority_public_key": runtime.public_key_hex(authority_key),
        "lab_root_key": lab_root_key,
        "lab_root_public_key": runtime.public_key_hex(lab_root_key),
        "target_key": target_key,
        "target_certificate": target_certificate,
        "q_sha256": q_sha256,
        "delegation": delegation,
        "request": request,
        "db_path": db_path,
    }


def _revocation(fixture: dict[str, object], **changes: object) -> dict[str, object]:
    delegation = fixture["delegation"]
    assert isinstance(delegation, dict)
    body = {
        "schema": "AUTHORITY_HEAD_V1",
        "delegation_id": delegation["delegation_id"],
        "principal_id": delegation["principal_id"],
        "actor_id": delegation["actor_id"],
        "q_sha256": delegation["q_sha256"],
        "object_id": delegation["object_id"],
        "target_id": delegation["target_id"],
        "operation": delegation["operation"],
        "epoch": 2,
        "status": "REVOKED",
        "prev_authority_head_sha256": delegation["authority_head_sha256"],
        "reason": "TEST_REVOCATION",
        "issuer_process_id": 101,
    }
    body.update(changes)
    key = fixture["authority_key"]
    assert isinstance(key, Ed25519PrivateKey)
    return runtime.sign_record(
        body,
        key=key,
        digest_field="authority_head_sha256",
    )


def _execute(fixture: dict[str, object], request: dict[str, object]):
    return runtime._target_execute(
        fixture["db_path"],
        request=request,
        q_sha256=fixture["q_sha256"],
        authority_public_key_hex=fixture["authority_public_key"],
        target_key=fixture["target_key"],
        target_certificate=fixture["target_certificate"],
    )


def _apply(fixture: dict[str, object], record: dict[str, object]):
    return runtime._apply_fence_record(
        fixture["db_path"],
        record=record,
        authority_public_key_hex=fixture["authority_public_key"],
        target_key=fixture["target_key"],
        target_certificate=fixture["target_certificate"],
    )


@pytest.mark.parametrize(
    "mutation",
    [
        {"object_id": "PowerOccurrence:other"},
        {"target_id": "VenueV:other-target"},
        {"operation": "OTHER_OPERATION"},
        {"status": "CURRENT"},
    ],
)
def test_fence_rejects_wrong_scope_or_non_revocation(tmp_path, mutation):
    fixture = _fixture(tmp_path)
    with pytest.raises(RuntimeError):
        _apply(fixture, _revocation(fixture, **mutation))
    audit = runtime._target_audit(fixture["db_path"])
    assert len(audit["authority_heads"]) == 1
    assert audit["effect_count"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        {"object_id": "PowerOccurrence:other"},
        {"target_id": "VenueV:other-target"},
        {"operation": "OTHER_OPERATION"},
        {"commit_logical_minute": 91},
    ],
)
def test_execute_rejects_aliases_and_expired_delegation(tmp_path, mutation):
    fixture = _fixture(tmp_path)
    request = copy.deepcopy(fixture["request"])
    request.update(mutation)
    with pytest.raises(RuntimeError):
        _execute(fixture, request)
    audit = runtime._target_audit(fixture["db_path"])
    assert audit["request_count"] == 0
    assert audit["effect_count"] == 0


def test_exact_request_is_idempotent_after_lost_ack(tmp_path):
    fixture = _fixture(tmp_path)
    request = fixture["request"]
    first = _execute(fixture, request)
    second = _execute(fixture, request)
    assert first == second
    assert first["decision"] == "COMMITTED"
    audit = runtime._target_audit(fixture["db_path"])
    assert audit["effect_count"] == 1
    assert audit["request_count"] == 1
    assert [event["event_type"] for event in audit["native_events"]] == [
        "AUTHORITY_FENCE_BOOTSTRAPPED",
        "REQUEST_INGRESS",
        "EFFECT_COMMITTED",
    ]


def test_authority_verifies_signed_exact_target_predecessor(tmp_path):
    fixture = _fixture(tmp_path)
    receipt = _execute(fixture, fixture["request"])
    verified = runtime.verify_authority_predecessor_receipt(
        receipt,
        pinned_lab_root_public_key_hex=fixture["lab_root_public_key"],
        prior_authority=fixture["delegation"],
    )
    assert verified["target_receipt_sha256"] == receipt["target_receipt_sha256"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("object_id", "PowerOccurrence:other"),
        ("target_id", "VenueV:other-target"),
        ("operation", "OTHER_OPERATION"),
        ("decision", "REJECTED_STALE_EPOCH"),
        ("presented_epoch", 99),
        ("durable_fence_head_sha256", "ff" * 32),
    ],
)
def test_authority_rejects_validly_resigned_wrong_predecessor(
    tmp_path, field, value
):
    fixture = _fixture(tmp_path)
    receipt = _execute(fixture, fixture["request"])
    body = runtime.without(
        receipt,
        "signature_hex",
        "target_receipt_sha256",
    )
    body[field] = value
    attacked = runtime.sign_record(
        body,
        key=fixture["target_key"],
        digest_field="target_receipt_sha256",
    )
    with pytest.raises(RuntimeError):
        runtime.verify_authority_predecessor_receipt(
            attacked,
            pinned_lab_root_public_key_hex=fixture["lab_root_public_key"],
            prior_authority=fixture["delegation"],
        )


def test_durable_matching_fence_precedes_and_blocks_effect(tmp_path):
    fixture = _fixture(tmp_path)
    fence = _apply(fixture, _revocation(fixture))
    refusal = _execute(fixture, fixture["request"])
    assert fence["decision"] == "FENCE_ADVANCED"
    assert refusal["decision"] == "REJECTED_STALE_EPOCH"
    assert refusal["reason"] == "REVOKED/STALE_AUTHORITY"
    audit = runtime._target_audit(fixture["db_path"])
    assert audit["effect_count"] == 0
    assert audit["refusal_count"] == 1
    events = audit["native_events"]
    assert [event["event_type"] for event in events] == [
        "AUTHORITY_FENCE_BOOTSTRAPPED",
        "FENCE_ADVANCED",
        "REQUEST_INGRESS",
        "AUTHORITY_REJECTED",
    ]
    assert fence["event_sequence"] < refusal["ingress_event_sequence"]


def test_full_twin_has_scored_s_r_and_unscored_u(tmp_path):
    twin = runtime.run_twin(tmp_path)
    assert twin["results"]["S"] == {
        "decision": "COMMITTED",
        "effect_count": 1,
        "acceptance_count": 2,
        "finality_count": 1,
        "retry_effect_count": 0,
    }
    assert twin["results"]["R"] == {
        "decision": "REJECTED_STALE_EPOCH",
        "effect_count": 0,
        "acceptance_count": 0,
        "finality_count": 0,
        "retry_effect_count": 0,
        "authority_rejection_count": 1,
    }
    assert twin["results"]["U"]["scoring_status"] == (
        "CONCURRENT_OR_UNORDERED/NOT_SCORED"
    )
    assert not twin["results"]["U"]["target_matching_fence_ack_exists"]
    assert twin["authority_timing"]["S"] == (
        "COMPLETED_BEFORE_AUTHORITY_REVOCATION_RECORD"
    )
    assert twin["revocation"][
        "experiment_predecessor_s_target_receipt_sha256"
    ] == twin["authority_timing"]["s_target_receipt_sha256"]
    assert twin["pre_response_isomorphism"][
        "recorded_candidate_startup_surface_equal_s_r_u"
    ]

    run_dir = pathlib.Path(twin["run_dir"])
    worlds = {
        role: json.loads((run_dir / relative).read_text(encoding="utf-8"))
        for role, relative in twin["worlds"].items()
    }
    assert twin["world_artifact_sha256"] == {
        role: world["world_artifact_sha256"] for role, world in worlds.items()
    }
    assert twin["artifact_hash_semantics"] == (
        "CANONICAL_JSON_SHA256_AFTER_REMOVING_TWIN_ARTIFACT_SHA256_FIELD"
    )
    for world in worlds.values():
        assert world["processes"]["candidate_source_exitcode"] == -15
        assert world["ack_drop_proxy_receipt"]["candidate_ack_delivered"] is False
        assert world["source_state_audit"]["ack_received_count"] == 0
        assert world["source_state_audit"]["retry_execute_count"] == 0
        keys = world["key_registry"]
        role_keys = [
            keys["authority_public_key_hex"],
            keys["lab_root_public_key_hex"],
            keys["target_public_key_hex"],
            keys["controller_public_key_hex"],
            keys["proxy_public_key_hex"],
            *keys["owner_public_keys"].values(),
        ]
        assert len(role_keys) == len(set(role_keys))
        for owner_id, owner_audit in world["owner_store_audits"].items():
            identity = owner_audit["identity"]
            assert identity["pinned_q_sha256"] == world["candidate_payload"][
                "q_sha256"
            ]
            if owner_id in {"O_Q", "O_V"}:
                assert identity["pinned_lab_root_public_key_hex"] == world[
                    "candidate_payload"
                ]["lab_root_public_key_hex"]
                assert json.loads(identity["pinned_acceptance_keys_json"]) == {}
            else:
                assert identity["pinned_lab_root_public_key_hex"] is None
                assert json.loads(identity["pinned_acceptance_keys_json"]) == {
                    owner: keys["owner_public_keys"][owner]
                    for owner in ("O_Q", "O_V")
                }

    assert worlds["R"]["fence_advanced_receipt"]["event_sequence"] < worlds[
        "R"
    ]["target_execute_receipt"]["ingress_event_sequence"]
    assert worlds["U"]["fence_advanced_receipt"] is None


def _status_for_fixture(fixture: dict[str, object]) -> dict[str, object]:
    _execute(fixture, fixture["request"])
    return runtime._target_status(
        fixture["db_path"],
        request_id=fixture["request"]["request_id"],
        target_key=fixture["target_key"],
        target_certificate=fixture["target_certificate"],
    )


def _resign_target_record(
    fixture: dict[str, object], record: dict[str, object]
) -> dict[str, object]:
    body = {
        key: value
        for key, value in record.items()
        if key not in {"signature_hex", "target_receipt_sha256"}
    }
    return runtime.sign_record(
        body,
        key=fixture["target_key"],
        digest_field="target_receipt_sha256",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("request_id", "different-request"),
        ("q_sha256", "0" * 64),
        ("object_id", "PowerOccurrence:other"),
        ("target_id", "VenueV:other-target"),
        ("operation", "OTHER_OPERATION"),
    ],
)
def test_recovery_rejects_validly_signed_but_detached_status(
    tmp_path, field, value
):
    fixture = _fixture(tmp_path)
    status = _status_for_fixture(fixture)
    receipt = copy.deepcopy(status["receipt"])
    receipt[field] = value
    receipt = _resign_target_record(fixture, receipt)
    readback = copy.deepcopy(status["readback"])
    if field == "request_id":
        readback["request_id"] = value
    if field == "target_id":
        readback["target_id"] = value
    readback["receipt_sha256"] = receipt["target_receipt_sha256"]
    readback = _resign_target_record(fixture, readback)
    with pytest.raises(RuntimeError):
        runtime._validate_target_status_for_request(
            {"receipt": receipt, "readback": readback},
            payload={
                "q_sha256": fixture["q_sha256"],
                "lab_root_public_key_hex": fixture["lab_root_public_key"],
            },
            request=fixture["request"],
        )


def test_owner_rejects_valid_records_detached_from_pinned_q(tmp_path):
    fixture = _fixture(tmp_path)
    status = _status_for_fixture(fixture)
    assert runtime._verify_target_status_for_owner(
        status,
        lab_root_public_key_hex=fixture["lab_root_public_key"],
        q_sha256=fixture["q_sha256"],
    )
    assert not runtime._verify_target_status_for_owner(
        status,
        lab_root_public_key_hex=fixture["lab_root_public_key"],
        q_sha256="0" * 64,
    )
