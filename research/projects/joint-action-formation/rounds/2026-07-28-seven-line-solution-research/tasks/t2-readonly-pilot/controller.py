#!/usr/bin/env python3
"""Deterministic disclosure controller for the T2 blind task.

The controller is not solver-visible. It accepts only method-visible query
batches, returns allowlisted minimal disclosures or refusals, and records a
hash-chained controller state. It does not solve or score the task.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parent
BLIND_PATH = ROOT / "blind" / "input.json"
ORACLE_PATH = ROOT / "oracle" / "truth.json"
TASK_ID = "T2-ENTERPRISE-PILOT-BLIND-V1"
BEHAVIOR_VERSION = "T2-DISCLOSURE-CONTROLLER-V1"

QUERY_FIELDS = {
    "authority_id",
    "request_type",
    "purpose",
    "relation_version_ref",
    "retention_scope",
}
BATCH_FIELDS = {
    "schema_version",
    "task_id",
    "method_id",
    "run_id",
    "round",
    "previous_round_hash",
    "queries",
}
MAX_QUERIES_PER_ROUND = 32
MAX_FIELD_LENGTH = 2048
ALLOWED_RETENTION_SCOPES = {"EPHEMERAL", "RUN_ONLY"}


class ControllerError(ValueError):
    """Safe controller error whose text contains no hidden task state."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControllerError("controller configuration is unavailable") from exc
    if not isinstance(value, dict):
        raise ControllerError("controller configuration is invalid")
    return value


def initial_state() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "controller_behavior_version": BEHAVIOR_VERSION,
        "runs": {},
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return initial_state()
    state = load_json(path)
    if (
        state.get("task_id") != TASK_ID
        or state.get("controller_behavior_version") != BEHAVIOR_VERSION
        or not isinstance(state.get("runs"), dict)
    ):
        raise ControllerError("controller state is incompatible")
    return state


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, path)


def validate_batch(batch: dict[str, Any]) -> None:
    if set(batch) != BATCH_FIELDS:
        raise ControllerError("query batch fields do not match the public schema")
    if batch.get("schema_version") != "1.0" or batch.get("task_id") != TASK_ID:
        raise ControllerError("query batch identity mismatch")
    for key in ("method_id", "run_id"):
        value = batch.get(key)
        if not isinstance(value, str) or not value or len(value) > 256:
            raise ControllerError(f"{key} must be a non-empty bounded string")
    round_number = batch.get("round")
    if not isinstance(round_number, int) or isinstance(round_number, bool):
        raise ControllerError("round must be an integer")
    if round_number < 1:
        raise ControllerError("round must be positive")
    previous = batch.get("previous_round_hash")
    if previous is not None and (
        not isinstance(previous, str)
        or len(previous) != 64
        or any(char not in "0123456789abcdef" for char in previous)
    ):
        raise ControllerError("previous_round_hash must be null or lowercase sha256")
    queries = batch.get("queries")
    if not isinstance(queries, list):
        raise ControllerError("queries must be an array")
    if len(queries) > MAX_QUERIES_PER_ROUND:
        raise ControllerError("too many queries in one round")


def build_indexes(
    blind: dict[str, Any],
    oracle: dict[str, Any],
) -> tuple[
    set[str],
    set[tuple[str, str]],
    set[str],
    dict[tuple[str, str], dict[str, Any]],
]:
    authorities: set[str] = set()
    allowed_pairs: set[tuple[str, str]] = set()
    request_types: set[str] = set()
    for interface in blind.get("authority_interfaces", []):
        authority_id = interface.get("authority_id")
        if not isinstance(authority_id, str):
            raise ControllerError("controller configuration is invalid")
        authorities.add(authority_id)
        for request_type in interface.get("allowed_request_types", []):
            if not isinstance(request_type, str):
                raise ControllerError("controller configuration is invalid")
            allowed_pairs.add((authority_id, request_type))
            request_types.add(request_type)

    disclosures: dict[tuple[str, str], dict[str, Any]] = {}
    for transition in oracle.get("disclosure_transitions", []):
        key = (transition.get("authority_id"), transition.get("request_type"))
        if (
            not all(isinstance(part, str) for part in key)
            or key in disclosures
            or not isinstance(transition.get("response_type"), str)
            or not isinstance(transition.get("disclosed_fields"), dict)
        ):
            raise ControllerError("controller configuration is invalid")
        disclosures[key] = {
            "response_type": transition["response_type"],
            "disclosed_fields": transition["disclosed_fields"],
        }

    if set(disclosures) != allowed_pairs:
        raise ControllerError("controller disclosure closure is invalid")
    return authorities, allowed_pairs, request_types, disclosures


def query_problem(query: Any) -> str | None:
    if not isinstance(query, dict):
        return "MALFORMED_QUERY"
    if set(query) != QUERY_FIELDS:
        return "MALFORMED_QUERY"
    for key in QUERY_FIELDS:
        value = query.get(key)
        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value) > MAX_FIELD_LENGTH
        ):
            return "MALFORMED_QUERY"
    if query["retention_scope"] not in ALLOWED_RETENTION_SCOPES:
        return "RETENTION_SCOPE_NOT_ALLOWED"
    return None


def public_query_projection(query: Any) -> dict[str, str]:
    if not isinstance(query, dict):
        return {key: "" for key in sorted(QUERY_FIELDS)}
    return {
        key: query.get(key, "") if isinstance(query.get(key), str) else ""
        for key in sorted(QUERY_FIELDS)
    }


def response_for_query(
    query: dict[str, str],
    authorities: set[str],
    allowed_pairs: set[tuple[str, str]],
    request_types: set[str],
    disclosures: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, str, dict[str, Any], str | None]:
    authority_id = query["authority_id"]
    request_type = query["request_type"]
    if authority_id not in authorities:
        return "REFUSE", "REFUSE", {}, "UNKNOWN_AUTHORITY"
    if request_type not in request_types:
        return "REFUSE", "REFUSE", {}, "UNKNOWN_REQUEST_TYPE"
    if (authority_id, request_type) not in allowed_pairs:
        return "REFUSE", "REFUSE", {}, "REQUEST_NOT_ALLOWED_FOR_AUTHORITY"
    disclosure = disclosures[(authority_id, request_type)]
    return (
        "DISCLOSE",
        disclosure["response_type"],
        json.loads(json.dumps(disclosure["disclosed_fields"], ensure_ascii=False)),
        None,
    )


def make_receipt(
    *,
    batch: dict[str, Any],
    query_index: int,
    query: dict[str, str],
    request_fingerprint: str,
    decision: str,
    response_type: str,
    disclosed_fields: dict[str, Any],
    response_hash: str,
    reason_code: str | None,
    replay_of_receipt_id: str | None,
) -> dict[str, Any]:
    request_id = f"REQ-{request_fingerprint[:20]}"
    receipt_base = {
        "request_id": request_id,
        "authority_id": query["authority_id"],
        "request_type": query["request_type"],
        "purpose": query["purpose"],
        "relation_version_ref": query["relation_version_ref"],
        "response_type": response_type,
        "disclosed_fields": sorted(disclosed_fields),
        "retention_scope": query["retention_scope"],
        "decision": decision,
        "reason_code": reason_code,
        "replay_of_receipt_id": replay_of_receipt_id,
        "round": batch["round"],
        "query_index": query_index,
        "response_hash": response_hash,
    }
    receipt_id_seed = {
        "task_id": TASK_ID,
        "method_id": batch["method_id"],
        "run_id": batch["run_id"],
        **receipt_base,
    }
    receipt = {
        "receipt_id": f"RCPT-{digest(receipt_id_seed)[:24]}",
        **receipt_base,
    }
    receipt["receipt_hash"] = digest(receipt)
    return receipt


def run_key(method_id: str, run_id: str) -> str:
    return digest({"method_id": method_id, "run_id": run_id})


def process_batch(
    batch: dict[str, Any],
    state: dict[str, Any],
    blind: dict[str, Any] | None = None,
    oracle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Process one batch and mutate controller-only state in memory."""

    validate_batch(batch)
    blind = blind if blind is not None else load_json(BLIND_PATH)
    oracle = oracle if oracle is not None else load_json(ORACLE_PATH)
    authorities, allowed_pairs, request_types, disclosures = build_indexes(
        blind, oracle
    )

    key = run_key(batch["method_id"], batch["run_id"])
    run = state["runs"].setdefault(
        key,
        {
            "method_id": batch["method_id"],
            "run_id": batch["run_id"],
            "rounds": [],
            "seen_queries": {},
        },
    )
    if (
        run.get("method_id") != batch["method_id"]
        or run.get("run_id") != batch["run_id"]
        or not isinstance(run.get("rounds"), list)
        or not isinstance(run.get("seen_queries"), dict)
    ):
        raise ControllerError("controller run state is incompatible")

    input_hash = digest(batch)
    round_number = batch["round"]
    existing_rounds = run["rounds"]
    if round_number <= len(existing_rounds):
        existing = existing_rounds[round_number - 1]
        if existing.get("input_hash") != input_hash:
            raise ControllerError("conflicting replay for an already recorded round")
        return existing["output"]
    if round_number != len(existing_rounds) + 1:
        raise ControllerError("round sequence is not contiguous")

    expected_previous = (
        None if not existing_rounds else existing_rounds[-1]["output"]["round_hash"]
    )
    if batch["previous_round_hash"] != expected_previous:
        raise ControllerError("previous_round_hash does not match controller history")

    results: list[dict[str, Any]] = []
    for index, raw_query in enumerate(batch["queries"]):
        query = public_query_projection(raw_query)
        problem = query_problem(raw_query)
        request_fingerprint = digest(
            {
                "task_id": TASK_ID,
                "query": query,
            }
        )
        prior = run["seen_queries"].get(request_fingerprint)
        if prior is not None:
            response_hash = prior["response_hash"]
            receipt = make_receipt(
                batch=batch,
                query_index=index,
                query=query,
                request_fingerprint=request_fingerprint,
                decision="REPLAY",
                response_type="REPLAY",
                disclosed_fields={},
                response_hash=response_hash,
                reason_code=None,
                replay_of_receipt_id=prior["receipt_id"],
            )
            results.append(
                {
                    "query_index": index,
                    "request_id": receipt["request_id"],
                    "decision": "REPLAY",
                    "response_type": "REPLAY",
                    "disclosed_fields": {},
                    "reason_code": None,
                    "response_hash": response_hash,
                    "replay_of_receipt_id": prior["receipt_id"],
                    "receipt": receipt,
                }
            )
            continue

        if problem is not None:
            decision, response_type, disclosed_fields, reason_code = (
                "REFUSE",
                "REFUSE",
                {},
                problem,
            )
        else:
            decision, response_type, disclosed_fields, reason_code = (
                response_for_query(
                    query,
                    authorities,
                    allowed_pairs,
                    request_types,
                    disclosures,
                )
            )
        response_hash = digest(
            {
                "request_fingerprint": request_fingerprint,
                "decision": decision,
                "response_type": response_type,
                "disclosed_fields": disclosed_fields,
                "reason_code": reason_code,
            }
        )
        receipt = make_receipt(
            batch=batch,
            query_index=index,
            query=query,
            request_fingerprint=request_fingerprint,
            decision=decision,
            response_type=response_type,
            disclosed_fields=disclosed_fields,
            response_hash=response_hash,
            reason_code=reason_code,
            replay_of_receipt_id=None,
        )
        result = {
            "query_index": index,
            "request_id": receipt["request_id"],
            "decision": decision,
            "response_type": response_type,
            "disclosed_fields": disclosed_fields,
            "reason_code": reason_code,
            "response_hash": response_hash,
            "replay_of_receipt_id": None,
            "receipt": receipt,
        }
        results.append(result)
        run["seen_queries"][request_fingerprint] = {
            "receipt_id": receipt["receipt_id"],
            "response_hash": response_hash,
            "decision": decision,
        }

    response_base = {
        "schema_version": "1.0",
        "task_id": TASK_ID,
        "controller_behavior_version": BEHAVIOR_VERSION,
        "method_id": batch["method_id"],
        "run_id": batch["run_id"],
        "round": round_number,
        "input_hash": input_hash,
        "previous_round_hash": expected_previous,
        "results": results,
    }
    round_hash = digest(response_base)
    prior_history_hash = (
        None if not existing_rounds else existing_rounds[-1]["output"]["history_hash"]
    )
    history_hash = digest(
        {
            "previous_history_hash": prior_history_hash,
            "round_hash": round_hash,
        }
    )
    output = {
        **response_base,
        "round_hash": round_hash,
        "history_hash": history_hash,
    }
    existing_rounds.append(
        {
            "round": round_number,
            "input_hash": input_hash,
            "output": output,
        }
    )
    return output


def read_batch(path_text: str) -> dict[str, Any]:
    try:
        if path_text == "-":
            value = json.load(sys.stdin)
        else:
            value = json.loads(Path(path_text).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ControllerError("query batch is unreadable or invalid JSON") from exc
    if not isinstance(value, dict):
        raise ControllerError("query batch top level must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one deterministic T2 disclosure round."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="method-visible query batch JSON path, or - for stdin",
    )
    parser.add_argument(
        "--state",
        required=True,
        help="controller-only state JSON path",
    )
    parser.add_argument(
        "--output",
        help="optional response JSON path; stdout is used when omitted",
    )
    args = parser.parse_args()

    try:
        batch = read_batch(args.input)
        state_path = Path(args.state)
        state = load_state(state_path)
        output = process_batch(batch, state)
        write_json_atomic(state_path, state)
        if args.output:
            write_json_atomic(Path(args.output), output)
        else:
            print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except ControllerError as exc:
        print(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "task_id": TASK_ID,
                    "error": "CONTROLLER_REJECTED_BATCH",
                    "message": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
