"""Independent worker executable registry and subprocess launcher."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
WORKER_DIR = ROOT / "workers"
WORKERS = {
    "strong_center": WORKER_DIR / "strong_center.py",
    "mature_composition": WORKER_DIR / "mature_composition.py",
    "human_institution": WORKER_DIR / "human_institution.py",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker_manifest() -> dict[str, Any]:
    return {
        name: {
            "source": f"workers/{path.name}",
            "source_sha256": _sha256(path),
            "executable_identity": f"{sys.executable}:{path.resolve()}",
            "decision_module": path.name,
        }
        for name, path in WORKERS.items()
    }


def validate_independent_workers() -> None:
    paths = [path.resolve() for path in WORKERS.values()]
    hashes = [_sha256(path) for path in WORKERS.values()]
    if len(paths) != len(set(paths)):
        raise RuntimeError("worker executable paths are aliased")
    if len(hashes) != len(set(hashes)):
        raise RuntimeError("worker source hashes are aliased")


def run_worker(name: str, packet: dict[str, Any], timeout_seconds: int = 10) -> dict[str, Any]:
    if name not in WORKERS:
        raise KeyError(name)
    validate_independent_workers()
    completed = subprocess.run(
        [sys.executable, str(WORKERS[name])],
        input=json.dumps(packet, ensure_ascii=False, sort_keys=True),
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
        cwd=ROOT,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{name} failed rc={completed.returncode}: {completed.stderr.strip()}"
        )
    output = json.loads(completed.stdout)
    if not isinstance(output, dict):
        raise ValueError(f"{name}: output is not a JSON object")
    if output.get("implementation") != name:
        raise ValueError(f"{name}: implementation identity mismatch")
    return output
