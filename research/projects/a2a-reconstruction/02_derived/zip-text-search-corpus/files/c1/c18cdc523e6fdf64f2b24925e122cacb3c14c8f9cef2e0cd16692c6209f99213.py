from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class Scenario:
    scenario_id: int
    grant_issued: int
    grant_expires: int
    grant_revoked: int | None
    permitted_purposes: tuple[str, ...]
    use_time: int
    use_purpose: str
    derivation_depth: int
    missing_parent_at: int | None
    rights_initial: tuple[str, ...]
    rights_amended: tuple[str, ...] | None
    rights_amend_time: int | None
    rights_independent_ratification: bool
    learning_time: int | None
    learning_persistent: bool


def active(issued: int, expires: int, revoked: int | None, at: int) -> bool:
    return issued <= at <= expires and (revoked is None or at < revoked)


def expanded_truth(s: Scenario) -> dict[str, Any]:
    use_authorized = active(s.grant_issued, s.grant_expires, s.grant_revoked, s.use_time) and s.use_purpose in s.permitted_purposes
    lineage_complete = s.missing_parent_at is None
    query_time = 100
    rights = s.rights_initial
    if s.rights_amended is not None and s.rights_amend_time is not None and s.rights_amend_time <= query_time:
        rights = s.rights_amended
    if s.learning_time is None or not s.learning_persistent:
        learning_authorized = True
    else:
        learning_authorized = active(s.grant_issued, s.grant_expires, s.grant_revoked, s.learning_time) and "training" in s.permitted_purposes
    return {
        "use_authorized_at_event_time": use_authorized,
        "lineage_complete": lineage_complete,
        "current_joint_rights": list(rights),
        "persistent_learning_authorized": learning_authorized,
        "joint_rights_requires_independent_object": bool(s.rights_amended is not None and s.rights_independent_ratification),
    }


def reduced_representation(s: Scenario) -> dict[str, Any]:
    # The five candidate concepts are represented using a generic Mandate,
    # typed Events, provenance edges, and (only when independently ratified)
    # a Commitment. Semantic distinctions remain; top-level object types shrink.
    mandate = {
        "kind": "Mandate",
        "resource": "source-data",
        "issued": s.grant_issued,
        "expires": s.grant_expires,
        "revoked": s.grant_revoked,
        "purposes": list(s.permitted_purposes),
    }
    events = [
        {"type": "DATA_USED", "time": s.use_time, "purpose": s.use_purpose, "mandate_ref": "m1"},
    ]
    provenance_edges = []
    for i in range(s.derivation_depth):
        if s.missing_parent_at == i:
            continue
        provenance_edges.append({"child": f"d{i+1}", "parent": "source" if i == 0 else f"d{i}"})
    policy = {"initial_rights": list(s.rights_initial), "amendments": []}
    commitments = []
    if s.rights_amended is not None:
        amendment = {"time": s.rights_amend_time, "rights": list(s.rights_amended)}
        if s.rights_independent_ratification:
            commitments.append({"kind": "Commitment", "scope": "joint-artifact-rights", **amendment})
        else:
            policy["amendments"].append(amendment)
    if s.learning_time is not None:
        events.append({"type": "EFFECT", "effect_type": "PERSISTENT_LEARNING" if s.learning_persistent else "EPHEMERAL_CONTEXT", "time": s.learning_time, "mandate_ref": "m1"})
    return {"mandate": mandate, "events": events, "provenance_edges": provenance_edges, "policy": policy, "commitments": commitments}


def query_reduced(rep: dict[str, Any], derivation_depth: int) -> dict[str, Any]:
    mandate = rep["mandate"]
    data_event = next(e for e in rep["events"] if e["type"] == "DATA_USED")
    use_authorized = active(mandate["issued"], mandate["expires"], mandate["revoked"], data_event["time"]) and data_event["purpose"] in mandate["purposes"]
    expected_edges = {(f"d{i+1}", "source" if i == 0 else f"d{i}") for i in range(derivation_depth)}
    observed_edges = {(e["child"], e["parent"]) for e in rep["provenance_edges"]}
    lineage_complete = expected_edges == observed_edges

    rights = rep["policy"]["initial_rights"]
    amendments = list(rep["policy"]["amendments"])
    amendments.extend({"time": c["time"], "rights": c["rights"]} for c in rep["commitments"] if c.get("scope") == "joint-artifact-rights")
    for amendment in sorted(amendments, key=lambda x: x["time"] or -1):
        if amendment["time"] is not None and amendment["time"] <= 100:
            rights = amendment["rights"]

    learning_events = [e for e in rep["events"] if e.get("effect_type") == "PERSISTENT_LEARNING"]
    learning_authorized = all(active(mandate["issued"], mandate["expires"], mandate["revoked"], e["time"]) and "training" in mandate["purposes"] for e in learning_events)
    return {
        "use_authorized_at_event_time": use_authorized,
        "lineage_complete": lineage_complete,
        "current_joint_rights": list(rights),
        "persistent_learning_authorized": learning_authorized,
        "joint_rights_requires_independent_object": bool(rep["commitments"]),
    }


def query_naive_flattened(s: Scenario) -> dict[str, Any]:
    # Deliberately common anti-pattern: retain only current grant status/current
    # rights and boolean flags, discarding event-time validity and lineage.
    current_active = active(s.grant_issued, s.grant_expires, s.grant_revoked, 100)
    rights = s.rights_amended if s.rights_amended is not None else s.rights_initial
    return {
        "use_authorized_at_event_time": current_active and s.use_purpose in s.permitted_purposes,
        "lineage_complete": s.derivation_depth > 0,  # has no edge-level proof
        "current_joint_rights": list(rights),
        "persistent_learning_authorized": (not s.learning_persistent) or (current_active and "training" in s.permitted_purposes),
        "joint_rights_requires_independent_object": False,
    }


def generate(rng: random.Random, idx: int) -> Scenario:
    issued = rng.randint(0, 10)
    expires = rng.randint(50, 110)
    revoked = rng.choice([None, None, rng.randint(15, 95)])
    purposes_pool = ["coordination", "evaluation", "training", "delivery"]
    permitted = tuple(sorted(rng.sample(purposes_pool, rng.randint(1, 4))))
    use_time = rng.randint(5, 100)
    use_purpose = rng.choice(purposes_pool)
    depth = rng.randint(1, 5)
    missing = rng.choice([None, None, None, rng.randrange(depth)])
    rights_options = [("buyer",), ("provider",), ("buyer", "provider")]
    initial = rng.choice(rights_options)
    has_amend = rng.random() < 0.45
    amended = rng.choice(rights_options) if has_amend else None
    amend_time = rng.randint(20, 90) if has_amend else None
    independent = bool(has_amend and rng.random() < 0.55)
    has_learning = rng.random() < 0.55
    learning_time = rng.randint(10, 100) if has_learning else None
    persistent = bool(has_learning and rng.random() < 0.7)
    return Scenario(idx, issued, expires, revoked, permitted, use_time, use_purpose, depth, missing, initial, amended, amend_time, independent, learning_time, persistent)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=int, default=50000)
    parser.add_argument("--seed", type=int, default=20260726)
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    reduced_errors = Counter()
    naive_errors = Counter()
    promoted = 0
    examples: list[dict[str, Any]] = []

    for idx in range(args.scenarios):
        s = generate(rng, idx)
        truth = expanded_truth(s)
        reduced = query_reduced(reduced_representation(s), s.derivation_depth)
        naive = query_naive_flattened(s)
        if truth["joint_rights_requires_independent_object"]:
            promoted += 1
        for key in truth:
            if reduced[key] != truth[key]:
                reduced_errors[key] += 1
            if naive[key] != truth[key]:
                naive_errors[key] += 1
        if len(examples) < 12 and any(naive[k] != truth[k] for k in truth):
            examples.append({"scenario": asdict(s), "truth": truth, "naive": naive})

    result = {
        "experiment": "ontology_reduction_trace_preservation",
        "seed": args.seed,
        "scenario_count": args.scenarios,
        "candidate_concepts": ["UsageGrant", "DataUseEvent", "DerivationRecord", "JointArtifactRights", "LearningUpdate"],
        "reduced_mapping": {
            "UsageGrant": "Mandate specialization when independently issued/revoked; otherwise policy field",
            "DataUseEvent": "Event subtype",
            "DerivationRecord": "provenance edge/payload on the produced assertion or artifact",
            "JointArtifactRights": "policy attachment; promoted to Commitment only when independently ratified/amendable",
            "LearningUpdate": "Effect event subtype; independently governed object only for persistent high-risk state",
        },
        "query_count_per_scenario": 5,
        "reduced_error_counts": dict(reduced_errors),
        "reduced_total_query_errors": sum(reduced_errors.values()),
        "naive_error_counts": dict(naive_errors),
        "naive_total_query_errors": sum(naive_errors.values()),
        "naive_query_error_rate": sum(naive_errors.values()) / (args.scenarios * 5),
        "joint_rights_promoted_count": promoted,
        "joint_rights_promoted_rate": promoted / args.scenarios,
        "top_level_candidate_types_before": 5,
        "top_level_candidate_types_after_default": 1,
        "conditional_promotions": ["Mandate", "Commitment"],
        "interpretation_limit": "Constructive representation test over an explicit generator. It shows that protocol object proliferation is unnecessary for these queries; it does not prove the five distinctions are unimportant or that real legal regimes accept the mapping.",
        "counterexamples": examples,
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "counterexamples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
