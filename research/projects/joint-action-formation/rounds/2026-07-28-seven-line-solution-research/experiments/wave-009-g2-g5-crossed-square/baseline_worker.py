#!/usr/bin/env python3
"""Untrusted baseline-side process: public packet in, candidate JSON out."""

from __future__ import annotations

import json
import sys

from baselines import run_baseline


def main() -> int:
    if len(sys.argv) != 2:
        return 2
    raw = sys.stdin.buffer.read()
    packet = json.loads(raw.decode("utf-8"))
    result = run_baseline(sys.argv[1], packet)
    sys.stdout.buffer.write(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
