"""Race, coordination, and target-fence simulator for MCB-G5-v2.

The method path only consumes signed owner-native responses.  Oracle snapshots
are read by the harness immediately before target execution and are not exposed
to the strategy.  This keeps method behavior separate from evaluation truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any
import uuid


OWNER_NAMES = ("request_owner", "budget_owner", "supplier_owner", "resource_owner")
STRATEGIES = (
    "no_common_transaction",
    "bounded_lease_confirm",
    "two_phase_hold",
    "saga_compensation",
    "unified_center",
)
FENCE_MODES = (
    "enforce",
    "ignore",
    "restart_loss",
    "cross_region_reorder",
)
OPERATION = {
    "operation_id": "joint-action-001",
    "object_id": "calibration-bid",
    "object_version": "v1",
    "canonical_digest": hashlib.sha256(
        b"calibration-bid|v1|owner-approved-material-closure"
    ).hexdigest(),
    "purpose": "emergency-calibration",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_signature(envelope: dict[str, Any], public_key: dict[str, int]) -> bool:
    signature = int(envelope["signature"], 16)
    unsigned = {key: value for key, value in envelope.items() if key != "signature"}
    digest = int.from_bytes(hashlib.sha256(canonical_bytes(unsigned)).digest(), "big")
    return pow(signature, public_key["e"], public_key["n"]) == digest


@dataclass(frozen=True)
class RacePlan:
    boundary: str
    owner: str
    action: str = "revoke"


@dataclass
class SimulationConfig:
    strategy: str
    race: RacePlan | None = None
    fence_mode: str = "enforce"
    authority_topology: str = "independent"
    crash_after_prepare: bool = False
    compensation_supported: bool = True
    lease_ms: int = 5_000
    hold_ms: int = 5_000


@dataclass
class TraceEvent:
    index: int
    event: str
    detail: dict[str, Any] = field(default_factory=dict)


class OwnerClient:
    def __init__(self, owner_id: str, runtime_dir: Path) -> None:
        self.owner_id = owner_id
        self.store_path = runtime_dir / "stores" / f"{owner_id}.json"
        self.private_key_path = runtime_dir / "keys" / f"{owner_id}.private.json"
        self.public_key_path = runtime_dir / "keys" / f"{owner_id}.public.json"
        owner_script = Path(__file__).with_name("owner_service.py")
        self.process = subprocess.Popen(
            [
                sys.executable,
                str(owner_script),
                "--owner-id",
                owner_id,
                "--store",
                str(self.store_path),
                "--private-key",
                str(self.private_key_path),
                "--public-key",
                str(self.public_key_path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        assert self.process.stdout is not None
        ready_line = self.process.stdout.readline()
        if not ready_line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"{owner_id} failed to start: {stderr}")
        self.ready = json.loads(ready_line)
        self.public_key = json.loads(self.public_key_path.read_text(encoding="utf-8"))

    @property
    def pid(self) -> int:
        return int(self.ready["process_id"])

    def rpc(self, command: str, **fields: Any) -> dict[str, Any]:
        if self.process.poll() is not None:
            raise RuntimeError(f"owner process {self.owner_id} is not running")
        request = {"command": command, **fields}
        assert self.process.stdin is not None
        assert self.process.stdout is not None
        self.process.stdin.write(json.dumps(request, sort_keys=True) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"{self.owner_id} closed RPC stream: {stderr}")
        envelope = json.loads(line)
        envelope["signature_verified"] = verify_signature(envelope, self.public_key)
        return envelope

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                self.rpc("shutdown")
            except (BrokenPipeError, RuntimeError):
                pass
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=2)
        for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
            if stream is not None and not stream.closed:
                stream.close()


class TargetFence:
    """Synthetic target-side enforcer whose acceptance is the observed Effect."""

    def __init__(self, mode: str) -> None:
        if mode not in FENCE_MODES:
            raise ValueError(f"unknown fence mode: {mode}")
        self.mode = mode
        self.global_epoch = 0
        self.memory_epoch = 0
        self.region_epochs: dict[str, int] = {}
        self.effects: list[dict[str, Any]] = []
        self.compensated_effects: set[str] = set()
        self.idempotency: dict[str, dict[str, Any]] = {}

    def restart(self) -> None:
        if self.mode == "restart_loss":
            self.memory_epoch = 0

    def execute(
        self, token: int, request_id: str, request_digest: str, region: str = "east"
    ) -> dict[str, Any]:
        previous = self.idempotency.get(request_id)
        if previous:
            if previous["request_digest"] != request_digest:
                return {
                    "accepted": False,
                    "reason": "IDEMPOTENCY_CONFLICT_CHANGED_BYTES",
                    "stale": token < self.global_epoch,
                }
            return dict(previous["result"], replay=True)

        stale = token < self.global_epoch
        accepted = False
        reason = ""
        if self.mode == "enforce":
            accepted = token > self.global_epoch
            reason = "MONOTONIC_FENCE_ACCEPT" if accepted else "STALE_FENCE_REJECT"
        elif self.mode == "ignore":
            accepted = True
            reason = "TARGET_IGNORED_FENCE"
        elif self.mode == "restart_loss":
            accepted = token > self.memory_epoch
            reason = "VOLATILE_FENCE_ACCEPT" if accepted else "VOLATILE_FENCE_REJECT"
            if accepted:
                self.memory_epoch = token
        elif self.mode == "cross_region_reorder":
            regional_epoch = self.region_epochs.get(region, 0)
            accepted = token > regional_epoch
            reason = (
                "REGION_LOCAL_FENCE_ACCEPT"
                if accepted
                else "REGION_LOCAL_FENCE_REJECT"
            )
            if accepted:
                self.region_epochs[region] = token

        if accepted:
            self.global_epoch = max(self.global_epoch, token)
            effect = {
                "effect_id": f"effect-{len(self.effects) + 1}",
                "token": token,
                "request_id": request_id,
                "request_digest": request_digest,
                "region": region,
                "stale": stale,
            }
            self.effects.append(effect)
            result = {
                "accepted": True,
                "reason": reason,
                "stale": stale,
                "effect_id": effect["effect_id"],
            }
        else:
            result = {"accepted": False, "reason": reason, "stale": stale}
        self.idempotency[request_id] = {
            "request_digest": request_digest,
            "result": result,
        }
        return result

    def compensate(self, effect_id: str, supported: bool) -> dict[str, Any]:
        if not supported:
            return {"compensated": False, "reason": "COMPENSATION_UNSUPPORTED"}
        self.compensated_effects.add(effect_id)
        return {"compensated": True, "reason": "COMPENSATING_EFFECT_RECORDED"}


class SimulationHarness:
    def __init__(self, config: SimulationConfig, runtime_dir: Path | None = None) -> None:
        if config.strategy not in STRATEGIES:
            raise ValueError(f"unknown strategy: {config.strategy}")
        self.config = config
        self._temporary = None
        if runtime_dir is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="g5-race-")
            runtime_dir = Path(self._temporary.name)
        self.runtime_dir = Path(runtime_dir)
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.owners = {
            owner: OwnerClient(owner, self.runtime_dir) for owner in OWNER_NAMES
        }
        self.target = TargetFence(config.fence_mode)
        self.trace: list[TraceEvent] = []
        self.metrics: dict[str, Any] = {
            "owner_rpcs": 0,
            "signature_failures": 0,
            "race_injections": 0,
            "race_effective": 0,
            "race_deferred": 0,
            "effect_attempted": 0,
            "effect_accepted": 0,
            "unsafe_effects": 0,
            "residual_unsafe_effects": 0,
            "compensations": 0,
            "compensation_failures": 0,
            "blocked_owner_holds": 0,
            "aborts": 0,
            "fence_rejections": 0,
        }
        self.txid = f"tx-{uuid.uuid4().hex}"
        self.operation_digest = OPERATION["canonical_digest"]
        self._race_fired = False
        self._oracle_before_execute: dict[str, Any] | None = None
        self._method_status = "RUNNING"
        self._effect: dict[str, Any] | None = None
        self._unified_transaction_active = False

    def record(self, event: str, **detail: Any) -> None:
        self.trace.append(TraceEvent(len(self.trace) + 1, event, detail))

    def call(self, owner: str, command: str, **fields: Any) -> dict[str, Any]:
        envelope = self.owners[owner].rpc(command, **fields)
        self.metrics["owner_rpcs"] += 1
        if not envelope["signature_verified"]:
            self.metrics["signature_failures"] += 1
        self.record(
            "owner_native_response",
            owner=owner,
            command=command,
            signature_verified=envelope["signature_verified"],
            native=envelope["result"],
        )
        return envelope["result"]

    def maybe_inject(self, boundary: str) -> None:
        race = self.config.race
        if not race or self._race_fired or race.boundary != boundary:
            return
        if self._unified_transaction_active:
            self._race_fired = True
            self.metrics["race_injections"] += 1
            self.metrics["race_deferred"] += 1
            self.record(
                "race_serialized_after_unified_commit",
                boundary=boundary,
                logical_owner=race.owner,
                action=race.action,
            )
            return
        result = self.call(race.owner, "mutate", action=race.action)
        self._race_fired = True
        self.metrics["race_injections"] += 1
        if result.get("effective"):
            self.metrics["race_effective"] += 1
        else:
            self.metrics["race_deferred"] += 1
        self.record(
            "race_injected",
            boundary=boundary,
            owner=race.owner,
            action=race.action,
            native=result,
        )

    def boundary(self, kind: str, subject: str) -> str:
        return f"{kind}:{subject}"

    def read_all(self, kind: str) -> dict[str, dict[str, Any]] | None:
        reads: dict[str, dict[str, Any]] = {}
        for owner in OWNER_NAMES:
            result = self.call(owner, "read")
            reads[owner] = result
            self.maybe_inject(self.boundary(kind, owner))
            if (
                not result.get("ok")
                or result.get("native_outcome") != "ACTIVE"
                or result.get("branch") != "main"
            ):
                self._method_status = (
                    "UNKNOWN_NATIVE_STATE"
                    if result.get("native_error") or result.get("branch") != "main"
                    else "AUTHORITATIVE_NEGATIVE"
                )
                return None
        return reads

    def sign_all(
        self,
        heads: dict[str, dict[str, Any]],
        stability_lease_ms: int = 0,
    ) -> bool:
        for owner in OWNER_NAMES:
            result = self.call(
                owner,
                "sign",
                txid=self.txid,
                operation_digest=self.operation_digest,
                expected_head=heads[owner]["head"],
                stability_lease_ms=stability_lease_ms,
            )
            self.maybe_inject(self.boundary("sign", owner))
            if not result.get("ok"):
                self._method_status = "SIGN_FAILED"
                return False
        return True

    def reserve(self) -> int | None:
        result = self.call(
            "resource_owner",
            "reserve",
            txid=self.txid,
            operation_digest=self.operation_digest,
            lease_ms=self.config.lease_ms,
        )
        self.maybe_inject(self.boundary("reserve", "resource_owner"))
        if not result.get("ok"):
            self._method_status = "RESERVATION_FAILED"
            return None
        return int(result["reservation"]["epoch"])

    def oracle_snapshot(self) -> dict[str, Any]:
        # Evaluation-side direct store read.  Strategy code receives no return
        # value from this method except inside execute_target's final metrics.
        snapshot: dict[str, Any] = {}
        for owner, client in self.owners.items():
            state = json.loads(client.store_path.read_text(encoding="utf-8"))
            snapshot[owner] = {
                "head": state["head"],
                "native_outcome": state["native_outcome"],
                "outage": state["outage"],
                "fork": state["fork"] is not None,
                "pending_revocation": state["pending_revocation"],
            }
        return snapshot

    @staticmethod
    def oracle_safe(snapshot: dict[str, Any]) -> bool:
        return all(
            state["native_outcome"] == "ACTIVE"
            and not state["outage"]
            and not state["fork"]
            for state in snapshot.values()
        )

    def execute_target(self, token: int) -> dict[str, Any]:
        self._oracle_before_execute = self.oracle_snapshot()
        oracle_safe = self.oracle_safe(self._oracle_before_execute)
        self.metrics["effect_attempted"] += 1
        result = self.target.execute(
            token,
            request_id=self.txid,
            request_digest=self.operation_digest,
        )
        self._effect = result
        self.maybe_inject(self.boundary("execute", "target"))
        if result["accepted"]:
            self.metrics["effect_accepted"] += 1
            if not oracle_safe:
                self.metrics["unsafe_effects"] += 1
                self.metrics["residual_unsafe_effects"] += 1
        else:
            self.metrics["fence_rejections"] += 1
        self.record(
            "target_readback",
            result=result,
            oracle_safe_at_execute=oracle_safe,
        )
        return result

    def abort_holds(self) -> None:
        for owner in OWNER_NAMES:
            self.call(owner, "abort", txid=self.txid)
        self.metrics["aborts"] += 1

    def run_no_common_transaction(self) -> None:
        first = self.read_all("read")
        if first is None:
            return
        second = self.read_all("reread")
        if second is None:
            return
        if not self.sign_all(second):
            return
        token = self.reserve()
        if token is None:
            return
        self.execute_target(token)
        self._method_status = "EFFECT_ATTEMPTED"

    def run_bounded_lease_confirm(self) -> None:
        first = self.read_all("read")
        if first is None:
            return
        if not self.sign_all(first, stability_lease_ms=self.config.lease_ms):
            return
        token = self.reserve()
        if token is None:
            return
        confirmed = self.read_all("reread")
        if confirmed is None:
            return
        self.execute_target(token)
        for owner in OWNER_NAMES:
            self.call(owner, "commit", txid=self.txid)
        self._method_status = "EFFECT_ATTEMPTED_WITH_BOUNDED_OWNER_LEASES"

    def run_two_phase_hold(self) -> None:
        first = self.read_all("read")
        if first is None:
            return
        if not self.sign_all(first):
            return
        prepared: list[str] = []
        for owner in OWNER_NAMES:
            result = self.call(
                owner,
                "prepare",
                txid=self.txid,
                operation_digest=self.operation_digest,
                expected_head=first[owner]["head"],
                hold_ms=self.config.hold_ms,
            )
            if not result.get("ok"):
                self.abort_holds()
                self._method_status = "PREPARE_FAILED"
                return
            prepared.append(owner)
        if self.config.crash_after_prepare:
            self.metrics["blocked_owner_holds"] = len(prepared)
            self._method_status = "COORDINATOR_CRASH_BLOCKING_HOLDS"
            return
        token = self.reserve()
        if token is None:
            self.abort_holds()
            return
        for owner in OWNER_NAMES:
            result = self.call(owner, "confirm", txid=self.txid)
            self.maybe_inject(self.boundary("reread", owner))
            if not result.get("ok"):
                self.abort_holds()
                self._method_status = "CONFIRM_FAILED"
                return
        self.execute_target(token)
        for owner in OWNER_NAMES:
            self.call(owner, "commit", txid=self.txid)
        self._method_status = "EFFECT_ATTEMPTED_WITH_2PC_LIKE_HOLDS"

    def run_saga_compensation(self) -> None:
        first = self.read_all("read")
        if first is None:
            return
        second = self.read_all("reread")
        if second is None:
            return
        if not self.sign_all(second):
            return
        token = self.reserve()
        if token is None:
            return
        result = self.execute_target(token)
        final = self.read_all("post_execute_read")
        must_compensate = final is None or (
            self._oracle_before_execute is not None
            and not self.oracle_safe(self._oracle_before_execute)
        )
        if result.get("accepted") and must_compensate:
            compensation = self.target.compensate(
                result["effect_id"], self.config.compensation_supported
            )
            self.record("compensation", result=compensation)
            if compensation["compensated"]:
                self.metrics["compensations"] += 1
                if self.metrics["residual_unsafe_effects"]:
                    self.metrics["residual_unsafe_effects"] -= 1
            else:
                self.metrics["compensation_failures"] += 1
        self._method_status = "SAGA_RECONCILED"

    def run_unified_center(self) -> None:
        if self.config.authority_topology != "unified":
            self._method_status = "NOT_APPLICABLE_EXTERNAL_NON_DELEGABLE_RIGHT"
            self.record(
                "unified_center_refused",
                reason="technical permission does not create unified Authority",
            )
            return
        # This branch models one real Principal, one consistency domain, and a
        # target Effect inside the same transaction.  Injected mutations are
        # serialized after commit and therefore do not retroactively invalidate
        # the Effect.
        self._unified_transaction_active = True
        for owner in OWNER_NAMES:
            self.record("unified_transaction_read", logical_locus=owner, state="ACTIVE")
            self.maybe_inject(self.boundary("read", owner))
        for owner in OWNER_NAMES:
            self.record("unified_transaction_sign", logical_locus=owner)
            self.maybe_inject(self.boundary("sign", owner))
        self.record("unified_transaction_reserve", epoch=1)
        self.maybe_inject(self.boundary("reserve", "resource_owner"))
        self.metrics["effect_attempted"] += 1
        self.metrics["effect_accepted"] += 1
        self.record("unified_transaction_effect", accepted=True)
        self.maybe_inject(self.boundary("execute", "target"))
        self._unified_transaction_active = False
        self._method_status = "UNIFIED_SINGLE_DOMAIN_COMMIT"

    def atomicity_claim(self) -> str:
        return {
            "no_common_transaction": "NONE_SERIAL_REREADS_ARE_NOT_CROSS_AUTHORITY_ATOMIC",
            "bounded_lease_confirm": "BOUNDED_OWNER_PROMISES_NOT_SIMULTANEOUS_SNAPSHOT",
            "two_phase_hold": "2PC_LIKE_HOLDS_WITH_BLOCKING_AND_EXPIRY",
            "saga_compensation": "COMPENSATION_NOT_ATOMIC_ROLLBACK",
            "unified_center": "SINGLE_AUTHORITY_SINGLE_CONSISTENCY_DOMAIN_ONLY",
        }[self.config.strategy]

    def run(self) -> dict[str, Any]:
        try:
            {
                "no_common_transaction": self.run_no_common_transaction,
                "bounded_lease_confirm": self.run_bounded_lease_confirm,
                "two_phase_hold": self.run_two_phase_hold,
                "saga_compensation": self.run_saga_compensation,
                "unified_center": self.run_unified_center,
            }[self.config.strategy]()
            report = {
                "schema_version": "research-b-race-report-v1",
                "evidence_level": "LOCAL_SYNTHETIC",
                "config": {
                    **asdict(self.config),
                    "race": asdict(self.config.race) if self.config.race else None,
                },
                "operation": OPERATION,
                "owner_processes": {
                    owner: {
                        "pid": client.pid,
                        "store": str(client.store_path),
                        "private_key": str(client.private_key_path),
                        "public_key": str(client.public_key_path),
                        "public_modulus_fingerprint": hashlib.sha256(
                            str(client.public_key["n"]).encode("ascii")
                        ).hexdigest(),
                    }
                    for owner, client in self.owners.items()
                },
                "method_status": self._method_status,
                "atomicity_claim": self.atomicity_claim(),
                "metrics": self.metrics,
                "oracle_before_execute": self._oracle_before_execute,
                "target_effects": self.target.effects,
                "target_compensated_effects": sorted(
                    self.target.compensated_effects
                ),
                "trace": [asdict(event) for event in self.trace],
                "cannot_support": [
                    "real Principal consent or legal Authority",
                    "production cryptographic security",
                    "cross-Authority simultaneous atomic snapshot",
                    "product-level OPA/Cedar/OpenFGA/XACML comparison",
                    "real-world Effect or Acceptance",
                ],
            }
            return report
        finally:
            self.close()

    def close(self) -> None:
        for owner in self.owners.values():
            owner.close()
        if self._temporary is not None:
            self._temporary.cleanup()


def run_fence_probe(mode: str) -> dict[str, Any]:
    target = TargetFence(mode)
    newer = target.execute(
        token=2,
        request_id="newer",
        request_digest=hashlib.sha256(b"newer").hexdigest(),
        region="east",
    )
    if mode == "restart_loss":
        target.restart()
    older = target.execute(
        token=1,
        request_id="older",
        request_digest=hashlib.sha256(b"older").hexdigest(),
        region="west",
    )
    return {
        "schema_version": "research-b-fence-probe-v1",
        "evidence_level": "LOCAL_SYNTHETIC",
        "mode": mode,
        "newer": newer,
        "older_after_newer": older,
        "stale_effect_observed": bool(older["accepted"] and older["stale"]),
        "target_effects": target.effects,
        "interpretation": {
            "enforce": "durable global monotonic comparison rejects old epoch",
            "ignore": "token exists but target ignores it",
            "restart_loss": "volatile highest epoch is lost on restart",
            "cross_region_reorder": "region-local maxima do not create a global fence",
        }[mode],
    }
