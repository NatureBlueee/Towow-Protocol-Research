思考了 13m 19s
PRO-G3-001 — Independent reconstruction of reachability formation
Bottom line

I would not retain the proposed five-way taxonomy as a set of mutually exclusive causal explanations. It mixes three different questions:

Did a qualified path or policy already exist?

Could the controller know, find, or reliably execute it?

Was the reported success valid under the original task and authority structure?

The cleaner reconstruction is a layered one:

Epistemic change: the world did not change; knowledge or search improved.

Ordinary state preparation: the world moved through already-authorized transitions such as enabling, repairing, granting, committing, or building a known adapter.

Transition-system or institutional extension: the available action, interface, policy, or authority structure itself changed.

Task mutation: the goal, floor, required principals, resource account, or qualification rule changed.

Invalid success: the old task was not actually satisfied because authority, identity, evidence, cost, or postcondition was unsound.

The most important consequence is this:

If the disclosures, permission requests, commitments, repairs, adapter builds, or human escalations that preceded success were themselves valid actions available from S0, within the original resource account and without violating Q, then they were simply the prefix of a path from S0.

In that case, global reachability was not created. Immediate executability changed, but a qualified preparatory policy already existed.

A distinct reachability-formation claim survives only relative to a declared boundary:

the original task remains semantically identical;

all permitted preparatory and human actions are included in the pre-state closure;

the pre-state is proven unreachable within a finite, declared model and budget;

a valid intervention changes the transition system or institution;

the post-state becomes reachable;

the intervention is causally necessary;

no controller substitution or self-report is used.

Even that would establish a bounded reachability change, not the need for a new method. An ordinary adapter build, policy amendment, human process, or central planner may fully solve it.

1. Independent problem reconstruction
1.1 The object should be a qualified contingent policy, not merely a path

With local information and independent principals, the controller usually cannot commit in advance to one fixed action sequence. It must choose actions conditionally:

ask a principal a question;

receive a disclosure, refusal, approval, or counterproposal;

obtain a properly scoped authorization;

select a route based on that response;

stop correctly if a necessary principal refuses.

The relevant object is therefore a policy:

σ:observed history→request, probe, execution action, escalation, or stop

A complete outcome space should contain at least:

QUALIFIED_SUCCESS

VALID_PRINCIPAL_REFUSAL

BOUNDED_UNREACHABLE

UNRESOLVED_MODEL

INVALID_APPARENT_SUCCESS

A system does not “solve” the problem by forcing every case to succeed. It closes the problem when it can produce a qualified result or correctly determine why no qualified result is presently obtainable.

1.2 Frozen task envelope

I would define the frozen task as:

τ=⟨S
0
	​

,G
0
	​

,V
min
	​

,Q
0
	​

,P
\*
,Λ
0
	​

,B,H,≡
τ
	​

⟩

Where:

S0: exact initial world snapshot.

G0: original goal.

Vmin: unacceptable-value floor.

Q0: qualification predicate over the full trace and final state, not only the endpoint.

P*: principals whose participation or acceptance is required.

Λ0: authority map for execution actions and preparatory or model-changing actions.

B: common resource account, including probes, human work, setup, retries, adapter construction, and verification.

H: time or action horizon.

≡τ: declared path-equivalence relation.

The equivalence relation is necessary because two traces can end in the same visible state while differing materially in:

which principals participated;

whether the action was authorized;

cost;

repeated or hidden effects;

privacy loss;

acceptance;

responsibility;

reversibility;

timing.

Without a frozen equivalence relation or a sufficiently complete Q0, the phrase “an equivalent path already existed” is underdefined.

1.3 World model and missing state

A minimally adequate world state is not just the business or physical state. It contains:

s
t
	​

=(x
t
	​

,k
t
	​

,c
t
	​

,u
t
	​

,m
t
	​

,j
t
	​

,θ
t
	​

,i
t
	​

,r
t
	​

,e
t
	​

)

Where:

x: domain state.

k: knowledge and disclosures available to each participant.

c: operational capabilities and tool availability.

u: current authorization, delegation, revocation, and scope.

m: commitments, consent, acceptance, and outstanding obligations.

j: interface and semantic compatibility.

θ: principals’ private decision conditions or response policies.

i: identity, credential, nonce, freshness, and provenance state.

r: cost, time, rate, privacy, and other resources.

e: independent evidence and target-domain witness state.

The packet freezes several important objects, but it does not explicitly freeze the complete action language, preparatory-action closure, principal response functions, or reachability quantifier. Those omissions are causally decisive.

1.4 Three different meanings of “reachable”

Independent principals make the quantifier over their decisions important.

Existential reachability

There exists some sequence of approvals and actions that reaches Q.

This is weak. It may amount to assuming that every independent principal voluntarily says yes.

Actual-policy reachability

Given the principals’ frozen response functions in the episode, there exists an observation-contingent controller policy that reaches Q.

This is the appropriate definition for causal classification of a particular synthetic episode.

Robust reachability

There exists a policy that reaches Q under every principal response allowed by the declared model.

This will often be false when a principal has a legitimate veto. A good system must treat a valid refusal as a correct terminal result, not as planning failure.

The experiment should report all three where practical rather than silently moving between them.

1.5 Layered reachability

I would divide admissible actions into four layers.

Layer	What it contains	Examples
L0 — execution	Direct actions in the currently exposed domain	transfer, deploy, project, read back, settle
L1 — preparation	Actions already defined that alter current state or enablement	probe, request approval, enable endpoint, renew credential, sign commitment, repair, build a known adapter
L2 — model or institutional extension	Actions that alter the available action schema, policy model, interface language, or authority structure	register a new adapter type, add a new policy rule, create a new delegation class, introduce a new operator
L3 — task mutation	Changes to the problem being judged	lower value floor, remove a required principal, weaken exact-once, change Q, expand budget

Let:

R
k
	​

(τ,M)=1

mean that a qualified policy exists using actions through layer Lk.

The formation depth is:

d(τ,M)=min{k:R
k
	​

(τ,M)=1}

This yields a cleaner classification:

d=0: direct path exists.

d=1: success requires ordinary preparation.

d=2: success requires model or institutional extension.

only L3 succeeds: it is a different task.

no level succeeds: bounded unreachable.

verifier rejects: invalid apparent success.

Knowledge and search quality are orthogonal to this depth. A controller can fail to find an L0 path even though it exists.

1.6 The prefix-closure test

This is the simplest and strongest causal test.

Suppose:

I is a valid preparatory policy from S0 to state SI;

every action in I was already available and properly authorized under the frozen model;

its cost and side effects are counted under the original B and Q0;

π is a qualified policy from SI to the goal.

Then the composition:

I;π

was a qualified policy from S0.

Therefore:

R
1
	​

(τ,M
0
	​

)=1

even if R0 became true only after executing I.

This means:

enabling an existing endpoint;

requesting a valid grant;

recovering a service;

obtaining a commitment under an existing decision process;

constructing an adapter using an already-available build operation;

escalating to an authorized human through an existing workflow

do not by themselves prove new closure reachability.

They may be practically important. They may convert a contingent, indirect, or unreliable possibility into immediate execution. But they do not establish that no path existed from S0.

The lemma fails only if, for example:

the preparatory action was not in the old action closure;

it required a new authority or policy rule;

it exceeded the original budget or horizon;

it violated a trace-level qualification condition;

the principal response policy itself changed;

the preparation was an exogenous event rather than an available action.

That is exactly why the action and meta-action boundary must be frozen.

1.7 Reconstructed causal classes

I would replace the original taxonomy with the following.

A. Latent-path discovery

The task and world transition system are unchanged. A qualified path already existed, but the controller did not know, search, select, or trust it.

B. Fixed-model preparation

A path became directly executable after moving through valid transitions already represented in the old model.

Activation, repair, approval, commitment, known-adapter construction, and ordinary workflow amendment usually belong here.

C. Model or institutional extension

A new action, interface, policy rule, authority relation, or representational object was introduced that was not reachable through the old preparatory closure.

This is the strongest candidate for genuine bounded reachability formation.

It is still not evidence that a bespoke “formation method” is required. Ordinary engineering, governance, or human intervention may be sufficient.

D. Principal-policy transition

A required principal’s decision changed.

This has two subcases:

If a fixed local decision rule says “approve when condition X is offered,” and the controller obtains X through existing actions, this is fixed-model preparation.

If the principal’s preference, authority, legal status, or response rule itself changes, the world model changed.

A synthetic trace cannot establish that a real principal recognized, preferred, accepted, or assumed responsibility for anything.

E. Task mutation

The old problem remains unreachable, but a modified goal, value floor, principal set, qualification rule, horizon, or resource budget becomes reachable.

F. Invalid apparent success

The surface result looks correct, but the trace fails old Q because of impersonation, stale authority, self-report, hidden repeated effects, missing target witness, cost erasure, or another invalid step.

G. Mixed episode

Several interventions are jointly required. There may be no single cause.

For an intervention set I={i
1
	​

,…,i
n
	​

}, the experiment should find minimal sufficient subsets:

J⊆I:R(M
do(J)
	​

,τ)=1

while every proper subset of J remains unreachable.

Counterfactual dependence and minimality are standard elements of actual-causation analysis; here they can be operationalized directly through intervention ablation rather than treated as philosophical labels. 
arXiv

2. Packet readback: direct statement / source interpretation / inference / unknown
Epistemic status	Readback
Directly stated	The research contract freezes S0, V0, Q, necessary principals, authority loci, target-domain witness, and a common resource account before classification.
Directly stated	One local synthetic episode produced a working cross-process trace after authority delivery, negative-decision handling, recovery, canonical readback, and target projection were added. Producer-only and wrong-authority controls produced no projection.
Directly stated	That report says deterministic or least-privilege central execution is preferable after the interface exists; it did not run a matched strong-center formation intervention and does not establish human recognition, business value, production validity, frequency, or A2A uniqueness.
Directly stated	A later local synthetic wave found that an earlier all-green implementation was vulnerable to hidden repeated effects, truth or log leakage, reconstructable keys, erased metering, stale replay, and self-reported identity.
Directly stated	The repaired version added process separation, runtime-random signatures, exact binding, policy checks, attempt-time idempotency, independent postcondition and acceptance levels, witness quorum, runner-owned identity, authoritative cost logs, and paired hidden worlds. Its 52 tests passed under a same-research-process root recheck.
Directly stated	The later wave was local synthetic evidence, not a blind independent implementation, and did not test general reachability formation.
Source interpretation	“A newly working path” and “the interface was formed” are the source report’s interpretation of the episode. They are not direct evidence that the pre-state had no qualified policy.
Source interpretation	The lack of projection in producer-only and wrong-authority controls is interpreted as evidence of target-side and authority-specific execution. That supports the validity of the reported path inside the tested model, but does not classify why it became reachable.
Source interpretation	The repaired all-green suite is interpreted as evidence that execution and evidence integrity were substantially improved.
My inference	The later wave primarily strengthens the predicate Verify(trace). It makes false success harder. It does not establish R(S0)=0.
My inference	The prior controls help distinguish valid execution from some forms of self-report or authority substitution, but they do not distinguish discovery from activation, preparation, or model extension.
My inference	Because no matched strong-center formation intervention was run, there is currently no comparative evidence that a special formation method adds value over a planner, workflow, human escalation, adapter, or their composition.
My inference	Because no complete pre-state action closure or bounded unreachability certificate is reported, “first reachable” is not yet supported.
Unknown	Whether authority delivery, recovery, negative-decision handling, canonical readback, and projection were actions already available from S0.
Unknown	Whether their costs, human effort, setup time, and failed probes were charged to the frozen resource account.
Unknown	Whether all semantically material parts of Q were frozen as executable code and test vectors rather than only descriptive text.
Unknown	Whether another equivalent route existed at S0.
Unknown	Whether the action model was complete enough for an unreachability claim.
Unknown	Whether formation-phase actors were included in the frozen principal and authority map.
Unknown	Whether principal response policies were fixed, or whether a principal’s willingness or authority changed during the episode.
Unknown	Whether a central planner with the same information, tools, authority calls, human escalation, and budget would have produced the same result.
Unknown	Whether the reported sequence was causally minimal or contained redundant interventions.
Unknown	Whether the same result survives a blind implementation by a team that did not construct the vocabulary, tests, or repaired system.

The repaired test suite should therefore be retained, but repositioned:

It is a promising execution-validity layer for a future causal experiment, not yet evidence of reachability formation.

3. Candidate solution matrix, including no-new-mechanism outcomes

A candidate fully closes the bounded problem when it can produce one of:

a qualified policy;

a valid principal refusal;

a checkable bounded-unreachability certificate;

an explicit unresolved-model result rather than fabricated success.

Existing planning machinery is a serious baseline. Classical planning explicitly separates state variables, action set, initial state, and goal; contingent planning treats sensing actions under partial observation; action-model-learning research addresses incomplete operator models; and counterfactual-planning work distinguishes changes to actions, initial state, and goals. None of this automatically solves distributed authority, but it means that “planner + sensing + model repair + verification” must be tested before a residual is presumed. 
arXiv
+2
AAAI
+2

Candidate	Exact conditions under which it fully closes the problem	What a positive result would mean
None needed: reuse or discovery	A valid replay path exists from exact S0, using only pre-existing actions, authorities, resources, and the old Q.	The episode was a search, indexing, selection, or utilization failure. No reachability-formation method is needed.
Existing contingent planner or workflow planner	Probes can be represented as sensing actions; enablement, grants, commitments, repairs, and known builds are represented as state-changing actions; the finite horizon is searchable; Q is executable.	The problem is ordinary planning under partial information and changing state.
Strong central planner with human escalation	The central component can query principals and synthesize plans but cannot sign or act for them; actual privileged actions are routed to valid authority holders; the human has the same legally disclosable information and action channels as any candidate; human cost is charged.	Centralized computation is sufficient even though authority remains distributed. Non-impersonable authority does not by itself imply a new protocol.
Mature workflow, IAM/policy, adapter registry, audit, and exception handling	Blockers fall into known classes; policies and schemas are sufficiently stable; approvals can be routed; exception humans can resolve remaining cases; independent target and cost evidence exists.	A composition of existing enterprise mechanisms closes the problem.
Human-led coordination	Frequency is low, latency is tolerable, principals are reachable, humans can understand local conditions and obtain valid approvals, and the trace is recorded for reproducibility.	No automated formation mechanism is necessary. The correct solution may simply be a disciplined human process.
Adapter or policy engineering	The only blocker is semantic, technical, or policy incompatibility; the original goal and authority structure are stable; an authorized engineer or administrator can construct or register the missing object.	A genuine object-level path may be created, but ordinary engineering or governance is the complete solution.
Combined coordinator plus local authoritative oracles	Private information cannot be centralized but principals can answer bounded queries, return signed decisions, and perform actions through stable interfaces; query leakage and privacy budgets are acceptable.	Distributed information and authority are handled by composition. A new general protocol is not yet implied.
Action-model learner or model-repair component	The main difficulty is an incomplete or inaccurate action model, and safe probes or traces can identify a usable model without violating Q.	The contribution is model acquisition or repair, not a new causal kind of formation.
New formation-specific method	After capability parity, the candidate repeatedly produces qualified outcomes or correct bounded-unreachability results where a strong central planner, human escalation, workflow stack, and adapter/model-repair composition fail under identical information, actions, authority endpoints, budget, and verification.	There is evidence of method-level value. It still does not prove that “formation” is an irreducible ontological primitive.

A particularly important baseline is a centralized policy synthesizer with decentralized execution. The planner may be central while every authorization, commitment, acceptance, and privileged action remains with its proper principal. Treating “central” as synonymous with “controller impersonates everyone” would create an artificially weak baseline.

4. Causal distinctions and failure modes
4.1 Missing causal variables that must be added

The next protocol should freeze or record:

The complete declared action language, including probes, repair, approval, credential renewal, adapter construction, policy amendment, and human escalation.

The meta-action boundary: which actions can create or modify other actions, policies, objects, or authority relations.

Principal response functions, or at least versioned scripted decision policies in the simulator.

The quantifier over principal behavior: existential, actual-policy, or robust.

The actor and authority for every intervention, including model-changing interventions.

Trace-level Q, including side effects, repeated attempts, privacy loss, cost, timing, and failed actions.

Semantic task invariance, not merely identical text or a task identifier.

The resource and horizon bound used for any unreachability claim.

The controller’s information state, distinct from the true world state.

Search completeness or algorithm limits, so “not found” is not mistaken for “does not exist.”

Path equivalence, including material side effects and principal participation.

Time, expiry, revocation, and replay state.

Whether probes themselves alter the world, trust, privacy budget, or principal policy.

Independence of the outcome, authority, cost, and acceptance verifiers.

Current NIST digital-identity guidance distinguishes identity proofing, authentication, and federation assurance as separate functions. By analogy—not as direct applicability to this simulator—actor identity, control of a credential, task-specific authority, and target acceptance should be verified as separate predicates rather than collapsed into “a signature exists.” 
NIST 页面

4.2 Decisive counterfactuals
Explanation	What changed	Decisive counterfactual
Latent discovery	Knowledge, search, or selection only	Reset exact S0; provide the learned information but none of the state or model changes. A qualified old-task path succeeds.
Activation or restoration	A pre-existing state variable such as enabled, current, mounted, or valid	The action model remains byte-identical; a valid old-model transition changes the state; the full prefix-plus-execution policy is valid from S0.
Ordinary condition construction	A new artifact or commitment is created using an already-existing build, request, or negotiation action	The old model checker finds a policy that includes constructing the condition. Therefore the condition did not create closure reachability.
Model or institutional extension	Action schema, interface vocabulary, policy rule, delegation class, or authority graph changes	Old model is bounded-UNSAT including all L1 preparation; new model is SAT under old task; the exact model diff is necessary.
Principal-policy transition	A principal’s response rule, preference, legal status, or willingness changes	Hold the proposal and external world fixed while replaying the old and new decision functions.
Task mutation	G, floor, required principals, Q, horizon, or resources change	The post trace fails the old evaluator and passes only the new evaluator.
Invalid success	Evidence or execution is unsound	Independent old-task verifier rejects authority, provenance, target state, cost, exact-once behavior, freshness, or acceptance.
4.3 Necessary evidence for a same-Q formation claim

The following are individually necessary:

N1. Semantic task invariance

The same executable evaluator, schema versions, thresholds, principal requirements, authority map, value floor, budget, and horizon must be used.

A text hash alone is insufficient. The package should include evaluator code and positive/negative test vectors.

N2. Valid post-intervention success

There must be an independently verified post-state trace that passes the old task.

N3. Bounded pre-state unreachability

A complete finite model checker, exhaustive search, or formal proof must show that no qualified policy existed within the declared action language, principal-response model, horizon, and resources.

A failed planner run is not this evidence.

N4. Inclusion of all fair preparatory actions

The pre-state search must include the same probes, human escalation, approval requests, adapter construction, policy proposals, and repair capabilities later used by the candidate.

Otherwise the baseline is being prevented from taking the very actions called “formation.”

N5. Counterfactual dependence

Removing the intervention while preserving other relevant conditions must remove reachability.

For multi-part interventions, minimal sufficient subsets should be identified.

N6. Authority validity

Every privileged action and model change must be performed or explicitly delegated by the correct authority, with exact object, task, target, scope, time, and nonce binding.

N7. Common resource accounting

Formation work must not be free. Search, probes, failed attempts, human time, model changes, adapter development, and verification must be included.

4.4 Jointly sufficient evidence in a finite synthetic model

Within a finite simulator, the following package would be sufficient for a bounded formation classification:

Exact hashes of S0, old task, evaluator, action model, authority map, budget, horizon, and principal policies.

A complete pre-state UNSAT certificate for all L0+L1 actions.

A post-intervention qualified witness trace under the unchanged task.

A precise action-model or institutional diff.

Independent authority, outcome, cost, and acceptance verification.

Exhaustive ablation showing that the model-changing intervention, or a minimal intervention set containing it, is necessary.

A replay showing that knowledge alone and ordinary state preparation alone are insufficient.

A fair strong-center and human-escalation baseline.

Outside a finite closed model, absolute “no path existed” is generally too strong. The defensible claim becomes:

No qualified policy existed within action language A, horizon H, resource budget B, and principal-response family Δ.

4.5 Main failure modes
Incomplete closure

A planner is declared unable to solve the task because approval, repair, adapter building, or human escalation was omitted from its action set.

Endpoint-only qualification

The final state is correct, but repeated effects, stale authority, hidden cost, or an invalid prefix are ignored.

Knowledge contamination

A post-hoc replay gives a baseline information that could not legally have been obtained at S0, or withholds information that the candidate was allowed to probe.

Unstable principal policies

A principal’s response changes because of time, persuasion, trust, or unmodeled interaction, but the analysis treats it as a fixed world fact.

Baseline asymmetry

The candidate can modify models or request human work while the central planner is restricted to direct execution.

Meta-action inflation

The old action language includes an unconstrained operation such as “write any program” or “ask a human to solve it,” making every constructible condition trivially pre-existing.

The closure must therefore be operationally bounded, costed, and authority-constrained.

Same-process overfitting

The same research process defines the theory, worlds, implementation, adversarial tests, repairs, and root recheck. The result may be internally coherent while sharing one blind spot.

Cryptographic authority laundering

A valid signature is treated as proof that the signer possessed the relevant authority or accepted responsibility. Those are separate questions.

4.6 Strongest counterexamples against the layered account

The layered account is my preferred reconstruction, but it has real limits.

Counterexample 1: A genuinely new institution

Suppose no existing principal can legally delegate a required action. A regulator or governing body then creates a new delegation class, without changing the outcome goal or value floor. The new legal relation makes a qualified path available.

This is genuine bounded reachability formation relative to the old institutional model. The prefix-closure test does not collapse it because the old model contained no authorized transition that could create the relation.

However, this still does not imply a novel computational method. Ordinary legislation, governance, or policy administration may be the complete solution.

Counterexample 2: Preferences are constituted through interaction

A principal may not have a fixed hidden threshold waiting to be discovered. Deliberation, explanation, and joint design may create a commitment that did not previously exist.

A simulator with frozen response functions cannot fully represent this. A method that helps principals form a joint intention might be valuable even when no static-model account captures it cleanly.

That requires real-principal or behavioral evidence, not a synthetic trace.

Counterexample 3: Open-ended tool invention

A novel adapter, proof technique, or program may be invented. Whether the path “already existed” depends on whether the old model includes a meta-action such as “synthesize arbitrary code.”

A closure broad enough to include all human creativity becomes vacuous; a closure narrow enough to be executable makes formation relative to the chosen abstraction.

Counterexample 4: Algorithmic value without ontic formation

A valid path may exist but be computationally inaccessible to every practical baseline. A specialized method may find it reliably.

That is real method value, even though the correct causal classification is discovery rather than creation.

Counterexample 5: No special mechanism is needed

A strong central planner, with the same probes, local authority calls, adapter builder, human escalation, budget, and verifier, finds every qualified policy that the proposed mechanism finds and correctly rejects the same impossible cases.

This result would fully answer the research question positively:

The problem is solved by an existing composition; no additional formation method is needed.

5. Minimal discriminating experiment
5.1 Experiment name

Qualified Handoff MiniSim — QHM-1

The simulator tests a small cross-principal handoff:

O: owner, the only principal permitted to authorize release.

P: producer, which holds the artifact.

T: target, the only principal permitted to accept and project it.

H: human or engineer escalation.

A: policy or interface administrator.

C: controller, which may plan and request but may not impersonate.

W: independent witness and evaluator.

5.2 Frozen task

A trial succeeds only when, by horizon 8 and cost at most 10:

exact artifact hash h appears in T’s authoritative store;

it appears exactly once;

it is represented under target schema β;

O has issued an exact-scope authorization bound to:

task hash,

artifact hash,

target,

operation,

nonce,

issue time,

expiry;

T has accepted the projection;

the controller has not acted or signed as O, T, H, or A;

authoritative cost logs remain intact;

W independently reads the target state and ledger;

the original task version is unchanged.

Q evaluates the full trace so that duplicate effects or an invalid setup prefix cannot be hidden behind a correct final state.

5.3 Action layers
L0: direct execution

transfer(P,T,artifact,route)

project(T,artifact)

accept(T,artifact)

readback(W,target)

verify(W,trace)

L1: ordinary preparation

probe(C,principal,question)

request_enable(C,T,endpoint)

enable(T,endpoint)

request_authorization(C,O,proposal)

issue_authorization(O,proposal)

request_commitment(C,T,terms)

sign_commitment(T,terms)

build_known_adapter(H,α→β)

install_known_adapter(T,adapter)

renew_credential(principal)

recover_service(principal)

L2: model or institutional extension

propose_new_operator(C or H,A,spec)

register_new_operator(A,spec)

create_new_delegation_rule(A,rule)

register_new_schema_mapping(A,mapping)

L3: prohibited task-changing controls

lower value floor;

remove O;

increase budget;

weaken exact-once;

accept producer self-report;

change target witness.

These controls are available only to demonstrate task drift, not as valid solutions.

5.4 Hidden paired worlds

Every system receives the same visible task and initial message. The hidden-world label is kept by the external runner.

World	Hidden reality	Ground-truth interpretation
W-DISCOVER	An alternate compatible target route is already active but unadvertised.	Latent path. Knowledge or search is the blocker.
W-ENABLE	The compatible route exists but is disabled. T is already authorized to enable it.	Ordinary activation; L1 closure was reachable.
W-COMMIT	O will authorize only if T signs a specified liability commitment. Both actions already exist.	Negotiation or commitment as ordinary contingent preparation.
W-BUILD	No compatible route exists, but H may build a known adapter using an existing authorized action.	Condition construction inside the old closure. No special formation mechanism required.
W-EXTEND	No known adapter can work. A can register a genuinely new operator after receiving a valid proposal.	L1 is unreachable; L2 is reachable. Model-level formation.
W-DRIFT	No path satisfies the old value floor and principal requirements. Weakening Q would make a surface result pass.	Task mutation only.
W-SUBSTITUTE	A surface result can be produced only by controller signing, stale authority, or producer self-report.	Invalid apparent success.
W-UNSAT	No qualified path or authorized extension exists within the horizon and budget.	Correct result is bounded unreachable or valid refusal.

The worlds should be paired so that trivial initial classification is impossible:

W-DISCOVER and W-ENABLE initially expose the same “primary route unavailable” message.

W-COMMIT and W-UNSAT initially expose the same owner refusal.

W-BUILD and W-EXTEND initially expose the same schema mismatch.

W-DRIFT and W-SUBSTITUTE can produce the same superficial final-state report.

5.5 Systems under test
Ground-truth oracle

Not a competitor. It sees the hidden state and exhaustively computes:

direct reachability;

preparatory closure reachability;

model-extension reachability;

minimal intervention sets;

bounded UNSAT certificates.

Baseline B1: strong central contingent planner with human escalation

It receives:

the same observation API;

the same probes;

the same principal endpoints;

the same adapter builder;

the same L2 proposal channel;

the same cost and horizon;

the same human escalation quota.

It may synthesize the entire plan centrally, but every privileged action must be executed and signed by the correct principal.

Baseline B2: mature workflow composition

A rule-based stack containing:

approval workflow;

policy checks;

adapter registry;

exception routing;

human escalation;

independent verification.

Candidate F

The proposed formation mechanism, with no additional information, keys, actions, budget, or human access.

Optional ablation B1-no-human

The strong planner without human escalation, to determine whether any advantage is merely supplied by human exception handling.

5.6 Fairness requirements

World labels and hidden policy parameters are blinded.

Every system uses the same observation and action API.

Human responses come from one separate scripted oracle with fixed cost and latency.

No method receives privileged keys or direct access to target truth.

All signing keys are runtime-random and held by separate principal processes.

The evaluator, target store, identity assignment, and cost ledger are runner-owned.

The old task evaluator is immutable during a run.

Random identifiers and action ordering prevent hard-coded world recognition.

All failed probes, retries, human calls, and model changes are costed.

The candidate and baselines receive identical L2 proposal capabilities.

This reuses the strongest parts of the repaired 52-test harness while adding the missing causal layer.

5.7 Automatic replays for every reported success
Replay R1: knowledge-only replay

Reset exact S0.

Preserve all information learned in the successful run.

Remove all state, authorization, commitment, adapter, and model changes.

Search again under the old task.

Success indicates latent discovery or search failure.

Replay R2: fixed-model prefix replay

Reset exact S0.

Restore the original action model.

Allow all original L1 actions.

Search for a policy that includes the observed preparation steps.

Success means the episode was activation, negotiation, recovery, or condition construction inside the old closure.

Replay R3: model-extension replay

Reset S0.

Apply only the exact L2 model or institutional diff.

Keep the old task.

Search and execute.

This tests whether the extension is sufficient.

Replay R4: intervention ablation

For the small intervention set, evaluate every subset and, where order matters, relevant orderings.

Report:

necessary interventions;

sufficient interventions;

minimal sufficient sets;

redundant interventions;

synergistic causes.

Replay R5: old-task verification

Run the original evaluator against the final trace regardless of what task version the system reports.

Replay R6: authority substitution control

Replace one authentic authority action at a time with:

controller signature;

producer self-report;

stale signature;

wrong target binding;

wrong nonce;

wrong policy version.

Every replacement must fail.

Replay R7: endpoint and repeated-effect control

Run worlds in which:

the final state is correct but the effect happened twice;

the in-process log claims success but the target does not;

the target is correct but the authoritative cost log is missing.

These must fail old Q.

5.8 Measurements

Primary measurements:

qualified-success rate under old Q;

correct-refusal or bounded-UNSAT rate;

invalid-success rate;

causal-classification accuracy;

formation-depth accuracy;

pre-state SAT/UNSAT agreement with the oracle;

minimal intervention-set recovery.

Comparative measurements:

total cost;

number of probes;

human escalations;

number of principal decisions;

number of model changes;

time to valid success or correct termination;

repeated-seed reproducibility.

The principal result is not “who got more green runs.” It is:

Which system obtains more independently qualified outcomes or correct no-path classifications without changing the task or authority model, under identical information and intervention capabilities?

6. Result-to-conclusion table
Observed result	Supported conclusion	Unsupported conclusion
Exact S0 replay produces a valid old-task path without any state or model change.	Latent path existed; original failure was discovery, search, or use.	Reachability was created.
Knowledge-only replay succeeds.	Disclosure or model knowledge was sufficient.	Activation or condition creation was necessary.
Knowledge-only replay fails, but an authorized enable or repair prefix plus execution succeeds in the old model.	Direct executability changed; preparatory closure already existed.	Global reachability first arose after activation.
A new commitment is necessary, but requesting and signing it were actions in the old model.	Ordinary contingent negotiation or preparation.	A new causal primitive is established.
A known adapter must be built, and build_known_adapter was already available and affordable.	Ordinary constructive planning or engineering.	No path existed from S0.
Old L0+L1 model is certified UNSAT; a valid L2 operator registration makes it SAT; old task passes.	Bounded model-level or institutional reachability formation occurred.	A new general method is required.
Strong central planner with human escalation proposes and obtains the same valid L2 extension as the candidate.	Existing composition fully solves the case.	Candidate-specific formation value.
Candidate and central baseline both solve all valid worlds with similar validity and cost.	No special formation mechanism is needed.	Federation or a new protocol adds value.
Human-led workflow solves every valid world and correctly rejects the others.	A disciplined human process is sufficient at this scale.	Automation is necessary.
Candidate succeeds only after lowering the floor, changing Q, removing a principal, or increasing resources.	Task mutation.	Same-task formation.
Candidate reports success but independent authority or target verifier rejects.	Apparent success through substitution or self-report.	Any reachability claim.
Candidate has more surface successes but also more verifier failures.	Candidate is less reliable, not more capable.	Superior formation.
All systems correctly return bounded UNSAT in W-UNSAT.	Refusal and impossibility handling are working.	The experiment failed because no success occurred.
Candidate alone succeeds across blind instances after full capability parity; central and workflow baselines fail; all old-task and authority checks pass.	Evidence of method-level advantage worth further investigation.	Generality, production value, human recognition, or A2A uniqueness.
Different minimal intervention sets succeed independently.	Reachability was overdetermined; there is no unique cause.	Any single observed intervention was “the” cause.
The first chronological intervention appears pivotal, but subset replay finds an earlier alternative route.	Chronological first-crossing was misleading.	First observed success identifies causal necessity.
7. Missing evidence and next local test
7.1 What this experiment cannot establish

Even a successful QHM-1 result would not establish:

that a real principal prefers, recognizes, accepts, or assumes responsibility for the result;

that simulated commitments correspond to meaningful human commitments;

production security outside the modeled attack surface;

business value;

general frequency of the identified world classes;

scalability to open action spaces or long horizons;

real strategic behavior, deception, persuasion, or trust formation;

absolute real-world unreachability;

novelty relative to every existing workflow, planning, governance, or integration method;

that federation, A2A, Towow, or any particular architecture is necessary;

blind independence unless the runner or implementation is external;

that a model-level formation event requires a reusable formation method.

The simulator can establish a much narrower but important result:

Within a finite declared world, it can distinguish pre-existing reachability, ordinary preparation, model-level extension, task mutation, and invalid success.

7.2 Evidence that would most change the present answer

The most answer-changing materials would be, in order:

1. A complete old-model bounded-UNSAT certificate

This must include all fair probes, approvals, human escalation, repairs, adapter builds, and model-proposal actions.

Without it, the formation claim remains underdetermined.

2. A matched strong-center result

The central planner must receive the same information, human service, authority endpoints, meta-actions, budget, and verifier.

A central-baseline success would strongly support none needed.

A repeated blind candidate-only success would support a residual.

3. Exact causal replays

Knowledge-only, fixed-model prefix, model-extension, old-task, and intervention-subset replays would directly classify the episode.

4. External blinded implementation

An independent team should receive only:

simulator contract;

task and API specification;

baseline requirements;

acceptance tests.

They should not receive the expected taxonomy labels for individual worlds.

5. Versioned principal-policy models

The experiment must show whether a commitment resulted from:

discovering a fixed condition;

satisfying a fixed condition;

or changing the principal’s decision policy.

6. At least one hard no-special-mechanism world

The suite should deliberately contain cases in which:

a hidden route already exists;

a central planner solves through ordinary preparation;

a human workflow solves;

the correct result is UNSAT.

Otherwise the simulator is structurally biased toward discovering “formation.”

7.3 The next local test

The next test should not be a larger success demonstration. It should be a causal replayer wrapped around the repaired execution harness.

A minimal local package would contain:

/spec/task.json
/spec/task_evaluator/
    evaluator.py
    positive_vectors.json
    negative_vectors.json

/spec/domain_l0.json
/spec/preparation_l1.json
/spec/model_actions_l2.json
/spec/authority_map.json
/spec/resource_account.json

/worlds/
    discover.*
    enable.*
    commit.*
    build.*
    extend.*
    drift.*
    substitute.*
    unsat.*

/runner/
    blinded_world_loader
    runtime_identity_service
    principal_processes
    authoritative_cost_ledger
    target_store
    independent_verifier
    bounded_model_checker
    counterfactual_replayer

/baselines/
    central_human/
    workflow_stack/

/candidate/
    formation_method/

/outputs/
    traces.jsonl
    manifests/
    sat_witnesses/
    unsat_certificates/
    intervention_ablations/
    result_matrix.csv

The release gate should require all of the following:

Every task, model, authority, policy, and resource object is hashed before a trial.

Every reported success passes the immutable old-task evaluator.

Every world has oracle-computed L0, L1, and L2 reachability labels.

Every success receives all causal replays.

Every intervention receives actor, authority, cost, before-hash, and after-hash records.

Strong-center and workflow baselines are run under exact capability parity.

World labels remain hidden until outputs are sealed.

The suite contains discovery, activation, construction, extension, drift, substitution, and true-UNSAT cases.

Candidate advantage is reported separately as:

better discovery;

better preparatory planning;

better model-extension proposal;

lower cost;

lower invalid-success rate.

No result is called general reachability formation unless old L0+L1 unreachability and new old-task reachability are both certified.

Present conclusion

On the packet as given, an additional formation method is not yet warranted, but neither is it ruled out.

The present evidence supports this narrower conclusion:

The project has developed a substantially stronger local synthetic execution-integrity harness. It has not yet shown which state or model change first made an unchanged qualified task reachable.

The central unresolved test is not another successful cross-process run. It is the prefix-closure and model-difference test:

Was the successful preparation already a valid policy from S0?

If not, exactly what old-model edge or institution was missing?

Did a fair central planner, human workflow, adapter process, or existing composition have the same ability to create it?

Does the result still pass the immutable old task under independent authority and target verification?

QHM-1 is small enough to answer those questions locally and strong enough to produce a genuine negative result: it can conclude that no special formation mechanism is needed.

来源
