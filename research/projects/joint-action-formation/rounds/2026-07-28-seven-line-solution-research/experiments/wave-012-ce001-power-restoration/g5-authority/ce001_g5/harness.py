from __future__ import annotations

import shutil
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

from .common import sha256, verify_signed_native, write_json
from .model import (
    AUTHORITY_STRATA,
    REVOKE_BOUNDARIES,
    build_materiality_cases,
    build_operation,
    build_standing_cases,
    build_topology,
    material_operation_closure,
    resource_owner_for_topology,
)
from .process import JsonLineProcess


NOW = 1_800_000_000
OWNER_CURRENT_OUTCOMES = {
    "UNIFIED_AUTHORITY_CURRENT",
    "EXACT_DELEGATION_CURRENT",
    "OWNER_AUTHORITY_CURRENT",
    "SIGNED_EXACT_OPERATION",
    "RESERVE_AUTHORITY_CURRENT",
    "EXECUTE_AUTHORITY_CURRENT",
    "RESOURCE_RESERVED_EXACT_OPERATION",
    "RESOURCE_RESERVATION_IDEMPOTENT",
}


def _outcomes(responses: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        owner: response["native"]["outcome"]
        for owner, response in responses.items()
    }


def _heads(responses: dict[str, dict[str, Any]]) -> dict[str, int]:
    return {
        owner: int(response["native"]["owner_head"])
        for owner, response in responses.items()
    }


def _all_current(responses: dict[str, dict[str, Any]]) -> bool:
    return bool(responses) and all(
        verify_signed_native(response)
        and response["native"]["outcome"] in OWNER_CURRENT_OUTCOMES
        for response in responses.values()
    )


class AuthorityCluster:
    """Owner processes plus a separate monotonic signed authority channel."""

    def __init__(
        self,
        root: Path,
        runtime: Path,
        operation: dict[str, Any],
        trace: list[dict[str, Any]],
        cell_id: str,
    ) -> None:
        self.root = root
        self.runtime = runtime
        self.operation = operation
        self.topology = build_topology(operation["authority"]["stratum"])
        self.trace = trace
        self.cell_id = cell_id
        self.clients: dict[str, JsonLineProcess] = {}
        self.hello: dict[str, dict[str, Any]] = {}
        worker = root / "workers" / "owner_service.py"
        for owner_id in self.topology["required_owners"]:
            owner_dir = runtime / "owners" / owner_id
            config = owner_dir / "config.json"
            write_json(
                config,
                {
                    "owner_id": owner_id,
                    "operation": operation,
                    "topology": self.topology,
                },
            )
            client = JsonLineProcess(
                [
                    sys.executable,
                    str(worker),
                    "--config",
                    str(config),
                    "--store",
                    str(owner_dir / "store.json"),
                    "--key",
                    str(owner_dir / "private-key.pem"),
                ],
                service_id=owner_id,
                trace=trace,
            )
            self.clients[owner_id] = client
            self.hello[owner_id] = client.request(
                {"op": "HELLO"}, phase="OWNER_HELLO", cell_id=cell_id
            )
        self.trusted_owner_keys = {
            owner: hello["public_key_ed25519_b64"]
            for owner, hello in self.hello.items()
        }
        channel_dir = runtime / "authority-channel"
        channel_config = channel_dir / "config.json"
        write_json(
            channel_config,
            {
                "operation": operation,
                "topology": self.topology,
                "trusted_owner_keys": self.trusted_owner_keys,
            },
        )
        self.channel = JsonLineProcess(
            [
                sys.executable,
                str(root / "workers" / "authority_channel.py"),
                "--config",
                str(channel_config),
                "--store",
                str(channel_dir / "store.json"),
                "--key",
                str(channel_dir / "private-key.pem"),
            ],
            service_id="AUTHORITY_CHANNEL",
            trace=trace,
        )
        self.channel_hello = self.channel.request(
            {"op": "HELLO"}, phase="AUTHORITY_CHANNEL_HELLO", cell_id=cell_id
        )
        self.trusted_channel_key = self.channel_hello["native"][
            "public_key_ed25519_b64"
        ]

    def close(self) -> None:
        for client in self.clients.values():
            client.close()
        self.channel.close()

    def ingest(self, receipt: dict[str, Any], phase: str) -> dict[str, Any]:
        return self.channel.request(
            {"op": "INGEST_OWNER_RECEIPT", "receipt": receipt},
            phase=f"AUTHORITY_CHANNEL_INGEST_{phase}",
            cell_id=self.cell_id,
        )

    def request_all(
        self,
        op: str,
        *,
        operation: dict[str, Any] | None = None,
        expected_heads: dict[str, int] | None = None,
        now: int = NOW,
    ) -> dict[str, dict[str, Any]]:
        responses: dict[str, dict[str, Any]] = {}
        for owner_id, client in self.clients.items():
            command: dict[str, Any] = {
                "op": op,
                "operation": operation or self.operation,
                "now": now,
            }
            if expected_heads is not None:
                command["expected_head"] = expected_heads[owner_id]
            response = client.request(command, phase=op, cell_id=self.cell_id)
            responses[owner_id] = response
            self.ingest(response, op)
        return responses

    def reserve(self, heads: dict[str, int]) -> dict[str, Any]:
        owner = resource_owner_for_topology(self.topology)
        receipt = self.clients[owner].request(
            {
                "op": "RESERVE_RESOURCE",
                "operation": self.operation,
                "expected_head": heads[owner],
                "now": NOW,
            },
            phase="RESERVE_RESOURCE",
            cell_id=self.cell_id,
        )
        self.ingest(receipt, "RESERVE_RESOURCE")
        return receipt

    def revoke(self, boundary: str, owner_id: str | None = None) -> dict[str, Any]:
        owner = owner_id or (
            "O_UNIFIED" if self.topology["derived_stratum"] == "U" else "O_V"
        )
        receipt = self.clients[owner].request(
            {"op": "REVOKE", "now": NOW + 1, "boundary": boundary},
            phase=f"REVOKE_AFTER_{boundary.upper()}",
            cell_id=self.cell_id,
        )
        self.ingest(receipt, "REVOKE")
        return receipt

    def rotate_resource_fence(self) -> dict[str, Any]:
        owner = resource_owner_for_topology(self.topology)
        receipt = self.clients[owner].request(
            {"op": "ROTATE_RESOURCE_FENCE", "now": NOW + 1},
            phase="OWNER_ROTATE_RESOURCE_FENCE",
            cell_id=self.cell_id,
        )
        self.ingest(receipt, "FENCE")
        return receipt

    def renew_head(self, owner_id: str) -> dict[str, Any]:
        receipt = self.clients[owner_id].request(
            {"op": "RENEW_HEAD", "now": NOW + 1},
            phase="OWNER_RENEW_HEAD",
            cell_id=self.cell_id,
        )
        self.ingest(receipt, "RENEW")
        return receipt

    def snapshot(self) -> dict[str, Any]:
        return self.channel.request(
            {"op": "SNAPSHOT"},
            phase="AUTHORITY_CHANNEL_SNAPSHOT",
            cell_id=self.cell_id,
        )

    def issue_takeover_lease(
        self,
        *,
        source_target_state_sha256: str,
        authority_snapshot_sha256: str,
        requested_epoch: int = 2,
    ) -> dict[str, Any]:
        return self.channel.request(
            {
                "op": "ISSUE_TAKEOVER_LEASE",
                "source_target_state_sha256": source_target_state_sha256,
                "authority_snapshot_sha256": authority_snapshot_sha256,
                "requested_epoch": requested_epoch,
                "acceptance_status": "PENDING_OUTSIDE_G5",
                "runtime_scope": "SHARED_DURABLE_STORE_PROCESS_RESTART",
            },
            phase="AUTHORITY_CHANNEL_ISSUE_TAKEOVER_LEASE",
            cell_id=self.cell_id,
        )

    def target(
        self,
        *,
        mode: str = "strict",
        reuse_store: Path | None = None,
        runtime_suffix: str = "target",
        runtime_id: str | None = None,
    ) -> tuple[JsonLineProcess, Path]:
        target_dir = self.runtime / runtime_suffix
        config = target_dir / "trust-config.json"
        write_json(
            config,
            {
                "operation": self.operation,
                "topology": self.topology,
                "trusted_owner_keys": self.trusted_owner_keys,
                "trusted_channel_key": self.trusted_channel_key,
                "runtime_id": runtime_id or runtime_suffix,
            },
        )
        store = reuse_store or (target_dir / "durable-store.json")
        client = JsonLineProcess(
            [
                sys.executable,
                str(self.root / "workers" / "target_service.py"),
                "--config",
                str(config),
                "--store",
                str(store),
                "--mode",
                mode,
            ],
            service_id=f"O_E_TARGET[{mode}][{runtime_suffix}]",
            trace=self.trace,
        )
        client.request({"op": "HELLO"}, phase="TARGET_HELLO", cell_id=self.cell_id)
        return client, store

    def sync_target(
        self, target: JsonLineProcess
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        snapshot = self.snapshot()
        response = target.request(
            {"op": "SYNC_AUTHORITY", "authority_snapshot": snapshot},
            phase="TARGET_SYNC_SIGNED_AUTHORITY_CHANNEL",
            cell_id=self.cell_id,
        )
        return snapshot, response


def _execute_command(
    operation: dict[str, Any],
    receipts: dict[str, dict[str, Any]],
    reservation: dict[str, Any],
    *,
    coordinator_epoch: int = 1,
) -> dict[str, Any]:
    return {
        "op": "EXECUTE",
        "action": "ENERGIZE",
        "target_operation_id": operation["operation_id"],
        "operation": operation,
        "owner_execute_receipts": receipts,
        "reservation_receipt": reservation,
        "coordinator_epoch": coordinator_epoch,
        "now": NOW,
    }


def run_race_cell(
    root: Path,
    runtime: Path,
    stratum: str,
    boundary: str,
    trace: list[dict[str, Any]],
) -> dict[str, Any]:
    operation = build_operation(stratum)
    cell_id = f"RACE-{stratum}-{boundary}"
    cluster = AuthorityCluster(root, runtime / cell_id, operation, trace, cell_id)
    target, _ = cluster.target()
    signs: dict[str, dict[str, Any]] = {}
    reserve_checks: dict[str, dict[str, Any]] = {}
    execute_checks: dict[str, dict[str, Any]] = {}
    reservation: dict[str, Any] | None = None
    execute: dict[str, Any] | None = None
    compensation: dict[str, Any] | None = None
    stopped_at: str | None = None
    try:
        reads = cluster.request_all("READ")
        heads = _heads(reads)
        if boundary == "read":
            cluster.revoke(boundary)
        signs = cluster.request_all("SIGN", expected_heads=heads)
        if not _all_current(signs):
            stopped_at = "sign"
        if boundary == "sign":
            cluster.revoke(boundary)
        if stopped_at is None:
            reserve_checks = cluster.request_all(
                "RESERVE_CHECK", expected_heads=heads
            )
            if not _all_current(reserve_checks):
                stopped_at = "reserve_check"
        if stopped_at is None:
            reservation = cluster.reserve(heads)
            if not _all_current({"resource": reservation}):
                stopped_at = "reserve"
        if stopped_at is None:
            execute_checks = cluster.request_all(
                "EXECUTE_CHECK", expected_heads=heads
            )
            if not _all_current(execute_checks):
                stopped_at = "execute_check"
        if boundary == "reserve" and reservation is not None:
            cluster.revoke(boundary)
        _, sync = cluster.sync_target(target)
        if stopped_at is None and reservation is not None:
            execute = target.request(
                _execute_command(operation, execute_checks, reservation),
                phase=(
                    "POST_CHECK_REVOKE_STALE_EXECUTOR"
                    if boundary == "reserve"
                    else "TARGET_EXECUTE"
                ),
                cell_id=cell_id,
            )
            if boundary != "reserve" and execute["native"]["outcome"] != "ENERGIZED":
                stopped_at = "target_execute"
        if boundary == "execute" and execute is not None:
            cluster.revoke(boundary)
            cluster.sync_target(target)
            compensation = target.request(
                {
                    "op": "EXECUTE",
                    "action": "DEENERGIZE",
                    "target_operation_id": f"COMPENSATE-{operation['operation_id']}",
                    "caused_by_operation_id": operation["operation_id"],
                    "operation": operation,
                    "coordinator_epoch": 1,
                    "now": NOW + 2,
                },
                phase="SAGA_COMPENSATION_TARGET_TRANSITION",
                cell_id=cell_id,
            )
        readback = target.request(
            {"op": "READBACK"}, phase="TARGET_FINAL_READBACK", cell_id=cell_id
        )
    finally:
        target.close()
        cluster.close()
    state = readback["native"]["target_state"]
    transitions = state["transitions"]
    if boundary in {"read", "sign"}:
        native_resolution = state["power_state"] == "OFF" and not transitions
    elif boundary == "reserve":
        native_resolution = (
            execute is not None
            and execute["native"]["outcome"]
            in {
                "TARGET_REJECTED_OWNER_NOT_CURRENT",
                "TARGET_REJECTED_STALE_OWNER_HEAD",
            }
            and state["power_state"] == "OFF"
            and not transitions
        )
    else:
        native_resolution = (
            execute is not None
            and execute["native"]["outcome"] == "ENERGIZED"
            and compensation is not None
            and compensation["native"]["outcome"] == "DEENERGIZED"
            and state["power_state"] == "OFF"
            and [item["action"] for item in transitions]
            == ["ENERGIZE", "DEENERGIZE"]
        )
    return {
        "cell_id": cell_id,
        "stratum": stratum,
        "stratum_name": cluster.topology["derived_stratum"],
        "topology_closure_sha256": cluster.topology["topology_closure_sha256"],
        "topology_closure_kind": cluster.topology["closure_kind"],
        "revoke_after": boundary,
        "owner_service_pids": {
            owner: hello["native"]["service_pid"]
            for owner, hello in cluster.hello.items()
        },
        "authority_channel_pid": cluster.channel_hello["native"]["channel_pid"],
        "owner_native_outcomes": {
            "read": _outcomes(reads),
            "sign": _outcomes(signs),
            "reserve_check": _outcomes(reserve_checks),
            "execute_check": _outcomes(execute_checks),
        },
        "target_sync_outcome": sync["native"]["outcome"],
        "target_execute_outcome": execute["native"]["outcome"] if execute else None,
        "compensation_target_outcome": (
            compensation["native"]["outcome"] if compensation else None
        ),
        "target_final_readback": readback,
        "stopped_at": stopped_at,
        "native_resolution": native_resolution,
    }


def _prepared_cluster(
    root: Path,
    runtime: Path,
    trace: list[dict[str, Any]],
    cell_id: str,
    *,
    stratum: str = "P",
    mode: str = "strict",
    runtime_id: str | None = None,
) -> tuple[
    AuthorityCluster,
    JsonLineProcess,
    dict[str, Any],
    dict[str, int],
    dict[str, Any],
    dict[str, dict[str, Any]],
]:
    operation = build_operation(stratum)
    cluster = AuthorityCluster(root, runtime / cell_id, operation, trace, cell_id)
    reads = cluster.request_all("READ")
    heads = _heads(reads)
    cluster.request_all("SIGN", expected_heads=heads)
    cluster.request_all("RESERVE_CHECK", expected_heads=heads)
    reservation = cluster.reserve(heads)
    execute_receipts = cluster.request_all("EXECUTE_CHECK", expected_heads=heads)
    target, _ = cluster.target(mode=mode, runtime_id=runtime_id)
    cluster.sync_target(target)
    return cluster, target, operation, heads, reservation, execute_receipts


def run_target_native_attacks(
    root: Path, runtime: Path, trace: list[dict[str, Any]]
) -> dict[str, Any]:
    attacks = [
        "NO_OWNER_RECEIPTS",
        "NAKED_FENCE_INJECTION",
        "POST_CHECK_REVOKE",
        "WRONG_OWNER",
        "STALE_HEAD",
        "CHANGED_Q",
        "CHANGED_OBJECT_ID",
        "CHANGED_OBJECT_REVISION",
        "CHANGED_SCOPE",
        "CHANGED_EXPIRY",
        "RUNTIME_EXPIRED",
        "RELABELED_TOPOLOGY",
        "FORGED_RECEIPT",
        "ACTIVE_SNAPSHOT_COMPENSATION",
    ]
    rows: list[dict[str, Any]] = []
    for attack in attacks:
        cell_id = f"TARGET-GATE-{attack}"
        cluster, target, operation, _, reservation, receipts = _prepared_cluster(
            root, runtime, trace, cell_id
        )
        try:
            command = _execute_command(operation, deepcopy(receipts), reservation)
            if attack == "NO_OWNER_RECEIPTS":
                command.pop("owner_execute_receipts")
                command.pop("reservation_receipt")
            elif attack == "NAKED_FENCE_INJECTION":
                response = target.request(
                    {"op": "ADVANCE_FENCE", "fence_epoch": 999},
                    phase="CONTROLLER_NAKED_FENCE_ATTACK",
                    cell_id=cell_id,
                )
                readback = target.request(
                    {"op": "READBACK"},
                    phase="ATTACK_READBACK",
                    cell_id=cell_id,
                )
                rows.append(
                    {
                        "attack": attack,
                        "target_native_outcome": response["native"]["outcome"],
                        "transition_count": len(
                            readback["native"]["target_state"]["transitions"]
                        ),
                    }
                )
                continue
            elif attack == "POST_CHECK_REVOKE":
                cluster.revoke("post-check")
                cluster.sync_target(target)
            elif attack == "STALE_HEAD":
                cluster.renew_head("O_V")
                cluster.sync_target(target)
            elif attack == "WRONG_OWNER":
                command["owner_execute_receipts"]["O_V"] = deepcopy(
                    command["owner_execute_receipts"]["O_Q"]
                )
            elif attack == "CHANGED_Q":
                command["operation"]["q_version"] = "Q@v2"
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "CHANGED_OBJECT_ID":
                command["operation"]["object_id"] = "Venue-V/Circuit-C8"
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "CHANGED_OBJECT_REVISION":
                command["operation"]["object_revision"] = "C7@rev6"
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "CHANGED_SCOPE":
                command["operation"]["scope"]["power_kw"] = 4.0
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "CHANGED_EXPIRY":
                command["operation"]["expiry"] += 60
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "RUNTIME_EXPIRED":
                command["now"] = operation["expiry"] + 1
            elif attack == "RELABELED_TOPOLOGY":
                command["operation"]["authority"]["stratum"] = "U"
                command["operation"]["authority"]["stratum_name"] = (
                    "LAWFULLY_UNIFIED"
                )
                command["operation"]["material_closure_sha256"] = (
                    material_operation_closure(command["operation"])
                )
            elif attack == "FORGED_RECEIPT":
                forged = command["owner_execute_receipts"]["O_V"]
                forged["signature_ed25519_b64"] = "AAAA"
            elif attack == "ACTIVE_SNAPSHOT_COMPENSATION":
                command = {
                    "op": "EXECUTE",
                    "action": "DEENERGIZE",
                    "target_operation_id": f"COMPENSATE-{operation['operation_id']}",
                    "caused_by_operation_id": operation["operation_id"],
                    "operation": operation,
                    "coordinator_epoch": 1,
                    "now": NOW,
                }
            response = target.request(
                command, phase=f"TARGET_NATIVE_ATTACK_{attack}", cell_id=cell_id
            )
            readback = target.request(
                {"op": "READBACK"}, phase="ATTACK_READBACK", cell_id=cell_id
            )
            rows.append(
                {
                    "attack": attack,
                    "target_native_outcome": response["native"]["outcome"],
                    "transition_count": len(
                        readback["native"]["target_state"]["transitions"]
                    ),
                }
            )
        finally:
            target.close()
            cluster.close()
    return {
        "rows": rows,
        "all_rejected_without_effect": all(
            row["target_native_outcome"] != "ENERGIZED"
            and row["transition_count"] == 0
            for row in rows
        ),
    }


def run_fence_failure_injections(
    root: Path, runtime: Path, trace: list[dict[str, Any]]
) -> dict[str, Any]:
    rows = []
    for mode in ("strict", "ignore_fence", "restart_loses_fence"):
        cell_id = f"FENCE-INJECTION-{mode}"
        cluster, target, operation, _, reservation, receipts = _prepared_cluster(
            root, runtime, trace, cell_id, stratum="D", mode=mode
        )
        try:
            cluster.rotate_resource_fence()
            if mode == "restart_loses_fence":
                target.request(
                    {"op": "RESTART"}, phase="TARGET_RESTART", cell_id=cell_id
                )
            cluster.sync_target(target)
            response = target.request(
                _execute_command(operation, receipts, reservation),
                phase="STALE_RESERVATION_ATTEMPT",
                cell_id=cell_id,
            )
            readback = target.request(
                {"op": "READBACK"}, phase="TARGET_READBACK", cell_id=cell_id
            )
        finally:
            target.close()
            cluster.close()
        transitions = readback["native"]["target_state"]["transitions"]
        rows.append(
            {
                "mode": mode,
                "target_native_outcome": response["native"]["outcome"],
                "stale_effect_observed": bool(transitions),
                "power_state": readback["native"]["target_state"]["power_state"],
            }
        )
    return {
        "rows": rows,
        "strict_target_rejected_stale": rows[0]["target_native_outcome"]
        == "TARGET_REJECTED_STALE_RESOURCE_FENCE_RECEIPT",
        "ignore_fence_failure_exposed": rows[1]["stale_effect_observed"],
        "restart_epoch_loss_failure_exposed": rows[2]["stale_effect_observed"],
    }


def run_standing_attack(
    root: Path, runtime: Path, trace: list[dict[str, Any]]
) -> dict[str, Any]:
    operation = build_operation("P")
    operation["standing"]["status"] = "UNRESOLVED"
    operation["material_closure_sha256"] = material_operation_closure(operation)
    cell_id = "TARGET-GATE-UNRESOLVED-STANDING"
    cluster = AuthorityCluster(root, runtime / cell_id, operation, trace, cell_id)
    target, _ = cluster.target()
    try:
        reads = cluster.request_all("READ")
        cluster.sync_target(target)
        response = target.request(
            {
                "op": "EXECUTE",
                "action": "ENERGIZE",
                "target_operation_id": operation["operation_id"],
                "operation": operation,
                "owner_execute_receipts": {},
                "reservation_receipt": {},
                "now": NOW,
            },
            phase="UNRESOLVED_STANDING_ATTACK",
            cell_id=cell_id,
        )
        readback = target.request(
            {"op": "READBACK"}, phase="ATTACK_READBACK", cell_id=cell_id
        )
    finally:
        target.close()
        cluster.close()
    return {
        "owner_native_outcomes": _outcomes(reads),
        "target_native_outcome": response["native"]["outcome"],
        "transition_count": len(readback["native"]["target_state"]["transitions"]),
        "standing_fail_closed": (
            set(_outcomes(reads).values())
            == {"STANDING_NOT_EXECUTION_ELIGIBLE"}
            and response["native"]["outcome"] == "TARGET_REJECTED_STANDING"
            and not readback["native"]["target_state"]["transitions"]
        ),
    }


def run_migration(
    root: Path, runtime: Path, trace: list[dict[str, Any]]
) -> dict[str, Any]:
    cell_id = "E6-MIGRATION"
    cluster, source, operation, _, reservation, receipts = _prepared_cluster(
        root,
        runtime,
        trace,
        cell_id,
        runtime_id="SOURCE-RUNTIME@epoch1",
    )
    store = Path(
        source.request(
            {"op": "HELLO"}, phase="SOURCE_RUNTIME_IDENTITY", cell_id=cell_id
        )["native"]["store"]
    )
    source_pid = source.pid
    try:
        effect = source.request(
            _execute_command(operation, receipts, reservation),
            phase="SOURCE_TARGET_EFFECT",
            cell_id=cell_id,
        )
        before = source.request(
            {"op": "READBACK"}, phase="SOURCE_TARGET_READBACK", cell_id=cell_id
        )
        source_state_hash = sha256(before["native"]["target_state"])
        source_authority_snapshot_hash = before["native"]["target_state"][
            "authority_snapshot_sha256"
        ]
    finally:
        source.close()
    rejected_high_epoch_request = cluster.issue_takeover_lease(
        source_target_state_sha256=source_state_hash,
        authority_snapshot_sha256=source_authority_snapshot_hash,
        requested_epoch=999,
    )
    takeover_lease = cluster.issue_takeover_lease(
        source_target_state_sha256=source_state_hash,
        authority_snapshot_sha256=source_authority_snapshot_hash,
        requested_epoch=2,
    )
    restored, _ = cluster.target(
        reuse_store=store,
        runtime_suffix="target-restored",
        runtime_id="TARGET-RUNTIME@epoch2",
    )
    target_pid = restored.pid
    old_source_restarted: JsonLineProcess | None = None
    try:
        forged_high_epoch_lease = deepcopy(takeover_lease)
        forged_high_epoch_lease["native"]["capsule"]["coordinator_epoch"] = 999
        forged_high_epoch = restored.request(
            {"op": "RESTORE", "takeover_lease": forged_high_epoch_lease},
            phase="FORGED_HIGH_EPOCH_TAKEOVER_LEASE",
            cell_id=cell_id,
        )
        unsigned_lease = deepcopy(takeover_lease)
        unsigned_lease.pop("signature_ed25519_b64")
        unsigned = restored.request(
            {"op": "RESTORE", "takeover_lease": unsigned_lease},
            phase="UNSIGNED_TAKEOVER_LEASE",
            cell_id=cell_id,
        )
        restore = restored.request(
            {"op": "RESTORE", "takeover_lease": takeover_lease},
            phase="TARGET_NATIVE_RESTORE",
            cell_id=cell_id,
        )
        cluster.sync_target(restored)
        old_source_restarted, _ = cluster.target(
            reuse_store=store,
            runtime_suffix="old-source-restarted",
            runtime_id="SOURCE-RUNTIME-RESTARTED@epoch1",
        )
        old_source_restarted_pid = old_source_restarted.pid
        old_runtime = old_source_restarted.request(
            _execute_command(
                operation, receipts, reservation, coordinator_epoch=1
            ),
            phase="ACTUAL_OLD_SOURCE_RESTARTED_REPLAY",
            cell_id=cell_id,
        )
        old_source_restarted.close()
        old_source_restarted = None
        new_runtime = restored.request(
            _execute_command(
                operation, receipts, reservation, coordinator_epoch=2
            ),
            phase="NEW_RUNTIME_REPLAY",
            cell_id=cell_id,
        )
        unissued_high_execute = restored.request(
            _execute_command(
                operation, receipts, reservation, coordinator_epoch=999
            ),
            phase="UNISSUED_HIGH_COORDINATOR_EPOCH_EXECUTE",
            cell_id=cell_id,
        )
        stale_lease = restored.request(
            {"op": "RESTORE", "takeover_lease": takeover_lease},
            phase="OLD_MIGRATION_STATE_REUSE_ATTACK",
            cell_id=cell_id,
        )
        forged_rows: dict[str, dict[str, Any]] = {}
        mutations = {
            "operation": {**operation, "q_version": "Q@v2"},
            "authority_snapshot_sha256": "0" * 64,
            "source_target_state_sha256": "0" * 64,
            "acceptance_status": "ACCEPTED",
            "runtime_scope": "CROSS_FAILURE_DOMAIN",
        }
        for field, value in mutations.items():
            forged = deepcopy(takeover_lease)
            forged["native"]["capsule"][field] = value
            response = restored.request(
                {"op": "RESTORE", "takeover_lease": forged},
                phase=f"MIGRATION_FORGERY_{field}",
                cell_id=cell_id,
            )
            forged_rows[field] = {
                "native_outcome": response["native"]["outcome"],
                "mismatched_fields": response["native"].get(
                    "mismatched_fields", []
                ),
            }
        final = restored.request(
            {"op": "READBACK"}, phase="POST_MIGRATION_READBACK", cell_id=cell_id
        )
    finally:
        if old_source_restarted is not None:
            old_source_restarted.close()
        restored.close()
        cluster.close()
    return {
        "effect_before_crash": effect["native"]["outcome"],
        "source_runtime_pid": source_pid,
        "target_runtime_pid": target_pid,
        "old_source_restarted_pid": old_source_restarted_pid,
        "distinct_runtime_processes": len(
            {source_pid, target_pid, old_source_restarted_pid}
        )
        == 3,
        "durable_store_scope": "SHARED_DURABLE_STORE_PROCESS_RESTART",
        "cross_failure_domain": "NOT_RUN",
        "restore_native_outcome": restore["native"]["outcome"],
        "old_runtime_replay_outcome": old_runtime["native"]["outcome"],
        "old_runtime_replay_response_pid": old_runtime["native"][
            "target_service_pid"
        ],
        "old_runtime_replay_runtime_id": old_runtime["native"]["runtime_id"],
        "new_runtime_replay_outcome": new_runtime["native"]["outcome"],
        "unissued_high_execute_outcome": unissued_high_execute["native"][
            "outcome"
        ],
        "controller_high_epoch_lease_request_outcome": rejected_high_epoch_request[
            "native"
        ]["outcome"],
        "forged_high_epoch_lease_outcome": forged_high_epoch["native"]["outcome"],
        "unsigned_lease_outcome": unsigned["native"]["outcome"],
        "old_migration_state_reuse_outcome": stale_lease["native"]["outcome"],
        "forgery_validations": forged_rows,
        "transition_count_after_replay": len(
            final["native"]["target_state"]["transitions"]
        ),
        "duplicate_effect": len(final["native"]["target_state"]["transitions"])
        != 1,
        "takeover_lease": takeover_lease,
    }


def run_experiment(root: Path, runtime: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if runtime.name != "current":
        raise ValueError("runtime path must end in current")
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)
    trace: list[dict[str, Any]] = []
    try:
        race_rows = [
            run_race_cell(root, runtime, stratum, boundary, trace)
            for stratum in AUTHORITY_STRATA
            for boundary in REVOKE_BOUNDARIES
        ]
        attacks = run_target_native_attacks(root, runtime, trace)
        fence = run_fence_failure_injections(root, runtime, trace)
        standing_attack = run_standing_attack(root, runtime, trace)
        migration = run_migration(root, runtime, trace)
        materiality = build_materiality_cases()
        standing = build_standing_cases()
        topology_closures = {
            stratum: build_topology(stratum) for stratum in AUTHORITY_STRATA
        }
        validations = {
            "all_strata_and_revoke_boundaries_executed": len(race_rows) == 12,
            "topology_closures_are_distinct_and_target_trusted": (
                len(
                    {
                        value["topology_closure_sha256"]
                        for value in topology_closures.values()
                    }
                )
                == 3
                and {
                    value["closure_kind"] for value in topology_closures.values()
                }
                == {
                    "UNIFIED_PRINCIPAL_ACT",
                    "EXACT_DELEGATED_ACT",
                    "DIRECT_OWNER_ACT",
                }
            ),
            "all_race_cells_native_resolution": all(
                row["native_resolution"] for row in race_rows
            ),
            "target_native_gate_rejects_all_attacks": attacks[
                "all_rejected_without_effect"
            ],
            "saga_compensation_is_target_transition_and_readback": all(
                row["compensation_target_outcome"] == "DEENERGIZED"
                and row["target_final_readback"]["native"]["target_state"][
                    "power_state"
                ]
                == "OFF"
                and [
                    transition["action"]
                    for transition in row["target_final_readback"]["native"][
                        "target_state"
                    ]["transitions"]
                ]
                == ["ENERGIZE", "DEENERGIZE"]
                for row in race_rows
                if row["revoke_after"] == "execute"
            ),
            "strict_target_enforces_owner_channel_resource_fence": fence[
                "strict_target_rejected_stale"
            ],
            "target_fence_failure_profiles_exposed": (
                fence["ignore_fence_failure_exposed"]
                and fence["restart_epoch_loss_failure_exposed"]
            ),
            "standing_fails_closed_at_owner_and_target": standing_attack[
                "standing_fail_closed"
            ],
            "material_closure_discriminates_material_change": (
                materiality[0]["same_operation_closure"]
                and all(
                    not row["same_operation_closure"] for row in materiality[1:]
                )
            ),
            "standing_preserves_unknown_and_late_reopen": {
                row["native_resolution"] for row in standing
            }
            >= {
                "EXECUTION_ELIGIBLE",
                "SUSPEND_EXECUTION",
                "COMPENSATE_AND_REOPEN",
                "CONTINUE_WITH_AUDIT",
                "UNKNOWN",
            },
            "migration_is_distinct_process_restart_without_duplicate": (
                migration["distinct_runtime_processes"]
                and migration["old_runtime_replay_response_pid"]
                == migration["old_source_restarted_pid"]
                and migration["old_runtime_replay_runtime_id"]
                == "SOURCE-RUNTIME-RESTARTED@epoch1"
                and migration["restore_native_outcome"]
                == "MIGRATION_PROCESS_RESTART_RESTORED"
                and migration["old_runtime_replay_outcome"]
                == "STALE_COORDINATOR_EPOCH_REJECTED"
                and migration["new_runtime_replay_outcome"] == "IDEMPOTENT_REPLAY"
                and not migration["duplicate_effect"]
            ),
            "old_and_forged_migration_state_rejected_target_native": (
                migration["old_migration_state_reuse_outcome"]
                != "MIGRATION_PROCESS_RESTART_RESTORED"
                and migration["controller_high_epoch_lease_request_outcome"]
                == "TAKEOVER_EPOCH_NOT_NEXT"
                and migration["forged_high_epoch_lease_outcome"]
                == "TARGET_REJECTED_FORGED_TAKEOVER_LEASE"
                and migration["unsigned_lease_outcome"]
                == "TARGET_REJECTED_FORGED_TAKEOVER_LEASE"
                and migration["unissued_high_execute_outcome"]
                == "UNISSUED_COORDINATOR_EPOCH_REJECTED"
                and all(
                    item["native_outcome"]
                    == "TARGET_REJECTED_FORGED_TAKEOVER_LEASE"
                    for item in migration["forgery_validations"].values()
                )
            ),
            "cross_failure_domain_remains_not_run": migration[
                "cross_failure_domain"
            ]
            == "NOT_RUN",
        }
        public_keys = {
            f"{entry['cell_id']}::{entry['service_id']}": {
                "public_key_ed25519_b64": entry["response"].get(
                    "public_key_ed25519_b64"
                )
                or entry["response"].get("native", {}).get(
                    "public_key_ed25519_b64"
                ),
                "fingerprint_sha256": sha256(
                    (
                        entry["response"].get("public_key_ed25519_b64")
                        or entry["response"].get("native", {}).get(
                            "public_key_ed25519_b64"
                        )
                    ).encode("utf-8")
                ),
            }
            for entry in trace
            if (
                entry["response"].get("public_key_ed25519_b64")
                or entry["response"].get("native", {}).get(
                    "public_key_ed25519_b64"
                )
            )
        }
        process_inventory = sorted(
            {
                (
                    entry["cell_id"],
                    entry["service_id"],
                    entry["service_pid"],
                )
                for entry in trace
            }
        )
        results = {
            "schema": "ce001.g5.authority-race-fence-results.v2",
            "status": (
                "COMPLETE_LOCAL_COMPONENT_MODEL"
                if all(validations.values())
                else "HARNESS_FAILURE"
            ),
            "scope": "CE-001 G5 Authority/race/fence only",
            "engine_status": {
                "LOCAL_OWNER_AUTHORITY_SERVICE": "RUN",
                "LOCAL_SIGNED_AUTHORITY_CHANNEL": "RUN",
                "LOCAL_TARGET_NATIVE_GATE": "RUN",
                "OPA": "NOT_RUN",
                "Cedar": "NOT_RUN",
                "OpenFGA": "NOT_RUN",
                "XACML": "NOT_RUN",
                "CROSS_FAILURE_DOMAIN_MIGRATION": "NOT_RUN",
            },
            "metrics": {
                "authority_strata": 3,
                "revoke_boundaries": 4,
                "race_cells": len(race_rows),
                "race_cells_native_resolution": sum(
                    row["native_resolution"] for row in race_rows
                ),
                "target_native_attack_cases": len(attacks["rows"]),
                "execute_boundary_compensations": sum(
                    row["compensation_target_outcome"] == "DEENERGIZED"
                    for row in race_rows
                ),
                "raw_trace_events": len(trace),
            },
            "topology_closures": topology_closures,
            "race_matrix": race_rows,
            "target_native_gate_attacks": attacks,
            "target_fence_failure_injections": fence,
            "material_operation_closure": materiality,
            "standing": standing,
            "standing_attack": standing_attack,
            "migration": migration,
            "public_keys": public_keys,
            "process_inventory": [
                {"cell_id": cell, "service_id": service, "pid": pid}
                for cell, service, pid in process_inventory
            ],
            "validations": validations,
            "evidence_boundary": [
                "LOCAL_SYNTHETIC_COMPONENT_MODEL",
                "OWNER_AND_TARGET_ARE_COOPERATIVE_LOCAL_SUBPROCESSES",
                "TRUSTED_TOPOLOGY_AND_KEYS_ARE_BOOTSTRAP_INPUTS_NOT_LEGAL_PROOF",
                "TRUSTED_BOOTSTRAP_CONFIGURATION_ASSUMED",
                "RELIABLE_OWNER_EVENT_INGEST_TO_AUTHORITY_CHANNEL_ASSUMED",
                "MALICIOUS_CONTROLLER_WITHHOLDING_REVOKE_NOT_SOLVED",
                "SHARED_DURABLE_STORE_PROVES_PROCESS_RESTART_ONLY",
                "NO_CROSS_FAILURE_DOMAIN_MIGRATION",
                "NO_REAL_PRINCIPAL_OR_LEGAL_AUTHORITY",
                "NO_REAL_POWER_EFFECT_OR_VENUE_ACCEPTANCE",
                "OPA_CEDAR_OPENFGA_XACML_NOT_RUN",
                "NO_PRODUCT_COMPARISON",
                "NO_NOVEL_MECHANISM_NECESSITY_CLAIM",
            ],
        }
        return results, trace
    finally:
        shutil.rmtree(runtime)
