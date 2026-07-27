#!/usr/bin/env python3
"""Run one evidence-captured, tool-less model turn.

Private prompt content is read from stdin or a file and passed to Claude on
stdin. It is never placed in argv. The caller supplies a JSON Schema so every
turn has a condition-independent, machine-readable action surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--schema-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--max-budget-usd", type=float, default=0.75)
    args = parser.parse_args()

    prompt = args.prompt_file.read_text(encoding="utf-8")
    schema = json.loads(args.schema_file.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    system_prompt = (
        "You are one bounded participant in a local, non-production engineering "
        "experiment. You have no tools. Use only the supplied context. Do not "
        "claim access to files, agents, tests, or facts not present. You may ask, "
        "refuse, return UNKNOWN, counter, propose, accept, or reject according to "
        "your role and authority. Preserve the original goal and report uncertainty."
    )
    command = [
        "claude",
        "-p",
        "--safe-mode",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--no-chrome",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, separators=(",", ":"), ensure_ascii=False),
        "--system-prompt",
        system_prompt,
        "--model",
        args.model,
        "--max-budget-usd",
        str(args.max_budget_usd),
    ]

    started = _utc_now()
    start = time.monotonic()
    completed = subprocess.run(
        command,
        input=prompt,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed = time.monotonic() - start
    ended = _utc_now()

    (args.output_dir / "stdout.json").write_text(completed.stdout, encoding="utf-8")
    (args.output_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    request = {
        "role": args.role,
        "model_alias": args.model,
        "runner": "claude",
        "runner_version": "2.1.219",
        "started_at_utc": started,
        "ended_at_utc": ended,
        "wall_clock_seconds": elapsed,
        "exit_code": completed.returncode,
        "prompt_path": str(args.prompt_file),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "prompt_bytes": len(prompt.encode()),
        "schema_path": str(args.schema_file),
        "schema_sha256": hashlib.sha256(
            json.dumps(schema, sort_keys=True).encode()
        ).hexdigest(),
        "private_prompt_in_argv": False,
        "tools": [],
        "flags": [
            "safe-mode",
            "tools-empty",
            "permission-mode=dontAsk",
            "no-chrome",
            "no-session-persistence",
            "output-format=json",
            "json-schema",
        ],
        "max_budget_usd": args.max_budget_usd,
    }
    (args.output_dir / "request.json").write_text(
        json.dumps(request, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    parsed: object
    try:
        parsed = json.loads(completed.stdout)
    except json.JSONDecodeError:
        parsed = {
            "parse_error": "stdout was not one JSON document",
            "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        }
    (args.output_dir / "parsed.json").write_text(
        json.dumps(parsed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(request, ensure_ascii=False))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
