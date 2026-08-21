#!/usr/bin/env python3
"""Target-side fence simulator with persistent readback."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class Target:
    def __init__(self, store: Path, mode: str) -> None:
        self.store = store
        self.mode = mode
        if store.exists():
            self.state = json.loads(store.read_text(encoding="utf-8"))
        else:
            self.state = {
                "max_fence": 0,
                "region_max": {"A": 0, "B": 0},
                "effects": [],
            }
            self._save()

    def _save(self) -> None:
        self.store.parent.mkdir(parents=True, exist_ok=True)
        self.store.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        op = command["op"]
        if op == "ADVANCE":
            token = int(command["fence"])
            region = command.get("region", "A")
            self.state["max_fence"] = max(self.state["max_fence"], token)
            self.state["region_max"][region] = max(self.state["region_max"][region], token)
            if self.mode != "cross_region_reorder":
                for name in self.state["region_max"]:
                    self.state["region_max"][name] = max(
                        self.state["region_max"][name], token
                    )
            self._save()
            return {"status": "ADVANCED", "fence": token}
        if op == "RESTART":
            if self.mode == "restart_loss":
                self.state["max_fence"] = 0
                self.state["region_max"] = {"A": 0, "B": 0}
                self._save()
            return {"status": "RESTARTED", "mode": self.mode}
        if op == "EXECUTE":
            token = int(command["fence"])
            region = command.get("region", "A")
            required = (
                self.state["region_max"][region]
                if self.mode == "cross_region_reorder"
                else self.state["max_fence"]
            )
            accepted = self.mode == "ignore" or token >= required
            if accepted:
                self.state["effects"].append(
                    {
                        "operation_hash": command["operation_hash"],
                        "fence": token,
                        "required_fence": required,
                        "region": region,
                    }
                )
                self.state["max_fence"] = max(self.state["max_fence"], token)
                self.state["region_max"][region] = max(
                    self.state["region_max"][region], token
                )
                self._save()
                return {"status": "EFFECT_CREATED", "stale": token < required}
            return {"status": "STALE_FENCE_REJECTED", "required_fence": required}
        if op == "READBACK":
            return {"status": "OK", "state": self.state}
        return {"status": "UNKNOWN_COMMAND", "op": op}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=["strict", "ignore", "restart_loss", "cross_region_reorder"],
        required=True,
    )
    args = parser.parse_args()
    target = Target(args.store, args.mode)
    for line in sys.stdin:
        if not line.strip():
            continue
        response = target.handle(json.loads(line))
        sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
