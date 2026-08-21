# Model-input layout study V4 fourth-fix audit

Status: `IMPLEMENTER FOURTH-FIX AUDIT / READY FOR INDEPENDENT NARROW REVIEW / NOT ACCEPTANCE`

This audit answers the authorization defect demonstrated by
`FINAL-THIRD-FIX-INDEPENDENT-ACCEPTANCE.md`. It does not alter or promote the
previously accepted scoped retrospective shape arithmetic. Power remains
`UNKNOWN`; C01 remains an external unresolved dependency; G and formal 3200
remain `NOT_RUN`.

## Failure accepted

V3 correctly bound local receipt bytes to hashes and closed schemas, but it still
treated a structurally valid local assertion as authority. The independent
reviewer constructed eight caller-made receipts with:

- unique IDs;
- correct local raw-byte SHA-256 values;
- the parser's exact scope strings;
- self-declared `SATISFIED` statuses;
- one arbitrary all-zero `subject_sha256`.

V3 returned `DELETE_SIGNED_HASH`. That proved only byte integrity of the caller's
own assertion, not issuer authority, subject identity, or requirement-specific
proof. The prior gate was therefore not a valid future deletion authority.

## V4 authority repair

The function is now named `signed_hash_receipt_diagnostic`. It retains the local
bundle parser so malformed schemas, IDs, hashes, scopes, statuses, and document
sets remain diagnosable, but it has no deletion-capable return path.

For any local input, its only possible decisions are:

- `UNKNOWN_DO_NOT_DELETE` when the local bundle is missing, malformed,
  incomplete, or contains a failed/unknown requirement;
- `EXTERNAL_AUTHORITY_REQUIRED` when all eight local receipts are structurally
  well formed and self-declare `SATISFIED`.

The implementation and frozen result state explicitly:

- `study_issues_receipts = false`;
- `study_can_authorize_deletion = false`;
- `issuer_authority_verified = false`;
- `subject_preimage_authority_verified = false`;
- `requirement_specific_proof_verified = false`.

The prior `DELETE_SIGNED_HASH` decision symbol is absent from the V4
implementation, result, README, and tests. A local bundle can be parsed, but it
cannot grant authority to this study.

Any future hash or family deletion must happen outside this scoped retrospective
study. An external controller or explicit user decision must bind all of:

1. trusted issuer authority that the caller and this study cannot self-assign;
2. the exact frozen subject preimage, not merely a syntactically valid digest;
3. requirement-specific proof and verifier result for every deletion condition.

This directory does not create that authority, issue a trusted receipt, or
contain a fabricated authorization-success path.

## Regression for the independent counterexample

`test_caller_made_eight_receipts_never_authorize_deletion` reconstructs the
reviewer's attack in memory. All eight self-made receipts pass the structural
parser (`validation_errors=[]`, `local_bundle_well_formed=true`), but the result
is exactly `EXTERNAL_AUTHORITY_REQUIRED`; all three authority/proof fields remain
false and `study_can_authorize_deletion` remains false.

The fixture is an adversarial rejection test, not a fabricated successful
authority path.

## Awareness wording repair

The module docstring no longer says it never reads an unspecified
“assignment.” It now states the exact boundary: the study does not read private
role or outcome assignments, but does read public-plan challenge treatments for
stratification. This matches:

`PRIVATE_ROLE_AND_OUTCOME_BLIND__PUBLIC_TREATMENT_AWARE`.

## Frozen V4 state

- result schema: `wave025-model-input-layout-study-result-v4`;
- status:
  `CANDIDATE_STUDY_V4__SCOPED_RETROSPECTIVE_SHAPE_ONLY__POWER_UNKNOWN__NO_G__NO_3200`;
- current receipts supplied: zero;
- current decision: `UNKNOWN_DO_NOT_DELETE` with
  `MISSING_EVIDENCE_BUNDLE`;
- power: `UNKNOWN`;
- C01: `EXTERNAL_UNRESOLVED_DEPENDENCY`;
- G: `NOT_RUN`;
- formal 3200: `NOT_RUN`.

No model layout, hash width, normalization, learner, power, formal lineage, or
feature deletion has been selected or authorized.

## Verification and exact bytes

- `layout_study.py --check RESULTS.candidate.json`: `RESULT_MATCH`.
- V4 regression suite: 18/18 pass.
- Python compile check: pass.
- `layout_study.py` SHA-256:
  `2ca6d909848d9f3daf50faf34a2813fecca6f5591cb6594114d9da53e7181237`.
- `RESULTS.candidate.json` SHA-256:
  `88330122d723efeff8253f5039d63e158e8d1d76b599fd9397f02299950885c0`.
- `README.md` SHA-256:
  `0c7ef5ab2b1fcb4427935207f22886e54cf270f96f20615193644dbfd34d261a`.
- `tests/test_layout_study.py` SHA-256:
  `8ccf46fa08ad2f5bcb43b6d213220abd7e52853eedba988da641e5951e58425d`.
- independent review input `FINAL-THIRD-FIX-INDEPENDENT-ACCEPTANCE.md`
  SHA-256:
  `1870c535c9ea76d3274092d2db16bec00bd55d2541f0ea90a58be628ea8fe4c3`.

These are implementer-produced checks and handoff anchors. They do not constitute
independent acceptance.
