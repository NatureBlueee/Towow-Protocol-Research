#!/usr/bin/env python3
"""Actual local runner for T6-G7-ORTHOGONAL-REPLAY-001.

The method process receives only the public packet and provider-native
responses.  ``provider_scenario`` is consumed inside provider simulators and
is never copied into a worker request.  Grading is intentionally external:
this file neither imports nor opens the private oracle.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterable, Mapping

from provider_simulators import (
    AcceptanceProvider,
    EffectorProvider,
    NativeAuthorityProvider,
    build_runtime_pair,
    canonical_bytes,
    digest,
    mutate_capsule,
)


ROOT = Path(__file__).resolve().parent
WORKERS = {
    "B0": ROOT / "workers" / "b0_immutable_contract.py",
    "B1": ROOT / "workers" / "b1_durable_workflow.py",
    "MATURE": ROOT / "workers" / "mature_composite.py",
    "EQUAL_CENTER": ROOT / "workers" / "equal_authority_center.py",
    "DELEGATED_CENTER": ROOT / "workers" / "delegated_center.py",
    "HUMAN": ROOT / "workers" / "human_rule.py",
}


def load_public_fixture(path: str | Path = ROOT / "fixture.json") -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    worlds = data.get("worlds")
    if not isinstance(worlds, list) or not worlds:
        raise ValueError("fixture must contain a non-empty worlds list")
    for world in worlds:
        if "world_id" not in world or "public_packet" not in world:
            raise ValueError("each world needs world_id and public_packet")
    return data


def _worker_identity(path: Path) -> dict[str, Any]:
    source = path.read_bytes()
    return {
        "path": str(path.relative_to(ROOT)),
        "source_sha256": sha256(source).hexdigest(),
        "bytes": len(source),
    }


def _runtime_snapshot(runtime: Any) -> dict[str, Any]:
    return {
        "runtime_id": runtime.runtime_id,
        "epoch": runtime.epoch,
        "fenced": runtime.fenced,
        "node_states": deepcopy(runtime.node_states),
        "active_intents": deepcopy(runtime.active_intents),
        "uncertain_effects": deepcopy(runtime.uncertain_effects),
        "effect_witnesses": deepcopy(runtime.effect_witnesses),
        "acceptance_records": deepcopy(runtime.acceptance_records),
        "compensation_obligations": deepcopy(runtime.obligations),
        "timers": deepcopy(runtime.timers),
        "history_root": runtime.ledger.root(),
    }


def invoke_worker(
    method: str,
    *,
    phase: str,
    world_id: str,
    public_packet: Mapping[str, Any],
    observations: Mapping[str, Any],
    runtime_snapshot: Mapping[str, Any],
    migration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if method not in WORKERS:
        raise ValueError(f"unknown method {method!r}; choose from {sorted(WORKERS)}")
    worker = WORKERS[method]
    request = {
        "phase": phase,
        "method_id": method,
        "world_id": world_id,
        "public_packet": deepcopy(dict(public_packet)),
        "observations": deepcopy(dict(observations)),
        "runtime_snapshot": deepcopy(dict(runtime_snapshot)),
        "migration": deepcopy(dict(migration or {})),
    }
    completed = subprocess.run(
        [sys.executable, str(worker)],
        input=canonical_bytes(request),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"worker {method} failed with {completed.returncode}: "
            f"{completed.stderr.decode('utf-8', errors='replace')}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"worker {method} returned invalid JSON") from exc
    required = {"action", "closure", "dispatch", "requires_fence", "reason", "cost"}
    missing = sorted(required - set(result))
    if missing:
        raise RuntimeError(f"worker {method} omitted {missing}")
    if result["action"] not in {
        "CONTINUE",
        "BLOCK",
        "RECOVER",
        "LOCAL_REOPEN",
        "GLOBAL_REOPEN",
        "HUMAN_AMEND",
        "BOUNDED_UNKNOWN",
    }:
        raise RuntimeError(f"worker {method} returned unknown action {result['action']!r}")
    result["_worker"] = _worker_identity(worker)
    result["_request_sha256"] = digest(request)
    return result


def _query_authorities(
    authority: NativeAuthorityProvider,
    public_packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    observations = []
    queries = public_packet.get("native_queries", [])
    if not queries:
        queries = [{"endpoint": "default", "request": {}}]
    for query in queries:
        request = deepcopy(dict(query))
        # response_ref selects a configured native endpoint result but is not a
        # truth label or normalized dependency identity.
        observations.append(authority.query(request))
    return observations


def _operation(public_packet: Mapping[str, Any]) -> dict[str, Any]:
    operation = public_packet.get("operation", public_packet.get("exact_operation", {}))
    if not isinstance(operation, Mapping):
        raise ValueError("public operation must be an object")
    result = deepcopy(dict(operation))
    if not result.get("semantic_effect_key"):
        result["semantic_effect_key"] = result.get("effect_key", "missing-effect-key")
    return result


def _precrash_attempt(
    source: Any,
    effector: EffectorProvider,
    operation: Mapping[str, Any],
    runtime_scenario: Mapping[str, Any],
    effect_config: Mapping[str, Any],
) -> dict[str, Any] | None:
    migration_phase = str(runtime_scenario.get("migration_phase", "NONE")).upper()
    dispatch_outcome = str(effect_config.get("dispatch_outcome", "")).upper()
    if migration_phase not in {
        "PLANNED_DRAIN",
        "CRASH_TAKEOVER",
        "RECONCILING",
        "IMPORTED",
    }:
        return None
    if dispatch_outcome not in {"ATTEMPTED", "ACCEPTED", "COMMITTED"}:
        return None
    intent = source.persist_intent(operation)
    response = effector.dispatch(
        operation=operation,
        intent=intent,
        coordinator_epoch=source.epoch,
        authority_check={
            "allowed": True,
            "precrash_commit_check": True,
            "observed_epoch": source.epoch,
        },
    )
    source.record_dispatch(operation["semantic_effect_key"], response)
    return response


def _run_migration(
    *,
    authority: NativeAuthorityProvider,
    effector: EffectorProvider,
    source: Any,
    target: Any,
    runtime_scenario: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    phase = str(runtime_scenario.get("migration_phase", "NONE")).upper()
    if phase == "NONE":
        return {}, []

    authority.advance_epoch(target.epoch)
    source.fence(target.epoch)
    capsule = source.export_capsule()
    mutated = mutate_capsule(
        capsule,
        drop_fields=runtime_scenario.get("capsule_field_drop", []),
        rename_fields=runtime_scenario.get("capsule_field_rename", {}),
        duplicate_fields=runtime_scenario.get("capsule_field_duplicate", {}),
        resign=bool(runtime_scenario.get("resign_mutated_capsule", False)),
    )
    import_receipt = target.import_capsule(mutated)

    reconciliation: list[dict[str, Any]] = []
    effect_keys = sorted(
        set(target.uncertain_effects)
        | set(source.uncertain_effects)
        | {str(operation.get("semantic_effect_key", ""))}
    )
    if import_receipt["imported"]:
        for effect_key in effect_keys:
            if not effect_key:
                continue
            readback = effector.readback({"semantic_effect_key": effect_key})
            target.record_readback(effect_key, readback)
            reconciliation.append(readback)

    old_restart = None
    old_restart_blocked = None
    if runtime_scenario.get("old_runtime_restart"):
        old_intent = source.active_intents.get(operation["semantic_effect_key"])
        if old_intent is None:
            old_intent = source.persist_intent(operation)
        check = authority.commit_check(
            operation, source.epoch, f"epoch:{source.epoch}"
        )
        if source.fenced:
            check = {**check, "allowed": False, "runtime_fenced": True}
        old_restart_blocked = not bool(check.get("allowed"))
        old_restart = effector.dispatch(
            operation=operation,
            intent=old_intent,
            coordinator_epoch=source.epoch,
            authority_check=check,
        )
        source.record_dispatch(operation["semantic_effect_key"], old_restart)

    return {
        "phase": phase,
        "capsule_sha256": capsule.get("capsule_sha256"),
        "transmitted_capsule_sha256": mutated.get("capsule_sha256"),
        "source_visible": capsule,
        "transmitted_capsule": mutated,
        "source_fenced": source.fenced,
        "source_epoch": source.epoch,
        "target_epoch": target.epoch,
        "imported": import_receipt["imported"],
        "import_receipt": import_receipt,
        "old_runtime_restart": old_restart,
        "old_runtime_restart_blocked": old_restart_blocked,
    }, reconciliation


def run_world(world: Mapping[str, Any], method: str) -> dict[str, Any]:
    world_id = str(world["world_id"])
    public_packet = deepcopy(dict(world["public_packet"]))
    provider_scenario = deepcopy(dict(world.get("provider_scenario", {})))
    runtime_scenario = deepcopy(dict(world.get("runtime_scenario", {})))

    authority = NativeAuthorityProvider(provider_scenario.get("authority", {}))
    effector = EffectorProvider(provider_scenario.get("effect", {}))
    acceptance = AcceptanceProvider(provider_scenario.get("acceptance", {}))
    source, target = build_runtime_pair(public_packet, runtime_scenario)
    operation = _operation(public_packet)

    history_before = source.ledger.snapshot()
    precrash = _precrash_attempt(
        source,
        effector,
        operation,
        runtime_scenario,
        provider_scenario.get("effect", {}),
    )
    migration_phase = str(runtime_scenario.get("migration_phase", "NONE")).upper()
    if precrash is not None and migration_phase in {"PLANNED_DRAIN", "IMPORTED"}:
        source_readback = effector.readback(
            {"semantic_effect_key": operation["semantic_effect_key"]}
        )
        source.record_readback(operation["semantic_effect_key"], source_readback)
        source_acceptance = acceptance.readback(
            {
                "case_id": public_packet.get("case_id"),
                "goal_version": public_packet.get("goal_version"),
                "relation_version": public_packet.get("relation_version"),
                "semantic_effect_key": operation["semantic_effect_key"],
                "operation": operation,
            }
        )
        source.record_acceptance(source_acceptance)
    authority_observations = _query_authorities(authority, public_packet)
    for observation in authority_observations:
        source.record_authority_observation(observation)
    observations: dict[str, Any] = {"authority": authority_observations}
    if precrash is not None:
        observations["precrash_dispatch"] = precrash

    decisions: list[dict[str, Any]] = []
    plan = invoke_worker(
        method,
        phase="PLAN",
        world_id=world_id,
        public_packet=public_packet,
        observations=observations,
        runtime_snapshot=_runtime_snapshot(source),
    )
    decisions.append(plan)

    migration_receipt, migration_readbacks = _run_migration(
        authority=authority,
        effector=effector,
        source=source,
        target=target,
        runtime_scenario=runtime_scenario,
        operation=operation,
    )
    active_runtime = target if migration_receipt.get("imported") else source
    if migration_readbacks:
        observations["migration_effect_readbacks"] = migration_readbacks

    post_migration = invoke_worker(
        method,
        phase="POST_MIGRATION",
        world_id=world_id,
        public_packet=public_packet,
        observations=observations,
        runtime_snapshot=_runtime_snapshot(active_runtime),
        migration=migration_receipt,
    )
    decisions.append(post_migration)
    active_plan = post_migration

    dispatch_response = None
    effect_readback = None
    acceptance_readback = None
    effect_key = operation["semantic_effect_key"]

    already_reconciled = effect_key in active_runtime.effect_witnesses
    if bool(active_plan.get("dispatch")) and active_plan["action"] == "CONTINUE":
        if already_reconciled:
            dispatch_response = {
                "outcome": "SUPPRESSED_AFTER_RECONCILIATION",
                "effect_key": effect_key,
                "committed": False,
                "duplicate_suppressed": True,
            }
            active_runtime.ledger.append("REPLAY_SUPPRESSED", dispatch_response)
        else:
            intent = active_runtime.persist_intent(operation)
            fence_token = (
                f"epoch:{active_runtime.epoch}"
                if active_plan.get("requires_fence")
                else None
            )
            authority_check = authority.commit_check(
                operation, active_runtime.epoch, fence_token
            )
            dispatch_response = effector.dispatch(
                operation=operation,
                intent=intent,
                coordinator_epoch=active_runtime.epoch,
                authority_check=authority_check,
            )
            active_runtime.record_dispatch(effect_key, dispatch_response)

    needs_effect_readback = bool(
        dispatch_response
        or active_plan["action"] == "RECOVER"
        or active_runtime.uncertain_effects
    )
    if needs_effect_readback:
        effect_readback = effector.readback({"semantic_effect_key": effect_key})
        active_runtime.record_readback(effect_key, effect_readback)
        observations["effect_readback"] = effect_readback

    if effect_readback is not None or active_runtime.effect_witnesses:
        acceptance_request = {
            "case_id": public_packet.get("case_id"),
            "goal_version": public_packet.get("goal_version"),
            "relation_version": public_packet.get("relation_version"),
            "semantic_effect_key": effect_key,
            "operation": operation,
        }
        acceptance_readback = acceptance.readback(acceptance_request)
        active_runtime.record_acceptance(acceptance_readback)
        observations["acceptance_readback"] = acceptance_readback

    final_plan = invoke_worker(
        method,
        phase="CLOSURE",
        world_id=world_id,
        public_packet=public_packet,
        observations=observations,
        runtime_snapshot=_runtime_snapshot(active_runtime),
        migration=migration_receipt,
    )
    decisions.append(final_plan)
    active_runtime.apply_reopen(
        final_plan["action"], final_plan.get("closure", []), final_plan["reason"]
    )

    history_after = source.ledger.snapshot()
    historical_prefix_preserved = history_after[: len(history_before)] == history_before
    unresolved_effects = sorted(active_runtime.uncertain_effects)
    unresolved_obligations = deepcopy(active_runtime.obligations)
    reconciled_effect_keys = sorted(
        {
            str(
                (
                    readback.get("native_body", {}).get("effect_key")
                    if isinstance(readback.get("native_body"), Mapping)
                    else ""
                )
                or operation["semantic_effect_key"]
            )
            for readback in migration_readbacks + ([effect_readback] if effect_readback else [])
        }
    )
    all_costs = [decision.get("cost", {}) for decision in decisions]

    return {
        "world_id": world_id,
        "method": method,
        "authority_stratum": (
            "LEGITIMATELY_DELEGATED"
            if public_packet.get("delegated_authority") is True
            else "INDEPENDENT_AUTHORITY"
        ),
        "public_packet_sha256": digest(public_packet),
        "worker_identity": decisions[0]["_worker"],
        "authority_observations": authority_observations,
        "decisions": decisions,
        "action": final_plan["action"],
        "closure": sorted(set(str(x) for x in final_plan.get("closure", []))),
        "final_action": final_plan["action"],
        "executed_closure": sorted(set(str(x) for x in final_plan.get("closure", []))),
        "dispatch_response": dispatch_response,
        "effect_readback": effect_readback,
        "acceptance_readback": acceptance_readback,
        "migration": migration_receipt,
        "capsule": migration_receipt.get("transmitted_capsule"),
        "transmitted_capsule": migration_receipt.get("transmitted_capsule"),
        "source_visible": migration_receipt.get("source_visible"),
        "migration_readbacks": migration_readbacks,
        "old_runtime_fenced": bool(
            not migration_receipt
            or (
                migration_receipt.get("source_fenced")
                and (
                    not migration_receipt.get("old_runtime_restart")
                    or migration_receipt.get("old_runtime_restart_blocked") is True
                )
            )
        ),
        "reconciliation": {
            "readback_effect_keys": reconciled_effect_keys,
            "unresolved_effects": unresolved_effects,
            "unresolved_obligations": unresolved_obligations,
            "complete": not unresolved_effects and not unresolved_obligations,
        },
        "history": {
            "prefix_preserved": historical_prefix_preserved,
            "source_root": source.ledger.root(),
            "target_root": target.ledger.root(),
            "source_records": source.ledger.snapshot(),
            "target_records": target.ledger.snapshot(),
        },
        "history_before": history_before,
        "history_after": history_after,
        "provider_ledgers": {
            "authority": authority.ledger.snapshot(),
            "effector": effector.ledger.snapshot(),
            "acceptance": acceptance.ledger.snapshot(),
        },
        "effect_count": len(effector.effects_by_key),
        "cost_records": all_costs,
    }


def run_all(
    fixture: Mapping[str, Any],
    methods: Iterable[str] = tuple(WORKERS),
    world_ids: set[str] | None = None,
) -> dict[str, Any]:
    selected_methods = list(methods)
    unknown = sorted(set(selected_methods) - set(WORKERS))
    if unknown:
        raise ValueError(f"unknown methods: {unknown}")
    records = []
    for world in fixture["worlds"]:
        if world_ids and str(world["world_id"]) not in world_ids:
            continue
        for method in selected_methods:
            records.append(run_world(world, method))
    identities = {method: _worker_identity(WORKERS[method]) for method in selected_methods}
    if len({item["source_sha256"] for item in identities.values()}) != len(identities):
        raise RuntimeError("worker source alias detected")
    return {
        "runner": "T6-G7-ORTHOGONAL-REPLAY-001",
        "evidence_level": "LOCAL_SYNTHETIC",
        "fixture_id": fixture.get("fixture_id"),
        "fixture_sha256": digest(fixture),
        "world_count": len({record["world_id"] for record in records}),
        "method_count": len(selected_methods),
        "run_count": len(records),
        "worker_identities": identities,
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=ROOT / "fixture.json")
    parser.add_argument(
        "--methods",
        nargs="+",
        choices=sorted(WORKERS),
        default=list(WORKERS),
    )
    parser.add_argument("--world", action="append", dest="worlds")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    fixture = load_public_fixture(args.fixture)
    result = run_all(
        fixture,
        methods=args.methods,
        world_ids=set(args.worlds) if args.worlds else None,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
