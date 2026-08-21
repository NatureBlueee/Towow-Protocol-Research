#!/usr/bin/env python3
"""Subprocess worker. It has an RPC proxy and never receives the parent ledger."""

from __future__ import annotations

import json
import sys
from typing import Any


STRATEGIES: dict[str, Any] = {}
declaration: Any = None


def install_runtime_read_guard() -> None:
    """Deny candidate-time file/import/process/network expansion."""
    denied_prefixes = (
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "subprocess.",
        "socket.",
        "ctypes.",
    )

    def guard(event: str, arguments: tuple[Any, ...]) -> None:
        if (
            event == "import"
            and arguments
            and arguments[0] == "typing"
        ):
            return
        if (
            event == "open"
            or event == "import"
            or event == "os.system"
            or event.startswith(denied_prefixes)
        ):
            raise PermissionError(
                f"candidate runtime operation denied: {event}"
            )

    sys.addaudithook(guard)


def load_guarded_candidate_module() -> None:
    """Read candidate source as data, install guard, then execute it."""
    global STRATEGIES, declaration
    strategy_path = (
        __file__.rsplit("/", 1)[0] + "/candidate_strategies.py"
    )
    with open(strategy_path, "r", encoding="utf-8") as handle:
        source = handle.read()
    compiled = compile(source, strategy_path, "exec")
    install_runtime_read_guard()
    namespace: dict[str, Any] = {
        "__name__": "guarded_candidate_strategies",
        "__file__": strategy_path,
    }
    exec(compiled, namespace)
    STRATEGIES = namespace["STRATEGIES"]
    declaration = namespace["declaration"]


class RemoteEvidenceAPI:
    def __init__(self) -> None:
        self.__sequence = 0

    def _rpc(self, method: str, **arguments: Any) -> Any:
        self.__sequence += 1
        request = {
            "type": "rpc",
            "id": self.__sequence,
            "method": method,
            "arguments": arguments,
        }
        print(json.dumps(request, sort_keys=True), flush=True)
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("parent broker closed the RPC stream")
        response = json.loads(line)
        if response.get("id") != self.__sequence:
            raise RuntimeError("RPC response sequence mismatch")
        if not response.get("ok"):
            raise PermissionError(response.get("error", "broker denied RPC"))
        return response.get("result")

    def get_request_context(self) -> dict[str, Any]:
        return self._rpc("get_request_context")

    def read(
        self,
        evidence_type: str,
        *,
        retry: bool = False,
    ) -> dict[str, Any]:
        return self._rpc(
            "read", evidence_type=evidence_type, retry=retry
        )

    def verify_signature(self, record: dict[str, Any]) -> bool:
        return bool(self._rpc("verify_signature", record=record))

    def validate_binding(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        return bool(self._rpc(
            "validate_binding", record=record, context=context
        ))

    def validate_observation_binding(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        return bool(self._rpc(
            "validate_observation_binding",
            record=record,
            context=context,
        ))

    def validate_freshness(
        self,
        record: dict[str, Any],
        context: dict[str, Any],
        *,
        max_age: int,
    ) -> bool:
        return bool(self._rpc(
            "validate_freshness",
            record=record,
            context=context,
            max_age=max_age,
        ))

    def validate_authority(
        self,
        record: dict[str, Any],
        authority_record: dict[str, Any],
        context: dict[str, Any],
    ) -> bool:
        return bool(self._rpc(
            "validate_authority",
            record=record,
            authority_record=authority_record,
            context=context,
        ))


def malicious_clear_log(api: RemoteEvidenceAPI) -> dict[str, Any]:
    decision = declaration(api)
    local_clear_blocked = False
    broker_clear_blocked = False
    try:
        api._log.clear()  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        local_clear_blocked = True
    try:
        api._rpc("clear_operation_log")
    except PermissionError:
        broker_clear_blocked = True
    decision["mutation_attempt"] = {
        "local_clear_blocked": local_clear_blocked,
        "broker_clear_blocked": broker_clear_blocked,
    }
    return decision


def spoof_implementation_id(api: RemoteEvidenceAPI) -> dict[str, Any]:
    decision = declaration(api)
    decision["implementation_id"] = "IMPL_SLA_RECOVERY"
    decision["spoofed_identity"] = True
    return decision


def repeated_access(api: RemoteEvidenceAPI) -> dict[str, Any]:
    context = api.get_request_context()
    first = api.read("declaration")
    second = api.read("declaration")
    api.verify_signature(first["record"])
    api.verify_signature(second["record"])
    api.validate_freshness(first["record"], context, max_age=10)
    api.validate_freshness(second["record"], context, max_age=10)
    return {
        "implementation_id": "IMPL_REPEATED_ACCESS_TEST",
        "rely": False,
        "decision_state": "TEST_ONLY",
        "reason": "repeat identical operations for billing audit",
    }


def private_state_read_attempt(
    api: RemoteEvidenceAPI,
) -> dict[str, Any]:
    decision = declaration(api)
    blocked = False
    try:
        with open("private/truth.json", "r", encoding="utf-8") as handle:
            handle.read()
    except PermissionError:
        blocked = True
    decision["private_state_read_blocked"] = blocked
    return decision


def forge_authority_context(
    api: RemoteEvidenceAPI,
) -> dict[str, Any]:
    context = api.get_request_context()
    declaration_response = api.read("declaration")
    record = declaration_response["record"]
    signature_ok = api.verify_signature(record)
    binding_ok = api.validate_binding(record, context)
    freshness_ok = api.validate_freshness(
        record, context, max_age=10
    )
    authority_response = api.read("authority_status")
    authority = authority_response["record"]
    authority_signature_ok = api.verify_signature(authority)
    forged_context = dict(context)
    for field in (
        "authority_head",
        "authority_epoch",
        "authority_contract_version",
    ):
        forged_context[field] = authority["payload"][field]
    authority_freshness_ok = api.validate_freshness(
        authority, forged_context, max_age=1
    )
    authority_ok = api.validate_authority(
        record, authority, forged_context
    )
    rely = all((
        signature_ok,
        binding_ok,
        freshness_ok,
        authority_signature_ok,
        authority_freshness_ok,
        authority_ok,
    ))
    return {
        "implementation_id": "IMPL_DECLARATION",
        "rely": rely,
        "decision_state": "RELY" if rely else "UNKNOWN",
        "reason": "candidate_forged_context_attempt",
    }


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: candidate_worker.py STRATEGY")
    strategy_name = sys.argv[1]
    load_guarded_candidate_module()
    functions = {
        **STRATEGIES,
        "MALICIOUS_CLEAR_LOG": malicious_clear_log,
        "SPOOF_IMPLEMENTATION_ID": spoof_implementation_id,
        "REPEATED_ACCESS": repeated_access,
        "PRIVATE_STATE_READ_ATTEMPT": private_state_read_attempt,
        "FORGE_AUTHORITY_CONTEXT": forge_authority_context,
    }
    if strategy_name not in functions:
        raise SystemExit(f"unknown strategy: {strategy_name}")
    api = RemoteEvidenceAPI()
    decision = functions[strategy_name](api)
    print(json.dumps({
        "type": "decision",
        "decision": decision,
    }, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
