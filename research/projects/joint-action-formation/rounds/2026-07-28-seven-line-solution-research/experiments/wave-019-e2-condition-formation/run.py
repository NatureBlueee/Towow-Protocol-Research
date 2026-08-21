#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from e2_runtime import run_suite


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
    )
    args = parser.parse_args()
    result = run_suite(args.output)
    print(
        json.dumps(
            {
                "status": result["status"],
                "suite_dir": result["suite_dir"],
                "cases": result["cases"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
