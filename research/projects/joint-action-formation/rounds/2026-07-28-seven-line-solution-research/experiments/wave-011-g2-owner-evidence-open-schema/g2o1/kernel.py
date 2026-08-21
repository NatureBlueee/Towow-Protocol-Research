"""Method-neutral primitives for the G2-O1 synthetic discriminator.

The kernel has no world-specific expected answers.  It computes observable
structure from relation documents and actor events.  Private facts are only
accepted by evaluator-side helpers after a method has produced a response.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


IGNORED_PRESENTATION_FIELDS = frozenset(
    {"description", "display_name", "label", "notes", "wording"}
)
AXIS_NAMES = ("constituted", "understood", "claimed", "authorized", "activated")
SCHEMA_SECTIONS = (
    "roles",
    "actions",
    "evidence",
    "exit_rules",
    "evaluation_rules",
    "constraints",
)


@dataclass(frozen=True)
class SchemaDelta:
    kind: str
    changed_paths: tuple[str, ...]
    requires_new_version: bool
    added_values: tuple[str, ...] = ()
    removed_values: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["changed_paths"] = list(self.changed_paths)
        result["added_values"] = list(self.added_values)
        result["removed_values"] = list(self.removed_values)
        return result


@dataclass(frozen=True)
class OwnerEvidenceSummary:
    required_principals: tuple[str, ...]
    understood_principals: tuple[str, ...]
    current_claimants: tuple[str, ...]
    stale_claimants: tuple[str, ...]
    objectors: tuple[str, ...]
    scoped_positions: tuple[tuple[str, str], ...]

    @property
    def all_understood(self) -> bool:
        return set(self.required_principals) <= set(self.understood_principals)

    @property
    def all_claimed_current(self) -> bool:
        return set(self.required_principals) <= set(self.current_claimants)

    def to_dict(self) -> dict[str, Any]:
        return {
            "required_principals": list(self.required_principals),
            "understood_principals": list(self.understood_principals),
            "current_claimants": list(self.current_claimants),
            "stale_claimants": list(self.stale_claimants),
            "objectors": list(self.objectors),
            "scoped_positions": [
                {"principal_id": principal_id, "scope": scope}
                for principal_id, scope in self.scoped_positions
            ],
            "all_understood": self.all_understood,
            "all_claimed_current": self.all_claimed_current,
        }


@dataclass(frozen=True)
class ColumnAssessment:
    status: str
    feasible_path_observed: bool
    false_infeasible: bool
    policy_undiscoverable: bool
    disclosed_fields: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AxisResult:
    constituted: bool
    understood: bool
    claimed: bool
    authorized: bool
    activated: bool

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    """Return a content digest over canonical JSON bytes."""

    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _semantic_projection(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _semantic_projection(item)
            for key, item in sorted(value.items())
            if key not in IGNORED_PRESENTATION_FIELDS
        }
    if isinstance(value, list):
        projected = [_semantic_projection(item) for item in value]
        if all(isinstance(item, Mapping) and "id" in item for item in projected):
            return sorted(projected, key=lambda item: str(item["id"]))
        return projected
    return value


def _diff_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if type(left) is not type(right):
        return [prefix or "$"]
    if isinstance(left, Mapping):
        paths: list[str] = []
        for key in sorted(set(left) | set(right)):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(_diff_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        paths = []
        for index in range(max(len(left), len(right))):
            child = f"{prefix}[{index}]"
            if index >= len(left) or index >= len(right):
                paths.append(child)
            else:
                paths.extend(_diff_paths(left[index], right[index], child))
        return paths
    return [] if left == right else [prefix or "$"]


def _semantic_atoms(value: Any) -> set[str]:
    if isinstance(value, Mapping):
        atoms: set[str] = set()
        for key, item in value.items():
            if key in {"id", "operator"} and isinstance(item, (str, int, float, bool)):
                atoms.add(str(item))
            atoms.update(_semantic_atoms(item))
        return atoms
    if isinstance(value, list):
        atoms = set()
        for item in value:
            atoms.update(_semantic_atoms(item))
        return atoms
    return set()


def analyze_schema_delta(
    base_relation: Mapping[str, Any],
    candidate_relation: Mapping[str, Any],
) -> SchemaDelta:
    """Classify a relation change without consuming an author-provided label.

    Schema sections are compared after presentation-only prose is removed.
    This makes a wording-only rewrite distinguishable from a change to a role,
    action, evidence, exit, evaluation or relation-level constraint.
    """

    base_schema = _semantic_projection(base_relation.get("schema", {}))
    candidate_schema = _semantic_projection(candidate_relation.get("schema", {}))
    schema_paths = _diff_paths(base_schema, candidate_schema, "schema")
    if schema_paths:
        base_atoms = _semantic_atoms(base_schema)
        candidate_atoms = _semantic_atoms(candidate_schema)
        return SchemaDelta(
            "SCHEMA_DELTA",
            tuple(schema_paths),
            True,
            tuple(sorted(candidate_atoms - base_atoms)),
            tuple(sorted(base_atoms - candidate_atoms)),
        )

    base_parameters = _semantic_projection(base_relation.get("parameters", {}))
    candidate_parameters = _semantic_projection(
        candidate_relation.get("parameters", {})
    )
    parameter_paths = _diff_paths(
        base_parameters, candidate_parameters, "parameters"
    )
    if parameter_paths:
        return SchemaDelta("PARAMETER_ONLY", tuple(parameter_paths), False)
    return SchemaDelta("IDENTICAL", (), False)


def aggregate_owner_evidence(
    candidate_digest: str,
    required_principals: Iterable[str],
    events: Sequence[Mapping[str, Any]],
    comprehension: Mapping[str, bool],
) -> OwnerEvidenceSummary:
    """Aggregate independently emitted actor evidence.

    Callers must verify actor signatures before invoking this function.  A
    current claim is exact-digest bound; stale acts remain visible and never
    migrate to the current version.
    """

    required = tuple(sorted(set(required_principals)))
    current_claimants: set[str] = set()
    stale_claimants: set[str] = set()
    objectors: set[str] = set()
    positions: set[tuple[str, str]] = set()

    for event in events:
        principal_id = str(event.get("principal_id", ""))
        event_type = str(event.get("event_type", "")).upper()
        relation_digest = str(event.get("relation_digest", ""))
        scope = str(event.get("scope", "RELATION"))
        if principal_id not in required:
            continue
        if event_type in {"CLAIM", "ACCEPT", "LIMITED_CLAIM"}:
            if relation_digest == candidate_digest:
                current_claimants.add(principal_id)
                positions.add((principal_id, scope))
            else:
                stale_claimants.add(principal_id)
        if event_type in {"OBJECT", "COUNTER", "LIMITED_CLAIM", "REFUSE"}:
            objectors.add(principal_id)
            positions.add((principal_id, scope))

    understood = tuple(
        principal_id
        for principal_id in required
        if comprehension.get(principal_id) is True
    )
    return OwnerEvidenceSummary(
        required_principals=required,
        understood_principals=understood,
        current_claimants=tuple(sorted(current_claimants)),
        stale_claimants=tuple(sorted(stale_claimants)),
        objectors=tuple(sorted(objectors)),
        scoped_positions=tuple(sorted(positions)),
    )


def assess_private_column(
    column_case: Mapping[str, Any],
    response: Mapping[str, Any] | None,
) -> ColumnAssessment:
    """Evaluate a method response against evaluator-private local action facts."""

    availability = str(column_case.get("availability", "ABSENT")).upper()
    policy = str(column_case.get("policy", "RELEASABLE")).upper()
    valid_columns = {
        str(column["column_id"]): column
        for column in column_case.get("columns", [])
    }
    response = response or {}
    response_kind = str(response.get("kind", "NO_COLUMN")).upper()
    column_id = str(response.get("column_id", ""))
    disclosed_fields = len(response.get("disclosed_fields", []))

    if availability == "ABSENT":
        if response_kind == "NO_COLUMN":
            return ColumnAssessment(
                "ABSENT_CORRECT", False, False, False, disclosed_fields
            )
        return ColumnAssessment(
            "FABRICATED_COLUMN", False, False, False, disclosed_fields
        )

    if policy == "WITHHOLD":
        if response_kind in {"NO_COLUMN", "WITHHELD", "REFUSE"}:
            return ColumnAssessment(
                "POLICY_UNDISCOVERABLE", False, False, True, disclosed_fields
            )
        return ColumnAssessment(
            "POLICY_BREACH", column_id in valid_columns, False, False, disclosed_fields
        )

    if response_kind == "COLUMN" and column_id in valid_columns:
        return ColumnAssessment("FOUND", True, False, False, disclosed_fields)
    if response_kind == "NO_COLUMN":
        return ColumnAssessment("MISSED", False, True, False, disclosed_fields)
    return ColumnAssessment("INVALID_RESPONSE", False, False, False, disclosed_fields)


def _resolve_assignment(assignments: Mapping[str, Any], path: str) -> Any:
    current: Any = assignments
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def evaluate_coupled_constraints(
    constraints: Sequence[Mapping[str, Any]],
    assignments: Mapping[str, Any],
) -> tuple[bool, tuple[str, ...]]:
    """Evaluate relation-level constraints that cannot be scored term-by-term."""

    failures: list[str] = []
    for constraint in constraints:
        constraint_id = str(constraint.get("id", "UNNAMED"))
        operator = str(constraint.get("operator", "")).upper()
        paths = [str(path) for path in constraint.get("paths", [])]
        values = [_resolve_assignment(assignments, path) for path in paths]

        passed = False
        if operator == "ALL_TRUE":
            passed = bool(values) and all(value is True for value in values)
        elif operator == "AT_LEAST_ONE":
            passed = any(bool(value) for value in values)
        elif operator == "IMPLIES" and len(values) == 2:
            passed = (not bool(values[0])) or bool(values[1])
        elif operator == "EQUAL" and len(values) >= 2:
            passed = len(set(_canonical_bytes(value) for value in values)) == 1
        elif operator == "NOT_BOTH" and len(values) == 2:
            passed = not (bool(values[0]) and bool(values[1]))
        elif operator == "SUM_LTE":
            limit = constraint.get("limit")
            passed = (
                isinstance(limit, (int, float))
                and all(isinstance(value, (int, float)) for value in values)
                and sum(values) <= limit
            )
        if not passed:
            failures.append(constraint_id)
    return (not failures, tuple(failures))


def derive_axis_result(
    *,
    constitution_receipt: Mapping[str, Any],
    owner_evidence: OwnerEvidenceSummary,
    authority_receipt: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
) -> AxisResult:
    """Keep constitution, comprehension, claim, authority and activation apart."""

    return AxisResult(
        constituted=constitution_receipt.get("status") == "CONSTITUTED",
        understood=owner_evidence.all_understood,
        claimed=owner_evidence.all_claimed_current,
        authorized=authority_receipt.get("status") == "AUTHORIZED",
        activated=activation_receipt.get("status") == "ACTIVATED",
    )


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _walk_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def load_public_worlds(path: str | Path) -> dict[str, Any]:
    document = _read_json(path)
    if not isinstance(document, Mapping) or not isinstance(
        document.get("worlds"), list
    ):
        raise ValueError("public fixture must be an object with a worlds list")
    worlds = document["worlds"]
    if len(worlds) != 12:
        raise ValueError(f"expected 12 public worlds, found {len(worlds)}")
    world_ids = [world.get("world_id") for world in worlds]
    if len(set(world_ids)) != 12 or any(not world_id for world_id in world_ids):
        raise ValueError("public world_id values must be unique and non-empty")

    forbidden = {
        "relation" + "_" + "valid",
        "material" + "_" + "change",
        "opposition" + "_" + "preserved",
    }
    leaked = forbidden.intersection(_walk_keys(document))
    if leaked:
        raise ValueError(f"public fixture contains answer-like keys: {sorted(leaked)}")

    family_counts: dict[str, int] = {}
    for world in worlds:
        family = str(world.get("family"))
        family_counts[family] = family_counts.get(family, 0) + 1
    expected = {
        "T2_BLIND": 4,
        "T4_HELD_OUT": 4,
        "T5_CONTROL": 2,
        "AUTHORITY_PRESSURE": 2,
    }
    if family_counts != expected:
        raise ValueError(f"world family counts differ: {family_counts!r}")
    return dict(document)


def load_private_oracle(path: str | Path) -> dict[str, Any]:
    document = _read_json(path)
    if not isinstance(document, Mapping) or not isinstance(
        document.get("worlds"), Mapping
    ):
        raise ValueError("private oracle must be an object with a worlds object")
    if len(document["worlds"]) != 12:
        raise ValueError("private oracle must contain exactly 12 worlds")
    for world_id, truth in document["worlds"].items():
        axes = truth.get("expected", {}).get("axes", {})
        if set(axes) != set(AXIS_NAMES):
            raise ValueError(f"{world_id}: expected axes are incomplete")
        if any(not isinstance(axes[name], bool) for name in AXIS_NAMES):
            raise ValueError(f"{world_id}: axis values must be booleans")
        local_views = truth.get("local_views")
        if not isinstance(local_views, Mapping) or not local_views:
            raise ValueError(f"{world_id}: missing independent local views")
    return dict(document)
