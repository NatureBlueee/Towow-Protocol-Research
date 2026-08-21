#!/usr/bin/env python3
"""Private-oracle evaluator for the finite Wave 011 G6 paired worlds.

Workers never import this module.  The checks below are post-run comparisons
against ``private_oracle/expected.json``.  The resulting rate is a synthetic
fixture-conformance rate, not PROGRAM coverage or real-world evidence.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "private_oracle" / "expected.json"


def _load_oracle() -> dict[str, Any]:
    value = json.loads(ORACLE.read_text(encoding="utf-8"))
    if value.get("kind") != "PRIVATE_G6_GRADER_ORACLE":
        raise ValueError("unexpected private oracle kind")
    return value


def _observed(output: Mapping[str, Any]) -> dict[str, Any]:
    raw_occurrences = list(output.get("raw_occurrences", ()))
    target_occurrences = [
        row for row in raw_occurrences if row.get("native_kind") == "TARGET_TRANSITION"
    ]
    attempts = [
        row for row in raw_occurrences if row.get("native_kind") == "ACTION_ATTEMPT"
    ]
    acceptance_acts = [
        row for row in raw_occurrences if row.get("native_kind") == "INSTITUTIONAL_ACT"
    ]
    authority = output.get("authority", {})
    counts = output.get("counts_toward_q", {})
    recovery = output.get("recovery_relevance", {})
    authorized_attempts = set(authority.get("authorized_attempt_ids", ()))
    qualified_acceptances = set(authority.get("qualified_acceptance_ids", ()))
    return {
        "raw_effect": bool(target_occurrences),
        "authority_valid": bool(attempts)
        and all(row.get("occurrence_id") in authorized_attempts for row in attempts),
        "counts_toward_q": bool(counts.get("effect_ids", ())),
        "recovery_required": bool(recovery.get("required")),
        "causal_attribution": output.get("causal_attribution"),
        "control_action": output.get("control_action"),
        "read_fresh": output.get("read_fresh"),
        "adoption": bool(counts.get("adoption_ids", ())),
        "raw_acceptance_act": bool(acceptance_acts),
        "acceptance_exact_object": bool(acceptance_acts)
        and len(qualified_acceptances) == len(acceptance_acts),
        "qualified_acceptance_count": len(qualified_acceptances),
        "acceptance_conflict": counts.get("acceptance_status") == "REJECTED",
        "acceptance_status": counts.get("acceptance_status"),
        "settlement_status": counts.get("settlement_status"),
        "consistent_cut": output.get("consistent_cut"),
        "duplicate_effect_forbidden": (
            len({row.get("occurrence_id") for row in target_occurrences})
            == len(target_occurrences)
            and len(counts.get("effect_ids", ())) <= 1
        ),
    }


def _p12_checks(
    world_id: str, stratum: str, observed: Mapping[str, Any]
) -> dict[str, bool]:
    """Check the authority-stratified P12 result.

    P12-A uses the independent owners' own acts.  P12-B uses a center.  The
    center is lawful in S1 and under the exact S3 delegation, but not in S2.
    """

    if world_id == "P12-A":
        return {
            "lawful_independent_owner_effect": bool(observed["counts_toward_q"]),
            "lawful_independent_owner_acceptance": observed["acceptance_status"]
            == "ACCEPTED",
            "no_recovery_for_lawful_owner_path": not bool(
                observed["recovery_required"]
            ),
        }
    center_lawful = stratum in {"S1", "S3"}
    return {
        "center_scope_effect": bool(observed["counts_toward_q"]) == center_lawful,
        "center_scope_acceptance": (
            observed["acceptance_status"] == "ACCEPTED"
        )
        == center_lawful,
        "unauthorized_center_recovery": bool(observed["recovery_required"])
        == (not center_lawful),
    }


def evaluate_matrix(run: Mapping[str, Any]) -> dict[str, Any]:
    if run.get("kind") != "G6_12_PAIR_3X3_RUN":
        raise ValueError("unexpected run kind")
    oracle = _load_oracle()
    rows: list[dict[str, Any]] = []
    method_totals: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    pair_records: dict[str, list[bool]] = defaultdict(list)

    for record in run.get("records", ()):
        implementation = str(record["implementation"])
        stratum = str(record["stratum"])
        record_checks: dict[str, bool] = {}
        world_rows = []
        for world_id, token in zip(record["world"], record["public_world_token"]):
            output = record["method_output"][token]
            observed = _observed(output)
            expected = oracle["worlds"][world_id]
            checks: dict[str, bool] = {}
            if world_id.startswith("P12-"):
                checks = _p12_checks(world_id, stratum, observed)
            else:
                for field, expected_value in expected.items():
                    if field in {
                        "authority_form",
                        "lawful",
                        "strata",
                    }:
                        continue
                    checks[field] = observed.get(field) == expected_value
            for name, passed in checks.items():
                record_checks[f"{world_id}:{name}"] = passed
            world_rows.append(
                {
                    "world": world_id,
                    "public_world_token": token,
                    "observed": observed,
                    "checks": checks,
                    "passed": all(checks.values()),
                }
            )

        passed_checks = sum(record_checks.values())
        total_checks = len(record_checks)
        method_totals[(implementation, stratum)][0] += passed_checks
        method_totals[(implementation, stratum)][1] += total_checks
        record_passed = total_checks > 0 and passed_checks == total_checks
        pair_records[str(record["pair"])].append(record_passed)
        rows.append(
            {
                "pair": record["pair"],
                "stratum": stratum,
                "implementation": implementation,
                "passed_checks": passed_checks,
                "total_checks": total_checks,
                "all_checks_passed": record_passed,
                "worlds": world_rows,
                "cost": record["cost"],
                "latency_ms": record["latency_ms"],
                "hitl_calls": record["hitl_calls"],
            }
        )

    method_summary: dict[str, Any] = {}
    for (implementation, stratum), (passed, total) in sorted(method_totals.items()):
        method_summary.setdefault(implementation, {})[stratum] = {
            "passed_checks": passed,
            "total_checks": total,
            "synthetic_check_rate": passed / total if total else 0.0,
        }

    return {
        "schema_version": "1.0",
        "kind": "G6_PRIVATE_ORACLE_EVALUATION",
        "evidence_state": "LOCAL_SYNTHETIC_FINITE_FIXTURE_CONFORMANCE",
        "record_count": len(rows),
        "all_records_passed": bool(rows)
        and all(row["all_checks_passed"] for row in rows),
        "passed_record_count": sum(row["all_checks_passed"] for row in rows),
        "pair_discrimination": {
            pair: {
                "passed_records": sum(values),
                "total_records": len(values),
                "all_implementations_and_strata_passed": all(values),
            }
            for pair, values in sorted(pair_records.items())
        },
        "method_summary": method_summary,
        "rows": rows,
        "cannot_support": [
            "PROGRAM requirement coverage",
            "X2 population, X2 result, or X1-to-X2 closure",
            "real-world frequency or external validity",
            "real Effect, human Acceptance, payment, or production recovery",
            "general superiority of a center, composition, or human institution",
            "necessity of a novel Effect protocol",
            "formal claim, line, mechanism, NOW, or PROGRAM status change",
        ],
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_matrix(json.loads(args.run.read_text(encoding="utf-8")))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
