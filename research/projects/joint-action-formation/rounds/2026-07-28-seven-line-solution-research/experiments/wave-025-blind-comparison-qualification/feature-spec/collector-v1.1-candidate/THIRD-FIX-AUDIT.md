# Collector V1.1 candidate third-fix audit

Date: 2026-08-01  
Scope: candidate-internal evidence-bearing G admission blockers identified in
`FINAL-INDEPENDENT-ACCEPTANCE.md`  
Authoritative status: `IMPLEMENTER_RESULT / CANDIDATE / NOT_ADOPTED / NOT_INDEPENDENTLY_ACCEPTED / G_NOT_RUN`

## Outcome

This revision closes the two candidate-internal blockers named by the same
independent reviewer, without changing formal status and without running G:

1. Controller material now binds `collector_input` only to
   `challenge/collector-input.json` and `subject_input` only to
   `challenge/input.bin`. Admission also reconstructs the live challenge
   inventory and joins both role records to the receipt byte contracts.
2. `/proc` provider enumeration no longer starts by materializing
   `readdirSync(procRoot)`. It reads entries incrementally and caps both total
   entries and cumulative UTF-8 entry-name bytes before the historical base
   collector receives the bounded numeric snapshot.

This is an implementer result, not an independent acceptance decision. The
same reviewer must re-run the counterexamples and decide whether the internal
G input gate is acceptable.

## 1. Exact role binding closure

The generated controller-material schema now fixes all three relevant path
spellings:

```text
challenge_root_relative_path = challenge
collector_input.relative_path = challenge/collector-input.json
subject_input.relative_path   = challenge/input.bin
```

Admission separately enforces the exact mapping even if schema validation is
replaced or bypassed. Each component of a bound path is checked for symlinks;
the two role files may not be hard links to the same inode. After reconstructing
the live challenge tree, admission requires the inventory rows for
`collector-input.json` and `input.bin` to be regular files and to equal the
receipt's corresponding length/hash contracts.

Direct regressions now cover:

- the reviewer's external-file escape with a newly recomputed receipt,
  execution evidence, controller preimage, and seal;
- collector/subject role swap;
- non-canonical path spellings `challenge/./input.bin` and
  `challenge//input.bin`;
- an exact-path symlink;
- a hard-link alias between the two role files.

The independently resealed external escape, role swap, and alternate spellings
reject at controller-preimage schema validation. Symlink and hard-link cases
reject with stable `BINDING_SYMLINK` and `CONTROLLER_ROLE_FILE_ALIAS` codes.

## 2. `/proc` allocation closure and claim boundary

The reviewed weakness was not merely numeric-PID overflow. The old preflight
first allocated the complete `readdirSync(procRoot)` result and only then
filtered/capped numeric entries; arbitrarily many nonnumeric names were outside
that cap.

`assertCanonicalProcProvider` now uses `opendirSync` plus incremental
`readSync` and rejects at either boundary:

```text
all directory entries       > 4096       -> PROC_DIRECTORY_ENTRY_CAP
cumulative UTF-8 name bytes > 1048576    -> PROC_DIRECTORY_NAME_BYTES_CAP
numeric PID entries         > 256        -> PROCESS_TRUNCATION
```

In G mode, the historical base collector receives a copy of the already
bounded, numeric-sorted PID-name snapshot for the exact `procRoot`; it therefore
does not perform a second full proc-root `readdirSync`. Calls for other roots
still use the original filesystem operation, and the temporary wrapper is
restored in `finally`.

This is a bounded allocation claim, not a claim that numeric-only capping is
sufficient or that the process view is immutable. `/proc` rows can still
disappear after enumeration; such failures remain error branches and G rejects
them. A same-permission malicious peer and trusted capture timing remain outside
this candidate-internal closure.

## 3. Stable package failure

Deleting the manifest-bound historical receipt schema now yields the stable
machine code `PACKAGE_FILE_MISSING` from both the Node producer and Python CLI.
It no longer escapes from Python as an uncaught `FileNotFoundError`.

## 4. Frozen artifact evidence

All byte lengths and SHA-256 values below were measured after the final release
and manifest builders ran:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `PACKAGE-MANIFEST.candidate.json` | 1313 | `2a0b3608e216338f3a7876e4f09a66381e10755bcf386413b958f71e30e33d84` |
| `ADMISSION-POLICY-V1.1.candidate.json` | 1574 | `d3b82f2aa7a7e807bfa9580b45c782793bffa27fd8d70a11d980b1e9cd95e2f1` |
| `COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json` | 15568 | `936a69001bc5409df7e7d3fe2e98ba84da223b0da09b8beb94928465feef13ee` |
| `EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json` | 2322 | `0143dfaea8ca1316e88edddfb4c9db3d114cda2b4c3c3442dee849f4b893864a` |
| `admit_receipt_v1_1.py` | 40982 | `057f7de6ad0bbe0580624fdf8d7a43f63b6bcc21487cbe5d8e310fbcf5bdcf08` |
| `producer-v1.1.candidate.js` | 21762 | `cfa43f65f65dd6119e869e685c1f83b9d63ae4c2212d0bfa64f690e2818b9342` |
| `raw-canonical-check.candidate.js` | 1316 | `54dfbf5deda94f0e79a2d840ac33f572c1f821ca9aed4684126bfe30129dc722` |
| `build_release_artifacts.py` | 6186 | `f904c6b532a6715838695eb4819f68ea32d2fc15aa68e9e4f225adcf72bddd16` |
| `build_package_manifest.py` | 1236 | `c011ec342095ea0600b3a0fc2ce97893c9b540b8cb9a4fa2e91e62cf64fc0b59` |
| `tests/test_admission_v1_1.py` | 42611 | `a49998f0b2df54a1d98f3f8869d521e1ed57437df90e040bfece50b937b076c1` |
| frozen historical collector source | 19757 | `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699` |
| frozen historical V1 schema | 27874 | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` |

The manifest's six runtime rows and two historical-input rows match the actual
files. Manifest, policy, admission schema, and controller-material schema all
pass the raw canonical JSON checker.

Historical F anchors remain byte-identical:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| F `precommit.json` | 4988 | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` |
| F `closed.json` | 18837 | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` |
| F `reveal.json` | 4449 | `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` |

## 5. Exact verification commands and results

Run from repository root `/Users/nature/通爻协议研究`:

```text
candidate='research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec/collector-v1.1-candidate'
feature_spec='research/projects/joint-action-formation/rounds/2026-07-28-seven-line-solution-research/experiments/wave-025-blind-comparison-qualification/feature-spec'

python3 "$candidate/build_release_artifacts.py"
exit 0

python3 "$candidate/build_package_manifest.py"
exit 0

PYTHONPYCACHEPREFIX=/tmp/wave025-third-target python3 -m pytest -q "$candidate/tests/test_admission_v1_1.py"
25 passed in 18.53s

PYTHONPYCACHEPREFIX=/tmp/wave025-third-combined python3 -m pytest -q "$candidate/tests/test_admission_v1_1.py" "$feature_spec/tests/test_collector_receipt_schema_candidate.py"
30 passed in 20.12s

PYTHONPYCACHEPREFIX=/tmp/wave025-third-full python3 -m pytest -q "$feature_spec" --junitxml=/tmp/wave025-third-full.xml
163 passed in 53.92s

for f in PACKAGE-MANIFEST.candidate.json ADMISSION-POLICY-V1.1.candidate.json COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json; do node "$candidate/raw-canonical-check.candidate.js" "$candidate/$f"; done
exit 0 for all four files
```

## 6. Preserved Unknowns and stopping boundary

This revision does not establish any of the following external facts:

- the expected package-manifest or controller-preimage seal originated in a
  worker-unwritable controller authority domain;
- the live challenge was actually mounted read-only for the worker;
- a real runner captured truthful launch, process, and execution evidence in
  the same execution window;
- a same-permission malicious local peer could not rewrite evidence;
- evidence-bearing G has run or produced a valid receipt.

Therefore:

```text
FORMAL: unchanged / not authorized / not run
G: unchanged / not run
CANDIDATE: implementer-fixed, awaiting the same independent reviewer
F: untouched and not promoted
```
