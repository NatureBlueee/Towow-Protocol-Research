# Model-input layout study V3 third-fix audit

Status: `IMPLEMENTER THIRD-FIX AUDIT / READY FOR SAME REVIEWER / NOT INDEPENDENT ACCEPTANCE`

This audit answers only the two remaining gate defects and the awareness-boundary
wording identified in `FINAL-INDEPENDENT-ACCEPTANCE.md`. It does not reopen or
upgrade the accepted retrospective shape arithmetic. It does not promote a model
layout, prove detector power, close C01, start G, or start formal 3200.

Current scientific state remains:

- shape result: `SCOPED_RETROSPECTIVE_SHAPE_ONLY`;
- power: `UNKNOWN`;
- C01 phase boundary: `EXTERNAL_UNRESOLVED_DEPENDENCY`;
- G: `NOT_RUN`;
- formal 3200: `NOT_RUN`.

## 1. Public-lineage multiplicity and common-rewrite repair

`verify_f_lineage_documents` now validates the raw plan and closed lists before
any dict or set projection:

1. both raw lists must contain exactly twelve rows;
2. every row must be an object;
3. exact duplicate rows are rejected;
4. empty IDs and duplicate plan or closed slot IDs are rejected;
5. receipt rows and disk slot directories must each be exactly twelve and unique;
6. unexpected disk entries are rejected;
7. declared, list, disk, and receipt multiplicities must agree;
8. only after those checks may slot sets and per-slot challenge/hash relations be
   compared.

The executable additionally binds the current plan and closed bytes to these
exploratory expected SHA-256 values:

- public plan: `09a8fc8a57906bc3d4182af7f3b1f08cccf5c36b2a6c6a07c2ccf1a9033acf72`;
- closed manifest: `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e`.

This anchor detects a plan/closed common rewrite against the frozen V3 study. It
is deliberately **not** called a formal controller anchor: a writer able to edit
the study can also co-rewrite the constants. Formal admission still requires an
expected preimage in a controller or permission domain the worker cannot rewrite.

Regression attacks now rejected:

- duplicate row appended to both plan and closed, even when the attacker supplies
  recomputed expected hashes;
- duplicate slot ID retained inside a twelve-row plan, even with a recomputed
  expected plan hash;
- coordinated plan/closed challenge rewrite against the frozen expected hashes.

## 2. Signed-hash deletion gate is receipt-bound

The old eight-Boolean AND gate has been removed. The V3 gate accepts only a
closed evidence-bundle schema with exactly the eight named requirements. Every
descriptor must bind:

- one unique, nonempty external evidence receipt ID;
- the SHA-256 of that receipt's exact raw bytes;
- the exact requirement-specific scope;
- a status from `SATISFIED`, `FAILED`, or `UNKNOWN`.

The gate requires the corresponding receipt bytes, recomputes each SHA, parses a
closed receipt schema, checks descriptor/receipt identity, requirement, scope and
status equality, validates the subject SHA, and rejects missing or unexpected
receipt documents. Only eight valid, unique, exact-scope, externally supplied
`SATISFIED` receipts can return `DELETE_SIGNED_HASH`.

The study is not an issuer for any of these receipts. No receipts currently
exist in this study, so the frozen result is stably:

`UNKNOWN_DO_NOT_DELETE` with `MISSING_EVIDENCE_BUNDLE`.

An old-style dict containing all eight Boolean values as `true` now fails the
closed bundle schema and cannot authorize deletion. Duplicate receipt IDs,
invalid SHAs, wrong scopes, missing bytes, or mismatched document sets also fail
closed. No receipt was fabricated to exercise a success path.

## 3. Precise information boundary

The result and README now use exactly:

`PRIVATE_ROLE_AND_OUTCOME_BLIND__PUBLIC_TREATMENT_AWARE`

The split does not read private role assignments or outcomes, but it does read
the public challenge treatments `D0-HOST-LEAK`, `D1-OCI-CANARY`, and
`T-OCI-ISOLATED`. It is therefore not broadly label-blind.

## 4. Verification and exact bytes

- `layout_study.py --check RESULTS.candidate.json`: `RESULT_MATCH`.
- V3 regression suite: 17/17 pass, including duplicate-append, duplicate-ID,
  common-rewrite-anchor, malformed descriptor, and all-true-Boolean rejection
  attacks.
- Python compile check: pass.
- `layout_study.py` SHA-256:
  `493fcb42f90b6e9a6e655e39704aada05e142e9b18a5fed9f5d2a5e2dc523680`.
- `RESULTS.candidate.json` SHA-256:
  `6900465b3719e53f9d63610726333f85e607935b5e612b120c0a77f7278abab2`.
- `README.md` SHA-256:
  `c622fffc2bf1adc05760644053da291bb04693cb596f67b551c50b0e04dbebf4`.
- `tests/test_layout_study.py` SHA-256:
  `052262e15afd50a0d33e07dae6ec2f09db65f3890a0220e02fe4bfe5aa29e3a8`.
- reviewer input `FINAL-INDEPENDENT-ACCEPTANCE.md` SHA-256:
  `b04270d0f79857d5995a19eb7c129723f4c01c93fcc2c931e02c2f0caf53df5a`.

These are implementer-produced checks and exact-byte pointers for the same
reviewer. They are not an independent acceptance result.
