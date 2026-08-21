编辑
PRO-WAVE013-CAUSAL-AUDIT-001
Revised causal audit after Evidence Update v3
A. Exact claims now supported—and claims still withheld
Claims now supported

The new evidence supports a stronger and more precise tested-blindness claim:

For the two reported persistent runs, the arm-visible interface did not expose the semantic case label through the previously identified channels: direct case_id, case-derived identifiers, the evaluator-private manifest hash, two-candidate manifest-hash dictionary matching, or inherited parent CLI arguments.

More specifically, the evidence supports that:

The first two blindness claims were invalid.
Any green runs produced before both the manifest-hash oracle and inherited sys.argv channels were removed remain development evidence only.

The current dual-view implementation separates evaluator-private and arm-visible data for the tested channels.

case_id and the full manifest_sha256 remain evaluator-private.

The arm receives a separately generated arm_binding_token.

Arm-facing requests and responses bind that token rather than the private manifest.

Private freeze receipts and evaluator artifacts retain full-manifest binding.

The visible identifiers in the two new runs were syntactically opaque under the stated checks.

Episode identity derived only from opaque run identity and the random arm token.

Run, process and working-directory identifiers were fixed-length and digits-only.

The child process recorded the sanitized argument vector:
["run.py", "--opaque-arm-child"].

The known two-label hash-oracle attack failed in both new runs.
Given the two candidate labels and the arm-visible data, the reported number of candidate hash matches was zero.

The evaluator enforced the new separation conditions.
It rejects a semantic case label or evaluator-private manifest hash appearing in the start payload or arm transcript.

The implementation passed the reported regression suite.
The 41/41 result supports implementation coverage for the encoded evaluator, runtime and root tests, including a real CLI leakage regression test. It does not establish completeness against unencoded side channels.

Two post-repair persistent runs were independently classified as reported.

One run was classified SUCCEEDED, with ExactTaskSuccess=true, CorrectResolution=true, SafeHandling=true, a valid bundle and no evaluator errors.

One run was classified BOUNDED_REFUSAL, with CorrectResolution=true, SafeHandling=true, a valid bundle and no evaluator errors.

The two observed classifications are no longer explainable by the specific previously demonstrated label channels.

The strongest revised statement is therefore:

In two persistent executions of one frozen synthetic world, after removing the demonstrated direct-label, identifier-derived, manifest-hash-dictionary and inherited-CLI channels, an implementation-independent evaluator classified one exact-task-success episode and one bounded-refusal episode from arm-visible transcripts that passed the stated semantic-label exclusion checks.

A shorter acceptable label is:

Tested arm-view label non-disclosure for E1 and E5 under the instrumented channel model.

This is stronger than the prior packet, but it is still not equivalent to absolute label blindness.

Claims still withheld

The following claims remain unsupported:

That the arm could not infer the case through any unmeasured process, filesystem, timing, descriptor-content, resource-usage or operating-system side channel.

That the two outcomes generalize beyond E1 and E5.

That the other six frozen cases are correctly handled.

That a malicious arm could not inspect the parent process, sibling processes, /proc, open files or the run directory.

That the entire run cannot be coherently regenerated or rewritten by a same-user controller.

That process separation implies independent administration or non-collusion.

That signing keys correspond to real organizational principals.

That Authority responses constitute real legal or organizational authority.

That A4 caused the observed target change.

That the signed readback establishes causal attribution.

That the effect observation is a real-world Effect.

That the two Acceptances are informed, independent or legally operative owner acts.

That Finality corresponds to irreversible external settlement.

That bounded refusal is complete outside the frozen inquiry boundary.

That the system solves an open-world joint-action problem.

That the distributed construction is necessary, superior or less costly than a mature central solution.

That V1, V2 or any broader system specification is complete.

The new evidence raises the confidence in experimental fairness for two cases. It does not raise the claim ceiling for causation, real authority, organizational independence or open-world correctness.

B. Strongest remaining false-positive construction
Within the currently stated threat model: causal twin remains first

Yes. The causal-twin construction remains the strongest false positive for ExactTaskSuccess.

It is stronger than another label-leak attack because it requires:

no semantic label;

no forged signature;

no malformed bundle;

no manifest-hash recovery;

no inherited argument leak;

no process-name leak;

no duplicate execution;

no cross-run artifact substitution;

no dishonest sensor or readback statement.

The construction is:

All required owners issue valid responses for the exact request.

A4 receives the exact request and emits a valid signed execution occurrence.

A4 does not cause the authoritative target transition. It may no-op, fail before commit or mutate a non-authoritative copy.

An independent target-side actor changes the authoritative target to the same expected post-state within the permitted interval.

The sensors truthfully observe that state.

READBACK truthfully reports the state.

Effect observation, Acceptance and Finality are truthfully signed.

The evaluator returns SUCCEEDED.

The packet can therefore be completely genuine while the following proposition is false:

[
A4(R)\ caused\ T_0@v_0 \rightarrow T_1@v_1
]

The visible evidence may instead establish only:

[
A4(R)\ occurred
]

and:

[
T_1@v_1\ was\ later\ observed
]

The two facts can coexist without the first causing the second.

This remains the first unresolved construction because it attacks the semantics of ExactTaskSuccess without exceeding the current trust boundary.

Just outside the current threat model: coherent whole-run rewrite

The strongest broader integrity construction remains a same-user whole-run rewrite:

the controller owns the run directory;

it can restart or replace all local services;

it can access all local signing keys;

it regenerates a coherent set of states, logs, sensor samples, Acceptances and Finality;

all hash chains and signatures verify because the entire synthetic history is replaced consistently.

This is a more powerful adversary, but it is outside the stated coverage. It attacks whether the evidence history is externally anchored at all.

The priority ordering is therefore:

Causal twin, for the current system-level claim of exact causal task success.

Whole-run rewrite, for hostile local-administrator resistance.

Remaining unmeasured label and side-channel attacks, for stronger blindness claims.

C. Smallest executable causal-twin test
Test name

CT-001 — Hidden-branch exogenous target twin

Question tested

Can the evaluator distinguish:

[
A4\ caused\ the\ target\ transition
]

from:

[
A4\ execution\ and\ the\ target\ transition\ merely\ occurred\ in\ the\ same\ episode?
]

Minimum structure

The test consists of one hidden randomized branch with two possible executions. No semantic case or arm label is supplied to A4 or any owner-facing service.

Common frozen inputs

Both branches use exactly the same:

request bytes;

owner-service states;

Authority requests and responses;

A4 identity;

target identity;

pre-state and pre-state version;

required post-state;

deadline;

evaluator rules;

arm-visible payload schema;

opaque run identifier format;

independently random arm_binding_token.

The evaluator-private manifest contains a random hidden bit:

[
b \in {0,1}
]

The hidden bit must not influence:

arm_binding_token;

run, process or path names;

payload lengths where avoidable;

environment key names;

child argument vectors;

owner-facing message structure.

A4 sees only the ordinary opaque execution request.

Branch 1: genuine causal execution

When (b=1):

A4 sends the exact mutation command to the authoritative target.

The target applies that command.

The target changes from (v_0) to (v_1).

The existing occurrence, sensor, READBACK, effect, Acceptance and Finality pipeline proceeds.

Branch 0: exogenous twin

When (b=0):

A4 receives and executes the same request-facing path.

Its target mutation is intercepted immediately before authoritative commit, or redirected to a disposable non-authoritative copy.

A separate evaluator-controlled helper changes the authoritative target from (v_0) to the identical (v_1).

The helper acts within the same allowed time interval.

The normal sensor, READBACK, effect, Acceptance and Finality pipeline proceeds.

A4 and the owner services must not be told that the helper exists.

Required matching conditions

The twin should preserve as much evaluator-visible evidence as the existing schema permits:

identical request hash;

identical owner-response structure;

valid A4 occurrence signature;

identical final target state and version semantics;

equivalent sensor observations;

valid READBACK;

valid effect observation;

valid owner Acceptances;

valid Finality;

no semantic labels;

no private manifest hash;

no branch-derived identifiers.

The helper must not forge A4's signature. It only supplies the independent target cause.

Primary observable

Only the evaluator's final classifications are required:

Genuine branch	Twin branch	Interpretation
SUCCEEDED	rejected, deferred or UNKNOWN	Current evidence distinguishes causal execution from temporal coexistence
SUCCEEDED	SUCCEEDED	ExactTaskSuccess currently accepts non-causal outcome coexistence
rejected	rejected	Evidence rule is too strict or valid causal evidence is missing
rejected	SUCCEEDED	Severe inversion or hidden-arm contamination

The decisive expected property is:

[
V(Genuine)=SUCCEEDED
]

and:

[
V(Twin)\neq SUCCEEDED
]

Do not add the repair before running the diagnostic

For maximum information, the first execution of CT-001 should use the current evidence schema unchanged.

Adding a target-issued causal receipt before the test would demonstrate the repair, but it would not reveal whether the present system already has the gap.

Smallest repair if the twin passes incorrectly

The minimal deterministic repair is an authoritative target-generated commit receipt created atomically with the mutation:

[
Receipt_T =
Sign_T(
hash(R),
arm_binding_token,
A4_principal,
target_id,
pre_version,
post_version,
commit_id
)
]

The target must:

authenticate the caller as A4;

verify the request hash and idempotency identifier;

apply the target mutation;

record the caller, exact request, pre-version and post-version;

issue the receipt within the same atomic commit boundary.

A later A4 occurrence record plus a later readback is not an equivalent substitute.

After implementing the receipt, rerun the same hidden-branch test. The genuine branch should have a valid target receipt. The twin branch should not.

D. Can mature technology or a lawful strong center eliminate the gap?

Yes, for a bounded digital target, mature technology can eliminate the technical causal-attribution gap. That counts as a positive solution.

Existing combined solution

A sufficient mature composition is:

Authenticated command submission

The target authenticates the exact A4 principal.

The command includes the exact request hash, target object and expected pre-version.

Optimistic concurrency or serialized transaction

The mutation is permitted only from the specified authoritative pre-version.

Concurrent or stale writes are rejected.

Atomic target-side mutation and receipt

The target changes its authoritative state.

In the same transaction, it records:

request hash;

authenticated caller;

pre-state version;

post-state version;

idempotency key;

authoritative commit identifier.

Transactional outbox or durable event emission

A post-commit event is derived from the committed transaction rather than emitted optimistically before commit.

Independent readback

READBACK confirms the authoritative post-state and commit identifier.

Separate owner Acceptance

Owners accept the exact result and version as a distinct act.

Workflow success does not synthesize Acceptance.

This is a conventional transaction, authenticated-command and durable-workflow design. It does not require a novel protocol.

Within the target's digital trust boundary, it converts the causal statement from:

A4 reported an attempt, and the desired state was later observed.

to:

The authoritative target recorded that an authenticated A4 command caused this exact version transition in the target's own commit boundary.

Lawful strong-center solution

A lawful strong center can also eliminate the gap when all of the following are true:

it has legitimate authority to receive or enforce the owners' decisions;

it has exclusive or serialized control over authoritative target writes;

all relevant competing writers are either prohibited or recorded;

it records the exact request, actor and version transition atomically;

owner Acceptance remains an explicit owner act unless legitimately delegated;

its audit history is protected against the relevant administrator threat.

Under those conditions, six independently signed synthetic services are not necessary for causal attribution. A central transactional authority may be simpler and stronger.

This is a fully positive result for the research question. Existing central infrastructure should be treated as solving the bounded problem whenever its authority and trust assumptions are valid.

Limits of the existing-tech solution

The mature composition solves only the causal gap that lies inside the authoritative digital target.

It does not automatically prove:

that an external physical machine performed the intended action;

that a human adopted the result;

that an organization accepted liability;

that the target system itself represents reality correctly;

that a lawful delegation actually exists;

that distinct owners are independent;

that the administrator cannot rewrite all local evidence.

For physical Effect, the equivalent mature solution requires a trusted actuation boundary:

authenticated controller-to-actuator command;

actuator-generated operation receipt;

tamper-resistant or independently administered sensor readback;

correlation to the exact physical object and operation;

explicit owner Acceptance where institutionally required.

For organizational Authority and Acceptance, legal delegation, identity governance and human acts remain necessary. A technical controller cannot create them by recording that they occurred.

Revised judgment

The v3 evidence supports a meaningful revision in one dimension:

The two new E1/E5 outcomes survived the specific known semantic-label, identifier, manifest-hash-oracle and inherited-CLI fairness attacks under the instrumented arm-view boundary.

It does not justify revising the causal claim ceiling:

The evidence still does not show that A4 caused the authoritative target transition rather than coexisting with an independently caused transition.

Accordingly:

Blindness/fairness judgment: upgraded for the tested channels and two runs.

Bounded evaluator feasibility judgment: retained.

Causal exact-task-success judgment: withheld.

Real authority, Effect and Acceptance judgment: withheld.

System-level or V1/V2 completion judgment: withheld.

Best next experiment: CT-001, the hidden-branch exogenous target twin.

Best positive existing solution: authoritative target-side atomic mutation receipt, implemented either by a mature distributed composition or a lawful strong center.
