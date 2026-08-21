#!/usr/bin/env python3
"""Mutation worker used only to prove method-process isolation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from worker_runtime import BrokerClient, abstain_all  # noqa: E402


client = BrokerClient()
client.predict("P0", abstain_all())
client.predict("P1", abstain_all())
client.finish(["deliberate sabotage mutation"])
