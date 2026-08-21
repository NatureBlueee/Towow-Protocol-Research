#!/usr/bin/env python3
"""Private owner-evidence worker.

Parent mode loads exactly one world's private record, then starts a distinct
child process for every Principal and truth-owner domain.  Only those child
processes instantiate signing keys.  Neither runner.py nor a method worker
receives private key material.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from g2o1.actors import PrincipalActor, canonical_bytes, digest  # noqa: E402


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _private_world(document: Any, world_id: str) -> dict[str, Any]:
    worlds = document.get("worlds", document) if isinstance(document, dict) else {}
    if isinstance(worlds, list):
        for row in worlds:
            if row.get("world_id") == world_id:
                return row
    if isinstance(worlds, dict) and isinstance(worlds.get(world_id), dict):
        return worlds[world_id]
    raise KeyError(f"PRIVATE_WORLD_NOT_FOUND:{world_id}")


def _relation(world: dict[str, Any]) -> dict[str, Any]:
    return (
        world.get("candidate_relation")
        or world.get("relation")
        or world.get("base_relation")
        or {}
    )


def _principal_ids(world: dict[str, Any]) -> list[str]:
    return list(world.get("principal_ids") or world.get("principals") or [])


def _local_views(private: dict[str, Any]) -> dict[str, dict[str, Any]]:
    views = private.get("local_views", {})
    if isinstance(views, list):
        return {
            str(row.get("principal_id") or row.get("id")): row
            for row in views
        }
    return {str(key): value for key, value in views.items()}


def _normalise_stance(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        stance = str(
            value.get("stance")
            or value.get("decision")
            or value.get("mode")
            or "SILENCE"
        ).upper()
        return {
            **value,
            "stance": stance,
            "claim_scope": value.get("claim_scope", "RELATION"),
            "opposition": value.get("opposition"),
        }
    text = str(value or "SILENCE").upper()
    aliases = {
        "ACCEPT": "ACCEPT",
        "ACCEPT_CURRENT": "ACCEPT",
        "CLAIM": "ACCEPT",
        "CLAIM_CURRENT": "ACCEPT",
        "CLAIM_IF_FEASIBLE": "ACCEPT",
        "PLATFORM_CONFIRM": "ACCEPT",
        "PLATFORM_FULFILL": "ACCEPT",
        "PLATFORM_CLOSE": "ACCEPT",
        "PARTIAL_ACCEPT": "PARTIAL",
        "OBJECT_SCOPE": "PARTIAL",
        "REFUSE": "REFUSE",
        "REJECT": "REFUSE",
        "REFUSE_UNTIL_CLARIFIED": "REFUSE",
        "DEFER_IF_NO_COLUMN": "REFUSE",
        # A local-oracle "no column" return is not a Relation stance.  Keeping
        # it silent prevents the controller from manufacturing owner claim.
        "RETURN_NO_COLUMN": "SILENCE",
        "WITHHOLD": "REFUSE",
        "PLATFORM_DECLINE": "REFUSE",
        "OPPOSE": "OPPOSE",
        "WITHDRAW": "WITHDRAW",
        "REVOKE": "WITHDRAW",
        "STALE": "STALE",
        "CLAIM_BASE_ONLY": "STALE",
        "SILENT": "SILENCE",
        "NONE": "SILENCE",
    }
    claim_scope = (
        "DEFECT_LIABILITY" if text == "OBJECT_SCOPE" else "RELATION"
    )
    return {
        "stance": aliases.get(text, text),
        "claim_scope": claim_scope,
        "opposition": text
        if text in {"OPPOSE", "PARTIAL", "OBJECT_SCOPE"}
        else None,
    }


def _normalise_understanding(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        correctness = value.get("correctness")
        if correctness is None:
            correctness = value.get("correct")
        if correctness is None:
            mode = str(value.get("mode", "")).upper()
            correctness = mode in {"CORRECT", "UNDERSTOOD", "PASS"}
        return {
            **value,
            "correctness": bool(correctness),
            "understanding_answers": value.get(
                "understanding_answers", value.get("answers", {})
            ),
        }
    text = str(value or "UNKNOWN").upper()
    return {
        "correctness": text
        in {"CORRECT", "UNDERSTOOD", "PASS", "TRUE", "PRECOMPILED"},
        "understanding_answers": {"model": text},
    }


def _events_for_principal(
    principal_id: str,
    local_view: dict[str, Any],
    private: dict[str, Any],
) -> list[tuple[str, dict[str, Any]]]:
    events: list[tuple[str, dict[str, Any]]] = []
    visible = local_view.get("visible_facts", {})
    schema_delta = (
        local_view.get("schema_delta")
        or (visible.get("schema_delta") if isinstance(visible, dict) else None)
    )
    proposal = (
        visible.get("schema_delta_proposal")
        if isinstance(visible, dict)
        else None
    )
    if not schema_delta and isinstance(proposal, dict) and proposal.get("id"):
        schema_delta = {
            "add": [proposal["id"]],
            "remove": [],
            "proposal": proposal,
        }
    if schema_delta:
        events.append(
            (
                "SCHEMA_OBSERVATION",
                {
                    "schema_delta": schema_delta,
                    "disclosure_units": local_view.get(
                        "schema_disclosure_units", 1
                    ),
                },
            )
        )
    events.append(
        (
            "UNDERSTANDING",
            _normalise_understanding(
                local_view.get(
                    "comprehension_model",
                    local_view.get("understanding"),
                )
            ),
        )
    )
    stance = _normalise_stance(
        local_view.get("stance_policy", local_view.get("stance"))
    )
    if stance["stance"] != "SILENCE":
        events.append(("STANCE", stance))
    if stance.get("opposition"):
        events.append(
            (
                "OPPOSITION",
                {
                    "claim_scope": stance.get("claim_scope"),
                    "opposition": stance["opposition"],
                    "proposed_resolution": stance.get(
                        "proposed_resolution"
                    ),
                },
            )
        )
    owner_acts = private.get("owner_acts", {})
    acts = owner_acts.get(principal_id, []) if isinstance(owner_acts, dict) else []
    for act in acts:
        if isinstance(act, dict) and act.get("action"):
            events.append(
                (
                    str(act["action"]).upper(),
                    {key: value for key, value in act.items() if key != "action"},
                )
            )
    return events


def _domain_actor_specs(
    world: dict[str, Any],
    private: dict[str, Any],
) -> list[dict[str, Any]]:
    relation = _relation(world)
    column_case = private.get("column_case", {})
    availability = str(column_case.get("availability", "ABSENT")).upper()
    policy = str(column_case.get("policy", "RELEASABLE")).upper()
    if availability == "ABSENT":
        public_column = {"status": "ABSENT"}
    elif policy == "WITHHOLD":
        public_column = {"status": "WITHHELD"}
    else:
        first = (column_case.get("columns") or [{}])[0]
        public_column = {
            "status": "PRESENT",
            "column": first,
            "column_id": first.get("column_id"),
        }
    constitution = {
        **private.get("constitution_rules", {}),
        "coupled_assignments": private.get("private_facts", {}).get(
            "coupled_assignments", {}
        ),
    }
    authority = dict(private.get("authority_facts", {}))
    authority["authorized"] = str(
        authority.get("decision", "")
    ).upper().startswith("AUTHORIZE")
    reservation = dict(authority.get("reservation", {}))
    if reservation:
        reservation["unique"] = not bool(
            reservation.get("duplicate_attempt", False)
        )
        reservation["current"] = True
    activation = dict(private.get("activation_facts", {}))
    activation["activated"] = str(
        activation.get("decision", "")
    ).upper().startswith("ACTIVATE")
    activation["target_readback"] = activation["activated"]
    activation["accepted"] = activation["activated"]
    topology = {
        **private.get("private_facts", {}).get("topology", {}),
        "fault_trace": private.get("private_facts", {}).get(
            "fault_trace", {}
        ),
    }
    schema_observation = private.get("private_facts", {}).get(
        "schema_observation", {}
    )
    locally_owned_schema_ids = {
        str(proposal["id"])
        for view in _local_views(private).values()
        for proposal in [
            view.get("visible_facts", {}).get("schema_delta_proposal")
        ]
        if isinstance(proposal, dict) and proposal.get("id")
    }
    schema_author_added_ids = [
        value
        for value in schema_observation.get("added_ids", [])
        if str(value) not in locally_owned_schema_ids
    ]
    return [
        {
            "principal_id": "__WORLD_SCHEMA_AUTHOR__",
            "local_view": {
                "base_schema": (world.get("base_relation") or {}).get(
                    "schema", {}
                ),
                "candidate_schema": relation.get("schema", {}),
                "schema_observation": schema_observation,
            },
            "events": [
                {
                    "action": "WORLD_SCHEMA",
                    "body": {
                        "base_schema": (
                            world.get("base_relation") or {}
                        ).get("schema", {}),
                        "candidate_schema": relation.get("schema", {}),
                    },
                },
                {
                    "action": "SCHEMA_OBSERVATION",
                    "body": {
                        "schema_delta": {
                            "add": schema_observation.get(
                                "added_ids", []
                            )
                            if not locally_owned_schema_ids
                            else schema_author_added_ids,
                            "remove": schema_observation.get(
                                "removed_ids", []
                            ),
                        },
                        "presentation_rewrite": schema_observation.get(
                            "presentation_rewrite", False
                        ),
                    },
                },
            ],
        },
        {
            "principal_id": "__CONSTITUTION_OWNER__",
            "local_view": constitution,
            "events": [
                {
                    "action": "CONSTITUTION_RULES",
                    "body": constitution,
                }
            ],
        },
        {
            "principal_id": "__PRIVATE_COLUMN_ORACLE__",
            "local_view": public_column,
            "events": [
                {
                    "action": "PRIVATE_COLUMN",
                    "body": public_column,
                }
            ],
        },
        {
            "principal_id": "__AUTHORITY_OWNER__",
            "local_view": authority,
            "events": (
                [
                {
                    "action": "AUTHORITY",
                    "body": authority,
                },
                ]
                + (
                    [
                        {
                            "action": "REVOCATION",
                            "body": authority,
                        }
                    ]
                    if authority.get("revoked")
                    else []
                )
                + [
                {
                    "action": "RESERVATION",
                    "body": reservation,
                },
                ]
            ),
        },
        {
            "principal_id": "__TARGET_ACCEPTANCE_OWNER__",
            "local_view": activation,
            "events": [
                {
                    "action": "ACTIVATION",
                    "body": activation,
                }
            ],
        },
        {
            "principal_id": "__TOPOLOGY_OWNER__",
            "local_view": topology,
            "events": [
                {
                    "action": str(
                        topology.get("fault", "TOPOLOGY")
                    ).upper(),
                    "body": topology,
                }
            ],
        },
    ]


def _run_actor_child(spec: dict[str, Any]) -> dict[str, Any]:
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "--actor"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate(
        canonical_bytes(spec), timeout=10
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"OWNER_ACTOR_FAILED:{spec['principal_id']}:"
            f"{stderr.decode('utf-8', errors='replace')}"
        )
    result = json.loads(stdout)
    if result.get("pid") != process.pid:
        raise RuntimeError("OWNER_ACTOR_PID_MISMATCH")
    return result


def actor_main() -> int:
    spec = json.loads(sys.stdin.buffer.read())
    actor = PrincipalActor.create(
        spec["world_id"],
        spec["principal_id"],
        spec["local_view"],
    )
    signed = []
    for sequence, item in enumerate(spec["events"], start=1):
        signed.append(
            actor.sign(
                action=item["action"],
                relation_version=item.get(
                    "relation_version", spec["relation_version"]
                ),
                version_digest=item.get(
                    "version_digest", spec["version_digest"]
                ),
                sequence=sequence,
                body=item.get("body", {}),
            )
        )
    sys.stdout.buffer.write(
        canonical_bytes(
            {
                "actor_id": actor.actor_id,
                "principal_id": actor.principal_id,
                "public_key": actor.public_key_hex,
                "events": signed,
                "pid": os.getpid(),
                "key_material_exported": False,
            }
        )
    )
    return 0


def parent_main(oracle_path: Path) -> int:
    request = json.loads(sys.stdin.buffer.read())
    world = request["world"]
    world_id = str(world["world_id"])
    private = _private_world(_load(oracle_path), world_id)
    relation = _relation(world)
    relation_version = str(relation.get("version", "UNSPECIFIED"))
    version_digest = digest(relation)
    local_views = _local_views(private)
    specs: list[dict[str, Any]] = []
    for principal_id in _principal_ids(world):
        local_view = local_views.get(principal_id, {})
        event_items = [
            {"action": action, "body": body}
            for action, body in _events_for_principal(
                principal_id, local_view, private
            )
        ]
        if str(local_view.get("stance_policy", "")).upper() == "CLAIM_BASE_ONLY":
            base = world.get("base_relation") or {}
            for item in event_items:
                if item["action"] == "STANCE":
                    item["relation_version"] = str(
                        base.get("version", "UNSPECIFIED")
                    )
                    item["version_digest"] = digest(base)
        specs.append(
            {
                "world_id": world_id,
                "principal_id": principal_id,
                "local_view": local_view,
                "relation_version": relation_version,
                "version_digest": version_digest,
                "events": event_items,
            }
        )
    for domain_spec in _domain_actor_specs(world, private):
        specs.append(
            {
                "world_id": world_id,
                "relation_version": relation_version,
                "version_digest": version_digest,
                **domain_spec,
            }
        )
    results = [_run_actor_child(spec) for spec in specs]
    packet = {
        "world_id": world_id,
        "relation_version": relation_version,
        "version_digest": version_digest,
        "public_keys": {
            result["actor_id"]: result["public_key"]
            for result in results
        },
        "owner_events": [
            event for result in results for event in result["events"]
        ],
        "owner_key_processes": {
            result["principal_id"]: result["pid"]
            for result in results
        },
        "key_material_exported": False,
        "owner_worker_pid": os.getpid(),
    }
    sys.stdout.buffer.write(canonical_bytes(packet))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actor", action="store_true")
    parser.add_argument("--oracle", type=Path)
    args = parser.parse_args()
    if args.actor:
        return actor_main()
    if args.oracle is None:
        parser.error("--oracle is required in parent mode")
    return parent_main(args.oracle)


if __name__ == "__main__":
    raise SystemExit(main())
