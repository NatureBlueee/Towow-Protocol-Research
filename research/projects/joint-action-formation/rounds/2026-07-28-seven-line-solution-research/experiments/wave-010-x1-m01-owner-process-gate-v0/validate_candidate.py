#!/usr/bin/env python3
"""Validate the Wave 010 M01 owner/process gate candidate.

This validator can establish structural binding and exercise signature/refusal
semantics with ephemeral self-test keys.  It cannot create real owner
decisions, resolve executable identities, enforce an OS sandbox, start a
runner, or activate/promote the research object.
"""

from __future__ import annotations

import argparse
import base64
import copy
import datetime as dt
import fnmatch
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent / "wave-010-x1-m01-freeze-bundle-v0"
REQUESTS_PATH = HERE / "owner-commitment-requests.json"
ALLOWLIST_PATH = HERE / "process-allowlist-candidate.json"
MANIFEST_PATH = HERE / "manifest.json"

EXPECTED_CONTENT_ROOT = (
    "c3df52b88c272a056f4d783a394be44194d32a071dba55e3d4caf1c7c45aecf8"
)
EXPECTED_BUNDLE_RAW = (
    "6d34bfdf6764ed58c0d183bbf3e467299767cf50d3870ca213bc6116f94f5bc7"
)
EXPECTED_AUDIT_RAW = (
    "a1ad68ef9bee75958376529a1047ed6ef3e6cf038222f162274a7b6a0857b37b"
)

OWNER_SOURCES = {
    "program-coordinator-domain": {
        "path": FREEZE / "private/g5-domains/program-coordinator.json",
        "raw_sha256": "eb50b90fab3c4b22e552eb56a55ba1467bc5449602c5371e386a6edcc2778805",
        "ledger_head": "d42bca7c014e440e6b7103b625334fe642a712ba64895ea0acb52385a4fdec00",
    },
    "delta-calibration-domain": {
        "path": FREEZE / "private/g5-domains/delta-calibration.json",
        "raw_sha256": "6cc45e9330c6ae24974656ab7bf1629472ea25ecebd25f5a9fb7dc5b241fd330",
        "ledger_head": "4907b0c00291c0ec78035c9ca026844adbd74a2f8e6f5b0ecb7f8ef957cad471",
    },
    "independent-validation-domain": {
        "path": FREEZE / "private/g5-domains/independent-validation.json",
        "raw_sha256": "47f32527c4fb1d0b7ed7f1d5782a4bdf5bd8cfb3b3039d262b6d751d59ac56ed",
        "ledger_head": "85af09cf9381386c31d791f275c84103bbc7f53c6de35b927414c08d49e3ee35",
    },
    "site-data-steward-domain": {
        "path": FREEZE / "private/g5-domains/site-data-steward.json",
        "raw_sha256": "79512b5f53c904abac2ff49055d66552b3e2e75d9f8c40bbb09661db028aecb0",
        "ledger_head": "b53a5289b716be73247e5875dcaefe47985acef9d9f24c966d64aea10604f22f",
    },
}

OWNER_ROLE_BY_DOMAIN = {
    "program-coordinator-domain": "owner-signer-program-coordinator",
    "delta-calibration-domain": "owner-signer-delta-calibration",
    "independent-validation-domain": "owner-signer-independent-validation",
    "site-data-steward-domain": "owner-signer-site-data-steward",
}

METHOD_ROLES = {
    "future-method-strong-center",
    "future-method-mature-composition",
    "future-method-human-interface",
    "future-method-candidate-arm",
}

EXPECTED_ROLES = set(OWNER_ROLE_BY_DOMAIN.values()) | METHOD_ROLES | {
    "future-neutral-controller",
    "future-independent-evaluator",
}

DECISION_BODY_FIELDS = {
    "gate_id",
    "request_id",
    "authority_domain_id",
    "owner_key_id",
    "decision",
    "authorization_payload_sha256",
    "decided_at",
    "expires_at",
    "refusal_reason",
}


class CandidateError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise CandidateError(f"time must carry timezone: {value}")
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CandidateError(message)


def validate_source_closure() -> dict[str, Any]:
    bundle_path = FREEZE / "bundle.json"
    audit_path = FREEZE / "AUDIT-002.md"
    require(sha256_file(bundle_path) == EXPECTED_BUNDLE_RAW, "bundle raw hash drift")
    require(sha256_file(audit_path) == EXPECTED_AUDIT_RAW, "accepted audit hash drift")
    bundle = load_json(bundle_path)
    require(
        bundle["content_root"]["sha256"] == EXPECTED_CONTENT_ROOT,
        "freeze content root drift",
    )
    require(
        bundle["current_truth"]
        == {
            "semantic_episode_candidates": 2,
            "scoreable_episode_candidates": 0,
            "accepted_scoreable_pairs": 0,
            "methods_implemented": 0,
            "runner_implemented": False,
            "runs_completed": 0,
            "coverage_available": False,
        },
        "freeze current-truth boundary drift",
    )
    for domain, expected in OWNER_SOURCES.items():
        require(
            sha256_file(expected["path"]) == expected["raw_sha256"],
            f"{domain} raw source drift",
        )
        source = load_json(expected["path"])
        require(source["authority_domain_id"] == domain, f"{domain} id mismatch")
        require(
            source["ledger_candidates"]["root_candidate_sha256"]
            == expected["ledger_head"],
            f"{domain} ledger head drift",
        )
        require(
            source["ledger_candidates"]["status"] == "CANDIDATE_UNSEALED_NOT_RUN",
            f"{domain} source unexpectedly sealed or run",
        )
    return bundle


def validate_request(request: dict[str, Any]) -> None:
    domain = request["authority_domain_id"]
    require(domain in OWNER_SOURCES, f"unknown authority domain: {domain}")
    source_spec = OWNER_SOURCES[domain]
    source = load_json(source_spec["path"])
    payload = request["authorization_payload"]

    require(request["decision_status"] == "PENDING_OWNER_DECISION", "decision preset")
    require(request["decision_envelope"] is None, "candidate contains owner decision")
    for owner_field in (
        "principal_id",
        "controller_id",
        "agent_entity_id",
        "owner_key_id",
    ):
        require(
            request["owner"][owner_field] == source["truth_owner"][owner_field],
            f"{domain} owner tuple drift at {owner_field}",
        )
    require(payload["authority_domain_id"] == domain, f"{domain} payload id drift")
    require(
        payload["owner_key_id"] == source["truth_owner"]["owner_key_id"],
        f"{domain} key id drift",
    )
    require(
        payload["owner_domain_raw_sha256"] == source_spec["raw_sha256"],
        f"{domain} raw hash not bound",
    )
    require(
        payload["owner_ledger_head"] == source_spec["ledger_head"],
        f"{domain} ledger head not bound",
    )
    require(
        payload["current_head"]["owner_ledger_root_candidate"]
        == source_spec["ledger_head"],
        f"{domain} current head not bound",
    )
    require(
        payload["freeze_bundle_raw_sha256"] == EXPECTED_BUNDLE_RAW,
        f"{domain} bundle bytes not bound",
    )
    require(
        payload["freeze_content_root_sha256"] == EXPECTED_CONTENT_ROOT,
        f"{domain} content root not bound",
    )
    require(
        payload["current_head"]["bundle_content_root"] == EXPECTED_CONTENT_ROOT,
        f"{domain} current bundle head not bound",
    )
    require(
        payload["accepted_audit_raw_sha256"] == EXPECTED_AUDIT_RAW,
        f"{domain} audit decision not bound",
    )
    require(
        payload["relation_coordinate"] == source["relation_coordinate"],
        f"{domain} relation coordinate drift",
    )
    require(payload["scope"] == source["truth_owner"]["exclusive_signing_scope"], "scope drift")
    require(
        "do not authorize a run" in payload["purpose"],
        f"{domain} purpose does not preserve not-run boundary",
    )
    require(payload["controller_proxy_signature_forbidden"] is True, "proxy not forbidden")
    require(payload["automatic_activation_or_promotion"] is False, "auto promotion enabled")
    not_before = parse_time(payload["not_before"])
    expires = parse_time(payload["expires_at"])
    require(not_before < expires, f"{domain} invalid validity interval")
    require(
        sha256_bytes(canonical_bytes(payload)) == request["authorization_payload_sha256"],
        f"{domain} authorization payload hash mismatch",
    )


def validate_requests_document(document: dict[str, Any]) -> list[dict[str, Any]]:
    require(document["status"] == "CANDIDATE_UNSIGNED_NOT_RUN", "request status drift")
    require(
        document["research_controller"]["may_sign_for_any_owner"] is False,
        "controller proxy signing enabled",
    )
    require(
        document["composition_rule"]["automatic_activation_or_promotion"] is False,
        "composition auto activation enabled",
    )
    requests = document["requests"]
    require(len(requests) == 4, "exactly four owner requests required")
    domains = [request["authority_domain_id"] for request in requests]
    require(set(domains) == set(OWNER_SOURCES), "owner-domain closure mismatch")
    require(len(domains) == len(set(domains)), "duplicate owner domain")
    request_ids = [request["request_id"] for request in requests]
    require(len(request_ids) == len(set(request_ids)), "duplicate request id")
    for request in requests:
        validate_request(request)
    return requests


def path_matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def validate_allowlist(document: dict[str, Any]) -> list[dict[str, Any]]:
    require(
        document["status"] == "CANDIDATE_IDENTITIES_UNRESOLVED_NOT_ENFORCED",
        "allowlist status overclaims enforcement",
    )
    require(document["runner_implemented"] is False, "runner unexpectedly implemented")
    enforcement = document["enforcement"]
    require(enforcement["active"] is False, "enforcement unexpectedly active")
    require(
        enforcement["path_allowlist_alone_is_security_boundary"] is False,
        "path list overclaimed as security boundary",
    )
    require(
        enforcement["same_uid_malicious_process_excluded"] is False,
        "same-UID malicious process incorrectly excluded",
    )
    processes = document["processes"]
    by_role = {process["role_id"]: process for process in processes}
    require(len(by_role) == len(processes), "duplicate process role")
    require(set(by_role) == EXPECTED_ROLES, "process role closure mismatch")

    for process in processes:
        require(process["identity_status"] == "UNRESOLVED_EXECUTABLE", "identity fabricated")
        require(process["executable_identity"] is None, "unresolved identity has value")
        require(process["network"] == "DENY", "network is not deny-by-default")

    all_domain_paths = {
        domain: f"../wave-010-x1-m01-freeze-bundle-v0/private/g5-domains/"
        f"{OWNER_SOURCES[domain]['path'].name}"
        for domain in OWNER_SOURCES
    }
    for domain, role in OWNER_ROLE_BY_DOMAIN.items():
        process = by_role[role]
        require(process["authority_domain_id"] == domain, f"{role} domain drift")
        own_path = all_domain_paths[domain]
        require(own_path in process["read_allowlist"], f"{role} cannot read own source")
        require(len(process["write_allowlist"]) == 1, f"{role} has broad write scope")
        denied = process["explicit_denies"]
        for other_domain, other_path in all_domain_paths.items():
            if other_domain != domain:
                require(other_path in denied, f"{role} can read other owner {other_domain}")
        require(
            process["private_key_provider"]
            == "EXTERNAL_OWNER_CONTROLLED_PROVIDER_UNRESOLVED",
            f"{role} private key provider falsely resolved",
        )

    method_output_roots: set[str] = set()
    for role in METHOD_ROLES:
        process = by_role[role]
        require(
            not any("/private/" in path or "/certificates/" in path for path in process["read_allowlist"]),
            f"{role} method-visible read surface leaks private truth",
        )
        require(
            "../wave-010-x1-m01-freeze-bundle-v0/private/**"
            in process["explicit_denies"],
            f"{role} lacks private deny",
        )
        require("owner-decisions/**" in process["explicit_denies"], f"{role} sees owner decisions")
        require(len(process["write_allowlist"]) == 1, f"{role} has broad write scope")
        output_root = process["write_allowlist"][0]
        require(output_root not in method_output_roots, "method output collision")
        method_output_roots.add(output_root)

    controller = by_role["future-neutral-controller"]
    require(controller["owner_signature_capability"] == "NONE", "controller can sign")
    require("owner-decisions/**" in controller["write_denies"], "controller can write decisions")
    require(
        "../wave-010-x1-m01-freeze-bundle-v0/private/**"
        in controller["read_denies"],
        "controller can read private truth",
    )
    evaluator = by_role["future-independent-evaluator"]
    require(evaluator["owner_signature_capability"] == "NONE", "evaluator can sign")
    for protected in (
        "owner-decisions/**",
        "future-method-outputs/**",
        "future-controller-state/**",
    ):
        require(protected in evaluator["write_denies"], f"evaluator can mutate {protected}")

    user_gate = document["user_decision_gate"]
    require(user_gate["required_after_owner_decisions_and_identity_resolution"] is True, "user gate missing")
    require(user_gate["automatic_activation_or_promotion"] is False, "user gate auto activates")
    return processes


def validate_manifest(document: dict[str, Any]) -> None:
    require(
        document["status"]
        == "STRUCTURAL_CANDIDATE_UNSIGNED_IDENTITIES_UNRESOLVED_NOT_RUN",
        "manifest status overclaims readiness",
    )
    source = document["source_freeze"]
    require(source["bundle_raw_sha256"] == EXPECTED_BUNDLE_RAW, "manifest bundle drift")
    require(
        source["content_root_sha256"] == EXPECTED_CONTENT_ROOT,
        "manifest content root drift",
    )
    require(
        source["accepted_audit_raw_sha256"] == EXPECTED_AUDIT_RAW,
        "manifest audit drift",
    )
    artifacts = {entry["path"]: entry["raw_sha256"] for entry in document["artifacts"]}
    require(
        set(artifacts)
        == {
            "owner-commitment-requests.json",
            "process-allowlist-candidate.json",
            "validate_candidate.py",
        },
        "manifest artifact closure mismatch",
    )
    for relative_path, expected_hash in artifacts.items():
        require(
            sha256_file(HERE / relative_path) == expected_hash,
            f"manifest artifact drift: {relative_path}",
        )
    not_satisfied = document["not_satisfied"]
    require(not_satisfied["real_owner_public_keys"] == 0, "public keys fabricated")
    require(not_satisfied["real_owner_signatures"] == 0, "signatures fabricated")
    require(not_satisfied["resolved_executable_identities"] == 0, "identities fabricated")
    require(not_satisfied["os_enforcement_profiles"] == 0, "enforcement fabricated")
    require(not_satisfied["runner_implemented"] is False, "runner fabricated")
    require(not_satisfied["formal_status_changed"] is False, "formal state changed")


def make_decision_body(
    request: dict[str, Any],
    decision: str,
    *,
    decided_at: str = "2026-07-30T00:00:00Z",
    refusal_reason: str | None = None,
) -> dict[str, Any]:
    payload = request["authorization_payload"]
    if decision == "REFUSE" and not refusal_reason:
        refusal_reason = "owner declines this exact candidate"
    if decision == "AUTHORIZE_EXACT_CANDIDATE":
        refusal_reason = None
    return {
        "gate_id": payload["gate_id"],
        "request_id": request["request_id"],
        "authority_domain_id": request["authority_domain_id"],
        "owner_key_id": request["owner"]["owner_key_id"],
        "decision": decision,
        "authorization_payload_sha256": request["authorization_payload_sha256"],
        "decided_at": decided_at,
        "expires_at": payload["expires_at"],
        "refusal_reason": refusal_reason,
    }


def sign_body(body: dict[str, Any], private_key: Ed25519PrivateKey) -> dict[str, Any]:
    return {
        "decision_body": body,
        "signature_b64": base64.b64encode(
            private_key.sign(canonical_bytes(body))
        ).decode("ascii"),
    }


def validate_decision_envelope(
    request: dict[str, Any],
    envelope: dict[str, Any],
    owner_public_key: Ed25519PublicKey,
    *,
    effective_at: str,
) -> str:
    body = envelope["decision_body"]
    require(set(body) == DECISION_BODY_FIELDS, "decision body field closure mismatch")
    require(body["gate_id"] == request["authorization_payload"]["gate_id"], "gate id drift")
    require(body["request_id"] == request["request_id"], "request id drift")
    require(body["authority_domain_id"] == request["authority_domain_id"], "domain drift")
    require(body["owner_key_id"] == request["owner"]["owner_key_id"], "owner key id drift")
    require(
        body["authorization_payload_sha256"] == request["authorization_payload_sha256"],
        "decision does not bind exact authorization payload",
    )
    require(
        body["expires_at"] == request["authorization_payload"]["expires_at"],
        "decision expiry does not bind request expiry",
    )
    require(
        body["decision"] in {"AUTHORIZE_EXACT_CANDIDATE", "REFUSE"},
        "unregistered owner decision",
    )
    if body["decision"] == "REFUSE":
        require(
            isinstance(body["refusal_reason"], str) and body["refusal_reason"].strip(),
            "signed refusal lacks reason",
        )
    else:
        require(body["refusal_reason"] is None, "authorization carries refusal reason")

    decided = parse_time(body["decided_at"])
    not_before = parse_time(request["authorization_payload"]["not_before"])
    expires = parse_time(body["expires_at"])
    effective = parse_time(effective_at)
    require(not_before <= decided <= expires, "decision time outside request interval")
    require(decided <= effective <= expires, "decision not current at effective time")
    try:
        owner_public_key.verify(
            base64.b64decode(envelope["signature_b64"], validate=True),
            canonical_bytes(body),
        )
    except (InvalidSignature, ValueError) as error:
        raise CandidateError("invalid owner signature") from error
    return body["decision"]


def compose_gate_state(
    requests: list[dict[str, Any]],
    envelopes: dict[str, dict[str, Any]],
    public_keys: dict[str, Ed25519PublicKey],
    *,
    effective_at: str,
) -> str:
    decisions: list[str] = []
    for request in requests:
        request_id = request["request_id"]
        envelope = envelopes.get(request_id)
        key_id = request["owner"]["owner_key_id"]
        public_key = public_keys.get(key_id)
        if envelope is None or public_key is None:
            return "NOT_AUTHORIZED"
        try:
            decisions.append(
                validate_decision_envelope(
                    request, envelope, public_key, effective_at=effective_at
                )
            )
        except CandidateError:
            return "NOT_AUTHORIZED"
    if "REFUSE" in decisions:
        return "BLOCKED_BY_OWNER_REFUSAL"
    if decisions == ["AUTHORIZE_EXACT_CANDIDATE"] * 4:
        return "READY_FOR_EXPLICIT_USER_DECISION"
    return "NOT_AUTHORIZED"


def expect_failure(callable_object: Any, label: str) -> None:
    try:
        callable_object()
    except CandidateError:
        return
    raise AssertionError(f"expected fail-closed result: {label}")


def run_self_test(requests: list[dict[str, Any]], allowlist: dict[str, Any]) -> None:
    owner_private_keys = {
        request["owner"]["owner_key_id"]: Ed25519PrivateKey.generate()
        for request in requests
    }
    owner_public_keys = {
        key_id: private.public_key() for key_id, private in owner_private_keys.items()
    }
    authorize_envelopes = {
        request["request_id"]: sign_body(
            make_decision_body(request, "AUTHORIZE_EXACT_CANDIDATE"),
            owner_private_keys[request["owner"]["owner_key_id"]],
        )
        for request in requests
    }
    state = compose_gate_state(
        requests,
        authorize_envelopes,
        owner_public_keys,
        effective_at="2026-07-31T00:00:00Z",
    )
    require(state == "READY_FOR_EXPLICIT_USER_DECISION", "four signatures bypassed user gate")

    # Every owner can independently refuse.  A refusal is not converted to an
    # authorization by the three other valid signatures.
    for request in requests:
        envelopes = copy.deepcopy(authorize_envelopes)
        envelopes[request["request_id"]] = sign_body(
            make_decision_body(request, "REFUSE"),
            owner_private_keys[request["owner"]["owner_key_id"]],
        )
        state = compose_gate_state(
            requests,
            envelopes,
            owner_public_keys,
            effective_at="2026-07-31T00:00:00Z",
        )
        require(state == "BLOCKED_BY_OWNER_REFUSAL", "independent refusal overridden")

    # A research-controller signature cannot be relabelled as an owner signature.
    controller_key = Ed25519PrivateKey.generate()
    first = requests[0]
    proxy_envelopes = copy.deepcopy(authorize_envelopes)
    proxy_envelopes[first["request_id"]] = sign_body(
        make_decision_body(first, "AUTHORIZE_EXACT_CANDIDATE"), controller_key
    )
    require(
        compose_gate_state(
            requests,
            proxy_envelopes,
            owner_public_keys,
            effective_at="2026-07-31T00:00:00Z",
        )
        == "NOT_AUTHORIZED",
        "controller proxy signature accepted",
    )

    # Exact bytes/hash/head/purpose/expiry are all inside the authorization
    # payload hash.  Mutating any one must invalidate the request.
    for mutation_name, mutate in (
        ("bundle bytes", lambda p: p.__setitem__("freeze_bundle_raw_sha256", "0" * 64)),
        ("head", lambda p: p["current_head"].__setitem__("bundle_content_root", "0" * 64)),
        ("purpose", lambda p: p.__setitem__("purpose", "different purpose")),
        ("expiry", lambda p: p.__setitem__("expires_at", "2026-08-06T00:00:00Z")),
    ):
        mutated = copy.deepcopy(first)
        mutate(mutated["authorization_payload"])
        expect_failure(lambda item=mutated: validate_request(item), mutation_name)

    expired = copy.deepcopy(authorize_envelopes[first["request_id"]])
    expect_failure(
        lambda: validate_decision_envelope(
            first,
            expired,
            owner_public_keys[first["owner"]["owner_key_id"]],
            effective_at="2026-08-06T00:00:00Z",
        ),
        "expired decision",
    )

    missing_one = dict(authorize_envelopes)
    missing_one.pop(first["request_id"])
    require(
        compose_gate_state(
            requests,
            missing_one,
            owner_public_keys,
            effective_at="2026-07-31T00:00:00Z",
        )
        == "NOT_AUTHORIZED",
        "missing owner was inferred",
    )

    # Candidate allowlist is intentionally not executable or enforced.
    require(allowlist["enforcement"]["active"] is False, "self-test activated enforcement")
    require(
        all(process["executable_identity"] is None for process in allowlist["processes"]),
        "self-test fabricated executable identity",
    )
    for process in allowlist["processes"]:
        if process["role_id"] in METHOD_ROLES:
            require(
                path_matches_any(
                    "../wave-010-x1-m01-freeze-bundle-v0/private/g5-fragments.json",
                    process["explicit_denies"],
                ),
                f"{process['role_id']} private deny not effective",
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    validate_source_closure()
    request_document = load_json(REQUESTS_PATH)
    requests = validate_requests_document(request_document)
    allowlist = load_json(ALLOWLIST_PATH)
    validate_allowlist(allowlist)
    validate_manifest(load_json(MANIFEST_PATH))
    if args.self_test:
        run_self_test(requests, allowlist)

    result = {
        "structural_candidate": "PASS",
        "self_test": "PASS" if args.self_test else "NOT_RUN",
        "real_owner_signatures": 0,
        "owner_public_keys_resolved": 0,
        "executable_identities_resolved": 0,
        "os_enforcement_active": False,
        "runner_implemented": False,
        "gate_state": "NOT_AUTHORIZED",
        "automatic_activation_or_promotion": False,
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
