# Wave025 model-input layout study V4

Status: `SCOPED RETROSPECTIVE SHAPE ONLY / NOT CANON / POWER UNKNOWN / NO G / NO FORMAL 3200`

This is a narrow representation and storage study, not `MODEL-INPUT` canon. V2
accepts the independent red-team rejection of V1's layout decision and repairs
the measurable boundaries without preserving the old conclusion.

## Inputs and awareness boundary

The executable reads the current routing candidate and schema, V1 receipt schema,
V2S primitives candidate, public F `public-plan.json`, public F `closed.json`, and
the twelve public `collector-features.json` receipts. It does not read private
registries, `runner-private-state.json`, `reveal.json`, private role assignments,
or outcome labels. It does read public-plan challenge assignments to stratify the
three public mechanisms. The exact boundary is therefore
`PRIVATE_ROLE_AND_OUTCOME_BLIND__PUBLIC_TREATMENT_AWARE`.

The public lineage check requires plan, closed manifest, disk, and receipt slot
sets to match exactly; all twelve `collector-features.json` hashes must match the
closed manifest. Multiplicity is checked before any dict/set projection: both raw
lists must contain exactly twelve unique rows and twelve unique slot IDs, with
declared/list/disk/receipt cardinalities equal and no unexpected or missing entry.
Duplicate-append and duplicate-ID attacks fail before de-duplication.

The verifier binds the current public-plan and closed hashes as exploratory
expected inputs. This detects a plan/closed common rewrite unless the study is
also rewritten. It is not a formal controller seal: a writer able to modify the
study can co-rewrite the expected hashes. Formal admission still needs an expected
preimage in an external controller or permission domain. The current check only
establishes observed F snapshot lineage, not V1.1 semantic admission.

The exploratory reference/probe split is stratified by the three public challenge
mechanisms. Within each four-slot stratum it ranks opaque slot IDs by a fixed
domain-separated hash and selects two reference/two probe. It was not precommitted
before F and therefore cannot support a novelty or power decision.

C01 and its real process-level phase boundary remain an external unresolved
dependency. The rejected C01 mini-suite is not used as ground truth.

## Two counts that must not be merged

The routing candidate has 109 rows and a 641-entry route/channel/stat matrix.

- **2,715** is the routing study's mixed index-zero representative-key count. It
  retains MISSING `expected_stat` distinctions and route-aware ngram contexts. It
  is not a predictor universe.
- **2,531** is the primitives-emittable index-zero representative-template count:
  2,312 numeric context/stat templates, 213 category context/channel templates
  before value expansion, and six direct-ngram family templates. MISSING collapses
  without `expected_stat`, and direct ngram collapses to family/bucket.

Neither number is a final column universe: category values and nonzero ordered
indices are not fully expanded.

The 47 wildcard-path rows are also heterogeneous: 11 retain the item index in an
ORDERED context, 35 drop it under BAG semantics, and one drops it for container
count. V2 does not call all 47 ordered or mathematically unbounded.

## Category-domain honesty

V2 no longer infers open domains from transform names. It classifies only what
primitive/routing grammar proves:

- JSON bool, JSON null, reserved MISSING2, and routing branch variants are closed;
- SHA256 grammar is non-enumerable for practical static exact allocation;
- UTF-8 and closed-record categories remain
  `UNKNOWN_NEEDS_SCHEMA_DOMAIN_PROOF` until a per-route schema-domain proof exists.

Among the 586 observed exact category identities, 51 are on the SHA256 grammar,
507 remain domain-unknown, and 28 are on proved-closed categories. This evidence
cannot justify a global “open-category” count.

## Retrospective F shape

Only F02--F07 have reachable direct-ngram routes, so the fixed direct-ngram block
is `6 * 4096 = 24,576` columns. The all-twelve retrospective snapshot contains:

- 1,604 contextual numeric identities;
- 586 exact category identities;
- 4,887 occupied direct-ngram buckets;
- 26,766 logical columns and 62,251 occupied structural cells;
- 747,064 bytes by the standard float64/uint32 CSR payload formula;
- 2,569,536 bytes dense;
- a 39,264-byte observed exact-category manifest.

Those figures are post-observation shape arithmetic. They are explicitly not a
calibration-frozen model allocation.

The twelve receipts contain 408 singleton category identities. Under the
public-mechanism-stratified exploratory split, all 204 probe-only identities are
singletons. The only responsible verdict is
`CURRENT_12_INSUFFICIENT_FOR_NOVELTY_OR_HASH_VALUE_DECISION`: the data cannot
separate transferable novelty from per-run identity noise.

## Real reference-frozen layout comparison

V2 freezes dictionaries from the six reference receipts, then applies them to
the six probe receipts without expansion. The reference dictionary contains
1,604 numeric identities, 382 exact categories, and 106 category structural
templates for `OTHER`. Probe application finds 204 exact OOV categories and zero
new numeric/category structural templates in this exploratory split.

At 4,096 hash buckets per family:

| Layout | Category behavior | Columns | Total nnz | CSR bytes |
|---|---|---:|---:|---:|
| exact-only | known exact; drop/log OOV | 26,562 | 62,047 | 744,616 |
| exact + OTHER | known exact; one OTHER per known template | 26,668 | 62,107 | 745,336 |
| hash-only presence | hash every category | 54,852 | 62,234 | 746,860 |
| hash-only signed | hash every category | 54,852 | 62,218 | 746,668 |
| hybrid OOV presence | exact known; hash only OOV | 55,234 | 62,250 | 747,052 |
| hybrid OOV signed | exact known; hash only OOV | 55,234 | 62,249 | 747,040 |

At 8,192 and 16,384 buckets, hash-only widths are 83,524 and 140,868; hybrid
widths are 83,906 and 141,250. Exact-only and exact+OTHER widths do not change.
This is now a genuine reference-frozen exact/OOV comparison, not V1's
all-twelve exact union plus duplicate hash-all layout.

## E1--E5 scoped results

1. **E1:** route-only merges two exact values. It cannot be the sole exact view.
2. **E2:** two exact values collide with opposite signs at width 4,096; signed
   sum is zero while independent presence is one.
3. **E3:** a numeric value equal to center and an absent value both map to value
   zero; the missing bit is necessary.
4. **E4:** pure row-wise family L2 without retained norm maps single-axis values
   1 and 10 to the same unit value. This does not show normalization is generally
   harmful when norm is retained.
5. **E5:** raw `[0,1,2,1000]` has three nonzeros, while the frozen robust transform
   has four. Logical width is unchanged, but zero-compressed nnz is not. Exact
   rational invertibility does not imply learner or CSR equivalence.

## Receipt parser and external deletion authority

This scoped retrospective study has no authority to delete signed hash or any
feature family. Its receipt parser is diagnostic only. It no longer accepts eight
caller-supplied booleans, and it can check that a local bundle has unique IDs,
exact raw-byte SHA-256 values, required scopes/statuses, closed schemas, and no
missing or unexpected documents. Those checks establish only that a local
self-assertion is structurally well formed; they do not establish its truth or
issuer authority.

The eight required receipt scopes cover:

1. split precommitted before receipts;
2. independent probe excluded from dictionary construction;
3. C01 phase boundary closed;
4. bound resource ceiling passed;
5. structural drift is zero;
6. every relevant route is closed-domain or a validated novelty alternative exists;
7. a frozen removal-fixture set passes on the independent probe;
8. exact/OTHER loses zero required distinguishing pairs against hash fallback.

This study issues none of these receipts and cannot turn any locally supplied
bundle into deletion authority. Missing, malformed, incomplete, or failed local
evidence returns `UNKNOWN_DO_NOT_DELETE`. Even eight locally constructed,
byte-bound `SATISFIED` receipts return `EXTERNAL_AUTHORITY_REQUIRED`, never a
delete decision.

Any future hash/family deletion must be decided outside this study by an external
controller or explicit user decision that binds a trusted issuer authority, the
exact frozen subject preimage, and requirement-specific proof. This directory
contains no fabricated success path and does not create its own authority.

## Rebuild

```bash
python3 layout_study.py --check RESULTS.candidate.json
python3 -m unittest discover -s tests -v
```

`RESULTS.candidate.json` is canonical compact UTF-8 JSON plus one LF. Byte counts
cover CSR payload (`float64 data + uint32 indices + uint32 indptr`) and exclude
container/library overhead. No classifier is fitted, power remains `UNKNOWN`,
and G/formal 3200 remain `NOT_RUN`.
