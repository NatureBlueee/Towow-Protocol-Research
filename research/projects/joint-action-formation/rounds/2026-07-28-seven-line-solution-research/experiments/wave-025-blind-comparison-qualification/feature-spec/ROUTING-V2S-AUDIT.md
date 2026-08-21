# Wave025 V2S executable structural routing audit

Status: `EXECUTABLE STRUCTURAL CANDIDATE / NOT ADOPTED / SEMANTIC AND FORMAL USE BLOCKED`

Date: 2026-08-01

This audit supersedes the earlier self-audit claims but does not alter or erase
`ROUTING-V2S-INDEPENDENT-REDTEAM.md` or
`ROUTING-V2S-POST-FIX-INDEPENDENT-ACCEPTANCE.md`. Those reports remain the
independent records of the original six blockers and the four residual hardening
failures. This document records the subsequently repaired candidate and local
regression evidence. It is not a replacement independent acceptance.

Audited artifacts:

- `FEATURE-ROUTING-V2S.candidate.json`
- `FEATURE-ROUTING-V2S.candidate.schema.json`
- `routing_v2s_coverage.py`
- `tests/test_routing_v2s_coverage.py`
- `COLLECTOR-RECEIPT-V1.candidate.schema.json`
- `V2S-PRIMITIVES.candidate.json`
- twelve raw F `collector-features.json` receipts

The historic reference extractor, evaluator engine, old feature specification and F
derived model output were not used as normative routing answers.

## Result and exact boundary

The repaired package is an executable candidate for structural routing review. It
now provides machine-checkable context capture, active branch selection, selected
pseudo-event ownership, schema-legal signed-zero routing, missing-channel identity,
and actual-byte dependency binding.

Current structural inventory:

- 109 rows: 98 `INCLUDE`, 11 `EXCLUDE`;
- full family identifiers throughout: F01 9, F02 7, F03 21, F04 16, F05 31,
  F06 19, F07 6;
- 85 scalar, 9 union-branch, 7 container, 5 closed-record and 3 absence rows;
- 64 `SCALAR_ONE`, 36 `BAG_MULTISET`, 7 `CONTAINER_COUNT`, 2
  `ORDERED_SERIES` rows;
- 226 declared channel/transform emissions;
- 23 lexical routes, all with same-view full-byte-length and truncation companions;
- all six SHA rows restricted by an exact `(channel, transform)` allowlist;
- candidate state remains `NOT_ADOPTED__NOT_FORMAL_CANON`.

This result does not mean that a feature provider exists, that two clean-room
providers agree byte-for-byte, that the receipt is semantically admissible, that
C01--C05 model columns are fixed, or that G/power has been demonstrated.

## Repair 1: named captures produce exact CTX2 bytes

Path patterns use only two named capture forms:

- `{index:*}` for a canonical array index (`0|[1-9][0-9]*`);
- `{field:a|b}` for a finite exact alternation.

Context templates reference captures explicitly, for example `KEY:{field}` or
`ORDERED:{index}`. The checker independently derives required capture references:
every finite alternation must occur exactly once as `KEY`, and every non-item
wildcard must occur exactly once as `ORDERED`. Unordered `item*` captures on BAG or
container rows must instead have a `BAG_ITEM` marker and must not enter CTX2. Thus
deleting or literalizing a required reference fails statically without waiting for
an F runtime collision. The checker also rejects unnamed, malformed, duplicate and
unbound captures, non-canonical indices and legacy `$FIELD`-style literals. It then
encodes the concrete context with the repaired primitives' CTX2 framing and tags:

- `KEY` = `0x01 || frame32(UTF8(name))`;
- `ORDERED` = `0x02 || u32be(index)`;
- `BAG_ITEM` = `0x03`;
- `DERIVED` = `0x04 || frame32(ASCII(label))`.

The test suite proves concrete separation for `identity.pid` versus `identity.ppid`
and all five directory-tree names. `BAG`, `LEXICAL_BAG` and `PARENT` now remove every
`ORDERED` segment. For R032 and R093, series item 0/1 therefore have different
`ORDERED` CTX2 but the same `PARENT` CTX2; R093's two captured series names still have
different parent contexts. Cmdline indices likewise differ in the ordered view but
are deliberately removed in unordered views. Across the twelve F receipts, every
emitted `SCALAR_ONE` identity occurs exactly once.

## Repair 2: selected pseudo events have reachable, bijective owners

The candidate contains a separate expected pseudo-event manifest whose 24 specs are
bijective with all non-scalar owner rows:

| event | expected specs |
|---|---:|
| union branch | 9 |
| container | 7 |
| closed record | 5 |
| optional absence | 3 |

The checker derives schema nodes independently and verifies:

- every selected branch path reaches a `oneOf` node and selector cardinality equals
  branch cardinality;
- every selected container reaches an array node;
- every record projection names an existing, closed `$defs` definition which is
  reachable at the declared path;
- every absence path corresponds to a schema-optional leaf;
- every pseudo spec and owner row agree on event, path and variant expression;
- no pseudo row is missing a spec and no spec shares an owner.

The expected universe is not authorized by the owner rows or specs themselves. A
separately reviewed receipt-schema pseudo-selection registry freezes a canonical
24-entry projection over event, path, variant expression, selector binding and
optional record definition. Its SHA-256 is
`67108f341f517ec93be9c7d79d1b4cc1ec3235bbf6e6b98a7c5d69b070c9f3cd`, enforced
both by the release schema and by an independent checker constant. Spec IDs and owner
row IDs are deliberately excluded from this projection. Consequently, synchronously
adding a row, matching spec and rebuilt matrix cannot enlarge the expected universe,
even if the caller also supplies a loosened routing schema and recomputed attacker
digest.

For each pseudo spec, the exact referenced subset of `variant_registry` is also bound
by SHA-256. Runtime generation requires exactly one active DNF selector alternative
and exactly one matching owner. Deleting, duplicating or misrouting R053, changing a
selector definition, or naming a missing/open record definition now fails closed.

## Repair 3: signed zero is one explicit integer route

The receipt schema admits `-0` for tree `mtime_ns` and `ctime_ns`. Static and runtime
classification now use `SIGNED_DECIMAL_INT_STRING`; R109 applies
`NORMALIZE_SIGNED_ZERO_THEN_PARSE_DECIMAL_INTEGER`. Both `0` and `-0` normalize to
primitive input `0`, while other canonical signed decimals remain unchanged.

A real F receipt mutated only at a tree `mtime_ns` to `"-0"` remains schema-valid and
classifies through R109 with zero unknown paths. This closes the earlier schema/runtime
grammar split without claiming semantic admission for arbitrary timestamps.

## Repair 4: union traces and selectors affect ownership

The 454 schema manifest entries retain their union trace. Static ownership evaluates
each row's DNF `variant_expression` against a 35-entry registry containing explicit
scope and trace rules. Runtime ownership evaluates the corresponding executable
selector against the concrete receipt. Unknown labels fail closed.

For example, `/hostname/os_hostname/value` as `UTF8_STRING` is owned by R019 under
`oneOf[0]`, has no UTF8 owner under `oneOf[1]`, and its `JSON_NULL` form under
`oneOf[1]` is owned by R020. Thus trace is no longer report-only metadata.

## Repair 5: absence declares the exact channel it replaces

Each `MISSING` emission includes `expected_channel` and the complete ordered
`expected_stats` taken from `channel_stat_registry`:

- R068: exact category, string shape, lexical length, truncation and n-gram;
- R070: numeric scalar and integer residues;
- R072: four-ID item, four-ID series and integer residues.

The captured field name is part of CTX2, so `name/state`, `ppid/threads` and `uid/gid`
do not collapse. A derived 641-entry channel/stat matrix binds family, route, channel,
stat, expected channel/stat and cardinality. Missing metadata, stat disagreement and
matrix drift fail closed.

## Repair 6: verification follows the actual bytes passed

`verify_candidate_bytes()` receives raw bytes for the routing candidate, routing
schema, receipt schema and primitives candidate. It hashes and parses the same
receipt/primitives bytes; it no longer hashes module-default path A while traversing
caller-supplied object B.

Current exact dependency bindings are:

- receipt schema SHA-256
  `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209`,
  27,874 bytes;
- repaired primitives SHA-256
  `2786e83d36a4d709915c84b57994b351dc29100a104413b6832c508fa197226b`,
  12,178 bytes.

The routing candidate itself must be canonical compact UTF-8 JSON plus exactly one
LF. The routing schema is now released in the same canonical form, and the verifier
rejects non-canonical routing-schema bytes. The receipt schema remains unchanged and
continues to be bound by its actual 27,874 bytes; this routing repair did not silently
canonicalize or rebind that separate artifact.

## Repaired BAG exactly-one-input-channel gate

For BAG numeric output, the bound primitives require exactly one input channel for
each `(family, concrete CTX2, base_stat)`. The verifier now uses exactly that key and
stores `(route_id, input_channel)` as its owner set; the input channel is no longer
part of the collision key. Adding `ALT_NUMERIC/value` beside R109's
`NUMERIC_SCALAR/value`, then legitimately rebuilding the channel/stat matrix, fails
with `BAG exactly-one-input-channel collision`.

## Structural proof and runtime observations

Static checker output:

- 454 reachable `(path pattern, input atom, union trace)` scalar/absence variants;
- 371 unique `(path pattern, input atom, absence)` shapes;
- zero unowned and zero multiply-owned scalar/absence variants;
- pseudo counts 9/7/5/3, all reachable and bijective;
- 641 bound channel/stat entries;
- 1,140 enumerated `(family, CTX2, base_stat)` BAG numeric identities, each with
  exactly one `(row, input channel)` owner;
- `structural_ownership=PASS`;
- `admission_or_semantic_completeness=NOT_PROVEN`.

All twelve raw F receipts validate against the receipt schema and pass the executable
runtime router:

| receipts | scalar leaves | pseudo events | unknown | multiply owned | scalar-one identity collisions |
|---:|---:|---:|---:|---:|---:|
| 8 | 528 | 71 | 0 | 0 | 0 |
| 4 | 547 | 74 | 0 | 0 | 0 |

These receipts support current-F structural execution only. They do not estimate
coverage frequency outside F, semantic validity, causal specificity or predictive
power.

## Regression attacks

The 56 targeted tests include the twelve separate F runtime cases and executable
counterexamples for:

- literal/unbound/duplicate captures, required-capture deletion/literalization,
  identity collapse and non-canonical indices;
- R032/R093 ordered item versus parent-series CTX2 behavior;
- missing, duplicate, unreachable or misrouted pseudo owners, plus synchronized
  row/spec/matrix/digest self-authorization;
- mutated selector definitions, unknown union labels and trace/atom disagreement;
- missing or open record definitions;
- schema-valid `-0`;
- omitted or inconsistent missing expected-channel metadata;
- alternate receipt/primitives bytes passed to the verifier;
- SHA prefix-channel bypass;
- recursive wildcard on an included route;
- channel/stat matrix drift, duplicate BAG owner and second-input-channel collision;
- non-canonical candidate or routing-schema bytes;
- schema-valid but semantically backwards timing.

The complete feature-spec suite also passes: `125 passed`.

## Deliberately unresolved blockers

### Semantic admission

The receipt schema is a structural and union enumerator, not an admission contract.
Duplicate raw keys/logical records, producer ordering, truncation truth and
observability, timing direction, canary provenance/hash/length consistency, producer
caps, receipt completeness and cross-field evidence consistency still require the
V1.1 semantic admission decision and validator. A schema-valid backwards wall clock
therefore remains structurally routable while explicitly `NOT_PROVEN` for admission.

### Independent provider conformance

This candidate binds repaired primitive definitions; it does not implement them or
prove that independent feature providers produce identical bytes. No independent
clean-room provider result was run or accepted in this repair round.

### Model layout, G and empirical power

C01--C05 column eligibility/layout, missing-column universe, deterministic math,
model input bytes, G, D0/D1 sensitivity, T specificity, causal counterexamples,
power and runtime cost remain blocked. Structural routing cannot promote any of
these claims.

## Reproduction

From `feature-spec/`:

```sh
python3 routing_v2s_coverage.py
PYTHONPYCACHEPREFIX=/tmp/wave025-routing-pycache \
  python3 -m pytest -q tests/test_routing_v2s_coverage.py
PYTHONPYCACHEPREFIX=/tmp/wave025-feature-spec-pycache \
  python3 -m pytest -q tests
```

Expected current results are `structural_ownership=PASS`, 56 targeted tests passed,
and 125 complete feature-spec tests passed.

## Decision

`EXECUTABLE_STRUCTURAL_ROUTING_CANDIDATE_READY_FOR_REVIEW`.

This is a repaired local candidate responding to the post-fix independent rejection;
it is not a self-issued independent acceptance and not adoption. The original
independent reviewer must rerun its acceptance attacks before the routing-specific
decision can change. Even a later routing acceptance would not close semantic
admission, independent provider conformance, model layout, G or power.
