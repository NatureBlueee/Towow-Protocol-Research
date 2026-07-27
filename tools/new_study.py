#!/usr/bin/env python3
"""Create an optional blank research project without imposing a methodology."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="short lowercase project name")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,48}", args.name):
        print("name must match [a-z0-9][a-z0-9-]{1,48}", file=sys.stderr)
        return 2

    project = args.root.resolve() / "research" / "projects" / args.name
    if project.exists():
        print(f"refusing to overwrite existing project: {project}", file=sys.stderr)
        return 3

    project.mkdir(parents=True)
    for directory in ("notes", "evidence", "experiments", "artifacts"):
        (project / directory).mkdir()
        (project / directory / ".gitkeep").touch()

    readme = f"""# {args.name}

This project is intentionally blank. Organize it around the research problem, not this scaffold.

Start by writing only what is useful:

- what you are trying to understand;
- why it may change a decision;
- the next action most likely to produce new information;
- where durable evidence and results should live.
"""
    (project / "README.md").write_text(readme, encoding="utf-8")
    print(project)
    return 0


if __name__ == "__main__":
    sys.exit(main())
