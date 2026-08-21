#!/usr/bin/env python3
"""Run truthful HW-B direct, derived and reciprocal controller actions."""

from __future__ import annotations

import json
from pathlib import Path

import adapter


HERE = Path(__file__).resolve().parent
STATE_PATH = HERE / "state" / "controller-state.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run() -> dict:
    adapter.materialize()
    contract = load(HERE / "normalized" / "contract.json")
    requests = {
        label: load(HERE / "normalized" / "inputs" / f"{label}.json")
        for label in ("direct", "derived", "reciprocal")
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if STATE_PATH.exists():
        STATE_PATH.unlink()

    direct = adapter.EXECUTOR.execute_persisted(
        contract, requests["direct"], STATE_PATH
    )
    adapter.write_json(HERE / "outputs" / "helios-direct.json", direct)

    derived = adapter.EXECUTOR.execute_persisted(
        contract, requests["derived"], STATE_PATH
    )
    adapter.write_json(HERE / "outputs" / "ion-derived.json", derived)

    reciprocal = adapter.EXECUTOR.execute_persisted(
        contract, requests["reciprocal"], STATE_PATH
    )
    reciprocal_record = {
        "status": "EXECUTED",
        "development_label": "DEVELOPMENT_POST_FEEDBACK_NOT_BLIND",
        "controller_result": reciprocal,
    }
    adapter.write_json(
        HERE / "outputs" / "reciprocal-juniper-kite.json",
        reciprocal_record,
    )
    return {
        "direct": direct,
        "derived": derived,
        "reciprocal": reciprocal_record,
    }


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, sort_keys=True, indent=2))
