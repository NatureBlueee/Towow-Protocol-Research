# Collector V1.1 candidate final independent acceptance

Date: 2026-08-01  
Reviewer: original `COLLECTOR-RECEIPT-SCHEMA-REDTEAM` reviewer  
Scope: local workspace candidate package and repository fixtures only  
Implementation changes by reviewer: none  
Status: `FINAL_INDEPENDENT_REJECTED_FOR_FORMAL_AND_EVIDENCE_BEARING_G`

## 1. Outcome first

The second revision is a material improvement. It is no longer true that the
manifest is decorative, the release schema is unresolvable, large G files are
silently outside the canary domain, or G can proceed with a missing process
snapshot. The revision really performs the new checks in the producer and CLI.

However, the complete candidate G input gate is still **REJECTED**. A new
decisive internal counterexample remains:

> The controller preimage binds bytes, but does not bind the `collector_input`
> and `subject_input` roles to the exact paths that the receipt claims the
> collector read. A correctly hashed and newly sealed preimage can bind both
> roles to files outside the challenge root while the actual
> `challenge/collector-input.json` and `challenge/input.bin` contain different
> bytes. Admission returns `CANDIDATE_G_INPUT_ADMISSION_PASS`.

This is not the external question of whether a controller really protected a
seal. It is a candidate-internal role-to-path/data-consistency omission. The
binding schema permits the wrong mapping even if the controller is perfectly
trusted and the root is genuinely read-only.

There is also a narrower resource-closure remainder: numeric PID overflow is
rejected before the historical base collector, but `assertCanonicalProcProvider`
first materializes the entire `readdirSync(procRoot)` result and ignores an
unbounded population of nonnumeric names. The tree-domain preflight is bounded
and precedes the base call; the process-directory allocation is not.

Final boundaries:

```text
FORMAL: REJECT / NOT AUTHORIZED / NOT RUN
EVIDENCE-BEARING G: BLOCKED
CANDIDATE G INPUT GATE AS A COMPLETE CLOSURE: REJECT
NON-G CONTROLLED ENGINEERING SMOKE: ALLOWED WITH EXPLICIT UNVERIFIED CODES
```

No historical F receipt was promoted or rewritten. `formal_admission` remains
`false` in every positive candidate report observed.

## 2. Exact reviewed package and historical invariants

| Artifact | SHA-256 | Result |
|---|---|---|
| package manifest | `bfddb4f4ef990a54660868c54a348033822adedc3eb0683f30a5174863594a7a` | `ACCEPT` current preimage |
| admission policy | `ac0ad100a00753d7b0389d6787c2ca898007104b8a0ce00fc70516744a70c16d` | `ACCEPT` manifest match |
| self-contained receipt schema | `936a69001bc5409df7e7d3fe2e98ba84da223b0da09b8beb94928465feef13ee` | `ACCEPT` manifest match |
| controller-material schema | `7ff51e44434933fd78615dfdded5cc6240ea17879835f5896aa8270f427f0858` | `ACCEPT` manifest match |
| Python admission | `f921f76e6ad2b4a793db525a13189deb75ff92b6dbeca0b27a019cdf99bf78dd` | `ACCEPT` manifest match |
| producer adapter | `b183f20590d1eedcfc82894402934a1febeeb2ac4c6e5bd2983ba12cb6313424` | `ACCEPT` manifest match |
| raw canonical checker | `54dfbf5deda94f0e79a2d840ac33f572c1f821ca9aed4684126bfe30129dc722` | `ACCEPT` manifest match |
| frozen collector source | `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699` | `ACCEPT / unchanged` |
| frozen V1 receipt schema | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` | `ACCEPT / unchanged` |
| F `precommit.json` | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` | `ACCEPT / unchanged` |
| F `closed.json` | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` | `ACCEPT / unchanged` |
| F `reveal.json` | `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` | `ACCEPT / unchanged` |

The ordered `slot-id + receipt SHA-256 + LF` list for all 12 historical F
receipts still hashes to:

```text
42f7869d5de0caf6babcd95779cf8b2d1bb4dfec36da1640e018ff1962bb46c1
```

All six runtime rows and both historical-input rows in the current manifest
match their actual byte lengths and SHA-256 values.

## 3. PF-B01..PF-B05 replay

| Finding | Final result | Independent evidence and exact boundary |
|---|---|---|
| PF-B01 self-contained executable schema | `ACCEPT` | The release schema contains its full `$defs`; direct `Draft202012Validator(schema).iter_errors(real_receipt)` succeeds offline, and CLI calls `validate_schema(receipt, RECEIPT_SCHEMA, ...)`. The old relative-ref failure is closed. |
| PF-B02 synchronized material forgery | `REJECT / PARTIALLY CLOSED` | Retaining the old controller-supplied preimage SHA after rewriting the preimage now rejects with `CONTROLLER_SEAL_MISMATCH`. Non-JSON config and live challenge-tree divergence are rejected. But exact semantic role paths are unbound; the newly sealed role/path divergence below passes G input admission. |
| PF-B03 tree depth and operation provenance | `ACCEPT FOR G; PARTIAL FOR NON-G` | Depth-six, the original wrong process leaf, wrong `/etc/hostname` source, and tree `syscall=connect` now reject. G rejects every remaining process/tree/hostname error branch. Non-G still accepts a process error with the right leaf but impossible `syscall=connect`, and similarly accepts `/etc/hostname` with the right path but wrong syscall. Those cases cannot enter G, so they are a non-G semantic limitation rather than a G evidence bypass. |
| PF-B04 process snapshot and status | `ACCEPT FOR G` | Available process view plus `process_snapshot=null` rejects with `G_PROCESS_SNAPSHOT_REQUIRED`. Error-only public branches cannot regain a pass through human-string prefix matching: G closes error branches and `validate_process_snapshot` uses machine codes. Success rows recompute cmdline/status/self bytes and population. |
| PF-B05 canonical release JSON | `ACCEPT` | Manifest, policy, receipt schema, and binding schema all pass `raw-canonical-check.candidate.js`. |

## 4. Decisive remaining internal counterexample: role/path divergence

An independent synthetic controller root was made from the repository's valid G
fixture, then changed as follows:

1. `challenge/collector-input.json` was replaced with bytes that are not the
   bound collector config.
2. `challenge/input.bin` was replaced with a different actual subject.
3. A valid `external-config.json` and a different `external-subject.bin` were
   created outside the challenge root.
4. The challenge was freshly snapshotted, and its exact current tree and
   canaries were placed in the receipt.
5. The receipt's `input_contract` and `subject_input` digests were set from the
   two external files; `subject_input.path` still said
   `$CHALLENGE/input.bin` as required by the receipt schema.
6. Receipt, execution evidence, every file binding, and the controller preimage
   were recomputed, and the new exact preimage SHA was supplied separately.

Actual result:

```text
ROLE_PATH_DIVERGENCE CANDIDATE_G_INPUT_ADMISSION_PASS False
remaining_unknown_codes = [SAME_PERMISSION_MALICIOUS_PEER_OUT_OF_SCOPE]
bound collector_input = external-config.json
actual collector path   = challenge/collector-input.json
bound subject_input     = external-subject.bin
receipt subject path    = $CHALLENGE/input.bin
```

The external config is strictly valid, so this does not reuse the previously
closed invalid-JSON case. The live challenge snapshot is also exact, so this
does not reuse the previously closed stale-tree case. The failure is that these
two independently valid facts are never related:

```text
binding.collector_input.relative_path
  != binding.challenge_root_relative_path + "/collector-input.json"

binding.subject_input.relative_path
  != binding.challenge_root_relative_path + "/input.bin"
```

Nor does admission require the subject digest/length to equal the inventory
record for live challenge `input.bin`.

The minimum internal closure is to encode and enforce the exact role mapping,
then add both negative cases to end-to-end G admission tests. Merely relying on
the controller to choose sensible relative paths would turn an executable
contract into an undocumented convention.

## 5. Package manifest, historical source and external expected SHA

Under a fixed expected manifest SHA supplied to the invocation, both producer
and Python admission now fail closed:

```text
MANIFEST_DELETE            producer PACKAGE_MANIFEST_MISSING
MANIFEST_DELETE            admission PACKAGE_MANIFEST_MISSING
HIST_SOURCE_TAMPER         producer PACKAGE_FILE_MISMATCH
HIST_SOURCE_TAMPER         admission PACKAGE_FILE_MISMATCH
SYNC_MANIFEST_OLD_EXPECTED producer PACKAGE_MANIFEST_SEAL_MISMATCH
SYNC_MANIFEST_OLD_EXPECTED admission PACKAGE_MANIFEST_SEAL_MISMATCH
HIST_SCHEMA_DELETE         producer PACKAGE_FILE_MISSING
```

Therefore runtime binding of the exact manifest, adapter, admission, checker,
frozen source and frozen schema is `ACCEPT` **conditional on the expected SHA
being an independent controller input**. Producer does not load the historical
collector until package verification succeeds.

When the modified historical source and manifest were synchronized and their
new SHA was supplied as a new expected value, both verifiers passed:

```text
SYNC_MANIFEST_NEW_EXPECTED producer PASS
SYNC_MANIFEST_NEW_EXPECTED admission PASS
```

That is expected, not a hash failure: a digest cannot establish who supplied
it. The interface now requires the value, but the local package cannot prove
that its origin is outside worker authority. The following remain external
`UNKNOWN`, not candidate-internal rejections:

- the actual controller chose the expected SHA before worker execution;
- the worker could not replace that input;
- the invoked Node/Python program was itself the controller-selected program.

One operational defect was observed: deleting the frozen schema makes the
Python verifier fail closed via uncaught `FileNotFoundError`, rather than its
canonical admission error report. Integrity is preserved, but the stable
machine-error contract is `PARTIAL` for this missing-file branch.

## 6. Config, challenge, canary and process consistency

### 6.1 Relations now closed

Within the paths actually named by the preimage, admission now independently:

- parses collector input bytes as strict JSON and requires the exact single
  declared schema object;
- matches collector input and subject byte length/hash to the receipt;
- reconstructs launch-environment rows and canaries;
- reconstructs the live challenge inventory, directory tree, hashes and
  canaries;
- compares the external challenge snapshot and receipt challenge tree to that
  reconstruction;
- binds the receipt hash into execution evidence;
- recomputes success process cmdline, status, self files, namespaces and exact
  PID population from the process snapshot.

These relations are `ACCEPT`. They do not repair the role/path gap in section 4.

### 6.2 Process snapshot

```text
G_NULL_PROCESS REJECT G_PROCESS_SNAPSHOT_REQUIRED
G error branches REJECT G_UNVERIFIED_ERROR_BRANCH or G_PROCESS_SNAPSHOT_INCOMPLETE
modified success cmdline raw REJECT PROCESS_SNAPSHOT_ROW_MISMATCH
```

Candidate-internal G process consistency is `ACCEPT`. Whether the process
snapshot was captured by a trusted controller from the same execution window
is external `UNKNOWN` until a real runner provides evidence.

### 6.3 Large files and canaries

An added 65,537-byte challenge file containing a canary produces:

```text
Python end-to-end G admission: REJECT G_CANARY_FILE_OVERSIZE
producer G preflight:          REJECT G_CANARY_FILE_OVERSIZE, baseCalled=0
```

Thus the old “large file silently means no canary” G bypass is closed. Non-G
continues to have an explicitly smaller scan domain; it must not be interpreted
as complete challenge canary absence.

## 7. Depth and error provenance replay

Independent single-mutation results:

```text
DEPTH6                                      REJECT TREE_DEPTH_UNREACHABLE
PROCESS_WRONG_LEAF                          REJECT PROCESS_ERROR_PATH_PROVENANCE
TREE_WRONG_SYSCALL                          REJECT TREE_ERROR_OPERATION_PROVENANCE
wrong /etc/hostname path                    REJECT HOSTNAME_ERROR_PROVENANCE
PROCESS_RIGHT_LEAF_WRONG_SYSCALL_NON_G      ACCEPT
PROCESS_RIGHT_LEAF_WRONG_SYSCALL_G          REJECT G_UNVERIFIED_ERROR_BRANCH
HOSTNAME_RIGHT_PATH_WRONG_SYSCALL_NON_G     ACCEPT
HOSTNAME_RIGHT_PATH_WRONG_SYSCALL_G         REJECT G_UNVERIFIED_ERROR_BRANCH
```

So the original PF-B03 cases are closed, and G has a clear all-error-branches
rejection boundary. The implementation should not describe non-G as having
complete operation provenance; it validates a narrower subset.

## 8. Producer preallocation and post-fingerprint ordering

An independent instrumentation harness replaced the base collector function
only to count whether it was reached. Package files on disk remained unchanged
and verified before each `collectCandidate` invocation.

```text
OVERSIZE         G_CANARY_FILE_OVERSIZE baseCalled=0
DEPTH            G_PREFLIGHT_TREE_DEPTH baseCalled=0
TREE_NODES       G_PREFLIGHT_DIRECTORY_CAP baseCalled=0
PROC_NUMERIC_257 PROCESS_TRUNCATION baseCalled=0
POST_FINGERPRINT G_PREFLIGHT_DOMAIN_CHANGED baseCalled=1
```

This establishes:

- G challenge/cwd/out/tmp/self-fd tree preflight runs before the historical
  collector;
- challenge file size, tree depth and directory/node population reject before
  the base call;
- numeric process population rejects before the base call;
- after the base call, an ordinary non-canary challenge-file addition is still
  detected by the post fingerprint. The post check is not merely a duplicate
  canary comparison.

But the process provider begins with:

```javascript
names = fs.readdirSync(procRoot)
```

and only then filters/counts numeric names. Three hundred nonnumeric synthetic
entries reached the stubbed base collector:

```text
PROC_NONNUMERIC_300 BASE_CALLED baseCalled=1
```

This is not a semantic PID-population bypass, but it disproves complete
preallocation closure for the process directory. An incremental read with a
total-entry/byte cap, followed by the numeric population cap, is still needed
if the producer claims bounded allocation against a noncanonical/synthetic proc
provider.

The pre/post equality itself depends on a stable read-only domain. A real G run
must establish that external premise; local instrumentation proves ordering and
detection behavior, not the mount's authority state.

## 9. Canonical JSON and schema execution

The exact checks were:

```bash
for f in \
  feature-spec/collector-v1.1-candidate/PACKAGE-MANIFEST.candidate.json \
  feature-spec/collector-v1.1-candidate/ADMISSION-POLICY-V1.1.candidate.json \
  feature-spec/collector-v1.1-candidate/COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json \
  feature-spec/collector-v1.1-candidate/EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json
do
  node feature-spec/collector-v1.1-candidate/raw-canonical-check.candidate.js "$f"
done
```

All four exited zero. Direct Draft 2020-12 schema checking and instance
validation of an unchanged F receipt also exited without errors. PF-B01 and
PF-B05 are fully closed for the reviewed bytes.

## 10. Local test results

Candidate tests alone:

```bash
python3 -m pytest -q \
  feature-spec/collector-v1.1-candidate/tests/test_admission_v1_1.py
```

```text
22 passed in 4.46s
```

Candidate plus unchanged historical receipt-schema suite:

```bash
python3 -m pytest -q \
  feature-spec/collector-v1.1-candidate/tests/test_admission_v1_1.py \
  feature-spec/tests/test_collector_receipt_schema_candidate.py
```

```text
27 passed in 6.92s
```

These tests are consistent with the implemented fixes but do not contain the
passing role/path-divergence counterexample. Test count is not acceptance.

All additional mutations used temporary synthesized controller roots and
subprocess instrumentation. They did not edit implementation, the frozen
source/schema, historical F, or repository fixtures.

## 11. Candidate-internal closure versus external Unknown

### Candidate-internal `ACCEPT`

- exact runtime manifest verification under a fixed expected SHA;
- manifest coverage of the frozen collector and frozen V1 schema;
- self-contained candidate schema actually used for receipt instances;
- four canonical release JSON documents;
- strict raw config parsing and declared parsed-object equality;
- live challenge reconstruction for the selected challenge root;
- G rejection of files over 65,536 bytes;
- G-required complete success process snapshot;
- G rejection of lossy error/unavailable branches;
- tree/depth/tree-operation checks needed by the original counterexamples;
- pre-base tree/large-file/numeric-PID gates and post tree fingerprint.

### Candidate-internal `REJECT` or `PARTIAL`

- `REJECT`: config and subject bindings do not have to name the exact files
  represented by `$CHALLENGE/collector-input.json` and
  `$CHALLENGE/input.bin`;
- `PARTIAL`: process-directory allocation occurs before a total directory-entry
  cap, and nonnumeric entries are unbounded;
- `PARTIAL`: non-G error provenance does not validate all syscall/path pairs;
- `PARTIAL`: Python missing historical file is fail-closed but not returned as
  a stable admission machine error.

### External `UNKNOWN`

- whether the expected manifest and preimage SHAs actually originated in an
  independent controller authority domain;
- whether the worker was unable to rewrite that domain;
- whether challenge was really mounted read-only during the run;
- whether execution-evidence assertions about network, authority channel and
  worker write access are true;
- whether process snapshot and receipt came from the same real execution
  window;
- whether the reviewed package/runtime was the package actually executed;
- real G behavior, population behavior, V2S extraction and scientific value.

The validator cannot turn a sealed JSON statement about these facts into proof
that the operating-system facts occurred. This is correctly an external
precondition, provided the final system preserves it as `UNKNOWN` until a real
controller/runner receipt exists.

## 12. Minimum next closure

Before evidence-bearing G is eligible for another acceptance decision:

1. Enforce exact semantic role paths, at minimum:
   `collector_input == challenge_root/collector-input.json` and
   `subject_input == challenge_root/input.bin`; also compare subject
   digest/length with the reconstructed challenge inventory entry.
2. Add an end-to-end negative fixture where both outside files are perfectly
   valid and the whole preimage is freshly sealed; it must reject for role/path
   mismatch, not for invalid JSON or stale challenge state.
3. If preallocation safety is a claim, incrementally bound all proc directory
   entries before materialization, not only numeric PIDs after `readdirSync`.
4. Normalize missing historical-file failures in Python into a stable canonical
   machine error.
5. After internal closure, run through a real controller-created immutable
   expected manifest SHA, controller-created preimage SHA, read-only challenge,
   process snapshot and independently interpretable execution evidence.

Even after those steps, a G pass remains an input/execution-evidence admission
result. Formal/scientific adoption still requires a separate explicit decision
and evidence review; it must not be inferred from this candidate's test suite or
status string.
