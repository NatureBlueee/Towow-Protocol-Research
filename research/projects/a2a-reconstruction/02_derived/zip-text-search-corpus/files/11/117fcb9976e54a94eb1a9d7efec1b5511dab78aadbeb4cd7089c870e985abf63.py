from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .schema_change import classify_change, compile_readiness
from .store import CaseStore, read_json, write_json


def _load_json(path: str | None) -> dict[str, Any]:
    if path is None:
        return {}
    return read_json(Path(path))


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="towow-fieldkit", description="Towow real-principal research fieldkit")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create a new research case directory")
    init.add_argument("case_dir")
    init.add_argument("--title", required=True)
    init.add_argument("--case-id")

    party = sub.add_parser("add-party", help="Register an external party/authority root")
    party.add_argument("case_dir")
    party.add_argument("--party-id", required=True)
    party.add_argument("--label", required=True)
    party.add_argument("--authority-root", required=True)
    party.add_argument("--contact-ref")

    intake = sub.add_parser("set-intake", help="Store a private prestate intake")
    intake.add_argument("case_dir")
    intake.add_argument("--party-id", required=True)
    intake.add_argument("--file", required=True)

    mandate = sub.add_parser("issue-mandate", help="Store a party-scoped mandate")
    mandate.add_argument("case_dir")
    mandate.add_argument("--party-id", required=True)
    mandate.add_argument("--file", required=True)

    relation = sub.add_parser("add-relation", help="Create a new shared relation version")
    relation.add_argument("case_dir")
    relation.add_argument("--file", required=True)

    event = sub.add_parser("event", help="Append a hash-chained event")
    event.add_argument("case_dir")
    event.add_argument("--type", required=True)
    event.add_argument("--actor", required=True)
    event.add_argument("--payload")
    event.add_argument("--relation-version", type=int)
    event.add_argument("--authority-ref")

    diff = sub.add_parser("classify-change", help="Classify relation-schema materiality")
    diff.add_argument("--old", required=True)
    diff.add_argument("--new", required=True)
    diff.add_argument("--current-state", required=True)
    diff.add_argument("--active-resources", nargs="*", default=[])
    diff.add_argument("--active-roles", nargs="*", default=[])

    compile_cmd = sub.add_parser("compile-check", help="Assess deterministic compilation readiness")
    compile_cmd.add_argument("--schema", required=True)
    compile_cmd.add_argument("--state", required=True)

    validate = sub.add_parser("validate", help="Validate case structure and event hash chain")
    validate.add_argument("case_dir")

    metrics = sub.add_parser("metrics", help="Compute a small auditable case summary")
    metrics.add_argument("case_dir")
    metrics.add_argument("--output")

    adjudicate = sub.add_parser("adjudicate", help="Record an independent outcome adjudication")
    adjudicate.add_argument("case_dir")
    adjudicate.add_argument("--file", required=True)

    export = sub.add_parser("export-redacted", help="Export shared/output artifacts without the private directory")
    export.add_argument("case_dir")
    export.add_argument("destination")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command

    if command == "init":
        store = CaseStore.create(Path(args.case_dir), args.title, args.case_id)
        _print(store.case())
    elif command == "add-party":
        store = CaseStore.open(Path(args.case_dir))
        store.add_party(args.party_id, args.label, args.authority_root, args.contact_ref)
        _print(store.case())
    elif command == "set-intake":
        store = CaseStore.open(Path(args.case_dir))
        path = store.set_private_intake(args.party_id, _load_json(args.file))
        _print({"written": str(path)})
    elif command == "issue-mandate":
        store = CaseStore.open(Path(args.case_dir))
        path = store.issue_mandate(args.party_id, _load_json(args.file))
        _print({"written": str(path)})
    elif command == "add-relation":
        store = CaseStore.open(Path(args.case_dir))
        path = store.add_relation_version(_load_json(args.file))
        _print({"written": str(path)})
    elif command == "event":
        store = CaseStore.open(Path(args.case_dir))
        result = store.append_event(
            event_type=args.type,
            actor=args.actor,
            payload=_load_json(args.payload),
            relation_version=args.relation_version,
            authority_ref=args.authority_ref,
        )
        _print(result)
    elif command == "classify-change":
        report = classify_change(
            _load_json(args.old),
            _load_json(args.new),
            current_state=args.current_state,
            active_resources=args.active_resources,
            active_roles=args.active_roles,
        )
        _print(report.to_dict())
    elif command == "compile-check":
        _print(compile_readiness(_load_json(args.schema), _load_json(args.state)))
    elif command == "validate":
        result = CaseStore.open(Path(args.case_dir)).validate()
        _print(result)
        return 0 if result["valid"] else 1
    elif command == "metrics":
        result = CaseStore.open(Path(args.case_dir)).metrics()
        if args.output:
            write_json(Path(args.output), result)
        _print(result)
    elif command == "adjudicate":
        path = CaseStore.open(Path(args.case_dir)).record_adjudication(_load_json(args.file))
        _print({"written": str(path)})
    elif command == "export-redacted":
        path = CaseStore.open(Path(args.case_dir)).export_redacted(Path(args.destination))
        _print({"written": str(path)})
    else:  # pragma: no cover
        raise AssertionError(command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
