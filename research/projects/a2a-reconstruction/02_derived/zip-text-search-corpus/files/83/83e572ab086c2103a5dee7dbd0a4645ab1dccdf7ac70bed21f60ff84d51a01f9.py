from __future__ import annotations

import argparse
import copy
import json
import random
from collections import Counter, deque
from pathlib import Path
from typing import Any

# Import from the fieldkit source tree without requiring installation.
import sys
HERE = Path(__file__).resolve()
FIELDKIT = HERE.parents[2] / "instrument" / "towow_fieldkit"
sys.path.insert(0, str(FIELDKIT))
from towow_fieldkit.schema_change import classify_change  # noqa: E402


def base_schema() -> dict[str, Any]:
    return {
        "schema_id": "bounded-ai-pilot",
        "version": "1",
        "roles": {"buyer_budget": {}, "buyer_ops": {}, "provider_business": {}, "provider_tech": {}, "legal": {}},
        "object_types": {"source_data": {}, "pilot_output": {}},
        "actions": {
            "propose": {"actor_roles": ["provider_business"], "material": True},
            "countercondition": {"actor_roles": ["buyer_ops", "provider_tech"], "material": True},
            "commit_budget": {"actor_roles": ["buyer_budget"], "material": True},
            "authorize_data": {"actor_roles": ["legal"], "material": True},
            "run_probe": {"actor_roles": ["provider_tech"], "material": True, "produces_effect": True},
            "accept": {"actor_roles": ["buyer_ops"], "material": True},
            "recover": {"actor_roles": ["provider_tech"], "material": True, "produces_effect": True},
            "archive_note": {"actor_roles": ["provider_business"], "material": False},
        },
        "transitions": [
            {"from": "FORMING", "action": "propose", "to": "PROPOSED"},
            {"from": "PROPOSED", "action": "countercondition", "to": "PROPOSED"},
            {"from": "PROPOSED", "action": "commit_budget", "to": "BUDGETED"},
            {"from": "BUDGETED", "action": "authorize_data", "to": "AUTHORIZED"},
            {"from": "AUTHORIZED", "action": "run_probe", "to": "EFFECT_PENDING"},
            {"from": "EFFECT_PENDING", "action": "accept", "to": "ACCEPTED"},
            {"from": "FAILED", "action": "recover", "to": "AUTHORIZED"},
            {"from": "ARCHIVED", "action": "archive_note", "to": "ARCHIVED"},
        ],
        "authority_rules": {
            "propose": ["provider_business"],
            "countercondition": ["buyer_ops", "provider_tech"],
            "commit_budget": ["buyer_budget"],
            "authorize_data": ["legal"],
            "run_probe": ["provider_tech"],
            "accept": ["buyer_ops"],
            "recover": ["provider_tech"],
            "archive_note": ["provider_business"],
        },
        "witness_rules": {
            "run_probe": {"source_role": "buyer_ops", "readback": "pilot_metric"},
            "recover": {"source_role": "buyer_ops", "readback": "recovery_metric"},
        },
        "acceptance_rules": {"accept": {"required_roles": ["buyer_ops"], "effect": "pilot_metric"}},
        "data_rules": {"source_data": {"purposes": ["pilot"], "training": False, "retention_days": 30}},
        "metadata": {"label": "initial", "documentation": "v1"},
    }


def reachable_transition_signature(schema: dict[str, Any], state: str, max_depth: int = 10) -> set[tuple[Any, ...]]:
    transitions = schema.get("transitions", [])
    by_source: dict[str, list[dict[str, Any]]] = {}
    for t in transitions:
        by_source.setdefault(t["from"], []).append(t)
    seen = {state}
    q: deque[tuple[str, int]] = deque([(state, 0)])
    sig: set[tuple[Any, ...]] = set()
    while q:
        source, depth = q.popleft()
        if depth >= max_depth:
            continue
        for t in by_source.get(source, []):
            action = t["action"]
            target = t["to"]
            sig.add((source, action, target, tuple(schema.get("authority_rules", {}).get(action, [])), json.dumps(schema.get("witness_rules", {}).get(action), sort_keys=True), json.dumps(schema.get("acceptance_rules", {}).get(action), sort_keys=True)))
            if target not in seen:
                seen.add(target)
                q.append((target, depth + 1))
    # Active resource semantics and role-definition integrity are part of
    # material trace validity. A transition that still names a deleted role is
    # not semantically equivalent merely because its string signature remains.
    sig.add(("DATA", "source_data", json.dumps(schema.get("data_rules", {}).get("source_data"), sort_keys=True)))
    defined_roles = set(schema.get("roles", {}))
    referenced_roles: set[str] = set()
    for item in sig:
        if len(item) >= 4 and isinstance(item[3], tuple):
            referenced_roles.update(str(role) for role in item[3])
    sig.add(("ROLE_INTEGRITY", tuple(sorted(defined_roles & referenced_roles)), tuple(sorted(referenced_roles - defined_roles))))
    return sig


def ground_truth(old: dict[str, Any], new: dict[str, Any]) -> bool:
    return reachable_transition_signature(old, "FORMING") != reachable_transition_signature(new, "FORMING")


def mutate(rng: random.Random, schema: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    kind = rng.choices(
        ["parameter", "metadata", "unreachable_action", "reachable_authority", "reachable_witness", "reachable_transition", "data_right", "acceptance", "active_role", "unreachable_role"],
        weights=[18, 10, 12, 10, 10, 12, 10, 8, 5, 5],
        k=1,
    )[0]
    new = copy.deepcopy(schema)
    instance = {"price": 5000, "deadline_days": 14}
    if kind == "parameter":
        instance["price"] = rng.choice([3000, 8000, 12000])
    elif kind == "metadata":
        new["metadata"]["label"] = f"label-{rng.randint(1, 9999)}"
    elif kind == "unreachable_action":
        name = f"archived_optional_{rng.randint(1, 999999)}"
        new["actions"][name] = {"actor_roles": ["provider_business"], "material": False}
        new["transitions"].append({"from": "ARCHIVED", "action": name, "to": "ARCHIVED"})
        new["authority_rules"][name] = ["provider_business"]
    elif kind == "reachable_authority":
        new["authority_rules"][rng.choice(["commit_budget", "authorize_data", "accept"])] = ["legal", "buyer_budget"]
    elif kind == "reachable_witness":
        new["witness_rules"]["run_probe"]["source_role"] = rng.choice(["provider_tech", "legal"])
    elif kind == "reachable_transition":
        victim = rng.choice(["commit_budget", "authorize_data", "run_probe", "accept"])
        new["transitions"] = [t for t in new["transitions"] if t["action"] != victim]
    elif kind == "data_right":
        new["data_rules"]["source_data"]["training"] = True
        new["data_rules"]["source_data"]["retention_days"] = 365
    elif kind == "acceptance":
        new["acceptance_rules"]["accept"]["required_roles"].append("buyer_budget")
    elif kind == "active_role":
        new["roles"].pop("buyer_ops", None)
    elif kind == "unreachable_role":
        new["roles"][f"observer_{rng.randint(1,999999)}"] = {"optional": True}
    return kind, new, instance


def classify_policies(old: dict[str, Any], new: dict[str, Any]) -> dict[str, bool]:
    typed = classify_change(old, new, current_state="FORMING", active_resources=["source_data", "pilot_output"], active_roles=["buyer_budget", "buyer_ops", "provider_business", "provider_tech", "legal"])
    return {
        "never_reopen": False,
        "always_reopen": True,
        "any_schema_diff": old != new,
        "typed_materiality": typed.material,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=20260727)
    parser.add_argument("--output", default="results.json")
    args = parser.parse_args()
    rng = random.Random(args.seed)
    matrix: dict[str, Counter[str]] = {name: Counter() for name in ["never_reopen", "always_reopen", "any_schema_diff", "typed_materiality"]}
    kinds = Counter()
    examples: list[dict[str, Any]] = []

    for idx in range(args.cases):
        old = base_schema()
        kind, new, instance = mutate(rng, old)
        truth = ground_truth(old, new)
        kinds[kind] += 1
        for policy, predicted in classify_policies(old, new).items():
            if truth and predicted:
                matrix[policy]["true_positive"] += 1
            elif truth and not predicted:
                matrix[policy]["false_negative"] += 1
            elif not truth and predicted:
                matrix[policy]["false_positive"] += 1
            else:
                matrix[policy]["true_negative"] += 1
        if len(examples) < 20:
            examples.append({"case": idx, "mutation": kind, "material_truth": truth, "instance_only_change": kind == "parameter"})

    policies: dict[str, Any] = {}
    for name, c in matrix.items():
        tp, fn, fp, tn = c["true_positive"], c["false_negative"], c["false_positive"], c["true_negative"]
        policies[name] = {
            **dict(c),
            "material_recall": tp / (tp + fn) if tp + fn else None,
            "nonmaterial_specificity": tn / (tn + fp) if tn + fp else None,
            "decision_error_rate": (fn + fp) / args.cases,
            # Illustrative engineering loss: a missed material reopen is much
            # more expensive than an unnecessary reopen.
            "illustrative_loss": fn * 20 + fp * 2 + tp * 3,
        }
    result = {
        "experiment": "relation_schema_materiality_classifier",
        "seed": args.seed,
        "case_count": args.cases,
        "generator_distribution": dict(kinds),
        "ground_truth": "Exact difference in bounded reachable transition, role-integrity, authority, witness, acceptance, and active-data semantics from FORMING; metadata and instance-parameter changes are excluded.",
        "policies": policies,
        "examples": examples,
        "interpretation_limit": "This is a constructive implementation stress test over a finite generated model. Perfect classification, if observed, means the operational definition and checker agree on this model—not that real organizations have unambiguous schemas or that materiality can always be automatically decided.",
    }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "examples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
