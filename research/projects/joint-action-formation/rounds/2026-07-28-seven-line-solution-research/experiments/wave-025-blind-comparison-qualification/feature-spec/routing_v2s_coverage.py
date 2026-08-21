#!/usr/bin/env python3
"""Executable structural checker for the Wave025 V2S routing candidate.

The proof is deliberately bounded: exact schema/primitives byte bindings, named
capture -> CTX2 construction, active union selectors, scalar and selected
pseudo-event ownership, channel/stat preconditions, and raw F path coverage.  It
does not replace the V1.1 semantic admission validator or prove model/power/G.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import jsonschema


HERE = Path(__file__).resolve().parent
DEFAULT_ROUTING = HERE / "FEATURE-ROUTING-V2S.candidate.json"
DEFAULT_ROUTING_SCHEMA = HERE / "FEATURE-ROUTING-V2S.candidate.schema.json"
DEFAULT_RECEIPT_SCHEMA = HERE / "COLLECTOR-RECEIPT-V1.candidate.schema.json"
DEFAULT_PRIMITIVES = HERE / "V2S-PRIMITIVES.candidate.json"

UNSIGNED_DECIMAL_RE = re.compile(r"0|[1-9][0-9]*\Z")
SIGNED_DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
PRIMITIVES_DECIMAL_RE = re.compile(r"0|-?[1-9][0-9]*\Z")
TAB_FOUR_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\t(?:0|[1-9][0-9]*)){3}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
INDEX_RE = re.compile(r"0|[1-9][0-9]*\Z")
CAPTURE_SEGMENT_RE = re.compile(r"^\{([a-z][a-z0-9_]*):(\*|[^{}]+)\}$")
CONTEXT_CAPTURE_RE = re.compile(r"^\{([a-z][a-z0-9_]*)\}$")
EXPECTED_PSEUDO_UNIVERSE_COUNT = 24
EXPECTED_PSEUDO_UNIVERSE_SHA256 = "67108f341f517ec93be9c7d79d1b4cc1ec3235bbf6e6b98a7c5d69b070c9f3cd"


class CoverageError(ValueError):
    pass


@dataclass(frozen=True)
class ManifestLeaf:
    path_pattern: str
    input_atom: str
    union_trace: tuple[str, ...]
    optional_absence: bool = False


@dataclass(frozen=True)
class SchemaNode:
    path_pattern: str
    kind: str
    union_trace: tuple[str, ...]
    ref_name: str | None = None
    branch_count: int | None = None


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_bytes())


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _escape(segment: str) -> str:
    return segment.replace("~", "~0").replace("/", "~1")


def pointer(parts: Sequence[str]) -> str:
    return "/" + "/".join(_escape(part) for part in parts)


def pointer_parts(path: str) -> list[str]:
    if not path.startswith("/"):
        raise CoverageError(f"not a JSON pointer: {path}")
    return [_unescape(part) for part in path[1:].split("/")] if path != "/" else [""]


def get_pointer(root: Any, path: str) -> Any:
    value = root
    for part in pointer_parts(path):
        if isinstance(value, list):
            if not INDEX_RE.fullmatch(part):
                raise KeyError(path)
            value = value[int(part)]
        elif isinstance(value, Mapping):
            value = value[part]
        else:
            raise KeyError(path)
    return value


def path_present(root: Any, path: str) -> bool:
    try:
        get_pointer(root, path)
        return True
    except (KeyError, IndexError):
        return False


def ancestor_paths(path: str) -> list[str]:
    parts = pointer_parts(path)
    return [pointer(parts[:index]) for index in range(len(parts), 0, -1)]


def compile_pattern(pattern: str, *, allow_recursive: bool = True) -> tuple[re.Pattern[str], tuple[str, ...]]:
    if not pattern.startswith("/"):
        raise CoverageError(f"not a JSON Pointer pattern: {pattern}")
    compiled = ["^"]
    captures: list[str] = []
    parts = pattern[1:].split("/")
    for index, raw in enumerate(parts):
        compiled.append("/")
        if raw == "**":
            if not allow_recursive or index != len(parts) - 1:
                raise CoverageError(f"illegal recursive wildcard: {pattern}")
            compiled.append(r"(?:[^/]+(?:/[^/]+)*)")
            continue
        match = CAPTURE_SEGMENT_RE.fullmatch(raw)
        if match:
            name, expression = match.groups()
            if name in captures:
                raise CoverageError(f"duplicate capture {name}: {pattern}")
            captures.append(name)
            if expression == "*":
                body = r"(?:0|[1-9][0-9]*)"
            else:
                choices = expression.split("|")
                if not choices or any(not choice for choice in choices):
                    raise CoverageError(f"empty alternation: {pattern}")
                body = "(?:" + "|".join(re.escape(_escape(choice)) for choice in choices) + ")"
            compiled.append(f"(?P<{name}>{body})")
        elif "{" in raw or "}" in raw or raw == "*":
            raise CoverageError(f"unnamed or malformed capture: {pattern}")
        else:
            compiled.append(re.escape(raw))
    compiled.append("$")
    return re.compile("".join(compiled)), tuple(captures)


def match_pattern(pattern: str, concrete_path: str) -> dict[str, str] | None:
    regex, _ = compile_pattern(pattern)
    match = regex.fullmatch(concrete_path)
    if not match:
        return None
    return {name: _unescape(value) for name, value in match.groupdict().items()}


def concretize_manifest_path(path_pattern: str) -> str:
    return path_pattern.replace("/*", "/0")


def pattern_matches(pattern: str, concrete_or_manifest_path: str) -> bool:
    return match_pattern(pattern, concretize_manifest_path(concrete_or_manifest_path)) is not None


def scope_match(pattern: str, path: str) -> tuple[str, dict[str, str]] | None:
    if pattern == "/**":
        return path, {}
    for candidate in ancestor_paths(path):
        captures = match_pattern(pattern, candidate)
        if captures is not None:
            return candidate, captures
    return None


def frame32(value: bytes) -> bytes:
    return struct.pack(">I", len(value)) + value


def resolve_context(row: Mapping[str, Any], captures: Mapping[str, str], view: str) -> bytes:
    segments: list[tuple[str, bytes]] = []
    referenced: set[str] = set()
    for template in row["context_segments"]:
        kind, raw_value = template.split(":", 1)
        capture = CONTEXT_CAPTURE_RE.fullmatch(raw_value)
        if capture:
            name = capture.group(1)
            if name not in captures:
                raise CoverageError(f"{row['id']} unbound context capture {name}")
            referenced.add(name)
            value = captures[name]
        else:
            if "{" in raw_value or "}" in raw_value or "$" in raw_value:
                raise CoverageError(f"{row['id']} malformed context template {template}")
            value = raw_value
        if kind == "ORDERED" and view in {"BAG", "LEXICAL_BAG", "PARENT"}:
            continue
        if kind == "KEY":
            encoded = b"\x01" + frame32(value.encode("utf-8"))
        elif kind == "ORDERED":
            if not INDEX_RE.fullmatch(value) or int(value) > 0xFFFFFFFF:
                raise CoverageError(f"{row['id']} noncanonical ORDERED capture {value!r}")
            encoded = b"\x02" + struct.pack(">I", int(value))
        elif kind == "BAG_ITEM":
            encoded = b"\x03"
        elif kind == "DERIVED":
            try:
                ascii_value = value.encode("ascii")
            except UnicodeEncodeError as error:
                raise CoverageError(f"{row['id']} non-ASCII DERIVED") from error
            encoded = b"\x04" + frame32(ascii_value)
        else:
            raise CoverageError(f"{row['id']} unknown context segment kind {kind}")
        segments.append((kind, encoded))
    # Every context placeholder must correspond to a named path capture. Captures
    # may intentionally be unreferenced for unordered bag item indices.
    _, declared = compile_pattern(row["path_pattern"])
    if not referenced <= set(declared):
        raise CoverageError(f"{row['id']} context capture is not declared by path")
    body = frame32(b"WAVE025_CONTEXT_V2S") + struct.pack(">I", len(segments)) + b"".join(value for _, value in segments)
    return body


def expand_finite_pattern(pattern: str) -> list[tuple[str, dict[str, str]]]:
    """Expand finite alternations and use index 0 as a wildcard representative."""
    parts = pattern[1:].split("/")
    options: list[list[tuple[str, str | None, str | None]]] = []
    for raw in parts:
        match = CAPTURE_SEGMENT_RE.fullmatch(raw)
        if not match:
            if raw == "**":
                return []
            options.append([(raw, None, None)])
            continue
        name, expression = match.groups()
        values = ["0"] if expression == "*" else expression.split("|")
        options.append([(_escape(value), name, value) for value in values])
    result = []
    for selected in itertools.product(*options):
        captures = {name: decoded for _, name, decoded in selected if name is not None}
        result.append(("/" + "/".join(encoded for encoded, _, _ in selected), captures))
    return result


def input_atom_for_value(value: Any, path: str) -> str:
    if value is None:
        return "JSON_NULL"
    if isinstance(value, bool):
        return "JSON_BOOL"
    if isinstance(value, int):
        return "JSON_INT"
    if isinstance(value, float):
        return "JSON_RATIONAL"
    if not isinstance(value, str):
        raise CoverageError(f"non-scalar passed at {path}")
    leaf_name = path.rsplit("/", 1)[-1]
    if SHA256_RE.fullmatch(value) and leaf_name.endswith("sha256"):
        return "SHA256_HEX"
    if TAB_FOUR_RE.fullmatch(value) and leaf_name in {"uid", "gid"} and "/status/" in path:
        return "TAB_DECIMAL_INT_SERIES"
    if leaf_name in {"mtime_ns", "ctime_ns"} and SIGNED_DECIMAL_RE.fullmatch(value):
        return "SIGNED_DECIMAL_INT_STRING"
    if UNSIGNED_DECIMAL_RE.fullmatch(value):
        if leaf_name in {
            "uid", "gid", "size_bytes", "inode", "device", "nlink", "ppid", "threads",
            "elapsed_ns", "monotonic_ns", "monotonic_start_ns", "monotonic_end_ns",
        } or re.fullmatch(r"/timing/(?:immediate_delta_ns|input_stat_elapsed_ns)/(?:0|[1-9][0-9]*)", path):
            return "DECIMAL_INT_STRING"
    return "UTF8_STRING"


def normalize_signed_decimal(value: str) -> str:
    if not SIGNED_DECIMAL_RE.fullmatch(value):
        raise CoverageError("NOT_QUALIFIED_INVALID_DECIMAL_INTEGER_STRING")
    normalized = "0" if value in {"0", "-0"} else value
    if not PRIMITIVES_DECIMAL_RE.fullmatch(normalized):
        raise CoverageError("NOT_QUALIFIED_INVALID_DECIMAL_INTEGER_STRING")
    return normalized


def atom_accepts(route_atom: str, leaf_atom: str, *, exclusion: bool = False) -> bool:
    return exclusion or route_atom == leaf_atom or (route_atom == "JSON_RATIONAL" and leaf_atom == "JSON_INT")


def scalar_leaves(value: Any, parts: tuple[str, ...] = ()) -> Iterator[tuple[str, Any, str]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            yield from scalar_leaves(value[key], parts + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from scalar_leaves(item, parts + (str(index),))
    else:
        path = pointer(parts)
        yield path, value, input_atom_for_value(value, path)


def all_nodes(value: Any, parts: tuple[str, ...] = ()) -> Iterator[tuple[str, Any]]:
    path = pointer(parts)
    yield path, value
    if isinstance(value, Mapping):
        for key in sorted(value):
            yield from all_nodes(value[key], parts + (str(key),))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from all_nodes(item, parts + (str(index),))


def _resolve(schema: Mapping[str, Any], root: Mapping[str, Any]) -> tuple[Mapping[str, Any], str | None]:
    seen: set[str] = set()
    result = dict(schema)
    last_ref = None
    while "$ref" in result:
        ref = result["$ref"]
        if ref in seen or not ref.startswith("#/$defs/"):
            raise CoverageError(f"unsupported/cyclic ref {ref}")
        seen.add(ref)
        last_ref = ref.split("/")[-1]
        if last_ref not in root.get("$defs", {}):
            raise CoverageError(f"missing schema definition {last_ref}")
        result = dict(root["$defs"][last_ref])
    return result, last_ref


def _merge_schema(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(left))
    for key, value in right.items():
        if key == "properties":
            result.setdefault(key, {}).update(copy.deepcopy(value))
        elif key == "required":
            result[key] = sorted(set(result.get(key, [])) | set(value))
        elif key in result and result[key] != value and key not in {"title", "description"}:
            result[key] = copy.deepcopy(value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _expand_all_of(schema: Mapping[str, Any], root: Mapping[str, Any]) -> tuple[Mapping[str, Any], str | None]:
    resolved, ref_name = _resolve(schema, root)
    if "allOf" not in resolved:
        return resolved, ref_name
    base = {key: value for key, value in resolved.items() if key != "allOf"}
    for member in resolved["allOf"]:
        expanded, _ = _expand_all_of(member, root)
        base = _merge_schema(base, expanded)
    return base, ref_name


def _schema_atom(schema: Mapping[str, Any], path: str) -> str:
    if "const" in schema:
        return input_atom_for_value(schema["const"], path)
    if "enum" in schema:
        atoms = {input_atom_for_value(value, path) for value in schema["enum"]}
        if len(atoms) != 1:
            raise CoverageError(f"mixed-type enum at {path}")
        return next(iter(atoms))
    kind = schema.get("type")
    if kind == "null": return "JSON_NULL"
    if kind == "boolean": return "JSON_BOOL"
    if kind == "integer": return "JSON_INT"
    if kind == "number": return "JSON_RATIONAL"
    if kind != "string":
        raise CoverageError(f"cannot infer scalar atom at {path}")
    pattern = schema.get("pattern", "")
    if pattern == "^[0-9a-f]{64}$" or path.endswith("sha256"):
        return "SHA256_HEX"
    if "\\t" in pattern and path.rsplit("/", 1)[-1] in {"uid", "gid"}:
        return "TAB_DECIMAL_INT_SERIES"
    if pattern.startswith("^-?"):
        return "SIGNED_DECIMAL_INT_STRING"
    if "0|[1-9][0-9]*" in pattern:
        return "DECIMAL_INT_STRING"
    return "UTF8_STRING"


def generate_schema_manifests(receipt_schema: Mapping[str, Any]) -> tuple[list[ManifestLeaf], list[SchemaNode]]:
    leaves: list[ManifestLeaf] = []
    nodes: list[SchemaNode] = []

    def visit(raw: Mapping[str, Any], parts: tuple[str, ...], trace: tuple[str, ...]) -> None:
        ref_name = raw.get("$ref", "").split("/")[-1] if raw.get("$ref", "").startswith("#/$defs/") else None
        node, resolved_ref = _expand_all_of(raw, receipt_schema)
        path = pointer(parts)
        if ref_name:
            nodes.append(SchemaNode(path, "REF", trace, ref_name))
        if "oneOf" in node:
            nodes.append(SchemaNode(path, "UNION", trace, resolved_ref or ref_name, len(node["oneOf"])))
            for index, variant in enumerate(node["oneOf"]):
                ref = variant.get("$ref") if isinstance(variant, Mapping) else None
                label = ref.split("/")[-1] if ref else f"oneOf[{index}]"
                visit(variant, parts, trace + (label,))
            return
        kind = node.get("type")
        if kind == "object" or "properties" in node:
            nodes.append(SchemaNode(path, "OBJECT", trace, resolved_ref or ref_name))
            properties = node.get("properties", {})
            required = set(node.get("required", []))
            for key in sorted(properties):
                child = parts + (key,)
                if key not in required:
                    leaves.append(ManifestLeaf(pointer(child), "MISSING2", trace + ("OPTIONAL_ABSENT",), True))
                visit(properties[key], child, trace)
            return
        if kind == "array":
            nodes.append(SchemaNode(path, "ARRAY", trace, resolved_ref or ref_name))
            if "prefixItems" in node:
                for index, child in enumerate(node["prefixItems"]):
                    visit(child, parts + (str(index),), trace + (f"prefix[{index}]",))
            if isinstance(node.get("items"), Mapping):
                visit(node["items"], parts + ("*",), trace + ("array_item",))
            return
        leaves.append(ManifestLeaf(path, _schema_atom(node, path), trace))

    visit(receipt_schema, (), ())
    return (
        sorted(set(leaves), key=lambda item: (item.path_pattern, item.input_atom, item.union_trace)),
        sorted(set(nodes), key=lambda item: (item.path_pattern, item.kind, item.union_trace, item.ref_name or "")),
    )


def generate_variant_manifest(receipt_schema: Mapping[str, Any]) -> list[ManifestLeaf]:
    return generate_schema_manifests(receipt_schema)[0]


def _static_variant_active(definition: Mapping[str, Any], leaf: ManifestLeaf) -> bool:
    if not any(scope_match(pattern, concretize_manifest_path(leaf.path_pattern)) for pattern in definition["scope_patterns"]):
        return False
    rule = definition["static_match"]
    if rule.get("atom") not in {None, leaf.input_atom}:
        return False
    if "optional_absence" in rule and bool(rule["optional_absence"]) != leaf.optional_absence:
        return False
    if "path_prefix" in rule and not leaf.path_pattern.startswith(rule["path_prefix"]):
        return False
    if "path_exact" in rule and leaf.path_pattern != rule["path_exact"]:
        return False
    if "path_contains" in rule and rule["path_contains"] not in leaf.path_pattern:
        return False
    if "trace_first" in rule and (not leaf.union_trace or leaf.union_trace[0] != rule["trace_first"]):
        return False
    if "trace_any" in rule and not all(token in leaf.union_trace for token in rule["trace_any"]):
        return False
    if "trace_last_oneof" in rule:
        oneofs = [token for token in leaf.union_trace if token.startswith("oneOf[")]
        if not oneofs or oneofs[-1] != rule["trace_last_oneof"]:
            return False
    return True


def variant_expression_static(routing: Mapping[str, Any], expression: Mapping[str, Any], leaf: ManifestLeaf) -> bool:
    registry = routing["variant_registry"]
    for conjunction in expression["any_of"]:
        if all(name in registry and _static_variant_active(registry[name], leaf) for name in conjunction):
            return True
    return False


def _runtime_type(value: Any) -> str:
    if value is None: return "null"
    if isinstance(value, bool): return "boolean"
    if isinstance(value, str): return "string"
    if isinstance(value, Mapping): return "object"
    if isinstance(value, list): return "array"
    if isinstance(value, (int, float)): return "number"
    return "unknown"


def _eval_selector(selector: Mapping[str, Any], scope_value: Any, *, atom: str, present: bool) -> bool:
    op = selector["op"]
    if op in {"ALWAYS", "PATH_SCOPE"}: return True
    if op == "CURRENT_ATOM": return atom == selector["atom"]
    if op == "CURRENT_OR_ANCESTOR_TYPE": return _runtime_type(scope_value) == selector["type"]
    if op == "CURRENT_PATH_PRESENT": return present
    if op == "CURRENT_PATH_ABSENT": return not present
    if op == "PROPERTY_PRESENT": return isinstance(scope_value, Mapping) and selector["property"] in scope_value
    if op == "PROPERTY_ABSENT": return isinstance(scope_value, Mapping) and selector["property"] not in scope_value
    if op == "PROPERTY_EQUALS": return isinstance(scope_value, Mapping) and scope_value.get(selector["property"], object()) == selector["value"]
    if op == "PROPERTY_NOT_EQUALS": return isinstance(scope_value, Mapping) and scope_value.get(selector["property"], object()) != selector["value"]
    if op == "ALL": return all(_eval_selector(member, scope_value, atom=atom, present=present) for member in selector["selectors"])
    raise CoverageError(f"unknown runtime selector op {op}")


def runtime_variant_active(routing: Mapping[str, Any], name: str, path: str, root: Any, atom: str, *, present: bool = True) -> bool:
    if name not in routing["variant_registry"]:
        raise CoverageError(f"unknown variant label {name}")
    definition = routing["variant_registry"][name]
    for pattern in definition["scope_patterns"]:
        matched = scope_match(pattern, path)
        if matched is None:
            continue
        scope_path, _ = matched
        scope_value = get_pointer(root, scope_path) if path_present(root, scope_path) else None
        if _eval_selector(definition["runtime_selector"], scope_value, atom=atom, present=present):
            return True
    return False


def variant_expression_runtime(routing: Mapping[str, Any], expression: Mapping[str, Any], path: str, root: Any, atom: str, *, present: bool = True) -> bool:
    return any(all(runtime_variant_active(routing, name, path, root, atom, present=present) for name in conjunction) for conjunction in expression["any_of"])


def matching_rows_static(routing: Mapping[str, Any], leaf: ManifestLeaf) -> list[Mapping[str, Any]]:
    kind = "ABSENCE" if leaf.optional_absence else "SCALAR_LEAF"
    result = []
    for row in routing["rows"]:
        if row["event_kind"] != kind or not pattern_matches(row["path_pattern"], leaf.path_pattern):
            continue
        exclusion = row["leaf_audit_owner"]["disposition"] == "EXCLUDE"
        if atom_accepts(row["input_atom"], leaf.input_atom, exclusion=exclusion) and variant_expression_static(routing, row["variant_expression"], leaf):
            result.append(row)
    return result


def matching_rows_runtime(routing: Mapping[str, Any], path: str, atom: str, root: Any, event_kind: str = "SCALAR_LEAF", *, present: bool = True) -> list[Mapping[str, Any]]:
    result = []
    for row in routing["rows"]:
        if row["event_kind"] != event_kind:
            continue
        captures = match_pattern(row["path_pattern"], path)
        if captures is None:
            continue
        exclusion = row["leaf_audit_owner"]["disposition"] == "EXCLUDE"
        if atom_accepts(row["input_atom"], atom, exclusion=exclusion) and variant_expression_runtime(routing, row["variant_expression"], path, root, atom, present=present):
            result.append(row)
    return result


def matching_rows(routing: Mapping[str, Any], path: str, atom: str, event_kind: str = "SCALAR_LEAF") -> list[Mapping[str, Any]]:
    """Compatibility helper for non-union path-only attacks.

    Executable verification uses matching_rows_static/runtime. This helper is
    intentionally unavailable for variant-dependent paths.
    """
    synthetic = ManifestLeaf(path, atom, ("NO_TRACE",), event_kind == "ABSENCE")
    return matching_rows_static(routing, synthetic)


def _definition_closed(schema: Mapping[str, Any], root: Mapping[str, Any], seen: set[str] | None = None) -> bool:
    seen = set() if seen is None else set(seen)
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/$defs/"): return False
        name = ref.split("/")[-1]
        if name in seen: return True
        if name not in root.get("$defs", {}): return False
        seen.add(name)
        return _definition_closed(root["$defs"][name], root, seen)
    if "oneOf" in schema:
        return all(_definition_closed(member, root, seen) for member in schema["oneOf"])
    if "allOf" in schema:
        return all(_definition_closed(member, root, seen) for member in schema["allOf"])
    if schema.get("type") == "object" or "properties" in schema:
        if schema.get("additionalProperties") is not False:
            return False
        return all(_definition_closed(member, root, seen) for member in schema.get("properties", {}).values())
    if schema.get("type") == "array":
        members = list(schema.get("prefixItems", []))
        if isinstance(schema.get("items"), Mapping): members.append(schema["items"])
        return all(_definition_closed(member, root, seen) for member in members)
    return True


def derive_channel_stat_matrix(routing: Mapping[str, Any]) -> list[dict[str, Any]]:
    registry = routing["channel_stat_registry"]
    output = []
    for row in routing["rows"]:
        for channel in row["channels"]:
            name = channel["channel"]
            if name not in registry:
                raise CoverageError(f"{row['id']} channel absent from channel/stat registry: {name}")
            if name == "MISSING":
                expected = channel.get("expected_channel")
                if expected not in registry or expected == "MISSING":
                    raise CoverageError(f"{row['id']} invalid expected_channel")
                if channel.get("expected_stats") != registry[expected]["stats"]:
                    raise CoverageError(f"{row['id']} expected_stats mismatch")
                for expected_stat in channel["expected_stats"]:
                    output.append({"family":row["family"],"route_id":row["id"],"channel":"MISSING","stat":"NONE","expected_channel":expected,"expected_stat":expected_stat,"cardinality":row["cardinality"]})
            else:
                if "expected_channel" in channel or "expected_stats" in channel:
                    raise CoverageError(f"{row['id']} nonmissing channel carries expected metadata")
                for stat in registry[name]["stats"]:
                    output.append({"family":row["family"],"route_id":row["id"],"channel":name,"stat":stat,"expected_channel":"NONE","expected_stat":"NONE","cardinality":row["cardinality"]})
    keys = ["family","route_id","channel","stat","expected_channel","expected_stat","cardinality"]
    return sorted(output, key=lambda item: tuple(item[key] for key in keys))


def derive_pseudo_expected_universe(routing: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project pseudo expectations without trusting owner row ids or spec ids.

    The resulting bytes are checked against a frozen digest derived from the
    receipt-schema nodes and the separately reviewed pseudo-selection registry.
    Therefore adding a row and a matching spec cannot enlarge the expected
    universe from inside the routing candidate.
    """
    output = []
    for spec in routing["pseudo_event_specs"]:
        item = {
            "event_kind": spec["event_kind"],
            "path_pattern": spec["path_pattern"],
            "variant_expression": spec["variant_expression"],
            "selector_binding_sha256": spec["selector_binding_sha256"],
        }
        if "schema_def" in spec:
            item["schema_def"] = spec["schema_def"]
        output.append(item)
    return sorted(
        output,
        key=lambda item: (
            item["event_kind"],
            item["path_pattern"],
            json.dumps(item["variant_expression"], sort_keys=True, separators=(",", ":")),
            item.get("schema_def", ""),
            item["selector_binding_sha256"],
        ),
    )


def verify_candidate_bytes(routing_bytes: bytes, routing_schema_bytes: bytes, receipt_schema_bytes: bytes, primitives_bytes: bytes) -> tuple[Mapping[str, Any], Mapping[str, Any], dict[str, Any]]:
    try:
        routing = json.loads(routing_bytes)
        routing_schema = json.loads(routing_schema_bytes)
        receipt_schema = json.loads(receipt_schema_bytes)
        primitives = json.loads(primitives_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CoverageError("invalid bound JSON bytes") from error
    if routing_bytes != canonical_bytes(routing):
        raise CoverageError("routing candidate is not canonical compact UTF-8 JSON plus one LF")
    if routing_schema_bytes != canonical_bytes(routing_schema):
        raise CoverageError("routing schema is not canonical compact UTF-8 JSON plus one LF")
    schema_errors = sorted(jsonschema.Draft202012Validator(routing_schema).iter_errors(routing), key=lambda error: list(error.path))
    if schema_errors:
        raise CoverageError("routing schema failure: " + "; ".join(error.message for error in schema_errors[:5]))
    for key, raw in [("input_schema", receipt_schema_bytes), ("primitives_binding", primitives_bytes)]:
        binding = routing[key]
        if binding["sha256"] != sha256_bytes(raw) or binding["byte_length"] != len(raw):
            raise CoverageError(f"{key} exact byte binding mismatch")
    if primitives.get("schema") != routing["primitives_binding"]["schema"] or primitives.get("candidate_status") != routing["primitives_binding"]["candidate_status"]:
        raise CoverageError("primitives schema/status binding mismatch")
    primitive_families = primitives.get("dependencies", {}).get("routing_contract", {}).get("exact_families")
    if primitive_families != routing["families"] or routing["primitives_binding"]["exact_families"] != routing["families"]:
        raise CoverageError("exact seven-family binding mismatch")

    ids = [row["id"] for row in routing["rows"]]
    if len(ids) != len(set(ids)):
        raise CoverageError("duplicate route id")
    for row in routing["rows"]:
        _, captures = compile_pattern(row["path_pattern"])
        capture_expressions = {
            match.group(1): match.group(2)
            for segment in row["path_pattern"][1:].split("/")
            if (match := CAPTURE_SEGMENT_RE.fullmatch(segment))
        }
        reference_kinds: dict[str, list[str]] = {}
        if "**" in row["path_pattern"] and row["leaf_audit_owner"]["disposition"] != "EXCLUDE":
            raise CoverageError(f"{row['id']} recursive pattern is not EXCLUDE")
        for template in row["context_segments"]:
            kind, raw = template.split(":", 1)
            capture = CONTEXT_CAPTURE_RE.fullmatch(raw)
            if capture:
                name = capture.group(1)
                if name not in captures:
                    raise CoverageError(f"{row['id']} unbound context capture {name}")
                reference_kinds.setdefault(name, []).append(kind)
            if "$" in template:
                raise CoverageError(f"{row['id']} contains legacy literal placeholder")
        required_captures: dict[str, str] = {}
        dropped_item_captures = set()
        for name, expression in capture_expressions.items():
            if expression == "*" and re.fullmatch(r"item[0-9]*", name) and row["cardinality"] in {"BAG_MULTISET", "CONTAINER_COUNT"}:
                dropped_item_captures.add(name)
            else:
                required_captures[name] = "ORDERED" if expression == "*" else "KEY"
        for name, required_kind in required_captures.items():
            kinds = reference_kinds.get(name, [])
            if kinds != [required_kind]:
                raise CoverageError(f"{row['id']} required capture {name} must be referenced exactly once as {required_kind}")
            if required_kind == "ORDERED" and row["leaf_audit_owner"]["disposition"] == "INCLUDE" and not any(
                channel["context"] in {"ROW", "ORDERED", "LEXICAL_ROUTE"}
                for channel in row["channels"]
            ):
                raise CoverageError(f"{row['id']} required ORDERED capture {name} is dropped by every emitted view")
        if dropped_item_captures:
            if any(name in reference_kinds for name in dropped_item_captures):
                raise CoverageError(f"{row['id']} unordered item capture must not enter CTX2")
            if not any(template.startswith("BAG_ITEM:") for template in row["context_segments"]):
                raise CoverageError(f"{row['id']} dropped item capture lacks BAG_ITEM marker")
        if set(reference_kinds) != set(required_captures):
            raise CoverageError(f"{row['id']} capture reference completeness failure")
        for conjunction in row["variant_expression"]["any_of"]:
            for name in conjunction:
                if name not in routing["variant_registry"]:
                    raise CoverageError(f"{row['id']} unknown union variant {name}")
        for path, path_captures in expand_finite_pattern(row["path_pattern"]):
            for channel in row["channels"] or [{"context":"ROW"}]:
                resolve_context(row, path_captures, channel["context"])
        if row["input_atom"] == "SHA256_HEX":
            allowed = {("EXACT_CATEGORY","TVE2_EXACT_CATEGORY"),("EXACT_CATEGORY","TVE2_EXACT_CATEGORY_COUNT")}
            actual = {(channel["channel"], channel["transform"]) for channel in row["channels"]}
            if len(actual) != 1 or not actual <= allowed:
                raise CoverageError(f"{row['id']} violates strict SHA exact-only allowlist")
        lexical_channels = [channel for channel in row["channels"] if "NGRAM" in channel["channel"]]
        for lexical in lexical_channels:
            suffix = "_BAG" if lexical["channel"].endswith("_BAG") else ("_ORDERED" if lexical["channel"].endswith("_ORDERED") else "")
            names = {channel["channel"] for channel in row["channels"]}
            if f"LEXICAL_FULL_BYTE_LENGTH{suffix}" not in names or f"LEXICAL_TRUNCATED{suffix}" not in names:
                raise CoverageError(f"{row['id']} ngram route lacks same-view companions")
            required_context = "LEXICAL_BAG" if suffix == "_BAG" else "LEXICAL_ROUTE"
            if lexical["context"] != required_context:
                raise CoverageError(f"{row['id']} ngram context is not route-aware")

    manifest, nodes = generate_schema_manifests(receipt_schema)
    unowned = []
    multiply = []
    for leaf in manifest:
        matches = matching_rows_static(routing, leaf)
        if not matches: unowned.append(leaf)
        elif len(matches) > 1: multiply.append((leaf, [row["id"] for row in matches]))

    # Pseudo specs are the expected manifest, separate from owner rows.
    spec_ids = [spec["id"] for spec in routing["pseudo_event_specs"]]
    if len(spec_ids) != len(set(spec_ids)):
        raise CoverageError("duplicate pseudo event spec id")
    expected_universe = derive_pseudo_expected_universe(routing)
    expected_universe_binding = routing["pseudo_event_expected_universe"]
    actual_universe_sha256 = sha256_bytes(canonical_bytes(expected_universe))
    if (
        len(expected_universe) != EXPECTED_PSEUDO_UNIVERSE_COUNT
        or actual_universe_sha256 != EXPECTED_PSEUDO_UNIVERSE_SHA256
        or expected_universe_binding["entry_count"] != EXPECTED_PSEUDO_UNIVERSE_COUNT
        or expected_universe_binding["sha256"] != EXPECTED_PSEUDO_UNIVERSE_SHA256
    ):
        raise CoverageError("pseudo expected universe differs from frozen schema-derived manifest")
    selected_owner_ids = []
    row_by_id = {row["id"]: row for row in routing["rows"]}
    node_counts = {"UNION_BRANCH":0,"CONTAINER":0,"CLOSED_RECORD":0,"ABSENCE":0}
    for spec in routing["pseudo_event_specs"]:
        owner = row_by_id.get(spec["owner_route_id"])
        if owner is None:
            raise CoverageError(f"{spec['id']} owner route missing")
        selected_owner_ids.append(owner["id"])
        for field in ["event_kind","path_pattern","variant_expression"]:
            if owner[field] != spec[field]:
                raise CoverageError(f"{spec['id']} owner {field} mismatch")
        selector_names = sorted({
            name
            for conjunction in spec["variant_expression"]["any_of"]
            for name in conjunction
        })
        try:
            selector_projection = {
                name: routing["variant_registry"][name]
                for name in selector_names
            }
        except KeyError as error:
            raise CoverageError(f"{spec['id']} unknown selector variant {error.args[0]}") from error
        if spec["selector_binding_sha256"] != sha256_bytes(canonical_bytes(selector_projection)):
            raise CoverageError(f"{spec['id']} selector binding mismatch")
        if spec["event_kind"] == "UNION_BRANCH":
            matched_nodes = [node for node in nodes if node.kind == "UNION" and pattern_matches(spec["path_pattern"], node.path_pattern)]
            if not matched_nodes:
                raise CoverageError(f"{spec['id']} branch path is unreachable")
            alternatives = len(spec["variant_expression"]["any_of"])
            if any(node.branch_count != alternatives for node in matched_nodes):
                raise CoverageError(f"{spec['id']} branch selector cardinality mismatch")
        elif spec["event_kind"] == "CONTAINER":
            if not any(node.kind == "ARRAY" and pattern_matches(spec["path_pattern"], node.path_pattern) for node in nodes):
                raise CoverageError(f"{spec['id']} container path is unreachable")
        elif spec["event_kind"] == "CLOSED_RECORD":
            ref = spec.get("schema_def", "").split("/")[-1]
            if ref not in receipt_schema.get("$defs", {}) or not _definition_closed({"$ref": spec["schema_def"]}, receipt_schema):
                raise CoverageError(f"{spec['id']} missing or open record definition")
            if owner.get("closed_projection", {}).get("schema_def") != spec["schema_def"]:
                raise CoverageError(f"{spec['id']} record projection mismatch")
            if not any(node.kind == "REF" and node.ref_name == ref and pattern_matches(spec["path_pattern"], node.path_pattern) for node in nodes):
                raise CoverageError(f"{spec['id']} record definition is not reachable at path")
        else:
            if not any(leaf.optional_absence and pattern_matches(spec["path_pattern"], leaf.path_pattern) for leaf in manifest):
                raise CoverageError(f"{spec['id']} absence path is unreachable")
        node_counts[spec["event_kind"]] += 1
    pseudo_rows = [row["id"] for row in routing["rows"] if row["event_kind"] != "SCALAR_LEAF"]
    if sorted(selected_owner_ids) != sorted(pseudo_rows) or len(selected_owner_ids) != len(set(selected_owner_ids)):
        raise CoverageError("pseudo event rows and selected owner specs are not bijective")

    matrix = derive_channel_stat_matrix(routing)
    matrix_bytes = canonical_bytes(matrix)
    declared_matrix = routing["channel_stat_matrix"]
    if declared_matrix["entry_count"] != len(matrix) or declared_matrix["sha256"] != sha256_bytes(matrix_bytes):
        raise CoverageError("channel/stat matrix binding mismatch")

    # Expand finite capture domains and prove every BAG numeric output identity is
    # owned by one route/channel only. Array item index 0 is representative because
    # BAG/LEXICAL_BAG removes ORDERED and item captures are never implicitly injected.
    bag_owners: dict[tuple[str,str,str], set[tuple[str,str]]] = {}
    registry = routing["channel_stat_registry"]
    for row in routing["rows"]:
        if row["cardinality"] != "BAG_MULTISET": continue
        for _, captures in expand_finite_pattern(row["path_pattern"]):
            for channel in row["channels"]:
                if registry[channel["channel"]]["kind"] != "NUMERIC": continue
                ctx = resolve_context(row, captures, channel["context"]).hex()
                for stat in registry[channel["channel"]]["stats"]:
                    bag_owners.setdefault((row["family"],ctx,stat),set()).add((row["id"],channel["channel"]))
    bag_collisions = {key:sorted(value) for key,value in bag_owners.items() if len(value)>1}
    if bag_collisions:
        raise CoverageError(f"BAG exactly-one-input-channel collision: {next(iter(bag_collisions.values()))}")

    report = {
        "route_count":len(routing["rows"]),
        "family_counts":{family:sum(row["family"]==family for row in routing["rows"]) for family in routing["families"]},
        "manifest_leaf_variants":len(manifest),
        "manifest_unique_path_atom":len({(leaf.path_pattern,leaf.input_atom,leaf.optional_absence) for leaf in manifest}),
        "unowned":[leaf.__dict__ for leaf in unowned],
        "multiply_owned":[{"leaf":leaf.__dict__,"rows":rows} for leaf,rows in multiply],
        "pseudo_event_spec_counts":node_counts,
        "channel_stat_matrix_entries":len(matrix),
        "bag_numeric_identity_owners":len(bag_owners),
        "structural_ownership":"PASS" if not unowned and not multiply else "FAIL",
        "admission_or_semantic_completeness":"NOT_PROVEN",
    }
    return routing, receipt_schema, report


def _concrete_missing_paths(spec_pattern: str, receipt: Any) -> list[str]:
    expanded = expand_finite_pattern(spec_pattern)
    output = []
    # Finite expansion uses item index 0; replace the first/each index capture by
    # every actual matching parent node through regex matching of the parent.
    leaf_parts = spec_pattern.split("/")
    parent_pattern = "/".join(leaf_parts[:-1])
    last = CAPTURE_SEGMENT_RE.fullmatch(leaf_parts[-1])
    fields = last.group(2).split("|") if last and last.group(2) != "*" else [leaf_parts[-1]]
    for parent_path, parent in all_nodes(receipt):
        if not isinstance(parent, Mapping) or match_pattern(parent_pattern, parent_path) is None:
            continue
        for field in fields:
            path = parent_path + "/" + _escape(field)
            if field not in parent:
                output.append(path)
    return sorted(output)


def pseudo_events_for_receipt(routing: Mapping[str, Any], receipt_schema: Mapping[str, Any], receipt: Any) -> list[dict[str, Any]]:
    events = []
    row_by_id = {row["id"]:row for row in routing["rows"]}
    nodes = list(all_nodes(receipt))
    for spec in routing["pseudo_event_specs"]:
        row = row_by_id[spec["owner_route_id"]]
        if spec["event_kind"] == "ABSENCE":
            candidates = [(path,None) for path in _concrete_missing_paths(spec["path_pattern"],receipt)]
        else:
            candidates = [(path,value) for path,value in nodes if match_pattern(spec["path_pattern"],path) is not None]
        for path,value in candidates:
            atom = {"UNION_BRANCH":"BRANCH_STATE","CONTAINER":"CONTAINER","CLOSED_RECORD":"CLOSED_RECORD_TVE2","ABSENCE":"MISSING2"}[spec["event_kind"]]
            present = spec["event_kind"] != "ABSENCE"
            if spec["event_kind"] == "CONTAINER" and not isinstance(value,list):
                raise CoverageError(f"{spec['id']} concrete container is not array")
            if spec["event_kind"] == "CLOSED_RECORD":
                validator = jsonschema.Draft202012Validator({"$ref":spec["schema_def"],"$defs":receipt_schema["$defs"]})
                if not validator.is_valid(value):
                    raise CoverageError(f"{spec['id']} concrete record fails closed projection")
            active = [conjunction for conjunction in spec["variant_expression"]["any_of"] if all(runtime_variant_active(routing,name,path,receipt,atom,present=present) for name in conjunction)]
            if len(active) != 1:
                raise CoverageError(f"{spec['id']} selector active alternatives={len(active)} at {path}")
            owners = matching_rows_runtime(routing,path,atom,receipt,spec["event_kind"],present=present)
            if [owner["id"] for owner in owners] != [row["id"]]:
                raise CoverageError(f"{spec['id']} runtime pseudo owner mismatch at {path}")
            captures = match_pattern(row["path_pattern"],path) or {}
            contexts = sorted({resolve_context(row,captures,channel["context"]).hex() for channel in row["channels"] or [{"context":"ROW"}]})
            events.append({"spec_id":spec["id"],"route_id":row["id"],"event_kind":spec["event_kind"],"path":path,"active_variant":active[0],"contexts":contexts})
    return events


def classify_receipt(routing: Mapping[str, Any], receipt_schema: Mapping[str, Any], receipt: Any) -> dict[str, Any]:
    jsonschema.Draft202012Validator(receipt_schema).validate(receipt)
    unknown=[];duplicate=[];classified=[];identity_counts={}
    for path,value,atom in scalar_leaves(receipt):
        matches=matching_rows_runtime(routing,path,atom,receipt)
        if not matches: unknown.append({"path":path,"input_atom":atom})
        elif len(matches)>1: duplicate.append({"path":path,"input_atom":atom,"rows":[row["id"] for row in matches]})
        else:
            row=matches[0];captures=match_pattern(row["path_pattern"],path) or {}
            contexts=[]
            for channel in row["channels"]:
                ctx=resolve_context(row,captures,channel["context"]).hex();contexts.append(ctx)
                if row["cardinality"]=="SCALAR_ONE":
                    key=(row["family"],ctx,channel["channel"])
                    identity_counts[key]=identity_counts.get(key,0)+1
            if atom=="SIGNED_DECIMAL_INT_STRING": normalize_signed_decimal(value)
            classified.append({"path":path,"input_atom":atom,"row":row["id"],"contexts":sorted(set(contexts))})
    scalar_identity_collisions=[{"identity":key,"count":count} for key,count in identity_counts.items() if count!=1]
    pseudo=pseudo_events_for_receipt(routing,receipt_schema,receipt)
    status="ZERO_UNCLASSIFIED" if not unknown and not duplicate and not scalar_identity_collisions else "STRUCTURAL_ROUTING_FAILURE"
    return {"scalar_leaf_count":len(classified)+len(unknown)+len(duplicate),"classified":classified,"unknown":unknown,"multiply_owned":duplicate,"scalar_one_identity_collisions":scalar_identity_collisions,"pseudo_event_count":len(pseudo),"pseudo_events":pseudo,"status":status,"admission_or_semantic_completeness":"NOT_PROVEN"}


def main(argv: Sequence[str] | None = None) -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--routing",type=Path,default=DEFAULT_ROUTING)
    parser.add_argument("--routing-schema",type=Path,default=DEFAULT_ROUTING_SCHEMA)
    parser.add_argument("--receipt-schema",type=Path,default=DEFAULT_RECEIPT_SCHEMA)
    parser.add_argument("--primitives",type=Path,default=DEFAULT_PRIMITIVES)
    parser.add_argument("--receipt",type=Path,action="append",default=[])
    args=parser.parse_args(argv)
    routing,receipt_schema,report=verify_candidate_bytes(args.routing.read_bytes(),args.routing_schema.read_bytes(),args.receipt_schema.read_bytes(),args.primitives.read_bytes())
    report["receipts"]=[]
    for path in args.receipt:
        result=classify_receipt(routing,receipt_schema,load_json(path));report["receipts"].append({"path":str(path),**result})
    print(json.dumps(report,ensure_ascii=False,sort_keys=True,separators=(",",":")))
    return 0 if report["structural_ownership"]=="PASS" and all(item["status"]=="ZERO_UNCLASSIFIED" for item in report["receipts"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
