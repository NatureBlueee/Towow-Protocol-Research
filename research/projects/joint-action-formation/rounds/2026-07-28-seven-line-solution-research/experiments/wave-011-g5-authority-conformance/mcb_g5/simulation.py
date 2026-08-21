from __future__ import annotations

import base64
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .common import canonical_bytes, load_json, sha256
from .native_adapter import derive_business_outcome


OWNER_IDS = [
    "program-coordinator",
    "delta-calibration",
    "independent-validation",
    "site-data-steward",
]


class JsonLineProcess:
    def __init__(self, argv: list[str]) -> None:
        self.process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    @property
    def pid(self) -> int:
        return self.process.pid

    def request(self, value: dict[str, Any]) -> dict[str, Any]:
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(json.dumps(value, sort_keys=True) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"worker exited without response: {stderr}")
        return json.loads(line)

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=2)
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()


def verify_envelope(envelope: dict[str, Any]) -> bool:
    public_key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(envelope["public_key_ed25519_b64"])
    )
    try:
        public_key.verify(
            base64.b64decode(envelope["signature_ed25519_b64"]),
            canonical_bytes(envelope["payload"]),
        )
    except Exception:
        return False
    return True


class OwnerCluster:
    def __init__(self, root: Path, runtime: Path) -> None:
        worker = root / "workers" / "owner_service.py"
        self.clients: dict[str, JsonLineProcess] = {}
        self.hello: dict[str, dict[str, Any]] = {}
        for owner_id in OWNER_IDS:
            owner_dir = runtime / owner_id
            client = JsonLineProcess(
                [
                    sys.executable,
                    str(worker),
                    "--owner-id",
                    owner_id,
                    "--store",
                    str(owner_dir / "store.json"),
                    "--key",
                    str(owner_dir / "owner-key.pem"),
                ]
            )
            self.clients[owner_id] = client
            self.hello[owner_id] = client.request({"op": "HELLO"})

    def close(self) -> None:
        for client in self.clients.values():
            client.close()

    def reset(self) -> None:
        for client in self.clients.values():
            client.request({"op": "MUTATE", "kind": "RESET"})

    def read_all(self) -> dict[str, dict[str, Any]]:
        return {
            owner_id: client.request({"op": "READ"})
            for owner_id, client in self.clients.items()
        }

    def active_heads(
        self, reads: dict[str, dict[str, Any]]
    ) -> tuple[bool, dict[str, int], str | None]:
        heads: dict[str, int] = {}
        for owner_id, result in reads.items():
            if result["status"] != "OK":
                return False, heads, result["status"]
            envelope = result["envelope"]
            if not verify_envelope(envelope):
                return False, heads, "INVALID_SIGNATURE"
            body = envelope["payload"]["body"]
            if body.get("fork_views"):
                return False, heads, "FORKED_HEAD"
            if body["mandate"] != "ACTIVE" or body["stance"] != "SUPPORT":
                return False, heads, "AUTHORITATIVE_REJECT_OR_REVOKE"
            heads[owner_id] = int(envelope["payload"]["owner_head"])
        return True, heads, None

    def sign_all(
        self, operation_hash: str, heads: dict[str, int]
    ) -> dict[str, dict[str, Any]]:
        return {
            owner_id: client.request(
                {
                    "op": "SIGN",
                    "operation_hash": operation_hash,
                    "expected_head": heads[owner_id],
                }
            )
            for owner_id, client in self.clients.items()
        }


def run_native_conformance(root: Path) -> dict[str, Any]:
    inputs = load_json(root / "fixtures" / "native-inputs.json")
    oracle_path = root / "fixtures" / "oracles" / "native-expected.json"
    oracle = load_json(oracle_path)["cases"]
    worker = root / "workers" / "local_policy_engine.py"
    rows = []
    for case in inputs["cases"]:
        raw_input = canonical_bytes(case)
        completed = subprocess.run(
            [sys.executable, str(worker)],
            input=raw_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        native = json.loads(completed.stdout)
        mapped = derive_business_outcome(native)
        expected = oracle[case["case_id"]]
        rows.append(
            {
                "case_id": case["case_id"],
                "worker_exit": completed.returncode,
                "worker_input_sha256": sha256(raw_input),
                "worker_stdout_sha256": sha256(completed.stdout),
                "native_record": native,
                "mapped_record": mapped,
                "native_exact": native["native_outcome"]
                == expected["native_outcome"],
                "business_exact": mapped["business_outcome"]
                == expected["business_outcome"],
            }
        )
    provider_inputs = load_json(root / "fixtures" / "provider-adapter-inputs.json")
    provider_oracle = load_json(
        root / "fixtures" / "oracles" / "provider-adapter-expected.json"
    )["cases"]
    provider_rows = []
    for native_shape in provider_inputs["cases"]:
        mapped = derive_business_outcome(native_shape)
        provider_rows.append(
            {
                "case_id": native_shape["case_id"],
                "provider": native_shape["native_engine"],
                "native_shape": native_shape,
                "mapped_record": mapped,
                "business_exact": (
                    mapped["business_outcome"]
                    == provider_oracle[native_shape["case_id"]]
                ),
                "execution_status": "SYNTHETIC_NATIVE_SHAPE_PRODUCT_NOT_RUN",
            }
        )
    return {
        "engine_runs": {
            "LOCAL_REFERENCE_POLICY_ENGINE": "RUN",
            "OPA": "NOT_RUN_ENGINE_NOT_INSTALLED",
            "CEDAR": "NOT_RUN_ENGINE_NOT_INSTALLED",
            "OPENFGA": "NOT_RUN_ENGINE_NOT_INSTALLED",
            "XACML": "NOT_RUN_ENGINE_NOT_INSTALLED",
        },
        "oracle_visibility": "WORKER_RECEIVES_CASE_ONLY_EVALUATOR_READS_ORACLE_AFTER_SEAL",
        "rows": rows,
        "provider_adapter_corpus": {
            "status": provider_inputs["status"],
            "rows": provider_rows,
            "all_business_exact": all(
                row["business_exact"] for row in provider_rows
            ),
        },
        "all_native_exact": all(row["native_exact"] for row in rows),
        "all_business_exact": all(row["business_exact"] for row in rows),
        "claim_boundary": (
            "Local executable engine conformance only; no OPA/Cedar/OpenFGA/XACML "
            "product result is claimed."
        ),
    }


def run_owner_independence(cluster: OwnerCluster) -> dict[str, Any]:
    cluster.reset()
    before = cluster.read_all()
    observations: dict[str, Any] = {}
    mutations = {
        "program-coordinator": "REJECT",
        "delta-calibration": "REVOKE",
        "independent-validation": "OUTAGE",
        "site-data-steward": "FORK",
    }
    for owner_id, kind in mutations.items():
        cluster.reset()
        initial = cluster.read_all()
        mutation = cluster.clients[owner_id].request({"op": "MUTATE", "kind": kind})
        after = cluster.read_all()
        unchanged_others = True
        for other_id in OWNER_IDS:
            if other_id == owner_id:
                continue
            left = initial[other_id]["envelope"]["payload"]
            right = after[other_id]["envelope"]["payload"]
            unchanged_others &= left == right
        observations[owner_id] = {
            "mutation": kind,
            "mutation_result": mutation,
            "owner_read_after": after[owner_id],
            "other_owner_state_unchanged": unchanged_others,
        }
    hellos = cluster.hello
    return {
        "owners": {
            owner_id: {
                "pid": cluster.clients[owner_id].pid,
                "store": hello["store"],
                "public_key_ed25519_b64": hello["public_key_ed25519_b64"],
            }
            for owner_id, hello in hellos.items()
        },
        "distinct_processes": len({client.pid for client in cluster.clients.values()})
        == 4,
        "distinct_stores": len({hello["store"] for hello in hellos.values()}) == 4,
        "distinct_public_keys": len(
            {hello["public_key_ed25519_b64"] for hello in hellos.values()}
        )
        == 4,
        "initial_reads_signed": all(
            item["status"] == "OK" and verify_envelope(item["envelope"])
            for item in before.values()
        ),
        "fault_observations": observations,
    }


def run_authority_strata(
    root: Path, cluster: OwnerCluster, operation_hash: str
) -> dict[str, Any]:
    worlds = load_json(root / "fixtures" / "authority-worlds.json")
    rows = []
    for stratum in worlds["strata"]:
        cluster.reset()
        reads = cluster.read_all()
        valid, heads, reason = cluster.active_heads(reads)
        signs = cluster.sign_all(operation_hash, heads) if valid else {}
        composition_signed = bool(signs) and all(
            result["status"] == "SIGNED"
            and verify_envelope(result["envelope"])
            for result in signs.values()
        )
        external = stratum["external_non_delegable_right"]
        effect_external = not stratum["all_effect_domains_accept_center_write"]
        strategies = {
            "PERMISSION_ONLY_CENTER": (
                "ALLOW",
                "FALSE_ALLOW" if external else "CORRECT",
            ),
            "AUTHORITY_AWARE_STRONG_CENTER": (
                "QUERY_EXTERNAL_OWNER" if external else "ALLOW_DIRECT",
                "CORRECT",
            ),
            "MATURE_COMPOSITION": (
                "ALLOW_WITH_OWNER_RECEIPTS"
                if composition_signed
                else f"STOP_{reason or 'SIGN_FAILURE'}",
                "CORRECT" if composition_signed else "SAFE_STOP",
            ),
            "CLM_HITL": (
                "ALLOW_AFTER_EXACT_OWNER_APPROVAL"
                if composition_signed
                else "DEFER_HUMAN_OR_OWNER",
                "CORRECT",
            ),
            "HUMAN_RULES": (
                "ALLOW_AFTER_OWNER_RULE_AND_SIGNATURE"
                if composition_signed
                else "DEFER_HUMAN_OR_OWNER",
                "CORRECT",
            ),
        }
        if effect_external:
            strategies["AUTHORITY_AWARE_STRONG_CENTER"] = (
                "OUTBOX_FENCE_TARGET_READBACK"
                if stratum["id"].startswith("X_")
                else strategies["AUTHORITY_AWARE_STRONG_CENTER"][0],
                "CORRECT",
            )
        rows.append(
            {
                "stratum": stratum,
                "owner_receipts_available": composition_signed,
                "strategies": {
                    name: {"route": route, "assessment": assessment}
                    for name, (route, assessment) in strategies.items()
                },
            }
        )
    return {
        "rows": rows,
        "paired_variable": "AUTHORITY_OWNERSHIP_ONLY_TECHNICAL_PERMISSIONS_IDENTICAL",
        "positive_results_allowed": [
            "strong center wins in true unified Authority",
            "mature composition fully closes external-owner world",
            "CLM/HITL or human rules win on lifecycle cost",
        ],
    }


def _race_inject(cluster: OwnerCluster, boundary: str, step: int) -> dict[str, Any]:
    return cluster.clients["site-data-steward"].request(
        {
            "op": "MUTATE",
            "kind": "REVOKE",
            "effective_step": step,
            "published_step": step,
            "boundary": boundary,
        }
    )


def run_races(
    root: Path, cluster: OwnerCluster, operation_hash: str, runtime: Path
) -> dict[str, Any]:
    boundaries = ["read", "re-read", "sign", "reserve", "execute"]
    strategies = [
        "NO_COMMON_TRANSACTION",
        "BOUNDED_LEASE_CONFIRM",
        "TWO_PC_LIKE_HOLD",
        "SAGA_COMPENSATION",
        "TRUE_UNIFIED_CENTER",
    ]
    rows = []
    resource_owner = cluster.clients["delta-calibration"]
    target_worker = root / "workers" / "target_service.py"
    for strategy in strategies:
        for stratum in ["U_TRUE_UNIFIED_AUTHORITY", "P_SAME_PERMISSION_EXTERNAL_RIGHT"]:
            for boundary in boundaries:
                cluster.reset()
                target_store = runtime / "race-targets" / strategy / stratum / f"{boundary}.json"
                target = JsonLineProcess(
                    [
                        sys.executable,
                        str(target_worker),
                        "--store",
                        str(target_store),
                        "--mode",
                        "strict",
                    ]
                )
                trace: list[dict[str, Any]] = []
                held = False
                transient_effect = False
                compensated = False
                stopped_reason: str | None = None
                try:
                    if strategy == "TRUE_UNIFIED_CENTER":
                        if stratum.startswith("P_"):
                            rows.append(
                                {
                                    "strategy": strategy,
                                    "stratum": stratum,
                                    "race_after": boundary,
                                    "effect": False,
                                    "transient_stale_effect": False,
                                    "compensated": False,
                                    "safe_final_state": True,
                                    "blocking_hold": False,
                                    "stopped_reason": "NOT_APPLICABLE_EXTERNAL_NON_DELEGABLE_RIGHT",
                                    "trace": [],
                                }
                            )
                            continue
                        # In U the center owns the state and commits in one domain.
                        rows.append(
                            {
                                "strategy": strategy,
                                "stratum": stratum,
                                "race_after": boundary,
                                "effect": boundary != "read",
                                "transient_stale_effect": False,
                                "compensated": False,
                                "safe_final_state": True,
                                "blocking_hold": False,
                                "stopped_reason": (
                                    "ATOMIC_REVOKE_WON" if boundary == "read" else None
                                ),
                                "trace": [
                                    {
                                        "event": "SINGLE_DOMAIN_SERIALIZATION",
                                        "winner": (
                                            "REVOKE" if boundary == "read" else "EXECUTE"
                                        ),
                                    }
                                ],
                            }
                        )
                        continue

                    reads = cluster.read_all()
                    trace.append({"event": "READ", "statuses": _statuses(reads)})
                    if boundary == "read":
                        trace.append(
                            {"event": "RACE", "result": _race_inject(cluster, boundary, 1)}
                        )

                    if strategy == "TWO_PC_LIKE_HOLD":
                        hold_results = {
                            owner_id: client.request(
                                {"op": "HOLD", "hold_id": f"hold-{boundary}"}
                            )
                            for owner_id, client in cluster.clients.items()
                        }
                        held = all(item["status"] == "HELD" for item in hold_results.values())
                        trace.append({"event": "HOLD", "statuses": _statuses(hold_results)})

                    rereads = cluster.read_all()
                    trace.append({"event": "RE_READ", "statuses": _statuses(rereads)})
                    valid, heads, reason = cluster.active_heads(rereads)
                    if not valid:
                        stopped_reason = reason
                    if boundary == "re-read" and stopped_reason is None:
                        trace.append(
                            {"event": "RACE", "result": _race_inject(cluster, boundary, 2)}
                        )

                    signs: dict[str, Any] = {}
                    if stopped_reason is None:
                        signs = cluster.sign_all(operation_hash, heads)
                        trace.append({"event": "SIGN", "statuses": _statuses(signs)})
                        if not all(item["status"] == "SIGNED" for item in signs.values()):
                            stopped_reason = "SIGN_REJECTED_OR_STALE"
                    if boundary == "sign" and stopped_reason is None:
                        trace.append(
                            {"event": "RACE", "result": _race_inject(cluster, boundary, 3)}
                        )

                    reservation: dict[str, Any] | None = None
                    if stopped_reason is None:
                        reservation = resource_owner.request(
                            {
                                "op": "RESERVE",
                                "slot": "delta-field-slot-2026-08-01",
                                "operation_hash": operation_hash,
                            }
                        )
                        trace.append({"event": "RESERVE", "status": reservation["status"]})
                        if reservation["status"] not in {"RESERVED", "IDEMPOTENT_REPLAY"}:
                            stopped_reason = reservation["status"]
                    if boundary == "reserve" and stopped_reason is None:
                        trace.append(
                            {"event": "RACE", "result": _race_inject(cluster, boundary, 4)}
                        )

                    if (
                        stopped_reason is None
                        and strategy == "BOUNDED_LEASE_CONFIRM"
                    ):
                        confirms = cluster.read_all()
                        ok, _, confirm_reason = cluster.active_heads(confirms)
                        trace.append({"event": "CONFIRM", "statuses": _statuses(confirms)})
                        if not ok:
                            stopped_reason = f"CONFIRM_{confirm_reason}"

                    effect = False
                    if stopped_reason is None and reservation is not None:
                        fence = int(reservation["fence"])
                        target.request({"op": "ADVANCE", "fence": fence, "region": "A"})
                        executed = target.request(
                            {
                                "op": "EXECUTE",
                                "fence": fence,
                                "operation_hash": operation_hash,
                                "region": "A",
                            }
                        )
                        effect = executed["status"] == "EFFECT_CREATED"
                        trace.append({"event": "EXECUTE", "result": executed})
                        if boundary == "execute":
                            trace.append(
                                {
                                    "event": "RACE",
                                    "result": _race_inject(cluster, boundary, 5),
                                }
                            )

                    final_reads = cluster.read_all()
                    final_valid, _, final_reason = cluster.active_heads(final_reads)
                    if effect and not final_valid and boundary != "execute":
                        transient_effect = True
                        if strategy == "SAGA_COMPENSATION":
                            compensated = True
                            trace.append({"event": "COMPENSATE", "status": "RECORDED"})

                    if held:
                        release_results = {
                            owner_id: client.request(
                                {"op": "RELEASE", "hold_id": f"hold-{boundary}"}
                            )
                            for owner_id, client in cluster.clients.items()
                        }
                        trace.append(
                            {"event": "RELEASE", "statuses": _statuses(release_results)}
                        )

                    safe = not transient_effect or compensated
                    rows.append(
                        {
                            "strategy": strategy,
                            "stratum": stratum,
                            "race_after": boundary,
                            "effect": effect,
                            "transient_stale_effect": transient_effect,
                            "compensated": compensated,
                            "safe_final_state": safe,
                            "stopped_reason": stopped_reason or final_reason,
                            "blocking_hold": held,
                            "trace": trace,
                        }
                    )
                finally:
                    target.close()
    return {
        "rows": rows,
        "boundaries": boundaries,
        "guarantee_boundary": (
            "Only true unified Authority is modeled as single-domain atomic. "
            "Other strategies are coordination, bounded hold, or compensation."
        ),
    }


def _statuses(values: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {key: value["status"] for key, value in values.items()}


def run_fence_matrix(root: Path, runtime: Path, operation_hash: str) -> dict[str, Any]:
    target_worker = root / "workers" / "target_service.py"
    rows = []
    for mode in ["strict", "ignore", "restart_loss", "cross_region_reorder"]:
        store = runtime / "fence-targets" / f"{mode}.json"
        target = JsonLineProcess(
            [
                sys.executable,
                str(target_worker),
                "--store",
                str(store),
                "--mode",
                mode,
            ]
        )
        try:
            target.request({"op": "ADVANCE", "fence": 2, "region": "A"})
            if mode == "restart_loss":
                target.request({"op": "RESTART"})
            result = target.request(
                {
                    "op": "EXECUTE",
                    "fence": 1,
                    "operation_hash": operation_hash,
                    "region": "B" if mode == "cross_region_reorder" else "A",
                }
            )
            readback = target.request({"op": "READBACK"})
            stale_effect = result["status"] == "EFFECT_CREATED" and 1 < 2
            rows.append(
                {
                    "mode": mode,
                    "execute_result": result,
                    "stale_effect_by_authoritative_epoch": stale_effect,
                    "target_readback": readback,
                    "expected_safe": mode == "strict",
                }
            )
        finally:
            target.close()
    return {
        "rows": rows,
        "all_failure_modes_exposed": all(
            (row["mode"] == "strict" and not row["stale_effect_by_authoritative_epoch"])
            or (row["mode"] != "strict" and row["stale_effect_by_authoritative_epoch"])
            for row in rows
        ),
        "claim_boundary": "A fence exists only where the target enforces and persists monotonic epochs.",
    }


def run_materiality_standing_migration(root: Path) -> dict[str, Any]:
    fixture = load_json(root / "fixtures" / "materiality-standing-migration.json")
    material_rows = []
    for case in fixture["material_closure_cases"]:
        if case["materiality_rule"] is None:
            decision = "UNKNOWN"
        elif case["sidecar_changed"] or case["external_dependency_changed"]:
            decision = "REAUTHORIZE"
        elif case["canonical_semantics_equal"]:
            decision = "SAME_OPERATION_CLOSURE"
        else:
            decision = "REAUTHORIZE"
        material_rows.append(
            {
                "case_id": case["case_id"],
                "decision": decision,
                "expected": case["expected"],
                "exact": decision == case["expected"],
            }
        )

    standing_rows = []
    for case in fixture["standing_cases"]:
        if case["standing"] == "ADJUDICATED" and case["effect"] == "SUSPEND_EXECUTE":
            decision = "DEFER"
        elif case["standing"] == "LATE_ADJUDICATED":
            decision = "LATE_REOPEN"
        elif case["jurisdiction"] == "CONFLICTING_RULES":
            decision = "DEFER"
        elif case["standing"] == "REJECTED":
            decision = "CONTINUE_WITH_AUDIT"
        else:
            decision = "UNKNOWN"
        standing_rows.append(
            {
                "case_id": case["case_id"],
                "decision": decision,
                "expected": case["expected"],
                "exact": decision == case["expected"],
            }
        )

    migration_rows = []
    for mapping in ["FAITHFUL", "LOSSY"]:
        case_rows = []
        for case in fixture["migration_cases"]:
            source = case["source"]
            target = dict(source)
            if mapping == "LOSSY":
                target.pop("forbid", None)
                target.pop("unknown", None)
                target.pop("owner", None)
                target.pop("source_bytes_hash", None)
            preserved = target == source
            case_rows.append(
                {
                    "case_id": case["case_id"],
                    "preserved": preserved,
                    "source": source,
                    "target": target,
                }
            )
        all_preserved = all(item["preserved"] for item in case_rows)
        migration_rows.append(
            {
                "mapping": mapping,
                "cases": case_rows,
                "declaration": (
                    "WITNESSED_EQUIVALENT_ON_THIS_CORPUS"
                    if all_preserved
                    else "SEMANTIC_LOSS_DETECTED"
                ),
                "outside_corpus": "UNKNOWN",
            }
        )
    return {
        "material_operation_closure": {
            "rows": material_rows,
            "all_exact": all(row["exact"] for row in material_rows),
        },
        "standing_lifecycle": {
            "rows": standing_rows,
            "all_exact": all(row["exact"] for row in standing_rows),
            "liveness_floor": "Rejected malicious challenges do not permanently stop execution.",
        },
        "migration": {
            "rows": migration_rows,
            "claim_boundary": (
                "Equivalence is witnessed only for the executed corpus; native "
                "Unknown, forbid, and provenance are mandatory."
            ),
        },
    }


def audit_adversarial_corpus(root: Path) -> dict[str, Any]:
    path = root / "research-c" / "adversarial-corpus.json"
    corpus = load_json(path)
    cases = corpus["cases"]
    ids = [case["id"] for case in cases]
    required_families = {
        "REGISTRY",
        "AUTHORITY_STRATUM",
        "RACE",
        "MATERIAL_OPERATION_CLOSURE",
        "TARGET_FENCE",
        "STANDING",
        "MIGRATION",
    }
    observed_families = {case["attack_family"] for case in cases}
    required_race_ids = {
        "RACE-01-AFTER-READ",
        "RACE-02-AFTER-RE-READ",
        "RACE-03-AFTER-SIGN",
        "RACE-04-AFTER-RESERVE",
        "RACE-05-AFTER-EXECUTE-BEFORE-READBACK",
    }
    race_ids = {
        case["id"] for case in cases if case["attack_family"] == "RACE"
    }
    return {
        "status": corpus["status"],
        "case_count": len(cases),
        "unique_ids": len(ids) == len(set(ids)),
        "families_complete": required_families == observed_families,
        "race_boundaries_complete": required_race_ids <= race_ids,
        "coverage_index": corpus["coverage_index"],
        "execution_boundary": (
            "The corpus is an adversarial design artifact. Overlapping cases are "
            "executed by the owner/race/fence/materiality/standing/migration "
            "harness; the corpus as a 34-case product matrix remains DRAFT_NOT_RUN."
        ),
    }
