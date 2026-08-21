#!/usr/bin/env python3
"""Pure scoring functions for separate G4 outcome predictions."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def confusion(rows: list[dict[str, Any]], stage: str, outcome: str) -> dict[str, Any]:
    counts = {
        "TP": 0,
        "FP": 0,
        "TN": 0,
        "FN": 0,
        "ABSTAIN_TRUE": 0,
        "ABSTAIN_FALSE": 0,
    }
    for row in rows:
        prediction = row["predictions"][stage][outcome]
        truth = bool(row["truth"][stage][outcome])
        if prediction == "ABSTAIN":
            counts["ABSTAIN_TRUE" if truth else "ABSTAIN_FALSE"] += 1
        elif prediction == "YES" and truth:
            counts["TP"] += 1
        elif prediction == "YES" and not truth:
            counts["FP"] += 1
        elif prediction == "NO" and truth:
            counts["FN"] += 1
        elif prediction == "NO" and not truth:
            counts["TN"] += 1
        else:
            raise ValueError(f"invalid prediction: {prediction}")
    safe_total = counts["TP"] + counts["FN"] + counts["ABSTAIN_TRUE"]
    rely_total = counts["TP"] + counts["FP"]
    return {
        **counts,
        "false_reliance_conditional": (
            counts["FP"] / rely_total if rely_total else None
        ),
        "false_reliance_all": counts["FP"] / len(rows) if rows else None,
        "safe_recall": counts["TP"] / safe_total if safe_total else None,
        "abstention_rate": (
            (counts["ABSTAIN_TRUE"] + counts["ABSTAIN_FALSE"]) / len(rows)
            if rows
            else None
        ),
    }


def cost_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    keys = (
        "queries",
        "disclosed_bytes",
        "latency_ticks",
        "sensitivity",
        "human_interruptions",
    )
    return {
        key: {
            "total": sum(row["cost"][key] for row in rows),
            "mean": (
                sum(row["cost"][key] for row in rows) / len(rows) if rows else 0
            ),
        }
        for key in keys
    }


def score_method(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_class[row["pair_class"]].append(row)
    return {
        "world_count": len(rows),
        "P0": {
            "success_confusion": confusion(rows, "P0", "Y_success"),
            "resolution_confusion": confusion(rows, "P0", "Y_resolution"),
        },
        "P1": {
            "success_confusion": confusion(rows, "P1", "Y_success"),
            "resolution_confusion": confusion(rows, "P1", "Y_resolution"),
        },
        "by_pair_class": {
            pair_class: {
                "world_count": len(group),
                "success_confusion": confusion(group, "P1", "Y_success"),
                "resolution_confusion": confusion(group, "P1", "Y_resolution"),
            }
            for pair_class, group in sorted(by_class.items())
        },
        "actual_outcomes": {
            outcome: {
                "true": sum(bool(row["outcomes"][outcome]) for row in rows),
                "false": sum(not bool(row["outcomes"][outcome]) for row in rows),
            }
            for outcome in (
                "Y_success",
                "Y_resolution",
                "Y_effect",
                "Y_acceptance",
            )
        },
        "recovery_readback": {
            "ambiguous_submit_responses": sum(
                any(
                    entry.get("action") == "submit_operation"
                    and entry.get("raw_response") is None
                    for entry in row["trace"]
                )
                for row in rows
            ),
            "correct_object_readbacks": sum(
                bool(row["outcomes"]["correct_object_readback_observed"])
                for row in rows
            ),
            "duplicate_effect_worlds": sum(
                bool(row["outcomes"]["duplicate_effect"]) for row in rows
            ),
        },
        "cost": cost_summary(rows),
    }
