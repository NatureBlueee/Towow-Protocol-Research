#!/usr/bin/env python3
"""Isolated public-worker launcher.

The process starts outside the experiment directory with a minimal environment
and installs a non-removable Python audit hook before importing worker code.
The hook denies private truth and all owner/grader/runner implementation reads.
"""

from __future__ import annotations

import os
import runpy
import sys
import importlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = next(
    parent for parent in ROOT.parents if parent.name == "通爻协议研究"
)
ALLOWED_WORKSPACE_FILES = {
    ROOT / "worker_capsule.py",
    *{
        ROOT / "formation" / f"{name}.py"
        for name in (
            "__init__",
            "worker_process",
            "execution_service",
            "protocol",
            "models",
            "canonical",
        )
    },
}
ALLOWED_PYC_STEMS = {
    "__init__",
    "worker_process",
    "execution_service",
    "protocol",
    "models",
    "canonical",
}


def _workspace_path(value: object) -> Path | None:
    if isinstance(value, int):
        return None
    try:
        candidate = Path(os.fsdecode(value)).resolve()
    except (TypeError, ValueError, OSError):
        return None
    if candidate == WORKSPACE_ROOT or WORKSPACE_ROOT in candidate.parents:
        return candidate
    return None


def _is_allowed_workspace_file(candidate: Path) -> bool:
    if candidate in ALLOWED_WORKSPACE_FILES:
        return True
    if candidate.parent == ROOT / "formation" / "__pycache__":
        return any(
            candidate.name.startswith(f"{stem}.")
            and candidate.suffix == ".pyc"
            for stem in ALLOWED_PYC_STEMS
        )
    return False


def _audit(event: str, args: tuple[object, ...]) -> None:
    if event == "open" and args:
        candidate = _workspace_path(args[0])
        if candidate is not None and not _is_allowed_workspace_file(candidate):
            raise PermissionError(f"WORKER_CAPSULE_READ_DENIED:{args[0]}")


def main() -> int:
    sys.addaudithook(_audit)
    if len(sys.argv) == 3 and sys.argv[1] == "--probe-denied-read":
        try:
            Path(sys.argv[2]).read_bytes()
        except PermissionError as error:
            print(str(error))
            return 77
        print("UNEXPECTED_READ_ALLOWED")
        return 1
    if len(sys.argv) == 3 and sys.argv[1] == "--probe-denied-import":
        sys.path.insert(0, str(ROOT))
        try:
            importlib.import_module(sys.argv[2])
        except PermissionError as error:
            print(str(error))
            return 78
        print("UNEXPECTED_IMPORT_ALLOWED")
        return 1
    sys.path.insert(0, str(ROOT))
    runpy.run_module("formation.worker_process", run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
