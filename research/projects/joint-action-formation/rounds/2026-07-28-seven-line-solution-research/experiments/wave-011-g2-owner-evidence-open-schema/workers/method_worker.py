#!/usr/bin/env python3
"""Untrusted method subprocess: public world + signed owner evidence in."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2o1.actors import canonical_bytes  # noqa: E402
from g2o1.methods import run_method  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    packet = json.loads(sys.stdin.buffer.read())
    if any("private" in key.lower() and key != "owner_packet" for key in packet):
        raise ValueError("METHOD_RECEIVED_PRIVATE_CHANNEL")
    owner_packet = packet["owner_packet"]
    if owner_packet.get("key_material_exported") is not False:
        raise ValueError("OWNER_KEY_BOUNDARY_NOT_ATTESTED")
    result = run_method(sys.argv[1], packet["world"], owner_packet)
    result["method_worker_pid"] = os.getpid()
    result["received_owner_keys"] = False
    sys.stdout.buffer.write(canonical_bytes(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
