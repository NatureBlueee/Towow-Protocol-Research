# Collector V1.1 third-fix final independent acceptance

Date: 2026-08-01  
Reviewer: original `COLLECTOR-RECEIPT-SCHEMA-REDTEAM` reviewer  
Scope: local candidate package, frozen historical inputs and repository fixtures only  
Implementation changes by reviewer: none  
Status: `CANDIDATE_INTERNAL_G_INPUT_GATE_ACCEPT_SCOPED / FORMAL_NOT_RUN / G_NOT_RUN`

## 1. Decision

The third fix closes the two remaining candidate-internal blockers identified
in `FINAL-INDEPENDENT-ACCEPTANCE.md`:

1. controller-bound collector config and subject now have exact semantic role
   paths and are joined to the live challenge inventory and receipt contracts;
2. proc-provider admission is incremental, bounds total entries, cumulative
   name bytes and numeric PIDs before the historical base collector, and serves
   the base collector the bounded PID-name snapshot without a second full
   proc-root `readdirSync`.

The complete **candidate-internal G input gate is `ACCEPT_SCOPED`** for the
reviewed bytes and the explicit trusted-controller/read-only execution model.

This does not mean that G has run, that any G receipt is accepted, or that the
candidate has become formal. The correct state is:

```text
CANDIDATE-INTERNAL G INPUT GATE: ACCEPT_SCOPED
EVIDENCE-BEARING G EXECUTION: NOT_RUN
FORMAL / SCIENTIFIC ADMISSION: NOT_RUN / NOT_ADOPTED / NOT_AUTHORIZED
HISTORICAL F: UNCHANGED / NOT_PROMOTED
```

`ACCEPT_SCOPED` means that no candidate-internal counterexample survived the
specified exact-role, material-join, package, schema, canonical, process,
canary, depth, provenance and preallocation checks. It does not replace the
external controller and runner evidence listed in section 10.

## 2. Exact reviewed preimage and historical invariants

| Artifact | SHA-256 | Result |
|---|---|---|
| package manifest | `2a0b3608e216338f3a7876e4f09a66381e10755bcf386413b958f71e30e33d84` | `ACCEPT` |
| admission policy | `d3b82f2aa7a7e807bfa9580b45c782793bffa27fd8d70a11d980b1e9cd95e2f1` | `ACCEPT` |
| self-contained receipt schema | `936a69001bc5409df7e7d3fe2e98ba84da223b0da09b8beb94928465feef13ee` | `ACCEPT` |
| controller-material schema | `0143dfaea8ca1316e88edddfb4c9db3d114cda2b4c3c3442dee849f4b893864a` | `ACCEPT` |
| Python admission | `057f7de6ad0bbe0580624fdf8d7a43f63b6bcc21487cbe5d8e310fbcf5bdcf08` | `ACCEPT` |
| producer adapter | `cfa43f65f65dd6119e869e685c1f83b9d63ae4c2212d0bfa64f690e2818b9342` | `ACCEPT` |
| raw canonical checker | `54dfbf5deda94f0e79a2d840ac33f572c1f821ca9aed4684126bfe30129dc722` | `ACCEPT` |
| frozen collector source | `bc18911c65815da3747755eae44b8f77398d034f9c7c67b54430893c5a1ad699` | `ACCEPT / unchanged` |
| frozen V1 receipt schema | `a2dcbc5630337b93cee38c72915e76d954642f69fef1341f32a63188d5fa9209` | `ACCEPT / unchanged` |
| F `precommit.json` | `d9a44ab9a5a781a90b70e25ff2a448a329c151ca19998255a2d4d6b45904a77e` | `ACCEPT / unchanged` |
| F `closed.json` | `26471d579c13a3f26261512c1d9ac1c67516cb3f610840afa7c8c1f16c42cb5e` | `ACCEPT / unchanged` |
| F `reveal.json` | `7f698271d211441ad46b6851d8b219238f6e81b87f72afbdcf6de579adb70287` | `ACCEPT / unchanged` |

The ordered `slot-id + receipt SHA-256 + LF` list for all 12 historical F
receipts remains:

```text
42f7869d5de0caf6babcd95779cf8b2d1bb4dfec36da1640e018ff1962bb46c1
```

The manifest has six runtime rows plus two historical-input rows: eight bound
rows in total. Every row's actual byte length and SHA-256 matched.

## 3. Exact semantic role-path red team

The binding schema now fixes:

```text
challenge_root_relative_path = challenge
collector_input.relative_path = challenge/collector-input.json
subject_input.relative_path   = challenge/input.bin
```

The Python admission layer repeats the role/path comparison after schema
validation. This is defense in depth rather than reliance on schema alone.

Independent results using a freshly recomputed preimage and expected preimage
SHA for every mutation:

| Mutation | Result |
|---|---|
| valid config and subject rebound to files outside challenge | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| collector and subject bindings swapped | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| `challenge/./input.bin` | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| `challenge//input.bin` | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| `challenge/Input.bin` | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| `challenge_root_relative_path=challenge/.` | `REJECT CONTROLLER_PREIMAGE_SCHEMA_INVALID` |
| exact subject leaf is a symlink | `REJECT BINDING_SYMLINK` |
| `challenge` path component is a symlink | `REJECT BINDING_SYMLINK` |
| config and subject exact paths are hard links to the same inode | `REJECT CONTROLLER_ROLE_FILE_ALIAS` |

To ensure the executable check was not merely a schema result, the external
subject case was replayed with `validate_schema` temporarily replaced by a
no-op in the in-memory independent harness. It still rejected:

```text
EXPLICIT_ROLE_CHECK_WITH_SCHEMA_BYPASS
  REJECT CONTROLLER_ROLE_PATH_MISMATCH
```

Therefore exact path, role swap, alternate spelling, component/leaf symlink,
cross-role hardlink alias and freshly resealed external-role attacks are
`ACCEPT` as closed findings.

### Hardlink scope boundary

An exact role path that has an additional hardlink elsewhere, but is not an
alias of the other role, is not rejected. The independent scoping probe returned:

```text
EXTERNAL_HARDLINK_ALIAS_SCOPING_PROBE
  CANDIDATE_G_INPUT_ADMISSION_PASS formal=false
```

This does not change which bytes or inode the exact role path denotes, so it is
not a role-swap or inventory-join bypass. It does mean the candidate does **not**
prove exclusive inode reachability or `nlink == 1`. Any writable alias outside
the protected controller/read-only domain remains part of the external
authority and same-permission-peer `UNKNOWN`. If a future threat model requires
exclusive-link ownership, it must add an explicit nlink/authority rule; that
stronger claim is not included in this `ACCEPT_SCOPED` decision.

## 4. Live inventory and receipt-contract join

Admission now requires the reconstructed live inventory rows
`collector-input.json` and `input.bin` to be regular files and to equal the
receipt's respective byte-length and SHA-256 contracts. Before that join it
also requires:

- each exact bound file to match its file binding;
- config bytes to parse as the exact closed input object;
- receipt config/subject contracts to match their exact bindings;
- the externally bound challenge snapshot to equal a fresh live reconstruction;
- the receipt challenge tree to equal that live reconstruction.

Independent results:

```text
POSITIVE_CONTROL
  CANDIDATE_G_INPUT_ADMISSION_PASS formal=false

RESEALED_CONTRACT_DIVERGENCE
  REJECT CONTROLLER_SUBJECT_MISMATCH

SYNCHRONIZED_REWRITE_OLD_CONTROLLER_SEAL
  REJECT CONTROLLER_SEAL_MISMATCH
```

The original reviewer counterexample synchronized valid outside-role files,
receipt, execution evidence, snapshot, preimage and a new seal. It now fails at
the exact role contract before it can exploit synchronized hashes.

If the exact live files, receipt, inventory snapshot, bindings, execution
evidence and preimage are all changed consistently **and the trusted controller
supplies a new expected seal**, the new world passes:

```text
SYNCHRONIZED_REWRITE_NEW_CONTROLLER_SEAL
  CANDIDATE_G_INPUT_ADMISSION_PASS formal=false
```

That is correct behavior, not a synchronization bypass. A genuinely new
controller seal authorizes a new candidate input preimage. Whether the new seal
actually came from an independent controller is the external origin question;
the local validator cannot answer it.

Within a stable read-only material domain and an independently supplied fixed
seal, the live-inventory/contract join is `ACCEPT`.

## 5. Proc incremental admission and base handoff

The old implementation first allocated `readdirSync(procRoot)` and ignored
nonnumeric population. The third fix instead uses `opendirSync` and one
`readSync` result at a time. The independent harness made any full
`readdirSync` call fail and recorded the number of incremental reads:

```text
TOTAL_ENTRY_CAP
  PROC_DIRECTORY_ENTRY_CAP incrementalReads=4097 fullReads=0

NAME_BYTE_CAP
  PROC_DIRECTORY_NAME_BYTES_CAP incrementalReads=1 fullReads=0

NUMERIC_PID_CAP
  PROCESS_TRUNCATION incrementalReads=257 fullReads=0
```

The same three populations were injected through the real
`collectCandidate(..., gMode=true)` path with the historical base collector
instrumented only to count reachability:

```text
TOTAL_ENTRY_CAP_COLLECT
  PROC_DIRECTORY_ENTRY_CAP baseCalled=0

NAME_BYTE_CAP_COLLECT
  PROC_DIRECTORY_NAME_BYTES_CAP baseCalled=0

NUMERIC_PID_CAP_COLLECT
  PROCESS_TRUNCATION baseCalled=0
```

For an admitted provider containing numeric directories, the base collector's
exact proc-root `readdirSync` was counted:

```text
BASE_PROC_SNAPSHOT
  G_UNVERIFIED_ERROR_BRANCH procRootFullReads=0
```

The later G error is expected because the small synthetic proc rows did not
contain complete process captures. The decisive result is that the historical
base was reached only after bounded enumeration and did not issue a second full
proc-root read. The temporary `fs.readdirSync` wrapper is restored in `finally`.

The three proc caps and base-before-allocation ordering are `ACCEPT` for the
single-process synchronous producer model. Process disappearance/appearance
after enumeration remains a temporal condition: read errors enter branches
that G rejects, while actual same-window capture remains external `UNKNOWN`.

## 6. Package, source and canonical layer

The current manifest binds exactly:

- policy;
- self-contained receipt schema;
- controller-material schema;
- Python admission;
- producer adapter;
- raw canonical checker;
- frozen historical collector source;
- frozen historical receipt schema.

Independent deletion/tamper replay with the original expected manifest SHA:

```text
MANIFEST_DELETE producer PACKAGE_MANIFEST_MISSING
MANIFEST_DELETE CLI      PACKAGE_MANIFEST_MISSING
SOURCE_TAMPER  producer PACKAGE_FILE_MISMATCH
SOURCE_TAMPER  CLI      PACKAGE_FILE_MISMATCH
OLD_SCHEMA_DELETE producer PACKAGE_FILE_MISSING
OLD_SCHEMA_DELETE CLI      PACKAGE_FILE_MISSING
```

The prior uncaught Python `FileNotFoundError` is closed; both consumers now
return stable fail-closed machine codes.

The following four documents independently passed the package's raw canonical
checker:

```text
PACKAGE-MANIFEST.candidate.json                         PASS
ADMISSION-POLICY-V1.1.candidate.json                    PASS
COLLECTOR-RECEIPT-V1.1-ADMISSION.candidate.schema.json PASS
EXTERNAL-MATERIAL-BINDING-V1.1.candidate.schema.json   PASS
```

Package/source binding is `ACCEPT` conditional on a fixed independently
supplied expected manifest SHA. The Node/Python executable provider identity
and origin of that expected SHA remain external runner/controller `UNKNOWN`.

## 7. PF-B01..PF-B05 regression matrix

| Finding | Third-fix result | Evidence boundary |
|---|---|---|
| PF-B01 self-contained executable schema | `ACCEPT` | Direct Draft 2020-12 instance validation succeeds; CLI uses the same self-contained schema. |
| PF-B02 synchronized material forgery | `ACCEPT_SCOPED` | Old expected seal rejects synchronized rewrite; fresh external-role reseal rejects; exact live-role world with a genuinely new expected seal is a new authorized candidate preimage, not proof of origin. |
| PF-B03 depth/error provenance | `ACCEPT FOR G` | Depth-six still rejects with `TREE_DEPTH_UNREACHABLE`; original wrong-leaf/path/syscall cases remain rejected; G rejects remaining lossy error branches. Non-G's narrower provenance claim remains unchanged. |
| PF-B04 process snapshot/status | `ACCEPT FOR G` | Available process view with null snapshot still rejects `G_PROCESS_SNAPSHOT_REQUIRED`; machine-code handling has not regressed. |
| PF-B05 canonical release JSON | `ACCEPT` | All four release/control JSON documents pass the same raw canonical checker. |

Additional preserved G boundaries:

```text
65,537-byte challenge canary file -> REJECT G_CANARY_FILE_OVERSIZE
tree depth six                    -> REJECT TREE_DEPTH_UNREACHABLE
ordinary post-base tree change   -> REJECT G_PREFLIGHT_DOMAIN_CHANGED
```

The previous preflight instrumentation still produced `baseCalled=0` for
large-file, depth, tree-node and numeric-PID overflow. Three hundred nonnumeric
proc entries now legitimately remain below the newly explicit 4,096 total-entry
cap; the decisive overflow replay uses 4,097 and rejects before base.

No PF-B01..PF-B05 G-path regression was found.

## 8. Independent test commands and results

Candidate suite:

```bash
PYTHONPYCACHEPREFIX=/tmp/w025-third-independent-target2 \
python3 -m pytest -q \
  feature-spec/collector-v1.1-candidate/tests/test_admission_v1_1.py
```

```text
25 passed in 19.99s
```

Candidate plus frozen historical receipt-schema suite:

```bash
PYTHONPYCACHEPREFIX=/tmp/w025-third-independent-combined2 \
python3 -m pytest -q \
  feature-spec/collector-v1.1-candidate/tests/test_admission_v1_1.py \
  feature-spec/tests/test_collector_receipt_schema_candidate.py
```

```text
30 passed in 23.91s
```

The repository-wide feature-spec suite was not used as collector acceptance
evidence because an unrelated C01 minisuite was being atomically updated in a
parallel workstream during this review. That transient cross-line state was not
counted as a collector failure or success. The frozen collector package and its
direct historical schema dependency are the acceptance surface used here.

Passing tests were only the starting point. Sections 3–6 record independent
mutations not inferred from the implementer's audit conclusion.

## 9. What `ACCEPT_SCOPED` now permits

The reviewed candidate may be treated as internally ready for a controlled G
runner attempt, provided that the runner supplies all external premises below.
It may reject the run before or after collection; that is expected gate
behavior.

This acceptance permits:

- preserving the candidate as the selected V1.1 admission implementation;
- constructing a real controller-owned manifest/preimage seal flow;
- attempting G under read-only/stable material and bounded provider conditions;
- evaluating any produced report as candidate evidence only after independent
  inspection of the actual controller and runner receipts.

It does not permit:

- calling G completed before it runs;
- treating `CANDIDATE_G_INPUT_ADMISSION_PASS` as formal validation;
- retrospectively promoting historical F;
- inferring external authority facts from booleans inside execution-evidence
  JSON;
- claiming resistance to a same-permission malicious peer;
- claiming exclusive hardlink ownership or a trusted Node/Python binary merely
  because candidate source bytes were hash-bound;
- starting a formal/scientific population without a separate explicit decision.

## 10. External `UNKNOWN` and next evidence

The following facts remain deliberately outside candidate-internal closure:

1. the expected manifest SHA actually originated in a controller authority
   domain the worker could not modify;
2. the controller preimage SHA was frozen before worker execution and delivered
   through an independent channel;
3. challenge and controller materials were actually mounted/read as immutable
   for the relevant execution window;
4. no writable hardlink alias or same-permission peer defeated that authority
   boundary;
5. the actual Node/Python runtime and reviewed package were the programs
   executed;
6. process snapshot, receipt and execution evidence came from the same real
   execution window;
7. network isolation, authority-channel absence and zero-call claims are true
   runtime facts rather than self-asserted fields;
8. G has run and its real output has scientific or practical value.

Those are not reasons to reject the now-closed candidate-internal gate. They
are the required inputs and observations for the next real controller/runner
experiment. Until such evidence exists, the only accurate final status is:

```text
CANDIDATE G INPUT GATE: ACCEPT_SCOPED
REAL G: NOT_RUN
FORMAL: NOT_RUN / NOT_ADOPTED
EXTERNAL CONTROLLER + READONLY + SAME-WINDOW EXECUTION FACTS: UNKNOWN
```
