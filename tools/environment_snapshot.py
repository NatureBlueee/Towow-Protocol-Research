#!/usr/bin/env python3
"""Print a small, redacted snapshot of the current local research environment."""

from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


ROOT = Path(__file__).resolve().parents[1]


def command(args: List[str]) -> Optional[str]:
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main() -> None:
    head = command(["git", "rev-parse", "HEAD"])
    branch = command(["git", "branch", "--show-current"])
    status = command(["git", "status", "--short", "--untracked-files=normal"]) or ""
    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "workspace": str(ROOT),
        "os": platform.platform(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "git": {
            "branch": branch,
            "head": head,
            "unborn": head is None,
            "dirty": bool(status),
            "status": status.splitlines(),
        },
        "active_agent_instructions": ["AGENTS.md"],
        "active_seed_packet": "towow_a2a_round5_codex_local_research_packet_v1.1",
        "network_tested": False,
        "secrets_included": False,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
