# CE-001 G1 provenance module

This directory is a local component model for the G1 handoff only. It starts
at `IntentAtCoordinationInterface`; the clarification prelude is hashed and
linked, but its vague request, questions, `IntentCandidate`, explain-back, and
claim are not method input and do not count as G1 success.

The default discovery run now uses three distinct PIDs: the controller, an
owner service, and a standalone stdlib-only worker launched with
`python -I -S` from a sanitized temporary cwd. The discovery worker receives:

- the frozen CE-001 intent and exact object/version constraints;
- a generic `discover(kind, predicates)` action for `candidate`, `resource`,
  and `partner`;
- evidence returned by owner-backed services under the allowed disclosure
  envelope.

It does **not** receive `L_benchmark`, `D_actual`, a list of allowed/correct
paths, the private service records, or a final proposal. The method constructs
a candidate from evidence it actually obtained. The private evaluator runs an
invalidity-first gate before any positive conclusion and resolves source and
Authority aliases independently.

`L_benchmark` is the frozen structural candidate population; `D_actual` is the
subset with a legal, in-budget evidence path at t0. A t1 operator can create a
qualification in `FULL_ACTUAL_TRACE`, but cannot be copied into `T0_REPLAY` or
silently enlarge `D_actual`. Preregistered operator application/removal/reversal
is controller-side; the method is not shown an answer-shaped operator menu.

`python3 runner.py` emits a composition-ready JSON object. Each
`g1_handoff` is bound by
`episode_id/Q_version/object_id/operation_id/owner_id/evidence_hash`, remains
`CANDIDATE_NOT_COMMITMENT`, and intentionally contains no G2-G7 result.
An otherwise valid owner-backed candidate outside the frozen `L_benchmark` is
reported as `NOVEL_CANDIDATE_FOR_NEXT_VERSION` and preserved for a next fixture
version; population membership is not an Authority or provenance validity gate.

Worker queries are forwarded byte-for-byte to the owner service. This owner is
explicitly a `CONTROLLER_HOSTED_SYNTHETIC_OWNER_FIXTURE`: the controller loads
its records/operators from the same synthetic `World`, so neither independent
owner truth nor real owner origin is claimed. Before launch, the controller
assigns distinct source/state/process instance IDs and later binds owner READY,
every response/event origin, worker READY, every query, and the worker result
to those assignments and to the corresponding controller-observed
`Popen.pid`. The owner issues each evidence event with those bindings, its
state version, and the SHA-256 of the exact request bytes.

The controller forwards a valid raw owner response unchanged to the worker and
records every JSONL frame with byte length, SHA-256, and base64 wire bytes.
Owner PID `424242`, worker PID `424242`, inconsistent event origin, and a wrong
source instance are actual subprocess injections; each fails closed before the
response can receive positive credit. Their receipts retain the actual
`Popen.pid`, controller-assigned launch instance, rejection reason, and raw
frames. The controller evaluates only after the worker exits;
evaluator/controller process separation is not claimed.

The existing internal handoff remains for the original regression surface.
The composition-facing `g1_line_envelope` uses the
`towow-g1-provenance-line-envelope-v2` schema and G1-prefixed fields. A
recursive validator rejects contract-success or later-line claim keys/values;
the old explicit non-claim list is not copied into this envelope. It includes
the local candidate identifiers, a SHA-256 reference to the exact episode ID,
controller-bound synthetic source instances, invalidity reasons, raw-trace
hash, and output hash. Hashing the episode reference keeps frozen identifiers
such as the E3 pair from importing later-line vocabulary into this envelope;
the exact episode ID remains in the forensic result outside it. Authority-root
data remains internal to the G1 invalidity evaluator and is not renamed into
the exported envelope.

Semantic failure-injection labels are not transmitted to the worker. The only
boundary-test label the worker can receive is its own PID-attestation injection;
this preserves the original five owner/evaluator attacks as method-blind
regressions.

The population receipt binds each episode's prelude/interface hashes,
`L_benchmark`, `D_actual`, and the private evidence/source/Authority oracle
roots. Those fields never enter method input; the binding prevents a later
denominator rewrite from preserving the same population hash.

The report includes a frozen manifest binding the complete Python source tree,
public and private input byte receipts, raw process-boundary traces, evaluator
raw traces, and result bytes. The private evaluator input really contains
`expected`, `L_benchmark`, `D_actual`, oracle roots, and a private canary before
the worker starts; scans of actual worker inbound bytes and worker-reachable
reflection/closure/frame/gc/import/env/argv/cwd surfaces do not contain them.

Evidence boundary: this is still a local synthetic component model. Distinct
PIDs, actual PID/launch-instance binding, and exact transmitted bytes establish
the cooperative default worker's process/API non-receipt and source-mismatch
rejection boundary, not hostile OS confinement. An executable absolute-path
probe remains `RED_NOT_ISOLATED`: a same-user process that already knows the
repository path can see that private fixture source is readable. The module
does not establish a real owner, independent owner truth/origin, a real product
run, real discovery, real power delivery, or complete CE-001 success. Frozen
`D_actual` recall therefore measures this local fixture and is not a general
discovery claim or a method-comparison winner.
