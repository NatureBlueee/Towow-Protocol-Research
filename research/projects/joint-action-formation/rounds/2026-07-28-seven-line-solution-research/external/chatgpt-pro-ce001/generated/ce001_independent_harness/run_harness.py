#!/usr/bin/env python3
"""Independent CE-001 reference harness.

This is a mechanism-level executable simulation, not a product benchmark.
It deliberately uses only Python's standard library and gives each arm its own
control loop. Arms share raw owner/resource/target APIs and a post-run evaluator,
but no candidate selector, normalized decision packet, or expected label.
"""
from __future__ import annotations

import argparse
import copy
import dataclasses
import hashlib
import hmac
import inspect
import json
import random
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ---------- Data model shared only as public interface ----------


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


class DecisionStatus(str, Enum):
    APPROVE = "APPROVE"
    REFUSE = "REFUSE"
    UNKNOWN = "UNKNOWN"


class AckLost(RuntimeError):
    pass


class CoordinatorCrash(RuntimeError):
    pass


class NotApplicable(RuntimeError):
    pass


@dataclass(frozen=True)
class TaskSpec:
    q_version: str = "Q@v1"
    target_circuit: str = "C7"
    kw_min: float = 2.85
    kw_max: float = 3.15
    duration: int = 45
    deadline: int = 90
    forbid_other_circuit_effect: bool = True


@dataclass(frozen=True)
class SignedDecision:
    owner: str
    kind: str
    subject: str
    action: str
    resource: str
    q_version: str
    issued_at: int
    expires_at: int
    sequence: int
    status: str
    constraints: Dict[str, Any]
    signature: str

    def payload(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d.pop("signature")
        return d


@dataclass
class Vendor:
    vendor_id: str
    available: bool
    qualified: bool
    cost: float
    known_initially: bool
    requires_formation: bool = False
    reservation_revokes: bool = False
    disclosure_tag: str = "temporary-power"


@dataclass
class EffectRecord:
    operation_id: str
    target_circuit: str
    start: int
    end: int
    kw: float
    fence_epoch: int
    authority_digest: str
    source: str


@dataclass
class ArmReport:
    arm: str
    case: str
    applicable: bool
    resolution: str
    actions: List[Dict[str, Any]]
    declared_success: bool
    declared_reason: str
    human_minutes: int
    wait_minutes: int
    compute_units: int
    governance_cost: float
    resource_cost: float
    crashed: bool = False
    recovered: bool = False
    cited_effect: Optional[Dict[str, Any]] = None


@dataclass
class EvalResult:
    arm: str
    case: str
    applicable: bool
    exact_task_success: bool
    correct_resolution: bool
    unsafe_effect: bool
    duplicate_effect: bool
    wrong_object_reliance: bool
    recovery_to_value: bool
    acceptance_complete: bool
    settlement_complete: bool
    deadline_met: bool
    net_value: float
    human_minutes: int
    wait_minutes: int
    effect_count: int
    resolution: str
    notes: List[str] = field(default_factory=list)


# ---------- World services: arms may query/act, but cannot read private fixture ----------


class OwnerService:
    def __init__(self, keys: Dict[str, bytes], case_private: Dict[str, Any]):
        self._keys = keys
        self._private = case_private
        self._seq: Dict[str, int] = {k: 0 for k in keys}
        self.decisions: List[SignedDecision] = []
        self.acceptances: List[SignedDecision] = []
        self.revoked_sequences: Dict[Tuple[str, str], int] = {}

    def _sign(self, owner: str, payload: Dict[str, Any]) -> str:
        return hmac.new(self._keys[owner], canonical(payload), hashlib.sha256).hexdigest()

    def verify(self, decision: SignedDecision, now: int) -> bool:
        if decision.owner not in self._keys:
            return False
        if decision.status != DecisionStatus.APPROVE.value:
            return False
        if not (decision.issued_at <= now < decision.expires_at):
            return False
        if decision.sequence <= self.revoked_sequences.get((decision.owner, decision.kind), -1):
            return False
        return hmac.compare_digest(self._sign(decision.owner, decision.payload()), decision.signature)

    def _issue(
        self,
        owner: str,
        kind: str,
        now: int,
        task: TaskSpec,
        status: DecisionStatus,
        action: str,
        resource: str,
        constraints: Optional[Dict[str, Any]] = None,
        ttl: int = 40,
    ) -> SignedDecision:
        self._seq[owner] += 1
        payload = {
            "owner": owner,
            "kind": kind,
            "subject": "coordinator",
            "action": action,
            "resource": resource,
            "q_version": task.q_version,
            "issued_at": now,
            "expires_at": now + ttl,
            "sequence": self._seq[owner],
            "status": status.value,
            "constraints": constraints or {},
        }
        dec = SignedDecision(signature=self._sign(owner, payload), **payload)
        self.decisions.append(dec)
        return dec

    def query_venue_authority(self, now: int, task: TaskSpec, proposal: Dict[str, Any]) -> SignedDecision:
        if self._private.get("venue_refuses", False):
            return self._issue("O_V", "venue_operation", now, task, DecisionStatus.REFUSE,
                               "energize", task.target_circuit, {"non_delegable": True})
        if self._private.get("formation_required", False):
            needed = proposal.get("purpose") == "community-workshop" and proposal.get("noise_plan") == "approved"
            if not needed:
                return self._issue("O_V", "venue_operation", now, task, DecisionStatus.UNKNOWN,
                                   "energize", task.target_circuit,
                                   {"missing": ["purpose", "noise_plan"],
                                    "required_purpose": "community-workshop",
                                    "required_noise_plan": "approved"})
        return self._issue("O_V", "venue_operation", now, task, DecisionStatus.APPROVE,
                           "energize", task.target_circuit,
                           {"exact_target": task.target_circuit, "kw_range": [task.kw_min, task.kw_max]})

    def query_requester_claim(self, now: int, task: TaskSpec) -> SignedDecision:
        return self._issue("O_Q", "task_claim", now, task, DecisionStatus.APPROVE,
                           "request", task.target_circuit, {"q_digest": digest(dataclasses.asdict(task))}, ttl=120)

    def query_safety(self, now: int, task: TaskSpec, vendor: Vendor) -> SignedDecision:
        if not vendor.qualified:
            return self._issue("O_S", "safety_permit", now, task, DecisionStatus.REFUSE,
                               "energize", task.target_circuit, {"reason": "unqualified_vendor"})
        return self._issue("O_S", "safety_permit", now, task, DecisionStatus.APPROVE,
                           "energize", task.target_circuit, {"vendor": vendor.vendor_id}, ttl=25)

    def query_payment(self, now: int, task: TaskSpec, vendor: Vendor) -> SignedDecision:
        return self._issue("O_P", "payment", now, task, DecisionStatus.APPROVE,
                           "pay", vendor.vendor_id, {"cap": vendor.cost + 20}, ttl=100)

    def revoke_resource_commitment(self, owner: str, kind: str, sequence: int) -> None:
        self.revoked_sequences[(owner, kind)] = max(sequence, self.revoked_sequences.get((owner, kind), -1))

    def accept_effect(self, owner: str, now: int, task: TaskSpec, effect_digest: str) -> SignedDecision:
        dec = self._issue(owner, "acceptance", now, task, DecisionStatus.APPROVE,
                          "accept", task.target_circuit,
                          {"effect_digest": effect_digest, "q_version": task.q_version}, ttl=300)
        self.acceptances.append(dec)
        return dec


class ResourceMarket:
    def __init__(self, vendors: List[Vendor], private: Dict[str, Any]):
        self._vendors = {v.vendor_id: copy.deepcopy(v) for v in vendors}
        self._private = private
        self.reservations: Dict[str, Dict[str, Any]] = {}
        self.search_calls = 0

    def local_asset(self) -> Optional[Vendor]:
        return copy.deepcopy(self._vendors.get("VENUE-BATTERY")) if "VENUE-BATTERY" in self._vendors else None

    def initial_candidates(self) -> List[Dict[str, Any]]:
        return [
            {"vendor_id": v.vendor_id, "tag": v.disclosure_tag, "claimed_available": v.available}
            for v in self._vendors.values() if v.known_initially and v.vendor_id != "VENUE-BATTERY"
        ]

    def search(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.search_calls += 1
        out = []
        for v in self._vendors.values():
            if v.vendor_id == "VENUE-BATTERY":
                continue
            if query.get("tag") and query["tag"] != v.disclosure_tag:
                continue
            out.append({
                "vendor_id": v.vendor_id,
                "claimed_available": v.available,
                "qualified_claim": v.qualified,
                "requires_formation": v.requires_formation,
                "cost": v.cost,
            })
        return out

    def inspect(self, vendor_id: str) -> Vendor:
        return copy.deepcopy(self._vendors[vendor_id])

    def reserve(self, vendor_id: str, reservation_id: str, now: int) -> Dict[str, Any]:
        v = self._vendors[vendor_id]
        if reservation_id in self.reservations:
            return copy.deepcopy(self.reservations[reservation_id])
        if not v.available:
            return {"status": "REFUSED", "vendor_id": vendor_id, "reason": "unavailable"}
        rec = {"status": "RESERVED", "vendor_id": vendor_id, "reservation_id": reservation_id,
               "expires_at": now + 30, "revoked": False, "cost": v.cost}
        self.reservations[reservation_id] = rec
        if v.reservation_revokes:
            rec["revoked"] = True
            rec["status"] = "REVOKED"
        return copy.deepcopy(rec)

    def current_reservation(self, reservation_id: str, now: int) -> Dict[str, Any]:
        rec = self.reservations.get(reservation_id)
        if not rec:
            return {"status": "MISSING"}
        if now >= rec["expires_at"]:
            rec["status"] = "EXPIRED"
        return copy.deepcopy(rec)


class TargetService:
    def __init__(self, private: Dict[str, Any], owners: OwnerService):
        self._private = private
        self._owners = owners
        self.command_ledger: Dict[str, Dict[str, Any]] = {}
        self.effects: List[EffectRecord] = []
        self.last_fence: Dict[str, int] = {}
        self.stale_receipts: List[Dict[str, Any]] = []
        if private.get("stale_wrong_object_receipt"):
            stale = {"operation_id": "old-op-C8", "target_circuit": "C8", "status": "APPLIED",
                     "start": 0, "end": 45, "kw": 3.0, "fence_epoch": 0}
            stale["effect_digest"] = digest(stale)
            self.stale_receipts.append(stale)

    def _auth_ok(self, decisions: Iterable[SignedDecision], task: TaskSpec, now: int, circuit: str) -> Tuple[bool, str]:
        kinds = {d.kind: d for d in decisions if d.resource in (circuit, "*") or d.kind in ("task_claim", "payment")}
        for required in ("task_claim", "venue_operation", "safety_permit"):
            dec = kinds.get(required)
            if dec is None or not self._owners.verify(dec, now):
                return False, f"missing_or_invalid:{required}"
        if kinds["venue_operation"].resource != circuit:
            return False, "wrong_target_authority"
        return True, "ok"

    def submit(
        self,
        *,
        operation_id: str,
        circuit: str,
        kw: float,
        duration: int,
        fence_epoch: int,
        decisions: List[SignedDecision],
        task: TaskSpec,
        now: int,
        source: str,
        technical_admin_override: bool = False,
    ) -> Dict[str, Any]:
        # Same operation id is target-side idempotent.
        if operation_id in self.command_ledger:
            return copy.deepcopy(self.command_ledger[operation_id])

        auth_ok, auth_reason = self._auth_ok(decisions, task, now, circuit)
        if not auth_ok and not technical_admin_override:
            rec = {"operation_id": operation_id, "status": "REJECTED", "reason": auth_reason,
                   "target_circuit": circuit, "fence_epoch": fence_epoch}
            self.command_ledger[operation_id] = rec
            return copy.deepcopy(rec)

        last = self.last_fence.get(circuit, -1)
        if fence_epoch < last:
            rec = {"operation_id": operation_id, "status": "REJECTED", "reason": "stale_fence",
                   "target_circuit": circuit, "fence_epoch": fence_epoch}
            self.command_ledger[operation_id] = rec
            return copy.deepcopy(rec)
        self.last_fence[circuit] = max(last, fence_epoch)

        mode = self._private.get("submit_mode", "normal")
        if mode == "ack_lost_no_effect_once" and not self._private.get("ack_loss_consumed"):
            self._private["ack_loss_consumed"] = True
            raise AckLost("ack lost before target applied operation")

        authority_digest = digest([d.payload() for d in decisions]) if decisions else "NONE"
        effect = EffectRecord(operation_id, circuit, now, now + duration, kw, fence_epoch, authority_digest, source)
        self.effects.append(effect)
        rec = {"operation_id": operation_id, "status": "APPLIED", "target_circuit": circuit,
               "fence_epoch": fence_epoch, "effect_digest": digest(dataclasses.asdict(effect)),
               "auth_ok": auth_ok, "auth_reason": auth_reason}
        self.command_ledger[operation_id] = rec

        if mode == "ack_lost_effect_once" and not self._private.get("ack_loss_consumed"):
            self._private["ack_loss_consumed"] = True
            raise AckLost("ack lost after target applied operation")
        if mode == "crash_after_effect_once" and not self._private.get("crash_consumed"):
            self._private["crash_consumed"] = True
            raise CoordinatorCrash("coordinator died after effect and before acceptance")
        return copy.deepcopy(rec)

    def advance_fence(self, circuit: str, fence_epoch: int) -> int:
        """Install a newer target-side coordinator epoch before a migrated runtime proceeds."""
        self.last_fence[circuit] = max(self.last_fence.get(circuit, -1), fence_epoch)
        installed = self.last_fence[circuit]
        if self._private.get("target_loses_fence_on_restart", False):
            # Counterexample intervention: the actuator restarts after accepting the new epoch
            # but loses the persisted epoch before an old runtime reappears.
            self.last_fence.pop(circuit, None)
        return installed

    def operation_status(self, operation_id: str) -> Dict[str, Any]:
        return copy.deepcopy(self.command_ledger.get(operation_id, {"operation_id": operation_id, "status": "MISSING"}))

    def broad_success_search(self) -> List[Dict[str, Any]]:
        return [copy.deepcopy(v) for v in self.command_ledger.values() if v.get("status") == "APPLIED"] + copy.deepcopy(self.stale_receipts)

    def meter_window(self, circuit: str, start: int = 0, end: int = 200) -> List[Dict[str, Any]]:
        points: List[Dict[str, Any]] = []
        for e in self.effects:
            if e.target_circuit != circuit:
                continue
            points.append({"operation_id": e.operation_id, "target_circuit": e.target_circuit,
                           "start": max(start, e.start), "end": min(end, e.end), "kw": e.kw,
                           "fence_epoch": e.fence_epoch, "effect_digest": digest(dataclasses.asdict(e))})
        return points


class SettlementService:
    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}

    def settle(self, key: str, vendor_id: str, amount: float, approvals: List[SignedDecision]) -> Dict[str, Any]:
        if key in self.records:
            return copy.deepcopy(self.records[key])
        required = {d.owner for d in approvals if d.kind in ("payment", "acceptance") and d.status == "APPROVE"}
        if not {"O_P", "O_Q", "O_V"}.issubset(required):
            rec = {"status": "BLOCKED", "reason": "missing_payment_or_acceptance"}
        else:
            rec = {"status": "SETTLED", "vendor_id": vendor_id, "amount": amount, "key": key}
        self.records[key] = rec
        return copy.deepcopy(rec)


class WorldAPI:
    """Public façade. Private case truth is intentionally not exposed."""

    def __init__(self, case: str, task: TaskSpec, private: Dict[str, Any], vendors: List[Vendor]):
        self.case = case  # evaluator metadata; arms are passed OpaqueWorld below
        self.task = task
        self._private = private
        keys = {owner: hashlib.sha256(f"{case}:{owner}:secret".encode()).digest()
                for owner in ("O_Q", "O_V", "O_R", "O_S", "O_P", "O_E")}
        self.owners = OwnerService(keys, private)
        self.market = ResourceMarket(vendors, private)
        self.target = TargetService(private, self.owners)
        self.settlement = SettlementService()
        self.clock = 0
        self.audit: List[Dict[str, Any]] = []
        self.rejections: List[str] = []
        self.run_generations = 0

    def tick(self, minutes: int, actor: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.clock += minutes
        self.audit.append({"t": self.clock, "dt": minutes, "actor": actor, "action": action, "details": details or {}})

    def opaque(self) -> "OpaqueWorld":
        return OpaqueWorld(self)


class OpaqueWorld:
    """What an arm can see: raw APIs and time, not private case labels or expected outcomes."""

    def __init__(self, world: WorldAPI):
        self._w = world

    @property
    def task(self) -> TaskSpec:
        return self._w.task

    @property
    def now(self) -> int:
        return self._w.clock

    @property
    def scenario_id(self) -> str:
        # Public episode metadata, not an expected outcome or private truth field.
        return self._w.case

    def trace(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self._w.audit)

    def market_search_calls(self) -> int:
        return self._w.market.search_calls

    def spend(self, minutes: int, actor: str, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        self._w.tick(minutes, actor, action, details)

    def local_asset(self) -> Optional[Vendor]:
        return self._w.market.local_asset()

    def initial_candidates(self) -> List[Dict[str, Any]]:
        return self._w.market.initial_candidates()

    def search_market(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._w.market.search(query)

    def inspect_vendor(self, vendor_id: str) -> Vendor:
        return self._w.market.inspect(vendor_id)

    def reserve(self, vendor_id: str, reservation_id: str) -> Dict[str, Any]:
        return self._w.market.reserve(vendor_id, reservation_id, self.now)

    def reservation_status(self, reservation_id: str) -> Dict[str, Any]:
        return self._w.market.current_reservation(reservation_id, self.now)

    def claim_task(self) -> SignedDecision:
        return self._w.owners.query_requester_claim(self.now, self.task)

    def venue_decision(self, proposal: Dict[str, Any]) -> SignedDecision:
        return self._w.owners.query_venue_authority(self.now, self.task, proposal)

    def safety_decision(self, vendor: Vendor) -> SignedDecision:
        return self._w.owners.query_safety(self.now, self.task, vendor)

    def payment_decision(self, vendor: Vendor) -> SignedDecision:
        return self._w.owners.query_payment(self.now, self.task, vendor)

    def submit(self, **kwargs: Any) -> Dict[str, Any]:
        return self._w.target.submit(task=self.task, now=self.now, **kwargs)

    def advance_fence(self, circuit: str, fence_epoch: int) -> int:
        return self._w.target.advance_fence(circuit, fence_epoch)

    def operation_status(self, operation_id: str) -> Dict[str, Any]:
        return self._w.target.operation_status(operation_id)

    def exact_meter(self, circuit: str) -> List[Dict[str, Any]]:
        return self._w.target.meter_window(circuit)

    def broad_success_search(self) -> List[Dict[str, Any]]:
        return self._w.target.broad_success_search()

    def accept(self, owner: str, effect_digest: str) -> SignedDecision:
        return self._w.owners.accept_effect(owner, self.now, self.task, effect_digest)

    def settle(self, key: str, vendor_id: str, amount: float, approvals: List[SignedDecision]) -> Dict[str, Any]:
        return self._w.settlement.settle(key, vendor_id, amount, approvals)

    def reject(self, reason: str) -> None:
        self._w.rejections.append(reason)

    def next_generation(self) -> int:
        self._w.run_generations += 1
        return self._w.run_generations


# ---------- Independent arm implementations ----------


class DirectPlatformArm:
    name = "direct_platform"

    def run(self, w: OpaqueWorld) -> ArmReport:
        actions: List[Dict[str, Any]] = []
        asset = w.local_asset()
        if asset is None:
            raise NotApplicable("no venue-owned native asset")
        w.spend(1, self.name, "read_local_asset")
        q = w.claim_task(); w.spend(1, self.name, "claim_task")
        v = w.venue_decision({"purpose": "community-workshop", "noise_plan": "approved"}); w.spend(1, self.name, "venue_authorize")
        s = w.safety_decision(asset); w.spend(1, self.name, "safety_authorize")
        op = "direct-op"
        rec = w.submit(operation_id=op, circuit=w.task.target_circuit, kw=3.0, duration=w.task.duration,
                       fence_epoch=1, decisions=[q, v, s], source=self.name)
        w.spend(1, self.name, "submit", rec)
        meter = w.exact_meter(w.task.target_circuit); w.spend(1, self.name, "read_exact_meter")
        if meter:
            w.spend(max(0, meter[-1]["end"] - w.now), self.name, "wait_for_effect_duration")
            meter = w.exact_meter(w.task.target_circuit); w.spend(1, self.name, "completion_meter_readback")
        eff = meter[-1]["effect_digest"] if meter else "missing"
        aq = w.accept("O_Q", eff); av = w.accept("O_V", eff); w.spend(2, self.name, "accept")
        p = w.payment_decision(asset); w.spend(1, self.name, "payment_authorize")
        st = w.settle("settle-direct", asset.vendor_id, asset.cost, [p, aq, av]); w.spend(1, self.name, "settle", st)
        actions.extend(w.trace())
        return ArmReport(self.name, w.scenario_id, True, "SUCCESS", actions, True, "native_path",
                         human_minutes=2, wait_minutes=w.now, compute_units=2, governance_cost=2.0,
                         resource_cost=asset.cost, cited_effect=meter[-1] if meter else None)


class ExistingPortfolioArm:
    """Independent deterministic portfolio using existing primitives only."""
    name = "existing_authority_aware_portfolio"

    def __init__(self, sabotage_exact_readback: bool = False, disable_condition_formation: bool = False):
        self.sabotage_exact_readback = sabotage_exact_readback
        self.disable_condition_formation = disable_condition_formation

    def _find_vendor(self, w: OpaqueWorld, exclude: Optional[set[str]] = None) -> Optional[Vendor]:
        exclude = exclude or set()
        local = w.local_asset()
        if local and local.available and local.qualified and local.vendor_id not in exclude:
            w.spend(1, self.name, "local_asset_found", {"vendor": local.vendor_id})
            return local
        w.spend(2, self.name, "market_search_begin")
        candidates = w.search_market({"tag": "temporary-power", "kw": 3.0, "deadline": w.task.deadline})
        for c in sorted(candidates, key=lambda x: (x["cost"], x["vendor_id"])):
            if c["vendor_id"] in exclude or not c["claimed_available"] or not c["qualified_claim"]:
                continue
            w.spend(1, self.name, "inspect_vendor", {"vendor": c["vendor_id"]})
            return w.inspect_vendor(c["vendor_id"])
        return None

    def _effect_readback(self, w: OpaqueWorld, op: str) -> Optional[Dict[str, Any]]:
        if self.sabotage_exact_readback:
            broad = w.broad_success_search(); w.spend(1, self.name, "SABOTAGED_broad_readback")
            return broad[0] if broad else None
        status = w.operation_status(op); w.spend(1, self.name, "read_operation_status", status)
        meter = w.exact_meter(w.task.target_circuit); w.spend(1, self.name, "read_exact_meter")
        for m in meter:
            if m["operation_id"] == op and m["target_circuit"] == w.task.target_circuit:
                return m
        if status.get("status") == "APPLIED":
            # Receipt without target-native meter is not enough.
            return None
        return None

    def run(self, w: OpaqueWorld) -> ArmReport:
        actions: List[Dict[str, Any]] = []
        q = w.claim_task(); w.spend(1, self.name, "claim_task")
        # Do not assume the venue's private acceptance conditions. Query once, then
        # form only the disclosed missing condition if the owner returns a bounded counterproposal.
        proposal = {"target": w.task.target_circuit}
        venue = w.venue_decision(proposal); w.spend(2, self.name, "venue_decision", {"status": venue.status})
        if venue.status == DecisionStatus.UNKNOWN.value and venue.constraints.get("missing"):
            if self.disable_condition_formation:
                w.reject("formation_operator_removed")
                actions.extend(w.trace())
                return ArmReport(self.name, w.scenario_id, True, "DEFER", actions, False, "formation_operator_removed",
                                 human_minutes=4, wait_minutes=w.now, compute_units=4, governance_cost=4.0,
                                 resource_cost=0.0)
            proposal = {
                "purpose": venue.constraints.get("required_purpose"),
                "noise_plan": venue.constraints.get("required_noise_plan"),
                "target": w.task.target_circuit,
            }
            w.spend(2, self.name, "form_disclosed_venue_condition", proposal)
            venue = w.venue_decision(proposal); w.spend(2, self.name, "venue_redecision", {"status": venue.status})
        if venue.status == DecisionStatus.REFUSE.value:
            w.reject("non_delegable_venue_refusal")
            w.spend(1, self.name, "bounded_reject")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "owner_refusal",
                             human_minutes=3, wait_minutes=w.now, compute_units=3, governance_cost=3.0,
                             resource_cost=0.0)
        if venue.status != DecisionStatus.APPROVE.value:
            w.reject("authority_unknown_after_proposal")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "DEFER", actions, False, "authority_unknown",
                             human_minutes=4, wait_minutes=w.now, compute_units=4, governance_cost=4.0,
                             resource_cost=0.0)

        excluded: set[str] = set()
        vendor: Optional[Vendor] = None
        reservation: Optional[Dict[str, Any]] = None
        while w.now < w.task.deadline - 10:
            vendor = self._find_vendor(w, excluded)
            if vendor is None:
                w.reject("no_qualified_resource")
                break
            safety = w.safety_decision(vendor); w.spend(1, self.name, "safety_decision", {"status": safety.status})
            if safety.status != DecisionStatus.APPROVE.value:
                excluded.add(vendor.vendor_id)
                continue
            payment = w.payment_decision(vendor); w.spend(1, self.name, "payment_decision")
            reservation_id = f"reserve:{vendor.vendor_id}:{digest(dataclasses.asdict(w.task))[:8]}"
            reservation = w.reserve(vendor.vendor_id, reservation_id); w.spend(2, self.name, "reserve", reservation)
            current = w.reservation_status(reservation_id); w.spend(1, self.name, "reservation_readback", current)
            if current.get("status") != "RESERVED":
                excluded.add(vendor.vendor_id)
                continue

            if w.now + w.task.duration > w.task.deadline:
                w.reject("insufficient_time_for_full_effect_window")
                break

            generation = w.next_generation()
            fence = generation
            operation_id = f"op:{digest(dataclasses.asdict(w.task))[:10]}:{vendor.vendor_id}"
            decisions = [q, venue, safety]
            crashed = False
            try:
                rec = w.submit(operation_id=operation_id, circuit=w.task.target_circuit, kw=3.0,
                               duration=w.task.duration, fence_epoch=fence, decisions=decisions,
                               source=self.name)
                w.spend(1, self.name, "submit", rec)
            except AckLost:
                w.spend(1, self.name, "ack_lost")
                effect = self._effect_readback(w, operation_id)
                if effect is None:
                    # Retry same exact operation id; target ledger makes this safe.
                    rec = w.submit(operation_id=operation_id, circuit=w.task.target_circuit, kw=3.0,
                                   duration=w.task.duration, fence_epoch=fence, decisions=decisions,
                                   source=self.name)
                    w.spend(1, self.name, "retry_same_operation_id", rec)
            except CoordinatorCrash:
                crashed = True
                w.spend(0, self.name, "coordinator_crashed")
                # New runtime resumes from durable identifiers; old runtime is fenced.
                generation = w.next_generation(); fence = generation
                w.advance_fence(w.task.target_circuit, fence)
                w.spend(0, self.name, "install_migrated_fence", {"fence": fence})
                effect = self._effect_readback(w, operation_id)
                if effect is None:
                    rec = w.submit(operation_id=operation_id, circuit=w.task.target_circuit, kw=3.0,
                                   duration=w.task.duration, fence_epoch=fence, decisions=decisions,
                                   source=self.name)
                    w.spend(1, self.name, "migrated_retry_same_operation_id", rec)
                # Simulate stale old runtime attempting a different command with stale fence.
                stale = w.submit(operation_id=operation_id + ":old-replay", circuit=w.task.target_circuit,
                                 kw=3.0, duration=w.task.duration, fence_epoch=max(0, fence - 1),
                                 decisions=decisions, source=self.name + ":old")
                w.spend(1, self.name, "old_runtime_replay", stale)

            effect = self._effect_readback(w, operation_id)
            if effect is None:
                w.reject("effect_unproven")
                break
            w.spend(max(0, effect["end"] - w.now), self.name, "wait_for_effect_duration")
            completed = self._effect_readback(w, operation_id)
            if completed is None or completed.get("end", w.now + 1) > w.now:
                w.reject("effect_duration_not_completed")
                break
            effect = completed
            aq = w.accept("O_Q", effect["effect_digest"]); av = w.accept("O_V", effect["effect_digest"])
            w.spend(2, self.name, "owner_acceptance")
            st = w.settle("settle:" + operation_id, vendor.vendor_id, vendor.cost, [payment, aq, av])
            w.spend(1, self.name, "settlement", st)
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "SUCCESS", actions, True,
                             "exact_effect_and_acceptance", human_minutes=5, wait_minutes=w.now,
                             compute_units=8 + w.market_search_calls(), governance_cost=5.0,
                             resource_cost=vendor.cost, crashed=crashed, recovered=crashed,
                             cited_effect=effect)

        actions.extend(w.trace())
        return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False,
                         "bounded_no_path", human_minutes=5, wait_minutes=w.now,
                         compute_units=8, governance_cost=5.0, resource_cost=0.0)


class HumanInstitutionArm:
    """Independent phone/ticket/SOP path. Same authority envelope, slower and costlier."""
    name = "bounded_human_institution"

    def run(self, w: OpaqueWorld) -> ArmReport:
        actions: List[Dict[str, Any]] = []
        w.spend(4, self.name, "open_incident_ticket")
        claim = w.claim_task(); w.spend(3, self.name, "requester_call")
        venue = w.venue_decision({"target": w.task.target_circuit})
        w.spend(7, self.name, "facilities_manager_call", {"status": venue.status})
        if venue.status == DecisionStatus.UNKNOWN.value and venue.constraints.get("missing"):
            w.spend(3, self.name, "facilitated_condition_conversation", venue.constraints)
            venue = w.venue_decision({
                "purpose": venue.constraints.get("required_purpose"),
                "noise_plan": venue.constraints.get("required_noise_plan"),
                "target": w.task.target_circuit,
            })
            w.spend(4, self.name, "facilities_manager_redecision", {"status": venue.status})
        if venue.status == DecisionStatus.REFUSE.value:
            w.reject("venue_manager_refused")
            w.spend(2, self.name, "record_refusal")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "owner_refusal",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=8.0, resource_cost=0.0)
        if venue.status != DecisionStatus.APPROVE.value:
            w.reject("venue_authority_unknown")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "DEFER", actions, False, "unknown",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=8.0, resource_cost=0.0)

        # Human checks local asset first, then calls every disclosed supplier; no shared selector.
        vendor = w.local_asset()
        if vendor:
            w.spend(4, self.name, "inspect_venue_asset")
        else:
            called: set[str] = set()
            vendor = None
            initial = w.initial_candidates(); w.spend(2, self.name, "read_supplier_sheet")
            directory = initial
            while w.now < w.task.deadline - 14 and vendor is None:
                for row in directory:
                    vid = row["vendor_id"]
                    if vid in called:
                        continue
                    called.add(vid)
                    w.spend(6, self.name, "phone_supplier", {"vendor": vid})
                    v = w.inspect_vendor(vid)
                    if v.available and v.qualified:
                        r = w.reserve(vid, f"human-reserve:{vid}"); w.spend(4, self.name, "verbal_and_ticket_reserve", r)
                        if w.reservation_status(f"human-reserve:{vid}").get("status") == "RESERVED":
                            vendor = v
                            break
                if vendor is None:
                    # Escalate to a broader directory only after initial sheet fails.
                    directory = w.search_market({"tag": "temporary-power"}); w.spend(8, self.name, "broker_directory_search")
                    if all(row["vendor_id"] in called for row in directory):
                        break
        if vendor is None:
            w.reject("human_no_resource_before_deadline")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "no_resource",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=12.0, resource_cost=0.0)

        safety = w.safety_decision(vendor); w.spend(5, self.name, "safety_officer_signoff")
        payment = w.payment_decision(vendor); w.spend(4, self.name, "purchase_order")
        if safety.status != DecisionStatus.APPROVE.value:
            w.reject("safety_refused")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "safety_refusal",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=12.0, resource_cost=0.0)

        if w.now + w.task.duration > w.task.deadline:
            w.reject("human_path_cannot_complete_before_deadline")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "deadline_infeasible_for_arm",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=15.0, resource_cost=0.0)

        op = f"ticket-op:{vendor.vendor_id}:{digest(dataclasses.asdict(w.task))[:8]}"
        fence = w.next_generation()
        crashed = False
        try:
            rec = w.submit(operation_id=op, circuit=w.task.target_circuit, kw=3.0,
                           duration=w.task.duration, fence_epoch=fence,
                           decisions=[claim, venue, safety], source=self.name)
            w.spend(2, self.name, "operator_submit", rec)
        except AckLost:
            w.spend(3, self.name, "operator_calls_target_room")
            meter = w.exact_meter(w.task.target_circuit); w.spend(4, self.name, "read_named_meter")
            if not any(m["operation_id"] == op for m in meter):
                rec = w.submit(operation_id=op, circuit=w.task.target_circuit, kw=3.0,
                               duration=w.task.duration, fence_epoch=fence,
                               decisions=[claim, venue, safety], source=self.name)
                w.spend(2, self.name, "repeat_same_ticket_number", rec)
        except CoordinatorCrash:
            crashed = True
            old_fence = fence
            w.spend(6, self.name, "new_shift_reads_ticket")
            fence = w.next_generation()
            w.advance_fence(w.task.target_circuit, fence)
            w.spend(0, self.name, "new_shift_installs_fence", {"fence": fence})
            meter = w.exact_meter(w.task.target_circuit); w.spend(4, self.name, "new_shift_meter_check")
            if not any(m["operation_id"] == op for m in meter):
                rec = w.submit(operation_id=op, circuit=w.task.target_circuit, kw=3.0,
                               duration=w.task.duration, fence_epoch=fence,
                               decisions=[claim, venue, safety], source=self.name)
                w.spend(2, self.name, "new_shift_same_ticket_retry", rec)
            stale = w.submit(operation_id=op + ":old-replay", circuit=w.task.target_circuit, kw=3.0,
                             duration=w.task.duration, fence_epoch=old_fence,
                             decisions=[claim, venue, safety], source=self.name + ":old")
            w.spend(1, self.name, "old_shift_replay", stale)

        meter = w.exact_meter(w.task.target_circuit); w.spend(4, self.name, "final_meter_log")
        match = next((m for m in meter if m["operation_id"] == op), None)
        if match is None:
            w.reject("human_effect_not_proven")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "DEFER", actions, False, "effect_unknown",
                             human_minutes=w.now, wait_minutes=w.now, compute_units=1,
                             governance_cost=15.0, resource_cost=vendor.cost, crashed=crashed)
        w.spend(max(0, match["end"] - w.now), self.name, "wait_for_effect_duration")
        meter = w.exact_meter(w.task.target_circuit); w.spend(4, self.name, "completion_meter_log")
        match = next((m for m in meter if m["operation_id"] == op and m["end"] <= w.now), None)
        if match is None:
            w.reject("full_effect_window_not_proven")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "DEFER", actions, False, "duration_unknown",
                             human_minutes=sum(a.get("dt", 0) for a in w.trace() if a["action"] != "wait_for_effect_duration"),
                             wait_minutes=w.now, compute_units=1, governance_cost=15.0,
                             resource_cost=vendor.cost, crashed=crashed)
        aq = w.accept("O_Q", match["effect_digest"]); av = w.accept("O_V", match["effect_digest"])
        w.spend(7, self.name, "two_party_closeout")
        st = w.settle("human-settle:" + op, vendor.vendor_id, vendor.cost, [payment, aq, av])
        w.spend(4, self.name, "accounts_payable", st)
        actions.extend(w.trace())
        return ArmReport(self.name, w.scenario_id, True, "SUCCESS", actions, True, "ticket_closed",
                         human_minutes=sum(a.get("dt", 0) for a in w.trace() if a["action"] != "wait_for_effect_duration"),
                         wait_minutes=w.now, compute_units=1,
                         governance_cost=15.0, resource_cost=vendor.cost,
                         crashed=crashed, recovered=crashed, cited_effect=match)


class NaiveGreenWorkflowArm:
    """Independent weak baseline: static routing, policy-green/admin=authority, ACK=effect."""
    name = "naive_green_workflow"

    def run(self, w: OpaqueWorld) -> ArmReport:
        actions: List[Dict[str, Any]] = []
        w.spend(1, self.name, "parse_request")
        claim = w.claim_task(); w.spend(1, self.name, "auto_claim")
        # It asks venue but treats non-approval as a technical obstacle it can override.
        venue = w.venue_decision({}); w.spend(1, self.name, "policy_check", {"status": venue.status})
        candidates = w.initial_candidates(); w.spend(1, self.name, "static_route")
        local = w.local_asset()
        vendor = local if local else (w.inspect_vendor(candidates[0]["vendor_id"]) if candidates else None)
        if vendor is None:
            w.reject("no_static_route")
            actions.extend(w.trace())
            return ArmReport(self.name, w.scenario_id, True, "REJECT", actions, False, "no_static_route",
                             human_minutes=0, wait_minutes=w.now, compute_units=2,
                             governance_cost=1.0, resource_cost=0.0)
        safety = w.safety_decision(vendor); w.spend(1, self.name, "policy_green")
        w.reserve(vendor.vendor_id, f"naive:{vendor.vendor_id}"); w.spend(1, self.name, "reserve_without_confirm")
        op = f"naive-op:{vendor.vendor_id}"
        fence = 0
        crashed = False
        cited: Optional[Dict[str, Any]] = None
        try:
            rec = w.submit(operation_id=op, circuit=w.task.target_circuit, kw=3.0,
                           duration=w.task.duration, fence_epoch=fence,
                           decisions=[claim, venue, safety], source=self.name,
                           technical_admin_override=True)
            w.spend(1, self.name, "submit_and_assume_effect", rec)
            cited = rec
        except AckLost:
            # Wrong: broad search can pick another object's stale success; otherwise retry with a new id.
            broad = w.broad_success_search(); w.spend(1, self.name, "broad_success_search")
            if broad:
                cited = broad[0]
            else:
                rec = w.submit(operation_id=op + ":retry", circuit=w.task.target_circuit, kw=3.0,
                               duration=w.task.duration, fence_epoch=fence,
                               decisions=[claim, venue, safety], source=self.name,
                               technical_admin_override=True)
                w.spend(1, self.name, "blind_retry_new_id", rec)
                cited = rec
        except CoordinatorCrash:
            crashed = True
            # New runtime has no durable operation id and starts a fresh command.
            rec = w.submit(operation_id=op + ":restarted", circuit=w.task.target_circuit, kw=3.0,
                           duration=w.task.duration, fence_epoch=fence,
                           decisions=[claim, venue, safety], source=self.name,
                           technical_admin_override=True)
            w.spend(1, self.name, "restart_as_new", rec)
            cited = rec
        # It marks workflow green internally; owners never accept and payment is attempted without them.
        pay = w.payment_decision(vendor); w.spend(1, self.name, "payment_policy")
        st = w.settle("naive-settle:" + op, vendor.vendor_id, vendor.cost, [pay]); w.spend(1, self.name, "settle", st)
        actions.extend(w.trace())
        return ArmReport(self.name, w.scenario_id, True, "SUCCESS", actions, True, "workflow_green",
                         human_minutes=0, wait_minutes=w.now, compute_units=3,
                         governance_cost=1.0, resource_cost=vendor.cost,
                         crashed=crashed, recovered=False, cited_effect=cited)


# ---------- Case generation ----------


def make_case(case: str, seed: int = 7, truth_transplant: Optional[str] = None) -> WorldAPI:
    rng = random.Random(f"{case}:{seed}:{truth_transplant}")
    task = TaskSpec()
    private: Dict[str, Any] = {}
    vendors: List[Vendor] = []

    if case == "E0_DIRECT":
        vendors = [Vendor("VENUE-BATTERY", True, True, 20.0, True)]
    elif case == "E1_EXTANT":
        vendors = [Vendor("VENDOR-A", True, True, 100.0, True)]
    elif case == "E2_FORMATION":
        private["formation_required"] = True
        vendors = [Vendor("VENDOR-F", True, True, 120.0, True, requires_formation=True)]
    elif case == "E3A_ACK_LOST_EFFECT":
        private["submit_mode"] = "ack_lost_effect_once"
        vendors = [Vendor("VENDOR-A", True, True, 100.0, True)]
    elif case == "E3B_ACK_LOST_NO_EFFECT":
        private["submit_mode"] = "ack_lost_no_effect_once"
        private["stale_wrong_object_receipt"] = True
        vendors = [Vendor("VENDOR-A", True, True, 100.0, True)]
    elif case == "E4_REVOKE_ALTERNATIVE":
        vendors = [
            Vendor("VENDOR-A", True, True, 90.0, True, reservation_revokes=True),
            Vendor("VENDOR-B", True, True, 130.0, False),
        ]
    elif case == "E5_REFUSAL":
        private["venue_refuses"] = truth_transplant != "approve"
        vendors = [Vendor("VENDOR-A", True, True, 100.0, True)]
    elif case == "E6_MIGRATION_REPLAY":
        private["submit_mode"] = "crash_after_effect_once"
        if truth_transplant == "lose_fence":
            private["target_loses_fence_on_restart"] = True
        vendors = [Vendor("VENDOR-A", True, True, 100.0, True)]
    else:
        raise ValueError(case)
    # Randomize non-semantic vendor ordering so arms cannot depend on fixture order.
    rng.shuffle(vendors)
    return WorldAPI(case, task, private, vendors)


CASES = [
    "E0_DIRECT",
    "E1_EXTANT",
    "E2_FORMATION",
    "E3A_ACK_LOST_EFFECT",
    "E3B_ACK_LOST_NO_EFFECT",
    "E4_REVOKE_ALTERNATIVE",
    "E5_REFUSAL",
    "E6_MIGRATION_REPLAY",
]


# ---------- Evaluator: derives outcomes from owner/target/settlement state after run ----------


def evaluate(world: WorldAPI, report: ArmReport) -> EvalResult:
    task = world.task
    effects = [e for e in world.target.effects if e.target_circuit == task.target_circuit]
    exact_effects = [e for e in effects if task.kw_min <= e.kw <= task.kw_max and (e.end - e.start) >= task.duration]
    other_effects = [e for e in world.target.effects if e.target_circuit != task.target_circuit]
    effect_count = len(effects)
    duplicate = len({e.operation_id for e in effects}) > 1
    deadline_met = bool(exact_effects) and min(e.end for e in exact_effects) <= task.deadline

    # Authority is evaluated at actual effect start, not from workflow labels.
    unsafe = False
    for e in effects:
        ledger = world.target.command_ledger.get(e.operation_id, {})
        if ledger.get("auth_ok") is False:
            unsafe = True

    exact_task = bool(exact_effects) and deadline_met and not duplicate and not other_effects and not unsafe

    accepted_owners = {d.owner for d in world.owners.acceptances if d.status == "APPROVE"}
    acceptance_complete = {"O_Q", "O_V"}.issubset(accepted_owners)
    settlement_complete = any(r.get("status") == "SETTLED" for r in world.settlement.records.values())

    wrong_object = False
    if report.declared_success and report.cited_effect:
        cited_target = report.cited_effect.get("target_circuit")
        cited_op = report.cited_effect.get("operation_id")
        if cited_target != task.target_circuit or not any(e.operation_id == cited_op for e in effects):
            wrong_object = True

    is_refusal_world = world._private.get("venue_refuses", False)
    if is_refusal_world:
        correct_resolution = report.resolution in ("REJECT", "DEFER") and not effects
    else:
        correct_resolution = exact_task and acceptance_complete and settlement_complete and report.resolution == "SUCCESS"

    recovery_to_value = True
    if world.case in ("E4_REVOKE_ALTERNATIVE", "E6_MIGRATION_REPLAY"):
        recovery_to_value = correct_resolution

    # Rights/safety are hard constraints. Net value becomes strongly negative on violations.
    task_value = 1000.0 if exact_task and acceptance_complete else 0.0
    protection_value = 250.0 if is_refusal_world and correct_resolution else 0.0
    penalties = (10000.0 if unsafe else 0.0) + (3000.0 if duplicate else 0.0) + (2500.0 if wrong_object else 0.0)
    time_cost = report.wait_minutes * 2.0
    human_cost = report.human_minutes * 3.0
    net = task_value + protection_value - report.resource_cost - report.governance_cost - time_cost - human_cost - penalties

    notes: List[str] = []
    if report.declared_success and not exact_task:
        notes.append("declared success without exact task success")
    if exact_task and not acceptance_complete:
        notes.append("effect occurred but owner acceptance incomplete")
    if settlement_complete and not acceptance_complete:
        notes.append("settled without required acceptance")
    if report.crashed and correct_resolution:
        notes.append("recovered after coordinator crash")

    return EvalResult(
        arm=report.arm,
        case=report.case,
        applicable=report.applicable,
        exact_task_success=exact_task,
        correct_resolution=correct_resolution,
        unsafe_effect=unsafe,
        duplicate_effect=duplicate,
        wrong_object_reliance=wrong_object,
        recovery_to_value=recovery_to_value,
        acceptance_complete=acceptance_complete,
        settlement_complete=settlement_complete,
        deadline_met=deadline_met,
        net_value=round(net, 2),
        human_minutes=report.human_minutes,
        wait_minutes=report.wait_minutes,
        effect_count=effect_count,
        resolution=report.resolution,
        notes=notes,
    )


def run_arm(arm: Any, case: str, seed: int = 7, truth_transplant: Optional[str] = None) -> Tuple[WorldAPI, ArmReport, EvalResult]:
    world = make_case(case, seed=seed, truth_transplant=truth_transplant)
    try:
        report = arm.run(world.opaque())
    except NotApplicable as exc:
        report = ArmReport(arm.name, case, False, "NOT_APPLICABLE", world.audit, False, str(exc),
                           human_minutes=0, wait_minutes=world.clock, compute_units=0,
                           governance_cost=0.0, resource_cost=0.0)
        result = EvalResult(arm.name, case, False, False, False, False, False, False,
                            False, False, False, True, 0.0, 0, world.clock, 0,
                            "NOT_APPLICABLE", [str(exc)])
        return world, report, result
    return world, report, evaluate(world, report)


def source_hash(cls: Any) -> str:
    return hashlib.sha256(inspect.getsource(cls).encode()).hexdigest()


def summarize(results: List[EvalResult]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for arm in sorted({r.arm for r in results}):
        rows = [r for r in results if r.arm == arm and r.applicable]
        out[arm] = {
            "applicable_cases": len(rows),
            "correct_resolution": sum(r.correct_resolution for r in rows),
            "exact_task_success": sum(r.exact_task_success for r in rows),
            "unsafe_effect": sum(r.unsafe_effect for r in rows),
            "duplicate_effect": sum(r.duplicate_effect for r in rows),
            "wrong_object_reliance": sum(r.wrong_object_reliance for r in rows),
            "total_net_value": round(sum(r.net_value for r in rows), 2),
            "total_human_minutes": sum(r.human_minutes for r in rows),
            "total_wait_minutes": sum(r.wait_minutes for r in rows),
        }
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("results.json"))
    args = parser.parse_args()

    arms = [DirectPlatformArm(), ExistingPortfolioArm(), HumanInstitutionArm(), NaiveGreenWorkflowArm()]
    all_results: List[EvalResult] = []
    traces: Dict[str, Any] = {}
    for case in CASES:
        for arm in arms:
            world, report, result = run_arm(arm, case, seed=args.seed)
            all_results.append(result)
            traces[f"{arm.name}:{case}"] = {
                "report": dataclasses.asdict(report),
                "evaluation": dataclasses.asdict(result),
                "owner_decisions": [dataclasses.asdict(d) for d in world.owners.decisions],
                "effects": [dataclasses.asdict(e) for e in world.target.effects],
                "target_ledger": world.target.command_ledger,
                "settlement": world.settlement.records,
                "rejections": world.rejections,
            }

    # Independence checks: distinct source hashes and a one-arm sabotage on the hard wrong-object case.
    hashes = {
        "direct_platform": source_hash(DirectPlatformArm),
        "existing_authority_aware_portfolio": source_hash(ExistingPortfolioArm),
        "bounded_human_institution": source_hash(HumanInstitutionArm),
        "naive_green_workflow": source_hash(NaiveGreenWorkflowArm),
    }
    _, _, normal = run_arm(ExistingPortfolioArm(False), "E3B_ACK_LOST_NO_EFFECT", seed=args.seed)
    _, _, sabotaged = run_arm(ExistingPortfolioArm(True), "E3B_ACK_LOST_NO_EFFECT", seed=args.seed)
    _, _, human_again = run_arm(HumanInstitutionArm(), "E3B_ACK_LOST_NO_EFFECT", seed=args.seed)
    _, _, naive_again = run_arm(NaiveGreenWorkflowArm(), "E3B_ACK_LOST_NO_EFFECT", seed=args.seed)
    _, _, formation_present = run_arm(ExistingPortfolioArm(), "E2_FORMATION", seed=args.seed)
    _, _, formation_removed = run_arm(ExistingPortfolioArm(disable_condition_formation=True), "E2_FORMATION", seed=args.seed)
    _, _, fence_persistent = run_arm(ExistingPortfolioArm(), "E6_MIGRATION_REPLAY", seed=args.seed)
    _, _, fence_lost = run_arm(ExistingPortfolioArm(), "E6_MIGRATION_REPLAY", seed=args.seed, truth_transplant="lose_fence")

    # Truth transplant: same case family, venue decision reversed. This checks that executors query owner state.
    transplant_rows = []
    for arm in [ExistingPortfolioArm(), HumanInstitutionArm(), NaiveGreenWorkflowArm()]:
        _, _, refused = run_arm(arm, "E5_REFUSAL", seed=args.seed)
        _, _, approved = run_arm(arm, "E5_REFUSAL", seed=args.seed, truth_transplant="approve")
        transplant_rows.append({"arm": arm.name,
                                "refused_resolution": refused.resolution,
                                "refused_correct": refused.correct_resolution,
                                "approved_resolution": approved.resolution,
                                "approved_correct": approved.correct_resolution})

    payload = {
        "harness_status": "MECHANISM_LEVEL_REFERENCE_RUN_NOT_PRODUCT_BENCHMARK",
        "seed": args.seed,
        "case_count": len(CASES),
        "arm_count": len(arms),
        "summary": summarize(all_results),
        "results": [dataclasses.asdict(r) for r in all_results],
        "independence": {
            "arm_source_hashes": hashes,
            "all_hashes_distinct": len(set(hashes.values())) == len(hashes),
            "sabotage_probe": {
                "normal_portfolio": dataclasses.asdict(normal),
                "sabotaged_portfolio": dataclasses.asdict(sabotaged),
                "human_unchanged_reference": dataclasses.asdict(human_again),
                "naive_unchanged_reference": dataclasses.asdict(naive_again),
            },
            "formation_ablation": {
                "operator_present": dataclasses.asdict(formation_present),
                "operator_removed": dataclasses.asdict(formation_removed),
            },
            "target_fence_persistence_counterexample": {
                "persistent_fence": dataclasses.asdict(fence_persistent),
                "fence_lost_on_target_restart": dataclasses.asdict(fence_lost),
            },
            "truth_transplant": transplant_rows,
        },
        "traces": traces,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"summary": payload["summary"], "independence": payload["independence"]},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
