"""Legacy outcome-only and causal evaluators for CT-001."""

from __future__ import annotations

from typing import Any, Mapping

from runtime import sha256_value, verify_request_envelope, verify_signed


def evaluate_legacy(bundle: Mapping[str, Any]) -> dict[str, Any]:
    projection = bundle.get("target_native", {}).get("state_projection", {})
    success = (
        projection.get("object_id") == bundle.get("public_manifest", {}).get("object_id")
        and projection.get("operation_id")
        == bundle.get("public_manifest", {}).get("operation_id")
        and projection.get("energized") is True
        and projection.get("version") == 1
    )
    return {
        "evaluator": "OUTCOME_ONLY_LEGACY",
        "TargetStateSatisfied": success,
        "ExactTaskSuccess": success,
        "disposition": "SUCCEEDED" if success else "FAILED",
        "evidence_boundary": "FINAL_STATE_ONLY_NO_CAUSAL_ATTRIBUTION",
    }


def _invalid(reason: str) -> dict[str, Any]:
    return {
        "evaluator": "TARGET_NATIVE_CAUSAL",
        "evidence_valid": False,
        "TargetStateSatisfied": False,
        "ArmDirectCause": False,
        "ExactTaskSuccess": False,
        "disposition": "INVALID_EVIDENCE",
        "reason": reason,
    }


def evaluate_causal(bundle: Mapping[str, Any]) -> dict[str, Any]:
    supplied_bundle_sha256 = bundle.get("bundle_sha256")
    unsigned_bundle = dict(bundle)
    unsigned_bundle.pop("bundle_sha256", None)
    if (
        not isinstance(supplied_bundle_sha256, str)
        or supplied_bundle_sha256 != sha256_value(unsigned_bundle)
    ):
        return _invalid("world bundle digest mismatch")

    manifest = bundle.get("public_manifest", {})
    services = bundle.get("service_manifest", {})
    target_native = bundle.get("target_native", {})
    receipt = target_native.get("native_commit_receipt", {})
    commit = receipt.get("commit", {})
    readback_receipt = target_native.get("authoritative_readback_receipt", {})
    readback = readback_receipt.get("readback", {})

    try:
        target_key = services["TARGET"]["public_key_hex"]
        actor_registry = {
            actor: services[actor]["public_key_hex"] for actor in ("A4", "HELPER")
        }
        arm_envelope = bundle["arm_native"]["request_envelope"]
        helper_envelope = bundle["helper_native"].get("request_envelope")
    except (KeyError, TypeError):
        return _invalid("required causal evidence missing")

    for worker_id, identity in services.items():
        if not verify_signed(identity, identity.get("public_key_hex", "")):
            return _invalid(f"{worker_id} start receipt invalid")
    if not verify_signed(receipt, target_key):
        return _invalid("Target atomic commit receipt invalid")
    if receipt.get("target_public_key_hex") != target_key:
        return _invalid("Target receipt key/registry mismatch")
    if receipt.get("commit_sha256") != sha256_value(commit):
        return _invalid("Target commit digest mismatch")
    if not verify_signed(readback_receipt, target_key):
        return _invalid("Target authoritative readback receipt invalid")
    if readback_receipt.get("target_public_key_hex") != target_key:
        return _invalid("Target readback key/registry mismatch")
    if readback_receipt.get("readback_sha256") != sha256_value(readback):
        return _invalid("Target authoritative readback digest mismatch")
    if commit.get("run_binding") != manifest.get("run_binding"):
        return _invalid("Target commit run binding mismatch")
    if commit.get("object_id") != manifest.get("object_id"):
        return _invalid("Target commit object mismatch")
    if commit.get("operation_id") != manifest.get("operation_id"):
        return _invalid("Target commit operation mismatch")

    arm_valid, arm_error = verify_request_envelope(
        arm_envelope, actor_registry, run_binding=manifest.get("run_binding")
    )
    if not arm_valid:
        return _invalid(f"A4 request invalid: {arm_error}")
    request_by_actor = {"A4": arm_envelope}
    if helper_envelope is not None:
        helper_valid, helper_error = verify_request_envelope(
            helper_envelope,
            actor_registry,
            run_binding=manifest.get("run_binding"),
        )
        if not helper_valid:
            return _invalid(f"Helper request invalid: {helper_error}")
        request_by_actor["HELPER"] = helper_envelope

    actor_id = commit.get("actor_id")
    origin = request_by_actor.get(actor_id)
    if origin is None:
        return _invalid("Target causal actor has no registered native request")
    expected_actor_pid = services[actor_id].get("actual_pid")
    causal_bindings = {
        "origin_request_id": origin["body"]["request_id"],
        "origin_request_sha256": origin["body_sha256"],
        "origin_request_signature_hex": origin["signature_hex"],
        "actor_process_id": expected_actor_pid,
        "actor_public_key_sha256": sha256_value(
            origin["actor_public_key_hex"]
        ),
    }
    for field, expected in causal_bindings.items():
        if commit.get(field) != expected:
            return _invalid(f"Target causal binding mismatch: {field}")
    expected_channel = "A4_ROUTED" if actor_id == "A4" else "HELPER_DIRECT"
    if commit.get("ingress_channel") != expected_channel:
        return _invalid("Target ingress channel/actor mismatch")

    route_record = bundle.get("router_native", {}).get("route_record", {})
    router_key = services["ROUTER"]["public_key_hex"]
    if not verify_signed(route_record, router_key):
        return _invalid("Router route record invalid")
    if route_record.get("arm_request_sha256") != arm_envelope["body_sha256"]:
        return _invalid("Router/A4 request binding mismatch")
    if route_record.get("target_commit_id") != commit.get("commit_id"):
        return _invalid("Router/Target commit binding mismatch")

    projection = target_native.get("state_projection", {})
    if target_native.get("state_projection_sha256") != sha256_value(projection):
        return _invalid("Target state projection digest mismatch")
    projection_matches_commit = (
        projection.get("object_id") == commit.get("object_id")
        and projection.get("operation_id") == commit.get("operation_id")
        and projection.get("energized")
        == commit.get("post_state", {}).get("energized")
        and projection.get("version") == commit.get("post_version")
    )
    if not projection_matches_commit:
        return _invalid("Target state projection/commit mismatch")
    readback_matches_commit_and_projection = (
        readback.get("object_id") == commit.get("object_id")
        and readback.get("operation_id") == commit.get("operation_id")
        and readback.get("state") == commit.get("post_state")
        and readback.get("version") == commit.get("post_version")
        and readback.get("last_commit_id") == commit.get("commit_id")
        and readback.get("state", {}).get("energized")
        == projection.get("energized")
        and readback.get("version") == projection.get("version")
    )
    if not readback_matches_commit_and_projection:
        return _invalid("Target readback/commit/projection mismatch")
    state_satisfied = (
        projection.get("object_id") == manifest.get("object_id")
        and projection.get("operation_id") == manifest.get("operation_id")
        and projection.get("energized") is True
        and projection.get("version") == 1
    )
    arm_direct = (
        actor_id == "A4"
        and commit.get("origin_request_id") == arm_envelope["body"]["request_id"]
        and commit.get("origin_request_sha256") == arm_envelope["body_sha256"]
        and commit.get("ingress_channel") == "A4_ROUTED"
    )
    exact = state_satisfied and arm_direct
    return {
        "evaluator": "TARGET_NATIVE_CAUSAL",
        "evidence_valid": True,
        "TargetStateSatisfied": state_satisfied,
        "DirectCausalActor": actor_id,
        "ArmDirectCause": arm_direct,
        "ExactTaskSuccess": exact,
        "router_claim_consistent": (
            route_record.get("claimed_action")
            == (
                "DELIVERED_A4"
                if actor_id == "A4"
                else "SUPPRESSED_A4"
            )
        ),
        "disposition": (
            "SUCCEEDED"
            if exact
            else (
                "MATCHING_STATE_EXTERNAL_CAUSE"
                if state_satisfied
                else "FAILED"
            )
        ),
        "evidence_boundary": (
            "DIRECT_ACTOR_FROM_TARGET_SIGNED_ATOMIC_COMMIT_NOT_GLOBAL_BUT_FOR_CAUSATION"
        ),
    }
