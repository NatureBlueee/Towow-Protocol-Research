#!/usr/bin/env python3
"""Tiny JSON-lines client shared by independent worker processes.

This module contains transport only. It has no decision, oracle, evaluator, or
service interpretation logic.
"""

from __future__ import annotations

import json
import sys
from typing import Any


PREDICTIONS = {"YES", "NO", "ABSTAIN"}


class BrokerClient:
    def __init__(self) -> None:
        first = sys.stdin.readline()
        if not first:
            raise RuntimeError("missing start message")
        message = json.loads(first)
        if message.get("type") != "start":
            raise RuntimeError("first message must be start")
        self.packet: dict[str, Any] = message["public_packet"]
        self.available = set(message["available_primitives"])

    def _send(self, message: dict[str, Any], expect_reply: bool = True) -> dict[str, Any]:
        sys.stdout.write(json.dumps(message, sort_keys=True, separators=(",", ":")) + "\n")
        sys.stdout.flush()
        if not expect_reply:
            return {}
        reply = sys.stdin.readline()
        if not reply:
            raise RuntimeError("broker closed")
        return json.loads(reply)

    def predict(self, stage: str, predictions: dict[str, str]) -> None:
        required = {"Y_success", "Y_resolution", "Y_effect", "Y_acceptance"}
        if set(predictions) != required:
            raise ValueError("prediction must keep four outcomes separate")
        if not set(predictions.values()) <= PREDICTIONS:
            raise ValueError("invalid prediction value")
        reply = self._send(
            {"type": "prediction", "stage": stage, "predictions": predictions}
        )
        if reply.get("type") != "ack":
            raise RuntimeError("prediction not acknowledged")

    def call(self, action: str, **args: Any) -> dict[str, Any] | None:
        if action not in self.available:
            raise PermissionError(f"primitive unavailable: {action}")
        reply = self._send({"type": "action", "action": action, "args": args})
        if reply.get("type") != "response":
            raise RuntimeError("invalid primitive response envelope")
        return reply.get("raw")

    def finish(self, notes: list[str]) -> None:
        self._send({"type": "result", "notes": notes}, expect_reply=False)


def abstain_all() -> dict[str, str]:
    return {
        "Y_success": "ABSTAIN",
        "Y_resolution": "ABSTAIN",
        "Y_effect": "ABSTAIN",
        "Y_acceptance": "ABSTAIN",
    }
