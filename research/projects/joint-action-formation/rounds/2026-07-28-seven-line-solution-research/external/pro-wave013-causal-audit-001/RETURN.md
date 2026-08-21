Below is the independent causal audit. External sources are used only to identify mature solution families; they do not validate the reported local executions.

编辑
PRO-WAVE013-CAUSAL-AUDIT-001
Independent audit of packet v1-minimal
Executive judgment

The packet supports a real but narrow positive result:

In one frozen synthetic closed world, a composition of deterministic, process-separated, cryptographically signed services can make one exact successful episode and one bounded refusal adjudicable by an evaluator that does not import the producer implementations.

More specifically, it demonstrates a viable mechanism for run-scoped evidence integrity, exact-request binding, typed stage separation and deterministic adjudication on the two exercised cases.

It does not yet establish causal attribution from the exact A4 execution to the observed effect, real organizational authority, real owner acceptance, open-world refusal correctness, resistance to a controller that can coherently regenerate the entire run, or system-level superiority over a legitimate central implementation.

The current system-level judgment should therefore be:

Positive constructive feasibility for a bounded attested-execution and refusal-adjudication subproblem; insufficient evidence for a general joint-action solution.

The highest-information next experiment is not another nominal case. It is a causal-twin differential experiment in which the same authorized request is followed by the same target state and observations, but the state transition is caused once by A4 and once by an independent hidden actor. That experiment tests the missing bridge between signed provenance and causal success.

1. Independent problem reconstruction

The experiment should not be reconstructed as:

Can six services produce a complete signed packet that passes a verifier?

That formulation would make document completeness and signature validity the target and would allow the experiment to prove itself.

The stronger and more relevant problem is:

Given an exact requested operation in a bounded multi-owner world, can an evaluator that does not trust the controller or executor implementation correctly distinguish:

an authorized exact operation that caused the required target-domain change and was subsequently accepted;

a correct bounded refusal;

an invalid, stale, substituted, unsafe or causally unsupported episode?

Let:

(R) be the exact byte sequence of the EXECUTE request;

(T_0@v_0) be the authoritative target state and version before execution;

(T_1@v_1) be the required post-state;

(A_i(R,t)) be owner (i)'s valid authority decision for (R) at execution time;

(O_{A4}(R)) be an actual A4 execution occurrence;

(\Delta_T(R)) mean that the exact execution caused the authoritative transition (T_0@v_0 \rightarrow T_1@v_1);

(E(R)) be a target-domain effect observation;

(Acc_i(R)) be a non-substitutable owner acceptance;

(F(R)) be valid finality;

(B(R,\Omega)) be a correct refusal within a frozen search and authority boundary (\Omega).

The evaluator is then approximately:

[
V(Evidence,\ TrustRoots,\ Rules)
\rightarrow
{SUCCESS,\ BOUNDED_REFUSAL,\ INVALID,\ UNSAFE,\ UNKNOWN}
]

The critical non-implications are:

[
Signature \not\Rightarrow Authority
]

[
Execution\ occurrence \not\Rightarrow Target\ effect
]

[
Temporal\ succession \not\Rightarrow Causation
]

[
Readback \not\Rightarrow Correct\ causal\ attribution
]

[
Effect \not\Rightarrow Adoption
]

[
Adoption \not\Rightarrow Acceptance
]

[
Acceptance \not\Rightarrow Finality
]

The experiment therefore contains four distinct assurance layers:

Evidence integrity: Were records altered, substituted, replayed or mixed across runs?

Semantic binding: Do the records refer to the exact task, identities, versions and deadlines?

Causal grounding: Did the exact authorized execution cause the observed target transition?

Institutional validity: Were the authority, effect, acceptance and finality acts performed by entities entitled to perform them in the relevant real domain?

The packet provides meaningful evidence for layer 1 and parts of layer 2. It provides limited evidence for layer 3 and no real-world establishment of layer 4.

A correct BOUNDED_REFUSAL should also be interpreted carefully. It can mean:

No qualifying execution was available under the enumerated services, current states, policies, deadline and inquiry boundary.

It cannot, from this packet alone, mean:

No valid route existed anywhere in the open world.

2. Evidence-supported claim ceiling
Strongest defensible claim

The strongest claim supported by the stated evidence is:

Constructive bounded feasibility: Under one frozen synthetic world, its supplied trust roots and its declared semantics, a deterministic composition of six process-private owner services, one target, one executor and a code-independent evaluator can produce and adjudicate a run-scoped signed evidence graph for at least one exact-task success and one correct bounded refusal. The implementation also detects the specifically exercised malformed, unsafe, stale, aliased, contradictory, duplicate and cross-run variants.

This is a positive result. It shows that no general model, novel Agent protocol or probabilistic reasoning system is inherently required for this bounded slice.

The slice being solved is best named:

Closed-world attested execution/refusal adjudication.

It includes:

exact request binding;

process and signing-key separation;

typed separation of authority, occurrence, readback, effect observation, acceptance and finality;

signed hash-chain histories;

execution-time expiry and deadline enforcement;

run-scoped evidence;

duplicate-execution idempotency;

deterministic external evaluation;

at least some distinction between success, bounded refusal, invalid run and unsafe effect.

Why the ceiling stops there

The evidence consists of two currently successful case outcomes, several earlier rejected runs and a collection of targeted tests. That establishes neither universal soundness nor statistical reliability.

In particular:

Successful evaluation of E1 does not establish that every accepted packet corresponds to a causally correct execution.

Correct evaluation of E5 does not establish refusal completeness outside its frozen boundary.

Earlier rejected runs show that the evaluator is not an accept-all function, but do not measure its false-positive rate against the strongest adversarial constructions.

Separate processes and keys demonstrate technical separation, but not separate administrative control or non-collusion.

An evaluator that does not import service code avoids one form of common implementation coupling, but it still relies on the truthfulness and authority of the evidence producers, the trust-root configuration and the semantics assigned to their statements.

Content-addressed parent edges establish declared derivation and packet structure. They do not by themselves prove physical or counterfactual causation.

Claim ladder
Candidate claim	Current status
The packet is internally signed and run-bound	Supported for the tested paths and mutations
The evaluator can distinguish several outcome classes	Supported for E1, E5 and the reported rejected runs
The exact request, deadline and selected identities are bound	Supported within tested constructions
Duplicate execution is controlled	Supported for the tested idempotency case
A4 caused the observed target effect	Not established
Owner services represent non-substitutable organizational authority	Not established
Observed Effect and Acceptance are real-world acts	Not established
Bounded refusal is complete in an open world	Not established
All eight frozen cases are solved	Not established
This composition is better than a strong central baseline	Not tested
A new protocol or architecture is necessary	Unsupported
The whole joint-action problem is solved	Unsupported

The strongest system-level statement is therefore an existence claim, not a generality, necessity or superiority claim.

3. Strongest concrete remaining false-positive construction
Causal-twin construction

The strongest construction that does not require forged signatures is a pair of worlds with the same evaluator-visible sequence but different causal truth.

Genuine world (W_G)

All six owners validly authorize exact request (R).

A4 receives (R).

A4 performs the target mutation.

The authoritative target moves from (T_0@v_0) to (T_1@v_1).

Sensors observe the resulting condition.

READBACK returns (T_1@v_1).

Effect, Acceptance and Finality are signed.

The evaluator returns SUCCEEDED.

False-positive world (W_F)

The same six owners validly authorize the same (R).

A4 receives (R) and produces the expected occurrence record, but its operation is a no-op, fails before commit, or affects a non-authoritative object.

During the allowed interval, a target-side scheduler, administrator, recovery process or unrelated actor (H) independently changes the authoritative target to the same (T_1@v_1).

The 46 sensor samples honestly observe (T_1).

READBACK honestly reports (T_1@v_1).

The effect observer and owners honestly accept the resulting state.

The evidence records include the A4 occurrence and request as content-addressed parents.

The evaluator returns SUCCEEDED.

Every signature can be genuine. Every observation can be accurate. The final target state can be real.

The false statement is:

[
O_{A4}(R) \land T_1
\Rightarrow
\Delta_T(R)
]

The packet shows that the execution and effect are related in the evidence graph. It does not necessarily show that the former caused the latter.

This construction can survive the currently listed tests:

Target-request byte binding: the same exact (R) was submitted.

Expiry and deadline: the unrelated transition occurs within the permitted window.

Readback causal parents: the parent hashes are present, but the relationship is asserted rather than interventionally established.

Private-alternative contradiction: every queried source can consistently report (T_1).

Identity aliasing: all identities can be genuine.

Duplicate idempotency: only one actual target transition occurs.

Run scoping: every artifact can be newly generated for the run.

The attack disappears only if the occurrence is stronger than an executor statement—for example, if it is an authoritative target-generated atomic commit receipt binding:

exact request hash;

authenticated executor identity;

pre-state identity and version;

post-state identity and version;

an unrepeatable mutation or transaction identifier;

the target's serialization or commit position;

a live challenge unavailable before execution.

Whether the current occurrence has these semantics is not established by the packet.

There is an important definitional fork:

If ExactTaskSuccess means only “a valid attempt was followed by the requested state,” (W_F) is not a false positive—but the claim is merely outcome correlation.

If it means “the exact authorized execution caused the requested effect,” (W_F) is a decisive false positive.

Given the task's causal framing and the use of causal-parent language, the second interpretation is the relevant one.

Stronger boundary variant

Under the explicitly untested hostile same-user whole-run threat, the controller can potentially create a coherent shadow world: regenerate service states, logs, sensor samples, acceptances and finality using all run-local keys, rather than modifying an individual node.

Hash chains and signatures then demonstrate consistency of the regenerated history, not continuity with a history committed outside the attacker's control.

Distinct keys do not solve this if all keys, process launches and genesis records remain under one administrative root. An append-only transparency log can make post-commit rewriting detectable, but the log still records claims rather than proving that their underlying physical or organizational propositions are true. Sigstore's Rekor, for example, is designed to make entries append-only and publicly auditable; its own documentation separately notes limits on treating log time as an externally verifiable physical timestamp.

4. Best existing/combined solution interpretation and strongest alternative
Best existing-solution interpretation: an attested deterministic saga

The strongest charitable interpretation is not “a new Agent protocol.” It is:

A domain-specific, cryptographically attested saga or durable workflow with explicit authority, target readback, acceptance and finality stages.

Its mature components are recognizable:

Owner-side policy and authority services

Each owner evaluates the exact request against its own current state and policy and signs the result. A policy engine such as OPA can implement deterministic policy decisions over structured requests, but OPA explicitly distinguishes policy evaluation from the authoritative external data supplying world state. Therefore, the owner's actual mandate and state source must remain authoritative outside the policy evaluator.

Durable workflow or saga orchestration

A workflow engine can preserve state across failures, retries and long-running operations. Temporal, for example, persists workflow event histories and replays them after failures. That addresses durable progression, not the truth of authority or physical effect.

Idempotent execution

An exact idempotency key or operation identifier can prevent a retry from producing duplicate mutations. AWS documents this mature design pattern for mutating APIs: repeated requests can return safely without repeating the side effect.

Signed provenance and verification rules

The evidence graph resembles an application-specific in-toto layout: signed records establish which identities performed declared steps and in what declared order. In-toto is a mature example of signed step metadata and verifier-side expectations, though its software-supply-chain semantics do not themselves establish real-world authority or effect.

Target-issued authoritative receipt

The target should produce an atomic receipt at mutation time, rather than relying on an executor's self-report followed by a later state observation.

Independent readback or witness

The authoritative target state should be read from a source that the executor cannot rewrite, ideally with the target commit identifier and version.

Explicit owner acceptance

Acceptance should remain a separate owner act, not a conclusion inferred from successful workflow progression.

Externally witnessed run commitment

A transparency service or evaluator-held commitment can prevent post hoc whole-run replacement.

This composition is enough to solve the bounded technical problem if its trust assumptions are accepted. The likely contribution is therefore a joint-action evidence profile, threat model and evaluation method, not necessarily a new cryptographic or orchestration primitive.

Strongest alternative: legitimate central transaction and authority system

The strongest competing solution is a legitimate strong center:

one authoritative system of record;

exact versioned tasks;

owner approvals or delegated mandates;

serializable target-state transactions;

idempotent commands;

durable workflow for external operations;

target-side readback;

explicit human or organizational acceptance;

append-only audit records.

Within one accepted administrative and legal boundary, a central system can be simpler and stronger than six independently signed synthetic services. PostgreSQL, for example, provides serializable transaction isolation and durable commit semantics for state inside one database boundary.

The central alternative wins when:

all owners legitimately delegate the relevant decisions to the center;

the target is inside or reliably integrated with its transaction boundary;

a central system of record is institutionally acceptable;

owner acceptance can be collected as an explicit workflow act.

It loses when:

the center is not authorized to impersonate an owner;

principals must retain independent revocation, refusal or disclosure control;

target and owner systems lie in mutually independent administrative domains;

no shared central truth authority is acceptable.

The present packet does not test which condition holds. It therefore cannot establish that the distributed composition is necessary or preferable.

A general model is not the strongest alternative for this bounded task. A model may help diagnose failures or translate formats, but deterministic policy, execution and verification components are stronger as the decision boundary. Human approval remains a legitimate component wherever Authority or Acceptance is inherently institutional rather than computational.

5. Highest-information next local experiment
Experiment: blinded causal-twin differential test

The next experiment should directly test whether the evaluator distinguishes causal execution from post hoc outcome correlation.

Fixed conditions

Freeze:

exact request bytes (R);

owner states and authority responses;

target identity;

initial target state and version (T_0@v_0);

desired state (T_1);

deadline;

executor identity;

evaluator rules;

artifact schema.

The evaluator must remain blind to the selected arm and must not import world, executor or service code.

Arm G: genuine execution

A4 executes (R).

The authoritative target transition is performed by the A4-triggered operation.

Normal occurrence, sensors, readback, effect, acceptance and finality evidence are emitted.

Arm X: exogenous causal twin

A4 receives the same (R) but no-ops or fails before target commit.

An unreported target-side scheduler or adversarial helper changes the target to the same (T_1) within the deadline.

Sensors, readback, effect observation, acceptance and finality proceed normally.

All evidence is signed by the expected identities.

No individual artifact is malformed, stale, aliased, duplicated or copied across runs.

The experiment should attempt to make the evaluator-visible packets equivalent under the current schema except for evidence that genuinely requires the target to attribute its atomic transition to A4 and (R).

Primary observable

The primary measurement is the evaluator's classification of Arm X:

SUCCEEDED

UNSAFE_EFFECT

INVALID_RUN

UNKNOWN or equivalent abstention

another explicitly defined outcome.

No new aggregate score is required.

Interpretation of outcomes

G succeeds; X is rejected or deferred for missing causal evidence

This would materially upgrade the judgment:

The mature composition supports bounded causal execution adjudication, not merely signed temporal correlation.

The upgrade would still depend on the target receipt's trust root and would not establish real organizational authority or open-world completeness.

Both G and X succeed

This would materially downgrade the claim:

The system verifies an internally consistent sequence of authorization, attempt and desired outcome, but cannot attribute the outcome to the exact execution.

ExactTaskSuccess would need to be renamed or weakened unless a target-side causal receipt is added.

Both G and X are rejected

The evidence requirements or evaluator rules are not yet operationally sufficient for valid success. The result would expose a safe-recall or liveness problem.

G is rejected; X succeeds

This would reveal a severe inversion or hidden dependency in the evaluator.

Diagnostic artifact

For each arm, record whether the current schema contains an authoritative target-generated object equivalent to:

[
C =
Sign_T(
hash(R),
nonce,
executor_identity,
target_id,
v_0,
v_1,
commit_id
)
]

The nonce should be generated after authority evidence is frozen and retained by the evaluator or another trust domain. If the same user is the adversary, the nonce or commitment must live outside that user's rewritable run directory—such as an evaluator-held hardware key, separate machine or independently controlled witness. Otherwise whole-run rewrite resistance is not genuinely being tested.

Why this experiment has the highest information value

Running the remaining nominal cases would improve coverage but would not change the type of claim being made.

The causal-twin experiment can change the judgment from:

signed closed-world provenance and adjudication

to either:

bounded causal execution verification

or:

outcome correlation incorrectly labelled as exact task success.

It therefore tests a structural assumption rather than adding another example.

6. What remains unknown
Case and distribution coverage

Outcomes for the other six frozen cases.

Behavior across state variations within each case.

False-positive and false-negative rates under an adversarially generated corpus.

Whether UNKNOWN, DEFER and REJECT are correctly separated.

Safe recall when evidence is incomplete but execution is valid.

Competing solutions

A central reference monitor using the same world and permissions.

A conventional workflow plus database and human approval.

An attestation framework without the proposed custom graph.

A manual institutional process.

A general-model-assisted implementation.

Development, runtime and maintenance cost across these arms.

Without these arms, the result supports feasibility but not necessity, uniqueness or comparative value.

Causal grounding

Whether the signed occurrence is an attempt receipt, executor self-report, target acceptance receipt or atomic target mutation receipt.

Resistance to exogenous changes, scheduled changes and recovery actions.

Concurrent valid causes.

Causal attribution when multiple requests seek the same final state.

Counterfactual behavior when the exact A4 execution is removed.

Whether the 46 sensor samples are independent observations or correlated projections of one synthetic state source.

Authority and owner acts

Whether service keys are bound to real organizations or owners.

Whether the controller can operate or replace those keys.

Delegation, revocation, expiry and challenge semantics in real institutions.

Whether an owner service's policy decision is legally or institutionally equivalent to the owner's act.

Whether Acceptance is informed, voluntary, version-specific and non-substitutable.

Effect and acceptance

Whether the target readback corresponds to an authoritative real-world system.

Whether sensor observations establish the intended domain effect rather than a proxy state.

Adoption, use, benefit and settlement after the observed effect.

Reversal, compensation and dispute handling.

Multiple owners disagreeing about effect or acceptance.

Security boundary

Whole-run regeneration after observing the expected result.

Collusion among evidence producers.

Compromise of one or more private keys.

Key creation and trust-root provenance.

Key rotation and revocation.

Forked histories presented to different evaluators.

Replay across task versions or evaluator configurations.

Rollback of target state after finality.

Resistance when the same operating-system administrator controls all processes.

Time and ordering

Real wall-clock behavior.

Trusted time source.

Revocation and deadline races.

Concurrent events with no total order.

Whether logical minutes correspond to any external temporal constraint.

Whether content-addressed parenthood is being used as a substitute for causal or temporal proof.

Open-world refusal

Undiscovered partners or executors.

Unqueried permissions or resources.

Alternative task representations.

New authority acquired during the episode.

Refusal under incomplete or refused disclosure.

Whether a bounded refusal is incorrectly presented as impossibility.

Lifecycle and practical value

Setup and integration effort.

Per-run latency and compute cost.

Key and certificate operations.

Failure recovery.

Human review burden.

Schema and policy migration.

Long-term evidence retention.

Cross-organization deployment.

Debugging and incident response.

Net advantage over a simpler trusted center.

Final determination

The experiment has crossed an important threshold: it is no longer merely a document, proposed protocol or test suite. It reports actual executions in which an implementation-independent evaluator accepted a success and a bounded refusal and rejected several earlier unsafe or invalid runs.

That supports a constructive engineering result.

The correct ceiling, however, is:

A mature deterministic composition can solve a bounded closed-world evidence-binding and adjudication slice of joint action under synthetic trust and truth assumptions.

The current evidence does not support:

The composition has established that the exact authorized execution caused a real effect accepted by real independent principals, or that it solves the wider joint-action problem.

The decisive missing distinction is not another signature or another nominal case. It is the distinction between:

[
authorized\ execution
\rightarrow
observed\ desired\ state
]

and:

[
authorized\ execution
;\mathbf{caused};
observed\ desired\ state
]

The causal-twin experiment is the single local test most likely to change that judgment.

A compact evaluator-facing decision memo or a formal assumptions–theorem–counterexample version would be the natural derivative of this audit.
