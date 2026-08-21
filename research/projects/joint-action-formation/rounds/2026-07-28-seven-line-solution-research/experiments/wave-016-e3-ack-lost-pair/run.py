#!/usr/bin/env python3
"""Run the Wave 016 E3 paired-world experiment."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pair_runtime import run_pair


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
    )
    args = parser.parse_args()
    result = run_pair(args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "run_dir": result["run_dir"],
                "pair_evaluation": result["pair_evaluation"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
