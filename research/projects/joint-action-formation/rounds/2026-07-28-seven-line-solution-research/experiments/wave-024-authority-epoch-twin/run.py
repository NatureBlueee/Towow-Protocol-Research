#!/usr/bin/env python3
"""Run the Wave 024 local Authority-epoch twin."""

from __future__ import annotations

import argparse
import json
import pathlib

from twin_runtime import run_twin


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent / "artifacts",
    )
    args = parser.parse_args()
    result = run_twin(args.output_root)
    print(
        json.dumps(
            {
                "status": result["status"],
                "run_dir": result["run_dir"],
                "results": result["results"],
                "twin_artifact_sha256": result["twin_artifact_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
