from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class JsonLineProcess:
    def __init__(
        self,
        argv: list[str],
        *,
        service_id: str,
        trace: list[dict[str, Any]],
    ) -> None:
        self.service_id = service_id
        self.trace = trace
        self.process = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    @property
    def pid(self) -> int:
        return self.process.pid

    def request(
        self, command: dict[str, Any], *, phase: str, cell_id: str
    ) -> dict[str, Any]:
        if self.process.stdin is None or self.process.stdout is None:
            raise RuntimeError("worker pipes unavailable")
        self.process.stdin.write(json.dumps(command, ensure_ascii=False, sort_keys=True) + "\n")
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            stderr = self.process.stderr.read() if self.process.stderr else ""
            raise RuntimeError(f"{self.service_id} exited without response: {stderr}")
        response = json.loads(line)
        self.trace.append(
            {
                "cell_id": cell_id,
                "phase": phase,
                "service_id": self.service_id,
                "service_pid": self.pid,
                "command": command,
                "response": response,
            }
        )
        return response

    def close(self) -> None:
        if self.process.stdin:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=3)
        if self.process.stdout:
            self.process.stdout.close()
        if self.process.stderr:
            self.process.stderr.close()


def scrub_private_runtime(path: Path) -> None:
    # This helper exists only to centralize the explicit runtime boundary.
    # The caller owns lifecycle cleanup; no broad path or glob is accepted.
    if path.name != "current":
        raise ValueError("refusing to identify a non-current runtime as private runtime")
