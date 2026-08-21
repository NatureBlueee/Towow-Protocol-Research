"""Runtime-random principal holder objects and verifiable execution receipts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from typing import Callable

from .spec import (
    OLD_TASK,
    canonical_json,
    expected_action_payload,
    expected_holder,
    fingerprint,
)


@dataclass(frozen=True)
class ActionRequest:
    action: str
    payload: dict[str, str]
    task_fingerprint: str


@dataclass(frozen=True)
class Receipt:
    receipt_id: str
    action: str
    holder_id: str
    executor_object_id: str
    payload_hash: str
    task_fingerprint: str
    sequence: int
    effect_log_id: str
    before_state_digest: str
    after_state_digest: str
    success: bool
    signature: str


@dataclass(frozen=True)
class EffectClaim:
    effect_log_id: str
    before_state_digest: str
    after_state_digest: str
    success: bool


class PrincipalHolder:
    """The holder object checks policy and invokes the privileged effect itself."""

    def __init__(
        self,
        holder_id: str,
        policy_allows: Callable[[ActionRequest], bool],
        effect: Callable[[ActionRequest, str], EffectClaim],
    ):
        self.holder_id = holder_id
        self.executor_object_id = f"holder-object:{holder_id}"
        self._policy_allows = policy_allows
        self._effect = effect
        self._secret = os.urandom(32)
        self._sequence = 0

    def _message(
        self,
        action: str,
        receipt_id: str,
        payload_hash: str,
        task_fingerprint: str,
        sequence: int,
        effect_claim: EffectClaim,
    ) -> bytes:
        return canonical_json(
            {
                "action": action,
                "receipt_id": receipt_id,
                "holder_id": self.holder_id,
                "executor_object_id": self.executor_object_id,
                "payload_hash": payload_hash,
                "task_fingerprint": task_fingerprint,
                "sequence": sequence,
                "effect_log_id": effect_claim.effect_log_id,
                "before_state_digest": effect_claim.before_state_digest,
                "after_state_digest": effect_claim.after_state_digest,
                "success": effect_claim.success,
            }
        ).encode("utf-8")

    def execute(
        self,
        request: ActionRequest,
    ) -> Receipt | None:
        if (
            expected_holder(request.action) != self.holder_id
            or request.task_fingerprint != fingerprint(OLD_TASK)
            or request.payload != expected_action_payload(request.action)
        ):
            return None
        if not self._policy_allows(request):
            return None
        self._sequence += 1
        receipt_id = (
            f"{self.holder_id}:{self._sequence}:{request.action}"
        )
        effect_claim = self._effect(request, receipt_id)
        if not effect_claim.success:
            return None
        payload_hash = hashlib.sha256(
            canonical_json(request.payload).encode("utf-8")
        ).hexdigest()
        message = self._message(
            request.action,
            receipt_id,
            payload_hash,
            request.task_fingerprint,
            self._sequence,
            effect_claim,
        )
        signature = hmac.new(
            self._secret, message, hashlib.sha256
        ).hexdigest()
        receipt = Receipt(
            receipt_id=receipt_id,
            action=request.action,
            holder_id=self.holder_id,
            executor_object_id=self.executor_object_id,
            payload_hash=payload_hash,
            task_fingerprint=request.task_fingerprint,
            sequence=self._sequence,
            effect_log_id=effect_claim.effect_log_id,
            before_state_digest=effect_claim.before_state_digest,
            after_state_digest=effect_claim.after_state_digest,
            success=effect_claim.success,
            signature=signature,
        )
        return receipt

    def verify(self, receipt: Receipt) -> bool:
        if (
            receipt.holder_id != self.holder_id
            or receipt.executor_object_id != self.executor_object_id
        ):
            return False
        message = self._message(
            receipt.action,
            receipt.receipt_id,
            receipt.payload_hash,
            receipt.task_fingerprint,
            receipt.sequence,
            EffectClaim(
                effect_log_id=receipt.effect_log_id,
                before_state_digest=receipt.before_state_digest,
                after_state_digest=receipt.after_state_digest,
                success=receipt.success,
            ),
        )
        expected = hmac.new(
            self._secret, message, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, receipt.signature)


class HolderRegistry:
    def __init__(
        self,
        policy_allows: Callable[[ActionRequest], bool],
        effect: Callable[[ActionRequest, str], EffectClaim],
    ):
        self._holders = {
            holder: PrincipalHolder(holder, policy_allows, effect)
            for holder in ("O", "P", "T", "H", "A", "W")
        }

    def dispatch(
        self,
        request: ActionRequest,
    ) -> Receipt | None:
        holder_id = expected_holder(request.action)
        if holder_id is None:
            raise ValueError(f"{request.action} is not a privileged action")
        return self._holders[holder_id].execute(request)

    def verify(self, receipt: Receipt) -> bool:
        holder = self._holders.get(receipt.holder_id)
        if holder is None:
            return False
        return holder.verify(receipt)
