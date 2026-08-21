# Model-input layout study V2 post-fix audit

Status: `IMPLEMENTER POST-FIX AUDIT / READY FOR INDEPENDENT RE-REVIEW / NOT ACCEPTANCE`

This audit records how `INDEPENDENT-REDTEAM.md` changed the implementation. It
does not overrule that review and does not promote this study to MODEL-INPUT
canon. Power remains `UNKNOWN`; C01's phase boundary is unresolved; G and formal
3200 remain `NOT_RUN`.

## Red-team findings converted to regressions

| Finding | V2 repair | Regression evidence |
|---|---|---|
| 2,715 mixed routing keys were presented as a predictor universe | Reports 2,715 mixed keys separately from 2,531 primitives-emittable representative templates: 2,312 numeric + 213 category-before-value + 6 ngram-family | `test_routing_mixed_keys_are_not_predictor_templates` |
| All 47 wildcard rows were called ordered/unbounded | Classifies 11 ORDERED-context retained, 35 BAG-item dropped, and 1 container-item dropped; makes no global unbounded claim | `test_wildcards_distinguish_ordered_bag_and_container` |
| “Open” was guessed from transform names | Domain status now comes only from input/event grammar: closed bool/null/MISSING/branch, non-enumerable SHA256, otherwise explicit UNKNOWN pending schema-domain proof | `test_category_domain_is_grammar_based_and_unknown_is_preserved` |
| A seventh unreachable ngram family block was allocated | Derives reachable ngram families from routing; uses six blocks and 24,576 columns | `test_only_six_ngram_family_blocks_are_allocated` |
| Receipt set was not bound to public F lineage | Requires plan/closed/disk slot-set equality, `CLOSED`, 12 complete slots, no unexpected entries, matching challenge and collector hashes | `test_public_plan_closed_and_disk_lineage_is_bound` |
| SHA-alternating receipt-content split ignored public mechanism strata | Uses a domain-separated opaque-slot ranking within each public challenge, 2 reference/2 probe per stratum; explicitly records that it was not precommitted and is exploratory only | `test_novelty_is_stratified_singleton_heavy_and_insufficient` |
| 58.2% novelty hid singleton dominance | Reports 408/586 all-category singletons; under V2 split, all 204 probe-only identities are singletons; verdict is insufficient evidence, not hash justification | same regression |
| E5 incorrectly claimed equal sparse shape | Fixture now reports three raw nonzeros versus four robust-transformed nonzeros and rejects zero-compressed equivalence | `test_e5_correctly_changes_zero_compressed_nnz` |
| Exact dictionary used all twelve receipts and “hybrid” duplicated hash-all | Freezes numeric/exact/OTHER dictionaries from six reference receipts only. Probe never expands them. Compares exact-only, exact+OTHER, hash-only, and exact-known plus OOV-only hash | `test_dictionary_is_reference_frozen_and_layouts_are_distinct` |
| Signed-hash deletion condition was circular | Adds an eight-input Boolean gate; deletion occurs only when every input is true. Current result is `UNKNOWN_DO_NOT_DELETE` | `test_signed_hash_deletion_gate_is_executable_and_currently_unknown` |

## Rebuilt measurements

The all-twelve union is retained only as retrospective arithmetic:

- 1,604 observed numeric identities;
- 586 observed exact categories;
- six reachable direct-ngram families, 24,576 fixed columns;
- 26,766 snapshot columns, 62,251 structural nnz;
- CSR payload 747,064 bytes; dense payload 2,569,536 bytes.

The grammar-domain audit leaves 507 observed category identities UNKNOWN, marks
51 as SHA256 non-enumerable, and proves only the remaining 28 closed. The old
global “open exact” interpretation is removed.

The public-mechanism-stratified reference dictionary contains 1,604 numeric
identities, 382 exact categories, and 106 structural OTHER templates. Probe has
204 exact OOV categories, no numeric structural drift, and no category-template
drift. At width 4,096:

| Layout | Columns | nnz | CSR bytes |
|---|---:|---:|---:|
| exact-only | 26,562 | 62,047 | 744,616 |
| exact + OTHER | 26,668 | 62,107 | 745,336 |
| hash-only presence | 54,852 | 62,234 | 746,860 |
| hash-only signed | 54,852 | 62,218 | 746,668 |
| hybrid OOV presence | 55,234 | 62,250 | 747,052 |
| hybrid OOV signed | 55,234 | 62,249 | 747,040 |

These numbers distinguish layout mechanics; they do not rank detector power.

## Deletion gate status

The gate requires: precommitted split, independent probe excluded from dictionary,
closed C01 phase boundary, passed bound resource ceiling, zero structural drift,
closed domain or validated novelty alternative, frozen removal fixtures passing
on independent probe, and zero required distinguishing pairs lost by exact/OTHER.

Only structural drift is zero in this exploratory split. The other seven inputs
are false or unknown. Current decision is therefore `UNKNOWN_DO_NOT_DELETE`, not
“retain forever” and not “delete now.”

## Verification and exact bytes

- `layout_study.py --check RESULTS.candidate.json`: `RESULT_MATCH`.
- V2 regression suite: 12/12 pass.
- `layout_study.py` SHA-256: `9915c77219ebedae7ad15bfdc3c8b456ae0a1d5a12ce3b174fefe00f642cecac`.
- `RESULTS.candidate.json` SHA-256: `5129149124c76562a780f96267b5f7f2ef332a379a189e48e13a5af35aa4018a`.
- `README.md` SHA-256: `933d5203233352feeada2472e50f198d8e66f80b4447d3bb99dfc65704b0f9a6`.
- `tests/test_layout_study.py` SHA-256: `8025c3af6457fbe919e220f397ef01a99c22ff7f55f177148efb05af00f8465c`.
- red-team input SHA-256: `fb4466d5d9415dda8c023097469ddd4ed3ca97fdcd18483a72e30c84e4c49064`.

The rebuilt result additionally binds public plan SHA-256
`09a8fc8a57906bc3d4182af7f3b1f08cccf5c36b2a6c6a07c2ccf1a9033acf72`
and closed SHA-256
`26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e`.
This is public lineage verification, not V1.1 admission or formal qualification.
