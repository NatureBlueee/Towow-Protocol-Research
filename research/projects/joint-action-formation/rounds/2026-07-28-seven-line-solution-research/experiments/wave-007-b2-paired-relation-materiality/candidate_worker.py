#!/usr/bin/env python3
"""Spawned candidate process speaking newline-delimited JSON-RPC."""

from __future__ import annotations

import json
import sys
from typing import Any

from candidate import run_candidate
from public_api import JsonRpcEvidenceGateway


class ParentRpcClient:
    __slots__ = ("_next_id",)

    def __init__(self) -> None:
        self._next_id = 1

    def call(self, method: str, params: dict[str, Any]) -> Any:
        request_id = self._next_id
        self._next_id += 1
        print(
            json.dumps(
                {
                    "type": "request",
                    "id": request_id,
                    "method": method,
                    "params": params,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
        response_line = sys.stdin.readline()
        if not response_line:
            raise RuntimeError("PARENT_RPC_CLOSED")
        response = json.loads(response_line)
        if (
            response.get("type") != "response"
            or response.get("id") != request_id
        ):
            raise RuntimeError("PARENT_RPC_PROTOCOL_MISMATCH")
        if not response.get("ok"):
            raise PermissionError(response.get("error", "RPC_REJECTED"))
        return response.get("result")


def main() -> int:
    bootstrap_line = sys.stdin.readline()
    if not bootstrap_line:
        raise RuntimeError("MISSING_BOOTSTRAP")
    bootstrap = json.loads(bootstrap_line)
    client = ParentRpcClient()
    gateway = JsonRpcEvidenceGateway(
        bootstrap["opaque_handle"], client
    )

    probe_results: dict[str, str] = {}
    for method in bootstrap.get("forbidden_rpc_probes", []):
        try:
            client.call(method, {})
        except PermissionError as exc:
            probe_results[method] = str(exc)
        else:
            probe_results[method] = "UNEXPECTEDLY_ALLOWED"

    candidate_output = run_candidate(
        gateway,
        visible_evidence=bootstrap["visible_evidence"],
        candidate_label=bootstrap.get(
            "candidate_claimed_label", "UNSPECIFIED"
        ),
        self_report=bootstrap.get("self_report"),
    )
    print(
        json.dumps(
            {
                "type": "result",
                "candidate_output": candidate_output,
                "forbidden_rpc_probe_results": probe_results,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
