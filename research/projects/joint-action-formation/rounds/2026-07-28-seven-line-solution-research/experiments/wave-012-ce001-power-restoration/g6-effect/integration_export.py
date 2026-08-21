#!/usr/bin/env python3
"""Export G6-local evidence without leaking contract-level conclusions."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _require_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def export_fragment(report: Mapping[str, Any]) -> dict[str, Any]:
    """Project an internal G6 report into a namespaced integration fragment.

    Internal resolution labels remain useful for G6 regression, but they are
    intentionally not copied into the cross-line handoff.  The independent
    contract evaluator must derive all episode-level conclusions itself.
    """

    records = report.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")

    record_refs: list[dict[str, Any]] = []
    for index, raw_record in enumerate(records):
        record = _require_mapping(raw_record, f"records[{index}]")
        evaluation = _require_mapping(
            record.get("evaluation"), f"records[{index}].evaluation"
        )
        method_result = _require_mapping(
            record.get("method_result"), f"records[{index}].method_result"
        )
        trace_closure = _require_mapping(
            record.get("trace_closure"), f"records[{index}].trace_closure"
        )

        if evaluation.get("evidence_closure_valid") is not True:
            raise ValueError(f"records[{index}] has no valid evidence closure")
        if not isinstance(evaluation.get("g6_line_local_closure"), bool):
            raise ValueError(f"records[{index}] has no G6-local closure state")
        receipt_closure = _require_mapping(
            method_result.get("evidence_closure"),
            f"records[{index}].method_result.evidence_closure",
        )

        required_trace_fields = {
            "schema_version",
            "session_id",
            "plan_sha256",
            "result_sha256",
            "trace_head",
            "owner_process_ids",
            "native_ledger_heads",
            "native_ledger_lengths",
        }
        missing = sorted(required_trace_fields - set(trace_closure))
        if missing:
            raise ValueError(
                f"records[{index}] trace closure missing {', '.join(missing)}"
            )

        # The method preserves the full receipt closure while the evaluator
        # builds a later trace closure. They are deliberately different
        # objects, so compare only the common source/state coordinates that
        # must remain identical across that transition.
        shared_binding_fields = (
            "session_id",
            "trace_head",
            "owner_process_ids",
            "native_ledger_heads",
            "native_ledger_lengths",
        )
        binding_mismatches = [
            field
            for field in shared_binding_fields
            if receipt_closure.get(field) != trace_closure.get(field)
        ]
        if method_result.get("plan_sha256") != trace_closure["plan_sha256"]:
            binding_mismatches.append("plan_sha256")
        if binding_mismatches:
            raise ValueError(
                f"records[{index}] closure binding mismatch: "
                + ", ".join(sorted(set(binding_mismatches)))
            )

        record_refs.append(
            {
                "case_ref": method_result.get("case_id"),
                "line_local_gate_closed": evaluation["g6_line_local_closure"],
                "line_local_component_digest": digest(
                    evaluation.get("g6_line_local_components")
                ),
                "trace_closure_digest": digest(trace_closure),
                "trace_schema_version": trace_closure["schema_version"],
                "session_ref": trace_closure["session_id"],
                "plan_sha256": trace_closure["plan_sha256"],
                "result_sha256": trace_closure["result_sha256"],
                "trace_head": trace_closure["trace_head"],
                "owner_process_ids": trace_closure["owner_process_ids"],
                "native_ledger_heads": trace_closure["native_ledger_heads"],
                "native_ledger_lengths": trace_closure["native_ledger_lengths"],
            }
        )

    return {
        "namespace": "G6",
        "qualification": "QUALIFIED_COMPONENT_OUTPUT",
        "evidence": {
            "source_report_digest": digest(report),
            "record_count": len(record_refs),
            "line_local_closed_count": sum(
                item["line_local_gate_closed"] for item in record_refs
            ),
            "record_refs": record_refs,
            "evidence_boundaries": {
                "real_product_execution": "NOT_RUN",
                "production_target_observation": "NOT_RUN",
                "human_owner_act": "NOT_RUN",
                "payment_finality": "NOT_RUN",
                "grader_hostile_blindness": "NOT_ESTABLISHED",
                "cross_line_score_status": "NOT_COMPUTED",
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("artifacts/e2e-results.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/integration-fragment.json"),
    )
    args = parser.parse_args()

    report = json.loads(args.input.read_text(encoding="utf-8"))
    fragment = export_fragment(report)
    args.output.write_text(
        json.dumps(fragment, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
