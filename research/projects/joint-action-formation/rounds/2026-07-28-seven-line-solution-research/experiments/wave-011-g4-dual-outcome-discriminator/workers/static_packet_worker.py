#!/usr/bin/env python3
"""Static packet baseline with no primitive calls or world intervention."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker_runtime import BrokerClient  # noqa: E402


client = BrokerClient()
values = {
    str(item.get("value", "")).upper()
    for item in client.packet.get("initial_evidence", [])
}
success = (
    "YES"
    if values & {"SERVING", "READY", "GREEN", "MACHINE OPERATIONAL"}
    else "ABSTAIN"
)
prediction = {
    "Y_success": success,
    "Y_resolution": "ABSTAIN",
    "Y_effect": "ABSTAIN",
    "Y_acceptance": "ABSTAIN",
}
client.predict("P0", prediction)
client.predict("P1", prediction)
client.finish(["static evidence only; no current query or formation"])
